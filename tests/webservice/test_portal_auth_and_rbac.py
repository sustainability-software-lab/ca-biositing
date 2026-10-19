"""Unit and integration tests for isolated Portal OIDC auth, 2-role RBAC, and GCS dashboard proxy."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Generator

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from ca_biositing.datamodels.database import get_session
from ca_biositing.datamodels.models.qc.qc_review_decision import QcReviewDecision
from ca_biositing.webservice.config import config
from ca_biositing.webservice.dependencies import get_current_user
from ca_biositing.webservice.main import app
from ca_biositing.webservice.services.dashboard_loader import clear_dashboard_cache
from ca_biositing.webservice.services.portal_auth import (
    PORTAL_COOKIE_NAME,
    PortalUser,
    create_portal_token,
)
import ca_biositing.webservice.services.portal_auth as portal_auth_module


@pytest.fixture
def sqlite_engine():
    """Create an in-memory SQLite engine for portal auth and RBAC tests."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(
        engine,
        tables=[QcReviewDecision.__table__],
    )
    return engine


@pytest.fixture
def client(
    sqlite_engine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient with isolated config and local dashboard directory."""
    monkeypatch.setenv(
        "BIOSITING_QC_SEED_CSV_PATH", str(tmp_path / "qc_seed.csv")
    )
    local_dash_dir = tmp_path / "exports_plots"
    local_dash_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("BIOSITING_DASHBOARDS_LOCAL_DIR", str(local_dash_dir))

    monkeypatch.setattr(config, "require_dashboard_auth", True)
    monkeypatch.setattr(
        config,
        "dashboard_allowed_domains",
        ["lbl.gov", "ucdavis.edu", "beamcircular.org"],
    )
    monkeypatch.setattr(
        config,
        "dashboard_allowed_emails",
        ["external.partner@stanford.edu"],
    )
    monkeypatch.setattr(
        config,
        "dashboard_admin_emails",
        ["admin.lead@lbl.gov", "petersmith@lbl.gov"],
    )
    monkeypatch.setattr(config, "dashboards_bucket_name", "")
    clear_dashboard_cache()

    def _override_session() -> Generator[Session, None, None]:
        with Session(sqlite_engine) as session:
            yield session

    app.dependency_overrides[get_session] = _override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    clear_dashboard_cache()


def test_calbioscape_cookie_and_endpoints_remain_isolated(client: TestClient) -> None:
    """Verify CalBioScape endpoints and `access_token` cookie do not collide with `biocirv_portal_token`."""
    import inspect

    assert PORTAL_COOKIE_NAME == "biocirv_portal_token"
    dep_source = inspect.getsource(get_current_user)
    assert "access_token" in dep_source
    assert PORTAL_COOKIE_NAME not in dep_source

    # Root and health endpoints work normally
    hello_resp = client.get("/hello")
    assert hello_resp.status_code == 200
    assert hello_resp.json() == {"message": "Hello, world"}

    v1_health = client.get("/v1/health")
    assert v1_health.status_code == 200
    assert v1_health.json() == {"status": "ok"}

    # Setting a portal token cookie does NOT authenticate CalBioScape /v1/feedstocks endpoints
    analyst_token = create_portal_token(
        PortalUser(email="scientist@lbl.gov", role="analyst")
    )
    client.cookies.set(PORTAL_COOKIE_NAME, analyst_token)
    feedstocks_resp = client.get(
        "/v1/feedstocks/usda/census/crops",
        params={"commodity": "CORN", "statisticcat": "PRODUCTION", "geoid": "06001"},
    )
    assert feedstocks_resp.status_code == 401

    # Conversely, setting an arbitrary CalBioScape `access_token` cookie does NOT grant portal access
    client.cookies.clear()
    client.cookies.set("access_token", "calbioscape-dummy-jwt")
    me_resp = client.get("/v1/qc/auth/me")
    assert me_resp.status_code == 401


def test_domain_and_email_allowlist_and_role_resolution(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify @lbl.gov, @ucdavis.edu, @beamcircular.org, and allowlisted emails get analyst; admins get admin; outside emails get 403."""
    # 1. @lbl.gov -> analyst
    r_lbl = client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "researcher@lbl.gov", "name": "LBL Researcher"},
    )
    assert r_lbl.status_code == 200
    assert r_lbl.json()["role"] == "analyst"
    assert PORTAL_COOKIE_NAME in r_lbl.cookies

    # 2. @ucdavis.edu -> analyst
    r_ucd = client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "ag.scientist@ucdavis.edu"},
    )
    assert r_ucd.status_code == 200
    assert r_ucd.json()["role"] == "analyst"

    # 3. @beamcircular.org -> analyst
    r_beam = client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "fellow@beamcircular.org"},
    )
    assert r_beam.status_code == 200
    assert r_beam.json()["role"] == "analyst"

    # 4. Explicit DASHBOARD_ALLOWED_EMAILS -> analyst
    r_allowed = client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "external.partner@stanford.edu"},
    )
    assert r_allowed.status_code == 200
    assert r_allowed.json()["role"] == "analyst"

    # 5. Explicit DASHBOARD_ADMIN_EMAILS -> admin
    r_admin = client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "admin.lead@lbl.gov"},
    )
    assert r_admin.status_code == 200
    assert r_admin.json()["role"] == "admin"

    # 6. Non-whitelisted outside email -> 403 Forbidden
    r_outside = client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "intruder@gmail.com"},
    )
    assert r_outside.status_code == 403

    # 7. Google OIDC token verification path
    monkeypatch.setattr(
        portal_auth_module,
        "verify_google_id_token",
        lambda token: {
            "email": "petersmith@lbl.gov",
            "email_verified": True,
            "name": "Peter Smith",
        },
    )
    r_oidc = client.post(
        "/v1/qc/auth/google",
        json={"id_token": "mock-google-oidc-id-token"},
    )
    assert r_oidc.status_code == 200
    assert r_oidc.json()["role"] == "admin"
    assert r_oidc.json()["email"] == "petersmith@lbl.gov"


def test_dashboard_routes_auth_redirect_and_rbac_for_products_1_to_5(
    client: TestClient,
    tmp_path: Path,
) -> None:
    """Verify unauthenticated redirect (302), analyst access to Products 1-4, and admin-only access to Product 5."""
    local_dash_dir = tmp_path / "exports_plots"
    (local_dash_dir / "metadata").mkdir(parents=True, exist_ok=True)
    (local_dash_dir / "audit").mkdir(parents=True, exist_ok=True)

    (local_dash_dir / "index.html").write_text("<html>Gallery</html>", encoding="utf-8")
    (local_dash_dir / "metadata" / "resource_analysis_dashboard.html").write_text(
        "<html>Product 1 Analysis</html>", encoding="utf-8"
    )
    (local_dash_dir / "metadata" / "resource_ai_overview_dashboard.html").write_text(
        "<html>Product 1</html>", encoding="utf-8"
    )
    (local_dash_dir / "metadata" / "resource_qc_outlier_dashboard.html").write_text(
        "<html>Product 2</html>", encoding="utf-8"
    )
    (local_dash_dir / "metadata" / "resource_explorer_dashboard.html").write_text(
        "<html>Product 3</html>", encoding="utf-8"
    )
    (local_dash_dir / "metadata" / "resource_audit_workbench.html").write_text(
        "<html>Product 4</html>", encoding="utf-8"
    )
    (local_dash_dir / "audit" / "db_environment_drift_dashboard.html").write_text(
        "<html>Product 5 Drift Audit</html>", encoding="utf-8"
    )

    # 1. Public login.html is accessible without authentication (even via built-in fallback)
    login_resp = client.get("/v1/dashboards/login.html", follow_redirects=False)
    assert login_resp.status_code == 200
    assert "BioCirV" in login_resp.text

    # 2. Unauthenticated request to Product 2 redirects 302 to login.html?next=...
    unauth_resp = client.get(
        "/v1/dashboards/metadata/resource_qc_outlier_dashboard.html?resource=almond",
        follow_redirects=False,
    )
    assert unauth_resp.status_code == 302
    assert unauth_resp.headers["location"].startswith(
        "/v1/dashboards/login.html?next=/v1/dashboards/metadata/resource_qc_outlier_dashboard.html"
    )

    # 3. Legacy /dashboards and /dashboards/{subpath} redirect 307 to /v1/dashboards/...
    legacy_root = client.get("/dashboards", follow_redirects=False)
    assert legacy_root.status_code == 307
    assert legacy_root.headers["location"] == "/v1/dashboards/index.html"

    legacy_resp = client.get(
        "/dashboards/metadata/resource_explorer_dashboard.html",
        follow_redirects=False,
    )
    assert legacy_resp.status_code == 307
    assert (
        legacy_resp.headers["location"]
        == "/v1/dashboards/metadata/resource_explorer_dashboard.html"
    )

    # 4. Log in as analyst: Products 1-4 succeed (200), Product 5 is blocked (403)
    client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "analyst@ucdavis.edu"},
    )
    root_resp = client.get("/v1/dashboards")
    assert root_resp.status_code == 200
    for subpath in [
        "index.html",
        "metadata/resource_analysis_dashboard.html",
        "metadata/resource_ai_overview_dashboard.html",
        "metadata/resource_qc_outlier_dashboard.html",
        "metadata/resource_explorer_dashboard.html",
        "metadata/resource_audit_workbench.html",
    ]:
        resp = client.get(f"/v1/dashboards/{subpath}")
        assert resp.status_code == 200, f"Analyst should access {subpath}"
        assert resp.headers.get("X-Dashboard-Source") == "local"

    drift_analyst = client.get(
        "/v1/dashboards/audit/db_environment_drift_dashboard.html"
    )
    assert drift_analyst.status_code == 403

    # 5. Log in as admin: Product 5 succeeds (200)
    client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "admin.lead@lbl.gov"},
    )
    drift_admin = client.get(
        "/v1/dashboards/audit/db_environment_drift_dashboard.html"
    )
    assert drift_admin.status_code == 200
    assert "Product 5 Drift Audit" in drift_admin.text

    # 6. Path traversal segments are rejected
    from fastapi import HTTPException
    from ca_biositing.webservice.services.dashboard_loader import (
        sanitize_dashboard_subpath,
    )

    with pytest.raises(HTTPException) as exc_info:
        sanitize_dashboard_subpath("../etc/passwd")
    assert exc_info.value.status_code == 400


def test_dashboard_loader_gcs_fallback_and_etag_cache(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify /v1/dashboards/{subpath} falls back to mocked GCS bucket when local file is absent."""
    monkeypatch.setattr(config, "dashboards_bucket_name", "biocirv-staging-dashboards")
    monkeypatch.setattr(config, "dashboards_gcs_prefix", "dashboards/staging/latest")

    download_calls = {"count": 0}

    class _MockBlob:
        def __init__(self, name: str) -> None:
            self.name = name
            self.etag = "etag-v1"

        def exists(self) -> bool:
            return self.name.endswith("metadata/gcs_only_dashboard.html")

        def reload(self) -> None:
            return None

        def download_as_bytes(self) -> bytes:
            download_calls["count"] += 1
            return b"<html>Loaded from GCS Bucket</html>"

    class _MockBucket:
        def __init__(self, name: str) -> None:
            self.name = name

        def blob(self, blob_name: str) -> _MockBlob:
            return _MockBlob(blob_name)

    class _MockStorageClient:
        def bucket(self, bucket_name: str) -> _MockBucket:
            return _MockBucket(bucket_name)

    import ca_biositing.webservice.services.dashboard_loader as loader_mod

    monkeypatch.setattr(
        loader_mod,
        "get_gcs_storage_client",
        lambda: _MockStorageClient(),
    )

    client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "analyst@lbl.gov"},
    )

    first = client.get("/v1/dashboards/metadata/gcs_only_dashboard.html")
    assert first.status_code == 200
    assert first.headers.get("X-Dashboard-Source") == "gcs"
    assert "Loaded from GCS Bucket" in first.text
    assert download_calls["count"] == 1

    # Second request within TTL is served from in-memory cache without re-downloading
    second = client.get("/v1/dashboards/metadata/gcs_only_dashboard.html")
    assert second.status_code == 200
    assert second.headers.get("X-Dashboard-Source") == "gcs_cache"
    assert download_calls["count"] == 1

    # Missing file on both local disk and GCS returns 404
    missing = client.get("/v1/dashboards/metadata/does_not_exist.html")
    assert missing.status_code == 404


def test_webservice_has_zero_pipeline_imports() -> None:
    """Verify no module in `ca_biositing.webservice` imports `ca_biositing.pipeline`."""
    webservice_root = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "ca_biositing"
        / "webservice"
        / "ca_biositing"
        / "webservice"
    )
    py_files = list(webservice_root.rglob("*.py"))
    assert py_files, "Expected Python files in ca_biositing.webservice"

    offending: list[str] = []
    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "ca_biositing.pipeline" in alias.name:
                        offending.append(f"{py_file.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if "ca_biositing.pipeline" in mod:
                    offending.append(f"{py_file.name}: from {mod} import ...")

    assert offending == [], f"Forbidden pipeline imports in webservice: {offending}"
