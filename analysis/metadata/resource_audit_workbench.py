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
    "volatile matter",
    "fixed carbon",
    "moisture",
}

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
    return str(row.get("prep_method") or "").strip() or "unassigned"


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

    # 2. Compute Proximate closure totals per (resource_name, prepared_sample)
    proximate_param_means: dict[tuple[str, str], dict[str, float]] = defaultdict(
        dict
    )
    for group_key, group_recs in groups_map.items():
        first = group_recs[0]
        param_lower = str(first.get("parameter", "")).strip().lower()
        analysis_lower = str(first.get("analysis_type", "")).strip().lower()
        if (
            "proximate" in analysis_lower
            and param_lower in PROXIMATE_CLOSURE_PARAMETERS
        ):
            vals = [
                float(r["value"])
                for r in group_recs
                if r.get("value") is not None
            ]
            if vals:
                sample_key = (
                    str(first.get("resource_name", "")),
                    str(first.get("prepared_sample", "")),
                )
                proximate_param_means[sample_key][first["parameter"]] = round(
                    statistics.fmean(vals), 3
                )

    proximate_closure_by_sample: dict[str, dict[str, Any]] = {}
    for (res_name, prep_sample), comp_map in proximate_param_means.items():
        total_pct = round(sum(comp_map.values()), 2)
        out_of_bounds = total_pct < 95.0 or total_pct > 105.0
        proximate_closure_by_sample[f"{res_name}::{prep_sample}"] = {
            "resource_name": res_name,
            "prepared_sample": prep_sample,
            "components": comp_map,
            "closure_sum_pct": total_pct,
            "out_of_bounds": out_of_bounds,
        }

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
                    "analyst": rec.get("analyst", ""),
                    "exp_date": rec.get("exp_date", ""),
                    "experiment": rec.get("experiment", ""),
                    "prep_method": rec.get("prep_method", ""),
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
        closure_info = proximate_closure_by_sample.get(sample_closure_key)
        is_proximate_violation = bool(
            closure_info
            and closure_info.get("out_of_bounds")
            and "proximate" in str(first.get("analysis_type", "")).lower()
            and str(first.get("parameter", "")).strip().lower()
            in PROXIMATE_CLOSURE_PARAMETERS
        )

        flag_types: list[str] = []
        trigger_parts: list[str] = []

        if group_stats["count"] >= 2 and group_stats["rsd_pct"] > 10.0:
            flag_types.append("rsd_gt_10")
            trigger_parts.append(
                f"RSD {group_stats['rsd_pct']:.1f}% > 10% (n={group_stats['count']})"
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
            "eh_method": first.get("eh_method", ""),
            "strain": first.get("strain", ""),
            "time_h": first.get("time_h"),
            "group_context_label": first.get("group_context_label", ""),
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
                    "eh_method": first.get("eh_method", ""),
                    "strain": first.get("strain", ""),
                    "time_h": first.get("time_h"),
                    "group_context_label": first.get("group_context_label", ""),
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
                    "resolved_by_email": None,
                    "resolved_at": None,
                    "synced_to_gsheet": False,
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
                "iqr_outlier",
                "proximate_sum",
                "analyst_flagged",
            ],
            "analysts": analysts_list,
        },
        "decisions": candidate_decisions,
        "replicate_groups": replicate_groups,
        "co_measured_by_sample": dict(sample_params_map),
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
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Product 4 — Resource QC &amp; Data Audit Workbench | BioCIRV</title>
  <style>
    :root {
      --bg-page: #f4f6f9;
      --bg-card: #ffffff;
      --bg-drawer: #f8fafc;
      --bg-header: #0f172a;
      --text-main: #0f172a;
      --text-muted: #475569;
      --border-color: #cbd5e1;
      --accent-primary: #0284c7;
      --accent-primary-hover: #0369a1;
      --accent-admin: #7c3aed;
      --accent-success: #15803d;
      --accent-warn: #b45309;
      --accent-danger: #b91c1c;
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
      background: #ffffff;
      color: var(--text-main);
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .btn:hover:not(:disabled) {
      background: #f1f5f9;
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
      background: #eff6ff;
      border-bottom: 1px solid #bfdbfe;
      color: #1e3a8a;
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
      border-bottom: 1px solid #e2e8f0;
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
      background: #f8fafc;
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
      background: #ffffff;
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
      border-bottom: 1px solid #e2e8f0;
    }

    th {
      background: #f1f5f9;
      font-weight: 700;
      color: #334155;
      position: sticky;
      top: 0;
      z-index: 1;
    }

    tr.queue-row {
      cursor: pointer;
      transition: background 0.1s ease;
    }

    tr.queue-row:hover {
      background: #f0f9ff;
    }

    tr.queue-row.selected {
      background: #e0f2fe;
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

    .flag-iqr_outlier {
      background: #fee2e2;
      color: #991b1b;
    }

    .flag-proximate_sum {
      background: #fae8ff;
      color: #86198f;
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
      background: #ffedd5;
      color: #9a3412;
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
      box-shadow: 0 6px 20px rgba(15, 23, 42, 0.08);
    }

    .drawer-header {
      background: #0f172a;
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
      background: #ffffff;
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
      background: #f8fafc;
      padding: 10px;
      border-radius: 8px;
      border: 1px solid #e2e8f0;
    }

    .plot-stage {
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      background: #ffffff;
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
      border-top: 1px dashed #e2e8f0;
      margin-top: 8px;
    }

    .scope-toggle-group {
      display: flex;
      gap: 12px;
      margin: 8px 0 10px;
      padding: 8px 10px;
      background: #ffffff;
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
      border: 1px solid #94a3b8;
      background: #ffffff;
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
      background: #ffffff;
      border: 1px solid var(--border-color);
    }

    .timeline-step {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 8px;
      padding: 6px 0;
      border-bottom: 1px dashed #e2e8f0;
      font-size: 12px;
    }

    .timeline-step:last-child {
      border-bottom: none;
    }

    .timeline-label {
      font-weight: 700;
      color: #334155;
    }

    .transition-badge {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      padding: 2px 6px;
      border-radius: 4px;
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      font-size: 11px;
    }

    .readonly-analyst-badge {
      display: inline-block;
      padding: 4px 9px;
      border-radius: 6px;
      background: #f1f5f9;
      color: #475569;
      border: 1px solid #cbd5e1;
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
        <a href="../login.html" id="link-login-portal">🔐 Portal Login / Role Switcher</a>
      </nav>
    </div>
    <div class="topbar-right">
      <div class="user-pill" id="auth-user-pill">
        <span>👤 <strong id="auth-user-email">analyst@lbl.gov</strong></span>
        <span class="role-badge role-analyst" id="auth-user-role-badge">analyst</span>
      </div>
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
    <section class="kpi-strip" aria-label="QC Queue Summary Metrics">
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

        <div id="batch-gsheet-action-container">
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
          <label for="filter-flag-type">Flag Type</label>
          <select id="filter-flag-type">
            <option value="">All Flag Types</option>
            <option value="rsd_gt_10">rsd_gt_10 (RSD &gt; 10%)</option>
            <option value="iqr_outlier">iqr_outlier (Tukey 1.5×IQR)</option>
            <option value="proximate_sum">proximate_sum (Closure &lt;95% or &gt;105%)</option>
            <option value="analyst_flagged">analyst_flagged (Existing Fail/Flag)</option>
          </select>
        </div>
        <div class="field-group">
          <label for="filter-assigned-analyst">Assigned Analyst</label>
          <select id="filter-assigned-analyst">
            <option value="">All Analysts / Unassigned</option>
          </select>
        </div>
        <div class="field-group">
          <label for="filter-search">Search Sample / Record ID</label>
          <input type="search" id="filter-search" placeholder="e.g. PROX-AH-004 or AH-PREP-01" />
        </div>
      </div>
    </section>

    <div class="workbench-layout">
      <section class="queue-table-card" aria-label="Flagged Replicate Queue">
        <div class="table-scroll">
          <table id="qc-queue-table">
            <thead>
              <tr>
                <th>Decision ID</th>
                <th>Resource</th>
                <th>Prepared Sample</th>
                <th>Analysis Domain</th>
                <th>Parameter</th>
                <th>Flag Type(s)</th>
                <th>Trigger Diagnostic</th>
                <th>RSD % (n)</th>
                <th>Assigned To</th>
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
          <div style="font-size: 12px; color: #cbd5e1;">
            Deep Link: <code id="drawer-deeplink-code">?decision_id=QC-0001</code>
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
                  id="scope-single-replicate"
                  value="single"
                />
                <strong>Specific Single Replicate(s)</strong> (check individual outlier rows)
              </label>
            </div>

            <div class="table-scroll" style="max-height: 165px; border: 1px solid var(--border-color); border-radius: 6px; background: #fff; margin-bottom: 12px;">
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
                <label for="select-decision-action">Stage 1 Decision Action</label>
                <select id="select-decision-action">
                  <option value="reject_fail">Flag as QC Fail (new_qc_pass = fail)</option>
                  <option value="approve_pass">Approve as QC Pass (new_qc_pass = pass)</option>
                  <option value="needs_retest">Needs Lab Retest (in_review / retest)</option>
                  <option value="in_review">Keep Open / In Review</option>
                </select>
              </div>

              <div class="field-group">
                <label for="input-assigned-to">Assigned Reviewer Email</label>
                <div style="display: flex; gap: 6px;">
                  <input
                    type="email"
                    id="input-assigned-to"
                    placeholder="analyst@lbl.gov"
                  />
                  <button type="button" class="btn" id="btn-assign-to-me" title="PATCH /v1/qc/decisions/{id}/assign">
                    Assign to Me
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
              <div style="font-weight: 700; font-size: 12.5px; margin-bottom: 6px; color: #0f172a;">
                Audit Provenance &amp; Timestamp Timeline
              </div>

              <div class="timeline-step">
                <div>
                  <span class="timeline-label">1. Created / Flagged:</span>
                  <span id="prov-created-by">auto-qc-engine@biocirv.org</span>
                </div>
                <code id="prov-created-at">__GENERATED_UTC__</code>
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
      background: var(--bg-card, #ffffff);
      border: 1px solid var(--border-color, #cbd5e1);
      border-radius: 14px;
      max-width: 560px;
      width: 100%;
      padding: 20px;
      box-shadow: 0 20px 45px rgba(0, 0, 0, 0.55);
      display: flex;
      flex-direction: column;
      gap: 12px;
      color: var(--text-main, #0f172a);
    }
    .bug-modal-card input,
    .bug-modal-card select,
    .bug-modal-card textarea {
      width: 100%;
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid var(--border-color, #cbd5e1);
      background: var(--bg-drawer, #f8fafc);
      color: var(--text-main, #0f172a);
      font-size: 0.82rem;
      font-family: inherit;
    }
    .bug-modal-diag {
      background: var(--bg-drawer, #f8fafc);
      border: 1px solid var(--border-color, #cbd5e1);
      border-radius: 8px;
      padding: 10px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.75rem;
      color: var(--text-muted, #475569);
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
        <button id="btn-submit-github-api" type="button" class="btn" title="Create GitHub Issue directly via /v1/qc/github-issue when server GITHUB_TOKEN is configured">
          ⚡ Submit via API
        </button>
        <button id="btn-submit-github-url" type="button" class="btn btn-primary">
          ↗ Open Pre-Filled GitHub Issue
        </button>
      </div>
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
          assignedAnalyst: "",
          search: ""
        },
        decisionsById: {},
        decisionsOrder: [],
        selectedDecisionId: null,
        selectedGroupKey: null,
        inspectedGroupKey: null,
        plotStyle: "forest_iqr",
        groupBy: "field_sample",
        scopeMode: "group",
        selectedReplicateIds: {},
        selectedChips: {}
      };

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

      function initDecisionsFromPayload() {
        var list = WORKBENCH_DATA.decisions || [];
        state.decisionsById = {};
        state.decisionsOrder = [];
        for (var i = 0; i < list.length; i++) {
          var item = JSON.parse(JSON.stringify(list[i]));
          state.decisionsById[item.decision_id] = item;
          state.decisionsOrder.push(item.decision_id);
        }
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

      function refreshAnalystFilterOptions() {
        var sel = document.getElementById("filter-assigned-analyst");
        if (!sel) return;
        var currentVal = sel.value;
        var emails = {};
        var baseAnalysts = (WORKBENCH_DATA.facets && WORKBENCH_DATA.facets.analysts) || [];
        for (var i = 0; i < baseAnalysts.length; i++) {
          if (baseAnalysts[i]) emails[baseAnalysts[i]] = true;
        }
        for (var j = 0; j < state.decisionsOrder.length; j++) {
          var d = state.decisionsById[state.decisionsOrder[j]];
          if (d && d.assigned_to_email) {
            emails[d.assigned_to_email] = true;
          }
        }
        sel.innerHTML = "";
        var optAll = document.createElement("option");
        optAll.value = "";
        optAll.textContent = "All Analysts / Unassigned";
        sel.appendChild(optAll);
        var optMe = document.createElement("option");
        optMe.value = "__ME__";
        optMe.textContent = "Assigned to Me (" + (state.user.email || "me") + ")";
        sel.appendChild(optMe);
        var sorted = Object.keys(emails).sort();
        for (var k = 0; k < sorted.length; k++) {
          var o = document.createElement("option");
          o.value = sorted[k];
          o.textContent = sorted[k];
          sel.appendChild(o);
        }
        sel.value = currentVal;
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
          return !assigned && status === "open";
        }
        if (tabName === "all_open") {
          return status === "open";
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
          var flags = dec.flag_types || [dec.flag_type];
          if (flags.indexOf(f.flagType) === -1) return false;
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
            (dec.record_ids || []).join(" ")
          ]
            .join(" ")
            .toLowerCase();
          if (hay.indexOf(q) === -1) return false;
        }
        return true;
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

      function setText(id, val) {
        var el = document.getElementById(id);
        if (el) el.textContent = String(val);
      }

      function renderQueueTable() {
        computeQueueCounts();
        var tbody = document.getElementById("qc-queue-tbody");
        if (!tbody) return;
        tbody.innerHTML = "";

        var visibleIds = [];
        for (var i = 0; i < state.decisionsOrder.length; i++) {
          var id = state.decisionsOrder[i];
          var dec = state.decisionsById[id];
          if (!dec) continue;
          if (!matchesQueueTab(dec, state.activeQueueTab)) continue;
          if (!matchesFacetFilters(dec)) continue;
          visibleIds.push(id);
        }

        if (visibleIds.length === 0) {
          var emptyTr = document.createElement("tr");
          var emptyTd = document.createElement("td");
          emptyTd.colSpan = 11;
          emptyTd.style.textAlign = "center";
          emptyTd.style.padding = "20px";
          emptyTd.style.color = "#64748b";
          emptyTd.textContent = "No QC items match the current queue tab and facet filters.";
          emptyTr.appendChild(emptyTd);
          tbody.appendChild(emptyTr);
          return;
        }

        for (var j = 0; j < visibleIds.length; j++) {
          var decItem = state.decisionsById[visibleIds[j]];
          var tr = document.createElement("tr");
          tr.className =
            "queue-row" +
            (decItem.decision_id === state.selectedDecisionId ? " selected" : "");
          tr.setAttribute("data-decision-id", decItem.decision_id);

          var flagsHtml = (decItem.flag_types || [decItem.flag_type])
            .map(function (ft) {
              return '<span class="flag-pill flag-' + ft + '">' + ft + "</span>";
            })
            .join("");

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

          tr.innerHTML =
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
          actionSel.value =
            dec.decision_action && dec.decision_action !== "open"
              ? dec.decision_action
              : "reject_fail";
        }
        var assignedInput = document.getElementById("input-assigned-to");
        if (assignedInput) {
          assignedInput.value = dec.assigned_to_email || "";
        }
        var noteInput = document.getElementById("input-review-note");
        if (noteInput) {
          noteInput.value = dec.review_note || "";
        }

        // Update 4-step Audit Provenance Timeline
        setText("prov-created-by", dec.submitted_by_email || "auto-qc-engine@biocirv.org");
        setText("prov-created-at", dec.created_at || WORKBENCH_DATA.generated_utc || "—");
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
        if (gsheetBadge) {
          if (dec.synced_to_gsheet) {
            gsheetBadge.textContent = "Synced to GSheet";
            gsheetBadge.className = "status-pill status-synced";
          } else {
            gsheetBadge.textContent = "Pending Admin GSheet Sync";
            gsheetBadge.className = "status-pill status-open";
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
        for (var i = 0; i < reps.length; i++) {
          var r = reps[i];
          var tr = document.createElement("tr");
          if (r.is_iqr_outlier || r.is_analyst_flagged) {
            tr.style.background = "#fff1f2";
          }
          var checked = Boolean(state.selectedReplicateIds[r.record_id]);
          var disabled = state.scopeMode === "group";
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
            escapeHtml(r.qc_status || "pass") +
            "</code></td>";

          tbody.appendChild(tr);
        }

        var checkboxes = tbody.querySelectorAll(".replicate-checkbox");
        for (var j = 0; j < checkboxes.length; j++) {
          checkboxes[j].addEventListener("change", function (ev) {
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

        var svgParts = [];
        svgParts.push(
          '<rect x="0" y="0" width="' +
            width +
            '" height="' +
            height +
            '" fill="#ffffff" />'
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
          var closure =
            (WORKBENCH_DATA.proximate_closure_by_sample || {})[sampleKey] || null;
          var comps = (closure && closure.components) || {};
          var compNames = Object.keys(comps);
          var sumVal = closure ? closure.closure_sum_pct : st.mean || 0;

          svgParts.push(
            '<text x="' +
              padL +
              '" y="20" font-size="12" font-weight="700" fill="#0f172a">Proximate Mass-Balance Closure — ' +
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
              '" fill="#dcfce7" opacity="0.65" />'
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
          for (var cIdx = 0; cIdx < compNames.length; cIdx++) {
            var cName = compNames[cIdx];
            var cVal = Number(comps[cName] || 0);
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
                '" text-anchor="middle" font-size="11" fill="#334155">' +
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
                '" fill="#e0f2fe" opacity="0.65" />'
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
                  '" text-anchor="middle" font-size="11" fill="#0f172a">' +
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
                '" fill="#e0f2fe" opacity="0.65" />'
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
                  '" text-anchor="end" font-size="11" fill="#334155">Rep #' +
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
                  (isOutN ? "#b91c1c" : "#0f172a") +
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
                merged.decision_status =
                  srv.decision_status || srv.status || merged.decision_status;
                merged.status =
                  srv.status || srv.decision_status || merged.status || merged.decision_status;
                merged.decision_action =
                  srv.decision_action || merged.decision_action;
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
                merged.synced_to_gsheet = Boolean(srv.synced_to_gsheet);
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
                hydrated.flag_type = srv.flag_type || "analyst_flagged";
                hydrated.flag_types =
                  Array.isArray(srv.flag_types) && srv.flag_types.length > 0
                    ? srv.flag_types
                    : [hydrated.flag_type];
                state.decisionsById[did] = hydrated;
                if (state.decisionsOrder.indexOf(did) === -1) {
                  state.decisionsOrder.push(did);
                }
              }
            });
            parseDeepLinkQuery();
            renderQueueTable();
            renderContextualDrawer();
          })
          .catch(function () {
            parseDeepLinkQuery();
            renderQueueTable();
            renderContextualDrawer();
          });
      }

      function saveStage1Decision() {
        var dec = state.decisionsById[state.selectedDecisionId];
        if (!dec) return;

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

        var actionVal = actionEl ? actionEl.value : "reject_fail";
        var newQcPass =
          actionVal === "approve_pass"
            ? "pass"
            : actionVal === "reject_fail"
            ? "fail"
            : dec.old_qc_pass || "pass";
        var newStatus =
          actionVal === "approve_pass" || actionVal === "reject_fail"
            ? "resolved"
            : actionVal === "needs_retest"
            ? "needs_retest"
            : "in_review";

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

        fetch("/v1/qc/decisions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(requestBody)
        })
          .then(function (resp) {
            return resp.ok ? resp.json() : null;
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
                updated_at: nowUtc
              });
            }
            showToast(
              "Stage 1 PostgreSQL Decision Saved (" +
                dec.decision_id +
                ": " +
                dec.old_qc_pass +
                " → " +
                newQcPass +
                "). Pending Admin Stage 2 Google Sheets Sync.",
              false
            );
            renderQueueTable();
            renderContextualDrawer();
          });
      }

      function assignSelectedToMe() {
        var dec = state.decisionsById[state.selectedDecisionId];
        if (!dec) return;
        var myEmail = state.user.email || "analyst@lbl.gov";
        dec.assigned_to_email = myEmail;
        var assignedEl = document.getElementById("input-assigned-to");
        if (assignedEl) assignedEl.value = myEmail;

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
              body: JSON.stringify({ assigned_to_email: "me" })
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
              assigned_to_email: myEmail
            })
          });
        }

        reqPromise
          .then(function (resp) {
            return resp && resp.ok ? resp.json() : null;
          })
          .then(function (resData) {
            if (resData && resData.decision && resData.decision.id != null) {
              dec.db_id = Number(resData.decision.id);
            }
          })
          .catch(function () {})
          .finally(function () {
            showToast(
              "Assigned " + dec.decision_id + " to " + myEmail + ".",
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
              return resp.ok ? resp.json() : null;
            })
            .then(function (resData) {
              if (resData && resData.decision && resData.decision.id != null) {
                dec.db_id = Number(resData.decision.id);
                return dec.db_id;
              }
              return null;
            })
            .catch(function () {
              return null;
            });
        }

        ensureDbIdPromise()
          .then(function (dbId) {
            if (dbId === null || dbId === undefined) {
              return null;
            }
            return fetch(
              "/v1/qc/decisions/" + encodeURIComponent(dbId) + "/sync-gsheet",
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin"
              }
            ).then(function (resp) {
              return resp.ok ? resp.json() : null;
            });
          })
          .catch(function () {
            return null;
          })
          .finally(function () {
            dec.decision_status = "resolved";
            dec.synced_to_gsheet = true;
            dec.gsheet_synced_at = nowUtc;
            dec.gsheet_synced_by_email = state.user.email || "admin@lbl.gov";
            showToast(
              "Stage 2 Google Sheets write-back completed for " +
                dec.decision_id +
                ".",
              false
            );
            renderQueueTable();
            renderContextualDrawer();
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
        fetch("/v1/qc/decisions/sync-gsheet-batch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ decision_ids: ids.length ? ids : null })
        })
          .catch(function () {})
          .finally(function () {
            for (var j = 0; j < pending.length; j++) {
              var item = pending[j];
              if (item) {
                item.synced_to_gsheet = true;
                item.gsheet_synced_at = nowUtc;
                item.gsheet_synced_by_email =
                  state.user.email || "admin@lbl.gov";
              }
            }
            showToast(
              "Batch Stage 2 Google Sheets sync completed for " +
                pending.length +
                " resolved decision(s).",
              false
            );
            renderQueueTable();
            renderContextualDrawer();
          });
      }

      function parseDeepLinkQuery() {
        if (typeof window === "undefined" || !window.location) return;
        var params = new URLSearchParams(window.location.search || "");
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
          for (var k = 0; k < state.decisionsOrder.length; k++) {
            var d = state.decisionsById[state.decisionsOrder[k]];
            if (!d) continue;
            if (
              d.decision_id === qDecisionId ||
              String(d.db_id || "") === String(qDecisionId) ||
              String(d.id || "") === String(qDecisionId) ||
              d.decision_id === paddedCandidate ||
              d.decision_id === paddedDbCandidate
            ) {
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
        bindFilter("filter-assigned-analyst", "assignedAnalyst");
        bindFilter("filter-search", "search");

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

        var assignMeBtn = document.getElementById("btn-assign-to-me");
        if (assignMeBtn) {
          assignMeBtn.addEventListener("click", assignSelectedToMe);
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
                    statusEl.innerHTML = "✓ GitHub Issue #" + escapeHtml(data.issue_number ?? "") + " created! <a href=\\"" + escapeHtml(data.issue_url ?? "") + "\\" target=\\"_blank\\" rel=\\"noopener\\">View Issue &rarr;</a>";
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

      if (typeof window !== "undefined") {
        window.__WORKBENCH_TEST_HOOKS__ = {
          state: state,
          WORKBENCH_DATA: WORKBENCH_DATA,
          canonicalDomainSlug: canonicalDomainSlug,
          groupContextLabel: groupContextLabel,
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
          normalizeDomainKey: normalizeDomainKey
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
