"""Tests for per-client API key endpoints and X-API-Key authentication.

Covers:
- POST /v1/auth/api-keys — admin creates key, raw key returned once
- GET /v1/auth/api-keys — list returns prefix only, not hash; supports pagination and filtering
- DELETE /v1/auth/api-keys/{id} — revocation blocks further use
- PATCH /v1/auth/api-keys/{id} — name/rate_limit update
- X-API-Key grants access to non-admin data endpoints (GET /v1/feedstocks/...)
- X-API-Key cannot be exchanged for a JWT via POST /v1/auth/refresh
- X-API-Key is blocked from admin endpoints (403)
- Invalid / revoked X-API-Key returns 401 on non-admin endpoints
- Rate limit enforcement returns 429
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from ca_biositing.datamodels.database import get_session
from ca_biositing.datamodels.models import ApiKey, ApiUser
from ca_biositing.webservice.main import app
from ca_biositing.webservice.services.analysis_service import AnalysisService
from ca_biositing.webservice.services.auth_service import get_password_hash

# Non-admin data endpoint guarded by get_current_user (accepts X-API-Key).
API_KEY_PROBE = "/v1/feedstocks/analysis/geoids"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="key_engine", scope="function")
def key_engine_fixture():
    """In-memory SQLite engine with ApiUser and ApiKey tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        ApiUser.__table__.create(conn, checkfirst=True)
        ApiKey.__table__.create(conn, checkfirst=True)
    yield engine
    engine.dispose()


@pytest.fixture(name="key_session", scope="function")
def key_session_fixture(key_engine):
    """A single SQLModel Session shared across all requests in a test.

    Sharing one session ensures that writes committed in one request are
    immediately visible to subsequent reads in the same test, working around
    SQLite in-memory StaticPool transaction-isolation quirks.
    """
    session = Session(key_engine)
    yield session
    session.close()


@pytest.fixture(name="key_client", scope="function")
def key_client_fixture(key_session):
    """TestClient that pins all requests to the same DB session.

    Each request gets the same session, but any uncommitted state left open
    after the handler returns (e.g., from list endpoints that SELECT without
    committing) is rolled back before the next request. This ensures each
    request starts with a clean transaction while preserving committed writes.
    """
    def override_get_session():
        try:
            yield key_session
        finally:
            # Roll back any open transaction left by the handler so the next
            # request starts fresh.  If the handler committed, this is a no-op.
            try:
                key_session.rollback()
            except Exception:
                pass

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture(name="admin_user", scope="function")
def admin_user_fixture(key_session) -> ApiUser:
    user = ApiUser(
        username="admin",
        hashed_password=get_password_hash("adminpass"),
        email="admin@test.com",
        is_admin=True,
        disabled=False,
    )
    key_session.add(user)
    key_session.commit()
    key_session.refresh(user)
    return user


@pytest.fixture(name="regular_user", scope="function")
def regular_user_fixture(key_session) -> ApiUser:
    user = ApiUser(
        username="user",
        hashed_password=get_password_hash("userpass"),
        email="user@test.com",
        is_admin=False,
        disabled=False,
    )
    key_session.add(user)
    key_session.commit()
    key_session.refresh(user)
    return user


@pytest.fixture(name="admin_token", scope="function")
def admin_token_fixture(key_client, admin_user) -> str:
    resp = key_client.post(
        "/v1/auth/token",
        data={"username": "admin", "password": "adminpass"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(name="user_token", scope="function")
def user_token_fixture(key_client, regular_user) -> str:
    resp = key_client.post(
        "/v1/auth/token",
        data={"username": "user", "password": "userpass"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(name="stub_probe")
def stub_probe_fixture(monkeypatch):
    """Stub the probe endpoint's data lookup; the test DB has no analysis view."""
    monkeypatch.setattr(AnalysisService, "list_geoids", staticmethod(lambda session: []))


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestCreateApiKey:
    """POST /v1/auth/api-keys"""

    def test_admin_creates_key_returns_raw_key_once(self, key_client, admin_token, admin_user):
        resp = key_client.post(
            "/v1/auth/api-keys",
            json={
                "name": "test-key",
                "api_user_id": admin_user.id,
                "rate_limit_per_minute": 60,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "raw_key" in body
        assert "key_prefix" in body
        assert body["raw_key"].startswith(body["key_prefix"])
        assert "id" in body

    def test_non_admin_cannot_create_key(self, key_client, user_token, admin_user):
        resp = key_client.post(
            "/v1/auth/api-keys",
            json={
                "name": "should-fail",
                "api_user_id": admin_user.id,
                "rate_limit_per_minute": 60,
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403

    def test_unknown_user_id_returns_404(self, key_client, admin_token):
        resp = key_client.post(
            "/v1/auth/api-keys",
            json={"name": "test", "api_user_id": 99999, "rate_limit_per_minute": 60},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404


class TestListApiKeys:
    """GET /v1/auth/api-keys"""

    def test_list_returns_prefix_not_hash(self, key_client, admin_token, admin_user):
        # Create a key first
        key_client.post(
            "/v1/auth/api-keys",
            json={"name": "my-key", "api_user_id": admin_user.id, "rate_limit_per_minute": 60},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = key_client.get(
            "/v1/auth/api-keys",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        keys = resp.json()
        assert len(keys) >= 1
        for k in keys:
            assert "key_prefix" in k
            assert "key_hash" not in k
            assert "raw_key" not in k

    def test_non_admin_cannot_list(self, key_client, user_token):
        resp = key_client.get(
            "/v1/auth/api-keys",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403

    def test_pagination_and_user_filter(self, key_client, admin_token, admin_user, regular_user):
        # Create 2 keys for admin_user, 1 for regular_user
        for name in ("key-a", "key-b"):
            key_client.post(
                "/v1/auth/api-keys",
                json={"name": name, "api_user_id": admin_user.id, "rate_limit_per_minute": 60},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        key_client.post(
            "/v1/auth/api-keys",
            json={"name": "key-c", "api_user_id": regular_user.id, "rate_limit_per_minute": 60},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Filter by admin_user — should see 2
        resp = key_client.get(
            f"/v1/auth/api-keys?api_user_id={admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

        # Pagination: limit=1, offset=0 → first key only
        resp = key_client.get(
            "/v1/auth/api-keys?limit=1&offset=0",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # Pagination: limit=10, offset=10 → empty (only 3 keys total)
        resp = key_client.get(
            "/v1/auth/api-keys?limit=10&offset=10",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0


class TestRevokeApiKey:
    """DELETE /v1/auth/api-keys/{id}"""

    def test_revoke_key_prevents_authentication(self, key_client, admin_token, admin_user):
        # Create key
        create_resp = key_client.post(
            "/v1/auth/api-keys",
            json={"name": "revoke-me", "api_user_id": admin_user.id, "rate_limit_per_minute": 0},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert create_resp.status_code == 201
        key_id = create_resp.json()["id"]
        raw_key = create_resp.json()["raw_key"]

        # Revoke
        del_resp = key_client.delete(
            f"/v1/auth/api-keys/{key_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert del_resp.status_code == 200

        # Clear the login cookie so only X-API-Key is available for auth.
        key_client.cookies.clear()

        # Revoked key must now return 401 on a non-admin endpoint that accepts
        # X-API-Key. 401 confirms auth failed, not 403 (which would mean auth
        # succeeded but access denied).
        auth_resp = key_client.get(
            API_KEY_PROBE,
            headers={"X-API-Key": raw_key},
        )
        assert auth_resp.status_code == 401

    def test_revoke_nonexistent_key_returns_404(self, key_client, admin_token, admin_user):
        resp = key_client.delete(
            "/v1/auth/api-keys/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404


class TestUpdateApiKey:
    """PATCH /v1/auth/api-keys/{id}"""

    def test_update_name_and_rate_limit(self, key_client, admin_token, admin_user):
        create_resp = key_client.post(
            "/v1/auth/api-keys",
            json={"name": "original-name", "api_user_id": admin_user.id, "rate_limit_per_minute": 60},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        key_id = create_resp.json()["id"]

        patch_resp = key_client.patch(
            f"/v1/auth/api-keys/{key_id}",
            json={"name": "updated-name", "rate_limit_per_minute": 120},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert patch_resp.status_code == 200
        body = patch_resp.json()
        assert body["name"] == "updated-name"
        assert body["rate_limit_per_minute"] == 120

    def test_partial_update_leaves_other_fields_unchanged(self, key_client, admin_token, admin_user):
        create_resp = key_client.post(
            "/v1/auth/api-keys",
            json={"name": "stable-name", "api_user_id": admin_user.id, "rate_limit_per_minute": 30},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        key_id = create_resp.json()["id"]

        patch_resp = key_client.patch(
            f"/v1/auth/api-keys/{key_id}",
            json={"rate_limit_per_minute": 90},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert patch_resp.status_code == 200
        body = patch_resp.json()
        assert body["name"] == "stable-name"
        assert body["rate_limit_per_minute"] == 90

    def test_patch_is_active_returns_422(self, key_client, admin_token, admin_user):
        """is_active is not a valid PATCH field — must return 422, not silently ignored."""
        create_resp = key_client.post(
            "/v1/auth/api-keys",
            json={"name": "boundary-test", "api_user_id": admin_user.id, "rate_limit_per_minute": 60},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert create_resp.status_code == 201
        key_id = create_resp.json()["id"]
        patch_resp = key_client.patch(
            f"/v1/auth/api-keys/{key_id}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert patch_resp.status_code == 422

    def test_patch_unknown_field_returns_422(self, key_client, admin_token, admin_user):
        """Any unrecognised field in the PATCH body must return 422."""
        create_resp = key_client.post(
            "/v1/auth/api-keys",
            json={"name": "boundary-test-2", "api_user_id": admin_user.id, "rate_limit_per_minute": 60},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert create_resp.status_code == 201
        key_id = create_resp.json()["id"]
        patch_resp = key_client.patch(
            f"/v1/auth/api-keys/{key_id}",
            json={"unknown_field": "value"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert patch_resp.status_code == 422


class TestApiKeyAuthentication:
    """X-API-Key header authentication on protected endpoints."""

    def test_valid_api_key_grants_non_admin_access(
        self, key_client, admin_token, admin_user, stub_probe
    ):
        """Valid X-API-Key grants access to non-admin endpoints (CurrentUserDep)."""
        create_resp = key_client.post(
            "/v1/auth/api-keys",
            json={"name": "frontend", "api_user_id": admin_user.id, "rate_limit_per_minute": 0},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        raw_key = create_resp.json()["raw_key"]

        # Clear login cookie so the request must authenticate via X-API-Key only.
        key_client.cookies.clear()

        resp = key_client.get(
            API_KEY_PROBE,
            headers={"X-API-Key": raw_key},
        )
        assert resp.status_code == 200

    def test_admin_api_key_cannot_be_exchanged_for_jwt(self, key_client, admin_token, admin_user):
        """CBS-SEC-002: an admin-owned API key must not mint a JWT via /refresh."""
        create_resp = key_client.post(
            "/v1/auth/api-keys",
            json={"name": "admin-key", "api_user_id": admin_user.id, "rate_limit_per_minute": 0},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        raw_key = create_resp.json()["raw_key"]
        key_client.cookies.clear()

        resp = key_client.post("/v1/auth/refresh", headers={"X-API-Key": raw_key})

        assert resp.status_code == 401
        assert "access_token" not in resp.json()
        assert "access_token" not in resp.cookies

    def test_valid_api_key_blocked_from_admin_endpoints(self, key_client, admin_token, admin_user):
        """X-API-Key must not access admin endpoints even for admin-linked keys."""
        create_resp = key_client.post(
            "/v1/auth/api-keys",
            json={"name": "admin-key", "api_user_id": admin_user.id, "rate_limit_per_minute": 0},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        raw_key = create_resp.json()["raw_key"]

        # Clear login cookie so only X-API-Key is used for auth.
        key_client.cookies.clear()

        # GET /v1/auth/api-keys requires AdminUserDep (JWT-only) — must return 401.
        resp = key_client.get(
            "/v1/auth/api-keys",
            headers={"X-API-Key": raw_key},
        )
        assert resp.status_code == 401

    def test_invalid_api_key_returns_401(self, key_client, admin_user):
        resp = key_client.get(
            API_KEY_PROBE,
            headers={"X-API-Key": "invalidkeyvalue12345"},
        )
        assert resp.status_code == 401

    def test_no_credentials_returns_401(self, key_client, admin_user):
        resp = key_client.get(API_KEY_PROBE)
        assert resp.status_code == 401


class TestRateLimiting:
    """Rate limiting via per-key fixed-window counter."""

    def test_exceeding_rate_limit_returns_429(
        self, key_client, admin_token, admin_user, stub_probe
    ):
        create_resp = key_client.post(
            "/v1/auth/api-keys",
            json={"name": "rate-limited", "api_user_id": admin_user.id, "rate_limit_per_minute": 3},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        raw_key = create_resp.json()["raw_key"]

        # Clear login cookie so requests must authenticate via X-API-Key only.
        key_client.cookies.clear()

        # 3 allowed requests must each succeed with 200.
        for _ in range(3):
            resp = key_client.get(
                API_KEY_PROBE,
                headers={"X-API-Key": raw_key},
            )
            assert resp.status_code == 200

        # 4th request must be rate-limited.
        resp = key_client.get(
            API_KEY_PROBE,
            headers={"X-API-Key": raw_key},
        )
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

    def test_unlimited_key_never_rate_limited(
        self, key_client, admin_token, admin_user, stub_probe
    ):
        create_resp = key_client.post(
            "/v1/auth/api-keys",
            json={"name": "unlimited", "api_user_id": admin_user.id, "rate_limit_per_minute": 0},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        raw_key = create_resp.json()["raw_key"]

        # Clear login cookie so requests must authenticate via X-API-Key only.
        key_client.cookies.clear()

        for _ in range(10):
            resp = key_client.get(
                API_KEY_PROBE,
                headers={"X-API-Key": raw_key},
            )
            assert resp.status_code == 200
