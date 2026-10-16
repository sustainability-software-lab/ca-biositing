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

"""Pretreatment Variance Dashboard Generator.

Generates the standalone HTML5 canvas interactive dashboard:
  exports/plots/conversion/pretreatment_variance_dashboard.html

Supports two data loading modes:
  1. --from-snapshot <path>: Loads from a JSON database snapshot (db_snapshot.json).
  2. Default (no flag): Queries PostgreSQL via ca_biositing.datamodels.database.get_engine().
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

DEFAULT_EXCLUDED_PROVIDERS = ["jaguar"]
DEFAULT_EXCLUDED_RESOURCES = [
    "sargassum",
    "#n/a",
    "lab media",
    "alfalfa",
    "almond hulls and shells mix",
    "almond shells and hulls mix",
    "almond woodchips",
]


def _read_snapshot_file(snapshot_path: Path) -> dict:
    """Read snapshot JSON, with fallback to embedded RAW_DATA if sandbox restricts cross-conversation paths."""
    try:
        with open(snapshot_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (PermissionError, FileNotFoundError):
        repo_root = Path(__file__).resolve().parents[2]
        fallback_html = repo_root / "exports" / "plots" / "metadata" / "resource_explorer_dashboard.html"
        if fallback_html.exists():
            text = fallback_html.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("const RAW_DATA = ") and stripped.endswith(";"):
                    return json.loads(stripped[len("const RAW_DATA = ") : -1])
        raise


def load_from_snapshot(snapshot_path: str | Path) -> list[dict]:
    """Load and filter pretreatment glucose_yld / xylose_yld records from db_snapshot.json."""
    snap = _read_snapshot_file(Path(snapshot_path))
    str_cols: list[str] = snap["str_cols"]
    dicts: dict[str, list[str]] = snap["dicts"]
    excl_res = {r.strip().lower() for r in snap.get("excluded_resources", DEFAULT_EXCLUDED_RESOURCES)}
    excl_prov = {p.strip().lower() for p in snap.get("excluded_providers", DEFAULT_EXCLUDED_PROVIDERS)}

    res_to_pap: dict[str, str] = {}
    for res in snap.get("resources", []):
        name = res.get("name")
        if name:
            pap = res.get("primary_ag_product")
            res_to_pap[name] = pap if pap and pap != "N/A" else "unknown"

    records: list[dict] = []
    for encoded_row in snap["rows"]:
        rec_id = str(encoded_row[0])
        decoded = {col: dicts[col][encoded_row[i + 1]] for i, col in enumerate(str_cols)}
        val = encoded_row[len(str_cols) + 2]
        if val is None:
            continue

        rec_type = (decoded.get("record_type") or decoded.get("analysis_type") or "").strip().lower()
        param_name = (
            decoded.get("param_name") or decoded.get("parameter") or decoded.get("analysis_param") or ""
        ).strip()

        if rec_type not in ("pretreatment", "pretreatment & hydrolysis"):
            continue
        if param_name not in ("glucose_yld", "xylose_yld"):
            continue

        try:
            numeric_val = round(float(val), 4)
        except (TypeError, ValueError):
            continue

        res_name = (decoded.get("resource_name") or "unknown").strip() or "unknown"
        pap_name = (decoded.get("primary_ag_product") or res_to_pap.get(res_name, "unknown")).strip() or "unknown"
        sample_name = (
            decoded.get("prepared_sample_name") or decoded.get("prepared_sample") or "unknown"
        ).strip() or "unknown"
        prov_code = (decoded.get("provider_code") or decoded.get("provider") or "unknown").strip() or "unknown"
        pt_method = (
            decoded.get("raw_pretreatment_method") or decoded.get("pt_method") or "unknown"
        ).strip() or "unknown"
        unit_name = (decoded.get("unit") or "unknown").strip() or "unknown"
        qc_pass = (decoded.get("qc_pass") or decoded.get("qc_status") or "unknown").strip().lower() or "unknown"

        if res_name.lower() in excl_res or prov_code.lower() in excl_prov or qc_pass == "fail":
            data_status = "Raw"
        else:
            data_status = "Portal Compliant"

        records.append(
            {
                "record_id": rec_id,
                "resource_name": res_name,
                "primary_ag_product": pap_name,
                "prepared_sample_name": sample_name,
                "provider_code": prov_code,
                "raw_pretreatment_method": pt_method,
                "analysis_param": param_name,
                "value": numeric_val,
                "unit": unit_name,
                "qc_pass": qc_pass,
                "data_status": data_status,
            }
        )

    return records


def load_from_db() -> list[dict]:
    """Query PostgreSQL for pretreatment glucose_yld and xylose_yld observations."""
    os.environ.setdefault("POSTGRES_HOST", "localhost")
    from sqlalchemy import text
    from ca_biositing.datamodels.database import get_engine

    try:
        from ca_biositing.datamodels.data_portal_views.common import (
            EXCLUDED_PROVIDERS,
            EXCLUDED_RESOURCES,
        )
    except Exception:
        EXCLUDED_PROVIDERS = DEFAULT_EXCLUDED_PROVIDERS
        EXCLUDED_RESOURCES = DEFAULT_EXCLUDED_RESOURCES

    excl_res = tuple(r.lower() for r in EXCLUDED_RESOURCES) or ("__none__",)
    excl_prov = tuple(p.lower() for p in EXCLUDED_PROVIDERS) or ("__none__",)

    query = text(
        """
        WITH all_records AS (
            SELECT record_id, resource_id, experiment_id, prepared_sample_id, qc_pass, note, pretreatment_method_id
            FROM pretreatment_record
        )
        SELECT
            obs.record_id,
            COALESCE(res.name, r_via_ps.name, 'unknown') AS resource_name,
            COALESCE(pap.name, pap_via_ps.name, 'unknown') AS primary_ag_product,
            COALESCE(psam.name, 'unknown') AS prepared_sample_name,
            COALESCE(prov.codename, 'unknown') AS provider_code,
            COALESCE(meth.name, 'unknown') AS raw_pretreatment_method,
            param.name AS analysis_param,
            obs.value,
            COALESCE(u.name, 'unknown') AS unit,
            LOWER(COALESCE(rec.qc_pass, 'unknown')) AS qc_pass,
            CASE
                WHEN LOWER(COALESCE(res.name, r_via_ps.name, '')) IN :excluded THEN 'Raw'
                WHEN LOWER(COALESCE(prov.codename, '')) IN :excluded_providers THEN 'Raw'
                WHEN LOWER(COALESCE(rec.qc_pass, '')) = 'fail' THEN 'Raw'
                ELSE 'Portal Compliant'
            END AS data_status
        FROM observation obs
        JOIN all_records rec ON obs.record_id = rec.record_id
        LEFT JOIN resource res ON rec.resource_id = res.id
        LEFT JOIN primary_ag_product pap ON res.primary_ag_product_id = pap.id
        LEFT JOIN prepared_sample psam ON rec.prepared_sample_id = psam.id
        LEFT JOIN field_sample fs ON psam.field_sample_id = fs.id
        LEFT JOIN resource r_via_ps ON fs.resource_id = r_via_ps.id
        LEFT JOIN primary_ag_product pap_via_ps ON r_via_ps.primary_ag_product_id = pap_via_ps.id
        LEFT JOIN provider prov ON fs.provider_id = prov.id
        LEFT JOIN parameter param ON obs.parameter_id = param.id
        LEFT JOIN unit u ON obs.unit_id = u.id
        LEFT JOIN method meth ON rec.pretreatment_method_id = meth.id
        WHERE obs.record_type = 'pretreatment'
          AND param.name IN ('glucose_yld', 'xylose_yld')
          AND obs.value IS NOT NULL
        """
    )

    engine = get_engine()
    records: list[dict] = []
    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {"excluded": excl_res, "excluded_providers": excl_prov},
        ).mappings().all()
        for r in rows:
            try:
                val = round(float(r["value"]), 4)
            except (TypeError, ValueError):
                continue
            records.append(
                {
                    "record_id": str(r["record_id"]),
                    "resource_name": str(r["resource_name"] or "unknown"),
                    "primary_ag_product": str(r["primary_ag_product"] or "unknown"),
                    "prepared_sample_name": str(r["prepared_sample_name"] or "unknown"),
                    "provider_code": str(r["provider_code"] or "unknown"),
                    "raw_pretreatment_method": str(r["raw_pretreatment_method"] or "unknown"),
                    "analysis_param": str(r["analysis_param"]),
                    "value": val,
                    "unit": str(r["unit"] or "unknown"),
                    "qc_pass": str(r["qc_pass"] or "unknown").lower(),
                    "data_status": str(r["data_status"]),
                }
            )
    return records


def encode_payload(records: list[dict]) -> dict:
    """Dictionary-compress records into compact PAYLOAD structure {d, r}."""
    dict_cols = [
        "resource_name",
        "primary_ag_product",
        "prepared_sample_name",
        "provider_code",
        "raw_pretreatment_method",
        "analysis_param",
        "unit",
        "qc_pass",
        "data_status",
    ]
    d: dict[str, list[str]] = {}
    idx_map: dict[str, dict[str, int]] = {}
    for col in dict_cols:
        vals = sorted({str(rec[col]) for rec in records})
        d[col] = vals
        idx_map[col] = {v: i for i, v in enumerate(vals)}

    r_list = []
    for rec in records:
        r_list.append(
            [
                rec["record_id"],
                idx_map["resource_name"][rec["resource_name"]],
                idx_map["primary_ag_product"][rec["primary_ag_product"]],
                idx_map["prepared_sample_name"][rec["prepared_sample_name"]],
                idx_map["provider_code"][rec["provider_code"]],
                idx_map["raw_pretreatment_method"][rec["raw_pretreatment_method"]],
                idx_map["analysis_param"][rec["analysis_param"]],
                rec["value"],
                idx_map["unit"][rec["unit"]],
                idx_map["qc_pass"][rec["qc_pass"]],
                idx_map["data_status"][rec["data_status"]],
            ]
        )

    return {"d": d, "r": r_list}


def build_dashboard_html(records: list[dict]) -> str:
    """Render standalone HTML5 canvas Pretreatment Variance Dashboard."""
    payload = encode_payload(records)
    payload_json = json.dumps(payload, separators=(",", ":"))

    total_obs = len(records)
    portal_obs = sum(1 for r in records if r["data_status"] == "Portal Compliant")
    raw_obs = sum(1 for r in records if r["data_status"] == "Raw")
    qcpass_obs = sum(1 for r in records if r["qc_pass"] == "pass")
    qcfail_obs = sum(1 for r in records if r["qc_pass"] == "fail")
    num_methods = len(payload["d"]["raw_pretreatment_method"])
    num_resources = len(payload["d"]["resource_name"])
    num_samples = len(payload["d"]["prepared_sample_name"])

    html = """<!DOCTYPE html>
<html lang="en" class="dark" data-theme="dark" data-user-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BioCirV — Pretreatment Variance Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    html[data-user-theme="light"], body[data-user-theme="light"] {
      --background: #f8fafc;
      --card: #ffffff;
      --foreground: #0f172a;
      --muted-foreground: #475569;
      --primary: #0284c7;
      --primary-foreground: #ffffff;
      --secondary: #e2e8f0;
      --secondary-foreground: #0f172a;
      --border: #cbd5e1;
      color-scheme: light;
    }
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
    body {
      background-color: var(--background);
      color: var(--foreground);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    select, input {
      background-color: var(--background);
      color: var(--foreground);
      border-color: var(--border);
    }
  </style>
</head>
<body data-user-theme="dark" class="bg-[var(--background)] text-[var(--foreground)] antialiased p-2 select-none">
  <div class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-xl p-3.5 shadow-sm">
    <!-- Top Header & View Switcher -->
    <div class="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-[var(--border)]">
      <div class="flex items-center gap-2.5">
        <div class="w-2.5 h-2.5 rounded-full bg-[#00B5E2]"></div>
        <h2 class="text-[var(--foreground)] font-semibold text-base tracking-tight">BioCirV — Pretreatment Variance Dashboard</h2>
        <span id="badge-count" class="text-xs px-2 py-0.5 rounded-full bg-[var(--secondary)] text-[var(--secondary-foreground)] font-medium">__TOTAL_OBS__ obs</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="flex items-center gap-1 bg-[var(--background)] p-1 rounded-lg border border-[var(--border)]">
          <button id="tab-scatter" onclick="setTab('scatter')" class="text-xs px-2.5 py-1 rounded-md font-medium bg-[var(--primary)] text-[var(--primary-foreground)] transition-colors">
            Scatter by Method
          </button>
          <button id="tab-strip" onclick="setTab('strip')" class="text-xs px-2.5 py-1 rounded-md font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors">
            Replicate Strip Plot
          </button>
          <button id="tab-export" onclick="setTab('export')" class="text-xs px-2.5 py-1 rounded-md font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors">
            Export Tray (<span id="tray-count">0</span>)
          </button>
        </div>
        <button id="theme-toggle" onclick="toggleTheme()" class="text-xs px-2.5 py-1 rounded-lg border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] hover:bg-[var(--secondary)] font-medium transition-colors">
          ☀️ Light
        </button>
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="flex flex-wrap items-center gap-2 py-2 border-b border-[var(--border)] text-xs">
      <!-- Status / QC Filter -->
      <div class="flex items-center gap-1">
        <span class="text-[var(--muted-foreground)] font-medium">Status / QC:</span>
        <select id="filter-status" onchange="applyFilters()" class="bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-1 text-xs focus:outline-none">
          <option value="ALL">All Statuses &amp; QC (__TOTAL_OBS__)</option>
          <option value="Portal Compliant">Portal Compliant (__PORTAL_OBS__)</option>
          <option value="Raw">Raw / Portal Excluded (__RAW_OBS__)</option>
          <option value="qc_pass">qc_pass: pass (__QCPASS_OBS__)</option>
          <option value="qc_fail">qc_pass: fail (__QCFAIL_OBS__)</option>
        </select>
      </div>

      <!-- Parameter Filter -->
      <div class="flex items-center gap-1">
        <span class="text-[var(--muted-foreground)] font-medium">Param:</span>
        <select id="filter-param" onchange="applyFilters()" class="bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-1 text-xs focus:outline-none">
          <option value="ALL">Both Parameters</option>
          <option value="glucose_yld">glucose_yld (%)</option>
          <option value="xylose_yld">xylose_yld (%)</option>
        </select>
      </div>

      <!-- Method Filter -->
      <div class="flex items-center gap-1">
        <span class="text-[var(--muted-foreground)] font-medium">Method:</span>
        <select id="filter-method" onchange="applyFilters()" class="bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-1 text-xs focus:outline-none">
          <option value="ALL">All Methods (__NUM_METHODS__)</option>
          <option value="cho10pc">cho10pc (Cholinium Lysinate)</option>
          <option value="h2o140c">h2o140c (Water 140°C)</option>
          <option value="butknt140c">butknt140c (Butylamine 140°C)</option>
          <option value="none20c">none20c (No Pretreatment)</option>
        </select>
      </div>

      <!-- Resource Filter -->
      <div class="flex items-center gap-1">
        <span class="text-[var(--muted-foreground)] font-medium">Resource:</span>
        <select id="filter-resource" onchange="applyFilters()" class="bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-1 text-xs max-w-[155px] focus:outline-none">
          <option value="ALL">All Resources (__NUM_RESOURCES__)</option>
        </select>
      </div>

      <!-- Sample Filter -->
      <div class="flex items-center gap-1">
        <span class="text-[var(--muted-foreground)] font-medium">Sample:</span>
        <select id="filter-sample" onchange="applyFilters()" class="bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-1 text-xs max-w-[150px] focus:outline-none">
          <option value="ALL">All Samples (__NUM_SAMPLES__)</option>
        </select>
      </div>

      <button onclick="resetFilters()" class="ml-auto text-xs px-2 py-1 rounded border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
        Reset
      </button>
    </div>

    <!-- Main Content Body (Compact 320px height to stay well under 500px total) -->
    <div id="view-charts" class="grid grid-cols-12 gap-3 pt-2.5 items-start">
      <!-- Left: Interactive Canvas Plot -->
      <div class="col-span-8 bg-[var(--background)] border border-[var(--border)] rounded-lg p-2 relative">
        <div class="flex items-center justify-between mb-1 px-1">
          <span id="chart-title" class="text-xs font-semibold text-[var(--foreground)]">Pretreatment Variance by Sample &amp; Method</span>
          <div id="strip-controls" class="hidden flex items-center gap-1.5 text-xs">
            <span class="text-[var(--muted-foreground)]">Sort:</span>
            <select id="strip-sort" onchange="renderCurrentView()" class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded px-1.5 py-0.5 text-xs">
              <option value="spread">Highest Variance (Range)</option>
              <option value="mean">Highest Mean Value</option>
              <option value="count">Most Replicates</option>
            </select>
          </div>
          <div id="method-legend" class="flex items-center gap-2.5 text-xs text-[var(--muted-foreground)]">
            <span class="inline-flex items-center gap-1"><span class="w-2.5 h-2.5 inline-block rounded-full bg-[#00B5E2]"></span>cho10pc</span>
            <span class="inline-flex items-center gap-1"><span class="w-2.5 h-2.5 inline-block bg-[#f59e0b]"></span>h2o140c</span>
            <span class="inline-flex items-center gap-1"><span class="w-2.5 h-2.5 inline-block rotate-45 bg-[#10b981]"></span>butknt140c</span>
            <span class="inline-flex items-center gap-1"><span class="w-2.5 h-2.5 inline-block rounded-sm bg-[#ec4899]"></span>none20c</span>
          </div>
        </div>
        <canvas id="plot-canvas" width="540" height="275" class="w-full h-[275px] cursor-crosshair block"></canvas>
        <!-- Floating Hover Tooltip -->
        <div id="hover-tooltip" class="hidden pointer-events-none absolute z-20 bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-lg p-2 shadow-lg text-xs max-w-[230px]"></div>
      </div>

      <!-- Right: Stats + Pinned Point Inspector -->
      <div class="col-span-4 flex flex-col gap-2">
        <!-- Summary Metrics -->
        <div class="grid grid-cols-2 gap-1.5">
          <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2">
            <div class="text-xs text-[var(--muted-foreground)]">Glucose Yield</div>
            <div id="stat-glucose-mean" class="text-sm font-semibold text-[var(--foreground)]">—</div>
            <div id="stat-glucose-sd" class="text-xs text-[var(--muted-foreground)]">SD: —</div>
          </div>
          <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2">
            <div class="text-xs text-[var(--muted-foreground)]">Xylose Yield</div>
            <div id="stat-xylose-mean" class="text-sm font-semibold text-[var(--foreground)]">—</div>
            <div id="stat-xylose-sd" class="text-xs text-[var(--muted-foreground)]">SD: —</div>
          </div>
        </div>

        <!-- Pinned Record Inspector (matches dashboard_click_export.js) -->
        <div class="bg-[var(--background)] border border-[#00B5E2]/60 rounded-lg p-2.5 flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-xs font-semibold text-[var(--foreground)]">Pinned Point Inspector</span>
              <span id="pin-status-badge" class="text-xs px-1.5 py-0.5 rounded bg-[var(--secondary)] text-[var(--secondary-foreground)]">Click a point</span>
            </div>
            <div id="pinned-details" class="text-xs text-[var(--muted-foreground)] space-y-1 min-h-[125px]">
              <p class="pt-4 text-center">Click any point on the chart to inspect record details, or <strong class="text-[var(--foreground)]">Cmd/Ctrl+Click</strong> to add directly to the export tray.</p>
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
    </div>

    <!-- Export Tray Tab View -->
    <div id="view-export" class="hidden pt-2.5">
      <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5 h-[305px] flex flex-col justify-between">
        <div class="flex items-center justify-between pb-2 border-b border-[var(--border)]">
          <span class="text-xs font-semibold text-[var(--foreground)]">Selected Records for Audit / CSV Export</span>
          <div class="flex items-center gap-2">
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
                <th class="py-1 px-1.5">Sample</th>
                <th class="py-1 px-1.5">Resource</th>
                <th class="py-1 px-1.5">Method</th>
                <th class="py-1 px-1.5">Param</th>
                <th class="py-1 px-1.5">Value</th>
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
    const PAYLOAD = __PAYLOAD_JSON__;

    // Decode dictionary-compressed dataset into full row objects with deterministic jitter
    const D = PAYLOAD.d;
    function seededRandom(seed) {
      let x = Math.sin(seed) * 10000;
      return x - Math.floor(x);
    }

    const ALL_ROWS = PAYLOAD.r.map((arr, idx) => {
      const u1 = Math.max(1e-6, seededRandom(idx * 17 + 3));
      const u2 = seededRandom(idx * 31 + 7);
      const jitter = Math.max(-2.2, Math.min(2.2, Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)));
      const method = D.raw_pretreatment_method[arr[5]];
      return {
        record_id: arr[0],
        resource_name: D.resource_name[arr[1]],
        primary_ag_product: D.primary_ag_product[arr[2]],
        prepared_sample_name: D.prepared_sample_name[arr[3]],
        provider_code: D.provider_code[arr[4]],
        raw_pretreatment_method: method,
        pretreatment_method: method,
        analysis_param: D.analysis_param[arr[6]],
        value: arr[7],
        unit: D.unit[arr[8]],
        qc_pass: D.qc_pass[arr[9]],
        data_status: D.data_status[arr[10]],
        jitter: jitter
      };
    });

    const METHOD_COLORS = {
      cho10pc: '#00B5E2',
      h2o140c: '#f59e0b',
      butknt140c: '#10b981',
      none20c: '#ec4899'
    };

    const SAMPLE_PALETTE = [
      '#00B5E2', '#3b82f6', '#8b5cf6', '#ec4899', '#f43f5e',
      '#f97316', '#eab308', '#10b981', '#14b8a6', '#06b6d4',
      '#6366f1', '#a855f7', '#d946ef', '#ef4444', '#84cc16'
    ];
    const sampleColorMap = {};
    D.prepared_sample_name.forEach((s, i) => {
      sampleColorMap[s] = SAMPLE_PALETTE[i % SAMPLE_PALETTE.length];
    });

    let currentTab = 'scatter';
    let currentTheme = 'dark';
    let filteredRows = [...ALL_ROWS];
    let renderedPoints = [];
    let pinnedRecord = null;
    let exportRows = [];

    function toggleTheme() {
      currentTheme = currentTheme === 'light' ? 'dark' : 'light';
      const root = document.documentElement;
      root.setAttribute('data-user-theme', currentTheme);
      root.setAttribute('data-theme', currentTheme);
      if (document.body) {
        document.body.setAttribute('data-user-theme', currentTheme);
      }
      root.classList.toggle('light', currentTheme === 'light');
      root.classList.toggle('dark', currentTheme === 'dark');
      const btn = document.getElementById('theme-toggle');
      if (btn) {
        btn.textContent = currentTheme === 'dark' ? '☀️ Light' : '🌙 Dark';
      }
      renderCurrentView();
    }

    function initDropdowns() {
      const resCounts = {};
      const samCounts = {};
      ALL_ROWS.forEach(r => {
        resCounts[r.resource_name] = (resCounts[r.resource_name] || 0) + 1;
        samCounts[r.prepared_sample_name] = (samCounts[r.prepared_sample_name] || 0) + 1;
      });

      const resSelect = document.getElementById('filter-resource');
      Object.entries(resCounts)
        .sort((a, b) => b[1] - a[1])
        .forEach(([name, count]) => {
          const opt = document.createElement('option');
          opt.value = name;
          opt.textContent = `${name} (${count})`;
          resSelect.appendChild(opt);
        });

      const samSelect = document.getElementById('filter-sample');
      Object.entries(samCounts)
        .sort((a, b) => b[1] - a[1])
        .forEach(([name, count]) => {
          const opt = document.createElement('option');
          opt.value = name;
          opt.textContent = `${name} (${count})`;
          samSelect.appendChild(opt);
        });
    }

    function matchSelectOption(selectEl, val) {
      if (!val || !selectEl) return false;
      const trimmed = val.trim();
      const lower = trimmed.toLowerCase();
      for (const opt of selectEl.options) {
        if (opt.value === trimmed || opt.value.toLowerCase() === lower) {
          selectEl.value = opt.value;
          return true;
        }
      }
      return false;
    }

    function applyUrlParams() {
      const params = new URLSearchParams(window.location.search);
      const statusParam = params.get('status') || params.get('qc');
      if (statusParam) {
        const sLower = statusParam.trim().toLowerCase();
        const statusEl = document.getElementById('filter-status');
        if (sLower === 'portal' || sLower === 'portal compliant' || sLower === 'compliant') {
          statusEl.value = 'Portal Compliant';
        } else if (sLower === 'raw' || sLower === 'excluded') {
          statusEl.value = 'Raw';
        } else if (sLower === 'pass' || sLower === 'qc_pass') {
          statusEl.value = 'qc_pass';
        } else if (sLower === 'fail' || sLower === 'qc_fail') {
          statusEl.value = 'qc_fail';
        } else if (sLower === 'all') {
          statusEl.value = 'ALL';
        } else {
          matchSelectOption(statusEl, statusParam);
        }
      }
      const resourceParam = params.get('resource');
      if (resourceParam) {
        matchSelectOption(document.getElementById('filter-resource'), resourceParam);
      }
      const sampleParam = params.get('sample');
      if (sampleParam) {
        matchSelectOption(document.getElementById('filter-sample'), sampleParam);
      }
      const methodParam = params.get('method');
      if (methodParam) {
        matchSelectOption(document.getElementById('filter-method'), methodParam);
      }
      const paramFilter = params.get('param') || params.get('parameter');
      if (paramFilter) {
        matchSelectOption(document.getElementById('filter-param'), paramFilter);
      }
      const tabParam = params.get('tab');
      if (tabParam && ['scatter', 'strip', 'export'].includes(tabParam.toLowerCase())) {
        currentTab = tabParam.toLowerCase();
      }
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
      const stripControls = document.getElementById('strip-controls');
      const methodLegend = document.getElementById('method-legend');
      const chartTitle = document.getElementById('chart-title');

      if (tab === 'export') {
        viewCharts.classList.add('hidden');
        viewExport.classList.remove('hidden');
        renderExportTable();
      } else {
        viewCharts.classList.remove('hidden');
        viewExport.classList.add('hidden');
        if (tab === 'scatter') {
          chartTitle.textContent = 'Pretreatment Variance by Sample & Method';
          stripControls.classList.add('hidden');
          methodLegend.classList.remove('hidden');
        } else {
          chartTitle.textContent = 'Variance within Sample / Method Replicates (Top 14)';
          stripControls.classList.remove('hidden');
          methodLegend.classList.add('hidden');
        }
        renderCurrentView();
      }
    }

    function applyFilters() {
      const status = document.getElementById('filter-status').value;
      const param = document.getElementById('filter-param').value;
      const method = document.getElementById('filter-method').value;
      const resource = document.getElementById('filter-resource').value;
      const sample = document.getElementById('filter-sample').value;

      filteredRows = ALL_ROWS.filter(r => {
        if (status === 'Portal Compliant' && r.data_status !== 'Portal Compliant') return false;
        if (status === 'Raw' && r.data_status !== 'Raw') return false;
        if (status === 'qc_pass' && r.qc_pass !== 'pass') return false;
        if (status === 'qc_fail' && r.qc_pass !== 'fail') return false;
        if (param !== 'ALL' && r.analysis_param !== param) return false;
        if (method !== 'ALL' && r.pretreatment_method !== method) return false;
        if (resource !== 'ALL' && r.resource_name !== resource) return false;
        if (sample !== 'ALL' && r.prepared_sample_name !== sample) return false;
        return true;
      });

      const uniqueSamples = new Set(filteredRows.map(r => r.prepared_sample_name)).size;
      document.getElementById('badge-count').textContent = `${filteredRows.length} / ${ALL_ROWS.length} obs · ${uniqueSamples} samples`;

      updateStats();
      renderCurrentView();
    }

    function resetFilters() {
      document.getElementById('filter-status').value = 'ALL';
      document.getElementById('filter-param').value = 'ALL';
      document.getElementById('filter-method').value = 'ALL';
      document.getElementById('filter-resource').value = 'ALL';
      document.getElementById('filter-sample').value = 'ALL';
      applyFilters();
    }

    function calcStats(vals) {
      if (!vals.length) return { mean: null, sd: null, min: null, max: null };
      const n = vals.length;
      const mean = vals.reduce((a, b) => a + b, 0) / n;
      const variance = vals.reduce((acc, v) => acc + (v - mean) ** 2, 0) / n;
      return {
        mean,
        sd: Math.sqrt(variance),
        min: Math.min(...vals),
        max: Math.max(...vals),
        n
      };
    }

    function updateStats() {
      const gluc = calcStats(filteredRows.filter(r => r.analysis_param === 'glucose_yld').map(r => r.value));
      const xylo = calcStats(filteredRows.filter(r => r.analysis_param === 'xylose_yld').map(r => r.value));

      document.getElementById('stat-glucose-mean').textContent = gluc.mean !== null ? `${gluc.mean.toFixed(1)}% (n=${gluc.n})` : '—';
      document.getElementById('stat-glucose-sd').textContent = gluc.mean !== null ? `±${gluc.sd.toFixed(1)}% · [${gluc.min.toFixed(1)}–${gluc.max.toFixed(1)}]` : 'No data';

      document.getElementById('stat-xylose-mean').textContent = xylo.mean !== null ? `${xylo.mean.toFixed(1)}% (n=${xylo.n})` : '—';
      document.getElementById('stat-xylose-sd').textContent = xylo.mean !== null ? `±${xylo.sd.toFixed(1)}% · [${xylo.min.toFixed(1)}–${xylo.max.toFixed(1)}]` : 'No data';
    }

    function getThemeColors() {
      const isLight = currentTheme !== 'dark';
      return {
        canvasBg: isLight ? '#f8fafc' : '#0f172a',
        grid: isLight ? 'rgba(15, 23, 42, 0.1)' : 'rgba(248, 250, 252, 0.1)',
        axisText: isLight ? '#475569' : '#94a3b8',
        titleText: isLight ? '#0f172a' : '#f8fafc',
        rangeBar: isLight ? 'rgba(15, 23, 42, 0.25)' : 'rgba(248, 250, 252, 0.28)',
        pinnedStroke: isLight ? '#0f172a' : '#ffffff'
      };
    }

    function drawShape(ctx, shape, x, y, r) {
      ctx.beginPath();
      if (shape === 'cho10pc') {
        ctx.arc(x, y, r, 0, Math.PI * 2);
      } else if (shape === 'h2o140c') {
        ctx.rect(x - r, y - r, r * 2, r * 2);
      } else if (shape === 'butknt140c') {
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

    function renderScatter() {
      const canvas = document.getElementById('plot-canvas');
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      const width = rect.width || 540;
      const height = 310;
      canvas.style.height = height + 'px';
      canvas.width = width * dpr;
      canvas.height = height * dpr;

      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);

      const theme = getThemeColors();
      ctx.fillStyle = theme.canvasBg;
      ctx.fillRect(0, 0, width, height);

      const pad = { top: 18, right: 20, bottom: 72, left: 46 };
      const plotW = width - pad.left - pad.right;
      const plotH = height - pad.top - pad.bottom;

      const maxVal = Math.max(105, ...filteredRows.map(r => r.value));
      const yMax = Math.ceil(maxVal / 20) * 20;

      // Y gridlines & labels
      ctx.font = '12px system-ui, -apple-system, sans-serif';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      const ySteps = 5;
      for (let i = 0; i <= ySteps; i++) {
        const val = (yMax / ySteps) * i;
        const y = pad.top + plotH - (val / yMax) * plotH;
        ctx.strokeStyle = theme.grid;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(pad.left + plotW, y);
        ctx.stroke();

        ctx.fillStyle = theme.axisText;
        ctx.fillText(`${Math.round(val)}%`, pad.left - 6, y);
      }

      // X-axis baseline
      ctx.strokeStyle = theme.axisText;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top + plotH);
      ctx.lineTo(pad.left + plotW, pad.top + plotH);
      ctx.stroke();

      // X categories (glucose_yld, xylose_yld) paired with method lanes
      const params = ['glucose_yld', 'xylose_yld'];
      const methodOffsets = { cho10pc: -0.24, h2o140c: -0.08, butknt140c: 0.08, none20c: 0.24 };

      params.forEach((p, idx) => {
        const cx = pad.left + plotW * (idx === 0 ? 0.27 : 0.73);
        const label = p === 'glucose_yld' ? 'glucose_yld (% of glucan)' : 'xylose_yld (% of xylan)';

        ctx.strokeStyle = theme.axisText;
        ctx.beginPath();
        ctx.moveTo(cx, pad.top + plotH);
        ctx.lineTo(cx, pad.top + plotH + 4);
        ctx.stroke();

        ctx.fillStyle = theme.titleText;
        ctx.font = '600 11.5px system-ui, -apple-system, sans-serif';
        ctx.save();
        ctx.translate(cx + 8, pad.top + plotH + 7);
        ctx.rotate(-Math.PI / 8.5);
        ctx.textAlign = 'right';
        ctx.textBaseline = 'top';
        ctx.fillText(label, 0, 0);
        ctx.restore();

        // Divider between parameters
        if (idx === 0) {
          ctx.strokeStyle = theme.grid;
          ctx.beginPath();
          ctx.moveTo(pad.left + plotW * 0.5, pad.top);
          ctx.lineTo(pad.left + plotW * 0.5, pad.top + plotH);
          ctx.stroke();
        }
      });

      ctx.fillStyle = theme.axisText;
      ctx.font = '600 10.5px system-ui, -apple-system, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillText('Pretreatment Monomeric Yield Parameter', pad.left + plotW / 2, height - 3);

      renderedPoints = [];
      filteredRows.forEach(r => {
        const pIdx = r.analysis_param === 'glucose_yld' ? 0 : 1;
        const baseCx = pad.left + plotW * (pIdx === 0 ? 0.27 : 0.73);
        const mOffset = (methodOffsets[r.pretreatment_method] || 0) * (plotW * 0.44);
        const x = baseCx + mOffset + r.jitter * 6.5;
        const y = pad.top + plotH - (r.value / yMax) * plotH;

        const isPinned = pinnedRecord && pinnedRecord.record_id === r.record_id;
        ctx.fillStyle = METHOD_COLORS[r.pretreatment_method] || '#00B5E2';
        ctx.globalAlpha = isPinned ? 1.0 : 0.78;
        ctx.strokeStyle = isPinned ? theme.pinnedStroke : 'rgba(0,0,0,0.25)';
        ctx.lineWidth = isPinned ? 2 : 0.8;

        drawShape(ctx, r.pretreatment_method, x, y, isPinned ? 6 : 4.2);
        renderedPoints.push({ x, y, r });
      });
      ctx.globalAlpha = 1.0;
    }

    function renderStrip() {
      const canvas = document.getElementById('plot-canvas');
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      const width = rect.width || 540;
      const height = 310;
      canvas.style.height = height + 'px';
      canvas.width = width * dpr;
      canvas.height = height * dpr;

      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);

      const theme = getThemeColors();
      ctx.fillStyle = theme.canvasBg;
      ctx.fillRect(0, 0, width, height);

      const pad = { top: 14, right: 20, bottom: 46, left: 145 };
      const plotW = width - pad.left - pad.right;
      const plotH = height - pad.top - pad.bottom;

      // Group replicates by (prepared_sample_name, pretreatment_method)
      const groups = {};
      filteredRows.forEach(r => {
        const key = `${r.prepared_sample_name} · ${r.pretreatment_method}`;
        if (!groups[key]) {
          groups[key] = {
            label: `${r.prepared_sample_name} (${r.pretreatment_method})`,
            sample: r.prepared_sample_name,
            method: r.pretreatment_method,
            rows: []
          };
        }
        groups[key].rows.push(r);
      });

      const groupList = Object.values(groups).map(g => {
        const vals = g.rows.map(x => x.value);
        const min = Math.min(...vals);
        const max = Math.max(...vals);
        const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
        return { ...g, min, max, spread: max - min, mean, count: vals.length };
      });

      const sortBy = document.getElementById('strip-sort').value;
      groupList.sort((a, b) => b[sortBy] - a[sortBy]);
      const topGroups = groupList.slice(0, 14);

      const maxVal = Math.max(105, ...filteredRows.map(r => r.value));
      const xMax = Math.ceil(maxVal / 20) * 20;

      // X-axis baseline
      ctx.strokeStyle = theme.axisText;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top + plotH);
      ctx.lineTo(pad.left + plotW, pad.top + plotH);
      ctx.stroke();

      // X gridlines
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
        ctx.fillText(`${Math.round(val)}%`, x, pad.top + plotH + 7);
      }

      ctx.fillStyle = theme.axisText;
      ctx.font = '600 10.5px system-ui, -apple-system, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillText('Monomeric Sugar Yield (% Theoretical)', pad.left + plotW / 2, height - 3);

      renderedPoints = [];
      const rowStep = plotH / Math.max(1, topGroups.length);

      topGroups.forEach((g, idx) => {
        const y = pad.top + idx * rowStep + rowStep / 2;
        ctx.fillStyle = theme.axisText;
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        const shortLabel = g.label.length > 22 ? g.label.slice(0, 21) + '…' : g.label;
        ctx.fillText(shortLabel, pad.left - 8, y);

        // Min-max spread bar
        const xMin = pad.left + (g.min / xMax) * plotW;
        const xMaxBar = pad.left + (g.max / xMax) * plotW;
        ctx.strokeStyle = theme.rangeBar;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(xMin, y);
        ctx.lineTo(xMaxBar, y);
        ctx.stroke();

        // Individual replicate dots
        g.rows.forEach(r => {
          const x = pad.left + (r.value / xMax) * plotW;
          const isPinned = pinnedRecord && pinnedRecord.record_id === r.record_id;
          ctx.fillStyle = r.analysis_param === 'glucose_yld' ? '#00B5E2' : '#f59e0b';
          ctx.strokeStyle = isPinned ? theme.pinnedStroke : 'rgba(0,0,0,0.3)';
          ctx.lineWidth = isPinned ? 2 : 0.8;
          ctx.beginPath();
          ctx.arc(x, y, isPinned ? 5.5 : 4, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
          renderedPoints.push({ x, y, r });
        });
      });
    }

    // Canvas hover & click interactions
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
      tooltipEl.innerHTML = `
        <div class="font-semibold text-[var(--foreground)]">${r.prepared_sample_name}</div>
        <div class="text-[var(--muted-foreground)]">${r.resource_name} · ${r.pretreatment_method}</div>
        <div class="mt-1 font-medium text-[#00B5E2]">${r.analysis_param}: ${r.value.toFixed(2)} ${r.unit}</div>
        <div class="text-[var(--muted-foreground)]">ID: ${r.record_id} · QC: ${r.qc_pass}</div>
      `;
      tooltipEl.classList.remove('hidden');
      const left = Math.min(hit.x + 12, canvasEl.clientWidth - 220);
      const top = Math.max(8, hit.y - 56);
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
      document.getElementById('pin-status-badge').textContent = r.data_status;
      document.getElementById('pinned-details').innerHTML = `
        <div class="flex justify-between"><span class="text-[var(--muted-foreground)]">Record ID:</span><span class="font-mono font-semibold text-[#00B5E2]">${r.record_id}</span></div>
        <div class="flex justify-between"><span class="text-[var(--muted-foreground)]">Sample:</span><span class="font-medium text-[var(--foreground)]">${r.prepared_sample_name}</span></div>
        <div class="flex justify-between"><span class="text-[var(--muted-foreground)]">Resource:</span><span class="text-[var(--foreground)]">${r.resource_name}</span></div>
        <div class="flex justify-between"><span class="text-[var(--muted-foreground)]">Method:</span><span class="text-[var(--foreground)]">${r.pretreatment_method}</span></div>
        <div class="flex justify-between"><span class="text-[var(--muted-foreground)]">Parameter:</span><span class="text-[var(--foreground)]">${r.analysis_param}</span></div>
        <div class="flex justify-between"><span class="text-[var(--muted-foreground)]">Measured:</span><span class="font-semibold text-[var(--foreground)]">${r.value.toFixed(2)} ${r.unit}</span></div>
        <div class="flex justify-between"><span class="text-[var(--muted-foreground)]">Provider / QC:</span><span class="text-[var(--foreground)]">${r.provider_code} / ${r.qc_pass}</span></div>
      `;
      document.getElementById('pinned-actions').classList.remove('hidden');
    }

    function addPinnedToExport() {
      if (!pinnedRecord) return;
      const noteInput = document.getElementById('pin-note');
      addRecordToExport(pinnedRecord, noteInput.value.trim());
      noteInput.value = '';
    }

    function addRecordToExport(r, note) {
      if (!exportRows.some(e => e.record_id === r.record_id)) {
        exportRows.push({ ...r, note: note || '' });
        document.getElementById('tray-count').textContent = exportRows.length;
      }
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
        tbody.innerHTML = `<tr><td colspan="8" class="py-8 text-center text-[var(--muted-foreground)]">No records added yet. Click points in the scatter or strip plot to inspect and add them.</td></tr>`;
        return;
      }
      tbody.innerHTML = exportRows.map((r, i) => `
        <tr>
          <td class="py-1 px-1.5 font-mono text-[#00B5E2]">${r.record_id}</td>
          <td class="py-1 px-1.5">${r.prepared_sample_name}</td>
          <td class="py-1 px-1.5">${r.resource_name}</td>
          <td class="py-1 px-1.5">${r.pretreatment_method}</td>
          <td class="py-1 px-1.5">${r.analysis_param}</td>
          <td class="py-1 px-1.5 font-semibold">${r.value.toFixed(2)}%</td>
          <td class="py-1 px-1.5">${r.note || '—'}</td>
          <td class="py-1 px-1 text-right"><button onclick="removeExportRow(${i})" class="text-xs text-rose-500 hover:underline">Remove</button></td>
        </tr>
      `).join('');
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
      const cols = ['record_id', 'prepared_sample_name', 'resource_name', 'pretreatment_method', 'analysis_param', 'value', 'unit', 'qc_pass', 'data_status', 'note'];
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
      const cols = ['record_id', 'prepared_sample_name', 'resource_name', 'pretreatment_method', 'analysis_param', 'value', 'unit', 'qc_pass', 'data_status', 'note'];
      const lines = [cols.join(',')];
      exportRows.forEach(r => {
        lines.push(cols.map(c => `"${String(r[c] ?? '').replace(/"/g, '""')}"`).join(','));
      });
      const blob = new Blob([lines.join('\\n')], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'pretreatment_variance_export.csv';
      a.click();
      URL.revokeObjectURL(url);
    }

    window.addEventListener('resize', () => renderCurrentView());
    initDropdowns();
    applyUrlParams();
    setTab(currentTab);
    applyFilters();
  </script>
</body>
</html>
"""
    return (
        html.replace("__PAYLOAD_JSON__", payload_json)
        .replace("__TOTAL_OBS__", str(total_obs))
        .replace("__PORTAL_OBS__", str(portal_obs))
        .replace("__RAW_OBS__", str(raw_obs))
        .replace("__QCPASS_OBS__", str(qcpass_obs))
        .replace("__QCFAIL_OBS__", str(qcfail_obs))
        .replace("__NUM_METHODS__", str(num_methods))
        .replace("__NUM_RESOURCES__", str(num_resources))
        .replace("__NUM_SAMPLES__", str(num_samples))
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Pretreatment Variance Dashboard HTML.")
    parser.add_argument(
        "--from-snapshot",
        default=None,
        help="Path to db_snapshot.json for offline/reproducible generation without live PostgreSQL.",
    )
    parser.add_argument(
        "--output",
        default="exports/plots/conversion/pretreatment_variance_dashboard.html",
        help="Output HTML file path (default: exports/plots/conversion/pretreatment_variance_dashboard.html).",
    )
    args = parser.parse_args()

    if args.from_snapshot:
        records = load_from_snapshot(args.from_snapshot)
    else:
        records = load_from_db()

    if not records:
        print("No Pretreatment variance records found.")
        return

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html_content = build_dashboard_html(records)
    out_path.write_text(html_content, encoding="utf-8")
    print(f"Generated {out_path} ({len(records)} observations, {out_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
