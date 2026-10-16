"""Modular Multi-Resource Analytical & Bioconversion Dashboard Suite (v2).

Generates two focused, uncluttered HTML5 dashboards from the canonical PostgreSQL
queries and `data/insights/resource_ai_insights.json` sidecar:
  1. `exports/plots/metadata/resource_analysis_dashboard.html` (Page 1):
     Clean Resource Characterization, Stoichiometric Closure & Synthesized AI Brief
     across 5 spacious domain tabs.
  2. `exports/plots/metadata/resource_qc_outlier_dashboard.html` (Page 2):
     Dedicated Statistical Replicate Precision (Within-Group vs. Between-Group RSD),
     Candidate Outlier Screening (Dixon's Q, RSD > 20%, >3xSD_pooled, <100 ppm / <0.5%
     low-abundance trace cutoffs), Mined Bench Notes Audit Trail, and Record Explorer.

Note: The legacy all-in-one 7-tab monolith dashboard is preserved at
`exports/plots/metadata/resource_analysis_dashboard_v1_monolith.html`.

Usage:
    # From live PostgreSQL (via Pixi):
    pixi run python analysis/metadata/resource_analysis_dashboard.py

    # From a JSON snapshot:
    python3 analysis/metadata/resource_analysis_dashboard.py --from-snapshot path/to/snapshot.json

    # Single-resource collaborator HTML export with analyst anonymization:
    python3 analysis/metadata/resource_analysis_dashboard.py --single-resource "sargassum" --exclude-analyst
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from resource_insights_engine import DEFAULT_SIDECAR_PATH, build_resource_insights

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "exports" / "plots" / "metadata"


def load_ca_counties_lookup() -> dict[str, str]:
    """Load canonical GEOID -> County Name mapping from data/static/ca_counties.geojson."""
    lookup: dict[str, str] = {"06000": "California (Statewide)"}
    candidates = [
        REPO_ROOT / "data" / "static" / "ca_counties.geojson",
        Path("/Users/pjsmitty301/ca-biositing/data/static/ca_counties.geojson"),
    ]
    for p in candidates:
        if p.exists():
            try:
                geo = json.loads(p.read_text(encoding="utf-8"))
                for feat in geo.get("features", []):
                    props = feat.get("properties", {})
                    geoid = str(props.get("GEOID") or "").strip()
                    name = str(props.get("NAME") or "").strip()
                    if geoid and name:
                        lookup[geoid] = f"{name} County"
                break
            except Exception:
                pass
    return lookup


def prepare_dashboard_payload(
    raw_payload: dict[str, Any],
    insights_sidecar: dict[str, Any],
    single_resource: str | None = None,
    exclude_analyst: bool = False,
) -> dict[str, Any]:
    """Filter or anonymize the payload and bundle AI insights for HTML embedding."""
    payload = deepcopy(raw_payload)
    str_cols: list[str] = payload["str_cols"]
    dicts: dict[str, list[str]] = payload["dicts"]

    if exclude_analyst and "analyst" in dicts:
        dicts["analyst"] = ["—" if a not in ("Unassigned", "") else a for a in dicts["analyst"]]
        for ps in payload.get("prepared_samples", []):
            ps["preparer"] = "—"

    if single_resource:
        target = single_resource.strip().lower()
        res_col_idx = str_cols.index("resource_name") + 1
        res_dict = dicts["resource_name"]
        matching_res_indices = {i for i, name in enumerate(res_dict) if name.lower() == target}
        payload["rows"] = [r for r in payload["rows"] if r[res_col_idx] in matching_res_indices]
        payload["resources"] = [r for r in payload.get("resources", []) if r["name"].lower() == target]
        payload["field_samples"] = [
            fs for fs in payload.get("field_samples", []) if fs["resource_name"].lower() == target
        ]
        payload["prepared_samples"] = [
            ps for ps in payload.get("prepared_samples", []) if ps["resource_name"].lower() == target
        ]
        filtered_insights = {
            k: v for k, v in insights_sidecar.get("resources", {}).items() if k.lower() == target
        }
    else:
        filtered_insights = insights_sidecar.get("resources", {})

    return {
        "generated_utc": payload.get("generated_utc", ""),
        "excluded_resources": payload.get("excluded_resources", []),
        "excluded_providers": payload.get("excluded_providers", []),
        "exclude_analyst_default": exclude_analyst,
        "single_resource": single_resource,
        "str_cols": str_cols,
        "dicts": dicts,
        "rows": payload["rows"],
        "resources": payload.get("resources", []),
        "field_samples": payload.get("field_samples", []),
        "prepared_samples": payload.get("prepared_samples", []),
        "county_lookup": load_ca_counties_lookup(),
        "catalog_medians": insights_sidecar.get("catalog_medians", {}),
        "insights": filtered_insights,
    }


SHARED_CSS = """
    :root, [data-theme="dark"] {
      --background: #0f172a;
      --card: #1e293b;
      --content: #334155;
      --foreground: #f8fafc;
      --muted-foreground: #cbd5e1;
      --primary: #38bdf8;
      --primary-foreground: #0f172a;
      --secondary: #334155;
      --secondary-foreground: #f8fafc;
      --accent: #451a03;
      --accent-foreground: #fde68a;
      --border: #475569;
      --pass-bg: #064e3b;
      --pass-fg: #6ee7b7;
      --pass-border: #059669;
      --fail-bg: #4c0519;
      --fail-fg: #fda4af;
      --fail-border: #e11d48;
      --info-bg: #0c4a6e;
      --info-fg: #7dd3fc;
      --info-border: #0284c7;
      --warn-bg: #451a03;
      --warn-fg: #fde68a;
      --warn-border: #d97706;
      color-scheme: dark;
    }
    [data-theme="light"] {
      --background: #f8fafc;
      --card: #ffffff;
      --content: #e2e8f0;
      --foreground: #0f172a;
      --muted-foreground: #475569;
      --primary: #0284c7;
      --primary-foreground: #ffffff;
      --secondary: #f1f5f9;
      --secondary-foreground: #0f172a;
      --accent: #fef3c7;
      --accent-foreground: #92400e;
      --border: #cbd5e1;
      --pass-bg: #d1fae5;
      --pass-fg: #065f46;
      --pass-border: #6ee7b7;
      --fail-bg: #ffe4e6;
      --fail-fg: #9f1239;
      --fail-border: #fda4af;
      --info-bg: #e0f2fe;
      --info-fg: #075985;
      --info-border: #7dd3fc;
      --warn-bg: #fef3c7;
      --warn-fg: #92400e;
      --warn-border: #fcd34d;
      color-scheme: light;
    }
    html, body {
      background-color: var(--background) !important;
      color: var(--foreground) !important;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    select, input {
      background-color: var(--card) !important;
      color: var(--foreground) !important;
      border-color: var(--border) !important;
    }
    option {
      background-color: var(--card);
      color: var(--foreground);
    }
    .badge-pass { background-color: var(--pass-bg); color: var(--pass-fg); border: 1px solid var(--pass-border); }
    .badge-fail { background-color: var(--fail-bg); color: var(--fail-fg); border: 1px solid var(--fail-border); }
    .badge-info { background-color: var(--info-bg); color: var(--info-fg); border: 1px solid var(--info-border); }
    .badge-warn { background-color: var(--warn-bg); color: var(--warn-fg); border: 1px solid var(--warn-border); }
"""


def build_analysis_dashboard_html(
    bundle: dict[str, Any],
    default_resource: str = "almond hulls",
    qc_page_filename: str = "resource_qc_outlier_dashboard.html",
) -> str:
    """Compile Page 1: Clean Resource Characterization & Executive AI Brief Dashboard."""
    data_json = json.dumps(bundle, separators=(",", ":"))
    single_res = bundle.get("single_resource")
    if single_res:
        default_resource = single_res.lower()
    title_prefix = single_res.title() if single_res else "All-Resources"

    html_template = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BioCirV — __TITLE_PREFIX__ Resource Characterization &amp; AI Brief (Page 1)</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>__SHARED_CSS__</style>
</head>
<body class="bg-[var(--background)] text-[var(--foreground)] antialiased p-3 sm:p-5">
  <div class="max-w-7xl mx-auto space-y-4">

    <!-- Shared Modular Suite Navigation Bar -->
    <nav class="bg-[var(--card)] border border-[var(--border)] rounded-xl px-3.5 py-2.5 shadow-sm flex flex-wrap items-center justify-between gap-2 text-xs">
      <div class="flex flex-wrap items-center gap-1.5">
        <span class="font-bold uppercase tracking-wider text-[var(--muted-foreground)] mr-1">BioCirV Suite:</span>
        <a id="nav-page-char" href="resource_analysis_dashboard.html" class="px-3 py-1.5 rounded-lg font-semibold bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm">
          1. Characterization &amp; AI Brief
        </a>
        <a id="nav-page-qc" href="__QC_PAGE_FILENAME__" class="px-3 py-1.5 rounded-lg font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)] transition flex items-center gap-1.5">
          <span>2. Statistical QC &amp; Lab Notes Audit</span>
          <span id="nav-qc-badge" class="px-1.5 py-0.2 rounded-full text-[11px] font-mono"></span>
        </a>
        <a id="nav-page-explorer" href="resource_explorer_dashboard.html" class="px-3 py-1.5 rounded-lg font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)] transition">
          3. Multi-Resource Side-by-Side Explorer
        </a>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <a href="../audit/db_environment_drift_dashboard.html" class="px-2.5 py-1 rounded-lg font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] border border-transparent hover:border-[var(--border)]">
          DB Drift Audit (Local/Staging/Prod)
        </a>
        <a id="nav-page-monolith" href="resource_analysis_dashboard_v1_monolith.html" class="px-2.5 py-1 rounded-lg font-mono text-[11px] text-[var(--muted-foreground)] hover:text-[var(--foreground)]" title="Open preserved v1 all-in-one 7-tab monolith">
          v1 Monolith
        </a>
      </div>
    </nav>

    <!-- Streamlined Resource Header & Single-Row Filter Bar -->
    <header class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 sm:p-5 shadow-sm space-y-3.5">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-1 flex-1 min-w-[260px]">
          <div class="flex flex-wrap items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-[var(--primary)] inline-block"></span>
            <h1 id="hdr-title" class="text-lg sm:text-xl font-bold text-[var(--foreground)]">BioCirV — Resource Characterization</h1>
            <span id="hdr-code-badge" class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-[var(--primary)] text-[var(--primary-foreground)] font-mono"></span>
            <span id="hdr-class-badge" class="px-2.5 py-0.5 text-xs font-medium rounded-full bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]"></span>
            <span id="hdr-portal-badge" class="px-2.5 py-0.5 text-xs font-semibold rounded-full"></span>
          </div>
          <p id="hdr-desc" class="text-xs sm:text-sm text-[var(--muted-foreground)]"></p>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <button id="btn-toggle-ai" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 transition">
            ✨ Hide AI Brief
          </button>
          <button id="btn-theme-toggle" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90 transition">
            ☀️ Light Mode
          </button>
          <button id="btn-download-csv" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90 transition">
            ⬇ Export CSV
          </button>
        </div>
      </div>

      <!-- Clean Single-Row Filter Bar -->
      <div class="pt-3 border-t border-[var(--border)] flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-2.5">
          <div id="resource-switcher-wrap" class="flex items-center gap-1.5">
            <label for="flt-resource" class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Resource:</label>
            <button id="btn-prev-res" title="Previous Resource" class="px-2 py-1 rounded-lg text-xs font-bold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-80">&larr;</button>
            <select id="flt-resource" class="rounded-lg px-2.5 py-1.5 text-xs sm:text-sm font-bold border min-w-[230px]"></select>
            <button id="btn-next-res" title="Next Resource" class="px-2 py-1 rounded-lg text-xs font-bold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-80">&rarr;</button>
          </div>

          <div class="flex items-center gap-1.5">
            <label for="flt-prepared-sample" class="text-xs font-semibold text-[var(--muted-foreground)]">Sample:</label>
            <select id="flt-prepared-sample" class="rounded-lg px-2.5 py-1.5 text-xs font-medium border min-w-[180px]"></select>
          </div>

          <div class="flex items-center gap-1.5">
            <span class="text-xs font-semibold text-[var(--muted-foreground)]">QC:</span>
            <div class="inline-flex rounded-lg border border-[var(--border)] bg-[var(--background)] p-0.5" id="flt-qc-group">
              <button data-qc="all" class="qc-btn px-2.5 py-1 rounded-md text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)]">All</button>
              <button data-qc="pass" class="qc-btn px-2.5 py-1 rounded-md text-xs font-medium text-[var(--muted-foreground)]">Pass</button>
              <button data-qc="fail" class="qc-btn px-2.5 py-1 rounded-md text-xs font-medium text-[var(--muted-foreground)]">Fail</button>
            </div>
          </div>

          <button id="btn-reset-filters" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90">
            Reset
          </button>
        </div>

        <!-- Subtle Stat QC & Lab Notes Link Pill -->
        <div class="flex flex-wrap items-center gap-2">
          <span id="active-slice-badge" class="text-xs font-mono text-[var(--muted-foreground)]"></span>
          <a id="hdr-qc-deep-link" href="__QC_PAGE_FILENAME__" class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition flex items-center gap-1.5"></a>
        </div>
      </div>
    </header>

    <!-- Compact 2-Card Executive AI Synthesis Brief -->
    <section id="ai-insights-panel" class="bg-[var(--card)] border border-[var(--primary)]/40 rounded-xl p-4 sm:p-5 shadow-sm space-y-3"></section>

    <!-- Streamlined 4-Card KPI Strip -->
    <section class="grid grid-cols-2 lg:grid-cols-4 gap-3" id="kpi-strip"></section>

    <!-- 5 Spacious Characterization & Conversion Domain Tabs -->
    <div class="flex flex-wrap gap-1.5 bg-[var(--card)] border border-[var(--border)] rounded-xl p-1.5 shadow-sm" id="main-tabs">
      <button data-tab="overview" class="tab-btn px-3.5 py-2 rounded-lg text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)]">1. Overview &amp; Lineage</button>
      <button data-tab="proximate" class="tab-btn px-3.5 py-2 rounded-lg text-xs font-semibold text-[var(--muted-foreground)]">2. Proximate &amp; Calorimetry</button>
      <button data-tab="compositional" class="tab-btn px-3.5 py-2 rounded-lg text-xs font-semibold text-[var(--muted-foreground)]">3. Compositional, Ultimate &amp; XRD</button>
      <button data-tab="elemental" class="tab-btn px-3.5 py-2 rounded-lg text-xs font-semibold text-[var(--muted-foreground)]">4. ICP &amp; XRF Elements</button>
      <button data-tab="conversion" class="tab-btn px-3.5 py-2 rounded-lg text-xs font-semibold text-[var(--muted-foreground)]">5. Pretreatment, Fermentation &amp; Gasification</button>
    </div>

    <!-- Dynamic Tab Content Container -->
    <main id="tab-content" class="space-y-4"></main>

  </div>

  <script>
    const BUNDLE = __DATA_JSON__;
    const DEFAULT_RESOURCE = __DEFAULT_RESOURCE__;
    const QC_PAGE_FILENAME = __QC_PAGE_FILENAME_JSON__;

    const ELEM_NAMES = {
      K: "Potassium (K)", Ca: "Calcium (Ca)", Na: "Sodium (Na)", S: "Sulfur (S)",
      Mg: "Magnesium (Mg)", P: "Phosphorus (P)", Fe: "Iron (Fe)", Al: "Aluminum (Al)",
      Si: "Silicon (Si)", Mn: "Manganese (Mn)", Zn: "Zinc (Zn)", Cu: "Copper (Cu)",
      B: "Boron (B)", Ti: "Titanium (Ti)", Sr: "Strontium (Sr)", Ba: "Barium (Ba)",
      Rb: "Rubidium (Rb)", Zr: "Zirconium (Zr)", Cr: "Chromium (Cr)", Ni: "Nickel (Ni)",
      Pb: "Lead (Pb)", As: "Arsenic (As)", Co: "Cobalt (Co)", Mo: "Molybdenum (Mo)",
      Cd: "Cadmium (Cd)", Se: "Selenium (Se)", Sb: "Antimony (Sb)", Sn: "Tin (Sn)",
      V: "Vanadium (V)", W: "Tungsten (W)", Ag: "Silver (Ag)", Hg: "Mercury (Hg)",
      Bi: "Bismuth (Bi)", Th: "Thorium (Th)", U: "Uranium (U)", Y: "Yttrium (Y)",
      La: "Lanthanum (La)", Ce: "Cerium (Ce)", Pr: "Praseodymium (Pr)", Nd: "Neodymium (Nd)",
      Nb: "Niobium (Nb)", Cl: "Chlorine (Cl)"
    };

    const COUNTY_LOOKUP = BUNDLE.county_lookup || {};
    const FS_LOOKUP = {};
    (BUNDLE.field_samples || []).forEach(fs => { FS_LOOKUP[fs.name] = fs; });
    const PS_LOOKUP = {};
    (BUNDLE.prepared_samples || []).forEach(ps => { PS_LOOKUP[ps.name] = ps; });

    function fmtGeoid(geoid) {
      if (!geoid) return "—";
      const g = String(geoid).trim();
      const cName = COUNTY_LOOKUP[g];
      return cName ? `${g} (${cName})` : g;
    }

    const ALL_RECORDS = BUNDLE.rows.map(arr => {
      const obj = { record_id: String(arr[0]) };
      BUNDLE.str_cols.forEach((col, idx) => {
        obj[col] = BUNDLE.dicts[col][arr[idx + 1]];
      });
      obj.replicate = arr[BUNDLE.str_cols.length + 1];
      obj.value = arr[BUNDLE.str_cols.length + 2];
      obj.exp_date = arr.length > BUNDLE.str_cols.length + 3 ? arr[BUNDLE.str_cols.length + 3] : "";
      obj.time_h = arr.length > BUNDLE.str_cols.length + 4 ? arr[BUNDLE.str_cols.length + 4] : null;
      const fsMeta = FS_LOOKUP[obj.field_sample] || {};
      const psMeta = PS_LOOKUP[obj.prepared_sample] || {};
      obj.collected_date = fsMeta.collected_at ? String(fsMeta.collected_at).slice(0, 10) : "";
      obj.geoid = fsMeta.geoid ? String(fsMeta.geoid).trim() : "";
      obj.county_name = obj.geoid ? (COUNTY_LOOKUP[obj.geoid] || "") : "";
      obj.prep_date = psMeta.prep_date ? String(psMeta.prep_date).slice(0, 10) : (obj.exp_date ? String(obj.exp_date).slice(0, 10) : "");
      if ((obj.analysis_type === "ICP Elemental Analysis" || obj.analysis_type === "XRF Elemental Analysis") && obj.parameter && obj.parameter !== "(metadata only)") {
        obj.parameter = obj.parameter.charAt(0).toUpperCase() + obj.parameter.slice(1).toLowerCase();
      }
      return obj;
    });

    const RECORDS_BY_RESOURCE = {};
    ALL_RECORDS.forEach(r => {
      if (!RECORDS_BY_RESOURCE[r.resource_name]) RECORDS_BY_RESOURCE[r.resource_name] = [];
      RECORDS_BY_RESOURCE[r.resource_name].push(r);
    });

    const ACTIVE_RESOURCES = Object.keys(RECORDS_BY_RESOURCE).sort(
      (a, b) => RECORDS_BY_RESOURCE[b].length - RECORDS_BY_RESOURCE[a].length
    );

    const urlParams = new URLSearchParams(window.location.search);
    const initialResParam = (urlParams.get("resource") || DEFAULT_RESOURCE).toLowerCase();
    const matchedInitialRes = ACTIVE_RESOURCES.find(r => r.toLowerCase() === initialResParam) || ACTIVE_RESOURCES[0];
    const rawTabParam = urlParams.get("tab") || "overview";
    const validTabs = ["overview", "proximate", "compositional", "elemental", "conversion"];
    const initialTabParam = validTabs.includes(rawTabParam) ? rawTabParam : (rawTabParam === "pretreatment" || rawTabParam === "fermentation" ? "conversion" : "overview");

    const state = {
      resource: matchedInitialRes,
      tab: initialTabParam,
      prepared_sample: "all",
      field_sample: "all",
      qc_status: "all",
      showAiPanel: true,
      proxGroupMode: "ps_exp",
      elemSourceMode: "all",
      icpScaleMode: "split",
      convSubTab: "all"
    };

    function formatMdInline(text) {
      if (!text) return "";
      return String(text)
        .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong class="text-[var(--foreground)] font-semibold">$1</strong>')
        .replace(/\\*([^*]+)\\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 rounded bg-[var(--content)] text-[var(--foreground)] font-mono text-xs">$1</code>')
        .replace(/\\$\\\\text\\{([^}]+)\\}\\s*\\+\\s*\\\\text\\{([^}]+)\\}\\s*\\+\\s*\\\\text\\{([^}]+)\\}\\s*=\\s*\\\\mathbf\\{([^}]+)\\}\\$/g, '<span class="font-mono font-bold text-[var(--foreground)]">$1 + $2 + $3 = $4</span>')
        .replace(/\\$\\\\text\\{RSD\\}_\\{\\\\text\\{within\\}\\}\\$/g, '<span class="font-mono font-semibold">RSD<sub>within</sub></span>')
        .replace(/\\$\\\\text\\{RSD\\}_\\{\\\\text\\{between\\}\\}\\$/g, '<span class="font-mono font-semibold">RSD<sub>between</sub></span>')
        .replace(/\\$\\\\alpha\\s*=\\s*0\\.05\\$/g, '<span class="font-mono">α = 0.05</span>')
        .replace(/\\$n\\s*\\\\ge\\s*3\\$/g, '<span class="font-mono">n ≥ 3</span>')
        .replace(/\\\\\\%/g, "%")
        .replace(/\\$\\\\text\\{H\\}_2\\s*=\\s*([^$]+)\\$/g, '<span class="font-mono">H₂ = $1</span>')
        .replace(/\\$\\\\text\\{CO\\}\\s*=\\s*([^$]+)\\$/g, '<span class="font-mono">CO = $1</span>');
    }

    function getResourceRecords() {
      return RECORDS_BY_RESOURCE[state.resource] || [];
    }

    function getResourcePreparedSamples() {
      return (BUNDLE.prepared_samples || []).filter(ps => ps.resource_name === state.resource);
    }

    function getResourceFieldSamples() {
      return (BUNDLE.field_samples || []).filter(fs => fs.resource_name === state.resource);
    }

    function getResourceInsights() {
      return (BUNDLE.insights && BUNDLE.insights[state.resource]) || null;
    }

    function calcStats(values) {
      const nums = values.filter(v => typeof v === "number" && !isNaN(v));
      if (nums.length === 0) return { n: 0, mean: null, sd: null, min: null, max: null, vals: [] };
      const n = nums.length;
      const mean = nums.reduce((a, b) => a + b, 0) / n;
      const variance = n > 1 ? nums.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / (n - 1) : 0;
      const sd = Math.sqrt(variance);
      return { n, mean, sd, min: Math.min(...nums), max: Math.max(...nums), vals: nums };
    }

    function fmtNum(v, digits = 2) {
      if (v === null || v === undefined || isNaN(v)) return "—";
      return Number(v).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: digits });
    }

    function qcBadgeHtml(qc) {
      if (qc === "pass") {
        return `<span class="badge-pass px-2 py-0.5 text-xs font-mono font-semibold rounded">PASS</span>`;
      }
      return `<span class="badge-fail px-2 py-0.5 text-xs font-mono font-semibold rounded">FAIL</span>`;
    }

    function initResourceSwitcher() {
      const sel = document.getElementById("flt-resource");
      sel.innerHTML = ACTIVE_RESOURCES.map(r => {
        const recs = RECORDS_BY_RESOURCE[r];
        const passCnt = recs.filter(x => x.qc_status === "pass").length;
        const passPct = recs.length ? ((passCnt / recs.length) * 100).toFixed(0) : "0";
        return `<option value="${r}">${r.toUpperCase()} — ${recs.length} obs (${passPct}% Pass)</option>`;
      }).join("");
      sel.value = state.resource;
      if (BUNDLE.single_resource) {
        document.getElementById("resource-switcher-wrap").classList.add("hidden");
      }
    }

    function initFiltersForResource() {
      const resRecs = getResourceRecords();
      const psList = getResourcePreparedSamples();
      const psCounts = {};
      resRecs.forEach(r => { psCounts[r.prepared_sample] = (psCounts[r.prepared_sample] || 0) + 1; });
      const allPsNames = Array.from(new Set([...psList.map(p => p.name), ...Object.keys(psCounts)])).filter(Boolean);
      const psMetaMap = {};
      psList.forEach(p => { psMetaMap[p.name] = p; });
      const selPs = document.getElementById("flt-prepared-sample");
      selPs.innerHTML = `<option value="all">All Prepared Samples (${allPsNames.length})</option>` + allPsNames.map(name => {
        const c = psCounts[name] || 0;
        const pm = psMetaMap[name] ? psMetaMap[name].prep_method : "";
        return `<option value="${name}">${name}${pm ? ' · ' + pm : ''} (${c})</option>`;
      }).join("");
      selPs.value = allPsNames.includes(state.prepared_sample) ? state.prepared_sample : "all";
    }

    function getFilteredRecords() {
      const resRecs = getResourceRecords();
      return resRecs.filter(r => {
        if (state.prepared_sample !== "all" && r.prepared_sample !== state.prepared_sample) return false;
        if (state.field_sample !== "all" && r.field_sample !== state.field_sample) return false;
        if (state.qc_status !== "all" && r.qc_status !== state.qc_status) return false;
        return true;
      });
    }

    function updateSuiteNavLinks() {
      const encRes = encodeURIComponent(state.resource);
      document.getElementById("nav-page-char").href = `resource_analysis_dashboard.html?resource=${encRes}`;
      document.getElementById("nav-page-qc").href = `${QC_PAGE_FILENAME}?resource=${encRes}`;
      document.getElementById("nav-page-explorer").href = `resource_explorer_dashboard.html?resource=${encRes}`;
      document.getElementById("nav-page-monolith").href = `resource_analysis_dashboard_v1_monolith.html?resource=${encRes}`;

      const ins = getResourceInsights();
      const out = (ins && ins.outlier_screening) || {};
      const activeFlags = out.flagged_active_groups || 0;
      const notesCnt = (ins && ins.curated_notes && ins.curated_notes.length) || 0;

      const navBadge = document.getElementById("nav-qc-badge");
      if (activeFlags > 0) {
        navBadge.className = "px-1.5 py-0.5 rounded-full text-[11px] font-mono badge-warn";
        navBadge.textContent = `⚑ ${activeFlags}`;
      } else {
        navBadge.className = "px-1.5 py-0.5 rounded-full text-[11px] font-mono badge-pass";
        navBadge.textContent = "✓ 0";
      }

      const hdrLink = document.getElementById("hdr-qc-deep-link");
      hdrLink.href = `${QC_PAGE_FILENAME}?resource=${encRes}`;
      if (activeFlags > 0 || notesCnt > 0) {
        hdrLink.className = "px-3 py-1.5 rounded-lg text-xs font-semibold badge-warn hover:opacity-90 transition flex items-center gap-1.5";
        hdrLink.innerHTML = `<span>⚑ Stat QC: <strong>${activeFlags}</strong> Flagged Group(s) · <strong>${notesCnt}</strong> Bench Note(s) &rarr; Audit</span>`;
      } else {
        hdrLink.className = "px-3 py-1.5 rounded-lg text-xs font-semibold badge-pass hover:opacity-90 transition flex items-center gap-1.5";
        hdrLink.innerHTML = `<span>✓ Stat QC: 0 Active Flags &rarr; Open Precision Audit</span>`;
      }
    }

    function updateHeader() {
      const ins = getResourceInsights();
      const resRecs = getResourceRecords();
      const fsList = getResourceFieldSamples();
      const psList = getResourcePreparedSamples();

      const rTitle = state.resource.replace(/\\b\\w/g, c => c.toUpperCase());
      document.getElementById("hdr-title").textContent = `BioCirV · ${rTitle} — Feedstock Characterization & Conversion`;
      document.getElementById("hdr-code-badge").textContent = ins
        ? `#${ins.resource_id || '—'} · ${ins.code}`
        : state.resource.slice(0, 4);
      document.getElementById("hdr-class-badge").textContent = ins
        ? ins.resource_class
        : "Biomass Resource";

      const portalBadge = document.getElementById("hdr-portal-badge");
      if (ins && ins.portal_excluded) {
        portalBadge.className = "px-2.5 py-0.5 text-xs font-semibold rounded-full badge-warn font-mono";
        portalBadge.textContent = "Raw DB Only";
      } else {
        portalBadge.className = "px-2.5 py-0.5 text-xs font-semibold rounded-full badge-pass font-mono";
        portalBadge.textContent = "Portal Active";
      }

      const provStr = ins && ins.providers && ins.providers.length ? ins.providers.join(", ") : "multi-provider";
      const colDates = Array.from(new Set(fsList.map(f => f.collected_at ? f.collected_at.slice(0, 10) : "").filter(Boolean))).sort();
      const geoids = Array.from(new Set(fsList.map(f => f.geoid).filter(Boolean))).map(fmtGeoid);
      const colSummary = colDates.length ? ` · Collected: <span class="font-mono text-[var(--foreground)]">${colDates.join(", ")}</span>` : "";
      const geoSummary = geoids.length ? ` · GEOID: <span class="font-mono text-[var(--primary)]">${geoids.join(", ")}</span>` : "";
      document.getElementById("hdr-desc").innerHTML = `
        <strong>${fsList.length} field sample(s)</strong> &rarr; <strong>${psList.length} prepared sample(s)</strong> &rarr;
        <strong>${resRecs.length.toLocaleString()} analytical &amp; conversion observations</strong> (Providers: <span class="font-mono">${provStr}</span>)${colSummary}${geoSummary}.
      `;
      updateSuiteNavLinks();
    }

    function renderAiInsightsPanel() {
      const panel = document.getElementById("ai-insights-panel");
      if (!state.showAiPanel) {
        panel.classList.add("hidden");
        return;
      }
      panel.classList.remove("hidden");

      const ins = getResourceInsights();
      if (!ins) {
        panel.innerHTML = `<div class="text-xs text-[var(--muted-foreground)]">No synthesized AI insights found for ${state.resource}.</div>`;
        return;
      }

      const d = ins.diagnostics || {};
      const p = ins.percentiles || {};
      const out = ins.outlier_screening || {};
      const notes = ins.curated_notes || [];
      const encRes = encodeURIComponent(state.resource);

      const pctBadges = [
        p.glucan_dw_pct ? { label: "Glucan", val: `${d.glucan_dw_pct}% dw`, pct: `${p.glucan_dw_pct}th %ile` } : null,
        p.ash_pct ? { label: "Ash", val: `${d.ash_pct}%`, pct: `${p.ash_pct}th %ile` } : null,
        p.best_glucose_yld_pct ? { label: `PT Glucose (${d.best_glu_pt_method})`, val: `${d.best_glucose_yld_pct}%`, pct: `${p.best_glucose_yld_pct}th %ile` } : null,
        p.titer_3hp_g_l ? { label: "3-HP Titer", val: `${d.titer_3hp_g_l} g/L`, pct: `${p.titer_3hp_g_l}th %ile` } : null
      ].filter(Boolean);

      panel.innerHTML = `
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-2.5">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded-md text-xs font-bold bg-[var(--primary)] text-[var(--primary-foreground)]">AI BRIEF</span>
            <h2 class="text-sm font-bold text-[var(--foreground)]">Synthesized Feedstock Meaning &amp; Stoichiometric Summary</h2>
          </div>
          <a href="${QC_PAGE_FILENAME}?resource=${encRes}" class="text-xs font-semibold text-[var(--primary)] hover:underline">
            View Full Statistical Outlier Screen (${out.flagged_active_groups || 0} flags) &amp; Mined Bench Notes (${notes.length}) &rarr;
          </a>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
          <!-- Card 1: Feedstock Meaning & Conversion Profile -->
          <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-4 space-y-3">
            <div class="text-xs font-bold uppercase tracking-wider text-[var(--primary)]">1. Feedstock Meaning &amp; Conversion Profile</div>
            <p class="text-xs text-[var(--muted-foreground)] leading-relaxed">${formatMdInline(ins.ai_narratives.feedstock_profile)}</p>
            ${pctBadges.length ? `
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-[var(--border)]">
                ${pctBadges.map(b => `
                  <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2">
                    <div class="text-[11px] text-[var(--muted-foreground)] truncate">${b.label}</div>
                    <div class="text-xs font-bold font-mono text-[var(--foreground)]">${b.val} <span class="text-[var(--primary)]">(${b.pct})</span></div>
                  </div>
                `).join("")}
              </div>
            ` : ""}
          </div>

          <!-- Card 2: Stoichiometric Closure & Key Diagnostics -->
          <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-4 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold uppercase tracking-wider text-[var(--primary)]">2. Stoichiometric Closure &amp; Precision Overview</span>
              <span class="text-[11px] font-mono text-[var(--muted-foreground)]">Within-Rep RSD: ${out.overall_within_rsd_median !== null && out.overall_within_rsd_median !== undefined ? out.overall_within_rsd_median + '%' : 'n=1'}</span>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
              <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2.5">
                <div class="text-[11px] text-[var(--muted-foreground)] font-sans">Proximate Wet Sum</div>
                <div class="font-bold text-sm text-[var(--foreground)]">${d.proximate_wet_closure_pct !== null ? d.proximate_wet_closure_pct + '%' : 'N/A'}</div>
              </div>
              <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2.5">
                <div class="text-[11px] text-[var(--muted-foreground)] font-sans">Polymer Sum</div>
                <div class="font-bold text-sm text-[var(--foreground)]">${d.compositional_polymer_sum_dw_pct !== null ? d.compositional_polymer_sum_dw_pct + '% dw' : 'N/A'}</div>
              </div>
              <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2.5">
                <div class="text-[11px] text-[var(--muted-foreground)] font-sans">Pretreatment Lift</div>
                <div class="font-bold text-sm text-[var(--foreground)]">${d.pretreatment_lift_factor !== null ? d.pretreatment_lift_factor + '×' : 'N/A'}</div>
              </div>
              <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2.5">
                <div class="text-[11px] text-[var(--muted-foreground)] font-sans">Moisture (As-Is/Dry)</div>
                <div class="font-bold text-sm text-[var(--foreground)]">${d.moisture_as_is_pct !== null ? d.moisture_as_is_pct + '%' : '—'} / ${d.moisture_dried_pct !== null ? d.moisture_dried_pct + '%' : '—'}</div>
              </div>
            </div>
            <div class="p-2.5 rounded-lg bg-[var(--card)] border border-[var(--border)] flex flex-wrap items-center justify-between gap-2 text-xs">
              <span class="text-[var(--muted-foreground)]">
                Statistical Screen: <strong>${out.flagged_active_groups || 0}</strong> active outlier group(s)
                ${out.suppressed_low_abundance_groups ? `(${out.suppressed_low_abundance_groups} trace &lt;100 ppm suppressed)` : ''} ·
                <strong>${notes.length}</strong> distinct lab note group(s)
              </span>
              <a href="${QC_PAGE_FILENAME}?resource=${encRes}" class="px-2.5 py-1 rounded bg-[var(--secondary)] text-[var(--foreground)] border border-[var(--border)] font-semibold hover:border-[var(--primary)]">
                Open QC &amp; Outlier Page &rarr;
              </a>
            </div>
          </div>
        </div>
      `;
    }

    function renderKpiStrip(filtered) {
      const resRecs = getResourceRecords();
      const psList = getResourcePreparedSamples();
      const fsList = getResourceFieldSamples();
      const ins = getResourceInsights();
      const d = (ins && ins.diagnostics) || {};

      const passCount = filtered.filter(r => r.qc_status === "pass").length;
      const failCount = filtered.filter(r => r.qc_status === "fail").length;
      const passRate = filtered.length ? ((passCount / filtered.length) * 100).toFixed(1) : "0.0";
      const activePs = new Set(filtered.map(r => r.prepared_sample).filter(Boolean)).size;
      const activeFs = new Set(filtered.map(r => r.field_sample).filter(Boolean)).size;

      const colDates = Array.from(new Set(filtered.map(r => r.collected_date).filter(Boolean))).sort();
      const prepDates = Array.from(new Set(filtered.map(r => r.prep_date).filter(Boolean))).sort();
      const geoids = Array.from(new Set(filtered.map(r => r.geoid).filter(Boolean))).map(fmtGeoid);

      const colDateStr = colDates.length
        ? (colDates.length === 1 ? colDates[0] : `${colDates[0]} → ${colDates[colDates.length - 1]}`)
        : "Not recorded";
      const prepDateStr = prepDates.length
        ? (prepDates.length === 1 ? prepDates[0] : `${prepDates[0]} → ${prepDates[prepDates.length - 1]}`)
        : "Not recorded";
      const geoStr = geoids.length ? geoids.join(", ") : "Statewide / Unassigned";

      document.getElementById("active-slice-badge").textContent = `${filtered.length} / ${resRecs.length} obs (${passRate}% QC Pass)`;

      const polyStr = d.compositional_polymer_sum_dw_pct !== null && d.compositional_polymer_sum_dw_pct !== undefined
        ? `${d.compositional_polymer_sum_dw_pct}% dw polymers`
        : (d.glucan_dw_pct ? `Glucan ${d.glucan_dw_pct}% dw` : "Pending Comp");
      const ashStr = d.ash_pct !== null && d.ash_pct !== undefined ? `Ash: ${d.ash_pct}% · VS: ${d.volatile_solids_pct ?? '—'}%` : "Proximate pending";

      const convMain = d.best_glucose_yld_pct !== null && d.best_glucose_yld_pct !== undefined
        ? `${d.best_glucose_yld_pct}% Glu Yield`
        : (d.titer_3hp_g_l ? `${d.titer_3hp_g_l} g/L 3-HP` : (d.syngas_comb_pct ? `${d.syngas_comb_pct}% Syngas` : "Characterization Only"));
      const convSub = d.best_glu_pt_method
        ? `Best PT: ${d.best_glu_pt_method}${d.titer_3hp_g_l ? ' · 3-HP: ' + d.titer_3hp_g_l + ' g/L' : ''}`
        : (d.syngas_h2_ppm ? `H2: ${fmtNum(d.syngas_h2_ppm, 0)} ppm` : "Aim 2 Conversion");

      const kpis = [
        { label: "Filtered Observations", value: `${filtered.length.toLocaleString()}`, sub: `${passRate}% QC Pass (${passCount}P · ${failCount}F) · Run/Prep: ${prepDateStr}` },
        { label: "Sample Lineage & Dates", value: `${activeFs} Field → ${activePs} Prep`, sub: `Collected: ${colDateStr} · GEOID: ${geoStr}` },
        { label: "Biochemical & Ash Signature", value: polyStr, sub: ashStr },
        { label: "Peak Conversion Performance", value: convMain, sub: convSub }
      ];

      document.getElementById("kpi-strip").innerHTML = kpis.map(k => `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-3.5 shadow-sm">
          <div class="text-xs font-medium text-[var(--muted-foreground)]">${k.label}</div>
          <div class="text-base sm:text-lg font-bold text-[var(--foreground)] mt-0.5 font-mono truncate" title="${k.value}">${k.value}</div>
          <div class="text-xs text-[var(--muted-foreground)] mt-0.5 truncate" title="${k.sub}">${k.sub}</div>
        </div>
      `).join("");

      const proxCnt = filtered.filter(r => r.analysis_type === "Proximate Analysis" || r.analysis_type === "Calorimetry").length;
      const compCnt = filtered.filter(r => ["Compositional Analysis", "Ultimate Analysis", "XRD Crystallinity"].includes(r.analysis_type)).length;
      const elemCnt = filtered.filter(r => ["ICP Elemental Analysis", "XRF Elemental Analysis"].includes(r.analysis_type)).length;
      const convCnt = filtered.filter(r => ["Pretreatment & Hydrolysis", "Fermentation (Bioconversion)", "Gasification"].includes(r.analysis_type)).length;

      const labels = {
        overview: "1. Overview & Lineage",
        proximate: `2. Proximate & Calorimetry (${proxCnt})`,
        compositional: `3. Compositional, Ultimate & XRD (${compCnt})`,
        elemental: `4. ICP & XRF Elements (${elemCnt})`,
        conversion: `5. Pretreatment, Fermentation & Gasification (${convCnt})`
      };
      document.querySelectorAll(".tab-btn").forEach(btn => {
        const t = btn.dataset.tab;
        btn.textContent = labels[t];
        btn.className = t === state.tab
          ? "tab-btn px-3.5 py-2 rounded-lg text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)]"
          : "tab-btn px-3.5 py-2 rounded-lg text-xs font-semibold text-[var(--muted-foreground)] hover:text-[var(--foreground)]";
      });
    }

    function tabInsightBannerHtml(tabKey) {
      const ins = getResourceInsights();
      const text = ins && ins.ai_narratives && ins.ai_narratives.tab_insights && ins.ai_narratives.tab_insights[tabKey];
      if (!text) return "";
      const out = (ins && ins.outlier_screening && ins.outlier_screening.by_tab && ins.outlier_screening.by_tab[tabKey]) || null;
      const activeFlags = out ? out.flagged_active : 0;
      const encRes = encodeURIComponent(state.resource);
      return `
        <div class="bg-[var(--card)] border border-[var(--primary)]/40 rounded-xl p-3.5 shadow-sm flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-start gap-2.5 flex-1 min-w-[260px]">
            <span class="px-2 py-0.5 rounded bg-[var(--primary)] text-[var(--primary-foreground)] font-mono text-xs font-bold shrink-0 mt-0.5">AI INSIGHT</span>
            <div class="text-xs text-[var(--muted-foreground)] leading-relaxed">${formatMdInline(text)}</div>
          </div>
          ${out && out.total_groups > 0 ? `
            <a href="${QC_PAGE_FILENAME}?resource=${encRes}&domain=${tabKey}" class="px-2.5 py-1 rounded-lg text-xs font-mono font-semibold shrink-0 ${activeFlags > 0 ? 'badge-warn' : 'badge-pass'} hover:opacity-90">
              ${activeFlags > 0 ? `⚑ ${activeFlags} Outlier Flag(s)` : '✓ 0 Active Flags'} · Within-RSD ${out.within_rsd_median !== null ? fmtNum(out.within_rsd_median, 1) + '%' : 'n=1'} &rarr;
            </a>
          ` : ""}
        </div>
      `;
    }

    function emptyStateHtml(domainName) {
      return `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-8 text-center space-y-2">
          <div class="text-sm font-bold text-[var(--foreground)]">No ${domainName} Records in Current Filter Slice</div>
          <p class="text-xs text-[var(--muted-foreground)]">Try clicking <strong>Reset</strong> or switching to another biomass resource.</p>
        </div>
      `;
    }

    function renderOverviewTab(filtered) {
      const resRecs = getResourceRecords();
      const psList = getResourcePreparedSamples();
      const fsList = getResourceFieldSamples();
      const ins = getResourceInsights();
      const med = BUNDLE.catalog_medians || {};
      const d = (ins && ins.diagnostics) || {};
      const p = (ins && ins.percentiles) || {};
      const encRes = encodeURIComponent(state.resource);

      const benchMetrics = [
        { label: "Glucan (% dw)", val: d.glucan_dw_pct, med: med.glucan_dw_pct, pct: p.glucan_dw_pct, max: 50, unit: "%" },
        { label: "Xylan (% dw)", val: d.xylan_dw_pct, med: med.xylan_dw_pct, pct: p.xylan_dw_pct, max: 30, unit: "%" },
        { label: "Lignin (% dw)", val: d.lignin_dw_pct, med: med.lignin_dw_pct, pct: p.lignin_dw_pct, max: 45, unit: "%" },
        { label: "Ash (% total)", val: d.ash_pct, med: med.ash_pct, pct: p.ash_pct, max: 40, unit: "%" },
        { label: "Peak PT Glucose Yield", val: d.best_glucose_yld_pct, med: med.best_glucose_yld_pct, pct: p.best_glucose_yld_pct, max: 100, unit: "%" },
        { label: "3-HP Titer (g/L)", val: d.titer_3hp_g_l, med: med.titer_3hp_g_l, pct: p.titer_3hp_g_l, max: 10, unit: " g/L" }
      ].filter(b => b.val !== null && b.val !== undefined);

      const benchHtml = benchMetrics.length ? `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-3">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 class="text-base font-bold text-[var(--foreground)]">Statewide Biomass Catalog Benchmark Standing</h2>
              <p class="text-xs text-[var(--muted-foreground)]">Compares <strong>${state.resource}</strong> against the California biomass catalog median (vertical marker line).</p>
            </div>
            <a href="resource_explorer_dashboard.html?resource=${encRes}" class="px-3 py-1 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--foreground)] border border-[var(--border)] hover:border-[var(--primary)]">
              Compare Side-by-Side with Other Resources &rarr;
            </a>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            ${benchMetrics.map(b => {
              const wVal = Math.min(100, Math.max(3, (b.val / b.max) * 100));
              const wMed = b.med ? Math.min(100, Math.max(2, (b.med / b.max) * 100)) : 0;
              return `
                <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-3.5 space-y-1.5">
                  <div class="flex items-center justify-between text-xs">
                    <span class="font-semibold text-[var(--foreground)]">${b.label}</span>
                    <span class="font-mono font-bold text-[var(--foreground)]">${fmtNum(b.val)}${b.unit} ${b.pct ? `<span class="text-[var(--primary)]">(${b.pct}th %ile)</span>` : ''}</span>
                  </div>
                  <div class="relative w-full h-3 rounded-full bg-[var(--content)] overflow-hidden">
                    <div class="h-full rounded-full bg-[var(--primary)]" style="width: ${wVal}%"></div>
                    ${wMed ? `<div class="absolute top-0 bottom-0 w-0.5 bg-[var(--foreground)]" style="left: ${wMed}%" title="Catalog Median: ${b.med}${b.unit}"></div>` : ""}
                  </div>
                  <div class="flex justify-between text-[11px] font-mono text-[var(--muted-foreground)]">
                    <span>Resource: ${fmtNum(b.val)}${b.unit}</span>
                    <span>CA Median: ${b.med !== null ? fmtNum(b.med) + b.unit : '—'}</span>
                  </div>
                </div>
              `;
            }).join("")}
          </div>
        </div>
      ` : "";

      const fsCards = fsList.map(fs => {
        const isSelected = state.field_sample === fs.name;
        const recs = filtered.filter(r => r.field_sample === fs.name);
        const colDate = fs.collected_at ? String(fs.collected_at).slice(0, 10) : "Not recorded";
        const geoLabel = fmtGeoid(fs.geoid);
        const childPreps = psList.filter(p => p.field_sample_name === fs.name).length;
        return `
          <div onclick="setQuickFilter('field_sample', '${fs.name}')" class="cursor-pointer rounded-xl p-3.5 border transition ${isSelected ? 'bg-[var(--secondary)] border-[var(--primary)] ring-1 ring-[var(--primary)]' : 'bg-[var(--background)] border-[var(--border)] hover:border-[var(--primary)]'}">
            <div class="flex items-center justify-between gap-2">
              <span class="font-mono font-bold text-sm text-[var(--foreground)]">Field: ${fs.name}</span>
              <span class="px-2 py-0.5 text-xs rounded-full badge-info font-mono">Collected: ${colDate}</span>
            </div>
            <div class="text-xs text-[var(--muted-foreground)] mt-1.5 space-y-0.5">
              <div><strong class="text-[var(--foreground)]">GEOID · County:</strong> <span class="font-mono text-[var(--primary)]">${geoLabel}</span></div>
              <div><strong class="text-[var(--foreground)]">Sampling Site:</strong> ${fs.sampling_site || '—'} · <strong class="text-[var(--foreground)]">Source:</strong> ${fs.sample_source || '—'}</div>
              <div><strong class="text-[var(--foreground)]">Storage / Particle:</strong> ${fs.field_storage || '—'} / ${fs.particle_size || '—'}</div>
            </div>
            <div class="mt-2 pt-2 border-t border-[var(--border)] flex items-center justify-between text-xs font-mono">
              <span>${childPreps} prep(s) · ${recs.length} obs</span>
              <span class="underline text-[var(--primary)]">${isSelected ? 'Active filter (click to clear)' : 'Filter by field sample'}</span>
            </div>
          </div>
        `;
      }).join("");

      const psCards = psList.map(ps => {
        const recs = filtered.filter(r => r.prepared_sample === ps.name);
        const totalAll = resRecs.filter(r => r.prepared_sample === ps.name).length;
        const passCnt = recs.filter(r => r.qc_status === "pass").length;
        const failCnt = recs.filter(r => r.qc_status === "fail").length;
        const types = Array.from(new Set(recs.map(r => r.analysis_type.split(" ")[0]))).join(", ") || "None in current slice";
        const isSelected = state.prepared_sample === ps.name;
        const fsMeta = FS_LOOKUP[ps.field_sample_name] || {};
        const colDate = fsMeta.collected_at ? String(fsMeta.collected_at).slice(0, 10) : "—";
        const geoLabel = fmtGeoid(fsMeta.geoid);
        const prepDate = ps.prep_date ? String(ps.prep_date).slice(0, 10) : "—";
        return `
          <div onclick="setQuickFilter('prepared_sample', '${ps.name}')" class="cursor-pointer rounded-xl p-3.5 border transition ${isSelected ? 'bg-[var(--secondary)] border-[var(--primary)] ring-1 ring-[var(--primary)]' : 'bg-[var(--background)] border-[var(--border)] hover:border-[var(--primary)]'}">
            <div class="flex items-center justify-between gap-2">
              <span class="font-mono font-bold text-sm text-[var(--foreground)]">${ps.name}</span>
              <span class="px-2 py-0.5 text-xs rounded-full bg-[var(--card)] border border-[var(--border)] font-mono">${recs.length} / ${totalAll} obs</span>
            </div>
            <div class="text-xs text-[var(--muted-foreground)] mt-1.5 space-y-0.5">
              <div><strong class="text-[var(--foreground)]">Prep / Run Date:</strong> <span class="font-mono text-[var(--foreground)]">${prepDate}</span> · <strong class="text-[var(--foreground)]">Method:</strong> ${ps.prep_method || '—'}</div>
              <div><strong class="text-[var(--foreground)]">Field Parent:</strong> <span class="font-mono">${ps.field_sample_name || '—'}</span> <span class="font-mono">(Collected: ${colDate} · GEOID: ${geoLabel})</span></div>
              <div><strong class="text-[var(--foreground)]">Domains:</strong> ${types}</div>
            </div>
            <div class="mt-2 pt-2 border-t border-[var(--border)] flex items-center justify-between text-xs font-mono">
              <span>${passCnt}P / ${failCnt}F</span>
              <span class="underline text-[var(--primary)]">${isSelected ? 'Active filter (click to clear)' : 'Filter by sample'}</span>
            </div>
          </div>
        `;
      }).join("");

      const byType = [
        { name: "Proximate Analysis", tbl: "proximate_record", tab: "proximate", qcDomain: "proximate", desc: "Moisture, Total Solids, Volatile Solids, Ash (% total weight)" },
        { name: "Calorimetry", tbl: "calorimetry_record", tab: "proximate", qcDomain: "proximate", desc: "Bomb calorimetry HHV runs & metadata" },
        { name: "Compositional Analysis", tbl: "compositional_record", tab: "compositional", qcDomain: "compositional", desc: "Glucan, Xylan, Lignin, Arabinan, Monomeric Sugars (% dw)" },
        { name: "Ultimate Analysis", tbl: "ultimate_record", tab: "compositional", qcDomain: "compositional", desc: "CHNSO combustion & ADF/Crude Fiber metrics" },
        { name: "XRD Crystallinity", tbl: "xrd_record", tab: "compositional", qcDomain: "compositional", desc: "Cellulose crystallinity index (%)" },
        { name: "ICP Elemental Analysis", tbl: "icp_record", tab: "elemental", qcDomain: "elemental", desc: "Inductively Coupled Plasma minerals (ppm)" },
        { name: "XRF Elemental Analysis", tbl: "xrf_record", tab: "elemental", qcDomain: "elemental", desc: "X-Ray Fluorescence multi-element profile (ppm)" },
        { name: "Pretreatment & Hydrolysis", tbl: "pretreatment_record", tab: "conversion", qcDomain: "pretreatment", desc: "Monomeric Glucose & Xylose yields across pretreatment chemistries" },
        { name: "Fermentation (Bioconversion)", tbl: "fermentation_record", tab: "conversion", qcDomain: "fermentation", desc: "3-HP & Ethanol titer/yield, sugar consumption (t0 -> tEOF), OD600" },
        { name: "Gasification", tbl: "gasification_record", tab: "conversion", qcDomain: "fermentation", desc: "Syngas H2/CO/CH4/CO2, combustible gas fraction vs. LFL, char & tar" }
      ].filter(t => resRecs.some(r => r.analysis_type === t.name));

      const typeRows = byType.map(t => {
        const recs = filtered.filter(r => r.analysis_type === t.name);
        const passCnt = recs.filter(r => r.qc_status === "pass").length;
        const failCnt = recs.filter(r => r.qc_status === "fail").length;
        const tabOut = ins && ins.outlier_screening && ins.outlier_screening.by_tab && ins.outlier_screening.by_tab[t.qcDomain];
        const flagCnt = tabOut ? tabOut.flagged_active : 0;
        const wMed = tabOut ? tabOut.within_rsd_median : null;
        return `
          <tr class="border-t border-[var(--border)] hover:bg-[var(--background)] transition text-xs">
            <td class="py-2.5 px-3 font-semibold text-[var(--foreground)]">${t.name} <span class="font-mono font-normal text-[var(--muted-foreground)]">(${t.tbl})</span></td>
            <td class="py-2.5 px-3 text-[var(--muted-foreground)]">${t.desc}</td>
            <td class="py-2.5 px-3 font-mono text-right font-semibold">${recs.length}</td>
            <td class="py-2.5 px-3 font-mono text-right">${passCnt}P / ${failCnt}F</td>
            <td class="py-2.5 px-3 font-mono text-right">
              <span>Within-RSD: <strong>${wMed !== null && wMed !== undefined ? fmtNum(wMed, 1) + '%' : 'n=1'}</strong></span>
              ${flagCnt > 0 ? `<a href="${QC_PAGE_FILENAME}?resource=${encRes}&domain=${t.qcDomain}" class="ml-2 px-1.5 py-0.5 rounded badge-warn text-[11px] font-bold hover:underline">⚑ ${flagCnt}</a>` : ""}
            </td>
            <td class="py-2.5 px-3 text-right">
              <button onclick="switchTab('${t.tab}')" class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)]">View Tab</button>
            </td>
          </tr>
        `;
      }).join("");

      return `
        ${benchHtml}

        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-4">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 class="text-base font-bold text-[var(--foreground)]">Sample Lineage: Field Sample Collection (Dates &amp; GEOID) &rarr; Prepared Samples</h2>
              <p class="text-xs text-[var(--muted-foreground)]">${fsList.length} Field Sample(s) processed into ${psList.length} Prepared Sample(s). Click any card to filter.</p>
            </div>
            <a href="resource_explorer_dashboard.html?resource=${encRes}" class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--foreground)] border border-[var(--border)] hover:border-[var(--primary)]">
              Compare by Collection / Prep Date in Explorer &rarr;
            </a>
          </div>
          ${fsCards ? `
            <div class="space-y-2">
              <div class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Field Samples (Collection Date &amp; County GEOID)</div>
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">${fsCards}</div>
            </div>
          ` : ''}
          <div class="space-y-2">
            <div class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Prepared Samples (Prep / Run Date &amp; Method)</div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              ${psCards || '<div class="text-xs text-[var(--muted-foreground)]">No prepared samples cataloged.</div>'}
            </div>
          </div>
        </div>

        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm overflow-x-auto">
          <h2 class="text-base font-bold text-[var(--foreground)] mb-3">Analytical &amp; Conversion Domain Coverage</h2>
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="text-xs font-semibold text-[var(--muted-foreground)] border-b border-[var(--border)]">
                <th class="py-2 px-3">Domain / Table</th>
                <th class="py-2 px-3">Measured Parameters</th>
                <th class="py-2 px-3 text-right">Observations</th>
                <th class="py-2 px-3 text-right">QC Split</th>
                <th class="py-2 px-3 text-right">Tech Repeatability</th>
                <th class="py-2 px-3 text-right">Explore</th>
              </tr>
            </thead>
            <tbody>${typeRows}</tbody>
          </table>
        </div>
      `;
    }

    function renderProximateTab(filtered) {
      const recs = filtered.filter(r => r.analysis_type === "Proximate Analysis" && r.value !== null);
      const calRecs = filtered.filter(r => r.analysis_type === "Calorimetry");
      if (recs.length === 0 && calRecs.length === 0) {
        return emptyStateHtml("Proximate Analysis & Calorimetry");
      }

      const groupKeyFn = r => state.proxGroupMode === "ps_exp"
        ? `${r.prepared_sample} · ${r.experiment}`
        : r.prepared_sample;

      const groups = Array.from(new Set(recs.map(groupKeyFn)));
      const params = ["moisture", "total solids", "volatile solids", "ash"];

      const massBalanceHtml = groups.map(g => {
        const gRecs = recs.filter(r => groupKeyFn(r) === g);
        const mStat = calcStats(gRecs.filter(r => r.parameter === "moisture").map(r => r.value));
        const tsStat = calcStats(gRecs.filter(r => r.parameter === "total solids").map(r => r.value));
        const vsStat = calcStats(gRecs.filter(r => r.parameter === "volatile solids").map(r => r.value));
        const ashStat = calcStats(gRecs.filter(r => r.parameter === "ash").map(r => r.value));

        const m = mStat.mean || 0;
        const vs = vsStat.mean || 0;
        const ash = ashStat.mean || 0;
        const sumWet = m + vs + ash;

        return `
          <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-3.5">
            <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
              <span class="font-mono font-semibold text-xs text-[var(--foreground)]">${g}</span>
              <span class="text-xs font-mono text-[var(--muted-foreground)]">
                Moisture (${fmtNum(m)}%) + VS (${fmtNum(vs)}%) + Ash (${fmtNum(ash)}%) = <strong class="text-[var(--foreground)]">${fmtNum(sumWet)}%</strong> | Total Solids = <strong class="text-[var(--foreground)]">${fmtNum(tsStat.mean)}%</strong>
              </span>
            </div>
            <div class="w-full h-5 rounded-lg bg-[var(--content)] overflow-hidden flex border border-[var(--border)]">
              <div style="width: ${Math.min(100, (m / Math.max(100, sumWet || 1)) * 100)}%" class="bg-[var(--primary)] h-full flex items-center justify-center text-xs text-[var(--primary-foreground)] font-mono truncate" title="Moisture: ${fmtNum(m)}%">${m > 8 ? 'M ' + fmtNum(m, 1) + '%' : ''}</div>
              <div style="width: ${Math.min(100, (vs / Math.max(100, sumWet || 1)) * 100)}%" class="bg-[var(--secondary)] h-full flex items-center justify-center text-xs text-[var(--secondary-foreground)] font-mono truncate border-l border-[var(--border)]" title="Volatile Solids: ${fmtNum(vs)}%">${vs > 8 ? 'VS ' + fmtNum(vs, 1) + '%' : ''}</div>
              <div style="width: ${Math.min(100, (ash / Math.max(100, sumWet || 1)) * 100)}%" class="bg-[var(--accent)] h-full flex items-center justify-center text-xs text-[var(--foreground)] font-mono truncate border-l border-[var(--border)]" title="Ash: ${fmtNum(ash)}%">${ash > 8 ? 'Ash ' + fmtNum(ash, 1) + '%' : ''}</div>
            </div>
          </div>
        `;
      }).join("");

      const paramCards = params.map(param => {
        const pRecs = recs.filter(r => r.parameter === param);
        if (pRecs.length === 0) return "";
        const rowsHtml = groups.map(g => {
          const gRecs = pRecs.filter(r => groupKeyFn(r) === g);
          if (gRecs.length === 0) return "";
          const st = calcStats(gRecs.map(r => r.value));
          const pct = Math.min(100, Math.max(2, st.mean || 0));
          const dots = st.vals.map(v => `<span class="inline-block px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] font-mono text-xs">${fmtNum(v)}%</span>`).join(" ");
          return `
            <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-3 space-y-1.5">
              <div class="flex items-center justify-between text-xs">
                <span class="font-mono font-semibold text-[var(--foreground)]">${g}</span>
                <span class="font-mono font-bold text-[var(--foreground)]">${fmtNum(st.mean)}% <span class="font-normal text-[var(--muted-foreground)]">± ${fmtNum(st.sd)} (n=${st.n})</span></span>
              </div>
              <div class="w-full h-2.5 rounded-full bg-[var(--content)] overflow-hidden">
                <div class="h-full rounded-full bg-[var(--primary)]" style="width: ${pct}%"></div>
              </div>
              <div class="flex flex-wrap items-center justify-between gap-1 pt-0.5 text-xs text-[var(--muted-foreground)]">
                <span>Replicates: ${dots}</span>
                <span class="font-mono">Range: ${fmtNum(st.min)}–${fmtNum(st.max)}%</span>
              </div>
            </div>
          `;
        }).join("");

        return `
          <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3">
            <div class="flex items-center justify-between border-b border-[var(--border)] pb-2">
              <h3 class="text-sm font-bold uppercase tracking-wide text-[var(--foreground)]">${param}</h3>
              <span class="text-xs font-mono text-[var(--muted-foreground)]">Unit: % total weight · ${pRecs.length} obs</span>
            </div>
            <div class="space-y-2.5">${rowsHtml}</div>
          </div>
        `;
      }).join("");

      const calHtml = calRecs.length ? `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-3">
          <h3 class="text-base font-bold text-[var(--foreground)]">Bomb Calorimetry Runs (${calRecs.length} calorimetry_record entries)</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            ${calRecs.map(r => `
              <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-3.5 space-y-1 text-xs">
                <div class="flex items-center justify-between font-mono">
                  <span class="font-bold text-[var(--foreground)]">Record: ${r.record_id}</span>
                  <span>${qcBadgeHtml(r.qc_status)}</span>
                </div>
                <div class="text-[var(--muted-foreground)]">Sample: <span class="font-mono text-[var(--foreground)]">${r.prepared_sample}</span> · Exp: <span class="font-mono">${r.experiment}</span></div>
                ${r.note ? `<div class="mt-1 p-2 rounded bg-[var(--card)] border border-[var(--border)] font-mono text-[var(--foreground)]">Note: "${r.note}"</div>` : ""}
              </div>
            `).join("")}
          </div>
        </div>
      ` : "";

      return `
        ${tabInsightBannerHtml("proximate")}
        ${recs.length ? `
          <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 class="text-base font-bold text-[var(--foreground)]">Wet-Basis Proximate Mass Balance Closure (${recs.length} Observations)</h2>
                <p class="text-xs text-[var(--muted-foreground)]">Moisture + Volatile Solids + Ash closure across prepared samples and drying protocols.</p>
              </div>
              <div class="inline-flex rounded-lg border border-[var(--border)] bg-[var(--background)] p-0.5">
                <button onclick="setSubMode('proxGroupMode', 'ps_exp')" class="px-3 py-1 rounded-md text-xs font-semibold ${state.proxGroupMode === 'ps_exp' ? 'bg-[var(--primary)] text-[var(--primary-foreground)]' : 'text-[var(--muted-foreground)]'}">By Sample × Experiment</button>
                <button onclick="setSubMode('proxGroupMode', 'ps')" class="px-3 py-1 rounded-md text-xs font-semibold ${state.proxGroupMode === 'ps' ? 'bg-[var(--primary)] text-[var(--primary-foreground)]' : 'text-[var(--muted-foreground)]'}">By Prepared Sample</button>
              </div>
            </div>
            <div class="space-y-2.5">${massBalanceHtml}</div>
          </div>
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">${paramCards}</div>
        ` : ""}
        ${calHtml}
      `;
    }

    function renderCompositionalTab(filtered) {
      const compRecs = filtered.filter(r => r.analysis_type === "Compositional Analysis" && r.value !== null);
      const ultRecs = filtered.filter(r => r.analysis_type === "Ultimate Analysis" && r.value !== null);
      const xrdRecs = filtered.filter(r => r.analysis_type === "XRD Crystallinity" && r.value !== null);

      if (compRecs.length === 0 && ultRecs.length === 0 && xrdRecs.length === 0) {
        return emptyStateHtml("Compositional, Ultimate & XRD Analysis");
      }

      const order = ["glucan", "glucose", "xylan", "xylose", "lignin", "lignin+", "arabinan", "arabinose"];
      const cardsHtml = order.map(param => {
        const pRecs = compRecs.filter(r => r.parameter === param);
        if (pRecs.length === 0) return "";
        const st = calcStats(pRecs.map(r => r.value));
        const pct = Math.min(100, ((st.mean || 0) / 45) * 100);
        const repsHtml = pRecs.slice(0, 8).map(r => `<span class="px-2 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] font-mono text-xs">${r.prepared_sample} Rep ${r.replicate}: ${fmtNum(r.value)}%</span>`).join(" ");
        return `
          <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-4 space-y-2">
            <div class="flex items-center justify-between">
              <div>
                <span class="text-sm font-bold uppercase text-[var(--foreground)]">${param}</span>
                <span class="ml-2 text-xs text-[var(--muted-foreground)] font-mono">(% dw · n=${st.n})</span>
              </div>
              <div class="text-sm font-mono font-bold text-[var(--foreground)]">
                ${fmtNum(st.mean)}% <span class="text-xs font-normal text-[var(--muted-foreground)]">± ${fmtNum(st.sd)}%</span>
              </div>
            </div>
            <div class="w-full h-3 rounded-full bg-[var(--content)] overflow-hidden">
              <div class="h-full rounded-full bg-[var(--primary)]" style="width: ${pct}%"></div>
            </div>
            <div class="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs text-[var(--muted-foreground)]">
              <div class="flex flex-wrap gap-1.5">${repsHtml}</div>
              <span class="font-mono">Range: ${fmtNum(st.min)}–${fmtNum(st.max)}%</span>
            </div>
          </div>
        `;
      }).join("");

      const gMean = calcStats(compRecs.filter(r => r.parameter === "glucan").map(r => r.value)).mean || 0;
      const xMean = calcStats(compRecs.filter(r => r.parameter === "xylan").map(r => r.value)).mean || 0;
      const lMean = calcStats(compRecs.filter(r => r.parameter === "lignin" || r.parameter === "lignin+").map(r => r.value)).mean || 0;
      const aMean = calcStats(compRecs.filter(r => r.parameter === "arabinan").map(r => r.value)).mean || 0;
      const polySum = gMean + xMean + lMean + aMean;
      const remSum = Math.max(0, 100 - polySum);

      const ultHtml = ultRecs.length ? `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-3">
          <h3 class="text-base font-bold text-[var(--foreground)]">Ultimate CHNSO &amp; Fiber Analysis (${ultRecs.length} Observations)</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            ${Array.from(new Set(ultRecs.map(r => r.parameter))).map(p => {
              const pRecs = ultRecs.filter(r => r.parameter === p);
              const st = calcStats(pRecs.map(r => r.value));
              return `
                <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-3.5 space-y-1">
                  <div class="flex justify-between text-xs">
                    <span class="font-bold uppercase text-[var(--foreground)]">${p}</span>
                    <span class="font-mono font-bold">${fmtNum(st.mean)} ${pRecs[0].unit || '%'} (n=${st.n})</span>
                  </div>
                  <div class="text-xs font-mono text-[var(--muted-foreground)]">Range: ${fmtNum(st.min)}–${fmtNum(st.max)}</div>
                </div>
              `;
            }).join("")}
          </div>
        </div>
      ` : "";

      const xrdHtml = xrdRecs.length ? `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-2">
          <h3 class="text-base font-bold text-[var(--foreground)]">XRD Crystallinity (${xrdRecs.length} Observations)</h3>
          <div class="flex flex-wrap gap-2">
            ${xrdRecs.map(r => `<span class="px-2.5 py-1 rounded-lg bg-[var(--background)] border border-[var(--border)] font-mono text-xs">${r.prepared_sample} Rep ${r.replicate}: <strong>${fmtNum(r.value)}%</strong></span>`).join("")}
          </div>
        </div>
      ` : "";

      return `
        ${tabInsightBannerHtml("compositional")}
        ${compRecs.length ? `
          <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-4">
            <div>
              <h2 class="text-base font-bold text-[var(--foreground)]">Compositional Cell-Wall Characterization (${compRecs.length} Observations)</h2>
              <p class="text-xs text-[var(--muted-foreground)] mt-0.5">Structural polysaccharides and Klason lignin (% dry weight).</p>
            </div>
            <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-4">
              <div class="flex flex-wrap items-center justify-between text-xs mb-2 gap-2">
                <span class="font-semibold text-[var(--foreground)]">Dry-Matter Structural Polymer Closure</span>
                <span class="font-mono text-[var(--muted-foreground)]">Glucan (${fmtNum(gMean)}%) + Xylan (${fmtNum(xMean)}%) + Lignin (${fmtNum(lMean)}%)${aMean ? ' + Arabinan (' + fmtNum(aMean) + '%)' : ''} = <strong>${fmtNum(polySum)}% dw</strong></span>
              </div>
              <div class="w-full h-6 rounded-lg bg-[var(--content)] overflow-hidden flex border border-[var(--border)] text-xs font-mono">
                <div style="width: ${Math.min(100, lMean)}%" class="bg-[var(--primary)] text-[var(--primary-foreground)] flex items-center justify-center truncate" title="Lignin: ${fmtNum(lMean)}%">${lMean > 6 ? 'Lig ' + fmtNum(lMean, 1) + '%' : ''}</div>
                <div style="width: ${Math.min(100, gMean)}%" class="bg-[var(--secondary)] text-[var(--secondary-foreground)] flex items-center justify-center border-l border-[var(--border)] truncate" title="Glucan: ${fmtNum(gMean)}%">${gMean > 6 ? 'Glu ' + fmtNum(gMean, 1) + '%' : ''}</div>
                <div style="width: ${Math.min(100, xMean + aMean)}%" class="bg-[var(--accent)] text-[var(--foreground)] flex items-center justify-center border-l border-[var(--border)] truncate" title="Hemicellulose (Xylan+Arabinan): ${fmtNum(xMean + aMean)}%">${(xMean + aMean) > 5 ? 'Xyl ' + fmtNum(xMean + aMean, 1) + '%' : ''}</div>
                <div style="width: ${Math.min(100, remSum)}%" class="bg-[var(--card)] text-[var(--muted-foreground)] flex items-center justify-center border-l border-[var(--border)] truncate">Ash + Extractives / Protein (${fmtNum(remSum, 1)}%)</div>
              </div>
            </div>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">${cardsHtml}</div>
          </div>
        ` : ""}
        ${ultHtml}
        ${xrdHtml}
      `;
    }

    function renderElementalTab(filtered) {
      const allElemRecs = filtered.filter(r =>
        (r.analysis_type === "ICP Elemental Analysis" || r.analysis_type === "XRF Elemental Analysis") &&
        r.value !== null && r.parameter !== "(metadata only)"
      );
      if (allElemRecs.length === 0) return emptyStateHtml("ICP & XRF Elemental Analysis");

      const recs = allElemRecs.filter(r => {
        if (state.elemSourceMode === "icp") return r.analysis_type === "ICP Elemental Analysis";
        if (state.elemSourceMode === "xrf") return r.analysis_type === "XRF Elemental Analysis";
        return true;
      });

      const params = Array.from(new Set(recs.map(r => r.parameter)));
      const statsList = params.map(p => {
        const pRecs = recs.filter(r => r.parameter === p);
        const st = calcStats(pRecs.map(r => r.value));
        return { param: p, label: ELEM_NAMES[p] || `Element ${p}`, st, recs: pRecs };
      }).sort((a, b) => (b.st.mean || 0) - (a.st.mean || 0));

      const maxElemVal = statsList.length ? Math.max(1000, statsList[0].st.mean || 1000) : 50000;

      const renderElemRow = (item, maxRef, useLog) => {
        const val = item.st.mean || 0;
        let pct = 2;
        if (useLog) {
          pct = val > 0 ? Math.min(100, (Math.log10(val + 1) / Math.log10(maxElemVal + 10)) * 100) : 2;
        } else {
          pct = maxRef > 0 ? Math.min(100, Math.max(2, (val / maxRef) * 100)) : 2;
        }
        return `
          <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-3 space-y-1.5">
            <div class="flex items-center justify-between text-xs">
              <span class="font-bold text-[var(--foreground)]">${item.label}</span>
              <span class="font-mono font-bold text-[var(--foreground)]">${fmtNum(val)} ppm <span class="font-normal text-[var(--muted-foreground)]">(${fmtNum(val / 10000, 3)}% dw · n=${item.st.n})</span></span>
            </div>
            <div class="w-full h-2.5 rounded-full bg-[var(--content)] overflow-hidden">
              <div class="h-full rounded-full bg-[var(--primary)]" style="width: ${pct}%"></div>
            </div>
            <div class="flex items-center justify-between text-[11px] font-mono text-[var(--muted-foreground)]">
              <span>Range: ${fmtNum(item.st.min)}–${fmtNum(item.st.max)} ppm</span>
              <span>SD: ±${fmtNum(item.st.sd)} ppm</span>
            </div>
          </div>
        `;
      };

      let bodyHtml = "";
      if (state.icpScaleMode === "split") {
        const macro = statsList.filter(x => (x.st.mean || 0) >= 500);
        const trace = statsList.filter(x => (x.st.mean || 0) < 500);
        const maxMacro = macro.length ? (macro[0].st.mean || 50000) : 50000;
        const maxTrace = trace.length ? Math.max(50, trace[0].st.mean || 300) : 300;
        bodyHtml = `
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 space-y-2.5">
              <h3 class="text-sm font-bold text-[var(--foreground)] border-b border-[var(--border)] pb-2">Macro Elements (&ge; 500 ppm · ${macro.length} elements)</h3>
              ${macro.map(x => renderElemRow(x, maxMacro, false)).join("") || '<div class="text-xs text-[var(--muted-foreground)]">No elements &ge; 500 ppm.</div>'}
            </div>
            <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 space-y-2.5">
              <h3 class="text-sm font-bold text-[var(--foreground)] border-b border-[var(--border)] pb-2">Trace &amp; Heavy Metals (&lt; 500 ppm · ${trace.length} elements)</h3>
              ${trace.map(x => renderElemRow(x, maxTrace, false)).join("") || '<div class="text-xs text-[var(--muted-foreground)]">No elements &lt; 500 ppm.</div>'}
            </div>
          </div>
        `;
      } else {
        const useLog = state.icpScaleMode === "log";
        bodyHtml = `
          <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
            ${statsList.map(x => renderElemRow(x, maxElemVal, useLog)).join("")}
          </div>
        `;
      }

      return `
        ${tabInsightBannerHtml("elemental")}
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="text-base font-bold text-[var(--foreground)]">ICP &amp; XRF Elemental Profile (${recs.length} Observations · ${statsList.length} Elements)</h2>
            <p class="text-xs text-[var(--muted-foreground)] mt-0.5">Standardized IUPAC chemical symbol notation with Macro (&ge;500 ppm) vs. Trace (&lt;500 ppm) split.</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <div class="inline-flex rounded-lg border border-[var(--border)] bg-[var(--background)] p-0.5">
              <button onclick="setSubMode('elemSourceMode', 'all')" class="px-2.5 py-1 rounded-md text-xs font-semibold ${state.elemSourceMode === 'all' ? 'bg-[var(--primary)] text-[var(--primary-foreground)]' : 'text-[var(--muted-foreground)]'}">All (${allElemRecs.length})</button>
              <button onclick="setSubMode('elemSourceMode', 'icp')" class="px-2.5 py-1 rounded-md text-xs font-semibold ${state.elemSourceMode === 'icp' ? 'bg-[var(--primary)] text-[var(--primary-foreground)]' : 'text-[var(--muted-foreground)]'}">ICP Only</button>
              <button onclick="setSubMode('elemSourceMode', 'xrf')" class="px-2.5 py-1 rounded-md text-xs font-semibold ${state.elemSourceMode === 'xrf' ? 'bg-[var(--primary)] text-[var(--primary-foreground)]' : 'text-[var(--muted-foreground)]'}">XRF Only</button>
            </div>
            <div class="inline-flex rounded-lg border border-[var(--border)] bg-[var(--background)] p-0.5">
              <button onclick="setSubMode('icpScaleMode', 'split')" class="px-2.5 py-1 rounded-md text-xs font-semibold ${state.icpScaleMode === 'split' ? 'bg-[var(--primary)] text-[var(--primary-foreground)]' : 'text-[var(--muted-foreground)]'}">Split Macro/Trace</button>
              <button onclick="setSubMode('icpScaleMode', 'log')" class="px-2.5 py-1 rounded-md text-xs font-semibold ${state.icpScaleMode === 'log' ? 'bg-[var(--primary)] text-[var(--primary-foreground)]' : 'text-[var(--muted-foreground)]'}">Log10</button>
              <button onclick="setSubMode('icpScaleMode', 'linear')" class="px-2.5 py-1 rounded-md text-xs font-semibold ${state.icpScaleMode === 'linear' ? 'bg-[var(--primary)] text-[var(--primary-foreground)]' : 'text-[var(--muted-foreground)]'}">Linear</button>
            </div>
          </div>
        </div>
        ${bodyHtml}
      `;
    }

    function renderConversionTab(filtered) {
      const ptRecs = filtered.filter(r => r.analysis_type === "Pretreatment & Hydrolysis");
      const fermRecs = filtered.filter(r => r.analysis_type === "Fermentation (Bioconversion)");
      const gasRecs = filtered.filter(r => r.analysis_type === "Gasification");

      if (ptRecs.length === 0 && fermRecs.length === 0 && gasRecs.length === 0) {
        return emptyStateHtml("Pretreatment, Fermentation & Gasification");
      }

      let ptHtml = "";
      if (ptRecs.length > 0 && (state.convSubTab === "all" || state.convSubTab === "pt")) {
        const condKey = r => `${r.pt_method} + ${r.eh_method} (${r.vessel})`;
        const conds = Array.from(new Set(ptRecs.map(condKey)));
        const condCards = conds.map(c => {
          const cRecs = ptRecs.filter(r => condKey(r) === c);
          const gluRecs = cRecs.filter(r => r.parameter === "glucose_yld" && r.value !== null);
          const xylRecs = cRecs.filter(r => r.parameter === "xylose_yld" && r.value !== null);
          const gSt = calcStats(gluRecs.map(r => r.value));
          const xSt = calcStats(xylRecs.map(r => r.value));
          return `
            <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-4 space-y-3">
              <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-2">
                <span class="font-mono font-bold text-sm text-[var(--foreground)]">${c}</span>
                <span class="text-xs font-mono text-[var(--muted-foreground)]">${cRecs.length} obs (${cRecs.filter(r => r.qc_status === 'pass').length}P / ${cRecs.filter(r => r.qc_status === 'fail').length}F)</span>
              </div>
              <div class="space-y-1">
                <div class="flex justify-between text-xs">
                  <span class="font-semibold text-[var(--foreground)]">Glucose Yield (% of glucan)</span>
                  <span class="font-mono font-bold">${fmtNum(gSt.mean)}% <span class="font-normal text-[var(--muted-foreground)]">± ${fmtNum(gSt.sd)}% (n=${gSt.n})</span></span>
                </div>
                <div class="w-full h-3 rounded-full bg-[var(--content)] overflow-hidden">
                  <div class="h-full rounded-full bg-[var(--primary)]" style="width: ${Math.min(100, gSt.mean || 0)}%"></div>
                </div>
              </div>
              <div class="space-y-1">
                <div class="flex justify-between text-xs">
                  <span class="font-semibold text-[var(--foreground)]">Xylose Yield (% of xylan)</span>
                  <span class="font-mono font-bold">${fmtNum(xSt.mean)}% <span class="font-normal text-[var(--muted-foreground)]">± ${fmtNum(xSt.sd)}% (n=${xSt.n})</span></span>
                </div>
                <div class="w-full h-3 rounded-full bg-[var(--content)] overflow-hidden">
                  <div class="h-full rounded-full bg-amber-500" style="width: ${Math.min(100, ((xSt.mean || 0) / 110) * 100)}%"></div>
                </div>
              </div>
            </div>
          `;
        }).join("");

        ptHtml = `
          ${tabInsightBannerHtml("pretreatment")}
          <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-4">
            <h2 class="text-base font-bold text-[var(--foreground)]">Pretreatment &amp; Enzymatic Hydrolysis (${ptRecs.length} Observations)</h2>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">${condCards}</div>
          </div>
        `;
      }

      let fermHtml = "";
      if (fermRecs.length > 0 && (state.convSubTab === "all" || state.convSubTab === "ferm")) {
        const groupKey = r => `${r.prepared_sample} · ${r.experiment}`;
        const groups = Array.from(new Set(fermRecs.map(groupKey)));
        const bioconvCards = groups.map(g => {
          const gRecs = fermRecs.filter(r => groupKey(r) === g);
          const hasEtoh = gRecs.some(r => r.parameter === "etohtiter" || r.parameter === "etohyield");
          const titerParam = hasEtoh ? "etohtiter" : "3hptiter";
          const yieldParam = hasEtoh ? "etohyield" : "3hpyield";
          const prodLabel = hasEtoh ? "Ethanol" : "3-HP";

          const tSt = calcStats(gRecs.filter(r => r.parameter === titerParam).map(r => r.value));
          const ySt = calcStats(gRecs.filter(r => r.parameter === yieldParam).map(r => r.value));
          const scSt = calcStats(gRecs.filter(r => r.parameter === "sugar_cons").map(r => r.value));
          const glu0 = calcStats(gRecs.filter(r => r.parameter === "gluconct0").map(r => r.value));
          const gluE = calcStats(gRecs.filter(r => r.parameter === "gluconcteof").map(r => r.value));
          const xyl0 = calcStats(gRecs.filter(r => r.parameter === "xylconct0").map(r => r.value));
          const xylE = calcStats(gRecs.filter(r => r.parameter === "xylconcteof").map(r => r.value));
          const sug0 = calcStats(gRecs.filter(r => r.parameter === "sugart0").map(r => r.value));
          const sugE = calcStats(gRecs.filter(r => r.parameter === "sugarteof").map(r => r.value));
          const strain = gRecs[0].strain || "Engineered Strain";

          return `
            <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-4 space-y-3">
              <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-2">
                <span class="font-mono font-bold text-sm text-[var(--foreground)]">${g}</span>
                <span class="text-xs font-mono text-[var(--muted-foreground)]">Strain: ${strain}</span>
              </div>
              <div class="grid grid-cols-3 gap-2.5">
                <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2.5">
                  <div class="text-xs text-[var(--muted-foreground)]">${prodLabel} Titer</div>
                  <div class="text-sm font-bold font-mono text-[var(--foreground)]">${fmtNum(tSt.mean)} g/L <span class="text-xs font-normal">±${fmtNum(tSt.sd)}</span></div>
                </div>
                <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2.5">
                  <div class="text-xs text-[var(--muted-foreground)]">${prodLabel} Yield</div>
                  <div class="text-sm font-bold font-mono text-[var(--foreground)]">${fmtNum(ySt.mean)}% <span class="text-xs font-normal">±${fmtNum(ySt.sd)}</span></div>
                </div>
                <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2.5">
                  <div class="text-xs text-[var(--muted-foreground)]">Sugar Consumed</div>
                  <div class="text-sm font-bold font-mono text-[var(--foreground)]">${fmtNum(scSt.mean)}%</div>
                </div>
              </div>
              <div class="grid grid-cols-3 gap-2 text-xs font-mono">
                <div class="p-2 rounded bg-[var(--card)] border border-[var(--border)]">
                  <div class="text-[var(--muted-foreground)]">Glucose (t0&rarr;tEOF)</div>
                  <div class="font-bold text-[var(--foreground)]">${fmtNum(glu0.mean)} &rarr; ${fmtNum(gluE.mean)} g/L</div>
                </div>
                <div class="p-2 rounded bg-[var(--card)] border border-[var(--border)]">
                  <div class="text-[var(--muted-foreground)]">Xylose (t0&rarr;tEOF)</div>
                  <div class="font-bold text-[var(--foreground)]">${fmtNum(xyl0.mean)} &rarr; ${fmtNum(xylE.mean)} g/L</div>
                </div>
                <div class="p-2 rounded bg-[var(--card)] border border-[var(--border)]">
                  <div class="text-[var(--muted-foreground)]">Total Sugar</div>
                  <div class="font-bold text-[var(--foreground)]">${fmtNum(sug0.mean)} &rarr; ${fmtNum(sugE.mean)} g/L</div>
                </div>
              </div>
            </div>
          `;
        }).join("");

        fermHtml = `
          ${tabInsightBannerHtml("fermentation")}
          <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-4">
            <h2 class="text-base font-bold text-[var(--foreground)]">Fermentation / Bioconversion (${fermRecs.length} Observations)</h2>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">${bioconvCards}</div>
          </div>
        `;
      }

      let gasHtml = "";
      if (gasRecs.length > 0 && (state.convSubTab === "all" || state.convSubTab === "gas")) {
        const gasGroups = Array.from(new Set(gasRecs.map(r => `${r.prepared_sample} · ${r.experiment}`)));
        const gasCards = gasGroups.map(g => {
          const gRecs = gasRecs.filter(r => `${r.prepared_sample} · ${r.experiment}` === g);
          const pStat = p => calcStats(gRecs.filter(r => r.parameter === p).map(r => r.value));
          const h2 = pStat("h2");
          const co = pStat("co");
          const ch4 = pStat("ch4");
          const co2 = pStat("co2");
          const comb = pStat("comb");
          const lfl = pStat("lfl");
          const ta = pStat("ta");
          return `
            <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-4 space-y-3">
              <div class="flex items-center justify-between border-b border-[var(--border)] pb-2">
                <span class="font-mono font-bold text-sm text-[var(--foreground)]">${g}</span>
                <span class="text-xs font-mono text-[var(--muted-foreground)]">Bed Temp: ${fmtNum(ta.mean)}°C</span>
              </div>
              <div class="grid grid-cols-4 gap-2 text-xs font-mono">
                <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2"><div class="text-[var(--muted-foreground)]">H₂ (ppm)</div><div class="font-bold text-sm">${fmtNum(h2.mean, 0)}</div></div>
                <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2"><div class="text-[var(--muted-foreground)]">CO (ppm)</div><div class="font-bold text-sm">${fmtNum(co.mean, 0)}</div></div>
                <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2"><div class="text-[var(--muted-foreground)]">CH₄ (ppm)</div><div class="font-bold text-sm">${fmtNum(ch4.mean, 0)}</div></div>
                <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2"><div class="text-[var(--muted-foreground)]">CO₂ (ppm)</div><div class="font-bold text-sm">${fmtNum(co2.mean, 0)}</div></div>
              </div>
              <div class="text-xs font-mono text-[var(--muted-foreground)]">
                Combustible Gas: <strong class="text-[var(--foreground)]">${fmtNum(comb.mean)}%</strong> vs LFL <strong class="text-[var(--foreground)]">${fmtNum(lfl.mean)}%</strong>
              </div>
            </div>
          `;
        }).join("");

        gasHtml = `
          <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-4">
            <h2 class="text-base font-bold text-[var(--foreground)]">Thermochemical Gasification (${gasRecs.length} Observations)</h2>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">${gasCards}</div>
          </div>
        `;
      }

      const subBtns = [
        { id: "all", label: `All Conversion (${ptRecs.length + fermRecs.length + gasRecs.length})` },
        { id: "pt", label: `Pretreatment & EH (${ptRecs.length})` },
        { id: "ferm", label: `Fermentation (${fermRecs.length})` },
        { id: "gas", label: `Gasification (${gasRecs.length})` }
      ];

      return `
        <div class="flex flex-wrap items-center gap-1.5">
          ${subBtns.map(b => `
            <button onclick="setSubMode('convSubTab', '${b.id}')" class="px-3 py-1.5 rounded-lg text-xs font-semibold border ${state.convSubTab === b.id ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]' : 'bg-[var(--card)] text-[var(--muted-foreground)] border-[var(--border)] hover:text-[var(--foreground)]'}">${b.label}</button>
          `).join("")}
        </div>
        ${ptHtml}
        ${fermHtml}
        ${gasHtml}
      `;
    }

    function syncUrl() {
      try {
        const u = new URL(window.location.href);
        u.searchParams.set("resource", state.resource);
        u.searchParams.set("tab", state.tab);
        window.history.replaceState({}, "", u.toString());
      } catch (_) {}
    }

    function render() {
      updateHeader();
      renderAiInsightsPanel();
      const filtered = getFilteredRecords();
      renderKpiStrip(filtered);

      const container = document.getElementById("tab-content");
      if (state.tab === "overview") container.innerHTML = renderOverviewTab(filtered);
      else if (state.tab === "proximate") container.innerHTML = renderProximateTab(filtered);
      else if (state.tab === "compositional") container.innerHTML = renderCompositionalTab(filtered);
      else if (state.tab === "elemental") container.innerHTML = renderElementalTab(filtered);
      else if (state.tab === "conversion") container.innerHTML = renderConversionTab(filtered);
      syncUrl();
    }

    window.selectResource = function(resName) {
      if (!RECORDS_BY_RESOURCE[resName]) return;
      state.resource = resName;
      state.prepared_sample = "all";
      state.field_sample = "all";
      initResourceSwitcher();
      initFiltersForResource();
      render();
    };

    window.switchTab = function(tabName) {
      state.tab = tabName;
      render();
    };

    window.setSubMode = function(key, val) {
      state[key] = val;
      render();
    };

    window.setQuickFilter = function(key, val) {
      state[key] = state[key] === val ? "all" : val;
      if (key === "prepared_sample") {
        document.getElementById("flt-prepared-sample").value = state.prepared_sample;
      }
      render();
    };

    document.getElementById("flt-resource").addEventListener("change", e => window.selectResource(e.target.value));
    document.getElementById("btn-prev-res").addEventListener("click", () => {
      const idx = ACTIVE_RESOURCES.indexOf(state.resource);
      window.selectResource(ACTIVE_RESOURCES[(idx - 1 + ACTIVE_RESOURCES.length) % ACTIVE_RESOURCES.length]);
    });
    document.getElementById("btn-next-res").addEventListener("click", () => {
      const idx = ACTIVE_RESOURCES.indexOf(state.resource);
      window.selectResource(ACTIVE_RESOURCES[(idx + 1) % ACTIVE_RESOURCES.length]);
    });
    document.getElementById("flt-prepared-sample").addEventListener("change", e => {
      state.prepared_sample = e.target.value;
      render();
    });

    document.querySelectorAll(".qc-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        state.qc_status = btn.dataset.qc;
        document.querySelectorAll(".qc-btn").forEach(b => {
          b.className = b.dataset.qc === state.qc_status
            ? "qc-btn px-2.5 py-1 rounded-md text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)]"
            : "qc-btn px-2.5 py-1 rounded-md text-xs font-medium text-[var(--muted-foreground)]";
        });
        render();
      });
    });

    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        state.tab = btn.dataset.tab;
        render();
      });
    });

    document.getElementById("btn-toggle-ai").addEventListener("click", () => {
      state.showAiPanel = !state.showAiPanel;
      document.getElementById("btn-toggle-ai").textContent = state.showAiPanel ? "✨ Hide AI Brief" : "✨ Show AI Brief";
      renderAiInsightsPanel();
    });

    document.getElementById("btn-reset-filters").addEventListener("click", () => {
      state.prepared_sample = "all";
      state.field_sample = "all";
      state.qc_status = "all";
      document.querySelectorAll(".qc-btn").forEach(b => {
        b.className = b.dataset.qc === "all"
          ? "qc-btn px-2.5 py-1 rounded-md text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)]"
          : "qc-btn px-2.5 py-1 rounded-md text-xs font-medium text-[var(--muted-foreground)]";
      });
      initFiltersForResource();
      render();
    });

    document.getElementById("btn-theme-toggle").addEventListener("click", () => {
      const htmlEl = document.documentElement;
      const next = htmlEl.getAttribute("data-theme") === "dark" ? "light" : "dark";
      htmlEl.setAttribute("data-theme", next);
      document.getElementById("btn-theme-toggle").textContent = next === "dark" ? "☀️ Light Mode" : "🌙 Dark Mode";
    });

    document.getElementById("btn-download-csv").addEventListener("click", () => {
      const filtered = getFilteredRecords();
      const cols = ["resource_name", "record_id", "analysis_type", "prepared_sample", "field_sample", "prep_method", "experiment", "parameter", "value", "unit", "replicate", "pt_method", "eh_method", "vessel", "well_or_block", "qc_status", "note"];
      const csv = [
        cols.join(","),
        ...filtered.map(r => cols.map(c => `"${String(r[c] ?? '').replace(/"/g, '""')}"`).join(","))
      ].join("\\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${state.resource.replace(/\\s+/g, "_")}_characterization.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });

    initResourceSwitcher();
    initFiltersForResource();
    render();
  </script>
</body>
</html>
"""
    return (
        html_template.replace("__SHARED_CSS__", SHARED_CSS)
        .replace("__TITLE_PREFIX__", title_prefix)
        .replace("__DATA_JSON__", data_json)
        .replace("__DEFAULT_RESOURCE__", json.dumps(default_resource))
        .replace("__QC_PAGE_FILENAME__", qc_page_filename)
        .replace("__QC_PAGE_FILENAME_JSON__", json.dumps(qc_page_filename))
    )


def build_qc_outlier_dashboard_html(
    bundle: dict[str, Any],
    default_resource: str = "almond hulls",
    char_page_filename: str = "resource_analysis_dashboard.html",
) -> str:
    """Compile Page 2: Dedicated Statistical Precision, Candidate Outlier Screening & Lab Notes Audit."""
    data_json = json.dumps(bundle, separators=(",", ":"))
    single_res = bundle.get("single_resource")
    if single_res:
        default_resource = single_res.lower()
    title_prefix = single_res.title() if single_res else "All-Resources"

    html_template = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BioCirV — __TITLE_PREFIX__ Statistical QC, Replicate Precision &amp; Lab Notes Audit (Page 2)</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>__SHARED_CSS__</style>
</head>
<body class="bg-[var(--background)] text-[var(--foreground)] antialiased p-3 sm:p-5">
  <div class="max-w-7xl mx-auto space-y-4">

    <!-- Shared Modular Suite Navigation Bar -->
    <nav class="bg-[var(--card)] border border-[var(--border)] rounded-xl px-3.5 py-2.5 shadow-sm flex flex-wrap items-center justify-between gap-2 text-xs">
      <div class="flex flex-wrap items-center gap-1.5">
        <span class="font-bold uppercase tracking-wider text-[var(--muted-foreground)] mr-1">BioCirV Suite:</span>
        <a id="nav-page-char" href="__CHAR_PAGE_FILENAME__" class="px-3 py-1.5 rounded-lg font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)] transition">
          1. Characterization &amp; AI Brief
        </a>
        <a id="nav-page-qc" href="resource_qc_outlier_dashboard.html" class="px-3 py-1.5 rounded-lg font-semibold bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm flex items-center gap-1.5">
          <span>2. Statistical QC &amp; Lab Notes Audit</span>
          <span id="nav-qc-badge" class="px-1.5 py-0.2 rounded-full text-[11px] font-mono bg-white/20"></span>
        </a>
        <a id="nav-page-explorer" href="resource_explorer_dashboard.html" class="px-3 py-1.5 rounded-lg font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)] transition">
          3. Multi-Resource Side-by-Side Explorer
        </a>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <a href="../audit/db_environment_drift_dashboard.html" class="px-2.5 py-1 rounded-lg font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] border border-transparent hover:border-[var(--border)]">
          DB Drift Audit (Local/Staging/Prod)
        </a>
        <a id="nav-page-monolith" href="resource_analysis_dashboard_v1_monolith.html" class="px-2.5 py-1 rounded-lg font-mono text-[11px] text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
          v1 Monolith
        </a>
      </div>
    </nav>

    <!-- Header & Statistical Screening Controls -->
    <header class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 sm:p-5 shadow-sm space-y-3.5">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-1 flex-1 min-w-[260px]">
          <div class="flex flex-wrap items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block"></span>
            <h1 id="hdr-title" class="text-lg sm:text-xl font-bold text-[var(--foreground)]">BioCirV — Statistical Replicate Precision &amp; Candidate Outlier Audit</h1>
            <span id="hdr-code-badge" class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-[var(--primary)] text-[var(--primary-foreground)] font-mono"></span>
            <span id="hdr-portal-badge" class="px-2.5 py-0.5 text-xs font-semibold rounded-full"></span>
          </div>
          <p id="hdr-desc" class="text-xs text-[var(--muted-foreground)]">
            Two-sided Dixon's Q (&alpha;=0.05, n&ge;3), Within-Group vs. Between-Group RSD, &gt;3&times;SD<sub>pooled</sub> replicate screening, Portal/QC status filtering, and Analyst QC Decision-Making Workbench.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <button id="btn-anon-analyst" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90">
            🔒 Hide Analysts
          </button>
          <button id="btn-theme-toggle" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90">
            ☀️ Light Mode
          </button>
          <button id="btn-export-flagged-csv" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90">
            ⬇ Export Flagged Groups CSV
          </button>
          <button id="btn-download-records-csv" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90">
            ⬇ Export Records CSV
          </button>
        </div>
      </div>

      <!-- Resource, Portal/QC Status, Sample, Experiment & Trace Cutoff Controls -->
      <div class="pt-3 border-t border-[var(--border)] flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-2.5">
          <div id="resource-switcher-wrap" class="flex items-center gap-1.5">
            <label for="flt-resource" class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Resource:</label>
            <button id="btn-prev-res" class="px-2 py-1 rounded-lg text-xs font-bold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">&larr;</button>
            <select id="flt-resource" class="rounded-lg px-2.5 py-1.5 text-xs sm:text-sm font-bold border min-w-[220px]"></select>
            <button id="btn-next-res" class="px-2 py-1 rounded-lg text-xs font-bold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">&rarr;</button>
          </div>

          <div class="flex items-center gap-1.5">
            <label for="flt-portal-qc" class="text-xs font-bold uppercase tracking-wider text-[var(--primary)]">QC / Portal Filter:</label>
            <select id="flt-portal-qc" class="rounded-lg px-2.5 py-1.5 text-xs font-semibold border border-[var(--primary)]/50 min-w-[215px]">
              <option value="all">All Statuses &amp; QC (Raw + Pass/Fail)</option>
              <option value="portal_compliant">Portal Compliant Only (qc_pass=pass &amp; Active)</option>
              <option value="qc_pass">qc_pass = pass Only (Unquarantined)</option>
              <option value="qc_fail">qc_pass = fail Only (Quarantined)</option>
            </select>
          </div>

          <div class="flex items-center gap-1.5">
            <label for="flt-prepared-sample" class="text-xs font-semibold text-[var(--muted-foreground)]">Sample:</label>
            <select id="flt-prepared-sample" class="rounded-lg px-2.5 py-1.5 text-xs font-medium border min-w-[150px]"></select>
          </div>

          <div class="flex items-center gap-1.5">
            <label for="flt-experiment" class="text-xs font-semibold text-[var(--muted-foreground)]">Experiment:</label>
            <select id="flt-experiment" class="rounded-lg px-2.5 py-1.5 text-xs font-medium border min-w-[130px]"></select>
          </div>

          <button id="btn-reset-filters" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">
            Reset
          </button>
        </div>

        <label class="inline-flex items-center gap-2 text-xs font-semibold text-[var(--foreground)] cursor-pointer select-none bg-[var(--background)] px-3 py-1.5 rounded-lg border border-[var(--border)]" title="Suppress outlier flags on low-abundance elemental data (<100 ppm for ICP/XRF) and trace sugars (<0.5% dw or <0.5 g/L)">
          <input id="chk-suppress-trace" type="checkbox" checked class="rounded border-[var(--border)] text-[var(--primary)]" />
          <span>Suppress Low-Abundance Trace Flags (&lt;100 ppm ICP/XRF, &lt;0.5% wt)</span>
        </label>
      </div>

      <!-- Analysis Domain Filter Pills -->
      <div class="pt-3 border-t border-[var(--border)] flex flex-wrap items-center gap-1.5" id="domain-pills"></div>
    </header>

    <!-- 5-Card Statistical Precision & QC KPI Strip -->
    <section class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3" id="qc-kpi-strip"></section>

    <!-- Analyst QC Decision-Making & Export Workbench Banner -->
    <section id="qc-decision-banner" class="bg-[var(--card)] border border-[var(--primary)]/50 rounded-xl p-3.5 shadow-sm"></section>

    <!-- 4 Dedicated Audit Workbench Sub-Tabs -->
    <div class="flex flex-wrap gap-1.5 bg-[var(--card)] border border-[var(--border)] rounded-xl p-1.5 shadow-sm" id="qc-sub-tabs">
      <button data-subtab="outliers" class="subtab-btn px-3.5 py-2 rounded-lg text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)]">1. Candidate Outlier Replicate Groups &amp; Decisions</button>
      <button data-subtab="rsd" class="subtab-btn px-3.5 py-2 rounded-lg text-xs font-semibold text-[var(--muted-foreground)]">2. Within vs. Between-Group RSD Precision</button>
      <button data-subtab="notes" class="subtab-btn px-3.5 py-2 rounded-lg text-xs font-semibold text-[var(--muted-foreground)]">3. Mined Lab &amp; Field Notes Audit</button>
      <button data-subtab="explorer" class="subtab-btn px-3.5 py-2 rounded-lg text-xs font-semibold text-[var(--muted-foreground)]">4. Full Record Explorer &amp; Record Decisions</button>
    </div>

    <!-- Dynamic Audit Workbench Container -->
    <main id="qc-content" class="space-y-4"></main>

  </div>

  <script>
    const BUNDLE = __DATA_JSON__;
    const DEFAULT_RESOURCE = __DEFAULT_RESOURCE__;
    const CHAR_PAGE_FILENAME = __CHAR_PAGE_FILENAME_JSON__;

    const ELEM_NAMES = {
      K: "Potassium (K)", Ca: "Calcium (Ca)", Na: "Sodium (Na)", S: "Sulfur (S)",
      Mg: "Magnesium (Mg)", P: "Phosphorus (P)", Fe: "Iron (Fe)", Al: "Aluminum (Al)",
      Si: "Silicon (Si)", Mn: "Manganese (Mn)", Zn: "Zinc (Zn)", Cu: "Copper (Cu)",
      B: "Boron (B)", Ti: "Titanium (Ti)", Sr: "Strontium (Sr)", Ba: "Barium (Ba)",
      Rb: "Rubidium (Rb)", Zr: "Zirconium (Zr)", Cr: "Chromium (Cr)", Ni: "Nickel (Ni)",
      Pb: "Lead (Pb)", As: "Arsenic (As)", Co: "Cobalt (Co)", Mo: "Molybdenum (Mo)",
      Cd: "Cadmium (Cd)", Se: "Selenium (Se)", Sb: "Antimony (Sb)", Sn: "Tin (Sn)",
      V: "Vanadium (V)", W: "Tungsten (W)", Ag: "Silver (Ag)", Hg: "Mercury (Hg)",
      Bi: "Bismuth (Bi)", Th: "Thorium (Th)", U: "Uranium (U)", Y: "Yttrium (Y)",
      La: "Lanthanum (La)", Ce: "Cerium (Ce)", Pr: "Praseodymium (Pr)", Nd: "Neodymium (Nd)",
      Nb: "Niobium (Nb)", Cl: "Chlorine (Cl)"
    };

    const DOMAIN_LABELS = {
      all: "All Analytical Domains",
      proximate: "Proximate & Calorimetry",
      compositional: "Compositional, Ultimate & XRD",
      elemental: "ICP & XRF Elements",
      pretreatment: "Pretreatment & EH",
      fermentation: "Fermentation & Gasification"
    };

    const DECISION_OPTIONS = [
      { value: "pending", label: "⏳ Pending Review", badgeClass: "bg-[var(--background)] text-[var(--muted-foreground)] border border-[var(--border)]" },
      { value: "keep", label: "✅ Keep / Valid Variance", badgeClass: "badge-pass" },
      { value: "exclude_qc_fail", label: "🚫 Exclude (Set qc_pass=fail)", badgeClass: "badge-fail" },
      { value: "re_assay", label: "🔁 Flag for Re-Assay", badgeClass: "badge-warn" },
      { value: "trace_ignore", label: "⚠️ Low-Abundance / Ignore", badgeClass: "badge-info" }
    ];

    const QUICK_RATIONALE_CHIPS = [
      "Replicate outlier",
      "High assay scatter",
      "<LOD trace noise",
      "Oven-dried protocol",
      "Valid biological spread"
    ];

    const COUNTY_LOOKUP = BUNDLE.ca_counties || {};
    const FS_LOOKUP = {};
    (BUNDLE.field_samples || []).forEach(fs => {
      FS_LOOKUP[`${fs.resource_name}::${fs.name}`] = fs;
      if (!FS_LOOKUP[fs.name]) FS_LOOKUP[fs.name] = fs;
    });
    const PS_LOOKUP = {};
    (BUNDLE.prepared_samples || []).forEach(ps => {
      PS_LOOKUP[`${ps.resource_name}::${ps.name}`] = ps;
      if (!PS_LOOKUP[ps.name]) PS_LOOKUP[ps.name] = ps;
    });

    const ALL_RECORDS = BUNDLE.rows.map(arr => {
      const obj = { record_id: String(arr[0]) };
      BUNDLE.str_cols.forEach((col, idx) => {
        obj[col] = BUNDLE.dicts[col][arr[idx + 1]];
      });
      obj.replicate = arr[BUNDLE.str_cols.length + 1];
      obj.value = arr[BUNDLE.str_cols.length + 2];
      obj.exp_date = arr.length > BUNDLE.str_cols.length + 3 ? arr[BUNDLE.str_cols.length + 3] : "";
      obj.time_h = arr.length > BUNDLE.str_cols.length + 4 ? arr[BUNDLE.str_cols.length + 4] : null;
      if ((obj.analysis_type === "ICP Elemental Analysis" || obj.analysis_type === "XRF Elemental Analysis") && obj.parameter && obj.parameter !== "(metadata only)") {
        obj.parameter = obj.parameter.charAt(0).toUpperCase() + obj.parameter.slice(1).toLowerCase();
      }
      const fsMeta = FS_LOOKUP[`${obj.resource_name}::${obj.field_sample}`] || FS_LOOKUP[obj.field_sample] || null;
      const psMeta = PS_LOOKUP[`${obj.resource_name}::${obj.prepared_sample}`] || PS_LOOKUP[obj.prepared_sample] || null;
      obj.collected_date = fsMeta && fsMeta.collected_at ? fsMeta.collected_at : "";
      obj.geoid = fsMeta && fsMeta.geoid ? String(fsMeta.geoid) : "";
      obj.county_name = obj.geoid && COUNTY_LOOKUP[obj.geoid] ? COUNTY_LOOKUP[obj.geoid] : "";
      obj.prep_date = psMeta && psMeta.prep_date ? psMeta.prep_date : "";
      const ins = BUNDLE.insights && BUNDLE.insights[obj.resource_name];
      obj.portal_excluded = Boolean(ins && ins.portal_excluded);
      obj.portal_compliant = obj.qc_status === "pass" && !obj.portal_excluded;
      return obj;
    });

    const RECORDS_BY_RESOURCE = {};
    ALL_RECORDS.forEach(r => {
      if (!RECORDS_BY_RESOURCE[r.resource_name]) RECORDS_BY_RESOURCE[r.resource_name] = [];
      RECORDS_BY_RESOURCE[r.resource_name].push(r);
    });

    const ACTIVE_RESOURCES = Object.keys(RECORDS_BY_RESOURCE).sort(
      (a, b) => RECORDS_BY_RESOURCE[b].length - RECORDS_BY_RESOURCE[a].length
    );

    const STORAGE_KEY_DECISIONS = "biocirv_qc_decisions_v1";
    function loadDecisionsStore() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY_DECISIONS);
        return raw ? JSON.parse(raw) : {};
      } catch (_) {
        return {};
      }
    }
    function saveDecisionsStore(store) {
      try {
        localStorage.setItem(STORAGE_KEY_DECISIONS, JSON.stringify(store));
      } catch (_) {}
    }
    let DECISIONS_STORE = loadDecisionsStore();

    const urlParams = new URLSearchParams(window.location.search);
    const initialResParam = (urlParams.get("resource") || DEFAULT_RESOURCE).toLowerCase();
    const matchedInitialRes = ACTIVE_RESOURCES.find(r => r.toLowerCase() === initialResParam) || ACTIVE_RESOURCES[0];
    const initialDomainParam = urlParams.get("domain") || "all";
    const initialSubtabParam = urlParams.get("subtab") || "outliers";
    const initialPortalQcParam = urlParams.get("portal_qc") || "all";

    const state = {
      resource: matchedInitialRes,
      domain: DOMAIN_LABELS[initialDomainParam] ? initialDomainParam : "all",
      subtab: ["outliers", "rsd", "notes", "explorer"].includes(initialSubtabParam) ? initialSubtabParam : "outliers",
      portalQcMode: ["all", "portal_compliant", "qc_pass", "qc_fail"].includes(initialPortalQcParam) ? initialPortalQcParam : "all",
      prepared_sample: "all",
      experiment: "all",
      suppressTraceFlags: true,
      outlierFilterMode: "flagged",
      explorerFlagFilter: "all",
      search: "",
      showDecisionQueueTable: false,
      anonymizeAnalyst: Boolean(BUNDLE.exclude_analyst_default)
    };

    function fmtNum(v, digits = 2) {
      if (v === null || v === undefined || isNaN(v)) return "—";
      return Number(v).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: digits });
    }

    function formatParamLabel(analysisType, param) {
      if ((analysisType === "ICP Elemental Analysis" || analysisType === "XRF Elemental Analysis") && ELEM_NAMES[param]) {
        return ELEM_NAMES[param];
      }
      return param;
    }

    function getAnalystLabel(rawAnalyst) {
      if (state.anonymizeAnalyst) {
        return rawAnalyst === "pass" ? "UC Combined Protocol" : "—";
      }
      if (rawAnalyst === "pass") return "UC Combined Protocol (prox50sd)";
      return rawAnalyst || "—";
    }

    function getResourceRecords() {
      return RECORDS_BY_RESOURCE[state.resource] || [];
    }

    function getResourceInsights() {
      return (BUNDLE.insights && BUNDLE.insights[state.resource]) || null;
    }

    function getSampleLineageSummary(resourceName, preparedSampleName) {
      const psMeta = PS_LOOKUP[`${resourceName}::${preparedSampleName}`] || PS_LOOKUP[preparedSampleName] || null;
      const fsName = psMeta && psMeta.field_sample ? psMeta.field_sample : "";
      const fsMeta = (fsName && (FS_LOOKUP[`${resourceName}::${fsName}`] || FS_LOOKUP[fsName])) || null;
      const collectedDate = fsMeta && fsMeta.collected_at ? fsMeta.collected_at : "";
      const geoid = fsMeta && fsMeta.geoid ? String(fsMeta.geoid) : "";
      const county = geoid && COUNTY_LOOKUP[geoid] ? COUNTY_LOOKUP[geoid] : "";
      const prepDate = psMeta && psMeta.prep_date ? psMeta.prep_date : "";
      return { fsName, collectedDate, geoid, county, prepDate };
    }

    function makeGroupDecisionKey(resourceName, g) {
      return `grp::${resourceName}::${g.analysis_type}::${g.prepared_sample}::${g.experiment}::${g.parameter}`;
    }

    function makeRecordDecisionKey(recordId) {
      return `rec::${recordId}`;
    }

    function getDecisionEntry(key) {
      return DECISIONS_STORE[key] || { decision: "pending", note: "", updated_at: "" };
    }

    function upsertDecisionEntry(key, patch, meta) {
      const existing = DECISIONS_STORE[key] || { decision: "pending", note: "", updated_at: "" };
      const merged = {
        ...existing,
        ...meta,
        ...patch,
        key,
        updated_at: new Date().toISOString().slice(0, 19).replace("T", " ")
      };
      if ((merged.decision === "pending" || !merged.decision) && (!merged.note || !merged.note.trim())) {
        delete DECISIONS_STORE[key];
      } else {
        DECISIONS_STORE[key] = merged;
      }
      saveDecisionsStore(DECISIONS_STORE);
    }

    function isRecordMatchingPortalQc(r, mode) {
      if (mode === "portal_compliant") return Boolean(r.portal_compliant);
      if (mode === "qc_pass") return r.qc_status === "pass";
      if (mode === "qc_fail") return r.qc_status !== "pass";
      return true;
    }

    function isGroupMatchingPortalQc(g, mode, resourcePortalExcluded) {
      if (mode === "portal_compliant") {
        return !resourcePortalExcluded && (g.qc_pass_count || 0) > 0;
      }
      if (mode === "qc_pass") {
        return (g.qc_pass_count || 0) > 0;
      }
      if (mode === "qc_fail") {
        return (g.qc_fail_count || 0) > 0;
      }
      return true;
    }

    function initResourceSwitcher() {
      const sel = document.getElementById("flt-resource");
      sel.innerHTML = ACTIVE_RESOURCES.map(r => {
        const ins = BUNDLE.insights && BUNDLE.insights[r];
        const flg = (ins && ins.outlier_screening && ins.outlier_screening.flagged_active_groups) || 0;
        const recs = RECORDS_BY_RESOURCE[r];
        const pTag = ins && ins.portal_excluded ? " [Portal Excluded]" : "";
        return `<option value="${r}">${r.toUpperCase()} — ${flg} Active Flag(s) (${recs.length} obs)${pTag}</option>`;
      }).join("");
      sel.value = state.resource;
      if (BUNDLE.single_resource) {
        document.getElementById("resource-switcher-wrap").classList.add("hidden");
      }
      const pqcSel = document.getElementById("flt-portal-qc");
      if (pqcSel) pqcSel.value = state.portalQcMode;
    }

    function initFiltersForResource() {
      const resRecs = getResourceRecords();
      const psCounts = {};
      const expCounts = {};
      resRecs.forEach(r => {
        if (r.prepared_sample) psCounts[r.prepared_sample] = (psCounts[r.prepared_sample] || 0) + 1;
        if (r.experiment) expCounts[r.experiment] = (expCounts[r.experiment] || 0) + 1;
      });

      const psNames = Object.keys(psCounts).sort();
      const selPs = document.getElementById("flt-prepared-sample");
      selPs.innerHTML = `<option value="all">All Prepared Samples (${psNames.length})</option>` + psNames.map(n => `<option value="${n}">${n} (${psCounts[n]})</option>`).join("");
      selPs.value = psNames.includes(state.prepared_sample) ? state.prepared_sample : "all";

      const expNames = Object.keys(expCounts).sort();
      const selExp = document.getElementById("flt-experiment");
      selExp.innerHTML = `<option value="all">All Experiments (${expNames.length})</option>` + expNames.map(n => `<option value="${n}">${n} (${expCounts[n]})</option>`).join("");
      selExp.value = expNames.includes(state.experiment) ? state.experiment : "all";
    }

    function getAllDomainOutlierGroups() {
      const ins = getResourceInsights();
      const resourcePortalExcluded = Boolean(ins && ins.portal_excluded);
      const byTab = (ins && ins.outlier_screening && ins.outlier_screening.by_tab) || {};
      const keys = state.domain === "all" ? Object.keys(byTab) : [state.domain];
      const groups = [];
      keys.forEach(k => {
        const t = byTab[k];
        if (!t) return;
        (t.replicate_groups || []).forEach(g => {
          if (state.prepared_sample !== "all" && g.prepared_sample !== state.prepared_sample) return;
          if (state.experiment !== "all" && g.experiment !== state.experiment) return;
          if (!isGroupMatchingPortalQc(g, state.portalQcMode, resourcePortalExcluded)) return;
          groups.push({ ...g, domainKey: k });
        });
      });
      return groups;
    }

    function getAllDomainParamRsdRows() {
      const ins = getResourceInsights();
      const resourcePortalExcluded = Boolean(ins && ins.portal_excluded);
      if (state.portalQcMode === "portal_compliant" && resourcePortalExcluded) return [];
      const byTab = (ins && ins.outlier_screening && ins.outlier_screening.by_tab) || {};
      const keys = state.domain === "all" ? Object.keys(byTab) : [state.domain];
      const rows = [];
      keys.forEach(k => {
        const t = byTab[k];
        if (!t) return;
        (t.param_rsd_table || []).forEach(p => {
          rows.push({ ...p, domainKey: k });
        });
      });
      return rows;
    }

    function isGroupMatchingFilter(g, mode, suppress) {
      if (suppress && g.below_cutoff) return false;
      const isPrimary = suppress ? g.active_flagged : g.raw_flagged;
      const isMod = suppress ? (g.active_flagged || g.active_rsd10) : (g.raw_flagged || g.raw_rsd10);
      if (mode === "flagged") return isPrimary;
      if (mode === "moderate") return isMod;
      if (mode === "dixon") return g.raw_dixon;
      if (mode === "rsd20") return g.raw_rsd20;
      if (mode === "sd3x") return g.raw_sd3x;
      if (mode === "unquarantined") return isPrimary && g.qc_pass_count > 0;
      if (mode === "reviewed") {
        const dKey = makeGroupDecisionKey(state.resource, g);
        const entry = DECISIONS_STORE[dKey];
        return Boolean(entry && (entry.decision !== "pending" || (entry.note && entry.note.trim())));
      }
      if (mode === "all_groups") return true;
      return isPrimary;
    }

    function renderDomainPills() {
      const ins = getResourceInsights();
      const resourcePortalExcluded = Boolean(ins && ins.portal_excluded);
      const byTab = (ins && ins.outlier_screening && ins.outlier_screening.by_tab) || {};
      const suppress = state.suppressTraceFlags;

      const domains = ["all", "proximate", "compositional", "elemental", "pretreatment", "fermentation"];
      document.getElementById("domain-pills").innerHTML = domains.map(d => {
        let flgCnt = 0;
        let grpCnt = 0;
        const tabKeys = d === "all" ? Object.keys(byTab) : (byTab[d] ? [d] : []);
        tabKeys.forEach(k => {
          const t = byTab[k];
          if (!t) return;
          (t.replicate_groups || []).forEach(g => {
            if (!isGroupMatchingPortalQc(g, state.portalQcMode, resourcePortalExcluded)) return;
            grpCnt += 1;
            if (isGroupMatchingFilter(g, "flagged", suppress)) flgCnt += 1;
          });
        });
        const active = state.domain === d;
        return `
          <button onclick="setDomain('${d}')" class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition flex items-center gap-1.5 ${active ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]' : 'bg-[var(--background)] text-[var(--muted-foreground)] border-[var(--border)] hover:text-[var(--foreground)]'}">
            <span>${DOMAIN_LABELS[d]}</span>
            <span class="px-1.5 py-0.2 rounded-full text-[11px] font-mono ${flgCnt > 0 ? (active ? 'bg-white/25 text-white' : 'badge-warn') : 'opacity-75'}">${flgCnt} flag / ${grpCnt} grp</span>
          </button>
        `;
      }).join("");
    }

    function renderDecisionBanner() {
      const allEntries = Object.values(DECISIONS_STORE);
      const resEntries = allEntries.filter(e => e.resource_name === state.resource);
      const keepCnt = allEntries.filter(e => e.decision === "keep").length;
      const exclCnt = allEntries.filter(e => e.decision === "exclude_qc_fail").length;
      const reassayCnt = allEntries.filter(e => e.decision === "re_assay").length;
      const traceCnt = allEntries.filter(e => e.decision === "trace_ignore").length;

      const bannerEl = document.getElementById("qc-decision-banner");
      if (!bannerEl) return;

      const queueRowsHtml = allEntries.length === 0
        ? `<div class="p-3 text-center text-xs text-[var(--muted-foreground)]">No analyst review decisions recorded yet. Select a decision or type a review note on any replicate group (Subtab 1) or individual record (Subtab 4) below.</div>`
        : `
          <div class="overflow-x-auto max-h-56 overflow-y-auto border border-[var(--border)] rounded-lg mt-2.5">
            <table class="w-full text-left border-collapse text-xs">
              <thead class="sticky top-0 bg-[var(--card)] border-b border-[var(--border)] text-[11px] text-[var(--muted-foreground)]">
                <tr>
                  <th class="py-1.5 px-2.5">Scope</th>
                  <th class="py-1.5 px-2.5">Resource</th>
                  <th class="py-1.5 px-2.5">Sample / Record</th>
                  <th class="py-1.5 px-2.5">Domain &amp; Parameter</th>
                  <th class="py-1.5 px-2.5">Decision</th>
                  <th class="py-1.5 px-2.5">Analyst Review Note</th>
                  <th class="py-1.5 px-2.5">Updated</th>
                  <th class="py-1.5 px-2.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                ${allEntries.map(e => {
                  const opt = DECISION_OPTIONS.find(o => o.value === e.decision) || DECISION_OPTIONS[0];
                  return `
                    <tr class="border-t border-[var(--border)] hover:bg-[var(--background)]">
                      <td class="py-1.5 px-2.5 font-mono text-[11px]">${e.scope || 'group'}</td>
                      <td class="py-1.5 px-2.5 font-semibold">${e.resource_name || '—'}</td>
                      <td class="py-1.5 px-2.5 font-mono">${e.target_label || e.prepared_sample || e.record_id || '—'}</td>
                      <td class="py-1.5 px-2.5">${e.analysis_type || ''} · <strong class="font-mono">${e.parameter || '—'}</strong></td>
                      <td class="py-1.5 px-2.5"><span class="px-2 py-0.5 rounded text-[11px] font-semibold ${opt.badgeClass}">${opt.label}</span></td>
                      <td class="py-1.5 px-2.5 font-mono text-[var(--foreground)]">${e.note || '—'}</td>
                      <td class="py-1.5 px-2.5 font-mono text-[11px] text-[var(--muted-foreground)]">${e.updated_at || ''}</td>
                      <td class="py-1.5 px-2.5 text-right">
                        <button onclick="removeDecisionEntry('${e.key.replace(/'/g, "\\'")}')" class="px-2 py-0.5 rounded text-[11px] badge-fail hover:opacity-80">Remove</button>
                      </td>
                    </tr>
                  `;
                }).join("")}
              </tbody>
            </table>
          </div>
        `;

      bannerEl.innerHTML = `
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-2.5">
            <span class="px-2.5 py-1 rounded-lg text-xs font-bold bg-[var(--primary)] text-[var(--primary-foreground)]">
              ⚖️ Analyst QC Decision Workbench
            </span>
            <span class="text-xs font-semibold text-[var(--foreground)]">
              ${allEntries.length} total decision(s) logged (${resEntries.length} on ${state.resource.toUpperCase()})
            </span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono badge-pass">Keep: ${keepCnt}</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono badge-fail">Exclude (qc_pass=fail): ${exclCnt}</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono badge-warn">Re-Assay: ${reassayCnt}</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono badge-info">Trace/Ignore: ${traceCnt}</span>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <button onclick="toggleDecisionQueueTable()" class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)]">
              ${state.showDecisionQueueTable ? '▲ Hide Review Queue' : `▼ Inspect Review Queue (${allEntries.length})`}
            </button>
            <button onclick="exportDecisionsCsv()" class="px-3 py-1 rounded-lg text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90">
              ⬇ Export Decisions CSV (${allEntries.length})
            </button>
            <button onclick="exportDecisionsJson()" class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90">
              ⬇ JSON
            </button>
            ${allEntries.length > 0 ? `<button onclick="clearAllDecisions()" class="px-2.5 py-1 rounded-lg text-xs font-semibold badge-fail hover:opacity-90">Clear All</button>` : ''}
          </div>
        </div>
        ${state.showDecisionQueueTable ? queueRowsHtml : ''}
      `;
    }

    function renderHeaderAndKpis() {
      const ins = getResourceInsights();
      const out = (ins && ins.outlier_screening) || {};
      const notes = getFilteredCuratedNotes();
      const rTitle = state.resource.replace(/\\b\\w/g, c => c.toUpperCase());

      document.getElementById("hdr-title").textContent = `BioCirV · ${rTitle} — Statistical QC, Precision & Lab Notes Audit`;
      document.getElementById("hdr-code-badge").textContent = ins ? `#${ins.resource_id || '—'} · ${ins.code}` : state.resource;
      const pBadge = document.getElementById("hdr-portal-badge");
      if (ins && ins.portal_excluded) {
        pBadge.className = "px-2.5 py-0.5 text-xs font-semibold rounded-full badge-warn";
        pBadge.textContent = "Excluded from Public Portal Views";
      } else {
        pBadge.className = "px-2.5 py-0.5 text-xs font-semibold rounded-full badge-pass";
        pBadge.textContent = "Portal Compliant Resource";
      }
      document.getElementById("btn-anon-analyst").textContent = state.anonymizeAnalyst ? "👤 Show Analysts" : "🔒 Hide Analysts";

      const encRes = encodeURIComponent(state.resource);
      document.getElementById("nav-page-char").href = `${CHAR_PAGE_FILENAME}?resource=${encRes}`;
      document.getElementById("nav-page-qc").href = `resource_qc_outlier_dashboard.html?resource=${encRes}`;
      document.getElementById("nav-page-explorer").href = `resource_explorer_dashboard.html?resource=${encRes}`;
      document.getElementById("nav-page-monolith").href = `resource_analysis_dashboard_v1_monolith.html?resource=${encRes}`;

      const groups = getAllDomainOutlierGroups();
      const suppress = state.suppressTraceFlags;
      const primaryGroups = groups.filter(g => isGroupMatchingFilter(g, "flagged", suppress));
      const dixonGroups = groups.filter(g => isGroupMatchingFilter(g, "dixon", suppress));
      const rsd20Groups = groups.filter(g => isGroupMatchingFilter(g, "rsd20", suppress));
      const sd3xGroups = groups.filter(g => isGroupMatchingFilter(g, "sd3x", suppress));
      const unquarGroups = groups.filter(g => isGroupMatchingFilter(g, "unquarantined", suppress));
      const suppressedCount = groups.filter(g => g.below_cutoff && g.raw_flagged).length;

      const resRecs = getResourceRecords();
      const colDates = Array.from(new Set(resRecs.map(r => r.collected_date).filter(Boolean))).sort();
      const prepDates = Array.from(new Set(resRecs.map(r => r.prep_date).filter(Boolean))).sort();
      const geoids = Array.from(new Set(resRecs.map(r => r.geoid ? (r.county_name ? `${r.county_name} (${r.geoid})` : r.geoid) : "").filter(Boolean)));

      document.getElementById("nav-qc-badge").textContent = `⚑ ${primaryGroups.length}`;

      const portalModeLabel = {
        all: "All Statuses (Raw + Pass/Fail)",
        portal_compliant: "Portal Compliant Only",
        qc_pass: "qc_pass = pass Only",
        qc_fail: "qc_pass = fail Only"
      }[state.portalQcMode];

      const kpis = [
        { label: `Flagged Groups (${portalModeLabel})`, value: `${primaryGroups.length} / ${groups.length}`, sub: `Dixon Q: ${dixonGroups.length} · RSD>20%: ${rsd20Groups.length} · >3×SD: ${sd3xGroups.length}` },
        { label: "Unquarantined (QC Pass) Flags", value: `${unquarGroups.length}`, sub: unquarGroups.length ? "Flagged groups with qc_pass=pass records" : "Zero unquarantined flags in current filter" },
        { label: "Within-Replicate RSD Median", value: out.overall_within_rsd_median !== null && out.overall_within_rsd_median !== undefined ? `${fmtNum(out.overall_within_rsd_median, 1)}%` : "N/A (n=1)", sub: `Across ${out.rsd_defined_groups || 0} multi-replicate groups` },
        { label: "Collection & Prep Dates", value: colDates.length ? colDates[0] : (prepDates.length ? `Prep ${prepDates[0]}` : "No Date"), sub: `${geoids.length ? geoids.join(', ') : 'GEOID unrecorded'} · Prep: ${prepDates.length ? prepDates.join(', ') : '—'}` },
        { label: "Trace Suppressed & Lab Notes", value: `${suppressedCount} trace · ${notes.length} notes`, sub: suppress ? "Trace floor ON (<100 ppm ICP/XRF, <0.5% wt)" : "Trace floor OFF (showing all raw flags)" }
      ];

      document.getElementById("qc-kpi-strip").innerHTML = kpis.map(k => `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-3.5 shadow-sm">
          <div class="text-xs font-medium text-[var(--muted-foreground)]">${k.label}</div>
          <div class="text-base sm:text-lg font-bold text-[var(--foreground)] mt-0.5 font-mono truncate">${k.value}</div>
          <div class="text-[11px] text-[var(--muted-foreground)] mt-0.5 truncate" title="${k.sub.replace(/"/g, '&quot;')}">${k.sub}</div>
        </div>
      `).join("");

      const paramRows = getAllDomainParamRsdRows();
      const filteredExplorer = getFilteredExplorerRecords();
      const subLabels = {
        outliers: `1. Candidate Outlier Replicate Groups & Decisions (${primaryGroups.length} flagged)`,
        rsd: `2. Within vs. Between-Group RSD Precision (${paramRows.length} params)`,
        notes: `3. Mined Lab & Field Notes Audit (${notes.length})`,
        explorer: `4. Full Record Explorer & Record Decisions (${filteredExplorer.length})`
      };
      document.querySelectorAll(".subtab-btn").forEach(btn => {
        const st = btn.dataset.subtab;
        btn.textContent = subLabels[st];
        btn.className = st === state.subtab
          ? "subtab-btn px-3.5 py-2 rounded-lg text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)]"
          : "subtab-btn px-3.5 py-2 rounded-lg text-xs font-semibold text-[var(--muted-foreground)] hover:text-[var(--foreground)]";
      });
    }

    function renderOutliersSubtab() {
      const ins = getResourceInsights();
      const resourcePortalExcluded = Boolean(ins && ins.portal_excluded);
      const groups = getAllDomainOutlierGroups();
      const suppress = state.suppressTraceFlags;
      const primaryGroups = groups.filter(g => isGroupMatchingFilter(g, "flagged", suppress));
      const modGroups = groups.filter(g => isGroupMatchingFilter(g, "moderate", suppress));
      const dixonGroups = groups.filter(g => isGroupMatchingFilter(g, "dixon", suppress));
      const rsd20Groups = groups.filter(g => isGroupMatchingFilter(g, "rsd20", suppress));
      const sd3xGroups = groups.filter(g => isGroupMatchingFilter(g, "sd3x", suppress));
      const unquarGroups = groups.filter(g => isGroupMatchingFilter(g, "unquarantined", suppress));
      const reviewedGroups = groups.filter(g => isGroupMatchingFilter(g, "reviewed", suppress));
      const displayedGroups = groups.filter(g => isGroupMatchingFilter(g, state.outlierFilterMode, suppress));

      const filterBtns = [
        { id: "flagged", label: `Primary Flagged (${primaryGroups.length})` },
        { id: "moderate", label: `Include Moderate RSD >10% (${modGroups.length})` },
        { id: "dixon", label: `Dixon's Q α=0.05 (${dixonGroups.length})` },
        { id: "rsd20", label: `RSD >20% (${rsd20Groups.length})` },
        { id: "sd3x", label: `>3×SD Pooled (${sd3xGroups.length})` },
        { id: "unquarantined", label: `Unquarantined / QC Pass (${unquarGroups.length})` },
        { id: "reviewed", label: `⚖️ Reviewed / Annotated (${reviewedGroups.length})` },
        { id: "all_groups", label: `All Replicate Groups (${groups.length})` }
      ];

      const portalExcludedNotice = (state.portalQcMode === "portal_compliant" && resourcePortalExcluded)
        ? `<div class="p-4 rounded-xl border border-amber-500/40 badge-warn text-xs">
             <strong>Note:</strong> Resource <span class="font-mono font-bold">${state.resource}</span> is currently in <span class="font-mono">EXCLUDED_RESOURCES</span> for the public data portal. Switch <strong>QC / Portal Filter</strong> to <span class="font-mono">qc_pass = pass Only</span> or <span class="font-mono">All Statuses</span> to inspect its replicate groups.
           </div>`
        : "";

      const rowsHtml = displayedGroups.length === 0
        ? `
          <div class="p-8 text-center text-xs text-[var(--muted-foreground)] bg-[var(--background)] rounded-xl border border-[var(--border)]">
            ✓ No replicate groups match the selected screen (<strong>${state.outlierFilterMode}</strong>) and QC/Portal filter (<strong>${state.portalQcMode}</strong>) in ${DOMAIN_LABELS[state.domain]}.
          </div>
        `
        : `
          <div class="overflow-x-auto max-h-[620px] overflow-y-auto border border-[var(--border)] rounded-xl">
            <table class="w-full text-left border-collapse">
              <thead class="sticky top-0 bg-[var(--card)] shadow-sm z-10">
                <tr class="text-[11px] font-semibold text-[var(--muted-foreground)] border-b border-[var(--border)]">
                  <th class="py-2.5 px-3">Domain &amp; Method</th>
                  <th class="py-2.5 px-3">Sample, Collection Date &amp; GEOID</th>
                  <th class="py-2.5 px-3">Parameter</th>
                  <th class="py-2.5 px-3">Replicates (n) &amp; Candidate Outlier (★)</th>
                  <th class="py-2.5 px-3 text-right">Mean &plusmn; SD</th>
                  <th class="py-2.5 px-3 text-right">Within vs. Between RSD</th>
                  <th class="py-2.5 px-3">Triggered Screens &amp; QC</th>
                  <th class="py-2.5 px-3 min-w-[270px]">⚖️ Analyst Review Decision &amp; Note</th>
                </tr>
              </thead>
              <tbody>
                ${displayedGroups.map(g => {
                  const sd3Set = new Set(g.sd3x_candidate_ids || []);
                  const repChips = (g.replicates || []).map(rep => {
                    const isDixonCand = g.dixon_candidate_id && rep.id === g.dixon_candidate_id;
                    const isSd3Cand = sd3Set.has(rep.id);
                    const isCand = isDixonCand || isSd3Cand;
                    const qcTag = rep.qc === "fail" ? " [FAIL]" : "";
                    return `<button onclick="jumpToRecord('${rep.id}')" title="Record ${rep.id} (Rep ${rep.rep}, QC: ${rep.qc})" class="px-1.5 py-0.5 rounded font-mono text-xs transition ${isCand ? 'badge-warn ring-1 ring-amber-500 font-bold' : 'bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] hover:border-[var(--primary)]'}">${isCand ? '★ ' : ''}${fmtNum(rep.val, 2)}${qcTag}</button>`;
                  }).join(" ");

                  const badges = [];
                  if (g.raw_dixon) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold badge-fail">Dixon Q=${fmtNum(g.dixon_q, 3)}</span>`);
                  if (g.raw_rsd20) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold badge-warn">RSD &gt; 20%</span>`);
                  else if (g.raw_rsd10) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono badge-info">RSD 10–20%</span>`);
                  if (g.raw_sd3x) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold badge-warn">&gt;3&times;SD<sub>pool</sub></span>`);
                  if (g.qc_mixed) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold badge-fail">Mixed QC</span>`);
                  if (g.below_cutoff) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono badge-info">Trace (${g.cutoff_label})</span>`);

                  const qcSummary = g.qc_fail_count === 0
                    ? `<span class="badge-pass px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold">Unquarantined (${g.qc_pass_count}P)</span>`
                    : (g.qc_pass_count === 0
                      ? `<span class="badge-fail px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold">Quarantined (${g.qc_fail_count}F)</span>`
                      : `<span class="badge-warn px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold">${g.qc_pass_count}P / ${g.qc_fail_count}F</span>`);

                  const pLabel = formatParamLabel(g.analysis_type, g.parameter);
                  const lin = getSampleLineageSummary(state.resource, g.prepared_sample);
                  const dKey = makeGroupDecisionKey(state.resource, g);
                  const dEntry = getDecisionEntry(dKey);
                  const safeKeyAttr = dKey.replace(/"/g, "&quot;").replace(/'/g, "\\'");
                  const candRecIds = (g.replicates || []).map(r => r.id).join("|");
                  const metaPayload = encodeURIComponent(JSON.stringify({
                    scope: "replicate_group",
                    resource_name: state.resource,
                    analysis_type: g.analysis_type,
                    prepared_sample: g.prepared_sample,
                    field_sample: lin.fsName || "",
                    collected_date: lin.collectedDate || "",
                    geoid: lin.geoid || "",
                    prep_date: lin.prepDate || "",
                    experiment: g.experiment,
                    parameter: g.parameter,
                    unit: g.unit || "",
                    n: g.n,
                    mean: g.mean,
                    sd: g.sd,
                    rsd_within_pct: g.rsd_within_pct,
                    dixon_q: g.dixon_q,
                    dixon_candidate_id: g.dixon_candidate_id || "",
                    record_ids: candRecIds,
                    target_label: `${g.prepared_sample} (${g.experiment})`
                  }));

                  return `
                    <tr class="border-t border-[var(--border)] hover:bg-[var(--background)] text-xs align-top">
                      <td class="py-2.5 px-3">
                        <div class="text-[11px] font-semibold text-[var(--foreground)]">${g.analysis_type}</div>
                        <div class="font-mono text-[11px] text-[var(--muted-foreground)] mt-0.5">${g.prep_method} · <strong class="text-[var(--foreground)]">${g.experiment}</strong></div>
                      </td>
                      <td class="py-2.5 px-3">
                        <div class="font-mono font-semibold text-[var(--primary)]">${g.prepared_sample}</div>
                        <div class="text-[11px] font-mono text-[var(--muted-foreground)] mt-0.5">
                          Col: <span class="text-[var(--foreground)]">${lin.collectedDate || 'Unrecorded'}</span>
                          · GEOID: <span class="text-[var(--foreground)]">${lin.geoid ? (lin.county ? `${lin.geoid} (${lin.county})` : lin.geoid) : '—'}</span>
                        </div>
                        <div class="text-[11px] font-mono text-[var(--muted-foreground)]">
                          Prep Date: <span class="text-[var(--foreground)]">${lin.prepDate || 'Unrecorded'}</span>
                        </div>
                      </td>
                      <td class="py-2.5 px-3 font-semibold text-[var(--foreground)]">
                        ${pLabel} <span class="font-mono text-[11px] font-normal text-[var(--muted-foreground)]">(${g.unit || '—'})</span>
                        <div class="mt-1">
                          <button onclick="inspectSampleParam('${g.prepared_sample}', '${g.parameter}')" class="px-2 py-0.5 rounded bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] text-[10px] font-semibold hover:border-[var(--primary)]">Inspect Records &rarr;</button>
                        </div>
                      </td>
                      <td class="py-2.5 px-3"><div class="flex flex-wrap items-center gap-1"><span class="text-[11px] font-mono text-[var(--muted-foreground)]">n=${g.n}:</span> ${repChips}</div></td>
                      <td class="py-2.5 px-3 font-mono text-right whitespace-nowrap"><strong>${fmtNum(g.mean, 2)}</strong> &plusmn; ${fmtNum(g.sd, 2)}</td>
                      <td class="py-2.5 px-3 font-mono text-right whitespace-nowrap">
                        <span class="${(g.rsd_within_pct || 0) > 20 ? 'text-red-500 font-bold' : ((g.rsd_within_pct || 0) > 10 ? 'text-amber-500 font-semibold' : 'text-[var(--foreground)]')}">${g.rsd_within_pct !== null ? fmtNum(g.rsd_within_pct, 1) + '%' : '—'}</span>
                        <span class="text-[var(--muted-foreground)]"> vs </span>
                        <span class="text-[var(--primary)]">${g.rsd_between_pct !== null && g.rsd_between_pct !== undefined ? fmtNum(g.rsd_between_pct, 1) + '%' : '—'}</span>
                      </td>
                      <td class="py-2.5 px-3 space-y-1">
                        <div class="flex flex-wrap gap-1">${badges.join("") || '<span class="text-[var(--muted-foreground)]">Pass</span>'}</div>
                        <div>${qcSummary}</div>
                        ${g.note ? `<div class="text-[11px] font-mono text-[var(--muted-foreground)] italic truncate max-w-[190px]" title="${g.note.replace(/"/g, '&quot;')}">"${g.note}"</div>` : ""}
                      </td>
                      <td class="py-2.5 px-3 space-y-1.5 min-w-[270px]">
                        <select onchange="handleDecisionChange('${safeKeyAttr}', this.value, '${metaPayload}')" class="w-full rounded px-2 py-1 text-xs font-semibold border border-[var(--border)]">
                          ${DECISION_OPTIONS.map(o => `<option value="${o.value}" ${dEntry.decision === o.value ? 'selected' : ''}>${o.label}</option>`).join("")}
                        </select>
                        <input type="text" value="${(dEntry.note || '').replace(/"/g, '&quot;')}" onchange="handleDecisionNote('${safeKeyAttr}', this.value, '${metaPayload}')" placeholder="Add reviewer rationale / action note..." class="w-full rounded px-2 py-1 text-xs border border-[var(--border)] font-mono" />
                        <div class="flex flex-wrap gap-1">
                          ${QUICK_RATIONALE_CHIPS.map(chip => `<button type="button" onclick="appendRationaleChip('${safeKeyAttr}', '${chip}', '${metaPayload}')" class="px-1.5 py-0.5 rounded text-[10px] bg-[var(--secondary)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] border border-[var(--border)]">+${chip}</button>`).join("")}
                        </div>
                      </td>
                    </tr>
                  `;
                }).join("")}
              </tbody>
            </table>
          </div>
        `;

      return `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-4">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 class="text-base font-bold text-[var(--foreground)]">Candidate Outlier Replicate Groups &amp; Analyst Review Decisions (${displayedGroups.length} shown)</h2>
              <p class="text-xs text-[var(--muted-foreground)]">Replicates marked with <strong>★</strong> are extreme candidate values identified by two-sided Dixon's Q (&alpha;=0.05, n&ge;3) or &gt;3&times;SD<sub>pooled</sub>. Record your QC decision and rationale note on the right to build an exportable audit log.</p>
            </div>
          </div>
          ${portalExcludedNotice}
          <div class="flex flex-wrap items-center gap-1.5">
            ${filterBtns.map(b => `
              <button onclick="setOutlierFilterMode('${b.id}')" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold transition border ${state.outlierFilterMode === b.id ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]' : 'bg-[var(--background)] text-[var(--muted-foreground)] border-[var(--border)] hover:text-[var(--foreground)]'}">${b.label}</button>
            `).join("")}
          </div>
          ${rowsHtml}
        </div>
      `;
    }

    function renderRsdSubtab() {
      const paramRows = getAllDomainParamRsdRows();
      const suppress = state.suppressTraceFlags;

      const driverBadgeClass = tone => {
        if (tone === "danger") return "badge-fail";
        if (tone === "warning") return "badge-warn";
        if (tone === "success") return "badge-pass";
        return "badge-info";
      };

      const rowsHtml = paramRows.map(p => {
        const wMed = p.within_rsd_median;
        const wMax = p.within_rsd_max;
        const bRsd = p.between_rsd_pct;
        const wBarPct = wMed !== null ? Math.min(100, Math.max(3, (wMed / 40) * 100)) : 0;
        const bBarPct = bRsd !== null ? Math.min(100, Math.max(3, (bRsd / 40) * 100)) : 0;
        const wBarColor = wMed === null ? "bg-gray-400" : (wMed > 20 ? "bg-red-500" : (wMed > 10 ? "bg-amber-500" : "bg-emerald-500"));
        const flagCnt = suppress ? p.flagged_active : p.flagged_raw;
        const label = formatParamLabel(p.analysis_type, p.parameter);

        return `
          <tr class="border-t border-[var(--border)] hover:bg-[var(--background)] text-xs ${p.below_cutoff && suppress ? 'opacity-65' : ''}">
            <td class="py-2.5 px-3 text-[11px] text-[var(--muted-foreground)]">${p.analysis_type}</td>
            <td class="py-2.5 px-3 font-semibold text-[var(--foreground)]">
              ${label} <span class="font-mono text-[11px] font-normal text-[var(--muted-foreground)]">(${p.unit || '—'})</span>
              ${p.below_cutoff ? `<span class="ml-1 px-1.5 py-0.5 rounded text-[10px] font-mono badge-info">${p.cutoff_label}</span>` : ""}
            </td>
            <td class="py-2.5 px-3 font-mono text-center">${p.n_groups} grp <span class="text-[var(--muted-foreground)]">(${p.n_obs} obs)</span></td>
            <td class="py-2.5 px-3 font-mono text-right font-semibold">${fmtNum(p.overall_mean, 2)}</td>
            <td class="py-2.5 px-3 font-mono">
              ${wMed !== null ? `
                <div class="flex items-center justify-between gap-2">
                  <span><strong>${fmtNum(wMed, 1)}%</strong> <span class="text-[var(--muted-foreground)]">(max ${fmtNum(wMax, 1)}%)</span></span>
                </div>
                <div class="w-full h-2 rounded-full bg-[var(--content)] overflow-hidden mt-1">
                  <div class="h-full rounded-full ${wBarColor}" style="width: ${wBarPct}%"></div>
                </div>
              ` : `<span class="text-[var(--muted-foreground)] italic">N/A (n=1)</span>`}
            </td>
            <td class="py-2.5 px-3 font-mono">
              ${bRsd !== null ? `
                <div class="flex items-center justify-between gap-2">
                  <strong class="text-[var(--primary)]">${fmtNum(bRsd, 1)}%</strong>
                  <span class="text-[10px] text-[var(--muted-foreground)]">across ${p.n_groups} means</span>
                </div>
                <div class="w-full h-2 rounded-full bg-[var(--content)] overflow-hidden mt-1">
                  <div class="h-full rounded-full bg-[var(--primary)]" style="width: ${bBarPct}%"></div>
                </div>
              ` : `<span class="text-[var(--muted-foreground)] italic">Single group</span>`}
            </td>
            <td class="py-2.5 px-3 font-mono text-right">${p.pooled_sd !== null ? `±${fmtNum(p.pooled_sd, 2)}` : '—'}</td>
            <td class="py-2.5 px-3 font-mono text-center">${flagCnt > 0 ? `<span class="px-2 py-0.5 rounded font-bold badge-warn">${flagCnt}</span>` : '0'}</td>
            <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded text-[11px] font-semibold ${driverBadgeClass(p.driver_tone)}">${p.driver_badge}</span></td>
          </tr>
        `;
      }).join("");

      return `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-4">
          <div>
            <h2 class="text-base font-bold text-[var(--foreground)]">Within-Replicate-Group vs. Between-Replicate-Group RSD by Parameter (${paramRows.length} Parameters)</h2>
            <p class="text-xs text-[var(--muted-foreground)]">Compares technical assay repeatability inside replicate groups (<strong>Within-Group RSD</strong>) against sample/batch/method dispersion across replicate group means (<strong>Between-Group RSD</strong>).</p>
          </div>
          <div class="overflow-x-auto max-h-[560px] overflow-y-auto border border-[var(--border)] rounded-xl">
            <table class="w-full text-left border-collapse">
              <thead class="sticky top-0 bg-[var(--card)] shadow-sm z-10">
                <tr class="text-[11px] font-semibold text-[var(--muted-foreground)] border-b border-[var(--border)]">
                  <th class="py-2.5 px-3">Domain</th>
                  <th class="py-2.5 px-3">Parameter (Unit)</th>
                  <th class="py-2.5 px-3 text-center">Replicate Groups</th>
                  <th class="py-2.5 px-3 text-right">Overall Mean</th>
                  <th class="py-2.5 px-3">Within-Group RSD (Tech Repeatability)</th>
                  <th class="py-2.5 px-3">Between-Group RSD (Sample / Method Spread)</th>
                  <th class="py-2.5 px-3 text-right">Pooled SD</th>
                  <th class="py-2.5 px-3 text-center">Flags</th>
                  <th class="py-2.5 px-3">Variance Driver</th>
                </tr>
              </thead>
              <tbody>${rowsHtml}</tbody>
            </table>
          </div>
        </div>
      `;
    }

    function getFilteredCuratedNotes() {
      const ins = getResourceInsights();
      const rawNotes = (ins && ins.curated_notes) || [];
      if (state.portalQcMode === "all") return rawNotes;
      const matchingRecIds = new Set(
        getResourceRecords()
          .filter(r => isRecordMatchingPortalQc(r, state.portalQcMode))
          .map(r => String(r.record_id))
      );
      return rawNotes.filter(n => {
        if (!n.record_ids || !n.record_ids.length) return state.portalQcMode !== "qc_fail";
        return n.record_ids.some(rid => matchingRecIds.has(String(rid)));
      });
    }

    function renderNotesSubtab() {
      const notes = getFilteredCuratedNotes();
      const fsList = (BUNDLE.field_samples || []).filter(fs => fs.resource_name === state.resource && fs.note);
      const psList = (BUNDLE.prepared_samples || []).filter(ps => ps.resource_name === state.resource && ps.note);

      const toneBadgeClass = tone => {
        if (tone === "danger") return "badge-fail";
        if (tone === "warning") return "badge-warn";
        if (tone === "success") return "badge-pass";
        return "badge-info";
      };

      const notesGrid = notes.length === 0
        ? `<div class="p-6 text-center text-xs text-[var(--muted-foreground)] bg-[var(--background)] rounded-xl border border-[var(--border)]">No observation notes match the active QC/Portal filter (<strong>${state.portalQcMode}</strong>) for ${state.resource}.</div>`
        : `<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            ${notes.map(n => {
              const sampleChips = (n.sample_names || []).map(s =>
                `<button onclick="inspectSampleParam('${s}', '')" class="px-2 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] font-mono text-xs hover:border-[var(--primary)]">${s}</button>`
              ).join(" ");
              const recChips = (n.record_ids || []).slice(0, 6).map(rid =>
                `<button onclick="jumpToRecord('${rid}')" class="px-2 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] font-mono text-xs text-[var(--primary)] hover:underline">${rid}</button>`
              ).join(" ");
              return `
                <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-4 space-y-2">
                  <div class="flex flex-wrap items-center justify-between gap-2">
                    <span class="px-2 py-0.5 rounded text-xs font-semibold ${toneBadgeClass(n.tone)}">${n.category}</span>
                    <span class="text-xs font-mono text-[var(--muted-foreground)]">${n.analysis_type} · ${n.count} rec(s)</span>
                  </div>
                  <div class="text-xs font-mono font-bold text-[var(--foreground)] bg-[var(--card)] p-2.5 rounded-lg border border-[var(--border)] break-words">"${n.note_text}"</div>
                  <div class="text-xs text-[var(--muted-foreground)] leading-relaxed"><strong class="text-[var(--foreground)]">AI Interpretation:</strong> ${n.interpretation}</div>
                  ${(sampleChips || recChips) ? `<div class="flex flex-wrap items-center gap-1.5 pt-1">${sampleChips} ${recChips}</div>` : ""}
                </div>
              `;
            }).join("")}
          </div>`;

      return `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-4">
          <div>
            <h2 class="text-base font-bold text-[var(--foreground)]">Mined Experimental Bench &amp; Field Notes Audit Trail (${notes.length} Note Groups)</h2>
            <p class="text-xs text-[var(--muted-foreground)]">Automated extraction and domain interpretation of analyst comments from <span class="font-mono">observation.note</span>, <span class="font-mono">prepared_sample.note</span>, and <span class="font-mono">field_sample.note</span>, filtered by QC/Portal mode (<strong>${state.portalQcMode}</strong>).</p>
          </div>
          ${(fsList.length || psList.length) ? `
            <div class="space-y-2">
              <h3 class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Field &amp; Preparation Lineage Notes (with Collection / Prep Dates &amp; GEOID)</h3>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                ${fsList.map(f => `<div class="p-3 rounded-lg bg-[var(--background)] border border-[var(--border)] text-xs"><strong class="font-mono">Field Sample ${f.name}</strong> <span class="font-mono text-[11px] text-[var(--muted-foreground)]">(Col: ${f.collected_at || 'Unrecorded'} · GEOID: ${f.geoid || '—'})</span>: "${f.note}"</div>`).join("")}
                ${psList.map(p => `<div class="p-3 rounded-lg bg-[var(--background)] border border-[var(--border)] text-xs"><strong class="font-mono">Prepared Sample ${p.name}</strong> <span class="font-mono text-[11px] text-[var(--muted-foreground)]">(Prep: ${p.prep_date || 'Unrecorded'})</span>: "${p.note}"</div>`).join("")}
              </div>
            </div>
          ` : ""}
          ${notesGrid}
        </div>
      `;
    }

    function getRecordOutlierLookup() {
      const ins = getResourceInsights();
      const map = {};
      if (!ins || !ins.outlier_screening || !ins.outlier_screening.by_tab) return map;
      const suppress = Boolean(state.suppressTraceFlags);
      Object.values(ins.outlier_screening.by_tab).forEach(tabOut => {
        (tabOut.replicate_groups || []).forEach(g => {
          const isPrimary = suppress ? g.active_flagged : g.raw_flagged;
          const isSuppressed = g.below_cutoff && g.raw_flagged;
          if (!isPrimary && !isSuppressed) return;
          const sd3Set = new Set(g.sd3x_candidate_ids || []);
          (g.replicates || []).forEach(rep => {
            const isDixonCand = g.dixon_candidate_id && rep.id === g.dixon_candidate_id;
            const isSd3Cand = sd3Set.has(rep.id);
            map[rep.id] = {
              isPrimary,
              isSuppressed,
              isCandidate: isDixonCand || isSd3Cand,
              isDixonCand,
              isSd3Cand,
              dixonQ: g.dixon_q,
              rsdWithin: g.rsd_within_pct,
              cutoffLabel: g.cutoff_label
            };
          });
        });
      });
      return map;
    }

    function getFilteredExplorerRecords() {
      const resRecs = getResourceRecords();
      const q = state.search.trim().toLowerCase();
      return resRecs.filter(r => {
        if (!isRecordMatchingPortalQc(r, state.portalQcMode)) return false;
        if (state.prepared_sample !== "all" && r.prepared_sample !== state.prepared_sample) return false;
        if (state.experiment !== "all" && r.experiment !== state.experiment) return false;
        if (q) {
          const hay = `${r.record_id} ${r.analysis_type} ${r.prepared_sample} ${r.field_sample} ${r.experiment} ${r.parameter} ${r.note} ${r.pt_method} ${r.eh_method} ${r.vessel} ${r.well_or_block} ${r.collected_date} ${r.prep_date} ${r.geoid} ${r.county_name}`.toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });
    }

    function renderExplorerSubtab() {
      const filtered = getFilteredExplorerRecords();
      const outlierMap = getRecordOutlierLookup();
      const flagFiltered = filtered.filter(r => {
        const info = outlierMap[r.record_id];
        if (state.explorerFlagFilter === "flagged") return info && info.isPrimary;
        if (state.explorerFlagFilter === "candidate") return info && info.isPrimary && info.isCandidate;
        if (state.explorerFlagFilter === "suppressed") return info && info.isSuppressed;
        if (state.explorerFlagFilter === "has_note") return Boolean(r.note);
        if (state.explorerFlagFilter === "reviewed") {
          const entry = DECISIONS_STORE[makeRecordDecisionKey(r.record_id)];
          return Boolean(entry && (entry.decision !== "pending" || (entry.note && entry.note.trim())));
        }
        return true;
      });

      const inFlaggedCnt = filtered.filter(r => outlierMap[r.record_id] && outlierMap[r.record_id].isPrimary).length;
      const candCnt = filtered.filter(r => outlierMap[r.record_id] && outlierMap[r.record_id].isPrimary && outlierMap[r.record_id].isCandidate).length;
      const suppCnt = filtered.filter(r => outlierMap[r.record_id] && outlierMap[r.record_id].isSuppressed).length;
      const noteCnt = filtered.filter(r => Boolean(r.note)).length;
      const revCnt = filtered.filter(r => {
        const entry = DECISIONS_STORE[makeRecordDecisionKey(r.record_id)];
        return Boolean(entry && (entry.decision !== "pending" || (entry.note && entry.note.trim())));
      }).length;

      const expFilterBtns = [
        { id: "all", label: `All Records (${filtered.length})` },
        { id: "flagged", label: `⚑ In Flagged Group (${inFlaggedCnt})` },
        { id: "candidate", label: `★ Extreme Candidate (${candCnt})` },
        { id: "suppressed", label: `Trace Suppressed (${suppCnt})` },
        { id: "has_note", label: `Has Bench Note (${noteCnt})` },
        { id: "reviewed", label: `⚖️ Reviewed (${revCnt})` }
      ];

      const rowsHtml = flagFiltered.slice(0, 600).map(r => {
        const info = outlierMap[r.record_id];
        let statCell = '<span class="text-[var(--muted-foreground)]">—</span>';
        if (info) {
          if (info.isSuppressed && state.suppressTraceFlags) {
            statCell = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono badge-info">Trace (${info.cutoffLabel})</span>`;
          } else if (info.isCandidate) {
            const tags = [];
            if (info.isDixonCand) tags.push(`Dixon Q=${fmtNum(info.dixonQ, 2)}`);
            if (info.isSd3Cand) tags.push(`>3×SD`);
            statCell = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold badge-warn ring-1 ring-amber-500">★ ${tags.join(' · ')}</span>`;
          } else if (info.isPrimary) {
            statCell = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono badge-warn">⚑ Grp RSD ${fmtNum(info.rsdWithin, 1)}%</span>`;
          }
        }
        const qcHtml = r.qc_status === "pass"
          ? `<span class="badge-pass px-2 py-0.5 text-xs font-mono font-semibold rounded">PASS</span>`
          : `<span class="badge-fail px-2 py-0.5 text-xs font-mono font-semibold rounded">FAIL</span>`;

        const recKey = makeRecordDecisionKey(r.record_id);
        const dEntry = getDecisionEntry(recKey);
        const safeKeyAttr = recKey.replace(/"/g, "&quot;").replace(/'/g, "\\'");
        const metaPayload = encodeURIComponent(JSON.stringify({
          scope: "record",
          resource_name: r.resource_name,
          record_id: r.record_id,
          analysis_type: r.analysis_type,
          prepared_sample: r.prepared_sample,
          field_sample: r.field_sample || "",
          collected_date: r.collected_date || "",
          geoid: r.geoid || "",
          prep_date: r.prep_date || "",
          exp_date: r.exp_date || "",
          experiment: r.experiment,
          parameter: r.parameter,
          value: r.value,
          unit: r.unit || "",
          qc_status: r.qc_status,
          target_label: `Rec ${r.record_id} (${r.prepared_sample})`
        }));

        return `
          <tr class="border-t border-[var(--border)] hover:bg-[var(--background)] text-xs align-top">
            <td class="py-2 px-2.5 font-mono font-semibold">${r.record_id}</td>
            <td class="py-2 px-2.5">${r.analysis_type}</td>
            <td class="py-2 px-2.5 font-mono">
              <div class="font-semibold text-[var(--primary)]">${r.prepared_sample}</div>
              <div class="text-[10px] text-[var(--muted-foreground)]">FS: ${r.field_sample || '—'}</div>
            </td>
            <td class="py-2 px-2.5 font-mono text-[11px]">
              <div>Col: <span class="text-[var(--foreground)]">${r.collected_date || '—'}</span></div>
              <div class="text-[10px] text-[var(--muted-foreground)]">GEOID: ${r.geoid ? (r.county_name ? `${r.geoid} (${r.county_name})` : r.geoid) : '—'}</div>
            </td>
            <td class="py-2 px-2.5 font-mono text-[11px]">
              <div>Prep: <span class="text-[var(--foreground)]">${r.prep_date || '—'}</span></div>
              <div class="text-[10px] text-[var(--muted-foreground)]">Run: ${r.exp_date || '—'}</div>
            </td>
            <td class="py-2 px-2.5 font-mono">${r.experiment}</td>
            <td class="py-2 px-2.5 font-mono font-semibold">${r.parameter || '—'}</td>
            <td class="py-2 px-2.5 font-mono text-right font-bold">${r.value !== null ? fmtNum(r.value, 3) : '—'} <span class="font-normal text-[10px] text-[var(--muted-foreground)]">${r.unit || ''}</span></td>
            <td class="py-2 px-2.5 text-center whitespace-nowrap">${statCell}</td>
            <td class="py-2 px-2.5 text-center">${qcHtml}</td>
            <td class="py-2 px-2.5 text-[var(--muted-foreground)] max-w-[160px] truncate" title="${(r.note || '').replace(/"/g, '&quot;')}">${r.note || ''}</td>
            <td class="py-2 px-2.5 min-w-[230px] space-y-1">
              <select onchange="handleDecisionChange('${safeKeyAttr}', this.value, '${metaPayload}')" class="w-full rounded px-1.5 py-1 text-[11px] font-semibold border border-[var(--border)]">
                ${DECISION_OPTIONS.map(o => `<option value="${o.value}" ${dEntry.decision === o.value ? 'selected' : ''}>${o.label}</option>`).join("")}
              </select>
              <input type="text" value="${(dEntry.note || '').replace(/"/g, '&quot;')}" onchange="handleDecisionNote('${safeKeyAttr}', this.value, '${metaPayload}')" placeholder="Reviewer note..." class="w-full rounded px-1.5 py-1 text-[11px] border border-[var(--border)] font-mono" />
            </td>
          </tr>
        `;
      }).join("");

      return `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-3.5">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 class="text-base font-bold text-[var(--foreground)]">Complete ${state.resource.toUpperCase()} Record Explorer (${flagFiltered.length} matching records)</h2>
              <p class="text-xs text-[var(--muted-foreground)]">Includes Collection Date, GEOID, Sample Prep/Run Date, Stat Screen status, and per-record Analyst QC Review decisions.</p>
            </div>
            <input id="flt-search-input" type="text" value="${state.search.replace(/"/g, '&quot;')}" oninput="updateSearch(this.value)" placeholder="Search record ID, parameter, GEOID, date, note..." class="rounded-lg px-3 py-1.5 text-xs border min-w-[260px]" />
          </div>
          <div class="flex flex-wrap items-center gap-1.5">
            ${expFilterBtns.map(b => `
              <button onclick="setExplorerFlagFilter('${b.id}')" class="px-2.5 py-1 rounded-lg text-xs font-semibold transition border ${state.explorerFlagFilter === b.id ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]' : 'bg-[var(--background)] text-[var(--muted-foreground)] border-[var(--border)] hover:text-[var(--foreground)]'}">${b.label}</button>
            `).join("")}
          </div>
          <div class="overflow-x-auto max-h-[560px] overflow-y-auto border border-[var(--border)] rounded-lg">
            <table class="w-full text-left border-collapse">
              <thead class="sticky top-0 bg-[var(--card)] shadow-sm z-10">
                <tr class="text-xs font-semibold text-[var(--muted-foreground)] border-b border-[var(--border)]">
                  <th class="py-2 px-2.5">Record ID</th>
                  <th class="py-2 px-2.5">Analysis Type</th>
                  <th class="py-2 px-2.5">Sample Lineage</th>
                  <th class="py-2 px-2.5">Collected &amp; GEOID</th>
                  <th class="py-2 px-2.5">Prep &amp; Run Date</th>
                  <th class="py-2 px-2.5">Exp</th>
                  <th class="py-2 px-2.5">Parameter</th>
                  <th class="py-2 px-2.5 text-right">Value</th>
                  <th class="py-2 px-2.5 text-center">Stat Screen</th>
                  <th class="py-2 px-2.5 text-center">QC</th>
                  <th class="py-2 px-2.5">Bench Note</th>
                  <th class="py-2 px-2.5">⚖️ Analyst Decision</th>
                </tr>
              </thead>
              <tbody>${rowsHtml}</tbody>
            </table>
          </div>
        </div>
      `;
    }

    function syncUrl() {
      try {
        const u = new URL(window.location.href);
        u.searchParams.set("resource", state.resource);
        u.searchParams.set("domain", state.domain);
        u.searchParams.set("subtab", state.subtab);
        u.searchParams.set("portal_qc", state.portalQcMode);
        window.history.replaceState({}, "", u.toString());
      } catch (_) {}
    }

    function render() {
      renderDomainPills();
      renderHeaderAndKpis();
      renderDecisionBanner();
      const container = document.getElementById("qc-content");
      if (state.subtab === "outliers") container.innerHTML = renderOutliersSubtab();
      else if (state.subtab === "rsd") container.innerHTML = renderRsdSubtab();
      else if (state.subtab === "notes") container.innerHTML = renderNotesSubtab();
      else if (state.subtab === "explorer") container.innerHTML = renderExplorerSubtab();
      syncUrl();
    }

    window.handleDecisionChange = function(key, decisionVal, encodedMeta) {
      let meta = {};
      try { meta = JSON.parse(decodeURIComponent(encodedMeta)); } catch (_) {}
      upsertDecisionEntry(key, { decision: decisionVal }, meta);
      renderDecisionBanner();
      renderHeaderAndKpis();
    };

    window.handleDecisionNote = function(key, noteVal, encodedMeta) {
      let meta = {};
      try { meta = JSON.parse(decodeURIComponent(encodedMeta)); } catch (_) {}
      const cur = getDecisionEntry(key);
      const nextDecision = (cur.decision === "pending" && noteVal.trim()) ? "keep" : cur.decision;
      upsertDecisionEntry(key, { decision: nextDecision, note: noteVal }, meta);
      renderDecisionBanner();
      renderHeaderAndKpis();
    };

    window.appendRationaleChip = function(key, chipText, encodedMeta) {
      let meta = {};
      try { meta = JSON.parse(decodeURIComponent(encodedMeta)); } catch (_) {}
      const cur = getDecisionEntry(key);
      const existingNote = (cur.note || "").trim();
      const nextNote = existingNote ? (existingNote.includes(chipText) ? existingNote : `${existingNote}; ${chipText}`) : chipText;
      const nextDecision = cur.decision === "pending" ? "exclude_qc_fail" : cur.decision;
      upsertDecisionEntry(key, { decision: nextDecision, note: nextNote }, meta);
      render();
    };

    window.removeDecisionEntry = function(key) {
      delete DECISIONS_STORE[key];
      saveDecisionsStore(DECISIONS_STORE);
      render();
    };

    window.toggleDecisionQueueTable = function() {
      state.showDecisionQueueTable = !state.showDecisionQueueTable;
      renderDecisionBanner();
    };

    window.clearAllDecisions = function() {
      DECISIONS_STORE = {};
      saveDecisionsStore(DECISIONS_STORE);
      render();
    };

    window.exportDecisionsCsv = function() {
      const entries = Object.values(DECISIONS_STORE);
      const cols = [
        "key", "scope", "resource_name", "analysis_type", "prepared_sample", "field_sample",
        "collected_date", "geoid", "prep_date", "experiment", "record_id", "parameter",
        "unit", "n", "mean", "sd", "rsd_within_pct", "dixon_q", "dixon_candidate_id",
        "record_ids", "decision", "note", "updated_at"
      ];
      const csv = [
        cols.join(","),
        ...entries.map(e => cols.map(c => `"${String(e[c] ?? '').replace(/"/g, '""')}"`).join(","))
      ].join("\\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `biocirv_qc_review_decisions_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    };

    window.exportDecisionsJson = function() {
      const entries = Object.values(DECISIONS_STORE);
      const blob = new Blob([JSON.stringify(entries, null, 2)], { type: "application/json;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `biocirv_qc_review_decisions_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    };

    window.selectResource = function(resName) {
      if (!RECORDS_BY_RESOURCE[resName]) return;
      state.resource = resName;
      state.prepared_sample = "all";
      state.experiment = "all";
      state.search = "";
      initResourceSwitcher();
      initFiltersForResource();
      render();
    };

    window.setDomain = function(d) {
      state.domain = d;
      render();
    };

    window.setOutlierFilterMode = function(mode) {
      state.outlierFilterMode = mode;
      render();
    };

    window.setExplorerFlagFilter = function(mode) {
      state.explorerFlagFilter = mode;
      render();
    };

    window.updateSearch = function(val) {
      state.search = val;
      render();
      const inp = document.getElementById("flt-search-input");
      if (inp) {
        inp.focus();
        inp.setSelectionRange(inp.value.length, inp.value.length);
      }
    };

    window.jumpToRecord = function(recId) {
      state.search = recId;
      state.explorerFlagFilter = "all";
      state.subtab = "explorer";
      render();
    };

    window.inspectSampleParam = function(sampleName, paramName) {
      state.prepared_sample = sampleName || "all";
      document.getElementById("flt-prepared-sample").value = state.prepared_sample;
      state.search = paramName || "";
      state.explorerFlagFilter = "all";
      state.subtab = "explorer";
      render();
    };

    document.getElementById("flt-resource").addEventListener("change", e => window.selectResource(e.target.value));
    document.getElementById("btn-prev-res").addEventListener("click", () => {
      const idx = ACTIVE_RESOURCES.indexOf(state.resource);
      window.selectResource(ACTIVE_RESOURCES[(idx - 1 + ACTIVE_RESOURCES.length) % ACTIVE_RESOURCES.length]);
    });
    document.getElementById("btn-next-res").addEventListener("click", () => {
      const idx = ACTIVE_RESOURCES.indexOf(state.resource);
      window.selectResource(ACTIVE_RESOURCES[(idx + 1) % ACTIVE_RESOURCES.length]);
    });
    document.getElementById("flt-portal-qc").addEventListener("change", e => {
      state.portalQcMode = e.target.value;
      render();
    });
    document.getElementById("flt-prepared-sample").addEventListener("change", e => {
      state.prepared_sample = e.target.value;
      render();
    });
    document.getElementById("flt-experiment").addEventListener("change", e => {
      state.experiment = e.target.value;
      render();
    });
    document.getElementById("chk-suppress-trace").addEventListener("change", e => {
      state.suppressTraceFlags = e.target.checked;
      render();
    });
    document.getElementById("btn-reset-filters").addEventListener("click", () => {
      state.domain = "all";
      state.portalQcMode = "all";
      document.getElementById("flt-portal-qc").value = "all";
      state.prepared_sample = "all";
      state.experiment = "all";
      state.search = "";
      state.outlierFilterMode = "flagged";
      state.explorerFlagFilter = "all";
      initFiltersForResource();
      render();
    });
    document.getElementById("btn-anon-analyst").addEventListener("click", () => {
      state.anonymizeAnalyst = !state.anonymizeAnalyst;
      render();
    });
    document.getElementById("btn-theme-toggle").addEventListener("click", () => {
      const htmlEl = document.documentElement;
      const next = htmlEl.getAttribute("data-theme") === "dark" ? "light" : "dark";
      htmlEl.setAttribute("data-theme", next);
      document.getElementById("btn-theme-toggle").textContent = next === "dark" ? "☀️ Light Mode" : "🌙 Dark Mode";
    });
    document.querySelectorAll(".subtab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        state.subtab = btn.dataset.subtab;
        render();
      });
    });

    document.getElementById("btn-export-flagged-csv").addEventListener("click", () => {
      const groups = getAllDomainOutlierGroups().filter(g => isGroupMatchingFilter(g, state.outlierFilterMode, state.suppressTraceFlags));
      const cols = [
        "resource_name", "analysis_type", "prepared_sample", "collected_date", "geoid", "prep_date",
        "prep_method", "experiment", "parameter", "unit", "n", "mean", "sd", "rsd_within_pct",
        "rsd_between_pct", "dixon_q", "dixon_crit", "dixon_candidate_id", "max_abs_dev", "pooled_sd",
        "below_cutoff", "cutoff_label", "qc_pass_count", "qc_fail_count", "replicates_summary",
        "analyst_decision", "analyst_review_note", "note"
      ];
      const rowsCsv = groups.map(g => {
        const repStr = (g.replicates || []).map(r => `${r.id}:${r.val}(${r.qc})`).join(" | ");
        const lin = getSampleLineageSummary(state.resource, g.prepared_sample);
        const dEntry = getDecisionEntry(makeGroupDecisionKey(state.resource, g));
        const rowObj = {
          resource_name: state.resource,
          collected_date: lin.collectedDate,
          geoid: lin.geoid,
          prep_date: lin.prepDate,
          ...g,
          replicates_summary: repStr,
          analyst_decision: dEntry.decision || "pending",
          analyst_review_note: dEntry.note || ""
        };
        return cols.map(c => `"${String(rowObj[c] ?? '').replace(/"/g, '""')}"`).join(",");
      });
      const csv = [cols.join(","), ...rowsCsv].join("\\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${state.resource.replace(/\\s+/g, "_")}_flagged_outlier_groups.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });

    document.getElementById("btn-download-records-csv").addEventListener("click", () => {
      const filtered = getFilteredExplorerRecords();
      const cols = [
        "resource_name", "record_id", "analysis_type", "prepared_sample", "field_sample",
        "collected_date", "geoid", "county_name", "prep_date", "exp_date", "prep_method",
        "experiment", "parameter", "value", "unit", "replicate", "pt_method", "eh_method",
        "vessel", "well_or_block", "qc_status", "portal_compliant", "analyst_decision",
        "analyst_review_note", "note"
      ];
      if (!state.anonymizeAnalyst) cols.splice(11, 0, "analyst");
      const csv = [
        cols.join(","),
        ...filtered.map(r => {
          const dEntry = getDecisionEntry(makeRecordDecisionKey(r.record_id));
          const rowObj = {
            ...r,
            analyst_decision: dEntry.decision || "pending",
            analyst_review_note: dEntry.note || ""
          };
          return cols.map(c => `"${String(rowObj[c] ?? '').replace(/"/g, '""')}"`).join(",");
        })
      ].join("\\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${state.resource.replace(/\\s+/g, "_")}_qc_records.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });

    initResourceSwitcher();
    initFiltersForResource();
    render();
  </script>
</body>
</html>
"""
    return (
        html_template.replace("__SHARED_CSS__", SHARED_CSS)
        .replace("__TITLE_PREFIX__", title_prefix)
        .replace("__DATA_JSON__", data_json)
        .replace("__DEFAULT_RESOURCE__", json.dumps(default_resource))
        .replace("__CHAR_PAGE_FILENAME__", char_page_filename)
        .replace("__CHAR_PAGE_FILENAME_JSON__", json.dumps(char_page_filename))
    )



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the modular 2-page Resource Characterization + Statistical QC Dashboard Suite."
    )
    parser.add_argument(
        "--from-snapshot",
        type=Path,
        default=None,
        help="Path to JSON snapshot from fetch_all_resource_data.",
    )
    parser.add_argument(
        "--sidecar",
        type=Path,
        default=DEFAULT_SIDECAR_PATH,
        help="Path to resource_ai_insights.json sidecar (computed on the fly if missing).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for resource_analysis_dashboard.html and resource_qc_outlier_dashboard.html.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=None,
        help="Optional directory to mirror generated HTML files.",
    )
    parser.add_argument(
        "--single-resource",
        type=str,
        default=None,
        help="Optional resource name to emit standalone single-resource collaborator dashboards.",
    )
    parser.add_argument(
        "--exclude-analyst",
        action="store_true",
        help="Mask analyst emails by default for external collaborator sharing.",
    )
    args = parser.parse_args()

    if args.from_snapshot is not None:
        raw_payload = json.loads(args.from_snapshot.read_text(encoding="utf-8"))
    else:
        from resource_explorer_dashboard import fetch_all_resource_data
        raw_payload = fetch_all_resource_data()

    if args.sidecar.exists():
        insights_sidecar = json.loads(args.sidecar.read_text(encoding="utf-8"))
    else:
        insights_sidecar = build_resource_insights(raw_payload)
        args.sidecar.parent.mkdir(parents=True, exist_ok=True)
        args.sidecar.write_text(json.dumps(insights_sidecar, indent=2), encoding="utf-8")

    bundle = prepare_dashboard_payload(
        raw_payload,
        insights_sidecar,
        single_resource=args.single_resource,
        exclude_analyst=args.exclude_analyst,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.single_resource:
        slug = args.single_resource.strip().lower().replace(" ", "_")
        char_name = f"{slug}_analysis_dashboard.html"
        qc_name = f"{slug}_qc_outlier_dashboard.html"
    else:
        char_name = "resource_analysis_dashboard.html"
        qc_name = "resource_qc_outlier_dashboard.html"

    char_html = build_analysis_dashboard_html(bundle, qc_page_filename=qc_name)
    qc_html = build_qc_outlier_dashboard_html(bundle, char_page_filename=char_name)

    char_file = args.output_dir / char_name
    qc_file = args.output_dir / qc_name
    char_file.write_text(char_html, encoding="utf-8")
    qc_file.write_text(qc_html, encoding="utf-8")

    print(f"Wrote Page 1 (Characterization & AI Brief): {char_file} ({char_file.stat().st_size / 1024:.1f} KB)")
    print(f"Wrote Page 2 (Statistical QC & Lab Notes Audit): {qc_file} ({qc_file.stat().st_size / 1024:.1f} KB)")

    if args.artifact_dir is not None:
        args.artifact_dir.mkdir(parents=True, exist_ok=True)
        for fname, html_content in [(char_name, char_html), (qc_name, qc_html)]:
            art_file = args.artifact_dir / fname
            art_file.write_text(html_content, encoding="utf-8")
            print(f"Mirrored to {art_file}")


if __name__ == "__main__":
    main()
