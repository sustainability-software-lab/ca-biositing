"""Tests for Product 4 (Resource QC & Data Audit Workbench) and 5-Product Gallery / Login Portal."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis.metadata.resource_audit_workbench import (  # noqa: E402
    ANALYSIS_TABLE_MAP,
    build_resource_audit_workbench,
    build_workbench_payload,
    load_snapshot,
    unpack_snapshot_records,
)
from scripts.generate_dashboard_gallery import generate_gallery  # noqa: E402

MINIMAL_SNAPSHOT = REPO_ROOT / "tests" / "fixtures" / "minimal_dashboard_snapshot.json"
WORKBENCH_SOURCE = REPO_ROOT / "analysis" / "metadata" / "resource_audit_workbench.py"


def _validate_inline_js_blocks(html_path: Path) -> int:
    """Validate all inline JavaScript <script> blocks in an HTML file with `node --check`."""
    html_text = html_path.read_text(encoding="utf-8")
    blocks = [
        block
        for block in re.findall(
            r"<script(?![^>]*\bsrc=)(?![^>]*application/json)[^>]*>(.*?)</script>",
            html_text,
            flags=re.S | re.I,
        )
        if block.strip()
    ]
    assert blocks, f"Expected at least one inline <script> block in {html_path}"

    node_bin = shutil.which("node")
    if node_bin is None:
        pytest.skip("node binary not available in PATH")

    for idx, js_code in enumerate(blocks):
        js_file = html_path.parent / f"{html_path.stem}_inline_{idx}.js"
        js_file.write_text(js_code, encoding="utf-8")
        proc = subprocess.run(
            [node_bin, "--check", str(js_file)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, (
            f"node --check failed for {html_path.name} script #{idx}: {proc.stderr}"
        )
    return len(blocks)


def test_analysis_table_map_and_db_id_contract() -> None:
    """Verify ANALYSIS_TABLE_MAP uses PostgreSQL *_record table names and candidate rows include db_id: None."""
    assert len(ANALYSIS_TABLE_MAP) == 10
    valid_tables = set(ANALYSIS_TABLE_MAP.values())
    for table_name in valid_tables:
        assert table_name.endswith("_record"), f"Expected *_record table, got {table_name}"

    source_text = WORKBENCH_SOURCE.read_text(encoding="utf-8")
    assert "observation_record" not in source_text

    snapshot = load_snapshot(MINIMAL_SNAPSHOT)
    payload = build_workbench_payload(snapshot)
    assert "records" not in payload
    assert payload["total_records"] == 37
    assert payload["decisions"], "Expected candidate decisions from minimal snapshot"
    for decision in payload["decisions"]:
        assert "db_id" in decision
        assert decision["db_id"] is None
        assert decision["record_table"] in valid_tables

    # Verify unpack_snapshot_records supports both len(str_cols)+3 (no exp_date) and len(str_cols)+4
    num_str_cols = len(snapshot["str_cols"])
    trimmed_snapshot = {
        **snapshot,
        "rows": [row[: num_str_cols + 3] for row in snapshot["rows"]],
    }
    trimmed_records = unpack_snapshot_records(trimmed_snapshot)
    assert len(trimmed_records) == len(snapshot["rows"]) == 37
    assert all(rec["exp_date"] == "" for rec in trimmed_records)


def test_build_workbench_payload_detects_all_four_qc_flag_types() -> None:
    """Verify snapshot unpacking and automatic QC screening on minimal_dashboard_snapshot.json."""
    snapshot = load_snapshot(MINIMAL_SNAPSHOT)
    records = unpack_snapshot_records(snapshot)
    assert len(records) == len(snapshot["rows"]) == 37

    payload = build_workbench_payload(snapshot)
    assert payload["total_records"] == 37
    assert payload["total_replicate_groups"] >= 8
    assert payload["total_flagged_groups"] >= 4

    all_flags: set[str] = set()
    for decision in payload["decisions"]:
        all_flags.update(decision.get("flag_types", []))

    assert "rsd_gt_10" in all_flags
    assert "iqr_outlier" in all_flags
    assert "proximate_sum" in all_flags
    assert "analyst_flagged" in all_flags

    # Verify AH-PREP-02 proximate closure violation (>105%) is captured
    closure_map = payload["proximate_closure_by_sample"]
    assert "Almond Hulls::AH-PREP-02" in closure_map
    ah_prep_02 = closure_map["Almond Hulls::AH-PREP-02"]
    assert ah_prep_02["out_of_bounds"] is True
    assert ah_prep_02["closure_sum_pct"] == pytest.approx(112.4, abs=0.2)

    # Verify co-measured parameters on Almond Hulls::AH-PREP-01 include multiple parameters
    co_measured = payload["co_measured_by_sample"].get("Almond Hulls::AH-PREP-01", [])
    param_names = {item["parameter_name"] for item in co_measured}
    assert {"Ash", "Volatile Matter", "Fixed Carbon", "Moisture"}.issubset(param_names)


def test_resource_audit_workbench_cli_and_dom_contract(tmp_path: Path) -> None:
    """Build resource_audit_workbench.html into tmp_path and verify UI/JS contract & syntax."""
    output_html = tmp_path / "resource_audit_workbench.html"
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "analysis" / "metadata" / "resource_audit_workbench.py"),
            "--from-snapshot",
            str(MINIMAL_SNAPSHOT),
            "--output",
            str(output_html),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"CLI failed: {proc.stderr}\n{proc.stdout}"
    assert output_html.exists()
    assert output_html.stat().st_size > 20_000

    html = output_html.read_text(encoding="utf-8")

    # 1. Queue & Task Assignment Bar tabs & batch GSheet sync button
    for expected_tab in (
        "Assigned to Me",
        "Unassigned",
        "All Open",
        "In Review / Retest",
        "Resolved (Pending GSheet Sync)",
        "Synced to GSheet",
        "Sync All Pending to Google Sheets",
    ):
        assert expected_tab in html

    # 2. Facet filters
    for filter_id in (
        "filter-resource",
        "filter-analysis-type",
        "filter-parameter",
        "filter-flag-type",
        "filter-assigned-analyst",
    ):
        assert f'id="{filter_id}"' in html

    # 3. Left pane multi-view diagnostic plot controls
    assert 'id="select-plot-style"' in html
    assert "Sample Forest / Caterpillar + IQR Band" in html
    assert "Run-Order / Batch Control Chart" in html
    assert "Proximate / Compositional Closure Bar" in html
    assert "Cross-Resource Box + Strip Plot" in html

    assert 'id="select-group-by"' in html
    assert 'id="select-co-measured-param"' in html
    assert "Inspect Co-Measured Parameter on Same Sample" in html

    # 4. Right pane replicate scope toggle, rationale chips, review note, API calls & BroadcastChannel
    assert "Entire Replicate Group" in html
    assert "Specific Single Replicate(s)" in html
    assert "rationale-chip" in html
    assert 'id="input-review-note"' in html
    assert 'BroadcastChannel("biocirv_qc_decisions")' in html
    assert 'id="btn-refresh-qc-state"' in html
    assert "Refresh QC State" in html
    assert "/v1/qc/decisions" in html
    assert "/v1/qc/decisions/sync-gsheet-batch" in html
    assert "/sync-gsheet" in html
    assert "/assign" in html

    # 5. Complete 4-step Audit Provenance & Timestamp Timeline + role-aware Stage 2 controls
    assert 'id="audit-provenance-timeline"' in html
    assert "Created / Flagged" in html
    assert "Assigned Reviewer" in html
    assert "Decision Recorded" in html
    assert "Google Sheets Sync Status" in html
    assert "Sync This Decision to Google Sheets" in html
    assert 'id="badge-analyst-gsheet-readonly"' in html

    # 6. Validate inline JS syntax via node --check
    script_count = _validate_inline_js_blocks(output_html)
    assert script_count >= 1


def test_generate_dashboard_gallery_and_login_portal(tmp_path: Path) -> None:
    """Verify generate_dashboard_gallery.py writes index.html and login.html into tmp_path."""
    # Also place a generated Product 4 workbench in tmp_path/metadata to exercise directory scanning
    meta_dir = tmp_path / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)
    build_resource_audit_workbench(
        snapshot_path=MINIMAL_SNAPSHOT,
        output_path=meta_dir / "resource_audit_workbench.html",
    )

    index_path_str, login_path_str = generate_gallery(output_dir=str(tmp_path))
    index_path = Path(index_path_str)
    login_path = Path(login_path_str)

    assert index_path.exists()
    assert login_path.exists()

    index_html = index_path.read_text(encoding="utf-8")
    login_html = login_path.read_text(encoding="utf-8")

    # Verify 5-product gallery links, live My Assigned Reviews badge, and Admin-only Product 5 gating
    assert "metadata/resource_analysis_dashboard.html" in index_html
    assert "metadata/resource_qc_outlier_dashboard.html" in index_html
    assert "metadata/resource_explorer_dashboard.html" in index_html
    assert "metadata/resource_audit_workbench.html" in index_html
    assert "audit/db_environment_drift_dashboard.html" in index_html
    assert 'id="badge-my-assigned-reviews"' in index_html
    assert "My Assigned Reviews" in index_html
    assert 'id="product-card-5-drift"' in index_html
    assert 'data-admin-only="true"' in index_html
    assert "/v1/qc/auth/me" in index_html

    # Verify login.html Google Sign-In, allowlisted domains, and localhost dev login
    assert "/v1/qc/auth/google" in login_html
    assert "/v1/qc/auth/dev-login" in login_html
    assert "@lbl.gov" in login_html
    assert "@ucdavis.edu" in login_html
    assert "@beamcircular.org" in login_html

    _validate_inline_js_blocks(index_path)
    _validate_inline_js_blocks(login_path)
