"""Unit tests for BioCirV dashboard qc_pass defaults, leak-free collaborator slice export, and GitHub bug links."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from analysis.metadata.resource_analysis_dashboard import (
    GITHUB_ISSUES_NEW_URL,
    _normalize_qc_statuses,
    build_analysis_dashboard_html,
    build_collaborator_slice_html,
    build_github_bug_issue_url,
    build_qc_outlier_dashboard_html,
    prepare_dashboard_payload,
)
from analysis.metadata.resource_explorer_dashboard import (
    build_full_dashboard_html,
    build_quick_widget_html,
)


@pytest.fixture()
def sample_raw_payload() -> dict:
    """Create a multi-resource dictionary-encoded payload with pass, fail, and provisional rows."""
    str_cols = [
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
    ]
    dicts = {
        "resource_name": ["almond hulls", "wheat straw"],
        "analysis_type": ["Proximate Analysis", "Fermentation (Bioconversion)"],
        "prepared_sample": ["AH-PS-01", "WS-PS-99"],
        "field_sample": ["AH-FS-01", "WS-FS-99"],
        "provider": ["capstan", "vibrant"],
        "prep_method": ["milling_2mm"],
        "experiment": ["EXP-001", "EXP-999"],
        "analyst": ["alice@lbl.gov", "bob@ucdavis.edu"],
        "qc_status": ["pass", "fail", "provisional"],
        "pt_method": ["N/A"],
        "eh_method": ["N/A"],
        "vessel": ["N/A"],
        "strain": ["N/A"],
        "bioconv": ["N/A"],
        "well_or_block": [""],
        "parameter": ["moisture", "ash"],
        "unit": ["%"],
        "note": ["Almond hull normal note", "Almond hull outlier note", "Secret wheat straw note"],
    }
    # Row layout: [record_id, *str_col_indices (18), replicate, value]
    rows = [
        # Almond hulls - pass
        ["REC-AH-1", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 12.4],
        # Almond hulls - fail
        ["REC-AH-2", 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 48.9],
        # Almond hulls - provisional (unscored)
        ["REC-AH-3", 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 6.1],
        # Wheat straw - pass (must never leak into almond hulls slice)
        ["REC-WS-1", 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 8.3],
    ]
    return {
        "generated_utc": "2026-10-16T00:00:00Z",
        "excluded_resources": [],
        "excluded_providers": ["jaguar"],
        "str_cols": str_cols,
        "dicts": dicts,
        "rows": rows,
        "resources": [
            {"id": 1, "name": "almond hulls", "primary_ag_product": "almonds"},
            {"id": 2, "name": "wheat straw", "primary_ag_product": "wheat"},
        ],
        "field_samples": [
            {
                "id": 10,
                "name": "AH-FS-01",
                "resource_name": "almond hulls",
                "provider_code": "capstan",
                "geoid": "06099",
                "collected_at": "2025-09-10",
            },
            {
                "id": 20,
                "name": "WS-FS-99",
                "resource_name": "wheat straw",
                "provider_code": "vibrant",
                "geoid": "06113",
                "collected_at": "2026-01-20",
            },
        ],
        "prepared_samples": [
            {
                "id": 100,
                "name": "AH-PS-01",
                "field_sample_name": "AH-FS-01",
                "resource_name": "almond hulls",
                "preparer": "alice@lbl.gov",
                "prep_date": "2025-10-05",
            },
            {
                "id": 200,
                "name": "WS-PS-99",
                "field_sample_name": "WS-FS-99",
                "resource_name": "wheat straw",
                "preparer": "bob@ucdavis.edu",
                "prep_date": "2026-02-14",
            },
        ],
        "county_lookup": {"06099": "Stanislaus", "06113": "Yolo"},
    }


@pytest.fixture()
def sample_insights_sidecar() -> dict:
    """Create a multi-resource insights sidecar."""
    return {
        "catalog_medians": {"moisture": 10.0},
        "resources": {
            "almond hulls": {"executive_summary": "Almond hulls summary", "qc_health": {"score": 95}},
            "wheat straw": {"executive_summary": "Confidential wheat straw summary", "qc_health": {"score": 88}},
        },
    }


def test_normalize_qc_statuses() -> None:
    assert _normalize_qc_statuses(None) is None
    assert _normalize_qc_statuses("all") is None
    assert _normalize_qc_statuses("pass") == {"pass"}
    assert _normalize_qc_statuses(["pass", "fail"]) == {"pass", "fail"}
    unscored = _normalize_qc_statuses(["unscored"])
    assert unscored is not None
    assert {"unscored", "provisional", "unknown", ""}.issubset(unscored)


def test_dashboards_default_to_qc_pass_only(
    sample_raw_payload: dict, sample_insights_sidecar: dict
) -> None:
    bundle = prepare_dashboard_payload(sample_raw_payload, sample_insights_sidecar)
    p1_html = build_analysis_dashboard_html(bundle)
    p2_html = build_qc_outlier_dashboard_html(bundle)
    p3_html = build_full_dashboard_html(sample_raw_payload)

    assert '(urlParams.get("qc") || "pass")' in p1_html
    assert 'state.qc_status = "pass"' in p1_html
    assert 'urlParams.get("portal_qc") || "qc_pass"' in p2_html
    assert '<option value="qc_pass" selected>qc_pass: pass</option>' in p3_html

    for doc in (p1_html, p2_html, p3_html):
        assert "pretreatment_variance_dashboard.html" not in doc
        assert "resource_analysis_dashboard_v1_monolith.html" not in doc
        assert "4. DB Environment Drift" in doc


def test_collaborator_slice_isolation_and_provider_codename_preservation(
    sample_raw_payload: dict, sample_insights_sidecar: dict
) -> None:
    # 1. Default slice (qc_pass = pass only)
    slice_pass = prepare_dashboard_payload(
        sample_raw_payload,
        sample_insights_sidecar,
        single_resource="almond hulls",
        qc_statuses=["pass"],
        exclude_analyst=True,
    )
    assert slice_pass["collaborator_slice_mode"] is True
    assert slice_pass["single_resource"] == "almond hulls"
    assert slice_pass["slice_resources"] == ["almond hulls"]
    assert len(slice_pass["rows"]) == 1
    assert slice_pass["rows"][0][0] == "REC-AH-1"

    # Verify dictionary compaction: zero wheat straw strings anywhere in dicts or payload
    assert slice_pass["dicts"]["resource_name"] == ["almond hulls"]
    assert slice_pass["dicts"]["prepared_sample"] == ["AH-PS-01"]
    assert slice_pass["dicts"]["field_sample"] == ["AH-FS-01"]
    assert slice_pass["dicts"]["qc_status"] == ["pass"]
    # Provider codenames are already anonymous and must be preserved as-is
    assert slice_pass["dicts"]["provider"] == ["capstan"]
    assert slice_pass["field_samples"][0]["provider_code"] == "capstan"
    # Analyst emails are masked when exclude_analyst=True
    assert slice_pass["dicts"]["analyst"] == ["—"]
    assert slice_pass["prepared_samples"][0]["preparer"] == "—"

    serialized_pass = json.dumps(slice_pass).lower()
    assert "wheat straw" not in serialized_pass
    assert "ws-ps-99" not in serialized_pass
    assert "ws-fs-99" not in serialized_pass
    assert "secret wheat straw note" not in serialized_pass
    assert "alice@lbl.gov" not in serialized_pass
    assert "bob@ucdavis.edu" not in serialized_pass

    # 2. Multi-status slice (pass + fail + unscored/provisional)
    slice_all_qc = prepare_dashboard_payload(
        sample_raw_payload,
        sample_insights_sidecar,
        single_resource="almond hulls",
        qc_statuses=["pass", "fail", "unscored"],
        exclude_analyst=True,
    )
    assert len(slice_all_qc["rows"]) == 3
    rec_ids = [r[0] for r in slice_all_qc["rows"]]
    assert rec_ids == ["REC-AH-1", "REC-AH-2", "REC-AH-3"]
    assert "wheat straw" not in json.dumps(slice_all_qc).lower()

    # 3. Full HTML slice export check
    slice_html = build_collaborator_slice_html(
        sample_raw_payload,
        sample_insights_sidecar,
        resource_name="almond hulls",
        qc_statuses=["pass"],
        exclude_analyst=True,
    )
    assert "wheat straw" not in slice_html.lower()
    assert "ws-ps-99" not in slice_html.lower()
    assert "capstan" in slice_html


def test_multi_resource_slice_and_filter_reflection(
    sample_raw_payload: dict, sample_insights_sidecar: dict
) -> None:
    # Multi-resource slice with both almond hulls and wheat straw
    multi_slice = prepare_dashboard_payload(
        sample_raw_payload,
        sample_insights_sidecar,
        resources=["almond hulls", "wheat straw"],
        qc_statuses=["pass"],
        slice_pages=["char", "explorer"],
        exclude_analyst=True,
    )
    assert multi_slice["collaborator_slice_mode"] is True
    assert multi_slice["single_resource"] is None
    assert set(multi_slice["slice_resources"]) == {"almond hulls", "wheat straw"}
    assert multi_slice["slice_pages"] == ["char", "explorer"]
    assert len(multi_slice["rows"]) == 2
    assert {r[0] for r in multi_slice["rows"]} == {"REC-AH-1", "REC-WS-1"}

    # Parameter filter reflection: restrict to 'ash' (only REC-AH-3 has ash, under provisional QC)
    ash_only_slice = prepare_dashboard_payload(
        sample_raw_payload,
        sample_insights_sidecar,
        resources=["almond hulls", "wheat straw"],
        qc_statuses=["pass", "unscored"],
        parameters=["ash"],
        exclude_analyst=True,
    )
    assert len(ash_only_slice["rows"]) == 1
    assert ash_only_slice["rows"][0][0] == "REC-AH-3"
    assert ash_only_slice["dicts"]["parameter"] == ["ash"]
    assert ash_only_slice["slice_filters"]["parameters"] == ["ash"]

    # Prepared sample filter reflection: both selected resources remain in dicts.resource_name even if 1 has 0 rows
    ps_slice = prepare_dashboard_payload(
        sample_raw_payload,
        sample_insights_sidecar,
        resources=["almond hulls", "wheat straw"],
        qc_statuses=["pass"],
        prepared_samples=["WS-PS-99"],
        exclude_analyst=True,
    )
    assert len(ps_slice["rows"]) == 1
    assert ps_slice["rows"][0][0] == "REC-WS-1"
    assert set(ps_slice["dicts"]["resource_name"]) == {"almond hulls", "wheat straw"}
    # Verify row resource_name index still maps to 'wheat straw'
    assert ps_slice["dicts"]["resource_name"][ps_slice["rows"][0][1]] == "wheat straw"


def test_date_range_filtering_and_modal_closed_on_open(
    sample_raw_payload: dict, sample_insights_sidecar: dict
) -> None:
    # Filter by Collection Date in 2025 -> only AH-FS-01 (2025-09-10) matches
    col_2025 = prepare_dashboard_payload(
        sample_raw_payload,
        sample_insights_sidecar,
        qc_statuses=["pass"],
        date_type="collected",
        from_date="2025-01-01",
        to_date="2025-12-31",
    )
    assert col_2025["collaborator_slice_mode"] is True
    assert len(col_2025["rows"]) == 1
    assert col_2025["rows"][0][0] == "REC-AH-1"
    assert col_2025["slice_filters"]["date_type"] == "collected"
    assert col_2025["slice_filters"]["from_date"] == "2025-01-01"
    assert col_2025["slice_filters"]["to_date"] == "2025-12-31"
    assert col_2025["slice_date_type"] == "collected"
    assert col_2025["slice_from_date"] == "2025-01-01"
    assert col_2025["slice_to_date"] == "2025-12-31"

    # Filter by Run / Prep Date in 2026 -> only WS-PS-99 (2026-02-14) matches
    run_2026 = prepare_dashboard_payload(
        sample_raw_payload,
        sample_insights_sidecar,
        qc_statuses=["pass"],
        date_type="run",
        from_date="2026-01-01",
        to_date="2026-12-31",
    )
    assert len(run_2026["rows"]) == 1
    assert run_2026["rows"][0][0] == "REC-WS-1"

    # Verify HTML slice has Export Slice modal hidden by default and includes page checkboxes & date controls
    slice_html = build_collaborator_slice_html(
        sample_raw_payload,
        sample_insights_sidecar,
        resources=["almond hulls", "wheat straw"],
        qc_statuses=["pass"],
        slice_pages=["char", "explorer"],
    )
    assert 'id="modal-export-slice" class="fixed inset-0 z-50 hidden' in slice_html
    assert 'id="slice-page-char"' in slice_html
    assert 'id="slice-page-explorer"' in slice_html
    assert 'id="slice-page-qc"' in slice_html
    assert 'id="flt-date-type"' in slice_html
    assert 'id="flt-from-date"' in slice_html
    assert 'id="flt-to-date"' in slice_html
    assert 'id="slice-date-type"' in slice_html
    assert 'id="slice-from-date"' in slice_html
    assert 'id="slice-to-date"' in slice_html

    # Verify Page 3 (Multi-Resource Explorer) has date range filters and Collection/Run Dates X-axis layout mode
    p3_html = build_full_dashboard_html(sample_raw_payload)
    assert 'id="filter-date-type"' in p3_html
    assert 'id="filter-from-date"' in p3_html
    assert 'id="filter-to-date"' in p3_html
    assert 'id="btn-xlayout-dates"' in p3_html


def test_build_github_bug_issue_url() -> None:
    url = build_github_bug_issue_url(
        title="Dixon Q badge clipping on narrow viewport",
        category="UI / Chart Rendering Bug",
        description="When opening Page 2 on 1280px screen, badge wraps.",
        expected_behavior="Badge stays inline.",
        page="Page 2 — Statistical QC & Lab Notes Audit",
        resource="almond hulls",
        domain_tab="proximate",
        qc_filter="qc_pass",
        query_string="?resource=almond+hulls",
        reporter_email="analyst@lbl.gov",
    )
    assert url.startswith(GITHUB_ISSUES_NEW_URL + "?")
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert qs["title"] == ["Dixon Q badge clipping on narrow viewport"]
    assert qs["labels"] == ["bug,dashboard-qc"]
    body = qs["body"][0]
    assert "Page 2 — Statistical QC & Lab Notes Audit" in body
    assert "`almond hulls`" in body
    assert "`proximate`" in body
    assert "`qc_pass`" in body
    assert "`analyst@lbl.gov`" in body


def test_page2_review_queue_triage_and_email_assignment(
    sample_raw_payload: dict, sample_insights_sidecar: dict
) -> None:
    bundle = prepare_dashboard_payload(sample_raw_payload, sample_insights_sidecar)
    p2_html = build_qc_outlier_dashboard_html(bundle)

    # Dedicated 5th sub-tab for Review Queue & Audit Ledger
    assert 'data-subtab="review_queue"' in p2_html
    assert "5. Review Queue &amp; Audit Ledger" in p2_html
    assert "renderReviewQueueSubtab" in p2_html

    # Single-Record vs. Whole-Replicate-Group triage selector
    assert "Whole Replicate Group" in p2_html
    assert "Single Candidate Outlier" in p2_html
    assert "window.handleDecisionScope = function" in p2_html

    # Email assignment controls and filters
    assert "window.handleDecisionAssignee = function" in p2_html
    assert "window.assignQueueEntryEmail = function" in p2_html
    assert "Assigned to Me" in p2_html

    # Live approve & sync + revert handlers
    assert "window.approveAndSyncDecision = async function" in p2_html
    assert "window.revertQueueItemByKey = async function" in p2_html
    assert "window.batchApproveFilteredQueue = async function" in p2_html


def test_inject_sliced_bundle_and_append_bundled_pages_no_body_truncation(
    sample_raw_payload: dict, sample_insights_sidecar: dict, tmp_path: Path
) -> None:
    """Simulate client-side slice export and verify no </body> truncation inside <script> and full resource preservation."""
    import re
    import shutil
    import subprocess

    # Include dollar replacement patterns ($&, $', $1) and closing tag sequences in a note to test escaping
    raw_copy = json.loads(json.dumps(sample_raw_payload))
    raw_copy["dicts"]["note"][0] = "Cost $100 & $& pattern $' $1 </script> </body> end"
    raw_copy["dicts"]["note"][2] = "Cost $100 & $& pattern $' $1 </script> </body> end"

    base_bundle = prepare_dashboard_payload(raw_copy, sample_insights_sidecar)
    p1_html = build_analysis_dashboard_html(base_bundle)
    p2_html = build_qc_outlier_dashboard_html(base_bundle)
    p3_html = build_full_dashboard_html(base_bundle)

    for label, html_doc in [("char", p1_html), ("qc", p2_html), ("explorer", p3_html)]:
        # Exactly one </body> tag in the entire document, located right before </html>
        body_matches = [m.start() for m in re.finditer(r"</body>", html_doc, flags=re.IGNORECASE)]
        assert len(body_matches) == 1, f"Expected 1 </body> tag in {label}, found {len(body_matches)}"
        assert body_matches[0] > len(html_doc) - 60, f"</body> tag in {label} is not at the end of document"

    node_bin = shutil.which("node")
    assert node_bin is not None, "node binary required to execute client-side slice JS functions"

    from analysis.metadata.resource_analysis_dashboard import SHARED_SLICE_AND_BUG_MODALS_JS

    js_harness = (
        'const window = { location: { search: "", protocol: "file:" }, addEventListener: () => {} };\n'
        'const document = { getElementById: () => null, addEventListener: () => {}, querySelectorAll: () => [], readyState: "complete" };\n'
        + SHARED_SLICE_AND_BUG_MODALS_JS
        + """
const fs = require("fs");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const baseBundle = input.baseBundle;
const pages = input.pages;

// Slice with both resources selected, but extra filter preparedSamples=['WS-PS-99'] so 'almond hulls' has 0 rows
const slicedBundle = window.buildClientSideSlicedBundle(
  baseBundle,
  ["almond hulls", "wheat straw"],
  ["pass"],
  true,
  { preparedSamples: ["WS-PS-99"], dateType: "run", fromDate: "2026-01-01", toDate: "2026-12-31" },
  ["char", "qc", "explorer"]
);

const defaultRes = slicedBundle.slice_resources[0];
const pagesMap = {
  char: window.injectSlicedBundleIntoHtml(pages.char, slicedBundle, defaultRes),
  qc: window.injectSlicedBundleIntoHtml(pages.qc, slicedBundle, defaultRes),
  explorer: window.injectSlicedBundleIntoHtml(pages.explorer, slicedBundle, defaultRes),
};
const finalCharDoc = window.appendBundledPagesScript(pagesMap.char, pagesMap);
const finalExplorerDoc = window.appendBundledPagesScript(pagesMap.explorer, pagesMap);

function evalPage1ActiveResources(BUNDLE) {
  const ALL_RECORDS = BUNDLE.rows.map(arr => ({
    resource_name: BUNDLE.dicts.resource_name[arr[1]]
  }));
  const RECORDS_BY_RESOURCE = {};
  ALL_RECORDS.forEach(r => {
    if (!RECORDS_BY_RESOURCE[r.resource_name]) RECORDS_BY_RESOURCE[r.resource_name] = [];
    RECORDS_BY_RESOURCE[r.resource_name].push(r);
  });
  if (BUNDLE.collaborator_slice_mode || (BUNDLE.slice_resources && BUNDLE.slice_resources.length > 0)) {
    const sliceResCandidates = [].concat(
      BUNDLE.dicts && BUNDLE.dicts.resource_name ? BUNDLE.dicts.resource_name : [],
      BUNDLE.slice_resources || []
    );
    const knownByLower = {};
    Object.keys(RECORDS_BY_RESOURCE).forEach(k => { knownByLower[k.trim().toLowerCase()] = k; });
    sliceResCandidates.forEach(sr => {
      const s = String(sr || "").trim();
      if (!s) return;
      const low = s.toLowerCase();
      const canon = knownByLower[low] || s;
      if (!RECORDS_BY_RESOURCE[canon]) RECORDS_BY_RESOURCE[canon] = [];
      knownByLower[low] = canon;
    });
  }
  return Object.keys(RECORDS_BY_RESOURCE);
}

function evalPage3ActiveResources(RAW_DATA) {
  const ALL_ROWS = RAW_DATA.rows.map(arr => ({
    resource_name: RAW_DATA.dicts.resource_name[arr[1]]
  }));
  const RESOURCE_COUNTS = {};
  ALL_ROWS.forEach(r => {
    if (r.resource_name && r.resource_name !== "Unassigned") {
      RESOURCE_COUNTS[r.resource_name] = (RESOURCE_COUNTS[r.resource_name] || 0) + 1;
    }
  });
  if (RAW_DATA.collaborator_slice_mode || (RAW_DATA.slice_resources && RAW_DATA.slice_resources.length > 0)) {
    const sliceResCandidates = [].concat(
      RAW_DATA.dicts && RAW_DATA.dicts.resource_name ? RAW_DATA.dicts.resource_name : [],
      RAW_DATA.slice_resources || []
    );
    const knownByLower = {};
    Object.keys(RESOURCE_COUNTS).forEach(k => { knownByLower[k.trim().toLowerCase()] = k; });
    sliceResCandidates.forEach(sr => {
      const s = String(sr || "").trim();
      if (!s || s === "Unassigned") return;
      const low = s.toLowerCase();
      const canon = knownByLower[low] || s;
      if (RESOURCE_COUNTS[canon] === undefined) RESOURCE_COUNTS[canon] = 0;
      knownByLower[low] = canon;
    });
  }
  return Object.keys(RESOURCE_COUNTS);
}

process.stdout.write(JSON.stringify({
  slicedBundle,
  finalCharDoc,
  finalExplorerDoc,
  p1Active: evalPage1ActiveResources(slicedBundle),
  p3Active: evalPage3ActiveResources(slicedBundle),
}));
"""
    )
    harness_path = tmp_path / "harness.js"
    harness_path.write_text(js_harness, encoding="utf-8")
    proc = subprocess.run(
        [node_bin, str(harness_path)],
        input=json.dumps(
            {
                "baseBundle": base_bundle,
                "pages": {"char": p1_html, "qc": p2_html, "explorer": p3_html},
            }
        ),
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    assert proc.returncode == 0, f"Node harness failed: {proc.stderr}"
    res = json.loads(proc.stdout)
    sliced_bundle = res["slicedBundle"]

    # Both selected resources must be in slice_resources, dicts.resource_name, and ACTIVE_RESOURCES
    assert set(sliced_bundle["slice_resources"]) == {"almond hulls", "wheat straw"}
    assert set(sliced_bundle["dicts"]["resource_name"]) == {"almond hulls", "wheat straw"}
    assert set(res["p1Active"]) == {"almond hulls", "wheat straw"}
    assert set(res["p3Active"]) == {"almond hulls", "wheat straw"}
    assert sliced_bundle["slice_date_type"] == "run"
    assert sliced_bundle["slice_from_date"] == "2026-01-01"
    assert sliced_bundle["slice_to_date"] == "2026-12-31"

    for doc_label, orig_doc, final_doc in [
        ("char", p1_html, res["finalCharDoc"]),
        ("explorer", p3_html, res["finalExplorerDoc"]),
    ]:
        body_positions = [m.start() for m in re.finditer(r"</body>", final_doc, flags=re.IGNORECASE)]
        assert len(body_positions) == 1, f"{doc_label} exported slice has {len(body_positions)} </body> tags"
        assert body_positions[0] > len(final_doc) - 60, f"{doc_label} </body> tag was not at end of document"
        assert '<script id="biocirv-bundled-slice-pages" type="application/json">' in final_doc
        # Verify the bundled pages script is placed at the end of the page immediately after </script> and before </body>
        bundled_pos = final_doc.index('<script id="biocirv-bundled-slice-pages"')
        assert bundled_pos > len(orig_doc) - 2000, (
            f"{doc_label} bundled script inserted too early ({bundled_pos} vs {len(orig_doc)})"
        )
        assert final_doc[:bundled_pos].rstrip().endswith("</script>")
        # Verify special regex replacement tokens ($&, $', $1) in notes were preserved without corruption
        assert "Cost $100 & $& pattern $' $1 <\\/script> <\\/body> end" in final_doc


def test_issue_515_date_filtering_and_default_start_date(
    sample_raw_payload: dict,
    sample_insights_sidecar: dict,
    tmp_path: Path,
) -> None:
    """Verify Issue #515 fix: date filtering works on all pages, auto-orders inverted ranges, and defaults start date to 2024-01-01."""
    import shutil
    import subprocess

    from analysis.metadata.resource_analysis_dashboard import SHARED_SLICE_AND_BUG_MODALS_JS

    # 1. Python slice filtering with inverted date range (from_date > to_date, as in Issue #515 URL)
    sliced_inverted = prepare_dashboard_payload(
        sample_raw_payload,
        sample_insights_sidecar,
        resources=["almond hulls", "wheat straw"],
        qc_statuses=["pass", "fail", "unscored"],
        date_type="run",
        from_date="2026-04-01",
        to_date="2026-02-01",
    )
    assert len(sliced_inverted["rows"]) > 0, "Inverted date range should auto-normalize instead of returning 0 rows"
    assert sliced_inverted["slice_from_date"] == "2026-02-01"
    assert sliced_inverted["slice_to_date"] == "2026-04-01"

    # 2. Verify HTML date inputs have default start date 2024-01-01 support and clear buttons
    base_bundle = prepare_dashboard_payload(sample_raw_payload, sample_insights_sidecar)
    p1_html = build_analysis_dashboard_html(base_bundle)
    p2_html = build_qc_outlier_dashboard_html(base_bundle)
    p3_html = build_full_dashboard_html(base_bundle)

    for html_doc in (p1_html, p2_html):
        assert 'DEFAULT_FILTER_START_DATE = "2024-01-01"' in html_doc
        assert 'placeholder="2024-01-01"' in html_doc
        assert 'id="flt-date-clear"' in html_doc
        assert "window.recordMatchesDateFilter" in html_doc

    assert 'placeholder="2024-01-01"' in p3_html
    assert "onFromDateFocus(this)" in p3_html
    assert 'id="filter-date-clear"' in p3_html
    assert "function recordMatchesDateFilter(" in p3_html
    assert "function normalizeExplorerDateRange(" in p3_html

    # 3. Execute JS recordMatchesDateFilter via Node on normal and inverted ranges
    node_bin = shutil.which("node")
    assert node_bin is not None
    js_test = (
        'const window = { location: { search: "", protocol: "file:" }, addEventListener: () => {} };\n'
        'const document = { getElementById: () => null, addEventListener: () => {}, querySelectorAll: () => [], readyState: "complete" };\n'
        + SHARED_SLICE_AND_BUG_MODALS_JS
        + """
const rec = {
  record_id: "rec-1",
  collected_date: "2024-11-15",
  exp_date: "2025-01-20",
  prep_date: "2025-01-20"
};
const undatedRec = {
  record_id: "rec-2",
  collected_date: "Undated",
  exp_date: "Unrecorded",
  prep_date: "Undated"
};

const results = {
  defaultStart: window.DEFAULT_PICKER_START_DATE,
  matchRunNormal: window.recordMatchesDateFilter(rec, "run", "2024-10-01", "2025-02-11"),
  matchRunInverted: window.recordMatchesDateFilter(rec, "run", "2025-02-11", "2024-10-01"),
  matchRunOutside: window.recordMatchesDateFilter(rec, "run", "2025-03-01", "2025-04-01"),
  matchCollected: window.recordMatchesDateFilter(rec, "collected", "2024-01-01", "2024-12-31"),
  matchUndatedWhenFiltered: window.recordMatchesDateFilter(undatedRec, "any", "2024-01-01", "2025-12-31"),
  matchUndatedWhenEmpty: window.recordMatchesDateFilter(undatedRec, "any", "", ""),
};
process.stdout.write(JSON.stringify(results));
"""
    )
    script_file = tmp_path / "date_test.js"
    script_file.write_text(js_test, encoding="utf-8")
    proc = subprocess.run(
        [node_bin, str(script_file)],
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    assert proc.returncode == 0, f"Node date test failed: {proc.stderr}"
    out = json.loads(proc.stdout)
    assert out["defaultStart"] == "2024-01-01"
    assert out["matchRunNormal"] is True
    assert out["matchRunInverted"] is True
    assert out["matchRunOutside"] is False
    assert out["matchCollected"] is True
    assert out["matchUndatedWhenFiltered"] is False
    assert out["matchUndatedWhenEmpty"] is True


def test_click_point_audit_tooltip_and_replicate_mean_sd_controls(
    sample_raw_payload: dict,
    sample_insights_sidecar: dict,
) -> None:
    """Verify click-point audit tooltip (replicate group vs single point) and Replicate Mean ± SD + Field Sample/Experiment grouping."""
    base_bundle = prepare_dashboard_payload(sample_raw_payload, sample_insights_sidecar)
    p1_html = build_analysis_dashboard_html(base_bundle)
    p2_html = build_qc_outlier_dashboard_html(base_bundle)
    p3_html = build_full_dashboard_html(base_bundle)

    # Shared Audit Modal: Replicate Group vs Single Point scope banner & sibling discovery
    for html_doc in (p1_html, p2_html, p3_html):
        assert 'id="finding-scope-prompt-banner"' in html_doc
        assert 'id="finding-scope-btn-group"' in html_doc
        assert 'id="finding-scope-btn-single"' in html_doc
        assert "discoverSiblingReplicates" in html_doc

    # Page 1: Replicate display mode selector & clickable replicate/group audit triggers
    assert 'id="flt-rep-mode"' in p1_html
    assert 'value="mean_sd"' in p1_html
    assert 'value="field_exp_mean_sd"' in p1_html
    assert "window.auditPage1PointOrGroup" in p1_html

    # Page 2: Clickable replicate chips opening group/single audit modal
    assert "window.auditPage2PointOrGroup" in p2_html

    # Page 3: Click-Point Audit Popover & Replicate Mean ± SD + Field Sample / Experiment grouping
    assert 'id="click-audit-popover"' in p3_html
    assert 'id="btn-audit-scope-group"' in p3_html
    assert 'id="btn-audit-scope-single"' in p3_html
    assert "function openClickAuditPopover(" in p3_html
    assert "function submitClickPopoverAuditFinding(" in p3_html
    assert "function escalateClickPopoverToModal(" in p3_html
    assert 'id="rep-mode-select"' in p3_html
    assert 'value="mean_sd"' in p3_html
    assert 'value="field_sample"' in p3_html
    assert 'value="experiment"' in p3_html
    assert 'id="btn-xlayout-by_field_sample"' in p3_html
    assert 'id="btn-xlayout-by_experiment"' in p3_html
    assert "function buildReplicateGroupsMap(" in p3_html


def test_report_a_bug_modal_executes_and_opens_across_dashboard_suite(
    sample_raw_payload: dict,
    sample_insights_sidecar: dict,
    tmp_path: Path,
) -> None:
    """Verify the full page <script> executes without TDZ/DOM errors and opens #modal-report-bug across pages."""
    import re
    import shutil
    import subprocess

    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("node not available")

    from analysis.metadata.resource_audit_workbench import (
        build_workbench_payload,
        render_workbench_html,
    )
    from scripts.generate_dashboard_gallery import generate_gallery

    base_bundle = prepare_dashboard_payload(sample_raw_payload, sample_insights_sidecar)
    p1_html = build_analysis_dashboard_html(base_bundle)
    p2_html = build_qc_outlier_dashboard_html(base_bundle)
    p3_html = build_full_dashboard_html(base_bundle)
    p4_html = render_workbench_html(build_workbench_payload(sample_raw_payload))
    gallery_path, _ = generate_gallery(base_dir=str(tmp_path), output_dir=str(tmp_path))
    gallery_html = Path(gallery_path).read_text(encoding="utf-8")

    dom_harness = """
const elements = {};
function makeEl(id) {
  return {
    id,
    value: "",
    textContent: "",
    innerHTML: "",
    className: id === "modal-report-bug" ? "hidden" : "",
    style: {},
    dataset: {},
    checked: false,
    disabled: false,
    options: Array.from({ length: 8 }, () => ({ textContent: "" })),
    listeners: {},
    classList: {
      _set: new Set(id === "modal-report-bug" ? ["hidden"] : []),
      add(...cls) { cls.forEach(c => this._set.add(c)); },
      remove(...cls) { cls.forEach(c => this._set.delete(c)); },
      toggle(c, force) {
        if (force === undefined) {
          if (this._set.has(c)) { this._set.delete(c); return false; }
          this._set.add(c); return true;
        }
        if (force) this._set.add(c); else this._set.delete(c);
        return !!force;
      },
      contains(c) { return this._set.has(c); }
    },
    addEventListener(evt, fn) {
      if (!this.listeners[evt]) this.listeners[evt] = [];
      this.listeners[evt].push(fn);
    },
    setAttribute(k, v) { this[k] = v; },
    getAttribute(k) { return this[k] || null; },
    appendChild() {},
    removeChild() {},
    insertBefore() {},
    querySelector() { return makeEl("qs"); },
    querySelectorAll() { return []; },
    closest() { return null; },
    parentElement: { clientWidth: 800, clientHeight: 400, getBoundingClientRect() { return { width: 800, height: 400, top: 0, left: 0 }; } },
    getContext() {
      return new Proxy({}, {
        get(_t, prop) {
          if (prop === "measureText") return () => ({ width: 50 });
          if (prop === "createLinearGradient") return () => ({ addColorStop() {} });
          return () => {};
        }
      });
    },
    getBoundingClientRect() { return { width: 800, height: 400, top: 0, left: 0 }; },
    click() {
      (this.listeners["click"] || []).forEach(fn => fn({ preventDefault(){}, stopPropagation(){}, target: this }));
    }
  };
}
let openedUrls = [];
global.window = global;
window.addEventListener = () => {};
window.dispatchEvent = () => {};
window.CustomEvent = class { constructor(t, o) { this.type = t; this.detail = o && o.detail; } };
window.location = { search: "?resource=Almond+hulls", href: "http://localhost:8000/test", pathname: "/test", origin: "http://localhost:8000" };
window.history = { replaceState() {}, pushState() {} };
window.open = (url) => { openedUrls.push(url); };
window.localStorage = { getItem() { return null; }, setItem() {}, removeItem() {} };
window.matchMedia = () => ({ matches: false, addEventListener() {} });
window.requestAnimationFrame = (cb) => cb();
window.URL = { createObjectURL() { return "blob:test"; }, revokeObjectURL() {} };
global.Blob = class {};
global.BroadcastChannel = class { postMessage() {} close() {} };
global.Plotly = { newPlot() {}, react() {}, purge() {}, Plots: { resize() {} }, downloadImage() {} };
global.fetch = async () => ({ ok: false, status: 503, json: async () => ({}) });
global.document = {
  documentElement: makeEl("html"),
  body: makeEl("body"),
  head: makeEl("head"),
  getElementById(id) {
    if (!elements[id]) elements[id] = makeEl(id);
    return elements[id];
  },
  querySelector() { return makeEl("qs"); },
  querySelectorAll() { return []; },
  createElement(tag) { return makeEl(tag); },
  addEventListener() {}
};
global.navigator = { clipboard: { writeText: async () => {} } };
"""
    verify_tail = """
const openBtn = document.getElementById("btn-open-bug-modal");
const bugModal = document.getElementById("modal-report-bug");
const submitUrlBtn = document.getElementById("btn-submit-github-url");
const hasClickListener = Boolean(openBtn.listeners["click"] && openBtn.listeners["click"].length > 0);
openBtn.click();
const openedModal = !bugModal.classList.contains("hidden");
const diagText = document.getElementById("bug-modal-diagnostics").textContent;
submitUrlBtn.click();
const closedModal = bugModal.classList.contains("hidden");
process.stdout.write(JSON.stringify({
  hasClickListener,
  openedModal,
  closedModal,
  diagText,
  openedUrl: openedUrls[0] || ""
}));
"""

    pages = [
        ("Page 1", p1_html),
        ("Page 2", p2_html),
        ("Page 3", p3_html),
        ("Page 4", p4_html),
        ("5-Product Portal Gallery", gallery_html),
    ]
    for expected_label, html_doc in pages:
        assert 'id="btn-open-bug-modal"' in html_doc
        assert 'id="modal-report-bug"' in html_doc
        assert ".hidden { display: none !important; }" in html_doc
        scripts = re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", html_doc, flags=re.S)
        assert scripts, f"{expected_label} missing inline script"
        proc = subprocess.run(
            [node_bin, "-"],
            input=dom_harness + "\n" + scripts[-1] + "\n" + verify_tail,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
        assert proc.returncode == 0, f"{expected_label} script crashed in Node: {proc.stderr}"
        out = json.loads(proc.stdout.strip().splitlines()[-1])
        assert out["hasClickListener"] is True, f"{expected_label} #btn-open-bug-modal listener not bound"
        assert out["openedModal"] is True, f"{expected_label} #modal-report-bug did not open on click"
        assert out["closedModal"] is True, f"{expected_label} #modal-report-bug did not close on submit"
        assert expected_label in out["diagText"]
        assert "/issues/new?" in out["openedUrl"]
