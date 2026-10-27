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


def test_card4_individual_analytical_domain_filters_and_cross_page_parity(
    tmp_path: Path,
) -> None:
    """Verify Card 4: byte-identical DOMAIN_DEFS/normalizeDomainKey across all 3 generators,
    10 individual domain pills on Page 2 & Page 3, and Page 2 filtering across shared by_tab keys."""
    node_bin = shutil.which("node")
    if node_bin is None:
        pytest.skip("node binary not available in PATH")

    from analysis.metadata.resource_audit_workbench import (
        build_resource_audit_workbench,
    )

    payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    insights = build_resource_insights(payload)
    bundle = prepare_dashboard_payload(payload, insights)
    res_key = next(
        (k for k in bundle.get("insights", {}) if k.lower() == "almond hulls"),
        "almond hulls",
    )
    bundle.setdefault("insights", {}).setdefault(res_key, {}).setdefault(
        "outlier_screening", {}
    )["by_tab"] = {
        "proximate": {
            "replicate_groups": [
                {
                    "replicate_group_key": "almond hulls::ah-ps-01::proximate::ash::oven-105c::exp-01",
                    "analysis_type": "Proximate Analysis",
                    "prepared_sample": "AH-PS-01",
                    "experiment": "EXP-01",
                    "parameter": "Ash",
                    "n": 3,
                    "qc_pass_count": 3,
                    "qc_fail_count": 0,
                    "active_flagged": True,
                    "raw_flagged": True,
                    "below_cutoff": False,
                },
                {
                    "replicate_group_key": "almond hulls::ah-ps-01::calorimetry::hhv::bomb::exp-01",
                    "analysis_type": "Calorimetry",
                    "prepared_sample": "AH-PS-01",
                    "experiment": "EXP-01",
                    "parameter": "HHV",
                    "n": 3,
                    "qc_pass_count": 3,
                    "qc_fail_count": 0,
                    "active_flagged": False,
                    "raw_flagged": False,
                    "below_cutoff": False,
                },
            ],
            "param_rsd_table": [
                {"analysis_type": "Proximate Analysis", "parameter": "Ash", "within_rsd_pct": 5.0},
                {"analysis_type": "Calorimetry", "parameter": "HHV", "within_rsd_pct": 1.2},
            ],
        },
        "compositional": {
            "replicate_groups": [
                {
                    "replicate_group_key": "almond hulls::ah-ps-01::compositional::glucan::nrel::exp-01",
                    "analysis_type": "Compositional Analysis",
                    "prepared_sample": "AH-PS-01",
                    "experiment": "EXP-01",
                    "parameter": "Glucan",
                    "n": 3,
                    "qc_pass_count": 3,
                    "qc_fail_count": 0,
                    "active_flagged": False,
                    "raw_flagged": False,
                    "below_cutoff": False,
                },
                {
                    "replicate_group_key": "almond hulls::ah-ps-01::ultimate::carbon::chn::exp-01",
                    "analysis_type": "Ultimate Analysis",
                    "prepared_sample": "AH-PS-01",
                    "experiment": "EXP-01",
                    "parameter": "Carbon",
                    "n": 3,
                    "qc_pass_count": 3,
                    "qc_fail_count": 0,
                    "active_flagged": True,
                    "raw_flagged": True,
                    "below_cutoff": False,
                },
                {
                    "replicate_group_key": "almond hulls::ah-ps-01::xrd::crystallinity::powder::exp-01",
                    "analysis_type": "XRD Crystallinity",
                    "prepared_sample": "AH-PS-01",
                    "experiment": "EXP-01",
                    "parameter": "Crystallinity",
                    "n": 3,
                    "qc_pass_count": 3,
                    "qc_fail_count": 0,
                    "active_flagged": False,
                    "raw_flagged": False,
                    "below_cutoff": False,
                },
            ],
            "param_rsd_table": [
                {"analysis_type": "Compositional Analysis", "parameter": "Glucan", "within_rsd_pct": 2.1},
                {"analysis_type": "Ultimate Analysis", "parameter": "Carbon", "within_rsd_pct": 3.4},
                {"analysis_type": "XRD Crystallinity", "parameter": "Crystallinity", "within_rsd_pct": 4.0},
            ],
        },
        "elemental": {
            "replicate_groups": [
                {
                    "replicate_group_key": "almond hulls::ah-ps-01::icp::ca::microwave::exp-01",
                    "analysis_type": "ICP Elemental Analysis",
                    "prepared_sample": "AH-PS-01",
                    "experiment": "EXP-01",
                    "parameter": "Ca",
                    "n": 3,
                    "qc_pass_count": 3,
                    "qc_fail_count": 0,
                    "active_flagged": False,
                    "raw_flagged": False,
                    "below_cutoff": False,
                },
                {
                    "replicate_group_key": "almond hulls::ah-ps-01::xrf::k::pellet::exp-01",
                    "analysis_type": "XRF Elemental Analysis",
                    "prepared_sample": "AH-PS-01",
                    "experiment": "EXP-01",
                    "parameter": "K",
                    "n": 3,
                    "qc_pass_count": 3,
                    "qc_fail_count": 0,
                    "active_flagged": True,
                    "raw_flagged": True,
                    "below_cutoff": False,
                },
            ],
            "param_rsd_table": [
                {"analysis_type": "ICP Elemental Analysis", "parameter": "Ca", "within_rsd_pct": 1.5},
                {"analysis_type": "XRF Elemental Analysis", "parameter": "K", "within_rsd_pct": 6.2},
            ],
        },
    }

    page2_html = build_qc_outlier_dashboard_html(bundle, default_resource="almond hulls")
    page3_html = build_full_dashboard_html(payload)
    wb_path = tmp_path / "wb.html"
    build_resource_audit_workbench(snapshot_path=SNAPSHOT_PATH, output_path=wb_path)
    wb_html = wb_path.read_text(encoding="utf-8")

    # 1. Verify byte-identical DOMAIN_DEFS and normalizeDomainKey block across all 3 generators
    domain_defs_pattern = re.compile(
        r"(const DOMAIN_DEFS = \[.*?\];\s*window\.DOMAIN_DEFS = DOMAIN_DEFS;\s*function normalizeDomainKey\(raw\) \{.*?\}\s*window\.normalizeDomainKey = normalizeDomainKey;)",
        re.S,
    )
    m_p2 = domain_defs_pattern.search(page2_html)
    m_p3 = domain_defs_pattern.search(page3_html)
    m_wb = domain_defs_pattern.search(wb_html)
    assert m_p2 and m_p3 and m_wb, "Expected DOMAIN_DEFS + normalizeDomainKey in all 3 generators"
    assert m_p2.group(1) == m_p3.group(1) == m_wb.group(1), (
        "DOMAIN_DEFS and normalizeDomainKey must be byte-identical across Page 1/2, Page 3, and Product 4"
    )

    # 2. Verify Page 3 splits Calorimetry and XRD (no paired calorimetry_xrd pill, axis title, or branch)
    assert "{ id: 'calorimetry', label: 'Calorimetry'" in page3_html
    assert "{ id: 'xrd', label: 'XRD'" in page3_html
    assert "calorimetry: 'Calorimetry Parameter (MJ/kg)'" in page3_html
    assert "xrd: 'XRD Crystallinity Parameter (%)'" in page3_html
    page3_own_source = page3_html.replace(SHARED_SLICE_AND_BUG_MODALS_JS, "")
    assert "calorimetry_xrd" not in page3_own_source

    # 3. Execute Page 2 inline JS in Node to verify individual domain pill rendering and shared-by_tab filtering
    m_script = re.search(
        r"<script>\s*(const BUNDLE = .*?)</script>", page2_html, flags=re.S
    )
    assert m_script
    p2_script = m_script.group(1)

    harness_js = tmp_path / "run_card4_domain_checks.js"
    harness_js.write_text(
        """
const elements = {};
function makeEl(id) {
  return {
    id, value: "", textContent: "", innerHTML: "", className: "", style: {}, dataset: {},
    classList: { add(){}, remove(){}, toggle(){}, contains(){ return false; } },
    addEventListener(){}, removeEventListener(){}, setAttribute(){}, getAttribute(){ return null; },
    appendChild(){}, querySelectorAll(){ return []; }, focus(){}, setSelectionRange(){}
  };
}
global.window = {
  location: { href: "http://localhost:8000/v1/dashboards/metadata/resource_qc_outlier_dashboard.html?resource=almond+hulls&domain=calorimetry_xrd", search: "?resource=almond+hulls&domain=calorimetry_xrd", origin: "http://localhost:8000", pathname: "/v1/dashboards/metadata/resource_qc_outlier_dashboard.html" },
  history: { replaceState(){} },
  addEventListener(){}
};
global.document = {
  documentElement: { getAttribute(){ return "dark"; }, setAttribute(){} },
  body: makeEl("body"),
  getElementById(id) { if (!elements[id]) elements[id] = makeEl(id); return elements[id]; },
  querySelectorAll(){ return []; },
  createElement(t){ return makeEl(t); }
};
global.localStorage = { getItem(){ return null; }, setItem(){}, removeItem(){} };
global.fetch = async () => ({ ok: false, status: 401, json: async () => ({}) });
"""
        + p2_script
        + """
const pillsHtml = document.getElementById("domain-pills").innerHTML;
// Verify legacy URL ?domain=calorimetry_xrd normalized to "calorimetry"
const initialDom = state.domain;

const byDom = {};
["all", ...window.DOMAIN_DEFS.map(d => d.key)].forEach(k => {
  window.setDomain(k);
  byDom[k] = {
    groups: getAllDomainOutlierGroups().map(g => g.parameter),
    params: getAllDomainParamRsdRows().map(p => p.parameter),
    navExplorerHref: document.getElementById("nav-page-explorer").href
  };
});

console.log(JSON.stringify({
  domainKeys: window.DOMAIN_DEFS.map(d => d.key),
  initialDom,
  pillsHtml,
  byDom,
  normTests: {
    ash: window.normalizeDomainKey("Ash"),
    xrf: window.normalizeDomainKey("XRF Elemental Analysis"),
    icp: window.normalizeDomainKey("ICP Elemental Analysis"),
    elemental: window.normalizeDomainKey("elemental"),
    calXrd: window.normalizeDomainKey("calorimetry_xrd"),
    xrd: window.normalizeDomainKey("XRD Crystallinity"),
    ferm: window.normalizeDomainKey("Fermentation (Bioconversion)")
  }
}));
""",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [node_bin, str(harness_js)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"Node harness failed: {proc.stderr}"
    out = json.loads(proc.stdout.strip().splitlines()[-1])

    assert out["domainKeys"] == [
        "proximate",
        "calorimetry",
        "compositional",
        "ultimate",
        "xrd",
        "icp",
        "xrf",
        "pretreatment",
        "fermentation",
        "gasification",
    ]
    assert out["initialDom"] == "calorimetry"
    assert out["normTests"] == {
        "ash": "xrf",
        "xrf": "xrf",
        "icp": "icp",
        "elemental": "icp",
        "calXrd": "calorimetry",
        "xrd": "xrd",
        "ferm": "fermentation",
    }
    # Compositional, Ultimate, and XRD are cleanly separated even though they share by_tab.compositional
    assert out["byDom"]["compositional"]["groups"] == ["Glucan"]
    assert out["byDom"]["ultimate"]["groups"] == ["Carbon"]
    assert out["byDom"]["xrd"]["groups"] == ["Crystallinity"]
    assert out["byDom"]["proximate"]["groups"] == ["Ash"]
    assert out["byDom"]["calorimetry"]["groups"] == ["HHV"]
    assert out["byDom"]["icp"]["groups"] == ["Ca"]
    assert out["byDom"]["xrf"]["groups"] == ["K"]
    assert len(out["byDom"]["all"]["groups"]) == 7
    assert "type=xrd" in out["byDom"]["xrd"]["navExplorerHref"]


def test_card5a_default_in_review_status_and_assignee_persistence(
    snapshot_and_pages: dict[str, str], tmp_path: Path
) -> None:
    """Verify Card 5a defaults to provisional/keep_note/in_review across all 4 surfaces and persists assignee emails on Pages 2 & 3."""
    from analysis.metadata.resource_audit_workbench import (
        build_resource_audit_workbench,
    )

    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("node binary not available")

    page1_html = snapshot_and_pages["page1"]
    page2_html = snapshot_and_pages["page2"]
    page3_html = snapshot_and_pages["page3"]
    wb_path = tmp_path / "wb_card5a.html"
    build_resource_audit_workbench(snapshot_path=SNAPSHOT_PATH, output_path=wb_path)
    wb_html = wb_path.read_text(encoding="utf-8")

    # 1. Verify HTML dropdown defaults across Shared Modal (Pages 1-3), Page 3 Popover & Pinned Inspector, and Product 4 Drawer
    modal_sel = re.search(
        r'<select id="finding-modal-qc-status"[^>]*>\s*<option value="([^"]+)" selected>',
        page1_html,
    )
    assert modal_sel and modal_sel.group(1) == "provisional"

    pop_sel = re.search(
        r'<select id="click-popover-action"[^>]*>\s*<option value="([^"]+)" selected>',
        page3_html,
    )
    assert pop_sel and pop_sel.group(1) == "keep_note"
    assert 'id="click-popover-assignee"' in page3_html

    pin_sel = re.search(
        r'<select id="pin-audit-action"[^>]*>\s*<option value="([^"]+)" selected>',
        page3_html,
    )
    assert pin_sel and pin_sel.group(1) == "keep_note"
    assert 'id="pin-audit-assignee"' in page3_html
    assert "(document.getElementById('click-popover-action') || {}).value || 'keep_note'" in page3_html
    assert "(document.getElementById('pin-audit-action') || {}).value || 'keep_note'" in page3_html
    assert "default_qc_status: 'provisional'" in page3_html
    assert "assigned_to_email: cleanAssignee" in page3_html

    wb_sel = re.search(
        r'<select id="select-decision-action"[^>]*>\s*<option value="([^"]+)" selected>',
        wb_html,
    )
    assert wb_sel and wb_sel.group(1) == "in_review"

    # 2. Execute Page 2 + Shared Modal JS in Node to verify default status & Page 2 assignee persistence
    m_p2_script = re.search(
        r"<script>\s*(const BUNDLE = .*?)</script>", page2_html, flags=re.S
    )
    assert m_p2_script
    p2_script = m_p2_script.group(1)

    p2_harness = tmp_path / "run_card5a_p2.js"
    p2_harness.write_text(
        """
const elements = {};
function makeEl(id) {
  return {
    id, value: "", textContent: "", innerHTML: "", className: "", style: {}, dataset: {},
    options: [{ value: "provisional" }, { value: "fail" }, { value: "pass" }, { value: "re_assay" }],
    classList: { add(){}, remove(){}, toggle(){}, contains(){ return false; } },
    addEventListener(ev, fn){ this["_on_" + ev] = fn; },
    removeEventListener(){}, setAttribute(){}, getAttribute(){ return null; },
    appendChild(){}, querySelectorAll(){ return []; }, focus(){}, setSelectionRange(){}
  };
}
const storage = {};
global.localStorage = {
  getItem(k){ return Object.prototype.hasOwnProperty.call(storage, k) ? storage[k] : null; },
  setItem(k, v){ storage[k] = String(v); },
  removeItem(k){ delete storage[k]; }
};
const listeners = {};
global.window = {
  location: { href: "http://localhost:8000/v1/dashboards/metadata/resource_qc_outlier_dashboard.html", search: "", origin: "http://localhost:8000", pathname: "/v1/dashboards/metadata/resource_qc_outlier_dashboard.html", protocol: "http:" },
  history: { replaceState(){} },
  addEventListener(ev, fn){ (listeners[ev] = listeners[ev] || []).push(fn); },
  dispatchEvent(ev){ (listeners[ev.type] || []).forEach(fn => fn(ev)); }
};
global.CustomEvent = function(type, init) { this.type = type; this.detail = init && init.detail; };
global.document = {
  documentElement: { getAttribute(){ return "dark"; }, setAttribute(){} },
  body: makeEl("body"),
  getElementById(id) { if (!elements[id]) elements[id] = makeEl(id); return elements[id]; },
  querySelectorAll(){ return []; },
  createElement(t){ return makeEl(t); }
};
const apiCalls = [];
let nextApiId = 500;
global.fetch = async (url, opts) => {
  const method = (opts && opts.method) || "GET";
  const body = (opts && opts.body) ? JSON.parse(opts.body) : null;
  apiCalls.push({ url, method, body });
  if (String(url).includes("/v1/qc/decisions/") && String(url).endsWith("/assign")) {
    return {
      ok: true,
      status: 200,
      json: async () => ({
        status: "ok",
        decision: { id: 500, assigned_to_email: body.assigned_to_email, decision_status: "in_review" }
      })
    };
  }
  if (String(url).endsWith("/v1/qc/decisions") && method === "POST") {
    const id = body.id || (++nextApiId);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        status: "ok",
        decision: {
          id,
          record_id: body.record_id,
          replicate_group_key: body.replicate_group_key,
          resource_name: body.resource_name,
          analysis_type: body.analysis_type,
          parameter_name: body.parameter_name,
          decision_action: body.decision_action,
          decision_status: body.decision_status,
          new_qc_pass: body.new_qc_pass,
          assigned_to_email: body.assigned_to_email,
          review_note: body.review_note
        }
      })
    };
  }
  return { ok: false, status: 404, json: async () => ({}) };
};
"""
        + p2_script
        + """
(async () => {
  // 1. Open shared finding modal with empty payload and verify default status is "provisional"
  window.openSubmitFindingModal({ resource_name: "almond hulls", parameter_name: "Ash", record_id: "rec-901" });
  const modalDefaultQc = document.getElementById("finding-modal-qc-status").value;

  // 2. Submit a finding with default provisional status and assignee email
  const findingRes = await window.BioCirvQcClient.submitFinding({
    scope: "replicate_group",
    resource_name: "almond hulls",
    analysis_type: "proximate",
    parameter_name: "Ash",
    record_id: "rec-901",
    target_record_ids: ["rec-901", "rec-902"],
    new_qc_status: modalDefaultQc,
    assigned_to_email: "Reviewer1@lbl.gov",
    audit_note: "Default provisional check"
  });

  // 3. Test Page 2 inline triage row: set assignee first, then change decision, then update assignee
  const metaObj = {
    scope: "replicate_group",
    replicate_group_key: "almond hulls::ah-01::proximate::moisture::oven::exp-1",
    resource_name: "almond hulls",
    analysis_type: "proximate",
    prepared_sample: "AH-01",
    experiment: "EXP-1",
    parameter: "Moisture",
    record_id: "rec-910",
    record_ids: "rec-910|rec-911"
  };
  const encodedMeta = encodeURIComponent(JSON.stringify(metaObj));
  const rowKey = "grp::almond hulls::ah-01::proximate::moisture::oven::exp-1";

  window.handleDecisionAssignee(rowKey, "pi.reviewer@lbl.gov", encodedMeta);
  await new Promise(r => setTimeout(r, 20));
  window.handleDecisionChange(rowKey, "accept_with_note", encodedMeta);
  await new Promise(r => setTimeout(r, 20));
  const afterDecisionEntry = JSON.parse(global.localStorage.getItem("biocirv_qc_decisions_v1"))[rowKey];

  window.handleDecisionAssignee(rowKey, "lead.analyst@lbl.gov", encodedMeta);
  await new Promise(r => setTimeout(r, 20));
  const afterReassignEntry = JSON.parse(global.localStorage.getItem("biocirv_qc_decisions_v1"))[rowKey];

  console.log(JSON.stringify({
    modalDefaultQc,
    findingSubmittedBody: apiCalls[0].body,
    findingDecision: findingRes.decision,
    afterDecisionEntry,
    afterReassignEntry,
    apiCalls
  }));
  process.exit(0);
})();
""",
        encoding="utf-8",
    )
    proc_p2 = subprocess.run(
        [node_bin, str(p2_harness)],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert proc_p2.returncode == 0, f"Page 2 Node harness failed: {proc_p2.stderr}"
    out_p2 = json.loads(proc_p2.stdout.strip().splitlines()[-1])

    assert out_p2["modalDefaultQc"] == "provisional"
    post_calls = [c for c in out_p2["apiCalls"] if c["method"] == "POST"]
    assert len(post_calls) >= 1
    first_post_body = post_calls[0]["body"]
    assert first_post_body["decision_action"] == "in_review"
    assert first_post_body["decision_status"] == "in_review"
    assert first_post_body["new_qc_pass"] is None
    assert first_post_body["new_qc_status"] == "provisional"
    assert first_post_body["decision"] == "accept_with_note"
    assert first_post_body["assigned_to_email"] == "reviewer1@lbl.gov"

    assert out_p2["afterDecisionEntry"]["decision"] == "accept_with_note"
    assert out_p2["afterDecisionEntry"]["assigned_to_email"] == "pi.reviewer@lbl.gov"
    assert out_p2["afterDecisionEntry"]["api_decision_id"] is not None

    assert out_p2["afterReassignEntry"]["assigned_to_email"] == "lead.analyst@lbl.gov"
    assign_patch_calls = [
        c for c in out_p2["apiCalls"] if c["method"] == "PATCH" and "/assign" in c["url"]
    ]
    assert len(assign_patch_calls) >= 1
    assert assign_patch_calls[-1]["body"]["assigned_to_email"] == "lead.analyst@lbl.gov"
