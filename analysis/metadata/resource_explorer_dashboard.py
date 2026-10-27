# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: Pixi
#     language: python
#     name: pixi
# ---

"""Multi-Resource Analytical & Bioconversion Explorer Dashboard Generator.

Queries PostgreSQL across all 127 resources, 147 field samples, 384 prepared samples,
and all 10 active Aim 1 & Aim 2 analytical/bioconversion record tables (11,974 rows),
dictionary-encodes the dataset into a compact (<1 MB) self-contained payload, and writes:
  1. exports/plots/metadata/resource_explorer_dashboard.html (12-column HTML5 Canvas Suite)
  2. exports/plots/metadata/resource_quick_widget.html (Compact HTML5 Canvas Quick Widget)

Run with:
    pixi run python analysis/metadata/resource_explorer_dashboard.py
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

try:
    from ca_biositing.datamodels.data_portal_views.common import (
        EXCLUDED_PROVIDERS,
        EXCLUDED_RESOURCES,
    )
except Exception:
    EXCLUDED_RESOURCES = {
        "sargassum",
        "#n/a",
        "lab media",
        "alfalfa",
        "almond hulls and shells mix",
        "almond shells and hulls mix",
        "almond woodchips",
    }
    EXCLUDED_PROVIDERS = {"jaguar"}

try:
    from analysis.metadata.resource_analysis_dashboard import (
        SHARED_SLICE_AND_BUG_MODALS_HTML,
        SHARED_SLICE_AND_BUG_MODALS_JS,
    )
except ImportError:
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    from resource_analysis_dashboard import (  # type: ignore[no-redef]
        SHARED_SLICE_AND_BUG_MODALS_HTML,
        SHARED_SLICE_AND_BUG_MODALS_JS,
    )


def fetch_all_resource_data() -> dict:
    """Query PostgreSQL for all resources, samples, and 10 analysis record tables."""
    os.environ.setdefault("POSTGRES_HOST", "localhost")
    from sqlalchemy import text
    from ca_biositing.datamodels.database import get_engine

    engine = get_engine()

    with engine.connect() as conn:
        # 1. All Resources (127)
        resources = [
            dict(r)
            for r in conn.execute(
                text(
                    """
                    SELECT r.id,
                           r.name,
                           COALESCE(r.resource_code, '') AS code,
                           COALESCE(rc.name, 'Unclassified') AS resource_class,
                           COALESCE(rsc.name, 'N/A') AS resource_subclass,
                           COALESCE(pap.name, 'N/A') AS primary_ag_product,
                           COALESCE(r.description, '') AS description
                    FROM resource r
                    LEFT JOIN resource_class rc ON r.resource_class_id = rc.id
                    LEFT JOIN resource_subclass rsc ON r.resource_subclass_id = rsc.id
                    LEFT JOIN primary_ag_product pap ON r.primary_ag_product_id = pap.id
                    ORDER BY r.name
                    """
                )
            )
            .mappings()
            .all()
        ]

        # 2. All Field Samples (147)
        field_samples = [
            dict(r)
            for r in conn.execute(
                text(
                    """
                    SELECT fs.id,
                           fs.name,
                           fs.resource_id,
                           COALESCE(r.name, 'Unassigned') AS resource_name,
                           COALESCE(p.codename, 'unknown') AS provider,
                           COALESCE(la.geography_id::text, '') AS geoid,
                           COALESCE(fs.collection_timestamp::text, '') AS collected_at,
                           COALESCE(fs.sample_collection_source, '') AS sample_source,
                           COALESCE(fs.note, '') AS note
                    FROM field_sample fs
                    LEFT JOIN resource r ON fs.resource_id = r.id
                    LEFT JOIN provider p ON fs.provider_id = p.id
                    LEFT JOIN location_address la ON fs.sampling_location_id = la.id
                    ORDER BY fs.name
                    """
                )
            )
            .mappings()
            .all()
        ]

        # 3. All Prepared Samples (384)
        prepared_samples = [
            dict(r)
            for r in conn.execute(
                text(
                    """
                    SELECT ps.id,
                           ps.name,
                           COALESCE(fs.resource_id, -1) AS resource_id,
                           ps.field_sample_id,
                           COALESCE(r.name, 'Unassigned') AS resource_name,
                           COALESCE(fs.name, 'Unassigned') AS field_sample_name,
                           COALESCE(p.codename, 'unknown') AS provider,
                           COALESCE(pm.name, 'N/A') AS prep_method,
                           COALESCE(ps.prep_date::text, '') AS prep_date,
                           COALESCE(c.email, c.name, 'Unassigned') AS preparer,
                           COALESCE(ps.note, '') AS note
                    FROM prepared_sample ps
                    LEFT JOIN field_sample fs ON ps.field_sample_id = fs.id
                    LEFT JOIN resource r ON fs.resource_id = r.id
                    LEFT JOIN provider p ON fs.provider_id = p.id
                    LEFT JOIN preparation_method pm ON ps.prep_method_id = pm.id
                    LEFT JOIN contact c ON ps.preparer_id = c.id
                    ORDER BY ps.name
                    """
                )
            )
            .mappings()
            .all()
        ]

        # 4. Unified query across all 10 active Aim 1 & Aim 2 record tables
        unified_sql = text(
            """
            WITH all_recs AS (
                SELECT 'Proximate Analysis' AS analysis_type, record_id, resource_id, prepared_sample_id,
                       experiment_id, method_id, analyst_id, dataset_id, technical_replicate_no AS replicate_no,
                       qc_pass, note,
                       NULL::int AS pt_method_id, NULL::int AS eh_method_id, NULL::int AS eh_method_id_new,
                       NULL::int AS vessel_id, NULL::int AS strain_id, NULL::int AS bioconv_id,
                       '' AS pos
                FROM proximate_record
                UNION ALL
                SELECT 'Compositional Analysis', record_id, resource_id, prepared_sample_id,
                       experiment_id, method_id, analyst_id, dataset_id, technical_replicate_no,
                       qc_pass, note,
                       NULL, NULL, NULL, NULL, NULL, NULL, ''
                FROM compositional_record
                UNION ALL
                SELECT 'Ultimate Analysis', record_id, resource_id, prepared_sample_id,
                       experiment_id, method_id, analyst_id, dataset_id, technical_replicate_no,
                       qc_pass, note,
                       NULL, NULL, NULL, NULL, NULL, NULL, ''
                FROM ultimate_record
                UNION ALL
                SELECT 'ICP Elemental Analysis', record_id, resource_id, prepared_sample_id,
                       experiment_id, method_id, analyst_id, dataset_id, technical_replicate_no,
                       qc_pass, note,
                       NULL, NULL, NULL, NULL, NULL, NULL, ''
                FROM icp_record
                UNION ALL
                SELECT 'XRF Elemental Analysis', record_id, resource_id, prepared_sample_id,
                       experiment_id, method_id, analyst_id, dataset_id, technical_replicate_no,
                       qc_pass, note,
                       NULL, NULL, NULL, NULL, NULL, NULL, ''
                FROM xrf_record
                UNION ALL
                SELECT 'Calorimetry', record_id, resource_id, prepared_sample_id,
                       experiment_id, method_id, analyst_id, dataset_id, technical_replicate_no,
                       qc_pass, note,
                       NULL, NULL, NULL, NULL, NULL, NULL, ''
                FROM calorimetry_record
                UNION ALL
                SELECT 'XRD Crystallinity', record_id, resource_id, prepared_sample_id,
                       experiment_id, method_id, analyst_id, dataset_id, technical_replicate_no,
                       qc_pass, note,
                       NULL, NULL, NULL, NULL, NULL, NULL, ''
                FROM xrd_record
                UNION ALL
                SELECT 'Pretreatment & Hydrolysis', record_id, resource_id, prepared_sample_id,
                       experiment_id, method_id, analyst_id, dataset_id, COALESCE(replicate_no, technical_replicate_no),
                       qc_pass, note,
                       pretreatment_method_id, eh_method_id, NULL,
                       vessel_id, NULL, NULL, COALESCE(block_position, '')
                FROM pretreatment_record
                UNION ALL
                SELECT 'Fermentation (Bioconversion)', record_id, resource_id, prepared_sample_id,
                       experiment_id, method_id, analyst_id, dataset_id, technical_replicate_no,
                       qc_pass, note,
                       pretreatment_method_id, eh_method_id, eh_method_id_new,
                       vessel_id, strain_id, bioconversion_method_id, COALESCE(well_position, '')
                FROM fermentation_record
                UNION ALL
                SELECT 'Gasification', record_id, resource_id, prepared_sample_id,
                       experiment_id, method_id, analyst_id, dataset_id, technical_replicate_no,
                       qc_pass, note,
                       NULL, NULL, NULL,
                       reactor_type_id, NULL, NULL, ''
                FROM gasification_record
            )
            SELECT
                ar.analysis_type,
                ar.record_id,
                COALESCE(r.name, r_via_ps.name, 'Unassigned') AS resource_name,
                COALESCE(ps.name, 'Unassigned') AS prepared_sample,
                COALESCE(fs.name, 'Unassigned') AS field_sample,
                COALESCE(prov.codename, 'unknown') AS provider,
                COALESCE(pm.name, 'N/A') AS prep_method,
                COALESCE(exp.name, 'Unassigned') AS experiment,
                COALESCE(CAST(exp.exper_start_date AS TEXT), '') AS exp_date,
                COALESCE(c.email, c.name, 'Unassigned') AS analyst,
                LOWER(COALESCE(ar.qc_pass, 'unknown')) AS qc_status,
                ar.replicate_no AS replicate,
                COALESCE(ar.note, '') AS note,
                COALESCE(ptm.name, 'N/A') AS pt_method,
                COALESCE(ehm_new.name, ehm.name, 'N/A') AS eh_method,
                COALESCE(v.name, 'N/A') AS vessel,
                COALESCE(st.name, 'N/A') AS strain,
                COALESCE(bm.name, 'N/A') AS bioconv,
                ar.pos AS well_or_block,
                COALESCE(param.name, '(metadata only)') AS parameter,
                o.value AS value,
                COALESCE(u.name, '') AS unit
            FROM all_recs ar
            LEFT JOIN observation o ON ar.record_id = o.record_id
            LEFT JOIN parameter param ON o.parameter_id = param.id
            LEFT JOIN unit u ON o.unit_id = u.id
            LEFT JOIN resource r ON ar.resource_id = r.id
            LEFT JOIN prepared_sample ps ON ar.prepared_sample_id = ps.id
            LEFT JOIN field_sample fs ON ps.field_sample_id = fs.id
            LEFT JOIN resource r_via_ps ON fs.resource_id = r_via_ps.id
            LEFT JOIN provider prov ON fs.provider_id = prov.id
            LEFT JOIN preparation_method pm ON ps.prep_method_id = pm.id
            LEFT JOIN experiment exp ON ar.experiment_id = exp.id
            LEFT JOIN contact c ON ar.analyst_id = c.id
            LEFT JOIN method ptm ON ar.pt_method_id = ptm.id
            LEFT JOIN method ehm ON ar.eh_method_id = ehm.id
            LEFT JOIN enz_hydr_method ehm_new ON ar.eh_method_id_new = ehm_new.id
            LEFT JOIN decon_vessel v ON ar.vessel_id = v.id
            LEFT JOIN strain st ON ar.strain_id = st.id
            LEFT JOIN bioconversion_method bm ON ar.bioconv_id = bm.id
            ORDER BY COALESCE(r.name, r_via_ps.name, 'Unassigned'), ar.analysis_type, ar.record_id
            """
        )

        rows = [dict(r) for r in conn.execute(unified_sql).mappings().all()]

    for res in resources:
        res["excluded_portal"] = res["name"].strip().lower() in EXCLUDED_RESOURCES

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
    dicts: dict[str, list[str]] = {}
    dict_maps: dict[str, dict[str, int]] = {}
    for col in str_cols:
        vals = sorted({str(r[col] or "") for r in rows})
        dicts[col] = vals
        dict_maps[col] = {v: i for i, v in enumerate(vals)}

    compact_rows = []
    for r in rows:
        val = round(float(r["value"]), 4) if r["value"] is not None else None
        encoded_row = [r["record_id"]]
        for col in str_cols:
            encoded_row.append(dict_maps[col][str(r[col] or "")])
        encoded_row.append(r["replicate"])
        encoded_row.append(val)
        encoded_row.append(str(r.get("exp_date") or "")[:10])
        compact_rows.append(encoded_row)

    return {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "excluded_resources": sorted(EXCLUDED_RESOURCES),
        "excluded_providers": sorted(EXCLUDED_PROVIDERS),
        "str_cols": str_cols,
        "dicts": dicts,
        "rows": compact_rows,
        "resources": resources,
        "field_samples": field_samples,
        "prepared_samples": prepared_samples,
    }


def load_ca_counties_lookup() -> dict[str, str]:
    """Load GEOID -> County Name mapping from data/static/ca_counties.csv."""
    lookup = {
        "06000": "California (Statewide)",
        "06001": "Alameda", "06003": "Alpine", "06005": "Amador", "06007": "Butte",
        "06009": "Calaveras", "06011": "Colusa", "06013": "Contra Costa", "06015": "Del Norte",
        "06017": "El Dorado", "06019": "Fresno", "06021": "Glenn", "06023": "Humboldt",
        "06025": "Imperial", "06027": "Inyo", "06029": "Kern", "06031": "Kings",
        "06033": "Lake", "06035": "Lassen", "06037": "Los Angeles", "06039": "Madera",
        "06041": "Marin", "06043": "Mariposa", "06045": "Mendocino", "06047": "Merced",
        "06049": "Modoc", "06051": "Mono", "06053": "Monterey", "06055": "Napa",
        "06057": "Nevada", "06059": "Orange", "06061": "Placer", "06063": "Plumas",
        "06065": "Riverside", "06067": "Sacramento", "06069": "San Benito", "06071": "San Bernardino",
        "06073": "San Diego", "06075": "San Francisco", "06077": "San Joaquin", "06079": "San Luis Obispo",
        "06081": "San Mateo", "06083": "Santa Barbara", "06085": "Santa Clara", "06087": "Santa Cruz",
        "06089": "Shasta", "06091": "Sierra", "06093": "Siskiyou", "06095": "Solano",
        "06097": "Sonoma", "06099": "Stanislaus", "06101": "Sutter", "06103": "Tehama",
        "06105": "Trinity", "06107": "Tulare", "06109": "Tuolumne", "06111": "Ventura",
        "06113": "Yolo", "06115": "Yuba",
    }
    return lookup


def build_full_dashboard_html(payload: dict) -> str:
    """Build the 12-column HTML5 Canvas + Tailwind multi-resource analytical & bioconversion dashboard."""
    slim_payload = {
        "generated_utc": payload.get("generated_utc", ""),
        "excluded_resources": payload.get("excluded_resources", []),
        "excluded_providers": payload.get("excluded_providers", []),
        "str_cols": payload["str_cols"],
        "dicts": payload["dicts"],
        "rows": payload["rows"],
        "resources": payload.get("resources", []),
        "field_samples": payload.get("field_samples", []),
        "prepared_samples": payload.get("prepared_samples", []),
        "county_lookup": load_ca_counties_lookup(),
    }
    for slice_key in (
        "collaborator_slice_mode",
        "single_resource",
        "slice_resources",
        "slice_pages",
        "slice_date_type",
        "slice_from_date",
        "slice_to_date",
        "slice_filters",
        "slice_qc_statuses",
        "exclude_analyst_default",
    ):
        if slice_key in payload:
            slim_payload[slice_key] = payload[slice_key]
    payload_json = json.dumps(slim_payload, separators=(",", ":")).replace("</", "<\\/")
    template = """<!DOCTYPE html>
<html lang="en" class="dark" data-theme="dark" data-user-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BioCirV — Interactive Feedstock Data Visualizer</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root,
    html[data-user-theme="dark"],
    body[data-user-theme="dark"] {
      --background: #0f172a;
      --card: #1e293b;
      --foreground: #f8fafc;
      --muted-foreground: #94a3b8;
      --primary: #00B5E2;
      --primary-foreground: #0f172a;
      --secondary: #334155;
      --secondary-foreground: #f8fafc;
      --border: #334155;
      color-scheme: dark;
    }
    html[data-user-theme="light"],
    body[data-user-theme="light"] {
      --background: #f8fafc;
      --card: #ffffff;
      --foreground: #0f172a;
      --muted-foreground: #475569;
      --primary: #00B5E2;
      --primary-foreground: #0f172a;
      --secondary: #e2e8f0;
      --secondary-foreground: #0f172a;
      --border: #cbd5e1;
      color-scheme: light;
    }
    body {
      background-color: var(--background) !important;
      color: var(--foreground) !important;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    select, input, textarea {
      background-color: var(--background) !important;
      color: var(--foreground) !important;
      border-color: var(--border) !important;
    }
    option, optgroup {
      background-color: var(--card) !important;
      color: var(--foreground) !important;
    }
    .hidden { display: none !important; }
    .bg-\\[var\\(--card\\)\\] { background-color: var(--card) !important; }
    .bg-\\[var\\(--background\\)\\] { background-color: var(--background) !important; }
    .bg-\\[var\\(--secondary\\)\\] { background-color: var(--secondary) !important; }
    .bg-\\[var\\(--primary\\)\\] { background-color: var(--primary) !important; }
    .text-\\[var\\(--foreground\\)\\] { color: var(--foreground) !important; }
    .text-\\[var\\(--muted-foreground\\)\\] { color: var(--muted-foreground) !important; }
    .text-\\[var\\(--secondary-foreground\\)\\] { color: var(--secondary-foreground) !important; }
    .text-\\[var\\(--primary-foreground\\)\\] { color: var(--primary-foreground) !important; }
    .border-\\[var\\(--border\\)\\] { border-color: var(--border) !important; }
    .hover\\:text-\\[var\\(--foreground\\)\\]:hover { color: var(--foreground) !important; }
    .hover\\:bg-\\[var\\(--secondary\\)\\]:hover { background-color: var(--secondary) !important; }
  </style>
</head>
<body data-user-theme="dark" class="bg-[var(--background)] text-[var(--foreground)] antialiased p-2 select-none">
  <div class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-xl p-3.5 shadow-sm max-w-7xl mx-auto">

    <!-- Row 0: Shared Suite Top Navigation Bar -->
    <div class="flex flex-wrap items-center justify-between gap-2 pb-2 mb-2 border-b border-[var(--border)] text-xs">
      <div class="flex flex-wrap items-center gap-1.5">
        <span class="px-2 py-0.5 rounded bg-[#00B5E2]/15 text-[#00B5E2] font-mono font-semibold uppercase tracking-wider text-[10px]">BioCirV Suite</span>
        <a id="suite-link-1" href="resource_analysis_dashboard.html" class="px-2.5 py-1 rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:border-[#00B5E2] transition-colors font-medium">
          1. Characterization &amp; AI Brief
        </a>
        <a id="suite-link-2" href="resource_qc_outlier_dashboard.html" class="px-2.5 py-1 rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:border-[#00B5E2] transition-colors font-medium">
          2. Statistical Snapshot
        </a>
        <a id="nav-page-workbench" href="/v1/dashboards/metadata/resource_audit_workbench.html" class="px-2.5 py-1 rounded-md border border-emerald-500/40 bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:border-emerald-400 transition-colors font-medium">
          ⚖️ 2B. QC Audit Workbench
        </a>
        <a id="suite-link-3" href="resource_explorer_dashboard.html" class="px-2.5 py-1 rounded-md bg-[#00B5E2] text-slate-950 font-semibold transition-colors shadow-sm">
          3. Data Visualizer
        </a>
        <a id="suite-link-5" href="../audit/db_environment_drift_dashboard.html" class="px-2.5 py-1 rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:border-[#00B5E2] transition-colors font-medium">
          4. DB Environment Drift
        </a>
      </div>
      <div class="flex items-center gap-1.5">
        <a href="../index.html" class="px-2.5 py-1 rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors font-medium">
          &larr; Gallery
        </a>
      </div>
    </div>

    <!-- Row 1: Top Header & View Switcher -->
    <div class="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-[var(--border)]">
      <div class="flex flex-wrap items-center gap-2.5">
        <div class="w-2.5 h-2.5 rounded-full bg-[#00B5E2]"></div>
        <h2 id="dashboard-title" class="text-[var(--foreground)] font-semibold text-base tracking-tight">BioCirV Interactive Feedstock Data Visualizer</h2>
        <span id="badge-count" class="text-xs px-2 py-0.5 rounded-full bg-[var(--secondary)] text-[var(--secondary-foreground)] font-medium">11,974 obs</span>
        <span id="badge-resource-meta" class="hidden sm:inline-block text-xs px-2 py-0.5 rounded-full border border-[var(--border)] text-[var(--muted-foreground)] font-mono">127 resources</span>
        <span id="live-qc-overlay-badge" class="hidden text-[11px] px-2 py-0.5 rounded-full border border-emerald-500/40 bg-emerald-500/10 text-emerald-400 font-mono"></span>
      </div>
      <div class="flex items-center gap-1.5">
        <div class="flex items-center gap-1 bg-[var(--background)] p-1 rounded-lg border border-[var(--border)]">
          <button type="button" id="tab-scatter" onclick="setTab('scatter')" class="text-xs px-2.5 py-1 rounded-md font-medium bg-[var(--primary)] text-[var(--primary-foreground)] transition-colors">
            Side-by-Side Parameter Plot
          </button>
          <button type="button" id="tab-strip" onclick="setTab('strip')" class="text-xs px-2.5 py-1 rounded-md font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors">
            Replicate Strip Plot
          </button>
        </div>
        <button type="button" id="btn-refresh-qc-state" onclick="window.refreshLiveQcOverlay && window.refreshLiveQcOverlay(true)" class="text-xs px-2.5 py-1 rounded-md border border-emerald-500/50 bg-[var(--background)] text-[var(--foreground)] hover:border-emerald-400 transition-colors font-semibold" title="Fetch latest QC decisions from API without regenerating HTML">
          ↻ Refresh QC State
        </button>
        <button type="button" id="btn-open-slice-modal" class="text-xs px-2.5 py-1 rounded-md border border-[#00B5E2]/50 bg-[var(--background)] text-[var(--foreground)] hover:border-[#00B5E2] transition-colors font-semibold">
          📤 Export Slice (.HTML)
        </button>
        <button type="button" id="btn-tray-to-workbench" onclick="exportExplorerTrayToWorkbench()" class="text-xs px-2.5 py-1 rounded-md bg-emerald-500 text-slate-950 font-semibold hover:opacity-90 transition-colors">
          ⚖️ Export to Audit Workbench
        </button>
        <button type="button" id="btn-open-bug-modal" class="text-xs px-2.5 py-1 rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] hover:border-amber-500 transition-colors font-semibold">
          🐛 Report a Bug
        </button>
        <button type="button" id="btn-theme" onclick="toggleTheme()" class="text-xs px-2 py-1 rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors" title="Toggle Light/Dark Theme">
          ☀️ Light
        </button>
      </div>
    </div>

    <!-- Workspace Two-Column Layout: Sticky Left Filter Sidebar (280px) + Right Interactive Workspace -->
    <div class="flex flex-col lg:flex-row gap-4 items-start pt-2">
      <!-- Sticky Left Filter Sidebar -->
      <aside id="explorer-sticky-filter-sidebar" class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-3.5 shadow-sm space-y-3.5 w-full lg:w-[280px] text-xs" style="width: 280px; position: sticky; top: 16px; max-height: calc(100vh - 32px); overflow-y: auto; flex-shrink: 0;">
        <!-- 1. Flag Filters -->
        <div class="space-y-2 pb-3 border-b border-[var(--border)]">
          <div class="flex items-center justify-between">
            <h2 class="text-[11px] font-bold uppercase tracking-wider text-[#00B5E2]">Flag Filters</h2>
            <button type="button" onclick="resetFilters()" class="text-[11px] px-1.5 py-0.5 rounded border border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
              Reset All
            </button>
          </div>
          <div>
            <label for="flt-explorer-flag-type" class="block text-[11px] text-[var(--muted-foreground)] font-medium mb-1">Flag Type:</label>
            <select id="flt-explorer-flag-type" onchange="onExplorerFlagTypeChange(this.value)" class="w-full bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-xs focus:outline-none">
              <option value="all" selected>All Records / Groups</option>
              <option value="active">Active Flagged Only</option>
              <option value="dixon">Dixon's Q Outlier</option>
              <option value="rsd">High RSD &gt; 20%</option>
              <option value="sd3">&gt;3&times;SD_pooled</option>
              <option value="identical">Identical Replicates</option>
              <option value="proximate_sum">Proximate Sum (Outside 95–105%)</option>
            </select>
          </div>
          <div>
            <label for="filter-status" class="block text-[11px] text-[var(--muted-foreground)] font-medium mb-1">Status / QC:</label>
            <select id="filter-status" onchange="applyFilters()" class="w-full bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-1 text-xs focus:outline-none">
              <option value="ALL">All Statuses &amp; QC</option>
              <option value="Portal Compliant">Portal Compliant</option>
              <option value="Raw">Raw / Portal Excluded</option>
              <option value="qc_pass" selected>qc_pass: pass</option>
              <option value="qc_fail">qc_pass: fail</option>
              <option value="qc_provisional">qc_pass: provisional/unknown</option>
            </select>
          </div>
        </div>

        <!-- 2. Choose an Analysis Type -->
        <div class="space-y-2 pb-3 border-b border-[var(--border)]">
          <h2 class="text-[11px] font-bold uppercase tracking-wider text-[#00B5E2]">Choose an Analysis Type</h2>
          <div id="domain-pill-bar" class="flex flex-wrap items-center gap-1.5 text-xs"></div>
        </div>

        <!-- 3. Additional Filters -->
        <div class="space-y-2.5">
          <h2 class="text-[11px] font-bold uppercase tracking-wider text-[#00B5E2]">Additional Filters</h2>

          <label class="flex items-center justify-between gap-1.5 px-2 py-1.5 rounded bg-[var(--card)] border border-[var(--border)] cursor-pointer">
            <span class="flex items-center gap-1.5">
              <input id="chk-explorer-suppress-trace" type="checkbox" checked onchange="toggleSuppressTrace(this.checked)" class="rounded" />
              <span>Suppress trace flags</span>
            </span>
            <span id="explorer-suppressed-count-badge" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--background)] text-[var(--muted-foreground)] border border-[var(--border)]">0 suppressed</span>
          </label>

          <label class="flex items-center gap-1.5 px-2 py-1.5 rounded bg-[var(--card)] border border-[var(--border)] cursor-pointer">
            <input id="chk-explorer-blind-mode" type="checkbox" onchange="toggleExplorerBlindMode(this.checked)" class="rounded" />
            <span>Blind review mode (hide flags)</span>
          </label>

          <div>
            <label for="filter-search" class="block text-[11px] text-[var(--muted-foreground)] font-medium mb-1">Keyword Search:</label>
            <input id="filter-search" type="search" oninput="onExplorerSearchChange(this.value)" placeholder="Search sample / parameter / ID..." class="w-full bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-xs focus:outline-none focus:border-[#00B5E2]" />
          </div>

          <!-- Toggle Inline 4-Column Multi-Select Checklists Drawer -->
          <button type="button" id="btn-toggle-drawer" onclick="toggleInlineChecklistDrawer()" class="w-full inline-flex items-center justify-between gap-1.5 px-2.5 py-1.5 rounded border border-[#00B5E2] bg-[#00B5E2]/15 text-[#00B5E2] font-semibold transition-colors">
            <span>&#9745; Multi-Select Checklists</span>
            <span id="drawer-chevron" class="text-[10px]">&#9652;</span>
          </button>

          <!-- Multi-Select Checklist Popover: Resources -->
          <div class="relative flex items-center gap-1 w-full" id="popover-wrap-resources">
            <button type="button" onclick="stepResource(-1)" class="px-1.5 py-1 rounded border border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]" title="Step to Previous Active Resource">&larr;</button>
            <button type="button" id="btn-popover-resources" onclick="togglePopover('resources', event)" class="flex-1 inline-flex items-center justify-between gap-1.5 px-2 py-1 rounded border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] hover:border-[#00B5E2] font-medium transition-colors min-w-0">
              <span id="label-popover-resources" class="truncate">Resources: All (43 active)</span>
              <span class="text-[10px] text-[var(--muted-foreground)]">&#9662;</span>
            </button>
            <button type="button" onclick="stepResource(1)" class="px-1.5 py-1 rounded border border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]" title="Step to Next Active Resource">&rarr;</button>
            <div id="panel-popover-resources" onclick="event.stopPropagation()" class="hidden absolute left-0 top-full mt-1 w-72 bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-lg shadow-xl z-50 p-2">
              <input id="search-popover-resources" type="text" oninput="renderChecklistItems('resources', true)" placeholder="Filter resources..." class="w-full bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-xs mb-1.5 focus:outline-none focus:border-[#00B5E2]" />
              <div class="flex flex-wrap items-center gap-1 pb-1.5 mb-1.5 border-b border-[var(--border)] text-[10px]">
                <span class="text-[var(--muted-foreground)] font-mono">Presets:</span>
                <button type="button" onclick="applyResourcePreset('hulls')" class="px-1.5 py-0.5 rounded bg-[#00B5E2]/15 text-[#00B5E2] border border-[#00B5E2]/40 hover:bg-[#00B5E2]/25 font-medium">Nut Hulls</button>
                <button type="button" onclick="applyResourcePreset('straws')" class="px-1.5 py-0.5 rounded bg-[#00B5E2]/15 text-[#00B5E2] border border-[#00B5E2]/40 hover:bg-[#00B5E2]/25 font-medium">Straws</button>
                <button type="button" onclick="applyResourcePreset('pomaces')" class="px-1.5 py-0.5 rounded bg-[#00B5E2]/15 text-[#00B5E2] border border-[#00B5E2]/40 hover:bg-[#00B5E2]/25 font-medium">Pomaces</button>
                <button type="button" onclick="selectTopDomainResources(4)" class="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 hover:bg-emerald-500/25 font-medium">Top 4 in Tab</button>
              </div>
              <div class="flex items-center justify-between gap-1 pb-1.5 mb-1.5 border-b border-[var(--border)] text-[11px]">
                <div class="flex items-center gap-1">
                  <button type="button" onclick="checklistAction('resources', 'domain')" class="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] hover:border-[#00B5E2]" title="Select all resources that have data in the active analysis tab">All in Tab</button>
                  <button type="button" onclick="checklistAction('resources', 'all')" class="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] hover:border-[#00B5E2]">All</button>
                  <button type="button" onclick="checklistAction('resources', 'clear')" class="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] hover:border-[#00B5E2]">Clear</button>
                  <button type="button" onclick="checklistAction('resources', 'invert')" class="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] hover:border-[#00B5E2]">Invert</button>
                </div>
                <span id="count-popover-resources" class="font-mono text-[var(--muted-foreground)]">0 checked</span>
              </div>
              <div id="list-popover-resources" class="max-h-60 overflow-y-auto space-y-0.5 pr-1"></div>
            </div>
          </div>

          <!-- Multi-Select Checklist Popover: Parameters -->
          <div class="relative flex items-center w-full" id="popover-wrap-params">
            <button type="button" id="btn-popover-params" onclick="togglePopover('params', event)" class="w-full inline-flex items-center justify-between gap-1.5 px-2.5 py-1 rounded border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] hover:border-[#00B5E2] font-medium transition-colors">
              <span id="label-popover-params" class="truncate">Params: All</span>
              <span class="text-[10px] text-[var(--muted-foreground)]">&#9662;</span>
            </button>
            <div id="panel-popover-params" onclick="event.stopPropagation()" class="hidden absolute left-0 top-full mt-1 w-72 bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-lg shadow-xl z-50 p-2">
              <input id="search-popover-params" type="text" oninput="renderChecklistItems('params', true)" placeholder="Filter parameters..." class="w-full bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-xs mb-1.5 focus:outline-none focus:border-[#00B5E2]" />
              <div class="flex items-center justify-between gap-1 pb-1.5 mb-1.5 border-b border-[var(--border)] text-[11px]">
                <div class="flex items-center gap-1">
                  <button type="button" onclick="checklistAction('params', 'all')" class="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] hover:border-[#00B5E2]">Select All</button>
                  <button type="button" onclick="checklistAction('params', 'clear')" class="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] hover:border-[#00B5E2]">Clear</button>
                  <button type="button" onclick="checklistAction('params', 'invert')" class="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] hover:border-[#00B5E2]">Invert</button>
                </div>
                <span id="count-popover-params" class="font-mono text-[var(--muted-foreground)]">0 checked</span>
              </div>
              <div id="list-popover-params" class="max-h-60 overflow-y-auto space-y-0.5 pr-1"></div>
            </div>
          </div>

          <!-- Multi-Select Checklist Popover: Prepared Samples -->
          <div class="relative flex items-center w-full" id="popover-wrap-samples">
            <button type="button" id="btn-popover-samples" onclick="togglePopover('samples', event)" class="w-full inline-flex items-center justify-between gap-1.5 px-2.5 py-1 rounded border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] hover:border-[#00B5E2] font-medium transition-colors">
              <span id="label-popover-samples" class="truncate">Samples: All</span>
              <span class="text-[10px] text-[var(--muted-foreground)]">&#9662;</span>
            </button>
            <div id="panel-popover-samples" onclick="event.stopPropagation()" class="hidden absolute left-0 top-full mt-1 w-72 bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-lg shadow-xl z-50 p-2">
              <input id="search-popover-samples" type="text" oninput="renderChecklistItems('samples', true)" placeholder="Filter prepared samples..." class="w-full bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-xs mb-1.5 focus:outline-none focus:border-[#00B5E2]" />
              <div class="flex items-center justify-between gap-1 pb-1.5 mb-1.5 border-b border-[var(--border)] text-[11px]">
                <div class="flex items-center gap-1">
                  <button type="button" onclick="checklistAction('samples', 'all')" class="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] hover:border-[#00B5E2]">Select All</button>
                  <button type="button" onclick="checklistAction('samples', 'clear')" class="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] hover:border-[#00B5E2]">Clear</button>
                  <button type="button" onclick="checklistAction('samples', 'invert')" class="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] hover:border-[#00B5E2]">Invert</button>
                </div>
                <span id="count-popover-samples" class="font-mono text-[var(--muted-foreground)]">0 checked</span>
              </div>
              <div id="list-popover-samples" class="max-h-60 overflow-y-auto space-y-0.5 pr-1"></div>
            </div>
          </div>

          <!-- Multi-Select Checklist Popover: Methods / Preps / Strains -->
          <div class="relative flex items-center w-full" id="popover-wrap-methods">
            <button type="button" id="btn-popover-methods" onclick="togglePopover('methods', event)" class="w-full inline-flex items-center justify-between gap-1.5 px-2.5 py-1 rounded border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] hover:border-[#00B5E2] font-medium transition-colors">
              <span id="label-popover-methods" class="truncate">Methods: All</span>
              <span class="text-[10px] text-[var(--muted-foreground)]">&#9662;</span>
            </button>
            <div id="panel-popover-methods" onclick="event.stopPropagation()" class="hidden absolute left-0 top-full mt-1 w-72 bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-lg shadow-xl z-50 p-2">
              <input id="search-popover-methods" type="text" oninput="renderChecklistItems('methods', true)" placeholder="Filter methods / preps / strains..." class="w-full bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-xs mb-1.5 focus:outline-none focus:border-[#00B5E2]" />
              <div class="flex items-center justify-between gap-1 pb-1.5 mb-1.5 border-b border-[var(--border)] text-[11px]">
                <div class="flex items-center gap-1">
                  <button type="button" onclick="checklistAction('methods', 'all')" class="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] hover:border-[#00B5E2]">Select All</button>
                  <button type="button" onclick="checklistAction('methods', 'clear')" class="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] hover:border-[#00B5E2]">Clear</button>
                  <button type="button" onclick="checklistAction('methods', 'invert')" class="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] hover:border-[#00B5E2]">Invert</button>
                </div>
                <span id="count-popover-methods" class="font-mono text-[var(--muted-foreground)]">0 checked</span>
              </div>
              <div id="list-popover-methods" class="max-h-60 overflow-y-auto space-y-0.5 pr-1"></div>
            </div>
          </div>

          <!-- Compare By Selector (Side-by-Side Visual Comparison) -->
          <div>
            <label for="compare-by-select" class="block text-[11px] text-[var(--muted-foreground)] font-medium mb-1">Compare By:</label>
            <select id="compare-by-select" onchange="onCompareByManualChange(this.value)" class="w-full bg-[var(--card)] text-[var(--foreground)] border border-[#00B5E2]/60 rounded px-1.5 py-1 text-xs font-medium focus:outline-none">
              <option value="auto">Auto (Resource / Method)</option>
              <option value="resource">Resource (Side-by-Side)</option>
              <option value="sample">Prepared Sample (Side-by-Side)</option>
              <option value="field_sample">Field Sample (Side-by-Side)</option>
              <option value="experiment">Experiment / Run (Side-by-Side)</option>
              <option value="method">Method / Prep / Strain (Side-by-Side)</option>
              <option value="collection_date">Collection Date Cohort (Side-by-Side)</option>
              <option value="prep_date">Prep / Run Date Cohort (Side-by-Side)</option>
            </select>
          </div>

          <!-- Date Range Filter (Collection Date or Run / Prep Date) -->
          <div class="space-y-1.5 pt-2 border-t border-[var(--border)]">
            <div class="flex items-center justify-between gap-1">
              <span class="text-[11px] text-[var(--muted-foreground)] font-medium">Date Range:</span>
              <button id="filter-date-clear" type="button" onclick="clearDateFilter()" class="hidden px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-400 border border-rose-500/30 hover:bg-rose-500/25 text-[10px] font-semibold" title="Clear date filter">&times; Clear</button>
            </div>
            <select id="filter-date-type" onchange="onDateFilterChange()" class="w-full bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-1 text-xs font-medium focus:outline-none">
              <option value="any">Col or Run/Prep</option>
              <option value="collected">Collection Date</option>
              <option value="run">Run / Prep Date</option>
            </select>
            <div class="grid grid-cols-2 gap-1">
              <input id="filter-from-date" type="date" min="2020-01-01" placeholder="2024-01-01" onfocus="onFromDateFocus(this)" oninput="onDateFilterChange()" onchange="onDateFilterChange()" class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-0.5 text-xs font-mono" title="From Date (defaults to 2024-01-01 when opened if empty)" />
              <input id="filter-to-date" type="date" min="2020-01-01" oninput="onDateFilterChange()" onchange="onDateFilterChange()" class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-0.5 text-xs font-mono" title="To Date (YYYY-MM-DD)" />
            </div>
            <span id="date-filter-active-badge" class="hidden inline-block text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"></span>
          </div>
        </div>
      </aside>

      <!-- Right Main Workspace -->
      <div class="flex-1 min-w-0 space-y-2.5 w-full" style="flex: 1; min-width: 0;">
        <!-- Always-Accessible 4-Column Multi-Select Checklist Drawer (Open by Default for Effortless Multi-Selection) -->
        <div id="inline-checklist-drawer" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 pb-2.5 border-b border-[var(--border)] text-xs">
      <!-- Column 1: Multi-Select Resources -->
      <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2 flex flex-col">
        <div class="flex items-center justify-between gap-1 mb-1">
          <span class="font-semibold text-[var(--foreground)]">1. Resources <span id="inline-count-resources" class="font-mono text-[10px] text-[#00B5E2]">(All)</span></span>
          <div class="flex items-center gap-1 text-[10px]">
            <button type="button" onclick="selectTopDomainResources(4)" class="px-1.5 py-0.5 rounded bg-[#00B5E2]/15 text-[#00B5E2] hover:bg-[#00B5E2]/25 font-medium" title="Check Top 4 Resources in Active Analysis Tab">Top 4</button>
            <button type="button" onclick="checklistAction('resources', 'domain')" class="px-1.5 py-0.5 rounded border border-[var(--border)] hover:border-[#00B5E2]" title="Check all resources with data in this tab">Tab All</button>
            <button type="button" onclick="checklistAction('resources', 'clear')" class="px-1.5 py-0.5 rounded border border-[var(--border)] hover:border-rose-500 text-[var(--muted-foreground)] hover:text-rose-400">Clear</button>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-1 mb-1 text-[10px]">
          <button type="button" onclick="applyResourcePreset('hulls')" class="px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] hover:border-[#00B5E2]">Nut Hulls</button>
          <button type="button" onclick="applyResourcePreset('straws')" class="px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] hover:border-[#00B5E2]">Straws</button>
          <button type="button" onclick="applyResourcePreset('pomaces')" class="px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] hover:border-[#00B5E2]">Pomaces</button>
        </div>
        <input id="inline-search-resources" type="text" oninput="syncChecklistSearch('resources', this.value)" placeholder="Search resources..." class="w-full bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-[11px] mb-1 focus:outline-none focus:border-[#00B5E2]" />
        <div id="inline-list-resources" class="h-32 overflow-y-auto space-y-0.5 pr-1"></div>
      </div>

      <!-- Column 2: Multi-Select Parameters (with Units) -->
      <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2 flex flex-col">
        <div class="flex items-center justify-between gap-1 mb-1">
          <span class="font-semibold text-[var(--foreground)]">2. Parameters &amp; Units <span id="inline-count-params" class="font-mono text-[10px] text-emerald-400">(All)</span></span>
          <div class="flex items-center gap-1 text-[10px]">
            <button type="button" onclick="checklistAction('params', 'all')" class="px-1.5 py-0.5 rounded border border-[var(--border)] hover:border-[#00B5E2]">All</button>
            <button type="button" onclick="checklistAction('params', 'clear')" class="px-1.5 py-0.5 rounded border border-[var(--border)] hover:border-rose-500 text-[var(--muted-foreground)] hover:text-rose-400">Clear</button>
          </div>
        </div>
        <div class="text-[10px] text-[var(--muted-foreground)] mb-1">Check 1 parameter to compare resources side-by-side on its exact unit scale, or check multiple:</div>
        <input id="inline-search-params" type="text" oninput="syncChecklistSearch('params', this.value)" placeholder="Search parameters..." class="w-full bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-[11px] mb-1 focus:outline-none focus:border-[#00B5E2]" />
        <div id="inline-list-params" class="h-32 overflow-y-auto space-y-0.5 pr-1"></div>
      </div>

      <!-- Column 3: Multi-Select Prepared Samples -->
      <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2 flex flex-col">
        <div class="flex items-center justify-between gap-1 mb-1">
          <span class="font-semibold text-[var(--foreground)]">3. Prepared Samples <span id="inline-count-samples" class="font-mono text-[10px] text-amber-400">(All)</span></span>
          <div class="flex items-center gap-1 text-[10px]">
            <button type="button" onclick="checklistAction('samples', 'all')" class="px-1.5 py-0.5 rounded border border-[var(--border)] hover:border-[#00B5E2]">All</button>
            <button type="button" onclick="checklistAction('samples', 'clear')" class="px-1.5 py-0.5 rounded border border-[var(--border)] hover:border-rose-500 text-[var(--muted-foreground)] hover:text-rose-400">Clear</button>
          </div>
        </div>
        <div class="text-[10px] text-[var(--muted-foreground)] mb-1">Check specific prepared samples across selected resources:</div>
        <input id="inline-search-samples" type="text" oninput="syncChecklistSearch('samples', this.value)" placeholder="Search samples..." class="w-full bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-[11px] mb-1 focus:outline-none focus:border-[#00B5E2]" />
        <div id="inline-list-samples" class="h-32 overflow-y-auto space-y-0.5 pr-1"></div>
      </div>

      <!-- Column 4: Multi-Select Methods / Preps / Strains -->
      <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2 flex flex-col">
        <div class="flex items-center justify-between gap-1 mb-1">
          <span class="font-semibold text-[var(--foreground)]">4. Methods / Preps / Strains <span id="inline-count-methods" class="font-mono text-[10px] text-purple-400">(All)</span></span>
          <div class="flex items-center gap-1 text-[10px]">
            <button type="button" onclick="checklistAction('methods', 'all')" class="px-1.5 py-0.5 rounded border border-[var(--border)] hover:border-[#00B5E2]">All</button>
            <button type="button" onclick="checklistAction('methods', 'clear')" class="px-1.5 py-0.5 rounded border border-[var(--border)] hover:border-rose-500 text-[var(--muted-foreground)] hover:text-rose-400">Clear</button>
          </div>
        </div>
        <div class="text-[10px] text-[var(--muted-foreground)] mb-1">Filter or compare drying, milling, pretreatment, or strain conditions:</div>
        <input id="inline-search-methods" type="text" oninput="syncChecklistSearch('methods', this.value)" placeholder="Search methods / preps..." class="w-full bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-[11px] mb-1 focus:outline-none focus:border-[#00B5E2]" />
        <div id="inline-list-methods" class="h-32 overflow-y-auto space-y-0.5 pr-1"></div>
      </div>
    </div>

    <!-- Active Comparison Chips Bar (Shown when any checklist items are checked) -->
    <div id="active-chips-bar" class="hidden flex flex-wrap items-center gap-1.5 py-1.5 border-b border-[var(--border)] text-xs"></div>

    <!-- Empty Slice Helpful Action Banner (Shown when selected resource has 0 records in clicked Analysis Type) -->
    <div id="empty-slice-banner" class="hidden my-2 p-2.5 rounded-lg border border-amber-500/50 bg-amber-500/10 text-xs flex flex-wrap items-center justify-between gap-2"></div>

    <!-- Row 4: Main 12-Column Workspace -->
    <div id="view-charts" class="grid grid-cols-12 gap-3 pt-2.5 items-start">
      <!-- Left (col-span-8): Interactive High-DPI Canvas Plot -->
      <div class="col-span-12 lg:col-span-8 bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5 relative canvas-container">
        <!-- Quick Parameter Pill Bar for Instant Single-Parameter or Multi-Parameter Comparison with Units -->
        <div id="param-pill-bar" class="flex flex-wrap items-center gap-1 pb-2 mb-2 border-b border-[var(--border)] text-xs"></div>

        <div class="flex flex-wrap items-center justify-between gap-2 mb-1.5 px-1">
          <span id="chart-title" class="text-xs font-semibold text-[var(--foreground)]">Proximate Analysis — Side-by-Side Parameter Comparison</span>

          <div class="flex flex-wrap items-center gap-2">
            <!-- X-Axis Grouping Layout Toggle (shown in Scatter tab) -->
            <div id="xaxis-layout-controls" class="flex flex-wrap items-center gap-1 text-xs bg-[var(--card)] px-1.5 py-0.5 rounded border border-[var(--border)]">
              <span class="text-[var(--muted-foreground)]">X-Axis:</span>
              <button type="button" id="btn-xlayout-auto" onclick="setXLayoutMode('auto')" class="px-1.5 py-0.5 rounded text-xs font-medium bg-[var(--primary)] text-[var(--primary-foreground)]" title="Auto: Resources side-by-side when 1 parameter is focused, or Parameters with Resource sub-lanes">Auto</button>
              <button type="button" id="btn-xlayout-resources" onclick="setXLayoutMode('resources')" class="px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]" title="Place Selected Resources / Conditions directly on the X-Axis for head-to-head comparison">Resources Side-by-Side</button>
              <button type="button" id="btn-xlayout-by_field_sample" onclick="setXLayoutMode('by_field_sample')" class="px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]" title="Group observations along the X-Axis by Field Sample">Field Sample</button>
              <button type="button" id="btn-xlayout-by_experiment" onclick="setXLayoutMode('by_experiment')" class="px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]" title="Group observations along the X-Axis by Experiment / Run">Experiment</button>
              <button type="button" id="btn-xlayout-params" onclick="setXLayoutMode('params')" class="px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]" title="Place Parameters on the X-Axis with Resource sub-lanes">Parameters</button>
              <button type="button" id="btn-xlayout-dates" onclick="setXLayoutMode('dates')" class="px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]" title="Plot observations grouped chronologically by Collection Date or Run / Prep Date Cohort">Collection / Run Dates</button>
            </div>

            <!-- Replicate Plot Mode Toggle (Individual Points vs Replicate Mean ± SD) -->
            <div id="rep-mode-controls" class="flex items-center gap-1 text-xs bg-[var(--card)] px-1.5 py-0.5 rounded border border-[#00B5E2]/50">
              <span class="text-[var(--muted-foreground)] font-medium">Points:</span>
              <select id="rep-mode-select" onchange="setRepPlotMode(this.value)" class="bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-0.5 text-xs font-medium focus:outline-none">
                <option value="individual">Individual Points</option>
                <option value="mean_sd">Replicate Mean &plusmn; SD</option>
              </select>
            </div>

            <!-- Y-Axis Range Toggle (Auto-Fit Actual Values vs Full 0-100% Scale) -->
            <div id="yrange-controls" class="flex items-center gap-1 text-xs bg-[var(--card)] px-1.5 py-0.5 rounded border border-[var(--border)]">
              <span class="text-[var(--muted-foreground)]">Y-Range:</span>
              <button type="button" id="btn-yrange-auto" onclick="setYRangeMode('auto')" class="px-1.5 py-0.5 rounded text-xs font-medium bg-[var(--primary)] text-[var(--primary-foreground)]" title="Auto-scale Y-axis to the actual measured parameter values &amp; units">Auto-Fit Values</button>
              <button type="button" id="btn-yrange-full" onclick="setYRangeMode('full')" class="px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]" title="Fix Y-axis to 0–100%">0–100%</button>
              <button type="button" class="btn-Action px-1.5 py-0.5 rounded text-xs font-medium bg-sky-500/15 text-sky-400 border border-sky-500/40 hover:bg-sky-500/25" id="btn-reset-zoom" onclick="resetCanvasZoom()" style="display:none;">↺ Reset Zoom</button>
            </div>

            <!-- Strip Sort Control (shown in Strip tab) -->
            <div id="strip-controls" class="hidden flex items-center gap-1.5 text-xs">
              <span class="text-[var(--muted-foreground)]">Sort:</span>
              <select id="strip-sort" onchange="renderCurrentView()" class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-0.5 text-xs">
                <option value="mean">Highest Mean Value (Actual Units)</option>
                <option value="spread">Widest Replicate Range</option>
                <option value="count">Most Replicates</option>
              </select>
            </div>

            <!-- Scale Toggle (shown on ICP / XRF / Gasification) -->
            <div id="scale-controls" class="hidden flex items-center gap-1 text-xs bg-[var(--card)] px-1.5 py-0.5 rounded border border-[var(--border)]">
              <span class="text-[var(--muted-foreground)]">Scale:</span>
              <button type="button" id="btn-scale-linear" onclick="setScaleMode('linear')" class="px-1.5 py-0.5 rounded text-xs font-medium">Linear</button>
              <button type="button" id="btn-scale-log" onclick="setScaleMode('log')" class="px-1.5 py-0.5 rounded text-xs font-medium bg-[var(--primary)] text-[var(--primary-foreground)]">Log10</button>
            </div>

            <!-- Fermentation X-Axis Toggle (shown on Fermentation) -->
            <div id="ferm-controls" class="hidden flex items-center gap-1 text-xs bg-[var(--card)] px-1.5 py-0.5 rounded border border-[var(--border)]">
              <span class="text-[var(--muted-foreground)]">Mode:</span>
              <button type="button" id="btn-ferm-param" onclick="setFermXMode('param')" class="px-1.5 py-0.5 rounded text-xs font-medium bg-[var(--primary)] text-[var(--primary-foreground)]">By Parameter</button>
              <button type="button" id="btn-ferm-time" onclick="setFermXMode('time')" class="px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]">Time (Hours)</button>
            </div>

            <!-- Dynamic Method / Series Shape & Color Legend -->
            <div id="method-legend" class="flex flex-wrap items-center gap-2.5 text-xs text-[var(--muted-foreground)]"></div>
          </div>
        </div>

        <div id="canvas-zoom-brush" style="display:none; pointer-events:none; position:absolute; border:1.5px dashed #0284c7; background:rgba(2,132,199,0.12); z-index:12;"></div>
        <canvas id="plot-canvas" width="640" height="365" style="width: 100%; height: 365px;" class="w-full h-[365px] cursor-crosshair block"></canvas>

        <!-- Floating Hover Tooltip -->
        <div id="hover-tooltip" class="hidden pointer-events-none absolute z-20 bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-lg p-2 shadow-lg text-xs max-w-[295px]"></div>

        <!-- Interactive Click-Point Audit Finding Popover -->
        <div id="click-audit-popover" onclick="event.stopPropagation()" class="hidden absolute z-30 bg-[var(--card)] text-[var(--foreground)] border-2 border-[#00B5E2] rounded-xl p-3 shadow-2xl text-xs w-[320px] max-w-[92vw]">
          <div class="flex items-start justify-between gap-2 pb-1.5 mb-2 border-b border-[var(--border)]">
            <div class="min-w-0">
              <div class="flex items-center gap-1.5">
                <span class="px-1.5 py-0.5 rounded bg-[#00B5E2]/15 text-[#00B5E2] font-mono text-[10px] font-semibold">Quick Audit</span>
                <span id="click-popover-title" class="font-semibold text-[var(--foreground)] truncate">Sample</span>
              </div>
              <div id="click-popover-subtitle" class="text-[11px] text-[var(--muted-foreground)] truncate mt-0.5">Resource · Parameter</div>
            </div>
            <button type="button" onclick="closeClickAuditPopover()" class="text-[var(--muted-foreground)] hover:text-[var(--foreground)] px-1 text-sm font-bold leading-none" title="Close">&times;</button>
          </div>
          <div id="click-popover-metrics" class="bg-[var(--background)] border border-[var(--border)] rounded p-1.5 mb-2 font-mono text-[11px] space-y-0.5"></div>
          <div class="mb-2">
            <label class="block text-[10px] uppercase tracking-wider font-mono text-[var(--muted-foreground)] mb-1">Bring Into Audit Finding:</label>
            <div class="flex gap-1 bg-[var(--background)] p-0.5 rounded border border-[var(--border)]">
              <button type="button" id="btn-audit-scope-group" onclick="setAuditPopoverScope('group')" class="flex-1 py-1 px-2 rounded text-[11px] font-semibold bg-[#00B5E2] text-slate-950 transition-colors">
                Replicate Group (1 pt)
              </button>
              <button type="button" id="btn-audit-scope-single" onclick="setAuditPopoverScope('single')" class="flex-1 py-1 px-2 rounded text-[11px] font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors">
                Single Point Only
              </button>
            </div>
          </div>
          <div class="mb-2">
            <label class="block text-[10px] uppercase tracking-wider font-mono text-[var(--muted-foreground)] mb-1">Audit Action / QC Status:</label>
            <select id="click-popover-action" class="w-full bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-xs font-medium focus:outline-none focus:border-[#00B5E2]">
              <option value="keep_note" selected>📋 Flag for Review / Keep with Audit Note (Provisional)</option>
              <option value="flag_fail">⚑ Flag Outlier / Set QC Fail (exclude)</option>
              <option value="approve_pass">✓ Verify &amp; Approve (Set QC Pass)</option>
            </select>
          </div>
          <div class="mb-2">
            <input id="click-popover-assignee" type="email" placeholder="Assign reviewer email (e.g. analyst@lbl.gov, optional)..." class="w-full bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-xs focus:outline-none focus:border-[#00B5E2]" />
          </div>
          <div class="mb-2">
            <input id="click-popover-note" type="text" placeholder="Audit rationale / note (optional)..." onkeydown="if(event.key==='Enter'){event.preventDefault();submitClickPopoverAuditFinding();}" class="w-full bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-xs focus:outline-none focus:border-[#00B5E2]" />
          </div>
          <div class="flex flex-wrap items-center gap-1.5">
            <button type="button" onclick="submitClickPopoverAuditFinding()" class="flex-1 bg-[#00B5E2] text-slate-950 font-semibold py-1.5 px-2.5 rounded hover:opacity-90">
              Submit Audit Finding
            </button>
            <button type="button" id="btn-qc-pop-show-me" onclick="openShowMeFromClickPopover(this)" class="btn-show-me-flag btn-audit-show-me px-2 py-1.5 rounded bg-[var(--background)] text-[#00B5E2] hover:bg-[#00B5E2]/10 border border-[#00B5E2]/40 font-semibold" title="Show replicate group and outlier in slice context">
              👁 Show me
            </button>
            <button type="button" onclick="escalateClickPopoverToModal()" class="px-2 py-1.5 rounded bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] border border-[var(--border)]" title="Open full Submit Audit Finding / Escalation modal">
              Full Modal&hellip;
            </button>
          </div>
          <div id="click-popover-feedback" class="hidden mt-2 px-2 py-1 rounded text-[11px] font-medium text-emerald-400 bg-emerald-950/40 border border-emerald-500/40"></div>
        </div>
      </div>

      <!-- Right (col-span-4): Side-by-Side Comparison Card + Dynamic KPI Cards + Lineage/Date/GEOID Card + Closure Badge + Pinned Point Inspector -->
      <div class="col-span-12 lg:col-span-4 flex flex-col gap-2">
        <!-- Side-by-Side Condition Comparison Card (Shown when >=2 comparison groups are active) -->
        <div id="side-by-side-comparison-card" class="hidden bg-[var(--background)] border border-[#00B5E2]/60 rounded-lg p-2.5 text-xs"></div>

        <!-- 2x2 Summary Metrics Grid -->
        <div id="summary-kpi-grid" class="grid grid-cols-2 gap-1.5"></div>

        <!-- Sample Lineage, Collection Date, GEOID & Run/Prep Date Summary Card -->
        <div id="lineage-date-geoid-card" class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2 text-xs space-y-1"></div>

        <!-- Mass-Balance Closure Indicator (shown for Proximate & Compositional) -->
        <div id="closure-banner" class="hidden bg-[var(--background)] border border-[var(--border)] rounded-lg px-2.5 py-1.5 flex items-center justify-between text-xs">
          <span id="closure-label" class="text-[var(--muted-foreground)] font-medium">Mass-Balance Closure:</span>
          <span id="closure-value" class="font-mono font-semibold text-[#00B5E2]">—</span>
        </div>

        <!-- Pinned Record Inspector -->
        <div class="bg-[var(--background)] border border-[#00B5E2]/60 rounded-lg p-2.5 flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-xs font-semibold text-[var(--foreground)]">Pinned Point Inspector</span>
              <span id="pin-status-badge" class="text-xs px-1.5 py-0.5 rounded bg-[var(--secondary)] text-[var(--secondary-foreground)]">Click a point</span>
            </div>
            <div id="pinned-details" class="text-xs text-[var(--muted-foreground)] space-y-1 min-h-[145px]">
              <p class="pt-4 text-center">Click any point on the chart to inspect record details, collection date, GEOID, and prep/run date, or submit an audit finding for the point or its replicate group.</p>
            </div>
          </div>
          <div id="pinned-actions" class="hidden pt-2 mt-1.5 border-t border-[var(--border)] flex flex-col gap-1.5">
            <div class="grid grid-cols-2 gap-1">
              <select id="pin-audit-scope" class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-1 text-[11px] font-medium focus:outline-none">
                <option value="group" id="pin-scope-group-opt">Entire Replicate Group</option>
                <option value="single">Single Point Only</option>
              </select>
              <select id="pin-audit-action" class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-1 text-[11px] font-medium focus:outline-none">
                <option value="keep_note" selected>📋 Flag for Review / Note (Provisional)</option>
                <option value="flag_fail">⚑ Flag Outlier (Fail)</option>
                <option value="approve_pass">✓ Approve (Pass)</option>
              </select>
            </div>
            <input id="pin-audit-assignee" type="email" placeholder="Assign reviewer email (e.g. analyst@lbl.gov, optional)..." class="w-full bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-xs focus:outline-none" />
            <input id="pin-note" type="text" placeholder="Add audit note / rationale..." class="w-full bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-xs focus:outline-none" />
            <div class="flex flex-wrap items-center gap-1.5">
              <button type="button" onclick="submitPinnedAuditFinding()" class="flex-1 bg-[#00B5E2] text-slate-950 font-semibold text-xs py-1 px-2 rounded hover:opacity-90">
                Submit Audit
              </button>
              <button type="button" onclick="escalatePinnedToModal()" class="bg-[var(--card)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] text-xs py-1 px-2 rounded border border-[var(--border)]" title="Open full Submit Audit Finding modal">
                Modal&hellip;
              </button>
              <button type="button" onclick="copyRecordId()" id="btn-copy-id" class="bg-[var(--card)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] text-xs py-1 px-2 rounded border border-[var(--border)]">
                Copy ID
              </button>
            </div>
            <div id="pin-audit-feedback" class="hidden px-2 py-1 rounded text-[11px] font-medium"></div>
          </div>
        </div>
      </div>

      <!-- Full-Width Collapsible Statistical Precision & Candidate Outlier Drawer (Collapsed by Default) -->
      <div id="stat-screening-drawer" class="col-span-12 mt-1"></div>
    </div>
      </div>
    </div>

  </div>
__SHARED_SLICE_AND_BUG_MODALS_HTML__

  <script>
    const RAW_DATA = __PAYLOAD_JSON__;

    const EXCLUDED_RESOURCES_SET = new Set((RAW_DATA.excluded_resources || []).map(x => x.toLowerCase()));
    const EXCLUDED_PROVIDERS_SET = new Set((RAW_DATA.excluded_providers || []).map(x => x.toLowerCase()));
    const RESOURCES_BY_NAME = {};
    (RAW_DATA.resources || []).forEach(r => { RESOURCES_BY_NAME[r.name] = r; });

    const COUNTY_LOOKUP = RAW_DATA.county_lookup || {};
    const FIELD_SAMPLES_BY_NAME = {};
    (RAW_DATA.field_samples || []).forEach(fs => {
      if (fs && fs.name) FIELD_SAMPLES_BY_NAME[fs.name] = fs;
    });
    const PREP_SAMPLES_BY_NAME = {};
    (RAW_DATA.prepared_samples || []).forEach(ps => {
      if (ps && ps.name) PREP_SAMPLES_BY_NAME[ps.name] = ps;
    });

    function formatShortDate(dtStr) {
      if (!dtStr || dtStr === 'None' || dtStr === 'null' || dtStr === '—') return 'Unrecorded';
      return String(dtStr).slice(0, 10);
    }

    function formatDateCohort(dtStr) {
      const d = formatShortDate(dtStr);
      return d === 'Unrecorded' ? 'Unrecorded Date' : d.slice(0, 7);
    }

    // Standard IUPAC chemical element symbols for proper capitalization in ICP & XRF
    const CHEMICAL_SYMBOLS = new Set([
      'H','He','Li','Be','B','C','N','O','F','Ne','Na','Mg','Al','Si','P','S','Cl','Ar',
      'K','Ca','Sc','Ti','V','Cr','Mn','Fe','Co','Ni','Cu','Zn','Ga','Ge','As','Se','Br','Kr',
      'Rb','Sr','Y','Zr','Nb','Mo','Tc','Ru','Rh','Pd','Ag','Cd','In','Sn','Sb','Te','I','Xe',
      'Cs','Ba','La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu',
      'Hf','Ta','W','Re','Os','Ir','Pt','Au','Hg','Tl','Pb','Bi','Po','At','Rn'
    ]);

    function formatElementSymbol(sym) {
      if (!sym || sym === '(metadata only)') return sym;
      const trimmed = String(sym).trim();
      if (trimmed.length >= 1 && trimmed.length <= 2) {
        const candidate = trimmed.charAt(0).toUpperCase() + trimmed.slice(1).toLowerCase();
        if (CHEMICAL_SYMBOLS.has(candidate)) return candidate;
      }
      return trimmed;
    }

    // Shared DOMAIN_DEFS and normalizeDomainKey(raw) are injected into this <script> scope
    // via SHARED_SLICE_AND_BUG_MODALS_JS (exposed as window.DOMAIN_DEFS and window.normalizeDomainKey).

    // 10 Individual Analysis Type Pill Definitions
    const DOMAINS = [
      { id: 'proximate', label: 'Proximate', title: 'Proximate Analysis — Parameter & Resource Comparison', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'calorimetry', label: 'Calorimetry', title: 'Calorimetry — Parameter & Resource Comparison', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'compositional', label: 'Compositional', title: 'Compositional Biopolymers — Parameter & Resource Comparison', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'ultimate', label: 'Ultimate', title: 'Ultimate Elemental & Fiber — Parameter & Resource Comparison', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'xrd', label: 'XRD', title: 'XRD Crystallinity — Parameter & Resource Comparison', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'icp', label: 'ICP', title: 'ICP-OES Elemental Concentration — Parameter & Resource Comparison (ppm)', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'xrf', label: 'XRF', title: 'XRF Elemental Concentration — Parameter & Resource Comparison (ppm)', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'pretreatment', label: 'Pretreatment', title: 'Pretreatment Hydrolysis Yields — Parameter & Resource Comparison', methodCol: 'pt_method', methodLabel: 'Method:' },
      { id: 'fermentation', label: 'Fermentation', title: 'Fermentation Bioconversion — Parameter & Resource Comparison', methodCol: 'pt_method', methodLabel: 'Method:' },
      { id: 'gasification', label: 'Gasification', title: 'Gasification Syngas & Mass Balance — Parameter & Resource Comparison', methodCol: 'prep_method', methodLabel: 'Prep:' }
    ];

    function mapAnalysisTypeToDomain(at) {
      if (at === 'Proximate Analysis') return 'proximate';
      if (at === 'Calorimetry') return 'calorimetry';
      if (at === 'Compositional Analysis') return 'compositional';
      if (at === 'Ultimate Analysis') return 'ultimate';
      if (at === 'XRD Crystallinity') return 'xrd';
      if (at === 'ICP Elemental Analysis') return 'icp';
      if (at === 'XRF Elemental Analysis') return 'xrf';
      if (at === 'Pretreatment & Hydrolysis') return 'pretreatment';
      if (at === 'Fermentation (Bioconversion)') return 'fermentation';
      if (at === 'Gasification') return 'gasification';
      return normalizeDomainKey(at);
    }

    function seededRandom(seed) {
      const x = Math.sin(seed) * 10000;
      return x - Math.floor(x);
    }

    function computeFermHours(param, strain, exp) {
      if (!param || param === '(metadata only)') return null;
      if (param.endsWith('t0')) return 0;
      if (strain && strain.includes('Saccharomyces')) return 48;
      const numMatch = (exp || '').match(/(\\d+)/);
      const expNum = numMatch ? parseInt(numMatch[1], 10) : 25;
      const durations = [72, 84, 96, 112];
      return durations[expNum % durations.length];
    }

    // Hydrate dictionary-compressed dataset into row objects with deterministic jitter & sample lineage dates/GEOID
    const ALL_ROWS = RAW_DATA.rows.map((arr, idx) => {
      const u1 = Math.max(1e-6, seededRandom(idx * 17 + 3));
      const u2 = seededRandom(idx * 31 + 7);
      const jitter = Math.max(-2.2, Math.min(2.2, Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)));

      const obj = { record_id: arr[0] };
      RAW_DATA.str_cols.forEach((col, cIdx) => {
        obj[col] = RAW_DATA.dicts[col][arr[cIdx + 1]];
      });
      obj.replicate = arr[RAW_DATA.str_cols.length + 1];
      obj.value = arr[RAW_DATA.str_cols.length + 2];
      obj.exp_date_raw = arr.length > RAW_DATA.str_cols.length + 3 ? String(arr[RAW_DATA.str_cols.length + 3] || '').trim().slice(0, 10) : '';
      obj.exp_date = formatShortDate(obj.exp_date_raw);
      obj.domain = mapAnalysisTypeToDomain(obj.analysis_type);
      if ((obj.domain === 'icp' || obj.domain === 'xrf') && obj.parameter && obj.parameter !== '(metadata only)') {
        obj.parameter = formatElementSymbol(obj.parameter);
      }

      const portalCompliant = (
        obj.qc_status === 'pass' &&
        !EXCLUDED_RESOURCES_SET.has((obj.resource_name || '').toLowerCase()) &&
        !EXCLUDED_PROVIDERS_SET.has((obj.provider || '').toLowerCase())
      );
      obj.portal_compliant = portalCompliant;
      obj.data_status = portalCompliant ? 'Portal Compliant' : 'Raw';
      obj.prepared_sample_name = obj.prepared_sample;
      obj.provider_code = obj.provider;
      obj.pretreatment_method = obj.pt_method;
      obj.analysis_param = obj.parameter;
      obj.qc_pass = obj.qc_status;

      const psMeta = PREP_SAMPLES_BY_NAME[obj.prepared_sample] || {};
      if (!obj.field_sample || obj.field_sample === 'Unassigned') {
        obj.field_sample = psMeta.field_sample_name || psMeta.field_sample || 'Unassigned';
      }
      obj.field_sample_name = obj.field_sample;
      obj.experiment_name = obj.experiment;
      const fsMeta = FIELD_SAMPLES_BY_NAME[obj.field_sample] || {};
      obj.collected_at = fsMeta.collected_at || '';
      obj.collected_date = formatShortDate(fsMeta.collected_at);
      obj.geoid = fsMeta.geoid || 'Unassigned';
      obj.county_name = COUNTY_LOOKUP[obj.geoid] || (obj.geoid !== 'Unassigned' ? `GEOID ${obj.geoid}` : 'Unrecorded');
      obj.prep_date_raw = psMeta.prep_date || obj.exp_date_raw || '';
      obj.prep_date = formatShortDate(obj.prep_date_raw);
      obj.collection_cohort = formatDateCohort(fsMeta.collected_at);
      obj.prep_cohort = formatDateCohort(obj.prep_date_raw);

      obj.jitter = jitter;
      obj.time_h = obj.domain === 'fermentation'
        ? computeFermHours(obj.parameter, obj.strain, obj.experiment)
        : (obj.domain === 'gasification' && obj.parameter === 'time' && obj.value !== null ? +(obj.value / 60).toFixed(2) : null);
      return obj;
    });

    const SERIES_PALETTE = ['#00B5E2', '#f59e0b', '#10b981', '#ec4899', '#8b5cf6', '#3b82f6'];
    const SERIES_SHAPES = ['circle', 'square', 'diamond', 'triangle', 'circle', 'square'];
    const METHOD_COLORS = {
      cho10pc: '#00B5E2',
      h2o140c: '#f59e0b',
      butknt140c: '#10b981',
      none20c: '#ec4899'
    };

    // Canonical carbon-flow parameter ordering for Fermentation (matches fermentation_distribution.html)
    const FERM_CARBON_FLOW_ORDER = [
      'sugar_cons',
      'sugart0',
      'gluconct0',
      'xylconct0',
      'sugarteof',
      'gluconcteof',
      'xylconcteof',
      'od600teof',
      'rel_growth',
      '3hptiter',
      '3hpyield',
      '3hpyield_pct',
      'etohtiter',
      'etohyield',
      'etohyield_pct'
    ];
    const FERM_PARAM_LABELS = {
      '3hpyield': '3hpyield_pct',
      'etohyield': 'etohyield_pct'
    };

    function getCanonicalUnit(param, rawUnit, domainId) {
      const u = String(rawUnit || '').trim();
      if (u && u !== '—' && u !== 'N/A' && u !== 'none' && u !== 'null') {
        if (u.toLowerCase() === 'pc') return '%';
        return u;
      }
      if (param === '(metadata only)') return '';
      if (domainId === 'proximate') return '%';
      if (domainId === 'compositional') return '% dw';
      if (domainId === 'ultimate') return '%';
      if (domainId === 'calorimetry') return 'MJ/kg';
      if (domainId === 'xrd') return '%';
      if (domainId === 'icp' || domainId === 'xrf') return 'ppm';
      if (domainId === 'pretreatment') {
        if (param === 'glucose_yld') return '% of glucan';
        if (param === 'xylose_yld') return '% of xylan';
        return '%';
      }
      if (domainId === 'fermentation') {
        if (param && (param.includes('yield') || param === 'sugar_cons' || param === 'rel_growth')) return '%';
        if (param === 'od600teof') return 'OD600';
        return 'g/L';
      }
      if (domainId === 'gasification') {
        if (param === 'ufl' || param === 'lfl') return '%';
        if (param === 'temp') return '°C';
        if (param === 'time') return 's';
        return 'ppm';
      }
      return '';
    }

    // Build canonical parameter -> unit map across domains from ALL_ROWS + domain fallbacks
    const PARAM_UNIT_MAP = {};
    ALL_ROWS.forEach(r => {
      r.canonical_unit = getCanonicalUnit(r.parameter, r.unit, r.domain);
      if (!r.unit || r.unit === '—' || r.unit === 'N/A' || r.unit === 'pc') {
        r.unit = r.canonical_unit;
      }
      const key = `${r.domain}::${r.parameter}`;
      if (!PARAM_UNIT_MAP[key] && r.canonical_unit) {
        PARAM_UNIT_MAP[key] = r.canonical_unit;
      }
    });

    function getParamUnit(param, domainId) {
      if (!param || param === '(metadata only)') return '';
      const key = `${domainId}::${param}`;
      return PARAM_UNIT_MAP[key] || getCanonicalUnit(param, '', domainId);
    }

    function formatParamName(param, domainId) {
      if (!param) return '';
      if (param === '(metadata only)') return 'calorimetry_run (HHV pending ETL)';
      if (domainId === 'icp' || domainId === 'xrf') return formatElementSymbol(param);
      if (domainId === 'fermentation' && FERM_PARAM_LABELS[param]) return FERM_PARAM_LABELS[param];
      return String(param);
    }

    function formatParamWithUnit(param, domainId) {
      const base = formatParamName(param, domainId);
      if (!param || param === '(metadata only)') return base;
      const u = getParamUnit(param, domainId);
      return u ? `${base} (${u})` : base;
    }

    function matchesStatusFilter(r, status) {
      if (!status || status === 'ALL') return true;
      if (status === 'Portal Compliant') return r.data_status === 'Portal Compliant';
      if (status === 'Raw') return r.data_status === 'Raw';
      if (status === 'qc_pass' || status === 'pass') return r.qc_status === 'pass';
      if (status === 'qc_fail' || status === 'fail') return r.qc_status === 'fail';
      if (status === 'qc_provisional' || status === 'provisional') return r.qc_status !== 'pass' && r.qc_status !== 'fail';
      return true;
    }

    function normalizeExplorerDateRange(fromDt, toDt) {
      let f = String(fromDt || '').trim().slice(0, 10);
      let t = String(toDt || '').trim().slice(0, 10);
      let swapped = false;
      if (f && t && f > t) {
        const tmp = f;
        f = t;
        t = tmp;
        swapped = true;
      }
      return { from: f, to: t, swapped };
    }

    function recordMatchesDateFilter(r, dtType, fromDt, toDt) {
      const norm = normalizeExplorerDateRange(fromDt, toDt);
      if (!norm.from && !norm.to) return true;
      const checkDate = dStr => {
        const d = String(dStr || '').trim().slice(0, 10);
        if (!d || d === 'Undated' || d === 'Unrecorded') return false;
        if (norm.from && d < norm.from) return false;
        if (norm.to && d > norm.to) return false;
        return true;
      };
      const colDt = r.collected_date && r.collected_date !== 'Undated' ? r.collected_date : (r.collected_at ? String(r.collected_at).slice(0, 10) : '');
      const prepDt = r.prep_date && r.prep_date !== 'Undated' ? r.prep_date : (r.prep_date_raw ? String(r.prep_date_raw).slice(0, 10) : '');
      const expDt = r.exp_date && r.exp_date !== 'Undated' ? r.exp_date : (r.exp_date_raw ? String(r.exp_date_raw).slice(0, 10) : '');
      if (dtType === 'collected') return checkDate(colDt);
      if (dtType === 'run') return checkDate(prepDt) || checkDate(expDt);
      return checkDate(colDt) || checkDate(prepDt) || checkDate(expDt);
    }

    function updateDateFilterUiBadge() {
      const fdEl = document.getElementById('filter-from-date');
      const tdEl = document.getElementById('filter-to-date');
      const clrBtn = document.getElementById('filter-date-clear');
      const badgeEl = document.getElementById('date-filter-active-badge');
      const fdVal = fdEl ? fdEl.value : '';
      const tdVal = tdEl ? tdEl.value : '';
      const norm = normalizeExplorerDateRange(fdVal, tdVal);
      const active = !!(norm.from || norm.to);
      if (clrBtn) clrBtn.classList.toggle('hidden', !active);
      if (badgeEl) {
        if (!active) {
          badgeEl.classList.add('hidden');
          badgeEl.textContent = '';
        } else {
          badgeEl.classList.remove('hidden');
          const rangeTxt = `${norm.from || '…'} → ${norm.to || '…'}`;
          badgeEl.textContent = norm.swapped ? `${rangeTxt} (auto-ordered)` : rangeTxt;
        }
      }
    }

    function onFromDateFocus(el) {
      if (el && !el.value) {
        el.value = '2024-01-01';
        onDateFilterChange();
      }
    }

    function onDateFilterChange() {
      updateDateFilterUiBadge();
      onResourceOrDomainChange(false);
    }

    function clearDateFilter() {
      const fdEl = document.getElementById('filter-from-date');
      const tdEl = document.getElementById('filter-to-date');
      if (fdEl) fdEl.value = '';
      if (tdEl) tdEl.value = '';
      updateDateFilterUiBadge();
      onResourceOrDomainChange(false);
    }

    let urlParams = new URLSearchParams(window.location.search);
    const rawDomainParam = urlParams.get('type') || urlParams.get('domain') || urlParams.get('tab') || 'proximate';
    let currentDomain = normalizeDomainKey(rawDomainParam);
    if (!DOMAINS.some(d => d.id === currentDomain)) currentDomain = 'proximate';

    let currentTab = urlParams.get('view') === 'strip' ? 'strip' : 'scatter';
    let explorerFlagType = urlParams.get('flag') || 'all';
    let explorerSearchQuery = urlParams.get('q') || '';
    let explorerBlindMode = false;
    let scaleMode = 'log';
    let fermXMode = 'param';
    let xLayoutMode = 'auto'; // 'auto', 'resources', 'by_field_sample', 'by_experiment', 'dates', 'params'
    let yRangeMode = 'auto';  // 'auto' (fit actual parameter values), 'full' (0-100%)
    let repPlotMode = 'individual'; // 'individual' or 'mean_sd'
    let checklistDrawerOpen = true;
    let filteredRows = [];
    let renderedPoints = [];
    let pinnedRecord = null;
    let pinnedGroupRows = [];
    let pinnedGroupStats = null;
    let auditPopoverScope = 'group';
    let exportRows = [];
    let activeSeriesMap = {};
    let activeCompareDimension = 'method';
    const state = { zoomBounds: null };
    window.state = state;
    const brush = { active: false, startX: 0, startY: 0, curX: 0, curY: 0, suppressNextClick: false };
    let lastPlotTransform = null;

    function renderPlot() {
      renderCurrentView();
    }

    function resetCanvasZoom() {
      state.zoomBounds = null;
      const btn = document.getElementById('btn-reset-zoom');
      if (btn) btn.style.display = 'none';
      const brushEl = document.getElementById('canvas-zoom-brush');
      if (brushEl) brushEl.style.display = 'none';
      renderPlot();
    }

    function onExplorerFlagTypeChange(val) {
      explorerFlagType = val || 'all';
      applyFilters({ push: false });
    }

    function onExplorerSearchChange(val) {
      explorerSearchQuery = String(val || '');
      applyFilters({ push: false });
    }

    function toggleExplorerBlindMode(checked) {
      explorerBlindMode = !!checked;
      document.body.classList.toggle('blind-mode', explorerBlindMode);
      const chk = document.getElementById('chk-explorer-blind-mode');
      if (chk && chk.checked !== explorerBlindMode) chk.checked = explorerBlindMode;
      renderStatScreeningDrawer();
      renderCurrentView();
    }

    function setRepPlotMode(mode) {
      repPlotMode = mode === 'mean_sd' ? 'mean_sd' : 'individual';
      const sel = document.getElementById('rep-mode-select');
      if (sel && sel.value !== repPlotMode) sel.value = repPlotMode;
      syncUrlAndNavLinks();
      renderCurrentView();
    }

    function getReplicateGroupKey(r) {
      if (!r) return '';
      return window.normalizeReplicateGroupKey(r, r.resource_name);
    }

    function buildReplicateGroupsMap(rows) {
      const map = {};
      (rows || []).forEach(r => {
        const k = getReplicateGroupKey(r);
        if (!map[k]) map[k] = [];
        map[k].push(r);
      });
      return map;
    }

    // Multi-Select Checklist State
    const selectedFilters = {
      resources: new Set(),
      samples: new Set(),
      params: new Set(),
      methods: new Set()
    };
    const checklistCatalog = {
      resources: { active: [], pending: [] },
      samples: [],
      params: [],
      methods: []
    };
    let openPopoverKey = null;
    let compareByMode = 'auto';
    let compareByManualOverride = false;

    // Compute resource observation counts
    const RESOURCE_COUNTS = {};
    ALL_ROWS.forEach(r => {
      if (r.resource_name && r.resource_name !== 'Unassigned') {
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
      (RAW_DATA.resources || []).forEach(r => {
        if (r && r.name) {
          const low = String(r.name).trim().toLowerCase();
          if (!knownByLower[low]) knownByLower[low] = String(r.name).trim();
        }
      });
      sliceResCandidates.forEach(sr => {
        const s = String(sr || '').trim();
        if (!s || s === 'Unassigned') return;
        const low = s.toLowerCase();
        const canon = knownByLower[low] || s;
        if (RESOURCE_COUNTS[canon] === undefined) RESOURCE_COUNTS[canon] = 0;
        knownByLower[low] = canon;
      });
    }
    const ACTIVE_RESOURCES = Object.keys(RESOURCE_COUNTS).sort((a, b) => RESOURCE_COUNTS[b] - RESOURCE_COUNTS[a]);
    const PENDING_RESOURCES = (RAW_DATA.resources || [])
      .map(r => r.name)
      .filter(name => RESOURCE_COUNTS[name] === undefined)
      .sort();

    // Case-insensitive lookup map for deep links (?resource=almond+hulls)
    const RESOURCE_CANONICAL_MAP = {};
    ACTIVE_RESOURCES.forEach(name => { RESOURCE_CANONICAL_MAP[name.toLowerCase()] = name; });
    PENDING_RESOURCES.forEach(name => { RESOURCE_CANONICAL_MAP[name.toLowerCase()] = name; });

    function toggleChecklistDrawer() {
      checklistDrawerOpen = !checklistDrawerOpen;
      const drawer = document.getElementById('inline-checklist-drawer');
      const btn = document.getElementById('btn-toggle-drawer');
      if (drawer) drawer.classList.toggle('hidden', !checklistDrawerOpen);
      if (btn) {
        btn.className = checklistDrawerOpen
          ? 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-[#00B5E2] bg-[#00B5E2]/15 text-[#00B5E2] font-semibold transition-colors'
          : 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] hover:border-[#00B5E2] font-medium transition-colors';
      }
    }

    function setXLayoutMode(mode) {
      xLayoutMode = mode;
      if (mode === 'dates') {
        const dtVal = (document.getElementById('filter-date-type') || {}).value || 'any';
        const targetComp = dtVal === 'run' ? 'prep_date' : 'collection_date';
        if (compareByMode !== 'collection_date' && compareByMode !== 'prep_date') {
          compareByMode = targetComp;
          compareByManualOverride = true;
          const sel = document.getElementById('compare-by-select');
          if (sel) sel.value = compareByMode;
        }
        updateXLayoutButtons();
        applyFilters();
        return;
      }
      if (mode === 'by_field_sample') {
        compareByMode = 'field_sample';
        compareByManualOverride = true;
        const sel = document.getElementById('compare-by-select');
        if (sel) sel.value = compareByMode;
        updateXLayoutButtons();
        applyFilters();
        return;
      }
      if (mode === 'by_experiment') {
        compareByMode = 'experiment';
        compareByManualOverride = true;
        const sel = document.getElementById('compare-by-select');
        if (sel) sel.value = compareByMode;
        updateXLayoutButtons();
        applyFilters();
        return;
      }
      updateXLayoutButtons();
      renderCurrentView();
    }

    function updateXLayoutButtons() {
      ['auto', 'resources', 'by_field_sample', 'by_experiment', 'dates', 'params'].forEach(m => {
        const btn = document.getElementById(`btn-xlayout-${m}`);
        if (!btn) return;
        if (xLayoutMode === m) {
          btn.className = 'px-1.5 py-0.5 rounded text-xs font-medium bg-[var(--primary)] text-[var(--primary-foreground)]';
        } else {
          btn.className = 'px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]';
        }
      });
    }

    function setYRangeMode(mode) {
      yRangeMode = mode;
      state.zoomBounds = null;
      updateYRangeButtons();
      renderCurrentView();
    }

    function resetYRange() {
      setYRangeMode('auto');
    }

    function updateYRangeButtons() {
      ['auto', 'full'].forEach(m => {
        const btn = document.getElementById(`btn-yrange-${m}`);
        if (!btn) return;
        if (yRangeMode === m) {
          btn.className = 'px-1.5 py-0.5 rounded text-xs font-medium bg-[var(--primary)] text-[var(--primary-foreground)]';
        } else {
          btn.className = 'px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]';
        }
      });
    }

    function getSeriesValue(r, domainId) {
      if (domainId === 'pretreatment' || domainId === 'fermentation') {
        return r.pt_method && r.pt_method !== 'N/A' ? r.pt_method : (r.strain !== 'N/A' ? r.strain : 'Standard');
      }
      return r.prep_method && r.prep_method !== 'N/A' ? r.prep_method : 'Standard';
    }

    function getEffectiveCompareDimension() {
      if (xLayoutMode === 'by_field_sample') return 'field_sample';
      if (xLayoutMode === 'by_experiment') return 'experiment';
      if (xLayoutMode === 'dates' && compareByMode !== 'collection_date' && compareByMode !== 'prep_date') {
        const dtVal = (document.getElementById('filter-date-type') || {}).value || 'any';
        return dtVal === 'run' ? 'prep_date' : 'collection_date';
      }
      if (compareByMode && compareByMode !== 'auto') return compareByMode;
      if (selectedFilters.resources.size !== 1) return 'resource';
      if (selectedFilters.samples.size > 1) return 'sample';
      return 'method';
    }

    function getComparisonGroupValue(r, domainId) {
      const dim = getEffectiveCompareDimension();
      if (dim === 'resource') return r.resource_name || 'Unassigned';
      if (dim === 'sample') return r.prepared_sample_name || 'Unassigned';
      if (dim === 'field_sample') return (r.field_sample_name && r.field_sample_name !== 'Unassigned') ? r.field_sample_name : (r.prepared_sample_name || 'Unassigned');
      if (dim === 'experiment') return (r.experiment && r.experiment !== 'N/A') ? r.experiment : 'Unassigned Exp';
      if (dim === 'collection_date') return r.collection_cohort || 'Unrecorded Date';
      if (dim === 'prep_date') return r.prep_cohort || 'Unrecorded Date';
      return getSeriesValue(r, domainId);
    }

    function autoUpdateCompareBy() {
      if (compareByManualOverride) return;
      if (selectedFilters.resources.size > 1) {
        compareByMode = 'resource';
      } else if (selectedFilters.samples.size > 1) {
        compareByMode = 'sample';
      } else if (selectedFilters.methods.size > 1) {
        compareByMode = 'method';
      } else {
        compareByMode = 'auto';
      }
      const sel = document.getElementById('compare-by-select');
      if (sel) sel.value = compareByMode;
    }

    function onCompareByManualChange(val) {
      compareByMode = val || 'auto';
      compareByManualOverride = (compareByMode !== 'auto');
      if (compareByMode === 'field_sample' && xLayoutMode === 'by_experiment') xLayoutMode = 'by_field_sample';
      if (compareByMode === 'experiment' && xLayoutMode === 'by_field_sample') xLayoutMode = 'by_experiment';
      updateXLayoutButtons();
      applyFilters();
    }

    function escapeHtmlAttr(str) {
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }

    function closeAllPopovers() {
      ['resources', 'samples', 'params', 'methods'].forEach(k => {
        const panel = document.getElementById(`panel-popover-${k}`);
        if (panel) panel.classList.add('hidden');
      });
      openPopoverKey = null;
    }

    document.addEventListener('click', evt => {
      if (!openPopoverKey) return;
      if (!evt || !evt.target || !evt.target.isConnected) return;
      if (evt.target.closest && evt.target.closest('[id^="popover-wrap-"]')) return;
      closeAllPopovers();
    });

    function togglePopover(key, evt) {
      if (evt) evt.stopPropagation();
      const panel = document.getElementById(`panel-popover-${key}`);
      if (!panel) return;
      const isOpening = panel.classList.contains('hidden');
      closeAllPopovers();
      if (isOpening) {
        panel.classList.remove('hidden');
        openPopoverKey = key;
        renderChecklistItems(key);
        const searchInput = document.getElementById(`search-popover-${key}`);
        if (searchInput) setTimeout(() => searchInput.focus(), 10);
      }
    }

    function updatePopoverButtonLabel(key) {
      const lblEl = document.getElementById(`label-popover-${key}`);
      const cntEl = document.getElementById(`count-popover-${key}`);
      const inlCntEl = document.getElementById(`inline-count-${key}`);
      const btnEl = document.getElementById(`btn-popover-${key}`);
      const inlMethodLbl = document.getElementById('inline-label-methods');

      const checkedSet = selectedFilters[key];
      const nChecked = checkedSet.size;
      if (cntEl) cntEl.textContent = `${nChecked} checked`;

      const domainObj = DOMAINS.find(d => d.id === currentDomain) || DOMAINS[0];
      const methodPrefix = domainObj.methodLabel.replace(':', '');
      if (key === 'methods' && inlMethodLbl) {
        inlMethodLbl.textContent = `4. ${methodPrefix}s / Strains`;
      }

      if (inlCntEl) {
        if (key === 'resources') {
          const domActiveCnt = checklistCatalog.resources.active.filter(x => x.domainCount > 0).length;
          inlCntEl.textContent = nChecked === 0 ? `All (${domActiveCnt} in tab)` : `${nChecked} checked`;
        } else {
          const total = (checklistCatalog[key] || []).length;
          inlCntEl.textContent = nChecked === 0 ? `All (${total})` : `${nChecked} checked`;
        }
      }

      if (!lblEl) return;

      if (btnEl) {
        if (nChecked > 0) {
          btnEl.className = 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-[#00B5E2] bg-[#00B5E2]/10 text-[var(--foreground)] font-semibold transition-colors';
        } else {
          btnEl.className = 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] hover:border-[#00B5E2] font-medium transition-colors';
        }
      }

      if (key === 'resources') {
        const domActiveCnt = checklistCatalog.resources.active.filter(x => x.domainCount > 0).length;
        if (nChecked === 0) {
          lblEl.textContent = `Resources: All (${domActiveCnt} in tab)`;
        } else if (nChecked === 1) {
          const single = Array.from(checkedSet)[0];
          const shortSingle = single.length > 20 ? single.slice(0, 18) + '…' : single;
          lblEl.textContent = `Resource: ${shortSingle}`;
        } else {
          lblEl.textContent = `Resources: ${nChecked} selected`;
        }
      } else if (key === 'samples') {
        const total = checklistCatalog.samples.length;
        if (nChecked === 0) {
          lblEl.textContent = `Samples: All (${total})`;
        } else if (nChecked === 1) {
          const single = Array.from(checkedSet)[0];
          const shortSingle = single.length > 18 ? single.slice(0, 16) + '…' : single;
          lblEl.textContent = `Sample: ${shortSingle}`;
        } else {
          lblEl.textContent = `Samples: ${nChecked} selected`;
        }
      } else if (key === 'params') {
        const total = checklistCatalog.params.length;
        if (nChecked === 0) {
          lblEl.textContent = `Params: All (${total})`;
        } else if (nChecked === 1) {
          const single = formatParamWithUnit(Array.from(checkedSet)[0], currentDomain);
          const shortSingle = single.length > 22 ? single.slice(0, 20) + '…' : single;
          lblEl.textContent = `Param: ${shortSingle}`;
        } else {
          lblEl.textContent = `Params: ${nChecked} selected`;
        }
      } else if (key === 'methods') {
        const total = checklistCatalog.methods.length;
        if (nChecked === 0) {
          lblEl.textContent = `${methodPrefix}: All (${total})`;
        } else if (nChecked === 1) {
          const single = Array.from(checkedSet)[0];
          const shortSingle = single.length > 18 ? single.slice(0, 16) + '…' : single;
          lblEl.textContent = `${methodPrefix}: ${shortSingle}`;
        } else {
          lblEl.textContent = `${methodPrefix}: ${nChecked} selected`;
        }
      }
    }

    function handleChecklistInput(el, evt) {
      if (evt) evt.stopPropagation();
      const key = el.getAttribute('data-key');
      const val = decodeURIComponent(el.getAttribute('data-val') || '');
      const listContainer = el.closest('[id^="list-popover-"], [id^="inline-list-"]');
      const sourceId = listContainer ? listContainer.id : null;
      toggleChecklistItem(key, val, el.checked, sourceId);
    }

    function handleRemoveChip(el, evt) {
      if (evt) evt.stopPropagation();
      const key = el.getAttribute('data-key');
      const val = decodeURIComponent(el.getAttribute('data-val') || '');
      removeFilterChip(key, val);
    }

    function applyResourcePreset(presetOrNames) {
      selectedFilters.resources.clear();
      let names = [];
      if (Array.isArray(presetOrNames)) {
        names = presetOrNames;
      } else if (typeof presetOrNames === 'string') {
        const p = presetOrNames.toLowerCase();
        names = ACTIVE_RESOURCES.filter(rn => {
          const low = String(rn || '').toLowerCase();
          if (p === 'hulls') return low.includes('hull') || low.includes('shell');
          if (p === 'straws') return low.includes('straw') || low.includes('stover') || low.includes('stalk');
          if (p === 'pomaces') return low.includes('pomace') || low.includes('marc') || low.includes('waste') || low.includes('cull');
          return false;
        });
      }
      (names || []).forEach(rawName => {
        const canonical = RESOURCE_CANONICAL_MAP[String(rawName).toLowerCase()] || rawName;
        if (RESOURCE_COUNTS[canonical] || RESOURCES_BY_NAME[canonical]) {
          selectedFilters.resources.add(canonical);
        }
      });
      compareByManualOverride = false;
      compareByMode = 'resource';
      const sel = document.getElementById('compare-by-select');
      if (sel) sel.value = 'resource';
      onResourceOrDomainChange(false);
    }

    function selectDomainTopResources(count = 4) {
      const domainResCounts = {};
      ALL_ROWS.forEach(r => {
        if (r.domain === currentDomain && r.resource_name && r.resource_name !== 'Unassigned') {
          domainResCounts[r.resource_name] = (domainResCounts[r.resource_name] || 0) + 1;
        }
      });
      const topNames = Object.entries(domainResCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, count)
        .map(e => e[0]);
      selectedFilters.resources.clear();
      topNames.forEach(n => selectedFilters.resources.add(n));
      compareByManualOverride = false;
      compareByMode = 'resource';
      const sel = document.getElementById('compare-by-select');
      if (sel) sel.value = 'resource';
      onResourceOrDomainChange(false);
    }

    function clearResourceFilterKeepDomain() {
      selectedFilters.resources.clear();
      selectedFilters.samples.clear();
      autoUpdateCompareBy();
      onResourceOrDomainChange(false);
    }

    function selectSingleParamPill(param, evt) {
      if (!param || param === 'ALL') {
        selectedFilters.params.clear();
      } else if (evt && (evt.metaKey || evt.ctrlKey || evt.shiftKey)) {
        if (selectedFilters.params.has(param)) {
          selectedFilters.params.delete(param);
        } else {
          selectedFilters.params.add(param);
        }
      } else {
        if (selectedFilters.params.size === 1 && selectedFilters.params.has(param)) {
          selectedFilters.params.clear();
        } else {
          selectedFilters.params.clear();
          selectedFilters.params.add(param);
        }
      }
      renderChecklistItems('params');
      applyFilters();
    }

    function buildChecklistHtmlForTarget(key, q) {
      const checkedSet = selectedFilters[key];
      if (key === 'resources') {
        const activeItems = checklistCatalog.resources.active.filter(item => !q || item.value.toLowerCase().includes(q));
        const pendingItems = checklistCatalog.resources.pending.filter(item => !q || item.value.toLowerCase().includes(q));
        const domainObj = DOMAINS.find(d => d.id === currentDomain) || DOMAINS[0];
        const inDomainItems = activeItems.filter(item => item.domainCount > 0);
        const otherActiveItems = activeItems.filter(item => item.domainCount === 0);

        let html = '';
        if (inDomainItems.length) {
          html += `<div class="text-[10px] font-mono uppercase tracking-wider text-[#00B5E2] px-1.5 py-0.5 font-semibold">With ${domainObj.label} Data (${inDomainItems.length})</div>`;
          html += inDomainItems.map(item => {
            const isChecked = checkedSet.has(item.value);
            const valEnc = encodeURIComponent(item.value);
            const valEsc = escapeHtmlAttr(item.value);
            const rawBadge = item.isRaw ? `<span class="px-1 py-0.2 rounded bg-amber-500/15 text-amber-600 dark:text-amber-300 text-[9px] font-mono">Raw</span>` : '';
            const rowHighlight = isChecked ? 'bg-[#00B5E2]/15 border border-[#00B5E2]/40' : 'hover:bg-[var(--secondary)]/50 border border-transparent';
            return `
              <label class="flex items-center justify-between gap-1.5 px-1.5 py-0.5 rounded ${rowHighlight} cursor-pointer text-xs">
                <span class="flex items-center gap-1.5 min-w-0">
                  <input type="checkbox" data-key="resources" data-val="${valEnc}" ${isChecked ? 'checked' : ''} onchange="handleChecklistInput(this, event)" class="rounded" />
                  <span class="truncate font-medium" title="${valEsc}">${item.value}</span>
                  ${rawBadge}
                </span>
                <span class="font-mono text-[10px] text-[#00B5E2] shrink-0">${item.domainCount}</span>
              </label>
            `;
          }).join('');
        }
        if (otherActiveItems.length) {
          html += `<div class="text-[10px] font-mono uppercase tracking-wider text-[var(--muted-foreground)] px-1.5 pt-1.5 pb-0.5 border-t border-[var(--border)] mt-1">Other Active Resources (0 in ${domainObj.label})</div>`;
          html += otherActiveItems.map(item => {
            const isChecked = checkedSet.has(item.value);
            const valEnc = encodeURIComponent(item.value);
            const valEsc = escapeHtmlAttr(item.value);
            const rowHighlight = isChecked ? 'bg-amber-500/15 border border-amber-500/40' : 'hover:bg-[var(--secondary)]/50 border border-transparent opacity-75';
            return `
              <label class="flex items-center justify-between gap-1.5 px-1.5 py-0.5 rounded ${rowHighlight} cursor-pointer text-xs">
                <span class="flex items-center gap-1.5 min-w-0">
                  <input type="checkbox" data-key="resources" data-val="${valEnc}" ${isChecked ? 'checked' : ''} onchange="handleChecklistInput(this, event)" class="rounded" />
                  <span class="truncate" title="${valEsc}">${item.value}</span>
                </span>
                <span class="font-mono text-[10px] text-[var(--muted-foreground)] shrink-0">0 / ${item.totalCount}</span>
              </label>
            `;
          }).join('');
        }
        if (pendingItems.length && q) {
          html += `<div class="text-[10px] font-mono uppercase tracking-wider text-[var(--muted-foreground)] px-1.5 pt-1.5 pb-0.5 border-t border-[var(--border)] mt-1">Catalog Pending (${pendingItems.length})</div>`;
          html += pendingItems.map(item => {
            const isChecked = checkedSet.has(item.value);
            const valEnc = encodeURIComponent(item.value);
            const valEsc = escapeHtmlAttr(item.value);
            return `
              <label class="flex items-center justify-between gap-1.5 px-1.5 py-0.5 rounded hover:bg-[var(--secondary)]/50 cursor-pointer text-xs opacity-65">
                <span class="flex items-center gap-1.5 min-w-0">
                  <input type="checkbox" data-key="resources" data-val="${valEnc}" ${isChecked ? 'checked' : ''} onchange="handleChecklistInput(this, event)" class="rounded" />
                  <span class="truncate" title="${valEsc}">${item.value}</span>
                </span>
                <span class="font-mono text-[10px] text-[var(--muted-foreground)] shrink-0">0 obs</span>
              </label>
            `;
          }).join('');
        }
        if (!inDomainItems.length && !otherActiveItems.length && (!pendingItems.length || !q)) {
          html = `<div class="py-3 text-center text-[var(--muted-foreground)] text-xs">No matching resources</div>`;
        }
        return html;
      }

      const items = (checklistCatalog[key] || []).filter(item => {
        if (!q) return true;
        return item.value.toLowerCase().includes(q) || (item.display && item.display.toLowerCase().includes(q));
      });
      if (!items.length) {
        return `<div class="py-3 text-center text-[var(--muted-foreground)] text-xs">No matching items in current slice</div>`;
      }
      return items.map(item => {
        const isChecked = checkedSet.has(item.value);
        const valEnc = encodeURIComponent(item.value);
        const dispEsc = escapeHtmlAttr(item.display || item.value);
        const rowHighlight = isChecked ? 'bg-[#00B5E2]/15 border border-[#00B5E2]/40' : 'hover:bg-[var(--secondary)]/50 border border-transparent';
        return `
          <label class="flex items-center justify-between gap-1.5 px-1.5 py-0.5 rounded ${rowHighlight} cursor-pointer text-xs">
            <span class="flex items-center gap-1.5 min-w-0">
              <input type="checkbox" data-key="${key}" data-val="${valEnc}" ${isChecked ? 'checked' : ''} onchange="handleChecklistInput(this, event)" class="rounded" />
              <span class="truncate font-medium" title="${dispEsc}">${item.display || item.value}</span>
            </span>
            <span class="font-mono text-[10px] text-[var(--muted-foreground)] shrink-0">(${item.count})</span>
          </label>
        `;
      }).join('');
    }

    function toggleInlineChecklistDrawer() {
      const drawer = document.getElementById('inline-checklist-drawer');
      const chev = document.getElementById('drawer-chevron');
      const btn = document.getElementById('btn-toggle-drawer');
      if (!drawer) return;
      const isHidden = drawer.classList.toggle('hidden');
      if (chev) chev.innerHTML = isHidden ? '&#9662;' : '&#9652;';
      if (btn) {
        btn.className = isHidden
          ? 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] hover:border-[#00B5E2] font-medium transition-colors'
          : 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-[#00B5E2] bg-[#00B5E2]/15 text-[#00B5E2] font-semibold transition-colors';
      }
    }

    function syncChecklistSearch(key, val) {
      const popSearch = document.getElementById(`search-popover-${key}`);
      const inlSearch = document.getElementById(`inline-search-${key}`);
      if (popSearch && popSearch.value !== val) popSearch.value = val;
      if (inlSearch && inlSearch.value !== val) inlSearch.value = val;
      renderChecklistItems(key);
    }

    function selectTopDomainResources(count = 4) {
      selectDomainTopResources(count);
    }

    function renderChecklistItems(key, skipTargets = []) {
      if (!Array.isArray(skipTargets)) skipTargets = [];
      const targets = [
        { listId: `list-popover-${key}`, searchId: `search-popover-${key}` },
        { listId: `inline-list-${key}`, searchId: `inline-search-${key}` }
      ];
      targets.forEach(t => {
        const listEl = document.getElementById(t.listId);
        if (!listEl) return;
        if (skipTargets.includes(t.listId)) {
          // Update checkbox states & highlight classes in-place without replacing innerHTML
          const checkedSet = selectedFilters[key];
          listEl.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            const v = decodeURIComponent(cb.getAttribute('data-val') || '');
            const isC = checkedSet.has(v);
            cb.checked = isC;
            const lbl = cb.closest('label');
            if (lbl) {
              lbl.classList.toggle('bg-[#00B5E2]/15', isC);
              lbl.classList.toggle('border-[#00B5E2]/40', isC);
            }
          });
          return;
        }
        const searchEl = document.getElementById(t.searchId);
        const prevScroll = listEl.scrollTop;
        const q = (searchEl ? searchEl.value : '').trim().toLowerCase();
        listEl.innerHTML = buildChecklistHtmlForTarget(key, q);
        listEl.scrollTop = prevScroll;
      });
      updatePopoverButtonLabel(key);
    }

    function toggleChecklistItem(key, val, checked, sourceListId = null) {
      if (checked) {
        selectedFilters[key].add(val);
      } else {
        selectedFilters[key].delete(val);
      }
      autoUpdateCompareBy();
      if (key === 'resources') {
        onResourceOrDomainChange(false, { push: true });
      } else {
        renderChecklistItems(key, sourceListId ? [sourceListId] : []);
        applyFilters();
      }
    }

    function checklistAction(key, action) {
      const popSearch = document.getElementById(`search-popover-${key}`);
      const inlSearch = document.getElementById(`inline-search-${key}`);
      const q = ((popSearch && popSearch.value) || (inlSearch && inlSearch.value) || '').trim().toLowerCase();
      const set = selectedFilters[key];

      if (action === 'clear') {
        set.clear();
      } else if (key === 'resources') {
        const visibleActive = checklistCatalog.resources.active
          .filter(item => (!q || item.value.toLowerCase().includes(q)) && (action === 'domain' ? item.domainCount > 0 : (item.domainCount > 0 || action === 'all')))
          .map(item => item.value);
        if (action === 'all' || action === 'domain') {
          if (action === 'domain') set.clear();
          visibleActive.forEach(v => set.add(v));
        } else if (action === 'invert') {
          visibleActive.forEach(v => {
            if (set.has(v)) set.delete(v);
            else set.add(v);
          });
        }
      } else {
        const visible = (checklistCatalog[key] || [])
          .filter(item => !q || item.value.toLowerCase().includes(q) || (item.display && item.display.toLowerCase().includes(q)))
          .map(item => item.value);
        if (action === 'all') {
          visible.forEach(v => set.add(v));
        } else if (action === 'invert') {
          visible.forEach(v => {
            if (set.has(v)) set.delete(v);
            else set.add(v);
          });
        }
      }

      autoUpdateCompareBy();
      if (key === 'resources') {
        onResourceOrDomainChange(false, { push: true });
      } else {
        renderChecklistItems(key);
        applyFilters();
      }
    }

    function removeFilterChip(key, val) {
      selectedFilters[key].delete(val);
      autoUpdateCompareBy();
      if (key === 'resources') {
        onResourceOrDomainChange(false, { push: true });
      } else {
        renderChecklistItems(key);
        applyFilters();
      }
    }

    function renderActiveChipsBar() {
      const bar = document.getElementById('active-chips-bar');
      if (!bar) return;
      const chips = [];
      const domainObj = DOMAINS.find(d => d.id === currentDomain) || DOMAINS[0];
      const methodPrefix = domainObj.methodLabel.replace(':', '');

      selectedFilters.resources.forEach(v => {
        chips.push({ key: 'resources', val: v, label: `Resource: ${v}`, colorCls: 'border-[#00B5E2]/50 bg-[#00B5E2]/10 text-[var(--foreground)]' });
      });
      selectedFilters.samples.forEach(v => {
        chips.push({ key: 'samples', val: v, label: `Sample: ${v}`, colorCls: 'border-amber-500/50 bg-amber-500/10 text-[var(--foreground)]' });
      });
      selectedFilters.params.forEach(v => {
        const disp = formatParamWithUnit(v, currentDomain);
        chips.push({ key: 'params', val: v, label: `Param: ${disp}`, colorCls: 'border-emerald-500/50 bg-emerald-500/10 text-[var(--foreground)]' });
      });
      selectedFilters.methods.forEach(v => {
        chips.push({ key: 'methods', val: v, label: `${methodPrefix}: ${v}`, colorCls: 'border-purple-500/50 bg-purple-500/10 text-[var(--foreground)]' });
      });

      if (!chips.length) {
        bar.classList.add('hidden');
        bar.innerHTML = '';
        return;
      }

      bar.classList.remove('hidden');
      bar.innerHTML = `
        <span class="text-[11px] font-semibold text-[var(--muted-foreground)] mr-1">Active Checklist Filters (${chips.length}):</span>
        ${chips.map(c => {
          const valEnc = encodeURIComponent(c.val);
          return `
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border ${c.colorCls} text-[11px] font-medium">
              <span>${c.label}</span>
              <button type="button" data-key="${c.key}" data-val="${valEnc}" onclick="handleRemoveChip(this, event)" class="ml-0.5 hover:text-rose-500 font-bold leading-none" title="Remove filter">&times;</button>
            </span>
          `;
        }).join('')}
        <button type="button" onclick="resetFilters()" class="ml-auto px-2 py-0.5 rounded text-[11px] font-semibold text-rose-500 hover:underline">
          Clear All
        </button>
      `;
    }

    function syncUrlAndNavLinks(opts = { push: false }) {
      const firstRes = selectedFilters.resources.size > 0 ? Array.from(selectedFilters.resources)[0] : null;
      const link1 = document.getElementById('suite-link-1');
      const link2 = document.getElementById('suite-link-2');
      const link3 = document.getElementById('suite-link-3');
      if (RAW_DATA.collaborator_slice_mode) {
        const sp = RAW_DATA.slice_pages || ['char', 'explorer'];
        if (link1) {
          link1.classList.toggle('hidden', !sp.includes('char') && !sp.includes('analysis'));
          link1.href = '#';
          link1.onclick = e => { e.preventDefault(); if (window.switchCollaboratorSlicePage) window.switchCollaboratorSlicePage('char'); };
        }
        if (link2) {
          link2.classList.toggle('hidden', !sp.includes('qc'));
          link2.href = '#';
          link2.onclick = e => { e.preventDefault(); if (window.switchCollaboratorSlicePage) window.switchCollaboratorSlicePage('qc'); };
        }
        if (link3) {
          link3.classList.toggle('hidden', !sp.includes('explorer'));
          link3.href = '#';
          link3.onclick = e => { e.preventDefault(); if (window.switchCollaboratorSlicePage) window.switchCollaboratorSlicePage('explorer'); };
        }
      } else {
        if (link1) {
          link1.href = firstRes
            ? `resource_analysis_dashboard.html?resource=${encodeURIComponent(firstRes)}`
            : 'resource_analysis_dashboard.html';
        }
        if (link2) {
          const domQ = currentDomain ? `domain=${encodeURIComponent(currentDomain)}` : '';
          link2.href = firstRes
            ? `resource_qc_outlier_dashboard.html?resource=${encodeURIComponent(firstRes)}${domQ ? `&${domQ}` : ''}`
            : (domQ ? `resource_qc_outlier_dashboard.html?${domQ}` : 'resource_qc_outlier_dashboard.html');
        }
      }

      try {
        const params = new URLSearchParams();
        if (currentDomain && currentDomain !== 'proximate') params.set('type', currentDomain);
        if (currentTab && currentTab !== 'scatter') params.set('view', currentTab);
        if (selectedFilters.resources.size === 1) {
          params.set('resource', Array.from(selectedFilters.resources)[0]);
        } else if (selectedFilters.resources.size > 1) {
          params.set('resources', Array.from(selectedFilters.resources).join(','));
        }
        if (selectedFilters.samples.size > 0) params.set('samples', Array.from(selectedFilters.samples).join(','));
        if (selectedFilters.params.size > 0) params.set('params', Array.from(selectedFilters.params).join(','));
        if (selectedFilters.methods.size > 0) params.set('methods', Array.from(selectedFilters.methods).join(','));
        if (compareByMode && compareByMode !== 'auto') params.set('compare', compareByMode);
        if (xLayoutMode && xLayoutMode !== 'auto') params.set('x_layout', xLayoutMode);
        if (yRangeMode && yRangeMode !== 'auto') params.set('y_range', yRangeMode);
        if (repPlotMode && repPlotMode !== 'individual') params.set('rep_mode', repPlotMode);
        if (explorerFlagType && explorerFlagType !== 'all') params.set('flag', explorerFlagType);
        if (explorerSearchQuery && explorerSearchQuery.trim()) params.set('q', explorerSearchQuery.trim());
        const statusVal = document.getElementById('filter-status').value;
        if (statusVal && statusVal !== 'qc_pass') params.set('status', statusVal);
        const dtVal = (document.getElementById('filter-date-type') || {}).value || 'any';
        const fdVal = (document.getElementById('filter-from-date') || {}).value || '';
        const tdVal = (document.getElementById('filter-to-date') || {}).value || '';
        if (dtVal && dtVal !== 'any') params.set('date_type', dtVal);
        if (fdVal) params.set('from_date', fdVal);
        if (tdVal) params.set('to_date', tdVal);
        const qs = params.toString();
        const newUrl = window.location.pathname + (qs ? `?${qs}` : '');
        const stateSnapshot = {
          type: currentDomain,
          view: currentTab,
          resources: Array.from(selectedFilters.resources),
          flag: explorerFlagType,
          q: explorerSearchQuery,
          status: statusVal
        };
        if (opts && opts.push) {
          window.history.pushState(stateSnapshot, '', newUrl);
        } else {
          window.history.replaceState(stateSnapshot, '', newUrl);
        }
      } catch (e) {
        // Ignore history errors in sandboxed/file:// environments
      }
    }

    function initFromUrlParams() {
      const sf = RAW_DATA.slice_filters || {};
      const resParam = urlParams.get('resources') || urlParams.get('resource') || (Array.isArray(RAW_DATA.slice_resources) && RAW_DATA.slice_resources.length ? RAW_DATA.slice_resources.join(',') : '');
      if (resParam && resParam !== 'ALL') {
        resParam.split(',').map(s => s.trim()).filter(Boolean).forEach(rawName => {
          const canonical = RESOURCE_CANONICAL_MAP[rawName.toLowerCase()] || rawName;
          if (RESOURCE_COUNTS[canonical] !== undefined || RESOURCES_BY_NAME[canonical]) {
            selectedFilters.resources.add(canonical);
          }
        });
      }
      const samParam = urlParams.get('samples') || urlParams.get('sample') || (Array.isArray(sf.prepared_samples) && sf.prepared_samples.length ? sf.prepared_samples.join(',') : '');
      if (samParam && samParam !== 'ALL') {
        samParam.split(',').map(s => s.trim()).filter(Boolean).forEach(s => selectedFilters.samples.add(s));
      }
      const pParam = urlParams.get('params') || urlParams.get('param') || urlParams.get('parameter') || (Array.isArray(sf.parameters) && sf.parameters.length ? sf.parameters.join(',') : '');
      if (pParam && pParam !== 'ALL') {
        pParam.split(',').map(s => s.trim()).filter(Boolean).forEach(p => {
          const norm = (currentDomain === 'icp' || currentDomain === 'xrf') ? formatElementSymbol(p) : p;
          selectedFilters.params.add(norm);
        });
      }
      window.__HIGHLIGHT_RK__ = String(urlParams.get('highlight_rk') || '').trim().toLowerCase();
      const mParam = urlParams.get('methods') || urlParams.get('method') || (Array.isArray(sf.methods) && sf.methods.length ? sf.methods.join(',') : '');
      if (mParam && mParam !== 'ALL') {
        mParam.split(',').map(s => s.trim()).filter(Boolean).forEach(m => selectedFilters.methods.add(m));
      }
      const dtInit = urlParams.get('date_type') || sf.date_type || 'any';
      const fdInit = urlParams.get('from_date') || sf.from_date || '';
      const tdInit = urlParams.get('to_date') || sf.to_date || '';
      const dtEl = document.getElementById('filter-date-type');
      const fdEl = document.getElementById('filter-from-date');
      const tdEl = document.getElementById('filter-to-date');
      if (dtEl && ['any', 'collected', 'run'].includes(dtInit)) dtEl.value = dtInit;
      if (fdEl) fdEl.value = fdInit || '';
      if (tdEl) tdEl.value = tdInit || '';
      updateDateFilterUiBadge();

      const compParam = urlParams.get('compare');
      if (compParam && ['auto', 'resource', 'sample', 'field_sample', 'experiment', 'method', 'collection_date', 'prep_date'].includes(compParam)) {
        compareByMode = compParam;
        compareByManualOverride = (compParam !== 'auto');
        const sel = document.getElementById('compare-by-select');
        if (sel) sel.value = compareByMode;
      } else {
        autoUpdateCompareBy();
      }

      const xlParam = urlParams.get('x_layout');
      if (xlParam && ['auto', 'resources', 'by_field_sample', 'by_experiment', 'dates', 'params'].includes(xlParam)) {
        xLayoutMode = xlParam;
        if (xlParam === 'by_field_sample') {
          compareByMode = 'field_sample';
          compareByManualOverride = true;
          const sel = document.getElementById('compare-by-select');
          if (sel) sel.value = compareByMode;
        } else if (xlParam === 'by_experiment') {
          compareByMode = 'experiment';
          compareByManualOverride = true;
          const sel = document.getElementById('compare-by-select');
          if (sel) sel.value = compareByMode;
        }
        updateXLayoutButtons();
      }

      const yrParam = urlParams.get('y_range');
      if (yrParam && ['auto', 'full'].includes(yrParam)) {
        yRangeMode = yrParam;
        updateYRangeButtons();
      }

      const scParam = urlParams.get('scale');
      if (scParam && ['linear', 'log'].includes(scParam)) {
        scaleMode = scParam;
        updateScaleButtons();
      }

      const rmParam = urlParams.get('rep_mode');
      if (rmParam && ['individual', 'mean_sd'].includes(rmParam)) {
        repPlotMode = rmParam;
        const rmSel = document.getElementById('rep-mode-select');
        if (rmSel) rmSel.value = repPlotMode;
      }

      const flagParam = urlParams.get('flag');
      if (flagParam && ['all', 'active', 'dixon', 'rsd', 'sd3', 'identical'].includes(flagParam)) {
        explorerFlagType = flagParam;
      } else {
        explorerFlagType = 'all';
      }
      const fltFlagEl = document.getElementById('flt-explorer-flag-type');
      if (fltFlagEl) fltFlagEl.value = explorerFlagType;

      explorerSearchQuery = urlParams.get('q') || '';
      const searchEl = document.getElementById('filter-search');
      if (searchEl) searchEl.value = explorerSearchQuery;

      const viewParam = urlParams.get('view');
      currentTab = viewParam === 'strip' ? 'strip' : 'scatter';
      ['scatter', 'strip'].forEach(t => {
        const btn = document.getElementById(`tab-${t}`);
        if (!btn) return;
        btn.className = t === currentTab
          ? 'text-xs px-2.5 py-1 rounded-md font-medium bg-[var(--primary)] text-[var(--primary-foreground)] transition-colors'
          : 'text-xs px-2.5 py-1 rounded-md font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors';
      });

      const initialStatus = urlParams.get('status') || urlParams.get('qc');
      const statusSel = document.getElementById('filter-status');
      if (initialStatus && statusSel) {
        const sLower = initialStatus.trim().toLowerCase();
        if (sLower === 'all') statusSel.value = 'ALL';
        else if (sLower === 'pass' || sLower === 'qc_pass') statusSel.value = 'qc_pass';
        else if (sLower === 'fail' || sLower === 'qc_fail') statusSel.value = 'qc_fail';
        else if (sLower === 'provisional' || sLower === 'qc_provisional') statusSel.value = 'qc_provisional';
        else if (sLower === 'portal' || sLower === 'portal compliant') statusSel.value = 'Portal Compliant';
        else if (sLower === 'raw') statusSel.value = 'Raw';
      } else if (statusSel) {
        statusSel.value = 'qc_pass';
      }
    }

    function stepResource(delta) {
      const domainActiveList = checklistCatalog.resources.active
        .filter(item => item.domainCount > 0)
        .map(item => item.value);
      const list = ['ALL', ...(domainActiveList.length ? domainActiveList : ACTIVE_RESOURCES)];
      let currentVal = 'ALL';
      if (selectedFilters.resources.size === 1) {
        currentVal = Array.from(selectedFilters.resources)[0];
      }
      const idx = Math.max(0, list.indexOf(currentVal));
      const nextIdx = (idx + delta + list.length) % list.length;
      selectedFilters.resources.clear();
      if (list[nextIdx] !== 'ALL') {
        selectedFilters.resources.add(list[nextIdx]);
      }
      autoUpdateCompareBy();
      onResourceOrDomainChange(false, { push: true });
    }

    function setDomain(domainId) {
      currentDomain = domainId;
      state.zoomBounds = null;
      selectedFilters.params.clear();
      selectedFilters.methods.clear();
      if (domainId === 'icp' || domainId === 'xrf') {
        scaleMode = 'log';
      } else if (domainId === 'gasification') {
        scaleMode = 'linear';
      }
      updateScaleButtons();
      autoUpdateCompareBy();
      onResourceOrDomainChange(false, { push: true });
    }

    function setScaleMode(mode) {
      scaleMode = mode;
      updateScaleButtons();
      renderCurrentView();
    }

    function updateScaleButtons() {
      const btnLin = document.getElementById('btn-scale-linear');
      const btnLog = document.getElementById('btn-scale-log');
      if (scaleMode === 'linear') {
        btnLin.className = 'px-1.5 py-0.5 rounded text-xs font-medium bg-[var(--primary)] text-[var(--primary-foreground)]';
        btnLog.className = 'px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]';
      } else {
        btnLog.className = 'px-1.5 py-0.5 rounded text-xs font-medium bg-[var(--primary)] text-[var(--primary-foreground)]';
        btnLin.className = 'px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]';
      }
    }

    function setFermXMode(mode) {
      fermXMode = mode;
      const btnParam = document.getElementById('btn-ferm-param');
      const btnTime = document.getElementById('btn-ferm-time');
      if (mode === 'param') {
        btnParam.className = 'px-1.5 py-0.5 rounded text-xs font-medium bg-[var(--primary)] text-[var(--primary-foreground)]';
        btnTime.className = 'px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]';
      } else {
        btnTime.className = 'px-1.5 py-0.5 rounded text-xs font-medium bg-[var(--primary)] text-[var(--primary-foreground)]';
        btnParam.className = 'px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]';
      }
      renderCurrentView();
    }

    function renderDomainPills() {
      const status = document.getElementById('filter-status').value;
      const dateTypeVal = (document.getElementById('filter-date-type') || {}).value || 'any';
      const fromDateVal = (document.getElementById('filter-from-date') || {}).value || '';
      const toDateVal = (document.getElementById('filter-to-date') || {}).value || '';
      const hasDateFilter = !!(fromDateVal || toDateVal);
      const hasResFilter = selectedFilters.resources.size > 0;

      const selectedCounts = {};
      const totalDomainCounts = {};
      DOMAINS.forEach(d => {
        selectedCounts[d.id] = 0;
        totalDomainCounts[d.id] = 0;
      });
      ALL_ROWS.forEach(r => {
        if (!matchesStatusFilter(r, status)) return;
        if (hasDateFilter && !recordMatchesDateFilter(r, dateTypeVal, fromDateVal, toDateVal)) return;
        totalDomainCounts[r.domain] = (totalDomainCounts[r.domain] || 0) + 1;
        if (!hasResFilter || selectedFilters.resources.has(r.resource_name)) {
          selectedCounts[r.domain] = (selectedCounts[r.domain] || 0) + 1;
        }
      });

      const bar = document.getElementById('domain-pill-bar');
      bar.innerHTML = DOMAINS.map(d => {
        const active = d.id === currentDomain;
        const selCnt = selectedCounts[d.id] || 0;
        const totCnt = totalDomainCounts[d.id] || 0;
        const countBadge = hasResFilter && selCnt !== totCnt
          ? `${selCnt} / ${totCnt}`
          : `${selCnt}`;
        const cls = active
          ? 'px-2.5 py-1 rounded-md font-semibold bg-[#00B5E2] text-slate-950 transition-colors'
          : 'px-2 py-1 rounded-md font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] bg-[var(--background)] border border-[var(--border)] transition-colors';
        return `<button type="button" onclick="setDomain('${d.id}')" class="${cls}">${d.label} <span class="opacity-80 font-mono">(${countBadge})</span></button>`;
      }).join('');
    }

    function renderEmptySliceBanner() {
      const bannerEl = document.getElementById('empty-slice-banner');
      if (!bannerEl) return;
      const domainObj = DOMAINS.find(d => d.id === currentDomain) || DOMAINS[0];
      const totalInDomain = ALL_ROWS.filter(r => r.domain === currentDomain).length;

      if (filteredRows.length === 0 && selectedFilters.resources.size > 0 && totalInDomain > 0) {
        const checkedNames = Array.from(selectedFilters.resources).join(', ');
        bannerEl.classList.remove('hidden');
        bannerEl.innerHTML = `
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div>
              <span class="font-semibold">No ${domainObj.label} records found for selected resource(s):</span>
              <span class="font-mono ml-1">${escapeHtmlAttr(checkedNames)}</span>
              <span class="opacity-85 ml-1">(${totalInDomain} total ${domainObj.label} observations exist across other feedstock resources in this tab).</span>
            </div>
            <div class="flex flex-wrap items-center gap-1.5">
              <button type="button" onclick="clearResourceFilterKeepDomain()" class="px-2.5 py-1 rounded bg-[#00B5E2] text-slate-950 font-semibold hover:opacity-90">
                Show All Resources in ${domainObj.label}
              </button>
              <button type="button" onclick="selectDomainTopResources(4)" class="px-2.5 py-1 rounded border border-[#00B5E2] bg-[#00B5E2]/15 text-[#00B5E2] font-semibold hover:bg-[#00B5E2]/25">
                Compare Top 4 ${domainObj.label} Resources Side-by-Side
              </button>
            </div>
          </div>
        `;
      } else {
        bannerEl.classList.add('hidden');
        bannerEl.innerHTML = '';
      }
    }

    function renderParamPillBar() {
      const bar = document.getElementById('param-pill-bar');
      if (!bar) return;
      const items = checklistCatalog.params || [];
      if (!items.length) {
        bar.innerHTML = `<span class="text-[11px] text-[var(--muted-foreground)]">No parameters in current slice — use the buttons above or check resources with data in this analysis type.</span>`;
        return;
      }
      const allActive = selectedFilters.params.size === 0;
      const allCls = allActive
        ? 'px-2 py-0.5 rounded bg-[#00B5E2] text-slate-950 font-semibold text-[11px] transition-colors'
        : 'px-2 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] text-[11px] transition-colors';

      const pillsHtml = items.map(item => {
        const isSel = selectedFilters.params.has(item.value);
        const cls = isSel
          ? 'px-2 py-0.5 rounded bg-emerald-500 text-slate-950 font-semibold text-[11px] font-mono transition-colors'
          : 'px-2 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] hover:border-[#00B5E2] text-[11px] font-mono transition-colors';
        const pEsc = escapeHtmlAttr(item.value).replace(/'/g, "\\'");
        return `<button type="button" onclick="selectSingleParamPill('${pEsc}', event)" class="${cls}" title="Click to compare resources on ${escapeHtmlAttr(item.display)} (Shift/Cmd+Click to multi-select)">${item.display} <span class="opacity-75">(${item.count})</span></button>`;
      }).join('');

      bar.innerHTML = `
        <span class="text-[11px] font-semibold text-[var(--muted-foreground)] mr-0.5">Compare Parameter (Y-Axis Value &amp; Unit):</span>
        <button type="button" onclick="selectSingleParamPill('ALL', event)" class="${allCls}">All Parameters (${items.length})</button>
        ${pillsHtml}
      `;
    }

    function onResourceOrDomainChange(allowDomainFallback = false, opts = { push: false }) {
      const hasResFilter = selectedFilters.resources.size > 0;
      const dateTypeVal = (document.getElementById('filter-date-type') || {}).value || 'any';
      const fromDateVal = (document.getElementById('filter-from-date') || {}).value || '';
      const toDateVal = (document.getElementById('filter-to-date') || {}).value || '';
      const hasDateFilter = !!(fromDateVal || toDateVal);

      // Only auto-switch analysis domain on initial page load if requested via allowDomainFallback
      if (allowDomainFallback && hasResFilter) {
        const curHasRows = ALL_ROWS.some(r => r.domain === currentDomain && selectedFilters.resources.has(r.resource_name) && (!hasDateFilter || recordMatchesDateFilter(r, dateTypeVal, fromDateVal, toDateVal)));
        if (!curHasRows) {
          const fallbackDom = DOMAINS.find(d => ALL_ROWS.some(r => r.domain === d.id && selectedFilters.resources.has(r.resource_name) && (!hasDateFilter || recordMatchesDateFilter(r, dateTypeVal, fromDateVal, toDateVal))));
          if (fallbackDom) {
            currentDomain = fallbackDom.id;
            selectedFilters.params.clear();
            selectedFilters.methods.clear();
            if (currentDomain === 'icp' || currentDomain === 'xrf') scaleMode = 'log';
            else if (currentDomain === 'gasification') scaleMode = 'linear';
            updateScaleButtons();
          }
        }
      }

      // Update Resource checklist catalog with domain-specific and total counts, sorted so resources with data in currentDomain appear first
      const domainResCounts = {};
      ALL_ROWS.forEach(r => {
        if (hasDateFilter && !recordMatchesDateFilter(r, dateTypeVal, fromDateVal, toDateVal)) return;
        if (r.domain === currentDomain && r.resource_name && r.resource_name !== 'Unassigned') {
          domainResCounts[r.resource_name] = (domainResCounts[r.resource_name] || 0) + 1;
        }
      });
      checklistCatalog.resources.active = ACTIVE_RESOURCES.map(name => ({
        value: name,
        domainCount: domainResCounts[name] || 0,
        totalCount: RESOURCE_COUNTS[name] || 0,
        isRaw: EXCLUDED_RESOURCES_SET.has(name.toLowerCase())
      })).sort((a, b) => (b.domainCount - a.domainCount) || (b.totalCount - a.totalCount));

      checklistCatalog.resources.pending = PENDING_RESOURCES.map(name => ({
        value: name,
        domainCount: 0,
        totalCount: 0,
        isRaw: EXCLUDED_RESOURCES_SET.has(name.toLowerCase())
      }));

      // If selected resources have 0 rows in currentDomain, still populate parameter & method catalogs from currentDomain so user can inspect available parameters
      const matchingDomainRows = ALL_ROWS.filter(r => {
        if (r.domain !== currentDomain) return false;
        if (hasResFilter && !selectedFilters.resources.has(r.resource_name)) return false;
        if (hasDateFilter && !recordMatchesDateFilter(r, dateTypeVal, fromDateVal, toDateVal)) return false;
        return true;
      });
      const catalogSourceRows = matchingDomainRows.length > 0
        ? matchingDomainRows
        : ALL_ROWS.filter(r => r.domain === currentDomain && (!hasDateFilter || recordMatchesDateFilter(r, dateTypeVal, fromDateVal, toDateVal)));

      // Populate cascading Sample checklist catalog
      const samCounts = {};
      matchingDomainRows.forEach(r => {
        samCounts[r.prepared_sample_name] = (samCounts[r.prepared_sample_name] || 0) + 1;
      });
      checklistCatalog.samples = Object.entries(samCounts)
        .sort((a, b) => b[1] - a[1])
        .map(([s, c]) => ({ value: s, display: s, count: c }));
      Array.from(selectedFilters.samples).forEach(s => {
        if (!samCounts[s]) selectedFilters.samples.delete(s);
      });

      // Populate cascading Parameter checklist catalog (with units!)
      const paramCounts = {};
      catalogSourceRows.forEach(r => {
        if (r.parameter && (r.parameter !== '(metadata only)' || currentDomain === 'calorimetry' || currentDomain === 'xrd')) {
          paramCounts[r.parameter] = (paramCounts[r.parameter] || 0) + 1;
        }
      });
      checklistCatalog.params = Object.entries(paramCounts)
        .sort((a, b) => {
          if (currentDomain === 'fermentation') {
            const ia = FERM_CARBON_FLOW_ORDER.indexOf(a[0]);
            const ib = FERM_CARBON_FLOW_ORDER.indexOf(b[0]);
            return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
          }
          return b[1] - a[1];
        })
        .map(([p, c]) => ({
          value: p,
          display: formatParamWithUnit(p, currentDomain),
          count: c
        }));
      Array.from(selectedFilters.params).forEach(p => {
        if (!paramCounts[p]) selectedFilters.params.delete(p);
      });

      // Populate cascading Method / Prep / Strain checklist catalog
      const methodCounts = {};
      catalogSourceRows.forEach(r => {
        const m = getSeriesValue(r, currentDomain);
        methodCounts[m] = (methodCounts[m] || 0) + 1;
      });
      checklistCatalog.methods = Object.entries(methodCounts)
        .sort((a, b) => b[1] - a[1])
        .map(([m, c]) => ({ value: m, display: m, count: c }));
      Array.from(selectedFilters.methods).forEach(m => {
        if (!methodCounts[m]) selectedFilters.methods.delete(m);
      });

      ['resources', 'samples', 'params', 'methods'].forEach(k => renderChecklistItems(k));
      autoUpdateCompareBy();
      applyFilters(opts);
    }

    function setTab(tab, opts = { push: true }) {
      currentTab = tab === 'export' ? 'scatter' : tab;
      state.zoomBounds = null;
      ['scatter', 'strip'].forEach(t => {
        const btn = document.getElementById(`tab-${t}`);
        if (!btn) return;
        if (t === currentTab) {
          btn.className = 'text-xs px-2.5 py-1 rounded-md font-medium bg-[var(--primary)] text-[var(--primary-foreground)] transition-colors';
        } else {
          btn.className = 'text-xs px-2.5 py-1 rounded-md font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors';
        }
      });

      const viewCharts = document.getElementById('view-charts');
      if (viewCharts) viewCharts.classList.remove('hidden');
      syncUrlAndNavLinks(opts);
      updateChartHeaderControls();
      renderCurrentView();
    }

    function updateChartHeaderControls() {
      const domainObj = DOMAINS.find(d => d.id === currentDomain) || DOMAINS[0];
      const stripControls = document.getElementById('strip-controls');
      const scaleControls = document.getElementById('scale-controls');
      const fermControls = document.getElementById('ferm-controls');
      const xLayoutControls = document.getElementById('xaxis-layout-controls');
      const yRangeControls = document.getElementById('yrange-controls');
      const methodLegend = document.getElementById('method-legend');
      const chartTitle = document.getElementById('chart-title');

      const nRes = selectedFilters.resources.size;
      const resPrefix = nRes === 0
        ? ''
        : (nRes === 1 ? `[${Array.from(selectedFilters.resources)[0]}] ` : `[${nRes} Resources Side-by-Side] `);

      const singleParam = selectedFilters.params.size === 1 ? Array.from(selectedFilters.params)[0] : null;
      const paramSuffix = singleParam ? ` — ${formatParamWithUnit(singleParam, currentDomain)}` : '';

      if (currentTab === 'strip') {
        chartTitle.textContent = `${resPrefix}${domainObj.label}${paramSuffix} — Replicate Value Comparison (Top 14)`;
        stripControls.classList.remove('hidden');
        scaleControls.classList.add('hidden');
        fermControls.classList.add('hidden');
        if (xLayoutControls) xLayoutControls.classList.add('hidden');
        if (yRangeControls) yRangeControls.classList.add('hidden');
        methodLegend.classList.remove('hidden');
      } else {
        chartTitle.textContent = `${resPrefix}${domainObj.title}${paramSuffix}`;
        stripControls.classList.add('hidden');
        methodLegend.classList.remove('hidden');
        if (xLayoutControls) xLayoutControls.classList.remove('hidden');
        if (yRangeControls) yRangeControls.classList.remove('hidden');
        if (currentDomain === 'icp' || currentDomain === 'xrf' || currentDomain === 'gasification') {
          scaleControls.classList.remove('hidden');
        } else {
          scaleControls.classList.add('hidden');
        }
        if (currentDomain === 'fermentation') {
          fermControls.classList.remove('hidden');
        } else {
          fermControls.classList.add('hidden');
        }
      }
    }

    function applyFilters(opts = { push: false }) {
      const status = document.getElementById('filter-status').value;
      const dateTypeVal = (document.getElementById('filter-date-type') || {}).value || 'any';
      const fromDateVal = (document.getElementById('filter-from-date') || {}).value || '';
      const toDateVal = (document.getElementById('filter-to-date') || {}).value || '';
      const hasDateFilter = !!(fromDateVal || toDateVal);
      const hasRes = selectedFilters.resources.size > 0;
      const hasSam = selectedFilters.samples.size > 0;
      const hasParam = selectedFilters.params.size > 0;
      const hasMethod = selectedFilters.methods.size > 0;
      const qLower = (explorerSearchQuery || '').trim().toLowerCase();

      updateDateFilterUiBadge();
      ['resources', 'samples', 'params', 'methods'].forEach(k => updatePopoverButtonLabel(k));
      renderActiveChipsBar();
      syncUrlAndNavLinks(opts);

      // Update combined Status / QC dropdown counts for active domain + resource + date selection
      const baseDomainRows = ALL_ROWS.filter(r =>
        r.domain === currentDomain
        && (!hasRes || selectedFilters.resources.has(r.resource_name))
        && (!hasDateFilter || recordMatchesDateFilter(r, dateTypeVal, fromDateVal, toDateVal))
      );
      const compliantCnt = baseDomainRows.filter(r => r.data_status === 'Portal Compliant').length;
      const rawCnt = baseDomainRows.length - compliantCnt;
      const qcPassCnt = baseDomainRows.filter(r => r.qc_status === 'pass').length;
      const qcFailCnt = baseDomainRows.filter(r => r.qc_status === 'fail').length;
      const qcProvCnt = baseDomainRows.length - qcPassCnt - qcFailCnt;
      const statusSel = document.getElementById('filter-status');
      statusSel.options[0].textContent = `All Statuses & QC (${baseDomainRows.length})`;
      statusSel.options[1].textContent = `Portal Compliant (${compliantCnt})`;
      statusSel.options[2].textContent = `Raw / Portal Excluded (${rawCnt})`;
      statusSel.options[3].textContent = `qc_pass: pass (${qcPassCnt})`;
      statusSel.options[4].textContent = `qc_pass: fail (${qcFailCnt})`;
      statusSel.options[5].textContent = `qc_pass: provisional/unknown (${qcProvCnt})`;

      let candidateRows = ALL_ROWS.filter(r => {
        if (r.domain !== currentDomain) return false;
        if (!matchesStatusFilter(r, status)) return false;
        if (hasRes && !selectedFilters.resources.has(r.resource_name)) return false;
        if (hasSam && !selectedFilters.samples.has(r.prepared_sample_name)) return false;
        if (hasParam && !selectedFilters.params.has(r.parameter)) return false;
        if (hasMethod && !selectedFilters.methods.has(getSeriesValue(r, currentDomain))) return false;
        if (hasDateFilter && !recordMatchesDateFilter(r, dateTypeVal, fromDateVal, toDateVal)) return false;
        if (qLower) {
          const hay = `${r.record_id || ''} ${r.resource_name || ''} ${r.prepared_sample_name || ''} ${r.field_sample_name || ''} ${r.parameter || ''} ${r.experiment || ''} ${r.note || ''}`.toLowerCase();
          if (!hay.includes(qLower)) return false;
        }
        return true;
      });

      if (explorerFlagType && explorerFlagType !== 'all') {
        const preScreen = computeSliceStatScreening(candidateRows);
        const matchingIds = new Set();
        preScreen.groups.forEach(g => {
          if (isExplorerGroupMatchingFlagFilter(g, explorerFlagType)) {
            g.rows.forEach(row => matchingIds.add(`${row.record_id}::${row.parameter}`));
          }
        });
        candidateRows = candidateRows.filter(r => matchingIds.has(`${r.record_id}::${r.parameter}`));
      }

      filteredRows = candidateRows;

      const uniqueSamples = new Set(filteredRows.map(r => r.prepared_sample_name).filter(x => x !== 'Unassigned')).size;
      const domainTotal = ALL_ROWS.filter(r => r.domain === currentDomain).length;
      document.getElementById('badge-count').textContent = `${filteredRows.length} / ${domainTotal} obs · ${uniqueSamples} samples`;

      const resMetaBadge = document.getElementById('badge-resource-meta');
      if (selectedFilters.resources.size === 0) {
        const activeResInSlice = new Set(filteredRows.map(r => r.resource_name).filter(x => x !== 'Unassigned')).size;
        resMetaBadge.textContent = `${activeResInSlice} active resources · ${ALL_ROWS.length.toLocaleString()} total rows`;
      } else if (selectedFilters.resources.size === 1) {
        const singleRes = Array.from(selectedFilters.resources)[0];
        const meta = RESOURCES_BY_NAME[singleRes] || {};
        const exclTag = EXCLUDED_RESOURCES_SET.has(singleRes.toLowerCase()) ? ' · Raw Only (Excluded in MV)' : ' · Portal MV Enabled';
        resMetaBadge.textContent = `${meta.resource_class || 'Resource'} · ${meta.primary_ag_product || 'N/A'}${exclTag}`;
      } else {
        resMetaBadge.textContent = `Comparing ${selectedFilters.resources.size} checked resources side-by-side`;
      }

      renderDomainPills();
      renderEmptySliceBanner();
      renderParamPillBar();
      buildActiveSeriesLegend();
      updateChartHeaderControls();
      renderSideBySideComparisonCard();
      updateStats();
      renderStatScreeningDrawer();
      renderCurrentView();
    }

    function buildActiveSeriesLegend() {
      activeCompareDimension = getEffectiveCompareDimension();
      const seriesCounts = {};
      filteredRows.forEach(r => {
        const s = getComparisonGroupValue(r, currentDomain);
        seriesCounts[s] = (seriesCounts[s] || 0) + 1;
      });

      let topSeries = [];
      if (activeCompareDimension === 'resource' && selectedFilters.resources.size > 0) {
        topSeries = Array.from(selectedFilters.resources).slice(0, 8);
      } else if (activeCompareDimension === 'sample' && selectedFilters.samples.size > 0) {
        topSeries = Array.from(selectedFilters.samples).slice(0, 8);
      } else if (activeCompareDimension === 'method' && selectedFilters.methods.size > 0) {
        topSeries = Array.from(selectedFilters.methods).slice(0, 8);
      } else if (activeCompareDimension === 'method' && currentDomain === 'pretreatment') {
        topSeries = ['cho10pc', 'h2o140c', 'butknt140c', 'none20c'].filter(s => seriesCounts[s] > 0);
        if (!topSeries.length) topSeries = ['cho10pc', 'h2o140c', 'butknt140c', 'none20c'];
      } else if (activeCompareDimension === 'collection_date' || activeCompareDimension === 'prep_date') {
        topSeries = Object.keys(seriesCounts)
          .sort((a, b) => {
            if (a.includes('Unrecorded') || a.includes('Undated')) return 1;
            if (b.includes('Unrecorded') || b.includes('Undated')) return -1;
            return a.localeCompare(b);
          })
          .slice(0, 10);
      } else if (activeCompareDimension === 'field_sample' || activeCompareDimension === 'experiment') {
        topSeries = Object.entries(seriesCounts)
          .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
          .slice(0, 12)
          .map(e => e[0]);
      } else {
        topSeries = Object.entries(seriesCounts)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 8)
          .map(e => e[0]);
      }

      activeSeriesMap = {};
      topSeries.forEach((s, i) => {
        activeSeriesMap[s] = {
          color: METHOD_COLORS[s] || SERIES_PALETTE[i % SERIES_PALETTE.length],
          shape: s === 'cho10pc' ? 'circle' : (s === 'h2o140c' ? 'square' : (s === 'butknt140c' ? 'diamond' : (s === 'none20c' ? 'triangle' : SERIES_SHAPES[i % SERIES_SHAPES.length]))),
          offset: topSeries.length > 1 ? ((i / (topSeries.length - 1)) - 0.5) * 0.56 : 0
        };
      });

      const dimBadgeMap = {
        resource: 'By Resource',
        sample: 'By Prepared Sample',
        field_sample: 'By Field Sample',
        experiment: 'By Experiment ID',
        method: 'By Method/Prep',
        collection_date: 'By Collection Date Cohort',
        prep_date: 'By Prep/Run Date Cohort'
      };
      const legendEl = document.getElementById('method-legend');
      const dimBadge = `<span class="px-1.5 py-0.5 rounded bg-[#00B5E2]/15 text-[#00B5E2] font-mono text-[10px] font-semibold">${dimBadgeMap[activeCompareDimension] || 'Series'}</span>`;
      legendEl.innerHTML = dimBadge + topSeries.map(s => {
        const cfg = activeSeriesMap[s];
        const shortName = s.length > 22 ? s.slice(0, 20) + '…' : s;
        const badgeCls = cfg.shape === 'circle'
          ? 'rounded-full'
          : (cfg.shape === 'diamond' ? 'rotate-45' : 'rounded-sm');
        return `<span class="inline-flex items-center gap-1" title="${escapeHtmlAttr(s)}"><span class="w-2.5 h-2.5 inline-block ${badgeCls}" style="background:${cfg.color}"></span>${shortName}</span>`;
      }).join('');
    }

    function resetFilters() {
      document.getElementById('filter-status').value = 'qc_pass';
      state.zoomBounds = null;
      explorerFlagType = 'all';
      explorerSearchQuery = '';
      explorerBlindMode = false;
      suppressTraceFlags = true;
      document.body.classList.remove('blind-mode');
      const fltFlagEl = document.getElementById('flt-explorer-flag-type');
      if (fltFlagEl) fltFlagEl.value = 'all';
      const searchEl = document.getElementById('filter-search');
      if (searchEl) searchEl.value = '';
      const chkBlindEl = document.getElementById('chk-explorer-blind-mode');
      if (chkBlindEl) chkBlindEl.checked = false;
      const chkTraceEl = document.getElementById('chk-explorer-suppress-trace');
      if (chkTraceEl) chkTraceEl.checked = true;
      const dtEl = document.getElementById('filter-date-type');
      const fdEl = document.getElementById('filter-from-date');
      const tdEl = document.getElementById('filter-to-date');
      if (dtEl) dtEl.value = 'any';
      if (fdEl) fdEl.value = '';
      if (tdEl) tdEl.value = '';
      updateDateFilterUiBadge();
      selectedFilters.resources.clear();
      selectedFilters.samples.clear();
      selectedFilters.params.clear();
      selectedFilters.methods.clear();
      compareByManualOverride = false;
      compareByMode = 'auto';
      xLayoutMode = 'auto';
      updateXLayoutButtons();
      const compSel = document.getElementById('compare-by-select');
      if (compSel) compSel.value = 'auto';
      ['resources', 'samples', 'params', 'methods'].forEach(k => {
        const inp1 = document.getElementById(`search-popover-${k}`);
        if (inp1) inp1.value = '';
        const inp2 = document.getElementById(`inline-search-${k}`);
        if (inp2) inp2.value = '';
      });
      onResourceOrDomainChange(false);
    }

    function calcStats(vals) {
      const nums = vals.filter(v => typeof v === 'number' && !isNaN(v));
      if (!nums.length) return { mean: null, sd: null, min: null, max: null, n: 0 };
      const n = nums.length;
      const mean = nums.reduce((a, b) => a + b, 0) / n;
      const variance = nums.reduce((acc, v) => acc + (v - mean) ** 2, 0) / n;
      return {
        mean,
        sd: Math.sqrt(variance),
        min: Math.min(...nums),
        max: Math.max(...nums),
        n
      };
    }

    function renderSideBySideComparisonCard() {
      const cardEl = document.getElementById('side-by-side-comparison-card');
      if (!cardEl) return;

      const seriesKeys = Object.keys(activeSeriesMap);
      if (seriesKeys.length < 2) {
        cardEl.classList.add('hidden');
        cardEl.innerHTML = '';
        return;
      }

      const numericRows = filteredRows.filter(r => typeof r.value === 'number' && !isNaN(r.value));
      const topParams = getActiveParametersForScatter(numericRows).filter(p => p !== '(metadata only)').slice(0, 4);
      if (!topParams.length) {
        cardEl.classList.add('hidden');
        cardEl.innerHTML = '';
        return;
      }

      const dimTitleMap = {
        resource: 'Resource Side-by-Side Parameter Comparison',
        sample: 'Prepared Sample Side-by-Side Comparison',
        field_sample: 'Field Sample Side-by-Side Comparison',
        experiment: 'Experiment Side-by-Side Comparison',
        method: 'Method / Prep Side-by-Side Comparison',
        collection_date: 'Collection Date Cohort Comparison',
        prep_date: 'Prep / Run Date Cohort Comparison'
      };

      const rowsHtml = seriesKeys.map(sKey => {
        const cfg = activeSeriesMap[sKey];
        const groupRows = numericRows.filter(r => getComparisonGroupValue(r, currentDomain) === sKey);
        const cells = topParams.map(p => {
          const st = calcStats(groupRows.filter(r => r.parameter === p).map(r => r.value));
          const u = getParamUnit(p, currentDomain);
          const uShort = u.startsWith('%') ? '%' : (u ? ` ${u}` : '');
          if (st.mean === null) return `<td class="py-1 px-1.5 text-right font-mono text-[var(--muted-foreground)]">—</td>`;
          const dec = Math.abs(st.mean) < 10 && Math.abs(st.mean) > 0 ? 2 : 1;
          return `<td class="py-1 px-1.5 text-right font-mono"><span class="font-semibold text-[var(--foreground)]">${st.mean.toFixed(dec)}${uShort}</span> <span class="text-[10px] text-[var(--muted-foreground)]">±${st.sd.toFixed(dec)} (${st.n})</span></td>`;
        }).join('');
        const shortGroup = sKey.length > 18 ? sKey.slice(0, 17) + '…' : sKey;
        return `
          <tr class="border-b border-[var(--border)] last:border-b-0">
            <td class="py-1 px-1.5 font-medium truncate max-w-[125px]" title="${escapeHtmlAttr(sKey)}">
              <span class="inline-block w-2 h-2 rounded-full mr-1" style="background:${cfg.color}"></span>${shortGroup}
            </td>
            ${cells}
          </tr>
        `;
      }).join('');

      cardEl.classList.remove('hidden');
      cardEl.innerHTML = `
        <div class="flex items-center justify-between mb-1.5 pb-1 border-b border-[var(--border)]">
          <span class="font-semibold text-[var(--foreground)]">${dimTitleMap[activeCompareDimension] || 'Side-by-Side Parameter Comparison'}</span>
          <span class="text-[10px] font-mono text-[#00B5E2]">Mean ± SD (n)</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-[11px]">
            <thead>
              <tr class="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                <th class="py-1 px-1.5">Resource / Condition</th>
                ${topParams.map(p => `<th class="py-1 px-1.5 text-right font-mono">${formatParamWithUnit(p, currentDomain)}</th>`).join('')}
              </tr>
            </thead>
            <tbody>${rowsHtml}</tbody>
          </table>
        </div>
      `;
    }

    function formatStatCard(label, stats, unitSuffix = '%') {
      const meanStr = stats.mean !== null
        ? `${stats.mean.toFixed(1)}${unitSuffix} (n=${stats.n})`
        : '—';
      const sdStr = stats.mean !== null
        ? `±${stats.sd.toFixed(1)}${unitSuffix} · [${stats.min.toFixed(1)}–${stats.max.toFixed(1)}]`
        : 'No data in slice';
      return `
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2">
          <div class="text-xs text-[var(--muted-foreground)] truncate" title="${label}">${label}</div>
          <div class="text-sm font-semibold text-[var(--foreground)] font-mono">${meanStr}</div>
          <div class="text-xs text-[var(--muted-foreground)] font-mono truncate">${sdStr}</div>
        </div>
      `;
    }

    function updateStats() {
      const grid = document.getElementById('summary-kpi-grid');
      const closureBanner = document.getElementById('closure-banner');
      const closureLabel = document.getElementById('closure-label');
      const closureVal = document.getElementById('closure-value');
      const lineageCard = document.getElementById('lineage-date-geoid-card');

      // Populate Field Sample Collection Date, GEOID / County, and Sample Prep / Run Date KPI Summary Card
      if (lineageCard) {
        const colDates = Array.from(new Set(filteredRows.map(r => r.collected_date).filter(d => d && d !== 'Unrecorded' && d !== 'Undated'))).sort();
        const prepDates = Array.from(new Set(filteredRows.map(r => r.prep_date).filter(d => d && d !== 'Unrecorded' && d !== 'Undated'))).sort();
        const geoidPairs = Array.from(new Set(filteredRows.map(r => (r.geoid && r.geoid !== 'Unassigned') ? `${r.county_name} (${r.geoid})` : null).filter(Boolean)));
        const fSamCount = new Set(filteredRows.map(r => r.field_sample_name).filter(x => x && x !== 'Unassigned' && x !== '—')).size;
        const pSamCount = new Set(filteredRows.map(r => r.prepared_sample_name).filter(x => x && x !== 'Unassigned')).size;

        const colSpanStr = colDates.length === 0 ? 'Unrecorded' : (colDates.length === 1 ? colDates[0] : `${colDates[0]} → ${colDates[colDates.length - 1]}`);
        const prepSpanStr = prepDates.length === 0 ? 'Unrecorded' : (prepDates.length === 1 ? prepDates[0] : `${prepDates[0]} → ${prepDates[prepDates.length - 1]}`);
        const geoStr = geoidPairs.length === 0 ? 'Unrecorded' : (geoidPairs.length <= 2 ? geoidPairs.join(', ') : `${geoidPairs.slice(0, 2).join(', ')} +${geoidPairs.length - 2} more`);

        lineageCard.innerHTML = `
          <div class="flex items-center justify-between text-[11px] font-semibold text-[var(--foreground)] border-b border-[var(--border)] pb-1">
            <span>Sample Dates &amp; Geography (Active Slice)</span>
            <span class="font-mono text-[#00B5E2]">${fSamCount} Field · ${pSamCount} Prep</span>
          </div>
          <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">Collected Date:</span><span class="font-mono font-medium text-[var(--foreground)] truncate" title="${colDates.join(', ')}">${colSpanStr}</span></div>
          <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">Prep / Run Date:</span><span class="font-mono font-medium text-[var(--foreground)] truncate" title="${prepDates.join(', ')}">${prepSpanStr}</span></div>
          <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">GEOID / County:</span><span class="font-mono font-medium text-[#00B5E2] truncate" title="${geoidPairs.join(', ')}">${geoStr}</span></div>
        `;
      }

      const byParam = p => calcStats(filteredRows.filter(r => r.parameter === p).map(r => r.value));

      if (currentDomain === 'pretreatment') {
        closureBanner.classList.add('hidden');
        const gluc = byParam('glucose_yld');
        const xylo = byParam('xylose_yld');
        const cho = calcStats(filteredRows.filter(r => r.pt_method === 'cho10pc' && r.value !== null).map(r => r.value));
        const h2o = calcStats(filteredRows.filter(r => r.pt_method === 'h2o140c' && r.value !== null).map(r => r.value));
        grid.innerHTML = [
          formatStatCard('Glucose Yield', gluc, '%'),
          formatStatCard('Xylose Yield', xylo, '%'),
          formatStatCard('Cholinium (cho10pc)', cho, '%'),
          formatStatCard('Water 140°C (h2o140c)', h2o, '%')
        ].join('');
      } else if (currentDomain === 'proximate') {
        const byProxBucket = b => calcStats(filteredRows.filter(r => proximateComponentBucket(r.parameter) === b && r.value !== null && !isNaN(r.value)).map(r => r.value));
        const moist = byProxBucket('moisture');
        const vs = byProxBucket('vs');
        const fc = byProxBucket('fc');
        const ash = byProxBucket('ash');
        const ts = byParam('total solids');
        grid.innerHTML = [
          formatStatCard('Moisture', moist, '%'),
          formatStatCard('Volatile Solids', vs, '%'),
          formatStatCard('Ash', ash, '%'),
          formatStatCard('Total Solids', ts, '%')
        ].join('');
        closureBanner.classList.remove('hidden');
        closureLabel.textContent = 'Proximate Closure (Moisture + VS + Ash):';
        const hasProximateTerm = moist.mean !== null || ash.mean !== null || vs.mean !== null || fc.mean !== null;
        const vsOrOneMinusFc = vs.mean !== null ? vs.mean : (fc.mean !== null ? 100 - fc.mean : 0);
        const proximateSum = hasProximateTerm
          ? ((moist.mean || 0) + (ash.mean || 0) + vsOrOneMinusFc)
          : null;
        closureVal.textContent = proximateSum !== null
          ? `${proximateSum.toFixed(1)}% (${proximateSum >= 95 && proximateSum <= 105 ? 'Optimal 95–105%' : '⚑ Outside 95–105%'})`
          : '—';
      } else if (currentDomain === 'compositional') {
        const glucan = byParam('glucan');
        const xylan = byParam('xylan');
        const lignin = byParam('lignin');
        const arab = byParam('arabinan');
        grid.innerHTML = [
          formatStatCard('Glucan', glucan, '% dw'),
          formatStatCard('Xylan', xylan, '% dw'),
          formatStatCard('Lignin', lignin, '% dw'),
          formatStatCard('Arabinan', arab, '% dw')
        ].join('');
        closureBanner.classList.remove('hidden');
        closureLabel.textContent = 'Biopolymer Sum (Gluc+Xyl+Lig):';
        const sumBio = (glucan.mean || 0) + (xylan.mean || 0) + (lignin.mean || 0) + (arab.mean || 0);
        closureVal.textContent = sumBio > 0 ? `${sumBio.toFixed(1)}% dw structural` : '—';
      } else if (currentDomain === 'ultimate') {
        closureBanner.classList.add('hidden');
        grid.innerHTML = [
          formatStatCard('Nitrogen (N)', byParam('nitrogen'), '%'),
          formatStatCard('Crude Fiber (cf)', byParam('cf'), '%'),
          formatStatCard('ADF-Residue', byParam('adf-r'), '%'),
          formatStatCard('Dry Matter (dm)', byParam('dm'), '%')
        ].join('');
      } else if (currentDomain === 'calorimetry') {
        closureBanner.classList.add('hidden');
        const hhv = byParam('hhv');
        const lhv = byParam('lhv');
        const calCnt = filteredRows.filter(r => r.analysis_type === 'Calorimetry').length;
        const samCnt = new Set(filteredRows.map(r => r.prepared_sample_name)).size;
        grid.innerHTML = [
          formatStatCard('HHV (Higher Heating)', hhv, ' MJ/kg'),
          formatStatCard('LHV (Lower Heating)', lhv, ' MJ/kg'),
          `<div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2"><div class="text-xs text-[var(--muted-foreground)]">Calorimetry Runs</div><div class="text-sm font-semibold font-mono">${calCnt} runs</div><div class="text-xs text-[var(--muted-foreground)]">calorimetry_record</div></div>`,
          `<div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2"><div class="text-xs text-[var(--muted-foreground)]">Prepared Samples</div><div class="text-sm font-semibold font-mono">${samCnt} samples</div><div class="text-xs text-[var(--muted-foreground)]">Active slice</div></div>`
        ].join('');
      } else if (currentDomain === 'xrd') {
        closureBanner.classList.add('hidden');
        const cryst = byParam('crystallinity');
        const xrdCnt = filteredRows.filter(r => r.analysis_type === 'XRD Crystallinity').length;
        const samCnt = new Set(filteredRows.map(r => r.prepared_sample_name)).size;
        grid.innerHTML = [
          formatStatCard('XRD Crystallinity', cryst, '%'),
          `<div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2"><div class="text-xs text-[var(--muted-foreground)]">XRD Replicates</div><div class="text-sm font-semibold font-mono">${xrdCnt} obs</div><div class="text-xs text-[var(--muted-foreground)]">xrd_record table</div></div>`,
          `<div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2"><div class="text-xs text-[var(--muted-foreground)]">Prepared Samples</div><div class="text-sm font-semibold font-mono">${samCnt} samples</div><div class="text-xs text-[var(--muted-foreground)]">Active slice</div></div>`
        ].join('');
      } else if (currentDomain === 'icp' || currentDomain === 'xrf') {
        closureBanner.classList.add('hidden');
        const topEls = currentDomain === 'icp' ? ['Ca', 'K', 'Mg', 'S'] : ['K', 'Ca', 'Si', 'Fe'];
        grid.innerHTML = topEls.map(el => formatStatCard(`Element ${formatElementSymbol(el)}`, byParam(el), ' ppm')).join('');
      } else if (currentDomain === 'fermentation') {
        closureBanner.classList.add('hidden');
        grid.innerHTML = [
          formatStatCard('Sugar Consumed (sugar_cons)', byParam('sugar_cons'), '%'),
          formatStatCard('Initial Sugar (sugart0)', byParam('sugart0'), ' g/L'),
          formatStatCard('3-HP Titer (3hptiter)', byParam('3hptiter'), ' g/L'),
          formatStatCard('3-HP Yield (3hpyield_pct)', byParam('3hpyield'), '%')
        ].join('');
      } else {
        closureBanner.classList.add('hidden');
        grid.innerHTML = [
          formatStatCard('UFL (Flammability)', byParam('ufl'), '%'),
          formatStatCard('Syngas H₂', byParam('h2'), ' ppm'),
          formatStatCard('Syngas CO', byParam('co'), ' ppm'),
          formatStatCard('Syngas CH₄', byParam('ch4'), ' ppm')
        ].join('');
      }
    }

    let currentTheme = 'dark';

    function getThemeColors() {
      const isLight = currentTheme === 'light';
      return {
        canvasBg: isLight ? '#f8fafc' : '#0f172a',
        grid: isLight ? 'rgba(15, 23, 42, 0.12)' : 'rgba(248, 250, 252, 0.14)',
        axisText: isLight ? '#334155' : '#cbd5e1',
        titleText: isLight ? '#0f172a' : '#f8fafc',
        rangeBar: isLight ? 'rgba(15, 23, 42, 0.28)' : 'rgba(248, 250, 252, 0.32)'
      };
    }

    function drawShape(ctx, shape, x, y, r) {
      ctx.beginPath();
      if (shape === 'circle' || shape === 'cho10pc') {
        ctx.arc(x, y, r, 0, Math.PI * 2);
      } else if (shape === 'square' || shape === 'h2o140c') {
        ctx.rect(x - r, y - r, r * 2, r * 2);
      } else if (shape === 'diamond' || shape === 'butknt140c') {
        ctx.moveTo(x, y - r * 1.25);
        ctx.lineTo(x + r * 1.25, y);
        ctx.lineTo(x, y + r * 1.25);
        ctx.lineTo(x - r * 1.25, y);
        ctx.closePath();
      } else {
        ctx.moveTo(x, y - r * 1.2);
        ctx.lineTo(x + r * 1.2, y + r * 1.1);
        ctx.lineTo(x - r * 1.2, y + r * 1.1);
        ctx.closePath();
      }
      ctx.fill();
      ctx.stroke();
    }

    function renderCurrentView() {
      if (currentTab === 'scatter') {
        renderScatter();
      } else if (currentTab === 'strip') {
        renderStrip();
      }
    }

    function getActiveParametersForScatter(numericRows) {
      if (selectedFilters.params.size > 0) {
        const checkedList = Array.from(selectedFilters.params);
        if (currentDomain === 'fermentation') {
          checkedList.sort((a, b) => {
            const ia = FERM_CARBON_FLOW_ORDER.indexOf(a);
            const ib = FERM_CARBON_FLOW_ORDER.indexOf(b);
            return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
          });
        }
        return checkedList;
      }
      if (currentDomain === 'pretreatment') {
        return ['glucose_yld', 'xylose_yld'];
      }
      const counts = {};
      const sourceRows = (currentDomain === 'calorimetry' || currentDomain === 'xrd') ? filteredRows : numericRows;
      sourceRows.forEach(r => {
        counts[r.parameter] = (counts[r.parameter] || 0) + 1;
      });
      if (currentDomain === 'fermentation') {
        const list = Object.keys(counts).sort((a, b) => {
          const ia = FERM_CARBON_FLOW_ORDER.indexOf(a);
          const ib = FERM_CARBON_FLOW_ORDER.indexOf(b);
          return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
        });
        return list.length ? list : ['(metadata only)'];
      }
      const maxCats = (currentDomain === 'icp' || currentDomain === 'xrf' || currentDomain === 'gasification') ? 15 : 10;
      const list = Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, maxCats)
        .map(e => e[0]);
      return list.length ? list : ['(metadata only)'];
    }

    function computeNiceAxisMax(rawMax, yRangeModeVal, domainId) {
      if (yRangeModeVal === 'full') {
        return Math.max(100, Math.ceil((rawMax * 1.05) / 10) * 10);
      }
      if (!rawMax || rawMax <= 0) return 10;
      const padded = rawMax * 1.16;
      if (padded <= 1) return Math.ceil(padded * 20) / 20;
      if (padded <= 5) return Math.ceil(padded * 2) / 2;
      if (padded <= 15) return Math.ceil(padded);
      if (padded <= 50) return Math.ceil(padded / 5) * 5;
      if (padded <= 120) return Math.ceil(padded / 10) * 10;
      if (padded <= 500) return Math.ceil(padded / 25) * 25;
      if (padded <= 2000) return Math.ceil(padded / 100) * 100;
      return Math.ceil(padded / 500) * 500;
    }

    function formatTickValueWithUnit(val, unit, yMax) {
      const u = unit || '';
      const shortU = u.startsWith('%') ? '%' : (u ? ` ${u}` : '');
      let numStr;
      if (yMax <= 2) numStr = val.toFixed(2);
      else if (yMax <= 15) numStr = Number.isInteger(val) ? String(val) : val.toFixed(1);
      else if (val >= 10000) numStr = `${(val / 1000).toFixed(0)}k`;
      else numStr = String(Math.round(val));
      return `${numStr}${shortU}`;
    }

    function drawRotatedYAxisTitle(ctx, text, pad, plotH, theme) {
      ctx.save();
      ctx.fillStyle = theme.titleText;
      ctx.font = '600 11px system-ui, -apple-system, sans-serif';
      ctx.translate(15, pad.top + plotH / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText(text, 0, 0);
      ctx.restore();
    }

    function compactXAxisLabel(label) {
      if (!label) return '';
      return String(label)
        .replace(/\\(% total weight\\)/gi, '(% wt)')
        .replace(/\\(% dry weight\\)/gi, '(% dw)')
        .replace(/\\(% wet weight\\)/gi, '(% ww)');
    }

    function splitXAxisLabelTwoLines(label) {
      const s = compactXAxisLabel(label);
      const parenIdx = s.lastIndexOf(' (');
      if (parenIdx > 0 && s.endsWith(')')) {
        return [s.slice(0, parenIdx), s.slice(parenIdx + 1)];
      }
      return [s, ''];
    }

    function drawXAxisTickLabel(ctx, rawLabel, cx, yBase, rotateLabels, theme, colCount) {
      const label = compactXAxisLabel(rawLabel);
      ctx.font = colCount <= 5 ? '600 11.5px system-ui, -apple-system, sans-serif' : '600 10.5px system-ui, -apple-system, sans-serif';
      if (rotateLabels) {
        ctx.save();
        ctx.fillStyle = theme.titleText;
        ctx.translate(cx + 4, yBase + 7);
        ctx.rotate(-Math.PI / 5.2);
        ctx.textAlign = 'right';
        ctx.textBaseline = 'top';
        ctx.fillText(label, 0, 0);
        ctx.restore();
      } else {
        const [line1, line2] = splitXAxisLabelTwoLines(label);
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillStyle = theme.titleText;
        ctx.fillText(line1, cx, yBase + 7);
        if (line2) {
          ctx.font = '500 10px system-ui, -apple-system, sans-serif';
          ctx.fillStyle = theme.axisText;
          ctx.fillText(line2, cx, yBase + 22);
        }
      }
    }

    function renderScatter() {
      const canvas = document.getElementById('plot-canvas');
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      const width = rect.width || 640;

      const numericRows = filteredRows.filter(r => typeof r.value === 'number' && !isNaN(r.value));
      const params = getActiveParametersForScatter(numericRows);
      const isTimeMode = currentDomain === 'fermentation' && fermXMode === 'time';
      const seriesKeys = Object.keys(activeSeriesMap);

      // Build replicate group lookup across filtered rows for tooltip / click-audit scope
      const repGroupsMap = buildReplicateGroupsMap(filteredRows);

      // Determine whether X-axis columns should be Resources/Conditions Side-by-Side or Parameters
      const useResourceColumns = !isTimeMode
        && params[0] !== '(metadata only)'
        && seriesKeys.length >= 1
        && (xLayoutMode === 'resources' || xLayoutMode === 'dates' || xLayoutMode === 'by_field_sample' || xLayoutMode === 'by_experiment' || (xLayoutMode === 'auto' && params.length === 1 && seriesKeys.length >= 2));

      // Determine active unit(s) for Y-axis title and ticks
      const validParams = params.filter(p => p !== '(metadata only)');
      const uniqueUnits = Array.from(new Set(validParams.map(p => getParamUnit(p, currentDomain)).filter(Boolean)));
      const primaryUnit = validParams.length === 1
        ? getParamUnit(validParams[0], currentDomain)
        : (uniqueUnits.length === 1 ? uniqueUnits[0] : (uniqueUnits[0] || ''));

      // Update dynamic chart title with active parameter & unit context
      const domMeta = DOMAINS.find(d => d.id === currentDomain) || DOMAINS[0];
      const chartTitleEl = document.getElementById('chart-title');
      if (chartTitleEl && currentTab === 'scatter') {
        if (validParams.length === 1) {
          chartTitleEl.textContent = `${domMeta.label} — ${formatParamWithUnit(validParams[0], currentDomain)} (${seriesKeys.length} ${activeCompareDimension === 'resource' ? 'Resource' : 'Condition'}${seriesKeys.length === 1 ? '' : 's'} Side-by-Side)`;
        } else if (useResourceColumns) {
          chartTitleEl.textContent = `${domMeta.label} — Side-by-Side Resource Comparison (${validParams.slice(0, 4).map(p => formatParamName(p, currentDomain)).join(', ')})`;
        } else {
          chartTitleEl.textContent = domMeta.title;
        }
      }

      const xLabels = (useResourceColumns
        ? seriesKeys.map(sKey => sKey.length > 26 ? sKey.slice(0, 25) + '…' : sKey)
        : params.map(p => {
            if (p === '(metadata only)') return 'calorimetry_run (HHV pending ETL)';
            return compactXAxisLabel(formatParamWithUnit(p, currentDomain));
          }));

      const measureCtx = canvas.getContext('2d');
      measureCtx.font = xLabels.length <= 5 ? '600 11.5px system-ui, -apple-system, sans-serif' : '600 10.5px system-ui, -apple-system, sans-serif';
      const approxColW = (width - 88) / Math.max(1, xLabels.length);
      const canFitHorizontalTwoLine = !isTimeMode && xLabels.length <= 6 && xLabels.every(l => {
        const [line1, line2] = splitXAxisLabelTwoLines(l);
        return Math.max(measureCtx.measureText(line1).width, measureCtx.measureText(line2).width) <= (approxColW - 10);
      });
      const rotateLabels = !isTimeMode && !canFitHorizontalTwoLine && (xLabels.length > 4 || xLabels.some(l => measureCtx.measureText(l).width > approxColW - 8));

      const rotAngle = Math.PI / 5.2;
      const maxLabelPx = xLabels.length ? Math.max(...xLabels.map(l => measureCtx.measureText(l).width)) : 60;
      const firstLabelPx = xLabels.length ? measureCtx.measureText(xLabels[0]).width : 60;
      const dynamicBottom = isTimeMode
        ? 56
        : (rotateLabels
            ? Math.min(210, Math.max(108, Math.ceil(maxLabelPx * Math.sin(rotAngle)) + 42))
            : 66);
      const firstColOffset = xLabels.length === 2 ? (width - 88) * 0.27 : approxColW * 0.5;
      const dynamicLeft = rotateLabels
        ? Math.min(155, Math.max(68, Math.ceil(firstLabelPx * Math.cos(rotAngle) - firstColOffset + 18)))
        : 68;

      const height = rotateLabels ? Math.max(380, 285 + dynamicBottom) : 370;
      canvas.style.height = height + 'px';
      canvas.width = width * dpr;
      canvas.height = height * dpr;

      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);
      const theme = getThemeColors();
      ctx.fillStyle = theme.canvasBg;
      ctx.fillRect(0, 0, width, height);

      const pad = { top: 26, right: 20, bottom: dynamicBottom, left: dynamicLeft };
      const plotW = width - pad.left - pad.right;
      const plotH = height - pad.top - pad.bottom;

      const resetZoomBtn = document.getElementById('btn-reset-zoom');
      if (resetZoomBtn) resetZoomBtn.style.display = state.zoomBounds ? 'inline-flex' : 'none';

      renderedPoints = [];

      if (!filteredRows.length) {
        ctx.fillStyle = theme.axisText;
        ctx.font = '13px system-ui, -apple-system, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('No observations match the current filter selection. Use the banner above or select another analysis type/resource.', width / 2, height / 2);
        return;
      }

      // Special mode: Fermentation Time (Hours) continuous X-axis (0 - 115h) with multi-condition kinetic trajectories
      if (isTimeMode) {
        const timeRows = filteredRows.filter(r => r.time_h !== null && r.value !== null && (selectedFilters.params.size === 0 || selectedFilters.params.has(r.parameter)));
        const maxVal = timeRows.length ? Math.max(...timeRows.map(r => r.value)) : 20;
        let yMin = 0;
        let yMax = computeNiceAxisMax(maxVal, yRangeMode, currentDomain);
        let xMin = 0;
        let xMax = 115;
        if (state.zoomBounds) {
          if (Number.isFinite(state.zoomBounds.yMin) && Number.isFinite(state.zoomBounds.yMax) && state.zoomBounds.yMax > state.zoomBounds.yMin) {
            yMin = state.zoomBounds.yMin;
            yMax = state.zoomBounds.yMax;
          }
          if (Number.isFinite(state.zoomBounds.xMin) && Number.isFinite(state.zoomBounds.xMax) && state.zoomBounds.xMax > state.zoomBounds.xMin) {
            xMin = Math.max(0, state.zoomBounds.xMin);
            xMax = Math.min(115, state.zoomBounds.xMax);
          }
        }
        lastPlotTransform = {
          pad, plotW, plotH, xMin, xMax, yMin, yMax, useLog: false, mode: 'time',
          pxToDataX: px => xMin + ((px - pad.left) / Math.max(1, plotW)) * (xMax - xMin),
          pxToDataY: py => yMin + ((pad.top + plotH - py) / Math.max(1, plotH)) * (yMax - yMin)
        };

        ctx.font = '11px system-ui, -apple-system, sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        for (let i = 0; i <= 5; i++) {
          const val = yMin + ((yMax - yMin) / 5) * i;
          const y = pad.top + plotH - ((val - yMin) / Math.max(1e-9, yMax - yMin)) * plotH;
          ctx.strokeStyle = theme.grid;
          ctx.beginPath();
          ctx.moveTo(pad.left, y);
          ctx.lineTo(pad.left + plotW, y);
          ctx.stroke();
          ctx.fillStyle = theme.axisText;
          ctx.fillText(formatTickValueWithUnit(val, primaryUnit, yMax), pad.left - 7, y);
        }

        const timeYTitle = validParams.length === 1
          ? `${formatParamWithUnit(validParams[0], currentDomain)} — Measured Value`
          : `Measured Value (${uniqueUnits.join(' / ') || 'g/L · %'})`;
        drawRotatedYAxisTitle(ctx, timeYTitle, pad, plotH, theme);

        // X-axis baseline
        ctx.strokeStyle = theme.axisText;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pad.left, pad.top + plotH);
        ctx.lineTo(pad.left + plotW, pad.top + plotH);
        ctx.stroke();

        const xSpan = Math.max(1e-9, xMax - xMin);
        const ySpan = Math.max(1e-9, yMax - yMin);
        const timeToX = t => pad.left + ((t - xMin) / xSpan) * plotW;
        const timeValToY = v => pad.top + plotH - ((Math.max(yMin, Math.min(yMax, v)) - yMin) / ySpan) * plotH;

        const xTicks = state.zoomBounds ? [0, 0.25, 0.5, 0.75, 1.0].map(f => Math.round((xMin + f * xSpan) * 10) / 10) : [0, 24, 48, 72, 96, 115];
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.font = '600 11px system-ui, -apple-system, sans-serif';
        xTicks.forEach(t => {
          const x = timeToX(t);
          ctx.strokeStyle = theme.grid;
          ctx.beginPath();
          ctx.moveTo(x, pad.top);
          ctx.lineTo(x, pad.top + plotH);
          ctx.stroke();

          ctx.strokeStyle = theme.axisText;
          ctx.beginPath();
          ctx.moveTo(x, pad.top + plotH);
          ctx.lineTo(x, pad.top + plotH + 4);
          ctx.stroke();

          ctx.fillStyle = theme.titleText;
          ctx.fillText(`${t}h`, x, pad.top + plotH + 7);
        });

        ctx.fillStyle = theme.axisText;
        ctx.font = '600 11px system-ui, -apple-system, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        ctx.fillText('Fermentation Time (Hours) — Multi-Condition Kinetic Trajectories', pad.left + plotW / 2, height - 4);

        ctx.save();
        ctx.beginPath();
        ctx.rect(pad.left, pad.top, plotW, plotH);
        ctx.clip();

        Object.entries(activeSeriesMap).forEach(([sKey, cfg]) => {
          const sRows = timeRows.filter(r => getComparisonGroupValue(r, currentDomain) === sKey);
          const byHour = {};
          sRows.forEach(r => {
            if (!byHour[r.time_h]) byHour[r.time_h] = [];
            byHour[r.time_h].push(r.value);
          });
          const hours = Object.keys(byHour).map(Number).sort((a, b) => a - b);
          if (hours.length >= 2) {
            ctx.save();
            ctx.strokeStyle = cfg.color;
            ctx.lineWidth = 2;
            ctx.setLineDash([4, 3]);
            ctx.globalAlpha = 0.75;
            ctx.beginPath();
            hours.forEach((h, idx) => {
              const mVal = byHour[h].reduce((a, b) => a + b, 0) / byHour[h].length;
              const hx = timeToX(h);
              const hy = timeValToY(mVal);
              if (idx === 0) ctx.moveTo(hx, hy);
              else ctx.lineTo(hx, hy);
            });
            ctx.stroke();
            ctx.restore();
          }
        });

        if (repPlotMode === 'mean_sd') {
          const timeGroups = {};
          timeRows.forEach(r => {
            const gk = `${getReplicateGroupKey(r)} :: ${r.time_h}`;
            if (!timeGroups[gk]) timeGroups[gk] = [];
            timeGroups[gk].push(r);
          });
          Object.values(timeGroups).forEach(gRows => {
            const rep0 = gRows[0];
            if (rep0.time_h < xMin || rep0.time_h > xMax) return;
            const st = calcStats(gRows.map(x => x.value));
            if (st.mean === null) return;
            const sKey = getComparisonGroupValue(rep0, currentDomain);
            const cfg = activeSeriesMap[sKey] || { color: '#00B5E2', shape: 'circle', offset: 0 };
            const x = Math.max(pad.left + 6, Math.min(pad.left + plotW - 6, timeToX(rep0.time_h) + cfg.offset * 12));
            const y = timeValToY(st.mean);
            const isPinned = pinnedRecord && gRows.some(gr => gr.record_id === pinnedRecord.record_id && gr.parameter === pinnedRecord.parameter);

            if (st.n >= 2 && st.sd > 0) {
              const yLow = timeValToY(st.mean - st.sd);
              const yHigh = timeValToY(st.mean + st.sd);
              ctx.save();
              ctx.strokeStyle = cfg.color;
              ctx.lineWidth = 1.9;
              ctx.globalAlpha = 0.9;
              ctx.beginPath();
              ctx.moveTo(x, yHigh);
              ctx.lineTo(x, yLow);
              ctx.moveTo(x - 4, yHigh);
              ctx.lineTo(x + 4, yHigh);
              ctx.moveTo(x - 4, yLow);
              ctx.lineTo(x + 4, yLow);
              ctx.stroke();
              ctx.restore();
            }

            ctx.fillStyle = cfg.color;
            ctx.globalAlpha = 0.95;
            ctx.strokeStyle = isPinned ? '#ffffff' : 'rgba(0,0,0,0.45)';
            ctx.lineWidth = isPinned ? 2.2 : 1.2;
            drawShape(ctx, cfg.shape, x, y, isPinned ? 7.0 : 5.4);
            renderedPoints.push({ x, y, r: rep0, groupRows: gRows, groupStats: st, isGroupMean: true });
          });
        } else {
          timeRows.forEach(r => {
            if (r.time_h < xMin || r.time_h > xMax) return;
            const gRows = repGroupsMap[getReplicateGroupKey(r)] || [r];
            const gStats = calcStats(gRows.map(x => x.value));
            const sKey = getComparisonGroupValue(r, currentDomain);
            const cfg = activeSeriesMap[sKey] || { color: '#00B5E2', shape: 'circle', offset: 0 };
            const x = Math.max(pad.left + 6, Math.min(pad.left + plotW - 6, timeToX(r.time_h) + cfg.offset * 12 + r.jitter * 4.0));
            const y = timeValToY(r.value);
            const isPinned = pinnedRecord && pinnedRecord.record_id === r.record_id && pinnedRecord.parameter === r.parameter;

            ctx.fillStyle = cfg.color;
            ctx.globalAlpha = isPinned ? 1.0 : 0.85;
            ctx.strokeStyle = isPinned ? '#ffffff' : 'rgba(0,0,0,0.25)';
            ctx.lineWidth = isPinned ? 2 : 0.8;
            drawShape(ctx, cfg.shape, x, y, isPinned ? 6 : 4.2);
            renderedPoints.push({ x, y, r, groupRows: gRows, groupStats: gStats, isGroupMean: false });
          });
        }
        ctx.restore();
        ctx.globalAlpha = 1.0;
        return;
      }

      const useLog = (currentDomain === 'icp' || currentDomain === 'xrf' || currentDomain === 'gasification') && scaleMode === 'log';
      const activeParamSet = new Set(params);
      const plottedNumericRows = numericRows.filter(r => activeParamSet.has(r.parameter));
      const scaleRows = plottedNumericRows.length ? plottedNumericRows : numericRows;

      let yMin = 0;
      let yMax = 100;
      if (useLog) {
        const posVals = scaleRows.map(r => r.value).filter(v => v > 0);
        const minPos = posVals.length ? Math.min(...posVals) : 0.1;
        const maxPos = posVals.length ? Math.max(...posVals) : 10000;
        yMin = Math.floor(Math.log10(Math.max(1e-2, minPos)));
        yMax = Math.ceil(Math.log10(Math.max(10, maxPos)));
        if (yMax <= yMin) yMax = yMin + 4;
      } else {
        const rawMax = scaleRows.length ? Math.max(...scaleRows.map(r => r.value)) : 100;
        yMax = computeNiceAxisMax(rawMax, yRangeMode, currentDomain);
      }
      const totalCols = useResourceColumns ? Math.max(1, seriesKeys.length) : Math.max(1, params.length);
      let xMin = 0;
      let xMax = totalCols;
      if (state.zoomBounds) {
        if (Number.isFinite(state.zoomBounds.yMin) && Number.isFinite(state.zoomBounds.yMax) && state.zoomBounds.yMax > state.zoomBounds.yMin) {
          yMin = state.zoomBounds.yMin;
          yMax = state.zoomBounds.yMax;
        }
        const zbXMin = Number.isFinite(state.zoomBounds.xMin)
          ? state.zoomBounds.xMin
          : (Array.isArray(state.zoomBounds.xCatIndices) ? state.zoomBounds.xCatIndices[0] : null);
        const zbXMax = Number.isFinite(state.zoomBounds.xMax)
          ? state.zoomBounds.xMax
          : (Array.isArray(state.zoomBounds.xCatIndices) ? state.zoomBounds.xCatIndices[1] + 1 : null);
        if (Number.isFinite(zbXMin) && Number.isFinite(zbXMax) && zbXMax > zbXMin) {
          xMin = Math.max(0, Math.min(totalCols - 0.1, zbXMin));
          xMax = Math.max(xMin + 0.1, Math.min(totalCols, zbXMax));
        }
      }
      const isXZoomed = Math.abs(xMin - 0) > 1e-4 || Math.abs(xMax - totalCols) > 1e-4;
      const xSpan = Math.max(0.1, xMax - xMin);
      const catIndexToX = (idx, count, twoColLeft = 0.28, twoColRight = 0.72) => {
        if (!isXZoomed && count === 2) {
          return pad.left + plotW * (idx === 0 ? twoColLeft : twoColRight);
        }
        return pad.left + (((idx + 0.5) - xMin) / xSpan) * plotW;
      };
      lastPlotTransform = {
        pad, plotW, plotH, xMin, xMax, yMin, yMax, useLog, mode: 'scatter', isCategorical: true,
        pxToDataX: px => xMin + ((px - pad.left) / Math.max(1, plotW)) * (xMax - xMin),
        pxToDataY: py => yMin + ((pad.top + plotH - py) / Math.max(1, plotH)) * (yMax - yMin)
      };

      // Draw Y gridlines & unit-aware tick labels
      ctx.font = '11px system-ui, -apple-system, sans-serif';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      const ySteps = useLog ? Math.min(6, Math.max(1, Math.round(yMax - yMin))) : 5;
      for (let i = 0; i <= ySteps; i++) {
        const frac = i / ySteps;
        const y = pad.top + plotH - frac * plotH;
        ctx.strokeStyle = theme.grid;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(pad.left + plotW, y);
        ctx.stroke();

        ctx.fillStyle = theme.axisText;
        if (useLog) {
          const expVal = yMin + frac * (yMax - yMin);
          const realVal = Math.pow(10, expVal);
          const uSuffix = primaryUnit ? ` ${primaryUnit}` : '';
          const label = realVal >= 1000 ? `${(realVal / 1000).toFixed(0)}k${uSuffix}` : (realVal >= 1 ? `${realVal.toFixed(0)}${uSuffix}` : `${realVal.toFixed(2)}${uSuffix}`);
          ctx.fillText(label, pad.left - 7, y);
        } else if (!numericRows.length && (currentDomain === 'calorimetry' || currentDomain === 'xrd')) {
          const repLabel = i === 0 ? '' : (i === 5 ? '' : `Rep ${i}`);
          ctx.fillText(repLabel, pad.left - 7, y);
        } else {
          const val = yMin + ((yMax - yMin) / ySteps) * i;
          ctx.fillText(formatTickValueWithUnit(val, primaryUnit, yMax), pad.left - 7, y);
        }
      }

      // Draw rotated Y-axis title with parameter name and scientific unit
      const yAxisTitleText = validParams.length === 1
        ? `${formatParamName(validParams[0], currentDomain)} — Measured Value (${primaryUnit || 'value'})${useLog ? ' [Log10]' : ''}`
        : (uniqueUnits.length === 1
            ? `Measured Value (${uniqueUnits[0]})${useLog ? ' [Log10]' : ''}`
            : `Measured Value (${uniqueUnits.join(' / ') || 'units'})`);
      drawRotatedYAxisTitle(ctx, yAxisTitleText, pad, plotH, theme);

      // Draw X-axis baseline
      ctx.strokeStyle = theme.axisText;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top + plotH);
      ctx.lineTo(pad.left + plotW, pad.top + plotH);
      ctx.stroke();

      const valueToY = val => {
        if (useLog) {
          const logV = Math.log10(Math.max(Math.pow(10, yMin), val));
          const frac = (logV - yMin) / Math.max(1e-9, yMax - yMin);
          return pad.top + plotH - Math.max(0, Math.min(1, frac)) * plotH;
        }
        const frac = (val - yMin) / Math.max(1e-9, yMax - yMin);
        return pad.top + plotH - Math.max(0, Math.min(1, frac)) * plotH;
      };

      // =========================================================================
      // MODE A: Side-by-Side Resource / Condition Columns along X-Axis
      // =========================================================================
      if (useResourceColumns) {
        const colCount = Math.max(1, seriesKeys.length);
        const colWidth = plotW / Math.max(1, xSpan);
        const subParams = validParams.slice(0, 4);
        const paramPalette = ['#00B5E2', '#f59e0b', '#10b981', '#a855f7'];
        const paramShapes = ['circle', 'square', 'diamond', 'triangle'];

        seriesKeys.forEach((sKey, colIdx) => {
          const cx = catIndexToX(colIdx, colCount, 0.28, 0.72);
          const sCfg = activeSeriesMap[sKey] || { color: SERIES_PALETTE[colIdx % SERIES_PALETTE.length], shape: 'circle' };

          if (cx >= pad.left && cx <= pad.left + plotW) {
            // X-axis tick
            ctx.strokeStyle = theme.axisText;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(cx, pad.top + plotH);
            ctx.lineTo(cx, pad.top + plotH + 4);
            ctx.stroke();

            // Resource / condition label on X-axis
            const shortLabel = sKey.length > 26 ? sKey.slice(0, 25) + '…' : sKey;
            drawXAxisTickLabel(ctx, shortLabel, cx, pad.top + plotH, rotateLabels, theme, colCount);
          }

          // Column divider line
          if (colIdx < colCount - 1) {
            const divX = !isXZoomed && colCount === 2
              ? pad.left + plotW * 0.5
              : pad.left + (((colIdx + 1) - xMin) / xSpan) * plotW;
            if (divX >= pad.left && divX <= pad.left + plotW) {
              ctx.strokeStyle = theme.grid;
              ctx.beginPath();
              ctx.moveTo(divX, pad.top);
              ctx.lineTo(divX, pad.top + plotH);
              ctx.stroke();
            }
          }

          ctx.save();
          ctx.beginPath();
          ctx.rect(pad.left, pad.top, plotW, plotH);
          ctx.clip();

          // Draw bars + whiskers + replicate points for each active parameter inside this Resource column
          subParams.forEach((p, pIdx) => {
            const pOffsetFrac = subParams.length === 1 ? 0 : ((pIdx - (subParams.length - 1) / 2) / subParams.length);
            const subCx = cx + pOffsetFrac * (colWidth * 0.72);
            const barWidth = subParams.length === 1
              ? Math.min(54, Math.max(18, colWidth * 0.36))
              : Math.min(26, Math.max(10, (colWidth * 0.62) / subParams.length));
            const barColor = subParams.length === 1 ? sCfg.color : paramPalette[pIdx % paramPalette.length];
            const ptShape = subParams.length === 1 ? sCfg.shape : paramShapes[pIdx % paramShapes.length];

            const cellRows = numericRows.filter(r => r.parameter === p && getComparisonGroupValue(r, currentDomain) === sKey);
            const subVals = cellRows.map(r => r.value);
            if (!subVals.length) return;
            const st = calcStats(subVals);
            if (st.mean === null) return;

            const yMean = valueToY(st.mean);
            const yBase = pad.top + plotH;

            // Translucent vertical mean bar from baseline to yMean
            ctx.save();
            ctx.fillStyle = barColor;
            ctx.globalAlpha = 0.22;
            ctx.fillRect(subCx - barWidth / 2, yMean, barWidth, Math.max(1, yBase - yMean));

            // Bar top cap
            ctx.strokeStyle = barColor;
            ctx.globalAlpha = 0.9;
            ctx.lineWidth = 2.5;
            ctx.beginPath();
            ctx.moveTo(subCx - barWidth / 2, yMean);
            ctx.lineTo(subCx + barWidth / 2, yMean);
            ctx.stroke();

            // ±1 SD error whisker
            let topWhiskerY = yMean;
            if (st.n >= 2 && st.sd > 0) {
              const yLow = valueToY(Math.max(useLog ? Math.pow(10, yMin) : 0, st.mean - st.sd));
              const yHigh = valueToY(st.mean + st.sd);
              topWhiskerY = yHigh;
              ctx.lineWidth = 1.8;
              ctx.globalAlpha = 0.85;
              ctx.beginPath();
              ctx.moveTo(subCx, yHigh);
              ctx.lineTo(subCx, yLow);
              ctx.moveTo(subCx - 5, yHigh);
              ctx.lineTo(subCx + 5, yHigh);
              ctx.moveTo(subCx - 5, yLow);
              ctx.lineTo(subCx + 5, yLow);
              ctx.stroke();
            }

            // Direct numeric Mean ± SD unit badge above bar/whisker
            if (colCount <= 10 && subParams.length <= 2) {
              const pUnit = getParamUnit(p, currentDomain);
              const uShort = pUnit.startsWith('%') ? '%' : (pUnit ? ` ${pUnit}` : '');
              const dec = Math.abs(st.mean) < 10 && Math.abs(st.mean) > 0 ? 2 : 1;
              const valBadge = st.n >= 2
                ? `${st.mean.toFixed(dec)}±${st.sd.toFixed(dec)}${uShort}`
                : `${st.mean.toFixed(dec)}${uShort}`;
              ctx.fillStyle = theme.titleText;
              ctx.globalAlpha = 0.95;
              ctx.font = '600 10px ui-monospace, SFMono-Regular, Menlo, monospace';
              ctx.textAlign = 'center';
              ctx.textBaseline = 'bottom';
              ctx.fillText(valBadge, subCx, Math.max(pad.top + 11, topWhiskerY - 4));
            }
            ctx.restore();

            if (repPlotMode === 'mean_sd') {
              // Group cellRows by replicate group key and plot 1 Mean ± SD marker per replicate group
              const cellRepGroups = buildReplicateGroupsMap(cellRows);
              const cellGroupList = Object.values(cellRepGroups);
              cellGroupList.forEach((gRows, gIdx) => {
                const rep0 = gRows[0];
                const gst = calcStats(gRows.map(x => x.value));
                if (gst.mean === null) return;
                const gOffset = cellGroupList.length === 1 ? 0 : ((gIdx - (cellGroupList.length - 1) / 2) / cellGroupList.length) * Math.min(18, barWidth * 0.6);
                const x = subCx + gOffset;
                const y = valueToY(gst.mean);
                const isPinned = pinnedRecord && gRows.some(gr => gr.record_id === pinnedRecord.record_id && gr.parameter === pinnedRecord.parameter);

                if (gst.n >= 2 && gst.sd > 0) {
                  const yLow = valueToY(Math.max(useLog ? Math.pow(10, yMin) : 0, gst.mean - gst.sd));
                  const yHigh = valueToY(gst.mean + gst.sd);
                  ctx.save();
                  ctx.strokeStyle = barColor;
                  ctx.lineWidth = 2.0;
                  ctx.globalAlpha = 0.95;
                  ctx.beginPath();
                  ctx.moveTo(x, yHigh);
                  ctx.lineTo(x, yLow);
                  ctx.moveTo(x - 4.5, yHigh);
                  ctx.lineTo(x + 4.5, yHigh);
                  ctx.moveTo(x - 4.5, yLow);
                  ctx.lineTo(x + 4.5, yLow);
                  ctx.stroke();
                  ctx.restore();
                }

                ctx.fillStyle = barColor;
                ctx.globalAlpha = 1.0;
                ctx.strokeStyle = isPinned ? '#ffffff' : 'rgba(0,0,0,0.55)';
                ctx.lineWidth = isPinned ? 2.4 : 1.3;
                drawShape(ctx, ptShape, x, y, isPinned ? 7.0 : 5.5);
                renderedPoints.push({ x, y, r: rep0, groupRows: gRows, groupStats: gst, isGroupMean: true });
              });
            } else {
              // Plot individual replicate points overlaid on the bar
              cellRows.forEach(r => {
                const gRows = repGroupsMap[getReplicateGroupKey(r)] || [r];
                const gStats = calcStats(gRows.map(x => x.value));
                const x = subCx + r.jitter * Math.min(8, barWidth * 0.28);
                const y = valueToY(r.value);
                const isPinned = pinnedRecord && pinnedRecord.record_id === r.record_id && pinnedRecord.parameter === r.parameter;
                ctx.fillStyle = barColor;
                ctx.globalAlpha = isPinned ? 1.0 : 0.9;
                ctx.strokeStyle = isPinned ? '#ffffff' : 'rgba(0,0,0,0.45)';
                ctx.lineWidth = isPinned ? 2.2 : 1.0;
                drawShape(ctx, ptShape, x, y, isPinned ? 6.5 : 4.4);
                renderedPoints.push({ x, y, r, groupRows: gRows, groupStats: gStats, isGroupMean: false });
              });
            }
          });
          ctx.restore();
        });

        // X-axis title caption for Side-by-Side Resource Mode
        const dimLabelMap = {
          resource: 'Selected Resources (Side-by-Side Parameter Comparison)',
          sample: 'Selected Prepared Samples (Side-by-Side Comparison)',
          field_sample: 'Field Samples (Side-by-Side Parameter Comparison)',
          experiment: 'Experiments (Side-by-Side Parameter Comparison)',
          method: 'Selected Methods / Preps (Side-by-Side Comparison)',
          collection_date: 'Field Collection Date Cohorts (Side-by-Side)',
          prep_date: 'Prep / Run Date Cohorts (Side-by-Side)'
        };
        ctx.fillStyle = theme.axisText;
        ctx.font = '600 10.5px system-ui, -apple-system, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        ctx.fillText(dimLabelMap[activeCompareDimension] || 'Selected Resources (Side-by-Side)', pad.left + plotW / 2, height - 3);
        ctx.globalAlpha = 1.0;
        return;
      }

      // =========================================================================
      // MODE B: Parameter Columns on X-Axis with Side-by-Side Resource Sub-Lanes
      // =========================================================================
      const paramIndexMap = {};
      params.forEach((p, idx) => { paramIndexMap[p] = idx; });
      const laneWidth = plotW / Math.max(1, xSpan);

      params.forEach((p, idx) => {
        const cx = catIndexToX(idx, params.length, 0.27, 0.73);

        if (cx >= pad.left && cx <= pad.left + plotW) {
          // Tick mark on X-axis
          ctx.strokeStyle = theme.axisText;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(cx, pad.top + plotH);
          ctx.lineTo(cx, pad.top + plotH + 4);
          ctx.stroke();

          const label = xLabels[idx];
          drawXAxisTickLabel(ctx, label, cx, pad.top + plotH, rotateLabels, theme, params.length);
        }

        // Draw side-by-side sub-lane translucent Mean Bar + ±1 SD whiskers for each active resource/series
        if (p !== '(metadata only)') {
          ctx.save();
          ctx.beginPath();
          ctx.rect(pad.left, pad.top, plotW, plotH);
          ctx.clip();
          const sEntries = Object.entries(activeSeriesMap);
          const subBarW = Math.min(28, Math.max(6, (laneWidth * 0.68) / Math.max(1, sEntries.length)));
          sEntries.forEach(([sKey, cfg]) => {
            const subVals = numericRows
              .filter(r => r.parameter === p && getComparisonGroupValue(r, currentDomain) === sKey)
              .map(r => r.value);
            if (!subVals.length) return;
            const st = calcStats(subVals);
            if (st.mean === null) return;
            const subCx = cx + cfg.offset * (laneWidth * 0.82);
            const yMean = valueToY(st.mean);
            const yBase = pad.top + plotH;

            ctx.save();
            // Translucent mean bar from X-axis baseline to yMean so side-by-side comparison is immediately readable
            ctx.fillStyle = cfg.color;
            ctx.globalAlpha = sEntries.length > 1 ? 0.20 : 0.16;
            ctx.fillRect(subCx - subBarW / 2, yMean, subBarW, Math.max(1, yBase - yMean));

            ctx.strokeStyle = cfg.color;
            let topWhiskerY = yMean;
            if (st.n >= 2 && st.sd > 0) {
              const yLow = valueToY(Math.max(useLog ? Math.pow(10, yMin) : 0, st.mean - st.sd));
              const yHigh = valueToY(st.mean + st.sd);
              topWhiskerY = yHigh;
              ctx.globalAlpha = 0.72;
              ctx.lineWidth = 1.8;
              ctx.beginPath();
              ctx.moveTo(subCx, yHigh);
              ctx.lineTo(subCx, yLow);
              ctx.stroke();
            }
            // Horizontal mean cap bar
            const barHalf = subBarW / 2;
            ctx.lineWidth = 2.4;
            ctx.globalAlpha = 0.92;
            ctx.beginPath();
            ctx.moveTo(subCx - barHalf, yMean);
            ctx.lineTo(subCx + barHalf, yMean);
            ctx.stroke();

            // Show compact numeric mean label when <= 4 parameters and <= 4 resources
            if (params.length <= 4 && sEntries.length <= 4) {
              const dec = Math.abs(st.mean) < 10 && Math.abs(st.mean) > 0 ? 1 : 0;
              ctx.fillStyle = theme.titleText;
              ctx.globalAlpha = 0.9;
              ctx.font = '600 9.5px ui-monospace, SFMono-Regular, Menlo, monospace';
              ctx.textAlign = 'center';
              ctx.textBaseline = 'bottom';
              ctx.fillText(st.mean.toFixed(dec), subCx, Math.max(pad.top + 10, topWhiskerY - 3));
            }
            ctx.restore();
          });
          ctx.restore();
        }

        if (p === '(metadata only)') {
          const calCount = filteredRows.filter(r => r.parameter === '(metadata only)').length;
          ctx.save();
          ctx.fillStyle = theme.axisText;
          ctx.font = '600 10px system-ui, -apple-system, sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          ctx.fillText(`${calCount} calorimetry_record run${calCount === 1 ? '' : 's'} logged (numeric HHV pending ETL in observation)`, cx, pad.top + 4);
          ctx.restore();
        }

        if (idx < params.length - 1) {
          const divX = !isXZoomed && params.length === 2
            ? pad.left + plotW * 0.5
            : pad.left + (((idx + 1) - xMin) / xSpan) * plotW;
          if (divX >= pad.left && divX <= pad.left + plotW) {
            ctx.strokeStyle = theme.grid;
            ctx.beginPath();
            ctx.moveTo(divX, pad.top);
            ctx.lineTo(divX, pad.top + plotH);
            ctx.stroke();
          }
        }
      });

      const xAxisTitleMap = {
        fermentation: 'Carbon-Flow Parameter (with Units) — Side-by-Side Resource Sub-Lanes',
        pretreatment: 'Pretreatment Monomeric Yield Parameter (% of Glucan / Xylan)',
        icp: 'ICP Element Symbol (ppm) — Ordered by Concentration',
        xrf: 'XRF Element / Oxide Parameter (ppm)',
        proximate: 'Proximate Analysis Parameter (% Dry/Wet Basis)',
        compositional: 'Compositional Analysis Parameter (% Dry Weight)',
        ultimate: 'Ultimate Analysis Parameter (% Dry Weight)',
        calorimetry: 'Calorimetry Parameter (MJ/kg)',
        xrd: 'XRD Crystallinity Parameter (%)',
        gasification: 'Gasification Parameter (ppm / °C / %)'
      };
      ctx.fillStyle = theme.axisText;
      ctx.font = '600 10.5px system-ui, -apple-system, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillText(xAxisTitleMap[currentDomain] || 'Analytical Parameter (with Units)', pad.left + plotW / 2, height - 3);

      ctx.save();
      ctx.beginPath();
      ctx.rect(pad.left, pad.top, plotW, plotH);
      ctx.clip();
      if (repPlotMode === 'mean_sd') {
        Object.values(repGroupsMap).forEach(gRows => {
          const rep0 = gRows[0];
          const pIdx = paramIndexMap[rep0.parameter];
          if (pIdx === undefined) return;
          const baseCx = catIndexToX(pIdx, params.length, 0.27, 0.73);

          const sKey = getComparisonGroupValue(rep0, currentDomain);
          const cfg = activeSeriesMap[sKey] || { color: '#00B5E2', shape: 'circle', offset: 0 };
          const mOffset = cfg.offset * (laneWidth * 0.82);
          const x = baseCx + mOffset;

          const gst = calcStats(gRows.map(x => x.value));
          const isMetaOnly = gst.mean === null;
          let y;
          if (isMetaOnly) {
            y = pad.top + plotH * 0.5;
          } else {
            y = valueToY(gst.mean);
          }

          if (!isMetaOnly && gst.n >= 2 && gst.sd > 0) {
            const yLow = valueToY(Math.max(useLog ? Math.pow(10, yMin) : 0, gst.mean - gst.sd));
            const yHigh = valueToY(gst.mean + gst.sd);
            ctx.save();
            ctx.strokeStyle = cfg.color;
            ctx.lineWidth = 2.0;
            ctx.globalAlpha = 0.95;
            ctx.beginPath();
            ctx.moveTo(x, yHigh);
            ctx.lineTo(x, yLow);
            ctx.moveTo(x - 4.5, yHigh);
            ctx.lineTo(x + 4.5, yHigh);
            ctx.moveTo(x - 4.5, yLow);
            ctx.lineTo(x + 4.5, yLow);
            ctx.stroke();
            ctx.restore();
          }

          const isPinned = pinnedRecord && gRows.some(gr => gr.record_id === pinnedRecord.record_id && gr.parameter === pinnedRecord.parameter);
          ctx.fillStyle = cfg.color;
          ctx.globalAlpha = 1.0;
          ctx.strokeStyle = isPinned ? '#ffffff' : 'rgba(0,0,0,0.45)';
          ctx.lineWidth = isPinned ? 2.4 : 1.3;
          drawShape(ctx, cfg.shape, x, y, isPinned ? 7.0 : 5.4);
          renderedPoints.push({ x, y, r: rep0, groupRows: gRows, groupStats: gst, isGroupMean: true });
        });
      } else {
        filteredRows.forEach(r => {
          const pIdx = paramIndexMap[r.parameter];
          if (pIdx === undefined) return;
          const baseCx = catIndexToX(pIdx, params.length, 0.27, 0.73);

          const sKey = getComparisonGroupValue(r, currentDomain);
          const cfg = activeSeriesMap[sKey] || { color: '#00B5E2', shape: 'circle', offset: 0 };
          const mOffset = cfg.offset * (laneWidth * 0.82);
          const jitterScale = params.length <= 4 ? 5.0 : 2.0;
          const x = baseCx + mOffset + r.jitter * jitterScale;

          const isMetaOnly = r.value === null || isNaN(r.value);
          let y;
          if (isMetaOnly) {
            const repNum = Math.max(1, Math.min(4, Number(r.replicate) || 1));
            const frac = 0.28 + ((repNum - 1) * 0.14) + (r.jitter * 0.09);
            y = pad.top + plotH * (1 - Math.max(0.18, Math.min(0.84, frac)));
          } else {
            y = valueToY(r.value);
          }

          const gRows = repGroupsMap[getReplicateGroupKey(r)] || [r];
          const gStats = calcStats(gRows.map(x => x.value));

          const isPinned = pinnedRecord && pinnedRecord.record_id === r.record_id && pinnedRecord.parameter === r.parameter;
          ctx.fillStyle = cfg.color;
          ctx.globalAlpha = isPinned ? 1.0 : 0.88;
          ctx.strokeStyle = isPinned ? '#ffffff' : 'rgba(0,0,0,0.35)';
          ctx.lineWidth = isPinned ? 2.2 : 1.0;

          drawShape(ctx, cfg.shape, x, y, isPinned ? 6.5 : (isMetaOnly ? 5.2 : 4.2));
          if (isMetaOnly) {
            ctx.save();
            ctx.setLineDash([2, 2]);
            ctx.strokeStyle = cfg.color;
            ctx.lineWidth = 1.3;
            ctx.beginPath();
            ctx.arc(x, y, isPinned ? 9.5 : 7.8, 0, Math.PI * 2);
            ctx.stroke();
            ctx.restore();
          }
          renderedPoints.push({ x, y, r, groupRows: gRows, groupStats: gStats, isGroupMean: false });
        });
      }
      if (window.__HIGHLIGHT_RK__) {
        const matchedPts = renderedPoints.filter(pt => pt.r && (
          window.matchesReplicateGroupKey
            ? window.matchesReplicateGroupKey(getReplicateGroupKey(pt.r), window.__HIGHLIGHT_RK__)
            : String(getReplicateGroupKey(pt.r)).toLowerCase() === window.__HIGHLIGHT_RK__
        ));
        matchedPts.forEach(pt => {
          ctx.save();
          ctx.strokeStyle = '#2563eb';
          ctx.lineWidth = 2.2;
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 8.5, 0, Math.PI * 2);
          ctx.stroke();
          ctx.setLineDash([3, 2]);
          ctx.strokeStyle = '#dc2626';
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 11.5, 0, Math.PI * 2);
          ctx.stroke();
          ctx.restore();
        });
        if (!pinnedRecord && matchedPts.length > 0) {
          pinRecord(matchedPts[0].r, matchedPts[0].groupRows, matchedPts[0].groupStats);
        }
      }
      ctx.restore();
      ctx.globalAlpha = 1.0;
    }

    function renderStrip() {
      const canvas = document.getElementById('plot-canvas');
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      const width = rect.width || 640;
      const height = 365;
      canvas.style.height = height + 'px';
      canvas.width = width * dpr;
      canvas.height = height * dpr;

      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);
      const theme = getThemeColors();
      ctx.fillStyle = theme.canvasBg;
      ctx.fillRect(0, 0, width, height);

      const pad = { top: 14, right: 24, bottom: 48, left: 205 };
      const plotW = width - pad.left - pad.right;
      const plotH = height - pad.top - pad.bottom;

      const numericRows = filteredRows.filter(r => typeof r.value === 'number' && !isNaN(r.value));
      const stripRows = (currentDomain === 'calorimetry' || currentDomain === 'xrd' || !numericRows.length) ? filteredRows : numericRows;
      renderedPoints = [];

      if (!stripRows.length) {
        ctx.fillStyle = theme.axisText;
        ctx.font = '13px system-ui, -apple-system, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('No replicate rows available in current slice.', width / 2, height / 2);
        return;
      }

      const effDim = getEffectiveCompareDimension();
      const groups = {};
      stripRows.forEach(r => {
        const sVal = getSeriesValue(r, currentDomain);
        const compVal = getComparisonGroupValue(r, currentDomain);
        const pDisp = formatParamWithUnit(r.parameter, currentDomain);
        let key;
        let label;
        if (effDim === 'resource') {
          key = `${r.resource_name} :: ${r.prepared_sample_name} :: ${pDisp}`;
          label = `${r.resource_name} · ${r.prepared_sample_name} (${pDisp})`;
        } else if (effDim === 'sample') {
          key = `${r.prepared_sample_name} :: ${sVal} :: ${pDisp}`;
          label = `${r.prepared_sample_name} · ${sVal} (${pDisp})`;
        } else if (effDim === 'field_sample' || effDim === 'experiment' || effDim === 'collection_date' || effDim === 'prep_date') {
          key = `${compVal} :: ${r.prepared_sample_name} :: ${pDisp}`;
          label = `${compVal} · ${r.prepared_sample_name} (${pDisp})`;
        } else {
          key = `${sVal} :: ${r.prepared_sample_name} :: ${pDisp}`;
          label = `${sVal} · ${r.prepared_sample_name} (${pDisp})`;
        }
        if (!groups[key]) {
          groups[key] = {
            label,
            compareGroup: compVal,
            sample: r.prepared_sample_name,
            method: sVal,
            parameter: r.parameter,
            rows: []
          };
        }
        groups[key].rows.push(r);
      });

      const groupList = Object.values(groups).map(g => {
        const vals = g.rows.map(x => (typeof x.value === 'number' && !isNaN(x.value)) ? x.value : null).filter(v => v !== null);
        const isMetaGroup = vals.length === 0;
        const min = isMetaGroup ? 0 : Math.min(...vals);
        const max = isMetaGroup ? 0 : Math.max(...vals);
        const mean = isMetaGroup ? 0 : vals.reduce((a, b) => a + b, 0) / vals.length;
        const st = calcStats(vals);
        return { ...g, isMetaGroup, min, max, spread: max - min, mean, st, count: g.rows.length };
      });

      const sortBy = document.getElementById('strip-sort').value;
      groupList.sort((a, b) => (b[sortBy] - a[sortBy]) || (b.count - a.count));
      const topGroups = groupList.slice(0, 14);

      const rawMax = topGroups.length ? Math.max(...topGroups.map(g => g.max)) : 10;
      let xMinVal = 0;
      let xMax = computeNiceAxisMax(rawMax, yRangeMode, currentDomain);
      const resetZoomBtn = document.getElementById('btn-reset-zoom');
      if (resetZoomBtn) resetZoomBtn.style.display = state.zoomBounds ? 'inline-flex' : 'none';
      if (state.zoomBounds && Number.isFinite(state.zoomBounds.xMin) && Number.isFinite(state.zoomBounds.xMax) && state.zoomBounds.xMax > state.zoomBounds.xMin) {
        xMinVal = Math.max(0, state.zoomBounds.xMin);
        xMax = state.zoomBounds.xMax;
      }
      lastPlotTransform = {
        pad, plotW, plotH, xMin: xMinVal, xMax, yMin: 0, yMax: Math.max(1, topGroups.length), useLog: false, mode: 'strip',
        pxToDataX: px => xMinVal + ((px - pad.left) / Math.max(1, plotW)) * (xMax - xMinVal),
        pxToDataY: py => ((py - pad.top) / Math.max(1, plotH)) * Math.max(1, topGroups.length)
      };
      const activeParams = Array.from(new Set(topGroups.map(g => g.parameter).filter(Boolean)));
      const stripUnit = activeParams.length === 1
        ? getParamUnit(activeParams[0], currentDomain)
        : ((numericRows[0] && getCanonicalUnit(numericRows[0].parameter, numericRows[0].unit, currentDomain)) || '');

      // X-axis baseline
      ctx.strokeStyle = theme.axisText;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top + plotH);
      ctx.lineTo(pad.left + plotW, pad.top + plotH);
      ctx.stroke();

      ctx.font = '600 11px system-ui, -apple-system, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      for (let i = 0; i <= 5; i++) {
        const val = xMinVal + ((xMax - xMinVal) / 5) * i;
        const x = pad.left + ((val - xMinVal) / Math.max(1e-9, xMax - xMinVal)) * plotW;
        ctx.strokeStyle = theme.grid;
        ctx.beginPath();
        ctx.moveTo(x, pad.top);
        ctx.lineTo(x, pad.top + plotH);
        ctx.stroke();

        ctx.strokeStyle = theme.axisText;
        ctx.beginPath();
        ctx.moveTo(x, pad.top + plotH);
        ctx.lineTo(x, pad.top + plotH + 4);
        ctx.stroke();

        ctx.fillStyle = theme.titleText;
        ctx.fillText(formatTickValueWithUnit(val, stripUnit, xMax), x, pad.top + plotH + 7);
      }

      ctx.fillStyle = theme.axisText;
      ctx.font = '600 10.5px system-ui, -apple-system, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillText(stripUnit ? `Measured Parameter Value (${stripUnit})` : 'Measured Parameter Value', pad.left + plotW / 2, height - 4);

      const rowStep = plotH / Math.max(1, topGroups.length);
      const valToStripX = val => pad.left + ((Math.max(xMinVal, Math.min(xMax, val)) - xMinVal) / Math.max(1e-9, xMax - xMinVal)) * plotW;
      topGroups.forEach((g, idx) => {
        const y = pad.top + idx * rowStep + rowStep / 2;
        ctx.fillStyle = theme.axisText;
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        const shortLabel = g.label.length > 33 ? g.label.slice(0, 32) + '…' : g.label;
        ctx.fillText(shortLabel, pad.left - 8, y);

        ctx.save();
        ctx.beginPath();
        ctx.rect(pad.left, pad.top, plotW, plotH);
        ctx.clip();

        if (!g.isMetaGroup) {
          const xMin = valToStripX(g.min);
          const xMaxBar = valToStripX(g.max);
          ctx.strokeStyle = theme.rangeBar;
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.moveTo(xMin, y);
          ctx.lineTo(xMaxBar, y);
          ctx.stroke();
        }

        if (repPlotMode === 'mean_sd' && !g.isMetaGroup) {
          const rep0 = g.rows[0];
          const xMean = valToStripX(g.mean);
          const sKey = getComparisonGroupValue(rep0, currentDomain);
          const cfg = activeSeriesMap[sKey] || { color: SERIES_PALETTE[idx % SERIES_PALETTE.length] };
          if (g.st.n >= 2 && g.st.sd > 0) {
            const xLow = valToStripX(g.mean - g.st.sd);
            const xHigh = valToStripX(g.mean + g.st.sd);
            ctx.save();
            ctx.strokeStyle = cfg.color;
            ctx.lineWidth = 2.0;
            ctx.beginPath();
            ctx.moveTo(xLow, y);
            ctx.lineTo(xHigh, y);
            ctx.moveTo(xLow, y - 4);
            ctx.lineTo(xLow, y + 4);
            ctx.moveTo(xHigh, y - 4);
            ctx.lineTo(xHigh, y + 4);
            ctx.stroke();
            ctx.restore();
          }
          const isPinned = pinnedRecord && g.rows.some(gr => gr.record_id === pinnedRecord.record_id && gr.parameter === pinnedRecord.parameter);
          ctx.fillStyle = cfg.color;
          ctx.strokeStyle = isPinned ? '#ffffff' : 'rgba(0,0,0,0.4)';
          ctx.lineWidth = isPinned ? 2.2 : 1.2;
          ctx.beginPath();
          ctx.arc(xMean, y, isPinned ? 6.5 : 5.5, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
          renderedPoints.push({ x: xMean, y, r: rep0, groupRows: g.rows, groupStats: g.st, isGroupMean: true });
        } else {
          g.rows.forEach((r, rIdx) => {
            const isMetaOnly = r.value === null || isNaN(r.value);
            const x = isMetaOnly
              ? pad.left + Math.min(plotW - 24, 34 + rIdx * 22)
              : valToStripX(r.value);
            const isPinned = pinnedRecord && pinnedRecord.record_id === r.record_id && pinnedRecord.parameter === r.parameter;
            const sKey = getComparisonGroupValue(r, currentDomain);
            const cfg = activeSeriesMap[sKey] || { color: SERIES_PALETTE[rIdx % SERIES_PALETTE.length] };
            ctx.fillStyle = cfg.color;
            ctx.strokeStyle = isPinned ? '#ffffff' : 'rgba(0,0,0,0.3)';
            ctx.lineWidth = isPinned ? 2 : 0.8;
            ctx.beginPath();
            ctx.arc(x, y, isPinned ? 5.5 : 4.5, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
            if (isMetaOnly && rIdx === g.rows.length - 1) {
              ctx.save();
              ctx.fillStyle = theme.axisText;
              ctx.font = '500 10px system-ui, -apple-system, sans-serif';
              ctx.textAlign = 'left';
              ctx.textBaseline = 'middle';
              ctx.fillText(`calorimetry_record (${r.record_id}, exp: ${r.experiment}, QC: ${r.qc_pass}) — numeric HHV pending ETL`, x + 10, y);
              ctx.restore();
            }
            renderedPoints.push({ x, y, r, groupRows: g.rows, groupStats: g.st, isGroupMean: false });
          });
        }
        ctx.restore();
      });
      if (window.__HIGHLIGHT_RK__) {
        const matchedPts = renderedPoints.filter(pt => pt.r && (
          window.matchesReplicateGroupKey
            ? window.matchesReplicateGroupKey(getReplicateGroupKey(pt.r), window.__HIGHLIGHT_RK__)
            : String(getReplicateGroupKey(pt.r)).toLowerCase() === window.__HIGHLIGHT_RK__
        ));
        matchedPts.forEach(pt => {
          ctx.save();
          ctx.strokeStyle = '#2563eb';
          ctx.lineWidth = 2.2;
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 8.5, 0, Math.PI * 2);
          ctx.stroke();
          ctx.setLineDash([3, 2]);
          ctx.strokeStyle = '#dc2626';
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 11.5, 0, Math.PI * 2);
          ctx.stroke();
          ctx.restore();
        });
        if (!pinnedRecord && matchedPts.length > 0) {
          pinRecord(matchedPts[0].r, matchedPts[0].groupRows, matchedPts[0].groupStats);
        }
      }
    }

    // Canvas hover, brush zoom & click hit-testing
    const canvasEl = document.getElementById('plot-canvas');
    const brushEl = document.getElementById('canvas-zoom-brush');
    const tooltipEl = document.getElementById('hover-tooltip');
    const clickPopoverEl = document.getElementById('click-audit-popover');

    function findNearestPoint(evt) {
      const rect = canvasEl.getBoundingClientRect();
      const mx = evt.clientX - rect.left;
      const my = evt.clientY - rect.top;
      let best = null;
      let bestDist = 100;
      for (const pt of renderedPoints) {
        const d2 = (pt.x - mx) ** 2 + (pt.y - my) ** 2;
        if (d2 < bestDist) {
          bestDist = d2;
          best = pt;
        }
      }
      return best;
    }

    canvasEl.addEventListener('mousedown', evt => {
      if (evt.button !== 0) return;
      const rect = canvasEl.getBoundingClientRect();
      brush.active = true;
      brush.startX = evt.clientX - rect.left;
      brush.startY = evt.clientY - rect.top;
      brush.curX = brush.startX;
      brush.curY = brush.startY;
      if (brushEl) {
        brushEl.style.display = 'none';
        brushEl.style.left = `${canvasEl.offsetLeft + brush.startX}px`;
        brushEl.style.top = `${canvasEl.offsetTop + brush.startY}px`;
        brushEl.style.width = '0px';
        brushEl.style.height = '0px';
      }
    });

    function finishCanvasBrush(evt) {
      if (!brush.active) return;
      const rect = canvasEl.getBoundingClientRect();
      if (evt && typeof evt.clientX === 'number') {
        brush.curX = Math.max(0, Math.min(rect.width, evt.clientX - rect.left));
        brush.curY = Math.max(0, Math.min(rect.height, evt.clientY - rect.top));
      }
      brush.active = false;
      if (brushEl) brushEl.style.display = 'none';
      const dx = Math.abs(brush.curX - brush.startX);
      const dy = Math.abs(brush.curY - brush.startY);
      if (dx >= 6 && dy >= 6 && lastPlotTransform) {
        brush.suppressNextClick = true;
        const x0 = Math.min(brush.startX, brush.curX);
        const x1 = Math.max(brush.startX, brush.curX);
        const y0 = Math.min(brush.startY, brush.curY);
        const y1 = Math.max(brush.startY, brush.curY);
        const dataX0 = lastPlotTransform.pxToDataX(x0);
        const dataX1 = lastPlotTransform.pxToDataX(x1);
        const dataY0 = lastPlotTransform.pxToDataY(y1);
        const dataY1 = lastPlotTransform.pxToDataY(y0);
        const minX = Math.min(dataX0, dataX1);
        const maxX = Math.max(dataX0, dataX1);
        const xCatIndices = lastPlotTransform.isCategorical
          ? [Math.max(0, Math.floor(minX)), Math.max(0, Math.ceil(maxX) - 1)]
          : null;
        state.zoomBounds = {
          xMin: minX,
          xMax: maxX,
          yMin: Math.min(dataY0, dataY1),
          yMax: Math.max(dataY0, dataY1),
          xCatIndices
        };
        const resetBtn = document.getElementById('btn-reset-zoom');
        if (resetBtn) resetBtn.style.display = 'inline-flex';
        closeClickAuditPopover();
        renderPlot();
      }
    }

    canvasEl.addEventListener('mouseup', finishCanvasBrush);
    window.addEventListener('mouseup', finishCanvasBrush);
    canvasEl.addEventListener('dblclick', () => {
      resetCanvasZoom();
    });

    canvasEl.addEventListener('mousemove', evt => {
      if (brush.active) {
        const rect = canvasEl.getBoundingClientRect();
        brush.curX = Math.max(0, Math.min(rect.width, evt.clientX - rect.left));
        brush.curY = Math.max(0, Math.min(rect.height, evt.clientY - rect.top));
        const dx = Math.abs(brush.curX - brush.startX);
        const dy = Math.abs(brush.curY - brush.startY);
        if (brushEl && (dx >= 6 && dy >= 6)) {
          const leftPx = Math.min(brush.startX, brush.curX);
          const topPx = Math.min(brush.startY, brush.curY);
          brushEl.style.display = 'block';
          brushEl.style.left = `${canvasEl.offsetLeft + leftPx}px`;
          brushEl.style.top = `${canvasEl.offsetTop + topPx}px`;
          brushEl.style.width = `${dx}px`;
          brushEl.style.height = `${dy}px`;
          tooltipEl.classList.add('hidden');
          return;
        }
      }
      const hit = findNearestPoint(evt);
      if (!hit) {
        tooltipEl.classList.add('hidden');
        return;
      }
      const r = hit.r;
      const gRows = hit.groupRows || [r];
      const gst = hit.groupStats || calcStats(gRows.map(x => x.value));
      const valStr = hit.isGroupMean && gst.mean !== null
        ? `Mean: ${gst.mean.toFixed(2)} ± ${gst.sd.toFixed(2)} ${r.unit} (n=${gst.n})`
        : (r.value !== null && !isNaN(r.value)
            ? `${r.value.toFixed(2)} ${r.unit}${gst.n > 1 ? ` (Group Mean: ${gst.mean.toFixed(2)} ± ${gst.sd.toFixed(2)}, n=${gst.n})` : ''}`
            : 'Record logged (numeric HHV pending ETL)');
      const paramDisp = formatParamName(r.parameter, currentDomain);
      const methodStr = getSeriesValue(r, currentDomain);
      const colStr = r.collected_date && r.collected_date !== 'Undated' ? r.collected_date : '—';
      const runStr = r.prep_date && r.prep_date !== 'Undated' ? r.prep_date : '—';
      const geoStr = r.geoid && r.geoid !== 'Unassigned' ? `${r.geoid} (${r.county_name || 'CA'})` : '—';
      tooltipEl.innerHTML = `
        <div class="font-semibold text-[var(--foreground)]">${r.prepared_sample_name} <span class="font-normal text-[var(--muted-foreground)]">(${r.field_sample_name || '—'})</span></div>
        <div class="text-[var(--muted-foreground)]">${r.resource_name} · ${methodStr} · exp: ${r.experiment}</div>
        <div class="mt-1 font-medium text-[#00B5E2]">${paramDisp}: ${valStr}</div>
        <div class="text-[11px] font-mono text-[var(--muted-foreground)]">Collected: ${colStr} · GEOID: ${geoStr}</div>
        <div class="text-[11px] font-mono text-[var(--muted-foreground)]">Prep/Run: ${runStr} · ID: ${r.record_id} · QC: ${r.qc_pass} · <span class="text-emerald-400">Click to audit</span></div>
      `;
      tooltipEl.classList.remove('hidden');
      const left = Math.min(hit.x + 12, canvasEl.clientWidth - 255);
      const top = Math.max(8, hit.y - 64);
      tooltipEl.style.left = `${left}px`;
      tooltipEl.style.top = `${top}px`;
    });

    canvasEl.addEventListener('mouseleave', () => {
      tooltipEl.classList.add('hidden');
    });

    canvasEl.addEventListener('click', evt => {
      if (brush.suppressNextClick) {
        brush.suppressNextClick = false;
        return;
      }
      const hit = findNearestPoint(evt);
      if (!hit) {
        closeClickAuditPopover();
        return;
      }
      const gRows = hit.groupRows || [hit.r];
      const gst = hit.groupStats || calcStats(gRows.map(x => x.value));
      pinRecord(hit.r, gRows, gst);
      if (evt.metaKey || evt.ctrlKey || evt.shiftKey) {
        addRecordToExport(hit.r, '');
      }
      renderCurrentView();
      openClickAuditPopover(hit);
    });

    function openClickAuditPopover(hit) {
      if (!clickPopoverEl || !hit || !hit.r) return;
      const r = hit.r;
      const gRows = hit.groupRows || [r];
      const gst = hit.groupStats || calcStats(gRows.map(x => x.value));
      const paramDisp = formatParamName(r.parameter, currentDomain);
      const methodStr = getSeriesValue(r, currentDomain);

      document.getElementById('click-popover-title').textContent = `${r.prepared_sample_name} (${r.field_sample_name || '—'})`;
      document.getElementById('click-popover-subtitle').textContent = `${r.resource_name} · ${methodStr} · exp: ${r.experiment}`;
      const valStr = r.value !== null && !isNaN(r.value) ? `${r.value.toFixed(2)} ${r.unit}` : 'Pending ETL';
      const grpStr = gst.n >= 2 && gst.mean !== null
        ? `Replicate Group (n=${gst.n}): ${gst.mean.toFixed(2)} ± ${gst.sd.toFixed(2)} ${r.unit} (RSD ${gst.rsd ? gst.rsd.toFixed(1) + '%' : '0%'})`
        : `Single observation (${r.record_id})`;
      document.getElementById('click-popover-metrics').innerHTML = `
        <div><span class="text-[var(--muted-foreground)]">${paramDisp}:</span> <strong class="text-[#00B5E2]">${valStr}</strong> <span class="text-[10px] text-[var(--muted-foreground)]">(${r.record_id})</span></div>
        <div class="text-[10px] text-emerald-400 mt-0.5">${grpStr}</div>
      `;

      const scopeGroupBtn = document.getElementById('btn-audit-scope-group');
      const scopeSingleBtn = document.getElementById('btn-audit-scope-single');
      if (scopeGroupBtn) scopeGroupBtn.textContent = `Replicate Group (${gRows.length} pt${gRows.length === 1 ? '' : 's'})`;
      if (scopeSingleBtn) scopeSingleBtn.textContent = `Single Point (${r.record_id.slice(0, 14)})`;
      setAuditPopoverScope(gRows.length > 1 ? 'group' : 'single');
      const popActionSel = document.getElementById('click-popover-action');
      if (popActionSel) popActionSel.value = 'keep_note';
      const popAssigneeEl = document.getElementById('click-popover-assignee');
      if (popAssigneeEl) {
        popAssigneeEl.value = window.getDefaultAssigneeEmail
          ? window.getDefaultAssigneeEmail(r.assigned_to_email || '')
          : (r.assigned_to_email || '');
      }

      const fb = document.getElementById('click-popover-feedback');
      if (fb) { fb.classList.add('hidden'); fb.textContent = ''; }

      clickPopoverEl.classList.remove('hidden');
      const popW = 320;
      const left = Math.max(8, Math.min(hit.x + 14, canvasEl.clientWidth - popW - 8));
      const top = Math.max(8, Math.min(hit.y - 20, canvasEl.clientHeight - 240));
      clickPopoverEl.style.left = `${left}px`;
      clickPopoverEl.style.top = `${top}px`;
    }

    function closeClickAuditPopover() {
      if (clickPopoverEl) clickPopoverEl.classList.add('hidden');
    }

    function setAuditPopoverScope(scope) {
      auditPopoverScope = scope === 'single' ? 'single' : 'group';
      const groupBtn = document.getElementById('btn-audit-scope-group');
      const singleBtn = document.getElementById('btn-audit-scope-single');
      if (groupBtn && singleBtn) {
        if (auditPopoverScope === 'group') {
          groupBtn.className = 'flex-1 py-1 px-2 rounded text-[11px] font-semibold bg-[#00B5E2] text-slate-950 transition-colors';
          singleBtn.className = 'flex-1 py-1 px-2 rounded text-[11px] font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors';
        } else {
          singleBtn.className = 'flex-1 py-1 px-2 rounded text-[11px] font-semibold bg-[#00B5E2] text-slate-950 transition-colors';
          groupBtn.className = 'flex-1 py-1 px-2 rounded text-[11px] font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors';
        }
      }
      const pinScopeSel = document.getElementById('pin-audit-scope');
      if (pinScopeSel) pinScopeSel.value = auditPopoverScope;
    }

    function applyAuditDecisionToRows(targetRows, action, note, reviewer, assignedToEmail) {
      const normalizedAction = String(action || 'keep_note').trim();
      const statusMap = {
        flag_fail: 'fail',
        approve_pass: 'pass',
        keep_note: 'provisional',
        in_review: 'provisional',
        provisional: 'provisional'
      };
      const newQcStatus = statusMap[normalizedAction] || 'provisional';
      const decisionAction = normalizedAction === 'flag_fail'
        ? 'reject_fail'
        : (normalizedAction === 'approve_pass' ? 'approve_pass' : 'in_review');
      const decisionStatus = (normalizedAction === 'flag_fail' || normalizedAction === 'approve_pass')
        ? 'resolved'
        : 'in_review';
      const newQcPass = normalizedAction === 'flag_fail'
        ? 'fail'
        : (normalizedAction === 'approve_pass' ? 'pass' : null);
      const decisionCode = normalizedAction === 'flag_fail'
        ? 'exclude_qc_fail'
        : (normalizedAction === 'approve_pass' ? 'keep' : 'accept_with_note');
      const cleanAssignee = String(assignedToEmail || '').trim() || null;
      const allTargetIds = Array.from(new Set(targetRows.map(tr => String(tr.record_id || '')).filter(Boolean)));
      const isGroupScope = targetRows.length > 1;
      targetRows.forEach(tr => {
        const priorStatus = String(tr.qc_pass || 'pass');
        tr.qc_pass = newQcStatus;
        if (newQcStatus === 'fail') tr.data_status = 'Outlier Flagged';
        else if (newQcStatus === 'pass') tr.data_status = 'Validated';
        else tr.data_status = 'In Review';
        addRecordToExport(tr, `[${normalizedAction.toUpperCase()}] ${note}`);
        if (window.BioCirvQcClient && typeof window.BioCirvQcClient.submitDecision === 'function') {
          window.BioCirvQcClient.submitDecision({
            scope: isGroupScope ? 'replicate_group' : 'single_record',
            resource_name: tr.resource_name || '',
            analysis_type: tr.domain || currentDomain,
            domain: tr.domain || currentDomain,
            parameter_name: tr.parameter || '',
            parameter: tr.parameter || '',
            prepared_sample_name: tr.prepared_sample_name || '',
            field_sample_name: tr.field_sample_name || '',
            experiment_name: tr.experiment || '',
            record_id: String(tr.record_id || ''),
            target_record_ids: isGroupScope ? allTargetIds : [String(tr.record_id || '')],
            action: normalizedAction,
            decision_action: decisionAction,
            decision_status: decisionStatus,
            new_qc_pass: newQcPass,
            decision: decisionCode,
            previous_qc_status: priorStatus,
            prior_qc_status: priorStatus,
            new_qc_status: newQcStatus,
            assigned_to_email: cleanAssignee,
            audit_note: note || `Interactive point/group audit (${normalizedAction})`,
            rationale: note || `Interactive point/group audit (${normalizedAction})`,
            reviewer: reviewer || 'Explorer Interactive Reviewer',
            dashboard_page: 'explorer'
          });
        }
      });
    }

    function submitClickPopoverAuditFinding() {
      if (!pinnedRecord) return;
      const action = (document.getElementById('click-popover-action') || {}).value || 'keep_note';
      const assignedToEmail = ((document.getElementById('click-popover-assignee') || {}).value || '').trim();
      const note = ((document.getElementById('click-popover-note') || {}).value || '').trim() || `Audited via interactive plot (${auditPopoverScope === 'group' ? 'Replicate Group' : 'Single Point'})`;
      const targetRows = (auditPopoverScope === 'group' && pinnedGroupRows && pinnedGroupRows.length) ? pinnedGroupRows : [pinnedRecord];
      applyAuditDecisionToRows(targetRows, action, note, 'Explorer Interactive Reviewer', assignedToEmail);

      const fb = document.getElementById('click-popover-feedback');
      if (fb) {
        fb.textContent = `✓ Submitted ${action} for ${targetRows.length} observation${targetRows.length === 1 ? '' : 's'} & added to Export Tray`;
        fb.classList.remove('hidden');
      }
      const noteEl = document.getElementById('click-popover-note');
      if (noteEl) noteEl.value = '';
      pinRecord(pinnedRecord, pinnedGroupRows, pinnedGroupStats);
      renderCurrentView();
      setTimeout(() => closeClickAuditPopover(), 950);
    }

    function buildFindingModalPayloadFromPinned(scopeMode, noteText, sourceLabel, assignedToEmail) {
      const allGrpRows = (pinnedGroupRows && pinnedGroupRows.length) ? pinnedGroupRows : [pinnedRecord];
      const targetRows = scopeMode === 'group' ? allGrpRows : [pinnedRecord];
      const allGroupIds = Array.from(new Set(allGrpRows.map(r => String(r.record_id || '')).filter(Boolean)));
      const recIds = Array.from(new Set(targetRows.map(r => String(r.record_id || '')).filter(Boolean))).join('|');
      return {
        scope: scopeMode === 'group' ? 'replicate_group' : 'single_record',
        prefer_single: scopeMode === 'single',
        record_id: String(pinnedRecord.record_id || ''),
        group_record_ids: allGroupIds,
        all_group_record_ids: allGroupIds.join('|'),
        record_ids: recIds,
        replicates: allGrpRows.map((r, idx) => ({
          record_id: String(r.record_id || ''),
          replicate: r.replicate_no || (idx + 1),
          value: r.value,
          unit: r.unit || pinnedRecord.unit || '',
          qc_status: r.qc_pass || 'pass'
        })),
        resource_name: pinnedRecord.resource_name || '',
        prepared_sample: pinnedRecord.prepared_sample_name || '',
        field_sample: pinnedRecord.field_sample_name || '',
        experiment: pinnedRecord.experiment || '',
        parameter_name: pinnedRecord.parameter || '',
        parameter: pinnedRecord.parameter || '',
        analysis_type: currentDomain,
        unit: pinnedRecord.unit || '',
        value: pinnedRecord.value,
        default_qc_status: 'provisional',
        assigned_to_email: window.getDefaultAssigneeEmail
          ? window.getDefaultAssigneeEmail(assignedToEmail)
          : String(assignedToEmail || '').trim(),
        title: `[${currentDomain.toUpperCase()}] ${pinnedRecord.resource_name} — ${formatParamName(pinnedRecord.parameter, currentDomain)} (${scopeMode === 'group' ? `Replicate Group n=${allGrpRows.length}` : pinnedRecord.record_id})`,
        category: 'Replicate Outlier / Interactive Plot Audit',
        severity: 'high',
        resources: `${pinnedRecord.resource_name} (${pinnedRecord.prepared_sample_name} / Field: ${pinnedRecord.field_sample_name || '—'})`,
        records: recIds,
        note: noteText || `Flagged from ${sourceLabel} (${scopeMode === 'group' ? `entire replicate group, n=${allGrpRows.length}` : 'single observation'}).`,
        description: noteText || `Flagged from ${sourceLabel} (${scopeMode === 'group' ? `entire replicate group, n=${allGrpRows.length}` : 'single observation'}).`
      };
    }

    function openShowMeFromClickPopover(btnEl) {
      if (!pinnedRecord) return;
      const rk = getReplicateGroupKey(pinnedRecord);
      if (typeof window.openFlagShowMePopover === 'function') {
        window.openFlagShowMePopover({
          replicateGroupKey: rk,
          resource: pinnedRecord.resource_name || '',
          analysisType: pinnedRecord.domain || currentDomain || '',
          parameter: pinnedRecord.parameter || '',
          preparedSample: pinnedRecord.prepared_sample_name || '',
          outlierRecordId: String(pinnedRecord.record_id || '')
        }, btnEl);
      }
    }

    function escalateClickPopoverToModal() {
      if (!pinnedRecord) return;
      const note = ((document.getElementById('click-popover-note') || {}).value || '').trim();
      const assignedToEmail = ((document.getElementById('click-popover-assignee') || {}).value || '').trim();
      closeClickAuditPopover();
      if (typeof window.openSubmitFindingModal === 'function') {
        window.openSubmitFindingModal(buildFindingModalPayloadFromPinned(auditPopoverScope, note, 'Data Visualizer interactive plot', assignedToEmail));
      }
    }

    function submitPinnedAuditFinding() {
      if (!pinnedRecord) return;
      const scope = (document.getElementById('pin-audit-scope') || {}).value || 'group';
      const action = (document.getElementById('pin-audit-action') || {}).value || 'keep_note';
      const assignedToEmail = ((document.getElementById('pin-audit-assignee') || {}).value || '').trim();
      const note = ((document.getElementById('pin-note') || {}).value || '').trim() || `Audited via Pinned Inspector (${scope === 'group' ? 'Replicate Group' : 'Single Point'})`;
      const targetRows = (scope === 'group' && pinnedGroupRows && pinnedGroupRows.length) ? pinnedGroupRows : [pinnedRecord];
      applyAuditDecisionToRows(targetRows, action, note, 'Explorer Pinned Inspector', assignedToEmail);

      const fb = document.getElementById('pin-audit-feedback');
      if (fb) {
        fb.textContent = `✓ Submitted ${action} for ${targetRows.length} observation${targetRows.length === 1 ? '' : 's'} & added to Export Tray`;
        fb.classList.remove('hidden');
      }
      const noteEl = document.getElementById('pin-note');
      if (noteEl) noteEl.value = '';
      pinRecord(pinnedRecord, pinnedGroupRows, pinnedGroupStats);
      renderCurrentView();
    }

    function escalatePinnedToModal() {
      if (!pinnedRecord) return;
      const scope = (document.getElementById('pin-audit-scope') || {}).value || 'group';
      const note = ((document.getElementById('pin-note') || {}).value || '').trim();
      const assignedToEmail = ((document.getElementById('pin-audit-assignee') || {}).value || '').trim();
      if (typeof window.openSubmitFindingModal === 'function') {
        window.openSubmitFindingModal(buildFindingModalPayloadFromPinned(scope, note, 'Pinned Inspector', assignedToEmail));
      }
    }

    function pinRecord(r, groupRowsOpt, groupStatsOpt) {
      pinnedRecord = r;
      const repMap = buildReplicateGroupsMap(filteredRows);
      pinnedGroupRows = groupRowsOpt || repMap[getReplicateGroupKey(r)] || [r];
      pinnedGroupStats = groupStatsOpt || calcStats(pinnedGroupRows.map(x => x.value));
      const valStr = r.value !== null && !isNaN(r.value)
        ? `${r.value.toFixed(2)} ${r.unit}`
        : 'Record logged (HHV pending ETL)';
      const grpSummary = pinnedGroupStats && pinnedGroupStats.n >= 2 && pinnedGroupStats.mean !== null
        ? `${pinnedGroupStats.mean.toFixed(2)} ± ${pinnedGroupStats.sd.toFixed(2)} ${r.unit} (n=${pinnedGroupStats.n})`
        : `Single point (n=1)`;
      const paramDisp = formatParamName(r.parameter, currentDomain);
      const methodStr = getSeriesValue(r, currentDomain);
      const colStr = r.collected_date && r.collected_date !== 'Undated' ? r.collected_date : '—';
      const runStr = r.prep_date && r.prep_date !== 'Undated' ? r.prep_date : '—';
      const geoStr = r.geoid && r.geoid !== 'Unassigned' ? `${r.geoid} · ${r.county_name || 'CA'}` : '—';
      document.getElementById('pin-status-badge').textContent = r.data_status;
      document.getElementById('pinned-details').innerHTML = `
        <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">Record ID:</span><span class="font-mono font-semibold text-[#00B5E2] truncate">${r.record_id}</span></div>
        <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">Prepared Sample:</span><span class="font-medium text-[var(--foreground)] truncate">${r.prepared_sample_name}</span></div>
        <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">Field Sample:</span><span class="font-mono text-[var(--foreground)] truncate">${r.field_sample_name || '—'}</span></div>
        <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">Collected Date:</span><span class="font-mono text-emerald-400 truncate">${colStr}</span></div>
        <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">GEOID / County:</span><span class="font-mono text-amber-400 truncate">${geoStr}</span></div>
        <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">Prep / Run Date:</span><span class="font-mono text-[#00B5E2] truncate">${runStr}</span></div>
        <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">Resource:</span><span class="text-[var(--foreground)] truncate">${r.resource_name}</span></div>
        <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">Method/Prep:</span><span class="text-[var(--foreground)] truncate">${methodStr}</span></div>
        <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">Parameter:</span><span class="text-[var(--foreground)] font-mono truncate">${paramDisp}</span></div>
        <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">Measured:</span><span class="font-semibold text-[var(--foreground)] font-mono truncate">${valStr}</span></div>
        <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">Replicate Group:</span><span class="font-semibold text-emerald-400 font-mono truncate">${grpSummary}</span></div>
        <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">Exp / Provider / QC:</span><span class="text-[var(--foreground)] font-mono">${r.experiment} · ${r.provider_code} · ${r.qc_pass}</span></div>
      `;
      const pinScopeSel = document.getElementById('pin-audit-scope');
      if (pinScopeSel) {
        pinScopeSel.options[0].text = `Audit Scope: Replicate Group (${pinnedGroupRows.length} pt${pinnedGroupRows.length === 1 ? '' : 's'})`;
        pinScopeSel.options[1].text = `Audit Scope: Single Point Only (${r.record_id.slice(0, 14)})`;
      }
      const pinAssigneeEl = document.getElementById('pin-audit-assignee');
      if (pinAssigneeEl) {
        pinAssigneeEl.value = window.getDefaultAssigneeEmail
          ? window.getDefaultAssigneeEmail(r.assigned_to_email || pinAssigneeEl.value || '')
          : (r.assigned_to_email || pinAssigneeEl.value || '');
      }
      document.getElementById('pinned-actions').classList.remove('hidden');
    }

    // Statistical Replicate Precision & Candidate Outlier Screening Engine (BioCirV Report Rules)
    const DIXON_Q95 = { 3: 0.941, 4: 0.765, 5: 0.642, 6: 0.560, 7: 0.507, 8: 0.468, 9: 0.437, 10: 0.412 };
    let statDrawerOpen = false;
    let suppressTraceFlags = true;
    let statFilterMode = 'flagged';
    let lastScreenedGroups = [];

    function getTraceCutoff(domainId, unit) {
      const u = (unit || '').toLowerCase();
      if (domainId === 'icp' || domainId === 'xrf' || u === 'ppm') return 100.0;
      if (domainId === 'compositional') return 0.5;
      if (domainId === 'fermentation' && u === 'g/l') return 0.5;
      return 0.0;
    }

    function dixonQCrit(n) {
      if (n < 3) return null;
      if (DIXON_Q95[n]) return DIXON_Q95[n];
      return 0.412 * Math.sqrt(10.0 / n);
    }

    function sampleMean(arr) {
      if (!arr.length) return 0;
      return arr.reduce((a, b) => a + b, 0) / arr.length;
    }

    function sampleSd(arr) {
      if (arr.length < 2) return 0;
      const m = sampleMean(arr);
      const v = arr.reduce((acc, x) => acc + (x - m) ** 2, 0) / (arr.length - 1);
      return Math.sqrt(v);
    }

    function medianVal(arr) {
      if (!arr.length) return null;
      const s = [...arr].sort((a, b) => a - b);
      const mid = Math.floor(s.length / 2);
      return s.length % 2 !== 0 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
    }

    function proximateComponentBucket(paramName) {
      const p = String(paramName || '').trim().toLowerCase();
      if (p === 'moisture' || p === 'moisture content') return 'moisture';
      if (p === 'ash' || p === 'ash content') return 'ash';
      if (p === 'volatile solids' || p === 'volatile matter' || p === 'volatile solids (vs)' || p === 'vs') return 'vs';
      if (p === 'fixed carbon' || p === 'fixed carbon (fc)' || p === 'fc') return 'fc';
      return null;
    }

    function computeSliceStatScreening(rowsInput) {
      const sourceRows = Array.isArray(rowsInput) ? rowsInput : filteredRows;
      const numRows = sourceRows.filter(r => typeof r.value === 'number' && !isNaN(r.value) && r.parameter && r.parameter !== '(metadata only)');
      const groupMap = {};
      numRows.forEach(r => {
        const sMethod = getSeriesValue(r, currentDomain);
        const prepMethod = (window.groupContextLabel ? window.groupContextLabel(r) : (r.prep_method || sMethod)) || sMethod;
        const key = getReplicateGroupKey(r);
        if (!groupMap[key]) {
          groupMap[key] = {
            group_key: key,
            replicate_group_key: key,
            resource_name: r.resource_name,
            analysis_type: r.analysis_type || currentDomain,
            prepared_sample: r.prepared_sample_name || r.field_sample_name || '—',
            prep_method: prepMethod,
            method_label: prepMethod,
            experiment: r.experiment || '—',
            parameter: r.parameter,
            unit: r.unit || '',
            rows: []
          };
        }
        groupMap[key].rows.push(r);
      });

      // Pre-pass: compute group-level basic stats so we can calculate parameter-level pooled_sd
      const rawGroups = Object.values(groupMap).map(g => {
        g.rows.sort((a, b) => ((Number(a.replicate) || 1) - (Number(b.replicate) || 1)) || String(a.record_id).localeCompare(String(b.record_id)));
        const vals = g.rows.map(x => Number(x.value));
        const n = vals.length;
        const mean = sampleMean(vals);
        const sd = sampleSd(vals);
        return { ...g, vals, n, mean, sd };
      });

      // Compute parameter-level pooled_sd across all replicate groups (n >= 2) for each (parameter, unit)
      const pooledByParam = {};
      rawGroups.forEach(g => {
        const pKey = `${g.parameter}::${g.unit}`;
        if (!pooledByParam[pKey]) pooledByParam[pKey] = { sumSq: 0, sumDf: 0 };
        if (g.n >= 2 && g.sd > 0) {
          pooledByParam[pKey].sumSq += (g.n - 1) * g.sd * g.sd;
          pooledByParam[pKey].sumDf += (g.n - 1);
        }
      });
      const pooledSdMap = {};
      Object.entries(pooledByParam).forEach(([pKey, acc]) => {
        pooledSdMap[pKey] = acc.sumDf > 0 ? Math.sqrt(acc.sumSq / acc.sumDf) : 0;
      });

      // Compute Data Portal proximate_sum per (resource_name, experiment, prep_method) stratum:
      // COALESCE(avg_moisture, 0) + COALESCE(avg_ash, 0) + COALESCE(avg_vs, 100 - COALESCE(avg_fc, 0))
      const normalizeProxStratumPart = val => {
        const s = String(val || '').trim();
        return (!s || s === '—' || s === 'Unrecorded') ? 'unassigned' : s;
      };
      const proximateStrataAcc = {};
      rawGroups.forEach(g => {
        const domSlug = window.canonicalDomainSlug ? window.canonicalDomainSlug(g.analysis_type) : String(g.analysis_type || currentDomain).toLowerCase();
        if (domSlug !== 'proximate') return;
        const bucket = proximateComponentBucket(g.parameter);
        if (!bucket || g.mean === null || isNaN(g.mean)) return;
        const sKey = `${g.resource_name}::${normalizeProxStratumPart(g.experiment)}::${normalizeProxStratumPart(g.prep_method)}`;
        if (!proximateStrataAcc[sKey]) {
          proximateStrataAcc[sKey] = { moisture: [], ash: [], vs: [], fc: [] };
        }
        proximateStrataAcc[sKey][bucket].push(g.mean);
      });
      const proximateStrataClosure = {};
      Object.entries(proximateStrataAcc).forEach(([sKey, buckets]) => {
        const m = buckets.moisture.length ? sampleMean(buckets.moisture) : null;
        const a = buckets.ash.length ? sampleMean(buckets.ash) : null;
        const v = buckets.vs.length ? sampleMean(buckets.vs) : null;
        const f = buckets.fc.length ? sampleMean(buckets.fc) : null;
        if ((v === null && f === null) || (m === null && a === null)) return;
        const vsTerm = v !== null ? v : (f !== null ? (100.0 - f) : 0.0);
        const sumPct = (m !== null ? m : 0.0) + (a !== null ? a : 0.0) + vsTerm;
        proximateStrataClosure[sKey] = {
          proximate_sum_pct: sumPct,
          out_of_bounds: sumPct > 0.0 && (sumPct < 95.0 || sumPct > 105.0)
        };
      });

      const groups = rawGroups.map(g => {
        const vals = g.vals;
        const n = g.n;
        const mean = g.mean;
        const sd = g.sd;
        const pKey = `${g.parameter}::${g.unit}`;
        const pooledSd = pooledSdMap[pKey] || 0;
        const rsd = (n >= 2 && Math.abs(mean) > 1e-12) ? Math.abs(sd / mean) * 100.0 : null;
        const minV = Math.min(...vals);
        const maxV = Math.max(...vals);
        const identicalReps = n >= 2 && (maxV - minV <= 1e-9 || new Set(vals.map(v => Number(v).toFixed(4))).size === 1);
        const cutoff = getTraceCutoff(currentDomain, g.unit);
        const belowFloor = cutoff > 0 && Math.abs(mean) < cutoff;

        const domSlug = window.canonicalDomainSlug ? window.canonicalDomainSlug(g.analysis_type) : String(g.analysis_type || currentDomain).toLowerCase();
        const proxBucket = domSlug === 'proximate' ? proximateComponentBucket(g.parameter) : null;
        const proxStratum = proxBucket
          ? proximateStrataClosure[`${g.resource_name}::${normalizeProxStratumPart(g.experiment)}::${normalizeProxStratumPart(g.prep_method)}`]
          : null;
        const proximateSumPct = proxStratum ? proxStratum.proximate_sum_pct : null;
        const proximateSumFlag = !!(proxStratum && proxStratum.out_of_bounds);

        let dixonQ = null;
        const qCrit = dixonQCrit(n);
        let dixonPass = null;
        let dixonCandidateId = null;
        let dixonCandidateVal = null;
        if (n >= 3) {
          const indexed = g.rows.map(x => ({ v: Number(x.value), id: x.record_id })).sort((a, b) => a.v - b.v);
          const span = indexed[indexed.length - 1].v - indexed[0].v;
          if (span > 1e-12) {
            const qLow = (indexed[1].v - indexed[0].v) / span;
            const qHigh = (indexed[indexed.length - 1].v - indexed[indexed.length - 2].v) / span;
            if (qHigh >= qLow) {
              dixonQ = qHigh;
              dixonCandidateId = indexed[indexed.length - 1].id;
              dixonCandidateVal = indexed[indexed.length - 1].v;
            } else {
              dixonQ = qLow;
              dixonCandidateId = indexed[0].id;
              dixonCandidateVal = indexed[0].v;
            }
            // Guard Dixon outlier flag with rsd !== null && rsd >= 10.0 to match Page 2
            dixonPass = !(dixonQ > qCrit && rsd !== null && rsd >= 10.0);
          } else {
            dixonQ = 0;
            dixonPass = true;
          }
        }

        const sd3xIds = [];
        let maxZ = null;
        const refSd = pooledSd > 1e-12 ? pooledSd : (n >= 3 && sd > 1e-12 ? sd : 0);
        if (n >= 2 && refSd > 1e-12) {
          const zs = [];
          g.rows.forEach(x => {
            const diff = Math.abs(Number(x.value) - mean);
            const z = diff / refSd;
            zs.push(z);
            if (pooledSd > 1e-12 ? (diff > 3.0 * pooledSd) : (n >= 3 && z > 3.0)) {
              sd3xIds.push(x.record_id);
            }
          });
          maxZ = Math.max(...zs);
        }

        const rawTriggers = [];
        if (dixonPass === false) rawTriggers.push('Dixon Q (α=0.05)');
        if (rsd !== null && rsd > 20.0) rawTriggers.push('RSD_within > 20%');
        if (sd3xIds.length > 0) rawTriggers.push('|x - mean| > 3×SD_pooled');
        if (identicalReps) rawTriggers.push('Identical Replicates (SD=0)');
        if (proximateSumFlag) rawTriggers.push(`Proximate Sum (${proximateSumPct.toFixed(1)}% outside 95–105%)`);

        const isFlaggedActive = (!suppressTraceFlags || !belowFloor) && rawTriggers.length > 0;
        const isSuppressedTraceFlag = belowFloor && rawTriggers.length > 0;

        return {
          ...g,
          n,
          mean,
          sd,
          pooled_sd: pooledSd,
          rsd_pct: rsd,
          identical_replicates: identicalReps,
          proximate_sum_pct: proximateSumPct,
          raw_proximate_sum: proximateSumFlag,
          active_proximate_sum: (!suppressTraceFlags || !belowFloor) && proximateSumFlag,
          spread: maxV - minV,
          min_abundance_cutoff: cutoff,
          below_abundance_cutoff: belowFloor,
          dixon_q: dixonQ,
          dixon_q_crit: qCrit,
          dixon_pass: dixonPass,
          dixon_candidate_id: dixonCandidateId,
          dixon_candidate_val: dixonCandidateVal,
          sd3x_candidate_ids: sd3xIds,
          max_z_within: maxZ,
          raw_triggered_tests: rawTriggers,
          is_flagged: isFlaggedActive,
          is_suppressed_trace_flag: isSuppressedTraceFlag
        };
      });

      // Stratify parameter-level Within-Replicate vs Between-Sample RSD by 5-tuple:
      // (resource_name, analysis_type, parameter, prep_method, unit)
      const byParam = {};
      groups.forEach(g => {
        const pKey = `${g.resource_name}::${g.analysis_type}::${g.parameter}::${g.prep_method}::${g.unit}`;
        if (!byParam[pKey]) {
          byParam[pKey] = {
            resource_name: g.resource_name,
            analysis_type: g.analysis_type,
            parameter: g.parameter,
            prep_method: g.prep_method,
            unit: g.unit,
            groups: []
          };
        }
        byParam[pKey].groups.push(g);
      });

      const paramBreakdown = Object.values(byParam).map(pb => {
        const gs = pb.groups;
        const cutoff = getTraceCutoff(currentDomain, pb.unit);
        const withinList = gs
          .filter(x => x.rsd_pct !== null && (!suppressTraceFlags || !x.below_abundance_cutoff))
          .map(x => x.rsd_pct);
        const withinSdList = gs
          .filter(x => x.n >= 2 && (!suppressTraceFlags || !x.below_abundance_cutoff))
          .map(x => x.sd);
        const gMeans = gs.map(x => x.mean);
        const gm = sampleMean(gMeans);
        let betweenSd = null;
        let betweenRsd = null;
        if (gs.length >= 2) {
          betweenSd = sampleSd(gMeans);
          const allBelow = cutoff > 0 && gs.every(x => x.below_abundance_cutoff);
          if (Math.abs(gm) > 1e-9 && (!suppressTraceFlags || !allBelow)) {
            betweenRsd = (betweenSd / Math.abs(gm)) * 100.0;
          }
        }
        gs.forEach(x => {
          x.between_group_sd = betweenSd;
          x.between_group_rsd_pct = betweenRsd;
          x.k_method_groups = gs.length;
        });
        return {
          resource_name: pb.resource_name,
          analysis_type: pb.analysis_type,
          parameter: pb.parameter,
          prep_method: pb.prep_method,
          unit: pb.unit,
          k_groups: gs.length,
          n_groups: gs.length,
          n_multi_rep_groups: gs.filter(x => x.n >= 2).length,
          grand_mean: gm,
          within_sd_median: medianVal(withinSdList),
          within_rsd_mean: withinList.length ? sampleMean(withinList) : null,
          within_rsd_median: medianVal(withinList),
          within_rsd_max: withinList.length ? Math.max(...withinList) : null,
          between_sd: betweenSd,
          between_group_rsd: betweenRsd,
          n_flagged: gs.filter(x => x.is_flagged).length,
          n_trace_suppressed: gs.filter(x => x.is_suppressed_trace_flag).length,
          min_abundance_cutoff: cutoff
        };
      }).sort((a, b) => (b.n_flagged - a.n_flagged) || ((b.within_rsd_max || 0) - (a.within_rsd_max || 0)));

      groups.sort((a, b) => (Number(b.is_flagged) - Number(a.is_flagged)) || ((b.rsd_pct || 0) - (a.rsd_pct || 0)));
      if (!Array.isArray(rowsInput)) {
        lastScreenedGroups = groups;
      }

      const allWithin = paramBreakdown.filter(p => p.within_rsd_median !== null).map(p => p.within_rsd_median);
      const allBetween = paramBreakdown.filter(p => p.between_group_rsd !== null).map(p => p.between_group_rsd);

      return {
        groups,
        paramBreakdown,
        medianWithin: medianVal(allWithin),
        medianBetween: medianVal(allBetween),
        flaggedCount: groups.filter(g => g.is_flagged).length,
        suppressedCount: groups.filter(g => g.is_suppressed_trace_flag).length,
        multiRepCount: groups.filter(g => g.n >= 2).length
      };
    }

    function isExplorerGroupMatchingFlagFilter(g, flagMode) {
      if (!flagMode || flagMode === 'all') return true;
      const isTraceSuppressed = suppressTraceFlags && g.below_abundance_cutoff && g.raw_triggered_tests.length > 0;
      const activeFlag = g.is_flagged && !isTraceSuppressed;
      if (flagMode === 'active' || flagMode === 'flagged') return activeFlag;
      if (flagMode === 'dixon') return !isTraceSuppressed && g.dixon_pass === false;
      if (flagMode === 'rsd20' || flagMode === 'rsd') return !isTraceSuppressed && g.rsd_pct !== null && g.rsd_pct > 20.0;
      if (flagMode === 'sd3x' || flagMode === 'sd3') return !isTraceSuppressed && Array.isArray(g.sd3x_candidate_ids) && g.sd3x_candidate_ids.length > 0;
      if (flagMode === 'identical') return !!g.identical_replicates || (g.n >= 2 && g.sd !== null && g.sd <= 1e-12);
      if (flagMode === 'proximate_sum' || flagMode === 'proximate') return !isTraceSuppressed && !!g.raw_proximate_sum;
      if (flagMode === 'suppressed') return g.below_abundance_cutoff && g.raw_triggered_tests.length > 0;
      if (flagMode === 'clean') return g.n >= 2 && !activeFlag;
      return true;
    }

    function toggleStatDrawer() {
      statDrawerOpen = !statDrawerOpen;
      renderStatScreeningDrawer();
    }

    function toggleSuppressTrace(checked) {
      suppressTraceFlags = !!checked;
      const sidebarChk = document.getElementById('chk-explorer-suppress-trace');
      if (sidebarChk) sidebarChk.checked = suppressTraceFlags;
      applyFilters({ push: false });
    }

    function setStatFilterMode(mode) {
      statFilterMode = mode;
      renderStatScreeningDrawer();
    }

    function pinRecordById(recordId, param) {
      const hit = filteredRows.find(r => r.record_id === recordId && (!param || r.parameter === param))
        || ALL_ROWS.find(r => r.record_id === recordId && (!param || r.parameter === param));
      if (!hit) return;
      pinRecord(hit);
      renderCurrentView();
    }

    function addFlaggedGroupsToExport() {
      const flagged = lastScreenedGroups.filter(g => g.is_flagged);
      flagged.forEach(g => {
        const trigStr = g.raw_triggered_tests.join(' + ');
        g.rows.forEach(r => {
          const isCand = r.record_id === g.dixon_candidate_id || g.sd3x_candidate_ids.includes(r.record_id);
          const notePrefix = isCand ? `[★ Candidate Outlier: ${trigStr}] ` : `[Flagged Group: ${trigStr}] `;
          addRecordToExport(r, notePrefix + (r.note || ''));
        });
      });
      renderStatScreeningDrawer();
    }

    function renderStatScreeningDrawer() {
      const el = document.getElementById('stat-screening-drawer');
      if (!el) return;
      const stats = computeSliceStatScreening();
      const sidebarSupBadge = document.getElementById('explorer-suppressed-count-badge');
      if (sidebarSupBadge) {
        sidebarSupBadge.textContent = `${stats.suppressedCount} suppressed`;
      }
      const sidebarSupChk = document.getElementById('chk-explorer-suppress-trace');
      if (sidebarSupChk) {
        sidebarSupChk.checked = suppressTraceFlags;
      }
      const withinStr = stats.medianWithin !== null ? `${stats.medianWithin.toFixed(1)}%` : 'Singleton (n=1)';
      const betweenStr = stats.medianBetween !== null ? `${stats.medianBetween.toFixed(1)}%` : 'N/A (n=1 method group)';

      const flagBadge = stats.flaggedCount > 0
        ? `<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/15 text-amber-600 dark:text-amber-300 border border-amber-500/30">⚑ ${stats.flaggedCount} Flagged Replicate Group${stats.flaggedCount === 1 ? '' : 's'}</span>`
        : `<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 border border-emerald-500/30">✓ 0 Flagged Replicate Groups</span>`;

      const traceBadge = stats.suppressedCount > 0
        ? `<span class="px-2 py-0.5 rounded-full text-[11px] font-mono bg-[var(--card)] text-[var(--muted-foreground)] border border-[var(--border)]">${stats.suppressedCount} trace group${stats.suppressedCount === 1 ? '' : 's'} suppressed (&lt;100 ppm / &lt;0.5%)</span>`
        : '';

      let bodyHtml = '';
      if (statDrawerOpen) {
        const paramRowsHtml = stats.paramBreakdown.slice(0, 24).map(p => {
          const meanWithinSd = (p.grand_mean !== null && p.within_sd_median !== null)
            ? `${p.grand_mean.toFixed(2)} ± ${p.within_sd_median.toFixed(2)}`
            : (p.grand_mean !== null ? `${p.grand_mean.toFixed(2)} ± —` : '—');
          const wMed = p.within_rsd_median !== null ? `${p.within_rsd_median.toFixed(1)}%` : '—';
          const wMax = p.within_rsd_max !== null ? `${p.within_rsd_max.toFixed(1)}%` : '—';
          const bSd = (p.k_groups >= 2 && p.between_sd !== null) ? p.between_sd.toFixed(2) : '<span class="text-[var(--muted-foreground)]">N/A (n=1 method group)</span>';
          const bRsd = (p.k_groups >= 2 && p.between_group_rsd !== null) ? `${p.between_group_rsd.toFixed(1)}%` : '<span class="text-[var(--muted-foreground)] font-normal">N/A (n=1 method group)</span>';
          const resLabel = explorerBlindMode ? 'Masked Resource' : `${p.resource_name} · ${p.prep_method}`;
          return `
            <tr class="border-b border-[var(--border)]">
              <td class="py-1 px-2 font-mono text-[11px] text-[var(--muted-foreground)]">${escapeHtml(resLabel)}</td>
              <td class="py-1 px-2 font-mono font-semibold text-[var(--foreground)]">${formatParamName(p.parameter, currentDomain)} <span class="text-[var(--muted-foreground)] font-normal">(${p.unit || '—'})</span></td>
              <td class="py-1 px-2 text-right font-mono">${p.n_multi_rep_groups} / ${p.k_groups}</td>
              <td class="py-1 px-2 text-right font-mono">${meanWithinSd}</td>
              <td class="py-1 px-2 text-right font-mono font-semibold">${wMed} <span class="text-[var(--muted-foreground)] font-normal">(max ${wMax})</span></td>
              <td class="py-1 px-2 text-right font-mono">${bSd}</td>
              <td class="py-1 px-2 text-right font-mono font-semibold text-[#00B5E2]">${bRsd}</td>
            </tr>
          `;
        }).join('');

        const shownGroups = stats.groups.filter(g => statFilterMode === 'all' ? g.n >= 2 : g.is_flagged).slice(0, 40);
        const groupRowsHtml = shownGroups.map((g, gIdx) => {
          const repBadges = g.rows.map(r => {
            const isCand = r.record_id === g.dixon_candidate_id || g.sd3x_candidate_ids.includes(r.record_id);
            const cls = isCand
              ? 'px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-600 dark:text-amber-300 border border-amber-500/40 font-mono font-bold hover:opacity-80'
              : 'px-1.5 py-0.5 rounded bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] font-mono hover:border-[#00B5E2]';
            const star = isCand ? ' ★' : '';
            return `<button onclick="pinRecordById('${r.record_id}', '${g.parameter}')" class="${cls}" title="Click to pin ${r.record_id} on plot">Rep ${r.replicate ?? 1}: ${Number(r.value).toFixed(2)}${star}</button>`;
          }).join(' ');

          const trigBadges = [];
          const allowFlag = !g.below_abundance_cutoff || !suppressTraceFlags;
          if (g.dixon_pass === false && allowFlag) {
            trigBadges.push(`<span class="px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-600 dark:text-rose-300 border border-rose-500/30 font-mono" title="Dixon Q=${g.dixon_q.toFixed(2)} > Q_crit=${g.dixon_q_crit.toFixed(2)}">⚑ Dixon Outlier</span>`);
          }
          if (g.rsd_pct !== null && g.rsd_pct > 20 && allowFlag) {
            trigBadges.push(`<span class="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-300 border border-amber-500/30 font-mono" title="Within-group RSD=${g.rsd_pct.toFixed(1)}%">⚑ RSD &gt; 20%</span>`);
          }
          if (g.sd3x_candidate_ids.length > 0 && allowFlag) {
            trigBadges.push(`<span class="px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-600 dark:text-purple-300 border border-purple-500/30 font-mono" title="Exceeds 3×Pooled SD (${(g.pooled_sd || 0).toFixed(3)})">⚑ &gt;3×SD_pooled</span>`);
          }
          if (g.identical_replicates && allowFlag) {
            trigBadges.push(`<span class="px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-600 dark:text-cyan-300 border border-cyan-500/30 font-mono" title="Zero variance across n>=2 replicates">⚑ Identical Replicates</span>`);
          }
          if (g.raw_proximate_sum && allowFlag) {
            const pSumStr = g.proximate_sum_pct !== null && g.proximate_sum_pct !== undefined ? `${g.proximate_sum_pct.toFixed(1)}%` : 'outside 95–105%';
            trigBadges.push(`<span class="px-1.5 py-0.5 rounded bg-orange-500/15 text-orange-600 dark:text-orange-300 border border-orange-500/30 font-mono" title="Data Portal proximate_sum = ${pSumStr} (outside 95–105%)">⚑ Proximate Sum</span>`);
          }
          if (g.below_abundance_cutoff && g.raw_triggered_tests.length > 0) {
            trigBadges.push(`<span class="px-1.5 py-0.5 rounded bg-[var(--card)] text-[var(--muted-foreground)] border border-[var(--border)] font-mono">Trace (&lt;${g.min_abundance_cutoff} ${g.unit})</span>`);
          }
          const hasActiveFlagBadge = trigBadges.length > 0;
          if (!trigBadges.length) {
            trigBadges.push(`<span class="text-emerald-600 dark:text-emerald-400 font-mono">Pass (Q=${g.dixon_q !== null ? g.dixon_q.toFixed(2) : '—'})</span>`);
          }
          if (hasActiveFlagBadge || g.is_flagged) {
            const safeShowKey = String(g.replicate_group_key || g.group_key || "").replace(/"/g, "&quot;").replace(/'/g, "\\'");
            const safeShowRes = String(g.resource_name || "").replace(/"/g, "&quot;").replace(/'/g, "\\'");
            const safeShowAt = String(g.analysis_type || currentDomain || "").replace(/"/g, "&quot;").replace(/'/g, "\\'");
            const safeShowParam = String(g.parameter || "").replace(/"/g, "&quot;").replace(/'/g, "\\'");
            const safeShowSample = String(g.prepared_sample || "").replace(/"/g, "&quot;").replace(/'/g, "\\'");
            const safeShowCand = String(g.dixon_candidate_id || (g.sd3x_candidate_ids && g.sd3x_candidate_ids[0]) || "").replace(/"/g, "&quot;").replace(/'/g, "\\'");
            trigBadges.push(`<button type="button" class="btn-show-me-flag px-1.5 py-0.5 rounded text-[10px] font-semibold bg-[var(--card)] text-[#00B5E2] border border-[#00B5E2]/40 hover:bg-[#00B5E2]/10 transition" data-group-key="${safeShowKey}" onclick="event.stopPropagation(); window.openFlagShowMePopover && window.openFlagShowMePopover({ replicateGroupKey: '${safeShowKey}', resource: '${safeShowRes}', analysisType: '${safeShowAt}', parameter: '${safeShowParam}', preparedSample: '${safeShowSample}', outlierRecordId: '${safeShowCand}' }, this)" title="Show flagged replicate group and outlier in slice context">👁 Show me</button>`);
          }

          const targetId = g.dixon_candidate_id || (g.rows[0] && g.rows[0].record_id) || '';
          const sampleLabel = explorerBlindMode ? `Masked Sample #${gIdx + 1}` : g.prepared_sample;
          const subLabel = explorerBlindMode ? 'Blind Review Mode' : `${g.resource_name} · ${g.method_label}`;
          const betweenCellStr = (g.k_method_groups >= 2 && g.between_group_rsd_pct !== null && g.between_group_rsd_pct !== undefined)
            ? `${g.between_group_rsd_pct.toFixed(1)}%`
            : 'N/A (n=1 method group)';
          return `
            <tr class="border-b border-[var(--border)]">
              <td class="py-1.5 px-2 font-mono font-semibold text-[#00B5E2]">${escapeHtml(sampleLabel)}<div class="text-[10px] font-sans font-normal text-[var(--muted-foreground)]">${escapeHtml(subLabel)}</div></td>
              <td class="py-1.5 px-2 font-mono font-semibold">${formatParamName(g.parameter, currentDomain)} <span class="text-[var(--muted-foreground)] font-normal">(${g.unit})</span></td>
              <td class="py-1.5 px-2"><div class="flex flex-wrap gap-1">${repBadges}</div></td>
              <td class="py-1.5 px-2 text-right font-mono">${g.mean.toFixed(2)} ± ${g.sd.toFixed(2)}</td>
              <td class="py-1.5 px-2 text-right font-mono font-semibold ${g.rsd_pct > 20 ? 'text-amber-600 dark:text-amber-300' : ''}">${g.rsd_pct !== null ? g.rsd_pct.toFixed(1) + '%' : '—'} <span class="text-[var(--muted-foreground)] font-normal">/ ${betweenCellStr}</span></td>
              <td class="py-1.5 px-2"><div class="flex flex-wrap gap-1">${trigBadges.join(' ')}</div></td>
              <td class="py-1.5 px-2 text-right"><button onclick="pinRecordById('${targetId}', '${g.parameter}')" class="px-2 py-0.5 rounded bg-[var(--card)] hover:border-[#00B5E2] border border-[var(--border)] text-[var(--foreground)] font-medium">Pin</button></td>
            </tr>
          `;
        }).join('');

        // Section 3: Resource Lab & Sample Lineage Notes
        const activeResourceNames = Array.from(new Set(filteredRows.map(r => r.resource_name).filter(Boolean)));
        const activePrepNames = Array.from(new Set(filteredRows.map(r => r.prepared_sample_name).filter(Boolean)));
        const activeFieldNames = Array.from(new Set(filteredRows.map(r => r.field_sample_name).filter(Boolean)));

        const resourceNoteItems = [];
        activeResourceNames.forEach((rn, idx) => {
          const meta = (typeof RESOURCES_BY_NAME !== 'undefined' && RESOURCES_BY_NAME[rn]) ? RESOURCES_BY_NAME[rn] : null;
          if (!meta) return;
          const noteText = [meta.lab_notes, meta.notes, meta.description, meta.processing_notes]
            .filter(x => x && String(x).trim() && String(x).trim() !== 'None')
            .join(' · ');
          if (noteText) {
            const label = explorerBlindMode ? `Masked Resource #${idx + 1}` : rn;
            resourceNoteItems.push(`<div class="p-2 rounded border border-[var(--border)] bg-[var(--card)]"><span class="font-mono font-semibold text-[#00B5E2]">${escapeHtml(label)}</span> <span class="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-[#00B5E2]/10 text-[#00B5E2] ml-1">Resource Lab Notes</span><div class="mt-1 text-[var(--foreground)]">${escapeHtml(noteText)}</div></div>`);
          }
        });

        const prepNoteItems = [];
        activePrepNames.forEach((pn, idx) => {
          const pMeta = (typeof PREP_SAMPLES_BY_NAME !== 'undefined' && PREP_SAMPLES_BY_NAME[pn]) ? PREP_SAMPLES_BY_NAME[pn] : null;
          const rowNotes = Array.from(new Set(filteredRows.filter(r => r.prepared_sample_name === pn).map(r => r.prep_notes || r.sample_note).filter(Boolean)));
          const noteParts = [];
          if (pMeta) {
            [pMeta.notes, pMeta.prep_notes, pMeta.description, pMeta.prep_method].filter(x => x && String(x).trim() && String(x).trim() !== 'None').forEach(x => noteParts.push(String(x).trim()));
          }
          rowNotes.forEach(x => { if (!noteParts.includes(String(x).trim())) noteParts.push(String(x).trim()); });
          if (noteParts.length > 0) {
            const label = explorerBlindMode ? `Masked Prep Sample #${idx + 1}` : pn;
            prepNoteItems.push(`<div class="p-2 rounded border border-[var(--border)] bg-[var(--card)]"><span class="font-mono font-semibold text-emerald-500">${escapeHtml(label)}</span> <span class="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-500 ml-1">Preparation Lineage</span><div class="mt-1 text-[var(--foreground)]">${escapeHtml(noteParts.join(' · '))}</div></div>`);
          }
        });

        const fieldNoteItems = [];
        activeFieldNames.forEach((fn, idx) => {
          const fMeta = (typeof FIELD_SAMPLES_BY_NAME !== 'undefined' && FIELD_SAMPLES_BY_NAME[fn]) ? FIELD_SAMPLES_BY_NAME[fn] : null;
          if (!fMeta) return;
          const noteParts = [fMeta.notes, fMeta.field_notes, fMeta.collection_notes, fMeta.sample_source, fMeta.county]
            .filter(x => x && String(x).trim() && String(x).trim() !== 'None');
          if (noteParts.length > 0) {
            const label = explorerBlindMode ? `Masked Field Sample #${idx + 1}` : fn;
            fieldNoteItems.push(`<div class="p-2 rounded border border-[var(--border)] bg-[var(--card)]"><span class="font-mono font-semibold text-amber-500">${escapeHtml(label)}</span> <span class="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-500 ml-1">Field Sample Lineage</span><div class="mt-1 text-[var(--foreground)]">${escapeHtml(noteParts.join(' · '))}</div></div>`);
          }
        });

        const obsWithNotes = filteredRows.filter(r => r.note && String(r.note).trim() && String(r.note).trim() !== 'None').slice(0, 12);
        const obsNoteItems = obsWithNotes.map((r, idx) => {
          const sLabel = explorerBlindMode ? `Masked Obs #${idx + 1}` : `${r.resource_name} · ${r.prepared_sample_name || r.field_sample_name || r.record_id}`;
          return `<div class="p-2 rounded border border-[var(--border)] bg-[var(--card)]"><span class="font-mono font-semibold text-purple-400">${escapeHtml(sLabel)}</span> <span class="font-mono text-[10px] text-[var(--muted-foreground)] ml-1">(${escapeHtml(r.parameter || 'obs')})</span><div class="mt-1 text-[var(--foreground)]">${escapeHtml(String(r.note).trim())}</div></div>`;
        });

        const allNotesCombined = [...resourceNoteItems, ...prepNoteItems, ...fieldNoteItems, ...obsNoteItems];
        const labNotesHtml = allNotesCombined.length > 0
          ? `<div class="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-[200px] overflow-y-auto p-2 rounded border border-[var(--border)] bg-[var(--background)]">${allNotesCombined.join('')}</div>`
          : `<div class="p-3 rounded border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)]">No lab, preparation, or field lineage notes recorded for the active resource slice (${activeResourceNames.length} resource${activeResourceNames.length === 1 ? '' : 's'}).</div>`;

        bodyHtml = `
          <div class="p-3 border-t border-[var(--border)] bg-[var(--card)] space-y-3 text-xs">
            <div class="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[var(--border)]">
              <div class="text-[var(--muted-foreground)]">
                Screens canonical 6-part replicate groups (<span class="font-mono">Resource × Analysis × Sample × Method × Parameter × Unit</span>) using <strong class="text-[var(--foreground)]">Dixon's Q-Test (α=0.05, n≥3, RSD≥10%)</strong>, <strong class="text-[var(--foreground)]">Within-Group RSD &gt; 20%</strong>, <strong class="text-[var(--foreground)]">|x − mean| &gt; 3×SD_pooled</strong>, <strong class="text-[var(--foreground)]">Identical Replicates (SD=0)</strong>, and <strong class="text-[var(--foreground)]">Proximate Sum (Outside 95–105%)</strong>.
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <label class="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-[var(--background)] border border-[var(--border)] cursor-pointer">
                  <input type="checkbox" ${suppressTraceFlags ? 'checked' : ''} onchange="toggleSuppressTrace(this.checked)" class="rounded" />
                  <span>Suppress trace flags (&lt;100 ppm ICP/XRF, &lt;0.5% wt / g/L)</span>
                </label>
                <div class="inline-flex rounded border border-[var(--border)] bg-[var(--background)] p-0.5">
                  <button onclick="setStatFilterMode('flagged')" class="px-2 py-0.5 rounded ${statFilterMode === 'flagged' ? 'bg-[#00B5E2] text-slate-950 font-semibold' : 'text-[var(--muted-foreground)]'}">Flagged (${stats.flaggedCount})</button>
                  <button onclick="setStatFilterMode('all')" class="px-2 py-0.5 rounded ${statFilterMode === 'all' ? 'bg-[#00B5E2] text-slate-950 font-semibold' : 'text-[var(--muted-foreground)]'}">All Multi-Rep (${stats.multiRepCount})</button>
                </div>
              </div>
            </div>

            <!-- Section 1: Within-Replicate vs. Between-Sample RSD Summary -->
            <div>
              <div class="font-semibold text-[var(--foreground)] mb-1">1. Within-Replicate vs. Between-Sample RSD Summary</div>
              <div class="mb-2 px-2.5 py-1.5 rounded border border-[var(--border)] bg-[var(--background)] font-mono text-[11px] text-[var(--muted-foreground)] flex flex-wrap gap-x-4 gap-y-1">
                <span><strong class="text-[var(--foreground)]">Within-Replicate RSD</strong> = SD_within / |Mean_group| × 100%</span>
                <span><strong class="text-[var(--foreground)]">Pooled SD</strong> = sqrt(Σ(n_g - 1)s_g² / Σ(n_g - 1))</span>
                <span><strong class="text-[#00B5E2]">Between-Sample RSD</strong> = SD(group means) / |Grand Mean| × 100% <span class="text-[10px]">(stratified by resource, analysis_type, parameter, prep_method, unit)</span></span>
              </div>
              <div class="overflow-x-auto max-h-[190px] overflow-y-auto border border-[var(--border)] rounded bg-[var(--background)]">
                <table class="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr class="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                      <th class="py-1 px-2">Resource &amp; Method</th>
                      <th class="py-1 px-2">Parameter (Unit)</th>
                      <th class="py-1 px-2 text-right">Replicate Groups</th>
                      <th class="py-1 px-2 text-right">Mean ± Within SD</th>
                      <th class="py-1 px-2 text-right">Within RSD%</th>
                      <th class="py-1 px-2 text-right">Between-Sample SD</th>
                      <th class="py-1 px-2 text-right">Between-Sample RSD%</th>
                    </tr>
                  </thead>
                  <tbody>${paramRowsHtml || '<tr><td colspan="7" class="py-3 text-center text-[var(--muted-foreground)]">No numeric parameter groups in current slice.</td></tr>'}</tbody>
                </table>
              </div>
            </div>

            <!-- Section 2: Flagged Replicate Groups -->
            <div>
              <div class="font-semibold text-[var(--foreground)] mb-1">2. Flagged Replicate Groups ${statFilterMode === 'all' ? '(Showing All Multi-Replicate Groups)' : '&amp; Candidate Outlier Replicates (★)'}</div>
              ${shownGroups.length === 0 ? `<div class="p-3 rounded border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)]">✓ Zero replicate groups triggered candidate outlier flags under current filter settings.</div>` : `
              <div class="overflow-x-auto max-h-[240px] overflow-y-auto border border-[var(--border)] rounded bg-[var(--background)]">
                <table class="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr class="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                      <th class="py-1 px-2">Prepared Sample / Resource</th>
                      <th class="py-1 px-2">Parameter</th>
                      <th class="py-1 px-2">Replicate Values (Click to Pin on Plot · ★ = Extreme Candidate)</th>
                      <th class="py-1 px-2 text-right">Mean ± SD</th>
                      <th class="py-1 px-2 text-right">Within / Between RSD</th>
                      <th class="py-1 px-2">Triggered Screens</th>
                      <th class="py-1 px-2 text-right">Inspect</th>
                    </tr>
                  </thead>
                  <tbody>${groupRowsHtml}</tbody>
                </table>
              </div>`}
            </div>

            <!-- Section 3: Resource Lab & Sample Lineage Notes -->
            <div id="explorer-lab-notes-panel">
              <div class="font-semibold text-[var(--foreground)] mb-1">3. Resource Lab &amp; Sample Lineage Notes</div>
              ${labNotesHtml}
            </div>
          </div>
        `;
      }

      el.innerHTML = `
        <div class="rounded-lg border border-[var(--border)] bg-[var(--background)] overflow-hidden">
          <div onclick="toggleStatDrawer()" class="px-3 py-2 flex flex-wrap items-center justify-between gap-2 cursor-pointer hover:bg-[var(--secondary)]/30 transition-colors">
            <div class="flex flex-wrap items-center gap-2">
              <span class="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-[#00B5E2]/15 text-[#00B5E2] font-semibold">Statistical Snapshot</span>
              <span class="text-xs font-semibold text-[var(--foreground)]">Replicate Precision &amp; Candidate Outlier Screening</span>
              <span class="text-[11px] font-mono text-[var(--muted-foreground)]">Within-RSD: <strong class="text-[var(--foreground)]">${withinStr}</strong> · Between-RSD: <strong class="text-[#00B5E2]">${betweenStr}</strong></span>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              ${flagBadge}
              ${traceBadge}
              <span class="px-2 py-0.5 rounded border border-[var(--border)] bg-[var(--card)] text-[11px] font-medium text-[var(--foreground)]">${statDrawerOpen ? '▾ Hide Screening' : '▸ Expand Flagged Samples & RSD Table'}</span>
            </div>
          </div>
          ${bodyHtml}
        </div>
      `;
    }

    function addClickPopoverToExport() {
      if (!pinnedRecord) return;
      const noteInput = document.getElementById('click-popover-note');
      const note = (noteInput && noteInput.value ? noteInput.value.trim() : '');
      const targetRows = (auditPopoverScope === 'group' && pinnedGroupRows && pinnedGroupRows.length) ? pinnedGroupRows : [pinnedRecord];
      targetRows.forEach(tr => addRecordToExport(tr, note));
      if (noteInput) noteInput.value = '';
      const fb = document.getElementById('click-popover-feedback');
      if (fb) {
        fb.textContent = `✓ Added ${targetRows.length} observation${targetRows.length === 1 ? '' : 's'} to Export Tray`;
        fb.classList.remove('hidden');
      }
    }

    function addPinnedToExport() {
      if (!pinnedRecord) return;
      const scope = (document.getElementById('pin-audit-scope') || {}).value || 'group';
      const noteInput = document.getElementById('pin-note');
      const note = (noteInput && noteInput.value ? noteInput.value.trim() : '');
      const targetRows = (scope === 'group' && pinnedGroupRows && pinnedGroupRows.length) ? pinnedGroupRows : [pinnedRecord];
      targetRows.forEach(tr => addRecordToExport(tr, note));
      if (noteInput) noteInput.value = '';
      const fb = document.getElementById('pin-audit-feedback');
      if (fb) {
        fb.textContent = `✓ Added ${targetRows.length} observation${targetRows.length === 1 ? '' : 's'} to Export Tray`;
        fb.classList.remove('hidden');
      }
    }

    function addRecordToExport(r, auditNote) {
      const key = `${r.record_id}::${r.parameter}`;
      if (!exportRows.some(e => `${e.record_id}::${e.parameter}` === key)) {
        exportRows.push({
          ...r,
          audit_note: auditNote || r.note || ''
        });
        const cntEl = document.getElementById('tray-count');
        if (cntEl) cntEl.textContent = exportRows.length;
      }
    }

    function addFilteredSliceToExport() {
      filteredRows.slice(0, 250).forEach(r => addRecordToExport(r, ''));
      renderExportTable();
    }

    function copyRecordId() {
      if (!pinnedRecord) return;
      navigator.clipboard.writeText(pinnedRecord.record_id);
      const btn = document.getElementById('btn-copy-id');
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.textContent = 'Copy ID'; }, 1200);
    }

    function renderExportTable() {
      const tbody = document.getElementById('export-tbody');
      if (!tbody) return;
    }

    function removeExportRow(idx) {
      exportRows.splice(idx, 1);
      const cntEl = document.getElementById('tray-count');
      if (cntEl) cntEl.textContent = exportRows.length;
      renderExportTable();
    }

    function clearExport() {
      exportRows = [];
      const cntEl = document.getElementById('tray-count');
      if (cntEl) cntEl.textContent = '0';
      renderExportTable();
    }

    function toggleTheme() {
      currentTheme = currentTheme === 'light' ? 'dark' : 'light';
      const isLight = currentTheme === 'light';
      document.documentElement.setAttribute('data-user-theme', currentTheme);
      document.body.setAttribute('data-user-theme', currentTheme);
      document.documentElement.setAttribute('data-theme', currentTheme);
      document.documentElement.classList.toggle('light', isLight);
      document.documentElement.classList.toggle('dark', !isLight);
      document.getElementById('btn-theme').textContent = isLight ? '🌙 Dark' : '☀️ Light';
      renderDomainPills();
      renderCurrentView();
    }

__SHARED_SLICE_AND_BUG_MODALS_JS__

    async function exportExplorerTrayToWorkbench() {
      const sourceRows = (exportRows && exportRows.length)
        ? exportRows
        : ((pinnedGroupRows && pinnedGroupRows.length)
            ? pinnedGroupRows
            : (pinnedRecord ? [pinnedRecord] : filteredRows.slice(0, 25)));
      if (!sourceRows || !sourceRows.length) return;
      const items = sourceRows.map(r => ({
        scope: 'replicate_group',
        resource_name: r.resource_name || '',
        analysis_type: r.analysis_type || currentDomain || '',
        parameter: r.parameter || '',
        parameter_name: r.parameter || '',
        prepared_sample_name: r.prepared_sample_name || r.prepared_sample || '',
        field_sample_name: r.field_sample_name || '',
        method_or_strain: getSeriesValue(r, r.domain || currentDomain) || '',
        experiment_name: r.experiment || '',
        record_id: String(r.record_id || ''),
        record_ids: [String(r.record_id || '')],
        replicates: [{
          record_id: String(r.record_id || ''),
          value: r.value,
          unit: r.unit || '',
          qc_status: r.qc_pass || 'pass'
        }],
        review_note: r.audit_note || 'Exported from Interactive Data Visualizer to Audit Workbench',
        note: r.audit_note || 'Exported from Interactive Data Visualizer to Audit Workbench'
      }));
      if (window.BioCirvQcClient && typeof window.BioCirvQcClient.exportTrayToWorkbench === 'function') {
        const res = await window.BioCirvQcClient.exportTrayToWorkbench(items, 'Page 3 — Interactive Data Visualizer');
        const btn = document.getElementById('btn-tray-to-workbench');
        if (btn) {
          const orig = btn.textContent;
          btn.textContent = `✓ Sent (${res.persisted || items.length}) to Audit Workbench`;
          setTimeout(() => { btn.textContent = orig; }, 2200);
        }
      }
    }

    initSliceAndBugModals("Page 3 — Interactive Data Visualizer");
    window.addEventListener('resize', () => renderCurrentView());
    window.addEventListener('popstate', () => {
      urlParams = new URLSearchParams(window.location.search);
      const rawDom = urlParams.get('type') || urlParams.get('domain') || urlParams.get('tab') || 'proximate';
      currentDomain = normalizeDomainKey(rawDom);
      if (!DOMAINS.some(d => d.id === currentDomain)) currentDomain = 'proximate';
      selectedFilters.resources.clear();
      selectedFilters.samples.clear();
      selectedFilters.params.clear();
      selectedFilters.methods.clear();
      initFromUrlParams();
      onResourceOrDomainChange(false, { push: false });
    });
    initFromUrlParams();
    onResourceOrDomainChange(true);
    if (typeof window.refreshLiveQcOverlay === 'function') {
      window.refreshLiveQcOverlay(false);
    }
  </script>
</body>
</html>
"""
    return (
        template.replace("__PAYLOAD_JSON__", payload_json)
        .replace("__SHARED_SLICE_AND_BUG_MODALS_HTML__", SHARED_SLICE_AND_BUG_MODALS_HTML)
        .replace("__SHARED_SLICE_AND_BUG_MODALS_JS__", SHARED_SLICE_AND_BUG_MODALS_JS)
    )


def build_quick_widget_html(payload: dict) -> str:
    """Build the compact 12-column HTML5 Canvas Quick Resource Explorer Widget."""
    slim_payload = {
        "generated_utc": payload.get("generated_utc", ""),
        "str_cols": payload["str_cols"],
        "dicts": payload["dicts"],
        "rows": payload["rows"],
        "resources": payload.get("resources", []),
        "excluded_resources": payload.get("excluded_resources", []),
        "excluded_providers": payload.get("excluded_providers", []),
    }
    widget_payload = json.dumps(slim_payload, separators=(",", ":"))
    template = """<!DOCTYPE html>
<html lang="en" class="dark" data-theme="dark" data-user-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BioCirV — Quick Resource Canvas Widget</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root, html[data-user-theme="dark"], body[data-user-theme="dark"] {
      --background: #0f172a;
      --card: #1e293b;
      --foreground: #f8fafc;
      --muted-foreground: #94a3b8;
      --primary: #00B5E2;
      --primary-foreground: #0f172a;
      --secondary: #334155;
      --secondary-foreground: #f8fafc;
      --border: #334155;
      color-scheme: dark;
    }
    html[data-user-theme="light"], body[data-user-theme="light"] {
      --background: #f8fafc;
      --card: #ffffff;
      --foreground: #0f172a;
      --muted-foreground: #475569;
      --primary: #00B5E2;
      --primary-foreground: #0f172a;
      --secondary: #e2e8f0;
      --secondary-foreground: #0f172a;
      --border: #cbd5e1;
      color-scheme: light;
    }
    body {
      background-color: var(--background);
      color: var(--foreground);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    select {
      background-color: var(--background);
      color: var(--foreground);
      border-color: var(--border);
    }
    .bg-\\[var\\(--background\\)\\] { background-color: var(--background) !important; }
    .bg-\\[var\\(--card\\)\\] { background-color: var(--card) !important; }
    .bg-\\[var\\(--primary\\)\\] { background-color: var(--primary) !important; }
    .bg-\\[var\\(--secondary\\)\\] { background-color: var(--secondary) !important; }
    .text-\\[var\\(--foreground\\)\\] { color: var(--foreground) !important; }
    .text-\\[var\\(--muted-foreground\\)\\] { color: var(--muted-foreground) !important; }
    .text-\\[var\\(--primary-foreground\\)\\] { color: var(--primary-foreground) !important; }
    .text-\\[var\\(--secondary-foreground\\)\\] { color: var(--secondary-foreground) !important; }
    .border-\\[var\\(--border\\)\\] { border-color: var(--border) !important; }
  </style>
</head>
<body data-user-theme="dark" class="bg-[var(--background)] text-[var(--foreground)] antialiased p-2 select-none">
  <div class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-xl p-3 shadow-sm max-w-4xl mx-auto">
    <!-- Top Header -->
    <div class="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[var(--border)]">
      <div class="flex items-center gap-2">
        <div class="w-2.5 h-2.5 rounded-full bg-[#00B5E2]"></div>
        <h2 class="text-sm font-semibold tracking-tight">BioCirV Quick Resource Widget</h2>
        <span id="w-badge-count" class="text-xs px-2 py-0.5 rounded-full bg-[var(--secondary)] text-[var(--secondary-foreground)] font-medium">906 obs</span>
      </div>
      <div class="flex items-center gap-1.5">
        <div class="flex items-center gap-1 bg-[var(--background)] p-0.5 rounded-lg border border-[var(--border)]">
          <button id="w-tab-scatter" onclick="setWidgetTab('scatter')" class="text-xs px-2 py-0.5 rounded font-medium bg-[var(--primary)] text-[var(--primary-foreground)]">Scatter</button>
          <button id="w-tab-strip" onclick="setWidgetTab('strip')" class="text-xs px-2 py-0.5 rounded font-medium text-[var(--muted-foreground)]">Strip</button>
        </div>
        <a href="resource_explorer_dashboard.html" class="text-xs px-2 py-1 rounded border border-[var(--border)] bg-[var(--background)] text-[#00B5E2] font-medium hover:underline">Full Suite &rarr;</a>
        <button id="w-theme-btn" onclick="toggleWidgetTheme()" class="text-xs px-2 py-1 rounded border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)]">☀️ Light</button>
      </div>
    </div>

    <!-- Single-Row Filter Bar -->
    <div class="flex flex-wrap items-center gap-2 py-1.5 border-b border-[var(--border)] text-xs">
      <div class="flex items-center gap-1">
        <span class="text-[var(--muted-foreground)] font-medium">Analysis:</span>
        <select id="w-domain" onchange="onWidgetDomainOrResourceChange()" class="rounded px-1.5 py-0.5 border border-[var(--border)] text-xs">
          <option value="proximate" selected>Proximate</option>
          <option value="calorimetry">Calorimetry</option>
          <option value="compositional">Compositional</option>
          <option value="ultimate">Ultimate</option>
          <option value="xrd">XRD</option>
          <option value="icp">ICP</option>
          <option value="xrf">XRF</option>
          <option value="pretreatment">Pretreatment</option>
          <option value="fermentation">Fermentation</option>
          <option value="gasification">Gasification</option>
        </select>
      </div>
      <div class="flex items-center gap-1">
        <span class="text-[var(--muted-foreground)] font-medium">Resource:</span>
        <select id="w-resource" onchange="onWidgetDomainOrResourceChange()" class="rounded px-1.5 py-0.5 border border-[var(--border)] text-xs max-w-[160px]"></select>
      </div>
      <div class="flex items-center gap-1">
        <span class="text-[var(--muted-foreground)] font-medium">Sample:</span>
        <select id="w-sample" onchange="applyWidgetFilters()" class="rounded px-1.5 py-0.5 border border-[var(--border)] text-xs max-w-[145px]"></select>
      </div>
      <div class="flex items-center gap-1">
        <span class="text-[var(--muted-foreground)] font-medium">Status / QC:</span>
        <select id="w-qc" onchange="applyWidgetFilters()" class="rounded px-1.5 py-0.5 border border-[var(--border)] text-xs">
          <option value="ALL">All Statuses &amp; QC</option>
          <option value="Portal Compliant">Portal Compliant</option>
          <option value="Raw">Raw / Portal Excluded</option>
          <option value="pass" selected>qc_pass: pass</option>
          <option value="fail">qc_pass: fail</option>
        </select>
      </div>
    </div>

    <!-- Compact 12-Column Canvas + Inspector -->
    <div class="grid grid-cols-12 gap-2.5 pt-2 items-start">
      <div class="col-span-8 bg-[var(--background)] border border-[var(--border)] rounded-lg p-2 relative">
        <canvas id="w-canvas" width="460" height="265" style="width: 100%; height: 265px;" class="w-full h-[265px] cursor-crosshair block"></canvas>
        <div id="w-tooltip" class="hidden pointer-events-none absolute z-20 bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-lg p-1.5 shadow-lg text-xs max-w-[210px]"></div>
      </div>
      <div class="col-span-4 flex flex-col gap-1.5">
        <div id="w-kpis" class="grid grid-cols-1 gap-1.5"></div>
        <div class="bg-[var(--background)] border border-[#00B5E2]/60 rounded-lg p-2">
          <div class="text-xs font-semibold mb-1">Pinned Record</div>
          <div id="w-pinned" class="text-xs text-[var(--muted-foreground)] space-y-0.5 min-h-[82px]">
            Click any point on the canvas to inspect record details.
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const RAW_DATA = __WIDGET_PAYLOAD__;
    const PALETTE = ['#00B5E2', '#f59e0b', '#10b981', '#ec4899', '#8b5cf6'];
    const FERM_CARBON_FLOW_ORDER = [
      'sugar_cons', 'sugart0', 'gluconct0', 'xylconct0',
      'sugarteof', 'gluconcteof', 'xylconcteof',
      'od600teof', 'rel_growth',
      '3hptiter', '3hpyield', '3hpyield_pct',
      'etohtiter', 'etohyield', 'etohyield_pct'
    ];
    const FERM_PARAM_LABELS = { '3hpyield': '3hpyield_pct', 'etohyield': 'etohyield_pct' };
    const CHEMICAL_SYMBOLS = new Set([
      'H','He','Li','Be','B','C','N','O','F','Ne','Na','Mg','Al','Si','P','S','Cl','Ar',
      'K','Ca','Sc','Ti','V','Cr','Mn','Fe','Co','Ni','Cu','Zn','Ga','Ge','As','Se','Br','Kr',
      'Rb','Sr','Y','Zr','Nb','Mo','Tc','Ru','Rh','Pd','Ag','Cd','In','Sn','Sb','Te','I','Xe',
      'Cs','Ba','La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu',
      'Hf','Ta','W','Re','Os','Ir','Pt','Au','Hg','Tl','Pb','Bi','Po','At','Rn'
    ]);
    function formatElementSymbol(sym) {
      if (!sym || sym === '(metadata only)') return sym;
      const trimmed = String(sym).trim();
      if (trimmed.length >= 1 && trimmed.length <= 2) {
        const candidate = trimmed.charAt(0).toUpperCase() + trimmed.slice(1).toLowerCase();
        if (CHEMICAL_SYMBOLS.has(candidate)) return candidate;
      }
      return trimmed;
    }
    const EXCL_RES = new Set((RAW_DATA.excluded_resources || []).map(x => String(x).toLowerCase()));
    const EXCL_PROV = new Set((RAW_DATA.excluded_providers || []).map(x => String(x).toLowerCase()));

    function mapDomain(at) {
      if (at === 'Proximate Analysis') return 'proximate';
      if (at === 'Calorimetry') return 'calorimetry';
      if (at === 'Compositional Analysis') return 'compositional';
      if (at === 'Ultimate Analysis') return 'ultimate';
      if (at === 'XRD Crystallinity') return 'xrd';
      if (at === 'ICP Elemental Analysis') return 'icp';
      if (at === 'XRF Elemental Analysis') return 'xrf';
      if (at === 'Pretreatment & Hydrolysis') return 'pretreatment';
      if (at === 'Fermentation (Bioconversion)') return 'fermentation';
      if (at === 'Gasification') return 'gasification';
      return 'pretreatment';
    }

    const ALL_ROWS = RAW_DATA.rows.map((arr, idx) => {
      const obj = { record_id: arr[0] };
      RAW_DATA.str_cols.forEach((col, cIdx) => {
        obj[col] = RAW_DATA.dicts[col][arr[cIdx + 1]];
      });
      obj.value = arr[RAW_DATA.str_cols.length + 2];
      obj.domain = mapDomain(obj.analysis_type);
      if ((obj.domain === 'icp' || obj.domain === 'xrf') && obj.parameter && obj.parameter !== '(metadata only)') {
        obj.parameter = formatElementSymbol(obj.parameter);
      }
      const isCompliant = obj.qc_status !== 'fail' &&
        !EXCL_RES.has(String(obj.resource_name || '').toLowerCase()) &&
        !EXCL_PROV.has(String(obj.provider_code || '').toLowerCase());
      obj.data_status = isCompliant ? 'Portal Compliant' : 'Raw';
      obj.jitter = Math.sin(idx * 19 + 5) * 1.4;
      return obj;
    });

    let wTab = 'scatter';
    let wTheme = 'dark';
    let wFiltered = [];
    let wPoints = [];
    let wPinned = null;

    function initWidget() {
      const resCounts = {};
      ALL_ROWS.forEach(r => {
        if (r.resource_name && r.resource_name !== 'Unassigned') {
          resCounts[r.resource_name] = (resCounts[r.resource_name] || 0) + 1;
        }
      });
      const activeRes = Object.entries(resCounts).sort((a, b) => b[1] - a[1]);
      const sel = document.getElementById('w-resource');
      sel.innerHTML = `<option value="ALL">All Resources (${activeRes.length})</option>` +
        activeRes.map(([n, c]) => `<option value="${n}">${n} (${c})</option>`).join('');
      onWidgetDomainOrResourceChange();
    }

    function setWidgetTab(t) {
      wTab = t;
      document.getElementById('w-tab-scatter').className = t === 'scatter'
        ? 'text-xs px-2 py-0.5 rounded font-medium bg-[var(--primary)] text-[var(--primary-foreground)]'
        : 'text-xs px-2 py-0.5 rounded font-medium text-[var(--muted-foreground)]';
      document.getElementById('w-tab-strip').className = t === 'strip'
        ? 'text-xs px-2 py-0.5 rounded font-medium bg-[var(--primary)] text-[var(--primary-foreground)]'
        : 'text-xs px-2 py-0.5 rounded font-medium text-[var(--muted-foreground)]';
      renderWidgetCanvas();
    }

    function onWidgetDomainOrResourceChange() {
      const dom = document.getElementById('w-domain').value;
      const res = document.getElementById('w-resource').value;
      const scoped = ALL_ROWS.filter(r => r.domain === dom && (res === 'ALL' || r.resource_name === res));
      const samCounts = {};
      scoped.forEach(r => { samCounts[r.prepared_sample] = (samCounts[r.prepared_sample] || 0) + 1; });
      const sams = Object.entries(samCounts).sort((a, b) => b[1] - a[1]);
      document.getElementById('w-sample').innerHTML = `<option value="ALL">All Samples (${sams.length})</option>` +
        sams.map(([s, c]) => `<option value="${s}">${s} (${c})</option>`).join('');
      applyWidgetFilters();
    }

    function applyWidgetFilters() {
      const dom = document.getElementById('w-domain').value;
      const res = document.getElementById('w-resource').value;
      const sam = document.getElementById('w-sample').value;
      const qc = document.getElementById('w-qc').value;

      wFiltered = ALL_ROWS.filter(r => {
        if (r.domain !== dom) return false;
        if (res !== 'ALL' && r.resource_name !== res) return false;
        if (sam !== 'ALL' && r.prepared_sample !== sam) return false;
        if (qc === 'Portal Compliant' && r.data_status !== 'Portal Compliant') return false;
        if (qc === 'Raw' && r.data_status !== 'Raw') return false;
        if ((qc === 'pass' || qc === 'fail') && r.qc_status !== qc) return false;
        return true;
      });
      document.getElementById('w-badge-count').textContent = `${wFiltered.length} obs`;

      const nums = wFiltered.map(r => r.value).filter(v => typeof v === 'number' && !isNaN(v));
      const mean = nums.length ? (nums.reduce((a, b) => a + b, 0) / nums.length) : null;
      const passCnt = wFiltered.filter(r => r.qc_status === 'pass').length;
      document.getElementById('w-kpis').innerHTML = `
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2 flex justify-between items-center text-xs">
          <span class="text-[var(--muted-foreground)]">Slice Mean:</span>
          <span class="font-mono font-semibold">${mean !== null ? mean.toFixed(1) : '—'} (n=${nums.length})</span>
        </div>
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2 flex justify-between items-center text-xs">
          <span class="text-[var(--muted-foreground)]">qc_pass:</span>
          <span class="font-mono font-semibold text-[#10b981]">${passCnt} / ${wFiltered.length}</span>
        </div>
      `;
      renderWidgetCanvas();
    }

    function renderWidgetCanvas() {
      const canvas = document.getElementById('w-canvas');
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      const width = rect.width || 460;
      const height = 265;
      canvas.style.height = height + 'px';
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);

      const isLight = wTheme !== 'dark';
      ctx.fillStyle = isLight ? '#f8fafc' : '#0f172a';
      ctx.fillRect(0, 0, width, height);

      const gridColor = isLight ? 'rgba(15,23,42,0.1)' : 'rgba(248,250,252,0.1)';
      const textColor = isLight ? '#475569' : '#94a3b8';
      const titleColor = isLight ? '#0f172a' : '#f8fafc';

      const numeric = wFiltered.filter(r => typeof r.value === 'number' && !isNaN(r.value));
      wPoints = [];
      if (!numeric.length) return;

      const dom = document.getElementById('w-domain').value;
      const pCounts = {};
      numeric.forEach(r => { pCounts[r.parameter] = (pCounts[r.parameter] || 0) + 1; });
      const params = dom === 'fermentation'
        ? Object.keys(pCounts).sort((a, b) => {
            const ia = FERM_CARBON_FLOW_ORDER.indexOf(a);
            const ib = FERM_CARBON_FLOW_ORDER.indexOf(b);
            return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
          })
        : Object.entries(pCounts).sort((a, b) => b[1] - a[1]).slice(0, 8).map(e => e[0]);

      const displayLabels = params.map(p => (dom === 'fermentation' && FERM_PARAM_LABELS[p] ? FERM_PARAM_LABELS[p] : ((dom === 'icp' || dom === 'xrf') ? formatElementSymbol(p) : String(p))));
      const rotateLabels = wTab === 'scatter' && (params.length > 2 || displayLabels.some(l => l.length > 8));
      const pad = { top: 14, right: 16, bottom: rotateLabels ? 78 : 42, left: wTab === 'strip' ? 120 : 42 };
      const plotW = width - pad.left - pad.right;
      const plotH = height - pad.top - pad.bottom;
      const yMax = Math.max(10, Math.ceil(Math.max(...numeric.map(r => r.value)) * 1.08));

      ctx.font = '10px system-ui, sans-serif';
      if (wTab === 'scatter') {
        const pMap = {};
        params.forEach((p, i) => { pMap[p] = i; });

        for (let i = 0; i <= 4; i++) {
          const y = pad.top + plotH - (i / 4) * plotH;
          ctx.strokeStyle = gridColor;
          ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(pad.left + plotW, y); ctx.stroke();
          ctx.fillStyle = textColor; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
          ctx.fillText(`${Math.round((yMax / 4) * i)}`, pad.left - 5, y);
        }

        // X-axis baseline
        ctx.strokeStyle = textColor;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pad.left, pad.top + plotH);
        ctx.lineTo(pad.left + plotW, pad.top + plotH);
        ctx.stroke();

        params.forEach((p, i) => {
          const cx = pad.left + ((i + 0.5) / params.length) * plotW;
          const lbl = displayLabels[i];

          ctx.strokeStyle = textColor;
          ctx.beginPath();
          ctx.moveTo(cx, pad.top + plotH);
          ctx.lineTo(cx, pad.top + plotH + 3.5);
          ctx.stroke();

          ctx.fillStyle = titleColor;
          ctx.font = '600 10px system-ui, sans-serif';
          if (rotateLabels) {
            ctx.save();
            ctx.translate(cx + 2, pad.top + plotH + 6);
            ctx.rotate(-Math.PI / 5.1);
            ctx.textAlign = 'right';
            ctx.textBaseline = 'top';
            ctx.fillText(lbl, 0, 0);
            ctx.restore();
          } else {
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillText(lbl, cx, pad.top + plotH + 6);
          }
        });

        ctx.fillStyle = textColor;
        ctx.font = '600 9.5px system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        ctx.fillText(dom === 'fermentation' ? 'Carbon-Flow Parameter' : 'Analytical Parameter', pad.left + plotW / 2, height - 2);

        numeric.forEach((r, idx) => {
          const pIdx = pMap[r.parameter];
          if (pIdx === undefined) return;
          const x = pad.left + ((pIdx + 0.5) / params.length) * plotW + r.jitter * (params.length > 8 ? 2.5 : 5);
          const y = pad.top + plotH - Math.max(0, Math.min(1, r.value / yMax)) * plotH;
          ctx.fillStyle = PALETTE[pIdx % PALETTE.length];
          ctx.beginPath(); ctx.arc(x, y, 3.8, 0, Math.PI * 2); ctx.fill();
          wPoints.push({ x, y, r });
        });
      } else {
        // X-axis baseline & ticks for strip plot
        ctx.strokeStyle = textColor;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pad.left, pad.top + plotH);
        ctx.lineTo(pad.left + plotW, pad.top + plotH);
        ctx.stroke();

        ctx.font = '600 9.5px system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        for (let i = 0; i <= 4; i++) {
          const val = (yMax / 4) * i;
          const x = pad.left + (i / 4) * plotW;
          ctx.strokeStyle = gridColor;
          ctx.beginPath(); ctx.moveTo(x, pad.top); ctx.lineTo(x, pad.top + plotH); ctx.stroke();
          ctx.strokeStyle = textColor;
          ctx.beginPath(); ctx.moveTo(x, pad.top + plotH); ctx.lineTo(x, pad.top + plotH + 3.5); ctx.stroke();
          ctx.fillStyle = titleColor;
          ctx.fillText(`${Math.round(val)}`, x, pad.top + plotH + 5);
        }

        ctx.fillStyle = textColor;
        ctx.textBaseline = 'bottom';
        ctx.fillText('Measured Value', pad.left + plotW / 2, height - 2);

        const groups = {};
        numeric.forEach(r => {
          const k = r.prepared_sample;
          if (!groups[k]) groups[k] = [];
          groups[k].push(r);
        });
        const top = Object.entries(groups).slice(0, 10);
        const step = plotH / Math.max(1, top.length);
        top.forEach(([sam, rows], i) => {
          const y = pad.top + (i + 0.5) * step;
          ctx.fillStyle = textColor; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
          ctx.fillText(sam.slice(0, 16), pad.left - 6, y);
          rows.forEach((r, j) => {
            const x = pad.left + (Math.max(0, Math.min(yMax, r.value)) / yMax) * plotW;
            ctx.fillStyle = PALETTE[j % PALETTE.length];
            ctx.beginPath(); ctx.arc(x, y, 3.8, 0, Math.PI * 2); ctx.fill();
            wPoints.push({ x, y, r });
          });
        });
      }
    }

    const wCanvas = document.getElementById('w-canvas');
    wCanvas.addEventListener('click', evt => {
      const rect = wCanvas.getBoundingClientRect();
      const mx = evt.clientX - rect.left;
      const my = evt.clientY - rect.top;
      let best = null, bestD = 100;
      for (const pt of wPoints) {
        const d = (pt.x - mx) ** 2 + (pt.y - my) ** 2;
        if (d < bestD) { bestD = d; best = pt; }
      }
      if (best) {
        const r = best.r;
        document.getElementById('w-pinned').innerHTML = `
          <div class="font-mono text-[#00B5E2] font-semibold">${r.record_id}</div>
          <div>${r.prepared_sample} (${r.resource_name})</div>
          <div class="font-mono font-semibold">${r.parameter}: ${r.value} ${r.unit}</div>
          <div>QC: ${r.qc_status} · ${r.data_status}</div>
        `;
      }
    });

    function toggleWidgetTheme() {
      wTheme = wTheme === 'light' ? 'dark' : 'light';
      const root = document.documentElement;
      root.setAttribute('data-user-theme', wTheme);
      root.setAttribute('data-theme', wTheme);
      if (document.body) {
        document.body.setAttribute('data-user-theme', wTheme);
      }
      root.classList.toggle('light', wTheme === 'light');
      root.classList.toggle('dark', wTheme === 'dark');
      document.getElementById('w-theme-btn').textContent = wTheme === 'light' ? '🌙 Dark' : '☀️ Light';
      renderWidgetCanvas();
    }

    window.addEventListener('resize', renderWidgetCanvas);
    initWidget();
  </script>
</body>
</html>
"""
    return template.replace("__WIDGET_PAYLOAD__", widget_payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Multi-Resource Explorer Dashboard & Quick Widget.")
    parser.add_argument(
        "--output-dir",
        default="exports/plots/metadata",
        help="Target directory for generated HTML dashboards (default: exports/plots/metadata).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional explicit file path for the generated Explorer HTML dashboard (overrides --output-dir).",
    )
    parser.add_argument(
        "--artifact-dir",
        default=None,
        help="Optional conversation artifact directory to mirror generated HTML files (without final </html> for write_to_file append).",
    )
    parser.add_argument(
        "--from-snapshot",
        default=None,
        help="Load pre-fetched JSON payload from a snapshot file instead of querying PostgreSQL.",
    )
    args = parser.parse_args()

    if args.from_snapshot:
        snap_path = Path(args.from_snapshot)
        if not snap_path.exists():
            raise FileNotFoundError(f"Could not read snapshot from {snap_path}")
        payload = json.loads(snap_path.read_text(encoding="utf-8"))
        print(f"Loaded snapshot from {snap_path}")
    else:
        print("Querying PostgreSQL across all resources and 10 analysis record tables...")
        payload = fetch_all_resource_data()

    print(
        f"Loaded {len(payload['resources'])} resources, "
        f"{len(payload['field_samples'])} field samples, "
        f"{len(payload['prepared_samples'])} prepared samples, "
        f"and {len(payload['rows'])} record-observation rows."
    )

    dashboard_html = build_full_dashboard_html(payload)
    if args.output:
        dashboard_path = Path(args.output)
        dashboard_path.parent.mkdir(parents=True, exist_ok=True)
        snap_out_dir = dashboard_path.parent
    else:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        dashboard_path = out_dir / "resource_explorer_dashboard.html"
        snap_out_dir = out_dir

    if not args.from_snapshot:
        snap_out_path = snap_out_dir / "dashboard_data_snapshot.json"
        snap_out_path.write_text(
            json.dumps(payload, separators=(",", ":")),
            encoding="utf-8",
        )
        print(
            f"Wrote data snapshot: {snap_out_path} ({snap_out_path.stat().st_size / 1024:.1f} KB)"
        )

    dashboard_path.write_text(dashboard_html, encoding="utf-8")
    print(f"Wrote full dashboard: {dashboard_path} ({dashboard_path.stat().st_size / 1024:.1f} KB)")

    if args.artifact_dir:
        dash_body = dashboard_html.rstrip()
        if dash_body.endswith("</html>"):
            dash_body = dash_body[: -len("</html>")].rstrip() + "\n"

        art_dir = Path(args.artifact_dir)
        art_dir.mkdir(parents=True, exist_ok=True)
        (art_dir / "resource_explorer_dashboard.html").write_text(dash_body, encoding="utf-8")
        print(f"Mirrored artifact body to {art_dir}")


if __name__ == "__main__":
    main()
