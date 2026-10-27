"""Tests for PR 5: Live QC Overlay, BroadcastChannel Sync, Replicate-Group-Default Selection, and Tray-to-Workbench."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis.metadata.resource_analysis_dashboard import (  # noqa: E402
    SHARED_SLICE_AND_BUG_MODALS_JS,
    build_analysis_dashboard_html,
    build_qc_outlier_dashboard_html,
    prepare_dashboard_payload,
)
from analysis.metadata.resource_explorer_dashboard import (  # noqa: E402
    build_full_dashboard_html,
)
from analysis.metadata.resource_insights_engine import (  # noqa: E402
    build_resource_insights,
)

SNAPSHOT_PATH = REPO_ROOT / "tests/fixtures/minimal_dashboard_snapshot.json"


@pytest.fixture(scope="module")
def snapshot_and_pages() -> dict[str, str]:
    payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    insights = build_resource_insights(payload)
    bundle = prepare_dashboard_payload(payload, insights)
    page1_html = build_analysis_dashboard_html(bundle)
    page2_html = build_qc_outlier_dashboard_html(bundle)
    page3_html = build_full_dashboard_html(payload)
    return {
        "page1": page1_html,
        "page2": page2_html,
        "page3": page3_html,
    }


def test_all_pages_include_live_qc_overlay_and_refresh_button(
    snapshot_and_pages: dict[str, str],
) -> None:
    for name, html in snapshot_and_pages.items():
        assert 'id="nav-page-workbench"' in html, f"{name} missing #nav-page-workbench link"
        assert "resource_audit_workbench.html" in html, f"{name} missing workbench href"
        assert 'id="btn-refresh-qc-state"' in html, f"{name} missing #btn-refresh-qc-state"
        assert "Refresh QC State" in html, f"{name} missing Refresh QC State label"
        assert 'id="live-qc-overlay-badge"' in html, f"{name} missing #live-qc-overlay-badge"
        assert 'BroadcastChannel("biocirv_qc_decisions")' in html, (
            f"{name} missing BroadcastChannel listener"
        )
        assert "/v1/qc/decisions" in html, f"{name} missing GET /v1/qc/decisions endpoint"
        assert "window.refreshLiveQcOverlay" in html, f"{name} missing refreshLiveQcOverlay"
        assert "applyLiveQcDecisionsOverlay" in html, (
            f"{name} missing applyLiveQcDecisionsOverlay"
        )
        # Strict requirement: zero background polling via setInterval
        assert "setInterval(" not in html, f"{name} must not use setInterval polling"


def test_replicate_group_default_selection_and_one_click_toggle(
    snapshot_and_pages: dict[str, str],
) -> None:
    page2 = snapshot_and_pages["page2"]
    page3 = snapshot_and_pages["page3"]

    # Shared modal defaults to "group" unless prefer_single === true or scope is single
    assert 'let initialChoice = "group";' in page2
    assert 'if (rawScope === "single" || rawScope === "single_record" || pf.prefer_single === true)' in page2
    assert 'id="finding-scope-btn-group"' in page2
    assert 'id="finding-scope-btn-single"' in page2
    assert "Entire Replicate Group" in page2
    assert "Single Point Only" in page2

    # Page 2 outlier and explorer tables default triage_scope to "group" and replicate_group scope
    assert 'const defaultTriageScope = "group";' in page2
    assert 'triage_scope: "group"' in page2
    assert 'scope: "replicate_group"' in page2

    # Page 3 defaults auditPopoverScope and pin-audit-scope to 'group' with 1-click toggle
    assert "let auditPopoverScope = 'group';" in page3
    assert "function setAuditPopoverScope(scope)" in page3
    assert 'id="btn-audit-scope-group"' in page3
    assert 'id="btn-audit-scope-single"' in page3


def test_unified_export_tray_and_export_to_audit_workbench(
    snapshot_and_pages: dict[str, str],
) -> None:
    page2 = snapshot_and_pages["page2"]
    page3 = snapshot_and_pages["page3"]

    for name, html in [("page2", page2), ("page3", page3)]:
        assert "⬇ Export Tray (.CSV)" in html, f"{name} missing CSV tray button"
        assert "📤 Export Slice (.HTML)" in html, f"{name} missing HTML slice tray button"
        assert "⚖️ Export to Audit Workbench" in html, (
            f"{name} missing Export to Audit Workbench button"
        )
        assert 'id="btn-tray-to-workbench"' in html, f"{name} missing #btn-tray-to-workbench"
        assert 'id="btn-finding-export-workbench"' in html, (
            f"{name} missing #btn-finding-export-workbench in modal"
        )
        assert "/v1/qc/tray-to-workbench" in html, (
            f"{name} missing POST /v1/qc/tray-to-workbench endpoint"
        )
        assert "exportTrayToWorkbench" in html, f"{name} missing exportTrayToWorkbench helper"


def test_tray_to_workbench_contract_and_unified_overlay_execution(
    snapshot_and_pages: dict[str, str], tmp_path: Path
) -> None:
    # Ensure Page 3 does not overwrite the shared applyLiveQcDecisionsOverlay
    page3 = snapshot_and_pages["page3"]
    assert page3.count("applyLiveQcDecisionsOverlay =") == 1

    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("node binary not available")

    harness = (
        """
const capturedBodies = [];
const badgeNode = {
  textContent: "",
  hidden: true,
  classList: {
    remove(cls) { if (cls === "hidden") badgeNode.hidden = false; },
    add(cls) { if (cls === "hidden") badgeNode.hidden = true; }
  }
};
global.window = global;
global.window.location = { protocol: "http:", search: "", href: "" };
global.BroadcastChannel = class BroadcastChannel { constructor(name) { this.name = name; } postMessage() {} close() {} };
global.CustomEvent = class CustomEvent { constructor(name, opts) { this.type = name; this.detail = opts && opts.detail; } };
global.window.dispatchEvent = () => {};
global.window.addEventListener = () => {};
global.localStorage = {
  _s: {},
  getItem(k) { return this._s[k] || null; },
  setItem(k, v) { this._s[k] = String(v); }
};
global.document = {
  title: "Test",
  readyState: "complete",
  getElementById(id) {
    if (id === "live-qc-overlay-badge") return badgeNode;
    return null;
  },
  querySelectorAll() { return []; },
  createElement() { return { style: {}, classList: { add(){}, remove(){} }, appendChild(){} }; },
  body: { appendChild(){} }
};
global.ALL_RECORDS = [
  { record_id: "rec-101", qc_status: "pass", qc_pass: "pass", resource_portal_excluded: false },
  { record_id: "rec-102", qc_status: "pass", qc_pass: "pass", resource_portal_excluded: false }
];
let filtersApplied = 0;
global.applyFilters = () => { filtersApplied += 1; };
global.ALL_ROWS = [
  { record_id: "rec-101", qc_pass: "pass", qc_status: "pass", data_status: "Portal Compliant" },
  { record_id: "rec-202", qc_pass: "pass", qc_status: "pass", data_status: "Portal Compliant" }
];
global.fetch = async (url, opts) => {
  const parsed = JSON.parse(opts.body);
  capturedBodies.push({ url, body: parsed });
  return {
    ok: true,
    async json() {
      return {
        status: "ok",
        created_count: parsed.items ? parsed.items.length : 1,
        decision_id: 1,
        decision_ids: [1, 2],
        workbench_url: "/v1/dashboards/metadata/resource_audit_workbench.html?decision_id=1",
        decisions: (parsed.items || []).map((it, idx) => ({
          id: idx + 1,
          record_table: it.record_table,
          record_id: it.record_id,
          record_ids: it.record_ids,
          new_qc_pass: "fail",
          decision_status: "reject_fail"
        }))
      };
    }
  };
};
"""
        + SHARED_SLICE_AND_BUG_MODALS_JS
        + """
(async () => {
  // 1. Test Array payload from Explorer exportExplorerTrayToWorkbench
  const resArr = await window.BioCirvQcClient.exportTrayToWorkbench([
    {
      scope: "replicate_group",
      resource_name: "Almond Hulls",
      analysis_type: "Compositional Analysis",
      parameter: "glucan",
      record_ids: ["rec-101", "rec-102"],
      note: "High RSD across replicates"
    },
    {
      scope: "single_record",
      resource_name: "Rice Straw",
      analysis_type: "Ultimate",
      parameter_name: "carbon",
      record_id: "rec-202",
      review_note: "Outlier carbon %"
    }
  ], "Page 3 — Multi-Resource Side-by-Side Explorer");

  // 2. Test overlay with API array format (new_qc_pass: "fail")
  const overlayStats1 = window.applyLiveQcDecisionsOverlay([
    { record_id: "rec-101", record_ids: ["rec-101", "rec-102"], new_qc_pass: "fail", decision_status: "reject_fail" }
  ]);

  // 3. Test overlay with plain object map format
  const overlayStats2 = window.applyLiveQcDecisionsOverlay({
    "rec-202": { new_qc_status: "fail" }
  });

  console.log(JSON.stringify({
    capturedBody: capturedBodies[0].body,
    persisted: resArr.persisted,
    overlayStats1,
    overlayStats2,
    allRecords: global.ALL_RECORDS,
    allRows: global.ALL_ROWS,
    filtersApplied,
    badgeText: badgeNode.textContent
  }));
  process.exit(0);
})();
"""
    )
    harness_path = tmp_path / "run_contract_test.js"
    harness_path.write_text(harness, encoding="utf-8")
    proc = subprocess.run(
        [node_bin, str(harness_path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert proc.returncode == 0, f"Node harness failed: {proc.stderr}"
    out = json.loads(proc.stdout.strip().splitlines()[-1])

    body = out["capturedBody"]
    assert body["record_table"] == "compositional_record"
    assert body["record_id"] == "rec-101"
    assert body["record_ids"] == ["rec-101", "rec-102"]
    assert body["review_note"] == "High RSD across replicates"
    assert len(body["items"]) == 2
    assert body["items"][0]["record_table"] == "compositional_record"
    assert body["items"][1]["record_table"] == "ultimate_record"
    assert body["items"][1]["record_id"] == "rec-202"
    assert body["items"][1]["record_ids"] == ["rec-202"]
    assert body["items"][1]["review_note"] == "Outlier carbon %"
    assert out["persisted"] == 2

    # Verify both ALL_RECORDS and ALL_ROWS were updated by unified applyLiveQcDecisionsOverlay
    assert out["overlayStats1"]["totalDecisions"] == 2
    assert out["allRecords"][0]["qc_status"] == "fail"
    assert out["allRecords"][1]["qc_status"] == "fail"
    assert out["allRows"][1]["qc_pass"] == "fail"
    assert out["allRows"][1]["data_status"] == "Raw"
    assert out["filtersApplied"] >= 2
    assert "Stage 1 Live Overlay" in out["badgeText"]


def test_inline_scripts_pass_node_syntax_check(
    snapshot_and_pages: dict[str, str], tmp_path: Path
) -> None:
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("node binary not available")

    script_pattern = re.compile(r"<script(?:\s+[^>]*)?>(.*?)</script>", re.DOTALL)
    for name, html in snapshot_and_pages.items():
        scripts = [s.strip() for s in script_pattern.findall(html) if s.strip()]
        assert scripts, f"No inline <script> blocks found in {name}"
        for idx, script_code in enumerate(scripts):
            js_file = tmp_path / f"{name}_script_{idx}.js"
            js_file.write_text(script_code, encoding="utf-8")
            proc = subprocess.run(
                [node_bin, "--check", str(js_file)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert proc.returncode == 0, (
                f"node --check failed for {name} script #{idx}: {proc.stderr}"
            )


def test_cli_output_flag_leaves_repo_clean(tmp_path: Path) -> None:
    out_analysis = tmp_path / "test_analysis.html"
    out_explorer = tmp_path / "test_explorer.html"

    res_analysis = subprocess.run(
        [
            sys.executable,
            "analysis/metadata/resource_analysis_dashboard.py",
            "--from-snapshot",
            str(SNAPSHOT_PATH),
            "--output",
            str(out_analysis),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_analysis.returncode == 0, res_analysis.stderr
    assert out_analysis.exists()
    assert (tmp_path / "resource_qc_outlier_dashboard.html").exists()

    res_explorer = subprocess.run(
        [
            sys.executable,
            "analysis/metadata/resource_explorer_dashboard.py",
            "--from-snapshot",
            str(SNAPSHOT_PATH),
            "--output",
            str(out_explorer),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_explorer.returncode == 0, res_explorer.stderr
    assert out_explorer.exists()


def test_card3_page2_kpi_labels_and_sd_display(
    snapshot_and_pages: dict[str, str],
) -> None:
    page1 = snapshot_and_pages["page1"]
    page2 = snapshot_and_pages["page2"]
    assert "${outSummary.flaggedActive || 0}</strong> active outlier group(s)" in page1
    assert "outSummary.suppressedTrace ? `(${outSummary.suppressedTrace} trace" in page1
    assert "${out.flagged_active_groups" not in page1
    assert "${out.suppressed_low_abundance_groups" not in page1
    assert "Flag Counts (" in page2
    assert "Within-Replicate RSD & SD" in page2
    assert "Between-Sample RSD & SD (Method-Stratified)" in page2
    assert "N/A (n=1 method group)" in page2
    assert "Identical Replicates (SD=0)" in page2
    assert "Collection & Prep Dates" not in page2


def test_card3_get_outlier_summary_and_live_overlay_replicate_groups(
    tmp_path: Path,
) -> None:
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("node binary not available")

    harness = (
        """
global.window = global;
global.window.location = { protocol: "http:", search: "", href: "" };
global.BroadcastChannel = class BroadcastChannel { constructor(name) { this.name = name; } postMessage() {} close() {} };
global.CustomEvent = class CustomEvent { constructor(name, opts) { this.type = name; this.detail = opts && opts.detail; } };
global.window.dispatchEvent = () => {};
global.window.addEventListener = () => {};
global.localStorage = {
  _s: {},
  getItem(k) { return this._s[k] || null; },
  setItem(k, v) { this._s[k] = String(v); }
};
global.document = {
  title: "Test",
  readyState: "complete",
  getElementById() { return null; },
  querySelectorAll() { return []; },
  createElement() { return { style: {}, classList: { add(){}, remove(){} }, appendChild(){} }; },
  body: { appendChild(){} }
};
global.BUNDLE = {
  insights: {
    "almond hulls": {
      outlier_screening: {
        summary: {
          flagged_replicate_groups: 2,
          overall_within_rsd_median: 14.2,
          overall_within_sd_median: 1.05,
          overall_between_rsd_median: 8.6,
          overall_between_sd_median: 0.72,
          rsd_defined_groups: 5,
          suppressed_low_abundance_groups: 1
        },
        by_tab: {
          proximate: {
            flagged_active: 1,
            replicate_groups: [
              {
                analysis_type: "Proximate Analysis",
                prepared_sample: "AH-PS-01",
                prep_method: "Dried 60C",
                experiment: "EXP-01",
                parameter: "Ash",
                n: 3,
                mean: 10.0,
                sd: 3.5,
                within_sd: 3.5,
                rsd_within_pct: 35.0,
                raw_dixon: true,
                dixon_candidate_id: "prox-3",
                raw_rsd20: true,
                raw_rsd10: true,
                raw_sd3x: false,
                below_cutoff: false,
                raw_flagged: true,
                active_flagged: true,
                flagged_active: true,
                qc_pass_count: 3,
                qc_fail_count: 0,
                replicates: [
                  { id: "prox-1", rep: 1, val: 8.0, qc: "pass" },
                  { id: "prox-2", rep: 2, val: 8.2, qc: "pass" },
                  { id: "prox-3", rep: 3, val: 13.8, qc: "pass" }
                ]
              },
              {
                analysis_type: "Proximate Analysis",
                prepared_sample: "AH-PS-02",
                prep_method: "Dried 60C",
                experiment: "EXP-01",
                parameter: "Volatile Matter",
                n: 3,
                mean: 70.0,
                sd: 8.5,
                within_sd: 8.5,
                rsd_within_pct: 12.14,
                raw_dixon: true,
                dixon_candidate_id: null,
                raw_rsd20: false,
                raw_rsd10: true,
                raw_sd3x: false,
                below_cutoff: false,
                raw_flagged: true,
                active_flagged: true,
                flagged_active: true,
                qc_pass_count: 3,
                qc_fail_count: 0,
                replicates: [
                  { id: "prox-vm-1", rep: 1, val: 65.0, qc: "pass" },
                  { id: "prox-vm-2", rep: 2, val: 65.4, qc: "pass" },
                  { id: "prox-vm-3", rep: 3, val: 79.6, qc: "pass" }
                ]
              }
            ]
          }
        }
      }
    }
  }
};
"""
        + SHARED_SLICE_AND_BUG_MODALS_JS
        + """
const sumNested = window.getOutlierSummary(global.BUNDLE.insights["almond hulls"]);

// Fallback when summary block is absent and only by_tab.replicate_groups + param_rsd_table exist
const sumFallback = window.getOutlierSummary({
  outlier_screening: {
    by_tab: {
      proximate: {
        replicate_groups: [
          { n: 3, rsd_within_pct: 4.0, within_sd: 0.25, active_flagged: true, raw_flagged: true, below_cutoff: false },
          { n: 3, rsd_within_pct: 6.0, within_sd: 0.45, active_flagged: false, raw_flagged: true, below_cutoff: true }
        ],
        param_rsd_table: [
          { between_rsd_pct: 11.5, between_sd: 0.88, below_cutoff: false }
        ]
      }
    }
  }
});

// Verify 6-part replicate_group_key alignment with pt_method-first for Pretreatment and Ash->xrf
const ptKey = window.normalizeReplicateGroupKey({
  resource_name: "Almond Hulls",
  prepared_sample: "AH-PS-01",
  analysis_type: "Pretreatment",
  parameter: "Glucose",
  pt_method: "Dilute Acid",
  prep_method: "Wiley Milled",
  eh_method: "CTec3",
  experiment: "EXP-PT-1"
});
const ashItem = window.BioCirvQcClient.normalizeTrayWorkbenchItem({
  resource_name: "Almond Hulls",
  prepared_sample: "AH-PS-01",
  analysis_type: "Ash",
  parameter: "CaO",
  prep_method: "600C Ashing",
  experiment: "EXP-XRF-1",
  record_id: "xrf-1"
});
const fermNoPtKey = window.normalizeReplicateGroupKey({
  resource_name: "Corn Stover",
  prepared_sample: "CS-PREP-01",
  analysis_type: "Fermentation (Bioconversion)",
  parameter: "Ethanol",
  prep_method: "Wiley Milled",
  strain: "S. cerevisiae",
  time_h: 48,
  experiment: "EXP-FERM-01"
});

// Apply live QC overlay to quarantine outliers prox-3 and prox-vm-3 -> active_flagged and raw_dixon should drop to false
const overlayRes = window.applyLiveQcDecisionsOverlay([
  { record_id: "prox-3", new_qc_pass: "fail", decision_status: "reject_fail" },
  { record_id: "prox-vm-3", new_qc_pass: "fail", decision_status: "reject_fail" }
]);
const grpAfter = global.BUNDLE.insights["almond hulls"].outlier_screening.by_tab.proximate.replicate_groups[0];
const grpNoCandAfter = global.BUNDLE.insights["almond hulls"].outlier_screening.by_tab.proximate.replicate_groups[1];
const sumAfter = window.getOutlierSummary(global.BUNDLE.insights["almond hulls"]);

console.log(JSON.stringify({
  sumNested,
  sumFallback,
  ptKey,
  ashKey: ashItem.replicate_group_key,
  fermNoPtKey,
  overlayRes,
  grpAfter: {
    qc_pass_count: grpAfter.qc_pass_count,
    qc_fail_count: grpAfter.qc_fail_count,
    within_sd: grpAfter.within_sd,
    rsd_within_pct: grpAfter.rsd_within_pct,
    raw_dixon: grpAfter.raw_dixon,
    active_flagged: grpAfter.active_flagged,
    flagged_active: grpAfter.flagged_active
  },
  grpNoCandAfter: {
    qc_pass_count: grpNoCandAfter.qc_pass_count,
    qc_fail_count: grpNoCandAfter.qc_fail_count,
    within_sd: grpNoCandAfter.within_sd,
    rsd_within_pct: grpNoCandAfter.rsd_within_pct,
    raw_dixon: grpNoCandAfter.raw_dixon,
    active_flagged: grpNoCandAfter.active_flagged,
    flagged_active: grpNoCandAfter.flagged_active
  },
  sumAfter
}));
"""
    )
    harness_path = tmp_path / "run_card3_test.js"
    harness_path.write_text(harness, encoding="utf-8")
    proc = subprocess.run(
        [node_bin, str(harness_path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert proc.returncode == 0, f"Node harness failed: {proc.stderr}"
    out = json.loads(proc.stdout.strip().splitlines()[-1])

    # Nested summary schema compatibility
    assert out["sumNested"]["flaggedActive"] == 2
    assert out["sumNested"]["withinRsdMedian"] == 14.2
    assert out["sumNested"]["withinSdMedian"] == 1.05
    assert out["sumNested"]["betweenRsdMedian"] == 8.6
    assert out["sumNested"]["betweenSdMedian"] == 0.72
    assert out["sumNested"]["rsdDefinedGroups"] == 5
    assert out["sumNested"]["suppressedTrace"] == 1

    # Fallback computation from by_tab
    assert out["sumFallback"]["flaggedActive"] == 1
    assert out["sumFallback"]["suppressedTrace"] == 1
    assert out["sumFallback"]["withinRsdMedian"] == 5.0
    assert out["sumFallback"]["withinSdMedian"] == 0.35
    assert out["sumFallback"]["betweenRsdMedian"] == 11.5
    assert out["sumFallback"]["betweenSdMedian"] == 0.88

    # 6-part key parity across Card 1, Card 2, and Card 3 (pt_method first for Pretreatment; Ash -> xrf)
    from analysis.metadata.resource_audit_workbench import (
        normalize_replicate_group_key as card2_normalize_key,
    )
    from analysis.metadata.resource_insights_engine import (
        compute_dataset_outlier_screening,
    )

    pt_row = {
        "record_id": "pt-1",
        "resource_name": "Almond Hulls",
        "prepared_sample": "AH-PS-01",
        "analysis_type": "Pretreatment",
        "parameter": "Glucose",
        "unit": "g/L",
        "value": 12.4,
        "qc_status": "pass",
        "pt_method": "Dilute Acid",
        "prep_method": "Wiley Milled",
        "eh_method": "CTec3",
        "experiment": "EXP-PT-1",
    }
    ash_row = {
        "record_id": "xrf-1",
        "resource_name": "Almond Hulls",
        "prepared_sample": "AH-PS-01",
        "analysis_type": "Ash",
        "parameter": "CaO",
        "unit": "%",
        "value": 4.2,
        "qc_status": "pass",
        "prep_method": "600C Ashing",
        "experiment": "EXP-XRF-1",
    }
    card1_screening = compute_dataset_outlier_screening(
        {"Almond Hulls": [pt_row, ash_row]}
    )["Almond Hulls"]
    card1_pt_key = card1_screening["by_tab"]["pretreatment"]["replicate_groups"][0][
        "replicate_group_key"
    ]
    card1_ash_key = card1_screening["by_tab"]["elemental"]["replicate_groups"][0][
        "replicate_group_key"
    ]
    card2_pt_key = card2_normalize_key(pt_row)
    card2_ash_key = card2_normalize_key(ash_row)

    expected_pt_key = "almond hulls::ah-ps-01::pretreatment::glucose::dilute acid · ctec3::exp-pt-1"
    expected_ash_key = "almond hulls::ah-ps-01::xrf::cao::600c ashing::exp-xrf-1"
    expected_ferm_no_pt_key = "corn stover::cs-prep-01::fermentation::ethanol::s. cerevisiae @ 48h::exp-ferm-01"
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
    assert out["ptKey"] == expected_pt_key == card1_pt_key == card2_pt_key
    assert out["ashKey"] == expected_ash_key == card1_ash_key == card2_ash_key
    assert out["fermNoPtKey"] == expected_ferm_no_pt_key == card2_normalize_key(ferm_no_pt_row)

    # Live overlay on replicate_groups recomputes within_sd, rsd_within_pct, raw_dixon, and active_flagged
    assert out["grpAfter"]["qc_pass_count"] == 2
    assert out["grpAfter"]["qc_fail_count"] == 1
    assert out["grpAfter"]["rsd_within_pct"] < 5.0
    assert out["grpAfter"]["within_sd"] < 0.2
    assert out["grpAfter"]["raw_dixon"] is False
    assert out["grpAfter"]["active_flagged"] is False
    assert out["grpAfter"]["flagged_active"] is False

    # Even when dixon_candidate_id is null, dropping rsd_within_pct < 10% clears raw_dixon and active_flagged
    assert out["grpNoCandAfter"]["qc_pass_count"] == 2
    assert out["grpNoCandAfter"]["qc_fail_count"] == 1
    assert out["grpNoCandAfter"]["rsd_within_pct"] < 1.0
    assert out["grpNoCandAfter"]["raw_dixon"] is False
    assert out["grpNoCandAfter"]["active_flagged"] is False
    assert out["grpNoCandAfter"]["flagged_active"] is False
    assert out["sumAfter"]["flaggedActive"] == 0
