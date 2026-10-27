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
    canonical_domain_slug,
    group_context_label,
    load_snapshot,
    matches_replicate_group_key,
    normalize_replicate_group_key,
    resolve_record_table,
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

    # Verify AH-PREP-02 proximate closure violation (outside 95-105% via Data Portal formula:
    # COALESCE(avg_moisture, 0) + COALESCE(avg_ash, 0) + COALESCE(avg_vs, 100 - COALESCE(avg_fc, 0))
    # = 0.0 + 5.9 + 82.0 = 87.9%) is captured at both sample and stratum levels
    closure_map = payload["proximate_closure_by_sample"]
    assert "Almond Hulls::AH-PREP-02" in closure_map
    ah_prep_02 = closure_map["Almond Hulls::AH-PREP-02"]
    assert ah_prep_02["out_of_bounds"] is True
    assert ah_prep_02["closure_sum_pct"] == pytest.approx(87.9, abs=0.2)
    assert ah_prep_02["proximate_sum_pct"] == pytest.approx(87.9, abs=0.2)

    stratum_map = payload["proximate_closure_by_stratum"]
    assert "Almond Hulls::EXP-PROX-02::Milled 2mm" in stratum_map
    assert stratum_map["Almond Hulls::EXP-PROX-02::Milled 2mm"]["proximate_sum_pct"] == pytest.approx(
        87.9, abs=0.2
    )
    assert stratum_map["Almond Hulls::EXP-PROX-02::Milled 2mm"]["out_of_bounds"] is True

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
    assert "/v1/qc/decisions/assign-batch" in html
    assert "/sync-gsheet" in html
    assert "/assign" in html
    assert 'id="qc-bulk-assign-bar"' in html
    assert 'id="chk-select-all-filtered"' in html
    assert 'id="chk-select-all-header"' in html
    assert 'id="bulk-selected-count"' in html
    assert 'id="btn-select-all-filtered"' in html
    assert 'id="btn-clear-selection"' in html
    assert 'id="bulk-assign-email"' in html
    assert 'id="AnalystDirectoryList"' in html
    assert 'id="btn-bulk-assign-apply"' in html
    assert "qc-row-select-chk" in html
    assert "bulkAssignSelected" in html
    assert "getDefaultAssigneeEmail" in html

    # 5. Complete 4-step Audit Provenance & Timestamp Timeline + role-aware Stage 2 controls
    assert 'id="audit-provenance-timeline"' in html
    assert "Created / Flagged" in html
    assert "Assigned Reviewer" in html
    assert "Decision Recorded" in html
    assert "Google Sheets Sync Status" in html
    assert "Sync This Decision to Google Sheets" in html
    assert 'id="badge-analyst-gsheet-readonly"' in html
    assert "3. Data Visualizer" in html

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
    assert "Interactive Data Visualizer" in index_html
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


def test_load_snapshot_fallbacks_and_custom_path_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify load_snapshot() 3-tier fallback for DEFAULT_SNAPSHOT_PATH and FileNotFoundError for custom paths."""
    import analysis.metadata.resource_audit_workbench as wb_mod

    fake_default_snap = tmp_path / "exports" / "plots" / "metadata" / "dashboard_data_snapshot.json"
    monkeypatch.setattr(wb_mod, "DEFAULT_SNAPSHOT_PATH", fake_default_snap)

    # 1. Custom missing path must still raise FileNotFoundError without querying live DB
    custom_missing = tmp_path / "does_not_exist.json"
    with pytest.raises(FileNotFoundError, match="Dashboard snapshot not found"):
        load_snapshot(custom_missing)

    # 2. Missing default snapshot falls back to minimal_dashboard_snapshot.json when live DB raises
    def _raise_db_err() -> dict[str, object]:
        raise RuntimeError("Simulated PostgreSQL connection refused")

    monkeypatch.setattr(wb_mod, "_fetch_live_resource_data", _raise_db_err)
    fallback_data = load_snapshot(fake_default_snap)
    captured = capsys.readouterr().out
    assert "Warning: could not fetch live data (Simulated PostgreSQL connection refused)" in captured
    assert len(fallback_data["rows"]) == 37
    assert not fake_default_snap.exists()

    # 3. Missing default snapshot caches and returns live DB payload when PostgreSQL succeeds
    synthetic_live = load_snapshot(MINIMAL_SNAPSHOT)
    monkeypatch.setattr(wb_mod, "_fetch_live_resource_data", lambda: synthetic_live)
    cached_data = load_snapshot(fake_default_snap)
    assert cached_data["rows"] == synthetic_live["rows"]
    assert fake_default_snap.exists()


def test_dashboard_artifacts_workflow_never_publishes_minimal_fixture_to_gcs() -> None:
    """Ensure dashboard-artifacts.yml tracks USED_MINIMAL_FIXTURE and blocks overwriting GCS latest/ with seed data."""
    workflow_path = REPO_ROOT / ".github" / "workflows" / "dashboard-artifacts.yml"
    content = workflow_path.read_text(encoding="utf-8")
    assert 'USED_MINIMAL_FIXTURE="true"' in content
    assert 'echo "USED_MINIMAL_FIXTURE=${USED_MINIMAL_FIXTURE}"' in content
    assert '[ "${USED_MINIMAL_FIXTURE:-false}" = "true" ]' in content
    assert "metadata/dashboard_data_snapshot.json" in content


def test_canonical_6_part_replicate_group_key_and_4_part_fallback() -> None:
    """Verify 6-part replicate_group_key normalization, Pretreatment/Fermentation context slots, and domain slug mapping."""
    assert len(ANALYSIS_TABLE_MAP) == 10
    for display_name, expected_table in ANALYSIS_TABLE_MAP.items():
        slug = canonical_domain_slug(display_name)
        assert resolve_record_table(display_name) == expected_table
        assert resolve_record_table(slug) == expected_table

    # Verify edge cases on canonical_domain_slug
    assert canonical_domain_slug(None) == "unknown"
    assert canonical_domain_slug("") == "unknown"
    assert canonical_domain_slug("   ") == "unknown"
    assert canonical_domain_slug("Ash") == "xrf"
    assert canonical_domain_slug("ash_record") == "xrf"
    assert canonical_domain_slug("calorimetry_xrd") == "calorimetry"
    assert canonical_domain_slug("Pretreatment & Hydrolysis") == "pretreatment"
    assert canonical_domain_slug("Fermentation (Bioconversion)") == "fermentation"
    assert canonical_domain_slug("ICP-OES / ICP-MS") == "icp"

    # Verify group_context_label and dict-based normalize_replicate_group_key for Pretreatment & Fermentation
    # Including real data shape where both prep_method (e.g. "Wiley Milled") and pt_method (e.g. "Dilute Acid") exist
    from analysis.metadata.resource_insights_engine import (
        _group_context_label as engine_group_context_label,
    )
    from ca_biositing.webservice.v1.endpoints.qc_review import (
        group_context_label as qc_review_group_context_label,
        normalize_replicate_group_key as qc_review_normalize_replicate_group_key,
    )

    pt_row = {
        "resource_name": "Corn Stover",
        "prepared_sample": "CS-PREP-01",
        "analysis_type": "Pretreatment & Hydrolysis",
        "parameter": "Glucose Yield",
        "prep_method": "Wiley Milled",
        "pt_method": "Dilute Acid",
        "eh_method": "Cellic CTec2",
        "experiment": "EXP-PT-01",
    }
    assert group_context_label(pt_row) == "Dilute Acid · Cellic CTec2"
    assert group_context_label(pt_row) == engine_group_context_label(pt_row)
    assert (
        normalize_replicate_group_key(pt_row)
        == "corn stover::cs-prep-01::pretreatment::glucose yield::dilute acid · cellic ctec2::exp-pt-01"
    )

    # Fallback when pt_method key is absent from synthetic row
    pt_fallback_row = {
        "resource_name": "Corn Stover",
        "prepared_sample": "CS-PREP-01",
        "analysis_type": "Pretreatment & Hydrolysis",
        "parameter": "Glucose Yield",
        "prep_method": "Dilute Acid",
        "eh_method": "Cellic CTec2",
        "experiment": "EXP-PT-01",
    }
    assert group_context_label(pt_fallback_row) == "Dilute Acid · Cellic CTec2"

    ferm_row_a = {
        "resource_name": "Corn Stover",
        "prepared_sample": "CS-PREP-01",
        "analysis_type": "Fermentation (Bioconversion)",
        "parameter": "Ethanol",
        "prep_method": "Wiley Milled",
        "pt_method": "SHF",
        "strain": "S. cerevisiae",
        "time_h": 48,
        "experiment": "EXP-FERM-01",
    }
    ferm_row_b = {
        **ferm_row_a,
        "strain": "Z. mobilis",
        "time_h": 72,
    }
    assert group_context_label(ferm_row_a) == "SHF · S. cerevisiae @ 48h"
    assert group_context_label(ferm_row_a) == engine_group_context_label(ferm_row_a)
    assert qc_review_group_context_label(ferm_row_a) == engine_group_context_label(
        ferm_row_a
    )
    assert group_context_label(ferm_row_b) == "SHF · Z. mobilis @ 72h"
    assert group_context_label(ferm_row_b) == engine_group_context_label(ferm_row_b)
    assert qc_review_group_context_label(ferm_row_b) == engine_group_context_label(
        ferm_row_b
    )
    assert normalize_replicate_group_key(ferm_row_a) != normalize_replicate_group_key(
        ferm_row_b
    )
    assert (
        normalize_replicate_group_key(ferm_row_a)
        == "corn stover::cs-prep-01::fermentation::ethanol::shf · s. cerevisiae @ 48h::exp-ferm-01"
    )
    assert qc_review_normalize_replicate_group_key(
        ferm_row_a
    ) == normalize_replicate_group_key(ferm_row_a)

    # Fermentation row without pt_method must NEVER fall back to prep_method for pt
    ferm_no_pt_row = {
        "resource_name": "Corn Stover",
        "prepared_sample": "CS-PREP-01",
        "analysis_type": "Fermentation (Bioconversion)",
        "parameter": "Ethanol",
        "prep_method": "Wiley Milled",
        "strain": "S. cerevisiae",
        "time_h": 48,
        "experiment": "EXP-FERM-01",
    }
    assert engine_group_context_label(ferm_no_pt_row) == "S. cerevisiae @ 48h"
    assert group_context_label(ferm_no_pt_row) == "S. cerevisiae @ 48h"
    assert qc_review_group_context_label(ferm_no_pt_row) == "S. cerevisiae @ 48h"
    assert (
        normalize_replicate_group_key(ferm_no_pt_row)
        == "corn stover::cs-prep-01::fermentation::ethanol::s. cerevisiae @ 48h::exp-ferm-01"
    )
    assert qc_review_normalize_replicate_group_key(
        ferm_no_pt_row
    ) == normalize_replicate_group_key(ferm_no_pt_row)

    # Verify unpack_snapshot_records unpacks pt_method + time_h and constructs Pretreatment/Fermentation 6-part keys
    synth_snapshot = {
        "generated_utc": "2026-01-01T00:00:00Z",
        "str_cols": [
            "resource_name",
            "field_sample",
            "prepared_sample",
            "analysis_type",
            "parameter",
            "unit",
            "qc_status",
            "analyst",
            "provider",
            "experiment",
            "prep_method",
            "pt_method",
            "eh_method",
            "strain",
            "note",
        ],
        "dicts": {
            "resource_name": ["Corn Stover"],
            "field_sample": ["CS-F1"],
            "prepared_sample": ["CS-PREP-01"],
            "analysis_type": [
                "Pretreatment & Hydrolysis",
                "Fermentation (Bioconversion)",
                "Ash",
            ],
            "parameter": ["Glucose Yield", "Ethanol", "SiO2"],
            "unit": ["g/L", "%"],
            "qc_status": ["pass"],
            "analyst": ["a@lbl.gov"],
            "provider": ["LBL"],
            "experiment": ["EXP-1"],
            "prep_method": ["Wiley Milled", "Muffle 575C"],
            "pt_method": ["Dilute Acid", "SHF", "none"],
            "eh_method": ["none", "Cellic CTec2"],
            "strain": ["none", "S. cerevisiae", "Z. mobilis"],
            "note": [""],
        },
        "rows": [
            ["PT-1", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 42.0, "2026-01-01", None],
            ["FM-1", 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 18.5, "2026-01-01", 48],
            ["FM-2", 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 2, 0, 1, 22.1, "2026-01-01", 72],
            ["ASH-1", 0, 0, 0, 2, 2, 1, 0, 0, 0, 0, 1, 2, 0, 0, 0, 1, 51.0, "2026-01-01", None],
        ],
    }
    unpacked = unpack_snapshot_records(synth_snapshot)
    assert len(unpacked) == 4
    assert (
        unpacked[0]["replicate_group_key"]
        == "corn stover::cs-prep-01::pretreatment::glucose yield::dilute acid · cellic ctec2::exp-1"
    )
    assert (
        unpacked[1]["replicate_group_key"]
        == "corn stover::cs-prep-01::fermentation::ethanol::shf · s. cerevisiae @ 48h::exp-1"
    )
    assert (
        unpacked[2]["replicate_group_key"]
        == "corn stover::cs-prep-01::fermentation::ethanol::shf · z. mobilis @ 72h::exp-1"
    )
    assert (
        unpacked[3]["replicate_group_key"]
        == "corn stover::cs-prep-01::xrf::sio2::muffle 575c::exp-1"
    )

    key_6 = normalize_replicate_group_key(
        "Almond Hulls",
        "AH-PREP-01",
        "Proximate Analysis",
        "Ash",
        "Mill-1mm",
        "EXP-2025-A",
    )
    assert key_6 == "almond hulls::ah-prep-01::proximate::ash::mill-1mm::exp-2025-a"

    key_4 = normalize_replicate_group_key(
        "grp::Almond Hulls::AH-PREP-01::Proximate Analysis::Ash"
    )
    assert key_4 == "almond hulls::ah-prep-01::proximate::ash"

    assert matches_replicate_group_key(key_6, key_6) is True
    assert (
        matches_replicate_group_key(
            key_6, "Almond Hulls::AH-PREP-01::Proximate Analysis::Ash"
        )
        is True
    )
    assert (
        matches_replicate_group_key(
            key_6,
            "almond hulls::ah-prep-01::proximate::ash::mill-2mm::exp-2025-a",
        )
        is False
    )

    records = unpack_snapshot_records(load_snapshot(MINIMAL_SNAPSHOT))
    assert records
    for rec in records:
        parts = rec["replicate_group_key"].split("::")
        assert len(parts) == 6
        assert parts[2] in {
            "proximate",
            "ultimate",
            "compositional",
            "calorimetry",
            "xrd",
            "icp",
            "xrf",
            "pretreatment",
            "fermentation",
            "gasification",
        }


def test_method_stratified_between_sd_and_between_rsd_pct_on_replicate_groups() -> None:
    """Verify within_sd and method-stratified between_sd / between_rsd_pct on replicate groups and decisions."""
    payload = build_workbench_payload(load_snapshot(MINIMAL_SNAPSHOT))
    groups = payload["replicate_groups"]
    assert groups

    # Almond Hulls Proximate Ash has two prepared samples (AH-PREP-01 and AH-PREP-02) with Milled 2mm & % (wt/wt db)
    ah_ash_key = "almond hulls::ah-prep-01::proximate::ash::milled 2mm::exp-prox-01"
    assert ah_ash_key in groups
    ah_ash_group = groups[ah_ash_key]
    assert ah_ash_group["within_sd"] is not None
    assert ah_ash_group["within_sd"] > 0
    assert ah_ash_group["between_k_groups"] == 2
    assert ah_ash_group["between_sd"] is not None and ah_ash_group["between_sd"] > 0
    assert (
        ah_ash_group["between_rsd_pct"] is not None
        and ah_ash_group["between_rsd_pct"] > 0
    )
    assert len(ah_ash_group["records"]) == ah_ash_group["replicate_count"] == 4

    # Single-sample stratum (k_groups < 2) must have between_sd=None and between_rsd_pct=None
    cs_ash_key = (
        "corn stover::cs-prep-01::proximate::ash::knife milled::exp-prox-01"
    )
    assert cs_ash_key in groups
    cs_ash_group = groups[cs_ash_key]
    assert cs_ash_group["between_k_groups"] == 1
    assert cs_ash_group["between_sd"] is None
    assert cs_ash_group["between_rsd_pct"] is None

    # Decisions also carry within_sd, between_sd, between_rsd_pct, and between_k_groups
    ah_decisions = [
        d for d in payload["decisions"] if d["replicate_group_key"] == ah_ash_key
    ]
    assert len(ah_decisions) == 1
    assert ah_decisions[0]["within_sd"] == ah_ash_group["within_sd"]
    assert ah_decisions[0]["between_sd"] == ah_ash_group["between_sd"]
    assert ah_decisions[0]["between_rsd_pct"] == ah_ash_group["between_rsd_pct"]


def test_js_refresh_qc_state_non_colliding_ids_and_drawer_fallback(
    tmp_path: Path,
) -> None:
    """Verify JS matchesReplicateGroupKey, non-colliding QC-DB- IDs, metadata preservation, and drawer fallback."""
    node_bin = shutil.which("node")
    if node_bin is None:
        pytest.skip("node binary not available in PATH")

    output_html = tmp_path / "resource_audit_workbench.html"
    build_resource_audit_workbench(
        snapshot_path=MINIMAL_SNAPSHOT,
        output_path=output_html,
    )
    html_text = output_html.read_text(encoding="utf-8")
    assert 'id="btn-bulk-assign-my-email"' in html_text
    assert 'id="btn-clear-selection"' in html_text
    blocks = [
        block
        for block in re.findall(
            r"<script(?![^>]*\bsrc=)(?![^>]*application/json)[^>]*>(.*?)</script>",
            html_text,
            flags=re.S | re.I,
        )
        if block.strip()
    ]
    assert blocks

    harness_js = tmp_path / "run_workbench_unit_checks.js"
    harness_code = (
        """
const assert = require("assert");
const elements = {};
function makeEl(id) {
  return {
    id: id,
    value: "",
    textContent: "",
    innerHTML: "",
    style: {},
    className: "",
    checked: false,
    disabled: false,
    classList: {
      add: function () {},
      remove: function () {},
      toggle: function () {}
    },
    appendChild: function () {},
    addEventListener: function () {},
    getAttribute: function () { return ""; },
    setAttribute: function () {},
    querySelectorAll: function () { return []; }
  };
}
global.document = {
  getElementById: function (id) {
    if (!elements[id]) elements[id] = makeEl(id);
    return elements[id];
  },
  querySelectorAll: function () { return []; },
  createElement: function (tag) { return makeEl(tag); }
};
global.window = {
  location: { pathname: "/v1/dashboards/metadata/resource_audit_workbench.html", search: "" },
  history: { replaceState: function () {} },
  open: function () {}
};
let mockServerDecisions = [];
global.fetch = function (url) {
  if (String(url).indexOf("/v1/qc/auth/me") !== -1) {
    return Promise.resolve({
      ok: true,
      json: function () {
        return Promise.resolve({
          email: "qa.analyst@lbl.gov",
          name: "QA Analyst",
          role: "analyst",
          authenticated: true
        });
      }
    });
  }
  if (String(url).indexOf("/v1/qc/decisions") !== -1) {
    return Promise.resolve({
      ok: true,
      json: function () {
        return Promise.resolve({
          decisions: mockServerDecisions
        });
      }
    });
  }
  return Promise.resolve({ ok: false, json: function () { return Promise.resolve(null); } });
};
"""
        + blocks[0]
        + """
(async function () {
  await new Promise((r) => setTimeout(r, 20));
  const hooks = global.window.__WORKBENCH_TEST_HOOKS__;
  assert.ok(hooks, "Expected __WORKBENCH_TEST_HOOKS__ on window");

  // 1. Verify JS canonicalDomainSlug, groupContextLabel, normalizeReplicateGroupKey, and matchesReplicateGroupKey
  assert.strictEqual(hooks.canonicalDomainSlug(""), "unknown");
  assert.strictEqual(hooks.canonicalDomainSlug(null), "unknown");
  assert.strictEqual(hooks.canonicalDomainSlug("Ash"), "xrf");
  assert.strictEqual(hooks.canonicalDomainSlug("calorimetry_xrd"), "calorimetry");
  assert.strictEqual(hooks.canonicalDomainSlug("Pretreatment & Hydrolysis"), "pretreatment");
  assert.strictEqual(hooks.canonicalDomainSlug("Fermentation (Bioconversion)"), "fermentation");

  const ptObj = {
    resource_name: "Corn Stover",
    prepared_sample: "CS-PREP-01",
    analysis_type: "Pretreatment & Hydrolysis",
    parameter: "Glucose Yield",
    prep_method: "Wiley Milled",
    pt_method: "Dilute Acid",
    eh_method: "Cellic CTec2",
    experiment: "EXP-PT-01"
  };
  assert.strictEqual(hooks.groupContextLabel(ptObj), "Dilute Acid \u00b7 Cellic CTec2");
  assert.strictEqual(
    hooks.normalizeReplicateGroupKey(ptObj),
    "corn stover::cs-prep-01::pretreatment::glucose yield::dilute acid \u00b7 cellic ctec2::exp-pt-01"
  );

  const fermObj = {
    resource_name: "Corn Stover",
    prepared_sample: "CS-PREP-01",
    analysis_type: "Fermentation (Bioconversion)",
    parameter: "Ethanol",
    prep_method: "Wiley Milled",
    pt_method: "SHF",
    strain: "S. cerevisiae",
    time_h: 48,
    experiment: "EXP-FERM-01"
  };
  assert.strictEqual(hooks.groupContextLabel(fermObj), "SHF \u00b7 S. cerevisiae @ 48h");
  assert.strictEqual(
    hooks.normalizeReplicateGroupKey(fermObj),
    "corn stover::cs-prep-01::fermentation::ethanol::shf \u00b7 s. cerevisiae @ 48h::exp-ferm-01"
  );

  // Fermentation row lacking pt_method key must NEVER fall back to prep_method for pt
  const fermNoPtObj = {
    resource_name: "Corn Stover",
    prepared_sample: "CS-PREP-01",
    analysis_type: "Fermentation (Bioconversion)",
    parameter: "Ethanol",
    prep_method: "Wiley Milled",
    strain: "S. cerevisiae",
    time_h: 48,
    experiment: "EXP-FERM-01"
  };
  assert.strictEqual(hooks.groupContextLabel(fermNoPtObj), "S. cerevisiae @ 48h");
  assert.strictEqual(
    hooks.normalizeReplicateGroupKey(fermNoPtObj),
    "corn stover::cs-prep-01::fermentation::ethanol::s. cerevisiae @ 48h::exp-ferm-01"
  );

  const k6 = "almond hulls::ah-prep-01::proximate::ash::milled 2mm::exp-prox-01";
  const k4 = "grp::Almond Hulls::AH-PREP-01::Proximate Analysis::Ash";
  assert.strictEqual(hooks.matchesReplicateGroupKey(k6, k6), true);
  assert.strictEqual(hooks.matchesReplicateGroupKey(k6, k4), true);
  assert.strictEqual(
    hooks.matchesReplicateGroupKey(k6, "almond hulls::ah-prep-01::proximate::ash::knife milled::exp-prox-01"),
    false
  );

  // 2. Capture static QC-0001 metadata before server refresh
  const origQc1 = JSON.parse(JSON.stringify(hooks.state.decisionsById["QC-0001"]));
  assert.ok(origQc1.prepared_sample, "Expected static QC-0001 to have prepared_sample");
  assert.ok(origQc1.rsd_pct > 0, "Expected static QC-0001 to have rsd_pct > 0");
  assert.ok(origQc1.replicate_count >= 2, "Expected static QC-0001 to have replicate_count >= 2");

  // 3. Simulate server decisions:
  //    - A bug_report row (must be ignored)
  //    - DB id=1 (decision_id="QC-0001" from server) for an UNFLAGGED group (CAL-AH-001) -> must NOT overwrite static QC-0001; gets QC-DB-0001
  //    - DB id=2 matching static QC-0001 via 4-part key -> merges status/note without clobbering prepared_sample/rsd_pct/replicate_count
  mockServerDecisions = [
    {
      id: 99,
      decision_id: "QC-0099",
      record_table: "portal_bug_report",
      flag_type: "bug_report",
      record_id: "BUG-1"
    },
    {
      id: 1,
      decision_id: "QC-0001",
      record_table: "icp_record",
      record_id: "ICP-AH-001",
      replicate_group_key: "Almond Hulls::AH-PREP-01::ICP Elemental Analysis::Potassium (K)",
      resource_name: "Almond Hulls",
      analysis_type: "ICP Elemental Analysis",
      parameter_name: "Potassium (K)",
      decision_status: "in_review",
      review_note: "Tray item with DB id=1"
    },
    {
      id: 2,
      decision_id: "QC-0002",
      record_table: origQc1.record_table,
      record_id: origQc1.record_id,
      replicate_group_key: origQc1.resource_name + "::" + origQc1.prepared_sample + "::" + origQc1.analysis_type + "::" + origQc1.parameter_name,
      decision_status: "resolved",
      decision_action: "reject_fail",
      new_qc_pass: "fail",
      review_note: "Verified outlier on static QC-0001",
      assigned_to_email: "qa.analyst@lbl.gov",
      synced_to_gsheet: false
    }
  ];

  hooks.refreshQcStateFromApi();
  await new Promise((r) => setTimeout(r, 30));

  // Verify bug_report row was ignored
  assert.strictEqual(hooks.state.decisionsById["QC-DB-0099"], undefined);

  // Verify static QC-0001 was NOT overwritten by server id=1, and merged server id=2 properly
  const afterQc1 = hooks.state.decisionsById["QC-0001"];
  assert.strictEqual(afterQc1.db_id, 2);
  assert.strictEqual(afterQc1.decision_status, "resolved");
  assert.strictEqual(afterQc1.review_note, "Verified outlier on static QC-0001");
  assert.strictEqual(afterQc1.prepared_sample, origQc1.prepared_sample);
  assert.strictEqual(afterQc1.rsd_pct, origQc1.rsd_pct);
  assert.strictEqual(afterQc1.within_sd, origQc1.within_sd);
  assert.strictEqual(afterQc1.replicate_count, origQc1.replicate_count);
  assert.strictEqual(afterQc1.replicate_group_key, origQc1.replicate_group_key);

  // Verify server id=1 became non-colliding QC-DB-0001 and hydrated metadata from replicate_groups
  const dbDec1 = hooks.state.decisionsById["QC-DB-0001"];
  assert.ok(dbDec1, "Expected QC-DB-0001 to be created");
  assert.strictEqual(dbDec1.db_id, 1);
  assert.strictEqual(dbDec1.prepared_sample, "AH-PREP-01");
  assert.strictEqual(dbDec1.replicate_count, 2);
  assert.ok(dbDec1.rsd_pct > 0);
  assert.strictEqual(
    dbDec1.replicate_group_key,
    "almond hulls::ah-prep-01::icp::potassium (k)::milled 2mm::exp-icp-01"
  );

  // Verify repeated refresh does not duplicate QC-DB-0001 in decisionsOrder
  const countBefore = hooks.state.decisionsOrder.filter((x) => x === "QC-DB-0001").length;
  hooks.refreshQcStateFromApi();
  await new Promise((r) => setTimeout(r, 30));
  const countAfter = hooks.state.decisionsOrder.filter((x) => x === "QC-DB-0001").length;
  assert.strictEqual(countBefore, 1);
  assert.strictEqual(countAfter, 1);

  // Verify findReplicateGroupForDecision fallback by record_id when replicate_group_key is missing
  const foundByRecId = hooks.findReplicateGroupForDecision({
    record_table: "proximate_record",
    record_id: "PROX-AH-002"
  });
  assert.ok(foundByRecId, "Expected findReplicateGroupForDecision to resolve group by record_id");
  assert.strictEqual(foundByRecId.prepared_sample, "AH-PREP-01");

  // Verify db_id-first and exact-6-part-before-4-part priority when two candidates share a 4-part prefix
  hooks.state.decisionsById["QC-FERM-A"] = {
    id: "QC-FERM-A",
    decision_id: "QC-FERM-A",
    db_id: null,
    replicate_group_key: "corn stover::cs-prep-01::fermentation::ethanol::shf s. cerevisiae @ 48h::exp-1",
    record_table: "fermentation_record",
    record_id: "FM-A1",
    decision_status: "open",
    review_note: "Initial A"
  };
  hooks.state.decisionsById["QC-FERM-B"] = {
    id: "QC-FERM-B",
    decision_id: "QC-FERM-B",
    db_id: 77,
    replicate_group_key: "corn stover::cs-prep-01::fermentation::ethanol::shf z. mobilis @ 72h::exp-1",
    record_table: "fermentation_record",
    record_id: "FM-B1",
    decision_status: "open",
    review_note: "Initial B"
  };
  hooks.state.decisionsOrder.unshift("QC-FERM-B");
  hooks.state.decisionsOrder.unshift("QC-FERM-A");

  mockServerDecisions = [
    {
      id: 77,
      decision_id: "QC-0077",
      record_table: "fermentation_record",
      record_id: "FM-B1",
      // 4-part prefix would match QC-FERM-A first in decisionsOrder if db_id wasn't checked in Pass 1!
      replicate_group_key: "corn stover::cs-prep-01::fermentation::ethanol",
      decision_status: "resolved",
      review_note: "Matched QC-FERM-B by db_id priority"
    }
  ];
  hooks.refreshQcStateFromApi();
  await new Promise((r) => setTimeout(r, 30));
  assert.strictEqual(
    hooks.state.decisionsById["QC-FERM-B"].review_note,
    "Matched QC-FERM-B by db_id priority"
  );
  assert.strictEqual(
    hooks.state.decisionsById["QC-FERM-A"].review_note,
    "Initial A"
  );

  // Verify Card 4: DOMAIN_DEFS, normalizeDomainKey, and matchesFacetFilters slug/label compatibility
  assert.strictEqual(Array.isArray(hooks.DOMAIN_DEFS), true);
  assert.strictEqual(hooks.DOMAIN_DEFS.length, 10);
  assert.strictEqual(hooks.normalizeDomainKey("Proximate Analysis"), "proximate");
  assert.strictEqual(hooks.normalizeDomainKey("XRD Crystallinity"), "xrd");
  assert.strictEqual(hooks.normalizeDomainKey("Ash"), "xrf");
  hooks.state.filters.analysisType = "proximate";
  assert.strictEqual(
    hooks.matchesFacetFilters({ analysis_type: "Proximate Analysis" }),
    true
  );
  assert.strictEqual(
    hooks.matchesFacetFilters({ analysis_type: "Calorimetry" }),
    false
  );
  hooks.state.filters.analysisType = "";
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
"""
    )
    harness_js.write_text(harness_code, encoding="utf-8")
    proc = subprocess.run(
        [node_bin, str(harness_js)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"JS unit harness failed: {proc.stderr}\n{proc.stdout}"


def test_proximate_sum_portal_parity_and_fc_fallback() -> None:
    """Verify build_workbench_payload computes Data Portal proximate_sum with VS priority and (100 - FC) fallback."""
    snapshot = {
        "str_cols": [
            "resource_name",
            "analysis_type",
            "prepared_sample",
            "field_sample",
            "provider",
            "prep_method",
            "experiment",
            "analyst",
            "qc_status",
            "pt_method",
            "eh_method",
            "vessel",
            "strain",
            "bioconv",
            "well_or_block",
            "parameter",
            "unit",
            "note",
        ],
        "dicts": {
            "resource_name": ["Almond Hulls", "Walnut Shells"],
            "analysis_type": ["Proximate Analysis"],
            "prepared_sample": ["AH-S1", "WS-S1"],
            "field_sample": ["AH-F1", "WS-F1"],
            "provider": ["lbl"],
            "prep_method": ["Milled 2mm"],
            "experiment": ["EXP-A", "EXP-B"],
            "analyst": ["QA"],
            "qc_status": ["pass"],
            "pt_method": [""],
            "eh_method": [""],
            "vessel": [""],
            "strain": [""],
            "bioconv": [""],
            "well_or_block": [""],
            "parameter": ["Moisture", "Ash", "Volatile Solids", "Fixed Carbon"],
            "unit": ["%"],
            "note": [""],
        },
        # Row format: [record_id] + 18 str_cols indices + [replicate, value, exp_date]
        "rows": [
            # Stratum 1 (Almond Hulls::EXP-A::Milled 2mm): Moisture=8.0, Ash=5.0, VS=75.0, FC=12.0
            # Portal formula uses Moisture + Ash + VS = 8.0 + 5.0 + 75.0 = 88.0% (<95% -> flagged, FC ignored when VS present)
            ["R-M1", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 8.0, "2026-01-01"],
            ["R-A1", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 5.0, "2026-01-01"],
            ["R-V1", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 1, 75.0, "2026-01-01"],
            ["R-F1", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 1, 12.0, "2026-01-01"],
            # Stratum 2 (Walnut Shells::EXP-B::Milled 2mm): Moisture=6.0, Ash=2.0, NO VS, FC=18.0
            # Portal formula uses Moisture + Ash + (100 - FC) = 6.0 + 2.0 + 82.0 = 90.0% (<95% -> flagged)
            ["R-M2", 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 6.0, "2026-01-02"],
            ["R-A2", 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 2.0, "2026-01-02"],
            ["R-F2", 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 1, 18.0, "2026-01-02"],
        ],
    }
    payload = build_workbench_payload(snapshot)
    strata = payload["proximate_closure_by_stratum"]
    assert strata["Almond Hulls::EXP-A::Milled 2mm"]["proximate_sum_pct"] == pytest.approx(88.0)
    assert strata["Almond Hulls::EXP-A::Milled 2mm"]["out_of_bounds"] is True
    assert strata["Walnut Shells::EXP-B::Milled 2mm"]["proximate_sum_pct"] == pytest.approx(90.0)
    assert strata["Walnut Shells::EXP-B::Milled 2mm"]["out_of_bounds"] is True


def test_card12_default_assignee_and_bulk_assign_selected(tmp_path: Path) -> None:
    """Verify Card 12: getDefaultAssigneeEmail auto-fill in drawer/bulk bar and bulkAssignSelected batch POST."""
    node_bin = shutil.which("node")
    if node_bin is None:
        pytest.skip("node binary not available in PATH")

    output_html = tmp_path / "resource_audit_workbench.html"
    build_resource_audit_workbench(
        snapshot_path=MINIMAL_SNAPSHOT,
        output_path=output_html,
    )
    html_text = output_html.read_text(encoding="utf-8")
    assert 'id="btn-bulk-assign-my-email"' in html_text
    assert 'id="btn-clear-selection"' in html_text
    blocks = [
        block
        for block in re.findall(
            r"<script(?![^>]*\bsrc=)(?![^>]*application/json)[^>]*>(.*?)</script>",
            html_text,
            flags=re.S | re.I,
        )
        if block.strip()
    ]
    assert blocks

    harness_js = tmp_path / "run_card12_workbench_checks.js"
    harness_code = (
        """
const assert = require("assert");
const elements = {};
function makeEl(id) {
  return {
    id: id,
    value: "",
    textContent: "",
    innerHTML: "",
    style: {},
    className: "",
    checked: false,
    indeterminate: false,
    disabled: false,
    classList: {
      add: function () {},
      remove: function () {},
      toggle: function () {}
    },
    appendChild: function () {},
    addEventListener: function () {},
    getAttribute: function () { return ""; },
    setAttribute: function () {},
    querySelectorAll: function () { return []; }
  };
}
global.document = {
  getElementById: function (id) {
    if (!elements[id]) elements[id] = makeEl(id);
    return elements[id];
  },
  querySelectorAll: function () { return []; },
  createElement: function (tag) { return makeEl(tag); }
};
global.window = {
  location: { pathname: "/v1/dashboards/metadata/resource_audit_workbench.html", search: "" },
  history: { replaceState: function () {} },
  open: function () {}
};
let batchRequests = [];
global.fetch = function (url, opts) {
  if (String(url).indexOf("/v1/qc/auth/me") !== -1) {
    return Promise.resolve({
      ok: true,
      json: function () {
        return Promise.resolve({
          email: "qa.analyst@lbl.gov",
          name: "QA Analyst",
          role: "analyst",
          authenticated: true
        });
      }
    });
  }
  if (String(url).indexOf("/v1/qc/decisions/assign-batch") !== -1) {
    const body = opts && opts.body ? JSON.parse(opts.body) : {};
    batchRequests.push(body);
    const assignedEmail = String(body.assigned_to_email || "").trim().toLowerCase();
    const outDecisions = (body.items || []).map(function (it, idx) {
      return {
        id: it.id || (200 + idx),
        decision_id: it.decision_id,
        record_table: it.record_table,
        record_id: it.record_id,
        replicate_group_key: it.replicate_group_key,
        resource_name: it.resource_name,
        analysis_type: it.analysis_type,
        parameter_name: it.parameter_name,
        decision_status: "in_review",
        decision_action: "in_review",
        assigned_to_email: assignedEmail,
        assigned_by_email: "qa.analyst@lbl.gov",
        assigned_at: "2026-04-20T12:00:00Z"
      };
    });
    return Promise.resolve({
      ok: true,
      json: function () {
        return Promise.resolve({
          status: "ok",
          assigned_count: outDecisions.length,
          assigned_to_email: assignedEmail,
          assigned_by_email: "qa.analyst@lbl.gov",
          decisions: outDecisions
        });
      }
    });
  }
  if (String(url).indexOf("/v1/qc/decisions") !== -1) {
    return Promise.resolve({
      ok: true,
      json: function () {
        return Promise.resolve({ decisions: [] });
      }
    });
  }
  return Promise.resolve({ ok: false, json: function () { return Promise.resolve(null); } });
};
"""
        + blocks[0]
        + """
(async function () {
  await new Promise((r) => setTimeout(r, 30));
  const hooks = global.window.__WORKBENCH_TEST_HOOKS__;
  assert.ok(hooks, "Expected __WORKBENCH_TEST_HOOKS__ on window");

  // 1. Verify getDefaultAssigneeEmail returns authenticated user email, preserves existing assignment on QC-0001, and auto-fills unassigned #input-assigned-to and #bulk-assign-email
  assert.strictEqual(hooks.getDefaultAssigneeEmail(), "qa.analyst@lbl.gov");
  assert.strictEqual(hooks.getDefaultAssigneeEmail("analyst@lbl.gov"), "analyst@lbl.gov");
  assert.strictEqual(elements["input-assigned-to"].value, "qa.analyst@lbl.gov");
  hooks.state.decisionsById["QC-0001"].assigned_to_email = "explicit.owner@lbl.gov";
  hooks.selectDecision("QC-0001", false);
  assert.strictEqual(elements["input-assigned-to"].value, "explicit.owner@lbl.gov");
  hooks.state.decisionsById["QC-0001"].assigned_to_email = "";
  hooks.selectDecision("QC-0001", false);
  assert.strictEqual(elements["input-assigned-to"].value, "qa.analyst@lbl.gov");
  assert.strictEqual(elements["bulk-assign-email"].value, "qa.analyst@lbl.gov");

  // 2. Verify selectAllFilteredRows selects all visible queue decisions and updates #bulk-selected-count
  const visibleIds = hooks.getVisibleQueueDecisionIds();
  assert.ok(visibleIds.length >= 2, "Expected at least 2 visible queue decisions");
  hooks.selectAllFilteredRows();
  assert.strictEqual(hooks.state.selectedIds.size, visibleIds.length);
  assert.strictEqual(elements["bulk-selected-count"].textContent, visibleIds.length + " selected");
  assert.strictEqual(elements["btn-bulk-assign-apply"].disabled, false);
  assert.strictEqual(elements["btn-clear-selection"].disabled, false);

  // 3. Toggle off all except first 2 rows, test fillBulkAssignMyEmail, and run bulkAssignSelected
  hooks.clearRowSelection();
  assert.strictEqual(hooks.state.selectedIds.size, 0);
  assert.strictEqual(elements["btn-clear-selection"].disabled, true);
  elements["bulk-assign-email"].value = "other@lbl.gov";
  assert.strictEqual(hooks.fillBulkAssignMyEmail(), "qa.analyst@lbl.gov");
  assert.strictEqual(elements["bulk-assign-email"].value, "qa.analyst@lbl.gov");

  hooks.toggleRowSelection(visibleIds[0], true);
  hooks.toggleRowSelection(visibleIds[1], true);
  assert.strictEqual(hooks.state.selectedIds.size, 2);

  elements["bulk-assign-email"].value = "Lead.Reviewer@lbl.gov";
  const onlineRes = await hooks.bulkAssignSelected();
  assert.strictEqual(onlineRes.online, true);

  assert.strictEqual(batchRequests.length, 1);
  assert.strictEqual(batchRequests[0].assigned_to_email, "lead.reviewer@lbl.gov");
  assert.strictEqual(batchRequests[0].items.length, 2);
  assert.strictEqual(hooks.state.selectedIds.size, 0, "Expected selection to clear after bulk assign");

  const d0 = hooks.state.decisionsById[visibleIds[0]];
  const d1 = hooks.state.decisionsById[visibleIds[1]];
  assert.strictEqual(d0.assigned_to_email, "lead.reviewer@lbl.gov");
  assert.strictEqual(d1.assigned_to_email, "lead.reviewer@lbl.gov");
  assert.strictEqual(d0.decision_status, "in_review");
  assert.strictEqual(d1.decision_status, "in_review");
  assert.ok(d0.db_id >= 200);
  assert.ok(d1.db_id >= 200);

  // 4. Verify offline / failed POST fallback sets online=false and updates local state cleanly
  global.fetch = function () {
    return Promise.resolve({ ok: false, status: 503, json: function () { return Promise.resolve(null); } });
  };
  hooks.toggleRowSelection(visibleIds[0], true);
  elements["bulk-assign-email"].value = "Offline.Reviewer@lbl.gov";
  const offlineRes = await hooks.bulkAssignSelected();
  assert.strictEqual(offlineRes.ok, true);
  assert.strictEqual(offlineRes.online, false);
  assert.strictEqual(offlineRes.status, "assigned_offline");
  assert.strictEqual(hooks.state.decisionsById[visibleIds[0]].assigned_to_email, "offline.reviewer@lbl.gov");
  assert.ok(String(elements["decision-toast"].textContent || "").indexOf("offline fallback") !== -1);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
"""
    )
    harness_js.write_text(harness_code, encoding="utf-8")
    proc = subprocess.run(
        [node_bin, str(harness_js)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"Card 12 JS harness failed: {proc.stderr}\n{proc.stdout}"
