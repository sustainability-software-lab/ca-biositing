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
