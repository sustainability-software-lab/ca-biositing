#!/usr/bin/env python3
"""Product 4: Self-contained Resource QC & Data Audit Workbench generator.

Builds ``exports/plots/metadata/resource_audit_workbench.html`` from a compact
dashboard data snapshot (``--from-snapshot``). The generated HTML application
provides:

1. Queue & Task Assignment Bar with 1-click tabs:
   - ``👤 Assigned to Me (k)``
   - ``Unassigned``
   - ``All Open``
   - ``In Review / Retest``
   - ``Resolved (Pending GSheet Sync)`` + Admin-only ``📤 Sync All Pending to Google Sheets (m)``
   - ``Synced to GSheet``
2. Facet filters (Resource, Analysis Domain, Parameter, Flag Type, Assigned Analyst).
3. Side-by-Side Contextual Workspace Drawer:
   - Left Pane: Interactive multi-view diagnostic plot viewer with ``Plot Style``,
     ``Group / Color By``, and ``Inspect Co-Measured Parameter on Same Sample``.
   - Right Pane: Granular replicate breakdown (``Entire Replicate Group`` vs
     ``Specific Single Replicate(s)``), structured rationale chips, required
     free-text review note, Stage 1 DB commit (``POST /v1/qc/decisions``),
     ``BroadcastChannel("biocirv_qc_decisions")`` cross-tab notification, and
     complete 4-step Audit Provenance & Timestamp Timeline with Admin-only
     Stage 2 Google Sheets write-back (``POST /v1/qc/decisions/{id}/sync-gsheet``).
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
from typing import Any

DEFAULT_SNAPSHOT_PATH = Path(
    "exports/plots/metadata/dashboard_data_snapshot.json"
)
DEFAULT_OUTPUT_PATH = Path(
    "exports/plots/metadata/resource_audit_workbench.html"
)

PROXIMATE_CLOSURE_PARAMETERS = {
    "ash",
    "ash solids",
    "volatile solids",
    "volatile matter",
    "fixed carbon",
    "moisture",
}

PROXIMATE_COMPONENT_BUCKET_MAP: dict[str, str] = {
    "moisture": "moisture",
    "ash": "ash",
    "ash solids": "ash",
    "volatile solids": "volatile_solids",
    "volatile matter": "volatile_solids",
    "fixed carbon": "fixed_carbon",
}


def proximate_component_bucket(param_name: str | None) -> str | None:
    """Map a parameter name to its canonical Data Portal proximate component bucket."""
    return PROXIMATE_COMPONENT_BUCKET_MAP.get(
        str(param_name or "").strip().lower()
    )

ANALYSIS_TABLE_MAP: dict[str, str] = {
    "Proximate Analysis": "proximate_record",
    "Ultimate Analysis": "ultimate_record",
    "Compositional Analysis": "compositional_record",
    "ICP Analysis": "icp_record",
    "Calorimetry Analysis": "calorimetry_record",
    "Fermentation": "fermentation_record",
    "Pretreatment": "pretreatment_record",
    "Gasification": "gasification_record",
    "XRD": "xrd_record",
    "XRF": "xrf_record",
}

CANONICAL_DOMAIN_SLUGS: tuple[str, ...] = (
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
)

DOMAIN_SLUG_TO_RECORD_TABLE: dict[str, str] = {
    "proximate": "proximate_record",
    "ultimate": "ultimate_record",
    "compositional": "compositional_record",
    "icp": "icp_record",
    "calorimetry": "calorimetry_record",
    "fermentation": "fermentation_record",
    "pretreatment": "pretreatment_record",
    "gasification": "gasification_record",
    "xrd": "xrd_record",
    "xrf": "xrf_record",
}

CANONICAL_DOMAIN_LOOKUP: dict[str, str] = {
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
    "gasification": "gasification",
}


def canonical_domain_slug(analysis_type: str | None) -> str:
    """Normalize an analysis domain display name or slug to its canonical 10-domain slug."""
    cleaned = str(analysis_type or "").strip().lower()
    if not cleaned:
        return "unknown"
    if cleaned.endswith("_record"):
        cleaned = cleaned[: -len("_record")].strip()
    if cleaned in CANONICAL_DOMAIN_LOOKUP:
        return CANONICAL_DOMAIN_LOOKUP[cleaned]
    for slug in CANONICAL_DOMAIN_SLUGS:
        if slug in cleaned:
            return slug
    return cleaned


def group_context_label(row: dict[str, Any]) -> str:
    """Return the context / method label defining experimental conditions for a replicate group."""
    existing = row.get("group_context_label")
    if isinstance(existing, str) and existing.strip():
        return existing.strip()
    domain_slug = canonical_domain_slug(
        row.get("analysis_type") or row.get("domain")
    )
    if domain_slug == "pretreatment":
        pt = (
            str(row.get("pt_method") or "").strip()
            or (
                str(row.get("prep_method") or "").strip()
                if "pt_method" not in row
                else ""
            )
            or "none"
        )
        eh = str(row.get("eh_method") or "").strip() or "none"
        return f"{pt} · {eh}" if eh and eh != "none" else pt
    if domain_slug == "fermentation":
        pt = str(row.get("pt_method") or "").strip()
        st = (
            str(row.get("strain") or "").strip()
            or (
                str(row.get("prep_method") or "").strip()
                if "strain" not in row
                else ""
            )
            or "no-strain"
        )
        th = row.get("time_h")
        base = f"{pt} · {st}" if pt and pt != "none" else st
        if th is not None and str(th).strip() != "":
            try:
                return f"{base} @ {float(th):g}h"
            except (TypeError, ValueError):
                return f"{base} @ {str(th).strip()}h"
        return base
    if domain_slug == "gasification":
        v = (
            str(row.get("vessel") or "").strip()
            or str(row.get("reactor_type") or "").strip()
            or str(row.get("prep_method") or "").strip()
        )
        if v and v.lower() not in {"none", "n/a", "unassigned"}:
            return v if v.lower().startswith("reactor:") else f"Reactor: {v}"
        return "Reactor: Unassigned"
    return str(row.get("prep_method") or "").strip() or "unassigned"


def compute_canonical_method_signature(row: dict[str, Any]) -> str:
    """Return the canonical domain-aware method/context signature for a measurement row."""
    return group_context_label(row)


def resolve_record_table(analysis_type_or_slug: str | None) -> str:
    """Resolve an analysis domain display name, slug, or record table name to its *_record table."""
    cleaned = str(analysis_type_or_slug or "").strip()
    if cleaned in ANALYSIS_TABLE_MAP:
        return ANALYSIS_TABLE_MAP[cleaned]
    lowered = cleaned.lower()
    if lowered in DOMAIN_SLUG_TO_RECORD_TABLE.values():
        return lowered
    slug = canonical_domain_slug(cleaned)
    if slug in DOMAIN_SLUG_TO_RECORD_TABLE:
        return DOMAIN_SLUG_TO_RECORD_TABLE[slug]
    for label, table_name in ANALYSIS_TABLE_MAP.items():
        prefix = label.split()[0].lower()
        if label.lower() in lowered or prefix in lowered:
            return table_name
    return "proximate_record"


def normalize_replicate_group_key(
    raw_key: str | dict[str, Any] | None = None,
    prepared_sample: str | None = None,
    analysis_type: str | None = None,
    parameter: str | None = None,
    prep_method: str | None = None,
    experiment: str | None = None,
    *,
    resource_name: str | None = None,
    parameter_name: str | None = None,
) -> str:
    """Build or normalize a canonical 6-part (or legacy 4-part) replicate_group_key."""
    if isinstance(raw_key, dict):
        if (
            isinstance(raw_key.get("replicate_group_key"), str)
            and "::" in raw_key["replicate_group_key"]
            and not raw_key.get("resource_name")
            and not raw_key.get("resource")
        ):
            return normalize_replicate_group_key(raw_key["replicate_group_key"])
        res_s = str(raw_key.get("resource_name") or raw_key.get("resource") or "").strip().lower()
        prep_s = str(raw_key.get("prepared_sample") or "").strip().lower()
        dom_s = canonical_domain_slug(raw_key.get("analysis_type") or raw_key.get("domain"))
        param_s = str(raw_key.get("parameter") or raw_key.get("parameter_name") or "").strip().lower()
        method_s = str(group_context_label(raw_key) or "").strip().lower()
        exp_s = str(raw_key.get("experiment") or "").strip().lower()
        return f"{res_s}::{prep_s}::{dom_s}::{param_s}::{method_s}::{exp_s}"

    has_component_args = any(
        val is not None
        for val in (
            prepared_sample,
            analysis_type,
            parameter,
            parameter_name,
            prep_method,
            experiment,
            resource_name,
        )
    )
    if isinstance(raw_key, str) and ("::" in raw_key or not has_component_args):
        s = raw_key.strip()
        if not s:
            return ""
        if s.lower().startswith("grp::"):
            s = s[5:].strip()
        parts = [p.strip().lower() for p in s.split("::")]
        if len(parts) >= 3:
            parts[2] = canonical_domain_slug(parts[2])
        if len(parts) == 4:
            return "::".join(parts[:4])
        if len(parts) >= 6:
            return "::".join(parts[:6])
        if len(parts) == 5:
            parts.append("")
            return "::".join(parts)
        return "::".join(parts)

    if raw_key is None and not has_component_args:
        return ""

    res_val = resource_name if resource_name is not None else raw_key
    param_val = parameter if parameter is not None else parameter_name
    res_s = str(res_val or "").strip().lower()
    prep_s = str(prepared_sample or "").strip().lower()
    dom_s = canonical_domain_slug(analysis_type)
    param_s = str(param_val or "").strip().lower()
    method_s = str(prep_method or "").strip().lower()
    exp_s = str(experiment or "").strip().lower()
    return f"{res_s}::{prep_s}::{dom_s}::{param_s}::{method_s}::{exp_s}"


def matches_replicate_group_key(
    key_a: str | None,
    key_b: str | None,
) -> bool:
    """Return True if two replicate group keys match on all 6 slots or via 4-part prefix fallback."""
    na = normalize_replicate_group_key(key_a) if key_a else ""
    nb = normalize_replicate_group_key(key_b) if key_b else ""
    if not na or not nb:
        return False
    if na == nb:
        return True
    pa = na.split("::")
    pb = nb.split("::")
    if (len(pa) == 4 or len(pb) == 4) and len(pa) >= 4 and len(pb) >= 4:
        return "::".join(pa[:4]) == "::".join(pb[:4])
    return False


def _fetch_live_resource_data() -> dict[str, Any]:
    """Import and invoke fetch_all_resource_data without permanently mutating sys.path."""
    try:
        from analysis.metadata.resource_explorer_dashboard import (
            fetch_all_resource_data,
        )
    except ImportError:
        import sys as _sys

        parent_dir = str(Path(__file__).resolve().parent)
        added = parent_dir not in _sys.path
        if added:
            _sys.path.insert(0, parent_dir)
        try:
            from resource_explorer_dashboard import (  # type: ignore[import-not-found,no-redef]
                fetch_all_resource_data,
            )
        finally:
            if added and parent_dir in _sys.path:
                _sys.path.remove(parent_dir)
    return fetch_all_resource_data()


def load_snapshot(snapshot_path: Path) -> dict[str, Any]:
    """Load a dashboard data snapshot JSON file from disk, or fetch live from PostgreSQL."""
    resolved = snapshot_path.expanduser().resolve()
    default_resolved = DEFAULT_SNAPSHOT_PATH.expanduser().resolve()
    if not resolved.exists() and (
        snapshot_path == DEFAULT_SNAPSHOT_PATH or resolved == default_resolved
    ):
        try:
            print(
                "Snapshot not found on disk; querying PostgreSQL for Product 4 QC Audit Workbench..."
            )
            live_data = _fetch_live_resource_data()
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(
                json.dumps(live_data, separators=(",", ":")),
                encoding="utf-8",
            )
            return live_data
        except Exception as exc:
            fallback_fixture = (
                Path(__file__).resolve().parents[2]
                / "tests"
                / "fixtures"
                / "minimal_dashboard_snapshot.json"
            )
            print(
                f"Warning: could not fetch live data ({exc}); falling back to {fallback_fixture}."
            )
            if fallback_fixture.exists():
                resolved = fallback_fixture
    if not resolved.exists():
        raise FileNotFoundError(f"Dashboard snapshot not found: {resolved}")
    with resolved.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or "rows" not in data:
        raise ValueError(
            f"Invalid dashboard snapshot structure in {resolved}: missing 'rows'"
        )
    return data


def _infer_record_table(analysis_type: str) -> str:
    return resolve_record_table(analysis_type)


def unpack_snapshot_records(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Decode compact dictionary-encoded rows from the snapshot into flat dicts."""
    str_cols: list[str] = list(snapshot.get("str_cols", []))
    dicts: dict[str, list[str]] = snapshot.get("dicts", {})
    rows: list[list[Any]] = snapshot.get("rows", [])

    records: list[dict[str, Any]] = []
    num_str_cols = len(str_cols)

    for raw_row in rows:
        if not isinstance(raw_row, list) or len(raw_row) < num_str_cols + 3:
            continue
        record_id = str(raw_row[0])
        decoded: dict[str, Any] = {"record_id": record_id}
        for idx, col_name in enumerate(str_cols):
            dict_idx = raw_row[idx + 1]
            col_values = dicts.get(col_name, [])
            if (
                isinstance(dict_idx, int)
                and 0 <= dict_idx < len(col_values)
            ):
                decoded[col_name] = col_values[dict_idx]
            else:
                decoded[col_name] = ""

        replicate_no = raw_row[num_str_cols + 1]
        raw_value = raw_row[num_str_cols + 2]
        exp_date = (
            raw_row[num_str_cols + 3] if len(raw_row) > num_str_cols + 3 else ""
        )
        raw_time_h = (
            raw_row[num_str_cols + 4] if len(raw_row) > num_str_cols + 4 else None
        )

        try:
            numeric_value = float(raw_value) if raw_value is not None else None
        except (TypeError, ValueError):
            numeric_value = None

        decoded["replicate_no"] = (
            int(replicate_no)
            if isinstance(replicate_no, (int, float))
            else 1
        )
        decoded["value"] = numeric_value
        decoded["exp_date"] = str(exp_date or "")
        decoded["time_h"] = raw_time_h
        decoded["parameter_name"] = decoded.get("parameter", "")
        decoded["record_table"] = resolve_record_table(
            decoded.get("analysis_type", "")
        )
        ctx_method = group_context_label(decoded)
        decoded["group_context_label"] = ctx_method
        decoded["replicate_group_key"] = normalize_replicate_group_key(
            resource_name=decoded.get("resource_name", ""),
            prepared_sample=decoded.get("prepared_sample", ""),
            analysis_type=decoded.get("analysis_type", ""),
            parameter=decoded.get("parameter", ""),
            prep_method=ctx_method,
            experiment=decoded.get("experiment", ""),
        )
        records.append(decoded)

    return records


def _compute_quantiles(values: list[float]) -> dict[str, float]:
    """Compute summary statistics and Tukey IQR fences for a numeric value list."""
    if not values:
        return {
            "count": 0,
            "mean": 0.0,
            "std": 0.0,
            "within_sd": 0.0,
            "median": 0.0,
            "q1": 0.0,
            "q3": 0.0,
            "iqr": 0.0,
            "lower_fence": 0.0,
            "upper_fence": 0.0,
            "min": 0.0,
            "max": 0.0,
            "rsd_pct": 0.0,
        }

    ordered = sorted(values)
    n = len(ordered)
    mean_val = statistics.fmean(ordered)
    std_val = statistics.stdev(ordered) if n >= 2 else 0.0
    median_val = statistics.median(ordered)

    if n >= 4:
        quartiles = statistics.quantiles(ordered, n=4, method="inclusive")
        q1, q3 = quartiles[0], quartiles[2]
    elif n >= 2:
        q1, q3 = ordered[0], ordered[-1]
    else:
        q1 = q3 = ordered[0]

    iqr = max(0.0, q3 - q1)
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    rsd_pct = (
        abs(std_val / mean_val) * 100.0
        if n >= 2 and abs(mean_val) > 1e-12
        else 0.0
    )

    rounded_std = round(std_val, 4)
    return {
        "count": n,
        "mean": round(mean_val, 4),
        "std": rounded_std,
        "within_sd": rounded_std,
        "median": round(median_val, 4),
        "q1": round(q1, 4),
        "q3": round(q3, 4),
        "iqr": round(iqr, 4),
        "lower_fence": round(lower_fence, 4),
        "upper_fence": round(upper_fence, 4),
        "min": round(ordered[0], 4),
        "max": round(ordered[-1], 4),
        "rsd_pct": round(rsd_pct, 2),
    }


def _method_stratum_key(rec: dict[str, Any]) -> tuple[str, str, str, str, str]:
    """Return method-stratified key (resource_name, analysis_type, parameter, prep_method, unit)."""
    ctx_method = rec.get("group_context_label")
    if ctx_method is None:
        ctx_method = group_context_label(rec)
    return (
        str(rec.get("resource_name", "")).strip().lower(),
        canonical_domain_slug(rec.get("analysis_type", "")),
        str(rec.get("parameter") or rec.get("parameter_name") or "").strip().lower(),
        str(ctx_method or "").strip().lower(),
        str(rec.get("unit", "")).strip().lower(),
    )


def build_workbench_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Build the normalized payload embedded into the Product 4 HTML workbench."""
    records = unpack_snapshot_records(snapshot)
    generated_utc = str(
        snapshot.get("generated_utc")
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    # 1. Group by (analysis_type, parameter) across resources & per-resource for IQR stats,
    #    and by (resource_name, analysis_type, parameter, prep_method, unit) -> prepared_sample
    #    for method-stratified between-sample SD / RSD.
    param_values_by_res: dict[str, list[float]] = defaultdict(list)
    param_values_global: dict[str, list[float]] = defaultdict(list)
    groups_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sample_params_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stratum_sample_values: dict[
        tuple[str, str, str, str, str], dict[str, list[float]]
    ] = defaultdict(lambda: defaultdict(list))

    for rec in records:
        val = rec.get("value")
        if val is None or (isinstance(val, float) and math.isnan(val)):
            continue
        fval = float(val)
        res_param_key = (
            f"{rec['resource_name']}::{rec['analysis_type']}::{rec['parameter']}"
        )
        global_param_key = f"{rec['analysis_type']}::{rec['parameter']}"
        param_values_by_res[res_param_key].append(fval)
        param_values_global[global_param_key].append(fval)
        groups_map[rec["replicate_group_key"]].append(rec)
        sample_slug = str(rec.get("prepared_sample", "")).strip().lower()
        stratum_sample_values[_method_stratum_key(rec)][sample_slug].append(fval)

    between_stats_by_stratum: dict[
        tuple[str, str, str, str, str], dict[str, Any]
    ] = {}
    for stratum_key, sample_vals_map in stratum_sample_values.items():
        sample_means = [
            statistics.fmean(svals)
            for svals in sample_vals_map.values()
            if svals
        ]
        k_groups = len(sample_means)
        if k_groups >= 2:
            mean_of_means = statistics.fmean(sample_means)
            raw_between_sd = statistics.stdev(sample_means)
            between_sd: float | None = round(raw_between_sd, 4)
            between_rsd_pct: float | None = (
                round(abs(raw_between_sd / mean_of_means) * 100.0, 2)
                if abs(mean_of_means) > 1e-12
                else 0.0
            )
        else:
            between_sd = None
            between_rsd_pct = None
        between_stats_by_stratum[stratum_key] = {
            "between_k_groups": k_groups,
            "between_sd": between_sd,
            "between_rsd_pct": between_rsd_pct,
        }

    res_param_stats: dict[str, dict[str, float]] = {
        key: _compute_quantiles(vals)
        for key, vals in param_values_by_res.items()
    }
    global_param_stats: dict[str, dict[str, float]] = {
        key: _compute_quantiles(vals)
        for key, vals in param_values_global.items()
    }

    # 2. Compute Proximate closure totals per (resource_name, experiment, prep_method) stratum
    #    using the exact Data Portal formula:
    #    COALESCE(avg_moisture, 0) + COALESCE(avg_ash, 0) + COALESCE(avg_vs, 100 - COALESCE(avg_fc, 0))
    proximate_stratum_vals: dict[
        tuple[str, str, str], dict[str, list[float]]
    ] = defaultdict(lambda: defaultdict(list))
    stratum_samples: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for rec in records:
        if canonical_domain_slug(rec.get("analysis_type", "")) != "proximate":
            continue
        if str(rec.get("qc_status") or "pass").strip().lower() == "fail":
            continue
        bucket = proximate_component_bucket(rec.get("parameter"))
        if bucket is None:
            continue
        val = rec.get("value")
        if val is None or (isinstance(val, float) and math.isnan(val)):
            continue
        stratum_key = (
            str(rec.get("resource_name", "")),
            str(rec.get("experiment") or "unassigned"),
            str(rec.get("group_context_label") or group_context_label(rec) or "unassigned"),
        )
        proximate_stratum_vals[stratum_key][bucket].append(float(val))
        stratum_samples[stratum_key].add(str(rec.get("prepared_sample", "")))

    proximate_closure_by_stratum: dict[str, dict[str, Any]] = {}
    proximate_closure_by_sample: dict[str, dict[str, Any]] = {}
    for (
        res_name,
        exp_name,
        prep_method,
    ), bucket_vals in proximate_stratum_vals.items():
        comp_map: dict[str, float] = {
            bucket: round(statistics.fmean(vals), 3)
            for bucket, vals in bucket_vals.items()
            if vals
        }
        avg_m = comp_map.get("moisture")
        avg_a = comp_map.get("ash")
        avg_vs = comp_map.get("volatile_solids")
        avg_fc = comp_map.get("fixed_carbon")
        has_closure_pair = (avg_vs is not None or avg_fc is not None) and (
            avg_m is not None or avg_a is not None
        )
        if avg_vs is not None:
            vs_or_fc = avg_vs
        elif avg_fc is not None:
            vs_or_fc = 100.0 - avg_fc
        else:
            vs_or_fc = 0.0
        total_pct = round((avg_m or 0.0) + (avg_a or 0.0) + vs_or_fc, 2)
        out_of_bounds = bool(
            has_closure_pair
            and total_pct > 0.0
            and (total_pct < 95.0 or total_pct > 105.0)
        )
        stratum_id = f"{res_name}::{exp_name}::{prep_method}"
        entry = {
            "resource_name": res_name,
            "experiment": exp_name,
            "prep_method": prep_method,
            "components": comp_map,
            "closure_sum_pct": total_pct,
            "proximate_sum_pct": total_pct,
            "out_of_bounds": out_of_bounds,
        }
        proximate_closure_by_stratum[stratum_id] = entry
        for prep_sample in sorted(
            stratum_samples[(res_name, exp_name, prep_method)]
        ):
            sample_entry = dict(entry)
            sample_entry["prepared_sample"] = prep_sample
            proximate_closure_by_sample[f"{res_name}::{prep_sample}"] = (
                sample_entry
            )

    # 3. Build replicate groups and candidate QC decisions
    replicate_groups: dict[str, dict[str, Any]] = {}
    candidate_decisions: list[dict[str, Any]] = []
    decision_counter = 1

    for group_key in sorted(groups_map.keys()):
        group_recs = sorted(
            groups_map[group_key],
            key=lambda r: (int(r.get("replicate_no", 1)), str(r.get("record_id", ""))),
        )
        first = group_recs[0]
        vals = [
            float(r["value"]) for r in group_recs if r.get("value") is not None
        ]
        group_stats = _compute_quantiles(vals)
        between_info = between_stats_by_stratum.get(
            _method_stratum_key(first),
            {
                "between_k_groups": 1,
                "between_sd": None,
                "between_rsd_pct": None,
            },
        )
        within_sd = group_stats["std"]
        between_sd = between_info["between_sd"]
        between_rsd_pct = between_info["between_rsd_pct"]
        between_k_groups = between_info["between_k_groups"]
        group_stats["between_sd"] = between_sd
        group_stats["between_rsd_pct"] = between_rsd_pct
        group_stats["between_k_groups"] = between_k_groups

        res_param_key = (
            f"{first['resource_name']}::{first['analysis_type']}::{first['parameter']}"
        )
        global_param_key = f"{first['analysis_type']}::{first['parameter']}"
        ref_stats = res_param_stats.get(res_param_key) or global_param_stats.get(
            global_param_key, group_stats
        )

        # Evaluate outlier replicates
        outlier_record_ids: list[str] = []
        analyst_flagged_ids: list[str] = []
        replicate_rows: list[dict[str, Any]] = []

        for rec in group_recs:
            val = float(rec["value"])
            qc_raw = str(rec.get("qc_status", "pass")).strip().lower()
            is_analyst_flagged = qc_raw in {
                "fail",
                "failed",
                "flagged",
                "retest",
                "rejected",
            }
            if is_analyst_flagged:
                analyst_flagged_ids.append(rec["record_id"])

            # Check IQR fence against group or resource distribution
            is_iqr_outlier = False
            if group_stats["count"] >= 4 and group_stats["iqr"] > 0:
                if (
                    val < group_stats["lower_fence"]
                    or val > group_stats["upper_fence"]
                ):
                    is_iqr_outlier = True
            if (
                not is_iqr_outlier
                and ref_stats["count"] >= 4
                and ref_stats["iqr"] > 0
            ):
                if (
                    val < ref_stats["lower_fence"]
                    or val > ref_stats["upper_fence"]
                ):
                    is_iqr_outlier = True
            if (
                not is_iqr_outlier
                and group_stats["count"] >= 3
                and group_stats["std"] > 0
                and abs(val - group_stats["median"])
                > max(2.0 * group_stats["iqr"], 1.35 * group_stats["std"])
                and group_stats["rsd_pct"] > 10.0
            ):
                is_iqr_outlier = True

            if is_iqr_outlier:
                outlier_record_ids.append(rec["record_id"])

            deviation_pct = (
                round(
                    ((val - group_stats["median"]) / group_stats["median"])
                    * 100.0,
                    2,
                )
                if abs(group_stats["median"]) > 1e-12
                else 0.0
            )
            replicate_rows.append(
                {
                    "record_id": rec["record_id"],
                    "replicate_no": rec["replicate_no"],
                    "value": val,
                    "unit": rec.get("unit", ""),
                    "qc_status": rec.get("qc_status", "pass"),
                    "qc_pass": rec.get("qc_status", "pass"),
                    "analyst": rec.get("analyst", ""),
                    "exp_date": rec.get("exp_date", ""),
                    "experiment": rec.get("experiment", ""),
                    "prep_method": rec.get("prep_method", ""),
                    "vessel": rec.get("vessel", ""),
                    "eh_method": rec.get("eh_method", ""),
                    "strain": rec.get("strain", ""),
                    "time_h": rec.get("time_h"),
                    "group_context_label": rec.get("group_context_label", ""),
                    "note": rec.get("note", ""),
                    "deviation_from_median_pct": deviation_pct,
                    "is_iqr_outlier": is_iqr_outlier,
                    "is_analyst_flagged": is_analyst_flagged,
                }
            )

        sample_closure_key = (
            f"{first.get('resource_name', '')}::{first.get('prepared_sample', '')}"
        )
        stratum_closure_key = (
            f"{first.get('resource_name', '')}::"
            f"{first.get('experiment') or 'unassigned'}::"
            f"{first.get('group_context_label') or group_context_label(first) or 'unassigned'}"
        )
        closure_info = proximate_closure_by_stratum.get(
            stratum_closure_key
        ) or proximate_closure_by_sample.get(sample_closure_key)
        is_proximate_violation = bool(
            closure_info
            and closure_info.get("out_of_bounds")
            and canonical_domain_slug(first.get("analysis_type", ""))
            == "proximate"
            and proximate_component_bucket(first.get("parameter", ""))
            is not None
        )

        flag_types: list[str] = []
        trigger_parts: list[str] = []

        if group_stats["count"] >= 2 and group_stats["rsd_pct"] > 10.0:
            flag_types.append("rsd_gt_10")
            trigger_parts.append(
                f"RSD {group_stats['rsd_pct']:.1f}% > 10% (n={group_stats['count']})"
            )
        if group_stats["count"] >= 2 and group_stats["rsd_pct"] > 20.0:
            flag_types.append("rsd_gt_20")
            trigger_parts.append(
                f"RSD {group_stats['rsd_pct']:.1f}% > 20% (n={group_stats['count']})"
            )
        if outlier_record_ids:
            flag_types.append("iqr_outlier")
            trigger_parts.append(
                f"IQR outlier ({', '.join(outlier_record_ids)})"
            )
        if is_proximate_violation and closure_info is not None:
            flag_types.append("proximate_sum")
            trigger_parts.append(
                f"Proximate sum {closure_info['closure_sum_pct']:.1f}% outside 95–105%"
            )
        if analyst_flagged_ids:
            flag_types.append("analyst_flagged")
            trigger_parts.append(
                f"Analyst flagged ({', '.join(analyst_flagged_ids)})"
            )

        lab_notes_seen: list[str] = []
        for r_item in replicate_rows:
            n_val = str(r_item.get("note") or "").strip()
            if n_val and n_val not in lab_notes_seen:
                lab_notes_seen.append(n_val)
        group_lab_note = " | ".join(lab_notes_seen)

        group_entry = {
            "replicate_group_key": group_key,
            "resource_name": first.get("resource_name", ""),
            "prepared_sample": first.get("prepared_sample", ""),
            "field_sample": first.get("field_sample", ""),
            "analysis_type": first.get("analysis_type", ""),
            "parameter_name": first.get("parameter", ""),
            "unit": first.get("unit", ""),
            "provider": first.get("provider", ""),
            "analyst": first.get("analyst", ""),
            "experiment": first.get("experiment", ""),
            "prep_method": first.get("prep_method", ""),
            "vessel": first.get("vessel", ""),
            "eh_method": first.get("eh_method", ""),
            "strain": first.get("strain", ""),
            "time_h": first.get("time_h"),
            "group_context_label": first.get("group_context_label", ""),
            "lab_lineage_note": group_lab_note,
            "exp_date": first.get("exp_date", ""),
            "record_table": first.get("record_table", "proximate_record"),
            "rsd_pct": group_stats["rsd_pct"],
            "within_sd": within_sd,
            "between_rsd_pct": between_rsd_pct,
            "between_sd": between_sd,
            "between_k_groups": between_k_groups,
            "replicate_count": group_stats["count"],
            "stats": group_stats,
            "reference_stats": ref_stats,
            "replicates": replicate_rows,
            "records": replicate_rows,
            "flag_types": flag_types,
            "proximate_closure": closure_info,
            "proximate_sum_pct": (
                closure_info["proximate_sum_pct"]
                if closure_info is not None
                and canonical_domain_slug(first.get("analysis_type", ""))
                == "proximate"
                else None
            ),
            "proximate_components": (
                closure_info["components"]
                if closure_info is not None
                and canonical_domain_slug(first.get("analysis_type", ""))
                == "proximate"
                else {}
            ),
        }
        replicate_groups[group_key] = group_entry

        sample_params_map[sample_closure_key].append(
            {
                "replicate_group_key": group_key,
                "parameter_name": first.get("parameter", ""),
                "analysis_type": first.get("analysis_type", ""),
                "unit": first.get("unit", ""),
                "mean": group_stats["mean"],
                "median": group_stats["median"],
                "rsd_pct": group_stats["rsd_pct"],
                "within_sd": within_sd,
                "between_rsd_pct": between_rsd_pct,
                "between_sd": between_sd,
                "between_k_groups": between_k_groups,
                "count": group_stats["count"],
                "flag_types": flag_types,
            }
        )

        if flag_types:
            primary_flag = flag_types[0]
            primary_record_id = (
                outlier_record_ids[0]
                if outlier_record_ids
                else (
                    analyst_flagged_ids[0]
                    if analyst_flagged_ids
                    else group_recs[0]["record_id"]
                )
            )
            all_record_ids = [r["record_id"] for r in group_recs]
            old_qc_pass = "fail" if analyst_flagged_ids else "pass"
            decision_id = f"QC-{decision_counter:04d}"
            decision_counter += 1

            candidate_decisions.append(
                {
                    "id": decision_id,
                    "decision_id": decision_id,
                    "db_id": None,
                    "replicate_group_key": group_key,
                    "record_table": first.get(
                        "record_table", "proximate_record"
                    ),
                    "record_id": primary_record_id,
                    "record_ids": all_record_ids,
                    "resource_name": first.get("resource_name", ""),
                    "prepared_sample": first.get("prepared_sample", ""),
                    "field_sample": first.get("field_sample", ""),
                    "analysis_type": first.get("analysis_type", ""),
                    "parameter_name": first.get("parameter", ""),
                    "unit": first.get("unit", ""),
                    "provider": first.get("provider", ""),
                    "analyst": first.get("analyst", ""),
                    "experiment": first.get("experiment", ""),
                    "prep_method": first.get("prep_method", ""),
                    "vessel": first.get("vessel", ""),
                    "eh_method": first.get("eh_method", ""),
                    "strain": first.get("strain", ""),
                    "time_h": first.get("time_h"),
                    "group_context_label": first.get("group_context_label", ""),
                    "lab_lineage_note": group_lab_note,
                    "source_label": "Auto-QC Screening",
                    "exp_date": first.get("exp_date", ""),
                    "flag_type": primary_flag,
                    "flag_types": flag_types,
                    "flag_trigger_value": "; ".join(trigger_parts),
                    "rsd_pct": group_stats["rsd_pct"],
                    "within_sd": within_sd,
                    "between_rsd_pct": between_rsd_pct,
                    "between_sd": between_sd,
                    "between_k_groups": between_k_groups,
                    "replicate_count": group_stats["count"],
                    "median_value": group_stats["median"],
                    "mean_value": group_stats["mean"],
                    "old_qc_pass": old_qc_pass,
                    "new_qc_pass": old_qc_pass,
                    "decision_status": "open",
                    "decision_action": "open",
                    "scope_mode": "group",
                    "rationale_chips": [],
                    "review_note": "",
                    "assigned_to_email": None,
                    "submitted_by_email": "auto-qc-engine@biocirv.org",
                    "created_at": generated_utc,
                    "submitted_at": generated_utc,
                    "resolved_by_email": None,
                    "resolved_at": None,
                    "synced_to_gsheet": False,
                    "sync_error": None,
                    "gsheet_synced_at": None,
                    "gsheet_synced_by_email": None,
                }
            )

    resources_list = sorted(
        {str(r.get("resource_name", "")) for r in records if r.get("resource_name")}
    )
    analysis_types_list = sorted(
        {str(r.get("analysis_type", "")) for r in records if r.get("analysis_type")}
    )
    parameters_list = sorted(
        {str(r.get("parameter", "")) for r in records if r.get("parameter")}
    )
    analysts_list = sorted(
        {str(r.get("analyst", "")) for r in records if r.get("analyst")}
    )

    return {
        "generated_utc": generated_utc,
        "total_records": len(records),
        "total_replicate_groups": len(replicate_groups),
        "total_flagged_groups": len(candidate_decisions),
        "facets": {
            "resources": resources_list,
            "analysis_types": analysis_types_list,
            "parameters": parameters_list,
            "flag_types": [
                "rsd_gt_10",
                "rsd_gt_20",
                "iqr_outlier",
                "proximate_sum",
                "visualizer_flagged",
                "stat_snapshot_flagged",
                "analyst_flagged",
            ],
            "analysts": analysts_list,
        },
        "decisions": candidate_decisions,
        "replicate_groups": replicate_groups,
        "co_measured_by_sample": dict(sample_params_map),
        "proximate_closure_by_stratum": proximate_closure_by_stratum,
        "proximate_closure_by_sample": proximate_closure_by_sample,
    }


def render_workbench_html(payload: dict[str, Any]) -> str:
    """Render the self-contained HTML5 + JS application for Product 4."""
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    generated_utc = payload.get("generated_utc", "")
    total_records = payload.get("total_records", 0)
    total_groups = payload.get("total_replicate_groups", 0)
    total_flagged = payload.get("total_flagged_groups", 0)

    html_template = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Product 4 — Resource QC &amp; Data Audit Workbench | BioCIRV</title>
  <style>
    :root, [data-theme="dark"] {
      --bg-page: #0f172a;
      --bg-card: #1e293b;
      --bg-drawer: #0f172a;
      --bg-subtle: #0f172a;
      --bg-hover: rgba(56, 189, 248, 0.12);
      --bg-selected: rgba(56, 189, 248, 0.22);
      --bg-header: #020617;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --border-color: #334155;
      --surface: #1e293b;
      --surface-alt: #0f172a;
      --text: #f8fafc;
      --muted: #94a3b8;
      --border: #334155;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --accent-primary: #0284c7;
      --accent-primary-hover: #0369a1;
      --accent-admin: #7c3aed;
      --accent-success: #15803d;
      --accent-warn: #b45309;
      --accent-danger: #b91c1c;
      --badge-open-bg: rgba(245, 158, 11, 0.2);
      --badge-open-fg: #fde68a;
      --badge-pass-bg: rgba(34, 197, 94, 0.2);
      --badge-pass-fg: #bbf7d0;
      --badge-fail-bg: rgba(239, 68, 68, 0.22);
      --badge-fail-fg: #fecaca;
      --badge-sync-bg: rgba(99, 102, 241, 0.22);
      --badge-sync-fg: #c7d2fe;
    }

    [data-theme="light"] {
      --bg-page: #f4f6f9;
      --bg-card: #ffffff;
      --bg-drawer: #f8fafc;
      --bg-subtle: #f1f5f9;
      --bg-hover: #f0f9ff;
      --bg-selected: #e0f2fe;
      --bg-header: #0f172a;
      --text-main: #0f172a;
      --text-muted: #475569;
      --border-color: #cbd5e1;
      --surface: #ffffff;
      --surface-alt: #f8fafc;
      --text: #0f172a;
      --muted: #475569;
      --border: #cbd5e1;
      --badge-open-bg: #fef3c7;
      --badge-open-fg: #92400e;
      --badge-pass-bg: #dcfce7;
      --badge-pass-fg: #166534;
      --badge-fail-bg: #fee2e2;
      --badge-fail-fg: #991b1b;
      --badge-sync-bg: #e0e7ff;
      --badge-sync-fg: #3730a3;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      background: var(--bg-page);
      color: var(--text-main);
      font-size: 14px;
      line-height: 1.45;
    }

    .topbar {
      background: var(--bg-header);
      color: #f8fafc;
      padding: 12px 20px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid #1e293b;
    }

    .topbar-left {
      display: flex;
      align-items: center;
      gap: 14px;
      flex-wrap: wrap;
    }

    .topbar-title {
      font-size: 17px;
      font-weight: 700;
      letter-spacing: -0.01em;
      margin: 0;
    }

    .topbar-subtitle {
      font-size: 12px;
      color: #94a3b8;
    }

    .nav-links a {
      color: #38bdf8;
      text-decoration: none;
      font-size: 12.5px;
      margin-right: 12px;
      font-weight: 500;
    }

    .nav-links a:hover {
      text-decoration: underline;
    }

    .topbar-right {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .user-pill {
      background: #1e293b;
      border: 1px solid #334155;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 12px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .role-badge {
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
    }

    .role-admin {
      background: #ede9fe;
      color: #5b21b6;
    }

    .role-analyst {
      background: #e0f2fe;
      color: #075985;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      background: var(--bg-card);
      color: var(--text-main);
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .btn:hover:not(:disabled) {
      background: var(--bg-subtle);
    }

    .btn:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }

    .btn-primary {
      background: var(--accent-primary);
      border-color: var(--accent-primary);
      color: #ffffff;
    }

    .btn-primary:hover:not(:disabled) {
      background: var(--accent-primary-hover);
    }

    .btn-admin {
      background: var(--accent-admin);
      border-color: var(--accent-admin);
      color: #ffffff;
    }

    .btn-admin:hover:not(:disabled) {
      background: #6d28d9;
    }

    .sync-banner {
      background: rgba(14, 165, 233, 0.12);
      border-bottom: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 8px 20px;
      font-size: 12.5px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }

    .container {
      max-width: 1680px;
      margin: 0 auto;
      padding: 16px 20px 40px;
    }

    .kpi-strip {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }

    .kpi-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 10px 14px;
    }

    .kpi-label {
      font-size: 11.5px;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
    }

    .kpi-value {
      font-size: 22px;
      font-weight: 700;
      margin-top: 2px;
    }

    .queue-bar {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 12px 14px;
      margin-bottom: 14px;
    }

    .queue-tabs-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--border-color);
    }

    .queue-tabs {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .queue-tab {
      padding: 6px 12px;
      border-radius: 999px;
      border: 1px solid var(--border-color);
      background: var(--bg-subtle);
      color: var(--text-main);
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
    }

    .queue-tab.active {
      background: var(--accent-primary);
      border-color: var(--accent-primary);
      color: #ffffff;
    }

    .facet-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
      gap: 10px;
      padding-top: 10px;
      align-items: end;
    }

    .field-group label {
      display: block;
      font-size: 11.5px;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 4px;
    }

    .field-group select,
    .field-group input,
    .field-group textarea {
      width: 100%;
      padding: 6px 9px;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      font-size: 13px;
      background: var(--bg-subtle);
      color: var(--text-main);
    }

    .workbench-layout {
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
    }

    .queue-table-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      overflow: hidden;
    }

    .table-scroll {
      max-height: 360px;
      overflow-y: auto;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
    }

    th, td {
      padding: 8px 10px;
      text-align: left;
      border-bottom: 1px solid var(--border-color);
    }

    th {
      background: var(--bg-subtle);
      font-weight: 700;
      color: var(--text-muted);
      position: sticky;
      top: 0;
      z-index: 1;
    }

    tr.queue-row {
      cursor: pointer;
      transition: background 0.1s ease;
    }

    tr.queue-row:hover {
      background: var(--bg-hover);
    }

    tr.queue-row.selected {
      background: var(--bg-selected);
      font-weight: 600;
    }

    .flag-pill {
      display: inline-block;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      margin-right: 4px;
      margin-bottom: 2px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }

    .flag-rsd_gt_10 {
      background: #fef3c7;
      color: #92400e;
    }

    .flag-rsd_gt_20 {
      background: #ffedd5;
      color: #9a3412;
    }

    .flag-iqr_outlier {
      background: #fee2e2;
      color: #991b1b;
    }

    .flag-proximate_sum {
      background: #fae8ff;
      color: #86198f;
    }

    .flag-visualizer_flagged {
      background: #cffafe;
      color: #155e75;
      border: 1px solid #06b6d4;
    }

    .flag-stat_snapshot_flagged {
      background: #d1fae5;
      color: #065f46;
      border: 1px solid #10b981;
    }

    .flag-analyst_flagged {
      background: #e0e7ff;
      color: #3730a3;
    }

    .status-pill {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
    }

    .status-open {
      background: var(--badge-open-bg);
      color: var(--badge-open-fg);
    }

    .status-in_review, .status-needs_retest {
      background: rgba(249, 115, 22, 0.22);
      color: #fdba74;
    }

    .status-resolved {
      background: var(--badge-pass-bg);
      color: var(--badge-pass-fg);
    }

    .status-synced {
      background: var(--badge-sync-bg);
      color: var(--badge-sync-fg);
    }

    /* Contextual Workspace Drawer (Side-by-Side) */
    .workspace-drawer {
      background: var(--bg-card);
      border: 2px solid var(--accent-primary);
      border-radius: 10px;
      overflow: hidden;
      box-shadow: 0 6px 20px rgba(15, 23, 42, 0.28);
    }

    .drawer-header {
      background: var(--bg-header);
      color: #ffffff;
      padding: 10px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
    }

    .drawer-panes {
      display: grid;
      grid-template-columns: 1.15fr 1fr;
      gap: 0;
    }

    @media (max-width: 1100px) {
      .drawer-panes {
        grid-template-columns: 1fr;
      }
    }

    .pane-left {
      padding: 16px;
      border-right: 1px solid var(--border-color);
      background: var(--bg-card);
    }

    .pane-right {
      padding: 16px;
      background: var(--bg-drawer);
    }

    .pane-title {
      font-size: 14px;
      font-weight: 700;
      margin: 0 0 10px;
      color: var(--text-main);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .plot-controls-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      margin-bottom: 12px;
      background: var(--bg-subtle);
      padding: 10px;
      border-radius: 8px;
      border: 1px solid var(--border-color);
    }

    .plot-stage {
      border: 1px solid var(--border-color);
      border-radius: 8px;
      background: var(--bg-subtle);
      padding: 10px;
      min-height: 290px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .plot-stats-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      font-size: 12px;
      color: var(--text-muted);
      padding-top: 8px;
      border-top: 1px dashed var(--border-color);
      margin-top: 8px;
    }

    .scope-toggle-group {
      display: flex;
      gap: 12px;
      margin: 8px 0 10px;
      padding: 8px 10px;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 6px;
    }

    .rationale-chips-container {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 6px 0 12px;
    }

    .rationale-chip {
      padding: 5px 10px;
      border-radius: 999px;
      border: 1px solid var(--border-color);
      background: var(--bg-card);
      color: var(--text-main);
      font-size: 11.5px;
      cursor: pointer;
      user-select: none;
    }

    .rationale-chip.selected {
      background: #0284c7;
      border-color: #0284c7;
      color: #ffffff;
      font-weight: 600;
    }

    .provenance-timeline {
      margin-top: 14px;
      padding: 12px;
      border-radius: 8px;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
    }

    .timeline-step {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 8px;
      padding: 6px 0;
      border-bottom: 1px dashed var(--border-color);
      font-size: 12px;
    }

    .timeline-step:last-child {
      border-bottom: none;
    }

    .timeline-label {
      font-weight: 700;
      color: var(--text-muted);
    }

    .transition-badge {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      padding: 2px 6px;
      border-radius: 4px;
      background: var(--bg-subtle);
      color: var(--text-main);
      border: 1px solid var(--border-color);
      font-size: 11px;
    }

    .readonly-analyst-badge {
      display: inline-block;
      padding: 4px 9px;
      border-radius: 6px;
      background: var(--bg-subtle);
      color: var(--text-muted);
      border: 1px solid var(--border-color);
      font-size: 11.5px;
      font-weight: 600;
    }

    .toast-status {
      margin-top: 8px;
      padding: 8px 10px;
      border-radius: 6px;
      font-size: 12px;
      display: none;
    }

    .toast-status.visible {
      display: block;
    }

    .kpi-strip.collapsed {
      display: none;
    }

    .table-scroll.compact {
      max-height: 170px;
    }

    .decision-lock-banner {
      display: none;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 8px 12px;
      margin-bottom: 10px;
      border-radius: 6px;
      background: #fef3c7;
      border: 1px solid #f59e0b;
      color: #92400e;
      font-size: 12px;
      font-weight: 600;
    }

    .decision-lock-banner.visible {
      display: flex;
    }

    .btn-revert {
      background: #ffffff;
      color: #92400e;
      border: 1px solid #d97706;
      padding: 4px 10px;
      font-size: 11.5px;
      font-weight: 700;
    }

    .btn-revert:hover {
      background: #fffbeb;
    }

    .rationale-chip.disabled {
      opacity: 0.55;
      pointer-events: none;
      cursor: not-allowed;
    }

    .section-collapse-bar {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      margin-bottom: 6px;
    }

    th.sortable-th {
      cursor: pointer;
      user-select: none;
    }

    th.sortable-th:hover {
      background: #e2e8f0;
      color: var(--text-main);
    }
  </style>
</head>
<body>
  <header class="topbar">
    <div class="topbar-left">
      <div>
        <h1 class="topbar-title">Product 4 — Resource QC &amp; Data Audit Workbench</h1>
        <div class="topbar-subtitle">
          Two-Stage QC Review Ledger &amp; Contextual Diagnostic Plotter • Snapshot UTC: <span id="snapshot-utc">__GENERATED_UTC__</span>
        </div>
      </div>
      <nav class="nav-links" aria-label="Portal Navigation">
        <a href="../index.html" id="link-portal-gallery">← Back to 5-Product Portal Gallery</a>
        <a href="resource_qc_outlier_dashboard.html" id="link-stat-snapshot">2. Statistical Snapshot</a>
        <a href="resource_explorer_dashboard.html" id="link-data-visualizer">3. Data Visualizer</a>
        <a href="../login.html" id="link-login-portal">🔐 Portal Login / Role Switcher</a>
      </nav>
    </div>
    <div class="topbar-right">
      <div class="user-pill" id="auth-user-pill">
        <span>👤 <strong id="auth-user-email">analyst@lbl.gov</strong></span>
        <span class="role-badge role-analyst" id="auth-user-role-badge">analyst</span>
      </div>
      <button type="button" class="btn" id="btn-theme-toggle" title="Toggle Dark / Light Mode">
        ☀️ Light Mode
      </button>
      <button type="button" class="btn" id="btn-toggle-role-sim" title="Toggle local role preview when offline">
        ⇄ Role Preview
      </button>
      <button type="button" class="btn btn-primary" id="btn-refresh-qc-state">
        ↻ Refresh QC State
      </button>
      <a class="btn" href="/v1/qc/export.csv" id="btn-export-ledger-csv" download="qc_review_decisions.csv">
        📥 Export Ledger CSV
      </a>
      <button type="button" class="btn" id="btn-export-client-json">
        📥 Export JSON
      </button>
      <button type="button" class="btn" id="btn-open-bug-modal" title="Report a Bug or QC Issue on GitHub">
        🐛 Report a Bug
      </button>
    </div>
  </header>

  <div class="sync-banner" id="cross-tab-sync-banner" role="status">
    <div>
      <strong>Live Synchronization Model:</strong>
      <code>BroadcastChannel("biocirv_qc_decisions")</code> synchronizes open tabs in the <strong>same browser</strong> immediately when a QC decision is saved.
      Other analysts' sessions in separate browsers update on page refresh or via <strong>↻ Refresh QC State</strong>.
    </div>
    <div id="last-sync-indicator">Channel: <code>biocirv_qc_decisions</code> active</div>
  </div>

  <main class="container">
    <div class="section-collapse-bar">
      <button type="button" class="btn" id="btn-toggle-kpi-strip" title="Collapse or expand KPI summary cards to save vertical screen space">
        ▲ Compact KPIs
      </button>
      <button type="button" class="btn" id="btn-toggle-queue-card" title="Toggle compact or expanded queue table height">
        ↕ Compact Queue Table
      </button>
    </div>

    <section class="kpi-strip" id="kpi-strip-section" aria-label="QC Queue Summary Metrics">
      <div class="kpi-card">
        <div class="kpi-label">Snapshot Observation Rows</div>
        <div class="kpi-value" id="kpi-total-records">__TOTAL_RECORDS__</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Replicate Groups</div>
        <div class="kpi-value" id="kpi-total-groups">__TOTAL_GROUPS__</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Candidate Flagged Queue</div>
        <div class="kpi-value" id="kpi-flagged-count">__TOTAL_FLAGGED__</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Assigned to Me (Open)</div>
        <div class="kpi-value" id="kpi-assigned-me">0</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Pending Admin GSheet Sync</div>
        <div class="kpi-value" id="kpi-pending-gsheet">0</div>
      </div>
    </section>

    <section class="queue-bar" aria-label="Queue &amp; Task Assignment Bar">
      <div class="queue-tabs-row">
        <div class="queue-tabs" role="tablist" id="queue-tabs-container">
          <button type="button" class="queue-tab" data-queue-tab="assigned_to_me" id="tab-assigned-to-me">
            👤 Assigned to Me (<span id="count-assigned-to-me">0</span>)
          </button>
          <button type="button" class="queue-tab" data-queue-tab="unassigned" id="tab-unassigned">
            Unassigned (<span id="count-unassigned">0</span>)
          </button>
          <button type="button" class="queue-tab active" data-queue-tab="all_open" id="tab-all-open">
            All Open (<span id="count-all-open">0</span>)
          </button>
          <button type="button" class="queue-tab" data-queue-tab="in_review" id="tab-in-review">
            In Review / Retest (<span id="count-in-review">0</span>)
          </button>
          <button type="button" class="queue-tab" data-queue-tab="pending_gsheet" id="tab-pending-gsheet">
            Resolved (Pending GSheet Sync) (<span id="count-pending-gsheet">0</span>)
          </button>
          <button type="button" class="queue-tab" data-queue-tab="synced_gsheet" id="tab-synced-gsheet">
            Synced to GSheet (<span id="count-synced-gsheet">0</span>)
          </button>
        </div>

        <div id="batch-gsheet-action-container" style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
          <button
            type="button"
            class="btn"
            id="btn-batch-assign-open"
            title="Assign all currently filtered open queue items to Reviewer or Analyst of Record"
          >
            ⚡ Batch-Assign Filtered Open
          </button>
          <button
            type="button"
            class="btn btn-admin"
            id="btn-sync-gsheet-batch"
            style="display: none;"
          >
            📤 Sync All Pending to Google Sheets (<span id="count-batch-sync-btn">0</span>)
          </button>
          <span
            class="readonly-analyst-badge"
            id="badge-batch-analyst-readonly"
          >
            🔒 Stage 2 GSheet Batch Sync: Admin Only
          </span>
        </div>
      </div>

      <div class="facet-row">
        <div class="field-group">
          <label for="filter-resource">Resource</label>
          <select id="filter-resource">
            <option value="">All Resources</option>
          </select>
        </div>
        <div class="field-group">
          <label for="filter-analysis-type">Analysis Domain</label>
          <select id="filter-analysis-type">
            <option value="">All Analysis Domains</option>
          </select>
        </div>
        <div class="field-group">
          <label for="filter-parameter">Parameter</label>
          <select id="filter-parameter">
            <option value="">All Parameters</option>
          </select>
        </div>
        <div class="field-group">
          <label for="filter-flag-type">Flag Type / Source</label>
          <select id="filter-flag-type">
            <option value="">All Flag Types</option>
            <option value="interactive_session">⚡ All Interactive Session Flags (Visualizer + Stat Snapshot)</option>
            <option value="visualizer_flagged">🔬 visualizer_flagged (Page 3 Data Visualizer Flag)</option>
            <option value="stat_snapshot_flagged">📊 stat_snapshot_flagged (Page 2 Statistical Snapshot Flag)</option>
            <option value="rsd_gt_10">rsd_gt_10 (RSD &gt; 10%)</option>
            <option value="rsd_gt_20">rsd_gt_20 (RSD &gt; 20%)</option>
            <option value="iqr_outlier">iqr_outlier (Tukey 1.5×IQR)</option>
            <option value="proximate_sum">proximate_sum (Closure &lt;95% or &gt;105%)</option>
            <option value="analyst_flagged">📋 analyst_flagged (Legacy GSheet Fail/Flag)</option>
          </select>
        </div>
        <div class="field-group">
          <label for="filter-qc-status">Current QC Status</label>
          <select id="filter-qc-status">
            <option value="">All QC Statuses</option>
            <option value="pass">pass (QC Pass)</option>
            <option value="fail">fail (QC Fail / Rejected)</option>
            <option value="provisional">provisional (In Review / Open)</option>
            <option value="needs_retest">needs_retest (Lab Retest)</option>
            <option value="mixed">mixed (Split Replicate QC)</option>
          </select>
        </div>
        <div class="field-group">
          <label for="filter-min-rsd" style="display:flex;align-items:center;justify-content:space-between;gap:6px;">
            <span>Min RSD % Threshold</span>
            <strong id="filter-min-rsd-val" style="color:#38bdf8;font-family:monospace;">&ge; 0% (All)</strong>
          </label>
          <div style="display:flex;align-items:center;gap:6px;">
            <input type="range" id="filter-min-rsd" min="0" max="50" step="1" value="0" style="flex:1;accent-color:#38bdf8;cursor:pointer;" />
            <button type="button" class="btn btn-rsd-preset active" id="btn-rsd-preset-0" onclick="window.setMinRsdFilter && window.setMinRsdFilter(0)" style="padding:2px 6px;font-size:10.5px;">All</button>
            <button type="button" class="btn btn-rsd-preset" id="btn-rsd-preset-10" onclick="window.setMinRsdFilter && window.setMinRsdFilter(10)" style="padding:2px 6px;font-size:10.5px;">&gt;10%</button>
            <button type="button" class="btn btn-rsd-preset" id="btn-rsd-preset-20" onclick="window.setMinRsdFilter && window.setMinRsdFilter(20)" style="padding:2px 6px;font-size:10.5px;">&gt;20%</button>
          </div>
        </div>
        <div class="field-group">
          <label for="filter-analyst-of-record">Analyst of Record (Lab)</label>
          <select id="filter-analyst-of-record">
            <option value="">All Lab Analysts</option>
          </select>
        </div>
        <div class="field-group">
          <label for="filter-assigned-reviewer">Assigned Reviewer</label>
          <select id="filter-assigned-reviewer">
            <option value="">All Reviewers / Unassigned</option>
          </select>
          <select id="filter-assigned-analyst" style="display:none;" aria-hidden="true">
            <option value="">All Analysts / Unassigned</option>
          </select>
        </div>
        <div class="field-group">
          <label for="sort-queue-select">Sort Queue By</label>
          <select id="sort-queue-select">
            <option value="rsd_desc" selected>RSD % (High → Low)</option>
            <option value="rsd_asc">RSD % (Low → High)</option>
            <option value="flag_severity">Flag Severity (RSD &gt; 20% / Multi-Flag)</option>
            <option value="resource_asc">Resource Name (A → Z)</option>
            <option value="sample_asc">Prepared Sample (A → Z)</option>
            <option value="default">Default Queue Order (Severity / ID)</option>
            <option value="interactive_first">⚡ Interactive Session Flags First (Visualizer &amp; Stat Snapshot)</option>
            <option value="recent_first">🕒 Most Recently Flagged / Updated First</option>
            <option value="flagged_by">👤 Flagged By Analyst (A → Z)</option>
            <option value="scope">🎯 Flag Scope (Single Point vs Replicate Group)</option>
            <option value="resource_param">🧪 Resource &amp; Parameter (A → Z)</option>
          </select>
          <select id="filter-sort-by" style="display:none;" aria-hidden="true">
            <option value="default">Default Queue Order (Severity / ID)</option>
            <option value="interactive_first">⚡ Interactive Session Flags First (Visualizer &amp; Stat Snapshot)</option>
            <option value="recent_first">🕒 Most Recently Flagged / Updated First</option>
            <option value="rsd_desc">📈 Highest RSD % First</option>
            <option value="rsd_asc">RSD % (Low → High)</option>
            <option value="flag_severity">Flag Severity (RSD &gt; 20% / Multi-Flag)</option>
            <option value="resource_asc">Resource Name (A → Z)</option>
            <option value="sample_asc">Prepared Sample (A → Z)</option>
            <option value="flagged_by">👤 Flagged By Analyst (A → Z)</option>
            <option value="scope">🎯 Flag Scope (Single Point vs Replicate Group)</option>
            <option value="resource_param">🧪 Resource &amp; Parameter (A → Z)</option>
          </select>
        </div>
        <div class="field-group">
          <label for="filter-search">Search Sample / Record / Provenance</label>
          <div style="display:flex;align-items:center;gap:6px;">
            <input type="search" id="filter-search" placeholder="e.g. PROX-AH-004, visualizer_flagged, analyst@lbl.gov" style="flex:1;" />
            <button type="button" class="btn" id="btn-reset-filters" onclick="window.resetAllFilters && window.resetAllFilters()" style="padding:5px 10px;font-size:11px;white-space:nowrap;" title="Reset all queue filters">↺ Reset Filters</button>
          </div>
        </div>
      </div>
      <div class="interactive-quick-filter-bar" style="display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:10px;padding-top:10px;border-top:1px dashed var(--border-color);font-size:11.5px;">
        <span style="font-weight:700;color:var(--text-muted);">Quick Session Triage:</span>
        <button type="button" class="btn" id="btn-quick-filter-interactive" onclick="window.setQuickFlagFilter && window.setQuickFlagFilter('interactive_session')" style="padding:3px 9px;font-size:11px;">
          ⚡ All Interactive Session Flags
        </button>
        <button type="button" class="btn" id="btn-quick-filter-visualizer" onclick="window.setQuickFlagFilter && window.setQuickFlagFilter('visualizer_flagged')" style="padding:3px 9px;font-size:11px;">
          🔬 Visualizer Flags (Page 3)
        </button>
        <button type="button" class="btn" id="btn-quick-filter-stat-snapshot" onclick="window.setQuickFlagFilter && window.setQuickFlagFilter('stat_snapshot_flagged')" style="padding:3px 9px;font-size:11px;">
          📊 Stat Snapshot Flags (Page 2)
        </button>
        <button type="button" class="btn" id="btn-quick-filter-legacy-gsheet" onclick="window.setQuickFlagFilter && window.setQuickFlagFilter('analyst_flagged')" style="padding:3px 9px;font-size:11px;">
          📋 Legacy GSheet Fails
        </button>
        <button type="button" class="btn" id="btn-quick-sort-recent" onclick="window.setQueueSortBy && window.setQueueSortBy('recent_first')" style="padding:3px 9px;font-size:11px;">
          🕒 Sort: Recently Flagged First
        </button>
      </div>
    </section>

    <div class="workbench-layout">
      <section class="queue-table-card" aria-label="Flagged Replicate Queue">
        <div
          id="qc-bulk-assign-bar"
          class="bulk-assign-bar"
          style="display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; padding: 10px 14px; border-bottom: 1px solid var(--border); background: rgba(15, 23, 42, 0.55);"
        >
          <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px;">
            <label style="display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600; color: var(--text); cursor: pointer;">
              <input type="checkbox" id="chk-select-all-filtered" onchange="window.toggleSelectAllFiltered && window.toggleSelectAllFiltered(this.checked)" />
              <span>Select All Filtered</span>
            </label>
            <span
              id="bulk-selected-count"
              style="padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 700; background: rgba(56, 189, 248, 0.16); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.35);"
            >0 selected</span>
            <button type="button" class="btn" id="btn-select-all-filtered" onclick="window.selectAllFilteredRows && window.selectAllFilteredRows()">Select All Filtered</button>
            <button type="button" class="btn" id="btn-clear-selection" onclick="window.clearRowSelection && window.clearRowSelection()">Clear</button>
          </div>
          <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px;">
            <label for="bulk-assign-email" style="font-size: 11px; font-weight: 600; color: var(--muted);">Assign Selected To:</label>
            <input
              type="email"
              id="bulk-assign-email"
              list="AnalystDirectoryList"
              placeholder="analyst@institution.edu"
              style="background: #0f172a; color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 5px 10px; font-size: 12px; min-width: 210px;"
            />
            <datalist id="AnalystDirectoryList"></datalist>
            <button type="button" class="btn" id="btn-bulk-assign-my-email" onclick="window.fillBulkAssignMyEmail && window.fillBulkAssignMyEmail()">
              Use My Email
            </button>
            <button type="button" class="btn btn-primary" id="btn-bulk-assign-apply" onclick="window.bulkAssignSelected && window.bulkAssignSelected()">
              👤 Bulk Assign Selected
            </button>
          </div>
        </div>
        <div class="table-scroll" id="queue-table-scroll-wrapper">
          <table id="qc-queue-table">
            <thead>
              <tr>
                <th style="width: 34px; text-align: center;">
                  <input type="checkbox" id="chk-select-all-header" title="Select all filtered rows" onchange="window.toggleSelectAllFiltered && window.toggleSelectAllFiltered(this.checked)" />
                </th>
                <th>Decision ID</th>
                <th>Resource</th>
                <th>Prepared Sample</th>
                <th>Analysis Domain</th>
                <th>Parameter</th>
                <th>Flag Type(s)</th>
                <th>Trigger Diagnostic</th>
                <th class="sortable-th" id="th-sort-rsd" title="Click to toggle RSD% sort direction">RSD % (n) ⇅</th>
                <th>Analyst of Record</th>
                <th>Assigned Reviewer</th>
                <th>QC Transition</th>
                <th>Stage 1 / Stage 2 Status</th>
              </tr>
            </thead>
            <tbody id="qc-queue-tbody"></tbody>
          </table>
        </div>
      </section>

      <section
        class="workspace-drawer"
        id="contextual-workspace-drawer"
        aria-label="Side-by-Side Contextual Workspace Drawer"
      >
        <div class="drawer-header">
          <div>
            <strong id="drawer-title">Contextual Workspace Drawer</strong>
            <span id="drawer-subtitle" style="margin-left: 10px; color: #94a3b8; font-size: 12px;"></span>
          </div>
          <div style="display: flex; align-items: center; gap: 10px; font-size: 12px; color: #cbd5e1;">
            <button
              id="btn-drawer-show-me-flag"
              type="button"
              class="btn-show-me-flag"
              data-decision-id="QC-0001"
              data-group-key=""
              title="Show flagged replicate group and outlier in slice context"
              style="padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; background: rgba(56,189,248,0.18); color: #38bdf8; border: 1px solid rgba(56,189,248,0.45); cursor: pointer;"
              onclick="event.stopPropagation(); window.openFlagShowMePopover && window.openFlagShowMePopover({ decisionId: this.getAttribute('data-decision-id'), replicateGroupKey: this.getAttribute('data-group-key') }, this);"
            >👁 Show me</button>
            <span>Deep Link: <code id="drawer-deeplink-code">?decision_id=QC-0001</code></span>
          </div>
        </div>

        <div class="drawer-panes">
          <!-- LEFT PANE: Interactive Multi-View Context Plotter -->
          <div class="pane-left">
            <div class="pane-title">
              <span>Left Pane — Interactive Multi-View Diagnostic Plotter</span>
              <span id="plot-active-group-badge" class="transition-badge"></span>
            </div>

            <div class="plot-controls-grid">
              <div class="field-group">
                <label for="select-plot-style">Plot Style</label>
                <select id="select-plot-style">
                  <option value="forest_iqr">Sample Forest / Caterpillar + IQR Band</option>
                  <option value="run_order">Run-Order / Batch Control Chart</option>
                  <option value="proximate_closure">Proximate / Compositional Closure Bar</option>
                  <option value="cross_resource_box">Cross-Resource Box + Strip Plot</option>
                </select>
              </div>

              <div class="field-group">
                <label for="select-group-by">Group / Color By</label>
                <select id="select-group-by">
                  <option value="field_sample">Field Sample</option>
                  <option value="prepared_sample">Prepared Sample</option>
                  <option value="experiment">Experiment / Batch</option>
                  <option value="prep_method">Preparation Method</option>
                  <option value="exp_date">Harvest / Collection Date</option>
                </select>
              </div>

              <div class="field-group">
                <label for="select-co-measured-param">Inspect Co-Measured Parameter on Same Sample</label>
                <select id="select-co-measured-param"></select>
              </div>
            </div>

            <div class="plot-stage">
              <div id="diagnostic-plot-container">
                <svg
                  id="diagnostic-plot-svg"
                  viewBox="0 0 640 260"
                  width="100%"
                  height="260"
                  role="img"
                  aria-label="Interactive QC Diagnostic Plot"
                ></svg>
              </div>
              <div class="plot-stats-bar" id="diagnostic-plot-stats"></div>
            </div>
          </div>

          <!-- RIGHT PANE: Granular Replicate Breakdown, Decision Form & Audit Provenance Timeline -->
          <div class="pane-right">
            <div class="pane-title">
              <span>Right Pane — Granular Replicate Scope, Decision &amp; Audit Provenance</span>
            </div>

            <div class="scope-toggle-group" role="radiogroup" aria-label="Decision Replicate Scope">
              <label>
                <input
                  type="radio"
                  name="replicate-scope-mode"
                  class="scope-radio"
                  id="scope-entire-group"
                  value="group"
                  checked
                />
                <strong>Entire Replicate Group</strong> (applies to all replicates in group)
              </label>
              <label>
                <input
                  type="radio"
                  name="replicate-scope-mode"
                  class="scope-radio"
                  id="scope-single-replicate"
                  value="single"
                />
                <strong>Specific Single Replicate(s)</strong> (check individual outlier rows)
              </label>
            </div>

            <div class="table-scroll" style="max-height: 165px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-card); margin-bottom: 12px;">
              <table>
                <thead>
                  <tr>
                    <th>Apply</th>
                    <th>Record ID</th>
                    <th>Rep #</th>
                    <th>Value</th>
                    <th>Δ vs Median</th>
                    <th>Analyst</th>
                    <th>Date</th>
                    <th>Current QC</th>
                  </tr>
                </thead>
                <tbody id="replicate-breakdown-tbody"></tbody>
              </table>
            </div>

            <div id="decision-lock-banner" class="decision-lock-banner" role="region" aria-label="Decision Lock Banner">
              <div>
                🔒 <span id="decision-lock-text">Stage 1 Decision Committed &amp; Locked.</span>
              </div>
              <button type="button" class="btn btn-revert" id="btn-revert-decision">
                ↺ Revert Decision to Open
              </button>
            </div>

            <div class="field-group">
              <label>Structured Rationale Chips (select one or more)</label>
              <div class="rationale-chips-container" id="rationale-chips-list">
                <span class="rationale-chip" data-chip="Replication outlier (RSD > 10%)">Replication outlier (RSD &gt; 10%)</span>
                <span class="rationale-chip" data-chip="Mass-balance / closure violation">Mass-balance / closure violation</span>
                <span class="rationale-chip" data-chip="Suspected unit / decimal shift">Suspected unit / decimal shift</span>
                <span class="rationale-chip" data-chip="Instrument drift / batch artifact">Instrument drift / batch artifact</span>
                <span class="rationale-chip" data-chip="Confirmed valid extreme biological value">Confirmed valid extreme biological value</span>
                <span class="rationale-chip" data-chip="Sample contamination / lab handling note">Sample contamination / lab handling note</span>
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
              <div class="field-group">
                <label for="select-decision-action">Stage 1 Decision Action (5-State QC Pass)</label>
                <select id="select-decision-action">
                  <option value="reject_fail">Flag as QC Fail (new_qc_pass = fail)</option>
                  <option value="approve_pass">Approve as QC Pass (new_qc_pass = pass)</option>
                  <option value="provisional">Mark Provisional Pass (new_qc_pass = provisional)</option>
                  <option value="needs_retest">Flag for Lab Retest (new_qc_pass = retest)</option>
                  <option value="in_review" selected>Keep In Review / Defer (new_qc_pass = in_review)</option>
                </select>
              </div>

              <div class="field-group">
                <label for="input-assigned-to">Assigned Reviewer Email</label>
                <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                  <input
                    type="email"
                    id="input-assigned-to"
                    placeholder="analyst@lbl.gov"
                    style="flex: 1; min-width: 140px;"
                  />
                  <button type="button" class="btn" id="btn-assign-to-me" title="PATCH /v1/qc/decisions/{id}/assign">
                    Assign to Me
                  </button>
                  <button type="button" class="btn" id="btn-assign-analyst-of-record" title="Assign to the lab Analyst of Record on this replicate group">
                    Assign to Analyst of Record
                  </button>
                </div>
              </div>
            </div>

            <div class="field-group" style="margin-bottom: 10px;">
              <label for="input-review-note">Required Free-Text Review Note</label>
              <textarea
                id="input-review-note"
                rows="2"
                required
                placeholder="Document technical justification for approving or rejecting replicate(s)..."
              ></textarea>
            </div>

            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap;">
              <button type="button" class="btn btn-primary" id="btn-save-decision">
                💾 Save QC Decision (Stage 1 PostgreSQL Commit)
              </button>
              <span style="font-size: 11.5px; color: var(--text-muted);">
                Commits immediately to PostgreSQL &amp; broadcasts on <code>biocirv_qc_decisions</code>
              </span>
            </div>

            <div id="decision-toast" class="toast-status" role="alert"></div>

            <!-- Complete 4-Step Audit Provenance & Timestamp Timeline -->
            <div class="provenance-timeline" id="audit-provenance-timeline">
              <div style="font-weight: 700; font-size: 12.5px; margin-bottom: 6px; color: var(--text-main);">
                Audit Provenance &amp; Timestamp Timeline
              </div>

              <div class="timeline-step">
                <div>
                  <span class="timeline-label">1. Created / Flagged:</span>
                  <span id="prov-created-by">auto-qc-engine@biocirv.org</span>
                  <span class="transition-badge" id="prov-source-badge" style="margin-left: 6px; display: none;"></span>
                </div>
                <code id="prov-created-at">__GENERATED_UTC__</code>
              </div>

              <div class="timeline-step" id="prov-lab-note-row" style="display: none;">
                <div>
                  <span class="timeline-label">Lab Sample / Submission Note:</span>
                  <span id="prov-lab-lineage-note" style="color: #cbd5e1; font-style: italic;">—</span>
                </div>
              </div>

              <div class="timeline-step">
                <div>
                  <span class="timeline-label">2. Assigned Reviewer:</span>
                  <span id="prov-assigned-to">Unassigned</span>
                </div>
                <span class="transition-badge" id="prov-scope-badge">Scope: Entire Replicate Group</span>
              </div>

              <div class="timeline-step">
                <div>
                  <span class="timeline-label">3. Decision Recorded (Stage 1 DB):</span>
                  <span id="prov-resolved-by">Pending analyst decision</span>
                </div>
                <div>
                  <span class="transition-badge" id="prov-transition-badge">pass → pass</span>
                  <code id="prov-resolved-at" style="margin-left: 6px;">—</code>
                </div>
              </div>

              <div class="timeline-step">
                <div>
                  <span class="timeline-label">4. Google Sheets Sync Status (Stage 2):</span>
                  <span class="status-pill status-open" id="prov-gsheet-status-badge">Pending Admin GSheet Sync</span>
                  <code id="prov-gsheet-synced-at" style="margin-left: 6px;">—</code>
                  <div id="prov-gsheet-sync-error" style="display: none; margin-top: 4px; font-size: 11px; color: #fca5a5;"></div>
                </div>
                <div id="prov-gsheet-action-slot">
                  <button
                    type="button"
                    class="btn btn-admin"
                    id="btn-sync-single-gsheet"
                    style="display: none;"
                  >
                    📤 Sync This Decision to Google Sheets
                  </button>
                  <span
                    class="readonly-analyst-badge"
                    id="badge-analyst-gsheet-readonly"
                  >
                    Read-Only (Admin Role Required for GSheet Write-Back)
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </main>

  <style>
    .hidden { display: none !important; }
    .bug-modal-backdrop {
      position: fixed;
      inset: 0;
      z-index: 200;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.72);
      padding: 16px;
    }
    .bug-modal-card {
      background: var(--bg-card, #1e293b);
      border: 1px solid var(--border-color, #334155);
      border-radius: 14px;
      max-width: 560px;
      width: 100%;
      padding: 20px;
      box-shadow: 0 20px 45px rgba(0, 0, 0, 0.55);
      display: flex;
      flex-direction: column;
      gap: 12px;
      color: var(--text-main, #f8fafc);
    }
    .bug-modal-card input,
    .bug-modal-card select,
    .bug-modal-card textarea {
      width: 100%;
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid var(--border-color, #334155);
      background: var(--bg-drawer, #0f172a);
      color: var(--text-main, #f8fafc);
      font-size: 0.82rem;
      font-family: inherit;
    }
    .bug-modal-diag {
      background: var(--bg-drawer, #0f172a);
      border: 1px solid var(--border-color, #334155);
      border-radius: 8px;
      padding: 10px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.75rem;
      color: var(--text-muted, #94a3b8);
      white-space: pre-wrap;
    }
  </style>

  <!-- Pre-populated GitHub Bug Report Modal -->
  <div id="modal-report-bug" class="bug-modal-backdrop hidden" role="dialog" aria-modal="true" aria-labelledby="bug-modal-heading">
    <div class="bug-modal-card">
      <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--border); padding-bottom: 10px;">
        <div>
          <h3 id="bug-modal-heading" style="font-size: 1rem; font-weight: 700;">🐛 Report a Dashboard or Data QC Issue</h3>
          <p style="font-size: 0.76rem; color: var(--text-muted); margin-top: 3px;">
            Automatically attaches your active page, queue tab, resource filter, and selected decision context to a GitHub Issue.
          </p>
        </div>
        <button id="btn-close-bug-modal" type="button" class="btn">✕</button>
      </div>

      <div>
        <label style="font-size: 0.76rem; font-weight: 600; display: block; margin-bottom: 4px;">Issue Summary Title</label>
        <input id="bug-modal-title" type="text" placeholder="e.g., Audit Workbench replicate group IQR whisker mismatch" />
      </div>

      <div>
        <label style="font-size: 0.76rem; font-weight: 600; display: block; margin-bottom: 4px;">Issue Category</label>
        <select id="bug-modal-category">
          <option value="UI / Chart Rendering Bug">UI / Chart Rendering Bug</option>
          <option value="Statistical Outlier / Suspect Value">Statistical Outlier / Suspect Value</option>
          <option value="Unit / Basis Normalization Issue">Unit / Basis Normalization Issue</option>
          <option value="Missing Metadata / Provenance Gap">Missing Metadata / Provenance Gap</option>
          <option value="Feature / Export Request">Feature / Export Request</option>
        </select>
      </div>

      <div>
        <label style="font-size: 0.76rem; font-weight: 600; display: block; margin-bottom: 4px;">What happened / Steps to reproduce</label>
        <textarea id="bug-modal-desc" rows="3" placeholder="Describe the unexpected value, chart behavior, or missing data..."></textarea>
      </div>

      <div>
        <label style="font-size: 0.76rem; font-weight: 600; display: block; margin-bottom: 4px;">Expected behavior (optional)</label>
        <textarea id="bug-modal-expected" rows="2" placeholder="What should be displayed or how should this record be handled?"></textarea>
      </div>

      <div class="bug-modal-diag">
        <div style="font-weight: 700; color: var(--text); margin-bottom: 4px;">Auto-Captured Diagnostic Context:</div>
        <div id="bug-modal-diagnostics">Loading current view state...</div>
      </div>

      <div id="bug-modal-status" class="hidden" style="font-size: 0.75rem; font-family: var(--mono); padding: 8px; border-radius: 6px; border: 1px solid var(--border);"></div>

      <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px; border-top: 1px solid var(--border); padding-top: 10px;">
        <button id="btn-cancel-bug-modal" type="button" class="btn">Cancel</button>
        <button id="btn-submit-github-api" type="button" class="btn btn-primary" title="Submit issue to PostgreSQL QC Ledger and GitHub via /v1/qc/github-issue">
          🚀 Submit Issue
        </button>
        <button id="btn-submit-github-url" type="button" class="btn btn-primary hidden" style="display:none;">
          ↗ Open Pre-Filled GitHub Issue
        </button>
      </div>
    </div>
  </div>

  <!-- Shared Contextual Flag "Show me" Mini-Plot Popover (Card 13) -->
  <div id="audit-flag-show-me-popover" class="hidden" style="display:none; position:fixed; z-index:85; top:96px; right:32px; width:460px; max-width:94vw; border-radius:14px; border:2px solid #38bdf8; background:var(--bg-card, #1e293b); color:var(--text-main, #f8fafc); opacity:1; backdrop-filter:none; box-shadow:0 24px 48px rgba(2,6,23,0.88); padding:14px;" role="dialog" aria-label="Contextual Flag Slice Mini-Plot">
    <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:8px; border-bottom:1px solid var(--border); padding-bottom:8px; margin-bottom:8px;">
      <div>
        <div id="show-me-popover-title" style="font-size:12px; font-weight:700; color:var(--text);">
          👁 Contextual Slice Mini-Plot
        </div>
        <div id="show-me-popover-subtitle" style="font-size:11px; font-family:var(--mono); color:var(--muted); margin-top:2px;"></div>
      </div>
      <button id="btn-close-show-me-popover" type="button" class="btn" style="padding:2px 8px; font-size:11px;" onclick="window.closeFlagShowMePopover && window.closeFlagShowMePopover()" title="Close mini-plot popover">✕</button>
    </div>
    <div id="show-me-flag-pills" style="display:flex; flex-wrap:wrap; align-items:center; gap:4px; margin-bottom:8px;"></div>
    <div id="show-me-mini-svg-wrap" style="border-radius:10px; border:1px solid var(--border); background:var(--bg-page, #0f172a); opacity:1; padding:8px; margin-bottom:8px;">
      <svg id="show-me-mini-svg" viewBox="0 0 420 150" width="100%" height="150" role="img" aria-label="Flagged Replicate Group vs Peer Slice Distribution"></svg>
    </div>
    <div id="show-me-proximate-bar" class="hidden" style="display:none; border-radius:10px; border:1px solid rgba(217,119,6,0.45); background:rgba(245,158,11,0.1); padding:8px 10px; font-size:11px; font-family:var(--mono); margin-bottom:8px;"></div>
    <div id="show-me-legend" style="display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:6px; font-size:10px; font-family:var(--mono); color:var(--muted); margin-bottom:8px;">
      <span>⚪ Peer Slice Points (#64748b)</span>
      <span>🔵 Target Replicate Group (#2563eb)</span>
      <span>🔴 Flagged Outlier (#dc2626)</span>
      <span>◆✕ QC Fail / Rejected (#f59e0b)</span>
    </div>
    <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; border-top:1px solid var(--border); padding-top:8px; font-size:11px;">
      <span id="show-me-stats-summary" style="font-family:var(--mono); font-size:10px; color:var(--muted);"></span>
      <a id="show-me-open-visualizer-link" href="resource_explorer_dashboard.html" class="btn btn-primary" style="text-decoration:none; font-size:11px; padding:4px 10px;">Open in Data Visualizer ↗</a>
    </div>
  </div>

  <script>
    (function () {
      "use strict";

      var WORKBENCH_DATA = __WORKBENCH_PAYLOAD_JSON__;

      var state = {
        user: {
          authenticated: true,
          email: "analyst@lbl.gov",
          name: "BioCIRV QC Analyst",
          role: "analyst",
          assigned_open_count: 0
        },
        activeQueueTab: "all_open",
        filters: {
          resource: "",
          analysisType: "",
          parameter: "",
          flagType: "",
          qcStatus: "",
          minRsd: 0,
          analystOfRecord: "",
          assignedReviewer: "",
          assignedAnalyst: "",
          sortBy: "default",
          search: ""
        },
        queueSort: "rsd_desc",
        decisionsById: {},
        decisionsOrder: [],
        selectedDecisionId: null,
        selectedGroupKey: null,
        inspectedGroupKey: null,
        plotStyle: "forest_iqr",
        groupBy: "field_sample",
        scopeMode: "group",
        selectedReplicateIds: {},
        selectedChips: {},
        selectedIds: new Set()
      };

      function getDefaultAssigneeEmail(existingEmail) {
        var placeholderEmails = [
          "unassigned",
          "none",
          "null",
          "anonymous",
          "guest",
          "local.analyst@lbl.gov"
        ];
        var cleanExisting = String(existingEmail || "").trim();
        if (
          cleanExisting &&
          placeholderEmails.indexOf(cleanExisting.toLowerCase()) === -1
        ) {
          return cleanExisting;
        }
        var userEmail = String((state.user && state.user.email) || "").trim();
        if (
          userEmail &&
          placeholderEmails.indexOf(userEmail.toLowerCase()) === -1
        ) {
          return userEmail;
        }
        try {
          var storedEmail = String(
            localStorage.getItem("biocirv_analyst_email") || ""
          ).trim();
          if (
            storedEmail &&
            placeholderEmails.indexOf(storedEmail.toLowerCase()) === -1
          ) {
            return storedEmail;
          }
        } catch (_e) {}
        return "";
      }
      if (typeof window !== "undefined") {
        window.getDefaultAssigneeEmail = getDefaultAssigneeEmail;
      }

      // Initialize cross-tab BroadcastChannel("biocirv_qc_decisions")
      var qcBroadcastChannel = null;
      if (typeof window !== "undefined" && "BroadcastChannel" in window) {
        try {
          qcBroadcastChannel = new BroadcastChannel("biocirv_qc_decisions");
          qcBroadcastChannel.onmessage = function (ev) {
            var msg = ev && ev.data ? ev.data : null;
            if (!msg || msg.type !== "qc_decision_saved") {
              return;
            }
            var indicator = document.getElementById("last-sync-indicator");
            if (indicator) {
              indicator.textContent =
                "Live BroadcastChannel update received (" +
                (msg.decision_id || msg.replicate_group_key || "QC") +
                " → " +
                (msg.new_qc_pass || "updated") +
                ")";
            }
            refreshQcStateFromApi();
          };
        } catch (err) {
          qcBroadcastChannel = null;
        }
      }

      function inferInteractiveFlagTypes(item) {
        if (!item) return [];
        var out = [];
        function addFlag(ft) {
          if (ft && out.indexOf(ft) === -1) out.push(ft);
        }
        if (Array.isArray(item.flag_types)) {
          for (var i = 0; i < item.flag_types.length; i++) {
            addFlag(item.flag_types[i]);
          }
        }
        if (item.flag_type) {
          addFlag(item.flag_type);
        }
        var srcLower = String(item.source_label || "").toLowerCase();
        if (
          srcLower.indexOf("visualizer") !== -1 ||
          srcLower.indexOf("explorer") !== -1 ||
          srcLower.indexOf("page 3") !== -1
        ) {
          addFlag("visualizer_flagged");
        } else if (
          srcLower.indexOf("statistical") !== -1 ||
          srcLower.indexOf("snapshot") !== -1 ||
          srcLower.indexOf("outlier") !== -1 ||
          srcLower.indexOf("page 2") !== -1
        ) {
          addFlag("stat_snapshot_flagged");
        }
        return out;
      }

      function mergeFlagTypesIntoDecision(targetDec, incomingItem) {
        if (!targetDec || !incomingItem) return;
        var existingFlags = Array.isArray(targetDec.flag_types)
          ? targetDec.flag_types.slice()
          : targetDec.flag_type
          ? [targetDec.flag_type]
          : [];
        var incomingFlags = inferInteractiveFlagTypes(incomingItem);
        for (var fi = 0; fi < incomingFlags.length; fi++) {
          var nf = incomingFlags[fi];
          if (nf && existingFlags.indexOf(nf) === -1) {
            if (nf === "visualizer_flagged" || nf === "stat_snapshot_flagged") {
              existingFlags.unshift(nf);
            } else {
              existingFlags.push(nf);
            }
          }
        }
        if (existingFlags.length > 0) {
          targetDec.flag_types = existingFlags;
        }
        if (
          incomingFlags.indexOf("visualizer_flagged") !== -1 ||
          incomingFlags.indexOf("stat_snapshot_flagged") !== -1
        ) {
          targetDec.flag_type =
            incomingFlags.indexOf("visualizer_flagged") !== -1
              ? "visualizer_flagged"
              : "stat_snapshot_flagged";
        }
      }

      function mergeLocalStorageDecisionsIntoState() {
        try {
          if (typeof localStorage === "undefined") return;
          var combinedItems = [];
          var keysToRead = [
            "biocirv_pending_qc_decisions",
            "biocirv_qc_decisions_ledger_v1",
            "biocirv_qc_decisions_v1"
          ];
          for (var ki = 0; ki < keysToRead.length; ki++) {
            var rawVal = localStorage.getItem(keysToRead[ki]);
            if (!rawVal) continue;
            try {
              var parsed = JSON.parse(rawVal);
              if (Array.isArray(parsed)) {
                for (var ai = 0; ai < parsed.length; ai++) {
                  if (parsed[ai]) combinedItems.push(parsed[ai]);
                }
              } else if (parsed && typeof parsed === "object") {
                var objKeys = Object.keys(parsed);
                for (var oi = 0; oi < objKeys.length; oi++) {
                  var entry = parsed[objKeys[oi]];
                  if (entry && typeof entry === "object") combinedItems.push(entry);
                }
              }
            } catch (_innerErr) {}
          }

          for (var p = 0; p < combinedItems.length; p++) {
            var pItem = combinedItems[p];
            if (!pItem) continue;
            if (pItem.record_table === "portal_bug_report" || pItem.flag_type === "bug_report") continue;
            var pKey = pItem.replicate_group_key
              ? normalizeReplicateGroupKey(pItem.replicate_group_key)
              : "";
            var matchedLocalId = null;
            if (pKey) {
              for (var k = 0; k < state.decisionsOrder.length; k++) {
                var cand = state.decisionsById[state.decisionsOrder[k]];
                if (
                  cand &&
                  cand.replicate_group_key &&
                  (normalizeReplicateGroupKey(cand.replicate_group_key) === pKey ||
                    matchesReplicateGroupKey(cand.replicate_group_key, pItem.replicate_group_key))
                ) {
                  matchedLocalId = cand.decision_id;
                  break;
                }
              }
            }
            if (!matchedLocalId && pItem.record_id) {
              for (var k2 = 0; k2 < state.decisionsOrder.length; k2++) {
                var cand2 = state.decisionsById[state.decisionsOrder[k2]];
                if (!cand2) continue;
                if (
                  String(cand2.record_id || "") === String(pItem.record_id) ||
                  (Array.isArray(cand2.record_ids) && cand2.record_ids.indexOf(String(pItem.record_id)) !== -1)
                ) {
                  matchedLocalId = cand2.decision_id;
                  break;
                }
              }
            }
            if (matchedLocalId && state.decisionsById[matchedLocalId]) {
              var locDec = state.decisionsById[matchedLocalId];
              mergeFlagTypesIntoDecision(locDec, pItem);
              locDec.submitted_by_email =
                pItem.submitted_by_email ||
                pItem.flagged_by_email ||
                locDec.submitted_by_email;
              locDec.submitted_at =
                pItem.submitted_at ||
                pItem.flagged_at ||
                pItem.created_at ||
                locDec.submitted_at;
              locDec.created_at =
                pItem.created_at ||
                pItem.submitted_at ||
                pItem.flagged_at ||
                locDec.created_at;
              locDec.lab_lineage_note =
                pItem.lab_lineage_note || locDec.lab_lineage_note || "";
              locDec.source_label =
                pItem.source_label || locDec.source_label || "";
              if (pItem.decision_status) {
                locDec.decision_status = pItem.decision_status;
              }
              if (pItem.decision_action) {
                locDec.decision_action = pItem.decision_action;
              }
              if (pItem.triage_scope || pItem.scope || pItem.scope_mode) {
                locDec.scope_mode =
                  pItem.triage_scope || pItem.scope || pItem.scope_mode;
              }
              if (pItem.review_note || pItem.note) {
                locDec.review_note = pItem.review_note || pItem.note;
              }
            } else {
              var matchedGrp = findReplicateGroupForDecision(pItem);
              var grpStats = (matchedGrp && matchedGrp.stats) || {};
              var rawIdCandidate =
                pItem.decision_id && String(pItem.decision_id).indexOf("QC-") === 0
                  ? String(pItem.decision_id)
                  : pItem.api_decision_id != null
                  ? "QC-DB-" + String(pItem.api_decision_id).padStart(4, "0")
                  : "QC-LOCAL-" + String(p + 1).padStart(4, "0");
              var offId = rawIdCandidate;
              while (state.decisionsById[offId]) {
                offId = offId + "-LOC";
              }
              var offCopy = JSON.parse(JSON.stringify(pItem));
              offCopy.decision_id = offId;
              offCopy.db_id =
                typeof pItem.api_decision_id === "number"
                  ? pItem.api_decision_id
                  : typeof pItem.db_id === "number"
                  ? pItem.db_id
                  : null;
              offCopy.replicate_group_key =
                (matchedGrp && matchedGrp.replicate_group_key) ||
                pKey ||
                offCopy.replicate_group_key ||
                "";
              offCopy.resource_name =
                offCopy.resource_name || (matchedGrp && matchedGrp.resource_name) || "";
              offCopy.prepared_sample =
                offCopy.prepared_sample ||
                offCopy.prepared_sample_name ||
                (matchedGrp && matchedGrp.prepared_sample) ||
                "";
              offCopy.field_sample =
                offCopy.field_sample ||
                offCopy.field_sample_name ||
                (matchedGrp && matchedGrp.field_sample) ||
                "";
              offCopy.analysis_type =
                offCopy.analysis_type || (matchedGrp && matchedGrp.analysis_type) || "";
              offCopy.parameter_name =
                offCopy.parameter_name ||
                offCopy.parameter ||
                (matchedGrp && matchedGrp.parameter_name) ||
                "";
              offCopy.unit =
                offCopy.unit || (matchedGrp && matchedGrp.unit) || "";
              offCopy.rsd_pct =
                matchedGrp && matchedGrp.rsd_pct != null
                  ? matchedGrp.rsd_pct
                  : grpStats.rsd_pct != null
                  ? grpStats.rsd_pct
                  : Number(offCopy.rsd_pct || 0);
              offCopy.replicate_count =
                matchedGrp && matchedGrp.replicate_count != null
                  ? matchedGrp.replicate_count
                  : grpStats.count != null
                  ? grpStats.count
                  : (Array.isArray(offCopy.record_ids) && offCopy.record_ids.length) || 1;
              offCopy.submitted_at =
                offCopy.submitted_at ||
                offCopy.flagged_at ||
                offCopy.created_at ||
                null;
              offCopy.created_at =
                offCopy.created_at || offCopy.submitted_at || null;
              offCopy.lab_lineage_note =
                offCopy.lab_lineage_note ||
                (matchedGrp && matchedGrp.lab_lineage_note) ||
                "";
              offCopy.source_label = offCopy.source_label || "";
              offCopy.decision_status =
                offCopy.decision_status || offCopy.status || "in_review";
              var inferredOffFlags = inferInteractiveFlagTypes(offCopy);
              offCopy.flag_type =
                (inferredOffFlags.indexOf("visualizer_flagged") !== -1
                  ? "visualizer_flagged"
                  : inferredOffFlags.indexOf("stat_snapshot_flagged") !== -1
                  ? "stat_snapshot_flagged"
                  : offCopy.flag_type) || "analyst_flagged";
              offCopy.flag_types =
                inferredOffFlags.length > 0
                  ? inferredOffFlags
                  : [offCopy.flag_type];
              offCopy.scope_mode =
                offCopy.triage_scope ||
                offCopy.scope ||
                offCopy.scope_mode ||
                "group";
              state.decisionsById[offId] = offCopy;
              if (state.decisionsOrder.indexOf(offId) === -1) {
                state.decisionsOrder.push(offId);
              }
            }
          }
        } catch (_e) {}
      }

      function initDecisionsFromPayload() {
        var list = WORKBENCH_DATA.decisions || [];
        state.decisionsById = {};
        state.decisionsOrder = [];
        for (var i = 0; i < list.length; i++) {
          var item = JSON.parse(JSON.stringify(list[i]));
          state.decisionsById[item.decision_id] = item;
          state.decisionsOrder.push(item.decision_id);
        }
        mergeLocalStorageDecisionsIntoState();
        if (state.decisionsOrder.length > 0 && !state.selectedDecisionId) {
          state.selectedDecisionId = state.decisionsOrder[0];
          var firstDec = state.decisionsById[state.selectedDecisionId];
          state.selectedGroupKey = firstDec ? firstDec.replicate_group_key : null;
          state.inspectedGroupKey = state.selectedGroupKey;
        }
      }

      var CANONICAL_DOMAIN_SLUGS_MAP = {
        "proximate analysis": "proximate",
        "proximate": "proximate",
        "proximate_record": "proximate",
        "ultimate analysis": "ultimate",
        "ultimate": "ultimate",
        "ultimate_record": "ultimate",
        "compositional analysis": "compositional",
        "compositional": "compositional",
        "compositional_record": "compositional",
        "calorimetry": "calorimetry",
        "calorimetry analysis": "calorimetry",
        "calorimetry_xrd": "calorimetry",
        "calorimetry_record": "calorimetry",
        "xrd": "xrd",
        "xrd analysis": "xrd",
        "xrd_record": "xrd",
        "icp": "icp",
        "icp-oes / icp-ms": "icp",
        "icp elemental analysis": "icp",
        "icp analysis": "icp",
        "icp_record": "icp",
        "xrf": "xrf",
        "xrf elemental": "xrf",
        "xrf elemental analysis": "xrf",
        "xrf analysis": "xrf",
        "xrf_record": "xrf",
        "ash": "xrf",
        "pretreatment": "pretreatment",
        "pretreatment & hydrolysis": "pretreatment",
        "pretreatment_record": "pretreatment",
        "fermentation": "fermentation",
        "fermentation (bioconversion)": "fermentation",
        "fermentation_record": "fermentation",
        "gasification": "gasification",
        "gasification_record": "gasification"
      };

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

      function canonicalDomainSlug(analysisType) {
        if (!analysisType) return "unknown";
        var cleaned = String(analysisType).trim().toLowerCase();
        if (!cleaned) return "unknown";
        if (cleaned.slice(-7) === "_record") {
          cleaned = cleaned.slice(0, -7).trim();
        }
        if (CANONICAL_DOMAIN_SLUGS_MAP[cleaned]) {
          return CANONICAL_DOMAIN_SLUGS_MAP[cleaned];
        }
        var slugs = [
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
        for (var i = 0; i < slugs.length; i++) {
          if (cleaned.indexOf(slugs[i]) !== -1) {
            return slugs[i];
          }
        }
        return cleaned;
      }

      function groupContextLabel(obj) {
        if (!obj || typeof obj !== "object") return "unassigned";
        if (
          typeof obj.group_context_label === "string" &&
          obj.group_context_label.trim() !== ""
        ) {
          return obj.group_context_label.trim();
        }
        var domSlug = canonicalDomainSlug(obj.analysis_type || obj.domain || "");
        var hasPtKey = Object.prototype.hasOwnProperty.call(obj, "pt_method");
        var hasStrainKey = Object.prototype.hasOwnProperty.call(obj, "strain");
        var prep = String(obj.prep_method || "").trim();
        var ptRaw = String(obj.pt_method || "").trim();
        if (domSlug === "pretreatment") {
          var pt = ptRaw || (!hasPtKey ? prep : "") || "none";
          var eh = String(obj.eh_method || "").trim() || "none";
          return eh && eh !== "none" ? pt + " \u00b7 " + eh : pt;
        }
        if (domSlug === "fermentation") {
          var fermPt = ptRaw;
          var strain =
            String(obj.strain || "").trim() ||
            (!hasStrainKey ? prep : "") ||
            "no-strain";
          var base =
            fermPt && fermPt !== "none" ? fermPt + " \u00b7 " + strain : strain;
          var th = obj.time_h;
          if (th !== null && th !== undefined && String(th).trim() !== "") {
            var numTh = Number(th);
            var thFmt = Number.isFinite(numTh)
              ? String(numTh)
              : String(th).trim();
            return base + " @ " + thFmt + "h";
          }
          return base;
        }
        if (domSlug === "gasification") {
          var v =
            String(obj.vessel || "").trim() ||
            String(obj.reactor_type || "").trim() ||
            prep;
          if (v && ["none", "n/a", "unassigned"].indexOf(v.toLowerCase()) === -1) {
            return v.toLowerCase().indexOf("reactor:") === 0 ? v : "Reactor: " + v;
          }
          return "Reactor: Unassigned";
        }
        return prep || "unassigned";
      }

      function computeCanonicalMethodSignature(obj) {
        return groupContextLabel(obj);
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
          var s = rawKeyOrResource.trim();
          if (s.toLowerCase().indexOf("grp::") === 0) {
            s = s.slice(5);
          }
          var parts = s.split("::").map(function (p) {
            return String(p || "").trim().toLowerCase();
          });
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
          var obj = rawKeyOrResource;
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
            String(obj.prepared_sample || "").trim().toLowerCase(),
            canonicalDomainSlug(obj.analysis_type || obj.domain || ""),
            String(obj.parameter_name || obj.parameter || "").trim().toLowerCase(),
            String(groupContextLabel(obj) || "").trim().toLowerCase(),
            String(obj.experiment || "").trim().toLowerCase()
          ].join("::");
        }
        return [
          String(rawKeyOrResource || "").trim().toLowerCase(),
          String(preparedSample || "").trim().toLowerCase(),
          canonicalDomainSlug(analysisType || ""),
          String(parameter || "").trim().toLowerCase(),
          String(prepMethod || "").trim().toLowerCase(),
          String(experiment || "").trim().toLowerCase()
        ].join("::");
      }

      function matchesReplicateGroupKey(a, b) {
        if (!a || !b) return false;
        var na = normalizeReplicateGroupKey(String(a));
        var nb = normalizeReplicateGroupKey(String(b));
        if (!na || !nb) return false;
        if (na === nb) return true;
        var pa = na.split("::");
        var pb = nb.split("::");
        if ((pa.length === 4 || pb.length === 4) && pa.length >= 4 && pb.length >= 4) {
          return pa.slice(0, 4).join("::") === pb.slice(0, 4).join("::");
        }
        return false;
      }

      function findReplicateGroupForDecision(dec) {
        if (!dec) return null;
        var groups = (WORKBENCH_DATA && WORKBENCH_DATA.replicate_groups) || {};
        if (dec.replicate_group_key && groups[dec.replicate_group_key]) {
          return groups[dec.replicate_group_key];
        }
        var groupList = Object.values(groups);
        if (dec.replicate_group_key) {
          for (var i = 0; i < groupList.length; i++) {
            var g = groupList[i];
            if (g && matchesReplicateGroupKey(g.replicate_group_key, dec.replicate_group_key)) {
              return g;
            }
          }
        }
        var targetRecIds = [];
        if (dec.record_id) {
          targetRecIds.push(String(dec.record_id));
        }
        if (Array.isArray(dec.record_ids)) {
          for (var rIdx = 0; rIdx < dec.record_ids.length; rIdx++) {
            if (dec.record_ids[rIdx]) {
              targetRecIds.push(String(dec.record_ids[rIdx]));
            }
          }
        }
        if (targetRecIds.length > 0) {
          for (var k = 0; k < groupList.length; k++) {
            var grp = groupList[k];
            if (!grp) continue;
            if (
              dec.record_table &&
              grp.record_table &&
              String(dec.record_table) !== String(grp.record_table)
            ) {
              continue;
            }
            var recs = grp.records || grp.replicates || [];
            for (var m = 0; m < recs.length; m++) {
              var recId = recs[m] && recs[m].record_id ? String(recs[m].record_id) : "";
              if (recId && targetRecIds.indexOf(recId) !== -1) {
                return grp;
              }
            }
          }
          for (var k2 = 0; k2 < groupList.length; k2++) {
            var grp2 = groupList[k2];
            if (!grp2) continue;
            var recs2 = grp2.records || grp2.replicates || [];
            for (var m2 = 0; m2 < recs2.length; m2++) {
              var recId2 = recs2[m2] && recs2[m2].record_id ? String(recs2[m2].record_id) : "";
              if (recId2 && targetRecIds.indexOf(recId2) !== -1) {
                return grp2;
              }
            }
          }
        }
        return null;
      }

      function populateFacetDropdowns() {
        var facets = WORKBENCH_DATA.facets || {};
        fillSelect("filter-resource", facets.resources || [], "All Resources");
        fillSelect("filter-analysis-type", facets.analysis_types || [], "All Analysis Domains");
        fillSelect("filter-parameter", facets.parameters || [], "All Parameters");
        refreshAnalystFilterOptions();
      }

      function fillSelect(selectId, values, defaultLabel) {
        var sel = document.getElementById(selectId);
        if (!sel) return;
        var currentVal = sel.value;
        sel.innerHTML = "";
        var opt0 = document.createElement("option");
        opt0.value = "";
        opt0.textContent = defaultLabel;
        sel.appendChild(opt0);
        for (var i = 0; i < values.length; i++) {
          var opt = document.createElement("option");
          opt.value = values[i];
          opt.textContent = values[i];
          sel.appendChild(opt);
        }
        sel.value = currentVal;
      }

      function getAnalystOfRecord(dec) {
        if (!dec) return "";
        if (dec.analyst) return String(dec.analyst);
        var grp =
          (WORKBENCH_DATA.replicate_groups || {})[dec.replicate_group_key] ||
          findReplicateGroupForDecision(dec);
        if (grp && grp.replicates && grp.replicates.length > 0) {
          for (var i = 0; i < grp.replicates.length; i++) {
            if (grp.replicates[i].analyst) {
              return String(grp.replicates[i].analyst);
            }
          }
        }
        return "";
      }

      function refreshAnalystFilterOptions() {
        var labAnalysts = {};
        var baseAnalysts = (WORKBENCH_DATA.facets && WORKBENCH_DATA.facets.analysts) || [];
        for (var i = 0; i < baseAnalysts.length; i++) {
          if (baseAnalysts[i]) labAnalysts[baseAnalysts[i]] = true;
        }
        var reviewerEmails = {};
        for (var b = 0; b < baseAnalysts.length; b++) {
          if (baseAnalysts[b]) reviewerEmails[baseAnalysts[b]] = true;
        }
        for (var j = 0; j < state.decisionsOrder.length; j++) {
          var d = state.decisionsById[state.decisionsOrder[j]];
          if (!d) continue;
          var aor = getAnalystOfRecord(d);
          if (aor) labAnalysts[aor] = true;
          if (d.assigned_to_email) {
            reviewerEmails[d.assigned_to_email] = true;
          }
        }

        fillSelect(
          "filter-analyst-of-record",
          Object.keys(labAnalysts).sort(),
          "All Lab Analysts"
        );

        var revSel = document.getElementById("filter-assigned-reviewer");
        if (revSel) {
          var currentRevVal = revSel.value;
          revSel.innerHTML = "";
          var optAllRev = document.createElement("option");
          optAllRev.value = "";
          optAllRev.textContent = "All Reviewers / Unassigned";
          revSel.appendChild(optAllRev);
          var optMeRev = document.createElement("option");
          optMeRev.value = "__ME__";
          optMeRev.textContent = "Assigned to Me (" + (state.user.email || "me") + ")";
          revSel.appendChild(optMeRev);
          var optUnassigned = document.createElement("option");
          optUnassigned.value = "__UNASSIGNED__";
          optUnassigned.textContent = "Unassigned Only";
          revSel.appendChild(optUnassigned);
          var sortedRev = Object.keys(reviewerEmails).sort();
          for (var kr = 0; kr < sortedRev.length; kr++) {
            var orOpt = document.createElement("option");
            orOpt.value = sortedRev[kr];
            orOpt.textContent = sortedRev[kr];
            revSel.appendChild(orOpt);
          }
          revSel.value = currentRevVal;
        }

        var sel = document.getElementById("filter-assigned-analyst");
        var sorted = Object.keys(reviewerEmails).sort();
        if (sel) {
          var currentVal = sel.value;
          sel.innerHTML = "";
          var optAll = document.createElement("option");
          optAll.value = "";
          optAll.textContent = "All Analysts / Unassigned";
          sel.appendChild(optAll);
          var optMe = document.createElement("option");
          optMe.value = "__ME__";
          optMe.textContent = "Assigned to Me (" + (state.user.email || "me") + ")";
          sel.appendChild(optMe);
          for (var k = 0; k < sorted.length; k++) {
            var o = document.createElement("option");
            o.value = sorted[k];
            o.textContent = sorted[k];
            sel.appendChild(o);
          }
          sel.value = currentVal;
        }

        var dataListEl = document.getElementById("AnalystDirectoryList");
        if (dataListEl) {
          dataListEl.innerHTML = "";
          var dlEmails = {};
          if (state.user && state.user.email) {
            dlEmails[state.user.email] = true;
          }
          for (var m = 0; m < sorted.length; m++) {
            dlEmails[sorted[m]] = true;
          }
          var dlSorted = Object.keys(dlEmails).sort();
          for (var n = 0; n < dlSorted.length; n++) {
            var dOpt = document.createElement("option");
            dOpt.value = dlSorted[n];
            dataListEl.appendChild(dOpt);
          }
        }
        var bulkEmailInput = document.getElementById("bulk-assign-email");
        if (
          bulkEmailInput &&
          (!bulkEmailInput.value || bulkEmailInput.value === "analyst@lbl.gov")
        ) {
          bulkEmailInput.value = getDefaultAssigneeEmail("");
        }
      }

      function updateRoleUI() {
        var emailEl = document.getElementById("auth-user-email");
        var badgeEl = document.getElementById("auth-user-role-badge");
        var batchBtn = document.getElementById("btn-sync-gsheet-batch");
        var batchReadonly = document.getElementById("badge-batch-analyst-readonly");
        var singleBtn = document.getElementById("btn-sync-single-gsheet");
        var singleReadonly = document.getElementById("badge-analyst-gsheet-readonly");

        if (emailEl) {
          emailEl.textContent = state.user.email || "analyst@lbl.gov";
        }
        var isAdmin = state.user.role === "admin";
        if (badgeEl) {
          badgeEl.textContent = isAdmin ? "admin" : "analyst";
          badgeEl.className = "role-badge " + (isAdmin ? "role-admin" : "role-analyst");
        }
        if (batchBtn && batchReadonly) {
          batchBtn.style.display = isAdmin ? "inline-flex" : "none";
          batchReadonly.style.display = isAdmin ? "none" : "inline-block";
        }
        if (singleBtn && singleReadonly) {
          singleBtn.style.display = isAdmin ? "inline-flex" : "none";
          singleReadonly.style.display = isAdmin ? "none" : "inline-block";
        }
      }

      function matchesQueueTab(dec, tabName) {
        var status = (dec.decision_status || "open").toLowerCase();
        var synced = Boolean(dec.synced_to_gsheet);
        var assigned = (dec.assigned_to_email || "").toLowerCase();
        var myEmail = (state.user.email || "").toLowerCase();

        if (tabName === "assigned_to_me") {
          return assigned !== "" && assigned === myEmail && status !== "resolved";
        }
        if (tabName === "unassigned") {
          return (
            !assigned &&
            (status === "open" || status === "in_review" || status === "needs_retest")
          );
        }
        if (tabName === "all_open") {
          return (
            status === "open" || status === "in_review" || status === "needs_retest"
          );
        }
        if (tabName === "in_review") {
          return status === "in_review" || status === "needs_retest";
        }
        if (tabName === "pending_gsheet") {
          return status === "resolved" && !synced;
        }
        if (tabName === "synced_gsheet") {
          return status === "resolved" && synced;
        }
        return true;
      }

      function matchesFacetFilters(dec) {
        var f = state.filters;
        if (f.resource && dec.resource_name !== f.resource) return false;
        if (f.analysisType && f.analysisType !== "all") {
          var exactMatch = dec.analysis_type === f.analysisType;
          var slugMatch =
            normalizeDomainKey(dec.analysis_type) === normalizeDomainKey(f.analysisType);
          if (!exactMatch && !slugMatch) return false;
        }
        if (f.parameter && dec.parameter_name !== f.parameter) return false;
        if (f.flagType) {
          var flags = dec.flag_types || dec.flags || (dec.flag_type ? [dec.flag_type] : []);
          var inferredFlags = inferInteractiveFlagTypes(dec);
          for (var ifi = 0; ifi < inferredFlags.length; ifi++) {
            if (flags.indexOf(inferredFlags[ifi]) === -1) {
              flags = flags.concat([inferredFlags[ifi]]);
            }
          }
          if (f.flagType === "interactive_session") {
            if (
              flags.indexOf("visualizer_flagged") === -1 &&
              flags.indexOf("stat_snapshot_flagged") === -1
            ) {
              return false;
            }
          } else if (f.flagType === "rsd_gt_20") {
            if (flags.indexOf("rsd_gt_20") === -1 && Number(dec.rsd_pct || 0) <= 20) {
              return false;
            }
          } else if (f.flagType === "rsd_gt_10") {
            if (flags.indexOf("rsd_gt_10") === -1 && Number(dec.rsd_pct || 0) <= 10) {
              return false;
            }
          } else if (flags.indexOf(f.flagType) === -1) {
            return false;
          }
        }
        if (f.qcStatus) {
          var oldSt = String(
            dec.old_qc_pass || dec.current_qc_status || "pass"
          ).toLowerCase();
          var newSt = String(
            dec.new_qc_pass || dec.new_qc_status || ""
          ).toLowerCase();
          var actStatus = String(dec.decision_status || "").toLowerCase();
          var decAct = String(dec.decision_action || dec.decision || "").toLowerCase();
          var curStatus = String(
            decAct === "reject_fail" || decAct === "exclude_qc_fail"
              ? "fail"
              : (newSt && newSt !== "provisional" && newSt !== "pending" ? newSt : "") ||
                  oldSt ||
                  "pass"
          ).toLowerCase();
          var qcFlags = dec.flag_types || dec.flags || (dec.flag_type ? [dec.flag_type] : []);
          var grp = findReplicateGroupForDecision(dec);
          var reps = (grp && grp.replicates) || [];
          var repStates = {};
          for (var ri = 0; ri < reps.length; ri++) {
            var st = String(reps[ri].qc_pass || reps[ri].qc_status || "pass").toLowerCase();
            repStates[st] = true;
          }
          var distinctStates = Object.keys(repStates);
          var isMixed =
            distinctStates.length > 1 ||
            curStatus === "mixed" ||
            qcFlags.indexOf("mixed_qc") !== -1;
          if (f.qcStatus === "mixed") {
            if (!isMixed) return false;
          } else if (f.qcStatus === "needs_retest") {
            if (
              curStatus !== "needs_retest" &&
              actStatus !== "needs_retest" &&
              decAct !== "needs_retest" &&
              decAct !== "mark_needs_retest" &&
              !repStates["needs_retest"]
            ) {
              return false;
            }
          } else if (f.qcStatus === "provisional") {
            if (
              curStatus !== "provisional" &&
              actStatus !== "in_review" &&
              !repStates["provisional"]
            ) {
              return false;
            }
          } else if (f.qcStatus === "pass" || f.qcStatus === "qc_pass") {
            if (
              curStatus !== "pass" ||
              (oldSt === "fail" && newSt !== "pass") ||
              newSt === "fail" ||
              decAct === "reject_fail" ||
              decAct === "exclude_qc_fail"
            ) {
              return false;
            }
          } else if (f.qcStatus === "fail" || f.qcStatus === "qc_fail") {
            if (curStatus !== "fail" && oldSt !== "fail" && newSt !== "fail" && !repStates["fail"]) {
              return false;
            }
          } else {
            if (curStatus !== f.qcStatus && !repStates[f.qcStatus]) {
              return false;
            }
          }
        }
        if (Number(f.minRsd || 0) > 0) {
          if (Number(dec.rsd_pct || 0) <= Number(f.minRsd)) return false;
        }
        if (f.analystOfRecord) {
          var aor = getAnalystOfRecord(dec);
          if (aor !== f.analystOfRecord) return false;
        }
        if (f.assignedReviewer) {
          var assignedEmail = (dec.assigned_to_email || "").trim();
          if (f.assignedReviewer === "__ME__") {
            if (assignedEmail.toLowerCase() !== (state.user.email || "").toLowerCase()) {
              return false;
            }
          } else if (f.assignedReviewer === "__UNASSIGNED__") {
            if (assignedEmail !== "") {
              return false;
            }
          } else if (assignedEmail !== f.assignedReviewer) {
            return false;
          }
        }
        if (f.assignedAnalyst) {
          if (f.assignedAnalyst === "__ME__") {
            if ((dec.assigned_to_email || "").toLowerCase() !== (state.user.email || "").toLowerCase()) {
              return false;
            }
          } else if (
            (dec.assigned_to_email || "") !== f.assignedAnalyst &&
            (dec.analyst || "") !== f.assignedAnalyst
          ) {
            return false;
          }
        }
        if (f.search) {
          var q = f.search.toLowerCase();
          var hay = [
            dec.decision_id,
            dec.resource_name,
            dec.prepared_sample,
            dec.field_sample,
            dec.parameter_name,
            dec.record_id,
            (dec.record_ids || []).join(" "),
            dec.flag_type,
            (dec.flag_types || []).join(" "),
            dec.source_label,
            dec.submitted_by_email,
            dec.assigned_to_email,
            getAnalystOfRecord(dec),
            dec.review_note,
            dec.scope_mode
          ]
            .join(" ")
            .toLowerCase();
          if (hay.indexOf(q) === -1) return false;
        }
        return true;
      }

      function setQuickFlagFilter(flagTypeVal) {
        mergeLocalStorageDecisionsIntoState();
        var nextVal = flagTypeVal || "";
        if (state.filters.flagType === nextVal && nextVal !== "") {
          nextVal = "";
        }
        state.filters.flagType = nextVal;
        if (
          nextVal &&
          (state.activeQueueTab === "pending_gsheet" ||
            state.activeQueueTab === "synced_gsheet")
        ) {
          state.activeQueueTab = "all_open";
          var tabBtns = document.querySelectorAll("#queue-tabs-container .queue-tab");
          for (var ti = 0; ti < tabBtns.length; ti++) {
            var tName = tabBtns[ti].getAttribute("data-queue-tab");
            tabBtns[ti].classList.toggle("active", tName === "all_open");
          }
        }
        var sel = document.getElementById("filter-flag-type");
        if (sel) sel.value = nextVal;
        renderQueueTable();
        refreshQcStateFromApi();
      }

      function setQueueSortBy(sortVal) {
        var nextSort = sortVal || "default";
        state.filters.sortBy = nextSort;
        state.queueSort = nextSort;
        var sel = document.getElementById("filter-sort-by");
        if (sel) sel.value = nextSort;
        var sortQ = document.getElementById("sort-queue-select");
        if (sortQ) sortQ.value = nextSort;
        renderQueueTable();
      }

      function setMinRsdFilter(val) {
        var num = Math.max(0, Math.min(50, Number(val || 0)));
        state.filters.minRsd = num;
        var slider = document.getElementById("filter-min-rsd");
        if (slider) slider.value = String(num);
        var valEl = document.getElementById("filter-min-rsd-val");
        if (valEl) valEl.textContent = num === 0 ? "\u2265 0% (All)" : num + "%";
        var presets = [0, 10, 20];
        for (var pi = 0; pi < presets.length; pi++) {
          var pBtn = document.getElementById("btn-rsd-preset-" + presets[pi]);
          if (pBtn && pBtn.classList) {
            if (num === presets[pi]) pBtn.classList.add("active");
            else pBtn.classList.remove("active");
          }
        }
        renderQueueTable();
      }

      function resetAllFilters() {
        state.filters.resource = "";
        state.filters.analysisType = "";
        state.filters.parameter = "";
        state.filters.flagType = "";
        state.filters.qcStatus = "";
        state.filters.minRsd = 0;
        state.filters.analystOfRecord = "";
        state.filters.assignedReviewer = "";
        state.filters.assignedAnalyst = "";
        state.filters.sortBy = "default";
        state.filters.search = "";
        var filterIds = [
          "filter-resource",
          "filter-analysis-type",
          "filter-parameter",
          "filter-flag-type",
          "filter-qc-status",
          "filter-analyst-of-record",
          "filter-assigned-reviewer",
          "filter-assigned-analyst",
          "filter-search"
        ];
        for (var fi = 0; fi < filterIds.length; fi++) {
          var el = document.getElementById(filterIds[fi]);
          if (el) el.value = "";
        }
        var sortEl = document.getElementById("filter-sort-by");
        if (sortEl) sortEl.value = "default";
        setMinRsdFilter(0);
      }

      if (typeof window !== "undefined") {
        window.setMinRsdFilter = setMinRsdFilter;
        window.setQuickFlagFilter = setQuickFlagFilter;
        window.setQueueSortBy = setQueueSortBy;
        window.resetAllFilters = resetAllFilters;
        window.computeCanonicalMethodSignature = computeCanonicalMethodSignature;
      }

      function computeQueueCounts() {
        var counts = {
          assigned_to_me: 0,
          unassigned: 0,
          all_open: 0,
          in_review: 0,
          pending_gsheet: 0,
          synced_gsheet: 0
        };
        for (var i = 0; i < state.decisionsOrder.length; i++) {
          var dec = state.decisionsById[state.decisionsOrder[i]];
          if (!dec) continue;
          if (matchesQueueTab(dec, "assigned_to_me")) counts.assigned_to_me++;
          if (matchesQueueTab(dec, "unassigned")) counts.unassigned++;
          if (matchesQueueTab(dec, "all_open")) counts.all_open++;
          if (matchesQueueTab(dec, "in_review")) counts.in_review++;
          if (matchesQueueTab(dec, "pending_gsheet")) counts.pending_gsheet++;
          if (matchesQueueTab(dec, "synced_gsheet")) counts.synced_gsheet++;
        }

        setText("count-assigned-to-me", counts.assigned_to_me);
        setText("count-unassigned", counts.unassigned);
        setText("count-all-open", counts.all_open);
        setText("count-in-review", counts.in_review);
        setText("count-pending-gsheet", counts.pending_gsheet);
        setText("count-synced-gsheet", counts.synced_gsheet);
        setText("count-batch-sync-btn", counts.pending_gsheet);
        setText("kpi-assigned-me", counts.assigned_to_me);
        setText("kpi-pending-gsheet", counts.pending_gsheet);
      }

      function renderKpis() {
        computeQueueCounts();
      }

      function setText(id, val) {
        var el = document.getElementById(id);
        if (el) el.textContent = String(val);
      }

      function isInteractiveFlaggedDecision(dec) {
        if (!dec) return false;
        var flags = inferInteractiveFlagTypes(dec);
        return (
          flags.indexOf("visualizer_flagged") !== -1 ||
          flags.indexOf("stat_snapshot_flagged") !== -1
        );
      }

      function getVisibleQueueDecisionIds() {
        var visibleIds = [];
        for (var i = 0; i < state.decisionsOrder.length; i++) {
          var id = state.decisionsOrder[i];
          var dec = state.decisionsById[id];
          if (!dec) continue;
          if (!matchesQueueTab(dec, state.activeQueueTab)) continue;
          if (!matchesFacetFilters(dec)) continue;
          visibleIds.push(id);
        }
        var sortBy = (state.filters && state.filters.sortBy) || "default";
        if (sortBy && sortBy !== "default" && visibleIds.length > 1) {
          visibleIds.sort(function (idA, idB) {
            var a = state.decisionsById[idA] || {};
            var b = state.decisionsById[idB] || {};
            if (sortBy === "interactive_first") {
              var aInt = isInteractiveFlaggedDecision(a) ? 1 : 0;
              var bInt = isInteractiveFlaggedDecision(b) ? 1 : 0;
              if (aInt !== bInt) return bInt - aInt;
              var aTs = String(a.submitted_at || a.created_at || "");
              var bTs = String(b.submitted_at || b.created_at || "");
              if (aTs !== bTs) return bTs.localeCompare(aTs);
            } else if (sortBy === "recent_first") {
              var aTime = String(a.submitted_at || a.created_at || "");
              var bTime = String(b.submitted_at || b.created_at || "");
              if (aTime !== bTime) return bTime.localeCompare(aTime);
            } else if (sortBy === "rsd_desc") {
              var aRsd = Number(a.rsd_pct || 0);
              var bRsd = Number(b.rsd_pct || 0);
              if (aRsd !== bRsd) return bRsd - aRsd;
            } else if (sortBy === "rsd_asc") {
              var aRsdAsc = Number(a.rsd_pct || 0);
              var bRsdAsc = Number(b.rsd_pct || 0);
              if (aRsdAsc !== bRsdAsc) return aRsdAsc - bRsdAsc;
            } else if (sortBy === "flag_severity") {
              var sevA =
                ((a.flag_types || []).indexOf("rsd_gt_20") !== -1 ? 100 : 0) +
                ((a.flag_types || []).length || 1) * 10 +
                Number(a.rsd_pct || 0);
              var sevB =
                ((b.flag_types || []).indexOf("rsd_gt_20") !== -1 ? 100 : 0) +
                ((b.flag_types || []).length || 1) * 10 +
                Number(b.rsd_pct || 0);
              if (sevB !== sevA) return sevB - sevA;
            } else if (sortBy === "resource_asc") {
              var resCmp = String(a.resource_name || "").localeCompare(
                String(b.resource_name || "")
              );
              if (resCmp !== 0) return resCmp;
            } else if (sortBy === "sample_asc") {
              var smpCmp = String(a.prepared_sample || "").localeCompare(
                String(b.prepared_sample || "")
              );
              if (smpCmp !== 0) return smpCmp;
            } else if (sortBy === "flagged_by") {
              var aWho = String(a.submitted_by_email || "zzzz").toLowerCase();
              var bWho = String(b.submitted_by_email || "zzzz").toLowerCase();
              if (aWho !== bWho) return aWho.localeCompare(bWho);
            } else if (sortBy === "scope") {
              var aScope = String(a.scope_mode || a.triage_scope || "group");
              var bScope = String(b.scope_mode || b.triage_scope || "group");
              if (aScope !== bScope) return aScope.localeCompare(bScope);
            } else if (sortBy === "resource_param") {
              var aKey =
                String(a.resource_name || "") + "::" + String(a.parameter_name || "");
              var bKey =
                String(b.resource_name || "") + "::" + String(b.parameter_name || "");
              if (aKey !== bKey) return aKey.localeCompare(bKey);
            }
            return String(idA).localeCompare(String(idB));
          });
        }
        return visibleIds;
      }

      function updateBulkAssignBar(visibleIdsOpt) {
        var visibleIds = Array.isArray(visibleIdsOpt)
          ? visibleIdsOpt
          : getVisibleQueueDecisionIds();
        var selectedCount = state.selectedIds ? state.selectedIds.size : 0;
        setText("bulk-selected-count", selectedCount + " selected");

        var allVisibleSelected =
          visibleIds.length > 0 &&
          visibleIds.every(function (id) {
            return state.selectedIds && state.selectedIds.has(id);
          });
        var chkBar = document.getElementById("chk-select-all-filtered");
        if (chkBar) chkBar.checked = allVisibleSelected;
        var chkHeader = document.getElementById("chk-select-all-header");
        if (chkHeader) chkHeader.checked = allVisibleSelected;

        var bulkEmailEl = document.getElementById("bulk-assign-email");
        if (bulkEmailEl && !bulkEmailEl.value) {
          bulkEmailEl.value = getDefaultAssigneeEmail("");
        }
        var applyBtn = document.getElementById("btn-bulk-assign-apply");
        if (applyBtn) applyBtn.disabled = selectedCount === 0;
        var clearBtn =
          document.getElementById("btn-clear-selection") ||
          document.getElementById("btn-bulk-clear-selection");
        if (clearBtn) clearBtn.disabled = selectedCount === 0;
      }

      function fillBulkAssignMyEmail() {
        var bulkEmailEl = document.getElementById("bulk-assign-email");
        var myEmail = getDefaultAssigneeEmail("");
        if (bulkEmailEl) {
          bulkEmailEl.value = myEmail;
        }
        return myEmail;
      }

      function toggleRowSelection(decisionId, checked) {
        if (!decisionId) return;
        if (!state.selectedIds) state.selectedIds = new Set();
        var shouldSelect =
          checked !== undefined
            ? Boolean(checked)
            : !state.selectedIds.has(decisionId);
        if (shouldSelect) {
          state.selectedIds.add(decisionId);
        } else {
          state.selectedIds.delete(decisionId);
        }
        var chks = document.querySelectorAll(".qc-row-select-chk");
        for (var i = 0; i < chks.length; i++) {
          if (chks[i].getAttribute("data-decision-id") === decisionId) {
            chks[i].checked = shouldSelect;
          }
        }
        updateBulkAssignBar();
      }

      function toggleSelectAllFiltered(checked) {
        if (!state.selectedIds) state.selectedIds = new Set();
        var visibleIds = getVisibleQueueDecisionIds();
        var shouldSelect = Boolean(checked);
        for (var i = 0; i < visibleIds.length; i++) {
          if (shouldSelect) {
            state.selectedIds.add(visibleIds[i]);
          } else {
            state.selectedIds.delete(visibleIds[i]);
          }
        }
        renderQueueTable();
      }

      function selectAllFilteredRows() {
        toggleSelectAllFiltered(true);
      }

      function clearRowSelection() {
        if (state.selectedIds) state.selectedIds.clear();
        renderQueueTable();
      }

      function bulkAssignSelected(overrideEmail) {
        var bulkEmailEl = document.getElementById("bulk-assign-email");
        var rawEmail =
          overrideEmail !== undefined && overrideEmail !== null
            ? String(overrideEmail)
            : (bulkEmailEl && bulkEmailEl.value) || getDefaultAssigneeEmail("");
        var targetEmail = String(rawEmail || "").trim().toLowerCase();
        var selectedIdsList = state.selectedIds
          ? Array.from(state.selectedIds)
          : [];
        if (selectedIdsList.length === 0) {
          showToast("Select at least one QC queue row to bulk-assign.", true);
          return Promise.resolve({ ok: false, assigned_count: 0 });
        }
        if (!targetEmail) {
          showToast(
            "Enter a target analyst email address for bulk assignment.",
            true
          );
          return Promise.resolve({ ok: false, assigned_count: 0 });
        }
        if (bulkEmailEl) bulkEmailEl.value = targetEmail;

        var actorEmail =
          getDefaultAssigneeEmail((state.user && state.user.email) || "") ||
          null;
        var nowIso = new Date().toISOString();
        var itemsPayload = [];
        var selectedDecisions = [];
        for (var i = 0; i < selectedIdsList.length; i++) {
          var d = state.decisionsById[selectedIdsList[i]];
          if (!d) continue;
          selectedDecisions.push(d);
          d.assigned_to_email = targetEmail;
          d.assigned_by_email = actorEmail;
          var curSt = String(d.decision_status || "open").toLowerCase();
          if (!curSt || curSt === "open" || curSt === "pending") {
            d.decision_status = "in_review";
          }
          if (!Array.isArray(d.audit_history)) {
            d.audit_history = [];
          }
          d.audit_history.push({
            action: "bulk_assign",
            assigned_to_email: targetEmail,
            assigned_by_email: actorEmail,
            actor_email: actorEmail,
            timestamp: nowIso
          });
          itemsPayload.push({
            decision_id:
              typeof d.db_id === "number" && Number.isInteger(d.db_id)
                ? d.db_id
                : d.decision_id,
            record_table: d.record_table || "proximate_record",
            record_id: d.record_id ? String(d.record_id) : null,
            record_ids: Array.isArray(d.record_ids)
              ? d.record_ids
              : d.record_id
                ? [String(d.record_id)]
                : [],
            replicate_group_key: d.replicate_group_key || null,
            resource_name: d.resource_name || "unknown",
            analysis_type: d.analysis_type || null,
            parameter_name: d.parameter_name || null,
            flag_type:
              d.flag_type ||
              (Array.isArray(d.flag_types) && d.flag_types[0]) ||
              "statistical_outlier",
            flag_trigger_value: d.flag_trigger_value || null,
            old_qc_pass: d.old_qc_pass || "pass",
            review_note: d.review_note || ""
          });
        }

        var syncedOnline = false;
        return fetch("/v1/qc/decisions/assign-batch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({
            assigned_to_email: targetEmail,
            assigned_by_email: actorEmail,
            items: itemsPayload
          })
        })
          .then(function (resp) {
            if (resp && resp.ok) {
              return resp.json().then(function (data) {
                syncedOnline = true;
                return data;
              });
            }
            return null;
          })
          .then(function (resData) {
            if (resData && Array.isArray(resData.decisions)) {
              for (var k = 0; k < resData.decisions.length; k++) {
                var apiDec = resData.decisions[k];
                var localDec = selectedDecisions[k];
                if (apiDec && localDec) {
                  if (apiDec.id != null) {
                    localDec.db_id = Number(apiDec.id);
                  }
                  if (apiDec.assigned_to_email) {
                    localDec.assigned_to_email = apiDec.assigned_to_email;
                  }
                  if (apiDec.decision_status) {
                    localDec.decision_status = apiDec.decision_status;
                  }
                }
              }
            }
          })
          .catch(function () {
            syncedOnline = false;
          })
          .finally(function () {
            if (qcBroadcastChannel) {
              try {
                qcBroadcastChannel.postMessage({
                  type: "qc_decision_saved",
                  decision_id: selectedIdsList[0] || "batch",
                  assigned_to_email: targetEmail,
                  updated_at: new Date().toISOString()
                });
              } catch (_e) {}
            }
            if (state.selectedIds) {
              state.selectedIds.clear();
            }
            if (syncedOnline) {
              showToast(
                "Bulk-assigned " +
                  selectedDecisions.length +
                  " QC item(s) to " +
                  targetEmail +
                  ".",
                false
              );
            } else {
              showToast(
                "Bulk-assigned " +
                  selectedDecisions.length +
                  " QC item(s) locally to " +
                  targetEmail +
                  " (offline fallback — API unreachable).",
                true
              );
            }
            refreshAnalystFilterOptions();
            renderQueueTable();
            renderContextualDrawer();
          })
          .then(function () {
            return {
              ok: true,
              online: syncedOnline,
              status: syncedOnline ? "assigned" : "assigned_offline",
              assigned_count: selectedDecisions.length,
              assigned_to_email: targetEmail
            };
          });
      }

      if (typeof window !== "undefined") {
        window.getVisibleQueueDecisionIds = getVisibleQueueDecisionIds;
        window.toggleRowSelection = toggleRowSelection;
        window.toggleSelectAllFiltered = toggleSelectAllFiltered;
        window.selectAllFilteredRows = selectAllFilteredRows;
        window.clearRowSelection = clearRowSelection;
        window.fillBulkAssignMyEmail = fillBulkAssignMyEmail;
        window.bulkAssignSelected = bulkAssignSelected;
        window.updateBulkAssignBar = updateBulkAssignBar;
      }

      function renderQueueTable() {
        computeQueueCounts();
        var tbody = document.getElementById("qc-queue-tbody");
        if (!tbody) return;
        tbody.innerHTML = "";

        var rsdTh = document.getElementById("th-sort-rsd");
        if (rsdTh) {
          rsdTh.textContent =
            state.queueSort === "rsd_asc" ? "RSD % (n) ↑" : "RSD % (n) ↓";
        }

        var visibleIds = getVisibleQueueDecisionIds();

        if (visibleIds.length === 0) {
          var emptyTr = document.createElement("tr");
          var emptyTd = document.createElement("td");
          emptyTd.colSpan = 13;
          emptyTd.style.textAlign = "center";
          emptyTd.style.padding = "20px";
          emptyTd.style.color = "#64748b";
          emptyTd.textContent = "No QC items match the current queue tab and facet filters.";
          emptyTr.appendChild(emptyTd);
          tbody.appendChild(emptyTr);
          updateBulkAssignBar(visibleIds);
          return;
        }

        for (var j = 0; j < visibleIds.length; j++) {
          var decItem = state.decisionsById[visibleIds[j]];
          var isRowChecked =
            state.selectedIds && state.selectedIds.has(decItem.decision_id);
          var tr = document.createElement("tr");
          tr.className =
            "queue-row" +
            (decItem.decision_id === state.selectedDecisionId ? " selected" : "");
          tr.setAttribute("data-decision-id", decItem.decision_id);

          var rowFlagList = inferInteractiveFlagTypes(decItem);
          if (rowFlagList.length === 0) {
            rowFlagList = decItem.flag_types || [decItem.flag_type || "analyst_flagged"];
          }
          var flagsHtml = rowFlagList
            .map(function (ft) {
              var badgePrefix = "";
              var badgeTitle = ft;
              if (ft === "visualizer_flagged") {
                badgePrefix = "🔬 ";
                badgeTitle = "Flagged interactively in Page 3 Data Visualizer";
              } else if (ft === "stat_snapshot_flagged") {
                badgePrefix = "📊 ";
                badgeTitle = "Flagged interactively in Page 2 Statistical Snapshot";
              } else if (ft === "analyst_flagged") {
                badgePrefix = "📋 ";
                badgeTitle = "Legacy GSheet QC Fail / Analyst Flag";
              }
              return (
                '<span class="flag-pill flag-' +
                escapeHtml(ft) +
                '" title="' +
                escapeHtml(badgeTitle) +
                '">' +
                badgePrefix +
                escapeHtml(ft) +
                "</span>"
              );
            })
            .join("");
          var showMeBtnHtml =
            ' <button type="button" class="btn-show-me-flag" data-decision-id="' +
            escapeHtml(decItem.decision_id) +
            '" data-group-key="' +
            escapeHtml(decItem.replicate_group_key || "") +
            '" title="Show flagged replicate group and outlier in slice context" style="margin-left:4px;padding:1px 6px;border-radius:5px;font-size:10px;font-weight:600;background:rgba(56,189,248,0.16);color:#38bdf8;border:1px solid rgba(56,189,248,0.45);cursor:pointer;" onclick="event.stopPropagation(); window.openFlagShowMePopover && window.openFlagShowMePopover({ decisionId: this.getAttribute(&quot;data-decision-id&quot;), replicateGroupKey: this.getAttribute(&quot;data-group-key&quot;) }, this);">👁 Show me</button>';
          var provSummaryHtml = "";
          if (
            isInteractiveFlaggedDecision(decItem) ||
            decItem.source_label ||
            (decItem.submitted_by_email &&
              decItem.submitted_by_email !== "auto-qc-engine@biocirv.org")
          ) {
            var provParts = [];
            if (decItem.source_label) {
              provParts.push(escapeHtml(decItem.source_label));
            }
            if (
              decItem.submitted_by_email &&
              decItem.submitted_by_email !== "auto-qc-engine@biocirv.org"
            ) {
              provParts.push("by " + escapeHtml(decItem.submitted_by_email));
            }
            var scopeTag =
              (decItem.scope_mode || decItem.triage_scope) === "single"
                ? "Single Point"
                : "Replicate Group";
            provParts.push("scope: " + scopeTag);
            if (decItem.submitted_at) {
              provParts.push(escapeHtml(String(decItem.submitted_at).slice(0, 19).replace("T", " ")));
            }
            provSummaryHtml =
              "<div class='queue-prov-meta' style='font-size:10.5px;color:#94a3b8;margin-top:3px;'>" +
              provParts.join(" • ") +
              "</div>";
          }

          var statusClass = "status-" + (decItem.decision_status || "open");
          var stageLabel =
            decItem.decision_status === "resolved"
              ? decItem.synced_to_gsheet
                ? "Synced to GSheet"
                : "Pending Admin GSheet Sync"
              : decItem.decision_status || "open";
          if (decItem.synced_to_gsheet) {
            statusClass = "status-synced";
          }
          var analystOfRecord = getAnalystOfRecord(decItem) || "—";

          tr.innerHTML =
            "<td style='text-align:center;' class='qc-row-select-cell'><input type='checkbox' class='qc-row-select-chk' data-decision-id='" +
            escapeHtml(decItem.decision_id) +
            "'" +
            (isRowChecked ? " checked" : "") +
            " onclick='event.stopPropagation(); window.toggleRowSelection && window.toggleRowSelection(this.dataset.decisionId, this.checked);' /></td>" +
            "<td><code>" +
            escapeHtml(decItem.decision_id) +
            "</code></td>" +
            "<td>" +
            escapeHtml(decItem.resource_name) +
            "</td>" +
            "<td><code>" +
            escapeHtml(decItem.prepared_sample) +
            "</code></td>" +
            "<td>" +
            escapeHtml(decItem.analysis_type) +
            "</td>" +
            "<td><strong>" +
            escapeHtml(decItem.parameter_name) +
            "</strong> <span style='color:#64748b;font-size:11px;'>(" +
            escapeHtml(decItem.unit || "") +
            ")</span></td>" +
            "<td>" +
            flagsHtml +
            showMeBtnHtml +
            provSummaryHtml +
            "</td>" +
            "<td>" +
            escapeHtml(decItem.flag_trigger_value || "") +
            "</td>" +
            "<td>" +
            Number(decItem.rsd_pct || 0).toFixed(1) +
            "% (n=" +
            Number(decItem.replicate_count || 1) +
            ")</td>" +
            "<td>" +
            escapeHtml(analystOfRecord) +
            "</td>" +
            "<td>" +
            escapeHtml(decItem.assigned_to_email || "Unassigned") +
            "</td>" +
            "<td><span class='transition-badge'>" +
            escapeHtml(decItem.old_qc_pass || "pass") +
            " → " +
            escapeHtml(decItem.new_qc_pass || "pass") +
            "</span></td>" +
            "<td><span class='status-pill " +
            statusClass +
            "'>" +
            escapeHtml(stageLabel) +
            "</span></td>";

          (function (clickedId) {
            tr.addEventListener("click", function () {
              selectDecision(clickedId, true);
            });
          })(decItem.decision_id);

          tbody.appendChild(tr);
        }
        updateBulkAssignBar(visibleIds);
      }

      function selectDecision(decisionId, updateUrl) {
        var dec = state.decisionsById[decisionId];
        if (!dec) return;
        var matchedGroup = findReplicateGroupForDecision(dec);
        var resolvedGroupKey =
          (matchedGroup && matchedGroup.replicate_group_key) || dec.replicate_group_key;
        state.selectedDecisionId = decisionId;
        state.selectedGroupKey = resolvedGroupKey;
        state.inspectedGroupKey = resolvedGroupKey;
        state.scopeMode = dec.scope_mode || "group";

        // Default replicate checkboxes
        state.selectedReplicateIds = {};
        var rIds = dec.record_ids || [dec.record_id];
        for (var i = 0; i < rIds.length; i++) {
          state.selectedReplicateIds[rIds[i]] = true;
        }

        // Default rationale chips
        state.selectedChips = {};
        var chips = dec.rationale_chips || [];
        for (var c = 0; c < chips.length; c++) {
          state.selectedChips[chips[c]] = true;
        }

        if (updateUrl && typeof window !== "undefined" && window.history && window.history.replaceState) {
          var newUrl =
            window.location.pathname +
            "?decision_id=" +
            encodeURIComponent(decisionId) +
            "&replicate_group_key=" +
            encodeURIComponent(resolvedGroupKey || dec.replicate_group_key || "");
          window.history.replaceState({ decision_id: decisionId }, "", newUrl);
        }

        renderQueueTable();
        renderContextualDrawer();
      }

      var selectQueueRow = selectDecision;

      function isDecisionLocked(dec) {
        if (!dec) return false;
        return (
          String(dec.decision_status || "").toLowerCase() === "resolved" ||
          Boolean(dec.synced_to_gsheet)
        );
      }

      function applyDecisionLockUI(dec) {
        var locked = isDecisionLocked(dec);
        var lockBanner = document.getElementById("decision-lock-banner");
        var revertBtn = document.getElementById("btn-revert-decision");
        if (lockBanner) {
          lockBanner.classList.toggle("hidden", !locked);
        }
        if (revertBtn) {
          revertBtn.classList.toggle("hidden", !locked);
        }

        var actionSel = document.getElementById("select-decision-action");
        if (actionSel) actionSel.disabled = locked;

        var noteInput = document.getElementById("input-review-note");
        if (noteInput) noteInput.disabled = locked;

        var saveBtn = document.getElementById("btn-save-decision");
        if (saveBtn) saveBtn.disabled = locked;

        var scopeRadios = document.querySelectorAll(".scope-radio");
        for (var r = 0; r < scopeRadios.length; r++) {
          scopeRadios[r].disabled = locked;
        }

        var chipEls = document.querySelectorAll("#rationale-chips-list .rationale-chip");
        for (var c = 0; c < chipEls.length; c++) {
          chipEls[c].classList.toggle("disabled", locked);
          if (locked) {
            chipEls[c].setAttribute("aria-disabled", "true");
          } else {
            chipEls[c].removeAttribute("aria-disabled");
          }
        }

        var repCheckboxes = document.querySelectorAll(".replicate-checkbox");
        for (var k = 0; k < repCheckboxes.length; k++) {
          repCheckboxes[k].disabled = locked || state.scopeMode === "group";
        }
      }

      function renderContextualDrawer() {
        var dec = state.decisionsById[state.selectedDecisionId];
        if (!dec) return;
        var group = findReplicateGroupForDecision(dec);
        var resolvedGroupKey =
          (group && group.replicate_group_key) || dec.replicate_group_key || "";
        var resolvedSample =
          dec.prepared_sample || (group && group.prepared_sample) || "";
        var resolvedResource =
          dec.resource_name || (group && group.resource_name) || "";

        setText(
          "drawer-title",
          dec.decision_id +
            " • " +
            resolvedResource +
            " — " +
            (dec.parameter_name || (group && group.parameter_name) || "") +
            " (" +
            resolvedSample +
            ")"
        );
        setText(
          "drawer-subtitle",
          (dec.analysis_type || (group && group.analysis_type) || "") +
            " • Table: " +
            (dec.record_table || (group && group.record_table) || "proximate_record")
        );
        setText(
          "drawer-deeplink-code",
          "?decision_id=" + dec.decision_id + "&replicate_group_key=" + resolvedGroupKey
        );
        var drawerShowMeBtn = document.getElementById("btn-drawer-show-me-flag");
        if (drawerShowMeBtn) {
          drawerShowMeBtn.setAttribute("data-decision-id", dec.decision_id || "");
          drawerShowMeBtn.setAttribute("data-group-key", resolvedGroupKey || "");
        }

        // Populate Co-Measured Parameter selector on same prepared_sample
        var sampleKey = resolvedResource + "::" + resolvedSample;
        var coList = (WORKBENCH_DATA.co_measured_by_sample || {})[sampleKey] || [];
        var coSelect = document.getElementById("select-co-measured-param");
        if (coSelect) {
          coSelect.innerHTML = "";
          for (var i = 0; i < coList.length; i++) {
            var item = coList[i];
            var opt = document.createElement("option");
            opt.value = item.replicate_group_key;
            var flagSuffix =
              item.flag_types && item.flag_types.length
                ? " [FLAG: " + item.flag_types.join(",") + "]"
                : "";
            opt.textContent =
              item.parameter_name +
              " (" +
              item.analysis_type +
              " • mean " +
              item.mean +
              " " +
              (item.unit || "") +
              ")" +
              flagSuffix;
              coSelect.appendChild(opt);
          }
          coSelect.value = state.inspectedGroupKey || resolvedGroupKey;
        }

        // Render Left Pane Plot
        renderDiagnosticPlot();

        // Render Right Pane Replicate Breakdown
        renderReplicateBreakdown(dec, group);

        // Sync form inputs
        var scopeGroupRadio = document.getElementById("scope-entire-group");
        var scopeSingleRadio = document.getElementById("scope-single-replicate");
        if (scopeGroupRadio && scopeSingleRadio) {
          scopeGroupRadio.checked = state.scopeMode === "group";
          scopeSingleRadio.checked = state.scopeMode === "single";
        }

        var chipEls = document.querySelectorAll("#rationale-chips-list .rationale-chip");
        for (var j = 0; j < chipEls.length; j++) {
          var chipVal = chipEls[j].getAttribute("data-chip");
          if (state.selectedChips[chipVal]) {
            chipEls[j].classList.add("selected");
          } else {
            chipEls[j].classList.remove("selected");
          }
        }

        var actionSel = document.getElementById("select-decision-action");
        if (actionSel) {
          var rawAct = dec.decision_action || "";
          if (rawAct === "mark_fail") rawAct = "reject_fail";
          if (rawAct === "retest") rawAct = "needs_retest";
          if (rawAct === "defer") rawAct = "in_review";
          actionSel.value =
            rawAct && rawAct !== "open" ? rawAct : "in_review";
        }
        var assignedInput = document.getElementById("input-assigned-to");
        if (assignedInput) {
          assignedInput.value = getDefaultAssigneeEmail(dec.assigned_to_email);
        }
        var noteInput = document.getElementById("input-review-note");
        if (noteInput) {
          noteInput.value = dec.review_note || "";
        }

        // Apply lock/revert state for resolved or synced records
        applyDecisionLockUI(dec);

        // Update 4-step Audit Provenance Timeline
        setText("prov-created-by", dec.submitted_by_email || "auto-qc-engine@biocirv.org");
        setText(
          "prov-created-at",
          dec.submitted_at || dec.created_at || WORKBENCH_DATA.generated_utc || "—"
        );
        var provSrcBadge = document.getElementById("prov-source-badge");
        if (provSrcBadge) {
          if (dec.source_label) {
            provSrcBadge.textContent = dec.source_label;
            provSrcBadge.style.display = "inline-block";
          } else {
            provSrcBadge.textContent = "";
            provSrcBadge.style.display = "none";
          }
        }
        var labNoteVal =
          dec.lab_lineage_note ||
          (group && group.lab_lineage_note) ||
          "";
        var provLabRow = document.getElementById("prov-lab-note-row");
        var provLabText = document.getElementById("prov-lab-lineage-note");
        if (provLabRow && provLabText) {
          if (labNoteVal) {
            provLabText.textContent = labNoteVal;
            provLabRow.style.display = "block";
          } else {
            provLabText.textContent = "";
            provLabRow.style.display = "none";
          }
        }
        setText("prov-assigned-to", dec.assigned_to_email || "Unassigned");
        setText(
          "prov-scope-badge",
          state.scopeMode === "single"
            ? "Scope: Specific Single Replicate(s)"
            : "Scope: Entire Replicate Group"
        );
        setText(
          "prov-resolved-by",
          dec.resolved_by_email
            ? "Resolved by " + dec.resolved_by_email
            : "Pending analyst Stage 1 commit"
        );
        setText(
          "prov-transition-badge",
          (dec.old_qc_pass || "pass") + " → " + (dec.new_qc_pass || "pass")
        );
        setText("prov-resolved-at", dec.resolved_at || "—");

        var gsheetBadge = document.getElementById("prov-gsheet-status-badge");
        var gsheetErrEl = document.getElementById("prov-gsheet-sync-error");
        if (gsheetBadge) {
          if (dec.synced_to_gsheet) {
            gsheetBadge.textContent = "Synced to GSheet";
            gsheetBadge.className = "status-pill status-synced";
          } else if (dec.sync_error) {
            gsheetBadge.textContent = "GSheet Sync Failed";
            gsheetBadge.className = "status-pill status-fail";
          } else {
            gsheetBadge.textContent = "Pending Admin GSheet Sync";
            gsheetBadge.className = "status-pill status-open";
          }
        }
        if (gsheetErrEl) {
          if (!dec.synced_to_gsheet && dec.sync_error) {
            gsheetErrEl.textContent = "Sync error: " + dec.sync_error;
            gsheetErrEl.style.display = "block";
          } else {
            gsheetErrEl.textContent = "";
            gsheetErrEl.style.display = "none";
          }
        }
        setText(
          "prov-gsheet-synced-at",
          dec.gsheet_synced_at
            ? dec.gsheet_synced_at +
                (dec.gsheet_synced_by_email ? " (" + dec.gsheet_synced_by_email + ")" : "")
            : "—"
        );
        updateRoleUI();
      }

      function renderReplicateBreakdown(dec, group) {
        var tbody = document.getElementById("replicate-breakdown-tbody");
        if (!tbody) return;
        tbody.innerHTML = "";
        var reps = (group && group.replicates) || [];
        var locked = isDecisionLocked(dec);
        for (var i = 0; i < reps.length; i++) {
          var r = reps[i];
          var tr = document.createElement("tr");
          if (r.is_iqr_outlier || r.is_analyst_flagged) {
            tr.style.background = "rgba(239, 68, 68, 0.16)";
          }
          var checked = Boolean(state.selectedReplicateIds[r.record_id]);
          var disabled = locked || state.scopeMode === "group";
          tr.innerHTML =
            "<td><input type='checkbox' class='replicate-checkbox' data-record-id='" +
            escapeHtml(r.record_id) +
            "' " +
            (checked ? "checked " : "") +
            (disabled ? "disabled " : "") +
            "/></td>" +
            "<td><code>" +
            escapeHtml(r.record_id) +
            "</code></td>" +
            "<td>#" +
            escapeHtml(String(r.replicate_no)) +
            "</td>" +
            "<td><strong>" +
            Number(r.value).toFixed(2) +
            "</strong> " +
            escapeHtml(r.unit || "") +
            "</td>" +
            "<td>" +
            (r.deviation_from_median_pct >= 0 ? "+" : "") +
            Number(r.deviation_from_median_pct).toFixed(1) +
            "%</td>" +
            "<td>" +
            escapeHtml(r.analyst || "") +
            "</td>" +
            "<td>" +
            escapeHtml(r.exp_date || "") +
            "</td>" +
            "<td><code>" +
            escapeHtml(r.qc_pass || r.qc_status || "pass") +
            "</code></td>";

          tbody.appendChild(tr);
        }

        var checkboxes = tbody.querySelectorAll(".replicate-checkbox");
        for (var j = 0; j < checkboxes.length; j++) {
          checkboxes[j].addEventListener("change", function (ev) {
            if (isDecisionLocked(dec)) return;
            var recId = ev.target.getAttribute("data-record-id");
            state.selectedReplicateIds[recId] = Boolean(ev.target.checked);
          });
        }
      }

      function renderDiagnosticPlot() {
        var svg = document.getElementById("diagnostic-plot-svg");
        var statsBar = document.getElementById("diagnostic-plot-stats");
        var badge = document.getElementById("plot-active-group-badge");
        if (!svg) return;

        var groups = WORKBENCH_DATA.replicate_groups || {};
        var targetKey = state.inspectedGroupKey || state.selectedGroupKey;
        var activeDec =
          state.selectedDecisionId && state.decisionsById[state.selectedDecisionId]
            ? state.decisionsById[state.selectedDecisionId]
            : null;
        var activeGroup = (targetKey && groups[targetKey]) || null;
        if (!activeGroup && targetKey) {
          activeGroup = findReplicateGroupForDecision({
            replicate_group_key: targetKey,
            record_id: activeDec ? activeDec.record_id : null,
            record_ids: activeDec ? activeDec.record_ids : null,
            record_table: activeDec ? activeDec.record_table : null
          });
        }
        if (!activeGroup && activeDec) {
          activeGroup = findReplicateGroupForDecision(activeDec);
        }
        if (!activeGroup) {
          svg.innerHTML =
            '<text x="320" y="130" text-anchor="middle" fill="#64748b">Select a replicate group to render diagnostic plot</text>';
          return;
        }

        if (badge) {
          badge.textContent =
            activeGroup.parameter_name +
            " • " +
            activeGroup.prepared_sample +
            " (" +
            state.plotStyle +
            " / color: " +
            state.groupBy +
            ")";
        }

        var st = activeGroup.stats || {};
        var ref = activeGroup.reference_stats || st;
        var reps = activeGroup.replicates || [];
        var width = 640;
        var height = 260;
        var padL = 70;
        var padR = 30;
        var padT = 28;
        var padB = 42;
        var plotW = width - padL - padR;
        var plotH = height - padT - padB;

        var isLightTheme =
          typeof document !== "undefined" &&
          document.documentElement &&
          typeof document.documentElement.getAttribute === "function" &&
          document.documentElement.getAttribute("data-theme") === "light";
        var svgBg = isLightTheme ? "#ffffff" : "#0f172a";
        var svgTextMain = isLightTheme ? "#0f172a" : "#f8fafc";
        var svgTextMuted = isLightTheme ? "#334155" : "#94a3b8";
        var svgIqrFill = isLightTheme ? "#e0f2fe" : "rgba(56, 189, 248, 0.16)";
        var svgClosFill = isLightTheme ? "#dcfce7" : "rgba(34, 197, 94, 0.18)";
        var svgOutText = isLightTheme ? "#b91c1c" : "#fca5a5";

        var svgParts = [];
        svgParts.push(
          '<rect x="0" y="0" width="' +
            width +
            '" height="' +
            height +
            '" fill="' +
            svgBg +
            '" />'
        );

        var palette = ["#0284c7", "#7c3aed", "#059669", "#d97706", "#dc2626", "#2563eb"];
        function colorForGroupVal(valStr) {
          var h = 0;
          var s = String(valStr || "default");
          for (var idx = 0; idx < s.length; idx++) {
            h = (h * 31 + s.charCodeAt(idx)) % 997;
          }
          return palette[h % palette.length];
        }

        if (state.plotStyle === "proximate_closure") {
          var sampleKey =
            activeGroup.resource_name + "::" + activeGroup.prepared_sample;
          var stratumKey =
            activeGroup.resource_name +
            "::" +
            (activeGroup.experiment || "unassigned") +
            "::" +
            (activeGroup.group_context_label || activeGroup.prep_method || "unassigned");
          var closure =
            activeGroup.proximate_closure ||
            (WORKBENCH_DATA.proximate_closure_by_stratum || {})[stratumKey] ||
            (WORKBENCH_DATA.proximate_closure_by_sample || {})[sampleKey] ||
            null;
          var rawComps = (closure && closure.components) || {};
          var mComp = rawComps.moisture !== undefined ? Number(rawComps.moisture) : null;
          var aComp = rawComps.ash !== undefined ? Number(rawComps.ash) : null;
          var vsComp =
            rawComps.volatile_solids !== undefined ? Number(rawComps.volatile_solids) : null;
          var fcComp =
            rawComps.fixed_carbon !== undefined ? Number(rawComps.fixed_carbon) : null;
          var portalSegments = [];
          if (mComp !== null) portalSegments.push({ label: "Moisture", val: mComp });
          if (aComp !== null) portalSegments.push({ label: "Ash", val: aComp });
          if (vsComp !== null) {
            portalSegments.push({ label: "Volatile Solids", val: vsComp });
          } else if (fcComp !== null) {
            portalSegments.push({ label: "100 - Fixed Carbon", val: 100.0 - fcComp });
          }
          var sumVal = closure
            ? Number(closure.proximate_sum_pct !== undefined ? closure.proximate_sum_pct : closure.closure_sum_pct)
            : Number(st.mean || 0);

          svgParts.push(
            '<text x="' +
              padL +
              '" y="20" font-size="12" font-weight="700" fill="' +
              svgTextMain +
              '">Proximate Mass-Balance Closure (Moisture + Ash + VS [or 100 - FC]) — ' +
              escapeHtml(sampleKey) +
              " (Total: " +
              Number(sumVal).toFixed(1) +
              "% | Target Band: 95–105%)</text>"
          );

          var maxScale = Math.max(120, sumVal + 10);
          var x95 = padL + (95 / maxScale) * plotW;
          var x105 = padL + (105 / maxScale) * plotW;
          svgParts.push(
            '<rect x="' +
              x95.toFixed(1) +
              '" y="' +
              (padT + 20) +
              '" width="' +
              (x105 - x95).toFixed(1) +
              '" height="' +
              (plotH - 40) +
              '" fill="' +
              svgClosFill +
              '" opacity="0.65" />'
          );
          svgParts.push(
            '<line x1="' +
              x95.toFixed(1) +
              '" y1="' +
              (padT + 14) +
              '" x2="' +
              x95.toFixed(1) +
              '" y2="' +
              (height - padB) +
              '" stroke="#15803d" stroke-dasharray="4,3" />'
          );
          svgParts.push(
            '<line x1="' +
              x105.toFixed(1) +
              '" y1="' +
              (padT + 14) +
              '" x2="' +
              x105.toFixed(1) +
              '" y2="' +
              (height - padB) +
              '" stroke="#b91c1c" stroke-dasharray="4,3" />'
          );

          var curX = padL;
          var barY = padT + 65;
          var barH = 48;
          for (var cIdx = 0; cIdx < portalSegments.length; cIdx++) {
            var cName = portalSegments[cIdx].label;
            var cVal = Number(portalSegments[cIdx].val || 0);
            var segW = (cVal / maxScale) * plotW;
            var segColor = palette[cIdx % palette.length];
            svgParts.push(
              '<rect x="' +
                curX.toFixed(1) +
                '" y="' +
                barY +
                '" width="' +
                Math.max(2, segW).toFixed(1) +
                '" height="' +
                barH +
                '" fill="' +
                segColor +
                '" stroke="#ffffff" />'
            );
            svgParts.push(
              '<text x="' +
                (curX + segW / 2).toFixed(1) +
                '" y="' +
                (barY + barH + 18) +
                '" text-anchor="middle" font-size="11" fill="' +
                svgTextMuted +
                '">' +
                escapeHtml(cName) +
                " (" +
                cVal.toFixed(1) +
                "%)</text>"
            );
            curX += segW;
          }
        } else {
          // Numeric value scale across replicates & reference IQR fences
          var allVals = [];
          for (var rIdx = 0; rIdx < reps.length; rIdx++) {
            allVals.push(Number(reps[rIdx].value));
          }
          if (ref && typeof ref.q1 === "number" && typeof ref.q3 === "number") {
            allVals.push(ref.q1, ref.q3);
          }
          var minVal = Math.min.apply(null, allVals);
          var maxVal = Math.max.apply(null, allVals);
          var span = maxVal - minVal;
          if (span < 1e-6) span = Math.max(1.0, Math.abs(maxVal) * 0.2);
          var domainMin = minVal - span * 0.18;
          var domainMax = maxVal + span * 0.18;

          function xScale(v) {
            return padL + ((v - domainMin) / (domainMax - domainMin)) * plotW;
          }
          function yScale(v) {
            return padT + plotH - ((v - domainMin) / (domainMax - domainMin)) * plotH;
          }

          if (state.plotStyle === "run_order") {
            // Run-Order / Batch Control Chart (x = replicate sequence, y = value)
            var yMed = yScale(st.median || 0);
            var yQ1 = yScale(st.q1 || st.min || 0);
            var yQ3 = yScale(st.q3 || st.max || 0);
            svgParts.push(
              '<rect x="' +
                padL +
                '" y="' +
                Math.min(yQ1, yQ3).toFixed(1) +
                '" width="' +
                plotW +
                '" height="' +
                Math.max(4, Math.abs(yQ1 - yQ3)).toFixed(1) +
                '" fill="' +
                svgIqrFill +
                '" opacity="0.65" />'
            );
            svgParts.push(
              '<line x1="' +
                padL +
                '" y1="' +
                yMed.toFixed(1) +
                '" x2="' +
                (width - padR) +
                '" y2="' +
                yMed.toFixed(1) +
                '" stroke="#0284c7" stroke-dasharray="4,3" stroke-width="1.5" />'
            );

            var pathPts = [];
            for (var k = 0; k < reps.length; k++) {
              var rx =
                padL +
                (reps.length === 1
                  ? plotW / 2
                  : (k / (reps.length - 1)) * plotW);
              var ry = yScale(Number(reps[k].value));
              pathPts.push(rx.toFixed(1) + "," + ry.toFixed(1));
            }
            if (pathPts.length > 1) {
              svgParts.push(
                '<polyline fill="none" stroke="#64748b" stroke-width="1.5" points="' +
                  pathPts.join(" ") +
                  '" />'
              );
            }
            for (var m = 0; m < reps.length; m++) {
              var repM = reps[m];
              var cxM =
                padL +
                (reps.length === 1
                  ? plotW / 2
                  : (m / (reps.length - 1)) * plotW);
              var cyM = yScale(Number(repM.value));
              var isOutM = repM.is_iqr_outlier || repM.is_analyst_flagged;
              var fillM = isOutM
                ? "#dc2626"
                : colorForGroupVal(repM[state.groupBy] || activeGroup[state.groupBy]);
              svgParts.push(
                '<circle cx="' +
                  cxM.toFixed(1) +
                  '" cy="' +
                  cyM.toFixed(1) +
                  '" r="' +
                  (isOutM ? 7 : 5.5) +
                  '" fill="' +
                  fillM +
                  '" stroke="#ffffff" stroke-width="1.5" />'
              );
              svgParts.push(
                '<text x="' +
                  cxM.toFixed(1) +
                  '" y="' +
                  (cyM - 10).toFixed(1) +
                  '" text-anchor="middle" font-size="11" fill="' +
                  svgTextMain +
                  '">' +
                  escapeHtml(repM.record_id) +
                  " (" +
                  Number(repM.value).toFixed(2) +
                  ")</text>"
              );
            }
          } else {
            // Sample Forest / Caterpillar + IQR Band OR Cross-Resource Box + Strip Plot
            var xQ1 = xScale(ref.q1 || st.q1 || minVal);
            var xQ3 = xScale(ref.q3 || st.q3 || maxVal);
            var xMed = xScale(st.median || 0);
            svgParts.push(
              '<rect x="' +
                Math.min(xQ1, xQ3).toFixed(1) +
                '" y="' +
                padT +
                '" width="' +
                Math.max(6, Math.abs(xQ3 - xQ1)).toFixed(1) +
                '" height="' +
                plotH +
                '" fill="' +
                svgIqrFill +
                '" opacity="0.65" />'
            );
            svgParts.push(
              '<line x1="' +
                xMed.toFixed(1) +
                '" y1="' +
                padT +
                '" x2="' +
                xMed.toFixed(1) +
                '" y2="' +
                (height - padB) +
                '" stroke="#0284c7" stroke-width="2" stroke-dasharray="5,3" />'
            );

            for (var n = 0; n < reps.length; n++) {
              var repN = reps[n];
              var rowY =
                padT +
                ((n + 0.5) / Math.max(1, reps.length)) * plotH;
              var valX = xScale(Number(repN.value));
              var isOutN = repN.is_iqr_outlier || repN.is_analyst_flagged;
              var dotColor = isOutN
                ? "#dc2626"
                : colorForGroupVal(repN[state.groupBy] || activeGroup[state.groupBy]);

              svgParts.push(
                '<line x1="' +
                  xMed.toFixed(1) +
                  '" y1="' +
                  rowY.toFixed(1) +
                  '" x2="' +
                  valX.toFixed(1) +
                  '" y2="' +
                  rowY.toFixed(1) +
                  '" stroke="#94a3b8" stroke-width="1.5" />'
              );
              svgParts.push(
                '<circle cx="' +
                  valX.toFixed(1) +
                  '" cy="' +
                  rowY.toFixed(1) +
                  '" r="' +
                  (isOutN ? 7 : 5.5) +
                  '" fill="' +
                  dotColor +
                  '" stroke="#ffffff" stroke-width="1.5" />'
              );
              svgParts.push(
                '<text x="' +
                  (padL - 6) +
                  '" y="' +
                  (rowY + 4).toFixed(1) +
                  '" text-anchor="end" font-size="11" fill="' +
                  svgTextMuted +
                  '">Rep #' +
                  escapeHtml(String(repN.replicate_no)) +
                  "</text>"
              );
              svgParts.push(
                '<text x="' +
                  (valX + 10).toFixed(1) +
                  '" y="' +
                  (rowY + 4).toFixed(1) +
                  '" font-size="11" font-weight="' +
                  (isOutN ? "700" : "500") +
                  '" fill="' +
                  (isOutN ? svgOutText : svgTextMain) +
                  '">' +
                  escapeHtml(repN.record_id) +
                  ": " +
                  Number(repN.value).toFixed(2) +
                  " " +
                  escapeHtml(repN.unit || "") +
                  "</text>"
              );
            }
          }
        }

        svg.innerHTML = svgParts.join("");

        if (statsBar) {
          statsBar.innerHTML =
            "<span><strong>Median:</strong> " +
            Number(st.median || 0).toFixed(2) +
            " " +
            escapeHtml(activeGroup.unit || "") +
            "</span>" +
            "<span><strong>Mean ± SD:</strong> " +
            Number(st.mean || 0).toFixed(2) +
            " ± " +
            Number(st.std || 0).toFixed(2) +
            "</span>" +
            "<span><strong>RSD:</strong> " +
            Number(st.rsd_pct || 0).toFixed(1) +
            "% (n=" +
            Number(st.count || 0) +
            ")</span>" +
            "<span><strong>IQR Band:</strong> [" +
            Number(ref.q1 || 0).toFixed(2) +
            ", " +
            Number(ref.q3 || 0).toFixed(2) +
            "]</span>" +
            "<span><strong>Tukey Fences:</strong> [" +
            Number(ref.lower_fence || 0).toFixed(2) +
            ", " +
            Number(ref.upper_fence || 0).toFixed(2) +
            "]</span>";
        }
      }

      function showToast(message, isError) {
        var toast = document.getElementById("decision-toast");
        if (!toast) return;
        toast.textContent = message;
        toast.style.background = isError ? "#fee2e2" : "#dcfce7";
        toast.style.color = isError ? "#991b1b" : "#166534";
        toast.style.border = isError ? "1px solid #fca5a5" : "1px solid #86efac";
        toast.className = "toast-status visible";
      }

      function refreshQcStateFromApi() {
        // 1. Fetch current authenticated session (/v1/qc/auth/me)
        fetch("/v1/qc/auth/me", { credentials: "same-origin" })
          .then(function (resp) {
            return resp.ok ? resp.json() : null;
          })
          .then(function (meData) {
            if (meData && meData.email) {
              state.user.email = meData.email;
              state.user.name = meData.name || meData.email;
              state.user.role = meData.role || "analyst";
              state.user.authenticated = Boolean(meData.authenticated);
              updateRoleUI();
              refreshAnalystFilterOptions();
              renderContextualDrawer();
            }
          })
          .catch(function () {
            updateRoleUI();
          });

        // 2. Fetch decisions from /v1/qc/decisions
        fetch("/v1/qc/decisions", { credentials: "same-origin" })
          .then(function (resp) {
            return resp.ok ? resp.json() : null;
          })
          .then(function (data) {
            var serverItems = (data && (data.decisions || data.items)) || [];
            serverItems.forEach(function (srv) {
              if (!srv) return;
              if (srv.record_table === "portal_bug_report" || srv.flag_type === "bug_report") return;
              var srvDbId =
                typeof srv.id === "number"
                  ? srv.id
                  : srv.id !== null &&
                    srv.id !== undefined &&
                    srv.id !== "" &&
                    Number.isInteger(Number(srv.id))
                  ? Number(srv.id)
                  : null;
              var targetId = null;
              var repGroups = (WORKBENCH_DATA && WORKBENCH_DATA.replicate_groups) || {};
              var normSrvKey = srv.replicate_group_key
                ? normalizeReplicateGroupKey(srv.replicate_group_key)
                : "";

              // Pass 1: Exact db_id match (highest priority)
              if (srvDbId !== null) {
                for (var j1 = 0; j1 < state.decisionsOrder.length; j1++) {
                  var cand1 = state.decisionsById[state.decisionsOrder[j1]];
                  if (!cand1) continue;
                  if (
                    cand1.db_id !== null &&
                    cand1.db_id !== undefined &&
                    (cand1.db_id === srv.id || Number(cand1.db_id) === srvDbId)
                  ) {
                    targetId = cand1.decision_id;
                    break;
                  }
                }
              }

              // Pass 2: Exact 6-part normalized replicate_group_key match
              if (!targetId && normSrvKey) {
                for (var j2 = 0; j2 < state.decisionsOrder.length; j2++) {
                  var cand2 = state.decisionsById[state.decisionsOrder[j2]];
                  if (!cand2) continue;
                  if (
                    srvDbId !== null &&
                    cand2.db_id !== null &&
                    cand2.db_id !== undefined &&
                    Number(cand2.db_id) !== srvDbId
                  ) {
                    continue;
                  }
                  if (
                    cand2.replicate_group_key &&
                    normalizeReplicateGroupKey(cand2.replicate_group_key) === normSrvKey
                  ) {
                    targetId = cand2.decision_id;
                    break;
                  }
                }
              }

              // Pass 3: 4-part prefix fallback match on replicate_group_key
              if (!targetId && srv.replicate_group_key) {
                for (var j3 = 0; j3 < state.decisionsOrder.length; j3++) {
                  var cand3 = state.decisionsById[state.decisionsOrder[j3]];
                  if (!cand3) continue;
                  if (
                    srvDbId !== null &&
                    cand3.db_id !== null &&
                    cand3.db_id !== undefined &&
                    Number(cand3.db_id) !== srvDbId
                  ) {
                    continue;
                  }
                  if (
                    cand3.replicate_group_key &&
                    matchesReplicateGroupKey(cand3.replicate_group_key, srv.replicate_group_key)
                  ) {
                    targetId = cand3.decision_id;
                    break;
                  }
                }
              }

              // Pass 4: Fallback match on (record_table, record_id)
              if (!targetId && srv.record_id) {
                for (var j4 = 0; j4 < state.decisionsOrder.length; j4++) {
                  var cand4 = state.decisionsById[state.decisionsOrder[j4]];
                  if (!cand4) continue;
                  if (
                    srvDbId !== null &&
                    cand4.db_id !== null &&
                    cand4.db_id !== undefined &&
                    Number(cand4.db_id) !== srvDbId
                  ) {
                    continue;
                  }
                  if (
                    !srv.record_table ||
                    !cand4.record_table ||
                    srv.record_table === cand4.record_table
                  ) {
                    var recMatched = false;
                    var candGrp =
                      repGroups[cand4.replicate_group_key] ||
                      findReplicateGroupForDecision(cand4);
                    var candRecs = (candGrp && (candGrp.records || candGrp.replicates)) || [];
                    for (var rIdx = 0; rIdx < candRecs.length; rIdx++) {
                      if (
                        candRecs[rIdx] &&
                        String(candRecs[rIdx].record_id) === String(srv.record_id)
                      ) {
                        recMatched = true;
                        break;
                      }
                    }
                    if (!recMatched && Array.isArray(cand4.record_ids)) {
                      if (cand4.record_ids.indexOf(srv.record_id) !== -1) {
                        recMatched = true;
                      }
                    }
                    if (recMatched) {
                      targetId = cand4.decision_id;
                      break;
                    }
                  }
                }
              }
              if (targetId && state.decisionsById[targetId]) {
                var merged = state.decisionsById[targetId];
                merged.db_id = srvDbId !== null ? srvDbId : srv.id !== undefined ? srv.id : merged.db_id || null;
                mergeFlagTypesIntoDecision(merged, srv);
                merged.decision_status =
                  srv.decision_status || srv.status || merged.decision_status;
                merged.status =
                  srv.status || srv.decision_status || merged.status || merged.decision_status;
                merged.decision_action =
                  srv.decision_action || merged.decision_action;
                if (srv.triage_scope || srv.scope || srv.scope_mode) {
                  merged.scope_mode = srv.triage_scope || srv.scope || srv.scope_mode;
                }
                merged.new_qc_pass = srv.new_qc_pass || merged.new_qc_pass;
                merged.assigned_to_email =
                  srv.assigned_to_email !== undefined
                    ? srv.assigned_to_email
                    : merged.assigned_to_email;
                merged.review_note =
                  srv.review_note !== undefined && srv.review_note !== null
                    ? srv.review_note
                    : merged.review_note;
                merged.rationale_chips =
                  Array.isArray(srv.rationale_chips) && srv.rationale_chips.length > 0
                    ? srv.rationale_chips
                    : merged.rationale_chips || [];
                merged.resolved_by_email =
                  srv.resolved_by_email || merged.resolved_by_email;
                merged.resolved_at = srv.resolved_at || merged.resolved_at;
                merged.submitted_by_email =
                  srv.submitted_by_email || merged.submitted_by_email;
                merged.created_at =
                  srv.created_at || srv.submitted_at || merged.created_at;
                merged.submitted_at =
                  srv.submitted_at || srv.created_at || merged.submitted_at || merged.created_at;
                merged.lab_lineage_note =
                  srv.lab_lineage_note ||
                  merged.lab_lineage_note ||
                  "";
                merged.source_label =
                  srv.source_label ||
                  merged.source_label ||
                  "";
                merged.synced_to_gsheet = Boolean(srv.synced_to_gsheet);
                merged.sync_error =
                  srv.sync_error !== undefined ? srv.sync_error : merged.sync_error || null;
                merged.gsheet_synced_at =
                  srv.gsheet_synced_at || merged.gsheet_synced_at;
                merged.gsheet_synced_by_email =
                  srv.gsheet_synced_by_email || merged.gsheet_synced_by_email;
              } else {
                var did = "QC-DB-" + String(srv.id).padStart(4, "0");
                var matchedGrp = findReplicateGroupForDecision(srv);
                var grpStats = (matchedGrp && matchedGrp.stats) || {};
                var hydrated = JSON.parse(JSON.stringify(srv));
                hydrated.db_id = srvDbId !== null ? srvDbId : srv.id;
                hydrated.decision_id = did;
                hydrated.record_table =
                  srv.record_table ||
                  (matchedGrp && matchedGrp.record_table) ||
                  "proximate_record";
                hydrated.record_ids =
                  Array.isArray(srv.record_ids) && srv.record_ids.length > 0
                    ? srv.record_ids
                    : matchedGrp && Array.isArray(matchedGrp.record_ids)
                    ? matchedGrp.record_ids.slice()
                    : srv.record_id
                    ? [srv.record_id]
                    : [];
                hydrated.replicate_group_key =
                  (matchedGrp && matchedGrp.replicate_group_key) ||
                  (srv.replicate_group_key
                    ? normalizeReplicateGroupKey(srv.replicate_group_key)
                    : "");
                hydrated.resource_name =
                  srv.resource_name || (matchedGrp && matchedGrp.resource_name) || "";
                hydrated.prepared_sample =
                  srv.prepared_sample ||
                  (matchedGrp && matchedGrp.prepared_sample) ||
                  "";
                hydrated.field_sample =
                  srv.field_sample || (matchedGrp && matchedGrp.field_sample) || "";
                hydrated.analysis_type =
                  srv.analysis_type || (matchedGrp && matchedGrp.analysis_type) || "";
                hydrated.parameter_name =
                  srv.parameter_name || (matchedGrp && matchedGrp.parameter_name) || "";
                hydrated.unit =
                  srv.unit || (matchedGrp && matchedGrp.unit) || "";
                hydrated.rsd_pct =
                  matchedGrp && matchedGrp.rsd_pct != null
                    ? matchedGrp.rsd_pct
                    : grpStats.rsd_pct != null
                    ? grpStats.rsd_pct
                    : srv.rsd_pct != null
                    ? srv.rsd_pct
                    : 0.0;
                hydrated.within_sd =
                  matchedGrp && matchedGrp.within_sd != null
                    ? matchedGrp.within_sd
                    : grpStats.within_sd != null
                    ? grpStats.within_sd
                    : srv.within_sd != null
                    ? srv.within_sd
                    : null;
                hydrated.between_rsd_pct =
                  matchedGrp && matchedGrp.between_rsd_pct !== undefined
                    ? matchedGrp.between_rsd_pct
                    : grpStats.between_rsd_pct !== undefined
                    ? grpStats.between_rsd_pct
                    : srv.between_rsd_pct !== undefined
                    ? srv.between_rsd_pct
                    : null;
                hydrated.between_sd =
                  matchedGrp && matchedGrp.between_sd !== undefined
                    ? matchedGrp.between_sd
                    : grpStats.between_sd !== undefined
                    ? grpStats.between_sd
                    : srv.between_sd !== undefined
                    ? srv.between_sd
                    : null;
                hydrated.replicate_count =
                  matchedGrp && matchedGrp.replicate_count != null
                    ? matchedGrp.replicate_count
                    : grpStats.count != null
                    ? grpStats.count
                    : srv.replicate_count != null
                    ? srv.replicate_count
                    : hydrated.record_ids.length || 1;
                hydrated.decision_status =
                  srv.decision_status || srv.status || "open";
                hydrated.status =
                  srv.status || srv.decision_status || "open";
                hydrated.submitted_by_email =
                  srv.submitted_by_email || "analyst@lbl.gov";
                hydrated.created_at =
                  srv.created_at || srv.submitted_at || WORKBENCH_DATA.generated_utc || null;
                hydrated.submitted_at =
                  srv.submitted_at || srv.created_at || hydrated.created_at;
                hydrated.lab_lineage_note =
                  srv.lab_lineage_note ||
                  (matchedGrp && matchedGrp.lab_lineage_note) ||
                  "";
                hydrated.source_label = srv.source_label || "";
                hydrated.sync_error = srv.sync_error || null;
                var inferredHydratedFlags = inferInteractiveFlagTypes(hydrated);
                hydrated.flag_type =
                  (inferredHydratedFlags.indexOf("visualizer_flagged") !== -1
                    ? "visualizer_flagged"
                    : inferredHydratedFlags.indexOf("stat_snapshot_flagged") !== -1
                    ? "stat_snapshot_flagged"
                    : srv.flag_type) || "analyst_flagged";
                hydrated.flag_types =
                  inferredHydratedFlags.length > 0
                    ? inferredHydratedFlags
                    : [hydrated.flag_type];
                hydrated.scope_mode =
                  srv.triage_scope || srv.scope || srv.scope_mode || "group";
                state.decisionsById[did] = hydrated;
                if (state.decisionsOrder.indexOf(did) === -1) {
                  state.decisionsOrder.push(did);
                }
              }
            });
            mergeLocalStorageDecisionsIntoState();
            if (!state.deepLinkParsed) {
              state.deepLinkParsed = true;
              parseDeepLinkQuery();
            }
            renderQueueTable();
            renderContextualDrawer();
          })
          .catch(function () {
            mergeLocalStorageDecisionsIntoState();
            if (!state.deepLinkParsed) {
              state.deepLinkParsed = true;
              parseDeepLinkQuery();
            }
            renderQueueTable();
            renderContextualDrawer();
          });
      }

      function saveStage1Decision() {
        var dec = state.decisionsById[state.selectedDecisionId];
        if (!dec) return;
        if (isDecisionLocked(dec)) {
          showToast(
            "Decision is locked. Click 'Revert Decision to Open' before making changes.",
            true
          );
          return;
        }

        var noteEl = document.getElementById("input-review-note");
        var actionEl = document.getElementById("select-decision-action");
        var assignedEl = document.getElementById("input-assigned-to");

        var noteText = noteEl ? noteEl.value.trim() : "";
        if (!noteText) {
          showToast(
            "Required: Please enter a free-text review note before committing a Stage 1 QC decision.",
            true
          );
          return;
        }

        var actionVal = actionEl ? actionEl.value : "in_review";
        var newQcPass = null;
        var newStatus = "in_review";
        if (actionVal === "approve_pass") {
          newQcPass = "pass";
          newStatus = "resolved";
        } else if (actionVal === "provisional") {
          newQcPass = "provisional";
          newStatus = "resolved";
        } else if (actionVal === "reject_fail" || actionVal === "mark_fail") {
          newQcPass = "fail";
          newStatus = "resolved";
        } else if (actionVal === "needs_retest" || actionVal === "retest") {
          newQcPass = "retest";
          newStatus = "needs_retest";
        } else if (actionVal === "in_review" || actionVal === "defer") {
          newQcPass = null;
          newStatus = "in_review";
        }

        var chosenIds = [];
        if (state.scopeMode === "single") {
          var keys = Object.keys(state.selectedReplicateIds);
          for (var i = 0; i < keys.length; i++) {
            if (state.selectedReplicateIds[keys[i]]) {
              chosenIds.push(keys[i]);
            }
          }
          if (chosenIds.length === 0) {
            showToast(
              "Select at least one replicate row when using Specific Single Replicate(s) scope.",
              true
            );
            return;
          }
        } else {
          chosenIds = (dec.record_ids || [dec.record_id]).slice();
        }

        var chosenChips = Object.keys(state.selectedChips).filter(function (c) {
          return Boolean(state.selectedChips[c]);
        });
        var nowUtc = new Date().toISOString();
        var numericId =
          typeof dec.db_id === "number" && Number.isInteger(dec.db_id)
            ? dec.db_id
            : null;

        var requestBody = {
          id: numericId,
          decision_id: numericId,
          record_table: dec.record_table || "proximate_record",
          record_id: chosenIds[0] || dec.record_id,
          record_ids: chosenIds,
          scope: state.scopeMode,
          replicate_group_key: dec.replicate_group_key,
          resource_name: dec.resource_name,
          analysis_type: dec.analysis_type,
          parameter_name: dec.parameter_name,
          flag_type: dec.flag_type,
          flag_trigger_value: dec.flag_trigger_value,
          old_qc_pass: dec.old_qc_pass || "pass",
          new_qc_pass: newQcPass,
          decision_status: newStatus,
          decision_action: actionVal,
          rationale_chips: chosenChips,
          review_note: noteText,
          assigned_to_email:
            assignedEl && assignedEl.value
              ? assignedEl.value.trim()
              : dec.assigned_to_email
        };

        // Update local state immediately for snappy UX
        dec.new_qc_pass = newQcPass;
        dec.decision_status = newStatus;
        dec.decision_action = actionVal;
        dec.rationale_chips = chosenChips;
        dec.review_note = noteText;
        dec.scope_mode = state.scopeMode;
        dec.assigned_to_email = requestBody.assigned_to_email;
        dec.resolved_by_email = state.user.email || "analyst@lbl.gov";
        dec.resolved_at = nowUtc;
        dec.synced_to_gsheet = false;

        // Also update replicate rows in WORKBENCH_DATA.replicate_groups so badges update immediately
        var repGrp =
          (WORKBENCH_DATA.replicate_groups || {})[dec.replicate_group_key] ||
          findReplicateGroupForDecision(dec);
        if (repGrp && Array.isArray(repGrp.replicates) && newQcPass) {
          for (var r = 0; r < repGrp.replicates.length; r++) {
            var repRow = repGrp.replicates[r];
            if (
              state.scopeMode === "group" ||
              chosenIds.indexOf(String(repRow.record_id)) !== -1
            ) {
              repRow.qc_pass = newQcPass;
              repRow.qc_status = newQcPass;
            }
          }
        }

        var stage1HttpError = null;
        fetch("/v1/qc/decisions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(requestBody)
        })
          .then(function (resp) {
            if (resp && resp.ok) {
              return resp.json();
            }
            if (resp) {
              return resp
                .json()
                .catch(function () {
                  return null;
                })
                .then(function (errBody) {
                  stage1HttpError =
                    (errBody && (errBody.sync_error || errBody.detail || errBody.error)) ||
                    "HTTP " + resp.status;
                  return null;
                });
            }
            return null;
          })
          .then(function (resData) {
            if (resData && resData.decision) {
              if (resData.decision.id != null) {
                dec.db_id = Number(resData.decision.id);
              }
              dec.resolved_at = resData.decision.resolved_at || nowUtc;
              dec.resolved_by_email =
                resData.decision.resolved_by_email || dec.resolved_by_email;
            }
          })
          .catch(function () {})
          .finally(function () {
            if (qcBroadcastChannel) {
              qcBroadcastChannel.postMessage({
                type: "qc_decision_saved",
                decision_id: dec.decision_id,
                db_id: dec.db_id,
                replicate_group_key: dec.replicate_group_key,
                record_ids: chosenIds,
                new_qc_pass: newQcPass,
                decision_status: newStatus,
                updated_at: nowUtc
              });
            }
            if (stage1HttpError) {
              showToast(
                "Stage 1 API warning for " +
                  dec.decision_id +
                  " (" +
                  stage1HttpError +
                  "). Saved in local session state.",
                true
              );
            } else {
              showToast(
                "Stage 1 PostgreSQL Decision Saved (" +
                  dec.decision_id +
                  ": " +
                  (dec.old_qc_pass || "pass") +
                  " → " +
                  newQcPass +
                  "). Pending Admin Stage 2 Google Sheets Sync.",
                false
              );
            }
            refreshAnalystFilterOptions();
            renderKpis();
            renderQueueTable();
            renderContextualDrawer();
          });
      }

      function revertCurrentDecision() {
        var dec = state.decisionsById[state.selectedDecisionId];
        if (!dec) return;
        var reason = "Reverted by reviewer in QC Workbench";
        if (typeof window !== "undefined" && typeof window.prompt === "function") {
          var prompted = window.prompt(
            "Optional reason for reverting " + dec.decision_id + " back to Open:",
            "Reverted for re-evaluation"
          );
          if (prompted === null) {
            return;
          }
          if (prompted.trim()) {
            reason = prompted.trim();
          }
        }

        var numericId =
          typeof dec.db_id === "number" && Number.isInteger(dec.db_id)
            ? dec.db_id
            : null;
        var nowUtc = new Date().toISOString();

        var revertPromise = numericId !== null
          ? fetch("/v1/qc/decisions/" + encodeURIComponent(numericId) + "/revert", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials: "same-origin",
              body: JSON.stringify({
                reason: reason,
                sync_to_gsheet: true
              })
            }).then(function (resp) {
              return resp.ok ? resp.json() : null;
            })
          : Promise.resolve({
              status: "ok",
              restored_qc_pass: dec.old_qc_pass != null ? dec.old_qc_pass : null,
              decisions: []
            });

        revertPromise
          .then(function (revertData) {
            if (!revertData || revertData.status !== "ok") {
              var errReason =
                (revertData && (revertData.detail || revertData.reason || revertData.message)) ||
                "Server rejected revert or network unavailable";
              showToast(
                "Failed to revert decision " +
                  dec.decision_id +
                  " (" +
                  errReason +
                  "). Decision remains locked.",
                true
              );
              renderKpis();
              renderQueueTable();
              renderContextualDrawer();
              return;
            }

            var srvDec = revertData.decision || null;
            var restoredPass =
              srvDec && srvDec.new_qc_pass !== undefined
                ? srvDec.new_qc_pass
                : revertData.restored_qc_pass !== undefined
                ? revertData.restored_qc_pass
                : dec.old_qc_pass != null
                ? dec.old_qc_pass
                : null;

            dec.new_qc_pass = restoredPass;
            dec.decision_status = "open";
            dec.decision_action = "open";
            dec.synced_to_gsheet = false;
            dec.gsheet_synced_at = "";
            dec.gsheet_synced_by_email = "";
            dec.resolved_at = "";
            dec.resolved_by_email = "";
            if (srvDec && srvDec.review_note) {
              dec.review_note = srvDec.review_note;
            }

            var perRecordPass = {};
            if (Array.isArray(revertData.decisions)) {
              for (var dIdx = 0; dIdx < revertData.decisions.length; dIdx++) {
                var sItem = revertData.decisions[dIdx];
                if (sItem && sItem.record_id) {
                  perRecordPass[String(sItem.record_id)] =
                    sItem.new_qc_pass !== undefined
                      ? sItem.new_qc_pass
                      : sItem.old_qc_pass !== undefined
                      ? sItem.old_qc_pass
                      : null;
                }
              }
            }

            var repGrp =
              (WORKBENCH_DATA.replicate_groups || {})[dec.replicate_group_key] ||
              findReplicateGroupForDecision(dec);
            if (repGrp && Array.isArray(repGrp.replicates)) {
              for (var r = 0; r < repGrp.replicates.length; r++) {
                var repRow = repGrp.replicates[r];
                var repRid = String(repRow.record_id || "");
                if (Object.prototype.hasOwnProperty.call(perRecordPass, repRid)) {
                  repRow.qc_pass = perRecordPass[repRid];
                  repRow.qc_status = perRecordPass[repRid] || "pass";
                } else {
                  repRow.qc_pass = restoredPass;
                  repRow.qc_status = restoredPass || "pass";
                }
              }
            }

            if (qcBroadcastChannel) {
              qcBroadcastChannel.postMessage({
                type: "qc_decision_reverted",
                decision_id: dec.decision_id,
                db_id: dec.db_id,
                replicate_group_key: dec.replicate_group_key,
                record_ids: dec.record_ids || [dec.record_id],
                new_qc_pass: restoredPass,
                decision_status: "open",
                updated_at: nowUtc
              });
            }

            showToast("Decision reverted and returned to Open queue.", false);
            renderKpis();
            renderQueueTable();
            renderContextualDrawer();
            if (numericId !== null) {
              refreshQcStateFromApi();
            }
          })
          .catch(function () {
            showToast(
              "Failed to revert decision " +
                dec.decision_id +
                ". Decision remains locked.",
              true
            );
            renderKpis();
            renderQueueTable();
            renderContextualDrawer();
          });
      }

      function assignDecisionToReviewer(dec, targetAssignee, useMeKeyword) {
        if (!dec || !targetAssignee) return Promise.resolve(null);
        dec.assigned_to_email = targetAssignee;
        if (dec.decision_id === state.selectedDecisionId) {
          var assignedEl = document.getElementById("input-assigned-to");
          if (assignedEl) assignedEl.value = targetAssignee;
        }

        var hasDbId =
          typeof dec.db_id === "number" && Number.isInteger(dec.db_id);
        var reqPromise;

        if (hasDbId) {
          reqPromise = fetch(
            "/v1/qc/decisions/" + encodeURIComponent(dec.db_id) + "/assign",
            {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              credentials: "same-origin",
              body: JSON.stringify({
                assigned_to_email: useMeKeyword ? "me" : targetAssignee,
                record_ids:
                  Array.isArray(dec.record_ids) && dec.record_ids.length
                    ? dec.record_ids
                    : dec.record_id
                    ? [dec.record_id]
                    : [],
                scope: dec.scope_mode || "group"
              })
            }
          );
        } else {
          reqPromise = fetch("/v1/qc/decisions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({
              id: null,
              decision_id: null,
              record_table: dec.record_table || "proximate_record",
              record_id: dec.record_id,
              record_ids: dec.record_ids || [dec.record_id],
              scope: dec.scope_mode || "group",
              replicate_group_key: dec.replicate_group_key,
              resource_name: dec.resource_name,
              analysis_type: dec.analysis_type,
              parameter_name: dec.parameter_name,
              flag_type: dec.flag_type,
              flag_trigger_value: dec.flag_trigger_value,
              old_qc_pass: dec.old_qc_pass || "pass",
              new_qc_pass: dec.new_qc_pass || dec.old_qc_pass || "pass",
              decision_status: dec.decision_status || "open",
              decision_action: dec.decision_action || "flag_for_review",
              review_note: dec.review_note || "",
              assigned_to_email: targetAssignee
            })
          });
        }

        return reqPromise
          .then(function (resp) {
            return resp && resp.ok ? resp.json() : null;
          })
          .then(function (resData) {
            if (resData && resData.decision && resData.decision.id != null) {
              dec.db_id = Number(resData.decision.id);
            }
            return resData;
          })
          .catch(function () {
            return null;
          });
      }

      function assignSelectedToMe() {
        var dec = state.decisionsById[state.selectedDecisionId];
        if (!dec) return;
        var myEmail = state.user.email || "analyst@lbl.gov";
        assignDecisionToReviewer(dec, myEmail, true).finally(function () {
          showToast(
            "Assigned " + dec.decision_id + " to " + myEmail + ".",
            false
          );
          refreshAnalystFilterOptions();
          renderQueueTable();
          renderContextualDrawer();
        });
      }

      function assignSelectedToAnalystOfRecord() {
        var dec = state.decisionsById[state.selectedDecisionId];
        if (!dec) return;
        var aor = getAnalystOfRecord(dec);
        if (!aor || aor === "Unassigned") {
          showToast("No Analyst of Record found for " + dec.decision_id + ".", true);
          return;
        }
        assignDecisionToReviewer(dec, aor, false).finally(function () {
          showToast(
            "Assigned " + dec.decision_id + " to Analyst of Record (" + aor + ").",
            false
          );
          refreshAnalystFilterOptions();
          renderQueueTable();
          renderContextualDrawer();
        });
      }

      function batchAssignFilteredOpen() {
        var visibleIds = getVisibleQueueDecisionIds();
        var targets = [];
        for (var i = 0; i < visibleIds.length; i++) {
          var d = state.decisionsById[visibleIds[i]];
          if (d && (d.decision_status || "open") === "open") {
            targets.push(d);
          }
        }
        if (targets.length === 0) {
          showToast("No open items in current filtered queue to batch-assign.", true);
          return;
        }
        var defaultAssignee = state.user.email || "analyst@lbl.gov";
        var chosenAssignee = defaultAssignee;
        if (typeof window !== "undefined" && typeof window.prompt === "function") {
          var inputVal = window.prompt(
            "Batch-assign " +
              targets.length +
              " open queue item(s). Enter reviewer email/handle, or 'aor' to assign each item to its Analyst of Record:",
            defaultAssignee
          );
          if (inputVal === null) return;
          if (inputVal.trim()) {
            chosenAssignee = inputVal.trim();
          }
        }
        var promises = [];
        for (var j = 0; j < targets.length; j++) {
          var item = targets[j];
          var assignee =
            chosenAssignee.toLowerCase() === "aor"
              ? getAnalystOfRecord(item)
              : chosenAssignee;
          if (assignee && assignee !== "Unassigned") {
            promises.push(assignDecisionToReviewer(item, assignee, false));
          }
        }
        Promise.all(promises).finally(function () {
          showToast(
            "Batch-assigned " + promises.length + " open queue item(s).",
            false
          );
          refreshAnalystFilterOptions();
          renderQueueTable();
          renderContextualDrawer();
        });
      }

      function syncSingleDecisionToGsheet() {
        var dec = state.decisionsById[state.selectedDecisionId];
        if (!dec) return;
        if (state.user.role !== "admin") {
          showToast(
            "Stage 2 Google Sheets write-back requires Admin role.",
            true
          );
          return;
        }
        var nowUtc = new Date().toISOString();

        var stage1EnsureErr = null;
        function ensureDbIdPromise() {
          if (typeof dec.db_id === "number" && Number.isInteger(dec.db_id)) {
            return Promise.resolve(dec.db_id);
          }
          return fetch("/v1/qc/decisions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({
              id: null,
              decision_id: null,
              record_table: dec.record_table || "proximate_record",
              record_id: dec.record_id,
              record_ids: dec.record_ids || [dec.record_id],
              replicate_group_key: dec.replicate_group_key,
              resource_name: dec.resource_name,
              analysis_type: dec.analysis_type,
              parameter_name: dec.parameter_name,
              flag_type: dec.flag_type,
              flag_trigger_value: dec.flag_trigger_value,
              old_qc_pass: dec.old_qc_pass || "pass",
              new_qc_pass: dec.new_qc_pass || "fail",
              decision_status: "resolved",
              decision_action: dec.decision_action || "reject_fail",
              review_note:
                dec.review_note || "Stage 1 committed prior to Admin GSheet sync",
              assigned_to_email: dec.assigned_to_email
            })
          })
            .then(function (resp) {
              if (resp && resp.ok) {
                return resp.json();
              }
              if (resp) {
                return resp
                  .json()
                  .catch(function () {
                    return null;
                  })
                  .then(function (errData) {
                    stage1EnsureErr =
                      (errData && (errData.sync_error || errData.detail || errData.error)) ||
                      "HTTP " + resp.status;
                    return null;
                  });
              }
              return null;
            })
            .then(function (resData) {
              if (resData && resData.decision && resData.decision.id != null) {
                dec.db_id = Number(resData.decision.id);
                return dec.db_id;
              }
              return null;
            })
            .catch(function (err) {
              stage1EnsureErr = (err && err.message) || null;
              return null;
            });
        }

        return ensureDbIdPromise()
          .then(function (dbId) {
            if (dbId === null || dbId === undefined) {
              return {
                synced_to_gsheet: false,
                sync_error:
                  "Unable to resolve PostgreSQL decision ID prior to GSheet sync" +
                  (stage1EnsureErr ? ": " + stage1EnsureErr : ".")
              };
            }
            return fetch(
              "/v1/qc/decisions/" + encodeURIComponent(dbId) + "/sync-gsheet",
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin"
              }
            ).then(function (resp) {
              return resp.json().catch(function () {
                return {
                  synced_to_gsheet: false,
                  sync_error: "HTTP " + resp.status
                };
              });
            });
          })
          .catch(function (err) {
            return {
              synced_to_gsheet: false,
              sync_error: (err && err.message) || "Network error contacting /sync-gsheet"
            };
          })
          .then(function (syncRes) {
            dec.decision_status = "resolved";
            var syncedOk = Boolean(syncRes && syncRes.synced_to_gsheet === true);
            if (syncedOk) {
              dec.synced_to_gsheet = true;
              dec.sync_error = null;
              dec.gsheet_synced_at =
                (syncRes.decision && syncRes.decision.gsheet_synced_at) ||
                syncRes.gsheet_synced_at ||
                nowUtc;
              dec.gsheet_synced_by_email =
                (syncRes.decision && syncRes.decision.gsheet_synced_by_email) ||
                state.user.email ||
                "admin@lbl.gov";
              showToast(
                "Stage 2 Google Sheets write-back completed for " +
                  dec.decision_id +
                  ".",
                false
              );
            } else {
              dec.synced_to_gsheet = false;
              var specificDetail =
                syncRes &&
                syncRes.detail &&
                syncRes.detail !== "Internal server error"
                  ? syncRes.detail
                  : null;
              var errReason =
                (syncRes && (syncRes.sync_error || specificDetail || syncRes.error)) ||
                (syncRes &&
                  syncRes.writeback &&
                  Array.isArray(syncRes.writeback.errors) &&
                  syncRes.writeback.errors.join("; ")) ||
                (syncRes && syncRes.detail) ||
                "Google Sheets row write-back did not confirm any updated cells.";
              dec.sync_error = errReason;
              showToast(
                "Stage 2 Google Sheets write-back failed for " +
                  dec.decision_id +
                  ": " +
                  errReason,
                true
              );
            }
            renderQueueTable();
            renderContextualDrawer();
            return syncRes;
          });
      }

      function syncBatchDecisionsToGsheet() {
        if (state.user.role !== "admin") {
          showToast(
            "Stage 2 Google Sheets batch sync requires Admin role.",
            true
          );
          return;
        }
        var pending = [];
        for (var i = 0; i < state.decisionsOrder.length; i++) {
          var d = state.decisionsById[state.decisionsOrder[i]];
          if (d && d.decision_status === "resolved" && !d.synced_to_gsheet) {
            pending.push(d);
          }
        }
        var ids = pending
          .map(function (d) {
            return d.db_id;
          })
          .filter(function (id) {
            return typeof id === "number" && Number.isInteger(id);
          });
        var nowUtc = new Date().toISOString();
        return fetch("/v1/qc/decisions/sync-gsheet-batch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ decision_ids: ids.length ? ids : null })
        })
          .then(function (resp) {
            return resp.json().catch(function () {
              return { synced_count: 0, sync_error: "HTTP " + resp.status };
            });
          })
          .catch(function (err) {
            return {
              synced_count: 0,
              sync_error: (err && err.message) || "Network error contacting /sync-gsheet-batch"
            };
          })
          .then(function (batchRes) {
            var syncedCount = Number((batchRes && batchRes.synced_count) || 0);
            var resultsById = {};
            var hasPerItemResults = Boolean(
              batchRes && Array.isArray(batchRes.results) && batchRes.results.length > 0
            );
            if (batchRes && Array.isArray(batchRes.results)) {
              for (var r = 0; r < batchRes.results.length; r++) {
                var itemRes = batchRes.results[r];
                if (itemRes) {
                  var resDbId =
                    itemRes.decision && itemRes.decision.id != null
                      ? itemRes.decision.id
                      : itemRes.decision_id != null
                      ? itemRes.decision_id
                      : null;
                  if (resDbId != null) {
                    resultsById[String(resDbId)] = itemRes;
                  }
                }
              }
            }
            var syncedIdSet = {};
            if (batchRes && Array.isArray(batchRes.synced_decision_ids)) {
              for (var si = 0; si < batchRes.synced_decision_ids.length; si++) {
                syncedIdSet[String(batchRes.synced_decision_ids[si])] = true;
              }
            }
            var failedIdSet = {};
            if (batchRes && Array.isArray(batchRes.failed_decision_ids)) {
              for (var fi = 0; fi < batchRes.failed_decision_ids.length; fi++) {
                failedIdSet[String(batchRes.failed_decision_ids[fi])] = true;
              }
            }
            var failedCount = 0;
            var lastErr = (batchRes && (batchRes.sync_error || batchRes.detail)) || "";
            for (var j = 0; j < pending.length; j++) {
              var item = pending[j];
              if (!item) continue;
              var itemKey = item.db_id != null ? String(item.db_id) : "";
              var matchedRes = itemKey ? resultsById[itemKey] : null;
              var itemSynced = false;
              var itemKnownFailed = false;
              if (matchedRes) {
                itemSynced = Boolean(matchedRes.synced_to_gsheet === true);
                itemKnownFailed = !itemSynced;
              } else if (itemKey && syncedIdSet[itemKey]) {
                itemSynced = true;
              } else if (itemKey && failedIdSet[itemKey]) {
                itemKnownFailed = true;
              } else if (!hasPerItemResults) {
                if (syncedCount > 0 && syncedCount === pending.length) {
                  itemSynced = true;
                } else if (syncedCount === 0) {
                  itemKnownFailed = true;
                } else if (j < syncedCount) {
                  itemSynced = true;
                } else {
                  itemKnownFailed = true;
                }
              }
              if (itemSynced) {
                item.synced_to_gsheet = true;
                item.sync_error = null;
                item.gsheet_synced_at = nowUtc;
                item.gsheet_synced_by_email =
                  state.user.email || "admin@lbl.gov";
              } else if (itemKnownFailed) {
                item.synced_to_gsheet = false;
                var itemErr =
                  (matchedRes && matchedRes.sync_error) ||
                  lastErr ||
                  "GSheet write-back did not confirm updated cells.";
                item.sync_error = itemErr;
                lastErr = itemErr;
                failedCount++;
              }
            }
            if (failedCount === 0 && syncedCount > 0) {
              showToast(
                "Batch Stage 2 Google Sheets sync completed for " +
                  syncedCount +
                  " resolved decision(s).",
                false
              );
            } else {
              showToast(
                "Batch Stage 2 Google Sheets sync: " +
                  syncedCount +
                  " synced, " +
                  failedCount +
                  " failed" +
                  (lastErr ? " (" + lastErr + ")" : "."),
                true
              );
            }
            renderQueueTable();
            renderContextualDrawer();
            return batchRes;
          });
      }

      function parseDeepLinkQuery() {
        if (typeof window === "undefined" || !window.location) return;
        var params = new URLSearchParams(window.location.search || "");
        var qFlagType = params.get("flag_type") || params.get("flagType");
        if (qFlagType) {
          state.filters.flagType = qFlagType;
          var selFlag = document.getElementById("filter-flag-type");
          if (selFlag) selFlag.value = qFlagType;
        }
        var qSortBy = params.get("sort_by") || params.get("sortBy");
        if (qSortBy) {
          state.filters.sortBy = qSortBy;
          var selSort = document.getElementById("filter-sort-by");
          if (selSort) selSort.value = qSortBy;
        }
        var qDomain = params.get("domain") || params.get("analysis_type") || params.get("type");
        if (qDomain && qDomain !== "all") {
          var normDom = normalizeDomainKey(qDomain);
          var selAt = document.getElementById("filter-analysis-type");
          if (selAt) {
            var matchedVal = "";
            for (var oi = 0; oi < selAt.options.length; oi++) {
              var optVal = selAt.options[oi].value;
              if (optVal && (optVal === qDomain || normalizeDomainKey(optVal) === normDom)) {
                matchedVal = optVal;
                break;
              }
            }
            state.filters.analysisType = matchedVal || normDom;
            if (matchedVal) selAt.value = matchedVal;
          } else {
            state.filters.analysisType = normDom;
          }
        }
        var qDecisionId = params.get("decision_id");
        var qGroupKey = params.get("replicate_group_key");
        if (qDecisionId) {
          var paddedCandidate = "QC-" + String(qDecisionId).padStart(4, "0");
          var paddedDbCandidate = "QC-DB-" + String(qDecisionId).padStart(4, "0");
          for (var kDb = 0; kDb < state.decisionsOrder.length; kDb++) {
            var dDb = state.decisionsById[state.decisionsOrder[kDb]];
            if (!dDb) continue;
            if (
              dDb.decision_id === qDecisionId ||
              String(dDb.db_id || "") === String(qDecisionId) ||
              String(dDb.id || "") === String(qDecisionId) ||
              dDb.decision_id === paddedDbCandidate
            ) {
              selectDecision(dDb.decision_id, false);
              return;
            }
          }
          for (var k = 0; k < state.decisionsOrder.length; k++) {
            var d = state.decisionsById[state.decisionsOrder[k]];
            if (!d) continue;
            if (d.decision_id === paddedCandidate) {
              selectDecision(d.decision_id, false);
              return;
            }
          }
        }
        if (qGroupKey) {
          for (var i = 0; i < state.decisionsOrder.length; i++) {
            var item = state.decisionsById[state.decisionsOrder[i]];
            if (item && matchesReplicateGroupKey(item.replicate_group_key, qGroupKey)) {
              selectDecision(item.decision_id, false);
              return;
            }
          }
          var fallbackGroup = findReplicateGroupForDecision({
            replicate_group_key: qGroupKey
          });
          if (fallbackGroup && fallbackGroup.replicate_group_key) {
            state.selectedGroupKey = fallbackGroup.replicate_group_key;
            state.inspectedGroupKey = fallbackGroup.replicate_group_key;
            renderDiagnosticPlot();
          }
        }
      }

      function bindEvents() {
        var tabBtns = document.querySelectorAll("#queue-tabs-container .queue-tab");
        for (var i = 0; i < tabBtns.length; i++) {
          tabBtns[i].addEventListener("click", function (ev) {
            var btn = ev.currentTarget;
            var tabName = btn.getAttribute("data-queue-tab");
            state.activeQueueTab = tabName || "all_open";
            for (var j = 0; j < tabBtns.length; j++) {
              tabBtns[j].classList.remove("active");
            }
            btn.classList.add("active");
            renderQueueTable();
          });
        }

        function bindFilter(id, key) {
          var el = document.getElementById(id);
          if (!el) return;
          el.addEventListener("input", function () {
            state.filters[key] = el.value;
            renderQueueTable();
          });
          el.addEventListener("change", function () {
            state.filters[key] = el.value;
            renderQueueTable();
          });
        }
        bindFilter("filter-resource", "resource");
        bindFilter("filter-analysis-type", "analysisType");
        bindFilter("filter-parameter", "parameter");
        bindFilter("filter-flag-type", "flagType");
        bindFilter("filter-qc-status", "qcStatus");
        bindFilter("filter-analyst-of-record", "analystOfRecord");
        bindFilter("filter-assigned-reviewer", "assignedReviewer");
        bindFilter("filter-assigned-analyst", "assignedAnalyst");
        bindFilter("filter-sort-by", "sortBy");
        bindFilter("filter-search", "search");

        var sortSelectEl = document.getElementById("sort-queue-select");
        if (sortSelectEl) {
          sortSelectEl.addEventListener("change", function () {
            state.queueSort = sortSelectEl.value || "rsd_desc";
            state.filters.sortBy = state.queueSort;
            renderQueueTable();
          });
        }

        var thSortRsd = document.getElementById("th-sort-rsd");
        if (thSortRsd) {
          thSortRsd.addEventListener("click", function () {
            state.queueSort =
              state.queueSort === "rsd_desc" ? "rsd_asc" : "rsd_desc";
            state.filters.sortBy = state.queueSort;
            if (sortSelectEl) {
              sortSelectEl.value = state.queueSort;
            }
            renderQueueTable();
          });
        }

        var toggleKpiBtn = document.getElementById("btn-toggle-kpi-strip");
        var kpiStripSection = document.getElementById("kpi-strip-section");
        if (toggleKpiBtn && kpiStripSection) {
          toggleKpiBtn.addEventListener("click", function () {
            var isCollapsed = kpiStripSection.classList.toggle("collapsed");
            toggleKpiBtn.textContent = isCollapsed
              ? "▸ Expand KPI Summary"
              : "▾ Collapse KPI Summary";
          });
        }

        var toggleQueueBtn = document.getElementById("btn-toggle-queue-card");
        var queueScrollWrap = document.getElementById("queue-table-scroll-wrapper");
        if (toggleQueueBtn && queueScrollWrap) {
          toggleQueueBtn.addEventListener("click", function () {
            var isCompact = queueScrollWrap.classList.toggle("compact");
            toggleQueueBtn.textContent = isCompact
              ? "▸ Expand Queue Table"
              : "▾ Compact Queue Table";
          });
        }

        var minRsdEl = document.getElementById("filter-min-rsd");
        if (minRsdEl) {
          minRsdEl.addEventListener("input", function () {
            setMinRsdFilter(minRsdEl.value);
          });
          minRsdEl.addEventListener("change", function () {
            setMinRsdFilter(minRsdEl.value);
          });
        }
        var flagSelectEl = document.getElementById("filter-flag-type");
        if (flagSelectEl) {
          flagSelectEl.addEventListener("change", function () {
            if (flagSelectEl.value === "rsd_gt_10") {
              setMinRsdFilter(10);
            } else if (flagSelectEl.value === "rsd_gt_20") {
              setMinRsdFilter(20);
            }
          });
        }

        var plotStyleEl = document.getElementById("select-plot-style");
        if (plotStyleEl) {
          plotStyleEl.addEventListener("change", function () {
            state.plotStyle = plotStyleEl.value;
            renderDiagnosticPlot();
          });
        }

        var groupByEl = document.getElementById("select-group-by");
        if (groupByEl) {
          groupByEl.addEventListener("change", function () {
            state.groupBy = groupByEl.value;
            renderDiagnosticPlot();
          });
        }

        var coParamEl = document.getElementById("select-co-measured-param");
        if (coParamEl) {
          coParamEl.addEventListener("change", function () {
            state.inspectedGroupKey = coParamEl.value;
            renderDiagnosticPlot();
          });
        }

        var scopeGroupRadio = document.getElementById("scope-entire-group");
        var scopeSingleRadio = document.getElementById("scope-single-replicate");
        if (scopeGroupRadio && scopeSingleRadio) {
          scopeGroupRadio.addEventListener("change", function () {
            if (scopeGroupRadio.checked) {
              state.scopeMode = "group";
              renderContextualDrawer();
            }
          });
          scopeSingleRadio.addEventListener("change", function () {
            if (scopeSingleRadio.checked) {
              state.scopeMode = "single";
              renderContextualDrawer();
            }
          });
        }

        var chipEls = document.querySelectorAll("#rationale-chips-list .rationale-chip");
        for (var c = 0; c < chipEls.length; c++) {
          chipEls[c].addEventListener("click", function (ev) {
            var dec = state.decisionsById[state.selectedDecisionId];
            if (isDecisionLocked(dec)) return;
            var chipEl = ev.currentTarget;
            var chipName = chipEl.getAttribute("data-chip");
            state.selectedChips[chipName] = !state.selectedChips[chipName];
            chipEl.classList.toggle("selected", Boolean(state.selectedChips[chipName]));
          });
        }

        var saveBtn = document.getElementById("btn-save-decision");
        if (saveBtn) {
          saveBtn.addEventListener("click", saveStage1Decision);
        }

        var revertBtn = document.getElementById("btn-revert-decision");
        if (revertBtn) {
          revertBtn.addEventListener("click", revertCurrentDecision);
        }

        var assignMeBtn = document.getElementById("btn-assign-to-me");
        if (assignMeBtn) {
          assignMeBtn.addEventListener("click", assignSelectedToMe);
        }

        var assignAorBtn = document.getElementById("btn-assign-analyst-of-record");
        if (assignAorBtn) {
          assignAorBtn.addEventListener("click", assignSelectedToAnalystOfRecord);
        }

        var batchAssignBtn = document.getElementById("btn-batch-assign-open");
        if (batchAssignBtn) {
          batchAssignBtn.addEventListener("click", batchAssignFilteredOpen);
        }

        var singleSyncBtn = document.getElementById("btn-sync-single-gsheet");
        if (singleSyncBtn) {
          singleSyncBtn.addEventListener("click", syncSingleDecisionToGsheet);
        }

        var batchSyncBtn = document.getElementById("btn-sync-gsheet-batch");
        if (batchSyncBtn) {
          batchSyncBtn.addEventListener("click", syncBatchDecisionsToGsheet);
        }

        var refreshBtn = document.getElementById("btn-refresh-qc-state");
        if (refreshBtn) {
          refreshBtn.addEventListener("click", refreshQcStateFromApi);
        }

        if (qcBroadcastChannel) {
          qcBroadcastChannel.onmessage = function () {
            mergeLocalStorageDecisionsIntoState();
            refreshQcStateFromApi();
          };
        }
        if (typeof window !== "undefined" && typeof window.addEventListener === "function") {
          window.addEventListener("storage", function () {
            mergeLocalStorageDecisionsIntoState();
            renderQueueTable();
          });
          window.addEventListener("focus", function () {
            mergeLocalStorageDecisionsIntoState();
            refreshQcStateFromApi();
          });
        }

        var roleToggleBtn = document.getElementById("btn-toggle-role-sim");
        if (roleToggleBtn) {
          roleToggleBtn.addEventListener("click", function () {
            if (state.user.role === "admin") {
              state.user.role = "analyst";
              state.user.email = "analyst@lbl.gov";
            } else {
              state.user.role = "admin";
              state.user.email = "admin@lbl.gov";
            }
            updateRoleUI();
            renderQueueTable();
            renderContextualDrawer();
          });
        }

        var themeToggleBtn = document.getElementById("btn-theme-toggle");
        if (themeToggleBtn) {
          themeToggleBtn.addEventListener("click", function () {
            var currentTheme =
              document.documentElement && typeof document.documentElement.getAttribute === "function"
                ? document.documentElement.getAttribute("data-theme")
                : "dark";
            var nextTheme = currentTheme === "light" ? "dark" : "light";
            if (document.documentElement && typeof document.documentElement.setAttribute === "function") {
              document.documentElement.setAttribute("data-theme", nextTheme);
            }
            themeToggleBtn.textContent = nextTheme === "light" ? "☀ Light Mode" : "🌙 Dark Mode";
            try {
              localStorage.setItem("biocirv_workbench_theme", nextTheme);
            } catch (_e) {}
            renderContextualDrawer();
          });
        }

        var exportJsonBtn = document.getElementById("btn-export-client-json");
        if (exportJsonBtn) {
          exportJsonBtn.addEventListener("click", function () {
            var exportPayload = {
              exported_at: new Date().toISOString(),
              user: state.user,
              decisions: state.decisionsOrder.map(function (id) {
                return state.decisionsById[id];
              })
            };
            var blob = new Blob([JSON.stringify(exportPayload, null, 2)], {
              type: "application/json"
            });
            var url = URL.createObjectURL(blob);
            var a = document.createElement("a");
            a.href = url;
            a.download = "qc_audit_decisions_snapshot.json";
            a.click();
            URL.revokeObjectURL(url);
          });
        }

        var bugModal = document.getElementById("modal-report-bug");
        var openBugBtn = document.getElementById("btn-open-bug-modal");
        function getBugDiagnosticsObject() {
          return {
            page: "Page 4 — Resource QC & Data Audit Workbench",
            resource: state.filters.resource || "all",
            domainTab: state.activeQueueTab || "all_open",
            qcFilter: state.filters.flagType || "all",
            selectedDecisionId: state.selectedDecisionId || "(none)",
            queryString: window.location.search || "(none)"
          };
        }
        function buildGitHubBugIssueUrl(opts) {
          var repoUrl = "https://github.com/uw-ssec/ca-biositing/issues/new";
          var title = (opts.title || "").trim() || ("[Dashboard Bug] " + (opts.category || "Issue") + " on " + (opts.page || "Page 4"));
          var bodyLines = [
            "### Dashboard Bug / Data QC Report",
            "",
            "- **Category:** " + (opts.category || "UI / Chart Rendering Bug"),
            "- **Dashboard Page:** " + (opts.page || "Page 4 — Resource QC & Data Audit Workbench"),
            "- **Active Resource:** `" + (opts.resource || "all") + "`",
            "- **Active Tab / Queue:** `" + (opts.domainTab || "all_open") + "`",
            "- **Active Flag Filter:** `" + (opts.qcFilter || "all") + "`",
            "- **Selected Decision ID:** `" + (opts.selectedDecisionId || "(none)") + "`",
            "- **URL Query State:** `" + (opts.queryString || "(none)") + "`",
            "- **Timestamp (UTC):** `" + new Date().toISOString() + "`",
            "",
            "### Observed Behavior / Steps to Reproduce",
            opts.description || "_Please describe what happened..._",
            "",
            "### Expected Behavior",
            opts.expectedBehavior || "_Optional: describe what you expected to see._"
          ];
          var params = new URLSearchParams();
          params.set("title", title);
          params.set("body", bodyLines.join("\\n"));
          params.set("labels", "bug,dashboard");
          return repoUrl + "?" + params.toString();
        }
        if (openBugBtn && bugModal) {
          openBugBtn.addEventListener("click", function () {
            var diag = getBugDiagnosticsObject();
            var diagEl = document.getElementById("bug-modal-diagnostics");
            if (diagEl) {
              diagEl.textContent =
                "Page: " + diag.page +
                "\\nResource: " + diag.resource +
                "\\nActive Queue Tab: " + diag.domainTab +
                "\\nFlag Filter: " + diag.qcFilter +
                "\\nSelected Decision: " + diag.selectedDecisionId +
                "\\nQuery: " + diag.queryString;
            }
            var statusEl = document.getElementById("bug-modal-status");
            if (statusEl) statusEl.classList.add("hidden");
            bugModal.classList.remove("hidden");
          });
        }
        ["btn-close-bug-modal", "btn-cancel-bug-modal"].forEach(function (id) {
          var el = document.getElementById(id);
          if (el && bugModal) {
            el.addEventListener("click", function () {
              bugModal.classList.add("hidden");
            });
          }
        });
        var submitUrlBtn = document.getElementById("btn-submit-github-url");
        if (submitUrlBtn) {
          submitUrlBtn.addEventListener("click", function () {
            var diag = getBugDiagnosticsObject();
            var issueUrl = buildGitHubBugIssueUrl({
              title: (document.getElementById("bug-modal-title") || {}).value || "",
              category: (document.getElementById("bug-modal-category") || {}).value || "UI / Chart Rendering Bug",
              description: (document.getElementById("bug-modal-desc") || {}).value || "",
              expectedBehavior: (document.getElementById("bug-modal-expected") || {}).value || "",
              page: diag.page,
              resource: diag.resource,
              domainTab: diag.domainTab,
              qcFilter: diag.qcFilter,
              selectedDecisionId: diag.selectedDecisionId,
              queryString: diag.queryString
            });
            window.open(issueUrl, "_blank", "noopener");
            if (bugModal) bugModal.classList.add("hidden");
          });
        }
        var submitApiBtn = document.getElementById("btn-submit-github-api");
        if (submitApiBtn) {
          submitApiBtn.addEventListener("click", async function () {
            var diag = getBugDiagnosticsObject();
            var payload = {
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
            var statusEl = document.getElementById("bug-modal-status");
            if (statusEl) {
              statusEl.textContent = "⏳ Submitting issue via /v1/qc/github-issue...";
              statusEl.classList.remove("hidden");
            }
            try {
              var apiBase = window.BIOCIRV_API_BASE || "http://localhost:8000";
              var resp = await fetch(apiBase + "/v1/qc/github-issue", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
              });
              if (resp.ok) {
                var data = await resp.json();
                if (data.created_via_api) {
                  if (statusEl) {
                    statusEl.innerHTML = "✓ GitHub Issue #" + escapeHtml(data.issue_number ?? "") + " created &amp; recorded in PostgreSQL QC Ledger (ID #" + escapeHtml(data.decision_id ?? "") + ")! <a href=\\"" + escapeHtml(data.issue_url ?? "") + "\\" target=\\"_blank\\" rel=\\"noopener\\">View Issue &rarr;</a>";
                    statusEl.classList.remove("hidden");
                  }
                  return;
                }
                if (data.persisted) {
                  var ghFallbackHref = escapeHtml(data.issue_url || data.fallback_url || "");
                  if (statusEl) {
                    statusEl.innerHTML = "✓ Issue recorded in PostgreSQL QC Ledger (ID #" + escapeHtml(data.decision_id ?? "") + ")." + (ghFallbackHref ? " <a href=\\"" + ghFallbackHref + "\\" target=\\"_blank\\" rel=\\"noopener\\">Optional: Open on GitHub &rarr;</a>" : "");
                    statusEl.classList.remove("hidden");
                  }
                  return;
                }
                if (data.issue_url) {
                  window.open(data.issue_url, "_blank", "noopener");
                  if (bugModal) bugModal.classList.add("hidden");
                  return;
                }
              }
            } catch (_err) {
              // Offline fallback
            }
            var fallbackUrl = buildGitHubBugIssueUrl({
              title: payload.title,
              category: payload.category,
              description: payload.description,
              expectedBehavior: payload.expected_behavior,
              page: diag.page,
              resource: diag.resource,
              domainTab: diag.domainTab,
              qcFilter: diag.qcFilter,
              selectedDecisionId: diag.selectedDecisionId,
              queryString: diag.queryString
            });
            window.open(fallbackUrl, "_blank", "noopener");
            if (bugModal) bugModal.classList.add("hidden");
          });
        }
      }

      function escapeHtml(str) {
        return String(str === null || str === undefined ? "" : str)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");
      }

      function closeFlagShowMePopover() {
        var pop = document.getElementById("audit-flag-show-me-popover");
        if (pop) {
          pop.classList.add("hidden");
          if (pop.style) pop.style.display = "none";
        }
      }

      function openFlagShowMePopover(opts, anchorEl) {
        var pop = document.getElementById("audit-flag-show-me-popover");
        var svgEl = document.getElementById("show-me-mini-svg");
        if (!pop || !svgEl) return null;

        var o = typeof opts === "string" ? { replicateGroupKey: opts } : (opts || {});
        var hasExplicitSelector = Boolean(
          o.decisionId ||
          o.replicateGroupKey ||
          o.replicate_group_key ||
          o.parameter ||
          o.preparedSample ||
          o.prepared_sample
        );
        var dec = null;
        if (o.decisionId && state.decisionsById[o.decisionId]) {
          dec = state.decisionsById[o.decisionId];
        } else if (!hasExplicitSelector && state.selectedDecisionId) {
          dec = state.decisionsById[state.selectedDecisionId];
        }

        var targetGroup = null;
        if (dec) {
          targetGroup = findReplicateGroupForDecision(dec);
        }
        var reqKey = String(
          o.replicateGroupKey || o.replicate_group_key || (dec && dec.replicate_group_key) || ""
        ).trim();
        var rawGroups = (WORKBENCH_DATA && WORKBENCH_DATA.replicate_groups) || {};
        var allGroups = Array.isArray(rawGroups)
          ? rawGroups
          : Object.values(rawGroups);
        if (!targetGroup && reqKey) {
          for (var i = 0; i < allGroups.length; i++) {
            if (matchesReplicateGroupKey(allGroups[i].replicate_group_key, reqKey)) {
              targetGroup = allGroups[i];
              break;
            }
          }
        }
        if (!targetGroup && (o.parameter || o.preparedSample || o.prepared_sample)) {
          var pLow = String(o.parameter || "").trim().toLowerCase();
          var sLow = String(o.preparedSample || o.prepared_sample || "").trim().toLowerCase();
          for (var gIdx = 0; gIdx < allGroups.length; gIdx++) {
            var candG = allGroups[gIdx];
            if (
              (!pLow || String(candG.parameter_name || "").trim().toLowerCase() === pLow) &&
              (!sLow || String(candG.prepared_sample || "").trim().toLowerCase() === sLow)
            ) {
              targetGroup = candG;
              break;
            }
          }
        }
        if (!targetGroup && !hasExplicitSelector && allGroups.length > 0) {
          targetGroup = allGroups[0];
        }
        if (!dec && targetGroup) {
          var decList = Object.values(state.decisionsById || {});
          for (var dIdx = 0; dIdx < decList.length; dIdx++) {
            if (
              matchesReplicateGroupKey(
                decList[dIdx].replicate_group_key,
                targetGroup.replicate_group_key
              )
            ) {
              dec = decList[dIdx];
              break;
            }
          }
        }

        var rawReps = (targetGroup && Array.isArray(targetGroup.replicates))
          ? targetGroup.replicates
          : [];
        if (!targetGroup || rawReps.length === 0) {
          svgEl.innerHTML =
            '<rect x="28" y="18" width="368" height="102" rx="8" fill="rgba(15,23,42,0.04)" stroke="rgba(148,163,184,0.22)" stroke-width="1" />' +
            '<text x="210" y="74" text-anchor="middle" font-size="11" font-family="monospace" fill="#94a3b8">No matching database records found in snapshot.</text>';
          setText("show-me-popover-subtitle", "No matching database records found");
          var emptyPillsEl = document.getElementById("show-me-flag-pills");
          if (emptyPillsEl) emptyPillsEl.innerHTML = "";
          setText("show-me-stats-summary", "No matching database records found");
          var emptyProxEl = document.getElementById("show-me-proximate-bar");
          if (emptyProxEl) {
            emptyProxEl.classList.add("hidden");
            if (emptyProxEl.style) emptyProxEl.style.display = "none";
            emptyProxEl.innerHTML = "";
          }
          pop.classList.remove("hidden");
          if (pop.style) pop.style.display = "block";
          return {
            empty: true,
            decisionId: dec ? dec.decision_id : o.decisionId || null,
            replicateGroupKey: reqKey,
            peerCount: 0,
            targetGroupCount: 0,
            outlierCount: 0,
            hasProximateBar: false
          };
        }

        var resolvedResource =
          o.resource ||
          (dec && dec.resource_name) ||
          (targetGroup && targetGroup.resource_name) ||
          "";
        var resolvedAnalysisType =
          o.analysisType ||
          (dec && dec.analysis_type) ||
          (targetGroup && targetGroup.analysis_type) ||
          "";
        var resolvedDomSlug = canonicalDomainSlug(resolvedAnalysisType);
        var resolvedParameter =
          o.parameter ||
          (dec && dec.parameter_name) ||
          (targetGroup && targetGroup.parameter_name) ||
          "";
        var resolvedMethod =
          o.method ||
          (dec && dec.prep_method) ||
          (targetGroup && targetGroup.prep_method) ||
          "";
        var resolvedSample =
          o.preparedSample ||
          (dec && dec.prepared_sample) ||
          (targetGroup && targetGroup.prepared_sample) ||
          "";
        var resolvedUnit =
          o.unit ||
          (dec && dec.unit) ||
          (targetGroup && targetGroup.unit) ||
          "";
        var activeFlags = [];
        if (Array.isArray(o.flags)) {
          activeFlags = o.flags.slice();
        } else if (o.flags) {
          activeFlags = [String(o.flags)];
        } else if (dec) {
          activeFlags = (dec.flag_types || [dec.flag_type]).filter(Boolean);
        } else if (targetGroup && Array.isArray(targetGroup.flag_types)) {
          activeFlags = targetGroup.flag_types.filter(Boolean);
        }

        var targetKey = targetGroup.replicate_group_key;
        var normStr = function (v) {
          return String(v || "").trim().toLowerCase();
        };

        var peerGroups = allGroups.filter(function (g) {
          return (
            g.replicate_group_key !== targetKey &&
            normStr(g.resource_name) === normStr(resolvedResource) &&
            canonicalDomainSlug(g.analysis_type) === resolvedDomSlug &&
            normStr(g.parameter_name) === normStr(resolvedParameter) &&
            (!resolvedMethod || normStr(g.prep_method) === normStr(resolvedMethod))
          );
        });
        if (peerGroups.length === 0) {
          peerGroups = allGroups.filter(function (g) {
            return (
              g.replicate_group_key !== targetKey &&
              normStr(g.resource_name) === normStr(resolvedResource) &&
              normStr(g.parameter_name) === normStr(resolvedParameter)
            );
          });
        }
        if (peerGroups.length === 0) {
          peerGroups = allGroups.filter(function (g) {
            return (
              g.replicate_group_key !== targetKey &&
              normStr(g.parameter_name) === normStr(resolvedParameter)
            );
          });
        }
        if (peerGroups.length === 0) {
          peerGroups = allGroups.filter(function (g) {
            return g.replicate_group_key !== targetKey;
          });
        }

        var targetReps = rawReps.map(function (r, idx) {
          var rawSt = String(
            String(r.qc_pass || "").toLowerCase() === "fail" ||
              String(r.qc_status || "").toLowerCase() === "fail"
              ? "fail"
              : r.qc_pass || r.qc_status || "pass"
          ).toLowerCase();
          return {
            record_id: String(r.record_id || ""),
            value: Number(r.value),
            replicate_no: Number(r.replicate_no || idx + 1),
            qc_pass: rawSt,
            prepared_sample: String(resolvedSample || ""),
            is_iqr_outlier: Boolean(r.is_iqr_outlier),
            is_analyst_flagged: Boolean(r.is_analyst_flagged),
            isTargetGroup: true,
            isOutlier: false
          };
        });

        var groupMean =
          targetReps.reduce(function (s, r) {
            return s + Number(r.value);
          }, 0) / (targetReps.length || 1);
        var explicitCandId = String(
          o.outlierRecordId || (dec && dec.record_id) || ""
        ).trim();

        for (var rIdx = 0; rIdx < targetReps.length; rIdx++) {
          var trItem = targetReps[rIdx];
          trItem.isOutlier = Boolean(
            (explicitCandId && trItem.record_id === explicitCandId) ||
              trItem.is_iqr_outlier ||
              trItem.is_analyst_flagged
          );
        }

        if (targetReps.length >= 2) {
          var outlierCnt = targetReps.filter(function (r) {
            return r.isOutlier;
          }).length;
          if (outlierCnt === 0 || outlierCnt === targetReps.length) {
            var furthestIdx = 0;
            var maxDist = -1;
            for (var k = 0; k < targetReps.length; k++) {
              var dist = Math.abs(Number(targetReps[k].value) - groupMean);
              if (dist > maxDist) {
                maxDist = dist;
                furthestIdx = k;
              }
            }
            for (var m = 0; m < targetReps.length; m++) {
              targetReps[m].isOutlier = m === furthestIdx;
            }
          }
        } else if (targetReps.length === 1) {
          targetReps[0].isOutlier = true;
        }

        var peerPoints = [];
        for (var pIdx = 0; pIdx < peerGroups.length; pIdx++) {
          var pg = peerGroups[pIdx];
          var pgReps = pg.replicates || [];
          for (var prIdx = 0; prIdx < pgReps.length; prIdx++) {
            var pr = pgReps[prIdx];
            if (typeof pr.value === "number" && !isNaN(pr.value)) {
              peerPoints.push({
                record_id: String(pr.record_id || ""),
                value: Number(pr.value),
                qc_pass: String(
                  String(pr.qc_pass || "").toLowerCase() === "fail" ||
                    String(pr.qc_status || "").toLowerCase() === "fail"
                    ? "fail"
                    : pr.qc_pass || pr.qc_status || "pass"
                ).toLowerCase(),
                prepared_sample: String(pg.prepared_sample || "Peer Sample"),
                replicate_group_key: pg.replicate_group_key,
                isTargetGroup: false,
                isOutlier: false
              });
            }
          }
        }

        var allPoints = peerPoints.concat(targetReps);
        var allVals = allPoints.map(function (pt) {
          return Number(pt.value);
        });
        var sliceMean = allVals.length
          ? allVals.reduce(function (s, v) {
              return s + v;
            }, 0) / allVals.length
          : groupMean;
        var sliceSd =
          allVals.length >= 2
            ? Math.sqrt(
                allVals.reduce(function (s, v) {
                  return s + Math.pow(v - sliceMean, 2);
                }, 0) /
                  (allVals.length - 1)
              )
            : Number((targetGroup && targetGroup.sd_value) || 0);

        var minVal = allVals.length ? Math.min.apply(null, allVals) : 0;
        var maxVal = allVals.length ? Math.max.apply(null, allVals) : 10;
        if (Math.abs(maxVal - minVal) < 1e-9) {
          minVal -= 1;
          maxVal += 1;
        } else {
          var pad = (maxVal - minVal) * 0.12;
          minVal -= pad;
          maxVal += pad;
        }

        var svgW = 420;
        var padL = 28;
        var padR = 24;
        var plotW = svgW - padL - padR;
        var xOf = function (val) {
          var t = (Number(val) - minVal) / (maxVal - minVal || 1);
          return Math.max(padL, Math.min(svgW - padR, padL + t * plotW));
        };

        var bandX1 = xOf(sliceMean - sliceSd);
        var bandX2 = xOf(sliceMean + sliceSd);
        var bandW = Math.max(2, bandX2 - bandX1);
        var targetMeanX = xOf(groupMean);
        var sliceMeanX = xOf(sliceMean);

        function renderQcFailDiamondOverlay(pt, cxNum, cyNum, rSize) {
          if (String(pt.qc_pass || "pass").toLowerCase() !== "fail") return "";
          var d = rSize + 2.2;
          var pts =
            cxNum.toFixed(1) + "," + (cyNum - d).toFixed(1) + " " +
            (cxNum + d).toFixed(1) + "," + cyNum.toFixed(1) + " " +
            cxNum.toFixed(1) + "," + (cyNum + d).toFixed(1) + " " +
            (cxNum - d).toFixed(1) + "," + cyNum.toFixed(1);
          var xOff = Math.max(2.5, rSize * 0.55);
          return (
            '<polygon class="show-me-qc-fail-diamond show-me-pt-qc-fail" data-qc-status="fail" data-record-id="' +
            escapeHtml(pt.record_id) +
            '" points="' +
            pts +
            '" fill="rgba(245,158,11,0.28)" stroke="#f59e0b" stroke-width="1.8" />' +
            '<line class="show-me-qc-fail-cross" x1="' +
            (cxNum - xOff).toFixed(1) +
            '" y1="' +
            (cyNum - xOff).toFixed(1) +
            '" x2="' +
            (cxNum + xOff).toFixed(1) +
            '" y2="' +
            (cyNum + xOff).toFixed(1) +
            '" stroke="#ef4444" stroke-width="1.8" />' +
            '<line class="show-me-qc-fail-cross" x1="' +
            (cxNum - xOff).toFixed(1) +
            '" y1="' +
            (cyNum + xOff).toFixed(1) +
            '" x2="' +
            (cxNum + xOff).toFixed(1) +
            '" y2="' +
            (cyNum - xOff).toFixed(1) +
            '" stroke="#ef4444" stroke-width="1.8" />'
          );
        }

        var peerCirclesSvg = peerPoints
          .map(function (pt, idx) {
            var cxNum = xOf(pt.value);
            var cyNum = 44 + ((idx * 17) % 28);
            var cx = cxNum.toFixed(1);
            var cy = cyNum.toFixed(1);
            var isFail = String(pt.qc_pass || "pass").toLowerCase() === "fail";
            return (
              '<circle class="show-me-pt-peer' +
              (isFail ? " show-me-pt-qc-fail" : "") +
              '" data-role="peer" data-qc-status="' +
              (isFail ? "fail" : "pass") +
              '" data-record-id="' +
              escapeHtml(pt.record_id) +
              '" cx="' +
              cx +
              '" cy="' +
              cy +
              '" r="4.5" fill="rgba(148,163,184,0.45)" stroke="#64748b" stroke-width="1.5"><title>' +
              escapeHtml(pt.record_id) +
              " | " +
              escapeHtml(pt.prepared_sample) +
              " | " +
              Number(pt.value).toFixed(2) +
              " " +
              escapeHtml(resolvedUnit) +
              (isFail ? " [QC_FAIL]" : "") +
              "</title></circle>" +
              renderQcFailDiamondOverlay(pt, cxNum, cyNum, 4.5)
            );
          })
          .join("");

        var targetGroupCirclesSvg = targetReps
          .filter(function (pt) {
            return !pt.isOutlier;
          })
          .map(function (pt, idx) {
            var cxNum = xOf(pt.value);
            var cyNum = 92 + ((idx * 13) % 18);
            var cx = cxNum.toFixed(1);
            var cy = cyNum.toFixed(1);
            var isFail = String(pt.qc_pass || "pass").toLowerCase() === "fail";
            return (
              '<circle class="show-me-pt-target-group' +
              (isFail ? " show-me-pt-qc-fail" : "") +
              '" data-role="target-group" data-qc-status="' +
              (isFail ? "fail" : "pass") +
              '" data-record-id="' +
              escapeHtml(pt.record_id) +
              '" cx="' +
              cx +
              '" cy="' +
              cy +
              '" r="6" fill="rgba(59,130,246,0.22)" stroke="#2563eb" stroke-width="2.5"><title>' +
              escapeHtml(pt.record_id) +
              " | " +
              escapeHtml(pt.prepared_sample) +
              " (Target Replicate Group) | " +
              Number(pt.value).toFixed(2) +
              " " +
              escapeHtml(resolvedUnit) +
              (isFail ? " [QC_FAIL]" : "") +
              "</title></circle>" +
              renderQcFailDiamondOverlay(pt, cxNum, cyNum, 6)
            );
          })
          .join("");

        var outlierCirclesSvg = targetReps
          .filter(function (pt) {
            return pt.isOutlier;
          })
          .map(function (pt, idx) {
            var cxNum = xOf(pt.value);
            var cyNum = 96 + ((idx * 11) % 14);
            var cx = cxNum.toFixed(1);
            var cy = cyNum.toFixed(1);
            var isFail = String(pt.qc_pass || "pass").toLowerCase() === "fail";
            return (
              '<circle class="show-me-outlier-pulse-ring" data-role="outlier-ring" data-record-id="' +
              escapeHtml(pt.record_id) +
              '" cx="' +
              cx +
              '" cy="' +
              cy +
              '" r="10.5" fill="none" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="3,2" opacity="0.85" />' +
              '<circle class="show-me-pt-outlier' +
              (isFail ? " show-me-pt-qc-fail" : "") +
              '" data-role="outlier" data-qc-status="' +
              (isFail ? "fail" : "pass") +
              '" data-record-id="' +
              escapeHtml(pt.record_id) +
              '" cx="' +
              cx +
              '" cy="' +
              cy +
              '" r="7.5" fill="rgba(239,68,68,0.28)" stroke="#dc2626" stroke-width="3"><title>' +
              escapeHtml(pt.record_id) +
              " | " +
              escapeHtml(pt.prepared_sample) +
              " (Flagged Outlier) | " +
              Number(pt.value).toFixed(2) +
              " " +
              escapeHtml(resolvedUnit) +
              (isFail ? " [QC_FAIL]" : "") +
              "</title></circle>" +
              renderQcFailDiamondOverlay(pt, cxNum, cyNum, 7.5)
            );
          })
          .join("");

        svgEl.innerHTML =
          '<rect x="' +
          padL +
          '" y="18" width="' +
          plotW +
          '" height="102" rx="8" fill="rgba(15,23,42,0.04)" stroke="rgba(148,163,184,0.22)" stroke-width="1" />' +
          '<rect class="show-me-slice-sd-band" x="' +
          bandX1.toFixed(1) +
          '" y="22" width="' +
          bandW.toFixed(1) +
          '" height="94" fill="rgba(96,165,250,0.16)" stroke="#60a5fa" stroke-width="1" stroke-dasharray="3,3" />' +
          '<line class="show-me-slice-mean-line" x1="' +
          sliceMeanX.toFixed(1) +
          '" y1="20" x2="' +
          sliceMeanX.toFixed(1) +
          '" y2="118" stroke="#64748b" stroke-width="1.2" stroke-dasharray="2,2" />' +
          '<line class="show-me-target-mean-line" x1="' +
          targetMeanX.toFixed(1) +
          '" y1="20" x2="' +
          targetMeanX.toFixed(1) +
          '" y2="118" stroke="#2563eb" stroke-width="2" stroke-dasharray="4,3" />' +
          '<text x="' +
          (padL + 4) +
          '" y="33" font-size="9" font-family="monospace" fill="#64748b">Peer Slice (n=' +
          peerPoints.length +
          ")</text>" +
          '<text x="' +
          (padL + 4) +
          '" y="82" font-size="9" font-family="monospace" fill="#2563eb">Target Replicate Group (' +
          escapeHtml(resolvedSample) +
          ", n=" +
          targetReps.length +
          ")</text>" +
          peerCirclesSvg +
          targetGroupCirclesSvg +
          outlierCirclesSvg +
          '<line x1="' +
          padL +
          '" y1="124" x2="' +
          (svgW - padR) +
          '" y2="124" stroke="#94a3b8" stroke-width="1" />' +
          '<text x="' +
          padL +
          '" y="138" font-size="9" font-family="monospace" fill="#64748b">' +
          minVal.toFixed(2) +
          " " +
          escapeHtml(resolvedUnit) +
          "</text>" +
          '<text x="' +
          (svgW / 2).toFixed(1) +
          '" y="138" text-anchor="middle" font-size="9" font-family="monospace" fill="#2563eb">Grp Mean: ' +
          groupMean.toFixed(2) +
          " " +
          escapeHtml(resolvedUnit) +
          "</text>" +
          '<text x="' +
          (svgW - padR) +
          '" y="138" text-anchor="end" font-size="9" font-family="monospace" fill="#64748b">' +
          maxVal.toFixed(2) +
          " " +
          escapeHtml(resolvedUnit) +
          "</text>";

        setText(
          "show-me-popover-subtitle",
          resolvedResource +
            " • " +
            resolvedAnalysisType +
            " • " +
            resolvedParameter +
            (resolvedUnit ? " (" + resolvedUnit + ")" : "") +
            " • " +
            resolvedSample
        );

        var pillsEl = document.getElementById("show-me-flag-pills");
        if (pillsEl) {
          var pillList = activeFlags.length ? activeFlags : ["flagged_group"];
          pillsEl.innerHTML = pillList
            .map(function (ft) {
              return '<span class="flag-pill flag-' + escapeHtml(ft) + '">⚑ ' + escapeHtml(ft) + "</span>";
            })
            .join(" ");
        }

        var rsdVal =
          targetGroup && typeof targetGroup.rsd_pct === "number"
            ? targetGroup.rsd_pct.toFixed(1) + "%"
            : "—";
        setText(
          "show-me-stats-summary",
          "Group Mean " +
            groupMean.toFixed(2) +
            " (RSD " +
            rsdVal +
            ") vs Slice Mean " +
            sliceMean.toFixed(2) +
            " ± " +
            sliceSd.toFixed(2)
        );

        var proxBarEl = document.getElementById("show-me-proximate-bar");
        var hasProximateFlag = Boolean(
          activeFlags.some(function (f) {
            return String(f).toLowerCase().indexOf("proximate") !== -1;
          }) ||
            (targetGroup && targetGroup.raw_proximate_sum) ||
            typeof o.proximateSumPct === "number" ||
            (targetGroup && typeof targetGroup.proximate_sum_pct === "number")
        );
        if (proxBarEl) {
          if (hasProximateFlag) {
            var closureInfo = (targetGroup && targetGroup.proximate_closure) || {};
            var comps = o.proximateComponents ||
              (targetGroup && targetGroup.proximate_components) ||
              closureInfo.components ||
              {};
            var moistVal = typeof comps.moisture === "number" ? comps.moisture : null;
            var ashVal = typeof comps.ash === "number" ? comps.ash : null;
            var vsRaw = typeof comps.vs === "number"
              ? comps.vs
              : (typeof comps.volatile_solids === "number" ? comps.volatile_solids : null);
            var fcRaw = typeof comps.fc === "number"
              ? comps.fc
              : (typeof comps.fixed_carbon === "number" ? comps.fixed_carbon : null);
            var vsOrFcVal = vsRaw !== null
              ? vsRaw
              : (fcRaw !== null ? Math.max(0, 100.0 - fcRaw) : null);
            var computedSum = (moistVal !== null || ashVal !== null || vsOrFcVal !== null)
              ? Number(((moistVal || 0) + (ashVal || 0) + (vsOrFcVal || 0)).toFixed(2))
              : null;
            var sumPct =
              typeof o.proximateSumPct === "number"
                ? o.proximateSumPct
                : targetGroup && typeof targetGroup.proximate_sum_pct === "number"
                  ? targetGroup.proximate_sum_pct
                  : typeof closureInfo.proximate_sum_pct === "number"
                    ? closureInfo.proximate_sum_pct
                    : computedSum;
            proxBarEl.classList.remove("hidden");
            if (proxBarEl.style) proxBarEl.style.display = "block";
            if (typeof sumPct === "number" && !isNaN(sumPct) && sumPct > 0) {
              var scaleMax = Math.max(120, sumPct * 1.05);
              var bandLeftPct = ((95.0 / scaleMax) * 100).toFixed(2);
              var bandWidthPct = (((105.0 - 95.0) / scaleMax) * 100).toFixed(2);
              var hasBreakdown = moistVal !== null || ashVal !== null || vsOrFcVal !== null;
              var mW = hasBreakdown && moistVal ? Math.max(0, (moistVal / scaleMax) * 100).toFixed(2) : "0";
              var aW = hasBreakdown && ashVal ? Math.max(0, (ashVal / scaleMax) * 100).toFixed(2) : "0";
              var vW = hasBreakdown && vsOrFcVal ? Math.max(0, (vsOrFcVal / scaleMax) * 100).toFixed(2) : "0";
              var totalW = Math.min(100, Math.max(0, (sumPct / scaleMax) * 100)).toFixed(2);
              var barSegmentsHtml = hasBreakdown
                ? (moistVal ? '<div style="width:' + mW + '%;height:100%;background:#38bdf8;" title="Moisture: ' + moistVal.toFixed(2) + '%"></div>' : "") +
                  (ashVal ? '<div style="width:' + aW + '%;height:100%;background:#fbbf24;" title="Ash: ' + ashVal.toFixed(2) + '%"></div>' : "") +
                  (vsOrFcVal ? '<div style="width:' + vW + '%;height:100%;background:#a78bfa;" title="VS / (100 - FC): ' + vsOrFcVal.toFixed(2) + '%"></div>' : "")
                : '<div style="width:' + totalW + '%;height:100%;background:#f59e0b;" title="Proximate Sum: ' + sumPct.toFixed(2) + '%"></div>';
              var detailText = hasBreakdown
                ? "Moisture (" + (moistVal !== null ? moistVal.toFixed(1) + "%" : "—") + ") + Ash (" + (ashVal !== null ? ashVal.toFixed(1) + "%" : "—") + ") + VS (or 100 - FC) (" + (vsOrFcVal !== null ? vsOrFcVal.toFixed(1) + "%" : "—") + ") = " + Number(sumPct).toFixed(2) + "% (Acceptance Band: 95%–105%)"
                : "Proximate Closure Sum = " + Number(sumPct).toFixed(2) + "% (Acceptance Band: 95%–105%)";
              proxBarEl.innerHTML =
                '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">' +
                "<strong>⚖️ Proximate Mass-Balance Closure (95–105% Band)</strong>" +
                '<span class="flag-pill flag-proximate_sum">Proximate Closure: ' +
                Number(sumPct).toFixed(2) +
                "%</span></div>" +
                '<div data-role="proximate-stacked-bar" style="position:relative;width:100%;height:14px;border-radius:4px;background:rgba(15,23,42,0.35);border:1px solid rgba(148,163,184,0.35);overflow:hidden;margin:6px 0;">' +
                '<div style="display:flex;width:100%;height:100%;">' +
                barSegmentsHtml +
                "</div>" +
                '<div style="position:absolute;top:0;bottom:0;left:' +
                bandLeftPct +
                "%;width:" +
                bandWidthPct +
                '%;border-left:1px dashed #34d399;border-right:1px dashed #34d399;background:rgba(16,185,129,0.18);pointer-events:none;" title="95%–105% Acceptance Band"></div>' +
                "</div>" +
                "<div>" +
                detailText +
                "</div>";
            } else {
              proxBarEl.innerHTML =
                "<div>Proximate closure sum unavailable for this slice in snapshot.</div>";
            }
          } else {
            proxBarEl.classList.add("hidden");
            if (proxBarEl.style) proxBarEl.style.display = "none";
            proxBarEl.innerHTML = "";
          }
        }

        var vizLink = document.getElementById("show-me-open-visualizer-link");
        if (vizLink) {
          var href =
            "resource_explorer_dashboard.html?resource=" +
            encodeURIComponent(resolvedResource) +
            "&resources=" +
            encodeURIComponent(resolvedResource) +
            "&domain=" +
            encodeURIComponent(resolvedDomSlug) +
            "&type=" +
            encodeURIComponent(resolvedDomSlug) +
            "&parameter=" +
            encodeURIComponent(resolvedParameter) +
            "&params=" +
            encodeURIComponent(resolvedParameter) +
            "&highlight_rk=" +
            encodeURIComponent(targetKey);
          vizLink.setAttribute("href", href);
          vizLink.href = href;
        }

        pop.classList.remove("hidden");
        if (pop.style) pop.style.display = "block";

        return {
          decisionId: dec ? dec.decision_id : o.decisionId || null,
          replicateGroupKey: targetKey,
          resource: resolvedResource,
          analysisType: resolvedAnalysisType,
          parameter: resolvedParameter,
          peerCount: peerPoints.length,
          targetGroupCount: targetReps.filter(function (r) {
            return !r.isOutlier;
          }).length,
          outlierCount: targetReps.filter(function (r) {
            return r.isOutlier;
          }).length,
          hasProximateBar: hasProximateFlag
        };
      }

      if (typeof window !== "undefined") {
        window.openFlagShowMePopover = openFlagShowMePopover;
        window.closeFlagShowMePopover = closeFlagShowMePopover;
        window.__WORKBENCH_TEST_HOOKS__ = {
          state: state,
          WORKBENCH_DATA: WORKBENCH_DATA,
          canonicalDomainSlug: canonicalDomainSlug,
          groupContextLabel: groupContextLabel,
          computeCanonicalMethodSignature: computeCanonicalMethodSignature,
          normalizeReplicateGroupKey: normalizeReplicateGroupKey,
          matchesReplicateGroupKey: matchesReplicateGroupKey,
          findReplicateGroupForDecision: findReplicateGroupForDecision,
          refreshQcStateFromApi: refreshQcStateFromApi,
          renderContextualDrawer: renderContextualDrawer,
          renderDiagnosticPlot: renderDiagnosticPlot,
          parseDeepLinkQuery: parseDeepLinkQuery,
          selectDecision: selectDecision,
          matchesFacetFilters: matchesFacetFilters,
          DOMAIN_DEFS: DOMAIN_DEFS,
          normalizeDomainKey: normalizeDomainKey,
          getDefaultAssigneeEmail: getDefaultAssigneeEmail,
          getVisibleQueueDecisionIds: getVisibleQueueDecisionIds,
          toggleRowSelection: toggleRowSelection,
          toggleSelectAllFiltered: toggleSelectAllFiltered,
          selectAllFilteredRows: selectAllFilteredRows,
          clearRowSelection: clearRowSelection,
          fillBulkAssignMyEmail: fillBulkAssignMyEmail,
          bulkAssignSelected: bulkAssignSelected,
          updateBulkAssignBar: updateBulkAssignBar,
          openFlagShowMePopover: openFlagShowMePopover,
          closeFlagShowMePopover: closeFlagShowMePopover,
          setMinRsdFilter: setMinRsdFilter,
          setQuickFlagFilter: setQuickFlagFilter,
          setQueueSortBy: setQueueSortBy,
          inferInteractiveFlagTypes: inferInteractiveFlagTypes,
          mergeFlagTypesIntoDecision: mergeFlagTypesIntoDecision,
          isInteractiveFlaggedDecision: isInteractiveFlaggedDecision,
          initDecisionsFromPayload: initDecisionsFromPayload,
          resetAllFilters: resetAllFilters,
          syncSingleDecisionToGsheet: syncSingleDecisionToGsheet,
          syncBatchDecisionsToGsheet: syncBatchDecisionsToGsheet
        };
      }

      // Boot application
      initDecisionsFromPayload();
      populateFacetDropdowns();
      bindEvents();
      updateRoleUI();
      parseDeepLinkQuery();
      renderQueueTable();
      renderContextualDrawer();
      refreshQcStateFromApi();
    })();
  </script>
</body>
</html>
"""
    return (
        html_template.replace("__GENERATED_UTC__", generated_utc)
        .replace("__TOTAL_RECORDS__", str(total_records))
        .replace("__TOTAL_GROUPS__", str(total_groups))
        .replace("__TOTAL_FLAGGED__", str(total_flagged))
        .replace("__WORKBENCH_PAYLOAD_JSON__", payload_json)
    )


def build_resource_audit_workbench(
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Build the Product 4 Resource QC & Data Audit Workbench HTML artifact."""
    snapshot = load_snapshot(snapshot_path)
    payload = build_workbench_payload(snapshot)
    html_content = render_workbench_html(payload)

    resolved_out = output_path.expanduser().resolve()
    resolved_out.parent.mkdir(parents=True, exist_ok=True)
    resolved_out.write_text(html_content, encoding="utf-8")
    return resolved_out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for generating Product 4."""
    parser = argparse.ArgumentParser(
        description="Generate Product 4: Resource QC & Data Audit Workbench HTML."
    )
    parser.add_argument(
        "--from-snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT_PATH,
        help="Path to dashboard_data_snapshot.json (default: exports/plots/metadata/dashboard_data_snapshot.json).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output HTML path (default: exports/plots/metadata/resource_audit_workbench.html).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory override.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)
    if args.output is not None:
        output_path = args.output
    elif args.output_dir is not None:
        output_path = args.output_dir / "metadata" / "resource_audit_workbench.html"
    else:
        output_path = DEFAULT_OUTPUT_PATH

    written = build_resource_audit_workbench(
        snapshot_path=args.from_snapshot,
        output_path=output_path,
    )
    print(f"Generated Product 4 QC Audit Workbench: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
