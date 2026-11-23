"""Note-Mining, Mass-Balance Diagnostics, and Synthesized AI Insights Engine.

Extracts analyst notes across `field_sample`, `prepared_sample`, and all 10
Aim 1 / Aim 2 `*_record` tables, computes per-resource mass-balance closures,
pretreatment lift factors, and cross-resource percentiles, and writes the
version-controlled JSON sidecar `data/insights/resource_ai_insights.json`.

Usage:
    # From live PostgreSQL (via Pixi):
    pixi run python analysis/metadata/resource_insights_engine.py

    # From a JSON snapshot:
    python3 analysis/metadata/resource_insights_engine.py --from-snapshot path/to/snapshot.json
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SIDECAR_PATH = REPO_ROOT / "data" / "insights" / "resource_ai_insights.json"


def _mean_sd(vals: list[float]) -> dict[str, float | int | None]:
    clean = [float(v) for v in vals if v is not None and not math.isnan(float(v))]
    if not clean:
        return {"n": 0, "mean": None, "sd": None, "min": None, "max": None, "cv_pct": None}
    n = len(clean)
    mean = sum(clean) / n
    var = sum((x - mean) ** 2 for x in clean) / (n - 1) if n > 1 else 0.0
    sd = math.sqrt(var)
    cv = (sd / abs(mean) * 100.0) if abs(mean) > 1e-9 and n > 1 else 0.0
    return {
        "n": n,
        "mean": round(mean, 3),
        "sd": round(sd, 3),
        "min": round(min(clean), 3),
        "max": round(max(clean), 3),
        "cv_pct": round(cv, 2),
    }


def _ordinal(n: int | None) -> str:
    if n is None:
        return ""
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


DIXON_Q_CRITICAL_VALUES_ALPHA_0_05: dict[int, float] = {
    3: 0.970,
    4: 0.829,
    5: 0.710,
    6: 0.625,
    7: 0.568,
    8: 0.526,
    9: 0.493,
    10: 0.466,
    11: 0.444,
    12: 0.426,
    13: 0.410,
    14: 0.396,
    15: 0.384,
    16: 0.374,
    17: 0.365,
    18: 0.356,
    19: 0.349,
    20: 0.342,
    21: 0.337,
    22: 0.331,
    23: 0.326,
    24: 0.321,
    25: 0.317,
    26: 0.312,
    27: 0.308,
    28: 0.305,
    29: 0.301,
    30: 0.290,
}

DIXON_MIN_RSD_PCT: float = 10.0

ANALYSIS_TYPE_TO_TAB: dict[str, str] = {
    "Proximate Analysis": "proximate",
    "Calorimetry": "proximate",
    "Compositional Analysis": "compositional",
    "Ultimate Analysis": "compositional",
    "XRD Crystallinity": "compositional",
    "ICP Elemental Analysis": "elemental",
    "ICP-OES / ICP-MS": "elemental",
    "XRF Elemental Analysis": "elemental",
    "XRF Elemental": "elemental",
    "Pretreatment & Hydrolysis": "pretreatment",
    "Pretreatment": "pretreatment",
    "Fermentation (Bioconversion)": "fermentation",
    "Fermentation": "fermentation",
    "Gasification": "fermentation",
}

_SLUG_TO_TAB: dict[str, str] = {
    "proximate": "proximate",
    "calorimetry": "proximate",
    "compositional": "compositional",
    "ultimate": "compositional",
    "xrd": "compositional",
    "icp": "elemental",
    "xrf": "elemental",
    "pretreatment": "pretreatment",
    "fermentation": "fermentation",
    "gasification": "fermentation",
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


def _canonical_domain_slug(analysis_type: str | None) -> str:
    """Map raw analysis_type string to one of the 10 canonical analytical domain slugs."""
    raw = str(analysis_type or "").strip().lower()
    if not raw:
        return "unknown"
    if raw.endswith("_record"):
        raw = raw[:-7]
    mapping = {
        "proximate analysis": "proximate",
        "proximate": "proximate",
        "ultimate analysis": "ultimate",
        "ultimate": "ultimate",
        "compositional analysis": "compositional",
        "compositional": "compositional",
        "calorimetry": "calorimetry",
        "calorimetry analysis": "calorimetry",
        "calorimetry_xrd": "calorimetry",
        "xrd crystallinity": "xrd",
        "xrd analysis": "xrd",
        "xrd": "xrd",
        "icp-oes / icp-ms": "icp",
        "icp elemental analysis": "icp",
        "icp analysis": "icp",
        "icp": "icp",
        "xrf elemental": "xrf",
        "xrf elemental analysis": "xrf",
        "xrf analysis": "xrf",
        "xrf": "xrf",
        "ash": "xrf",
        "pretreatment": "pretreatment",
        "pretreatment & hydrolysis": "pretreatment",
        "fermentation": "fermentation",
        "fermentation (bioconversion)": "fermentation",
        "gasification": "gasification",
    }
    if raw in mapping:
        return mapping[raw]
    for slug in CANONICAL_DOMAIN_SLUGS:
        if slug in raw:
            return slug
    return raw


canonical_domain_slug = _canonical_domain_slug


def _median(vals: list[float]) -> float | None:
    clean = sorted(float(v) for v in vals if v is not None and not math.isnan(float(v)))
    if not clean:
        return None
    m = len(clean)
    if m % 2 == 1:
        return round(clean[m // 2], 2)
    return round(0.5 * (clean[m // 2 - 1] + clean[m // 2]), 2)


def _check_abundance_cutoff(analysis_type: str, parameter: str, unit: str, mean_val: float | None) -> tuple[bool, str | None]:
    """Return (below_cutoff, cutoff_label) to suppress low-abundance noise flags."""
    if mean_val is None:
        return True, "No numeric mean"
    abs_m = abs(float(mean_val))
    u_low = (unit or "").strip().lower()
    p_low = (parameter or "").strip().lower()
    if analysis_type in ("ICP Elemental Analysis", "XRF Elemental Analysis") or u_low == "ppm":
        # ICP, XRF, and trace syngas ppm measurements: suppress flags below 100 ppm (0.01 wt%)
        if abs_m < 100.0:
            return True, "<100 ppm"
        return False, None
    if analysis_type == "Compositional Analysis":
        # Suppress trace sugar/extractive fractions below 0.5% dry weight
        if abs_m < 0.5:
            return True, "<0.5% dw"
        return False, None
    if analysis_type == "Fermentation (Bioconversion)":
        # Suppress near-zero depleted sugar residuals or trace titers below 0.5 g/L (or 0.5 OD)
        if ("conc" in p_low or "titer" in p_low or "sugar" in p_low or "od600" in p_low) and abs_m < 0.5:
            return True, "<0.5 g/L"
        if abs_m < 1.0 and "yield" in p_low:
            return True, "<1.0% yld"
        return False, None
    if abs_m < 0.25:
        return True, "<0.25 baseline"
    return False, None


def _group_context_label(row: dict[str, Any]) -> str:
    """Return the relevant method/strain/time context string for a replicate group."""
    slug = _canonical_domain_slug(row.get("analysis_type") or row.get("domain"))
    if slug == "pretreatment":
        pt = (
            row.get("pt_method")
            or (row.get("prep_method") if "pt_method" not in row else None)
            or "none"
        )
        eh = row.get("eh_method") or "none"
        return f"{pt} · {eh}" if eh and eh != "none" else pt
    if slug == "fermentation":
        pt = row.get("pt_method") or ""
        st = (
            row.get("strain")
            or (row.get("prep_method") if "strain" not in row else None)
            or "no-strain"
        )
        th = row.get("time_h")
        base = f"{pt} · {st}" if pt and pt != "none" else st
        if th is not None and th != "":
            try:
                return f"{base} @ {float(th):g}h"
            except (TypeError, ValueError):
                pass
        return base
    if slug == "gasification":
        vessel = str(row.get("vessel") or "").strip()
        if vessel and vessel.lower() not in ("n/a", "none"):
            return (
                vessel
                if vessel.lower().startswith("reactor:")
                else f"Reactor: {vessel}"
            )
        return str(row.get("prep_method") or "unassigned")
    return row.get("prep_method") or "unassigned"


group_context_label = _group_context_label


def compute_canonical_method_signature(
    row_or_domain: dict[str, Any] | str | None,
    row: dict[str, Any] | None = None,
) -> str:
    """Return canonical domain-aware method/context signature (`group_context_label`)."""
    if isinstance(row_or_domain, dict):
        return _group_context_label(row_or_domain)
    merged = dict(row or {})
    if row_or_domain and "analysis_type" not in merged:
        merged["analysis_type"] = str(row_or_domain)
    return _group_context_label(merged)


def _replicate_group_key(row: dict[str, Any]) -> tuple[str, ...]:
    """Build the canonical replicate group key (extending the 6-part Aim 1 key to Aim 2)."""
    return (
        str(row.get("resource_name") or ""),
        str(row.get("prepared_sample") or ""),
        str(row.get("analysis_type") or ""),
        str(row.get("parameter") or ""),
        str(row.get("unit") or ""),
        _group_context_label(row),
        str(row.get("experiment") or ""),
    )


def _percentile_rank(val: float | None, population: list[float]) -> int | None:
    if val is None or not population:
        return None
    clean = sorted(float(x) for x in population if x is not None)
    if not clean:
        return None
    below = sum(1 for x in clean if x < val)
    equal = sum(1 for x in clean if abs(x - val) <= 1e-9)
    pct = int(round(((below + 0.5 * equal) / len(clean)) * 100))
    return max(1, min(99, pct))


PROXIMATE_CLOSURE_MIN_PCT = 95.0
PROXIMATE_CLOSURE_MAX_PCT = 105.0


def _proximate_component_bucket(param_name: str) -> str | None:
    """Map a parameter name to its canonical Data Portal proximate component bucket."""
    p = str(param_name or "").strip().lower()
    if p == "moisture":
        return "moisture"
    if p in {"ash", "ash solids"}:
        return "ash"
    if p in {"volatile solids", "volatile matter"}:
        return "volatile_solids"
    if p == "fixed carbon":
        return "fixed_carbon"
    return None


def compute_proximate_closure_strata(
    rows_by_resource: dict[str, list[dict[str, Any]]],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Compute Data Portal proximate_sum across (resource_name, experiment, prep_method) strata.

    Formula:
        avg_moisture + avg_ash + (avg_vs if avg_vs is not None else (100 - avg_fc if avg_fc is not None else 0))
    Across non-fail Proximate Analysis observations.
    """
    stratum_buckets: dict[tuple[str, str, str], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for rname, rrows in rows_by_resource.items():
        for r in rrows:
            if _canonical_domain_slug(r.get("analysis_type")) != "proximate":
                continue
            if str(r.get("qc_status") or "pass").lower() == "fail":
                continue
            bucket = _proximate_component_bucket(str(r.get("parameter") or ""))
            if bucket is None:
                continue
            val = r.get("value")
            if val is None:
                continue
            try:
                fval = float(val)
            except (TypeError, ValueError):
                continue
            if math.isnan(fval):
                continue
            key = (
                str(r.get("resource_name") or rname or ""),
                str(r.get("experiment") or "unassigned"),
                _group_context_label(r) or "unassigned",
            )
            stratum_buckets[key][bucket].append(fval)

    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for key, comp_lists in stratum_buckets.items():
        comp_means: dict[str, float] = {
            comp: round(sum(vals) / len(vals), 4)
            for comp, vals in comp_lists.items()
            if vals
        }
        avg_m = comp_means.get("moisture")
        avg_a = comp_means.get("ash")
        avg_vs = comp_means.get("volatile_solids")
        avg_fc = comp_means.get("fixed_carbon")
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
            and (
                total_pct < PROXIMATE_CLOSURE_MIN_PCT
                or total_pct > PROXIMATE_CLOSURE_MAX_PCT
            )
        )
        result[key] = {
            "resource_name": key[0],
            "experiment": key[1],
            "prep_method": key[2],
            "components": comp_means,
            "proximate_sum_pct": total_pct,
            "out_of_bounds": out_of_bounds,
        }
    return result


def compute_dataset_outlier_screening(
    rows_by_resource: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """Run colleague's replicate-precision & candidate outlier screens + Within vs Between RSD."""
    proximate_closure_by_stratum = compute_proximate_closure_strata(rows_by_resource)

    # Step 1: Partition all numeric observations into replicate groups
    raw_groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for rname, rrows in rows_by_resource.items():
        for r in rrows:
            if r.get("value") is None or r.get("parameter") == "(metadata only)":
                continue
            key = _replicate_group_key(r)
            raw_groups[key].append(r)

    # Step 2: Compute basic group stats (n, mean, sd, rsd_within, dixon_q) and accumulate pooled SD
    # Pooled SD is accumulated per (analysis_type, parameter, unit) across groups above the abundance cutoff
    pooled_num: dict[tuple[str, str, str], float] = defaultdict(float)
    pooled_den: dict[tuple[str, str, str], int] = defaultdict(int)
    group_records: list[dict[str, Any]] = []

    for key, grp_rows in raw_groups.items():
        rname, ps_name, atype, param, unit, ctx_method, exp_id = key
        # Sort observations ascending by numeric value for Dixon's Q test
        obs_sorted = sorted(
            grp_rows,
            key=lambda x: (float(x["value"]), str(x.get("record_id") or "")),
        )
        vals = [float(x["value"]) for x in obs_sorted]
        n = len(vals)
        mean_val = sum(vals) / n
        var_val = sum((v - mean_val) ** 2 for v in vals) / (n - 1) if n >= 2 else None
        sd_val = math.sqrt(var_val) if var_val is not None else None
        rsd_within = (
            round((sd_val / abs(mean_val)) * 100.0, 2)
            if (sd_val is not None and abs(mean_val) > 1e-9)
            else None
        )

        below_cutoff, cutoff_label = _check_abundance_cutoff(atype, param, unit, mean_val)

        if n >= 2 and sd_val is not None and not below_cutoff:
            p_key = (atype, param, unit)
            pooled_num[p_key] += (n - 1) * (sd_val ** 2)
            pooled_den[p_key] += (n - 1)

        # Dixon's Q two-sided test (alpha = 0.05, 3 <= n <= 30)
        dixon_q: float | None = None
        dixon_crit: float | None = None
        dixon_side: str | None = None
        dixon_cand_id: str | None = None
        raw_dixon = False
        if 3 <= n <= 30:
            dixon_crit = DIXON_Q_CRITICAL_VALUES_ALPHA_0_05.get(n)
            data_range = vals[-1] - vals[0]
            if data_range > 1e-12 and dixon_crit is not None:
                q_low = (vals[1] - vals[0]) / data_range
                q_high = (vals[-1] - vals[-2]) / data_range
                if q_low >= q_high:
                    dixon_q = round(q_low, 4)
                    dixon_side = "low"
                    dixon_cand_id = str(obs_sorted[0]["record_id"])
                else:
                    dixon_q = round(q_high, 4)
                    dixon_side = "high"
                    dixon_cand_id = str(obs_sorted[-1]["record_id"])
                raw_dixon = bool(
                    dixon_q > dixon_crit
                    and rsd_within is not None
                    and rsd_within >= DIXON_MIN_RSD_PCT
                )
            elif data_range <= 1e-12:
                dixon_q = 0.0

        has_identical_replicates = bool(
            n >= 2
            and (
                (max(vals) - min(vals)) <= 1e-9
                or len({round(v, 4) for v in vals}) == 1
            )
        )

        replicate_group_key = (
            f"{rname.strip().lower()}::{ps_name.strip().lower()}::"
            f"{_canonical_domain_slug(atype)}::{param.strip().lower()}::"
            f"{ctx_method.strip().lower()}::{exp_id.strip().lower()}"
        )

        qc_pass_cnt = sum(1 for x in obs_sorted if x.get("qc_status") == "pass")
        qc_fail_cnt = sum(1 for x in obs_sorted if x.get("qc_status") == "fail")
        qc_mixed = bool(qc_pass_cnt > 0 and qc_fail_cnt > 0)

        notes_uniq = list(dict.fromkeys(
            strip_qc_audit_annotations(x.get("note"))
            for x in obs_sorted
            if strip_qc_audit_annotations(x.get("note"))
        ))

        tab_resolved = (
            ANALYSIS_TYPE_TO_TAB.get(atype)
            or _SLUG_TO_TAB.get(_canonical_domain_slug(atype), "proximate")
        )

        prox_info = (
            proximate_closure_by_stratum.get(
                (rname, exp_id or "unassigned", ctx_method or "unassigned")
            )
            if _canonical_domain_slug(atype) == "proximate"
            and _proximate_component_bucket(param) is not None
            else None
        )
        raw_proximate_sum = bool(prox_info["out_of_bounds"]) if prox_info else False
        proximate_sum_pct = prox_info["proximate_sum_pct"] if prox_info else None
        proximate_components = dict(prox_info["components"]) if prox_info else {}

        sd_rounded = round(sd_val, 3) if sd_val is not None else None
        group_records.append({
            "resource_name": rname,
            "tab_key": tab_resolved,
            "group_id": "|".join(key),
            "replicate_group_key": replicate_group_key,
            "analysis_type": atype,
            "prepared_sample": ps_name,
            "prep_method": ctx_method,
            "experiment": exp_id,
            "parameter": param,
            "unit": unit,
            "n": n,
            "mean": round(mean_val, 3),
            "sd": sd_rounded,
            "within_sd": sd_rounded,
            "rsd_within_pct": rsd_within,
            "dixon_q": dixon_q,
            "dixon_crit": dixon_crit,
            "dixon_side": dixon_side,
            "dixon_candidate_id": dixon_cand_id,
            "has_identical_replicates": has_identical_replicates,
            "qc_pass_count": qc_pass_cnt,
            "qc_fail_count": qc_fail_cnt,
            "qc_mixed": qc_mixed,
            "below_cutoff": below_cutoff,
            "cutoff_label": cutoff_label,
            "raw_dixon": raw_dixon,
            "raw_rsd20": bool(rsd_within is not None and rsd_within > 20.0),
            "raw_rsd10": bool(rsd_within is not None and rsd_within > 10.0),
            "raw_proximate_sum": raw_proximate_sum,
            "proximate_sum_pct": proximate_sum_pct,
            "proximate_components": proximate_components,
            "replicates": [
                {
                    "id": str(x["record_id"]),
                    "rep": x.get("replicate") or (idx + 1),
                    "val": round(float(x["value"]), 3),
                    "qc": x.get("qc_status") or "pass",
                }
                for idx, x in enumerate(obs_sorted)
            ],
            "note": "; ".join(notes_uniq)[:240] if notes_uniq else "",
        })

    pooled_sd_map: dict[tuple[str, str, str], float] = {
        pk: math.sqrt(pooled_num[pk] / pooled_den[pk])
        for pk in pooled_num
        if pooled_den.get(pk, 0) > 0
    }

    # Step 3: Evaluate 3xSD_pooled screen and group by (resource_name, analysis_type, parameter, prep_method, unit)
    groups_by_res_param: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for g in group_records:
        pk = (g["analysis_type"], g["parameter"], g["unit"])
        p_sd = pooled_sd_map.get(pk)
        g["pooled_sd"] = round(p_sd, 3) if p_sd is not None else None
        max_dev: float | None = None
        sd3x_ids: list[str] = []
        if g["n"] >= 2:
            m_v = float(g["mean"])
            devs = [abs(float(r["val"]) - m_v) for r in g["replicates"]]
            max_dev = round(max(devs), 3) if devs else None
            if p_sd is not None and p_sd > 1e-9:
                thresh = 3.0 * p_sd
                sd3x_ids = [
                    r["id"]
                    for r in g["replicates"]
                    if abs(float(r["val"]) - m_v) > thresh
                ]
        g["max_abs_dev"] = max_dev
        g["sd3x_candidate_ids"] = sd3x_ids
        g["raw_sd3x"] = len(sd3x_ids) > 0

        # Primary candidate outlier screen: Dixon Q OR RSD > 20% OR 3xSD OR Mixed QC OR Proximate Sum
        raw_flagged = bool(
            g["raw_dixon"]
            or g["raw_rsd20"]
            or g["raw_sd3x"]
            or g["qc_mixed"]
            or g["raw_proximate_sum"]
        )
        g["raw_flagged"] = raw_flagged
        active_flagged = bool(not g["below_cutoff"] and raw_flagged)
        g["active_flagged"] = active_flagged
        g["flagged_active"] = active_flagged
        g["active_rsd10"] = bool(not g["below_cutoff"] and g["raw_rsd10"])
        g["active_proximate_sum"] = bool(
            not g["below_cutoff"] and g["raw_proximate_sum"]
        )

        groups_by_res_param[(g["resource_name"], g["analysis_type"], g["parameter"], g["prep_method"], g["unit"])].append(g)

    # Step 4: Compute Parameter-level Within-Group vs Between-Group SD and RSD per Resource (stratified by prep_method)
    param_summaries_by_res_tab: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for (rname, atype, param, p_method, unit), p_groups in groups_by_res_param.items():
        tab_key = (
            ANALYSIS_TYPE_TO_TAB.get(atype)
            or _SLUG_TO_TAB.get(_canonical_domain_slug(atype), "proximate")
        )
        k_groups = len(p_groups)
        total_n = sum(g["n"] for g in p_groups)
        group_means = [float(g["mean"]) for g in p_groups]
        overall_mean = sum(group_means) / k_groups if k_groups > 0 else 0.0
        between_sd: float | None = None
        between_rsd: float | None = None
        if k_groups >= 2:
            b_var = sum((gm - overall_mean) ** 2 for gm in group_means) / (k_groups - 1)
            between_sd = round(math.sqrt(b_var), 3)
            if abs(overall_mean) > 1e-9:
                between_rsd = round((math.sqrt(b_var) / abs(overall_mean)) * 100.0, 2)

        w_sds = [float(g["sd"]) for g in p_groups if g["sd"] is not None]
        w_sd_median = round(statistics.median(w_sds), 3) if w_sds else None

        within_rsds = [float(g["rsd_within_pct"]) for g in p_groups if g["rsd_within_pct"] is not None]
        w_median = _median(within_rsds)
        w_max = round(max(within_rsds), 2) if within_rsds else None
        below_cut, cut_lbl = _check_abundance_cutoff(atype, param, unit, overall_mean)

        # Annotate each group with its parameter stratum's between_sd, rsd_between_pct, and between_k_groups
        for g in p_groups:
            g["between_sd"] = between_sd
            g["rsd_between_pct"] = between_rsd
            g["between_rsd_pct"] = between_rsd
            g["between_k_groups"] = k_groups

        # Determine variance driver interpretation badge
        if below_cut:
            driver_badge = f"Trace Floor ({cut_lbl})"
            driver_tone = "muted"
        elif not within_rsds:
            driver_badge = "Singleton Groups (n=1 only)"
            driver_tone = "muted"
        elif w_median is not None and w_median > 15.0:
            driver_badge = "Elevated Assay Spread (Within-Group)"
            driver_tone = "warning"
        elif between_rsd is not None and between_rsd > 20.0 and between_rsd > 2.0 * max(w_median or 1.0, 1.0):
            driver_badge = "Sample / Method Heterogeneity (Between >> Within)"
            driver_tone = "info"
        elif between_rsd is not None and between_rsd > 12.0 and between_rsd > 1.5 * max(w_median or 1.0, 1.0):
            driver_badge = "Moderate Batch / Prep Spread"
            driver_tone = "info"
        elif (w_median or 0.0) <= 10.0 and (between_rsd is None or between_rsd <= 15.0):
            driver_badge = "High Repeatability & Consistency"
            driver_tone = "success"
        else:
            driver_badge = "Balanced Within / Between Spread"
            driver_tone = "info"

        n_flagged_active = sum(1 for g in p_groups if g["active_flagged"])
        n_flagged_raw = sum(1 for g in p_groups if g["raw_flagged"])

        param_summaries_by_res_tab[(rname, tab_key)].append({
            "analysis_type": atype,
            "parameter": param,
            "prep_method": p_method,
            "unit": unit,
            "n_groups": k_groups,
            "n_obs": total_n,
            "n_rsd_defined": len(within_rsds),
            "overall_mean": round(overall_mean, 3),
            "within_sd_median": w_sd_median,
            "within_rsd_median": w_median,
            "within_rsd_max": w_max,
            "between_sd": between_sd,
            "between_rsd_pct": between_rsd,
            "between_k_groups": k_groups,
            "pooled_sd": p_groups[0].get("pooled_sd"),
            "below_cutoff": below_cut,
            "cutoff_label": cut_lbl,
            "flagged_active": n_flagged_active,
            "flagged_active_groups": n_flagged_active,
            "flagged_replicate_groups": n_flagged_active,
            "flagged_raw": n_flagged_raw,
            "driver_badge": driver_badge,
            "driver_tone": driver_tone,
        })

    # Step 5: Assemble per-resource `outlier_screening` object
    out_by_res: dict[str, dict[str, Any]] = {}
    groups_by_res_tab: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for g in group_records:
        groups_by_res_tab[(g["resource_name"], g["tab_key"])].append(g)

    for rname in rows_by_resource.keys():
        by_tab_out: dict[str, Any] = {}
        res_all_groups: list[dict[str, Any]] = []
        res_all_params: list[dict[str, Any]] = []

        for tab_key in ("proximate", "compositional", "elemental", "pretreatment", "fermentation"):
            t_groups = groups_by_res_tab.get((rname, tab_key), [])
            t_params = param_summaries_by_res_tab.get((rname, tab_key), [])
            # Sort parameter table: non-trace first, then by flagged_active desc, then overall_mean desc
            t_params_sorted = sorted(
                t_params,
                key=lambda p: (
                    1 if p["below_cutoff"] else 0,
                    -p["flagged_active"],
                    -(p["within_rsd_max"] or 0.0),
                    p["parameter"],
                ),
            )
            # Sort replicate groups: active_flagged first, then raw_dixon, then rsd_within_pct desc
            t_groups_sorted = sorted(
                t_groups,
                key=lambda g: (
                    0 if g["active_flagged"] else (1 if g["active_rsd10"] else (2 if g["raw_flagged"] else 3)),
                    0 if g["raw_dixon"] else 1,
                    -(g["rsd_within_pct"] or -1.0),
                    g["prepared_sample"],
                    g["parameter"],
                ),
            )
            # Retain all replicate groups in sorted order so Page 2 ("All Replicate Groups")
            # and downstream statistical consumers can inspect both flagged and unflagged groups.
            kept_groups = [
                {k: v for k, v in g.items() if k not in ("resource_name", "tab_key", "group_id")}
                for g in t_groups_sorted
            ]

            w_vals = [
                p["within_rsd_median"]
                for p in t_params_sorted
                if not p["below_cutoff"] and p["within_rsd_median"] is not None
            ]
            b_vals = [
                p["between_rsd_pct"]
                for p in t_params_sorted
                if not p["below_cutoff"] and p["between_rsd_pct"] is not None
            ]
            w_sd_vals = [
                float(p["within_sd_median"])
                for p in t_params_sorted
                if not p["below_cutoff"] and p.get("within_sd_median") is not None
            ]
            b_sd_vals = [
                float(p["between_sd"])
                for p in t_params_sorted
                if not p["below_cutoff"] and p.get("between_sd") is not None
            ]

            tab_flagged_active = sum(1 for g in t_groups if g["active_flagged"])
            by_tab_out[tab_key] = {
                "total_groups": len(t_groups),
                "rsd_defined_groups": sum(1 for g in t_groups if g["n"] >= 2),
                "singleton_groups": sum(1 for g in t_groups if g["n"] == 1),
                "flagged_active": tab_flagged_active,
                "flagged_active_groups": tab_flagged_active,
                "flagged_replicate_groups": tab_flagged_active,
                "flagged_raw": sum(1 for g in t_groups if g["raw_flagged"]),
                "suppressed_trace": sum(1 for g in t_groups if g["below_cutoff"] and g["raw_flagged"]),
                "dixon_flagged": sum(1 for g in t_groups if not g["below_cutoff"] and g["raw_dixon"]),
                "rsd20_flagged": sum(1 for g in t_groups if not g["below_cutoff"] and g["raw_rsd20"]),
                "rsd10_flagged": sum(1 for g in t_groups if not g["below_cutoff"] and g["raw_rsd10"]),
                "sd3x_flagged": sum(1 for g in t_groups if not g["below_cutoff"] and g["raw_sd3x"]),
                "proximate_sum_count": sum(1 for g in t_groups if not g["below_cutoff"] and g["raw_proximate_sum"]),
                "proximate_sum_flagged": sum(1 for g in t_groups if not g["below_cutoff"] and g["raw_proximate_sum"]),
                "proximate_sum_flagged_groups": sum(1 for g in t_groups if not g["below_cutoff"] and g["raw_proximate_sum"]),
                "qc_mixed_flagged": sum(1 for g in t_groups if g["qc_mixed"]),
                "within_sd_median": round(statistics.median(w_sd_vals), 3) if w_sd_vals else None,
                "between_sd_median": round(statistics.median(b_sd_vals), 3) if b_sd_vals else None,
                "within_rsd_median": _median(w_vals),
                "between_rsd_median": _median(b_vals),
                "param_rsd_table": t_params_sorted,
                "replicate_groups": kept_groups,
            }
            res_all_groups.extend(t_groups)
            res_all_params.extend(t_params_sorted)

        all_w = [
            p["within_rsd_median"]
            for p in res_all_params
            if not p["below_cutoff"] and p["within_rsd_median"] is not None
        ]
        all_b = [
            p["between_rsd_pct"]
            for p in res_all_params
            if not p["below_cutoff"] and p["between_rsd_pct"] is not None
        ]
        all_w_sd = [
            float(p["within_sd_median"])
            for p in res_all_params
            if not p["below_cutoff"] and p.get("within_sd_median") is not None
        ]
        all_b_sd = [
            float(p["between_sd"])
            for p in res_all_params
            if not p["below_cutoff"] and p.get("between_sd") is not None
        ]
        overall_w_rsd = _median(all_w)
        overall_b_rsd = _median(all_b)
        overall_w_sd = round(statistics.median(all_w_sd), 3) if all_w_sd else None
        overall_b_sd = round(statistics.median(all_b_sd), 3) if all_b_sd else None
        total_groups_cnt = len(res_all_groups)
        rsd_defined_cnt = sum(1 for g in res_all_groups if g["n"] >= 2)
        singleton_cnt = sum(1 for g in res_all_groups if g["n"] == 1)
        flagged_active_cnt = sum(1 for g in res_all_groups if g["active_flagged"])
        flagged_raw_cnt = sum(1 for g in res_all_groups if g["raw_flagged"])
        suppressed_trace_cnt = sum(1 for g in res_all_groups if g["below_cutoff"] and g["raw_flagged"])

        out_by_res[rname] = {
            "flagged_active": flagged_active_cnt,
            "flagged_active_groups": flagged_active_cnt,
            "flagged_replicate_groups": flagged_active_cnt,
            "proximate_sum_count": sum(1 for g in res_all_groups if not g["below_cutoff"] and g["raw_proximate_sum"]),
            "proximate_sum_flagged": sum(1 for g in res_all_groups if not g["below_cutoff"] and g["raw_proximate_sum"]),
            "rsd_defined_groups": rsd_defined_cnt,
            "suppressed_low_abundance_groups": suppressed_trace_cnt,
            "overall_within_rsd_median": overall_w_rsd,
            "overall_between_rsd_median": overall_b_rsd,
            "overall_within_sd_median": overall_w_sd,
            "overall_between_sd_median": overall_b_sd,
            "summary": {
                "total_groups": total_groups_cnt,
                "rsd_defined_groups": rsd_defined_cnt,
                "singleton_groups": singleton_cnt,
                "flagged_active": flagged_active_cnt,
                "flagged_active_groups": flagged_active_cnt,
                "flagged_replicate_groups": flagged_active_cnt,
                "flagged_raw": flagged_raw_cnt,
                "suppressed_trace": suppressed_trace_cnt,
                "suppressed_low_abundance_groups": suppressed_trace_cnt,
                "dixon_flagged": sum(1 for g in res_all_groups if not g["below_cutoff"] and g["raw_dixon"]),
                "rsd20_flagged": sum(1 for g in res_all_groups if not g["below_cutoff"] and g["raw_rsd20"]),
                "rsd10_flagged": sum(1 for g in res_all_groups if not g["below_cutoff"] and g["raw_rsd10"]),
                "sd3x_flagged": sum(1 for g in res_all_groups if not g["below_cutoff"] and g["raw_sd3x"]),
                "proximate_sum_count": sum(1 for g in res_all_groups if not g["below_cutoff"] and g["raw_proximate_sum"]),
                "proximate_sum_flagged": sum(1 for g in res_all_groups if not g["below_cutoff"] and g["raw_proximate_sum"]),
                "proximate_sum_flagged_groups": sum(1 for g in res_all_groups if not g["below_cutoff"] and g["raw_proximate_sum"]),
                "qc_mixed_flagged": sum(1 for g in res_all_groups if g["qc_mixed"]),
                "overall_within_rsd_median": overall_w_rsd,
                "overall_between_rsd_median": overall_b_rsd,
                "overall_within_sd_median": overall_w_sd,
                "overall_between_sd_median": overall_b_sd,
            },
            "by_tab": by_tab_out,
        }

    return out_by_res



_NOTE_SPELLING_FIXES: tuple[tuple[str, str], ...] = (
    ("across", "across"),
    ("Across", "Across"),
    ("between", "between"),
    ("Between", "Between"),
    ("performed", "performed"),
    ("Performed", "Performed"),
    ("measurement", "measurement"),
    ("Measurement", "Measurement"),
    ("sulfur", "sulfur"),
    ("Sulfur", "Sulfur"),
    ("gelatin", "gelatin"),
    ("Gelatin", "Gelatin"),
    ("small", "small"),
    ("Small", "Small"),
    ("<DL", "<DL"),
    ("<dl", "<dl"),
)


_QC_AUDIT_TAG_RE = re.compile(r"\s*\|?\s*\[QC_AUDIT\b[^\]]*\]", re.IGNORECASE)


def strip_qc_audit_annotations(text: str | None) -> str:
    """Remove all `[QC_AUDIT ...]` audit tags and clean leading/trailing pipe separators."""
    if not text:
        return ""
    cleaned = _QC_AUDIT_TAG_RE.sub("", str(text))
    cleaned = re.sub(r"^\s*\|\s*|\s*\|\s*$", "", cleaned).strip()
    return cleaned


def _clean_note_spelling(text: str) -> str:
    """Normalize common bench-note spelling typos before emitting curated insights."""
    out = strip_qc_audit_annotations(text)
    if not out:
        return ""
    for bad, good in _NOTE_SPELLING_FIXES:
        out = out.replace(bad, good)
    return out


def classify_and_interpret_note(
    note_text: str,
    source_level: str,
    analysis_type: str = "",
    qc_statuses: list[str] | None = None,
) -> tuple[str, str, str]:
    """Classify a raw note into (category, badge_tone, ai_interpretation)."""
    note_text = _clean_note_spelling(note_text)
    low = note_text.strip().lower()
    qc_set = set(qc_statuses or [])

    # 1. URL / Google Sheet provenance links
    if low.startswith("http://") or low.startswith("https://"):
        return (
            "Protocol / Provenance Link",
            "info",
            "Direct link to raw experimental bench sheet in Google Drive for primary audit traceability.",
        )

    if re.match(r"^\d+(\s*dup)?$", low):
        return (
            "Protocol / Run & Duplicate ID",
            "info",
            f"Internal bench run / technical duplicate identifier ('{note_text.strip()}') recorded during {analysis_type or 'elemental'} combustion analysis.",
        )

    # 2. Sample loss / hardware or assay failure
    if "hydrolysate leaked" in low or "sample discarded" in low:
        return (
            "Sample Loss / Hardware Failure",
            "danger",
            "Physical vial leakage during high-temperature pretreatment/hydrolysis; record is flagged QC FAIL with no sugar yield observation.",
        )
    if "failed glucose measurement" in low or "hplc measurement error" in low or "detection error" in low:
        return (
            "Sample Loss / Hardware Failure",
            "danger",
            "Analytical HPLC/glucose assay drop-out at initial or final timepoint; artificially skews apparent sugar consumption and % yield calculations (flagged QC FAIL).",
        )
    if "blown out of crucible" in low:
        return (
            "Sample Loss / Hardware Failure",
            "danger",
            "Bomb calorimetry sample was ejected from the crucible during O₂ pressurization/ignition and did not fully combust.",
        )
    if "molded discard" in low:
        return (
            "Sample Loss / Hardware Failure",
            "danger",
            "High-moisture prepared sample developed microbial mold prior to drying and was discarded from downstream testing.",
        )
    if "loss of the strain" in low or "below detection limit" in low:
        return (
            "Sample Loss / Hardware Failure",
            "warning",
            "Biological fermentation run produced near-zero 3-HP titer due to strain instability or product concentration below HPLC detection limit.",
        )
    if "sample not obtained" in low or "unable to reach optimal conditions" in low or "optimal conditions were not sustained" in low:
        return (
            "Sample Loss / Hardware Failure",
            "danger",
            "Downdraft gasification reactor did not sustain target bed temperatures (~700°C) or experienced gas sampling failure.",
        )

    # 3. Stoichiometric / Yield & QC Warnings
    if "over 100%" in low or "above 100%" in low:
        if "fermentation" in analysis_type.lower():
            return (
                "Stoichiometric / Yield Warning",
                "warning",
                "Apparent fermentation yield >100% indicates baseline fermentable sugar underestimation at t₀ or co-utilization of non-glucose/xylose oligomers in the hydrolysate.",
            )
        return (
            "Stoichiometric / Yield Warning",
            "warning",
            "Apparent enzymatic hydrolysis yield slightly exceeds 100% of theoretical polysaccharide due to compositional variance or minor evaporation during incubation (flagged QC FAIL).",
        )
    if "sulfur is 270%" in low or "flipping this to fail" in low:
        return (
            "Stoichiometric / Yield Warning",
            "danger",
            "Manual reviewer QC override: elemental sulfur entry implied an unphysical 270% mass fraction and was quarantined as QC FAIL.",
        )
    if "too much variability" in low or "high variation across triplicates" in low:
        return (
            "Stoichiometric / Yield Warning",
            "warning",
            "Elevated biological replicate spread (CV%) across microplate wells, attributed to heterogeneous inoculum mixing, dissolved oxygen gradients, or near-DL readings.",
        )
    if "does not pass qc" in low or "greater than combustible fraction" in low or "poor quality" in low:
        return (
            "Stoichiometric / Yield Warning",
            "warning",
            "Syngas lower flammability limit (LFL) exceeded combustible fraction or bed bridging/voids degraded gas quality; flagged QC FAIL.",
        )
    if "mistakenly used hhv of capsule" in low:
        return (
            "Stoichiometric / Yield Warning",
            "warning",
            "Historical calculation artifact (~87 MJ/kg) traced to swapping gelatin capsule vs. bag calorific correction factors during bomb calorimetry.",
        )

    # 4. ETL / Pending Data Gaps
    if "only one sample run so far" in low:
        return (
            "ETL / Replicate Gap",
            "info",
            "Single bomb calorimetry determination logged to date; a duplicate/triplicate run is scheduled to complete QC validation.",
        )
    if "mock data" in low:
        return (
            "ETL / Synthetic Placeholder",
            "warning",
            "XRD crystallinity entry is marked as placeholder/mock data and should be excluded from publication-grade structural comparisons.",
        )

    # 5. Protocol / Unit / Prep Context
    if "uc combined protocol" in low:
        return (
            "Protocol / Method Context",
            "info",
            "Analyzed under the harmonized UC Combined Proximate Protocol on oven-dried/milled biomass (~2% residual moisture), yielding higher dry-basis ash and volatile solids than wet as-is runs.",
        )
    if "entered as percent (pc)" in low or "entered as ppm" in low:
        return (
            "Protocol / Unit Normalization",
            "info",
            "Audit trail confirming ICP elemental values originally recorded in weight-% were standardized to ppm (×10⁴) for schema consistency.",
        )
    if "<dl" in low:
        return (
            "Protocol / Detection Limit",
            "info",
            "One or two technical XRF replicates fell below the instrument Limit of Detection (<DL); reported statistics reflect the quantifiable replicate(s).",
        )
    if "meaningless for moisture" in low or "sample is oven dried" in low:
        return (
            "Protocol / Method Context",
            "warning",
            "Proximate analysis was performed on pre-oven-dried material; reported moisture reflects post-drying residual moisture rather-than field harvest moisture.",
        )
    if "isoperibolic" in low or "gelatin capsules" in low or "gelatin capsules" in low:
        return (
            "Protocol / Method Context",
            "info",
            "Bomb calorimetry performed isoperibolically at 25°C using powder-packed gelatin capsules with co-measured moisture correction for dry-basis HHV.",
        )
    if "comb > lfl, pass qc" in low or "sustained gasification conditions" in low or "combustible gas fraction is greater than lfl" in low:
        return (
            "Protocol / Method Context",
            "success",
            "Gasification achieved stable autothermal bed temperatures with combustible gas fraction exceeding the Lower Flammability Limit (LFL), supporting a self-sustaining flame.",
        )

    # 6. Field & Sample Preparation Provenance
    if source_level in ("Field Sample", "Prepared Sample"):
        return (
            "Field & Prep Provenance",
            "info",
            f"{source_level} provenance context explaining physical particle state, harvest handling, or cold-storage chain prior to lab characterization.",
        )

    # Default fallback
    tone = "warning" if "fail" in qc_set else "info"
    return (
        "Experimental Context",
        tone,
        f"Analyst bench note recorded during {analysis_type or source_level} execution.",
    )


def build_resource_insights(payload: dict[str, Any]) -> dict[str, Any]:
    """Compute quantitative diagnostics, mine notes, and synthesize AI insights for all resources."""
    str_cols: list[str] = payload["str_cols"]
    dicts: dict[str, list[str]] = payload["dicts"]
    excluded_res = {str(x).lower() for x in payload.get("excluded_resources", [])}
    excluded_prov = {str(x).lower() for x in payload.get("excluded_providers", [])}

    # Hydrate rows
    rows_by_resource: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for arr in payload["rows"]:
        obj: dict[str, Any] = {"record_id": str(arr[0])}
        for idx, col in enumerate(str_cols):
            obj[col] = dicts[col][arr[idx + 1]]
        obj["replicate"] = arr[len(str_cols) + 1]
        obj["value"] = arr[len(str_cols) + 2]
        obj["exp_date"] = arr[len(str_cols) + 3] if len(arr) > len(str_cols) + 3 else ""
        obj["time_h"] = arr[len(str_cols) + 4] if len(arr) > len(str_cols) + 4 else None
        # Capitalize chemical symbols for ICP & XRF
        if obj["analysis_type"] in ("ICP Elemental Analysis", "XRF Elemental Analysis"):
            p = obj.get("parameter", "")
            if p and p != "(metadata only)":
                obj["parameter"] = p[0].upper() + p[1:].lower()
        rows_by_resource[obj["resource_name"]].append(obj)

    res_meta_map = {r["name"]: r for r in payload.get("resources", [])}
    fs_by_res: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fs in payload.get("field_samples", []):
        fs_by_res[fs["resource_name"]].append(fs)

    ps_by_res: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ps in payload.get("prepared_samples", []):
        ps_by_res[ps["resource_name"]].append(ps)

    # First pass: compute key metrics per active resource so we can compute cross-resource percentiles
    per_res_metrics: dict[str, dict[str, Any]] = {}
    for rname, rrows in rows_by_resource.items():
        pass_rows = [r for r in rrows if r["qc_status"] == "pass" and r["value"] is not None]
        use_rows = pass_rows if pass_rows else [r for r in rrows if r["value"] is not None]

        def vals_for(atype: str, param: str, rows_pool: list[dict[str, Any]] = use_rows) -> list[float]:
            return [
                float(r["value"])
                for r in rows_pool
                if r["analysis_type"] == atype and r["parameter"].lower() == param.lower() and r["value"] is not None
            ]

        glucan_st = _mean_sd(vals_for("Compositional Analysis", "glucan"))
        xylan_st = _mean_sd(vals_for("Compositional Analysis", "xylan"))
        lignin_vals = vals_for("Compositional Analysis", "lignin") + vals_for("Compositional Analysis", "lignin+")
        lignin_st = _mean_sd(lignin_vals)
        ash_st = _mean_sd(vals_for("Proximate Analysis", "ash"))
        vs_st = _mean_sd(vals_for("Proximate Analysis", "volatile solids"))
        ts_st = _mean_sd(vals_for("Proximate Analysis", "total solids"))
        moist_st = _mean_sd(vals_for("Proximate Analysis", "moisture"))

        # As-is vs oven-dry moisture
        moist_as_is = _mean_sd([
            float(r["value"])
            for r in rrows
            if r["analysis_type"] == "Proximate Analysis"
            and r["parameter"] == "moisture"
            and r["value"] is not None
            and "as is" in (r.get("prep_method") or "").lower()
        ])
        moist_dried = _mean_sd([
            float(r["value"])
            for r in rrows
            if r["analysis_type"] == "Proximate Analysis"
            and r["parameter"] == "moisture"
            and r["value"] is not None
            and "as is" not in (r.get("prep_method") or "").lower()
        ])

        # Pretreatment by pt_method
        pt_rows = [r for r in rrows if r["analysis_type"] == "Pretreatment & Hydrolysis" and r["value"] is not None]
        pt_pass = [r for r in pt_rows if r["qc_status"] == "pass"]
        pt_pool = pt_pass if pt_pass else pt_rows
        glu_by_pt: dict[str, dict[str, Any]] = {}
        xyl_by_pt: dict[str, dict[str, Any]] = {}
        for ptm in sorted({r["pt_method"] for r in pt_pool if r.get("pt_method")}):
            g_v = [float(r["value"]) for r in pt_pool if r["pt_method"] == ptm and r["parameter"] == "glucose_yld"]
            x_v = [float(r["value"]) for r in pt_pool if r["pt_method"] == ptm and r["parameter"] == "xylose_yld"]
            if g_v:
                glu_by_pt[ptm] = _mean_sd(g_v)
            if x_v:
                xyl_by_pt[ptm] = _mean_sd(x_v)

        best_glu_pt = max(glu_by_pt.items(), key=lambda kv: kv[1]["mean"] or 0.0) if glu_by_pt else (None, {"mean": None, "sd": None})
        best_xyl_pt = max(xyl_by_pt.items(), key=lambda kv: kv[1]["mean"] or 0.0) if xyl_by_pt else (None, {"mean": None, "sd": None})
        ctrl_glu = glu_by_pt.get("none20c", {}).get("mean")
        pt_lift = (
            round(float(best_glu_pt[1]["mean"]) / float(ctrl_glu), 2)
            if best_glu_pt[1].get("mean") and ctrl_glu and float(ctrl_glu) > 0.5
            else None
        )

        # Fermentation metrics
        titer_3hp = _mean_sd(vals_for("Fermentation (Bioconversion)", "3hptiter"))
        yield_3hp = _mean_sd(vals_for("Fermentation (Bioconversion)", "3hpyield"))
        titer_etoh = _mean_sd(vals_for("Fermentation (Bioconversion)", "etohtiter"))
        yield_etoh = _mean_sd(vals_for("Fermentation (Bioconversion)", "etohyield"))
        sugar_cons = _mean_sd(vals_for("Fermentation (Bioconversion)", "sugar_cons"))

        # ICP & XRF top elements
        icp_elem_means: dict[str, float] = {}
        for r in use_rows:
            if r["analysis_type"] == "ICP Elemental Analysis" and r["parameter"] != "(metadata only)":
                icp_elem_means.setdefault(r["parameter"], [])  # type: ignore[arg-type]
        icp_by_el = defaultdict(list)
        xrf_by_el = defaultdict(list)
        for r in use_rows:
            if r["analysis_type"] == "ICP Elemental Analysis" and r["value"] is not None:
                icp_by_el[r["parameter"]].append(float(r["value"]))
            elif r["analysis_type"] == "XRF Elemental Analysis" and r["value"] is not None:
                xrf_by_el[r["parameter"]].append(float(r["value"]))

        icp_summary = {el: round(sum(v) / len(v), 1) for el, v in icp_by_el.items() if v}
        xrf_summary = {el: round(sum(v) / len(v), 1) for el, v in xrf_by_el.items() if v}
        total_icp_ppm = round(sum(icp_summary.values()), 1) if icp_summary else None
        total_xrf_ppm = round(sum(xrf_summary.values()), 1) if xrf_summary else None

        # Gasification summary
        gas_rows = [r for r in rrows if r["analysis_type"] == "Gasification"]
        gas_h2 = _mean_sd(vals_for("Gasification", "h2", rrows))
        gas_co = _mean_sd(vals_for("Gasification", "co", rrows))
        gas_ch4 = _mean_sd(vals_for("Gasification", "ch4", rrows))
        gas_comb = _mean_sd(vals_for("Gasification", "comb", rrows))
        gas_lfl = _mean_sd(vals_for("Gasification", "lfl", rrows))

        per_res_metrics[rname] = {
            "glucan": glucan_st,
            "xylan": xylan_st,
            "lignin": lignin_st,
            "ash": ash_st,
            "volatile_solids": vs_st,
            "total_solids": ts_st,
            "moisture": moist_st,
            "moisture_as_is": moist_as_is,
            "moisture_dried": moist_dried,
            "best_glu_pt_method": best_glu_pt[0],
            "best_glu_yld": best_glu_pt[1].get("mean"),
            "best_xyl_pt_method": best_xyl_pt[0],
            "best_xyl_yld": best_xyl_pt[1].get("mean"),
            "ctrl_glu_yld": ctrl_glu,
            "pt_lift_factor": pt_lift,
            "glu_by_pt": glu_by_pt,
            "xyl_by_pt": xyl_by_pt,
            "titer_3hp": titer_3hp,
            "yield_3hp": yield_3hp,
            "titer_etoh": titer_etoh,
            "yield_etoh": yield_etoh,
            "sugar_cons": sugar_cons,
            "icp_summary": icp_summary,
            "xrf_summary": xrf_summary,
            "total_icp_ppm": total_icp_ppm,
            "total_xrf_ppm": total_xrf_ppm,
            "gas_count": len(gas_rows),
            "gas_h2": gas_h2,
            "gas_co": gas_co,
            "gas_ch4": gas_ch4,
            "gas_comb": gas_comb,
            "gas_lfl": gas_lfl,
        }

    # Population distributions for cross-resource percentile benchmarking
    pop_glucan = [m["glucan"]["mean"] for m in per_res_metrics.values() if m["glucan"]["mean"] is not None]
    pop_xylan = [m["xylan"]["mean"] for m in per_res_metrics.values() if m["xylan"]["mean"] is not None]
    pop_lignin = [m["lignin"]["mean"] for m in per_res_metrics.values() if m["lignin"]["mean"] is not None]
    pop_ash = [m["ash"]["mean"] for m in per_res_metrics.values() if m["ash"]["mean"] is not None]
    pop_vs = [m["volatile_solids"]["mean"] for m in per_res_metrics.values() if m["volatile_solids"]["mean"] is not None]
    pop_glu_yld = [m["best_glu_yld"] for m in per_res_metrics.values() if m["best_glu_yld"] is not None]
    pop_xyl_yld = [m["best_xyl_yld"] for m in per_res_metrics.values() if m["best_xyl_yld"] is not None]
    pop_3hp = [m["titer_3hp"]["mean"] for m in per_res_metrics.values() if m["titer_3hp"]["mean"] is not None]

    catalog_medians = {
        "glucan_dw_pct": round(sorted(pop_glucan)[len(pop_glucan) // 2], 2) if pop_glucan else None,
        "xylan_dw_pct": round(sorted(pop_xylan)[len(pop_xylan) // 2], 2) if pop_xylan else None,
        "lignin_dw_pct": round(sorted(pop_lignin)[len(pop_lignin) // 2], 2) if pop_lignin else None,
        "ash_pct": round(sorted(pop_ash)[len(pop_ash) // 2], 2) if pop_ash else None,
        "volatile_solids_pct": round(sorted(pop_vs)[len(pop_vs) // 2], 2) if pop_vs else None,
        "best_glucose_yld_pct": round(sorted(pop_glu_yld)[len(pop_glu_yld) // 2], 2) if pop_glu_yld else None,
        "best_xylose_yld_pct": round(sorted(pop_xyl_yld)[len(pop_xyl_yld) // 2], 2) if pop_xyl_yld else None,
        "titer_3hp_g_l": round(sorted(pop_3hp)[len(pop_3hp) // 2], 2) if pop_3hp else None,
    }

    outlier_by_res = compute_dataset_outlier_screening(rows_by_resource)

    resources_out: dict[str, Any] = {}

    for rname in sorted(rows_by_resource.keys()):
        rrows = rows_by_resource[rname]
        rmeta = res_meta_map.get(rname, {
            "id": None,
            "name": rname,
            "code": rname[:4],
            "resource_class": "unclassified",
            "resource_subclass": "na",
            "primary_ag_product": "na",
            "description": "",
            "excluded_portal": rname.lower() in excluded_res,
        })
        f_samples = fs_by_res.get(rname, [])
        p_samples = ps_by_res.get(rname, [])
        m = per_res_metrics[rname]
        out_screen = outlier_by_res.get(rname, {"summary": {}, "by_tab": {}})
        out_sum = out_screen.get("summary", {})

        # Compute deterministic hash of this resource's slice
        hash_payload = json.dumps(
            {
                "n_rows": len(rrows),
                "ids": [r["record_id"] for r in rrows[:50]],
                "notes": sorted({r["note"] for r in rrows if r.get("note")}),
            },
            sort_keys=True,
        )
        data_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()[:16]

        # Counts & QC split
        total_obs = len(rrows)
        pass_cnt = sum(1 for r in rrows if r["qc_status"] == "pass")
        fail_cnt = sum(1 for r in rrows if r["qc_status"] == "fail")
        pass_rate = round((pass_cnt / total_obs) * 100.0, 1) if total_obs else 0.0

        by_atype_counts: dict[str, int] = defaultdict(int)
        for r in rrows:
            by_atype_counts[r["analysis_type"]] += 1

        providers = sorted({r["provider"] for r in rrows if r.get("provider") and r["provider"] != "Unassigned"})
        portal_excluded = (rname.lower() in excluded_res) or all(p.lower() in excluded_prov for p in providers if p)

        # Percentiles
        percentiles = {
            "glucan_dw_pct": _percentile_rank(m["glucan"]["mean"], pop_glucan),
            "xylan_dw_pct": _percentile_rank(m["xylan"]["mean"], pop_xylan),
            "lignin_dw_pct": _percentile_rank(m["lignin"]["mean"], pop_lignin),
            "ash_pct": _percentile_rank(m["ash"]["mean"], pop_ash),
            "volatile_solids_pct": _percentile_rank(m["volatile_solids"]["mean"], pop_vs),
            "best_glucose_yld_pct": _percentile_rank(m["best_glu_yld"], pop_glu_yld),
            "best_xylose_yld_pct": _percentile_rank(m["best_xyl_yld"], pop_xyl_yld),
            "titer_3hp_g_l": _percentile_rank(m["titer_3hp"]["mean"], pop_3hp),
        }

        # Mine & deduplicate notes across Field Samples, Prepared Samples, and Records
        curated_notes: list[dict[str, Any]] = []
        seen_notes: set[tuple[str, str]] = set()

        for fs in f_samples:
            nt = _clean_note_spelling((fs.get("note") or "").strip())
            if nt and ("Field Sample", nt) not in seen_notes:
                seen_notes.add(("Field Sample", nt))
                cat, tone, interp = classify_and_interpret_note(nt, "Field Sample")
                curated_notes.append({
                    "source_level": "Field Sample",
                    "analysis_type": "Field Collection",
                    "category": cat,
                    "tone": tone,
                    "note_text": nt,
                    "interpretation": interp,
                    "sample_names": [fs["name"]],
                    "record_ids": [],
                    "count": 1,
                })

        for ps in p_samples:
            nt = _clean_note_spelling((ps.get("note") or "").strip())
            if nt and ("Prepared Sample", nt) not in seen_notes:
                seen_notes.add(("Prepared Sample", nt))
                cat, tone, interp = classify_and_interpret_note(nt, "Prepared Sample")
                matching_ps = [p["name"] for p in p_samples if _clean_note_spelling((p.get("note") or "").strip()) == nt]
                curated_notes.append({
                    "source_level": "Prepared Sample",
                    "analysis_type": f"Prep ({ps.get('prep_method', 'N/A')})",
                    "category": cat,
                    "tone": tone,
                    "note_text": nt,
                    "interpretation": interp,
                    "sample_names": matching_ps[:4],
                    "record_ids": [],
                    "count": len(matching_ps),
                })

        # Group record notes by (analysis_type, note_text)
        rec_note_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for r in rrows:
            nt = _clean_note_spelling((r.get("note") or "").strip())
            if nt:
                rec_note_groups[(r["analysis_type"], nt)].append(r)

        for (atype, nt), grp in sorted(rec_note_groups.items(), key=lambda kv: (-len(kv[1]), kv[0][0])):
            cat, tone, interp = classify_and_interpret_note(
                nt, "Record", atype, [g["qc_status"] for g in grp]
            )
            rec_ids = list(dict.fromkeys(g["record_id"] for g in grp))
            s_names = list(dict.fromkeys(g["prepared_sample"] for g in grp if g.get("prepared_sample")))
            curated_notes.append({
                "source_level": "Analytical Record",
                "analysis_type": atype,
                "category": cat,
                "tone": tone,
                "note_text": nt,
                "interpretation": interp,
                "sample_names": s_names[:4],
                "record_ids": rec_ids[:6],
                "count": len(grp),
            })

        # Also check if Calorimetry metadata-only records exist without notes
        cal_rows = [r for r in rrows if r["analysis_type"] == "Calorimetry"]
        if cal_rows and not any(c["analysis_type"] == "Calorimetry" for c in curated_notes):
            cal_ids = [r["record_id"] for r in cal_rows]
            curated_notes.append({
                "source_level": "Analytical Record",
                "analysis_type": "Calorimetry",
                "category": "ETL / Pending Data Gap",
                "tone": "info",
                "note_text": f"{len(cal_rows)} bomb calorimetry run(s) logged in calorimetry_record ({', '.join(cal_ids[:3])}) with 0 linked observation rows.",
                "interpretation": "Bomb calorimetry was physically executed in the lab, and metadata records are present in PostgreSQL while numeric HHV/LHV observation values await ETL parameter mapping.",
                "sample_names": list(dict.fromkeys(r["prepared_sample"] for r in cal_rows)),
                "record_ids": cal_ids[:6],
                "count": len(cal_rows),
            })

        # Proximate & Compositional Mass-Balance Closure Diagnostics
        prox_closure_sum = None
        prox_rows = [
            r
            for r in rrows
            if _canonical_domain_slug(r.get("analysis_type")) == "proximate"
            and r.get("value") is not None
            and str(r.get("qc_status") or "pass").lower() != "fail"
        ]
        if prox_rows:
            stratum_closures = []
            for key in {
                f"{r.get('experiment') or 'unassigned'}|{_group_context_label(r) or 'unassigned'}"
                for r in prox_rows
            }:
                sub = [
                    r
                    for r in prox_rows
                    if f"{r.get('experiment') or 'unassigned'}|{_group_context_label(r) or 'unassigned'}"
                    == key
                ]
                mv = _mean_sd(
                    [
                        float(r["value"])
                        for r in sub
                        if _proximate_component_bucket(r["parameter"]) == "moisture"
                    ]
                )["mean"]
                av = _mean_sd(
                    [
                        float(r["value"])
                        for r in sub
                        if _proximate_component_bucket(r["parameter"]) == "ash"
                    ]
                )["mean"]
                vv = _mean_sd(
                    [
                        float(r["value"])
                        for r in sub
                        if _proximate_component_bucket(r["parameter"])
                        == "volatile_solids"
                    ]
                )["mean"]
                fcv = _mean_sd(
                    [
                        float(r["value"])
                        for r in sub
                        if _proximate_component_bucket(r["parameter"])
                        == "fixed_carbon"
                    ]
                )["mean"]
                vs_or_fc = (
                    float(vv)
                    if vv is not None
                    else ((100.0 - float(fcv)) if fcv is not None else None)
                )
                parts = [float(x) for x in (mv, av, vs_or_fc) if x is not None]
                if len(parts) >= 2:
                    stratum_closures.append(round(sum(parts), 2))
            if stratum_closures:
                prox_closure_sum = round(
                    sum(stratum_closures) / len(stratum_closures), 2
                )

        comp_polymer_sum = None
        comp_uncharacterized_dw = None
        if m["glucan"]["mean"] is not None or m["xylan"]["mean"] is not None or m["lignin"]["mean"] is not None:
            g_val = float(m["glucan"]["mean"] or 0.0)
            x_val = float(m["xylan"]["mean"] or 0.0)
            l_val = float(m["lignin"]["mean"] or 0.0)
            comp_polymer_sum = round(g_val + x_val + l_val, 2)
            ash_val = float(m["ash"]["mean"] or 0.0)
            comp_uncharacterized_dw = round(max(0.0, 100.0 - comp_polymer_sum - ash_val), 2)

        # Build synthesized AI Narratives
        rclass = rmeta.get("resource_class") or "biomass"
        desc = rmeta.get("description") or f"California {rclass} feedstock evaluated across Aim 1 characterization and Aim 2 conversion pipelines."

        # 1. Feedstock Meaning & Conversion Profile Narrative
        profile_parts = [
            f"**{rname.title()}** (`{rmeta.get('code', rname[:4])}`, *{rclass}*) comprises **{total_obs:,} database records** across **{len(f_samples)} field sample(s)** and **{len(p_samples)} prepared sample(s)** ({', '.join(providers) if providers else 'multi-team'})."
        ]
        if comp_polymer_sum is not None:
            g_v = m["glucan"]["mean"] or 0.0
            x_v = m["xylan"]["mean"] or 0.0
            l_v = m["lignin"]["mean"] or 0.0
            g_pct_rank = percentiles["glucan_dw_pct"]
            rank_str = f" ({_ordinal(g_pct_rank)} percentile statewide)" if g_pct_rank else ""
            profile_parts.append(
                f"Cell-wall characterization shows **{g_v:.1f}% glucan**{rank_str}, **{x_v:.1f}% xylan**, and **{l_v:.1f}% lignin** (structural polymer sum **{comp_polymer_sum:.1f}% dw**)."
            )
        if m["ash"]["mean"] is not None:
            ash_v = m["ash"]["mean"]
            vs_v = m["volatile_solids"]["mean"]
            ash_rank = percentiles["ash_pct"]
            ash_str = f"**{ash_v:.1f}% ash**" + (f" ({_ordinal(ash_rank)} percentile)" if ash_rank else "")
            if vs_v is not None:
                profile_parts.append(f"Proximate analysis averages {ash_str} and **{vs_v:.1f}% volatile solids**.")
            else:
                profile_parts.append(f"Proximate analysis averages {ash_str}.")
        if m["best_glu_yld"] is not None:
            lift_txt = f" (a **{m['pt_lift_factor']}× lift** over untreated `none20c` at {m['ctrl_glu_yld']:.1f}%)" if m["pt_lift_factor"] else ""
            profile_parts.append(
                f"In Aim 2 deconstruction, **`{m['best_glu_pt_method']}`** achieves the highest monomeric glucose release at **{m['best_glu_yld']:.1f}% of theoretical glucan**{lift_txt} and **{m['best_xyl_yld'] or 0.0:.1f}% xylose yield**."
            )
        if m["titer_3hp"]["mean"] is not None:
            profile_parts.append(
                f"Bioconversion with engineered *R. toruloides* yields **{m['titer_3hp']['mean']:.2f} g/L 3-HP** ({m['yield_3hp']['mean'] or 0.0:.1f}% g/g yield) with **{m['sugar_cons']['mean'] or 0.0:.1f}% sugar consumption**."
            )
        elif m["titer_etoh"]["mean"] is not None:
            profile_parts.append(
                f"Ethanol fermentation reaches **{m['titer_etoh']['mean']:.2f} g/L ethanol** ({m['yield_etoh']['mean'] or 0.0:.1f}% molar yield) with **{m['sugar_cons']['mean'] or 0.0:.1f}% sugar consumption**."
            )
        if m["gas_count"] > 0:
            profile_parts.append(
                f"Thermochemical gasification was evaluated across **{m['gas_count']} observations** (mean combustible gas fraction **{m['gas_comb']['mean'] or 0.0:.1f}%** vs. LFL **{m['gas_lfl']['mean'] or 0.0:.1f}%**)."
            )

        feedstock_profile_md = " ".join(profile_parts)

        # 2. Data Quality & Mass-Balance Audit Narrative
        audit_parts = [
            f"**QC Pass Rate:** **{pass_rate:.1f}%** (**{pass_cnt:,} Pass** · **{fail_cnt:,} Fail** across {len(by_atype_counts)} analytical domains)."
        ]
        if portal_excluded:
            reasons = []
            if rname.lower() in excluded_res:
                reasons.append(f"`\"{rname}\"` is in `EXCLUDED_RESOURCES`")
            excl_p = [p for p in providers if p.lower() in excluded_prov]
            if excl_p:
                reasons.append(f"provider `{', '.join(excl_p)}` is in `EXCLUDED_PROVIDERS`")
            audit_parts.append(
                f"**Portal View Status:** Currently filtered out of `ca_biositing.analysis_data_view` because {' and '.join(reasons)}; all underlying records are surfaced directly here."
            )
        else:
            audit_parts.append(
                "**Portal View Status:** Active in `ca_biositing.analysis_data_view` (`qc_pass = 'pass'` records propagate directly to portal materialized views)."
            )

        if prox_closure_sum is not None:
            closure_status = "excellent stoichiometric closure" if 97.0 <= prox_closure_sum <= 103.0 else "notable deviation from 100% due to oven-dried vs. as-is basis differences"
            audit_parts.append(
                f"**Proximate Wet Closure:** $\\text{{Moisture}} + \\text{{VS}} + \\text{{Ash}} = \\mathbf{{{prox_closure_sum:.2f}\\%}}$ ({closure_status})."
            )
        if m["moisture_as_is"]["mean"] is not None and m["moisture_dried"]["mean"] is not None:
            audit_parts.append(
                f"Preparation method strongly shifts moisture: `as is` samples average **{m['moisture_as_is']['mean']:.1f}% moisture** vs. **{m['moisture_dried']['mean']:.1f}%** for oven-dried/milled preparations."
            )
        if comp_polymer_sum is not None and comp_uncharacterized_dw is not None:
            audit_parts.append(
                f"**Compositional Accounting:** Structural cell-wall polymers account for **{comp_polymer_sum:.1f}% dw**, leaving **{comp_uncharacterized_dw:.1f}% dw** as non-cellulosic extractives, protein, pectin, or algal carbohydrates."
            )
        if out_sum.get("total_groups", 0) > 0:
            w_med = out_sum.get("overall_within_rsd_median")
            b_med = out_sum.get("overall_between_rsd_median")
            rsd_str = (
                f"median **Within-Group RSD {w_med:.1f}%** vs. **Between-Group RSD {b_med:.1f}%**"
                if (w_med is not None and b_med is not None)
                else (f"median **Within-Group RSD {w_med:.1f}%**" if w_med is not None else "singleton groups")
            )
            audit_parts.append(
                f"**Replicate Precision & Outlier Screen:** Across **{out_sum['rsd_defined_groups']} multi-replicate groups** ({rsd_str}), "
                f"**{out_sum['flagged_active']} group(s)** trigger candidate review flags (`Dixon Q`: {out_sum['dixon_flagged']}, `RSD > 20%`: {out_sum['rsd20_flagged']}, `3×SD`: {out_sum['sd3x_flagged']}; "
                f"{out_sum['suppressed_trace']} trace `<100 ppm` / `<0.5%` group(s) suppressed)."
            )
        if cal_rows:
            audit_parts.append(
                f"**Calorimetry ETL Note:** **{len(cal_rows)} `calorimetry_record` run(s)** are logged in PostgreSQL awaiting numeric HHV observation mapping."
            )

        quality_audit_md = " ".join(audit_parts)

        # 3. Tab-Specific Synthesized Insights
        tab_insights = {
            "overview": feedstock_profile_md,
            "proximate": (
                f"Proximate analysis for **{rname.title()}** spans **{by_atype_counts.get('Proximate Analysis', 0)} observations** "
                f"(Wet-basis closure: **{prox_closure_sum if prox_closure_sum is not None else 'N/A'}%**). "
                + (
                    f"Comparing `as is` ({m['moisture_as_is']['mean']:.1f}% moisture) against dried/milled preps ({m['moisture_dried']['mean']:.1f}% moisture) highlights the importance of normalizing volatile solids and ash to dry weight."
                    if m["moisture_as_is"]["mean"] is not None and m["moisture_dried"]["mean"] is not None
                    else f"Mean moisture is **{m['moisture']['mean'] or 0.0:.1f}%**, volatile solids **{m['volatile_solids']['mean'] or 0.0:.1f}%**, and ash **{m['ash']['mean'] or 0.0:.1f}%**."
                )
            ),
            "compositional": (
                f"Compositional & structural characterization (**{by_atype_counts.get('Compositional Analysis', 0)} Compositional**, "
                f"**{by_atype_counts.get('Ultimate Analysis', 0)} Ultimate**, **{by_atype_counts.get('XRD Crystallinity', 0)} XRD** obs) "
                + (
                    f"shows **{m['glucan']['mean'] or 0.0:.1f}% glucan**, **{m['xylan']['mean'] or 0.0:.1f}% xylan**, and **{m['lignin']['mean'] or 0.0:.1f}% lignin** (total structural polymers: **{comp_polymer_sum:.1f}% dw**)."
                    if comp_polymer_sum is not None
                    else "provides elemental and structural fiber baselines for stoichiometric conversion modeling."
                )
            ),
            "elemental": (
                f"Elemental characterization includes **{by_atype_counts.get('ICP Elemental Analysis', 0)} ICP** and **{by_atype_counts.get('XRF Elemental Analysis', 0)} XRF** observations. "
                + (
                    f"Total ICP mineral content is **{m['total_icp_ppm']:,.0f} ppm ({m['total_icp_ppm']/10000.0:.2f}% dw)**, led by "
                    + ", ".join(f"**{k}** ({v:,.0f} ppm)" for k, v in sorted(m["icp_summary"].items(), key=lambda x: -x[1])[:4])
                    + "."
                    if m["total_icp_ppm"]
                    else (
                        f"XRF elemental screening detects **{len(m['xrf_summary'])} elements**, led by "
                        + ", ".join(f"**{k}** ({v:,.0f} ppm)" for k, v in sorted(m["xrf_summary"].items(), key=lambda x: -x[1])[:4])
                        + " (note: trace elements near instrument limits carry `<DL` replicate annotations)."
                        if m["xrf_summary"]
                        else "No ICP or XRF elemental observations recorded yet for this resource."
                    )
                )
            ),
            "pretreatment": (
                f"Aim 2 Pretreatment & Enzymatic Hydrolysis (**{by_atype_counts.get('Pretreatment & Hydrolysis', 0)} observations**) "
                + (
                    f"demonstrates peak monomeric glucose yield under **`{m['best_glu_pt_method']}`** at **{m['best_glu_yld']:.1f}% of glucan** "
                    f"and peak xylose yield under **`{m['best_xyl_pt_method']}`** at **{m['best_xyl_yld'] or 0.0:.1f}% of xylan**"
                    + (f" (**{m['pt_lift_factor']}× lift** over untreated control `none20c` at {m['ctrl_glu_yld']:.1f}%)." if m["pt_lift_factor"] else ".")
                    if m["best_glu_yld"] is not None
                    else "has no enzymatic hydrolysis observations recorded for this resource."
                )
            ),
            "fermentation": (
                f"Aim 2 Bioconversion & Thermochemical Conversion (**{by_atype_counts.get('Fermentation (Bioconversion)', 0)} Fermentation**, **{by_atype_counts.get('Gasification', 0)} Gasification** obs): "
                + (
                    f"Fermentation achieves **{m['titer_3hp']['mean']:.2f} g/L 3-HP** (**{m['yield_3hp']['mean'] or 0.0:.1f}% g/g yield**) with **{m['sugar_cons']['mean'] or 0.0:.1f}% total sugar consumption**. "
                    if m["titer_3hp"]["mean"] is not None
                    else (
                        f"Fermentation achieves **{m['titer_etoh']['mean']:.2f} g/L ethanol** (**{m['yield_etoh']['mean'] or 0.0:.1f}% molar yield**) with **{m['sugar_cons']['mean'] or 0.0:.1f}% sugar consumption**. "
                        if m["titer_etoh"]["mean"] is not None
                        else ""
                    )
                )
                + (
                    f"Gasification testing ({m['gas_count']} obs) recorded mean syngas $\\text{{H}}_2 = {m['gas_h2']['mean'] or 0.0:,.0f}\\text{{ ppm}}$, $\\text{{CO}} = {m['gas_co']['mean'] or 0.0:,.0f}\\text{{ ppm}}$, and combustible fraction **{m['gas_comb']['mean'] or 0.0:.1f}%** (LFL **{m['gas_lfl']['mean'] or 0.0:.1f}%**)."
                    if m["gas_count"] > 0
                    else ""
                )
            ),
        }

        resources_out[rname] = {
            "resource_name": rname,
            "resource_id": rmeta.get("id"),
            "code": rmeta.get("code") or rname[:4],
            "resource_class": rclass,
            "primary_ag_product": rmeta.get("primary_ag_product") or "na",
            "description": desc,
            "portal_excluded": portal_excluded,
            "providers": providers,
            "data_hash": data_hash,
            "counts": {
                "total_observations": total_obs,
                "qc_pass": pass_cnt,
                "qc_fail": fail_cnt,
                "qc_pass_rate_pct": pass_rate,
                "field_samples": len(f_samples),
                "prepared_samples": len(p_samples),
                "by_analysis_type": dict(by_atype_counts),
                "mined_notes": len(curated_notes),
            },
            "diagnostics": {
                "proximate_wet_closure_pct": prox_closure_sum,
                "compositional_polymer_sum_dw_pct": comp_polymer_sum,
                "compositional_uncharacterized_dw_pct": comp_uncharacterized_dw,
                "glucan_dw_pct": m["glucan"]["mean"],
                "xylan_dw_pct": m["xylan"]["mean"],
                "lignin_dw_pct": m["lignin"]["mean"],
                "ash_pct": m["ash"]["mean"],
                "volatile_solids_pct": m["volatile_solids"]["mean"],
                "moisture_pct": m["moisture"]["mean"],
                "moisture_as_is_pct": m["moisture_as_is"]["mean"],
                "moisture_dried_pct": m["moisture_dried"]["mean"],
                "best_glu_pt_method": m["best_glu_pt_method"],
                "best_glucose_yld_pct": m["best_glu_yld"],
                "best_xyl_pt_method": m["best_xyl_pt_method"],
                "best_xylose_yld_pct": m["best_xyl_yld"],
                "untreated_glucose_yld_pct": m["ctrl_glu_yld"],
                "pretreatment_lift_factor": m["pt_lift_factor"],
                "titer_3hp_g_l": m["titer_3hp"]["mean"],
                "yield_3hp_pct": m["yield_3hp"]["mean"],
                "titer_etoh_g_l": m["titer_etoh"]["mean"],
                "yield_etoh_pct": m["yield_etoh"]["mean"],
                "sugar_consumed_pct": m["sugar_cons"]["mean"],
                "total_icp_ppm": m["total_icp_ppm"],
                "total_xrf_ppm": m["total_xrf_ppm"],
                "gasification_combustible_pct": m["gas_comb"]["mean"],
                "gasification_lfl_pct": m["gas_lfl"]["mean"],
            },
            "percentiles": percentiles,
            "ai_narratives": {
                "feedstock_profile": feedstock_profile_md,
                "quality_audit": quality_audit_md,
                "tab_insights": tab_insights,
            },
            "curated_notes": curated_notes,
            "outlier_screening": out_screen,
        }

    return {
        "schema_version": "1.1.0",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "active_resource_count": len(resources_out),
        "catalog_medians": catalog_medians,
        "resources": resources_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build resource_ai_insights.json sidecar for all active resources.")
    parser.add_argument(
        "--from-snapshot",
        type=Path,
        default=None,
        help="Path to JSON snapshot from fetch_all_resource_data.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_SIDECAR_PATH,
        help="Destination path for resource_ai_insights.json.",
    )
    args = parser.parse_args()

    if args.from_snapshot is not None:
        payload = json.loads(args.from_snapshot.read_text(encoding="utf-8"))
    else:
        from resource_explorer_dashboard import fetch_all_resource_data
        payload = fetch_all_resource_data()

    sidecar = build_resource_insights(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    print(
        f"Wrote AI insights sidecar for {sidecar['active_resource_count']} active resources to {args.output} "
        f"({args.output.stat().st_size / 1024:.1f} KB)"
    )


if __name__ == "__main__":
    main()
