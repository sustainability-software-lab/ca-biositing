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
    payload_json = json.dumps(slim_payload, separators=(",", ":"))
    template = """<!DOCTYPE html>
<html lang="en" class="dark" data-theme="dark" data-user-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BioCirV — Multi-Resource Side-by-Side Parameter &amp; Analytical Explorer</title>
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
    select, input {
      background-color: var(--background) !important;
      color: var(--foreground) !important;
      border-color: var(--border) !important;
    }
    option, optgroup {
      background-color: var(--card) !important;
      color: var(--foreground) !important;
    }
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
          1. Resource Characterization &amp; AI Brief
        </a>
        <a id="suite-link-2" href="resource_qc_outlier_dashboard.html" class="px-2.5 py-1 rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:border-[#00B5E2] transition-colors font-medium">
          2. Statistical QC &amp; Lab Notes Audit
        </a>
        <a id="suite-link-3" href="resource_explorer_dashboard.html" class="px-2.5 py-1 rounded-md bg-[#00B5E2] text-slate-950 font-semibold transition-colors shadow-sm">
          3. Multi-Resource Side-by-Side Explorer
        </a>
      </div>
      <div class="flex items-center gap-1.5">
        <a href="../audit/db_environment_drift_dashboard.html" class="px-2.5 py-1 rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:border-[#00B5E2] transition-colors font-medium">
          DB Drift Audit
        </a>
        <a href="../index.html" class="px-2.5 py-1 rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors font-medium">
          &larr; Gallery
        </a>
      </div>
    </div>

    <!-- Row 1: Top Header & View Switcher -->
    <div class="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-[var(--border)]">
      <div class="flex flex-wrap items-center gap-2.5">
        <div class="w-2.5 h-2.5 rounded-full bg-[#00B5E2]"></div>
        <h2 id="dashboard-title" class="text-[var(--foreground)] font-semibold text-base tracking-tight">BioCirV Multi-Resource Side-by-Side Parameter Explorer</h2>
        <span id="badge-count" class="text-xs px-2 py-0.5 rounded-full bg-[var(--secondary)] text-[var(--secondary-foreground)] font-medium">11,974 obs</span>
        <span id="badge-resource-meta" class="hidden sm:inline-block text-xs px-2 py-0.5 rounded-full border border-[var(--border)] text-[var(--muted-foreground)] font-mono">127 resources</span>
      </div>
      <div class="flex items-center gap-1.5">
        <div class="flex items-center gap-1 bg-[var(--background)] p-1 rounded-lg border border-[var(--border)]">
          <button type="button" id="tab-scatter" onclick="setTab('scatter')" class="text-xs px-2.5 py-1 rounded-md font-medium bg-[var(--primary)] text-[var(--primary-foreground)] transition-colors">
            Side-by-Side Parameter Plot
          </button>
          <button type="button" id="tab-strip" onclick="setTab('strip')" class="text-xs px-2.5 py-1 rounded-md font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors">
            Replicate Strip Plot
          </button>
          <button type="button" id="tab-export" onclick="setTab('export')" class="text-xs px-2.5 py-1 rounded-md font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors">
            Export Tray (<span id="tray-count">0</span>)
          </button>
        </div>
        <button type="button" id="btn-theme" onclick="toggleTheme()" class="text-xs px-2 py-1 rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors" title="Toggle Light/Dark Theme">
          ☀️ Light
        </button>
      </div>
    </div>

    <!-- Row 2: Analysis Type Pill Bar (9 Analysis Domains) -->
    <div id="domain-pill-bar" class="flex flex-wrap items-center gap-1.5 py-1.5 border-b border-[var(--border)] text-xs"></div>

    <!-- Row 3: Multi-Select Checklist Filter Bar & Compare By Selector -->
    <div class="flex flex-wrap items-center gap-2 py-2 border-b border-[var(--border)] text-xs relative">
      <!-- Combined Status / QC Filter -->
      <div class="flex items-center gap-1">
        <span class="text-[var(--muted-foreground)] font-medium">Status / QC:</span>
        <select id="filter-status" onchange="applyFilters()" class="bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-1 text-xs focus:outline-none">
          <option value="ALL">All Statuses &amp; QC</option>
          <option value="Portal Compliant">Portal Compliant</option>
          <option value="Raw">Raw / Portal Excluded</option>
          <option value="qc_pass">qc_pass: pass</option>
          <option value="qc_fail">qc_pass: fail</option>
          <option value="qc_provisional">qc_pass: provisional/unknown</option>
        </select>
      </div>

      <!-- Toggle Inline 4-Column Multi-Select Checklists Drawer -->
      <button type="button" id="btn-toggle-drawer" onclick="toggleInlineChecklistDrawer()" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-[#00B5E2] bg-[#00B5E2]/15 text-[#00B5E2] font-semibold transition-colors">
        <span>&#9745; Multi-Select Checklists</span>
        <span id="drawer-chevron" class="text-[10px]">&#9652;</span>
      </button>

      <!-- Multi-Select Checklist Popover: Resources -->
      <div class="relative inline-flex items-center gap-1" id="popover-wrap-resources">
        <button type="button" onclick="stepResource(-1)" class="px-1.5 py-1 rounded border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]" title="Step to Previous Active Resource">&larr;</button>
        <button type="button" id="btn-popover-resources" onclick="togglePopover('resources', event)" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] hover:border-[#00B5E2] font-medium transition-colors">
          <span id="label-popover-resources">Resources: All (43 active)</span>
          <span class="text-[10px] text-[var(--muted-foreground)]">&#9662;</span>
        </button>
        <button type="button" onclick="stepResource(1)" class="px-1.5 py-1 rounded border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]" title="Step to Next Active Resource">&rarr;</button>
        <div id="panel-popover-resources" onclick="event.stopPropagation()" class="hidden absolute left-0 top-full mt-1 w-80 bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-lg shadow-xl z-50 p-2">
          <input id="search-popover-resources" type="text" oninput="renderChecklistItems('resources', true)" placeholder="Filter resources..." class="w-full bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-xs mb-1.5 focus:outline-none focus:border-[#00B5E2]" />
          <div class="flex flex-wrap items-center gap-1 pb-1.5 mb-1.5 border-b border-[var(--border)] text-[10px]">
            <span class="text-[var(--muted-foreground)] font-mono">Presets:</span>
            <button type="button" onclick="applyResourcePreset(['almond hulls','pistachio hulls','walnut hulls'])" class="px-1.5 py-0.5 rounded bg-[#00B5E2]/15 text-[#00B5E2] border border-[#00B5E2]/40 hover:bg-[#00B5E2]/25 font-medium">Nut Hulls (3)</button>
            <button type="button" onclick="applyResourcePreset(['wheat straw','rice straw','corn stover'])" class="px-1.5 py-0.5 rounded bg-[#00B5E2]/15 text-[#00B5E2] border border-[#00B5E2]/40 hover:bg-[#00B5E2]/25 font-medium">Straws (3)</button>
            <button type="button" onclick="applyResourcePreset(['olive pomace','tomato pomace','food waste'])" class="px-1.5 py-0.5 rounded bg-[#00B5E2]/15 text-[#00B5E2] border border-[#00B5E2]/40 hover:bg-[#00B5E2]/25 font-medium">Pomaces (3)</button>
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
      <div class="relative inline-flex items-center" id="popover-wrap-params">
        <button type="button" id="btn-popover-params" onclick="togglePopover('params', event)" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] hover:border-[#00B5E2] font-medium transition-colors">
          <span id="label-popover-params">Params: All</span>
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
      <div class="relative inline-flex items-center" id="popover-wrap-samples">
        <button type="button" id="btn-popover-samples" onclick="togglePopover('samples', event)" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] hover:border-[#00B5E2] font-medium transition-colors">
          <span id="label-popover-samples">Samples: All</span>
          <span class="text-[10px] text-[var(--muted-foreground)]">&#9662;</span>
        </button>
        <div id="panel-popover-samples" onclick="event.stopPropagation()" class="hidden absolute left-0 top-full mt-1 w-80 bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-lg shadow-xl z-50 p-2">
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
      <div class="relative inline-flex items-center" id="popover-wrap-methods">
        <button type="button" id="btn-popover-methods" onclick="togglePopover('methods', event)" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] hover:border-[#00B5E2] font-medium transition-colors">
          <span id="label-popover-methods">Methods: All</span>
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
      <div class="flex items-center gap-1 pl-1 border-l border-[var(--border)]">
        <span class="text-[var(--muted-foreground)] font-medium">Compare By:</span>
        <select id="compare-by-select" onchange="onCompareByManualChange(this.value)" class="bg-[var(--background)] text-[var(--foreground)] border border-[#00B5E2]/60 rounded px-1.5 py-1 text-xs font-medium focus:outline-none">
          <option value="auto">Auto (Resource / Method)</option>
          <option value="resource">Resource (Side-by-Side)</option>
          <option value="sample">Prepared Sample (Side-by-Side)</option>
          <option value="method">Method / Prep / Strain (Side-by-Side)</option>
          <option value="collection_date">Collection Date Cohort (Side-by-Side)</option>
          <option value="prep_date">Prep / Run Date Cohort (Side-by-Side)</option>
        </select>
      </div>

      <button type="button" onclick="resetFilters()" class="ml-auto text-xs px-2 py-1 rounded border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
        Reset All
      </button>
    </div>

    <!-- Row 3B: Always-Accessible 4-Column Multi-Select Checklist Drawer (Open by Default for Effortless Multi-Selection) -->
    <div id="inline-checklist-drawer" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 py-2.5 border-b border-[var(--border)] text-xs">
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
          <button type="button" onclick="applyResourcePreset(['almond hulls','pistachio hulls','walnut hulls'])" class="px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] hover:border-[#00B5E2]">Nut Hulls</button>
          <button type="button" onclick="applyResourcePreset(['wheat straw','rice straw','corn stover'])" class="px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] hover:border-[#00B5E2]">Straws</button>
          <button type="button" onclick="applyResourcePreset(['olive pomace','tomato pomace','food waste'])" class="px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] hover:border-[#00B5E2]">Pomaces</button>
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
      <div class="col-span-12 lg:col-span-8 bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5 relative">
        <!-- Quick Parameter Pill Bar for Instant Single-Parameter or Multi-Parameter Comparison with Units -->
        <div id="param-pill-bar" class="flex flex-wrap items-center gap-1 pb-2 mb-2 border-b border-[var(--border)] text-xs"></div>

        <div class="flex flex-wrap items-center justify-between gap-2 mb-1.5 px-1">
          <span id="chart-title" class="text-xs font-semibold text-[var(--foreground)]">Proximate Analysis — Side-by-Side Parameter Comparison</span>

          <div class="flex flex-wrap items-center gap-2">
            <!-- X-Axis Grouping Layout Toggle (shown in Scatter tab) -->
            <div id="xaxis-layout-controls" class="flex items-center gap-1 text-xs bg-[var(--card)] px-1.5 py-0.5 rounded border border-[var(--border)]">
              <span class="text-[var(--muted-foreground)]">X-Axis:</span>
              <button type="button" id="btn-xlayout-auto" onclick="setXLayoutMode('auto')" class="px-1.5 py-0.5 rounded text-xs font-medium bg-[var(--primary)] text-[var(--primary-foreground)]" title="Auto: Resources side-by-side when 1 parameter is focused, or Parameters with Resource sub-lanes">Auto</button>
              <button type="button" id="btn-xlayout-resources" onclick="setXLayoutMode('resources')" class="px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]" title="Place Selected Resources / Conditions directly on the X-Axis for head-to-head comparison">Resources Side-by-Side</button>
              <button type="button" id="btn-xlayout-params" onclick="setXLayoutMode('params')" class="px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]" title="Place Parameters on the X-Axis with Resource sub-lanes">Parameters</button>
            </div>

            <!-- Y-Axis Range Toggle (Auto-Fit Actual Values vs Full 0-100% Scale) -->
            <div id="yrange-controls" class="flex items-center gap-1 text-xs bg-[var(--card)] px-1.5 py-0.5 rounded border border-[var(--border)]">
              <span class="text-[var(--muted-foreground)]">Y-Range:</span>
              <button type="button" id="btn-yrange-auto" onclick="setYRangeMode('auto')" class="px-1.5 py-0.5 rounded text-xs font-medium bg-[var(--primary)] text-[var(--primary-foreground)]" title="Auto-scale Y-axis to the actual measured parameter values &amp; units">Auto-Fit Values</button>
              <button type="button" id="btn-yrange-full" onclick="setYRangeMode('full')" class="px-1.5 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground)]" title="Fix Y-axis to 0–100%">0–100%</button>
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

        <canvas id="plot-canvas" width="640" height="365" style="width: 100%; height: 365px;" class="w-full h-[365px] cursor-crosshair block"></canvas>

        <!-- Floating Hover Tooltip -->
        <div id="hover-tooltip" class="hidden pointer-events-none absolute z-20 bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-lg p-2 shadow-lg text-xs max-w-[285px]"></div>
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
              <p class="pt-4 text-center">Click any point on the chart to inspect record details, collection date, GEOID, and prep/run date, or <strong class="text-[var(--foreground)]">Cmd/Ctrl+Click</strong> to add directly to the export tray.</p>
            </div>
          </div>
          <div id="pinned-actions" class="hidden pt-2 mt-1.5 border-t border-[var(--border)] flex flex-col gap-1.5">
            <input id="pin-note" type="text" placeholder="Add audit note..." class="w-full bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-2 py-1 text-xs focus:outline-none" />
            <div class="flex items-center gap-1.5">
              <button onclick="addPinnedToExport()" class="flex-1 bg-[#00B5E2] text-slate-950 font-semibold text-xs py-1 px-2 rounded hover:opacity-90">
                + Add to Export
              </button>
              <button onclick="copyRecordId()" id="btn-copy-id" class="bg-[var(--secondary)] text-[var(--secondary-foreground)] text-xs py-1 px-2 rounded border border-[var(--border)] hover:opacity-90">
                Copy ID
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Full-Width Collapsible Statistical Precision & Candidate Outlier Drawer (Collapsed by Default) -->
      <div id="stat-screening-drawer" class="col-span-12 mt-1"></div>
    </div>

    <!-- Export Tray Tab View -->
    <div id="view-export" class="hidden pt-2.5">
      <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5 h-[340px] flex flex-col justify-between">
        <div class="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[var(--border)]">
          <span class="text-xs font-semibold text-[var(--foreground)]">Selected Records for Audit / CSV Export</span>
          <div class="flex items-center gap-2">
            <button onclick="addFilteredSliceToExport()" class="text-xs px-2.5 py-1 rounded bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] font-medium hover:border-[#00B5E2]">
              + Add Current Slice (max 250)
            </button>
            <button onclick="copyExportTSV()" id="btn-copy-tsv" class="text-xs px-2.5 py-1 rounded bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] font-medium">
              Copy TSV
            </button>
            <button onclick="downloadExportCSV()" class="text-xs px-2.5 py-1 rounded bg-[#00B5E2] text-slate-950 font-semibold">
              Download CSV
            </button>
            <button onclick="clearExport()" class="text-xs px-2 py-1 rounded text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
              Clear
            </button>
          </div>
        </div>
        <div class="overflow-y-auto flex-1 my-1.5">
          <table class="w-full text-left border-collapse text-xs">
            <thead>
              <tr class="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                <th class="py-1 px-1.5">Record ID</th>
                <th class="py-1 px-1.5">Domain</th>
                <th class="py-1 px-1.5">Sample</th>
                <th class="py-1 px-1.5">Resource</th>
                <th class="py-1 px-1.5">Method / Strain</th>
                <th class="py-1 px-1.5">Param</th>
                <th class="py-1 px-1.5">Value</th>
                <th class="py-1 px-1.5">Status</th>
                <th class="py-1 px-1.5">Note</th>
                <th class="py-1 px-1"></th>
              </tr>
            </thead>
            <tbody id="export-tbody" class="divide-y divide-[var(--border)]"></tbody>
          </table>
        </div>
      </div>
    </div>

  </div>

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

    // 9 Analysis Type Pill Definitions
    const DOMAINS = [
      { id: 'proximate', label: 'Proximate', title: 'Proximate Analysis — Parameter & Resource Comparison', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'compositional', label: 'Compositional', title: 'Compositional Biopolymers — Parameter & Resource Comparison', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'ultimate', label: 'Ultimate', title: 'Ultimate Elemental & Fiber — Parameter & Resource Comparison', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'calorimetry_xrd', label: 'Calorimetry & XRD', title: 'XRD Crystallinity & Calorimetry — Parameter & Resource Comparison', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'icp', label: 'ICP Elements', title: 'ICP-OES Elemental Concentration — Parameter & Resource Comparison (ppm)', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'xrf', label: 'XRF Elements', title: 'XRF Elemental Concentration — Parameter & Resource Comparison (ppm)', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'pretreatment', label: 'Pretreatment', title: 'Pretreatment Hydrolysis Yields — Parameter & Resource Comparison', methodCol: 'pt_method', methodLabel: 'Method:' },
      { id: 'fermentation', label: 'Fermentation', title: 'Fermentation Bioconversion — Parameter & Resource Comparison', methodCol: 'pt_method', methodLabel: 'Method:' },
      { id: 'gasification', label: 'Gasification', title: 'Gasification Syngas & Mass Balance — Parameter & Resource Comparison', methodCol: 'prep_method', methodLabel: 'Prep:' }
    ];

    function mapAnalysisTypeToDomain(at) {
      if (at === 'Proximate Analysis') return 'proximate';
      if (at === 'Compositional Analysis') return 'compositional';
      if (at === 'Ultimate Analysis') return 'ultimate';
      if (at === 'Calorimetry' || at === 'XRD Crystallinity') return 'calorimetry_xrd';
      if (at === 'ICP Elemental Analysis') return 'icp';
      if (at === 'XRF Elemental Analysis') return 'xrf';
      if (at === 'Pretreatment & Hydrolysis') return 'pretreatment';
      if (at === 'Fermentation (Bioconversion)') return 'fermentation';
      if (at === 'Gasification') return 'gasification';
      return 'proximate';
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

      const fsMeta = FIELD_SAMPLES_BY_NAME[obj.field_sample] || {};
      const psMeta = PREP_SAMPLES_BY_NAME[obj.prepared_sample] || {};
      obj.collected_at = fsMeta.collected_at || '';
      obj.collected_date = formatShortDate(fsMeta.collected_at);
      obj.geoid = fsMeta.geoid || 'Unassigned';
      obj.county_name = COUNTY_LOOKUP[obj.geoid] || (obj.geoid !== 'Unassigned' ? `GEOID ${obj.geoid}` : 'Unrecorded');
      obj.prep_date_raw = psMeta.prep_date || '';
      obj.prep_date = formatShortDate(psMeta.prep_date);
      obj.collection_cohort = formatDateCohort(fsMeta.collected_at);
      obj.prep_cohort = formatDateCohort(psMeta.prep_date);

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
      if (domainId === 'calorimetry_xrd') return param === 'crystallinity' ? '%' : 'MJ/kg';
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

    const urlParams = new URLSearchParams(window.location.search);
    let currentDomain = urlParams.get('type') || urlParams.get('tab') || 'proximate';
    if (!DOMAINS.some(d => d.id === currentDomain)) currentDomain = 'proximate';

    let currentTab = 'scatter';
    let scaleMode = 'log';
    let fermXMode = 'param';
    let xLayoutMode = 'auto'; // 'auto', 'resources', 'params'
    let yRangeMode = 'auto';  // 'auto' (fit actual parameter values), 'full' (0-100%)
    let checklistDrawerOpen = true;
    let filteredRows = [];
    let renderedPoints = [];
    let pinnedRecord = null;
    let exportRows = [];
    let activeSeriesMap = {};
    let activeCompareDimension = 'method';

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
    const ACTIVE_RESOURCES = Object.keys(RESOURCE_COUNTS).sort((a, b) => RESOURCE_COUNTS[b] - RESOURCE_COUNTS[a]);
    const PENDING_RESOURCES = (RAW_DATA.resources || [])
      .map(r => r.name)
      .filter(name => !RESOURCE_COUNTS[name])
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
      updateXLayoutButtons();
      renderCurrentView();
    }

    function updateXLayoutButtons() {
      ['auto', 'resources', 'params'].forEach(m => {
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
      updateYRangeButtons();
      renderCurrentView();
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
      if (compareByMode && compareByMode !== 'auto') return compareByMode;
      if (selectedFilters.resources.size !== 1) return 'resource';
      if (selectedFilters.samples.size > 1) return 'sample';
      return 'method';
    }

    function getComparisonGroupValue(r, domainId) {
      const dim = getEffectiveCompareDimension();
      if (dim === 'resource') return r.resource_name || 'Unassigned';
      if (dim === 'sample') return r.prepared_sample_name || 'Unassigned';
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

    function applyResourcePreset(names) {
      selectedFilters.resources.clear();
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
        onResourceOrDomainChange(false);
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
        onResourceOrDomainChange(false);
      } else {
        renderChecklistItems(key);
        applyFilters();
      }
    }

    function removeFilterChip(key, val) {
      selectedFilters[key].delete(val);
      autoUpdateCompareBy();
      if (key === 'resources') {
        onResourceOrDomainChange(false);
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

    function syncUrlAndNavLinks() {
      const firstRes = selectedFilters.resources.size > 0 ? Array.from(selectedFilters.resources)[0] : null;
      const link1 = document.getElementById('suite-link-1');
      const link2 = document.getElementById('suite-link-2');
      if (link1) {
        link1.href = firstRes
          ? `resource_analysis_dashboard.html?resource=${encodeURIComponent(firstRes)}`
          : 'resource_analysis_dashboard.html';
      }
      if (link2) {
        link2.href = firstRes
          ? `resource_qc_outlier_dashboard.html?resource=${encodeURIComponent(firstRes)}`
          : 'resource_qc_outlier_dashboard.html';
      }

      try {
        const params = new URLSearchParams();
        if (currentDomain && currentDomain !== 'proximate') params.set('type', currentDomain);
        if (selectedFilters.resources.size === 1) {
          params.set('resource', Array.from(selectedFilters.resources)[0]);
        } else if (selectedFilters.resources.size > 1) {
          params.set('resources', Array.from(selectedFilters.resources).join(','));
        }
        if (selectedFilters.samples.size > 0) params.set('samples', Array.from(selectedFilters.samples).join(','));
        if (selectedFilters.params.size > 0) params.set('params', Array.from(selectedFilters.params).join(','));
        if (selectedFilters.methods.size > 0) params.set('methods', Array.from(selectedFilters.methods).join(','));
        if (compareByMode && compareByMode !== 'auto') params.set('compare', compareByMode);
        const statusVal = document.getElementById('filter-status').value;
        if (statusVal && statusVal !== 'ALL') params.set('status', statusVal);
        const qs = params.toString();
        const newUrl = window.location.pathname + (qs ? `?${qs}` : '');
        window.history.replaceState(null, '', newUrl);
      } catch (e) {
        // Ignore history errors in sandboxed/file:// environments
      }
    }

    function initFromUrlParams() {
      const resParam = urlParams.get('resources') || urlParams.get('resource');
      if (resParam && resParam !== 'ALL') {
        resParam.split(',').map(s => s.trim()).filter(Boolean).forEach(rawName => {
          const canonical = RESOURCE_CANONICAL_MAP[rawName.toLowerCase()] || rawName;
          if (RESOURCE_COUNTS[canonical] || RESOURCES_BY_NAME[canonical]) {
            selectedFilters.resources.add(canonical);
          }
        });
      }
      const samParam = urlParams.get('samples') || urlParams.get('sample');
      if (samParam && samParam !== 'ALL') {
        samParam.split(',').map(s => s.trim()).filter(Boolean).forEach(s => selectedFilters.samples.add(s));
      }
      const pParam = urlParams.get('params') || urlParams.get('param');
      if (pParam && pParam !== 'ALL') {
        pParam.split(',').map(s => s.trim()).filter(Boolean).forEach(p => {
          const norm = (currentDomain === 'icp' || currentDomain === 'xrf') ? formatElementSymbol(p) : p;
          selectedFilters.params.add(norm);
        });
      }
      const mParam = urlParams.get('methods') || urlParams.get('method');
      if (mParam && mParam !== 'ALL') {
        mParam.split(',').map(s => s.trim()).filter(Boolean).forEach(m => selectedFilters.methods.add(m));
      }
      const compParam = urlParams.get('compare');
      if (compParam && ['auto', 'resource', 'sample', 'method', 'collection_date', 'prep_date'].includes(compParam)) {
        compareByMode = compParam;
        compareByManualOverride = (compParam !== 'auto');
        const sel = document.getElementById('compare-by-select');
        if (sel) sel.value = compareByMode;
      } else {
        autoUpdateCompareBy();
      }

      const initialStatus = urlParams.get('status') || urlParams.get('qc');
      if (initialStatus) {
        const sLower = initialStatus.trim().toLowerCase();
        const statusSel = document.getElementById('filter-status');
        if (sLower === 'pass' || sLower === 'qc_pass') statusSel.value = 'qc_pass';
        else if (sLower === 'fail' || sLower === 'qc_fail') statusSel.value = 'qc_fail';
        else if (sLower === 'portal' || sLower === 'portal compliant') statusSel.value = 'Portal Compliant';
        else if (sLower === 'raw') statusSel.value = 'Raw';
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
      onResourceOrDomainChange(false);
    }

    function setDomain(domainId) {
      currentDomain = domainId;
      selectedFilters.params.clear();
      selectedFilters.methods.clear();
      if (domainId === 'icp' || domainId === 'xrf') {
        scaleMode = 'log';
      } else if (domainId === 'gasification') {
        scaleMode = 'linear';
      }
      updateScaleButtons();
      autoUpdateCompareBy();
      onResourceOrDomainChange(false);
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
      const hasResFilter = selectedFilters.resources.size > 0;

      const selectedCounts = {};
      const totalDomainCounts = {};
      DOMAINS.forEach(d => {
        selectedCounts[d.id] = 0;
        totalDomainCounts[d.id] = 0;
      });
      ALL_ROWS.forEach(r => {
        if (!matchesStatusFilter(r, status)) return;
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

    function onResourceOrDomainChange(allowDomainFallback = false) {
      const hasResFilter = selectedFilters.resources.size > 0;

      // Only auto-switch analysis domain on initial page load if requested via allowDomainFallback
      if (allowDomainFallback && hasResFilter) {
        const curHasRows = ALL_ROWS.some(r => r.domain === currentDomain && selectedFilters.resources.has(r.resource_name));
        if (!curHasRows) {
          const fallbackDom = DOMAINS.find(d => ALL_ROWS.some(r => r.domain === d.id && selectedFilters.resources.has(r.resource_name)));
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
        return true;
      });
      const catalogSourceRows = matchingDomainRows.length > 0
        ? matchingDomainRows
        : ALL_ROWS.filter(r => r.domain === currentDomain);

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
        if (r.parameter && (r.parameter !== '(metadata only)' || currentDomain === 'calorimetry_xrd')) {
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
      applyFilters();
    }

    function setTab(tab) {
      currentTab = tab;
      ['scatter', 'strip', 'export'].forEach(t => {
        const btn = document.getElementById(`tab-${t}`);
        if (t === tab) {
          btn.className = 'text-xs px-2.5 py-1 rounded-md font-medium bg-[var(--primary)] text-[var(--primary-foreground)] transition-colors';
        } else {
          btn.className = 'text-xs px-2.5 py-1 rounded-md font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors';
        }
      });

      const viewCharts = document.getElementById('view-charts');
      const viewExport = document.getElementById('view-export');

      if (tab === 'export') {
        viewCharts.classList.add('hidden');
        viewExport.classList.remove('hidden');
        renderExportTable();
      } else {
        viewCharts.classList.remove('hidden');
        viewExport.classList.add('hidden');
        updateChartHeaderControls();
        renderCurrentView();
      }
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

    function applyFilters() {
      const status = document.getElementById('filter-status').value;
      const hasRes = selectedFilters.resources.size > 0;
      const hasSam = selectedFilters.samples.size > 0;
      const hasParam = selectedFilters.params.size > 0;
      const hasMethod = selectedFilters.methods.size > 0;

      ['resources', 'samples', 'params', 'methods'].forEach(k => updatePopoverButtonLabel(k));
      renderActiveChipsBar();
      syncUrlAndNavLinks();

      // Update combined Status / QC dropdown counts for active domain + resource selection
      const baseDomainRows = ALL_ROWS.filter(r => r.domain === currentDomain && (!hasRes || selectedFilters.resources.has(r.resource_name)));
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

      filteredRows = ALL_ROWS.filter(r => {
        if (r.domain !== currentDomain) return false;
        if (!matchesStatusFilter(r, status)) return false;
        if (hasRes && !selectedFilters.resources.has(r.resource_name)) return false;
        if (hasSam && !selectedFilters.samples.has(r.prepared_sample_name)) return false;
        if (hasParam && !selectedFilters.params.has(r.parameter)) return false;
        if (hasMethod && !selectedFilters.methods.has(getSeriesValue(r, currentDomain))) return false;
        return true;
      });

      const uniqueSamples = new Set(filteredRows.map(r => r.prepared_sample_name).filter(x => x !== 'Unassigned')).size;
      const domainTotal = ALL_ROWS.filter(r => r.domain === currentDomain).length;
      document.getElementById('badge-count').textContent = `${filteredRows.length} / ${domainTotal} obs · ${uniqueSamples} samples`;

      const resMetaBadge = document.getElementById('badge-resource-meta');
      if (selectedFilters.resources.size === 0) {
        const activeResInSlice = new Set(filteredRows.map(r => r.resource_name).filter(x => x !== 'Unassigned')).size;
        resMetaBadge.textContent = `${activeResInSlice} active resources · 11,974 total DB rows`;
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
        sample: 'By Sample',
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
      document.getElementById('filter-status').value = 'ALL';
      selectedFilters.resources.clear();
      selectedFilters.samples.clear();
      selectedFilters.params.clear();
      selectedFilters.methods.clear();
      compareByManualOverride = false;
      compareByMode = 'auto';
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
        const moist = byParam('moisture');
        const vs = byParam('volatile solids');
        const ash = byParam('ash');
        const ts = byParam('total solids');
        grid.innerHTML = [
          formatStatCard('Moisture', moist, '%'),
          formatStatCard('Volatile Solids', vs, '%'),
          formatStatCard('Ash', ash, '%'),
          formatStatCard('Total Solids', ts, '%')
        ].join('');
        closureBanner.classList.remove('hidden');
        closureLabel.textContent = 'Proximate Closure (VS + Ash):';
        const dryClosure = (vs.mean !== null && ash.mean !== null) ? (vs.mean + ash.mean) : null;
        closureVal.textContent = dryClosure !== null
          ? `${dryClosure.toFixed(1)}% dw (${dryClosure >= 95 && dryClosure <= 105 ? 'Optimal' : 'Check Fixed C'})`
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
      } else if (currentDomain === 'calorimetry_xrd') {
        closureBanner.classList.add('hidden');
        const cryst = byParam('crystallinity');
        const calCnt = filteredRows.filter(r => r.analysis_type === 'Calorimetry').length;
        const xrdCnt = filteredRows.filter(r => r.analysis_type === 'XRD Crystallinity').length;
        const samCnt = new Set(filteredRows.map(r => r.prepared_sample_name)).size;
        grid.innerHTML = [
          formatStatCard('XRD Crystallinity', cryst, '%'),
          `<div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2"><div class="text-xs text-[var(--muted-foreground)]">XRD Replicates</div><div class="text-sm font-semibold font-mono">${xrdCnt} obs</div><div class="text-xs text-[var(--muted-foreground)]">xrd_record table</div></div>`,
          `<div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2"><div class="text-xs text-[var(--muted-foreground)]">Calorimetry Runs</div><div class="text-sm font-semibold font-mono">${calCnt} runs</div><div class="text-xs text-[var(--muted-foreground)]">calorimetry_record</div></div>`,
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
      const sourceRows = currentDomain === 'calorimetry_xrd' ? filteredRows : numericRows;
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

    function renderScatter() {
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

      const numericRows = filteredRows.filter(r => typeof r.value === 'number' && !isNaN(r.value));
      const params = getActiveParametersForScatter(numericRows);
      const isTimeMode = currentDomain === 'fermentation' && fermXMode === 'time';
      const seriesKeys = Object.keys(activeSeriesMap);

      // Determine whether X-axis columns should be Resources/Conditions Side-by-Side or Parameters
      const useResourceColumns = !isTimeMode
        && params[0] !== '(metadata only)'
        && seriesKeys.length >= 1
        && (xLayoutMode === 'resources' || (xLayoutMode === 'auto' && params.length === 1 && seriesKeys.length >= 2));

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

      const xLabels = useResourceColumns
        ? seriesKeys
        : params.map(p => {
            if (p === '(metadata only)') return 'calorimetry_run (HHV pending ETL)';
            return formatParamWithUnit(p, currentDomain);
          });

      const rotateLabels = !isTimeMode && (xLabels.length > 3 || xLabels.some(l => l.length > 16));
      const pad = { top: 26, right: 20, bottom: rotateLabels ? 94 : 56, left: 68 };
      const plotW = width - pad.left - pad.right;
      const plotH = height - pad.top - pad.bottom;

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
        const yMax = computeNiceAxisMax(maxVal, yRangeMode, currentDomain);
        const xMax = 115;

        ctx.font = '11px system-ui, -apple-system, sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        for (let i = 0; i <= 5; i++) {
          const val = (yMax / 5) * i;
          const y = pad.top + plotH - (val / yMax) * plotH;
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

        const xTicks = [0, 24, 48, 72, 96, 115];
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.font = '600 11px system-ui, -apple-system, sans-serif';
        xTicks.forEach(t => {
          const x = pad.left + (t / xMax) * plotW;
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
              const hx = pad.left + (h / xMax) * plotW;
              const hy = pad.top + plotH - (Math.max(0, mVal) / yMax) * plotH;
              if (idx === 0) ctx.moveTo(hx, hy);
              else ctx.lineTo(hx, hy);
            });
            ctx.stroke();
            ctx.restore();
          }
        });

        timeRows.forEach(r => {
          const sKey = getComparisonGroupValue(r, currentDomain);
          const cfg = activeSeriesMap[sKey] || { color: '#00B5E2', shape: 'circle', offset: 0 };
          const x = Math.max(pad.left + 6, Math.min(pad.left + plotW - 6, pad.left + (r.time_h / xMax) * plotW + cfg.offset * 12 + r.jitter * 4.0));
          const y = pad.top + plotH - (Math.max(0, r.value) / yMax) * plotH;
          const isPinned = pinnedRecord && pinnedRecord.record_id === r.record_id && pinnedRecord.parameter === r.parameter;

          ctx.fillStyle = cfg.color;
          ctx.globalAlpha = isPinned ? 1.0 : 0.85;
          ctx.strokeStyle = isPinned ? '#ffffff' : 'rgba(0,0,0,0.25)';
          ctx.lineWidth = isPinned ? 2 : 0.8;
          drawShape(ctx, cfg.shape, x, y, isPinned ? 6 : 4.2);
          renderedPoints.push({ x, y, r });
        });
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

      // Draw Y gridlines & unit-aware tick labels
      ctx.font = '11px system-ui, -apple-system, sans-serif';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      const ySteps = useLog ? Math.min(6, yMax - yMin) : 5;
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
        } else if (!numericRows.length && currentDomain === 'calorimetry_xrd') {
          const repLabel = i === 0 ? '' : (i === 5 ? '' : `Rep ${i}`);
          ctx.fillText(repLabel, pad.left - 7, y);
        } else {
          const val = (yMax / ySteps) * i;
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
          const frac = (logV - yMin) / (yMax - yMin);
          return pad.top + plotH - Math.max(0, Math.min(1, frac)) * plotH;
        }
        return pad.top + plotH - Math.max(0, Math.min(1, val / yMax)) * plotH;
      };

      // =========================================================================
      // MODE A: Side-by-Side Resource / Condition Columns along X-Axis
      // =========================================================================
      if (useResourceColumns) {
        const colCount = Math.max(1, seriesKeys.length);
        const colWidth = plotW / colCount;
        const subParams = validParams.slice(0, 4);
        const paramPalette = ['#00B5E2', '#f59e0b', '#10b981', '#a855f7'];
        const paramShapes = ['circle', 'square', 'diamond', 'triangle'];

        seriesKeys.forEach((sKey, colIdx) => {
          const cx = colCount === 2
            ? pad.left + plotW * (colIdx === 0 ? 0.28 : 0.72)
            : pad.left + ((colIdx + 0.5) / colCount) * plotW;
          const sCfg = activeSeriesMap[sKey] || { color: SERIES_PALETTE[colIdx % SERIES_PALETTE.length], shape: 'circle' };

          // X-axis tick
          ctx.strokeStyle = theme.axisText;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(cx, pad.top + plotH);
          ctx.lineTo(cx, pad.top + plotH + 4);
          ctx.stroke();

          // Resource / condition label on X-axis
          ctx.fillStyle = theme.titleText;
          ctx.font = colCount <= 5 ? '600 11.5px system-ui, -apple-system, sans-serif' : '600 10.5px system-ui, -apple-system, sans-serif';
          const shortLabel = sKey.length > 24 ? sKey.slice(0, 23) + '…' : sKey;
          if (rotateLabels) {
            ctx.save();
            ctx.translate(cx + 3, pad.top + plotH + 7);
            ctx.rotate(-Math.PI / 5.1);
            ctx.textAlign = 'right';
            ctx.textBaseline = 'top';
            ctx.fillText(shortLabel, 0, 0);
            ctx.restore();
          } else {
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillText(shortLabel, cx, pad.top + plotH + 8);
          }

          // Column divider line
          if (colIdx < colCount - 1) {
            const divX = colCount === 2
              ? pad.left + plotW * 0.5
              : pad.left + ((colIdx + 1) / colCount) * plotW;
            ctx.strokeStyle = theme.grid;
            ctx.beginPath();
            ctx.moveTo(divX, pad.top);
            ctx.lineTo(divX, pad.top + plotH);
            ctx.stroke();
          }

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

            // Plot individual replicate points overlaid on the bar
            cellRows.forEach(r => {
              const x = subCx + r.jitter * Math.min(8, barWidth * 0.28);
              const y = valueToY(r.value);
              const isPinned = pinnedRecord && pinnedRecord.record_id === r.record_id && pinnedRecord.parameter === r.parameter;
              ctx.fillStyle = barColor;
              ctx.globalAlpha = isPinned ? 1.0 : 0.9;
              ctx.strokeStyle = isPinned ? '#ffffff' : 'rgba(0,0,0,0.45)';
              ctx.lineWidth = isPinned ? 2.2 : 1.0;
              drawShape(ctx, ptShape, x, y, isPinned ? 6.5 : 4.4);
              renderedPoints.push({ x, y, r });
            });
          });
        });

        // X-axis title caption for Side-by-Side Resource Mode
        const dimLabelMap = {
          resource: 'Selected Resources (Side-by-Side Parameter Comparison)',
          sample: 'Selected Prepared Samples (Side-by-Side Comparison)',
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
      const laneWidth = plotW / Math.max(1, params.length);

      params.forEach((p, idx) => {
        const cx = params.length === 2
          ? pad.left + plotW * (idx === 0 ? 0.27 : 0.73)
          : pad.left + ((idx + 0.5) / params.length) * plotW;

        // Tick mark on X-axis
        ctx.strokeStyle = theme.axisText;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(cx, pad.top + plotH);
        ctx.lineTo(cx, pad.top + plotH + 4);
        ctx.stroke();

        ctx.fillStyle = theme.titleText;
        ctx.font = params.length <= 4 ? '600 11.5px system-ui, -apple-system, sans-serif' : '600 10.5px system-ui, -apple-system, sans-serif';
        const label = xLabels[idx];

        if (rotateLabels) {
          ctx.save();
          ctx.translate(cx + 3, pad.top + plotH + 7);
          ctx.rotate(-Math.PI / 5.1);
          ctx.textAlign = 'right';
          ctx.textBaseline = 'top';
          ctx.fillText(label, 0, 0);
          ctx.restore();
        } else {
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          ctx.fillText(label, cx, pad.top + plotH + 8);
        }

        // Draw side-by-side sub-lane translucent Mean Bar + ±1 SD whiskers for each active resource/series
        if (p !== '(metadata only)') {
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
          const divX = params.length === 2
            ? pad.left + plotW * 0.5
            : pad.left + ((idx + 1) / params.length) * plotW;
          ctx.strokeStyle = theme.grid;
          ctx.beginPath();
          ctx.moveTo(divX, pad.top);
          ctx.lineTo(divX, pad.top + plotH);
          ctx.stroke();
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
        calorimetry_xrd: 'Calorimetry & XRD Parameter (%)',
        gasification: 'Gasification Parameter (ppm / °C / %)'
      };
      ctx.fillStyle = theme.axisText;
      ctx.font = '600 10.5px system-ui, -apple-system, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillText(xAxisTitleMap[currentDomain] || 'Analytical Parameter (with Units)', pad.left + plotW / 2, height - 3);

      filteredRows.forEach(r => {
        const pIdx = paramIndexMap[r.parameter];
        if (pIdx === undefined) return;
        const baseCx = params.length === 2
          ? pad.left + plotW * (pIdx === 0 ? 0.27 : 0.73)
          : pad.left + ((pIdx + 0.5) / params.length) * plotW;

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
        renderedPoints.push({ x, y, r });
      });
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
      const stripRows = (currentDomain === 'calorimetry_xrd' || !numericRows.length) ? filteredRows : numericRows;
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
        } else if (effDim === 'collection_date' || effDim === 'prep_date') {
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
        return { ...g, isMetaGroup, min, max, spread: max - min, mean, count: g.rows.length };
      });

      const sortBy = document.getElementById('strip-sort').value;
      groupList.sort((a, b) => (b[sortBy] - a[sortBy]) || (b.count - a.count));
      const topGroups = groupList.slice(0, 14);

      const rawMax = topGroups.length ? Math.max(...topGroups.map(g => g.max)) : 10;
      const xMax = computeNiceAxisMax(rawMax, yRangeMode, currentDomain);
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
        const val = (xMax / 5) * i;
        const x = pad.left + (val / xMax) * plotW;
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
      topGroups.forEach((g, idx) => {
        const y = pad.top + idx * rowStep + rowStep / 2;
        ctx.fillStyle = theme.axisText;
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        const shortLabel = g.label.length > 33 ? g.label.slice(0, 32) + '…' : g.label;
        ctx.fillText(shortLabel, pad.left - 8, y);

        if (!g.isMetaGroup) {
          const xMin = pad.left + (Math.max(0, g.min) / xMax) * plotW;
          const xMaxBar = pad.left + (Math.min(xMax, g.max) / xMax) * plotW;
          ctx.strokeStyle = theme.rangeBar;
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.moveTo(xMin, y);
          ctx.lineTo(xMaxBar, y);
          ctx.stroke();
        }

        g.rows.forEach((r, rIdx) => {
          const isMetaOnly = r.value === null || isNaN(r.value);
          const x = isMetaOnly
            ? pad.left + Math.min(plotW - 24, 34 + rIdx * 22)
            : pad.left + (Math.max(0, Math.min(xMax, r.value)) / xMax) * plotW;
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
          renderedPoints.push({ x, y, r });
        });
      });
    }

    // Canvas hover & click hit-testing
    const canvasEl = document.getElementById('plot-canvas');
    const tooltipEl = document.getElementById('hover-tooltip');

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

    canvasEl.addEventListener('mousemove', evt => {
      const hit = findNearestPoint(evt);
      if (!hit) {
        tooltipEl.classList.add('hidden');
        return;
      }
      const r = hit.r;
      const valStr = r.value !== null && !isNaN(r.value)
        ? `${r.value.toFixed(2)} ${r.unit}`
        : 'Record logged (numeric HHV pending ETL)';
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
        <div class="text-[11px] font-mono text-[var(--muted-foreground)]">Prep/Run: ${runStr} · ID: ${r.record_id} · QC: ${r.qc_pass}</div>
      `;
      tooltipEl.classList.remove('hidden');
      const left = Math.min(hit.x + 12, canvasEl.clientWidth - 235);
      const top = Math.max(8, hit.y - 60);
      tooltipEl.style.left = `${left}px`;
      tooltipEl.style.top = `${top}px`;
    });

    canvasEl.addEventListener('mouseleave', () => {
      tooltipEl.classList.add('hidden');
    });

    canvasEl.addEventListener('click', evt => {
      const hit = findNearestPoint(evt);
      if (!hit) return;
      pinRecord(hit.r);
      if (evt.metaKey || evt.ctrlKey || evt.shiftKey) {
        addRecordToExport(hit.r, '');
      }
      renderCurrentView();
    });

    function pinRecord(r) {
      pinnedRecord = r;
      const valStr = r.value !== null && !isNaN(r.value)
        ? `${r.value.toFixed(2)} ${r.unit}`
        : 'Record logged (HHV pending ETL)';
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
        <div class="flex justify-between gap-2"><span class="text-[var(--muted-foreground)]">Exp / Provider / QC:</span><span class="text-[var(--foreground)] font-mono">${r.experiment} · ${r.provider_code} · ${r.qc_pass}</span></div>
      `;
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

    function computeSliceStatScreening() {
      const numRows = filteredRows.filter(r => typeof r.value === 'number' && !isNaN(r.value) && r.parameter && r.parameter !== '(metadata only)');
      const groupMap = {};
      numRows.forEach(r => {
        const sMethod = getSeriesValue(r, currentDomain);
        const key = `${r.resource_name}::${r.prepared_sample_name}::${sMethod}::${r.experiment}::${r.parameter}::${r.unit}`;
        if (!groupMap[key]) {
          groupMap[key] = {
            group_key: key,
            resource_name: r.resource_name,
            prepared_sample: r.prepared_sample_name,
            method_label: sMethod,
            experiment: r.experiment || '—',
            parameter: r.parameter,
            unit: r.unit || '',
            rows: []
          };
        }
        groupMap[key].rows.push(r);
      });

      const groups = Object.values(groupMap).map(g => {
        g.rows.sort((a, b) => ((Number(a.replicate) || 1) - (Number(b.replicate) || 1)) || String(a.record_id).localeCompare(String(b.record_id)));
        const vals = g.rows.map(x => Number(x.value));
        const n = vals.length;
        const mean = sampleMean(vals);
        const sd = sampleSd(vals);
        const rsd = (n >= 2 && Math.abs(mean) > 1e-12) ? Math.abs(sd / mean) * 100.0 : null;
        const minV = Math.min(...vals);
        const maxV = Math.max(...vals);
        const cutoff = getTraceCutoff(currentDomain, g.unit);
        const belowFloor = cutoff > 0 && Math.abs(mean) < cutoff;

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
            dixonPass = dixonQ <= qCrit;
          } else {
            dixonQ = 0;
            dixonPass = true;
          }
        }

        const sd3xIds = [];
        let maxZ = null;
        if (n >= 3 && sd > 1e-12) {
          const zs = [];
          g.rows.forEach(x => {
            const z = Math.abs(Number(x.value) - mean) / sd;
            zs.push(z);
            if (z > 3.0) sd3xIds.push(x.record_id);
          });
          maxZ = Math.max(...zs);
        }

        const rawTriggers = [];
        if (dixonPass === false) rawTriggers.push('Dixon Q (α=0.05)');
        if (rsd !== null && rsd > 20.0) rawTriggers.push('RSD_within > 20%');
        if (sd3xIds.length > 0) rawTriggers.push('|x - mean| > 3×SD');

        const isFlaggedActive = (!suppressTraceFlags || !belowFloor) && rawTriggers.length > 0;
        const isSuppressedTraceFlag = belowFloor && rawTriggers.length > 0;

        return {
          ...g,
          n,
          mean,
          sd,
          rsd_pct: rsd,
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

      // Compute parameter-level Within-Group vs Between-Group RSD
      const byParam = {};
      groups.forEach(g => {
        const pKey = `${g.parameter}::${g.unit}`;
        if (!byParam[pKey]) byParam[pKey] = { parameter: g.parameter, unit: g.unit, groups: [] };
        byParam[pKey].groups.push(g);
      });

      const paramBreakdown = Object.values(byParam).map(pb => {
        const gs = pb.groups;
        const cutoff = getTraceCutoff(currentDomain, pb.unit);
        const withinList = gs
          .filter(x => x.rsd_pct !== null && (!suppressTraceFlags || !x.below_abundance_cutoff))
          .map(x => x.rsd_pct);
        const gMeans = gs.map(x => x.mean);
        let betweenRsd = null;
        if (gs.length >= 2) {
          const gm = sampleMean(gMeans);
          const gsd = sampleSd(gMeans);
          const allBelow = cutoff > 0 && gs.every(x => x.below_abundance_cutoff);
          if (Math.abs(gm) > 1e-12 && (!suppressTraceFlags || !allBelow)) {
            betweenRsd = Math.abs(gsd / gm) * 100.0;
          }
        }
        gs.forEach(x => { x.between_group_rsd_pct = betweenRsd; });
        return {
          parameter: pb.parameter,
          unit: pb.unit,
          n_groups: gs.length,
          n_multi_rep_groups: gs.filter(x => x.n >= 2).length,
          within_rsd_mean: withinList.length ? sampleMean(withinList) : null,
          within_rsd_median: medianVal(withinList),
          within_rsd_max: withinList.length ? Math.max(...withinList) : null,
          between_group_rsd: betweenRsd,
          n_flagged: gs.filter(x => x.is_flagged).length,
          n_trace_suppressed: gs.filter(x => x.is_suppressed_trace_flag).length,
          min_abundance_cutoff: cutoff
        };
      }).sort((a, b) => (b.n_flagged - a.n_flagged) || ((b.within_rsd_max || 0) - (a.within_rsd_max || 0)));

      groups.sort((a, b) => (Number(b.is_flagged) - Number(a.is_flagged)) || ((b.rsd_pct || 0) - (a.rsd_pct || 0)));
      lastScreenedGroups = groups;

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

    function toggleStatDrawer() {
      statDrawerOpen = !statDrawerOpen;
      renderStatScreeningDrawer();
    }

    function toggleSuppressTrace(checked) {
      suppressTraceFlags = !!checked;
      renderStatScreeningDrawer();
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
      const withinStr = stats.medianWithin !== null ? `${stats.medianWithin.toFixed(1)}%` : 'Singleton (n=1)';
      const betweenStr = stats.medianBetween !== null ? `${stats.medianBetween.toFixed(1)}%` : 'Single group';

      const flagBadge = stats.flaggedCount > 0
        ? `<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/15 text-amber-600 dark:text-amber-300 border border-amber-500/30">⚑ ${stats.flaggedCount} Flagged Replicate Group${stats.flaggedCount === 1 ? '' : 's'}</span>`
        : `<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 border border-emerald-500/30">✓ 0 Flagged Replicate Groups</span>`;

      const traceBadge = stats.suppressedCount > 0
        ? `<span class="px-2 py-0.5 rounded-full text-[11px] font-mono bg-[var(--card)] text-[var(--muted-foreground)] border border-[var(--border)]">${stats.suppressedCount} trace group${stats.suppressedCount === 1 ? '' : 's'} suppressed (&lt;100 ppm / &lt;0.5%)</span>`
        : '';

      let bodyHtml = '';
      if (statDrawerOpen) {
        const paramRowsHtml = stats.paramBreakdown.slice(0, 18).map(p => {
          const wMed = p.within_rsd_median !== null ? `${p.within_rsd_median.toFixed(1)}%` : '—';
          const wMax = p.within_rsd_max !== null ? `${p.within_rsd_max.toFixed(1)}%` : '—';
          const bRsd = p.between_group_rsd !== null ? `${p.between_group_rsd.toFixed(1)}%` : '—';
          let interp = '<span class="text-[var(--muted-foreground)]">Singleton / 1 group</span>';
          if (p.within_rsd_median !== null && p.between_group_rsd !== null) {
            if (p.between_group_rsd > p.within_rsd_median * 1.5 && p.within_rsd_median <= 15) {
              interp = '<span class="text-emerald-600 dark:text-emerald-400 font-medium">Sample/method driven (Between &gt; Within)</span>';
            } else if (p.within_rsd_max !== null && p.within_rsd_max > 20) {
              interp = '<span class="text-amber-600 dark:text-amber-300 font-medium">Assay replicate scatter (&gt;20% Within-RSD)</span>';
            } else {
              interp = '<span class="text-[#00B5E2] font-medium">Uniformly tight precision</span>';
            }
          } else if (p.within_rsd_max !== null && p.within_rsd_max > 20) {
            interp = '<span class="text-amber-600 dark:text-amber-300 font-medium">Assay replicate scatter (&gt;20% Within-RSD)</span>';
          } else if (p.within_rsd_median !== null) {
            interp = '<span class="text-emerald-600 dark:text-emerald-400 font-medium">High technical repeatability</span>';
          }
          const fCell = p.n_flagged > 0
            ? `<span class="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-300 font-mono font-semibold">${p.n_flagged} / ${p.n_multi_rep_groups}</span>`
            : `<span class="text-[var(--muted-foreground)] font-mono">0 / ${p.n_multi_rep_groups}</span>`;
          return `
            <tr class="border-b border-[var(--border)]">
              <td class="py-1 px-2 font-mono font-semibold text-[var(--foreground)]">${formatParamName(p.parameter, currentDomain)} <span class="text-[var(--muted-foreground)] font-normal">(${p.unit || '—'})</span></td>
              <td class="py-1 px-2 text-right font-mono">${p.n_multi_rep_groups} / ${p.n_groups}</td>
              <td class="py-1 px-2 text-right font-mono font-semibold">${wMed} <span class="text-[var(--muted-foreground)] font-normal">(max ${wMax})</span></td>
              <td class="py-1 px-2 text-right font-mono font-semibold text-[#00B5E2]">${bRsd}</td>
              <td class="py-1 px-2 text-center">${fCell}</td>
              <td class="py-1 px-2">${interp}</td>
            </tr>
          `;
        }).join('');

        const shownGroups = stats.groups.filter(g => statFilterMode === 'all' ? g.n >= 2 : g.is_flagged).slice(0, 40);
        const groupRowsHtml = shownGroups.map(g => {
          const repBadges = g.rows.map(r => {
            const isCand = r.record_id === g.dixon_candidate_id || g.sd3x_candidate_ids.includes(r.record_id);
            const cls = isCand
              ? 'px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-600 dark:text-amber-300 border border-amber-500/40 font-mono font-bold hover:opacity-80'
              : 'px-1.5 py-0.5 rounded bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] font-mono hover:border-[#00B5E2]';
            const star = isCand ? ' ★' : '';
            return `<button onclick="pinRecordById('${r.record_id}', '${g.parameter}')" class="${cls}" title="Click to pin ${r.record_id} on plot">Rep ${r.replicate ?? 1}: ${Number(r.value).toFixed(2)}${star}</button>`;
          }).join(' ');

          const trigBadges = [];
          if (g.dixon_pass === false && (!suppressTraceFlags || !g.below_abundance_cutoff)) {
            trigBadges.push(`<span class="px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-600 dark:text-rose-300 border border-rose-500/30 font-mono">Dixon Q=${g.dixon_q.toFixed(2)} &gt; ${g.dixon_q_crit.toFixed(2)}</span>`);
          }
          if (g.rsd_pct !== null && g.rsd_pct > 20 && (!suppressTraceFlags || !g.below_abundance_cutoff)) {
            trigBadges.push(`<span class="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-300 border border-amber-500/30 font-mono">RSD=${g.rsd_pct.toFixed(1)}%</span>`);
          }
          if (g.sd3x_candidate_ids.length > 0 && (!suppressTraceFlags || !g.below_abundance_cutoff)) {
            trigBadges.push(`<span class="px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-600 dark:text-purple-300 border border-purple-500/30 font-mono">&gt;3×SD</span>`);
          }
          if (g.below_abundance_cutoff && g.raw_triggered_tests.length > 0) {
            trigBadges.push(`<span class="px-1.5 py-0.5 rounded bg-[var(--card)] text-[var(--muted-foreground)] border border-[var(--border)] font-mono">Trace (&lt;${g.min_abundance_cutoff} ${g.unit})</span>`);
          }
          if (!trigBadges.length) {
            trigBadges.push(`<span class="text-emerald-600 dark:text-emerald-400 font-mono">Pass (Q=${g.dixon_q !== null ? g.dixon_q.toFixed(2) : '—'})</span>`);
          }

          const targetId = g.dixon_candidate_id || (g.rows[0] && g.rows[0].record_id) || '';
          return `
            <tr class="border-b border-[var(--border)]">
              <td class="py-1.5 px-2 font-mono font-semibold text-[#00B5E2]">${g.prepared_sample}<div class="text-[10px] font-sans font-normal text-[var(--muted-foreground)]">${g.resource_name} · ${g.method_label}</div></td>
              <td class="py-1.5 px-2 font-mono font-semibold">${formatParamName(g.parameter, currentDomain)} <span class="text-[var(--muted-foreground)] font-normal">(${g.unit})</span></td>
              <td class="py-1.5 px-2"><div class="flex flex-wrap gap-1">${repBadges}</div></td>
              <td class="py-1.5 px-2 text-right font-mono">${g.mean.toFixed(2)} ± ${g.sd.toFixed(2)}</td>
              <td class="py-1.5 px-2 text-right font-mono font-semibold ${g.rsd_pct > 20 ? 'text-amber-600 dark:text-amber-300' : ''}">${g.rsd_pct !== null ? g.rsd_pct.toFixed(1) + '%' : '—'} <span class="text-[var(--muted-foreground)] font-normal">/ ${g.between_group_rsd_pct !== null && g.between_group_rsd_pct !== undefined ? g.between_group_rsd_pct.toFixed(1) + '%' : '—'}</span></td>
              <td class="py-1.5 px-2"><div class="flex flex-wrap gap-1">${trigBadges.join(' ')}</div></td>
              <td class="py-1.5 px-2 text-right"><button onclick="pinRecordById('${targetId}', '${g.parameter}')" class="px-2 py-0.5 rounded bg-[var(--card)] hover:border-[#00B5E2] border border-[var(--border)] text-[var(--foreground)] font-medium">Pin</button></td>
            </tr>
          `;
        }).join('');

        bodyHtml = `
          <div class="p-3 border-t border-[var(--border)] bg-[var(--card)] space-y-3 text-xs">
            <div class="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[var(--border)]">
              <div class="text-[var(--muted-foreground)]">
                Screens replicate groups (<span class="font-mono">Sample × Method × Exp × Parameter</span>) using <strong class="text-[var(--foreground)]">Dixon's Q-Test (α=0.05, n≥3)</strong>, <strong class="text-[var(--foreground)]">Within-Group RSD &gt; 20%</strong>, and <strong class="text-[var(--foreground)]">|x − mean| &gt; 3×SD</strong>, alongside <strong class="text-[var(--foreground)]">Between-Group RSD</strong> across samples/batches.
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
                ${stats.flaggedCount > 0 ? `<button onclick="addFlaggedGroupsToExport()" class="px-2 py-1 rounded bg-[#00B5E2] text-slate-950 font-semibold hover:opacity-90">+ Add Flagged to Export Tray</button>` : ''}
              </div>
            </div>

            <!-- Section A: Within vs Between Group RSD Table -->
            <div>
              <div class="font-semibold text-[var(--foreground)] mb-1">1. Within-Replicate-Group vs. Between-Replicate-Group RSD by Parameter</div>
              <div class="overflow-x-auto max-h-[190px] overflow-y-auto border border-[var(--border)] rounded bg-[var(--background)]">
                <table class="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr class="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                      <th class="py-1 px-2">Parameter</th>
                      <th class="py-1 px-2 text-right">Multi-Rep / Total Groups</th>
                      <th class="py-1 px-2 text-right">Within-Group RSD (Med / Max)</th>
                      <th class="py-1 px-2 text-right">Between-Group RSD</th>
                      <th class="py-1 px-2 text-center">Flagged</th>
                      <th class="py-1 px-2">Variance Driver</th>
                    </tr>
                  </thead>
                  <tbody>${paramRowsHtml || '<tr><td colspan="6" class="py-3 text-center text-[var(--muted-foreground)]">No numeric parameter groups in current slice.</td></tr>'}</tbody>
                </table>
              </div>
            </div>

            <!-- Section B: Flagged Replicate Groups Table -->
            <div>
              <div class="font-semibold text-[var(--foreground)] mb-1">2. ${statFilterMode === 'flagged' ? 'Flagged Replicate Groups & Candidate Outlier Replicates (★)' : 'All Multi-Replicate Groups'}</div>
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
          </div>
        `;
      }

      el.innerHTML = `
        <div class="rounded-lg border border-[var(--border)] bg-[var(--background)] overflow-hidden">
          <div onclick="toggleStatDrawer()" class="px-3 py-2 flex flex-wrap items-center justify-between gap-2 cursor-pointer hover:bg-[var(--secondary)]/30 transition-colors">
            <div class="flex flex-wrap items-center gap-2">
              <span class="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-[#00B5E2]/15 text-[#00B5E2] font-semibold">Stat QC Screen</span>
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

    function addPinnedToExport() {
      if (!pinnedRecord) return;
      const noteInput = document.getElementById('pin-note');
      addRecordToExport(pinnedRecord, noteInput.value.trim());
      noteInput.value = '';
    }

    function addRecordToExport(r, auditNote) {
      const key = `${r.record_id}::${r.parameter}`;
      if (!exportRows.some(e => `${e.record_id}::${e.parameter}` === key)) {
        exportRows.push({
          ...r,
          audit_note: auditNote || r.note || ''
        });
        document.getElementById('tray-count').textContent = exportRows.length;
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
      if (!exportRows.length) {
        tbody.innerHTML = `<tr><td colspan="10" class="py-8 text-center text-[var(--muted-foreground)]">No records added yet. Click points in the scatter or strip plot to inspect and add them, or click "+ Add Current Slice".</td></tr>`;
        return;
      }
      tbody.innerHTML = exportRows.map((r, i) => {
        const valStr = r.value !== null && !isNaN(r.value) ? `${r.value.toFixed(2)} ${r.unit}` : 'metadata';
        return `
          <tr>
            <td class="py-1 px-1.5 font-mono text-[#00B5E2]">${r.record_id}</td>
            <td class="py-1 px-1.5">${r.analysis_type}</td>
            <td class="py-1 px-1.5 font-mono">${r.prepared_sample_name}</td>
            <td class="py-1 px-1.5">${r.resource_name}</td>
            <td class="py-1 px-1.5">${getSeriesValue(r, r.domain)}</td>
            <td class="py-1 px-1.5 font-mono">${formatParamName(r.parameter, r.domain)}</td>
            <td class="py-1 px-1.5 font-semibold font-mono">${valStr}</td>
            <td class="py-1 px-1.5">${r.qc_pass} · ${r.data_status}</td>
            <td class="py-1 px-1.5">${r.audit_note || '—'}</td>
            <td class="py-1 px-1 text-right"><button onclick="removeExportRow(${i})" class="text-xs text-rose-500 hover:underline">Remove</button></td>
          </tr>
        `;
      }).join('');
    }

    function removeExportRow(idx) {
      exportRows.splice(idx, 1);
      document.getElementById('tray-count').textContent = exportRows.length;
      renderExportTable();
    }

    function clearExport() {
      exportRows = [];
      document.getElementById('tray-count').textContent = '0';
      renderExportTable();
    }

    function copyExportTSV() {
      if (!exportRows.length) return;
      const cols = ['record_id', 'analysis_type', 'prepared_sample_name', 'field_sample_name', 'collected_date', 'geoid', 'county_name', 'prep_date', 'resource_name', 'pretreatment_method', 'prep_method', 'parameter', 'value', 'unit', 'qc_pass', 'data_status', 'audit_note'];
      const lines = [cols.join('\\t')];
      exportRows.forEach(r => {
        lines.push(cols.map(c => r[c] ?? '').join('\\t'));
      });
      navigator.clipboard.writeText(lines.join('\\n'));
      const btn = document.getElementById('btn-copy-tsv');
      btn.textContent = 'Copied TSV!';
      setTimeout(() => { btn.textContent = 'Copy TSV'; }, 1200);
    }

    function downloadExportCSV() {
      if (!exportRows.length) return;
      const cols = ['record_id', 'analysis_type', 'prepared_sample_name', 'field_sample_name', 'collected_date', 'geoid', 'county_name', 'prep_date', 'resource_name', 'pretreatment_method', 'prep_method', 'parameter', 'value', 'unit', 'qc_pass', 'data_status', 'audit_note'];
      const lines = [cols.join(',')];
      exportRows.forEach(r => {
        lines.push(cols.map(c => `"${String(r[c] ?? '').replace(/"/g, '""')}"`).join(','));
      });
      const blob = new Blob([lines.join('\\n')], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `biocirv_${currentDomain}_export.csv`;
      a.click();
      URL.revokeObjectURL(url);
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

    window.addEventListener('resize', () => renderCurrentView());
    initFromUrlParams();
    onResourceOrDomainChange(true);
  </script>
</body>
</html>
"""
    return template.replace("__PAYLOAD_JSON__", payload_json)


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
          <option value="compositional">Compositional</option>
          <option value="ultimate">Ultimate</option>
          <option value="calorimetry_xrd">Calorimetry &amp; XRD</option>
          <option value="icp">ICP Elements</option>
          <option value="xrf">XRF Elements</option>
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
          <option value="pass">qc_pass: pass</option>
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
      if (at === 'Compositional Analysis') return 'compositional';
      if (at === 'Ultimate Analysis') return 'ultimate';
      if (at === 'Calorimetry' || at === 'XRD Crystallinity') return 'calorimetry_xrd';
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

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.from_snapshot:
        snap_path = Path(args.from_snapshot)
        fallback_snaps = [
            Path("/Users/pjsmitty301/.gemini/antigravity/brain/42a5010b-7235-40e6-8c99-569580ebe1ec/scratch/db_snapshot.json"),
            Path("/Users/pjsmitty301/.gemini/antigravity/brain/cdc7a3ec-4997-4e2e-ba3d-df9a384b16fe/scratch/db_snapshot.json"),
            Path("/Users/pjsmitty301/.gemini/antigravity/brain/15a53a73-9236-4423-9235-fd92d0ccc4f9/scratch/db_snapshot.json"),
        ]
        loaded = False
        for candidate in [snap_path, *fallback_snaps]:
            try:
                if candidate.exists():
                    payload = json.loads(candidate.read_text(encoding="utf-8"))
                    print(f"Loaded snapshot from {candidate}")
                    loaded = True
                    break
            except PermissionError:
                continue
        if not loaded:
            raise FileNotFoundError(f"Could not read snapshot from {snap_path}")
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
    widget_html = build_quick_widget_html(payload)

    dashboard_path = out_dir / "resource_explorer_dashboard.html"
    widget_path = out_dir / "resource_quick_widget.html"

    dashboard_path.write_text(dashboard_html, encoding="utf-8")
    widget_path.write_text(widget_html, encoding="utf-8")

    print(f"Wrote full dashboard: {dashboard_path} ({dashboard_path.stat().st_size / 1024:.1f} KB)")
    print(f"Wrote quick widget:   {widget_path} ({widget_path.stat().st_size / 1024:.1f} KB)")

    if args.artifact_dir:
        dash_body = dashboard_html.rstrip()
        if dash_body.endswith("</html>"):
            dash_body = dash_body[: -len("</html>")].rstrip() + "\n"
        wid_body = widget_html.rstrip()
        if wid_body.endswith("</html>"):
            wid_body = wid_body[: -len("</html>")].rstrip() + "\n"

        art_dir = Path(args.artifact_dir)
        try:
            art_dir.mkdir(parents=True, exist_ok=True)
            (art_dir / "resource_explorer_dashboard.html").write_text(dash_body, encoding="utf-8")
            (art_dir / "resource_quick_widget.html").write_text(wid_body, encoding="utf-8")
            print(f"Mirrored artifact bodies to {art_dir}")
        except PermissionError:
            fallback_art = Path("/Users/pjsmitty301/.gemini/antigravity/brain/cdc7a3ec-4997-4e2e-ba3d-df9a384b16fe")
            fallback_art.mkdir(parents=True, exist_ok=True)
            (fallback_art / "resource_explorer_dashboard.html").write_text(dash_body, encoding="utf-8")
            (fallback_art / "resource_quick_widget.html").write_text(wid_body, encoding="utf-8")
            print(f"Mirrored artifact bodies to sandbox artifact dir {fallback_art}")


if __name__ == "__main__":
    main()
