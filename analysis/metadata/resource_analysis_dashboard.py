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
from collections.abc import Sequence
from copy import deepcopy
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

try:
    from analysis.metadata.resource_insights_engine import (
        DEFAULT_SIDECAR_PATH,
        build_resource_insights,
    )
except ImportError:
    from resource_insights_engine import (  # type: ignore[no-redef]
        DEFAULT_SIDECAR_PATH,
        build_resource_insights,
    )

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "exports" / "plots" / "metadata"
GITHUB_ISSUES_NEW_URL = "https://github.com/uw-ssec/ca-biositing/issues/new"


def build_github_bug_issue_url(
    title: str,
    category: str = "UI / Chart Rendering Bug",
    description: str = "",
    expected_behavior: str = "",
    page: str = "Page 1 — Characterization & AI Brief",
    resource: str = "",
    domain_tab: str = "",
    qc_filter: str = "pass",
    query_string: str = "",
    reporter_email: str = "",
    repo_issues_url: str = GITHUB_ISSUES_NEW_URL,
) -> str:
    """Build a pre-populated GitHub issue creation URL with structured diagnostic context."""
    clean_title = title.strip() or f"[BioCirV Dashboard] {category} ({resource or 'all resources'})"
    body_lines = [
        "### Bug / Issue Report — BioCirV Resource & QC Dashboard Suite",
        "",
        f"**Category:** {category}",
        "",
        "#### Description & Steps to Reproduce",
        description.strip() or "_Please describe what happened and the steps to reproduce._",
        "",
        "#### Expected Behavior",
        expected_behavior.strip() or "_Please describe what you expected to see._",
        "",
        "#### Auto-Captured Dashboard Diagnostic State",
        "| Field | Value |",
        "| :--- | :--- |",
        f"| **Dashboard Page** | `{page}` |",
        f"| **Active Resource** | `{resource or 'N/A'}` |",
        f"| **Active Domain / Tab** | `{domain_tab or 'N/A'}` |",
        f"| **Active QC Filter** | `{qc_filter or 'pass'}` |",
        f"| **URL Query String** | `{query_string or '(none)'}` |",
    ]
    if reporter_email.strip():
        body_lines.append(f"| **Reporter** | `{reporter_email.strip()}` |")
    params = urlencode(
        {
            "title": clean_title,
            "labels": "bug,dashboard-qc",
            "body": "\n".join(body_lines),
        }
    )
    return f"{repo_issues_url}?{params}"


def _normalize_qc_statuses(slice_qc_status: Sequence[str] | str | None) -> set[str] | None:
    """Normalize a QC status filter specification into a set of allowed lowercase statuses.

    Returns None when all statuses should be included.
    """
    if slice_qc_status is None:
        return None
    if isinstance(slice_qc_status, str):
        tokens = [t.strip().lower() for t in slice_qc_status.split(",") if t.strip()]
    else:
        tokens = [str(t).strip().lower() for t in slice_qc_status if str(t).strip()]
    if not tokens or "all" in tokens:
        return None
    allowed: set[str] = set()
    for token in tokens:
        if token in ("pass", "qc_pass"):
            allowed.add("pass")
        elif token in ("fail", "qc_fail"):
            allowed.add("fail")
        elif token in ("unscored", "provisional", "unknown"):
            allowed.update({"unscored", "provisional", "unknown", ""})
        else:
            allowed.add(token)
    return allowed


def load_ca_counties_lookup() -> dict[str, str]:
    """Load canonical GEOID -> County Name mapping from data/static/ca_counties.geojson."""
    lookup: dict[str, str] = {"06000": "California (Statewide)"}
    candidates = [
        REPO_ROOT / "data" / "static" / "ca_counties.geojson",
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


def _normalize_filter_list(spec: Sequence[str] | str | None) -> list[str]:
    """Normalize a filter specification into a deduplicated list of lowercase tokens.

    Returns an empty list when no filter is active (or when 'all' is specified).
    """
    if spec is None:
        return []
    raw_items = spec.split(",") if isinstance(spec, str) else list(spec)
    out: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        tok = str(item or "").strip().lower()
        if not tok or tok == "all":
            continue
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


def prepare_dashboard_payload(
    raw_payload: dict[str, Any],
    insights_sidecar: dict[str, Any],
    single_resource: str | Sequence[str] | None = None,
    exclude_analyst: bool = False,
    slice_qc_status: Sequence[str] | str | None = None,
    qc_statuses: Sequence[str] | str | None = None,
    collaborator_slice_mode: bool | None = None,
    resources: Sequence[str] | str | None = None,
    prepared_samples: Sequence[str] | str | None = None,
    field_samples: Sequence[str] | str | None = None,
    parameters: Sequence[str] | str | None = None,
    methods: Sequence[str] | str | None = None,
    slice_pages: Sequence[str] | str | None = None,
    date_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    """Filter or anonymize the payload and bundle AI insights for HTML embedding.

    Supports single-resource or multi-resource slices (`resources` / `single_resource`),
    parameter/unit, prepared_sample, field_sample, method, and date-range (`date_type`,
    `from_date`, `to_date`) filters, and dashboard page selection (`slice_pages`).
    Physically compacts `dicts` and `rows` so zero non-selected resource names, sample IDs,
    parameters, or excluded QC rows are present in the serialized HTML bundle. Preserves
    anonymous `provider` codenames as-is.
    """
    payload = deepcopy(raw_payload)
    str_cols: list[str] = payload["str_cols"]
    dicts: dict[str, list[str]] = payload["dicts"]
    effective_qc_spec = qc_statuses if qc_statuses is not None else slice_qc_status
    allowed_qc = _normalize_qc_statuses(effective_qc_spec)

    target_resources = _normalize_filter_list(resources if resources is not None else single_resource)
    target_res_set = set(target_resources)
    single_resource_val = target_resources[0] if len(target_resources) == 1 else None

    target_ps_list = _normalize_filter_list(prepared_samples)
    target_ps_set = set(target_ps_list)
    target_fs_list = _normalize_filter_list(field_samples)
    target_fs_set = set(target_fs_list)
    target_param_list = _normalize_filter_list(parameters)
    target_param_set = set(target_param_list)
    target_method_list = _normalize_filter_list(methods)
    target_method_set = set(target_method_list)

    norm_date_type = str(date_type or "any").strip().lower()
    if norm_date_type not in ("collected", "run", "any"):
        norm_date_type = "any"
    norm_from_date = str(from_date or "").strip()[:10] or None
    norm_to_date = str(to_date or "").strip()[:10] or None
    if norm_from_date and norm_to_date and norm_from_date > norm_to_date:
        norm_from_date, norm_to_date = norm_to_date, norm_from_date
    has_date_filter = bool(norm_from_date or norm_to_date)

    raw_pages = _normalize_filter_list(slice_pages)
    valid_page_order = ["char", "explorer", "qc"]
    norm_pages = [p for p in raw_pages if p in valid_page_order]

    has_any_slice_filter = bool(
        target_res_set
        or target_ps_set
        or target_fs_set
        or target_param_set
        or target_method_set
        or has_date_filter
        or norm_pages
    )
    if collaborator_slice_mode is None:
        collaborator_slice_mode = has_any_slice_filter
    if collaborator_slice_mode and not norm_pages:
        norm_pages = ["char", "explorer"]

    if exclude_analyst and "analyst" in dicts:
        dicts["analyst"] = ["—" if a not in ("Unassigned", "") else a for a in dicts["analyst"]]
        for ps in payload.get("prepared_samples", []):
            ps["preparer"] = "—"

    res_col_idx = str_cols.index("resource_name") + 1 if "resource_name" in str_cols else -1
    if target_res_set and res_col_idx > 0:
        res_dict = dicts["resource_name"]
        matching_res_indices = {i for i, name in enumerate(res_dict) if str(name).strip().lower() in target_res_set}
        payload["rows"] = [r for r in payload["rows"] if r[res_col_idx] in matching_res_indices]

    if target_ps_set and "prepared_sample" in str_cols:
        ps_col_idx = str_cols.index("prepared_sample") + 1
        ps_dict = dicts["prepared_sample"]
        matching_ps_indices = {i for i, v in enumerate(ps_dict) if str(v).strip().lower() in target_ps_set}
        payload["rows"] = [r for r in payload["rows"] if r[ps_col_idx] in matching_ps_indices]

    if target_fs_set and "field_sample" in str_cols:
        fs_col_idx = str_cols.index("field_sample") + 1
        fs_dict = dicts["field_sample"]
        matching_fs_indices = {i for i, v in enumerate(fs_dict) if str(v).strip().lower() in target_fs_set}
        payload["rows"] = [r for r in payload["rows"] if r[fs_col_idx] in matching_fs_indices]

    if target_param_set and "parameter" in str_cols:
        param_col_idx = str_cols.index("parameter") + 1
        param_dict = dicts["parameter"]
        unit_col_idx = str_cols.index("unit") + 1 if "unit" in str_cols else -1
        unit_dict = dicts.get("unit", [])

        def _row_matches_param(row: list[Any]) -> bool:
            p_str = str(param_dict[row[param_col_idx]] if row[param_col_idx] < len(param_dict) else "").strip().lower()
            if p_str in target_param_set:
                return True
            if unit_col_idx > 0 and row[unit_col_idx] < len(unit_dict):
                u_str = str(unit_dict[row[unit_col_idx]]).strip().lower()
                if u_str and f"{p_str} ({u_str})" in target_param_set:
                    return True
            return False

        payload["rows"] = [r for r in payload["rows"] if _row_matches_param(r)]

    if target_method_set:
        method_cols = [c for c in ("prep_method", "pt_method", "eh_method", "strain", "experiment") if c in str_cols]
        method_col_specs = [(str_cols.index(c) + 1, dicts.get(c, [])) for c in method_cols]

        def _row_matches_method(row: list[Any]) -> bool:
            for c_idx, c_dict in method_col_specs:
                if row[c_idx] < len(c_dict):
                    val_str = str(c_dict[row[c_idx]]).strip().lower()
                    if val_str in target_method_set:
                        return True
            return False

        if method_col_specs:
            payload["rows"] = [r for r in payload["rows"] if _row_matches_method(r)]

    if has_date_filter:
        fs_date_lookup: dict[str, str] = {}
        for fs in payload.get("field_samples", []):
            fn = str(fs.get("name") or "").strip().lower()
            cd = str(fs.get("collected_at") or "").strip()[:10]
            if fn and cd:
                fs_date_lookup[fn] = cd
        ps_date_lookup: dict[str, str] = {}
        ps_fs_lookup: dict[str, str] = {}
        for ps in payload.get("prepared_samples", []):
            pn = str(ps.get("name") or "").strip().lower()
            pd_val = str(ps.get("prep_date") or "").strip()[:10]
            fn = str(ps.get("field_sample_name") or ps.get("field_sample") or "").strip().lower()
            if pn and pd_val:
                ps_date_lookup[pn] = pd_val
            if pn and fn:
                ps_fs_lookup[pn] = fn

        ps_col_idx = str_cols.index("prepared_sample") + 1 if "prepared_sample" in str_cols else -1
        fs_col_idx = str_cols.index("field_sample") + 1 if "field_sample" in str_cols else -1
        ps_dict = dicts.get("prepared_sample", [])
        fs_dict = dicts.get("field_sample", [])
        exp_date_idx = len(str_cols) + 3

        def _date_in_range(d_val: str) -> bool:
            if not d_val:
                return False
            if norm_from_date and d_val < norm_from_date:
                return False
            if norm_to_date and d_val > norm_to_date:
                return False
            return True

        def _row_matches_date(row: list[Any]) -> bool:
            ps_name = (
                str(ps_dict[row[ps_col_idx]]).strip().lower()
                if ps_col_idx > 0 and row[ps_col_idx] < len(ps_dict)
                else ""
            )
            fs_name = (
                str(fs_dict[row[fs_col_idx]]).strip().lower()
                if fs_col_idx > 0 and row[fs_col_idx] < len(fs_dict)
                else ""
            )
            if not fs_name and ps_name in ps_fs_lookup:
                fs_name = ps_fs_lookup[ps_name]
            col_date = fs_date_lookup.get(fs_name, "")
            exp_date_raw = str(row[exp_date_idx] or "").strip()[:10] if len(row) > exp_date_idx else ""
            prep_date_raw = ps_date_lookup.get(ps_name, "")
            run_date = exp_date_raw or prep_date_raw
            if norm_date_type == "collected":
                return _date_in_range(col_date)
            if norm_date_type == "run":
                return _date_in_range(run_date) or _date_in_range(prep_date_raw)
            return _date_in_range(col_date) or _date_in_range(run_date) or _date_in_range(prep_date_raw)

        payload["rows"] = [r for r in payload["rows"] if _row_matches_date(r)]

    if allowed_qc is not None and "qc_status" in str_cols:
        qc_col_idx = str_cols.index("qc_status") + 1
        qc_dict = dicts["qc_status"]
        matching_qc_indices = {
            i for i, status_val in enumerate(qc_dict) if str(status_val).strip().lower() in allowed_qc
        }
        payload["rows"] = [r for r in payload["rows"] if r[qc_col_idx] in matching_qc_indices]

    surviving_res_set: set[str] | None = None
    if target_res_set:
        surviving_res_set = set(target_res_set)
    elif (target_ps_set or target_fs_set or target_param_set or target_method_set or has_date_filter) and res_col_idx > 0:
        res_dict = dicts["resource_name"]
        surviving_res_set = {
            str(res_dict[r[res_col_idx]]).strip().lower()
            for r in payload["rows"]
            if r[res_col_idx] < len(res_dict)
        }

    if surviving_res_set is not None:
        payload["resources"] = [
            r for r in payload.get("resources", []) if str(r.get("name", "")).strip().lower() in surviving_res_set
        ]
        payload["field_samples"] = [
            fs
            for fs in payload.get("field_samples", [])
            if str(fs.get("resource_name") or fs.get("resource") or "").strip().lower() in surviving_res_set
        ]
        payload["prepared_samples"] = [
            ps
            for ps in payload.get("prepared_samples", [])
            if str(ps.get("resource_name") or ps.get("resource") or "").strip().lower() in surviving_res_set
        ]
        payload["excluded_resources"] = [
            er for er in payload.get("excluded_resources", []) if str(er).strip().lower() in surviving_res_set
        ]
        filtered_insights = deepcopy(
            {
                k: v
                for k, v in insights_sidecar.get("resources", {}).items()
                if k.strip().lower() in surviving_res_set
            }
        )
    else:
        filtered_insights = deepcopy(insights_sidecar.get("resources", {}))

    if target_ps_set:
        payload["prepared_samples"] = [
            ps for ps in payload.get("prepared_samples", []) if str(ps.get("name", "")).strip().lower() in target_ps_set
        ]
        if not target_fs_set:
            linked_fs = {
                str(ps.get("field_sample_name") or ps.get("field_sample") or "").strip().lower()
                for ps in payload.get("prepared_samples", [])
            } - {""}
            if "field_sample" in str_cols:
                fs_col_idx = str_cols.index("field_sample") + 1
                fs_dict = dicts["field_sample"]
                linked_fs |= {
                    str(fs_dict[r[fs_col_idx]]).strip().lower()
                    for r in payload["rows"]
                    if r[fs_col_idx] < len(fs_dict)
                } - {""}
            payload["field_samples"] = [
                fs for fs in payload.get("field_samples", []) if str(fs.get("name", "")).strip().lower() in linked_fs
            ]

    if target_fs_set:
        payload["field_samples"] = [
            fs for fs in payload.get("field_samples", []) if str(fs.get("name", "")).strip().lower() in target_fs_set
        ]

    if has_date_filter and "prepared_sample" in str_cols and "field_sample" in str_cols:
        ps_col_idx = str_cols.index("prepared_sample") + 1
        fs_col_idx = str_cols.index("field_sample") + 1
        ps_dict = dicts["prepared_sample"]
        fs_dict = dicts["field_sample"]
        surviving_ps = {
            str(ps_dict[r[ps_col_idx]]).strip().lower()
            for r in payload["rows"]
            if r[ps_col_idx] < len(ps_dict)
        } - {""}
        surviving_fs = {
            str(fs_dict[r[fs_col_idx]]).strip().lower()
            for r in payload["rows"]
            if r[fs_col_idx] < len(fs_dict)
        } - {""}
        payload["prepared_samples"] = [
            ps for ps in payload.get("prepared_samples", []) if str(ps.get("name", "")).strip().lower() in surviving_ps
        ]
        for ps in payload["prepared_samples"]:
            fn = str(ps.get("field_sample_name") or ps.get("field_sample") or "").strip().lower()
            if fn:
                surviving_fs.add(fn)
        payload["field_samples"] = [
            fs for fs in payload.get("field_samples", []) if str(fs.get("name", "")).strip().lower() in surviving_fs
        ]

    if has_any_slice_filter or allowed_qc is not None or collaborator_slice_mode:
        new_dicts: dict[str, list[str]] = {}
        col_index_maps: list[dict[int, int]] = []
        for col_idx, col_name in enumerate(str_cols):
            old_list = dicts[col_name]
            used_old_indices = sorted({r[col_idx + 1] for r in payload["rows"]})
            new_list = [old_list[old_i] for old_i in used_old_indices]
            if col_name == "resource_name" and target_resources:
                existing_lower = {str(n).strip().lower() for n in new_list}
                old_by_lower = {str(n).strip().lower(): n for n in old_list}
                for tr in target_resources:
                    tr_low = str(tr).strip().lower()
                    if tr_low and tr_low not in existing_lower:
                        new_list.append(old_by_lower.get(tr_low, tr))
                        existing_lower.add(tr_low)
            new_dicts[col_name] = new_list
            col_index_maps.append({old_i: new_i for new_i, old_i in enumerate(used_old_indices)})

        remapped_rows: list[list[Any]] = []
        for r in payload["rows"]:
            new_row = [r[0]]
            for col_idx in range(len(str_cols)):
                new_row.append(col_index_maps[col_idx][r[col_idx + 1]])
            new_row.extend(r[len(str_cols) + 1 :])
            remapped_rows.append(new_row)

        dicts = new_dicts
        payload["dicts"] = dicts
        payload["rows"] = remapped_rows

    slice_qc_list = sorted(allowed_qc - {""}) if allowed_qc is not None else ["all"]

    return {
        "generated_utc": payload.get("generated_utc", ""),
        "excluded_resources": payload.get("excluded_resources", []),
        "excluded_providers": payload.get("excluded_providers", []),
        "exclude_analyst_default": exclude_analyst,
        "single_resource": single_resource_val,
        "slice_resources": target_resources,
        "slice_pages": norm_pages if norm_pages else ["char", "explorer", "qc"],
        "slice_date_type": norm_date_type,
        "slice_from_date": norm_from_date,
        "slice_to_date": norm_to_date,
        "slice_filters": {
            "resources": target_resources,
            "prepared_samples": target_ps_list,
            "field_samples": target_fs_list,
            "parameters": target_param_list,
            "methods": target_method_list,
            "date_type": norm_date_type,
            "from_date": norm_from_date,
            "to_date": norm_to_date,
        },
        "slice_qc_statuses": slice_qc_list,
        "collaborator_slice_mode": bool(collaborator_slice_mode),
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
    select, input, textarea {
      background-color: var(--card) !important;
      color: var(--foreground) !important;
      border-color: var(--border) !important;
    }
    option {
      background-color: var(--card);
      color: var(--foreground);
    }
    .hidden { display: none !important; }
    .bg-\\[var\\(--card\\)\\] { background-color: var(--card); }
    .bg-\\[var\\(--background\\)\\] { background-color: var(--background); }
    .bg-\\[var\\(--primary\\)\\] { background-color: var(--primary); }
    .bg-\\[var\\(--secondary\\)\\] { background-color: var(--secondary); }
    .text-\\[var\\(--foreground\\)\\] { color: var(--foreground); }
    .text-\\[var\\(--muted-foreground\\)\\] { color: var(--muted-foreground); }
    .text-\\[var\\(--primary-foreground\\)\\] { color: var(--primary-foreground); }
    .text-\\[var\\(--secondary-foreground\\)\\] { color: var(--secondary-foreground); }
    .border-\\[var\\(--border\\)\\] { border-color: var(--border); }
    .badge-pass { background-color: var(--pass-bg); color: var(--pass-fg); border: 1px solid var(--pass-border); }
    .badge-fail { background-color: var(--fail-bg); color: var(--fail-fg); border: 1px solid var(--fail-border); }
    .badge-info { background-color: var(--info-bg); color: var(--info-fg); border: 1px solid var(--info-border); }
    .badge-warn { background-color: var(--warn-bg); color: var(--warn-fg); border: 1px solid var(--warn-border); }
"""

SHARED_SLICE_AND_BUG_MODALS_HTML = """
  <!-- Collaborator Multi-Resource & Multi-Page Slice (.html / .csv) Export Modal -->
  <div id="modal-export-slice" class="fixed inset-0 z-50 hidden flex items-center justify-center bg-black/70 p-4">
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl max-w-xl w-full p-5 shadow-2xl space-y-3.5 max-h-[92vh] overflow-y-auto">
      <div class="flex items-start justify-between gap-3 border-b border-[var(--border)] pb-3">
        <div>
          <h2 class="text-base font-bold text-[var(--foreground)]">📤 Export Collaborator Slice (.html &amp; .csv)</h2>
          <p class="text-xs text-[var(--muted-foreground)] mt-0.5">
            Generates a standalone, zero-leakage <code>.html</code> dashboard and <code>.csv</code> dataset containing <strong>only</strong> the selected biomass resources, dashboard pages, and active filter choices.
          </p>
        </div>
        <button id="btn-close-slice-modal" class="text-xs font-bold px-2 py-1 rounded bg-[var(--secondary)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]">✕</button>
      </div>

      <div class="space-y-3 text-xs">
        <div class="space-y-1.5">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <label class="font-semibold text-[var(--foreground)]">
              1. Target Biomass Resources <span id="slice-selected-res-badge" class="font-mono text-[11px] text-[var(--primary)] ml-1">(1 selected)</span>
            </label>
            <div class="flex items-center gap-1">
              <button type="button" id="btn-slice-res-active" class="px-2 py-0.5 rounded text-[11px] font-semibold bg-[var(--secondary)] text-[var(--foreground)] border border-[var(--border)] hover:border-[var(--primary)]">Use Page Selection</button>
              <button type="button" id="btn-slice-res-all" class="px-2 py-0.5 rounded text-[11px] font-semibold bg-[var(--secondary)] text-[var(--foreground)] border border-[var(--border)] hover:border-[var(--primary)]">Select All</button>
              <button type="button" id="btn-slice-res-clear" class="px-2 py-0.5 rounded text-[11px] font-semibold bg-[var(--secondary)] text-[var(--muted-foreground)] border border-[var(--border)] hover:text-[var(--foreground)]">Clear</button>
            </div>
          </div>
          <input id="slice-modal-resource-search" type="text" placeholder="Search biomass resources..." class="w-full rounded-lg px-2.5 py-1.5 text-xs border border-[var(--border)]" />
          <div id="slice-modal-resources-list" class="max-h-36 overflow-y-auto grid grid-cols-1 sm:grid-cols-2 gap-1 p-2 rounded-lg bg-[var(--background)] border border-[var(--border)]"></div>
          <select id="slice-modal-resource" class="hidden"></select>
        </div>

        <div class="space-y-1.5">
          <div class="font-semibold text-[var(--foreground)]">2. Dashboard Pages / Views to Export</div>
          <div class="grid grid-cols-1 gap-1.5">
            <label class="flex items-center gap-2 p-2 rounded-lg bg-[var(--background)] border border-[var(--border)] cursor-pointer">
              <input id="slice-page-char" type="checkbox" value="char" checked class="slice-page-checkbox rounded" />
              <span><strong>1. Resource Characterization &amp; AI Brief</strong> <span class="badge-pass px-1.5 py-0.5 rounded font-mono text-[10px] ml-1">Default</span></span>
            </label>
            <label class="flex items-center gap-2 p-2 rounded-lg bg-[var(--background)] border border-[var(--border)] cursor-pointer">
              <input id="slice-page-explorer" type="checkbox" value="explorer" checked class="slice-page-checkbox rounded" />
              <span><strong>3. Multi-Resource Side-by-Side Explorer</strong> <span class="badge-pass px-1.5 py-0.5 rounded font-mono text-[10px] ml-1">Default</span></span>
            </label>
            <label class="flex items-center gap-2 p-2 rounded-lg bg-[var(--background)] border border-[var(--border)] cursor-pointer">
              <input id="slice-page-qc" type="checkbox" value="qc" class="slice-page-checkbox rounded" />
              <span><strong>2. Statistical Snapshot</strong> <span class="text-[var(--muted-foreground)] text-[11px]">(Optional internal QC view)</span></span>
            </label>
          </div>
        </div>

        <div class="space-y-1.5">
          <div class="font-semibold text-[var(--foreground)]">3. Active Parameter, Sample &amp; Method Filter Scope</div>
          <label class="flex items-start gap-2 p-2 rounded-lg bg-[var(--background)] border border-[var(--border)] cursor-pointer">
            <input id="slice-apply-active-filters" type="checkbox" checked class="rounded mt-0.5" />
            <div>
              <div class="font-medium text-[var(--foreground)]">Reflect active page choices for <code>parameters/units</code>, <code>prepared_samples</code>, <code>field_samples</code>, and <code>methods</code></div>
              <div class="text-[11px] text-[var(--muted-foreground)]">If specific items are selected on the page, exports only those selections; if none are selected for a filter, exports all.</div>
              <div id="slice-active-filters-summary" class="mt-1 font-mono text-[11px] text-[var(--primary)]"></div>
            </div>
          </label>
        </div>

        <div class="space-y-1.5">
          <div class="font-semibold text-[var(--foreground)]">4. Collection Date or Run / Prep Date Filter (<code>from_date</code> &mdash; <code>to_date</code>)</div>
          <div class="grid grid-cols-1 sm:grid-cols-4 gap-2 p-2 rounded-lg bg-[var(--background)] border border-[var(--border)] items-end">
            <div>
              <label for="slice-date-type" class="block text-[10px] font-semibold uppercase text-[var(--muted-foreground)] mb-0.5">Date Basis</label>
              <select id="slice-date-type" class="w-full rounded px-2 py-1 text-xs border border-[var(--border)] font-semibold">
                <option value="any">Collection or Run Date</option>
                <option value="collected">Collection Date Only</option>
                <option value="run">Run / Prep Date Only</option>
              </select>
            </div>
            <div>
              <label for="slice-from-date" class="block text-[10px] font-semibold uppercase text-[var(--muted-foreground)] mb-0.5">From Date</label>
              <input id="slice-from-date" type="date" class="w-full rounded px-2 py-1 text-xs border border-[var(--border)] font-mono" />
            </div>
            <div>
              <label for="slice-to-date" class="block text-[10px] font-semibold uppercase text-[var(--muted-foreground)] mb-0.5">To Date</label>
              <input id="slice-to-date" type="date" class="w-full rounded px-2 py-1 text-xs border border-[var(--border)] font-mono" />
            </div>
            <div>
              <button type="button" id="btn-slice-clear-dates" class="w-full px-2 py-1 rounded text-[11px] font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)]">
                Clear Dates
              </button>
            </div>
          </div>
        </div>

        <div class="space-y-1.5">
          <div class="font-semibold text-[var(--foreground)]">5. QC Status Inclusion Scope (Default: <code>qc_pass = pass</code>)</div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-1.5">
            <label class="flex items-center gap-1.5 p-2 rounded-lg bg-[var(--background)] border border-[var(--border)] cursor-pointer">
              <input id="slice-qc-pass" type="checkbox" checked class="rounded" />
              <span><code>qc_pass = pass</code></span>
            </label>
            <label class="flex items-center gap-1.5 p-2 rounded-lg bg-[var(--background)] border border-[var(--border)] cursor-pointer">
              <input id="slice-qc-fail" type="checkbox" class="rounded" />
              <span><code>qc_pass = fail</code></span>
            </label>
            <label class="flex items-center gap-1.5 p-2 rounded-lg bg-[var(--background)] border border-[var(--border)] cursor-pointer">
              <input id="slice-qc-unscored" type="checkbox" class="rounded" />
              <span>Unscored / Prov.</span>
            </label>
          </div>
        </div>

        <div class="space-y-1.5">
          <div class="font-semibold text-[var(--foreground)]">6. Collaborator Privacy &amp; Metadata</div>
          <label class="flex items-center gap-2 p-2 rounded-lg bg-[var(--background)] border border-[var(--border)] cursor-pointer">
            <input id="slice-mask-analyst" type="checkbox" checked class="rounded" />
            <span>Mask analyst emails (anonymous <code>provider_code</code> codenames are preserved as-is)</span>
          </label>
        </div>

        <div id="slice-preview-count" class="p-2.5 rounded-lg bg-[var(--background)] border border-[var(--primary)]/40 font-mono text-xs text-[var(--foreground)]"></div>
      </div>

      <div class="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
        <button id="btn-cancel-slice-modal" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">
          Cancel
        </button>
        <button id="btn-download-slice-csv-modal" class="px-3.5 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 text-white hover:opacity-90">
          ⬇ Download Sliced CSV (.csv)
        </button>
        <button id="btn-confirm-slice-export" class="px-4 py-1.5 rounded-lg text-xs font-bold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90">
          ⬇ Download Standalone Slice (.html)
        </button>
      </div>
    </div>
  </div>

  <!-- Report a Bug (GitHub Issue) Modal -->
  <div id="modal-report-bug" class="fixed inset-0 z-50 hidden flex items-center justify-center bg-black/70 p-4">
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl max-w-lg w-full p-5 shadow-2xl space-y-4">
      <div class="flex items-start justify-between gap-3 border-b border-[var(--border)] pb-3">
        <div>
          <h2 class="text-base font-bold text-[var(--foreground)]">🐛 Report a Bug / Create GitHub Issue</h2>
          <p class="text-xs text-[var(--muted-foreground)] mt-0.5">
            Automatically captures your current dashboard state and opens a pre-populated GitHub issue on <code>ca-biositing</code>.
          </p>
        </div>
        <button id="btn-close-bug-modal" class="text-xs font-bold px-2 py-1 rounded bg-[var(--secondary)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]">✕</button>
      </div>

      <div class="space-y-3 text-xs">
        <div>
          <label for="bug-modal-title" class="block font-semibold text-[var(--foreground)] mb-1">Issue Title</label>
          <input id="bug-modal-title" type="text" placeholder="e.g., Unexpected ash % closure on prepared sample..." class="w-full rounded-lg px-3 py-2 text-xs border border-[var(--border)]" />
        </div>

        <div>
          <label for="bug-modal-category" class="block font-semibold text-[var(--foreground)] mb-1">Category</label>
          <select id="bug-modal-category" class="w-full rounded-lg px-3 py-2 text-xs font-semibold border border-[var(--border)]">
            <option value="UI / Chart Rendering Bug">UI / Chart Rendering Bug</option>
            <option value="Data / Stoichiometric Calculation Issue">Data / Stoichiometric Calculation Issue</option>
            <option value="QC Flag / Statistical Threshold Issue">QC Flag / Statistical Threshold Issue</option>
            <option value="Google Sheets Write-Back / Sync Issue">Google Sheets Write-Back / Sync Issue</option>
            <option value="Feature Request / UX Improvement">Feature Request / UX Improvement</option>
          </select>
        </div>

        <div>
          <label for="bug-modal-desc" class="block font-semibold text-[var(--foreground)] mb-1">Description &amp; Steps to Reproduce</label>
          <textarea id="bug-modal-desc" rows="3" placeholder="Describe what looks wrong or how to trigger the issue..." class="w-full rounded-lg px-3 py-2 text-xs border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)]"></textarea>
        </div>

        <div>
          <label for="bug-modal-expected" class="block font-semibold text-[var(--foreground)] mb-1">Expected Behavior</label>
          <textarea id="bug-modal-expected" rows="2" placeholder="What should happen instead?" class="w-full rounded-lg px-3 py-2 text-xs border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)]"></textarea>
        </div>

        <div>
          <div class="font-semibold text-[var(--muted-foreground)] mb-1">Auto-Captured Diagnostic Context</div>
          <pre id="bug-modal-diagnostics" class="p-2.5 rounded-lg bg-[var(--background)] border border-[var(--border)] font-mono text-[11px] text-[var(--muted-foreground)] whitespace-pre-wrap overflow-x-auto"></pre>
        </div>
        <div id="bug-modal-status" class="hidden text-xs font-mono p-2 rounded-lg"></div>
      </div>

      <div class="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
        <button id="btn-cancel-bug-modal" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">
          Cancel
        </button>
        <button id="btn-submit-github-api" class="px-4 py-1.5 rounded-lg text-xs font-bold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90">
          🚀 Submit Issue
        </button>
        <button id="btn-submit-github-url" style="display:none;" class="hidden px-4 py-1.5 rounded-lg text-xs font-bold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90">
          🚀 Open Pre-Filled GitHub Issue &rarr;
        </button>
      </div>
    </div>
  </div>

  <!-- Google OAuth / Analyst Identity Sign-In Modal -->
  <div id="modal-analyst-signin" class="fixed inset-0 z-50 hidden flex items-center justify-center bg-black/70 p-4">
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl max-w-md w-full p-5 shadow-2xl space-y-4">
      <div class="flex items-start justify-between gap-3 border-b border-[var(--border)] pb-3">
        <div>
          <h2 class="text-base font-bold text-[var(--foreground)]">🔐 Analyst Identity &amp; Google Sign-In</h2>
          <p class="text-xs text-[var(--muted-foreground)] mt-0.5">
            Sign in to attribute QC status flips, review queue approvals, task assignments, and Google Sheets write-backs.
          </p>
        </div>
        <button id="btn-close-signin-modal" class="text-xs font-bold px-2 py-1 rounded bg-[var(--secondary)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]">✕</button>
      </div>

      <div class="space-y-3 text-xs">
        <div id="gsi-button-container" class="hidden flex justify-center py-1"></div>
        <div>
          <label for="signin-analyst-email" class="block font-semibold text-[var(--foreground)] mb-1">Analyst Email Address</label>
          <input id="signin-analyst-email" type="email" placeholder="analyst@lbl.gov" class="w-full rounded-lg px-3 py-2 text-xs font-mono border border-[var(--border)]" />
        </div>
        <div>
          <label for="signin-analyst-name" class="block font-semibold text-[var(--foreground)] mb-1">Display Name (optional)</label>
          <input id="signin-analyst-name" type="text" placeholder="e.g., BioCirV QC Lead" class="w-full rounded-lg px-3 py-2 text-xs border border-[var(--border)]" />
        </div>
        <div>
          <label for="signin-api-base" class="block font-semibold text-[var(--muted-foreground)] mb-1">QC Review API Endpoint (<code>/v1/qc</code>)</label>
          <input id="signin-api-base" type="text" placeholder="http://localhost:8000" class="w-full rounded-lg px-3 py-1.5 text-xs font-mono border border-[var(--border)]" />
        </div>
        <div id="signin-sync-status" class="p-2 rounded-lg bg-[var(--background)] border border-[var(--border)] font-mono text-[11px] text-[var(--muted-foreground)]"></div>
      </div>

      <div class="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
        <button id="btn-cancel-signin-modal" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">
          Cancel
        </button>
        <button id="btn-save-signin-modal" class="px-4 py-1.5 rounded-lg text-xs font-bold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90">
          ✓ Save Analyst Session
        </button>
      </div>
    </div>
  </div>

  <!-- + Submit Audit Finding Modal (Ad-Hoc or Record/Group QC Review Queue Submission) -->
  <div id="modal-submit-finding" class="fixed inset-0 z-50 hidden flex items-center justify-center bg-black/70 p-4">
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl max-w-xl w-full p-5 shadow-2xl space-y-4 max-h-[92vh] overflow-y-auto">
      <div class="flex items-start justify-between gap-3 border-b border-[var(--border)] pb-3">
        <div>
          <h2 class="text-base font-bold text-[var(--foreground)]">📝 Submit Audit Finding to QC Review Queue</h2>
          <p class="text-xs text-[var(--muted-foreground)] mt-0.5">
            Choose whether your audit finding applies to the <strong>Entire Replicate Group</strong> or a <strong>Single Data Point</strong>, or log a general resource observation.
          </p>
        </div>
        <button id="btn-close-finding-modal" class="text-xs font-bold px-2 py-1 rounded bg-[var(--secondary)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]">✕</button>
      </div>

      <!-- Interactive Prompt: Entire Replicate Group vs. Single Data Point -->
      <div id="finding-scope-prompt-banner" class="bg-[var(--background)] border-2 border-[var(--primary)]/50 rounded-xl p-3.5 space-y-2.5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="text-xs font-bold uppercase tracking-wider text-[var(--primary)]">⚖️ Apply Audit Finding To:</span>
          <span id="finding-scope-context-pill" class="text-[11px] font-mono text-[var(--muted-foreground)]">Select target scope below</span>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <button type="button" id="finding-scope-btn-group" data-scope-choice="group" class="text-left p-2.5 rounded-lg border-2 border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)] transition-all">
            <div class="flex items-center justify-between gap-1">
              <span class="text-xs font-bold text-[var(--foreground)]">📦 Entire Replicate Group</span>
              <span id="finding-scope-group-badge" class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)]">All Replicates</span>
            </div>
            <p id="finding-scope-group-summary" class="text-[11px] text-[var(--muted-foreground)] mt-1 font-mono">
              Flags all sibling replicates for this sample, experiment &amp; parameter.
            </p>
          </button>
          <button type="button" id="finding-scope-btn-single" data-scope-choice="single" class="text-left p-2.5 rounded-lg border-2 border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)] transition-all">
            <div class="flex items-center justify-between gap-1">
              <span class="text-xs font-bold text-[var(--foreground)]">🎯 Single Point Only</span>
              <span id="finding-scope-single-badge" class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)]">1 Record</span>
            </div>
            <p id="finding-scope-single-summary" class="text-[11px] text-[var(--muted-foreground)] mt-1 font-mono">
              Flags only the selected observation <code>record_id</code>.
            </p>
          </button>
        </div>
        <div id="finding-scope-replicates-wrap" class="hidden pt-1.5 border-t border-[var(--border)] space-y-1">
          <div class="flex items-center justify-between text-[11px] text-[var(--muted-foreground)]">
            <span>Replicates in group (click a chip to target a specific replicate):</span>
            <span id="finding-scope-target-count" class="font-mono font-semibold text-[var(--foreground)]"></span>
          </div>
          <div id="finding-scope-replicates-list" class="flex flex-wrap gap-1.5"></div>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
        <div>
          <label for="finding-modal-resource" class="block font-semibold text-[var(--foreground)] mb-1">Target Resource</label>
          <select id="finding-modal-resource" class="w-full rounded-lg px-2.5 py-2 text-xs font-semibold border border-[var(--border)]"></select>
        </div>
        <div>
          <label for="finding-modal-scope" class="block font-semibold text-[var(--foreground)] mb-1">Finding Scope</label>
          <select id="finding-modal-scope" class="w-full rounded-lg px-2.5 py-2 text-xs font-semibold border border-[var(--border)]">
            <option value="group">Whole Replicate Group (All Replicates)</option>
            <option value="single">Single Observation (Specific record_id)</option>
            <option value="finding">Ad-Hoc Observation / Resource Finding</option>
          </select>
        </div>
        <div>
          <label for="finding-modal-domain" class="block font-semibold text-[var(--foreground)] mb-1">Analytical Domain</label>
          <select id="finding-modal-domain" class="w-full rounded-lg px-2.5 py-2 text-xs font-semibold border border-[var(--border)]">
            <option value="proximate">Proximate Analysis</option>
            <option value="ultimate">Ultimate / Elemental</option>
            <option value="compositional">Compositional</option>
            <option value="ash">Ash &amp; XRF Minerals</option>
            <option value="icp">ICP Trace Metals</option>
            <option value="calorimetry">Calorimetry (HHV/LHV)</option>
            <option value="ftnir">FT-NIR Spectroscopy</option>
            <option value="xrd">XRD Crystallinity</option>
            <option value="fermentation">Fermentation</option>
            <option value="pretreatment">Pretreatment</option>
            <option value="general">General / Cross-Domain</option>
          </select>
        </div>
        <div>
          <label for="finding-modal-parameter" class="block font-semibold text-[var(--foreground)] mb-1">Parameter Name</label>
          <input id="finding-modal-parameter" type="text" placeholder="e.g., moisture, ash, glucan, or Resource-Level Observation" class="w-full rounded-lg px-2.5 py-2 text-xs font-mono border border-[var(--border)]" />
        </div>
        <div>
          <label for="finding-modal-record-id" class="block font-semibold text-[var(--foreground)] mb-1">Target <code>record_id</code>(s)</label>
          <input id="finding-modal-record-id" type="text" placeholder="e.g., aim1-prox-0042 (or pipe-separated group IDs)" class="w-full rounded-lg px-2.5 py-2 text-xs font-mono border border-[var(--border)]" />
        </div>
        <div>
          <label for="finding-modal-qc-status" class="block font-semibold text-[var(--foreground)] mb-1">Recommended QC Status</label>
          <select id="finding-modal-qc-status" class="w-full rounded-lg px-2.5 py-2 text-xs font-semibold border border-[var(--border)]">
            <option value="provisional" selected>provisional — Flagged for Analyst / PI Review (Default)</option>
            <option value="fail">qc_fail — Exclude from Portal Slice</option>
            <option value="pass">qc_pass — Verified Valid Replicate</option>
            <option value="re_assay">re_assay — Flag for Bench Re-Assay</option>
          </select>
        </div>
      </div>

      <div class="space-y-3 text-xs">
        <div>
          <label for="finding-modal-assigned-email" class="block font-semibold text-[var(--foreground)] mb-1">Assign Review Task to Email Address (optional)</label>
          <input id="finding-modal-assigned-email" type="email" placeholder="colleague@lbl.gov (assigns this finding in the Review Queue)" class="w-full rounded-lg px-3 py-2 text-xs font-mono border border-[var(--border)]" />
        </div>

        <div>
          <span class="block font-semibold text-[var(--foreground)] mb-1">Quick Rationale Tags</span>
          <div id="finding-modal-chips" class="flex flex-wrap gap-1.5">
            <button type="button" data-chip="Suspect Moisture / Dry Basis" class="finding-rationale-chip px-2 py-1 rounded-md text-[11px] font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">Suspect Moisture / Dry Basis</button>
            <button type="button" data-chip="High Replicate RSD (>20%)" class="finding-rationale-chip px-2 py-1 rounded-md text-[11px] font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">High Replicate RSD (&gt;20%)</button>
            <button type="button" data-chip="Unit / Basis Mixup" class="finding-rationale-chip px-2 py-1 rounded-md text-[11px] font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">Unit / Basis Mixup</button>
            <button type="button" data-chip="Out-of-Envelope Value" class="finding-rationale-chip px-2 py-1 rounded-md text-[11px] font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">Out-of-Envelope Value</button>
            <button type="button" data-chip="Instrument / Calibration Drift" class="finding-rationale-chip px-2 py-1 rounded-md text-[11px] font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">Instrument / Calibration Drift</button>
            <button type="button" data-chip="Sample Prep / Contamination" class="finding-rationale-chip px-2 py-1 rounded-md text-[11px] font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">Sample Prep / Contamination</button>
          </div>
        </div>

        <div>
          <label for="finding-modal-note" class="block font-semibold text-[var(--foreground)] mb-1">Audit Finding Note / Observations</label>
          <textarea id="finding-modal-note" rows="3" placeholder="e.g., This moisture value looks abnormally high compared to peer replicates — please verify raw bench sheet." class="w-full rounded-lg px-3 py-2 text-xs border border-[var(--border)]"></textarea>
        </div>

        <label class="flex items-center gap-2 cursor-pointer text-[var(--muted-foreground)]">
          <input id="finding-modal-gsheet-sync" type="checkbox" checked class="rounded" />
          <span>Request Google Sheets write-back when approved in the Review Queue</span>
        </label>

        <div id="finding-modal-status" class="hidden p-2.5 rounded-lg text-xs font-mono"></div>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[var(--border)]">
        <div class="flex flex-wrap items-center gap-2">
          <button id="btn-finding-open-github" type="button" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] border border-[var(--border)]">
            🚀 Open GitHub Issue
          </button>
          <button id="btn-finding-export-workbench" type="button" class="px-3 py-1.5 rounded-lg text-xs font-semibold badge-warn hover:opacity-90">
            ⚖️ Export to Audit Workbench
          </button>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button id="btn-cancel-finding-modal" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">
            Cancel
          </button>
          <button id="btn-confirm-submit-finding" class="px-4 py-1.5 rounded-lg text-xs font-bold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90">
            📥 Submit to Review Queue
          </button>
        </div>
      </div>
    </div>
  </div>
"""

SHARED_SLICE_AND_BUG_MODALS_JS = """
    var GITHUB_ISSUES_NEW_URL = "https://github.com/uw-ssec/ca-biositing/issues/new";

    function buildGitHubBugIssueUrl(opts) {
      const repoNewUrl = GITHUB_ISSUES_NEW_URL || "https://github.com/uw-ssec/ca-biositing/issues/new";
      const o = opts || {};
      const cat = o.category || "UI / Chart Rendering Bug";
      const res = o.resource || (typeof state !== "undefined" && state.resource) || "all resources";
      const cleanTitle = (o.title || "").trim() || `[BioCirV Dashboard] ${cat} (${res})`;
      const bodyLines = [
        "### Bug / Issue Report — BioCirV Resource & QC Dashboard Suite",
        "",
        `**Category:** ${cat}`,
        "",
        "#### Description & Steps to Reproduce",
        (o.description || "").trim() || "_Please describe what happened and the steps to reproduce._",
        "",
        "#### Expected Behavior",
        (o.expectedBehavior || "").trim() || "_Please describe what you expected to see._",
        "",
        "#### Auto-Captured Dashboard Diagnostic State",
        "| Field | Value |",
        "| :--- | :--- |",
        `| **Dashboard Page** | \\`${o.page || document.title}\\` |`,
        `| **Active Resource** | \\`${res}\\` |`,
        `| **Active Domain / Tab** | \\`${o.domainTab || "overview"}\\` |`,
        `| **Active QC Filter** | \\`${o.qcFilter || "pass"}\\` |`,
        `| **URL Query String** | \\`${o.queryString || window.location.search || "(none)"}\\` |`
      ];
      if (o.reporterEmail) {
        bodyLines.push(`| **Reporter** | \\`${o.reporterEmail}\\` |`);
      }
      const params = new URLSearchParams({
        title: cleanTitle,
        labels: "bug,dashboard-qc",
        body: bodyLines.join("\\n")
      });
      return `${repoNewUrl}?${params.toString()}`;
    }
    window.buildGitHubBugIssueUrl = buildGitHubBugIssueUrl;

    function normalizeFilterTokenArray(spec) {
      if (!spec) return [];
      const arr = Array.isArray(spec) ? spec : (spec instanceof Set ? Array.from(spec) : String(spec).split(","));
      const out = [];
      const seen = new Set();
      arr.forEach(item => {
        const tok = String(item || "").trim().toLowerCase();
        if (!tok || tok === "all") return;
        if (!seen.has(tok)) {
          seen.add(tok);
          out.push(tok);
        }
      });
      return out;
    }

    var DEFAULT_FILTER_START_DATE = "2024-01-01";
    window.DEFAULT_FILTER_START_DATE = DEFAULT_FILTER_START_DATE;
    window.DEFAULT_PICKER_START_DATE = DEFAULT_FILTER_START_DATE;

    function normalizeDateRange(fromDt, toDt) {
      let f = String(fromDt || "").trim().slice(0, 10);
      let t = String(toDt || "").trim().slice(0, 10);
      if (f && !/^\\d{4}-\\d{2}-\\d{2}$/.test(f)) f = "";
      if (t && !/^\\d{4}-\\d{2}-\\d{2}$/.test(t)) t = "";
      if (f && t && f > t) {
        const tmp = f;
        f = t;
        t = tmp;
      }
      return { from: f, to: t, hasFilter: Boolean(f || t) };
    }
    window.normalizeDateRange = normalizeDateRange;

    function recordMatchesDateFilter(r, dtType, fromDt, toDt) {
      const range = normalizeDateRange(fromDt, toDt);
      if (!range.hasFilter) return true;
      const mode = ["collected", "run", "any"].includes(String(dtType || "any").trim().toLowerCase())
        ? String(dtType || "any").trim().toLowerCase()
        : "any";
      const isIsoDate = d => Boolean(d && /^\\d{4}-\\d{2}-\\d{2}$/.test(d));
      const rawCol = (r && (r.collected_date || r.collected_at)) ? String(r.collected_date || r.collected_at).trim().slice(0, 10) : "";
      const rawExp = (r && r.exp_date) ? String(r.exp_date).trim().slice(0, 10) : "";
      const rawPrep = (r && r.prep_date) ? String(r.prep_date).trim().slice(0, 10) : "";
      const cDate = isIsoDate(rawCol) ? rawCol : "";
      const rDate = isIsoDate(rawExp) ? rawExp : (isIsoDate(rawPrep) ? rawPrep : "");
      const inRange = d => {
        if (!isIsoDate(d)) return false;
        if (range.from && d < range.from) return false;
        if (range.to && d > range.to) return false;
        return true;
      };
      if (mode === "collected") return inRange(cDate);
      if (mode === "run") return inRange(rDate) || inRange(rawPrep);
      return inRange(cDate) || inRange(rDate) || inRange(rawPrep);
    }
    window.recordMatchesDateFilter = recordMatchesDateFilter;

    function initDateFilterInputs(fromEl, toEl, typeEl, clearBtnEl, onChangeFn) {
      if (typeof clearBtnEl === "function" && onChangeFn === undefined) {
        onChangeFn = clearBtnEl;
        clearBtnEl = typeEl;
        typeEl = null;
      }
      const resolveEl = (el) => (typeof el === "string" ? document.getElementById(el) : el);
      fromEl = resolveEl(fromEl);
      toEl = resolveEl(toEl);
      typeEl = resolveEl(typeEl);
      clearBtnEl = resolveEl(clearBtnEl);

      let lastClearedAt = 0;
      const syncClearBtnVisibility = () => {
        if (clearBtnEl && clearBtnEl.classList) {
          const hasDate = Boolean((fromEl && fromEl.value) || (toEl && toEl.value));
          clearBtnEl.classList.toggle("hidden", !hasDate);
        }
      };
      const fireChange = () => {
        syncClearBtnVisibility();
        if (typeof onChangeFn === "function") {
          onChangeFn(
            fromEl ? (fromEl.value || "") : "",
            toEl ? (toEl.value || "") : "",
            typeEl ? (typeEl.value || "any") : "any"
          );
        }
      };
      if (fromEl && typeof fromEl.setAttribute === "function") {
        const defaultStartDate = DEFAULT_FILTER_START_DATE || "2024-01-01";
        fromEl.setAttribute("min", "2020-01-01");
        fromEl.setAttribute("placeholder", defaultStartDate);
        const seedDefaultStartDate = () => {
          if (!fromEl.value && (Date.now() - lastClearedAt > 350)) {
            fromEl.value = defaultStartDate;
            fireChange();
          }
        };
        fromEl.addEventListener("mousedown", seedDefaultStartDate);
        fromEl.addEventListener("focus", seedDefaultStartDate);
        fromEl.addEventListener("input", fireChange);
        fromEl.addEventListener("change", fireChange);
      }
      if (toEl && typeof toEl.setAttribute === "function") {
        toEl.setAttribute("min", "2020-01-01");
        toEl.addEventListener("input", fireChange);
        toEl.addEventListener("change", fireChange);
      }
      if (typeEl && typeof typeEl.addEventListener === "function") {
        typeEl.addEventListener("input", fireChange);
        typeEl.addEventListener("change", fireChange);
      }
      if (clearBtnEl && typeof clearBtnEl.addEventListener === "function") {
        clearBtnEl.addEventListener("click", (e) => {
          e.preventDefault();
          lastClearedAt = Date.now();
          if (fromEl) fromEl.value = "";
          if (toEl) toEl.value = "";
          if (typeEl) typeEl.value = "any";
          fireChange();
        });
      }
      syncClearBtnVisibility();
    }
    window.initDateFilterInputs = initDateFilterInputs;

    function buildClientSideSlicedBundle(baseBundle, targetRes, qcStatuses, maskAnalyst, extraFilters, selectedPages) {
      if (targetRes && typeof targetRes === "object" && !Array.isArray(targetRes) && !(targetRes instanceof Set)) {
        const optsObj = targetRes;
        targetRes = optsObj.resources || optsObj.selectedResources || optsObj.resource || optsObj.targetRes || [];
        qcStatuses = qcStatuses !== undefined ? qcStatuses : (optsObj.qcStatuses || optsObj.qc_statuses || ["pass"]);
        maskAnalyst = maskAnalyst !== undefined ? maskAnalyst : (optsObj.maskAnalyst !== undefined ? optsObj.maskAnalyst : optsObj.exclude_analyst_default);
        extraFilters = extraFilters || optsObj.extraFilters || optsObj.filters || optsObj;
        selectedPages = selectedPages || optsObj.selectedPages || optsObj.pages;
      }
      const ef = extraFilters || {};
      let targetResources = normalizeFilterTokenArray(targetRes);
      if (targetResources.length === 0 && (ef.resources || ef.selectedResources || ef.resource)) {
        targetResources = normalizeFilterTokenArray(ef.resources || ef.selectedResources || ef.resource);
      }
      const targetResSet = new Set(targetResources);
      const allowedSet = new Set();
      const qcStatusList = Array.isArray(qcStatuses)
        ? qcStatuses
        : (typeof qcStatuses === "string" && qcStatuses.trim() ? [qcStatuses.trim()] : ["pass"]);
      qcStatusList.forEach(s => {
        const tok = String(s).trim().toLowerCase();
        if (tok === "all") {
          ["pass", "fail", "unscored", "provisional", "unknown", ""].forEach(v => allowedSet.add(v));
        } else if (tok === "pass" || tok === "qc_pass") allowedSet.add("pass");
        else if (tok === "fail" || tok === "qc_fail") allowedSet.add("fail");
        else if (tok === "unscored" || tok === "provisional" || tok === "unknown") {
          allowedSet.add("unscored");
          allowedSet.add("provisional");
          allowedSet.add("unknown");
          allowedSet.add("");
        } else if (tok) allowedSet.add(tok);
      });

      const psFilterList = normalizeFilterTokenArray(ef.prepared_samples || ef.preparedSamples);
      const psFilterSet = new Set(psFilterList);
      const fsFilterList = normalizeFilterTokenArray(ef.field_samples || ef.fieldSamples);
      const fsFilterSet = new Set(fsFilterList);
      const paramFilterList = normalizeFilterTokenArray(ef.parameters);
      const paramFilterSet = new Set(paramFilterList);
      const methodFilterList = normalizeFilterTokenArray(ef.methods);
      const methodFilterSet = new Set(methodFilterList);

      const rawDateType = String(ef.date_type || ef.dateType || "any").trim().toLowerCase();
      const normDateType = ["collected", "run", "any"].includes(rawDateType) ? rawDateType : "any";
      const normRange = normalizeDateRange(ef.from_date || ef.fromDate || "", ef.to_date || ef.toDate || "");
      const normFromDate = normRange.from || null;
      const normToDate = normRange.to || null;
      const hasDateFilter = normRange.hasFilter;

      const pageOrder = ["char", "explorer", "qc"];
      const normPages = normalizeFilterTokenArray(selectedPages).filter(p => pageOrder.includes(p));
      const effectivePages = normPages.length ? normPages : ["char", "explorer"];

      const strCols = (baseBundle.str_cols || []).slice();
      const origDicts = JSON.parse(JSON.stringify(baseBundle.dicts || {}));
      if (maskAnalyst && origDicts.analyst) {
        origDicts.analyst = origDicts.analyst.map(a => (a !== "Unassigned" && a !== "") ? "—" : a);
      }

      const resColIdx = strCols.indexOf("resource_name") + 1;
      const qcColIdx = strCols.indexOf("qc_status") + 1;
      const psColIdx = strCols.indexOf("prepared_sample") + 1;
      const fsColIdx = strCols.indexOf("field_sample") + 1;
      const paramColIdx = strCols.indexOf("parameter") + 1;
      const unitColIdx = strCols.indexOf("unit") + 1;
      const methodColIndices = ["prep_method", "pt_method", "eh_method", "strain", "experiment"]
        .map(c => ({ name: c, idx: strCols.indexOf(c) + 1, dict: origDicts[c] || [] }))
        .filter(spec => spec.idx > 0);

      const fsDateLookup = {};
      (baseBundle.field_samples || []).forEach(fs => {
        const fn = String(fs.name || "").trim().toLowerCase();
        const cd = String(fs.collected_at || "").trim().slice(0, 10);
        if (fn && cd) fsDateLookup[fn] = cd;
      });
      const psDateLookup = {};
      const psFsLookup = {};
      (baseBundle.prepared_samples || []).forEach(ps => {
        const pn = String(ps.name || "").trim().toLowerCase();
        const pdVal = String(ps.prep_date || "").trim().slice(0, 10);
        const fn = String(ps.field_sample_name || ps.field_sample || "").trim().toLowerCase();
        if (pn && pdVal) psDateLookup[pn] = pdVal;
        if (pn && fn) psFsLookup[pn] = fn;
      });

      const matchingResIdx = new Set();
      (origDicts.resource_name || []).forEach((n, idx) => {
        const normName = String(n).trim().toLowerCase();
        if (targetResSet.size === 0 || targetResSet.has(normName)) {
          matchingResIdx.add(idx);
        }
      });

      const matchingQcIdx = new Set();
      (origDicts.qc_status || []).forEach((q, idx) => {
        if (allowedSet.has(String(q).trim().toLowerCase())) matchingQcIdx.add(idx);
      });

      const matchingPsIdx = new Set();
      if (psFilterSet.size > 0 && psColIdx > 0) {
        (origDicts.prepared_sample || []).forEach((v, idx) => {
          if (psFilterSet.has(String(v).trim().toLowerCase())) matchingPsIdx.add(idx);
        });
      }

      const matchingFsIdx = new Set();
      if (fsFilterSet.size > 0 && fsColIdx > 0) {
        (origDicts.field_sample || []).forEach((v, idx) => {
          if (fsFilterSet.has(String(v).trim().toLowerCase())) matchingFsIdx.add(idx);
        });
      }

      const paramDict = origDicts.parameter || [];
      const unitDict = origDicts.unit || [];
      const rowMatchesParam = (r) => {
        if (paramFilterSet.size === 0 || paramColIdx <= 0) return true;
        const pVal = String(paramDict[r[paramColIdx]] || "").trim().toLowerCase();
        if (paramFilterSet.has(pVal)) return true;
        const uVal = unitColIdx > 0 ? String(unitDict[r[unitColIdx]] || "").trim().toLowerCase() : "";
        if (uVal && paramFilterSet.has(`${pVal} (${uVal})`)) return true;
        return false;
      };

      const rowMatchesMethod = (r) => {
        if (methodFilterSet.size === 0 || methodColIndices.length === 0) return true;
        for (let i = 0; i < methodColIndices.length; i++) {
          const spec = methodColIndices[i];
          const mVal = String(spec.dict[r[spec.idx]] || "").trim().toLowerCase();
          if (methodFilterSet.has(mVal)) return true;
        }
        return false;
      };

      const psDictOrig = origDicts.prepared_sample || [];
      const fsDictOrig = origDicts.field_sample || [];
      const expDateColIdx = strCols.length + 3;
      const dateInRange = (dStr) => {
        if (!dStr) return false;
        if (normFromDate && dStr < normFromDate) return false;
        if (normToDate && dStr > normToDate) return false;
        return true;
      };
      const rowMatchesDate = (r) => {
        if (!hasDateFilter) return true;
        const psName = psColIdx > 0 ? String(psDictOrig[r[psColIdx]] || "").trim().toLowerCase() : "";
        let fsName = fsColIdx > 0 ? String(fsDictOrig[r[fsColIdx]] || "").trim().toLowerCase() : "";
        if (!fsName && psName && psFsLookup[psName]) fsName = psFsLookup[psName];
        const colDate = fsDateLookup[fsName] || "";
        const expDateRaw = r.length > expDateColIdx ? String(r[expDateColIdx] || "").trim().slice(0, 10) : "";
        const prepDateRaw = psDateLookup[psName] || "";
        const runDate = expDateRaw || prepDateRaw;
        if (normDateType === "collected") return dateInRange(colDate);
        if (normDateType === "run") return dateInRange(runDate) || dateInRange(prepDateRaw);
        return dateInRange(colDate) || dateInRange(runDate) || dateInRange(prepDateRaw);
      };

      const filteredRows = (baseBundle.rows || []).filter(r => {
        if (resColIdx > 0 && !matchingResIdx.has(r[resColIdx])) return false;
        if (qcColIdx > 0 && !matchingQcIdx.has(r[qcColIdx])) return false;
        if (psFilterSet.size > 0 && psColIdx > 0 && !matchingPsIdx.has(r[psColIdx])) return false;
        if (fsFilterSet.size > 0 && fsColIdx > 0 && !matchingFsIdx.has(r[fsColIdx])) return false;
        if (!rowMatchesParam(r)) return false;
        if (!rowMatchesMethod(r)) return false;
        if (!rowMatchesDate(r)) return false;
        return true;
      });

      const newDicts = {};
      const colIndexMaps = [];
      strCols.forEach((colName, colIdx) => {
        const oldList = origDicts[colName] || [];
        const usedSet = new Set(filteredRows.map(r => r[colIdx + 1]));
        const usedOld = Array.from(usedSet).sort((a, b) => a - b);
        let newList = usedOld.map(oldI => oldList[oldI]);
        if (colName === "resource_name" && targetResources.length > 0) {
          const existingLower = new Set(newList.map(n => String(n || "").trim().toLowerCase()));
          const oldByLower = {};
          oldList.forEach(n => { oldByLower[String(n || "").trim().toLowerCase()] = n; });
          targetResources.forEach(tr => {
            const trLow = String(tr || "").trim().toLowerCase();
            if (trLow && !existingLower.has(trLow)) {
              newList.push(oldByLower[trLow] || tr);
              existingLower.add(trLow);
            }
          });
        }
        newDicts[colName] = newList;
        const idxMap = {};
        usedOld.forEach((oldI, newI) => { idxMap[oldI] = newI; });
        colIndexMaps.push(idxMap);
      });

      const remappedRows = filteredRows.map(r => {
        const nr = [r[0]];
        for (let i = 0; i < strCols.length; i++) {
          nr.push(colIndexMaps[i][r[i + 1]]);
        }
        for (let j = strCols.length + 1; j < r.length; j++) {
          nr.push(r[j]);
        }
        return nr;
      });

      const survivingResSet = targetResSet.size > 0
        ? targetResSet
        : new Set((newDicts.resource_name || []).map(n => String(n).trim().toLowerCase()));

      const survivingPsByDate = hasDateFilter
        ? new Set((newDicts.prepared_sample || []).map(n => String(n || "").trim().toLowerCase()).filter(Boolean))
        : null;

      let preparedSamples = JSON.parse(JSON.stringify(
        (baseBundle.prepared_samples || []).filter(ps => {
          const rName = String(ps.resource_name || ps.resource || "").trim().toLowerCase();
          if (survivingResSet.size > 0 && !survivingResSet.has(rName)) return false;
          const psName = String(ps.name || "").trim().toLowerCase();
          if (psFilterSet.size > 0 && !psFilterSet.has(psName)) return false;
          if (survivingPsByDate && !survivingPsByDate.has(psName)) return false;
          return true;
        })
      ));
      if (maskAnalyst) {
        preparedSamples.forEach(ps => { ps.preparer = "—"; });
      }

      const linkedFsNames = new Set();
      if ((psFilterSet.size > 0 || hasDateFilter) && fsFilterSet.size === 0) {
        preparedSamples.forEach(ps => {
          const fn = String(ps.field_sample_name || ps.field_sample || "").trim().toLowerCase();
          if (fn) linkedFsNames.add(fn);
        });
        (newDicts.field_sample || []).forEach(fn => {
          const normFn = String(fn || "").trim().toLowerCase();
          if (normFn) linkedFsNames.add(normFn);
        });
      }

      let fieldSamples = JSON.parse(JSON.stringify(
        (baseBundle.field_samples || []).filter(fs => {
          const rName = String(fs.resource_name || fs.resource || "").trim().toLowerCase();
          if (survivingResSet.size > 0 && !survivingResSet.has(rName)) return false;
          const fsName = String(fs.name || "").trim().toLowerCase();
          if (fsFilterSet.size > 0 && !fsFilterSet.has(fsName)) return false;
          if ((psFilterSet.size > 0 || hasDateFilter) && fsFilterSet.size === 0 && linkedFsNames.size > 0 && !linkedFsNames.has(fsName)) return false;
          return true;
        })
      ));

      const resources = JSON.parse(JSON.stringify(
        (baseBundle.resources || []).filter(r => {
          const rName = String((r && typeof r === "object" ? r.name : r) || "").trim().toLowerCase();
          return survivingResSet.size === 0 || survivingResSet.has(rName);
        })
      ));
      const excludedResources = (baseBundle.excluded_resources || []).filter(er => {
        const rName = String(er || "").trim().toLowerCase();
        return survivingResSet.size === 0 || survivingResSet.has(rName);
      });
      const nonResourceInsightKeys = new Set([
        "schema_version",
        "generated_at",
        "generated_utc",
        "model_metadata",
        "catalog_medians"
      ]);
      const filteredInsights = {};
      if (baseBundle.insights && typeof baseBundle.insights === "object") {
        Object.keys(baseBundle.insights).forEach(k => {
          const val = baseBundle.insights[k];
          if (k === "resources" && val && typeof val === "object" && !Array.isArray(val)) {
            const subRes = {};
            Object.keys(val).forEach(rk => {
              if (survivingResSet.size === 0 || survivingResSet.has(rk.trim().toLowerCase())) {
                subRes[rk] = JSON.parse(JSON.stringify(val[rk]));
              }
            });
            filteredInsights.resources = subRes;
          } else if (nonResourceInsightKeys.has(k)) {
            filteredInsights[k] = JSON.parse(JSON.stringify(val));
          } else if (survivingResSet.size === 0 || survivingResSet.has(k.trim().toLowerCase())) {
            filteredInsights[k] = JSON.parse(JSON.stringify(val));
          }
        });
      }

      const finalResList = targetResources.length > 0
        ? targetResources
        : (newDicts.resource_name || []).map(n => String(n).trim().toLowerCase());

      return {
        generated_utc: baseBundle.generated_utc || "",
        excluded_resources: excludedResources,
        excluded_providers: baseBundle.excluded_providers || [],
        exclude_analyst_default: Boolean(maskAnalyst),
        single_resource: finalResList.length === 1 ? finalResList[0] : null,
        slice_resources: finalResList,
        slice_pages: effectivePages,
        slice_date_type: normDateType,
        slice_from_date: normFromDate,
        slice_to_date: normToDate,
        slice_filters: {
          resources: finalResList,
          prepared_samples: psFilterList,
          field_samples: fsFilterList,
          parameters: paramFilterList,
          methods: methodFilterList,
          domain: ef.domain || null,
          date_type: normDateType,
          from_date: normFromDate,
          to_date: normToDate
        },
        slice_qc_statuses: Array.from(allowedSet).filter(Boolean).sort(),
        collaborator_slice_mode: true,
        str_cols: strCols,
        dicts: newDicts,
        rows: remappedRows,
        resources: resources,
        field_samples: fieldSamples,
        prepared_samples: preparedSamples,
        county_lookup: baseBundle.county_lookup || baseBundle.ca_counties || {},
        catalog_medians: baseBundle.catalog_medians || {},
        insights: filteredInsights
      };
    }
    window.buildClientSideSlicedBundle = buildClientSideSlicedBundle;

    function getBundledSlicePagesMap() {
      if (window.__BIOCIRV_BUNDLED_SLICE_PAGES__ && typeof window.__BIOCIRV_BUNDLED_SLICE_PAGES__ === "object") {
        return window.__BIOCIRV_BUNDLED_SLICE_PAGES__;
      }
      const scriptEl = document.getElementById("biocirv-bundled-slice-pages");
      if (scriptEl && scriptEl.textContent) {
        try {
          const parsed = JSON.parse(scriptEl.textContent);
          window.__BIOCIRV_BUNDLED_SLICE_PAGES__ = parsed;
          return parsed;
        } catch (_) {}
      }
      return null;
    }

    function appendBundledPagesScript(htmlDoc, pagesMap) {
      const safePagesJson = JSON.stringify(pagesMap).replace(/<\\//g, "<\\\\/");
      const closeBody = "<" + "/body>";
      const closeScript = "<" + "/script>";
      const openScript = "<" + 'script id="biocirv-bundled-slice-pages" type="application/json">';
      const stripRe = new RegExp("<" + 'script id="biocirv-bundled-slice-pages" type="application/json">[\\\\s\\\\S]*?<' + "/script>", "gi");
      const cleaned = htmlDoc.replace(stripRe, "");
      const idx = cleaned.toLowerCase().lastIndexOf(closeBody);
      if (idx !== -1) {
        return cleaned.slice(0, idx) + openScript + safePagesJson + closeScript + "\\n" + cleaned.slice(idx);
      }
      return cleaned + openScript + safePagesJson + closeScript;
    }
    window.appendBundledPagesScript = appendBundledPagesScript;

    function injectSlicedBundleIntoHtml(rawHtmlStr, slicedBundle, defaultRes) {
      const safeJson = JSON.stringify(slicedBundle).replace(/<\\//g, "<\\\\/");
      const safeDefaultRes = JSON.stringify(defaultRes).replace(/<\\//g, "<\\\\/");
      const stripRe = new RegExp("<" + 'script id="biocirv-bundled-slice-pages" type="application/json">[\\\\s\\\\S]*?<' + "/script>", "gi");
      let out = rawHtmlStr.replace(stripRe, "");
      const bundleReplacement = `const BUNDLE = ${safeJson};\\n    const DEFAULT_RESOURCE = ${safeDefaultRes};`;
      if (/const BUNDLE = \\{[^\\r\\n]*\\};\\s*const DEFAULT_RESOURCE = [^;]+;/.test(out)) {
        out = out.replace(
          /const BUNDLE = \\{[^\\r\\n]*\\};\\s*const DEFAULT_RESOURCE = [^;]+;/,
          () => bundleReplacement
        );
      } else {
        out = out.replace(
          /const BUNDLE = \\{[\\s\\S]*?\\};\\n\\s*const DEFAULT_RESOURCE = [^;]+;/,
          () => bundleReplacement
        );
      }
      const rawDataReplacement = `const RAW_DATA = ${safeJson};`;
      if (/const RAW_DATA = \\{[^\\r\\n]*\\};/.test(out)) {
        out = out.replace(/const RAW_DATA = \\{[^\\r\\n]*\\};/, () => rawDataReplacement);
      } else {
        out = out.replace(/const RAW_DATA = \\{[\\s\\S]*?\\};/, () => rawDataReplacement);
      }
      return out;
    }
    window.injectSlicedBundleIntoHtml = injectSlicedBundleIntoHtml;

    function switchCollaboratorSlicePage(targetPageKey) {
      const pagesMap = getBundledSlicePagesMap();
      if (!pagesMap || !pagesMap[targetPageKey]) return false;
      const targetHtml = appendBundledPagesScript(pagesMap[targetPageKey], pagesMap);
      window.__BIOCIRV_BUNDLED_SLICE_PAGES__ = pagesMap;
      document.open();
      document.write(targetHtml);
      document.close();
      return true;
    }
    window.switchCollaboratorSlicePage = switchCollaboratorSlicePage;

    function openSliceExportModal(opts) {
      if (typeof window._sliceModalOpenImpl === "function") {
        return window._sliceModalOpenImpl(opts);
      }
      if (document.getElementById("modal-export-slice")) {
        initSliceAndBugModals("Dashboard");
        if (typeof window._sliceModalOpenImpl === "function") {
          return window._sliceModalOpenImpl(opts);
        }
      }
      const modalEl = document.getElementById("modal-export-slice");
      if (modalEl && modalEl.classList) {
        modalEl.classList.remove("hidden");
      }
      return modalEl;
    }
    window.openSliceExportModal = openSliceExportModal;

    function initSliceAndBugModals(pageLabel) {
      if (!document.getElementById("modal-export-slice")) {
        if (document.readyState === "loading") {
          document.addEventListener("DOMContentLoaded", () => initSliceAndBugModals(pageLabel), { once: true });
        } else {
          setTimeout(() => initSliceAndBugModals(pageLabel), 0);
        }
        return;
      }

      // Always ensure all modals and popovers start closed (prevents exported slices from opening with a modal up)
      ["modal-export-slice", "modal-report-bug", "modal-analyst-signin", "modal-submit-finding"].forEach(id => {
        const m = document.getElementById(id);
        if (m) m.classList.add("hidden");
      });
      ["panel-popover-resources", "panel-popover-params", "panel-popover-samples", "panel-popover-methods"].forEach(id => {
        const p = document.getElementById(id);
        if (p) p.classList.add("hidden");
      });

      const sliceModal = document.getElementById("modal-export-slice");
      const bugModal = document.getElementById("modal-report-bug");
      const openSliceBtn = document.getElementById("btn-open-slice-modal");
      const openBugBtn = document.getElementById("btn-open-bug-modal");
      const activePayload = typeof BUNDLE !== "undefined" ? BUNDLE : (typeof RAW_DATA !== "undefined" ? RAW_DATA : {});
      const activeResourcesList = (typeof ACTIVE_RESOURCES !== "undefined" && ACTIVE_RESOURCES.length)
        ? ACTIVE_RESOURCES
        : ((activePayload.dicts && activePayload.dicts.resource_name && activePayload.dicts.resource_name.length)
            ? activePayload.dicts.resource_name.slice().sort()
            : ["resource"]);

      if (activePayload.collaborator_slice_mode) {
        if (openSliceBtn) openSliceBtn.classList.add("hidden");
        const allowedPages = new Set(activePayload.slice_pages || ["char", "explorer"]);
        const pageNavSpecs = [
          { key: "char", ids: ["nav-page-char", "suite-link-1"] },
          { key: "qc", ids: ["nav-page-qc", "suite-link-2"] },
          { key: "explorer", ids: ["nav-page-explorer", "suite-link-3"] }
        ];
        pageNavSpecs.forEach(spec => {
          spec.ids.forEach(id => {
            const el = document.getElementById(id);
            if (!el) return;
            if (!allowedPages.has(spec.key)) {
              el.classList.add("hidden");
              el.style.display = "none";
            } else {
              el.classList.remove("hidden");
              el.style.display = "";
              el.setAttribute("href", "javascript:void(0)");
              el.addEventListener("click", (evt) => {
                evt.preventDefault();
                switchCollaboratorSlicePage(spec.key);
              });
            }
          });
        });
        ["nav-page-pretreatment", "nav-page-drift", "nav-page-monolith", "suite-link-4", "suite-link-5", "btn-open-finding-modal"].forEach(id => {
          const el = document.getElementById(id);
          if (el) {
            el.classList.add("hidden");
            el.style.display = "none";
          }
        });
      }

      const selectedSliceResources = new Set();

      function getPageDefaultResources() {
        if (typeof selectedFilters !== "undefined" && selectedFilters.resources && selectedFilters.resources.size > 0) {
          return Array.from(selectedFilters.resources);
        }
        if (typeof state !== "undefined" && state.resource) {
          return [state.resource];
        }
        return activeResourcesList.slice();
      }

      function getPageDateInputs() {
        const dtEl = document.getElementById("flt-date-type") || document.getElementById("filter-date-type");
        const fromEl = document.getElementById("flt-from-date") || document.getElementById("filter-from-date");
        const toEl = document.getElementById("flt-to-date") || document.getElementById("filter-to-date");
        return {
          date_type: (dtEl && dtEl.value) || (typeof state !== "undefined" && state.date_type) || "any",
          from_date: (fromEl && fromEl.value) || (typeof state !== "undefined" && state.from_date) || "",
          to_date: (toEl && toEl.value) || (typeof state !== "undefined" && state.to_date) || ""
        };
      }

      function getPageActiveExtraFilters() {
        const applyEl = document.getElementById("slice-apply-active-filters");
        const shouldApply = applyEl ? applyEl.checked : true;
        const dtModal = document.getElementById("slice-date-type");
        const fromModal = document.getElementById("slice-from-date");
        const toModal = document.getElementById("slice-to-date");
        const dateTypeVal = (dtModal && dtModal.value) || "any";
        const fromDateVal = (fromModal && fromModal.value) || "";
        const toDateVal = (toModal && toModal.value) || "";

        if (!shouldApply) {
          return {
            prepared_samples: [],
            field_samples: [],
            parameters: [],
            methods: [],
            domain: null,
            date_type: dateTypeVal,
            from_date: fromDateVal,
            to_date: toDateVal
          };
        }
        const ps = [];
        const fs = [];
        const params = [];
        const methods = [];
        let domain = null;

        if (typeof selectedFilters !== "undefined") {
          if (selectedFilters.samples && selectedFilters.samples.size > 0) {
            selectedFilters.samples.forEach(v => ps.push(v));
          }
          if (selectedFilters.params && selectedFilters.params.size > 0) {
            selectedFilters.params.forEach(v => params.push(v));
          }
          if (selectedFilters.methods && selectedFilters.methods.size > 0) {
            selectedFilters.methods.forEach(v => methods.push(v));
          }
          if (typeof currentDomain !== "undefined" && currentDomain) {
            domain = currentDomain;
          }
        } else if (typeof state !== "undefined") {
          if (state.prepared_sample && state.prepared_sample !== "all") {
            ps.push(state.prepared_sample);
          }
          if (state.field_sample && state.field_sample !== "all") {
            fs.push(state.field_sample);
          }
          if (state.experiment && state.experiment !== "all") {
            methods.push(state.experiment);
          }
          if (state.tab && state.tab !== "overview") {
            domain = state.tab;
          } else if (state.domain && state.domain !== "all") {
            domain = state.domain;
          }
        }
        return {
          prepared_samples: ps,
          field_samples: fs,
          parameters: params,
          methods: methods,
          domain: domain,
          date_type: dateTypeVal,
          from_date: fromDateVal,
          to_date: toDateVal
        };
      }

      function getSelectedSlicePages() {
        const pages = [];
        const cChar = document.getElementById("slice-page-char");
        const cExp = document.getElementById("slice-page-explorer");
        const cQc = document.getElementById("slice-page-qc");
        if (cChar && cChar.checked) pages.push("char");
        if (cExp && cExp.checked) pages.push("explorer");
        if (cQc && cQc.checked) pages.push("qc");
        return pages.length ? pages : ["char"];
      }

      function getSelectedSliceResourcesList() {
        if (selectedSliceResources.size > 0) {
          return Array.from(selectedSliceResources);
        }
        const resSel = document.getElementById("slice-modal-resource");
        if (resSel && resSel.value) {
          return normalizeFilterTokenArray(resSel.value);
        }
        return activeResourcesList.slice();
      }

      function syncHiddenResourceSelect() {
        const resSel = document.getElementById("slice-modal-resource");
        if (!resSel) return;
        const list = getSelectedSliceResourcesList();
        const joined = list.join(",");
        resSel.innerHTML = `<option value="${joined}" selected>${joined}</option>` +
          activeResourcesList.map(r => `<option value="${r}">${r.toUpperCase()}</option>`).join("");
        resSel.value = joined;
      }

      function renderSliceModalResourceCheckboxes() {
        const listEl = document.getElementById("slice-modal-resources-list");
        const searchEl = document.getElementById("slice-modal-resource-search");
        const badgeEl = document.getElementById("slice-selected-res-badge");
        if (badgeEl) {
          badgeEl.textContent = selectedSliceResources.size === 0 || selectedSliceResources.size === activeResourcesList.length
            ? `(All ${activeResourcesList.length} selected)`
            : `(${selectedSliceResources.size} of ${activeResourcesList.length} selected)`;
        }
        if (!listEl) return;
        const q = (searchEl ? searchEl.value : "").trim().toLowerCase();
        const visible = activeResourcesList.filter(r => !q || r.toLowerCase().includes(q));
        if (!visible.length) {
          listEl.innerHTML = `<div class="col-span-2 py-2 text-center text-[var(--muted-foreground)]">No matching resources</div>`;
          return;
        }
        listEl.innerHTML = visible.map(r => {
          const isChecked = selectedSliceResources.has(r);
          const safeVal = r.replace(/"/g, "&quot;");
          return `
            <label class="flex items-center gap-1.5 px-2 py-1 rounded cursor-pointer border ${isChecked ? 'border-[var(--primary)] bg-[var(--primary)]/10 font-semibold text-[var(--foreground)]' : 'border-transparent hover:bg-[var(--secondary)]/50 text-[var(--muted-foreground)]'}">
              <input type="checkbox" data-slice-res="${safeVal}" ${isChecked ? 'checked' : ''} class="slice-res-cb rounded" />
              <span class="truncate">${r.toUpperCase()}</span>
            </label>
          `;
        }).join("");
        listEl.querySelectorAll(".slice-res-cb").forEach(cb => {
          cb.addEventListener("change", () => {
            const rName = cb.getAttribute("data-slice-res");
            if (cb.checked) selectedSliceResources.add(rName);
            else selectedSliceResources.delete(rName);
            syncHiddenResourceSelect();
            renderSliceModalResourceCheckboxes();
            updateSlicePreviewCount();
          });
        });
      }

      function updateActiveFilterSummaryBanner() {
        const sumEl = document.getElementById("slice-active-filters-summary");
        if (!sumEl) return;
        const ef = getPageActiveExtraFilters();
        const dateSummary = (ef.from_date || ef.to_date)
          ? `${ef.date_type === 'collected' ? 'Collected' : (ef.date_type === 'run' ? 'Run/Prep' : 'Any Date')}: ${ef.from_date || '*'} → ${ef.to_date || '*'}`
          : "All Dates";
        const parts = [
          `Parameters: ${ef.parameters.length ? ef.parameters.slice(0, 4).join(", ") + (ef.parameters.length > 4 ? ` (+${ef.parameters.length - 4})` : "") : "All"}`,
          `Prepared Samples: ${ef.prepared_samples.length ? ef.prepared_samples.slice(0, 3).join(", ") + (ef.prepared_samples.length > 3 ? ` (+${ef.prepared_samples.length - 3})` : "") : "All"}`,
          `Field Samples: ${ef.field_samples.length ? ef.field_samples.slice(0, 3).join(", ") + (ef.field_samples.length > 3 ? ` (+${ef.field_samples.length - 3})` : "") : "All"}`,
          `Methods: ${ef.methods.length ? ef.methods.slice(0, 3).join(", ") + (ef.methods.length > 3 ? ` (+${ef.methods.length - 3})` : "") : "All"}`,
          `Dates: ${dateSummary}`
        ];
        sumEl.textContent = parts.join(" · ");
      }

      function getSelectedSliceQcStatuses() {
        const st = [];
        const cPass = document.getElementById("slice-qc-pass");
        const cFail = document.getElementById("slice-qc-fail");
        const cUnscored = document.getElementById("slice-qc-unscored");
        if (cPass && cPass.checked) st.push("pass");
        if (cFail && cFail.checked) st.push("fail");
        if (cUnscored && cUnscored.checked) st.push("unscored");
        return st.length ? st : ["pass"];
      }

      function updateSlicePreviewCount() {
        const previewEl = document.getElementById("slice-preview-count");
        if (!previewEl) return;
        updateActiveFilterSummaryBanner();
        const targetResList = getSelectedSliceResourcesList();
        const qcSt = getSelectedSliceQcStatuses();
        const ef = getPageActiveExtraFilters();
        const pages = getSelectedSlicePages();
        const sliced = buildClientSideSlicedBundle(activePayload, targetResList, qcSt, true, ef, pages);
        const resLabel = targetResList.length === 1
          ? `"${targetResList[0]}"`
          : `${targetResList.length} selected resources`;
        const pageNames = pages.map(p => p === "char" ? "Page 1 (Characterization)" : (p === "explorer" ? "Page 3 (Multi-Resource)" : "Page 2 (QC)")).join(" + ");
        previewEl.textContent = `Slice preview: ${sliced.rows.length.toLocaleString()} observation(s) across ${resLabel} · Pages: [${pageNames}] · QC: [${qcSt.join(", ").toUpperCase()}] · 0 non-selected resources included.`;
      }

      function openSliceExportModalImpl(opts) {
        selectedSliceResources.clear();
        let explicitResources = [];
        if (typeof opts === "string" && opts.trim()) {
          explicitResources = normalizeFilterTokenArray(opts);
        } else if (Array.isArray(opts)) {
          explicitResources = normalizeFilterTokenArray(opts);
        } else if (opts && typeof opts === "object") {
          explicitResources = normalizeFilterTokenArray(
            opts.resources || opts.selectedResources || opts.resource || ""
          );
        }
        if (explicitResources.length > 0) {
          const knownByLower = {};
          activeResourcesList.forEach(r => {
            knownByLower[String(r || "").trim().toLowerCase()] = r;
          });
          explicitResources.forEach(er => {
            const norm = String(er || "").trim().toLowerCase();
            if (!norm) return;
            const matched = knownByLower[norm] || er;
            if (!activeResourcesList.includes(matched)) {
              activeResourcesList.push(matched);
            }
            selectedSliceResources.add(matched);
          });
        } else {
          getPageDefaultResources().forEach(r => selectedSliceResources.add(r));
        }
        const pageDates = getPageDateInputs();
        const dtModal = document.getElementById("slice-date-type");
        const fromModal = document.getElementById("slice-from-date");
        const toModal = document.getElementById("slice-to-date");
        if (dtModal && pageDates.date_type) dtModal.value = pageDates.date_type;
        if (fromModal) fromModal.value = pageDates.from_date || "";
        if (toModal) toModal.value = pageDates.to_date || "";
        syncHiddenResourceSelect();
        renderSliceModalResourceCheckboxes();
        updateSlicePreviewCount();
        const modalEl = sliceModal || document.getElementById("modal-export-slice");
        if (modalEl) {
          modalEl.classList.remove("hidden");
        }
        return modalEl;
      }
      window._sliceModalOpenImpl = openSliceExportModalImpl;
      window.openSliceExportModal = openSliceExportModalImpl;
      if (window.BioCirvQcClient) {
        window.BioCirvQcClient.openSliceExportModal = openSliceExportModalImpl;
      }

      if (openSliceBtn && sliceModal) {
        openSliceBtn.addEventListener("click", () => {
          openSliceExportModalImpl();
        });
      }

      const btnClearDates = document.getElementById("btn-slice-clear-dates");
      if (window.initDateFilterInputs) {
        window.initDateFilterInputs(
          document.getElementById("slice-from-date"),
          document.getElementById("slice-to-date"),
          document.getElementById("slice-date-type"),
          btnClearDates,
          () => updateSlicePreviewCount()
        );
      }

      const btnResActive = document.getElementById("btn-slice-res-active");
      if (btnResActive) {
        btnResActive.addEventListener("click", () => {
          selectedSliceResources.clear();
          getPageDefaultResources().forEach(r => selectedSliceResources.add(r));
          syncHiddenResourceSelect();
          renderSliceModalResourceCheckboxes();
          updateSlicePreviewCount();
        });
      }
      const btnResAll = document.getElementById("btn-slice-res-all");
      if (btnResAll) {
        btnResAll.addEventListener("click", () => {
          selectedSliceResources.clear();
          activeResourcesList.forEach(r => selectedSliceResources.add(r));
          syncHiddenResourceSelect();
          renderSliceModalResourceCheckboxes();
          updateSlicePreviewCount();
        });
      }
      const btnResClear = document.getElementById("btn-slice-res-clear");
      if (btnResClear) {
        btnResClear.addEventListener("click", () => {
          selectedSliceResources.clear();
          syncHiddenResourceSelect();
          renderSliceModalResourceCheckboxes();
          updateSlicePreviewCount();
        });
      }
      const resSearchInput = document.getElementById("slice-modal-resource-search");
      if (resSearchInput) {
        resSearchInput.addEventListener("input", renderSliceModalResourceCheckboxes);
      }

      const hiddenResSel = document.getElementById("slice-modal-resource");
      if (hiddenResSel) {
        hiddenResSel.addEventListener("change", () => {
          selectedSliceResources.clear();
          normalizeFilterTokenArray(hiddenResSel.value).forEach(r => selectedSliceResources.add(r));
          renderSliceModalResourceCheckboxes();
          updateSlicePreviewCount();
        });
      }

      [
        "slice-qc-pass", "slice-qc-fail", "slice-qc-unscored",
        "slice-apply-active-filters", "slice-page-char", "slice-page-explorer", "slice-page-qc"
      ].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener("change", updateSlicePreviewCount);
      });

      ["btn-close-slice-modal", "btn-cancel-slice-modal"].forEach(id => {
        const el = document.getElementById(id);
        if (el && sliceModal) el.addEventListener("click", () => sliceModal.classList.add("hidden"));
      });

      function buildSliceFilenameSlug(targetResList) {
        if (!targetResList || targetResList.length === 0) return "all_resources";
        if (targetResList.length === 1) return targetResList[0].replace(/\\s+/g, "_").toLowerCase();
        if (targetResList.length <= 3) {
          return targetResList.map(r => r.replace(/\\s+/g, "_").toLowerCase()).join("__");
        }
        const firstSlug = targetResList[0].replace(/\\s+/g, "_").toLowerCase();
        return `${firstSlug}_plus_${targetResList.length - 1}_resources`;
      }

      function downloadSlicedBundleAsCsv(slicedBundle, targetResList, qcSt) {
        const countyMap = slicedBundle.county_lookup || {};
        const fsMap = {};
        (slicedBundle.field_samples || []).forEach(fs => {
          fsMap[fs.name] = fs;
          const rKey = fs.resource_name || fs.resource;
          if (rKey) fsMap[`${rKey}::${fs.name}`] = fs;
        });
        const psMap = {};
        (slicedBundle.prepared_samples || []).forEach(ps => {
          psMap[ps.name] = ps;
          const rKey = ps.resource_name || ps.resource;
          if (rKey) psMap[`${rKey}::${ps.name}`] = ps;
        });

        const cols = [
          "resource_name", "record_id", "analysis_type", "prepared_sample", "field_sample",
          "collected_date", "geoid", "county_name", "prep_date", "exp_date", "prep_method",
          "experiment", "parameter", "value", "unit", "replicate", "pt_method", "eh_method",
          "strain", "vessel", "well_or_block", "provider", "qc_status", "note"
        ];
        const rowsObjs = (slicedBundle.rows || []).map(arr => {
          const obj = { record_id: String(arr[0]) };
          (slicedBundle.str_cols || []).forEach((col, idx) => {
            const dictArr = (slicedBundle.dicts && slicedBundle.dicts[col]) || [];
            obj[col] = dictArr[arr[idx + 1]] ?? "";
          });
          const sLen = (slicedBundle.str_cols || []).length;
          obj.replicate = arr[sLen + 1] ?? "";
          obj.value = arr[sLen + 2] ?? "";
          obj.exp_date = arr.length > sLen + 3 ? (arr[sLen + 3] ?? "") : "";
          const psMeta = psMap[`${obj.resource_name}::${obj.prepared_sample}`] || psMap[obj.prepared_sample] || {};
          const fsName = obj.field_sample || psMeta.field_sample_name || psMeta.field_sample || "";
          const fsMeta = fsMap[`${obj.resource_name}::${fsName}`] || fsMap[fsName] || {};
          obj.collected_date = fsMeta.collected_at ? String(fsMeta.collected_at).slice(0, 10) : "";
          obj.geoid = fsMeta.geoid ? String(fsMeta.geoid).trim() : "";
          obj.county_name = obj.geoid && countyMap[obj.geoid] ? countyMap[obj.geoid] : "";
          obj.prep_date = psMeta.prep_date ? String(psMeta.prep_date).slice(0, 10) : (obj.exp_date ? String(obj.exp_date).slice(0, 10) : "");
          return obj;
        });

        const csv = [
          cols.join(","),
          ...rowsObjs.map(r => cols.map(c => `"${String(r[c] ?? '').replace(/"/g, '""')}"`).join(","))
        ].join("\\n");
        const slug = buildSliceFilenameSlug(targetResList);
        const qcSlug = qcSt.join("_");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${slug}_collaborator_slice_${qcSlug}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }

      const downloadSliceCsvModalBtn = document.getElementById("btn-download-slice-csv-modal");
      if (downloadSliceCsvModalBtn && sliceModal) {
        downloadSliceCsvModalBtn.addEventListener("click", () => {
          const targetResList = getSelectedSliceResourcesList();
          const qcSt = getSelectedSliceQcStatuses();
          const maskEl = document.getElementById("slice-mask-analyst");
          const maskAnalyst = maskEl ? maskEl.checked : true;
          const ef = getPageActiveExtraFilters();
          const pages = getSelectedSlicePages();
          const slicedBundle = buildClientSideSlicedBundle(activePayload, targetResList, qcSt, maskAnalyst, ef, pages);
          downloadSlicedBundleAsCsv(slicedBundle, slicedBundle.slice_resources, qcSt);
          if (window.showQcToast) {
            window.showQcToast(`Downloaded ${slicedBundle.rows.length} sliced records (.csv) across ${slicedBundle.slice_resources.length} resource(s)`, "pass");
          }
        });
      }

      const confirmSliceBtn = document.getElementById("btn-confirm-slice-export");
      if (confirmSliceBtn && sliceModal) {
        confirmSliceBtn.addEventListener("click", async () => {
          const targetResList = getSelectedSliceResourcesList();
          const qcSt = getSelectedSliceQcStatuses();
          const maskEl = document.getElementById("slice-mask-analyst");
          const maskAnalyst = maskEl ? maskEl.checked : true;
          const ef = getPageActiveExtraFilters();
          const selectedPages = getSelectedSlicePages();
          const slicedBundle = buildClientSideSlicedBundle(activePayload, targetResList, qcSt, maskAnalyst, ef, selectedPages);
          const defaultRes = slicedBundle.slice_resources[0] || activeResourcesList[0] || "resource";

          // Close all modals & popovers BEFORE capturing outerHTML so the exported slice never opens with a popup
          ["modal-export-slice", "modal-report-bug", "modal-analyst-signin", "modal-submit-finding"].forEach(id => {
            const m = document.getElementById(id);
            if (m) m.classList.add("hidden");
          });
          ["panel-popover-resources", "panel-popover-params", "panel-popover-samples", "panel-popover-methods"].forEach(id => {
            const p = document.getElementById(id);
            if (p) p.classList.add("hidden");
          });

          // Temporarily clear dynamic resource lists inside modals so unselected resource names aren't serialized in DOM
          const cleanupIds = [
            "slice-modal-resources-list", "slice-modal-resource", "finding-modal-resource",
            "list-popover-resources", "inline-list-resources", "flt-resource"
          ];
          const savedHtmlMap = {};
          cleanupIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
              savedHtmlMap[id] = el.innerHTML;
              el.innerHTML = "";
            }
          });

          const currentPageKey = pageLabel.includes("Page 3") ? "explorer" : (pageLabel.includes("Page 2") ? "qc" : "char");
          const currentOuterHtml = "<!DOCTYPE html>\\n" + document.documentElement.outerHTML;

          // Restore live DOM lists in the parent tab
          Object.keys(savedHtmlMap).forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = savedHtmlMap[id];
          });

          const pagesMap = {};
          pagesMap[currentPageKey] = injectSlicedBundleIntoHtml(currentOuterHtml, slicedBundle, defaultRes);

          const pageFileMap = {
            char: "resource_analysis_dashboard.html",
            qc: "resource_qc_outlier_dashboard.html",
            explorer: "resource_explorer_dashboard.html"
          };
          const existingBundled = getBundledSlicePagesMap() || {};
          for (let i = 0; i < selectedPages.length; i++) {
            const pKey = selectedPages[i];
            if (pKey === currentPageKey) continue;
            if (existingBundled[pKey]) {
              pagesMap[pKey] = injectSlicedBundleIntoHtml(existingBundled[pKey], slicedBundle, defaultRes);
              continue;
            }
            if (window.location.protocol === "http:" || window.location.protocol === "https:") {
              try {
                const resp = await fetch(pageFileMap[pKey], { cache: "no-store" });
                if (resp.ok) {
                  const rawPageHtml = await resp.text();
                  pagesMap[pKey] = injectSlicedBundleIntoHtml(rawPageHtml, slicedBundle, defaultRes);
                }
              } catch (_) {}
            }
          }

          const entryPageKey = selectedPages.includes(currentPageKey)
            ? currentPageKey
            : (pagesMap[selectedPages[0]] ? selectedPages[0] : currentPageKey);
          const finalDoc = appendBundledPagesScript(pagesMap[entryPageKey] || pagesMap[currentPageKey], pagesMap);

          const slug = buildSliceFilenameSlug(slicedBundle.slice_resources);
          const qcSlug = qcSt.join("_");
          const blob = new Blob([finalDoc], { type: "text/html;charset=utf-8;" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `${slug}_collaborator_slice_${qcSlug}.html`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          if (window.showQcToast) {
            window.showQcToast(`Downloaded standalone collaborator slice (.html) across ${slicedBundle.slice_resources.length} resource(s) (${slicedBundle.rows.length} obs)`, "pass");
          }
        });
      }

      function getBugDiagnosticsObject() {
        const activeRes = (typeof state !== "undefined" && (state.resource || state.primaryResource))
          || (typeof selectedFilters !== "undefined" && selectedFilters.resources && selectedFilters.resources.size ? Array.from(selectedFilters.resources).slice(0, 4).join(", ") : "")
          || (typeof checkedSet !== "undefined" && checkedSet.resources && checkedSet.resources.size ? Array.from(checkedSet.resources).slice(0, 4).join(", ") : "all");
        const activeDomain = (typeof state !== "undefined" && (state.tab || state.domain || state.subtab))
          || (typeof currentDomain !== "undefined" ? currentDomain : "overview");
        const activeQc = (typeof state !== "undefined" && (state.qc_status || state.portalQcFilter || state.qcFilter))
          || ((document.getElementById("filter-status") || {}).value)
          || "pass";
        return {
          page: pageLabel,
          resource: activeRes,
          domainTab: activeDomain,
          qcFilter: activeQc,
          queryString: window.location.search || "(none)"
        };
      }
      window.getBugDiagnosticsObject = getBugDiagnosticsObject;

      function openBugReportModal() {
        const modalEl = bugModal || document.getElementById("modal-report-bug");
        if (!modalEl) return;
        const diag = getBugDiagnosticsObject();
        const diagEl = document.getElementById("bug-modal-diagnostics");
        if (diagEl) {
          diagEl.textContent =
            `Page: ${diag.page}\\nResource: ${diag.resource}\\nActive Tab/Domain: ${diag.domainTab}\\nActive QC Filter: ${diag.qcFilter}\\nQuery: ${diag.queryString}`;
        }
        const statusEl = document.getElementById("bug-modal-status");
        if (statusEl) statusEl.classList.add("hidden");
        modalEl.classList.remove("hidden");
      }
      window.openBugReportModal = openBugReportModal;

      if (openBugBtn && bugModal) {
        openBugBtn.addEventListener("click", openBugReportModal);
      }

      ["btn-close-bug-modal", "btn-cancel-bug-modal"].forEach(id => {
        const el = document.getElementById(id);
        if (el && bugModal) el.addEventListener("click", () => bugModal.classList.add("hidden"));
      });

      const submitUrlBtn = document.getElementById("btn-submit-github-url");
      if (submitUrlBtn) {
        submitUrlBtn.addEventListener("click", () => {
          const diag = getBugDiagnosticsObject();
          const issueUrl = buildGitHubBugIssueUrl({
            title: (document.getElementById("bug-modal-title") || {}).value || "",
            category: (document.getElementById("bug-modal-category") || {}).value || "UI / Chart Rendering Bug",
            description: (document.getElementById("bug-modal-desc") || {}).value || "",
            expectedBehavior: (document.getElementById("bug-modal-expected") || {}).value || "",
            ...diag
          });
          window.open(issueUrl, "_blank", "noopener");
          if (bugModal) bugModal.classList.add("hidden");
        });
      }

      const submitApiBtn = document.getElementById("btn-submit-github-api");
      if (submitApiBtn) {
        submitApiBtn.addEventListener("click", async () => {
          const diag = getBugDiagnosticsObject();
          const payload = {
            title: (document.getElementById("bug-modal-title") || {}).value || "BioCirV Dashboard Bug Report",
            category: (document.getElementById("bug-modal-category") || {}).value || "UI / Chart Rendering Bug",
            description: (document.getElementById("bug-modal-desc") || {}).value || "",
            expected_behavior: (document.getElementById("bug-modal-expected") || {}).value || "",
            page: diag.page,
            resource: diag.resource,
            domain_tab: diag.domainTab,
            qc_filter: diag.qcFilter,
            query_string: diag.queryString,
            create_via_api: true
          };
          const statusEl = document.getElementById("bug-modal-status");
          if (statusEl) {
            statusEl.className = "text-xs font-mono p-2 rounded-lg badge-info";
            statusEl.textContent = "⏳ Submitting issue via /v1/qc/github-issue...";
            statusEl.classList.remove("hidden");
          }
          try {
            const apiBase = window.BIOCIRV_API_BASE || "http://localhost:8000";
            const resp = await fetch(`${apiBase}/v1/qc/github-issue`, {
              method: "POST",
              headers: BioCirvQcClient.getHeaders(),
              body: JSON.stringify(payload)
            });
            if (resp.ok) {
              const data = await resp.json();
              const escBugHtml = (s) => String(s ?? "")
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#39;");
              if (data.created_via_api) {
                if (statusEl) {
                  statusEl.className = "text-xs font-mono p-2.5 rounded-lg badge-pass";
                  statusEl.innerHTML = `✓ GitHub Issue #${escBugHtml(data.issue_number ?? "")} created &amp; recorded in PostgreSQL QC Ledger (ID #${escBugHtml(data.decision_id ?? "")})! <a href="${escBugHtml(data.issue_url ?? "")}" target="_blank" rel="noopener" class="underline font-bold ml-1">View Issue on GitHub &rarr;</a>`;
                  statusEl.classList.remove("hidden");
                }
                if (window.showQcToast) {
                  window.showQcToast(`Created GitHub Issue #${data.issue_number ?? ""} & saved to PostgreSQL (ID #${data.decision_id ?? ""})`, "pass");
                }
                return;
              }
              if (data.persisted) {
                const ghFallbackHref = escBugHtml(data.issue_url || data.fallback_url || "");
                if (statusEl) {
                  statusEl.className = "text-xs font-mono p-2.5 rounded-lg badge-pass";
                  statusEl.innerHTML = `✓ Issue recorded in PostgreSQL QC Ledger (ID #${escBugHtml(data.decision_id ?? "")}).${ghFallbackHref ? ` <a href="${ghFallbackHref}" target="_blank" rel="noopener" class="underline font-bold ml-1">Optional: Open on GitHub &rarr;</a>` : ""}`;
                  statusEl.classList.remove("hidden");
                }
                if (window.showQcToast) {
                  window.showQcToast(`Issue recorded in PostgreSQL QC Ledger (ID #${data.decision_id ?? ""})`, "pass");
                }
                return;
              }
              if (statusEl) {
                statusEl.className = "text-xs font-mono p-2.5 rounded-lg badge-warn";
                statusEl.textContent = `ℹ️ No server GITHUB_TOKEN configured (${data.api_error ?? "using pre-filled URL fallback"}). Opened pre-filled GitHub issue form in a new tab.`;
                statusEl.classList.remove("hidden");
              }
              if (data.issue_url) window.open(data.issue_url, "_blank", "noopener");
              return;
            }
          } catch (_err) {
            // Fall back to direct pre-populated GitHub issue URL when running offline
          }
          const fallbackUrl = buildGitHubBugIssueUrl({
            title: payload.title,
            category: payload.category,
            description: payload.description,
            expectedBehavior: payload.expected_behavior,
            ...diag
          });
          window.open(fallbackUrl, "_blank", "noopener");
          if (bugModal) bugModal.classList.add("hidden");
        });
      }

      initAnalystSignInBar();
      initSubmitFindingModal(activeResourcesList);
    }

    window.showQcToast = function(message, variant) {
      let container = document.getElementById("biocirv-toast-container");
      if (!container) {
        container = document.createElement("div");
        container.id = "biocirv-toast-container";
        container.className = "fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-md";
        document.body.appendChild(container);
      }
      const toast = document.createElement("div");
      const badgeCls = variant === "fail" ? "badge-fail" : (variant === "warn" ? "badge-warn" : (variant === "info" ? "badge-info" : "badge-pass"));
      toast.className = `px-3.5 py-2.5 rounded-xl shadow-xl border border-[var(--border)] text-xs font-mono ${badgeCls} transition-opacity duration-300`;
      toast.innerHTML = message;
      container.appendChild(toast);
      setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => {
          if (toast.parentElement) toast.parentElement.removeChild(toast);
        }, 300);
      }, 4500);
    };

    const ANALYST_IDENTITY_STORAGE_KEY = "biocirv_analyst_identity_v1";
    const LOCAL_DECISIONS_STORAGE_KEY = "biocirv_qc_decisions_ledger_v1";
    const PAGE2_DECISIONS_STORAGE_KEY = "biocirv_qc_decisions_v1";

    const DOMAIN_DEFS = [
      { key: "proximate", label: "Proximate", analysisType: "Proximate Analysis" },
      { key: "calorimetry", label: "Calorimetry", analysisType: "Calorimetry" },
      { key: "compositional", label: "Compositional", analysisType: "Compositional Analysis" },
      { key: "ultimate", label: "Ultimate", analysisType: "Ultimate Analysis" },
      { key: "xrd", label: "XRD", analysisType: "XRD Crystallinity" },
      { key: "icp", label: "ICP", analysisType: "ICP-OES / ICP-MS" },
      { key: "xrf", label: "XRF", analysisType: "XRF Elemental" },
      { key: "pretreatment", label: "Pretreatment", analysisType: "Pretreatment" },
      { key: "fermentation", label: "Fermentation", analysisType: "Fermentation" },
      { key: "gasification", label: "Gasification", analysisType: "Gasification" }
    ];
    window.DOMAIN_DEFS = DOMAIN_DEFS;

    function normalizeDomainKey(raw) {
      const s = String(raw || "").trim().toLowerCase();
      if (!s) return "proximate";
      if (s === "all") return "all";
      if (s === "calorimetry_xrd" || s.includes("calorim") || s.includes("hhv") || s.includes("lhv")) return "calorimetry";
      if (s.includes("proximate")) return "proximate";
      if (s.includes("ultimate")) return "ultimate";
      if (s.includes("compositional") || s.includes("structural")) return "compositional";
      if (s.includes("xrd") || s.includes("crystallin")) return "xrd";
      if (s === "elemental" || s.includes("icp")) return "icp";
      if (s.includes("xrf") || s === "ash" || s.startsWith("ash ")) return "xrf";
      if (s.includes("pretreatment") || s.includes("hydrolysis")) return "pretreatment";
      if (s.includes("fermentation") || s.includes("bioconversion")) return "fermentation";
      if (s.includes("gasification")) return "gasification";
      return s;
    }
    window.normalizeDomainKey = normalizeDomainKey;

    const CANONICAL_DOMAIN_LOOKUP = {
      "proximate analysis": "proximate",
      "proximate": "proximate",
      "ultimate analysis": "ultimate",
      "ultimate": "ultimate",
      "compositional analysis": "compositional",
      "compositional": "compositional",
      "calorimetry": "calorimetry",
      "calorimetry analysis": "calorimetry",
      "calorimetry_xrd": "calorimetry",
      "xrd": "xrd",
      "xrd analysis": "xrd",
      "icp": "icp",
      "icp-oes / icp-ms": "icp",
      "icp elemental analysis": "icp",
      "icp analysis": "icp",
      "xrf": "xrf",
      "xrf elemental": "xrf",
      "xrf elemental analysis": "xrf",
      "xrf analysis": "xrf",
      "ash": "xrf",
      "pretreatment": "pretreatment",
      "pretreatment & hydrolysis": "pretreatment",
      "fermentation": "fermentation",
      "fermentation (bioconversion)": "fermentation",
      "gasification": "gasification"
    };

    const CANONICAL_DOMAIN_SLUGS = [
      "proximate",
      "ultimate",
      "compositional",
      "calorimetry",
      "xrd",
      "icp",
      "xrf",
      "pretreatment",
      "fermentation",
      "gasification"
    ];

    function canonicalDomainSlug(analysisType) {
      let cleaned = String(analysisType || "").trim().toLowerCase();
      if (!cleaned) return "unknown";
      if (cleaned.endsWith("_record")) {
        cleaned = cleaned.slice(0, -"_record".length).trim();
      }
      if (CANONICAL_DOMAIN_LOOKUP[cleaned]) {
        return CANONICAL_DOMAIN_LOOKUP[cleaned];
      }
      for (let i = 0; i < CANONICAL_DOMAIN_SLUGS.length; i++) {
        if (cleaned.indexOf(CANONICAL_DOMAIN_SLUGS[i]) !== -1) {
          return CANONICAL_DOMAIN_SLUGS[i];
        }
      }
      return cleaned;
    }

    function groupContextLabel(obj) {
      if (!obj || typeof obj !== "object") return "unassigned";
      if (typeof obj.group_context_label === "string" && obj.group_context_label.trim() !== "") {
        return obj.group_context_label.trim();
      }
      const domSlug = canonicalDomainSlug(obj.analysis_type || obj.domain || "");
      const hasPtKey = Object.prototype.hasOwnProperty.call(obj, "pt_method");
      const hasStrainKey = Object.prototype.hasOwnProperty.call(obj, "strain");
      const prep = String(obj.prep_method || "").trim();
      const ptRaw = String(obj.pt_method || "").trim();
      if (domSlug === "pretreatment") {
        const pt = ptRaw || (!hasPtKey ? prep : "") || "none";
        const eh = String(obj.eh_method || "").trim() || "none";
        return eh && eh !== "none" ? `${pt} \u00b7 ${eh}` : pt;
      }
      if (domSlug === "fermentation") {
        const fermPt = ptRaw;
        const strain = String(obj.strain || "").trim() || (!hasStrainKey ? prep : "") || "no-strain";
        const base = fermPt && fermPt !== "none" ? `${fermPt} \u00b7 ${strain}` : strain;
        const th = obj.time_h;
        if (th !== null && th !== undefined && String(th).trim() !== "") {
          const numTh = Number(th);
          const thFmt = Number.isFinite(numTh) ? String(numTh) : String(th).trim();
          return `${base} @ ${thFmt}h`;
        }
        return base;
      }
      return prep || "unassigned";
    }

    function normalizeReplicateGroupKey(
      rawKeyOrResource,
      preparedSample,
      analysisType,
      parameter,
      prepMethod,
      experiment
    ) {
      if (
        typeof rawKeyOrResource === "string" &&
        rawKeyOrResource.indexOf("::") !== -1 &&
        preparedSample === undefined &&
        analysisType === undefined &&
        parameter === undefined
      ) {
        let s = rawKeyOrResource.trim();
        const isLegacyGrp = s.toLowerCase().indexOf("grp::") === 0;
        if (isLegacyGrp) {
          s = s.slice(5);
        }
        const parts = s.split("::").map(p => String(p || "").trim().toLowerCase());
        if (isLegacyGrp && parts.length === 5) {
          // Legacy grp::{resource}::{analysis_type}::{prepared_sample}::{experiment}::{parameter}
          return [
            parts[0],
            parts[2],
            canonicalDomainSlug(parts[1]),
            parts[4],
            "unassigned",
            parts[3]
          ].join("::");
        }
        if (parts.length >= 3) {
          parts[2] = canonicalDomainSlug(parts[2]);
        }
        if (parts.length === 4 || parts.length === 6) {
          return parts.join("::");
        }
        if (parts.length === 5) {
          parts.push("");
          return parts.join("::");
        }
        if (parts.length > 6) {
          return parts.slice(0, 6).join("::");
        }
        return parts.join("::");
      }
      if (rawKeyOrResource && typeof rawKeyOrResource === "object") {
        const obj = rawKeyOrResource;
        if (
          typeof obj.replicate_group_key === "string" &&
          obj.replicate_group_key.indexOf("::") !== -1 &&
          !obj.resource_name &&
          !obj.resource
        ) {
          return normalizeReplicateGroupKey(obj.replicate_group_key);
        }
        return [
          String(obj.resource_name || obj.resource || "").trim().toLowerCase(),
          String(obj.prepared_sample || obj.prepared_sample_name || "").trim().toLowerCase(),
          canonicalDomainSlug(obj.analysis_type || obj.domain || ""),
          String(obj.parameter_name || obj.parameter || "").trim().toLowerCase(),
          String(groupContextLabel(obj) || "").trim().toLowerCase(),
          String(obj.experiment || obj.experiment_name || "").trim().toLowerCase()
        ].join("::");
      }
      return [
        String(rawKeyOrResource || "").trim().toLowerCase(),
        String(preparedSample || "").trim().toLowerCase(),
        canonicalDomainSlug(analysisType || ""),
        String(parameter || "").trim().toLowerCase(),
        String(prepMethod || "unassigned").trim().toLowerCase(),
        String(experiment || "").trim().toLowerCase()
      ].join("::");
    }

    function matchesReplicateGroupKey(a, b) {
      if (!a || !b) return false;
      const na = normalizeReplicateGroupKey(String(a));
      const nb = normalizeReplicateGroupKey(String(b));
      if (!na || !nb) return false;
      if (na === nb) return true;
      const pa = na.split("::");
      const pb = nb.split("::");
      if (pa.length >= 4 && pb.length >= 4) {
        const samePrefix = pa.slice(0, 4).join("::") === pb.slice(0, 4).join("::");
        if (!samePrefix) return false;
        if (pa.length === 4 || pb.length === 4) return true;
        if ((pa[4] === "unassigned" || pb[4] === "unassigned") && pa[5] === pb[5]) return true;
      }
      return false;
    }

    function computeMedianNumeric(vals) {
      const clean = (vals || [])
        .filter(v => typeof v === "number" && Number.isFinite(v))
        .slice()
        .sort((a, b) => a - b);
      if (!clean.length) return null;
      const mid = Math.floor(clean.length / 2);
      return clean.length % 2 === 1 ? clean[mid] : (clean[mid - 1] + clean[mid]) / 2.0;
    }

    function getOutlierSummary(insOrOut) {
      const out = (insOrOut && insOrOut.outlier_screening) ? insOrOut.outlier_screening : (insOrOut || {});
      const s = (out && out.summary && typeof out.summary === "object") ? out.summary : out;
      const firstNum = (...cands) => {
        for (const c of cands) {
          if (typeof c === "number" && Number.isFinite(c)) return c;
        }
        return null;
      };
      const allGroups = [];
      const allParams = [];
      if (out && out.by_tab && typeof out.by_tab === "object") {
        Object.values(out.by_tab).forEach(t => {
          const grps = (t && (t.replicate_groups || t.groups)) || [];
          if (Array.isArray(grps)) allGroups.push(...grps);
          const prms = (t && (t.param_rsd_table || t.parameters)) || [];
          if (Array.isArray(prms)) allParams.push(...prms);
        });
      }
      const multiRepGroups = allGroups.filter(
        g => g && (g.n || 0) >= 2 && typeof g.rsd_within_pct === "number" && Number.isFinite(g.rsd_within_pct)
      );
      const flaggedActive = firstNum(
        s && s.flagged_active,
        s && s.flagged_active_groups,
        s && s.flagged_replicate_groups,
        out && out.flagged_active,
        out && out.flagged_active_groups,
        out && out.flagged_replicate_groups
      ) ?? (allGroups.length ? allGroups.filter(g => Boolean(g && (g.active_flagged ?? g.flagged_active))).length : 0);
      const flaggedRaw = firstNum(
        s && s.flagged_raw,
        s && s.flagged_raw_groups,
        out && out.flagged_raw,
        out && out.flagged_raw_groups
      ) ?? (allGroups.length ? allGroups.filter(g => Boolean(g && g.raw_flagged)).length : 0);
      const suppressedTrace = firstNum(
        s && s.suppressed_trace,
        s && s.suppressed_low_abundance_groups,
        s && s.suppressed_below_cutoff_groups,
        out && out.suppressed_trace,
        out && out.suppressed_low_abundance_groups,
        out && out.suppressed_below_cutoff_groups
      ) ?? Math.max(0, flaggedRaw - flaggedActive);
      const totalGroups = firstNum(
        s && s.total_groups,
        s && s.total_replicate_groups,
        out && out.total_groups,
        out && out.total_replicate_groups
      ) ?? allGroups.length;
      const rsdDefinedGroups = firstNum(
        s && s.rsd_defined_groups,
        s && s.multi_rep_groups,
        out && out.rsd_defined_groups
      ) ?? multiRepGroups.length;
      const withinRsdMedian = firstNum(
        s && s.overall_within_rsd_median,
        s && s.within_rsd_median,
        s && s.median_within_rsd_pct,
        out && out.overall_within_rsd_median,
        out && out.within_rsd_median,
        out && out.median_within_rsd_pct
      ) ?? computeMedianNumeric(multiRepGroups.map(g => g.rsd_within_pct));
      const withinSdMedian = firstNum(
        s && s.overall_within_sd_median,
        s && s.within_sd_median,
        out && out.overall_within_sd_median,
        out && out.within_sd_median
      ) ?? computeMedianNumeric(multiRepGroups.map(g => (typeof g.within_sd === "number" ? g.within_sd : g.sd)));
      const betweenRsdMedian = firstNum(
        s && s.overall_between_rsd_median,
        s && s.between_rsd_median,
        s && s.median_between_rsd_pct,
        out && out.overall_between_rsd_median,
        out && out.between_rsd_median,
        out && out.median_between_rsd_pct
      ) ?? computeMedianNumeric(
        (allParams.length ? allParams : multiRepGroups).map(
          x => (typeof x.between_rsd_pct === "number" ? x.between_rsd_pct : x.rsd_between_pct)
        )
      );
      const betweenSdMedian = firstNum(
        s && s.overall_between_sd_median,
        s && s.between_sd_median,
        out && out.overall_between_sd_median,
        out && out.between_sd_median
      ) ?? computeMedianNumeric(
        (allParams.length ? allParams : multiRepGroups).map(
          x => (typeof x.between_sd === "number" ? x.between_sd : x.pooled_sd)
        )
      );
      const dixonActive = firstNum(
        s && s.dixon_flagged,
        s && s.dixon_active,
        s && s.dixon_q_groups_active,
        out && out.dixon_flagged,
        out && out.dixon_active,
        out && out.dixon_q_groups_active
      ) ?? allGroups.filter(g => Boolean(g && g.raw_dixon && !g.below_cutoff)).length;
      const dixonRaw = firstNum(
        s && s.dixon_raw,
        s && s.dixon_q_groups_raw,
        out && out.dixon_raw,
        out && out.dixon_q_groups_raw
      ) ?? allGroups.filter(g => Boolean(g && g.raw_dixon)).length;
      return {
        flaggedActive,
        flaggedRaw,
        suppressedTrace,
        totalGroups,
        rsdDefinedGroups,
        withinRsdMedian,
        withinSdMedian,
        betweenRsdMedian,
        betweenSdMedian,
        dixonActive,
        dixonRaw
      };
    }

    window.canonicalDomainSlug = canonicalDomainSlug;
    window.groupContextLabel = groupContextLabel;
    window.normalizeReplicateGroupKey = normalizeReplicateGroupKey;
    window.matchesReplicateGroupKey = matchesReplicateGroupKey;
    window.computeMedianNumeric = computeMedianNumeric;
    window.getOutlierSummary = getOutlierSummary;

    const BioCirvQcClient = {
      canonicalDomainSlug,
      groupContextLabel,
      normalizeReplicateGroupKey,
      matchesReplicateGroupKey,
      getOutlierSummary,
      _pendingSignInCallback: null,

      hasConfirmedIdentity() {
        try {
          const raw = localStorage.getItem(ANALYST_IDENTITY_STORAGE_KEY);
          if (!raw) return false;
          const parsed = JSON.parse(raw);
          return Boolean(parsed && parsed.email);
        } catch (_e) {
          return false;
        }
      },

      ensureSignedIn(onConfirmedCallback) {
        if (this.hasConfirmedIdentity()) {
          if (typeof onConfirmedCallback === "function") {
            onConfirmedCallback(this.getAnalystIdentity());
          }
          return true;
        }
        this._pendingSignInCallback = onConfirmedCallback || null;
        const openBtn = document.getElementById("btn-open-signin-modal");
        if (openBtn) {
          openBtn.click();
          const statusEl = document.getElementById("signin-sync-status");
          if (statusEl) {
            statusEl.textContent = "🔐 Please confirm your Analyst Email Address below to attribute this QC Review approval & Google Sheets write-back.";
          }
          return false;
        }
        if (typeof onConfirmedCallback === "function") {
          onConfirmedCallback(this.getAnalystIdentity());
        }
        return true;
      },

      getAnalystIdentity() {
        try {
          const raw = localStorage.getItem(ANALYST_IDENTITY_STORAGE_KEY);
          if (raw) {
            const parsed = JSON.parse(raw);
            return {
              email: (parsed.email || "local.analyst@lbl.gov").trim().toLowerCase(),
              name: (parsed.name || "Local Analyst").trim(),
              idToken: parsed.idToken || "",
              apiBase: (parsed.apiBase || window.BIOCIRV_API_BASE || "http://localhost:8000").replace(/\\/+$/, "")
            };
          }
        } catch (_e) {}
        return {
          email: "local.analyst@lbl.gov",
          name: "Local Analyst",
          idToken: "",
          apiBase: (window.BIOCIRV_API_BASE || "http://localhost:8000").replace(/\\/+$/, "")
        };
      },

      getUser() {
        return this.getAnalystIdentity();
      },

      setAnalystIdentity(identity) {
        const current = this.getAnalystIdentity();
        const next = {
          email: ((identity && identity.email) || current.email || "local.analyst@lbl.gov").trim().toLowerCase(),
          name: ((identity && identity.name) || current.name || "Local Analyst").trim(),
          idToken: (identity && identity.idToken !== undefined) ? identity.idToken : current.idToken,
          apiBase: ((identity && identity.apiBase) || current.apiBase || "http://localhost:8000").replace(/\\/+$/, ""),
          confirmedAt: new Date().toISOString()
        };
        window.BIOCIRV_API_BASE = next.apiBase;
        try {
          localStorage.setItem(ANALYST_IDENTITY_STORAGE_KEY, JSON.stringify(next));
        } catch (_e) {}
        window.dispatchEvent(new CustomEvent("biocirv:analyst-changed", { detail: next }));
        window.dispatchEvent(new CustomEvent("biocirv-auth-changed", { detail: next }));
        return next;
      },

      getHeaders() {
        const id = this.getAnalystIdentity();
        const headers = {
          "Content-Type": "application/json",
          "X-Analyst-Email": id.email,
          "X-Analyst-Name": id.name
        };
        if (id.idToken) {
          headers["Authorization"] = `Bearer ${id.idToken}`;
        }
        return headers;
      },

      getLocalDecisions() {
        try {
          const raw = localStorage.getItem(LOCAL_DECISIONS_STORAGE_KEY);
          if (raw) {
            const arr = JSON.parse(raw);
            if (Array.isArray(arr)) return arr;
          }
        } catch (_e) {}
        return [];
      },

      saveLocalDecisions(list) {
        try {
          localStorage.setItem(LOCAL_DECISIONS_STORAGE_KEY, JSON.stringify(list || []));
        } catch (_e) {}
      },

      mirrorToPage2DecisionsStore(item) {
        if (!item) return;
        try {
          const raw = localStorage.getItem(PAGE2_DECISIONS_STORAGE_KEY);
          const store = raw ? JSON.parse(raw) : {};
          const repGroupKey = item.replicate_group_key || item.group_key || (
            (item.resource_name || item.prepared_sample_name || item.prepared_sample || item.parameter_name || item.parameter)
              ? normalizeReplicateGroupKey(item, item.resource_name)
              : null
          );
          const key = item.decision_key || item.key || (
            (item.scope === "replicate_group" || item.triage_scope === "group" || (!item.scope && repGroupKey)) && repGroupKey
              ? `grp::${repGroupKey}`
              : (item.id ? `api::${item.id}` : `finding::${Date.now()}`)
          );
          const existing = store[key] || {};
          const normScope = (item.scope === "finding" || item.scope === "ad_hoc_finding")
            ? "ad_hoc_finding"
            : ((item.scope === "single" || item.scope === "single_record") ? "single_record" : "replicate_group");
          const rawAct = String(item.decision || item.decision_action || item.new_qc_status || item.new_qc_pass || "").trim().toLowerCase();
          let mappedDecision = existing.decision || "accept_with_note";
          if (rawAct === "keep" || rawAct === "approve_pass" || rawAct === "pass" || item.new_qc_pass === "pass" || item.new_qc_status === "pass") {
            mappedDecision = "keep";
          } else if (rawAct === "trace_ignore") {
            mappedDecision = "trace_ignore";
          } else if (rawAct === "re_assay" || rawAct === "needs_retest" || rawAct === "retest") {
            mappedDecision = "re_assay";
          } else if (rawAct === "exclude_qc_fail" || rawAct === "flag_fail" || rawAct === "reject_fail" || rawAct === "fail" || item.new_qc_pass === "fail" || item.new_qc_status === "fail") {
            mappedDecision = "exclude_qc_fail";
          } else if (rawAct === "accept_with_note" || rawAct === "keep_note" || rawAct === "in_review" || rawAct === "provisional") {
            mappedDecision = "accept_with_note";
          }
          const nextAssignee = (item.assigned_to_email !== undefined && item.assigned_to_email !== null && String(item.assigned_to_email).trim() !== "")
            ? String(item.assigned_to_email).trim()
            : (existing.assigned_to_email || "");
          store[key] = {
            ...existing,
            key,
            replicate_group_key: repGroupKey || existing.replicate_group_key || "",
            api_decision_id: item.api_decision_id || item.id || existing.api_decision_id || null,
            scope: normScope,
            triage_scope: normScope === "single_record" ? "single" : "group",
            resource_name: item.resource_name || existing.resource_name || "",
            analysis_type: item.analysis_type || existing.analysis_type || "",
            prepared_sample: item.prepared_sample_name || item.prepared_sample || existing.prepared_sample || "",
            prep_method: item.prep_method || existing.prep_method || "",
            experiment: item.experiment_name || item.experiment || existing.experiment || "",
            record_id: item.record_id || existing.record_id || "",
            record_ids: Array.isArray(item.target_record_ids)
              ? item.target_record_ids.join("|")
              : (item.target_record_ids || (Array.isArray(item.record_ids) ? item.record_ids.join("|") : item.record_ids) || item.record_id || existing.record_ids || ""),
            parameter: item.parameter_name || item.parameter || existing.parameter || "Resource-Level Observation",
            decision: mappedDecision,
            status: item.status || (item.decision_status === "resolved" || item.review_status === "resolved" ? "approved" : (item.decision_status || item.review_status || existing.status || "open")),
            note: item.review_note || item.rationale_note || item.audit_note || item.note || existing.note || "",
            assigned_to_email: nextAssignee,
            reviewer_email: item.resolved_by_email || item.reviewer_email || item.analyst_email || existing.reviewer_email || "",
            synced_to_gsheet: Boolean(item.synced_to_gsheet || existing.synced_to_gsheet),
            updated_at: (item.updated_at || item.created_at || new Date().toISOString()).slice(0, 19).replace("T", " ")
          };
          localStorage.setItem(PAGE2_DECISIONS_STORAGE_KEY, JSON.stringify(store));
        } catch (_e) {}
      },

      upsertLocalDecision(item) {
        const list = this.getLocalDecisions();
        const idx = list.findIndex(d =>
          (item.id && d.id === item.id) ||
          (item.decision_key && d.decision_key === item.decision_key) ||
          (item.record_id && d.record_id === item.record_id && d.scope === item.scope)
        );
        let savedItem = item;
        if (idx >= 0) {
          savedItem = { ...list[idx], ...item, updated_at: new Date().toISOString() };
          list[idx] = savedItem;
        } else {
          savedItem = {
            id: item.id || Date.now() + Math.floor(Math.random() * 1000),
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            ...item
          };
          list.unshift(savedItem);
        }
        this.saveLocalDecisions(list);
        this.mirrorToPage2DecisionsStore(savedItem);
        return list;
      },

      async listDecisions(filters) {
        const f = filters || {};
        const id = this.getAnalystIdentity();
        const params = new URLSearchParams();
        if (f.resource_name) params.set("resource_name", f.resource_name);
        if (f.scope) params.set("scope", f.scope);
        if (f.review_status || f.status) params.set("status", f.review_status || f.status);
        if (f.assigned_to_email) params.set("assigned_to_email", f.assigned_to_email);

        try {
          const resp = await fetch(`${id.apiBase}/v1/qc/decisions?${params.toString()}`, {
            method: "GET",
            headers: this.getHeaders()
          });
          if (resp.ok) {
            const data = await resp.json();
            const items = data.decisions || data.items || [];
            if (Array.isArray(items) && !f.resource_name && !f.scope && !f.review_status && !f.assigned_to_email) {
              this.saveLocalDecisions(items);
              items.forEach(d => this.mirrorToPage2DecisionsStore(d));
            }
            return { ok: true, source: "api", count: data.count || items.length, decisions: items };
          }
        } catch (_e) {}

        let local = this.getLocalDecisions();
        if (f.resource_name) {
          const targetRes = f.resource_name.trim().toLowerCase();
          local = local.filter(d => String(d.resource_name || "").trim().toLowerCase() === targetRes);
        }
        if (f.scope) {
          local = local.filter(d => d.scope === f.scope);
        }
        if (f.review_status || f.status) {
          const st = f.review_status || f.status;
          local = local.filter(d => (d.status || d.review_status) === st);
        }
        if (f.assigned_to_email) {
          const targetEmail = f.assigned_to_email.trim().toLowerCase();
          if (targetEmail === "unassigned") {
            local = local.filter(d => !d.assigned_to_email);
          } else {
            local = local.filter(d => String(d.assigned_to_email || "").trim().toLowerCase() === targetEmail);
          }
        }
        return { ok: true, source: "local", count: local.length, decisions: local };
      },

      async fetchDecisions(filters) {
        return this.listDecisions(filters);
      },

      async submitDecision(payload) {
        const id = this.getAnalystIdentity();
        const repGroupKey = payload.replicate_group_key || payload.group_key || (
          (payload.resource_name || payload.prepared_sample_name || payload.prepared_sample || payload.parameter_name || payload.parameter)
            ? normalizeReplicateGroupKey(payload, payload.resource_name)
            : null
        );
        const rawAction = String(
          payload.decision_action || payload.action || payload.decision || payload.new_qc_status || payload.new_qc_pass || "in_review"
        ).trim().toLowerCase();
        let canonicalAction = "in_review";
        let canonicalStatus = payload.decision_status || payload.review_status || payload.status || "in_review";
        let canonicalNewQcPass = null;
        let legacyNewQcStatus = "provisional";
        let legacyDecision = "accept_with_note";

        if (rawAction === "approve_pass" || rawAction === "keep" || rawAction === "pass" || rawAction === "qc_pass" || rawAction === "trace_ignore") {
          canonicalAction = rawAction === "trace_ignore" ? "trace_ignore" : "approve_pass";
          canonicalStatus = "resolved";
          canonicalNewQcPass = "pass";
          legacyNewQcStatus = "pass";
          legacyDecision = rawAction === "trace_ignore" ? "trace_ignore" : "keep";
        } else if (rawAction === "reject_fail" || rawAction === "exclude_qc_fail" || rawAction === "flag_fail" || rawAction === "fail" || rawAction === "qc_fail") {
          canonicalAction = "reject_fail";
          canonicalStatus = "resolved";
          canonicalNewQcPass = "fail";
          legacyNewQcStatus = "fail";
          legacyDecision = "exclude_qc_fail";
        } else if (rawAction === "needs_retest" || rawAction === "re_assay" || rawAction === "retest") {
          canonicalAction = "needs_retest";
          canonicalStatus = "needs_retest";
          canonicalNewQcPass = null;
          legacyNewQcStatus = "re_assay";
          legacyDecision = "re_assay";
        } else {
          canonicalAction = "in_review";
          if (!canonicalStatus || canonicalStatus === "pending" || canonicalStatus === "provisional" || canonicalStatus === "open") {
            canonicalStatus = "in_review";
          }
          canonicalNewQcPass = null;
          legacyNewQcStatus = "provisional";
          legacyDecision = "accept_with_note";
        }

        const targetRecs = Array.isArray(payload.target_record_ids)
          ? payload.target_record_ids
          : (Array.isArray(payload.record_ids)
            ? payload.record_ids
            : (payload.record_ids ? String(payload.record_ids).split("|").map(s => s.trim()).filter(Boolean) : (payload.record_id ? [String(payload.record_id)] : [])));
        const primaryRecId = payload.record_id || targetRecs[0] || repGroupKey || null;
        const rationaleList = Array.isArray(payload.rationale_chips)
          ? payload.rationale_chips
          : (Array.isArray(payload.rationale_tags) ? payload.rationale_tags : []);
        const noteText = payload.review_note || payload.audit_note || payload.note || "";

        const body = {
          id: payload.api_decision_id || payload.id || null,
          decision_id: payload.api_decision_id || payload.decision_id || payload.id || null,
          decision_key: payload.decision_key || payload.key || (repGroupKey ? `grp::${repGroupKey}` : null),
          replicate_group_key: repGroupKey,
          scope: payload.scope || "finding",
          resource_name: (payload.resource_name || "unknown").trim().toLowerCase(),
          analysis_type: (payload.analysis_type || "proximate").trim().toLowerCase(),
          parameter_name: (payload.parameter_name || payload.parameter || "Resource-Level Observation").trim(),
          prepared_sample_name: payload.prepared_sample_name || payload.prepared_sample || null,
          field_sample_name: payload.field_sample_name || payload.field_sample || null,
          experiment_name: payload.experiment_name || payload.experiment || null,
          record_id: primaryRecId,
          record_ids: targetRecs,
          target_record_ids: targetRecs,
          old_qc_pass: payload.old_qc_pass || payload.previous_qc_status || "pass",
          previous_qc_status: payload.previous_qc_status || payload.old_qc_pass || "pass",
          new_qc_pass: canonicalNewQcPass,
          new_qc_status: legacyNewQcStatus,
          decision_action: canonicalAction,
          decision: payload.decision || legacyDecision,
          decision_status: canonicalStatus,
          status: canonicalStatus,
          rationale_chips: rationaleList,
          rationale_tags: rationaleList,
          review_note: noteText,
          audit_note: noteText,
          assigned_to_email: payload.assigned_to_email ? payload.assigned_to_email.trim().toLowerCase() : null,
          gsheet_writeback_requested: Boolean(payload.gsheet_writeback_requested)
        };

        try {
          const resp = await fetch(`${id.apiBase}/v1/qc/decisions`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify(body)
          });
          if (resp.ok) {
            const data = await resp.json();
            const mergedDec = data.decision ? { ...body, ...data.decision, api_decision_id: data.decision.id } : body;
            this.upsertLocalDecision(mergedDec);
            window.dispatchEvent(new CustomEvent("biocirv:decisions-updated", { detail: mergedDec }));
            window.dispatchEvent(new CustomEvent("biocirv-decisions-updated", { detail: mergedDec }));
            return { ok: true, source: "api", ...data, decision: mergedDec };
          }
        } catch (_e) {}

        const localEntry = {
          id: Date.now() + Math.floor(Math.random() * 1000),
          ...body,
          analyst_email: id.email,
          reviewer_email: id.email,
          sync_status: "local_only",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        this.upsertLocalDecision(localEntry);
        window.dispatchEvent(new CustomEvent("biocirv:decisions-updated", { detail: localEntry }));
        window.dispatchEvent(new CustomEvent("biocirv-decisions-updated", { detail: localEntry }));
        return { ok: true, source: "local", status: "saved_offline", decision: localEntry };
      },

      async submitFinding(payload) {
        return this.submitDecision({ ...payload, scope: payload.scope || "finding", review_status: "open" });
      },

      async assignTask(decisionId, assignedToEmail, note) {
        const id = this.getAnalystIdentity();
        const cleanEmail = assignedToEmail ? assignedToEmail.trim().toLowerCase() : null;
        try {
          const resp = await fetch(`${id.apiBase}/v1/qc/decisions/${encodeURIComponent(String(decisionId))}/assign`, {
            method: "PATCH",
            headers: this.getHeaders(),
            body: JSON.stringify({ assigned_to_email: cleanEmail, note: note || null })
          });
          if (resp.ok) {
            const data = await resp.json();
            if (data.decision) this.upsertLocalDecision(data.decision);
            window.dispatchEvent(new CustomEvent("biocirv:decisions-updated", { detail: data.decision }));
            window.dispatchEvent(new CustomEvent("biocirv-decisions-updated", { detail: data.decision }));
            return { ok: true, source: "api", ...data };
          }
        } catch (_e) {}

        const list = this.getLocalDecisions();
        const found = list.find(d => String(d.id) === String(decisionId) || String(d.decision_key) === String(decisionId));
        if (found) {
          found.assigned_to_email = cleanEmail;
          if (note) {
            found.audit_note = `${found.audit_note || ""} | [Assigned to ${cleanEmail || "unassigned"}: ${note}]`.replace(/^\\s*\\|\\s*/, "");
          }
          found.updated_at = new Date().toISOString();
          this.saveLocalDecisions(list);
          this.mirrorToPage2DecisionsStore(found);
          window.dispatchEvent(new CustomEvent("biocirv:decisions-updated", { detail: found }));
          window.dispatchEvent(new CustomEvent("biocirv-decisions-updated", { detail: found }));
          return { ok: true, source: "local", status: "assigned_offline", decision: found };
        }
        return { ok: false, source: "local", status: "not_found" };
      },

      async assignDecision(decisionId, assignedToEmail, note) {
        return this.assignTask(decisionId, assignedToEmail, note);
      },

      async approveDecisions(itemsOrPayload, syncToGsheet = true) {
        const id = this.getAnalystIdentity();
        let requestBody;
        if (Array.isArray(itemsOrPayload)) {
          requestBody = {
            sync_to_gsheet: Boolean(syncToGsheet),
            items: itemsOrPayload.map(e => {
              const repGroupKey = e.replicate_group_key || normalizeReplicateGroupKey(e, e.resource_name);
              return {
                decision_key: e.key || e.decision_key || (repGroupKey ? `grp::${repGroupKey}` : null),
                replicate_group_key: repGroupKey,
                scope: e.scope || (e.triage_scope === "single" ? "single_record" : "replicate_group"),
                resource_name: e.resource_name || "",
                analysis_type: e.analysis_type || "",
                prepared_sample_name: e.prepared_sample || e.prepared_sample_name || "",
                field_sample_name: e.field_sample || e.field_sample_name || "",
                experiment_name: e.experiment || e.experiment_name || "",
                record_id: e.record_id || (e.triage_scope === "single" ? (e.dixon_candidate_id || "") : ""),
                record_ids: e.record_ids || e.all_group_record_ids || e.record_id || "",
                parameter_name: e.parameter || e.parameter_name || "",
                decision: (!e.decision || e.decision === "pending") ? "exclude_qc_fail" : e.decision,
                rationale_note: e.note || e.rationale_note || e.audit_note || "",
                assigned_to_email: e.assigned_to_email || null,
                anomaly_flags_json: e.dixon_q ? JSON.stringify({ dixon_q: e.dixon_q, rsd_within_pct: e.rsd_within_pct }) : ""
              };
            })
          };
        } else if (itemsOrPayload && Array.isArray(itemsOrPayload.items)) {
          requestBody = itemsOrPayload;
        } else {
          const p = itemsOrPayload || {};
          const repGroupKey = p.replicate_group_key || normalizeReplicateGroupKey(p, p.resource_name);
          requestBody = {
            sync_to_gsheet: Boolean(p.sync_to_gsheet ?? syncToGsheet),
            items: [{
              decision_key: p.key || p.decision_key || (repGroupKey ? `grp::${repGroupKey}` : null),
              replicate_group_key: repGroupKey,
              scope: p.scope || "single_record",
              resource_name: p.resource_name || "",
              analysis_type: p.analysis_type || "",
              record_id: p.record_id || "",
              target_record_ids: p.target_record_ids || (p.record_id ? [p.record_id] : []),
              parameter_name: p.parameter_name || p.parameter || "",
              decision: p.decision || (p.new_qc_status === "pass" ? "keep" : "exclude_qc_fail"),
              rationale_note: p.audit_note || p.note || "",
              assigned_to_email: p.assigned_to_email || null
            }]
          };
        }

        try {
          const resp = await fetch(`${id.apiBase}/v1/qc/decisions/approve`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify(requestBody)
          });
          if (resp.ok) {
            const data = await resp.json();
            const decisionsList = data.decisions || data.results || [];
            decisionsList.forEach(d => this.upsertLocalDecision(d));
            window.dispatchEvent(new CustomEvent("biocirv:decisions-updated", { detail: data }));
            window.dispatchEvent(new CustomEvent("biocirv-decisions-updated", { detail: data }));
            return { ok: true, source: "api", data, decisions: decisionsList, ...data };
          }
        } catch (_e) {}

        const fallbackItems = (requestBody.items || []).map(it => {
          const localEntry = {
            id: Date.now() + Math.floor(Math.random() * 1000),
            decision_key: it.decision_key || `local::${Date.now()}`,
            scope: it.scope || "single_record",
            resource_name: (it.resource_name || "unknown").trim().toLowerCase(),
            analysis_type: (it.analysis_type || "proximate").trim().toLowerCase(),
            parameter_name: it.parameter_name || "unknown",
            record_id: it.record_id || null,
            record_ids: it.record_ids || "",
            decision: it.decision || "exclude_qc_fail",
            rationale_note: it.rationale_note || "",
            reviewer_email: id.email,
            assigned_to_email: it.assigned_to_email || null,
            status: "approved",
            synced_to_gsheet: false
          };
          this.upsertLocalDecision(localEntry);
          return localEntry;
        });
        window.dispatchEvent(new CustomEvent("biocirv:decisions-updated", { detail: fallbackItems }));
        window.dispatchEvent(new CustomEvent("biocirv-decisions-updated", { detail: fallbackItems }));
        return {
          ok: true,
          source: "local",
          status: "approved_offline",
          data: { decisions: fallbackItems },
          decisions: fallbackItems
        };
      },

      async revertDecision(decisionId, reason) {
        const id = this.getAnalystIdentity();
        try {
          const resp = await fetch(`${id.apiBase}/v1/qc/decisions/${encodeURIComponent(String(decisionId))}/revert`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify({
              reason: reason || "Reverted by analyst",
              revert_to_status: "pass",
              sync_to_gsheet: true
            })
          });
          if (resp.ok) {
            const data = await resp.json();
            if (data.decision) this.upsertLocalDecision(data.decision);
            window.dispatchEvent(new CustomEvent("biocirv:decisions-updated", { detail: data.decision }));
            window.dispatchEvent(new CustomEvent("biocirv-decisions-updated", { detail: data.decision }));
            return { ok: true, source: "api", ...data };
          }
        } catch (_e) {}

        const list = this.getLocalDecisions();
        const found = list.find(d => String(d.id) === String(decisionId) || String(d.decision_key) === String(decisionId));
        if (found) {
          found.review_status = "reverted";
          found.status = "reverted";
          found.new_qc_status = "pass";
          found.updated_at = new Date().toISOString();
          this.saveLocalDecisions(list);
          this.mirrorToPage2DecisionsStore(found);
          this.broadcastQcUpdate(found);
          window.dispatchEvent(new CustomEvent("biocirv:decisions-updated", { detail: found }));
          window.dispatchEvent(new CustomEvent("biocirv-decisions-updated", { detail: found }));
          return { ok: true, source: "local", status: "reverted_offline", decision: found };
        }
        return { ok: false, source: "local", status: "not_found" };
      },

      broadcastQcUpdate(detail) {
        try {
          if (typeof BroadcastChannel !== "undefined") {
            const bc = new BroadcastChannel("biocirv_qc_decisions");
            bc.postMessage({
              type: "qc_decision_saved",
              timestamp: Date.now(),
              detail: detail || null
            });
            bc.close();
          }
        } catch (_e) {}
      },

      resolveRecordTable(analysisTypeOrDomain) {
        const raw = String(analysisTypeOrDomain || "").trim().toLowerCase();
        if (raw.endsWith("_record")) return raw;
        if (raw.includes("ult")) return "ultimate_record";
        if (raw.includes("comp")) return "compositional_record";
        if (raw.includes("icp") || raw.includes("elem")) return "icp_record";
        if (raw.includes("xrd")) return "xrd_record";
        if (raw.includes("xrf") || raw === "ash") return "xrf_record";
        if (raw.includes("calor")) return "calorimetry_record";
        if (raw.includes("ferm")) return "fermentation_record";
        if (raw.includes("pretreat") || raw.includes("hydro") || raw.includes("conv")) return "pretreatment_record";
        if (raw.includes("gasif")) return "gasification_record";
        return "proximate_record";
      },

      normalizeTrayWorkbenchItem(item, sourceLabel) {
        const it = item || {};
        const rawScope = String(it.selection_scope || it.scope || it.triage_scope || "replicate_group").toLowerCase();
        const selectionScope = (rawScope === "single" || rawScope === "single_record")
          ? "single_record"
          : "replicate_group";
        const targetIds = Array.isArray(it.target_record_ids)
          ? it.target_record_ids.map(x => String(x).trim()).filter(Boolean)
          : (Array.isArray(it.record_ids)
              ? it.record_ids.map(x => String(x).trim()).filter(Boolean)
              : String(it.record_ids || it.record_id || "")
                  .split(/[|,]/g)
                  .map(x => x.trim())
                  .filter(Boolean));
        const primaryRecordId = String(it.record_id || targetIds[0] || "").trim() || null;
        const effectiveIds = selectionScope === "single_record" && primaryRecordId
          ? [primaryRecordId]
          : (targetIds.length ? targetIds : (primaryRecordId ? [primaryRecordId] : []));
        const analysisType = String(it.analysis_type || it.domain || "proximate").trim().toLowerCase();
        const recordTable = this.resolveRecordTable(it.record_table || analysisType);
        const reviewNote = String(
          it.review_note || it.note || it.audit_note ||
          (sourceLabel ? `Flagged from ${sourceLabel}` : "Flagged from Selection & Export Tray")
        ).trim();
        const repGroupKey = (
          it.resource_name || it.prepared_sample_name || it.prepared_sample || it.parameter_name || it.parameter || it.replicate_group_key || it.group_key
        )
          ? normalizeReplicateGroupKey(it, it.resource_name)
          : null;
        return {
          record_table: recordTable,
          record_id: primaryRecordId,
          record_ids: effectiveIds,
          target_record_ids: effectiveIds,
          replicate_group_key: repGroupKey,
          selection_scope: selectionScope,
          resource_name: String(it.resource_name || "unknown").trim().toLowerCase(),
          analysis_type: analysisType,
          parameter_name: String(it.parameter_name || it.parameter || "Observation").trim(),
          prepared_sample: it.prepared_sample || it.prepared_sample_name || null,
          field_sample: it.field_sample || it.field_sample_name || null,
          prep_method: it.prep_method || it.group_context_label || null,
          experiment: it.experiment || it.experiment_name || null,
          flag_type: String(it.flag_type || "analyst_flagged"),
          flag_trigger_value: it.flag_trigger_value != null ? String(it.flag_trigger_value) : null,
          old_qc_pass: String(it.old_qc_pass || it.previous_qc_status || "pass"),
          recommended_qc_status: it.recommended_qc_status || it.new_qc_status || "provisional",
          assigned_to_email: it.assigned_to_email || null,
          review_note: reviewNote,
          note: reviewNote
        };
      },

      async exportTrayToWorkbench(payload, sourceLabel) {
        const id = this.getAnalystIdentity();
        const rawItems = Array.isArray(payload)
          ? payload
          : (payload && Array.isArray(payload.items) ? payload.items : [payload || {}]);
        const normalizedItems = rawItems
          .map(it => this.normalizeTrayWorkbenchItem(it, sourceLabel))
          .filter(it => it.record_id || (Array.isArray(it.record_ids) && it.record_ids.length > 0));
        const primaryItem = normalizedItems[0] || this.normalizeTrayWorkbenchItem(
          Array.isArray(payload) ? (payload[0] || {}) : (payload || {}),
          sourceLabel
        );
        const openWorkbench = (payload && !Array.isArray(payload) && payload.open_workbench === false) ? false : true;

        const reqBody = {
          ...primaryItem,
          items: normalizedItems.length ? normalizedItems : [primaryItem]
        };

        const candidateUrls = [];
        if (window.location.protocol === "http:" || window.location.protocol === "https:") {
          candidateUrls.push("/v1/qc/tray-to-workbench");
        }
        if (id.apiBase) {
          candidateUrls.push(`${id.apiBase}/v1/qc/tray-to-workbench`);
        }

        for (const url of candidateUrls) {
          try {
            const resp = await fetch(url, {
              method: "POST",
              headers: this.getHeaders(),
              credentials: "include",
              body: JSON.stringify(reqBody)
            });
            if (resp.ok) {
              const data = await resp.json();
              if (Array.isArray(data.decisions)) {
                data.decisions.forEach(d => this.upsertLocalDecision(d));
              } else if (data.decision) {
                this.upsertLocalDecision(data.decision);
              }
              const broadcastTarget = data.decisions || data.decision || reqBody;
              this.broadcastQcUpdate(broadcastTarget);
              window.dispatchEvent(new CustomEvent("biocirv:decisions-updated", { detail: broadcastTarget }));
              if (openWorkbench && data.workbench_url) {
                window.location.href = data.workbench_url;
              }
              const persistedCount = data.created_count || (Array.isArray(data.decisions) ? data.decisions.length : 1);
              return { ok: true, source: "api", persisted: persistedCount, ...data };
            }
          } catch (_e) {}
        }

        const fallbackDecisions = [];
        for (const normIt of reqBody.items) {
          const fb = await this.submitFinding({
            scope: normIt.selection_scope,
            triage_scope: normIt.selection_scope === "single_record" ? "single" : "group",
            resource_name: normIt.resource_name,
            analysis_type: normIt.analysis_type,
            parameter_name: normIt.parameter_name,
            prepared_sample: normIt.prepared_sample,
            field_sample: normIt.field_sample,
            experiment: normIt.experiment,
            record_id: normIt.record_id,
            target_record_ids: normIt.target_record_ids,
            new_qc_status: normIt.recommended_qc_status,
            assigned_to_email: normIt.assigned_to_email,
            audit_note: normIt.review_note,
            sync_to_gsheet: false
          });
          if (fb && fb.decision) fallbackDecisions.push(fb.decision);
        }
        this.broadcastQcUpdate(fallbackDecisions.length ? fallbackDecisions : reqBody);
        const fallbackUrl = `/v1/dashboards/metadata/resource_audit_workbench.html?resource=${encodeURIComponent(primaryItem.resource_name)}&scope=${encodeURIComponent(primaryItem.selection_scope)}`;
        return {
          ok: true,
          source: "local",
          persisted: fallbackDecisions.length || reqBody.items.length,
          workbench_url: fallbackUrl,
          decision: fallbackDecisions[0] || null,
          decisions: fallbackDecisions
        };
      },

      openSliceExportModal(opts) {
        return window.openSliceExportModal ? window.openSliceExportModal(opts) : null;
      }
    };
    window.BioCirvQcClient = BioCirvQcClient;

    function resolveEffectiveStage1QcStatus(d) {
      if (!d || typeof d !== "object") return null;
      const revStatus = String(d.review_status || d.status || "").toLowerCase();
      const decStatus = String(d.decision_status || d.decision_action || "").toLowerCase();
      const decCode = String(d.decision || "").toLowerCase();
      const newQc = String(d.new_qc_pass || d.new_qc_status || "").toLowerCase();
      if (revStatus === "reverted" || decStatus === "revert" || decStatus === "approve_pass" || decCode === "keep" || newQc === "pass") {
        return "pass";
      }
      if (newQc === "fail" || decStatus === "reject_fail" || decCode === "exclude_qc_fail") {
        return "fail";
      }
      return null;
    }

    function extractDecisionTargetIds(d) {
      const out = [];
      if (!d || typeof d !== "object") return out;
      if (Array.isArray(d.target_record_ids)) {
        d.target_record_ids.forEach(id => {
          const clean = String(id || "").trim();
          if (clean) out.push(clean);
        });
      }
      if (Array.isArray(d.record_ids)) {
        d.record_ids.forEach(id => {
          const clean = String(id || "").trim();
          if (clean) out.push(clean);
        });
      } else if (d.record_ids) {
        String(d.record_ids).split(/[|,]/g).forEach(id => {
          const clean = String(id || "").trim();
          if (clean) out.push(clean);
        });
      }
      if (d.record_id) {
        String(d.record_id).split(/[|,]/g).forEach(id => {
          const clean = String(id || "").trim();
          if (clean) out.push(clean);
        });
      }
      return Array.from(new Set(out));
    }

    function applyLiveQcDecisionsOverlay(decisionsInput) {
      let decisions = [];
      if (Array.isArray(decisionsInput)) {
        decisions = decisionsInput;
      } else if (decisionsInput && typeof decisionsInput === "object") {
        decisions = Object.entries(decisionsInput).map(([rid, val]) => {
          if (val && typeof val === "object") {
            return { ...val, record_id: val.record_id || rid };
          }
          return { record_id: rid, new_qc_pass: String(val || "") };
        });
      } else {
        return { overlaidCount: 0, failCount: 0, totalDecisions: 0 };
      }

      const sorted = [...decisions].sort((a, b) => {
        const ta = String((a && (a.updated_at || a.reviewed_at || a.created_at)) || "");
        const tb = String((b && (b.updated_at || b.reviewed_at || b.created_at)) || "");
        return ta.localeCompare(tb);
      });

      const recordQcOverlay = new Map();
      sorted.forEach(d => {
        const effQc = resolveEffectiveStage1QcStatus(d);
        if (!effQc) return;
        const recIds = extractDecisionTargetIds(d);
        recIds.forEach(rid => {
          recordQcOverlay.set(rid, effQc);
        });
      });

      let overlaidCount = 0;
      let failCount = 0;

      if (typeof ALL_RECORDS !== "undefined" && Array.isArray(ALL_RECORDS)) {
        ALL_RECORDS.forEach(r => {
          if (!r || !r.record_id) return;
          if (!r._baseline_qc_status) {
            r._baseline_qc_status = r.qc_status || "pass";
          }
          const overQc = recordQcOverlay.get(String(r.record_id));
          if (!overQc) return;
          overlaidCount += 1;
          if (overQc === "fail") failCount += 1;
          r.qc_status = overQc;
          r.qc_pass = overQc;
          r.portal_compliant = (overQc === "pass" && !r.resource_portal_excluded);
        });
      }

      if (typeof ALL_ROWS !== "undefined" && Array.isArray(ALL_ROWS)) {
        let explorerChanged = 0;
        ALL_ROWS.forEach(r => {
          if (!r || !r.record_id) return;
          if (!r._baseline_qc_status) {
            r._baseline_qc_status = r.qc_pass || r.qc_status || "pass";
          }
          if (!r._baseline_data_status) {
            r._baseline_data_status = r.data_status || "Portal Compliant";
          }
          const overQc = recordQcOverlay.get(String(r.record_id));
          if (!overQc) return;
          overlaidCount += 1;
          if (overQc === "fail") failCount += 1;
          const nextDataStatus = overQc === "fail" ? "Raw" : (overQc === "pass" ? "Portal Compliant" : r._baseline_data_status);
          if (r.qc_pass !== overQc || r.qc_status !== overQc || r.data_status !== nextDataStatus) {
            r.qc_pass = overQc;
            r.qc_status = overQc;
            r.data_status = nextDataStatus;
            explorerChanged += 1;
          }
        });
        if (explorerChanged > 0 && typeof applyFilters === "function") {
          try { applyFilters(); } catch (_e) {}
        }
      }

      if (typeof BUNDLE !== "undefined" && BUNDLE && Array.isArray(BUNDLE.rows)) {
        BUNDLE.rows.forEach(row => {
          if (!Array.isArray(row) || row.length < 17) return;
          const rid = String(row[2] || "");
          if (!rid) return;
          const overQc = recordQcOverlay.get(rid);
          if (overQc) {
            row[15] = overQc;
            row[16] = (overQc === "pass");
          }
        });
      }

      if (typeof BUNDLE !== "undefined" && BUNDLE && BUNDLE.insights && typeof BUNDLE.insights === "object") {
        Object.values(BUNDLE.insights).forEach(ins => {
          const byTab = ins && ins.outlier_screening && ins.outlier_screening.by_tab;
          if (!byTab || typeof byTab !== "object") return;
          let totalFlaggedActive = 0;
          let anyResourceOverlaid = false;
          Object.values(byTab).forEach(tabObj => {
            const groups = (tabObj && (tabObj.replicate_groups || tabObj.groups)) || null;
            if (!Array.isArray(groups)) return;
            let tabFlaggedActive = 0;
            let anyTabOverlaid = false;
            groups.forEach(g => {
              if (!Array.isArray(g.replicates)) return;
              let passCnt = 0;
              let failCnt = 0;
              let anyOverlaid = false;
              const passVals = [];
              const allVals = [];
              g.replicates.forEach(rep => {
                if (!rep._baseline_qc) rep._baseline_qc = rep.qc || "pass";
                const overQc = recordQcOverlay.get(String(rep.id || ""));
                if (overQc) {
                  anyOverlaid = true;
                  anyTabOverlaid = true;
                  anyResourceOverlaid = true;
                }
                rep.qc = overQc || rep._baseline_qc;
                if (rep.qc === "fail") {
                  failCnt += 1;
                } else {
                  passCnt += 1;
                  if (typeof rep.val === "number" && !Number.isNaN(rep.val)) passVals.push(rep.val);
                }
                if (typeof rep.val === "number" && !Number.isNaN(rep.val)) allVals.push(rep.val);
              });
              g.qc_pass_count = passCnt;
              g.qc_fail_count = failCnt;
              g.qc_mixed = passCnt > 0 && failCnt > 0;
              const activeVals = passVals.length > 0 ? passVals : allVals;
              if (activeVals.length > 0) {
                const meanVal = activeVals.reduce((s, v) => s + v, 0) / activeVals.length;
                g.mean = meanVal;
                if (activeVals.length > 1) {
                  const variance = activeVals.reduce((s, v) => s + Math.pow(v - meanVal, 2), 0) / (activeVals.length - 1);
                  g.sd = Math.sqrt(variance);
                  g.within_sd = g.sd;
                  g.rsd_within_pct = Math.abs(meanVal) > 1e-9 ? (g.sd / Math.abs(meanVal)) * 100.0 : 0.0;
                } else {
                  g.sd = 0.0;
                  g.within_sd = 0.0;
                  g.rsd_within_pct = 0.0;
                }
              }
              if (g._baseline_raw_dixon === undefined) {
                g._baseline_raw_dixon = Boolean(g.raw_dixon);
              }
              if (anyOverlaid) {
                const rsdNow = g.rsd_within_pct || 0;
                g.raw_rsd20 = rsdNow > 20.0;
                g.raw_rsd10 = rsdNow > 10.0;
                const dixonStillPassing = g._baseline_raw_dixon && rsdNow >= 10.0 && (
                  g.dixon_candidate_id
                    ? g.replicates.some(r => String(r.id) === String(g.dixon_candidate_id) && r.qc !== "fail")
                    : passCnt > 0
                );
                g.raw_dixon = Boolean(dixonStillPassing);
                if (passCnt === 0) {
                  g.raw_dixon = false;
                  g.active_flagged = false;
                  g.flagged_active = false;
                } else if (!g.below_cutoff) {
                  g.active_flagged = Boolean(g.raw_dixon || g.raw_rsd20 || g.raw_sd3x);
                  g.flagged_active = g.active_flagged;
                }
              }
              if (g.active_flagged || g.flagged_active) {
                tabFlaggedActive += 1;
                totalFlaggedActive += 1;
              }
            });
            if (anyTabOverlaid) {
              tabObj.flagged_active = tabFlaggedActive;
              tabObj.flagged_active_groups = tabFlaggedActive;
              tabObj.flagged_replicate_groups = tabFlaggedActive;
            }
          });
          if (anyResourceOverlaid && ins && ins.outlier_screening) {
            ins.outlier_screening.flagged_active = totalFlaggedActive;
            ins.outlier_screening.flagged_active_groups = totalFlaggedActive;
            ins.outlier_screening.flagged_replicate_groups = totalFlaggedActive;
            if (ins.outlier_screening.summary && typeof ins.outlier_screening.summary === "object") {
              ins.outlier_screening.summary.flagged_active = totalFlaggedActive;
              ins.outlier_screening.summary.flagged_active_groups = totalFlaggedActive;
              ins.outlier_screening.summary.flagged_replicate_groups = totalFlaggedActive;
            }
          }
        });
      }

      const badgeEl = document.getElementById("live-qc-overlay-badge");
      if (badgeEl) {
        if (recordQcOverlay.size > 0) {
          badgeEl.classList.remove("hidden");
          badgeEl.textContent = `⚡ Stage 1 Live Overlay: ${recordQcOverlay.size} rec(s) (${failCount} fail)`;
        } else {
          badgeEl.classList.add("hidden");
        }
      }

      if (typeof render === "function") {
        try { render(); } catch (_e) {}
      }
      return { overlaidCount, failCount, totalDecisions: recordQcOverlay.size };
    }
    window.applyLiveQcDecisionsOverlay = applyLiveQcDecisionsOverlay;

    async function refreshLiveQcOverlay(showFeedback) {
      const isSliceMode = typeof BUNDLE !== "undefined" && BUNDLE && Boolean(BUNDLE.collaborator_slice_mode);
      const isFileProtocol = typeof window !== "undefined" && window.location && window.location.protocol === "file:";
      if (isSliceMode) {
        ["btn-refresh-qc-state", "btn-tray-to-workbench", "btn-finding-export-workbench", "nav-page-workbench"].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.classList.add("hidden");
        });
        return { ok: false, skipped: "collaborator_slice_mode" };
      }
      if (isFileProtocol) {
        try {
          const localDecisions = BioCirvQcClient.getLocalDecisions();
          if (localDecisions && localDecisions.length) {
            applyLiveQcDecisionsOverlay(localDecisions);
          }
        } catch (_e) {}
        return { ok: false, skipped: "file_protocol" };
      }

      const refreshBtn = document.getElementById("btn-refresh-qc-state");
      if (refreshBtn && showFeedback) {
        refreshBtn.textContent = "↻ Syncing QC...";
      }

      const id = BioCirvQcClient.getAnalystIdentity();
      const candidateUrls = ["/v1/qc/decisions?limit=500"];
      if (id.apiBase) {
        candidateUrls.push(`${id.apiBase}/v1/qc/decisions?limit=500`);
      }

      for (const url of candidateUrls) {
        try {
          const resp = await fetch(url, {
            method: "GET",
            headers: BioCirvQcClient.getHeaders(),
            credentials: "include"
          });
          if (resp.ok) {
            const data = await resp.json();
            const apiDecisions = Array.isArray(data.decisions) ? data.decisions : [];
            apiDecisions.forEach(d => BioCirvQcClient.upsertLocalDecision(d));
            const merged = BioCirvQcClient.getLocalDecisions();
            const stats = applyLiveQcDecisionsOverlay(merged.length ? merged : apiDecisions);
            if (refreshBtn) {
              refreshBtn.textContent = showFeedback ? `✓ QC Synced (${stats.totalDecisions})` : "↻ Refresh QC State";
              if (showFeedback) {
                setTimeout(() => { refreshBtn.textContent = "↻ Refresh QC State"; }, 2000);
              }
            }
            return { ok: true, source: "api", ...stats };
          }
        } catch (_e) {}
      }

      try {
        const localDecisions = BioCirvQcClient.getLocalDecisions();
        const stats = applyLiveQcDecisionsOverlay(localDecisions);
        if (refreshBtn) refreshBtn.textContent = "↻ Refresh QC State";
        return { ok: true, source: "local", ...stats };
      } catch (_e) {
        if (refreshBtn) refreshBtn.textContent = "↻ Refresh QC State";
        return { ok: false, source: "none" };
      }
    }
    window.refreshLiveQcOverlay = refreshLiveQcOverlay;

    try {
      if (typeof BroadcastChannel !== "undefined") {
        const qcDecisionChannel = new BroadcastChannel("biocirv_qc_decisions");
        qcDecisionChannel.onmessage = (evt) => {
          if (evt && evt.data && evt.data.type === "qc_decision_saved") {
            window.refreshLiveQcOverlay(false);
          }
        };
        if (typeof qcDecisionChannel.unref === "function") {
          qcDecisionChannel.unref();
        }
      }
    } catch (_e) {}

    function initAnalystSignInBar() {
      const bugBtn = document.getElementById("btn-open-bug-modal");
      const signinModal = document.getElementById("modal-analyst-signin");
      if (bugBtn && bugBtn.parentElement && !document.getElementById("btn-open-signin-modal")) {
        const signInBtn = document.createElement("button");
        signInBtn.id = "btn-open-signin-modal";
        signInBtn.className = "px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)] transition-colors";
        signInBtn.title = "Analyst Identity & Google Sign-In for QC Review Queue";
        bugBtn.parentElement.insertBefore(signInBtn, bugBtn.nextSibling);
      }

      function renderAnalystBadge() {
        const btn = document.getElementById("btn-open-signin-modal");
        if (!btn) return;
        const id = BioCirvQcClient.getAnalystIdentity();
        const confirmed = BioCirvQcClient.hasConfirmedIdentity();
        btn.textContent = confirmed ? `🔐 ${id.email}` : `🔐 Sign In (${id.email})`;
      }
      renderAnalystBadge();
      window.addEventListener("biocirv:analyst-changed", renderAnalystBadge);

      const openSigninBtn = document.getElementById("btn-open-signin-modal");
      if (openSigninBtn && signinModal) {
        openSigninBtn.addEventListener("click", async () => {
          const id = BioCirvQcClient.getAnalystIdentity();
          const emailInput = document.getElementById("signin-analyst-email");
          const nameInput = document.getElementById("signin-analyst-name");
          const apiInput = document.getElementById("signin-api-base");
          const statusEl = document.getElementById("signin-sync-status");
          if (emailInput) emailInput.value = id.email;
          if (nameInput) nameInput.value = id.name;
          if (apiInput) apiInput.value = id.apiBase;
          if (statusEl && !BioCirvQcClient._pendingSignInCallback) {
            statusEl.textContent = "Checking connection to /v1/qc/auth-config...";
          }
          signinModal.classList.remove("hidden");

          try {
            const resp = await fetch(`${id.apiBase}/v1/qc/auth-config`, { headers: BioCirvQcClient.getHeaders() });
            if (resp.ok) {
              const cfg = await resp.json();
              if (statusEl && !BioCirvQcClient._pendingSignInCallback) {
                statusEl.textContent = `🟢 Live API connected (${id.apiBase}) · Signed in as ${cfg.current_analyst?.email || id.email}`;
              }
              return;
            }
          } catch (_e) {}
          if (statusEl && !BioCirvQcClient._pendingSignInCallback) {
            statusEl.textContent = `🟡 Offline / Standalone HTML Mode — decisions & assignments are cached locally in browser storage until connected to ${id.apiBase}.`;
          }
        });
      }

      ["btn-close-signin-modal", "btn-cancel-signin-modal"].forEach(id => {
        const el = document.getElementById(id);
        if (el && signinModal) {
          el.addEventListener("click", () => {
            BioCirvQcClient._pendingSignInCallback = null;
            signinModal.classList.add("hidden");
          });
        }
      });

      const saveSigninBtn = document.getElementById("btn-save-signin-modal");
      if (saveSigninBtn && signinModal) {
        saveSigninBtn.addEventListener("click", () => {
          const emailVal = (document.getElementById("signin-analyst-email") || {}).value || "local.analyst@lbl.gov";
          const nameVal = (document.getElementById("signin-analyst-name") || {}).value || "Local Analyst";
          const apiVal = (document.getElementById("signin-api-base") || {}).value || "http://localhost:8000";
          const saved = BioCirvQcClient.setAnalystIdentity({
            email: emailVal,
            name: nameVal,
            apiBase: apiVal
          });
          signinModal.classList.add("hidden");
          if (window.showQcToast) {
            window.showQcToast(`Signed in as ${saved.email}`, "pass");
          }
          if (typeof BioCirvQcClient._pendingSignInCallback === "function") {
            const cb = BioCirvQcClient._pendingSignInCallback;
            BioCirvQcClient._pendingSignInCallback = null;
            cb(saved);
          }
        });
      }
    }

    function initSubmitFindingModal(activeResourcesList) {
      const findingModal = document.getElementById("modal-submit-finding");
      const sliceBtn = document.getElementById("btn-open-slice-modal");
      const bugBtn = document.getElementById("btn-open-bug-modal");
      const anchorBtn = sliceBtn || bugBtn;

      if (anchorBtn && anchorBtn.parentElement && !document.getElementById("btn-open-finding-modal")) {
        const findingBtn = document.createElement("button");
        findingBtn.id = "btn-open-finding-modal";
        findingBtn.className = "px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)] transition-colors";
        findingBtn.title = "Submit an ad-hoc audit finding or flag a record/group in the QC Review Queue";
        findingBtn.textContent = "📝 + Submit Audit Finding";
        anchorBtn.parentElement.insertBefore(findingBtn, anchorBtn);
      }

      const selectedFindingChips = new Set();
      document.querySelectorAll(".finding-rationale-chip").forEach(chipBtn => {
        chipBtn.addEventListener("click", () => {
          const tag = chipBtn.getAttribute("data-chip");
          if (!tag) return;
          if (selectedFindingChips.has(tag)) {
            selectedFindingChips.delete(tag);
            chipBtn.className = "finding-rationale-chip px-2 py-1 rounded-md text-[11px] font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]";
          } else {
            selectedFindingChips.add(tag);
            chipBtn.className = "finding-rationale-chip px-2 py-1 rounded-md text-[11px] font-semibold bg-[var(--primary)] text-[var(--primary-foreground)] border border-[var(--primary)]";
          }
        });
      });

      let currentFindingContext = {
        choice: "group",
        singleRecordId: "",
        groupRecordIds: [],
        replicates: [],
        resource_name: "",
        prepared_sample: "",
        field_sample: "",
        experiment: "",
        parameter_name: "",
        analysis_type: "",
        unit: ""
      };

      function discoverSiblingReplicates(pf, fallbackRes) {
        const allPool = (typeof ALL_RECORDS !== "undefined" && Array.isArray(ALL_RECORDS))
          ? ALL_RECORDS
          : ((typeof RAW_RECORDS !== "undefined" && Array.isArray(RAW_RECORDS)) ? RAW_RECORDS : []);
        const recById = {};
        allPool.forEach(r => { if (r && r.record_id) recById[String(r.record_id)] = r; });

        const clickedId = String(pf.record_id || "").split("|")[0].trim();
        const seedRec = (clickedId && recById[clickedId]) ? recById[clickedId] : null;

        const resName = pf.resource_name || (seedRec && seedRec.resource_name) || fallbackRes || "";
        const prepSample = pf.prepared_sample || (seedRec && seedRec.prepared_sample) || "";
        const fieldSample = pf.field_sample || (seedRec && seedRec.field_sample) || "";
        const expName = pf.experiment || (seedRec && (seedRec.experiment || seedRec.method)) || "";
        const paramName = pf.parameter_name || pf.parameter || (seedRec && seedRec.parameter) || "";
        const analysisType = pf.analysis_type || (seedRec && seedRec.analysis_type) || "";
        const unit = pf.unit || (seedRec && seedRec.unit) || "";

        let reps = [];
        if (Array.isArray(pf.replicates) && pf.replicates.length > 0) {
          reps = pf.replicates.map((rep, idx) => {
            const rid = String(rep.record_id || rep.id || "").trim();
            const full = rid && recById[rid] ? recById[rid] : {};
            return {
              record_id: rid || `rep-${idx + 1}`,
              replicate: rep.replicate ?? rep.rep ?? full.replicate ?? (idx + 1),
              value: rep.value ?? rep.val ?? full.value ?? null,
              unit: rep.unit || full.unit || unit || "",
              qc_status: rep.qc_status || rep.qc || full.qc_status || "pass"
            };
          });
        } else if (allPool.length > 0 && resName && paramName) {
          const siblings = allPool.filter(r => {
            if (String(r.resource_name || "").toLowerCase() !== String(resName).toLowerCase()) return false;
            if (String(r.parameter || "").toLowerCase() !== String(paramName).toLowerCase()) return false;
            if (prepSample && r.prepared_sample && String(r.prepared_sample) !== String(prepSample)) return false;
            if (expName && (r.experiment || r.method) && String(r.experiment || r.method) !== String(expName)) return false;
            return true;
          });
          reps = siblings.map((r, idx) => ({
            record_id: String(r.record_id),
            replicate: r.replicate ?? (idx + 1),
            value: r.value,
            unit: r.unit || unit || "",
            qc_status: r.qc_status || "pass"
          }));
        }

        const rawGroupIds = pf.group_record_ids || pf.all_group_record_ids || pf.record_ids || "";
        const explicitIds = Array.isArray(rawGroupIds)
          ? rawGroupIds.map(x => String(x).trim()).filter(Boolean)
          : String(rawGroupIds).split("|").map(x => x.trim()).filter(Boolean);

        if (reps.length === 0 && explicitIds.length > 0) {
          reps = explicitIds.map((rid, idx) => {
            const full = recById[rid] || {};
            return {
              record_id: rid,
              replicate: full.replicate ?? (idx + 1),
              value: full.value ?? (rid === clickedId ? pf.value : null),
              unit: full.unit || unit || "",
              qc_status: full.qc_status || "pass"
            };
          });
        }
        if (reps.length === 0 && clickedId) {
          reps = [{
            record_id: clickedId,
            replicate: (seedRec && seedRec.replicate) || 1,
            value: pf.value ?? (seedRec && seedRec.value) ?? null,
            unit: unit,
            qc_status: (seedRec && seedRec.qc_status) || "pass"
          }];
        }

        const groupIds = Array.from(new Set([
          ...reps.map(r => r.record_id).filter(Boolean),
          ...explicitIds
        ]));
        const primarySingleId = clickedId || groupIds[0] || "";

        return {
          singleRecordId: primarySingleId,
          groupRecordIds: groupIds,
          replicates: reps,
          resource_name: resName,
          prepared_sample: prepSample,
          field_sample: fieldSample,
          experiment: expName,
          parameter_name: paramName,
          analysis_type: analysisType,
          unit: unit
        };
      }

      function renderFindingScopePromptUI() {
        const btnGroup = document.getElementById("finding-scope-btn-group");
        const btnSingle = document.getElementById("finding-scope-btn-single");
        const grpBadge = document.getElementById("finding-scope-group-badge");
        const sglBadge = document.getElementById("finding-scope-single-badge");
        const grpSum = document.getElementById("finding-scope-group-summary");
        const sglSum = document.getElementById("finding-scope-single-summary");
        const ctxPill = document.getElementById("finding-scope-context-pill");
        const repWrap = document.getElementById("finding-scope-replicates-wrap");
        const repList = document.getElementById("finding-scope-replicates-list");
        const tgtCount = document.getElementById("finding-scope-target-count");
        const scopeSel = document.getElementById("finding-modal-scope");
        const recInput = document.getElementById("finding-modal-record-id");

        const nGrp = currentFindingContext.groupRecordIds.length;
        const sId = currentFindingContext.singleRecordId || (currentFindingContext.groupRecordIds[0] || "");
        const choice = currentFindingContext.choice;

        const isGroupActive = choice === "group";
        const isSingleActive = choice === "single";

        if (btnGroup) {
          btnGroup.className = isGroupActive
            ? "text-left p-2.5 rounded-lg border-2 border-[var(--primary)] bg-[var(--primary)]/10 shadow-sm transition-all"
            : "text-left p-2.5 rounded-lg border border-[var(--border)] bg-[var(--card)] opacity-80 hover:opacity-100 hover:border-[var(--primary)] transition-all";
        }
        if (btnSingle) {
          btnSingle.className = isSingleActive
            ? "text-left p-2.5 rounded-lg border-2 border-[var(--primary)] bg-[var(--primary)]/10 shadow-sm transition-all"
            : "text-left p-2.5 rounded-lg border border-[var(--border)] bg-[var(--card)] opacity-80 hover:opacity-100 hover:border-[var(--primary)] transition-all";
        }
        if (grpBadge) {
          grpBadge.textContent = nGrp > 0 ? `All ${nGrp} Replicate${nGrp === 1 ? '' : 's'}` : "All Replicates";
          grpBadge.className = isGroupActive
            ? "px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-[var(--primary)] text-[var(--primary-foreground)]"
            : "px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)]";
        }
        if (sglBadge) {
          sglBadge.textContent = sId ? `1 Pt (${sId.slice(0, 14)})` : "1 Record";
          sglBadge.className = isSingleActive
            ? "px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-[var(--primary)] text-[var(--primary-foreground)]"
            : "px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)]";
        }
        if (grpSum) {
          const sampleLabel = currentFindingContext.prepared_sample || currentFindingContext.field_sample || "current sample";
          const expLabel = currentFindingContext.experiment ? ` · ${currentFindingContext.experiment}` : "";
          grpSum.textContent = nGrp > 0
            ? `Flags all ${nGrp} replicates in ${sampleLabel}${expLabel}`
            : "Flags all sibling replicates for this sample, experiment & parameter.";
        }
        if (sglSum) {
          const matchedRep = currentFindingContext.replicates.find(r => r.record_id === sId);
          const valStr = matchedRep && matchedRep.value !== null && matchedRep.value !== undefined
            ? ` (val=${Number(matchedRep.value).toLocaleString(undefined, { maximumFractionDigits: 3 })}${matchedRep.unit ? ' ' + matchedRep.unit : ''})`
            : "";
          sglSum.textContent = sId
            ? `Flags only record ${sId}${valStr}`
            : "Flags only the selected observation record_id.";
        }
        if (ctxPill) {
          const parts = [
            currentFindingContext.prepared_sample || currentFindingContext.field_sample,
            currentFindingContext.experiment,
            currentFindingContext.parameter_name
          ].filter(Boolean);
          ctxPill.textContent = parts.length ? parts.join(" · ") : "Choose Entire Group vs Single Point";
        }

        if (scopeSel && scopeSel.value !== choice) {
          scopeSel.value = choice;
        }
        if (recInput) {
          if (choice === "group") {
            recInput.value = currentFindingContext.groupRecordIds.join("|");
          } else if (choice === "single") {
            recInput.value = sId;
          }
        }
        if (tgtCount) {
          tgtCount.textContent = choice === "group"
            ? `Targeting all ${nGrp} replicate(s)`
            : (sId ? `Targeting 1 replicate (${sId})` : "Ad-hoc resource finding");
        }

        if (repWrap && repList) {
          if (currentFindingContext.replicates.length > 0) {
            repWrap.classList.remove("hidden");
            repList.innerHTML = currentFindingContext.replicates.map((rep, idx) => {
              const isSelectedSingle = choice === "single" && rep.record_id === sId;
              const isSelectedGroup = choice === "group";
              const activeCls = (isSelectedSingle || isSelectedGroup)
                ? "bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)] font-bold"
                : "bg-[var(--card)] text-[var(--foreground)] border-[var(--border)] hover:border-[var(--primary)]";
              const valFormatted = (rep.value !== null && rep.value !== undefined && !isNaN(Number(rep.value)))
                ? Number(rep.value).toLocaleString(undefined, { maximumFractionDigits: 3 })
                : "—";
              return `<button type="button" data-rep-id="${rep.record_id}" class="finding-rep-chip px-2 py-0.5 rounded border text-[11px] font-mono transition ${activeCls}" title="Click to focus ${rep.record_id} (Single Point)">Rep ${rep.replicate ?? (idx + 1)}: ${valFormatted}${rep.unit ? ' ' + rep.unit : ''} (${rep.record_id})</button>`;
            }).join("");
            repList.querySelectorAll(".finding-rep-chip").forEach(btn => {
              btn.addEventListener("click", () => {
                const rid = btn.getAttribute("data-rep-id");
                if (rid) {
                  currentFindingContext.singleRecordId = rid;
                  currentFindingContext.choice = "single";
                  renderFindingScopePromptUI();
                }
              });
            });
          } else {
            repWrap.classList.add("hidden");
            repList.innerHTML = "";
          }
        }
      }

      const btnScopeGroup = document.getElementById("finding-scope-btn-group");
      const btnScopeSingle = document.getElementById("finding-scope-btn-single");
      const scopeSelectEl = document.getElementById("finding-modal-scope");
      if (btnScopeGroup) {
        btnScopeGroup.addEventListener("click", () => {
          currentFindingContext.choice = "group";
          renderFindingScopePromptUI();
        });
      }
      if (btnScopeSingle) {
        btnScopeSingle.addEventListener("click", () => {
          currentFindingContext.choice = "single";
          renderFindingScopePromptUI();
        });
      }
      if (scopeSelectEl) {
        scopeSelectEl.addEventListener("change", () => {
          currentFindingContext.choice = scopeSelectEl.value || "group";
          renderFindingScopePromptUI();
        });
      }

      function openSubmitFindingModal(prefill) {
        if (!findingModal) return;
        const pf = prefill || {};
        const defaultRes = pf.resource_name
          || (typeof state !== "undefined" && (state.resource || state.primaryResource))
          || (typeof checkedSet !== "undefined" && checkedSet.resources && checkedSet.resources.size ? Array.from(checkedSet.resources)[0] : null)
          || (activeResourcesList && activeResourcesList[0])
          || "resource";

        const discovered = discoverSiblingReplicates(pf, defaultRes);
        const rawScope = String(pf.scope || pf.triage_scope || "").toLowerCase();
        let initialChoice = "group";
        if (rawScope === "single" || rawScope === "single_record" || pf.prefer_single === true) {
          initialChoice = "single";
        } else {
          initialChoice = "group";
        }

        currentFindingContext = {
          ...discovered,
          choice: initialChoice
        };

        const resSel = document.getElementById("finding-modal-resource");
        if (resSel) {
          const resOptions = Array.from(new Set([...(activeResourcesList || []), discovered.resource_name].filter(Boolean)));
          resSel.innerHTML = resOptions.map(r => `<option value="${r}">${String(r).toUpperCase()}</option>`).join("");
          resSel.value = discovered.resource_name || defaultRes;
        }
        const domSel = document.getElementById("finding-modal-domain");
        if (domSel) {
          const normDom = normalizeDomainKey(
            discovered.analysis_type
            || (typeof state !== "undefined" && (state.domain || state.tab))
            || (typeof currentDomain !== "undefined" ? currentDomain : "proximate")
          );
          if (Array.from(domSel.options).some(o => o.value === normDom)) {
            domSel.value = normDom;
          }
        }
        const paramInput = document.getElementById("finding-modal-parameter");
        if (paramInput) paramInput.value = discovered.parameter_name || pf.parameter_name || pf.parameter || "";
        const qcSel = document.getElementById("finding-modal-qc-status");
        if (qcSel) qcSel.value = pf.default_qc_status || pf.new_qc_status || "provisional";
        const assignInput = document.getElementById("finding-modal-assigned-email");
        if (assignInput) assignInput.value = pf.assigned_to_email || "";
        const noteInput = document.getElementById("finding-modal-note");
        if (noteInput) noteInput.value = pf.audit_note || pf.note || "";
        const statusEl = document.getElementById("finding-modal-status");
        if (statusEl) statusEl.classList.add("hidden");

        renderFindingScopePromptUI();
        findingModal.classList.remove("hidden");
      }
      window.openSubmitFindingModal = openSubmitFindingModal;

      const openFindingBtn = document.getElementById("btn-open-finding-modal");
      if (openFindingBtn) {
        openFindingBtn.addEventListener("click", () => openSubmitFindingModal({}));
      }

      const openGitHubFromFindingBtn = document.getElementById("btn-finding-open-github");
      if (openGitHubFromFindingBtn) {
        openGitHubFromFindingBtn.addEventListener("click", () => {
          const resVal = (document.getElementById("finding-modal-resource") || {}).value || currentFindingContext.resource_name || "resource";
          const scopeVal = (document.getElementById("finding-modal-scope") || {}).value || currentFindingContext.choice || "group";
          const domVal = (document.getElementById("finding-modal-domain") || {}).value || "proximate";
          const paramVal = ((document.getElementById("finding-modal-parameter") || {}).value || "").trim() || "Observation";
          const recVal = ((document.getElementById("finding-modal-record-id") || {}).value || "").trim() || "(unspecified)";
          const qcVal = (document.getElementById("finding-modal-qc-status") || {}).value || "provisional";
          const noteVal = ((document.getElementById("finding-modal-note") || {}).value || "").trim();
          const scopeLabel = scopeVal === "group"
            ? `Entire Replicate Group (${currentFindingContext.groupRecordIds.length || 1} replicates)`
            : (scopeVal === "single" ? `Single Data Point (${currentFindingContext.singleRecordId || recVal})` : "Resource-Level Finding");
          const url = buildGitHubBugIssueUrl({
            category: `Data / QC Audit Finding — ${scopeLabel}`,
            resource: resVal,
            domainTab: domVal,
            qcFilter: qcVal,
            title: `[QC Audit] ${resVal} · ${paramVal} (${scopeVal === 'group' ? 'Replicate Group' : 'Single Point'})`,
            description: [
              "**Audit Scope:** " + scopeLabel,
              "**Resource:** `" + resVal + "`",
              "**Sample / Experiment:** `" + (currentFindingContext.prepared_sample || currentFindingContext.field_sample || "—") + "` / `" + (currentFindingContext.experiment || "—") + "`",
              "**Parameter:** `" + paramVal + "`",
              "**Target Record ID(s):** `" + recVal + "`",
              "**Recommended QC Action:** `" + qcVal + "`",
              "**Rationale Tags:** " + (Array.from(selectedFindingChips).join(", ") || "(none)"),
              "",
              "**Analyst Observation / Note:**",
              noteVal || "_Please review this replicate group / data point against raw lab notebooks._"
            ].join("\\n"),
            expectedBehavior: "Verify bench notebook values and apply QC status `" + qcVal + "` to " + scopeLabel + "."
          });
          window.open(url, "_blank", "noopener");
        });
      }

      const exportFindingWorkbenchBtn = document.getElementById("btn-finding-export-workbench");
      if (exportFindingWorkbenchBtn && findingModal) {
        exportFindingWorkbenchBtn.addEventListener("click", async () => {
          const resVal = (document.getElementById("finding-modal-resource") || {}).value || (activeResourcesList && activeResourcesList[0]) || "resource";
          const scopeVal = (document.getElementById("finding-modal-scope") || {}).value || currentFindingContext.choice || "group";
          const domVal = (document.getElementById("finding-modal-domain") || {}).value || "proximate";
          const paramVal = ((document.getElementById("finding-modal-parameter") || {}).value || "").trim() || "Observation";
          const recVal = ((document.getElementById("finding-modal-record-id") || {}).value || "").trim() || null;
          const qcVal = (document.getElementById("finding-modal-qc-status") || {}).value || "provisional";
          const assignVal = ((document.getElementById("finding-modal-assigned-email") || {}).value || "").trim() || null;
          const noteVal = ((document.getElementById("finding-modal-note") || {}).value || "").trim();

          const rawIdsFromInput = recVal ? recVal.split("|").map(s => s.trim()).filter(Boolean) : [];
          const targetIds = scopeVal === "group"
            ? (currentFindingContext.groupRecordIds.length ? currentFindingContext.groupRecordIds : rawIdsFromInput)
            : (rawIdsFromInput.length ? [rawIdsFromInput[0]] : (currentFindingContext.singleRecordId ? [currentFindingContext.singleRecordId] : []));
          const primaryRecId = scopeVal === "single"
            ? (targetIds[0] || recVal)
            : (currentFindingContext.singleRecordId || targetIds[0] || recVal);

          const res = await BioCirvQcClient.exportTrayToWorkbench({
            selection_scope: scopeVal === "single" ? "single_record" : "replicate_group",
            resource_name: resVal,
            analysis_type: domVal,
            parameter_name: paramVal,
            prepared_sample: currentFindingContext.prepared_sample || "",
            field_sample: currentFindingContext.field_sample || "",
            experiment: currentFindingContext.experiment || "",
            record_id: primaryRecId,
            target_record_ids: targetIds,
            recommended_qc_status: qcVal,
            assigned_to_email: assignVal,
            note: noteVal || Array.from(selectedFindingChips).join("; "),
            open_workbench: window.location.protocol === "http:" || window.location.protocol === "https:"
          });
          const statusEl = document.getElementById("finding-modal-status");
          if (statusEl) {
            const wbUrl = res.workbench_url || "/v1/dashboards/metadata/resource_audit_workbench.html";
            statusEl.className = "p-2.5 rounded-lg text-xs font-mono badge-pass";
            statusEl.innerHTML = `✓ Exported to <a href="${wbUrl}" class="underline font-bold">⚖️ QC Audit Workbench</a> (${scopeVal === "single" ? "Single Point Only" : "Entire Replicate Group"}).`;
            statusEl.classList.remove("hidden");
          }
          window.refreshLiveQcOverlay(false);
        });
      }

      const refreshQcBtn = document.getElementById("btn-refresh-qc-state");
      if (refreshQcBtn) {
        refreshQcBtn.addEventListener("click", () => {
          window.refreshLiveQcOverlay(true);
        });
      }

      ["btn-close-finding-modal", "btn-cancel-finding-modal"].forEach(id => {
        const el = document.getElementById(id);
        if (el && findingModal) el.addEventListener("click", () => findingModal.classList.add("hidden"));
      });

      const confirmFindingBtn = document.getElementById("btn-confirm-submit-finding");
      if (confirmFindingBtn && findingModal) {
        confirmFindingBtn.addEventListener("click", async () => {
          const resVal = (document.getElementById("finding-modal-resource") || {}).value || (activeResourcesList && activeResourcesList[0]) || "resource";
          const scopeVal = (document.getElementById("finding-modal-scope") || {}).value || "group";
          const domVal = (document.getElementById("finding-modal-domain") || {}).value || "proximate";
          const paramVal = ((document.getElementById("finding-modal-parameter") || {}).value || "").trim() || "Resource-Level Observation";
          const recVal = ((document.getElementById("finding-modal-record-id") || {}).value || "").trim() || null;
          const qcVal = (document.getElementById("finding-modal-qc-status") || {}).value || "provisional";
          const assignVal = ((document.getElementById("finding-modal-assigned-email") || {}).value || "").trim() || null;
          const noteVal = ((document.getElementById("finding-modal-note") || {}).value || "").trim();
          const gsheetSync = Boolean((document.getElementById("finding-modal-gsheet-sync") || {}).checked);

          const rawIdsFromInput = recVal ? recVal.split("|").map(s => s.trim()).filter(Boolean) : [];
          const targetIds = scopeVal === "group"
            ? (currentFindingContext.groupRecordIds.length ? currentFindingContext.groupRecordIds : rawIdsFromInput)
            : (rawIdsFromInput.length ? [rawIdsFromInput[0]] : (currentFindingContext.singleRecordId ? [currentFindingContext.singleRecordId] : []));
          const primaryRecId = scopeVal === "single"
            ? (targetIds[0] || recVal)
            : (currentFindingContext.singleRecordId || targetIds[0] || recVal);

          const result = await BioCirvQcClient.submitFinding({
            scope: scopeVal === "group" ? "replicate_group" : (scopeVal === "single" ? "single_record" : "finding"),
            triage_scope: scopeVal,
            resource_name: resVal,
            analysis_type: domVal,
            parameter_name: paramVal,
            prepared_sample: currentFindingContext.prepared_sample || "",
            field_sample: currentFindingContext.field_sample || "",
            experiment: currentFindingContext.experiment || "",
            record_id: primaryRecId,
            target_record_ids: targetIds,
            previous_qc_status: "pass",
            new_qc_status: qcVal,
            rationale_tags: Array.from(selectedFindingChips),
            audit_note: noteVal || `Audit finding logged for ${resVal} (${paramVal}, scope=${scopeVal === 'group' ? 'Entire Replicate Group' : 'Single Point'})`,
            assigned_to_email: assignVal,
            gsheet_writeback_requested: gsheetSync
          });
          BioCirvQcClient.broadcastQcUpdate(result.decision);
          window.refreshLiveQcOverlay(false);

          if (typeof upsertDecisionEntry === "function") {
            const repGroupKey = normalizeReplicateGroupKey(
              {
                ...currentFindingContext,
                resource_name: resVal,
                analysis_type: currentFindingContext.analysis_type || domVal,
                parameter: paramVal
              },
              resVal
            );
            const localKey = scopeVal === "single" && primaryRecId
              ? `rec::${primaryRecId}`
              : `grp::${repGroupKey}`;
            upsertDecisionEntry(
              localKey,
              {
                decision: qcVal === "pass" ? "keep" : (qcVal === "provisional" || qcVal === "in_review" ? "accept_with_note" : (qcVal === "re_assay" ? "re_assay" : "exclude_qc_fail")),
                api_decision_id: (result.decision && result.decision.id) ? result.decision.id : undefined,
                triage_scope: scopeVal === "single" ? "single" : "group",
                assigned_to_email: assignVal || "",
                note: noteVal || Array.from(selectedFindingChips).join("; ")
              },
              {
                scope: scopeVal === "single" ? "single_record" : "replicate_group",
                replicate_group_key: repGroupKey,
                resource_name: resVal,
                analysis_type: currentFindingContext.analysis_type || domVal,
                prepared_sample: currentFindingContext.prepared_sample || "",
                field_sample: currentFindingContext.field_sample || "",
                prep_method: currentFindingContext.prep_method || "",
                experiment: currentFindingContext.experiment || "",
                parameter: paramVal,
                record_id: primaryRecId || "",
                record_ids: targetIds.join("|")
              }
            );
            if (typeof render === "function") render();
          }

          const statusEl = document.getElementById("finding-modal-status");
          if (statusEl) {
            const assignMsg = assignVal ? ` · Assigned to ${assignVal}` : "";
            const scopeMsg = scopeVal === "group" ? `Entire Replicate Group (${targetIds.length || 1} recs)` : `Single Point (${primaryRecId || '1 rec'})`;
            statusEl.className = "p-2.5 rounded-lg text-xs font-mono badge-pass";
            statusEl.innerHTML = `✓ Queued <strong>${scopeMsg}</strong> (${result.source === "api" ? "API + Seed CSV" : "Browser Local Queue"})${assignMsg}. View &amp; triage in <a href="resource_qc_outlier_dashboard.html?subtab=review_queue" class="underline font-bold">Page 2 Review Queue</a> or <a href="/v1/dashboards/metadata/resource_audit_workbench.html" class="underline font-bold">QC Audit Workbench</a>.`;
            statusEl.classList.remove("hidden");
          }
          setTimeout(() => {
            if (findingModal) findingModal.classList.add("hidden");
          }, 1200);
        });
      }
    }
"""


def build_analysis_dashboard_html(
    bundle: dict[str, Any],
    default_resource: str = "almond hulls",
    qc_page_filename: str = "resource_qc_outlier_dashboard.html",
) -> str:
    """Compile Page 1: Clean Resource Characterization & Executive AI Brief Dashboard."""
    data_json = json.dumps(bundle, separators=(",", ":")).replace("</", "<\\/")
    single_res = bundle.get("single_resource")
    slice_res_list = bundle.get("slice_resources") or []
    dict_res_list = (bundle.get("dicts") or {}).get("resource_name") or []
    if single_res:
        default_resource = single_res.lower()
        title_prefix = single_res.title()
    elif slice_res_list:
        default_resource = str(slice_res_list[0]).lower()
        title_prefix = (
            str(slice_res_list[0]).title()
            if len(slice_res_list) == 1
            else f"{len(slice_res_list)}-Resource Slice"
        )
    elif dict_res_list and default_resource.lower() not in [str(x).lower() for x in dict_res_list]:
        default_resource = str(dict_res_list[0]).lower()
        title_prefix = "All-Resources"
    else:
        title_prefix = "All-Resources"

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
          <span>2. Statistical Snapshot</span>
          <span id="nav-qc-badge" class="px-1.5 py-0.2 rounded-full text-[11px] font-mono"></span>
        </a>
        <a id="nav-page-explorer" href="resource_explorer_dashboard.html" class="px-3 py-1.5 rounded-lg font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)] transition">
          3. Multi-Resource Side-by-Side Explorer
        </a>
        <a id="nav-page-drift" href="../audit/db_environment_drift_dashboard.html" class="px-3 py-1.5 rounded-lg font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)] transition">
          4. DB Environment Drift
        </a>
        <a id="nav-page-workbench" href="/v1/dashboards/metadata/resource_audit_workbench.html" class="px-3 py-1.5 rounded-lg font-semibold badge-warn hover:opacity-90 transition">
          ⚖️ QC Audit Workbench
        </a>
      </div>
    </nav>

    <!-- Page 1 Reorganized Top Workspace: 3 Logical Cards -->
    <header class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 sm:p-5 shadow-sm space-y-4">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 items-stretch" id="page1-top-workspace-cards">
        <!-- Card 1: Resource Metadata & Lab Notes -->
        <div id="top-card-resource-metadata" class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-3.5 space-y-2.5 flex flex-col justify-between">
          <div class="space-y-2">
            <div class="text-[11px] font-bold uppercase tracking-wider text-[var(--primary)]">Resource Metadata &amp; Lab Notes</div>
            <div class="flex flex-wrap items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-[var(--primary)] inline-block"></span>
              <h1 id="hdr-title" class="text-base sm:text-lg font-bold text-[var(--foreground)]">BioCirV — Resource Characterization</h1>
              <span id="hdr-code-badge" class="px-2 py-0.5 text-xs font-semibold rounded-full bg-[var(--primary)] text-[var(--primary-foreground)] font-mono"></span>
              <span id="hdr-class-badge" class="px-2 py-0.5 text-xs font-medium rounded-full bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]"></span>
              <span id="hdr-portal-badge" class="px-2 py-0.5 text-xs font-semibold rounded-full"></span>
              <span id="live-qc-overlay-badge" class="hidden px-2 py-0.5 text-xs font-semibold rounded-full badge-warn font-mono"></span>
            </div>
            <div id="resource-switcher-wrap" class="flex items-center gap-1.5 pt-1">
              <label for="flt-resource" class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Resource:</label>
              <button id="btn-prev-res" title="Previous Resource" class="px-2 py-1 rounded-lg text-xs font-bold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-80">&larr;</button>
              <select id="flt-resource" class="rounded-lg px-2.5 py-1.5 text-xs sm:text-sm font-bold border min-w-[200px] flex-1"></select>
              <button id="btn-next-res" title="Next Resource" class="px-2 py-1 rounded-lg text-xs font-bold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-80">&rarr;</button>
            </div>
            <p id="hdr-desc" class="text-xs text-[var(--muted-foreground)]"></p>
          </div>
          <div class="pt-2 border-t border-[var(--border)] flex flex-wrap items-center justify-between gap-2 text-xs">
            <span id="active-slice-badge" class="font-mono text-[var(--muted-foreground)]"></span>
            <span id="hdr-lab-notes-summary" class="font-mono text-[var(--foreground)]"></span>
          </div>
        </div>

        <!-- Card 2: Flag Counts & Statistical Snapshot -->
        <div id="top-card-flag-counts" class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-3.5 space-y-2.5 flex flex-col justify-between">
          <div class="space-y-1">
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs font-bold uppercase tracking-wider text-[var(--primary)]">Flag Counts</span>
              <span class="text-[11px] font-mono text-[var(--muted-foreground)]">Scoped to selected resource &amp; analysis type</span>
            </div>
            <div class="grid grid-cols-3 gap-2 pt-1.5 text-xs font-mono">
              <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2">
                <div class="text-[10px] font-sans text-[var(--muted-foreground)]">Active Flags</div>
                <div id="p1-flag-count-val" class="text-sm font-bold text-[var(--foreground)] mt-0.5">0</div>
              </div>
              <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2">
                <div class="text-[10px] font-sans text-[var(--muted-foreground)]">Within-Rep RSD</div>
                <div id="p1-within-rsd-val" class="text-xs font-bold text-[var(--foreground)] mt-0.5 truncate">—</div>
              </div>
              <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-2">
                <div class="text-[10px] font-sans text-[var(--muted-foreground)]">Between-Sample RSD</div>
                <div id="p1-between-rsd-val" class="text-xs font-bold text-[var(--foreground)] mt-0.5 truncate">—</div>
              </div>
            </div>
          </div>
          <div class="pt-2 border-t border-[var(--border)] flex items-center justify-between gap-2">
            <a id="hdr-qc-deep-link" href="__QC_PAGE_FILENAME__" class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition flex items-center gap-1.5 w-full justify-center"></a>
          </div>
        </div>

        <!-- Card 3: Unified Controls & Export -->
        <div id="top-card-controls-export" class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-3.5 space-y-2.5 flex flex-col justify-between">
          <div class="space-y-2">
            <div class="text-[11px] font-bold uppercase tracking-wider text-[var(--primary)]">Unified Controls &amp; Export</div>
            <div class="flex flex-col gap-1.5 text-xs">
              <label class="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[var(--card)] border border-[var(--border)] cursor-pointer">
                <input id="chk-p1-suppress-trace" type="checkbox" checked class="rounded" />
                <span class="font-medium text-[var(--foreground)]">Suppress Low-Abundance Trace</span>
              </label>
              <label class="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[var(--card)] border border-[var(--border)] cursor-pointer">
                <input id="chk-p1-blind-mode" type="checkbox" class="rounded" />
                <span class="font-medium text-[var(--foreground)]">Blind Analyst Mode</span>
              </label>
            </div>
          </div>
          <div class="pt-2 border-t border-[var(--border)] flex flex-wrap items-center justify-between gap-1.5">
            <div class="flex flex-wrap items-center gap-1.5">
              <button id="btn-open-slice-modal" title="📤 Export Slice (.HTML)" class="px-3 py-1.5 rounded-lg text-xs font-bold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 transition">
                📤 Export
              </button>
              <button id="btn-download-csv" class="hidden px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90 transition">
                ⬇ Export CSV
              </button>
              <button id="btn-refresh-qc-state" type="button" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--primary)]/50 hover:border-[var(--primary)] transition" title="Pull latest Stage 1 QC decisions from /v1/qc/decisions">
                ↻ Refresh QC State
              </button>
            </div>
            <div class="flex flex-wrap items-center gap-1.5">
              <button id="btn-toggle-ai" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90 transition">
                ✨ Hide AI Brief
              </button>
              <button id="btn-theme-toggle" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90 transition">
                ☀️ Light Mode
              </button>
              <button id="btn-open-bug-modal" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-amber-400 transition">
                🐛 Report a Bug
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Clean Single-Row Filter Bar -->
      <div class="pt-3 border-t border-[var(--border)] flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-2.5">
          <div class="flex items-center gap-1.5">
            <label for="flt-prepared-sample" class="text-xs font-semibold text-[var(--muted-foreground)]">Sample:</label>
            <select id="flt-prepared-sample" class="rounded-lg px-2.5 py-1.5 text-xs font-medium border min-w-[180px]"></select>
          </div>

          <div class="flex items-center gap-1.5">
            <span class="text-xs font-semibold text-[var(--muted-foreground)]">QC:</span>
            <div class="inline-flex rounded-lg border border-[var(--border)] bg-[var(--background)] p-0.5" id="flt-qc-group">
              <button data-qc="pass" class="qc-btn px-2.5 py-1 rounded-md text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)]">Pass</button>
              <button data-qc="all" class="qc-btn px-2.5 py-1 rounded-md text-xs font-medium text-[var(--muted-foreground)]">All</button>
              <button data-qc="fail" class="qc-btn px-2.5 py-1 rounded-md text-xs font-medium text-[var(--muted-foreground)]">Fail</button>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-1.5 pl-1 border-l border-[var(--border)]">
            <label for="flt-date-type" class="text-xs font-semibold text-[var(--muted-foreground)]">Date:</label>
            <select id="flt-date-type" class="rounded-lg px-2 py-1 text-xs font-medium border">
              <option value="any">Collection or Run Date</option>
              <option value="collected">Collection Date</option>
              <option value="run">Run / Prep Date</option>
            </select>
            <input id="flt-from-date" type="date" min="2020-01-01" placeholder="2024-01-01" title="From Date (YYYY-MM-DD, defaults to 2024-01-01 on focus)" class="rounded-lg px-2 py-1 text-xs font-mono border" />
            <span class="text-xs text-[var(--muted-foreground)]">&ndash;</span>
            <input id="flt-to-date" type="date" min="2020-01-01" title="To Date (YYYY-MM-DD)" class="rounded-lg px-2 py-1 text-xs font-mono border" />
            <button id="flt-date-clear" type="button" title="Clear date filter" class="hidden px-1.5 py-0.5 rounded text-[11px] font-mono bg-[var(--secondary)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] border border-[var(--border)]">&#x2715;</button>
          </div>

          <div class="flex items-center gap-1.5 pl-1 border-l border-[var(--border)]">
            <label for="flt-rep-mode" class="text-xs font-semibold text-[var(--muted-foreground)]" title="Control how individual replicates vs. group means are displayed">Replicate Display:</label>
            <select id="flt-rep-mode" class="rounded-lg px-2 py-1 text-xs font-medium border">
              <option value="replicates">Individual Replicates + Mean</option>
              <option value="mean_sd">Mean ± SD Summary Only</option>
              <option value="field_exp_mean_sd">By Field Sample × Experiment (Mean ± SD)</option>
            </select>
          </div>

          <button id="btn-reset-filters" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90">
            Reset
          </button>
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

__SHARED_SLICE_AND_BUG_MODALS_HTML__
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

    const ACTIVE_RESOURCES = Object.keys(RECORDS_BY_RESOURCE).sort(
      (a, b) => RECORDS_BY_RESOURCE[b].length - RECORDS_BY_RESOURCE[a].length
    );

    const urlParams = new URLSearchParams(window.location.search);
    const initialResParam = (urlParams.get("resource") || DEFAULT_RESOURCE).toLowerCase();
    const matchedInitialRes = ACTIVE_RESOURCES.find(r => r.toLowerCase() === initialResParam) || ACTIVE_RESOURCES[0];
    const rawTabParam = urlParams.get("tab") || "overview";
    const validTabs = ["overview", "proximate", "compositional", "elemental", "conversion"];
    const initialTabParam = validTabs.includes(rawTabParam) ? rawTabParam : (rawTabParam === "pretreatment" || rawTabParam === "fermentation" ? "conversion" : "overview");
    const rawQcParam = (urlParams.get("qc") || "pass").toLowerCase();
    const initialQcParam = ["all", "pass", "fail"].includes(rawQcParam) ? rawQcParam : "pass";

    const state = {
      resource: matchedInitialRes,
      tab: initialTabParam,
      prepared_sample: "all",
      field_sample: "all",
      qc_status: initialQcParam,
      date_type: BUNDLE.slice_date_type || (BUNDLE.slice_filters && BUNDLE.slice_filters.date_type) || "any",
      from_date: BUNDLE.slice_from_date || (BUNDLE.slice_filters && BUNDLE.slice_filters.from_date) || "",
      to_date: BUNDLE.slice_to_date || (BUNDLE.slice_filters && BUNDLE.slice_filters.to_date) || "",
      repMode: "replicates",
      suppressTraceFlags: true,
      blindMode: false,
      showAiPanel: true,
      proxGroupMode: "ps_exp",
      elemSourceMode: "all",
      icpScaleMode: "split",
      convSubTab: "all"
    };

    function renderGroupFlagBadges(g) {
      if (!g) return "";
      const badges = [];
      const allowFlags = !g.below_cutoff || !state.suppressTraceFlags;
      if (allowFlags) {
        if (g.raw_dixon) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold badge-fail" title="Dixon Q=${fmtNum(g.dixon_q, 3)}">⚑ Dixon Outlier</span>`);
        if (g.raw_rsd20) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold badge-warn" title="Within-group RSD ${fmtNum(g.rsd_within_pct, 1)}% > 20%">⚑ RSD &gt; 20%</span>`);
        else if (g.raw_rsd10) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono badge-info" title="Within-group RSD ${fmtNum(g.rsd_within_pct, 1)}%">⚑ RSD 10–20%</span>`);
        if (g.raw_sd3x) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold badge-warn" title=">3×SD_pooled candidate">⚑ &gt;3&times;SD_pooled</span>`);
        if (g.has_identical_replicates) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono badge-info" title="Informational: all replicates in group are identical (within_sd = 0) — Identical Replicates (SD=0)">⚑ Identical Replicates</span>`);
        if (g.qc_mixed) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold badge-fail" title="Mixed QC (${g.qc_pass_count}P/${g.qc_fail_count}F)">⚑ Mixed QC</span>`);
      }
      if (g.below_cutoff) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono badge-info" title="Low-abundance trace parameter (${g.cutoff_label})">Trace (${g.cutoff_label})</span>`);
      return badges.join(" ");
    }

    function findOutlierGroupForRecords(groupRecs, paramName) {
      if (!groupRecs || !groupRecs.length) return null;
      const ins = typeof getResourceInsights === "function" ? getResourceInsights() : null;
      const out = ins && ins.outlier_screening;
      if (!out) return null;
      const allGroups = [];
      if (Array.isArray(out.groups)) allGroups.push(...out.groups);
      if (Array.isArray(out.replicate_groups)) allGroups.push(...out.replicate_groups);
      if (out.by_tab && typeof out.by_tab === "object") {
        Object.values(out.by_tab).forEach(t => {
          if (t && Array.isArray(t.replicate_groups)) allGroups.push(...t.replicate_groups);
          else if (t && Array.isArray(t.groups)) allGroups.push(...t.groups);
        });
      }
      if (!allGroups.length) return null;
      const hasAnyFlag = g => Boolean(
        g && (g.raw_dixon || g.raw_rsd20 || g.raw_rsd10 || g.raw_sd3x || g.has_identical_replicates || g.qc_mixed || g.below_cutoff)
      );
      const recIdSet = new Set(groupRecs.map(r => String(r.record_id || "").trim()).filter(Boolean));
      if (recIdSet.size > 0) {
        const idMatches = allGroups.filter(g => {
          const reps = Array.isArray(g.replicates) ? g.replicates : [];
          return reps.some(rep => recIdSet.has(String(rep.id || rep.record_id || "").trim()));
        });
        if (idMatches.length > 0) {
          return idMatches.find(hasAnyFlag) || idMatches[0];
        }
      }
      const first = groupRecs[0];
      const rawParam = (paramName && !String(paramName).startsWith("⚑") && !String(paramName).includes(":"))
        ? paramName
        : (first.parameter || "");
      const targetParam = String(rawParam).trim().toLowerCase();
      const targetPs = String(first.prepared_sample || "").trim().toLowerCase();
      const targetAt = String(first.analysis_type || "").trim().toLowerCase();
      const propMatches = allGroups.filter(g =>
        String(g.parameter || "").trim().toLowerCase() === targetParam &&
        (!targetPs || String(g.prepared_sample || "").trim().toLowerCase() === targetPs) &&
        (!targetAt || String(g.analysis_type || "").trim().toLowerCase() === targetAt)
      );
      return propMatches.find(hasAnyFlag) || propMatches[0] || null;
    }

    window.auditPage1PointOrGroup = function(encodedPayload) {
      let prefill = {};
      try { prefill = JSON.parse(decodeURIComponent(encodedPayload)); } catch (_) {}
      if (typeof window.openSubmitFindingModal === "function") {
        window.openSubmitFindingModal(prefill);
      }
    };

    function buildAuditChipHtml(rec, groupRecs, labelText, extraClasses) {
      const siblings = (groupRecs || [rec]).map(x => ({
        id: String(x.record_id),
        rep: x.replicate,
        val: x.value,
        qc: x.qc_status,
        prepared_sample: x.prepared_sample,
        experiment: x.experiment
      }));
      const payload = encodeURIComponent(JSON.stringify({
        scope: "single_record",
        resource_name: rec.resource_name || state.resource,
        analysis_type: rec.analysis_type || "",
        parameter: rec.parameter || "",
        prepared_sample: rec.prepared_sample || "",
        field_sample: rec.field_sample || "",
        experiment: rec.experiment || "",
        record_id: String(rec.record_id || ""),
        value: rec.value,
        unit: rec.unit || "",
        replicates: siblings,
        group_record_ids: siblings.map(s => s.id)
      }));
      const cls = extraClasses || "px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] font-mono text-xs cursor-pointer transition";
      return `<button type="button" onclick="window.auditPage1PointOrGroup('${payload}')" title="Click to flag/audit Record ${rec.record_id} or its entire replicate group (n=${siblings.length})" class="${cls}">${labelText}</button>`;
    }

    function buildAuditGroupBtnHtml(groupRecs, paramName, unitLabel) {
      if (!groupRecs || !groupRecs.length) return "";
      const first = groupRecs[0];
      const siblings = groupRecs.map(x => ({
        id: String(x.record_id),
        rep: x.replicate,
        val: x.value,
        qc: x.qc_status,
        prepared_sample: x.prepared_sample,
        experiment: x.experiment
      }));
      const resolvedParam = (paramName && !String(paramName).startsWith("⚑") && !String(paramName).includes(":"))
        ? paramName
        : (first.parameter || "");
      const payload = encodeURIComponent(JSON.stringify({
        scope: "replicate_group",
        resource_name: first.resource_name || state.resource,
        analysis_type: first.analysis_type || "",
        parameter: resolvedParam,
        prepared_sample: first.prepared_sample || "",
        field_sample: first.field_sample || "",
        experiment: first.experiment || "",
        record_id: String(first.record_id || ""),
        unit: unitLabel || first.unit || "",
        replicates: siblings,
        group_record_ids: siblings.map(s => s.id)
      }));
      const matchedOutlierGroup = findOutlierGroupForRecords(groupRecs, resolvedParam);
      const flagBadgesHtml = matchedOutlierGroup ? renderGroupFlagBadges(matchedOutlierGroup) : "";
      const btnHtml = `<button type="button" onclick="window.auditPage1PointOrGroup('${payload}')" title="Flag/audit this replicate group (n=${siblings.length}) or a single point" class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-[var(--secondary)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] border border-[var(--border)] hover:border-[var(--primary)] transition">⚑ Audit (n=${siblings.length})</button>`;
      return flagBadgesHtml ? `<span class="inline-flex flex-wrap items-center gap-1">${flagBadgesHtml} ${btnHtml}</span>` : btnHtml;
    }

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
      const wrapEl = document.getElementById("resource-switcher-wrap");
      if (wrapEl) {
        if (BUNDLE.single_resource || ACTIVE_RESOURCES.length <= 1) {
          wrapEl.classList.add("hidden");
        } else {
          wrapEl.classList.remove("hidden");
        }
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

    function recordMatchesDateFilter(r, dtType, fromDt, toDt) {
      if (typeof window.recordMatchesDateFilter === "function") {
        return window.recordMatchesDateFilter(r, dtType, fromDt, toDt);
      }
      if (!fromDt && !toDt) return true;
      let f = fromDt || "";
      let t = toDt || "";
      if (f && t && f > t) { const tmp = f; f = t; t = tmp; }
      const cDate = r.collected_date ? String(r.collected_date).slice(0, 10) : "";
      const rDate = r.exp_date ? String(r.exp_date).slice(0, 10) : (r.prep_date ? String(r.prep_date).slice(0, 10) : "");
      const inRange = d => {
        if (!d || d === "Unrecorded") return false;
        if (f && d < f) return false;
        if (t && d > t) return false;
        return true;
      };
      if (dtType === "collected") return inRange(cDate);
      if (dtType === "run") return inRange(rDate);
      return inRange(cDate) || inRange(rDate);
    }

    function getFilteredRecords() {
      const resRecs = getResourceRecords();
      return resRecs.filter(r => {
        if (state.prepared_sample !== "all" && r.prepared_sample !== state.prepared_sample) return false;
        if (state.field_sample !== "all" && r.field_sample !== state.field_sample) return false;
        if (state.qc_status !== "all" && r.qc_status !== state.qc_status) return false;
        if (!recordMatchesDateFilter(r, state.date_type, state.from_date, state.to_date)) return false;
        return true;
      });
    }

    function updateSuiteNavLinks() {
      const encRes = encodeURIComponent(state.resource);
      document.getElementById("nav-page-char").href = `resource_analysis_dashboard.html?resource=${encRes}`;
      document.getElementById("nav-page-qc").href = `${QC_PAGE_FILENAME}?resource=${encRes}`;
      document.getElementById("nav-page-explorer").href = `resource_explorer_dashboard.html?resource=${encRes}`;

      if (BUNDLE.collaborator_slice_mode) {
        const slicePages = BUNDLE.slice_pages || ["char"];
        ["nav-page-pretreatment", "nav-page-drift", "nav-page-monolith", "btn-open-slice-modal", "btn-open-finding-modal"].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.classList.add("hidden");
        });
        const qcNav = document.getElementById("nav-page-qc");
        if (qcNav && !slicePages.includes("qc")) qcNav.classList.add("hidden");
        const expNav = document.getElementById("nav-page-explorer");
        if (expNav && !slicePages.includes("explorer")) expNav.classList.add("hidden");
        const dlCsvBtn = document.getElementById("btn-download-csv");
        if (dlCsvBtn) {
          dlCsvBtn.textContent = "⬇ Download Sliced Data (.csv)";
          dlCsvBtn.className = "px-3.5 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 text-white hover:opacity-90 transition";
        }
        const hdrLink = document.getElementById("hdr-qc-deep-link");
        if (hdrLink) {
          const qcScope = (BUNDLE.slice_qc_statuses || ["pass"]).join(", ").toUpperCase();
          const resCount = ACTIVE_RESOURCES.length;
          hdrLink.removeAttribute("href");
          hdrLink.className = "px-3 py-1.5 rounded-lg text-xs font-semibold badge-info flex items-center gap-1.5";
          hdrLink.innerHTML = `<span>🔒 Collaborator Slice (${resCount} resource${resCount === 1 ? "" : "s"}) · QC Scope: <strong>${qcScope}</strong></span>`;
        }
        return;
      }

      const ins = getResourceInsights();
      const outSummary = window.getOutlierSummary ? window.getOutlierSummary(ins) : {};
      const activeFlags = state.suppressTraceFlags
        ? (outSummary.flaggedActive || 0)
        : (outSummary.flaggedRaw ?? outSummary.flaggedActive ?? 0);
      const tabOut = (state.tab && state.tab !== "overview" && ins && ins.outlier_screening && ins.outlier_screening.by_tab && ins.outlier_screening.by_tab[state.tab]) || null;
      const scopedActiveFlags = tabOut
        ? (state.suppressTraceFlags ? (tabOut.flagged_active ?? 0) : (tabOut.flagged_raw ?? tabOut.flagged_active ?? 0))
        : activeFlags;
      const notesCnt = (ins && ins.curated_notes && ins.curated_notes.length) || 0;

      const flagValEl = document.getElementById("p1-flag-count-val");
      if (flagValEl) {
        flagValEl.textContent = `${scopedActiveFlags}`;
      }
      const wRsdEl = document.getElementById("p1-within-rsd-val");
      if (wRsdEl) {
        const wMed = tabOut ? tabOut.within_rsd_median : outSummary.withinRsdMedian;
        const wSd = tabOut ? tabOut.within_sd_median : outSummary.withinSdMedian;
        wRsdEl.textContent = wMed !== null && wMed !== undefined
          ? `${fmtNum(wMed, 1)}%${wSd !== null && wSd !== undefined ? ` (±${fmtNum(wSd, 2)})` : ""}`
          : "N/A (n=1)";
      }
      const bRsdEl = document.getElementById("p1-between-rsd-val");
      if (bRsdEl) {
        const bMed = tabOut ? tabOut.between_rsd_median : outSummary.betweenRsdMedian;
        const bSd = tabOut ? tabOut.between_sd_median : outSummary.betweenSdMedian;
        bRsdEl.textContent = bMed !== null && bMed !== undefined
          ? `${fmtNum(bMed, 1)}%${bSd !== null && bSd !== undefined ? ` (±${fmtNum(bSd, 2)})` : ""}`
          : "N/A (n=1 method group)";
      }
      const notesSumEl = document.getElementById("hdr-lab-notes-summary");
      if (notesSumEl) {
        notesSumEl.textContent = `Lab Notes: ${notesCnt} curated group(s)`;
      }

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
        hdrLink.className = "px-3 py-1.5 rounded-lg text-xs font-semibold badge-warn hover:opacity-90 transition flex items-center gap-1.5 w-full justify-center";
        hdrLink.innerHTML = `<span>⚑ Statistical Snapshot: <strong>${activeFlags}</strong> Flagged Group(s) · <strong>${notesCnt}</strong> Bench Note(s) &rarr; Audit</span>`;
      } else {
        hdrLink.className = "px-3 py-1.5 rounded-lg text-xs font-semibold badge-pass hover:opacity-90 transition flex items-center gap-1.5 w-full justify-center";
        hdrLink.innerHTML = `<span>✓ Statistical Snapshot: 0 Active Flags &rarr; Open Precision Audit</span>`;
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
      const geoids = Array.from(new Set(fsList.map(f => f.geoid).filter(Boolean))).map(fmtGeoid);
      const geoSummary = geoids.length ? ` · GEOID: <span class="font-mono text-[var(--primary)]">${geoids.join(", ")}</span>` : "";
      document.getElementById("hdr-desc").innerHTML = `
        <strong>${fsList.length} field sample(s)</strong> &rarr; <strong>${psList.length} prepared sample(s)</strong> &rarr;
        <strong>${resRecs.length.toLocaleString()} analytical &amp; conversion observations</strong> (Providers: <span class="font-mono">${provStr}</span>)${geoSummary}.
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
      const outSummary = window.getOutlierSummary ? window.getOutlierSummary(ins) : {};
      const notes = ins.curated_notes || [];
      const encRes = encodeURIComponent(state.resource);

      const pctBadges = [
        p.glucan_dw_pct ? { label: "Glucan", val: `${d.glucan_dw_pct}% dw`, pct: `${p.glucan_dw_pct}th %ile` } : null,
        p.ash_pct ? { label: "Ash", val: `${d.ash_pct}%`, pct: `${p.ash_pct}th %ile` } : null,
        p.best_glucose_yld_pct ? { label: `PT Glucose (${d.best_glu_pt_method})`, val: `${d.best_glucose_yld_pct}%`, pct: `${p.best_glucose_yld_pct}th %ile` } : null,
        p.titer_3hp_g_l ? { label: "3-HP Titer", val: `${d.titer_3hp_g_l} g/L`, pct: `${p.titer_3hp_g_l}th %ile` } : null
      ].filter(Boolean);

      const withinRsdLabel = outSummary.withinRsdMedian !== null && outSummary.withinRsdMedian !== undefined
        ? `${outSummary.withinRsdMedian}%${outSummary.withinSdMedian !== null && outSummary.withinSdMedian !== undefined ? ` (±${fmtNum(outSummary.withinSdMedian, 2)})` : ''}`
        : 'n=1';

      panel.innerHTML = `
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-2.5">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded-md text-xs font-bold bg-[var(--primary)] text-[var(--primary-foreground)]">AI BRIEF</span>
            <h2 class="text-sm font-bold text-[var(--foreground)]">Synthesized Feedstock Meaning &amp; Stoichiometric Summary</h2>
          </div>
          <a href="${QC_PAGE_FILENAME}?resource=${encRes}" class="text-xs font-semibold text-[var(--primary)] hover:underline">
            View Full Statistical Outlier Screen (${outSummary.flaggedActive || 0} flags) &amp; Mined Bench Notes (${notes.length}) &rarr;
          </a>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
          <!-- Card 1: Feedstock Meaning & Conversion Profile -->
          <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-4 space-y-3">
            <div class="text-xs font-bold uppercase tracking-wider text-[var(--primary)]">1. Feedstock Meaning &amp; Conversion Profile</div>
            <p class="text-xs text-[var(--muted-foreground)] leading-relaxed">${formatMdInline((ins.ai_narratives && ins.ai_narratives.feedstock_profile) || ins.executive_summary || "")}</p>
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
              <span class="text-[11px] font-mono text-[var(--muted-foreground)]">Within-Rep RSD: ${withinRsdLabel}</span>
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
                Statistical Screen: <strong>${outSummary.flaggedActive || 0}</strong> active outlier group(s)
                ${outSummary.suppressedTrace ? `(${outSummary.suppressedTrace} trace &lt;100 ppm suppressed)` : ''} ·
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

      const geoids = Array.from(new Set(filtered.map(r => r.geoid).filter(Boolean))).map(fmtGeoid);
      const geoStr = geoids.length ? geoids.join(", ") : "Statewide / Unassigned";

      const sliceBadgeSuffix = BUNDLE.collaborator_slice_mode
        ? ` · Slice [${(BUNDLE.slice_qc_statuses || ["pass"]).join("+").toUpperCase()}]`
        : "";
      document.getElementById("active-slice-badge").textContent = `${filtered.length} / ${resRecs.length} obs (${passRate}% QC Pass)${sliceBadgeSuffix}`;

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
        { label: "Filtered Observations", value: `${filtered.length.toLocaleString()}`, sub: `${passRate}% QC Pass (${passCount}P · ${failCount}F)` },
        { label: "Sample Lineage & Geography", value: `${activeFs} Field → ${activePs} Prep`, sub: `GEOID: ${geoStr}` },
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
      const activeFlags = out
        ? (state.suppressTraceFlags ? (out.flagged_active ?? 0) : (out.flagged_raw ?? out.flagged_active ?? 0))
        : 0;
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
        const flagCnt = tabOut
          ? (state.suppressTraceFlags ? (tabOut.flagged_active ?? 0) : (tabOut.flagged_raw ?? tabOut.flagged_active ?? 0))
          : 0;
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

      const groupKeyFn = r => {
        if (state.repMode === "field_exp_mean_sd") return `Field: ${r.field_sample || r.prepared_sample} · ${r.experiment}`;
        if (state.proxGroupMode === "ps_exp") return `${r.prepared_sample} · ${r.experiment}`;
        if (state.proxGroupMode === "by_date") return `Col: ${r.collected_date || '—'} · Prep: ${r.prep_date || '—'} (${r.prepared_sample})`;
        return r.prepared_sample;
      };

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
          const dots = state.repMode === "replicates"
            ? gRecs.map(r => buildAuditChipHtml(r, gRecs, `${fmtNum(r.value)}%`)).join(" ")
            : `<span class="font-mono text-xs text-[var(--foreground)] font-semibold">Mean ± SD: ${fmtNum(st.mean)}% ± ${fmtNum(st.sd)}% (n=${st.n})</span>`;
          return `
            <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-3 space-y-1.5">
              <div class="flex items-center justify-between text-xs gap-2">
                <span class="font-mono font-semibold text-[var(--foreground)]">${g}</span>
                <div class="flex items-center gap-1.5">
                  <span class="font-mono font-bold text-[var(--foreground)]">${fmtNum(st.mean)}% <span class="font-normal text-[var(--muted-foreground)]">± ${fmtNum(st.sd)} (n=${st.n})</span></span>
                  ${buildAuditGroupBtnHtml(gRecs, "⚑ Audit")}
                </div>
              </div>
              <div class="w-full h-2.5 rounded-full bg-[var(--content)] overflow-hidden">
                <div class="h-full rounded-full bg-[var(--primary)]" style="width: ${pct}%"></div>
              </div>
              <div class="flex flex-wrap items-center justify-between gap-1 pt-0.5 text-xs text-[var(--muted-foreground)]">
                <span class="flex flex-wrap items-center gap-1">${state.repMode === "replicates" ? "Replicates (click to audit):" : "Summary:"} ${dots}</span>
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
            ${calRecs.map(r => {
              const sibs = calRecs.filter(x => x.prepared_sample === r.prepared_sample && x.experiment === r.experiment);
              return `
              <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-3.5 space-y-1 text-xs">
                <div class="flex items-center justify-between font-mono">
                  <span class="font-bold text-[var(--foreground)]">Record: ${r.record_id}</span>
                  <span class="flex items-center gap-1.5">${qcBadgeHtml(r.qc_status)} ${buildAuditChipHtml(r, sibs, "⚑ Audit")}</span>
                </div>
                <div class="text-[var(--muted-foreground)]">Sample: <span class="font-mono text-[var(--foreground)]">${r.prepared_sample}</span> · Exp: <span class="font-mono">${r.experiment}</span></div>
                ${r.note ? `<div class="mt-1 p-2 rounded bg-[var(--card)] border border-[var(--border)] font-mono text-[var(--foreground)]">Note: "${r.note}"</div>` : ""}
              </div>
            `;
            }).join("")}
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
                <p class="text-xs text-[var(--muted-foreground)]">Moisture + Volatile Solids + Ash closure across prepared samples, drying protocols, and collection/prep dates.</p>
              </div>
              <div class="inline-flex rounded-lg border border-[var(--border)] bg-[var(--background)] p-0.5">
                <button onclick="setSubMode('proxGroupMode', 'ps_exp')" class="px-3 py-1 rounded-md text-xs font-semibold ${state.proxGroupMode === 'ps_exp' ? 'bg-[var(--primary)] text-[var(--primary-foreground)]' : 'text-[var(--muted-foreground)]'}">By Sample × Experiment</button>
                <button onclick="setSubMode('proxGroupMode', 'ps')" class="px-3 py-1 rounded-md text-xs font-semibold ${state.proxGroupMode === 'ps' ? 'bg-[var(--primary)] text-[var(--primary-foreground)]' : 'text-[var(--muted-foreground)]'}">By Prepared Sample</button>
                <button onclick="setSubMode('proxGroupMode', 'by_date')" class="px-3 py-1 rounded-md text-xs font-semibold ${state.proxGroupMode === 'by_date' ? 'bg-[var(--primary)] text-[var(--primary-foreground)]' : 'text-[var(--muted-foreground)]'}">By Collection / Prep Date</button>
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
        let repsHtml = "";
        if (state.repMode === "replicates") {
          repsHtml = pRecs.slice(0, 12).map(r => {
            const sibs = pRecs.filter(x => x.prepared_sample === r.prepared_sample && x.experiment === r.experiment);
            return buildAuditChipHtml(r, sibs, `${r.prepared_sample} Rep ${r.replicate}: ${fmtNum(r.value)}%`);
          }).join(" ");
        } else {
          const gKeyFn = r => state.repMode === "field_exp_mean_sd"
            ? `${r.field_sample || r.prepared_sample} · ${r.experiment}`
            : `${r.prepared_sample} · ${r.experiment}`;
          const gKeys = Array.from(new Set(pRecs.map(gKeyFn)));
          repsHtml = gKeys.map(gk => {
            const grpRecs = pRecs.filter(r => gKeyFn(r) === gk);
            const gst = calcStats(grpRecs.map(r => r.value));
            return buildAuditGroupBtnHtml(grpRecs, `${gk}: ${fmtNum(gst.mean)}±${fmtNum(gst.sd)}% (n=${gst.n})`);
          }).join(" ");
        }
        return `
          <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-4 space-y-2">
            <div class="flex items-center justify-between gap-2">
              <div>
                <span class="text-sm font-bold uppercase text-[var(--foreground)]">${param}</span>
                <span class="ml-2 text-xs text-[var(--muted-foreground)] font-mono">(% dw · n=${st.n})</span>
              </div>
              <div class="flex items-center gap-1.5 text-sm font-mono font-bold text-[var(--foreground)]">
                <span>${fmtNum(st.mean)}% <span class="text-xs font-normal text-[var(--muted-foreground)]">± ${fmtNum(st.sd)}%</span></span>
                ${buildAuditGroupBtnHtml(pRecs, "⚑ Audit")}
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
              const chips = state.repMode === "replicates"
                ? `<div class="flex flex-wrap gap-1 pt-1">${pRecs.slice(0, 6).map(r => buildAuditChipHtml(r, pRecs, `${fmtNum(r.value)}${r.unit || '%'}`)).join(" ")}</div>`
                : "";
              return `
                <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-3.5 space-y-1">
                  <div class="flex justify-between items-center text-xs gap-1">
                    <span class="font-bold uppercase text-[var(--foreground)]">${p}</span>
                    <span class="flex items-center gap-1 font-mono font-bold">${fmtNum(st.mean)} ${pRecs[0].unit || '%'} (n=${st.n}) ${buildAuditGroupBtnHtml(pRecs, "⚑")}</span>
                  </div>
                  <div class="text-xs font-mono text-[var(--muted-foreground)]">Range: ${fmtNum(st.min)}–${fmtNum(st.max)}</div>
                  ${chips}
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
            ${xrdRecs.map(r => buildAuditChipHtml(r, xrdRecs.filter(x => x.prepared_sample === r.prepared_sample && x.experiment === r.experiment), `${r.prepared_sample} Rep ${r.replicate}: ${fmtNum(r.value)}%`)).join("")}
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
        const repRowHtml = state.repMode === "replicates"
          ? `<div class="flex flex-wrap gap-1 pt-1">${item.recs.slice(0, 8).map(r => buildAuditChipHtml(r, item.recs.filter(x => x.prepared_sample === r.prepared_sample && x.experiment === r.experiment), `${r.prepared_sample}#${r.replicate}: ${fmtNum(r.value)}`)).join(" ")}</div>`
          : "";
        return `
          <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-3 space-y-1.5">
            <div class="flex items-center justify-between text-xs gap-2">
              <span class="font-bold text-[var(--foreground)]">${item.label}</span>
              <span class="flex items-center gap-1.5 font-mono font-bold text-[var(--foreground)]">
                <span>${fmtNum(val)} ppm <span class="font-normal text-[var(--muted-foreground)]">(${fmtNum(val / 10000, 3)}% dw · n=${item.st.n})</span></span>
                ${buildAuditGroupBtnHtml(item.recs, "⚑ Audit")}
              </span>
            </div>
            <div class="w-full h-2.5 rounded-full bg-[var(--content)] overflow-hidden">
              <div class="h-full rounded-full bg-[var(--primary)]" style="width: ${pct}%"></div>
            </div>
            <div class="flex items-center justify-between text-[11px] font-mono text-[var(--muted-foreground)]">
              <span>Range: ${fmtNum(item.st.min)}–${fmtNum(item.st.max)} ppm</span>
              <span>SD: ±${fmtNum(item.st.sd)} ppm</span>
            </div>
            ${repRowHtml}
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
        const condKey = r => state.repMode === "field_exp_mean_sd"
          ? `${r.field_sample || r.prepared_sample} · ${r.experiment} (${r.pt_method} + ${r.eh_method})`
          : `${r.pt_method} + ${r.eh_method} (${r.vessel})`;
        const conds = Array.from(new Set(ptRecs.map(condKey)));
        const condCards = conds.map(c => {
          const cRecs = ptRecs.filter(r => condKey(r) === c);
          const gluRecs = cRecs.filter(r => r.parameter === "glucose_yld" && r.value !== null);
          const xylRecs = cRecs.filter(r => r.parameter === "xylose_yld" && r.value !== null);
          const gSt = calcStats(gluRecs.map(r => r.value));
          const xSt = calcStats(xylRecs.map(r => r.value));
          const gluChips = state.repMode === "replicates" && gluRecs.length
            ? `<div class="flex flex-wrap gap-1 pt-1">${gluRecs.slice(0, 8).map(r => buildAuditChipHtml(r, gluRecs, `${fmtNum(r.value)}%`)).join(" ")}</div>`
            : "";
          const xylChips = state.repMode === "replicates" && xylRecs.length
            ? `<div class="flex flex-wrap gap-1 pt-1">${xylRecs.slice(0, 8).map(r => buildAuditChipHtml(r, xylRecs, `${fmtNum(r.value)}%`)).join(" ")}</div>`
            : "";
          return `
            <div class="bg-[var(--background)] border border-[var(--border)] rounded-xl p-4 space-y-3">
              <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-2">
                <span class="font-mono font-bold text-sm text-[var(--foreground)]">${c}</span>
                <span class="flex items-center gap-1.5 text-xs font-mono text-[var(--muted-foreground)]">
                  <span>${cRecs.length} obs (${cRecs.filter(r => r.qc_status === 'pass').length}P / ${cRecs.filter(r => r.qc_status === 'fail').length}F)</span>
                  ${buildAuditGroupBtnHtml(cRecs, "⚑ Audit")}
                </span>
              </div>
              <div class="space-y-1">
                <div class="flex justify-between text-xs">
                  <span class="font-semibold text-[var(--foreground)]">Glucose Yield (% of glucan)</span>
                  <span class="font-mono font-bold">${fmtNum(gSt.mean)}% <span class="font-normal text-[var(--muted-foreground)]">± ${fmtNum(gSt.sd)}% (n=${gSt.n})</span></span>
                </div>
                <div class="w-full h-3 rounded-full bg-[var(--content)] overflow-hidden">
                  <div class="h-full rounded-full bg-[var(--primary)]" style="width: ${Math.min(100, gSt.mean || 0)}%"></div>
                </div>
                ${gluChips}
              </div>
              <div class="space-y-1">
                <div class="flex justify-between text-xs">
                  <span class="font-semibold text-[var(--foreground)]">Xylose Yield (% of xylan)</span>
                  <span class="font-mono font-bold">${fmtNum(xSt.mean)}% <span class="font-normal text-[var(--muted-foreground)]">± ${fmtNum(xSt.sd)}% (n=${xSt.n})</span></span>
                </div>
                <div class="w-full h-3 rounded-full bg-[var(--content)] overflow-hidden">
                  <div class="h-full rounded-full bg-amber-500" style="width: ${Math.min(100, ((xSt.mean || 0) / 110) * 100)}%"></div>
                </div>
                ${xylChips}
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
        const groupKey = r => state.repMode === "field_exp_mean_sd"
          ? `${r.field_sample || r.prepared_sample} · ${r.experiment}`
          : `${r.prepared_sample} · ${r.experiment}`;
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
                <span class="flex items-center gap-1.5 text-xs font-mono text-[var(--muted-foreground)]">
                  <span>Strain: ${strain}</span>
                  ${buildAuditGroupBtnHtml(gRecs, "⚑ Audit")}
                </span>
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
                <span class="flex items-center gap-1.5 text-xs font-mono text-[var(--muted-foreground)]">
                  <span>Bed Temp: ${fmtNum(ta.mean)}°C</span>
                  ${buildAuditGroupBtnHtml(gRecs, "⚑ Audit")}
                </span>
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

    function syncUrl(opts = { push: false }) {
      try {
        const u = new URL(window.location.href);
        u.searchParams.set("resource", state.resource);
        u.searchParams.set("tab", state.tab);
        u.searchParams.set("qc", state.qc_status);
        const stateSnapshot = { resource: state.resource, tab: state.tab, qc: state.qc_status };
        const nextUrl = u.toString();
        if (opts && opts.push === true && u.search !== window.location.search) {
          window.history.pushState(stateSnapshot, "", nextUrl);
        } else {
          window.history.replaceState(stateSnapshot, "", nextUrl);
        }
      } catch (_) {}
    }

    function render(opts = { push: false }) {
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
      syncUrl(opts);
    }

    window.selectResource = function(resName) {
      if (!RECORDS_BY_RESOURCE[resName]) return;
      state.resource = resName;
      state.prepared_sample = "all";
      state.field_sample = "all";
      initResourceSwitcher();
      initFiltersForResource();
      render({ push: true });
    };

    window.switchTab = function(tabName) {
      state.tab = tabName;
      render({ push: true });
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
    const fltRepModeEl = document.getElementById("flt-rep-mode");
    if (fltRepModeEl) {
      fltRepModeEl.value = state.repMode || "replicates";
      fltRepModeEl.addEventListener("change", e => {
        state.repMode = e.target.value;
        render();
      });
    }
    const fltDateTypeEl = document.getElementById("flt-date-type");
    const fltFromDateEl = document.getElementById("flt-from-date");
    const fltToDateEl = document.getElementById("flt-to-date");
    if (fltDateTypeEl) {
      fltDateTypeEl.value = state.date_type || "any";
      fltDateTypeEl.addEventListener("change", e => {
        state.date_type = e.target.value;
        render();
      });
    }
    if (fltFromDateEl) fltFromDateEl.value = state.from_date || "";
    if (fltToDateEl) fltToDateEl.value = state.to_date || "";
    if (window.initDateFilterInputs) {
      window.initDateFilterInputs("flt-from-date", "flt-to-date", "flt-date-type", "flt-date-clear", (fromVal, toVal, typeVal) => {
        state.from_date = fromVal;
        state.to_date = toVal;
        if (typeVal) state.date_type = typeVal;
        render();
      });
    }

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
        render({ push: true });
      });
    });

    const chkP1SuppressEl = document.getElementById("chk-p1-suppress-trace");
    if (chkP1SuppressEl) {
      chkP1SuppressEl.checked = state.suppressTraceFlags !== false;
      chkP1SuppressEl.addEventListener("change", e => {
        state.suppressTraceFlags = Boolean(e.target.checked);
        render();
      });
    }
    const chkP1BlindEl = document.getElementById("chk-p1-blind-mode");
    if (chkP1BlindEl) {
      chkP1BlindEl.checked = Boolean(state.blindMode);
      chkP1BlindEl.addEventListener("change", e => {
        state.blindMode = Boolean(e.target.checked);
        document.body.classList.toggle("blind-analyst-mode", state.blindMode);
        render();
      });
    }
    document.getElementById("btn-toggle-ai").addEventListener("click", () => {
      state.showAiPanel = !state.showAiPanel;
      document.getElementById("btn-toggle-ai").textContent = state.showAiPanel ? "✨ Hide AI Brief" : "✨ Show AI Brief";
      renderAiInsightsPanel();
    });

    document.getElementById("btn-reset-filters").addEventListener("click", () => {
      state.prepared_sample = "all";
      state.field_sample = "all";
      state.qc_status = "pass";
      state.repMode = "replicates";
      state.date_type = "any";
      state.from_date = "";
      state.to_date = "";
      if (fltRepModeEl) fltRepModeEl.value = "replicates";
      if (fltDateTypeEl) fltDateTypeEl.value = "any";
      if (fltFromDateEl) fltFromDateEl.value = "";
      if (fltToDateEl) fltToDateEl.value = "";
      const clrBtn = document.getElementById("flt-date-clear");
      if (clrBtn) clrBtn.classList.add("hidden");
      document.querySelectorAll(".qc-btn").forEach(b => {
        b.className = b.dataset.qc === "pass"
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
      let rowsToExport = getFilteredRecords();
      if (BUNDLE.collaborator_slice_mode && ACTIVE_RESOURCES.length > 1) {
        rowsToExport = ALL_RECORDS.filter(r => {
          if (state.qc_status !== "all" && r.qc_status !== state.qc_status) return false;
          if (!recordMatchesDateFilter(r, state.date_type, state.from_date, state.to_date)) return false;
          return true;
        });
      }
      const cols = ["resource_name", "record_id", "analysis_type", "prepared_sample", "field_sample", "collected_date", "geoid", "county_name", "prep_date", "exp_date", "prep_method", "experiment", "parameter", "value", "unit", "replicate", "pt_method", "eh_method", "vessel", "well_or_block", "qc_status", "note"];
      const csv = [
        cols.join(","),
        ...rowsToExport.map(r => cols.map(c => `"${String(r[c] ?? '').replace(/"/g, '""')}"`).join(","))
      ].join("\\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const slug = (BUNDLE.collaborator_slice_mode && ACTIVE_RESOURCES.length > 1)
        ? `multi_resource_${ACTIVE_RESOURCES.length}_resources`
        : state.resource.replace(/\\s+/g, "_");
      a.download = `${slug}_characterization.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });

    document.querySelectorAll(".qc-btn").forEach(b => {
      b.className = b.dataset.qc === state.qc_status
        ? "qc-btn px-2.5 py-1 rounded-md text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)]"
        : "qc-btn px-2.5 py-1 rounded-md text-xs font-medium text-[var(--muted-foreground)]";
    });
__SHARED_SLICE_AND_BUG_MODALS_JS__
    initSliceAndBugModals("Page 1 — Characterization & AI Brief");
    initResourceSwitcher();
    initFiltersForResource();
    window.addEventListener("popstate", () => {
      const p = new URLSearchParams(window.location.search);
      const resParam = (p.get("resource") || p.get("res") || DEFAULT_RESOURCE).toLowerCase();
      const matched = ACTIVE_RESOURCES.find(r => r.toLowerCase() === resParam) || ACTIVE_RESOURCES[0];
      const resourceChanged = matched !== state.resource;
      state.resource = matched;
      const tabParam = p.get("tab") || p.get("domain") || p.get("type") || "overview";
      state.tab = ["overview", ...TABS.map(t => t.key)].includes(tabParam) ? tabParam : "overview";
      const qcParam = p.get("qc");
      if (qcParam && ["pass", "all", "fail"].includes(qcParam)) {
        state.qc_status = qcParam;
      }
      initResourceSwitcher();
      if (resourceChanged) {
        state.prepared_sample = "all";
        state.field_sample = "all";
        initFiltersForResource();
      }
      render({ push: false });
    });
    render();
    window.refreshLiveQcOverlay(false);
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
        .replace("__SHARED_SLICE_AND_BUG_MODALS_HTML__", SHARED_SLICE_AND_BUG_MODALS_HTML)
        .replace("__SHARED_SLICE_AND_BUG_MODALS_JS__", SHARED_SLICE_AND_BUG_MODALS_JS)
    )


def build_qc_outlier_dashboard_html(
    bundle: dict[str, Any],
    default_resource: str = "almond hulls",
    char_page_filename: str = "resource_analysis_dashboard.html",
) -> str:
    """Compile Page 2: Dedicated Statistical Precision, Candidate Outlier Screening & Lab Notes Audit."""
    data_json = json.dumps(bundle, separators=(",", ":")).replace("</", "<\\/")
    single_res = bundle.get("single_resource")
    slice_res = bundle.get("slice_resources") or []
    dict_res = bundle.get("dicts", {}).get("resource_name") or []
    if single_res:
        default_resource = single_res.lower()
        title_prefix = single_res.title()
    elif slice_res:
        if default_resource.lower() not in [str(r).lower() for r in slice_res]:
            default_resource = str(slice_res[0]).lower()
        title_prefix = f"{len(slice_res)}-Resource Slice" if len(slice_res) > 1 else str(slice_res[0]).title()
    elif dict_res and default_resource.lower() not in [str(r).lower() for r in dict_res]:
        default_resource = str(dict_res[0]).lower()
        title_prefix = "All-Resources"
    else:
        title_prefix = "All-Resources"

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
          <span>2. Statistical Snapshot</span>
          <span id="nav-qc-badge" class="px-1.5 py-0.2 rounded-full text-[11px] font-mono bg-white/20"></span>
        </a>
        <a id="nav-page-explorer" href="resource_explorer_dashboard.html" class="px-3 py-1.5 rounded-lg font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)] transition">
          3. Multi-Resource Side-by-Side Explorer
        </a>
        <a id="nav-page-drift" href="../audit/db_environment_drift_dashboard.html" class="px-3 py-1.5 rounded-lg font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)] transition">
          4. DB Environment Drift
        </a>
        <a id="nav-page-workbench" href="/v1/dashboards/metadata/resource_audit_workbench.html" class="px-3 py-1.5 rounded-lg font-semibold badge-warn hover:opacity-90 transition">
          ⚖️ QC Audit Workbench
        </a>
      </div>
    </nav>

    <!-- Workspace Container: Left Sticky Filter Sidebar + Right Main Content -->
    <div class="flex flex-col lg:flex-row gap-4 items-start">
      <!-- Left Sticky Filter Sidebar (280px) -->
      <aside id="qc-sticky-filter-sidebar" class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-4 w-full lg:w-[280px]" style="width: 280px; position: sticky; top: 16px; max-height: calc(100vh - 32px); overflow-y: auto; flex-shrink: 0;">
        <div class="flex items-center justify-between border-b border-[var(--border)] pb-2">
          <h2 class="text-xs font-bold uppercase tracking-wider text-[var(--foreground)]">Filter Controls</h2>
          <button id="btn-reset-filters" type="button" class="px-2 py-1 rounded text-[11px] font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)]">
            Reset
          </button>
        </div>

        <!-- 1. Flag Filters -->
        <div class="space-y-2.5 border-b border-[var(--border)] pb-3.5">
          <div class="text-[11px] font-bold uppercase tracking-wider text-[var(--primary)]">Flag Filters</div>
          <div class="space-y-1">
            <label for="flt-sidebar-flag-type" class="block text-[11px] font-semibold text-[var(--muted-foreground)]">Flag Type:</label>
            <select id="flt-sidebar-flag-type" class="w-full rounded-lg px-2.5 py-1.5 text-xs font-semibold border border-[var(--border)] bg-[var(--background)]">
              <option value="all_groups">All Replicate Groups</option>
              <option value="flagged" selected>Active Flagged Only</option>
              <option value="dixon">Dixon's Q Outlier</option>
              <option value="rsd20">High RSD &gt; 20%</option>
              <option value="sd3x">&gt;3&times;SD_pooled</option>
              <option value="identical">Identical Replicates</option>
            </select>
          </div>
          <div class="space-y-1">
            <label for="flt-portal-qc" class="block text-[11px] font-semibold text-[var(--muted-foreground)]">QC / Portal Filter:</label>
            <select id="flt-portal-qc" class="w-full rounded-lg px-2.5 py-1.5 text-xs font-semibold border border-[var(--primary)]/50 bg-[var(--background)]">
              <option value="qc_pass" selected>qc_pass = pass Only (Unquarantined)</option>
              <option value="all">All Statuses &amp; QC (Raw + Pass/Fail)</option>
              <option value="portal_compliant">Portal Compliant Only (qc_pass=pass &amp; Active)</option>
              <option value="qc_fail">qc_pass = fail Only (Quarantined)</option>
            </select>
          </div>
        </div>

        <!-- 2. Choose an Analysis Type -->
        <div class="space-y-2 border-b border-[var(--border)] pb-3.5">
          <div class="text-[11px] font-bold uppercase tracking-wider text-[var(--primary)]">Choose an Analysis Type</div>
          <div class="flex flex-wrap gap-1.5" id="domain-pills"></div>
        </div>

        <!-- 3. Additional Filters -->
        <div class="space-y-2.5">
          <div class="text-[11px] font-bold uppercase tracking-wider text-[var(--primary)]">Additional Filters</div>

          <label class="flex items-start gap-2 text-xs font-semibold text-[var(--foreground)] cursor-pointer select-none bg-[var(--background)] p-2 rounded-lg border border-[var(--border)]" title="Suppress outlier flags on low-abundance elemental data (<100 ppm for ICP/XRF) and trace sugars (<0.5% dw or <0.5 g/L)">
            <input id="chk-suppress-trace" type="checkbox" checked class="mt-0.5 rounded border-[var(--border)] text-[var(--primary)]" />
            <span class="flex-1 leading-snug">
              Suppress Low-Abundance Trace Flags (&lt;100 ppm ICP/XRF, &lt;0.5% wt)
              <span id="sidebar-suppressed-count-badge" class="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono badge-info">0 suppressed</span>
            </span>
          </label>

          <label class="flex items-center gap-2 text-xs font-semibold text-[var(--foreground)] cursor-pointer select-none bg-[var(--background)] p-2 rounded-lg border border-[var(--border)]">
            <input id="chk-sidebar-blind-mode" type="checkbox" class="rounded border-[var(--border)] text-[var(--primary)]" />
            <span>Blind / Anonymize Analysts</span>
          </label>

          <div class="space-y-1">
            <label for="sidebar-search-input" class="block text-[11px] font-semibold text-[var(--muted-foreground)]">Keyword Search:</label>
            <input id="sidebar-search-input" type="text" placeholder="Search sample, parameter, note..." class="w-full rounded-lg px-2.5 py-1.5 text-xs border border-[var(--border)] bg-[var(--background)]" />
          </div>

          <div id="resource-switcher-wrap" class="space-y-1">
            <label for="flt-resource" class="block text-[11px] font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Resource:</label>
            <div class="flex items-center gap-1">
              <button id="btn-prev-res" type="button" class="px-2 py-1 rounded-lg text-xs font-bold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">&larr;</button>
              <select id="flt-resource" class="flex-1 min-w-0 rounded-lg px-2 py-1.5 text-xs font-bold border"></select>
              <button id="btn-next-res" type="button" class="px-2 py-1 rounded-lg text-xs font-bold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]">&rarr;</button>
            </div>
          </div>

          <div class="space-y-1">
            <label for="flt-prepared-sample" class="block text-[11px] font-semibold text-[var(--muted-foreground)]">Sample:</label>
            <select id="flt-prepared-sample" class="w-full rounded-lg px-2.5 py-1.5 text-xs font-medium border"></select>
          </div>

          <div class="space-y-1">
            <label for="flt-experiment" class="block text-[11px] font-semibold text-[var(--muted-foreground)]">Experiment:</label>
            <select id="flt-experiment" class="w-full rounded-lg px-2.5 py-1.5 text-xs font-medium border"></select>
          </div>

          <div class="space-y-1.5 bg-[var(--background)] p-2 rounded-lg border border-[var(--border)]">
            <div class="flex items-center justify-between">
              <label for="flt-date-type" class="text-[11px] font-semibold text-[var(--muted-foreground)]">Date:</label>
              <button id="flt-date-clear" type="button" title="Clear date filter" class="hidden px-1.5 py-0.5 rounded text-[10px] font-bold badge-warn hover:opacity-80">✕</button>
            </div>
            <select id="flt-date-type" class="w-full rounded px-1.5 py-0.5 text-xs font-medium border border-[var(--border)] bg-[var(--card)]">
              <option value="any">Collection or Run Date</option>
              <option value="collected">Collection Date Only</option>
              <option value="run">Run / Prep Date Only</option>
            </select>
            <div class="flex items-center gap-1">
              <input id="flt-from-date" type="date" min="2020-01-01" placeholder="2024-01-01" title="From Date (inclusive, defaults to 2024-01-01 when opened)" class="flex-1 min-w-0 rounded px-1.5 py-0.5 text-[11px] font-mono border border-[var(--border)] bg-[var(--card)]" />
              <span class="text-xs text-[var(--muted-foreground)]">&rarr;</span>
              <input id="flt-to-date" type="date" min="2020-01-01" placeholder="2024-01-01" title="To Date (inclusive)" class="flex-1 min-w-0 rounded px-1.5 py-0.5 text-[11px] font-mono border border-[var(--border)] bg-[var(--card)]" />
            </div>
          </div>
        </div>
      </aside>

      <!-- Right Main Content Column -->
      <div class="flex-1 min-w-0 space-y-4 w-full" style="flex: 1; min-width: 0;">
        <!-- Header & Statistical Screening Controls -->
        <header class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 sm:p-5 shadow-sm space-y-3.5">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div class="space-y-1 flex-1 min-w-[260px]">
              <div class="flex flex-wrap items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block"></span>
                <h1 id="hdr-title" class="text-lg sm:text-xl font-bold text-[var(--foreground)]">BioCirV — Statistical Replicate Precision &amp; Candidate Outlier Audit</h1>
                <span id="hdr-code-badge" class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-[var(--primary)] text-[var(--primary-foreground)] font-mono"></span>
                <span id="hdr-portal-badge" class="px-2.5 py-0.5 text-xs font-semibold rounded-full"></span>
                <span id="live-qc-overlay-badge" class="hidden px-2.5 py-0.5 text-xs font-semibold rounded-full badge-warn font-mono"></span>
              </div>
              <p id="hdr-desc" class="text-xs text-[var(--muted-foreground)]">
                Two-sided Dixon's Q (&alpha;=0.05, n&ge;3), Within-Group vs. Between-Group RSD, &gt;3&times;SD<sub>pooled</sub> replicate screening, Portal/QC status filtering, and Analyst QC Decision-Making Workbench.
              </p>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <button id="btn-refresh-qc-state" type="button" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--primary)]/50 hover:border-[var(--primary)] transition" title="Pull latest Stage 1 QC decisions from /v1/qc/decisions">
                ↻ Refresh QC State
              </button>
              <button id="btn-anon-analyst" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90">
                🔒 Hide Analysts
              </button>
              <button id="btn-theme-toggle" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90">
                ☀️ Light Mode
              </button>
              <button id="btn-open-slice-modal" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--primary)]/50 hover:border-[var(--primary)]">
                📤 Export Slice (.HTML)
              </button>
              <button id="btn-tray-to-workbench" type="button" onclick="window.sendSelectionTrayToWorkbench('pending')" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90">
                ⚖️ Export to Audit Workbench
              </button>
              <button id="btn-open-bug-modal" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-amber-500">
                🐛 Report a Bug
              </button>
              <button id="btn-export-flagged-csv" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90">
                ⬇ Export Flagged Groups CSV
              </button>
              <button id="btn-download-records-csv" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90">
                ⬇ Export Records CSV
              </button>
            </div>
          </div>
        </header>

        <!-- 5-Card Statistical Precision & QC KPI Strip -->
        <section class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3" id="qc-kpi-strip"></section>

        <!-- Analyst QC Decision-Making & Export Workbench Banner -->
        <section id="qc-decision-banner" class="bg-[var(--card)] border border-[var(--primary)]/50 rounded-xl p-3.5 shadow-sm"></section>

        <!-- 5 Dedicated Audit Workbench Sub-Tabs -->
        <div class="flex flex-wrap gap-1.5 bg-[var(--card)] border border-[var(--border)] rounded-xl p-1.5 shadow-sm" id="qc-sub-tabs">
          <button data-subtab="outliers" class="subtab-btn px-3.5 py-2 rounded-lg text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)]">1. Candidate Outlier Replicate Groups &amp; Decisions</button>
          <button data-subtab="rsd" class="subtab-btn px-3.5 py-2 rounded-lg text-xs font-semibold text-[var(--muted-foreground)]">2. Within vs. Between-Group RSD Precision</button>
          <button data-subtab="notes" class="subtab-btn px-3.5 py-2 rounded-lg text-xs font-semibold text-[var(--muted-foreground)]">3. Mined Lab &amp; Field Notes Audit</button>
          <button data-subtab="explorer" class="subtab-btn px-3.5 py-2 rounded-lg text-xs font-semibold text-[var(--muted-foreground)]">4. Full Record Explorer &amp; Record Decisions</button>
          <button data-subtab="review_queue" class="subtab-btn px-3.5 py-2 rounded-lg text-xs font-semibold text-[var(--muted-foreground)]">5. Review Queue &amp; Audit Ledger</button>
        </div>

        <!-- Dynamic Audit Workbench Container -->
        <main id="qc-content" class="space-y-4"></main>
      </div>
    </div>

  </div>

__SHARED_SLICE_AND_BUG_MODALS_HTML__
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
      all: "All",
      proximate: "Proximate",
      calorimetry: "Calorimetry",
      compositional: "Compositional",
      ultimate: "Ultimate",
      xrd: "XRD",
      icp: "ICP",
      xrf: "XRF",
      pretreatment: "Pretreatment",
      fermentation: "Fermentation",
      gasification: "Gasification"
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
      "Trace detection noise",
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
    const rawDomainParam = urlParams.get("domain") || urlParams.get("type") || "all";
    const initialDomainParam = rawDomainParam === "all" ? "all" : normalizeDomainKey(rawDomainParam);
    const initialSubtabParam = urlParams.get("subtab") || "outliers";
    const initialPortalQcParam = urlParams.get("portal_qc") || "qc_pass";

    const state = {
      resource: matchedInitialRes,
      domain: DOMAIN_LABELS[initialDomainParam] ? initialDomainParam : "all",
      subtab: ["outliers", "rsd", "notes", "explorer", "review_queue"].includes(initialSubtabParam) ? initialSubtabParam : "outliers",
      portalQcMode: ["all", "portal_compliant", "qc_pass", "qc_fail"].includes(initialPortalQcParam) ? initialPortalQcParam : "qc_pass",
      prepared_sample: "all",
      experiment: "all",
      date_type: BUNDLE.slice_date_type || (BUNDLE.slice_filters && BUNDLE.slice_filters.date_type) || "any",
      from_date: BUNDLE.slice_from_date || (BUNDLE.slice_filters && BUNDLE.slice_filters.from_date) || "",
      to_date: BUNDLE.slice_to_date || (BUNDLE.slice_filters && BUNDLE.slice_filters.to_date) || "",
      suppressTraceFlags: true,
      outlierFilterMode: urlParams.get("flag") || "flagged",
      explorerFlagFilter: "all",
      search: urlParams.get("q") || "",
      showDecisionQueueTable: false,
      queueStatusFilter: "all",
      queueScopeFilter: "all",
      queueAssigneeFilter: "all",
      queueAssigneeEmail: "",
      queueResourceScope: "all",
      anonymizeAnalyst: Boolean(BUNDLE.exclude_analyst_default)
    };
    Object.defineProperties(state, {
      selectedResource: { get() { return this.resource; }, set(v) { this.resource = v; } },
      selectedDomain: { get() { return this.domain; }, set(v) { this.domain = v; } },
      activeSubtab: { get() { return this.subtab; }, set(v) { this.subtab = v; } },
      outliersFilter: { get() { return this.outlierFilterMode; }, set(v) { this.outlierFilterMode = v; } },
      outliersSearch: { get() { return this.search; }, set(v) { this.search = v; } },
      blindMode: { get() { return this.anonymizeAnalyst; }, set(v) { this.anonymizeAnalyst = Boolean(v); } }
    });

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
      const repKey = window.normalizeReplicateGroupKey
        ? window.normalizeReplicateGroupKey(g, resourceName)
        : `${String(resourceName || "").toLowerCase()}::${g.prepared_sample || ""}::${g.analysis_type || ""}::${g.parameter || ""}::${g.prep_method || ""}::${g.experiment || ""}`;
      return `grp::${repKey}`;
    }

    function makeRecordDecisionKey(recordId) {
      return `rec::${recordId}`;
    }

    function getDecisionEntry(key) {
      if (DECISIONS_STORE[key]) return DECISIONS_STORE[key];
      if (String(key || "").startsWith("grp::") && window.matchesReplicateGroupKey) {
        const rawTargetKey = String(key).slice(5);
        const matched = Object.values(DECISIONS_STORE).find(e => {
          const eKey = e && (e.replicate_group_key || (String(e.key || "").startsWith("grp::") ? String(e.key).slice(5) : ""));
          return eKey && window.matchesReplicateGroupKey(rawTargetKey, eKey);
        });
        if (matched) return matched;
      }
      return { decision: "pending", note: "", updated_at: "" };
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
        const outSum = window.getOutlierSummary ? window.getOutlierSummary(ins) : {};
        const flg = outSum.flaggedActive || 0;
        const recs = RECORDS_BY_RESOURCE[r];
        const pTag = ins && ins.portal_excluded ? " [Portal Excluded]" : "";
        return `<option value="${r}">${r.toUpperCase()} — ${flg} Active Flag(s) (${recs.length} obs)${pTag}</option>`;
      }).join("");
      sel.value = state.resource;
      const wrap = document.getElementById("resource-switcher-wrap");
      if (wrap) {
        if (BUNDLE.single_resource || ACTIVE_RESOURCES.length <= 1) {
          wrap.classList.add("hidden");
        } else {
          wrap.classList.remove("hidden");
        }
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

    function matchesActiveDomain(rowOrGroup, tabKey, domainFilter) {
      if (!domainFilter || domainFilter === "all") return true;
      const target = normalizeDomainKey(domainFilter);
      if (rowOrGroup && rowOrGroup.analysis_type) {
        return normalizeDomainKey(rowOrGroup.analysis_type) === target;
      }
      return tabKey === target;
    }

    function getAllDomainOutlierGroups() {
      const ins = getResourceInsights();
      const resourcePortalExcluded = Boolean(ins && ins.portal_excluded);
      const byTab = (ins && ins.outlier_screening && ins.outlier_screening.by_tab) || {};
      const keys = Object.keys(byTab);
      const groups = [];
      const normRange = window.normalizeDateRange
        ? window.normalizeDateRange(state.from_date, state.to_date)
        : { from: state.from_date || "", to: state.to_date || "" };
      keys.forEach(k => {
        const t = byTab[k];
        if (!t) return;
        (t.replicate_groups || []).forEach(g => {
          if (!matchesActiveDomain(g, k, state.domain)) return;
          if (state.prepared_sample !== "all" && g.prepared_sample !== state.prepared_sample) return;
          if (state.experiment !== "all" && g.experiment !== state.experiment) return;
          if (!isGroupMatchingPortalQc(g, state.portalQcMode, resourcePortalExcluded)) return;
          if (normRange.from || normRange.to) {
            const lin = getSampleLineageSummary(state.resource, g.prepared_sample);
            const dtType = state.date_type || "any";
            const colD = lin.collectedDate ? String(lin.collectedDate).slice(0, 10) : "";
            const runD = lin.prepDate ? String(lin.prepDate).slice(0, 10) : "";
            const candidates = dtType === "collected"
              ? (colD ? [colD] : [])
              : (dtType === "run" ? (runD ? [runD] : []) : [colD, runD].filter(Boolean));
            if (!candidates.length) return;
            const ok = candidates.some(d => (!normRange.from || d >= normRange.from) && (!normRange.to || d <= normRange.to));
            if (!ok) return;
          }
          const resolvedDomKey = g && g.analysis_type ? normalizeDomainKey(g.analysis_type) : k;
          groups.push({ ...g, domainKey: resolvedDomKey });
        });
      });
      return groups;
    }

    function getAllDomainParamRsdRows() {
      const ins = getResourceInsights();
      const resourcePortalExcluded = Boolean(ins && ins.portal_excluded);
      if (state.portalQcMode === "portal_compliant" && resourcePortalExcluded) return [];
      const byTab = (ins && ins.outlier_screening && ins.outlier_screening.by_tab) || {};
      const keys = Object.keys(byTab);
      const rows = [];
      keys.forEach(k => {
        const t = byTab[k];
        if (!t) return;
        (t.param_rsd_table || []).forEach(p => {
          if (!matchesActiveDomain(p, k, state.domain)) return;
          const resolvedDomKey = p && p.analysis_type ? normalizeDomainKey(p.analysis_type) : k;
          rows.push({ ...p, domainKey: resolvedDomKey });
        });
      });
      return rows;
    }

    function isGroupMatchingFilter(g, mode, suppress) {
      if (suppress && g.below_cutoff) return false;
      if (mode === "identical") return Boolean(g.has_identical_replicates || g.identical_replicates);
      const isPrimary = suppress ? g.active_flagged : g.raw_flagged;
      const isMod = suppress ? (g.active_flagged || g.active_rsd10) : (g.raw_flagged || g.raw_rsd10);
      if (mode === "flagged" || mode === "active") return isPrimary;
      if (mode === "moderate") return isMod;
      if (mode === "dixon") return g.raw_dixon;
      if (mode === "rsd20" || mode === "rsd") return g.raw_rsd20;
      if (mode === "sd3x" || mode === "sd3") return g.raw_sd3x;
      if (mode === "unquarantined") return isPrimary && g.qc_pass_count > 0;
      if (mode === "reviewed") {
        const dKey = makeGroupDecisionKey(state.resource, g);
        const entry = DECISIONS_STORE[dKey];
        return Boolean(entry && (entry.decision !== "pending" || (entry.note && entry.note.trim())));
      }
      if (mode === "all_groups" || mode === "all") return true;
      return isPrimary;
    }

    function renderDomainPills() {
      const ins = getResourceInsights();
      const resourcePortalExcluded = Boolean(ins && ins.portal_excluded);
      const byTab = (ins && ins.outlier_screening && ins.outlier_screening.by_tab) || {};
      const suppress = state.suppressTraceFlags;

      const domains = ["all", ...DOMAIN_DEFS.map(d => d.key)];
      const tabKeys = Object.keys(byTab);
      document.getElementById("domain-pills").innerHTML = domains.map(d => {
        let flgCnt = 0;
        let grpCnt = 0;
        tabKeys.forEach(k => {
          const t = byTab[k];
          if (!t) return;
          (t.replicate_groups || []).forEach(g => {
            if (!matchesActiveDomain(g, k, d)) return;
            if (!isGroupMatchingPortalQc(g, state.portalQcMode, resourcePortalExcluded)) return;
            grpCnt += 1;
            if (isGroupMatchingFilter(g, "flagged", suppress)) flgCnt += 1;
          });
        });
        const active = state.domain === d;
        const label = DOMAIN_LABELS[d] || d;
        return `
          <button onclick="setDomain('${d}')" class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition flex items-center gap-1.5 ${active ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]' : 'bg-[var(--background)] text-[var(--muted-foreground)] border-[var(--border)] hover:text-[var(--foreground)]'}">
            <span>${label}</span>
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

      const currentAnalystEmail = (window.BioCirvQcClient && window.BioCirvQcClient.getUser() && window.BioCirvQcClient.getUser().email)
        ? String(window.BioCirvQcClient.getUser().email).toLowerCase()
        : "";
      const assignedToMeCnt = currentAnalystEmail
        ? allEntries.filter(e => String(e.assigned_to_email || "").toLowerCase() === currentAnalystEmail).length
        : 0;

      const queueRowsHtml = allEntries.length === 0
        ? `<div class="p-3 text-center text-xs text-[var(--muted-foreground)]">No analyst review decisions recorded yet. Select a decision or type a review note on any replicate group (Subtab 1), individual record (Subtab 4), or submit an ad-hoc finding.</div>`
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
                  <th class="py-1.5 px-2.5">Assigned To</th>
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
                      <td class="py-1.5 px-2.5 font-mono text-[11px]">${e.triage_scope || e.scope || 'group'}</td>
                      <td class="py-1.5 px-2.5 font-semibold">${e.resource_name || '—'}</td>
                      <td class="py-1.5 px-2.5 font-mono">${e.target_label || e.prepared_sample || e.record_id || '—'}</td>
                      <td class="py-1.5 px-2.5">${e.analysis_type || ''} · <strong class="font-mono">${e.parameter || '—'}</strong></td>
                      <td class="py-1.5 px-2.5"><span class="px-2 py-0.5 rounded text-[11px] font-semibold ${opt.badgeClass}">${opt.label}</span></td>
                      <td class="py-1.5 px-2.5 font-mono text-[11px] text-[var(--primary)]">${e.assigned_to_email || '<span class="text-[var(--muted-foreground)]">Unassigned</span>'}</td>
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
            ${currentAnalystEmail ? `<span class="px-2 py-0.5 rounded text-[11px] font-mono bg-[var(--secondary)] text-[var(--primary)] border border-[var(--border)]">👤 Assigned to Me: ${assignedToMeCnt}</span>` : ''}
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <button onclick="openReviewQueueSubtab()" class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90">
              📋 Open Review Queue Tab (${allEntries.length})
            </button>
            <button onclick="toggleDecisionQueueTable()" class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)]">
              ${state.showDecisionQueueTable ? '▲ Hide Quick Preview' : `▼ Quick Preview (${allEntries.length})`}
            </button>
            <button onclick="exportDecisionsCsv()" class="px-3 py-1 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90">
              ⬇ CSV (${allEntries.length})
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
      const domQueryPage2 = state.domain && state.domain !== "all" ? `&domain=${encodeURIComponent(state.domain)}` : "";
      const domQueryPage3 = state.domain && state.domain !== "all" ? `&type=${encodeURIComponent(state.domain)}` : "";
      document.getElementById("nav-page-char").href = `${CHAR_PAGE_FILENAME}?resource=${encRes}`;
      document.getElementById("nav-page-qc").href = `resource_qc_outlier_dashboard.html?resource=${encRes}${domQueryPage2}`;
      document.getElementById("nav-page-explorer").href = `resource_explorer_dashboard.html?resource=${encRes}${domQueryPage3}`;

      const groups = getAllDomainOutlierGroups();
      const paramRows = getAllDomainParamRsdRows();
      const suppress = state.suppressTraceFlags;
      const primaryGroups = groups.filter(g => isGroupMatchingFilter(g, "flagged", suppress));
      const dixonGroups = groups.filter(g => isGroupMatchingFilter(g, "dixon", suppress));
      const rsd20Groups = groups.filter(g => isGroupMatchingFilter(g, "rsd20", suppress));
      const sd3xGroups = groups.filter(g => isGroupMatchingFilter(g, "sd3x", suppress));
      const unquarGroups = groups.filter(g => isGroupMatchingFilter(g, "unquarantined", suppress));
      const suppressedCount = groups.filter(g => g.below_cutoff && g.raw_flagged).length;

      document.getElementById("nav-qc-badge").textContent = `⚑ ${primaryGroups.length}`;
      const suppBadgeEl = document.getElementById("sidebar-suppressed-count-badge");
      if (suppBadgeEl) suppBadgeEl.textContent = `${suppressedCount} suppressed`;
      const chkBlindEl = document.getElementById("chk-sidebar-blind-mode");
      if (chkBlindEl) chkBlindEl.checked = Boolean(state.anonymizeAnalyst);
      const sidebarFlagEl = document.getElementById("flt-sidebar-flag-type");
      if (sidebarFlagEl) {
        const modeMap = { all: "all_groups", active: "flagged", rsd: "rsd20", sd3: "sd3x" };
        const targetVal = modeMap[state.outlierFilterMode] || state.outlierFilterMode;
        if (!sidebarFlagEl.options || Array.from(sidebarFlagEl.options).some(o => o.value === targetVal)) {
          sidebarFlagEl.value = targetVal;
        }
      }
      const sidebarSearchEl = document.getElementById("sidebar-search-input");
      if (sidebarSearchEl && document.activeElement !== sidebarSearchEl) {
        sidebarSearchEl.value = state.search || "";
      }

      const portalModeLabel = {
        all: "All Statuses (Raw + Pass/Fail)",
        portal_compliant: "Portal Compliant Only",
        qc_pass: "qc_pass = pass Only",
        qc_fail: "qc_pass = fail Only"
      }[state.portalQcMode];

      const outSummary = window.getOutlierSummary ? window.getOutlierSummary(ins) : {};
      const activeEvalGroups = groups.filter(g => !(suppress && g.below_cutoff));
      const multiRepGroups = activeEvalGroups.filter(g => (g.n || 0) >= 2 && g.rsd_within_pct !== null && g.rsd_within_pct !== undefined);
      const dynWithinRsdMed = window.computeMedianNumeric
        ? window.computeMedianNumeric(multiRepGroups.map(g => g.rsd_within_pct))
        : null;
      const dynWithinSdMed = window.computeMedianNumeric
        ? window.computeMedianNumeric(multiRepGroups.map(g => g.within_sd !== undefined && g.within_sd !== null ? g.within_sd : g.sd))
        : null;
      const withinRsdVal = dynWithinRsdMed !== null
        ? dynWithinRsdMed
        : (groups.length === 0 ? (outSummary.withinRsdMedian ?? null) : null);
      const withinSdVal = dynWithinSdMed !== null
        ? dynWithinSdMed
        : (groups.length === 0 ? (outSummary.withinSdMedian ?? null) : null);
      const multiRepCount = groups.length > 0 ? multiRepGroups.length : (outSummary.rsdDefinedGroups || 0);
      const withinKpiValue = withinRsdVal !== null && withinRsdVal !== undefined
        ? `${fmtNum(withinRsdVal, 1)}%${withinSdVal !== null && withinSdVal !== undefined ? ` (±${fmtNum(withinSdVal, 2)})` : ""}`
        : "N/A (n=1)";

      const activeParamRows = paramRows.filter(p => !(suppress && p.below_cutoff));
      const dynBetweenRsdMed = window.computeMedianNumeric
        ? window.computeMedianNumeric(
            activeParamRows.length > 0
              ? activeParamRows.map(p => p.between_rsd_pct)
              : activeEvalGroups.map(g => g.rsd_between_pct)
          )
        : null;
      const dynBetweenSdMed = window.computeMedianNumeric
        ? window.computeMedianNumeric(
            activeParamRows.length > 0
              ? activeParamRows.map(p => p.between_sd !== undefined && p.between_sd !== null ? p.between_sd : p.pooled_sd)
              : activeEvalGroups.map(g => g.between_sd)
          )
        : null;
      const betweenRsdVal = dynBetweenRsdMed !== null
        ? dynBetweenRsdMed
        : (groups.length === 0 ? (outSummary.betweenRsdMedian ?? null) : null);
      const betweenSdVal = dynBetweenSdMed !== null
        ? dynBetweenSdMed
        : (groups.length === 0 ? (outSummary.betweenSdMedian ?? null) : null);
      const multiMethodParamCnt = activeParamRows.filter(p => p.between_rsd_pct !== null && p.between_rsd_pct !== undefined).length;
      const betweenKpiValue = betweenRsdVal !== null && betweenRsdVal !== undefined
        ? `${fmtNum(betweenRsdVal, 1)}%${betweenSdVal !== null && betweenSdVal !== undefined ? ` (±${fmtNum(betweenSdVal, 2)})` : ""}`
        : "N/A (n=1 method group)";
      const betweenKpiSub = betweenRsdVal !== null && betweenRsdVal !== undefined
        ? `Method-stratified across ${multiMethodParamCnt || activeParamRows.length} parameter(s)`
        : "Single method group per parameter (k=1)";

      const kpis = [
        { label: `Flag Counts (${portalModeLabel})`, value: `${primaryGroups.length} / ${groups.length}`, sub: `Dixon Q: ${dixonGroups.length} · RSD>20%: ${rsd20Groups.length} · >3×SD: ${sd3xGroups.length}` },
        { label: "Unquarantined (QC Pass) Flags", value: `${unquarGroups.length}`, sub: unquarGroups.length ? "Flagged groups with qc_pass=pass records" : "Zero unquarantined flags in current filter" },
        { label: "Within-Replicate RSD & SD", value: withinKpiValue, sub: `Across ${multiRepCount} multi-replicate groups` },
        { label: "Between-Sample RSD & SD (Method-Stratified)", value: betweenKpiValue, sub: betweenKpiSub },
        { label: "Trace Suppressed & Lab Notes", value: `${suppressedCount} trace · ${notes.length} notes`, sub: suppress ? "Trace floor ON (<100 ppm ICP/XRF, <0.5% wt)" : "Trace floor OFF (showing all raw flags)" }
      ];

      document.getElementById("qc-kpi-strip").innerHTML = kpis.map(k => `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-3.5 shadow-sm">
          <div class="text-xs font-medium text-[var(--muted-foreground)]">${k.label}</div>
          <div class="text-base sm:text-lg font-bold text-[var(--foreground)] mt-0.5 font-mono truncate">${k.value}</div>
          <div class="text-[11px] text-[var(--muted-foreground)] mt-0.5 truncate" title="${k.sub.replace(/"/g, '&quot;')}">${k.sub}</div>
        </div>
      `).join("");

      const filteredExplorer = getFilteredExplorerRecords();
      const queueEntries = Object.values(DECISIONS_STORE);
      const openQueueCnt = queueEntries.filter(e => !e.status || e.status === "open" || e.status === "pending").length;
      const subLabels = {
        outliers: `1. Candidate Outlier Replicate Groups & Decisions (${primaryGroups.length} flagged)`,
        rsd: `2. Within vs. Between-Group RSD Precision (${paramRows.length} params)`,
        notes: `3. Mined Lab & Field Notes Audit (${notes.length})`,
        explorer: `4. Full Record Explorer & Record Decisions (${filteredExplorer.length})`,
        review_queue: `5. Review Queue & Audit Ledger (${openQueueCnt} open / ${queueEntries.length} total)`
      };
      document.querySelectorAll(".subtab-btn").forEach(btn => {
        const st = btn.dataset.subtab;
        btn.textContent = subLabels[st] || st;
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
      const identicalGroups = groups.filter(g => isGroupMatchingFilter(g, "identical", suppress));
      const unquarGroups = groups.filter(g => isGroupMatchingFilter(g, "unquarantined", suppress));
      const reviewedGroups = groups.filter(g => isGroupMatchingFilter(g, "reviewed", suppress));
      const qSearch = (state.search || "").trim().toLowerCase();
      const displayedGroups = groups.filter(g => {
        if (!isGroupMatchingFilter(g, state.outlierFilterMode, suppress)) return false;
        if (qSearch) {
          const hay = `${g.prepared_sample || ""} ${g.parameter || ""} ${g.experiment || ""} ${g.prep_method || ""} ${g.analysis_type || ""} ${g.note || ""} ${(g.replicates || []).map(r => r.id).join(" ")}`.toLowerCase();
          if (!hay.includes(qSearch)) return false;
        }
        return true;
      });

      const filterBtns = [
        { id: "flagged", label: `Primary Flagged (${primaryGroups.length})` },
        { id: "moderate", label: `Include Moderate RSD >10% (${modGroups.length})` },
        { id: "dixon", label: `Dixon's Q α=0.05 (${dixonGroups.length})` },
        { id: "rsd20", label: `RSD >20% (${rsd20Groups.length})` },
        { id: "sd3x", label: `>3×SD Pooled (${sd3xGroups.length})` },
        { id: "identical", label: `Identical Replicates (${identicalGroups.length})` },
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
                  <th class="py-2.5 px-3 min-w-[300px]">⚖️ Triage Scope (Single vs. Group), Decision &amp; Assignee</th>
                </tr>
              </thead>
              <tbody>
                ${displayedGroups.map(g => {
                  const sd3Set = new Set(g.sd3x_candidate_ids || []);
                  const candRecIds = (g.replicates || []).map(r => r.id).join("|");
                  const singleCandId = g.dixon_candidate_id || ((g.sd3x_candidate_ids && g.sd3x_candidate_ids[0]) || ((g.replicates && g.replicates[0] && g.replicates[0].id) || ""));
                  const repGroupKey = window.normalizeReplicateGroupKey ? window.normalizeReplicateGroupKey(g, state.resource) : "";
                  const repChips = (g.replicates || []).map(rep => {
                    const isDixonCand = g.dixon_candidate_id && rep.id === g.dixon_candidate_id;
                    const isSd3Cand = sd3Set.has(rep.id);
                    const isCand = isDixonCand || isSd3Cand;
                    const qcTag = rep.qc === "fail" ? " [FAIL]" : "";
                    const chipAuditPayload = encodeURIComponent(JSON.stringify({
                      resource_name: state.resource,
                      analysis_type: g.analysis_type,
                      prepared_sample: g.prepared_sample,
                      prep_method: g.prep_method || "",
                      group_context_label: g.group_context_label || g.prep_method || "",
                      experiment: g.experiment,
                      parameter: g.parameter,
                      replicate_group_key: repGroupKey,
                      record_id: rep.id,
                      dixon_candidate_id: rep.id,
                      record_ids: candRecIds,
                      all_group_record_ids: candRecIds,
                      n: g.n,
                      scope: "replicate_group",
                      triage_scope: "group",
                      note: `Clicked replicate ${rep.id} (val=${fmtNum(rep.val, 2)} ${g.unit || ''}, n=${g.n}, group mean=${fmtNum(g.mean, 2)} ± ${fmtNum(g.sd, 2)})`
                    }));
                    return `<span class="inline-flex items-center gap-0.5"><button type="button" onclick="window.auditPage2PointOrGroup('${chipAuditPayload}')" title="Click to select Entire Replicate Group (n=${g.n}, default) or Single Point Only (${rep.id}) · Rep ${rep.rep}, QC: ${rep.qc}" class="px-1.5 py-0.5 rounded font-mono text-xs transition ${isCand ? 'badge-warn ring-1 ring-amber-500 font-bold' : 'bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] hover:border-[var(--primary)]'}">⚑ ${isCand ? '★ ' : ''}${fmtNum(rep.val, 2)}${qcTag}</button><button type="button" onclick="jumpToRecord('${rep.id}')" title="Jump to Record ${rep.id} in Explorer" class="px-1 py-0.5 rounded text-[10px] text-[var(--muted-foreground)] hover:text-[var(--primary)]">🔍</button></span>`;
                  }).join(" ");

                  const badges = [];
                  const showActiveFlags = !g.below_cutoff || !state.suppressTraceFlags;
                  if (showActiveFlags) {
                    if (g.raw_dixon) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold badge-fail" title="Dixon Q=${fmtNum(g.dixon_q, 3)}">⚑ Dixon Outlier</span>`);
                    if (g.raw_rsd20) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold badge-warn" title="Within-group RSD ${fmtNum(g.rsd_within_pct, 1)}% > 20%">⚑ RSD &gt; 20%</span>`);
                    else if (g.raw_rsd10) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono badge-info" title="Within-group RSD ${fmtNum(g.rsd_within_pct, 1)}%">⚑ RSD 10–20%</span>`);
                    if (g.raw_sd3x) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold badge-warn" title=">3×SD_pooled candidate">⚑ &gt;3&times;SD_pooled</span>`);
                    if (g.has_identical_replicates) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono badge-info" title="Informational: all replicates in group are identical (within_sd = 0) — Identical Replicates (SD=0)">⚑ Identical Replicates</span>`);
                    if (g.qc_mixed) badges.push(`<span class="px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold badge-fail" title="Mixed QC (${g.qc_pass_count}P/${g.qc_fail_count}F)">⚑ Mixed QC</span>`);
                  }
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
                  const defaultTriageScope = "group";
                  const currentTriageScope = dEntry.triage_scope || defaultTriageScope;
                  const metaPayload = encodeURIComponent(JSON.stringify({
                    scope: currentTriageScope === "single" ? "single_record" : "replicate_group",
                    triage_scope: currentTriageScope,
                    replicate_group_key: repGroupKey,
                    resource_name: state.resource,
                    analysis_type: g.analysis_type,
                    prepared_sample: g.prepared_sample,
                    prep_method: g.prep_method || "",
                    group_context_label: g.group_context_label || g.prep_method || "",
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
                    within_sd: g.within_sd !== undefined ? g.within_sd : g.sd,
                    rsd_within_pct: g.rsd_within_pct,
                    dixon_q: g.dixon_q,
                    dixon_candidate_id: singleCandId,
                    record_id: currentTriageScope === "single" ? singleCandId : singleCandId,
                    record_ids: currentTriageScope === "single" ? singleCandId : candRecIds,
                    all_group_record_ids: candRecIds,
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
                        <div class="mt-1 flex flex-wrap gap-1">
                          <button onclick="inspectSampleParam('${g.prepared_sample}', '${g.parameter}')" class="px-2 py-0.5 rounded bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] text-[10px] font-semibold hover:border-[var(--primary)]">Inspect Records &rarr;</button>
                          <button type="button" onclick="window.auditPage2PointOrGroup('${metaPayload}')" class="px-2 py-0.5 rounded badge-warn text-[10px] font-semibold hover:opacity-90">⚑ Audit Modal</button>
                        </div>
                      </td>
                      <td class="py-2.5 px-3"><div class="flex flex-wrap items-center gap-1"><span class="text-[11px] font-mono text-[var(--muted-foreground)]">n=${g.n}:</span> ${repChips}</div></td>
                      <td class="py-2.5 px-3 font-mono text-right whitespace-nowrap"><strong>${fmtNum(g.mean, 2)}</strong> &plusmn; ${fmtNum(g.within_sd !== undefined && g.within_sd !== null ? g.within_sd : g.sd, 2)}</td>
                      <td class="py-2.5 px-3 font-mono text-right whitespace-nowrap">
                        <span class="${(g.rsd_within_pct || 0) > 20 ? 'text-red-500 font-bold' : ((g.rsd_within_pct || 0) > 10 ? 'text-amber-500 font-semibold' : 'text-[var(--foreground)]')}">${g.rsd_within_pct !== null && g.rsd_within_pct !== undefined ? `${fmtNum(g.rsd_within_pct, 1)}% (±${fmtNum(g.within_sd !== undefined && g.within_sd !== null ? g.within_sd : g.sd, 2)})` : '—'}</span>
                        <span class="text-[var(--muted-foreground)]"> vs </span>
                        <span class="text-[var(--primary)]">${g.rsd_between_pct !== null && g.rsd_between_pct !== undefined ? `${fmtNum(g.rsd_between_pct, 1)}%${g.between_sd !== null && g.between_sd !== undefined ? ` (±${fmtNum(g.between_sd, 2)})` : ''}` : 'N/A (n=1 method group)'}</span>
                      </td>
                      <td class="py-2.5 px-3 space-y-1">
                        <div class="flex flex-wrap gap-1">${badges.join("") || '<span class="text-[var(--muted-foreground)]">Pass</span>'}</div>
                        <div>${qcSummary}</div>
                        ${g.note ? `<div class="text-[11px] font-mono text-[var(--muted-foreground)] italic truncate max-w-[190px]" title="${g.note.replace(/"/g, '&quot;')}">"${g.note}"</div>` : ""}
                      </td>
                      <td class="py-2.5 px-3 space-y-1.5 min-w-[300px]">
                        <div class="flex items-center gap-1 text-[10px]">
                          <span class="font-semibold text-[var(--muted-foreground)]">Selection Scope:</span>
                          <select onchange="handleDecisionScope('${safeKeyAttr}', this.value, '${metaPayload}')" class="flex-1 rounded px-1.5 py-0.5 text-[11px] font-mono font-semibold border border-[var(--border)] bg-[var(--background)]">
                            <option value="group" ${currentTriageScope === 'group' ? 'selected' : ''}>Entire Replicate Group (n=${g.n} recs)</option>
                            <option value="single" ${currentTriageScope === 'single' ? 'selected' : ''}>Single Point Only (${singleCandId || 'rec'})</option>
                          </select>
                        </div>
                        <select onchange="handleDecisionChange('${safeKeyAttr}', this.value, '${metaPayload}')" class="w-full rounded px-2 py-1 text-xs font-semibold border border-[var(--border)]">
                          ${DECISION_OPTIONS.map(o => `<option value="${o.value}" ${dEntry.decision === o.value ? 'selected' : ''}>${o.label}</option>`).join("")}
                        </select>
                        <input type="text" value="${(dEntry.note || '').replace(/"/g, '&quot;')}" onchange="handleDecisionNote('${safeKeyAttr}', this.value, '${metaPayload}')" placeholder="Add reviewer rationale / action note..." class="w-full rounded px-2 py-1 text-xs border border-[var(--border)] font-mono" />
                        <div class="flex items-center gap-1">
                          <input type="email" value="${(dEntry.assigned_to_email || '').replace(/"/g, '&quot;')}" onchange="handleDecisionAssignee('${safeKeyAttr}', this.value, '${metaPayload}')" placeholder="Assign to email (e.g. reviewer@lbl.gov)..." class="flex-1 rounded px-2 py-1 text-[11px] border border-[var(--border)] font-mono" />
                          <button type="button" onclick="approveAndSyncDecision('${safeKeyAttr}', '${metaPayload}')" title="Approve decision &amp; sync to Google Sheets + Postgres" class="px-2 py-1 rounded text-[10px] font-bold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 whitespace-nowrap">⚡ Approve &amp; Sync</button>
                        </div>
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
              <p class="text-xs text-[var(--muted-foreground)]">Replicates marked with <strong>★</strong> are extreme candidate values identified by two-sided Dixon's Q (&alpha;=0.05, n&ge;3) or &gt;3&times;SD<sub>pooled</sub>. Choose whether to flip a <strong>Single Candidate Outlier</strong> or the <strong>Whole Replicate Group</strong>, assign a reviewer by email, or click <strong>⚡ Approve &amp; Sync</strong> to write back to Google Sheets.</p>
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
        const wSdMed = p.within_sd_median !== undefined && p.within_sd_median !== null ? p.within_sd_median : p.pooled_sd;
        const bRsd = p.between_rsd_pct;
        const bSd = p.between_sd !== undefined && p.between_sd !== null ? p.between_sd : null;
        const wBarPct = wMed !== null ? Math.min(100, Math.max(3, (wMed / 40) * 100)) : 0;
        const bBarPct = bRsd !== null ? Math.min(100, Math.max(3, (bRsd / 40) * 100)) : 0;
        const wBarColor = wMed === null ? "bg-gray-400" : (wMed > 20 ? "bg-red-500" : (wMed > 10 ? "bg-amber-500" : "bg-emerald-500"));
        const flagCnt = suppress ? (p.flagged_active ?? p.flagged_replicate_groups ?? 0) : p.flagged_raw;
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
              ${wMed !== null && wMed !== undefined ? `
                <div class="flex items-center justify-between gap-2">
                  <span><strong>${fmtNum(wMed, 1)}%</strong>${wSdMed !== null && wSdMed !== undefined ? ` <span class="text-[var(--foreground)]">(±${fmtNum(wSdMed, 2)})</span>` : ""} <span class="text-[var(--muted-foreground)]">(max ${fmtNum(wMax, 1)}%)</span></span>
                </div>
                <div class="w-full h-2 rounded-full bg-[var(--content)] overflow-hidden mt-1">
                  <div class="h-full rounded-full ${wBarColor}" style="width: ${wBarPct}%"></div>
                </div>
              ` : `<span class="text-[var(--muted-foreground)] italic">N/A (n=1)</span>`}
            </td>
            <td class="py-2.5 px-3 font-mono">
              ${bRsd !== null && bRsd !== undefined ? `
                <div class="flex items-center justify-between gap-2">
                  <span><strong class="text-[var(--primary)]">${fmtNum(bRsd, 1)}%</strong>${bSd !== null && bSd !== undefined ? ` <span class="text-[var(--foreground)]">(±${fmtNum(bSd, 2)})</span>` : ""}</span>
                  <span class="text-[10px] text-[var(--muted-foreground)]">across ${p.between_k_groups || p.n_groups} means</span>
                </div>
                <div class="w-full h-2 rounded-full bg-[var(--content)] overflow-hidden mt-1">
                  <div class="h-full rounded-full bg-[var(--primary)]" style="width: ${bBarPct}%"></div>
                </div>
              ` : `<span class="text-[var(--muted-foreground)] italic">N/A (n=1 method group)</span>`}
            </td>
            <td class="py-2.5 px-3 font-mono text-right">${p.pooled_sd !== null && p.pooled_sd !== undefined ? `±${fmtNum(p.pooled_sd, 2)}` : '—'}</td>
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
      const rawNotes = ((ins && ins.curated_notes) || []).filter(n => {
        if (state.domain !== "all" && n && n.analysis_type) {
          return normalizeDomainKey(n.analysis_type) === state.domain;
        }
        return true;
      });
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
              rawRsd20: Boolean(g.raw_rsd20),
              hasIdentical: Boolean(g.has_identical_replicates),
              qcMixed: Boolean(g.qc_mixed),
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
        if (state.domain !== "all" && r.analysis_type && normalizeDomainKey(r.analysis_type) !== state.domain) return false;
        if (!isRecordMatchingPortalQc(r, state.portalQcMode)) return false;
        if (state.prepared_sample !== "all" && r.prepared_sample !== state.prepared_sample) return false;
        if (state.experiment !== "all" && r.experiment !== state.experiment) return false;
        if (state.from_date || state.to_date) {
          if (window.recordMatchesDateFilter) {
            if (!window.recordMatchesDateFilter(r, state.date_type || "any", state.from_date, state.to_date)) return false;
          } else {
            const norm = window.normalizeDateRange
              ? window.normalizeDateRange(state.from_date, state.to_date)
              : { from: state.from_date || "", to: state.to_date || "" };
            const dtType = state.date_type || "any";
            const colD = r.collected_date ? String(r.collected_date).slice(0, 10) : "";
            const runD = r.exp_date ? String(r.exp_date).slice(0, 10) : (r.prep_date ? String(r.prep_date).slice(0, 10) : "");
            const candidates = dtType === "collected"
              ? (colD ? [colD] : [])
              : (dtType === "run" ? (runD ? [runD] : []) : [colD, runD].filter(Boolean));
            if (!candidates.length) return false;
            const ok = candidates.some(d => (!norm.from || d >= norm.from) && (!norm.to || d <= norm.to));
            if (!ok) return false;
          }
        }
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

      const groupSiblingsMap = {};
      getResourceRecords().forEach(rec => {
        const gKey = `${rec.analysis_type || ''}||${rec.prepared_sample || ''}||${rec.experiment || ''}||${rec.parameter || ''}`;
        if (!groupSiblingsMap[gKey]) groupSiblingsMap[gKey] = [];
        groupSiblingsMap[gKey].push(rec.record_id);
      });

      const rowsHtml = flagFiltered.slice(0, 600).map(r => {
        const info = outlierMap[r.record_id];
        let statCell = '<span class="text-[var(--muted-foreground)]">—</span>';
        if (info) {
          if (info.isSuppressed && state.suppressTraceFlags) {
            statCell = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono badge-info">Trace (${info.cutoffLabel})</span>`;
          } else if (info.isCandidate) {
            const tags = [];
            if (info.isDixonCand) tags.push(`⚑ Dixon Outlier`);
            if (info.isSd3Cand) tags.push(`⚑ >3×SD_pooled`);
            statCell = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold badge-warn ring-1 ring-amber-500" title="Dixon Q=${fmtNum(info.dixonQ, 2)} · Within-RSD ${fmtNum(info.rsdWithin, 1)}%">${tags.join(' · ')}</span>`;
          } else if (info.isPrimary) {
            const pillLabel = info.rawRsd20 ? "⚑ RSD &gt; 20%" : "⚑ Outlier Flag";
            statCell = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono badge-warn" title="Within-group RSD ${fmtNum(info.rsdWithin, 1)}%">${pillLabel}</span>`;
          }
        }
        const qcHtml = r.qc_status === "pass"
          ? `<span class="badge-pass px-2 py-0.5 text-xs font-mono font-semibold rounded">PASS</span>`
          : `<span class="badge-fail px-2 py-0.5 text-xs font-mono font-semibold rounded">FAIL</span>`;

        const recKey = makeRecordDecisionKey(r.record_id);
        const dEntry = getDecisionEntry(recKey);
        const safeKeyAttr = recKey.replace(/"/g, "&quot;").replace(/'/g, "\\'");
        const gKey = `${r.analysis_type || ''}||${r.prepared_sample || ''}||${r.experiment || ''}||${r.parameter || ''}`;
        const groupRecIdsArr = groupSiblingsMap[gKey] || [r.record_id];
        const groupRecIdsStr = groupRecIdsArr.join("|");
        const metaPayload = encodeURIComponent(JSON.stringify({
          scope: "replicate_group",
          triage_scope: "group",
          resource_name: r.resource_name,
          record_id: r.record_id,
          dixon_candidate_id: r.record_id,
          record_ids: groupRecIdsStr,
          all_group_record_ids: groupRecIdsStr,
          n: groupRecIdsArr.length,
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
          target_label: `${r.prepared_sample} (${r.experiment})`
        }));

        return `
          <tr class="border-t border-[var(--border)] hover:bg-[var(--background)] text-xs align-top">
            <td class="py-2 px-2.5 font-mono font-semibold"><div class="flex items-center gap-1"><button type="button" onclick="window.auditPage2PointOrGroup('${metaPayload}')" title="Click to select Entire Replicate Group (default) or Single Point Only (${r.record_id})" class="hover:text-[var(--primary)] underline decoration-dotted">⚑ ${r.record_id}</button></div></td>
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
            <td class="py-2 px-2.5 min-w-[250px] space-y-1">
              <select onchange="handleDecisionChange('${safeKeyAttr}', this.value, '${metaPayload}')" class="w-full rounded px-1.5 py-1 text-[11px] font-semibold border border-[var(--border)]">
                ${DECISION_OPTIONS.map(o => `<option value="${o.value}" ${dEntry.decision === o.value ? 'selected' : ''}>${o.label}</option>`).join("")}
              </select>
              <input type="text" value="${(dEntry.note || '').replace(/"/g, '&quot;')}" onchange="handleDecisionNote('${safeKeyAttr}', this.value, '${metaPayload}')" placeholder="Reviewer note..." class="w-full rounded px-1.5 py-1 text-[11px] border border-[var(--border)] font-mono" />
              <div class="flex items-center gap-1">
                <input type="email" value="${(dEntry.assigned_to_email || '').replace(/"/g, '&quot;')}" onchange="handleDecisionAssignee('${safeKeyAttr}', this.value, '${metaPayload}')" placeholder="Assign to email..." class="flex-1 rounded px-1.5 py-0.5 text-[10px] border border-[var(--border)] font-mono" />
                <button type="button" onclick="window.auditPage2PointOrGroup('${metaPayload}')" title="Open Audit Finding Modal (Entire Replicate Group default vs Single Point Only)" class="px-1.5 py-0.5 rounded text-[10px] font-bold badge-warn hover:opacity-90">⚑ Audit</button>
                <button type="button" onclick="approveAndSyncDecision('${safeKeyAttr}', '${metaPayload}')" class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90">⚡ Sync</button>
              </div>
            </td>
          </tr>
        `;
      }).join("");

      return `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm space-y-3.5">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 class="text-base font-bold text-[var(--foreground)]">Complete ${state.resource.toUpperCase()} Record Explorer (${flagFiltered.length} matching records)</h2>
              <p class="text-xs text-[var(--muted-foreground)]">Includes Collection Date, GEOID, Sample Prep/Run Date, Statistical Snapshot status, and per-record Analyst QC Review decisions &amp; email task assignment.</p>
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
                  <th class="py-2 px-2.5 text-center">Statistical Snapshot</th>
                  <th class="py-2 px-2.5 text-center">QC</th>
                  <th class="py-2 px-2.5">Bench Note</th>
                  <th class="py-2 px-2.5">⚖️ Analyst Decision &amp; Assignee</th>
                </tr>
              </thead>
              <tbody>${rowsHtml}</tbody>
            </table>
          </div>
        </div>
      `;
    }

    function getFilteredQueueEntries() {
      const allEntries = Object.values(DECISIONS_STORE);
      const currentAnalystEmail = (window.BioCirvQcClient && window.BioCirvQcClient.getUser() && window.BioCirvQcClient.getUser().email)
        ? String(window.BioCirvQcClient.getUser().email).toLowerCase()
        : "";
      return allEntries.filter(e => {
        if (state.queueResourceScope === "current" && e.resource_name && e.resource_name !== state.resource) {
          return false;
        }
        const entryStatus = e.status || (e.synced_to_gsheet ? "approved" : "open");
        if (state.queueStatusFilter !== "all" && entryStatus !== state.queueStatusFilter) {
          return false;
        }
        const entryScope = e.scope || (e.triage_scope === "single" ? "single_record" : "replicate_group");
        if (state.queueScopeFilter !== "all" && entryScope !== state.queueScopeFilter) {
          return false;
        }
        const assignee = String(e.assigned_to_email || "").trim().toLowerCase();
        if (state.queueAssigneeFilter === "mine") {
          if (!currentAnalystEmail || assignee !== currentAnalystEmail) return false;
        } else if (state.queueAssigneeFilter === "unassigned") {
          if (assignee !== "") return false;
        } else if (state.queueAssigneeFilter === "custom_email") {
          const qEmail = String(state.queueAssigneeEmail || "").trim().toLowerCase();
          if (qEmail && !assignee.includes(qEmail)) return false;
        }
        return true;
      });
    }

    function renderReviewQueueSubtab() {
      const allEntries = Object.values(DECISIONS_STORE);
      const filteredEntries = getFilteredQueueEntries();
      const currentAnalystEmail = (window.BioCirvQcClient && window.BioCirvQcClient.getUser() && window.BioCirvQcClient.getUser().email)
        ? String(window.BioCirvQcClient.getUser().email)
        : "";
      const openCnt = allEntries.filter(e => (e.status || "open") === "open").length;
      const approvedCnt = allEntries.filter(e => e.status === "approved" || e.synced_to_gsheet).length;
      const adhocCnt = allEntries.filter(e => e.scope === "ad_hoc_finding").length;
      const assignedToMeCnt = currentAnalystEmail
        ? allEntries.filter(e => String(e.assigned_to_email || "").toLowerCase() === currentAnalystEmail.toLowerCase()).length
        : 0;

      const rowsHtml = filteredEntries.length === 0
        ? `
          <div class="p-8 text-center text-xs text-[var(--muted-foreground)] bg-[var(--background)] rounded-xl border border-[var(--border)]">
            No review queue entries match the current filters. Submit an ad-hoc finding with <strong>+ Submit Audit Finding</strong> or record a decision on Subtab 1 or Subtab 4.
          </div>
        `
        : `
          <div class="overflow-x-auto max-h-[600px] overflow-y-auto border border-[var(--border)] rounded-xl">
            <table class="w-full text-left border-collapse text-xs">
              <thead class="sticky top-0 bg-[var(--card)] shadow-sm z-10 border-b border-[var(--border)] text-[11px] text-[var(--muted-foreground)]">
                <tr>
                  <th class="py-2.5 px-3">Status &amp; Sync</th>
                  <th class="py-2.5 px-3">Scope &amp; Source</th>
                  <th class="py-2.5 px-3">Resource &amp; Target</th>
                  <th class="py-2.5 px-3">Domain &amp; Parameter</th>
                  <th class="py-2.5 px-3 min-w-[200px]">Assigned To (Email)</th>
                  <th class="py-2.5 px-3 min-w-[250px]">Decision &amp; Rationale Note</th>
                  <th class="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${filteredEntries.map(e => {
                  const safeKeyAttr = (e.key || "").replace(/"/g, "&quot;").replace(/'/g, "\\'");
                  const entryStatus = e.status || (e.synced_to_gsheet ? "approved" : "open");
                  const statusBadge = entryStatus === "approved"
                    ? `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold badge-pass">✓ Approved &amp; Synced</span>`
                    : (entryStatus === "reverted"
                      ? `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold badge-info">↩ Reverted</span>`
                      : `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold badge-warn">⏳ Open / Needs Triage</span>`);
                  const scopeLabel = e.scope === "ad_hoc_finding"
                    ? `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono badge-warn">Ad-Hoc Finding</span>`
                    : ((e.triage_scope === "single" || e.scope === "single_record")
                      ? `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono badge-info">Single Record</span>`
                      : `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-[var(--secondary)] text-[var(--foreground)] border border-[var(--border)]">Whole Group</span>`);
                  const metaPayload = encodeURIComponent(JSON.stringify(e));
                  return `
                    <tr class="border-t border-[var(--border)] hover:bg-[var(--background)] align-top">
                      <td class="py-2.5 px-3 space-y-1">
                        <div>${statusBadge}</div>
                        <div class="text-[10px] font-mono text-[var(--muted-foreground)]">${e.updated_at || ''}</div>
                        ${e.reviewer_email ? `<div class="text-[10px] font-mono text-[var(--muted-foreground)]">By: ${e.reviewer_email}</div>` : ''}
                      </td>
                      <td class="py-2.5 px-3 space-y-1">
                        <div>${scopeLabel}</div>
                        ${e.anomaly_Category ? `<div class="text-[10px] font-mono text-[var(--muted-foreground)]">${e.anomaly_Category}</div>` : ''}
                      </td>
                      <td class="py-2.5 px-3">
                        <div class="font-semibold text-[var(--foreground)]">${e.resource_name || '—'}</div>
                        <div class="font-mono text-[11px] text-[var(--primary)]">${e.target_label || e.prepared_sample || e.record_id || '—'}</div>
                        ${e.record_ids ? `<div class="font-mono text-[10px] text-[var(--muted-foreground)] truncate max-w-[180px]" title="${e.record_ids}">Recs: ${e.record_ids}</div>` : ''}
                      </td>
                      <td class="py-2.5 px-3">
                        <div class="text-[11px] font-semibold">${e.analysis_type || '—'}</div>
                        <div class="font-mono text-[11px] text-[var(--muted-foreground)]">${e.parameter || '—'}</div>
                      </td>
                      <td class="py-2.5 px-3 space-y-1 min-w-[200px]">
                        <input type="email" value="${(e.assigned_to_email || '').replace(/"/g, '&quot;')}" onchange="assignQueueEntryEmail('${safeKeyAttr}', this.value)" placeholder="Assign to email..." class="w-full rounded px-2 py-1 text-[11px] border border-[var(--border)] font-mono" />
                        ${currentAnalystEmail ? `<button type="button" onclick="assignQueueEntryEmail('${safeKeyAttr}', '${currentAnalystEmail.replace(/'/g, "\\'")}')" class="px-1.5 py-0.5 rounded text-[10px] bg-[var(--secondary)] text-[var(--primary)] border border-[var(--border)] hover:border-[var(--primary)]">👤 Assign to Me</button>` : ''}
                      </td>
                      <td class="py-2.5 px-3 space-y-1 min-w-[250px]">
                        <select onchange="handleDecisionChange('${safeKeyAttr}', this.value, '${metaPayload}')" class="w-full rounded px-2 py-1 text-xs font-semibold border border-[var(--border)]">
                          ${DECISION_OPTIONS.map(o => `<option value="${o.value}" ${e.decision === o.value ? 'selected' : ''}>${o.label}</option>`).join("")}
                        </select>
                        <input type="text" value="${(e.note || '').replace(/"/g, '&quot;')}" onchange="handleDecisionNote('${safeKeyAttr}', this.value, '${metaPayload}')" placeholder="Reviewer note..." class="w-full rounded px-2 py-1 text-xs border border-[var(--border)] font-mono" />
                      </td>
                      <td class="py-2.5 px-3 text-right space-y-1 whitespace-nowrap">
                        <div>
                          <button type="button" onclick="approveAndSyncDecision('${safeKeyAttr}', '${metaPayload}')" class="px-2.5 py-1 rounded text-[11px] font-bold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90">⚡ Approve &amp; Sync</button>
                        </div>
                        <div class="flex items-center justify-end gap-1">
                          ${e.api_decision_id ? `<button type="button" onclick="revertQueueItemByKey('${safeKeyAttr}')" class="px-2 py-0.5 rounded text-[10px] font-semibold badge-info hover:opacity-80">↩ Revert</button>` : ''}
                          <button type="button" onclick="removeDecisionEntry('${safeKeyAttr}')" class="px-2 py-0.5 rounded text-[10px] font-semibold badge-fail hover:opacity-80">Remove</button>
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
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 class="text-base font-bold text-[var(--foreground)]">5. Unified Analyst Review Queue &amp; Audit Ledger (${filteredEntries.length} shown of ${allEntries.length} total)</h2>
              <p class="text-xs text-[var(--muted-foreground)]">Manage statistical outlier flags, whole-replicate-group vs. single-record flips, and ad-hoc audit findings. Assign tasks to team members by email address and approve write-backs to Google Sheets &amp; PostgreSQL.</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button type="button" onclick="openSubmitFindingModal({ resource_name: state.resource, analysis_type: (DOMAIN_DEFS.find(d => d.key === state.domain) || {}).analysisType || (state.domain === 'all' ? 'Proximate Analysis' : state.domain) })" class="px-3 py-1.5 rounded-lg text-xs font-semibold badge-warn hover:opacity-90">
                + Submit Audit Finding
              </button>
              <button type="button" onclick="syncReviewQueueWithApi()" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:border-[var(--primary)]">
                🔄 Sync with /v1/qc API
              </button>
              <button type="button" onclick="batchApproveFilteredQueue()" class="px-3 py-1.5 rounded-lg text-xs font-bold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90">
                ⚡ Batch Approve Filtered (${filteredEntries.length})
              </button>
            </div>
          </div>

          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div class="p-3 rounded-lg bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[10px] font-semibold uppercase text-[var(--muted-foreground)]">Open / Pending Triage</div>
              <div class="text-lg font-bold font-mono text-amber-500 mt-0.5">${openCnt}</div>
            </div>
            <div class="p-3 rounded-lg bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[10px] font-semibold uppercase text-[var(--muted-foreground)]">Approved &amp; GSheet Synced</div>
              <div class="text-lg font-bold font-mono text-emerald-500 mt-0.5">${approvedCnt}</div>
            </div>
            <div class="p-3 rounded-lg bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[10px] font-semibold uppercase text-[var(--muted-foreground)]">Ad-Hoc Audit Findings</div>
              <div class="text-lg font-bold font-mono text-[var(--primary)] mt-0.5">${adhocCnt}</div>
            </div>
            <div class="p-3 rounded-lg bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[10px] font-semibold uppercase text-[var(--muted-foreground)]">👤 Assigned to Me</div>
              <div class="text-lg font-bold font-mono text-[var(--foreground)] mt-0.5">${assignedToMeCnt}</div>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2.5 bg-[var(--background)] p-3 rounded-xl border border-[var(--border)] text-xs">
            <div class="flex items-center gap-1.5">
              <label class="font-semibold text-[var(--muted-foreground)]">Resource:</label>
              <select onchange="setQueueFilter('queueResourceScope', this.value)" class="rounded px-2 py-1 text-xs border border-[var(--border)] font-semibold">
                <option value="all" ${state.queueResourceScope === 'all' ? 'selected' : ''}>All Resources (${allEntries.length})</option>
                <option value="current" ${state.queueResourceScope === 'current' ? 'selected' : ''}>Current Resource: ${state.resource.toUpperCase()}</option>
              </select>
            </div>
            <div class="flex items-center gap-1.5">
              <label class="font-semibold text-[var(--muted-foreground)]">Status:</label>
              <select onchange="setQueueFilter('queueStatusFilter', this.value)" class="rounded px-2 py-1 text-xs border border-[var(--border)] font-semibold">
                <option value="all" ${state.queueStatusFilter === 'all' ? 'selected' : ''}>All Statuses</option>
                <option value="open" ${state.queueStatusFilter === 'open' ? 'selected' : ''}>⏳ Open / Needs Triage</option>
                <option value="approved" ${state.queueStatusFilter === 'approved' ? 'selected' : ''}>✓ Approved &amp; Synced</option>
                <option value="reverted" ${state.queueStatusFilter === 'reverted' ? 'selected' : ''}>↩ Reverted</option>
              </select>
            </div>
            <div class="flex items-center gap-1.5">
              <label class="font-semibold text-[var(--muted-foreground)]">Scope:</label>
              <select onchange="setQueueFilter('queueScopeFilter', this.value)" class="rounded px-2 py-1 text-xs border border-[var(--border)] font-semibold">
                <option value="all" ${state.queueScopeFilter === 'all' ? 'selected' : ''}>All Scopes</option>
                <option value="ad_hoc_finding" ${state.queueScopeFilter === 'ad_hoc_finding' ? 'selected' : ''}>Ad-Hoc Findings</option>
                <option value="replicate_group" ${state.queueScopeFilter === 'replicate_group' ? 'selected' : ''}>Whole Replicate Group</option>
                <option value="single_record" ${state.queueScopeFilter === 'single_record' ? 'selected' : ''}>Single Record</option>
              </select>
            </div>
            <div class="flex items-center gap-1.5">
              <label class="font-semibold text-[var(--muted-foreground)]">Assigned Email:</label>
              <select onchange="setQueueFilter('queueAssigneeFilter', this.value)" class="rounded px-2 py-1 text-xs border border-[var(--border)] font-semibold">
                <option value="all" ${state.queueAssigneeFilter === 'all' ? 'selected' : ''}>All Assignees</option>
                <option value="mine" ${state.queueAssigneeFilter === 'mine' ? 'selected' : ''}>👤 Assigned to Me (${currentAnalystEmail || 'Sign In'})</option>
                <option value="unassigned" ${state.queueAssigneeFilter === 'unassigned' ? 'selected' : ''}>Unassigned Only</option>
                <option value="custom_email" ${state.queueAssigneeFilter === 'custom_email' ? 'selected' : ''}>Filter by Email Address...</option>
              </select>
              ${state.queueAssigneeFilter === 'custom_email' ? `
                <input type="email" value="${(state.queueAssigneeEmail || '').replace(/"/g, '&quot;')}" oninput="setQueueFilter('queueAssigneeEmail', this.value)" placeholder="Type email..." class="rounded px-2 py-1 text-xs border border-[var(--border)] font-mono" />
              ` : ''}
            </div>
          </div>

          ${rowsHtml}
        </div>
      `;
    }

    function syncUrl(opts = { push: false }) {
      try {
        const u = new URL(window.location.href);
        if (state.resource) {
          u.searchParams.set("resource", state.resource);
        } else {
          u.searchParams.delete("resource");
        }
        if (state.domain && state.domain !== "all") {
          u.searchParams.set("domain", state.domain);
        } else {
          u.searchParams.delete("domain");
        }
        if (state.subtab && state.subtab !== "outliers") {
          u.searchParams.set("subtab", state.subtab);
        } else {
          u.searchParams.delete("subtab");
        }
        if (state.portalQcMode && state.portalQcMode !== "qc_pass") {
          u.searchParams.set("portal_qc", state.portalQcMode);
        } else {
          u.searchParams.delete("portal_qc");
        }
        if (state.outlierFilterMode && state.outlierFilterMode !== "flagged") {
          u.searchParams.set("flag", state.outlierFilterMode);
        } else {
          u.searchParams.delete("flag");
        }
        if (state.search && state.search.trim()) {
          u.searchParams.set("q", state.search.trim());
        } else {
          u.searchParams.delete("q");
        }
        const stateSnapshot = {
          resource: state.resource,
          selectedResource: state.resource,
          domain: state.domain,
          selectedDomain: state.domain,
          subtab: state.subtab,
          activeSubtab: state.subtab,
          portalQcMode: state.portalQcMode,
          outliersFilter: state.outlierFilterMode,
          outliersSearch: state.search
        };
        if (opts && opts.push) {
          window.history.pushState(stateSnapshot, "", u.toString());
        } else {
          window.history.replaceState(stateSnapshot, "", u.toString());
        }
      } catch (_) {}
    }

    const SELECTION_TRAY_KEY = "biocirv_qc_selection_tray_v1";
    function loadSelectionTray() {
      try {
        const raw = localStorage.getItem(SELECTION_TRAY_KEY);
        return raw ? JSON.parse(raw) : [];
      } catch (_) {
        return [];
      }
    }
    function saveSelectionTray(items) {
      try {
        localStorage.setItem(SELECTION_TRAY_KEY, JSON.stringify(items));
      } catch (_) {}
    }
    let SELECTION_TRAY = loadSelectionTray();

    window.addSelectionToTray = function(encodedPayload) {
      let meta = {};
      try { meta = JSON.parse(decodeURIComponent(encodedPayload)); } catch (_) { return; }
      const repGroupKey = window.normalizeReplicateGroupKey
        ? window.normalizeReplicateGroupKey(meta, meta.resource_name || state.resource)
        : (meta.replicate_group_key || "");
      const itemKey = `${repGroupKey || `${meta.resource_name || state.resource}||${meta.analysis_type || ''}||${meta.prepared_sample || ''}||${meta.experiment || ''}||${meta.parameter || ''}`}||${meta.record_id || ''}`;
      const existingIdx = SELECTION_TRAY.findIndex(x => x.tray_key === itemKey);
      const item = {
        tray_key: itemKey,
        replicate_group_key: repGroupKey,
        resource_name: meta.resource_name || state.resource,
        analysis_type: meta.analysis_type || "",
        prepared_sample: meta.prepared_sample || "",
        prep_method: meta.prep_method || meta.group_context_label || "",
        experiment: meta.experiment || "",
        parameter: meta.parameter || "",
        record_id: meta.record_id || meta.dixon_candidate_id || "",
        all_group_record_ids: meta.all_group_record_ids || meta.record_ids || meta.record_id || "",
        triage_scope: meta.triage_scope === "single" ? "single" : "group",
        scope: meta.triage_scope === "single" ? "single_record" : "replicate_group",
        record_ids: meta.triage_scope === "single"
          ? (meta.record_id || meta.dixon_candidate_id || "")
          : (meta.all_group_record_ids || meta.record_ids || meta.record_id || ""),
        note: meta.note || ""
      };
      if (existingIdx >= 0) {
        SELECTION_TRAY[existingIdx] = item;
      } else {
        SELECTION_TRAY.push(item);
      }
      saveSelectionTray(SELECTION_TRAY);
      if (window.showQcToast) {
        window.showQcToast(`Staged ${item.prepared_sample || item.record_id} (${item.triage_scope === 'group' ? 'Entire Replicate Group' : 'Single Point Only'}) for Audit Workbench`, "info");
      }
    };

    window.toggleTrayItemScope = function(idx, scopeVal) {
      const item = SELECTION_TRAY[idx];
      if (!item) return;
      item.triage_scope = scopeVal === "single" ? "single" : "group";
      item.scope = item.triage_scope === "single" ? "single_record" : "replicate_group";
      item.record_ids = item.triage_scope === "single"
        ? (item.record_id || String(item.all_group_record_ids || "").split("|")[0] || "")
        : (item.all_group_record_ids || item.record_id || "");
      saveSelectionTray(SELECTION_TRAY);
    };

    window.removeTrayItem = function(idx) {
      SELECTION_TRAY.splice(idx, 1);
      saveSelectionTray(SELECTION_TRAY);
    };

    window.clearSelectionTray = function() {
      SELECTION_TRAY = [];
      saveSelectionTray(SELECTION_TRAY);
    };

    window.sendSelectionTrayToWorkbench = async function(defaultDecision) {
      if (!window.BioCirvQcClient) return;
      let sourceItems = SELECTION_TRAY;
      if (!sourceItems.length) {
        const decisionEntries = Object.values(DECISIONS_STORE || {});
        if (decisionEntries.length) {
          sourceItems = decisionEntries;
        } else {
          window.openReviewQueueSubtab();
          return;
        }
      }
      const items = sourceItems.map(it => ({
        scope: it.scope || (it.triage_scope === "single" ? "single_record" : "replicate_group"),
        replicate_group_key: it.replicate_group_key || (window.normalizeReplicateGroupKey ? window.normalizeReplicateGroupKey(it, it.resource_name || state.resource) : ""),
        resource_name: it.resource_name || state.resource,
        analysis_type: it.analysis_type || "",
        prepared_sample_name: it.prepared_sample || it.prepared_sample_name || "",
        prep_method: it.prep_method || "",
        experiment_name: it.experiment || it.experiment_name || "",
        parameter_name: it.parameter || it.parameter_name || "",
        record_id: it.triage_scope === "single" ? (it.record_id || "") : "",
        target_record_ids: String(it.record_ids || it.all_group_record_ids || it.record_id || "").split(/[|,\\s]+/).map(s => s.trim()).filter(Boolean),
        decision: it.decision || defaultDecision || "pending",
        rationale_note: it.note || "Exported from Page 2 to Audit Workbench"
      }));
      await window.BioCirvQcClient.exportTrayToWorkbench(items, defaultDecision || "pending", "Exported from Page 2 to Audit Workbench");
      await window.syncReviewQueueWithApi();
    };

    function render(opts = { push: false }) {
      renderDomainPills();
      renderHeaderAndKpis();
      renderDecisionBanner();
      const container = document.getElementById("qc-content");
      if (state.subtab === "outliers") container.innerHTML = renderOutliersSubtab();
      else if (state.subtab === "rsd") container.innerHTML = renderRsdSubtab();
      else if (state.subtab === "notes") container.innerHTML = renderNotesSubtab();
      else if (state.subtab === "explorer") container.innerHTML = renderExplorerSubtab();
      else if (state.subtab === "review_queue") container.innerHTML = renderReviewQueueSubtab();
      syncUrl(opts);
    }

    window.openReviewQueueSubtab = function() {
      state.subtab = "review_queue";
      render({ push: true });
    };

    window.setQueueFilter = function(field, val) {
      state[field] = val;
      render();
    };

    window.handleDecisionScope = function(key, triageScopeVal, encodedMeta) {
      let meta = {};
      try { meta = JSON.parse(decodeURIComponent(encodedMeta)); } catch (_) {}
      const nextScope = triageScopeVal === "single" ? "single_record" : "replicate_group";
      const nextRecIds = triageScopeVal === "single"
        ? (meta.dixon_candidate_id || meta.record_id || "")
        : (meta.all_group_record_ids || meta.record_ids || "");
      upsertDecisionEntry(key, {
        triage_scope: triageScopeVal,
        scope: nextScope,
        record_id: triageScopeVal === "single" ? nextRecIds : "",
        record_ids: nextRecIds
      }, meta);
      render();
    };

    window.handleDecisionAssignee = function(key, emailVal, encodedMeta) {
      let meta = {};
      try { meta = JSON.parse(decodeURIComponent(encodedMeta)); } catch (_) {}
      const cur = getDecisionEntry(key);
      const cleanEmail = (emailVal || "").trim();
      const nextDecision = cur.decision || "pending";
      upsertDecisionEntry(key, {
        decision: nextDecision,
        assigned_to_email: cleanEmail
      }, meta);
      const updated = getDecisionEntry(key);
      if (window.BioCirvQcClient) {
        if (updated.api_decision_id && typeof window.BioCirvQcClient.assignDecision === "function") {
          window.BioCirvQcClient.assignDecision(updated.api_decision_id, cleanEmail);
        } else if (cleanEmail && typeof window.BioCirvQcClient.submitDecision === "function") {
          window.BioCirvQcClient.submitDecision({
            decision_key: key,
            replicate_group_key: updated.replicate_group_key || meta.replicate_group_key || key.replace(/^grp::/, ""),
            scope: updated.scope || "replicate_group",
            resource_name: updated.resource_name || meta.resource_name || state.resource,
            analysis_type: updated.analysis_type || meta.analysis_type || state.domain,
            parameter_name: updated.parameter || meta.parameter || "",
            prepared_sample: updated.prepared_sample || meta.prepared_sample || "",
            experiment: updated.experiment || meta.experiment || "",
            record_id: updated.record_id || meta.record_id || "",
            record_ids: updated.record_ids || meta.record_ids || "",
            decision: nextDecision === "pending" ? "accept_with_note" : nextDecision,
            note: updated.note || "",
            assigned_to_email: cleanEmail
          }).then(res => {
            if (res && res.decision && res.decision.id && DECISIONS_STORE[key]) {
              DECISIONS_STORE[key].api_decision_id = res.decision.id;
              DECISIONS_STORE[key].assigned_to_email = cleanEmail;
              saveDecisionsStore(DECISIONS_STORE);
            }
          }).catch(() => {});
        }
      }
      renderDecisionBanner();
      renderHeaderAndKpis();
    };

    window.assignQueueEntryEmail = function(key, emailVal) {
      const cur = DECISIONS_STORE[key];
      if (!cur) return;
      cur.assigned_to_email = (emailVal || "").trim();
      cur.updated_at = new Date().toISOString().slice(0, 19).replace("T", " ");
      DECISIONS_STORE[key] = cur;
      saveDecisionsStore(DECISIONS_STORE);
      if (cur.api_decision_id && window.BioCirvQcClient) {
        window.BioCirvQcClient.assignDecision(cur.api_decision_id, cur.assigned_to_email);
      }
      render();
    };

    window.approveAndSyncDecision = async function(key, encodedMeta) {
      let meta = {};
      try { meta = JSON.parse(decodeURIComponent(encodedMeta)); } catch (_) {}
      if (window.BioCirvQcClient && !window.BioCirvQcClient.hasConfirmedIdentity()) {
        window.BioCirvQcClient.ensureSignedIn(() => window.approveAndSyncDecision(key, encodedMeta));
        return;
      }
      const cur = getDecisionEntry(key);
      const merged = {
        ...meta,
        ...cur,
        key,
        decision: (!cur.decision || cur.decision === "pending") ? "exclude_qc_fail" : cur.decision,
        status: "approved",
        reviewer_email: (window.BioCirvQcClient && window.BioCirvQcClient.getUser().email) || cur.reviewer_email || "",
        updated_at: new Date().toISOString().slice(0, 19).replace("T", " ")
      };
      DECISIONS_STORE[key] = merged;
      saveDecisionsStore(DECISIONS_STORE);
      if (window.BioCirvQcClient) {
        const res = await window.BioCirvQcClient.approveDecisions([merged], true);
        if (res && res.ok) {
          const dec0 = res.data && res.data.decisions && res.data.decisions[0];
          const wbStatus = (res.data && res.data.gsheet_sync && res.data.gsheet_sync.status) || (dec0 && dec0.gsheet_writeback && dec0.gsheet_writeback.status) || "saved_local";
          merged.synced_to_gsheet = wbStatus === "synced";
          if (dec0 && dec0.id) {
            merged.api_decision_id = dec0.id;
          }
          DECISIONS_STORE[key] = merged;
          saveDecisionsStore(DECISIONS_STORE);
          if (window.showQcToast) {
            if (wbStatus === "synced") {
              window.showQcToast(`✓ Decision approved, saved to DB/CSV & synced to Google Sheets (${key})`, "success");
            } else {
              const reason = (res.data && res.data.gsheet_sync && (res.data.gsheet_sync.reason || res.data.gsheet_sync.message)) || "saved to PostgreSQL & CSV seed";
              window.showQcToast(`✓ Decision approved & saved to DB/CSV (GSheet status: ${wbStatus} — ${reason})`, "info");
            }
          }
        } else if (window.showQcToast) {
          window.showQcToast(`⚠ Saved locally in browser; API sync returned: ${(res && res.error) || "offline"}`, "warn");
        }
      }
      render();
    };

    window.revertQueueItemByKey = async function(key) {
      const cur = DECISIONS_STORE[key];
      if (!cur) return;
      if (cur.api_decision_id && window.BioCirvQcClient) {
        await window.BioCirvQcClient.revertDecision(cur.api_decision_id, "Reverted from Page 2 Review Queue");
      }
      cur.status = "reverted";
      cur.synced_to_gsheet = false;
      cur.updated_at = new Date().toISOString().slice(0, 19).replace("T", " ");
      DECISIONS_STORE[key] = cur;
      saveDecisionsStore(DECISIONS_STORE);
      if (window.showQcToast) {
        window.showQcToast(`↩ Reverted decision for ${key}`, "info");
      }
      render();
    };

    window.batchApproveFilteredQueue = async function() {
      const entries = getFilteredQueueEntries();
      if (!entries.length) return;
      if (window.BioCirvQcClient && !window.BioCirvQcClient.hasConfirmedIdentity()) {
        window.BioCirvQcClient.ensureSignedIn(() => window.batchApproveFilteredQueue());
        return;
      }
      entries.forEach(e => {
        e.status = "approved";
        if (!e.decision || e.decision === "pending") e.decision = "exclude_qc_fail";
        e.updated_at = new Date().toISOString().slice(0, 19).replace("T", " ");
        DECISIONS_STORE[e.key] = e;
      });
      saveDecisionsStore(DECISIONS_STORE);
      if (window.BioCirvQcClient) {
        const res = await window.BioCirvQcClient.approveDecisions(entries, true);
        if (window.showQcToast) {
          if (res && res.ok) {
            window.showQcToast(`✓ Batch approved ${entries.length} decision(s) & persisted to DB/CSV + GSheet sync`, "success");
          } else {
            window.showQcToast(`⚠ Batch approved ${entries.length} decision(s) locally`, "warn");
          }
        }
      }
      render();
    };

    window.syncReviewQueueWithApi = async function() {
      if (!window.BioCirvQcClient) return;
      const res = await window.BioCirvQcClient.fetchDecisions({});
      if (res && res.ok && Array.isArray(res.decisions)) {
        res.decisions.forEach(d => {
          const repGroupKey = d.replicate_group_key || (window.normalizeReplicateGroupKey ? window.normalizeReplicateGroupKey(d, d.resource_name || state.resource) : "");
          const k = d.decision_key || (d.scope === "replicate_group" && repGroupKey ? `grp::${repGroupKey}` : `api::${d.id}`);
          DECISIONS_STORE[k] = {
            ...(DECISIONS_STORE[k] || {}),
            key: k,
            replicate_group_key: repGroupKey,
            api_decision_id: d.id,
            scope: d.scope || "replicate_group",
            resource_name: d.resource_name || state.resource,
            analysis_type: d.analysis_type || "",
            prepared_sample: d.prepared_sample_name || d.prepared_sample || "",
            experiment: d.experiment_name || d.experiment || "",
            record_id: d.record_id || "",
            record_ids: Array.isArray(d.target_record_ids) ? d.target_record_ids.join("|") : (d.target_record_ids || ""),
            parameter: d.parameter_name || d.parameter || "",
            decision: d.decision || "pending",
            status: d.status || "open",
            note: d.rationale_note || d.audit_note || "",
            assigned_to_email: d.assigned_to_email || "",
            reviewer_email: d.reviewer_email || "",
            synced_to_gsheet: Boolean(d.synced_to_gsheet),
            updated_at: (d.updated_at || d.created_at || "").slice(0, 19).replace("T", " ")
          };
        });
        saveDecisionsStore(DECISIONS_STORE);
        render();
      }
    };

    window.addEventListener("biocirv-decisions-updated", () => {
      const fromStorage = loadDecisionsStore();
      Object.keys(DECISIONS_STORE || {}).forEach(k => {
        const mem = DECISIONS_STORE[k];
        if (!fromStorage[k]) {
          fromStorage[k] = mem;
        } else {
          if (mem.assigned_to_email && !fromStorage[k].assigned_to_email) {
            fromStorage[k].assigned_to_email = mem.assigned_to_email;
          }
          if (mem.api_decision_id && !fromStorage[k].api_decision_id) {
            fromStorage[k].api_decision_id = mem.api_decision_id;
          }
        }
      });
      DECISIONS_STORE = fromStorage;
      render();
    });

    window.addEventListener("biocirv-auth-changed", () => {
      render();
    });

    window.handleDecisionChange = function(key, decisionVal, encodedMeta) {
      let meta = {};
      try { meta = JSON.parse(decodeURIComponent(encodedMeta)); } catch (_) {}
      const prev = getDecisionEntry(key);
      const preservedEmail = (prev && prev.assigned_to_email) ? prev.assigned_to_email : "";
      upsertDecisionEntry(key, {
        decision: decisionVal,
        ...(preservedEmail ? { assigned_to_email: preservedEmail } : {})
      }, meta);
      const updated = getDecisionEntry(key);
      if (decisionVal && decisionVal !== "pending" && window.BioCirvQcClient && typeof window.BioCirvQcClient.submitDecision === "function") {
        window.BioCirvQcClient.submitDecision({
          api_decision_id: updated.api_decision_id || null,
          decision_key: key,
          replicate_group_key: updated.replicate_group_key || meta.replicate_group_key || key.replace(/^grp::/, ""),
          scope: updated.scope || "replicate_group",
          resource_name: updated.resource_name || meta.resource_name || state.resource,
          analysis_type: updated.analysis_type || meta.analysis_type || state.domain,
          parameter_name: updated.parameter || meta.parameter || "",
          prepared_sample: updated.prepared_sample || meta.prepared_sample || "",
          experiment: updated.experiment || meta.experiment || "",
          record_id: updated.record_id || meta.record_id || "",
          record_ids: updated.record_ids || meta.record_ids || "",
          decision: decisionVal,
          note: updated.note || "",
          assigned_to_email: updated.assigned_to_email || preservedEmail || null
        }).then(res => {
          if (res && res.decision && res.decision.id && DECISIONS_STORE[key]) {
            DECISIONS_STORE[key].api_decision_id = res.decision.id;
            if (preservedEmail && !DECISIONS_STORE[key].assigned_to_email) {
              DECISIONS_STORE[key].assigned_to_email = preservedEmail;
            }
            saveDecisionsStore(DECISIONS_STORE);
          }
        }).catch(() => {});
      }
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
        "key", "scope", "triage_scope", "status", "resource_name", "analysis_type", "prepared_sample", "field_sample",
        "collected_date", "geoid", "prep_date", "experiment", "record_id", "parameter",
        "unit", "n", "mean", "sd", "rsd_within_pct", "dixon_q", "dixon_candidate_id",
        "record_ids", "decision", "assigned_to_email", "note", "updated_at"
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
      render({ push: true });
    };

    window.setDomain = function(d) {
      const norm = d === "all" ? "all" : normalizeDomainKey(d);
      state.domain = DOMAIN_LABELS[norm] ? norm : "all";
      render({ push: true });
    };

    window.setOutlierFilterMode = function(mode) {
      state.outlierFilterMode = mode;
      render({ push: false });
    };

    window.setExplorerFlagFilter = function(mode) {
      state.explorerFlagFilter = mode;
      render({ push: false });
    };

    window.updateSearch = function(val) {
      state.search = val;
      render({ push: false });
      const inp = document.getElementById("flt-search-input");
      if (inp) {
        inp.focus();
        inp.setSelectionRange(inp.value.length, inp.value.length);
      }
    };

    window.jumpToRecord = function(recId) {
      if (state.domain !== "all") {
        const targetRec = getResourceRecords().find(r => String(r.record_id) === String(recId));
        if (targetRec && targetRec.analysis_type && normalizeDomainKey(targetRec.analysis_type) !== state.domain) {
          state.domain = "all";
        }
      }
      state.search = recId;
      state.explorerFlagFilter = "all";
      state.subtab = "explorer";
      render({ push: true });
    };

    window.inspectSampleParam = function(sampleName, paramName) {
      state.prepared_sample = sampleName || "all";
      document.getElementById("flt-prepared-sample").value = state.prepared_sample;
      state.search = paramName || "";
      state.explorerFlagFilter = "all";
      state.subtab = "explorer";
      render({ push: true });
    };

    window.auditPage2PointOrGroup = function(encodedPayload) {
      if (!window.openSubmitFindingModal) return;
      try {
        const payload = JSON.parse(decodeURIComponent(encodedPayload));
        window.openSubmitFindingModal(payload);
      } catch (_) {}
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
    const fltDateTypeEl = document.getElementById("flt-date-type");
    const fltFromDateEl = document.getElementById("flt-from-date");
    const fltToDateEl = document.getElementById("flt-to-date");
    if (fltDateTypeEl) {
      fltDateTypeEl.addEventListener("change", e => {
        state.date_type = e.target.value;
        render();
      });
    }
    if (window.initDateFilterInputs) {
      window.initDateFilterInputs("flt-from-date", "flt-to-date", "flt-date-type", "flt-date-clear", (fromVal, toVal, typeVal) => {
        state.from_date = fromVal;
        state.to_date = toVal;
        if (typeVal) state.date_type = typeVal;
        render();
      });
    } else {
      if (fltFromDateEl) {
        ["change", "input"].forEach(evt => fltFromDateEl.addEventListener(evt, e => {
          state.from_date = e.target.value;
          render();
        }));
      }
      if (fltToDateEl) {
        ["change", "input"].forEach(evt => fltToDateEl.addEventListener(evt, e => {
          state.to_date = e.target.value;
          render();
        }));
      }
    }
    document.getElementById("chk-suppress-trace").addEventListener("change", e => {
      state.suppressTraceFlags = e.target.checked;
      render({ push: false });
    });
    const sidebarFlagSelectEl = document.getElementById("flt-sidebar-flag-type");
    if (sidebarFlagSelectEl) {
      sidebarFlagSelectEl.addEventListener("change", e => {
        state.outlierFilterMode = e.target.value;
        render({ push: false });
      });
    }
    const sidebarBlindChkEl = document.getElementById("chk-sidebar-blind-mode");
    if (sidebarBlindChkEl) {
      sidebarBlindChkEl.checked = Boolean(state.anonymizeAnalyst);
      sidebarBlindChkEl.addEventListener("change", e => {
        state.anonymizeAnalyst = Boolean(e.target.checked);
        document.body.classList.toggle("blind-analyst-mode", state.anonymizeAnalyst);
        render({ push: false });
      });
    }
    const sidebarSearchInputEl = document.getElementById("sidebar-search-input");
    if (sidebarSearchInputEl) {
      sidebarSearchInputEl.value = state.search || "";
      sidebarSearchInputEl.addEventListener("input", e => {
        state.search = e.target.value;
        render({ push: false });
      });
    }
    document.getElementById("btn-reset-filters").addEventListener("click", () => {
      state.domain = "all";
      state.portalQcMode = "qc_pass";
      document.getElementById("flt-portal-qc").value = "qc_pass";
      state.prepared_sample = "all";
      state.experiment = "all";
      state.date_type = "any";
      state.from_date = "";
      state.to_date = "";
      if (fltDateTypeEl) fltDateTypeEl.value = "any";
      if (fltFromDateEl) fltFromDateEl.value = "";
      if (fltToDateEl) fltToDateEl.value = "";
      const fltDateClearEl = document.getElementById("flt-date-clear");
      if (fltDateClearEl) fltDateClearEl.classList.add("hidden");
      state.search = "";
      if (sidebarSearchInputEl) sidebarSearchInputEl.value = "";
      state.outlierFilterMode = "flagged";
      if (sidebarFlagSelectEl) sidebarFlagSelectEl.value = "flagged";
      state.explorerFlagFilter = "all";
      initFiltersForResource();
      render({ push: false });
    });
    document.getElementById("btn-anon-analyst").addEventListener("click", () => {
      state.anonymizeAnalyst = !state.anonymizeAnalyst;
      document.body.classList.toggle("blind-analyst-mode", state.anonymizeAnalyst);
      if (sidebarBlindChkEl) sidebarBlindChkEl.checked = state.anonymizeAnalyst;
      render({ push: false });
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
        render({ push: true });
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

__SHARED_SLICE_AND_BUG_MODALS_JS__
    const _origApplyOverlayP2 = window.applyLiveQcDecisionsOverlay;
    window.applyLiveQcDecisionsOverlay = function(decisions) {
      const count = _origApplyOverlayP2 ? _origApplyOverlayP2(decisions) : 0;
      const byRecord = new Map();
      (decisions || []).forEach(d => {
        if (!d || d.status === "reverted") return;
        const decVal = String(d.decision || "").toLowerCase();
        if (!decVal || decVal === "pending") return;
        const nextQc = (decVal === "exclude_qc_fail" || decVal === "fail") ? "fail" : (decVal === "keep" || decVal === "pass" ? "pass" : null);
        if (!nextQc) return;
        const targets = [];
        if (d.record_id) targets.push(String(d.record_id).trim());
        if (Array.isArray(d.target_record_ids)) d.target_record_ids.forEach(t => targets.push(String(t).trim()));
        targets.filter(Boolean).forEach(rid => byRecord.set(rid, { qc: nextQc, decision: decVal, reviewer: d.reviewer_email || "" }));
      });
      if (byRecord.size > 0) {
        Object.values(RECORDS_BY_RESOURCE || {}).forEach(recs => {
          (recs || []).forEach(r => {
            const ov = byRecord.get(String(r.record_id));
            if (ov) {
              r.qc_status = ov.qc;
              r.portal_compliant = ov.qc === "pass";
              r.live_qc_decision = ov.decision;
            }
          });
        });
      }
      render();
      return count;
    };
    initSliceAndBugModals("Page 2 — Statistical QC & Lab Notes Audit");
    initResourceSwitcher();
    initFiltersForResource();
    window.addEventListener("popstate", () => {
      const p = new URLSearchParams(window.location.search);
      const resParam = (p.get("resource") || p.get("res") || DEFAULT_RESOURCE).toLowerCase();
      const matchedRes = ACTIVE_RESOURCES.find(r => r.toLowerCase() === resParam) || ACTIVE_RESOURCES[0];
      const resourceChanged = matchedRes !== state.resource;
      state.resource = matchedRes;
      const domParam = p.get("domain") || p.get("type") || "all";
      const normDom = domParam === "all" ? "all" : normalizeDomainKey(domParam);
      state.domain = DOMAIN_LABELS[normDom] ? normDom : "all";
      const subParam = p.get("subtab") || "outliers";
      state.subtab = ["outliers", "rsd", "notes", "explorer", "review_queue"].includes(subParam) ? subParam : "outliers";
      const pqcParam = p.get("portal_qc") || "qc_pass";
      state.portalQcMode = ["all", "portal_compliant", "qc_pass", "qc_fail"].includes(pqcParam) ? pqcParam : "qc_pass";
      state.outlierFilterMode = p.get("flag") || "flagged";
      state.search = p.get("q") || "";
      const pqcEl = document.getElementById("flt-portal-qc");
      if (pqcEl) pqcEl.value = state.portalQcMode;
      const searchEl = document.getElementById("sidebar-search-input");
      if (searchEl) searchEl.value = state.search;
      initResourceSwitcher();
      if (resourceChanged) {
        state.prepared_sample = "all";
        state.experiment = "all";
        initFiltersForResource();
      }
      render({ push: false });
    });
    render();
    window.syncReviewQueueWithApi();
    if (window.refreshLiveQcOverlay) {
      window.refreshLiveQcOverlay(false);
    }
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
        .replace("__SHARED_SLICE_AND_BUG_MODALS_HTML__", SHARED_SLICE_AND_BUG_MODALS_HTML)
        .replace("__SHARED_SLICE_AND_BUG_MODALS_JS__", SHARED_SLICE_AND_BUG_MODALS_JS)
    )


def build_collaborator_slice_html(
    raw_payload: dict[str, Any],
    insights_sidecar: dict[str, Any],
    resource_name: str | Sequence[str] | None = None,
    qc_statuses: Sequence[str] | str = ("pass",),
    exclude_analyst: bool = True,
    *,
    resources: Sequence[str] | str | None = None,
    prepared_samples: Sequence[str] | str | None = None,
    field_samples: Sequence[str] | str | None = None,
    parameters: Sequence[str] | str | None = None,
    methods: Sequence[str] | str | None = None,
    slice_pages: Sequence[str] | str | None = None,
    date_type: str = "any",
    from_date: str | None = None,
    to_date: str | None = None,
) -> str:
    """Build a standalone, leak-free single- or multi-resource HTML slice for external collaborators.

    Defaults to `qc_pass = pass` records only, masks analyst emails when `exclude_analyst=True`,
    preserves anonymous `provider` codenames as-is, and physically removes all non-selected resources'
    rows, dictionaries, and sample metadata from the embedded JSON payload.
    """
    target_resources = resources if resources is not None else resource_name
    bundle = prepare_dashboard_payload(
        raw_payload,
        insights_sidecar,
        single_resource=resource_name if isinstance(resource_name, str) and resources is None else None,
        resources=target_resources,
        exclude_analyst=exclude_analyst,
        slice_qc_status=qc_statuses,
        collaborator_slice_mode=True,
        prepared_samples=prepared_samples,
        field_samples=field_samples,
        parameters=parameters,
        methods=methods,
        slice_pages=slice_pages,
        date_type=date_type,
        from_date=from_date,
        to_date=to_date,
    )
    slice_res_list = bundle.get("slice_resources") or []
    if slice_res_list:
        default_res = str(slice_res_list[0]).strip().lower()
    elif isinstance(resource_name, str) and resource_name.strip():
        default_res = resource_name.strip().lower()
    else:
        dict_res = bundle.get("dicts", {}).get("resource_name") or []
        default_res = str(dict_res[0]).strip().lower() if dict_res else "resource"
    return build_analysis_dashboard_html(
        bundle,
        default_resource=default_res,
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
        "--write-sidecar",
        action="store_true",
        help="Persist computed sidecar JSON to --sidecar path when missing.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional explicit output file path for Page 1 HTML (Page 2 written alongside it).",
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
        "--slice-resource",
        type=str,
        default=None,
        help="Resource name to export as a standalone single-resource collaborator .html slice.",
    )
    parser.add_argument(
        "--slice-qc-status",
        type=str,
        default=None,
        help=(
            "Comma-separated QC statuses to include in the slice export "
            "(defaults to 'pass' for --slice-resource; e.g. 'pass', 'pass,fail', 'pass,fail,unscored', or 'all')."
        ),
    )
    parser.add_argument(
        "--slice-output",
        type=Path,
        default=None,
        help="Optional explicit output file path for --slice-resource HTML export.",
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
        if args.write_sidecar:
            args.sidecar.parent.mkdir(parents=True, exist_ok=True)
            args.sidecar.write_text(json.dumps(insights_sidecar, indent=2), encoding="utf-8")

    out_dir = args.output.parent if args.output is not None else args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.slice_resource:
        qc_spec = args.slice_qc_status if args.slice_qc_status is not None else "pass"
        slice_html = build_collaborator_slice_html(
            raw_payload,
            insights_sidecar,
            resource_name=args.slice_resource,
            qc_statuses=qc_spec,
            exclude_analyst=True,
        )
        slug = args.slice_resource.strip().lower().replace(" ", "_")
        slice_file = args.slice_output or args.output or (out_dir / f"{slug}_collaborator_slice.html")
        slice_file.parent.mkdir(parents=True, exist_ok=True)
        slice_file.write_text(slice_html, encoding="utf-8")
        print(f"Wrote Collaborator Slice HTML ({args.slice_resource}, qc={qc_spec}): {slice_file} ({slice_file.stat().st_size / 1024:.1f} KB)")
        return

    bundle = prepare_dashboard_payload(
        raw_payload,
        insights_sidecar,
        single_resource=args.single_resource,
        exclude_analyst=args.exclude_analyst,
        slice_qc_status=args.slice_qc_status,
    )

    if args.single_resource:
        slug = args.single_resource.strip().lower().replace(" ", "_")
        char_name = args.output.name if args.output is not None else f"{slug}_analysis_dashboard.html"
        qc_name = f"{slug}_qc_outlier_dashboard.html"
    else:
        char_name = args.output.name if args.output is not None else "resource_analysis_dashboard.html"
        qc_name = "resource_qc_outlier_dashboard.html"

    char_html = build_analysis_dashboard_html(bundle, qc_page_filename=qc_name)
    qc_html = build_qc_outlier_dashboard_html(bundle, char_page_filename=char_name)

    char_file = args.output if args.output is not None else (out_dir / char_name)
    qc_file = out_dir / qc_name
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
