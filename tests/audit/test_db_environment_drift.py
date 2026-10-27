"""Unit tests for the multi-environment PostgreSQL drift assessment tool."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis.audit import db_environment_drift as drift  # noqa: E402


def test_no_synthetic_or_hardcoded_personal_paths_in_source() -> None:
    """Ensure db_environment_drift.py has zero synthetic multipliers or hardcoded personal paths."""
    src_path = Path(drift.__file__).resolve()
    content = src_path.read_text(encoding="utf-8")
    forbidden_tokens = [
        "simulated_staging_lag",
        "simulated_prod_release",
        "build_seeded_fingerprints",
        "_load_snapshot_bundle",
        "pjsmitty301",
        "antigravity",
        "0.865",
        "390 / 2777",
        "611 / 801",
        "baseline_records_snapshot",
    ]
    for token in forbidden_tokens:
        assert token not in content, f"Forbidden synthetic/personal token found in {src_path}: {token}"


def test_committed_fingerprints_are_live_measured() -> None:
    """Verify live environment fingerprints (when extracted on disk) or fixture fingerprints are valid."""
    fp_dir = drift.REPO_ROOT / "audit" / "output" / "env_fingerprints"
    fixture_fp = drift.REPO_ROOT / "tests" / "fixtures" / "minimal_env_fingerprint.json"
    checked = 0
    for env_key in ("local", "staging", "production"):
        fp_path = fp_dir / f"{env_key}_fingerprint.json"
        if not fp_path.exists():
            continue
        data = json.loads(fp_path.read_text(encoding="utf-8"))
        assert data["environment"] == env_key
        assert data["capture_mode"] == "live_db"
        assert data.get("is_measured") is True
        assert "layer1_schema" in data
        assert "layer2_row_counts" in data
        assert "layer3_coverage_and_lineage" in data
        assert "layer4_parameters_and_funnels" in data
        assert data["layer2_row_counts"]["core_tables"]["observation"] > 0
        assert len(data["layer3_coverage_and_lineage"]["resource_analysis_matrix"]) > 0
        assert len(data["layer4_parameters_and_funnels"]["parameter_stats"]) > 0
        checked += 1

    if checked == 0:
        if fixture_fp.exists():
            data = json.loads(fixture_fp.read_text(encoding="utf-8"))
            assert "layer1_schema" in data
            assert "layer2_row_counts" in data
            assert "layer3_coverage_and_lineage" in data
            assert "layer4_parameters_and_funnels" in data
        else:
            pytest.skip(
                "Live fingerprints are untracked; run --extract-all locally to test live output"
            )


def test_extract_live_fingerprint_handles_unreachable_db_gracefully(tmp_path: Path) -> None:
    """Unreachable database connection should return an honest unmeasured_offline fingerprint without crashing."""
    fp = drift.extract_live_fingerprint(
        env_key="production",
        base_dir=tmp_path,
        host="127.0.0.1",
        port=59999,
        dbname="nonexistent_db",
        user="nobody",
        password="p@ss:word/with?special#chars",
    )
    assert fp["environment"] == "production"
    assert fp["is_measured"] is False
    assert fp["capture_mode"] == "unmeasured_offline"
    assert (tmp_path / "audit" / "output" / "env_fingerprints" / "production_fingerprint.json").exists()


def test_load_db_reset_config_respects_staging_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit DB_*_STAGING env vars must take precedence over resources/config/db_reset.yaml."""
    monkeypatch.setattr(drift, "_parse_dotenv", lambda: {})
    monkeypatch.setenv("DB_HOST_STAGING", "10.0.0.42")
    monkeypatch.setenv("DB_PORT_STAGING", "15434")
    monkeypatch.setenv("DB_NAME_STAGING", "custom_staging_db")
    monkeypatch.setenv("DB_USER_STAGING", "readonly_user")
    monkeypatch.setenv("DB_PASSWORD_STAGING", "secret")

    configs = drift.load_db_reset_config()
    staging = configs["staging"]
    assert staging["host"] == "10.0.0.42"
    assert staging["port"] == 15434
    assert staging["database"] == "custom_staging_db"
    assert staging["user"] == "readonly_user"
    assert staging["password"] == "secret"


def test_load_db_reset_config_respects_prod_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit DB_*_PROD / BIOCIRV_PROD_USER_PW env vars must take precedence over db_reset.yaml."""
    monkeypatch.setattr(drift, "_parse_dotenv", lambda: {})
    monkeypatch.setenv("DB_HOST_PROD", "10.0.0.99")
    monkeypatch.setenv("DB_PORT_PROD", "15435")
    monkeypatch.setenv("DB_NAME_PROD", "custom_prod_db")
    monkeypatch.setenv("DB_USER_PROD", "readonly_prod_user")
    monkeypatch.setenv("DB_PASSWORD_PROD", "prod_secret")

    configs = drift.load_db_reset_config()
    prod = configs["production"]
    assert prod["host"] == "10.0.0.99"
    assert prod["port"] == 15435
    assert prod["database"] == "custom_prod_db"
    assert prod["user"] == "readonly_prod_user"
    assert prod["password"] == "prod_secret"

    # Also verify BIOCIRV_PROD_USER_PW fallback when DB_PASSWORD_PROD is not set
    monkeypatch.delenv("DB_PASSWORD_PROD", raising=False)
    monkeypatch.setenv("BIOCIRV_PROD_USER_PW", "biocirv_prod_secret")
    configs_fallback = drift.load_db_reset_config()
    assert configs_fallback["production"]["password"] == "biocirv_prod_secret"


def test_extract_live_fingerprint_records_query_errors_and_negative_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Permission / privilege SQL errors on tables or views must set cnt = -1 and append to query_errors."""

    class FakeResult:
        def __init__(self, rows: list | None = None, scalar_val: object = 0) -> None:
            self._rows = rows or []
            self._scalar = scalar_val

        def scalar(self) -> object:
            return self._scalar

        def all(self) -> list:
            return self._rows

    class FakeConnection:
        def __init__(self) -> None:
            self.rollbacks = 0

        def __enter__(self) -> FakeConnection:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

        def rollback(self) -> None:
            self.rollbacks += 1

        def execute(self, stmt: object, params: object = None) -> FakeResult:
            sql = str(stmt)
            if "FROM public.resource" in sql and "COUNT(*)" in sql:
                raise PermissionError("permission denied for table resource")
            if "FROM ca_biositing.analysis_data_view" in sql and "COUNT(*)" in sql:
                raise RuntimeError("insufficient privilege for view analysis_data_view")
            if "alembic_version" in sql:
                return FakeResult(scalar_val="abc123def456")
            if "COUNT(*)" in sql:
                return FakeResult(scalar_val=5)
            return FakeResult(rows=[])

    class FakeEngine:
        def connect(self) -> FakeConnection:
            return FakeConnection()

    monkeypatch.setattr("sqlalchemy.create_engine", lambda *args, **kwargs: FakeEngine())

    fp = drift.extract_live_fingerprint(env_key="staging", base_dir=tmp_path)
    assert fp["is_measured"] is True
    assert fp["layer2_row_counts"]["core_tables"]["resource"] == -1
    assert fp["layer2_row_counts"]["views"]["ca_biositing.analysis_data_view"] == -1
    assert any("table:resource:" in err and "permission denied" in err for err in fp["query_errors"])
    assert any(
        "view:ca_biositing.analysis_data_view:" in err and "insufficient privilege" in err
        for err in fp["query_errors"]
    )


def test_fail_on_unmeasured_exits_2_when_query_errors_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--fail-on-unmeasured must exit with code 2 when is_measured is True but query_errors is non-empty."""
    fake_fp = {
        "environment": "staging",
        "is_measured": True,
        "capture_mode": "live_db",
        "query_errors": ["table:resource: permission denied for table resource"],
    }
    monkeypatch.setattr(drift, "extract_live_fingerprint", lambda **kwargs: fake_fp)

    with pytest.raises(SystemExit) as exc_info:
        drift.main(["--extract-env", "staging", "--fail-on-unmeasured", "--base-dir", str(tmp_path)])

    assert exc_info.value.code == 2
    err_out = capsys.readouterr().err
    assert "table:resource: permission denied" in err_out


def test_verify_readonly_grants_exits_2_on_missing_select_privilege(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--verify-readonly-grants must exit with code 2 if any expected table or view has cnt < 0."""
    core_tables = {t_name: 10 for t_name, _, _, _ in drift.CORE_TABLE_METADATA}
    core_tables["observation"] = -1
    views = {v_name: 5 for v_name, _, _ in drift.ALL_19_VIEWS}
    fake_fp = {
        "environment": "staging",
        "is_measured": True,
        "capture_mode": "live_db",
        "query_errors": [],
        "layer2_row_counts": {
            "core_tables": core_tables,
            "views": views,
        },
    }
    monkeypatch.setattr(drift, "extract_live_fingerprint", lambda **kwargs: fake_fp)

    with pytest.raises(SystemExit) as exc_info:
        drift.main(["--extract-envs", "staging", "--verify-readonly-grants", "--base-dir", str(tmp_path)])

    assert exc_info.value.code == 2
    err_out = capsys.readouterr().err
    assert "public.observation" in err_out
    assert "view (" not in err_out


def test_verify_readonly_grants_passes_healthy_string_keyed_views_and_catches_view_failure() -> None:
    """_check_readonly_grant_failures must pass on string-keyed views and flag view cnt < 0."""
    core_tables = {t_name: 10 for t_name, _, _, _ in drift.CORE_TABLE_METADATA}
    views = {v_name: 5 for v_name, _, _ in drift.ALL_19_VIEWS}
    healthy_fp = {
        "environment": "staging",
        "is_measured": True,
        "capture_mode": "live_db",
        "query_errors": [],
        "layer2_row_counts": {
            "core_tables": core_tables,
            "views": dict(views),
        },
    }
    assert drift._check_readonly_grant_failures({"staging": healthy_fp}) == []

    broken_views = dict(views)
    broken_views["ca_biositing.analysis_data_view"] = -1
    broken_fp = {
        **healthy_fp,
        "layer2_row_counts": {
            "core_tables": core_tables,
            "views": broken_views,
        },
    }
    failures = drift._check_readonly_grant_failures({"staging": broken_fp})
    assert len(failures) == 1
    assert "ca_biositing.analysis_data_view" in failures[0]


def test_compute_pair_comparison_marks_negative_count_as_query_error() -> None:
    """Tables or views with cnt = -1 must be marked QUERY ERROR, not SYNCED or bogus drift."""
    import copy

    fixture_path = REPO_ROOT / "tests" / "fixtures" / "minimal_env_fingerprint.json"
    base_fp = json.loads(fixture_path.read_text(encoding="utf-8"))

    fp_a = copy.deepcopy(base_fp)
    fp_a["environment"] = "staging"
    fp_a["is_measured"] = True
    fp_a["layer2_row_counts"]["core_tables"]["resource"] = -1
    fp_a["layer2_row_counts"]["views"]["ca_biositing.analysis_data_view"] = -1

    fp_b = copy.deepcopy(base_fp)
    fp_b["environment"] = "production"
    fp_b["is_measured"] = True
    fp_b["layer2_row_counts"]["core_tables"]["resource"] = -1
    fp_b["layer2_row_counts"]["views"]["ca_biositing.analysis_data_view"] = 100

    comp = drift.compute_pair_comparison(fp_a, fp_b)
    res_diff = next(t for t in comp["table_diffs"] if t["name"] == "resource")
    assert res_diff["status"] == "QUERY ERROR"
    assert res_diff["delta"] == 0

    adv_diff = next(
        v for v in comp["view_diffs"] if v["name"] == "ca_biositing.analysis_data_view"
    )
    assert adv_diff["status"] == "QUERY ERROR"
    assert adv_diff["delta"] == 0
