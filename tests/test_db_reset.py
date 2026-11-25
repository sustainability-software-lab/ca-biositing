"""db_reset keeps private schemas (auth) away from the read-only role (#580)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from db_reset import DatabaseResetOrchestrator  # noqa: E402


@pytest.fixture
def orchestrator(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return DatabaseResetOrchestrator(
        env="local",
        config_path=str(REPO_ROOT / "resources" / "config" / "db_reset.yaml"),
        dry_run=True,
    )


def test_private_schemas_are_wiped_and_recreated(orchestrator):
    sql = orchestrator.render_phase_sql("db_reset_wipe.sql")
    assert "DROP SCHEMA IF EXISTS auth CASCADE;" in sql
    assert "CREATE SCHEMA auth;" in sql


def test_private_schemas_are_owned_by_app_user(orchestrator):
    sql = orchestrator.render_phase_sql("db_reset_ownership.sql")
    assert "'auth'" in sql


def test_private_schemas_are_not_granted_to_readonly(orchestrator):
    sql = orchestrator.render_phase_sql("db_reset_readonly.sql")
    grant_array = next(line for line in sql.splitlines() if "schemas TEXT[]" in line)
    assert "'auth'" not in grant_array
    assert "REVOKE ALL ON SCHEMA %I FROM %I" in sql
    assert "private_schemas TEXT[] := ARRAY['auth']" in sql
