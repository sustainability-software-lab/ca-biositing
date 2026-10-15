#!/usr/bin/env python3
"""Generate self-contained interactive California County Map HTML widgets.

This utility powers the `ca-county-map` skill across ALL biomass resources in
`data_portal`. It combines:
  1. Canonical California county boundaries (`data/static/ca_counties.geojson` in
     `EPSG:4326` and pre-projected `data/static/ca_counties_svg.json` in `EPSG:3310`
     California Albers).
  2. Multi-tier county-level biomass volume, primary crop, seasonal availability,
     chemical composition, and market pricing data from `data_portal`
     materialized views:
       - `data_portal.mv_biomass_volume_estimate` (Tier 1: `commodity_direct`,
         `production_based`, `census_production_based`, `acreage_based`, `prune_acres`)
       - `data_portal.mv_usda_county_production` (Tier 2: USDA Census bearing/harvested
         acreage fallback & historical census supplement)
       - `public.resource_production_record` (Tier 3: 2017-2024 historical direct
         series where available)
       - `data_portal.mv_biomass_search` (Resource metadata, primary crop, sibling
         co-products, moisture/ash/lignin composition)
       - `data_portal.mv_biomass_availability` (Seasonal harvest months & per-acre factors)
       - `data_portal.mv_biomass_pricing` (County/regional market prices when available)

It outputs a zero-external-JS-dependency interactive HTML/SVG widget styled with
Tailwind CSS (`https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js`)
and semantic CSS variables (`--card`, `--foreground`, `--muted-foreground`,
`--border`) that renders both inline via `<agent-embed>` (<500px height) and as
a standalone HTML export in `exports/plots/geospatial/`.
"""

from __future__ import annotations

import argparse
import datetime
import decimal
import json
import math
import os
import re
from pathlib import Path
from typing import Any


DEFAULT_SVG_JSON = Path("data/static/ca_counties_svg.json")

NSJV_GEOIDS = {
    "06047": "merced",
    "06077": "san joaquin",
    "06099": "stanislaus",
}

MONTH_ABBR = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

RESOURCE_META_DEFAULTS: dict[str, dict[str, Any]] = {
    "almond hulls": {
        "resource_id": 32,
        "resource_code": "almhu",
        "display_title": "Almond Hull",
        "plural_label": "Almond Hulls",
        "short_kpi_label": "NSJV Hull Total",
        "factor_description": "1.0 ton hulls / ton commodity (commodity_direct)",
        "coproduct_resource": "almond shells",
        "coproduct_short": "almond shells",
        "thresholds": [260000, 380000],
        "legend_bins": ["200k–260k", "260k–380k", "380k+ t"],
    },
    "almond shells": {
        "resource_id": 5,
        "resource_code": "almsh",
        "display_title": "Almond Shell",
        "plural_label": "Almond Shells",
        "short_kpi_label": "NSJV Shell Total",
        "factor_description": "1.0 ton shells / ton commodity (commodity_direct)",
        "coproduct_resource": "almond hulls",
        "coproduct_short": "almond hulls",
        "thresholds": [80000, 160000],
        "legend_bins": ["<80k", "80k–160k", "160k+ t"],
    },
}


def _json_default(obj: Any) -> Any:
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    return str(obj)


def _slugify_resource(resource_name: str) -> str:
    s = resource_name.strip().lower()
    # Keep singular form for common plural suffixes in filenames (`hulls` -> `hull`, `shells` -> `shell`)
    if s.endswith(" hulls"):
        s = s[:-1]
    elif s.endswith(" shells"):
        s = s[:-1]
    slug = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return slug or "biomass"


def _singularize_title(resource_name: str) -> str:
    words = resource_name.strip().split()
    if not words:
        return "Biomass"
    last = words[-1].lower()
    if last in ("hulls", "shells", "culls", "vines", "branches", "sticks", "stalks", "husks", "cobs", "stems", "peels", "seeds", "pits"):
        if last == "branches":
            words[-1] = "branch"
        else:
            words[-1] = words[-1][:-1]
    return " ".join(w.capitalize() for w in words)


def _format_season(from_month: Any, to_month: Any, year_round: Any = None) -> str:
    if year_round:
        return "Year-round"
    if from_month is None or to_month is None:
        return "Seasonal"
    fm = int(from_month)
    tm = int(to_month)
    if fm == 1 and tm == 12:
        return "Year-round"
    return f"{MONTH_ABBR.get(fm, str(fm))}–{MONTH_ABBR.get(tm, str(tm))}"


def load_svg_geometries(svg_json_path: Path = DEFAULT_SVG_JSON) -> dict[str, Any]:
    """Load pre-projected EPSG:3310 SVG paths and metadata for all 58 CA counties."""
    if not svg_json_path.exists():
        raise FileNotFoundError(
            f"Missing {svg_json_path}. Run `pixi run python scripts/build_ca_counties_geo.py` first."
        )
    return json.loads(svg_json_path.read_text(encoding="utf-8"))


def query_resource_from_db(resource_name: str = "almond hulls") -> dict[str, Any]:
    """Query `data_portal` views and `resource_production_record` from PostgreSQL for any resource."""
    os.environ.setdefault("POSTGRES_HOST", "localhost")
    from sqlalchemy import text
    from ca_biositing.datamodels.database import get_engine

    target_lower = resource_name.strip().lower()
    engine = get_engine()
    with engine.connect() as conn:
        # 1. Discover target resource and sibling co-products sharing the same primary_product
        target_search = (
            conn.execute(
                text(
                    """
                    SELECT
                        id,
                        name,
                        resource_code,
                        primary_product,
                        total_annual_volume,
                        county_count,
                        volume_unit,
                        total_annual_volume_year,
                        calculated_estimate_volume_min,
                        calculated_estimate_volume_mid,
                        calculated_estimate_volume_max,
                        volume_estimate_year,
                        moisture_percent,
                        ash_percent,
                        lignin_percent
                    FROM data_portal.mv_biomass_search
                    WHERE LOWER(name) = :target
                    """
                ),
                {"target": target_lower},
            )
            .mappings()
            .all()
        )

        primary_product = None
        if target_search:
            primary_product = target_search[0].get("primary_product")

        if primary_product:
            sibling_rows = (
                conn.execute(
                    text(
                        """
                        SELECT
                            id,
                            name,
                            resource_code,
                            primary_product,
                            total_annual_volume,
                            county_count,
                            volume_unit,
                            total_annual_volume_year,
                            calculated_estimate_volume_min,
                            calculated_estimate_volume_mid,
                            calculated_estimate_volume_max,
                            volume_estimate_year,
                            moisture_percent,
                            ash_percent,
                            lignin_percent
                        FROM data_portal.mv_biomass_search
                        WHERE LOWER(primary_product) = LOWER(:pp)
                        ORDER BY id
                        """
                    ),
                    {"pp": str(primary_product)},
                )
                .mappings()
                .all()
            )
            search_rows = sibling_rows
        else:
            search_rows = target_search

        query_names = {target_lower}
        if target_lower.startswith("almond"):
            query_names.update({"almond hulls", "almond shells"})
        for s in search_rows:
            if s.get("name"):
                query_names.add(str(s["name"]).strip().lower())

        # 2. Tier 1: mv_biomass_volume_estimate
        vol_rows = (
            conn.execute(
                text(
                    """
                    SELECT
                        id,
                        resource_id,
                        resource_name,
                        geoid,
                        county,
                        county_fips,
                        state,
                        dataset_year,
                        production_volume,
                        county_crop_acres,
                        production_unit,
                        factor_min,
                        factor_mid,
                        factor_max,
                        estimated_residue_volume_min,
                        estimated_residue_volume_mid,
                        estimated_residue_volume_max,
                        volume_source,
                        biomass_unit
                    FROM data_portal.mv_biomass_volume_estimate
                    WHERE geoid IN ('06047', '06077', '06099')
                      AND LOWER(resource_name) = ANY(:names)
                    ORDER BY dataset_year DESC, resource_name, geoid
                    """
                ),
                {"names": list(query_names)},
            )
            .mappings()
            .all()
        )

        # 3. Tier 2: mv_usda_county_production (bearing/harvested acreage fallback & census supplement)
        usda_rows = (
            conn.execute(
                text(
                    """
                    SELECT
                        id,
                        resource_id,
                        resource_name,
                        primary_ag_product,
                        geoid,
                        county,
                        state,
                        dataset_year,
                        primary_product_volume,
                        volume_unit,
                        production_acres,
                        calculated_estimate_volume,
                        biomass_unit
                    FROM data_portal.mv_usda_county_production
                    WHERE geoid IN ('06047', '06077', '06099')
                      AND LOWER(resource_name) = ANY(:names)
                    ORDER BY dataset_year DESC, resource_name, geoid
                    """
                ),
                {"names": list(query_names)},
            )
            .mappings()
            .all()
        )

        # 4. Seasonal availability: mv_biomass_availability
        avail_rows = (
            conn.execute(
                text(
                    """
                    SELECT
                        resource_id,
                        resource_name,
                        from_month,
                        to_month,
                        year_round,
                        dry_tons_per_acre,
                        wet_tons_per_acre
                    FROM data_portal.mv_biomass_availability
                    WHERE LOWER(resource_name) = ANY(:names)
                    ORDER BY resource_name
                    """
                ),
                {"names": list(query_names)},
            )
            .mappings()
            .all()
        )

        # 5. Market pricing: mv_biomass_pricing
        price_rows = (
            conn.execute(
                text(
                    """
                    SELECT
                        id,
                        resource_id,
                        resource_name,
                        geoid,
                        county,
                        county_fips,
                        state,
                        report_date::text AS report_date,
                        report_source,
                        market_type_category,
                        sale_type,
                        price_min,
                        price_max,
                        price_avg,
                        price_unit
                    FROM data_portal.mv_biomass_pricing
                    WHERE LOWER(resource_name) = ANY(:names)
                    ORDER BY report_date DESC, resource_name, geoid
                    """
                ),
                {"names": list(query_names)},
            )
            .mappings()
            .all()
        )

        # 6. Historical direct series: public.resource_production_record
        prod_rows = (
            conn.execute(
                text(
                    """
                    SELECT
                        r.id AS resource_id,
                        r.name AS resource_name,
                        r.resource_code,
                        rpr.geoid,
                        pl.county_name,
                        rpr.report_date::text AS report_date,
                        p.name AS parameter,
                        obs.value,
                        u.name AS unit
                    FROM public.resource_production_record rpr
                    JOIN public.resource r ON rpr.resource_id = r.id
                    LEFT JOIN public.place pl ON rpr.geoid = pl.geoid
                    LEFT JOIN public.observation obs
                        ON obs.record_type = 'resource_production_record'
                       AND obs.record_id = rpr.id::text
                    LEFT JOIN public.parameter p ON obs.parameter_id = p.id
                    LEFT JOIN public.unit u ON obs.unit_id = u.id
                    WHERE LOWER(r.name) = ANY(:names)
                    ORDER BY rpr.report_date DESC, r.name, rpr.geoid
                    """
                ),
                {"names": list(query_names)},
            )
            .mappings()
            .all()
        )

    return {
        "mv_biomass_volume_estimate": [dict(r) for r in vol_rows],
        "mv_usda_county_production": [dict(r) for r in usda_rows],
        "mv_biomass_availability": [dict(r) for r in avail_rows],
        "mv_biomass_pricing": [dict(r) for r in price_rows],
        "resource_production_record": [dict(r) for r in prod_rows],
        "mv_biomass_search": [dict(r) for r in search_rows],
    }


def _extract_year(val: Any) -> int | None:
    if val is None:
        return None
    s = str(val).strip()
    if len(s) >= 4 and s[:4].isdigit():
        return int(s[:4])
    return None


def _format_bin_label(val: float) -> str:
    if val >= 10000:
        if val % 1000 == 0:
            return f"{int(round(val / 1000.0))}k"
        return f"{val / 1000.0:.1f}k"
    if val >= 1000:
        if val % 1000 == 0:
            return f"{int(round(val / 1000.0))}k"
        return f"{val / 1000.0:.1f}k"
    return f"{int(round(val))}"


def _round_clean_midpoint(low: float, high: float) -> float:
    mid = (low + high) / 2.0
    span = high - low
    for step in (50000, 25000, 10000, 5000, 2500, 1000, 500, 250, 100, 50, 10, 1):
        if span >= step * 1.2:
            candidate = round(mid / step) * step
            if low < candidate <= high:
                return float(candidate)
            # Try ceil from low
            candidate2 = math.ceil((low + 1e-6) / step) * step
            if low < candidate2 <= high:
                return float(candidate2)
    return round(mid, 1)


def _compute_clean_thresholds(
    latest_vals: list[float],
    all_vals: list[float],
    unit_short: str = "t",
) -> tuple[list[float], list[str]]:
    """Compute 3-tier choropleth thresholds that cleanly separate county volumes."""
    distinct_latest = sorted({round(v, 2) for v in latest_vals if v > 0})
    if len(distinct_latest) >= 3:
        t1 = _round_clean_midpoint(distinct_latest[0], distinct_latest[1])
        t2 = _round_clean_midpoint(distinct_latest[-2], distinct_latest[-1])
    elif len(all_vals) >= 3:
        s_all = sorted({round(v, 2) for v in all_vals if v > 0})
        if len(s_all) >= 3:
            t1 = _round_clean_midpoint(s_all[0], s_all[len(s_all) // 2])
            t2 = _round_clean_midpoint(s_all[len(s_all) // 2], s_all[-1])
        else:
            t1 = round(all_vals[0] * 0.75, -2)
            t2 = round(all_vals[-1] * 0.95, -2)
    elif distinct_latest:
        base = distinct_latest[-1]
        t1 = _round_clean_midpoint(base * 0.25, base * 0.5)
        t2 = _round_clean_midpoint(base * 0.65, base * 0.9)
    else:
        t1, t2 = 10000.0, 50000.0

    if t2 <= t1:
        t2 = t1 * 1.5 if t1 > 0 else 1000.0

    bins = [
        f"<{_format_bin_label(t1)}",
        f"{_format_bin_label(t1)}–{_format_bin_label(t2)}",
        f"{_format_bin_label(t2)}+ {unit_short}",
    ]
    return [t1, t2], bins


def build_nsjv_dataset(
    raw_query_data: dict[str, Any],
    resource_name: str = "almond hulls",
) -> dict[str, Any]:
    """Structure NSJV county-level biomass production, crop, availability & pricing for any resource."""
    target_res = resource_name.strip().lower()
    singular_title = _singularize_title(resource_name)
    plural_title = resource_name.strip().title()

    meta = dict(
        RESOURCE_META_DEFAULTS.get(
            target_res,
            {
                "resource_id": None,
                "resource_code": target_res[:5],
                "display_title": singular_title,
                "plural_label": plural_title,
                "short_kpi_label": f"NSJV {singular_title} Total",
                "factor_description": None,
                "coproduct_resource": None,
                "coproduct_short": None,
                "thresholds": None,
                "legend_bins": None,
            },
        )
    )

    mv_vol_rows = (
        raw_query_data.get("mv_biomass_volume_estimate")
        or raw_query_data.get("mv_biomass_volume_estimate_almond")
        or []
    )
    usda_rows = raw_query_data.get("mv_usda_county_production") or []
    avail_rows = raw_query_data.get("mv_biomass_availability") or []
    rpr_rows = (
        raw_query_data.get("resource_production_record")
        or raw_query_data.get("resource_production_record_almond")
        or []
    )
    price_rows = (
        raw_query_data.get("mv_biomass_pricing")
        or raw_query_data.get("mv_biomass_pricing_almond")
        or raw_query_data.get("mv_biomass_pricing_almond_hulls")
        or []
    )
    search_rows = raw_query_data.get("mv_biomass_search") or []

    # 1. Enrich metadata from mv_biomass_search & discover sibling co-product
    search_summary: dict[str, Any] = {}
    sibling_candidates: list[str] = []
    for s in search_rows:
        sname = str(s.get("name", "")).strip().lower()
        if sname == target_res:
            search_summary = dict(s)
            if meta["resource_id"] is None and s.get("id") is not None:
                meta["resource_id"] = int(s["id"])
            if s.get("resource_code"):
                meta["resource_code"] = str(s["resource_code"])
        elif sname:
            sibling_candidates.append(sname)

    primary_product = str(search_summary.get("primary_product") or "").strip()

    # Availability metadata
    avail_info: dict[str, Any] = {}
    for a in avail_rows:
        if str(a.get("resource_name", "")).strip().lower() == target_res:
            avail_info = dict(a)
            break
    season_label = _format_season(
        avail_info.get("from_month"),
        avail_info.get("to_month"),
        avail_info.get("year_round"),
    )

    # Determine primary and secondary sibling co-products
    coproduct_res = meta.get("coproduct_resource")
    secondary_coprod_res = meta.get("secondary_coproduct_resource")
    sibling_vols: dict[str, float] = {}
    sibling_units: dict[str, str] = {}
    for r in mv_vol_rows:
        rn = str(r.get("resource_name", "")).strip().lower()
        est = r.get("estimated_residue_volume_mid")
        b_u = str(r.get("biomass_unit") or "tons")
        if rn:
            sibling_units[rn] = "dry t" if b_u == "dry_tons" else "t"
        if (
            rn != target_res
            and (not sibling_candidates or rn in sibling_candidates)
            and est is not None
            and float(est) > 0
        ):
            sibling_vols[rn] = sibling_vols.get(rn, 0.0) + float(est)

    ranked_siblings = [
        kv[0]
        for kv in sorted(
            sibling_vols.items(),
            key=lambda kv: (
                round(kv[1], 2),
                1 if ("shells" in kv[0] or "hulls" in kv[0]) else 0,
                -len(kv[0]),
            ),
            reverse=True,
        )
    ]
    if not coproduct_res and ranked_siblings:
        coproduct_res = ranked_siblings[0]
        meta["coproduct_resource"] = coproduct_res
        meta["coproduct_short"] = coproduct_res
    if not secondary_coprod_res:
        for cand in ranked_siblings:
            if cand != coproduct_res:
                secondary_coprod_res = cand
                break
        if secondary_coprod_res:
            meta["secondary_coproduct_resource"] = secondary_coprod_res
            meta["secondary_coproduct_short"] = secondary_coprod_res

    coproduct_unit_short = sibling_units.get(coproduct_res or "", "t")

    # 2. Tier 3 (base layer): Historical resource_production_record (2017-2024)
    primary_by_yr_geoid: dict[tuple[int, str], dict[str, Any]] = {}
    rpr_raw_by_yr_geoid: dict[tuple[int, str], float] = {}
    coprod_by_yr_geoid: dict[tuple[int, str], float] = {}
    secondary_coprod_by_yr_geoid: dict[tuple[int, str], float] = {}

    for r in rpr_rows:
        rname = str(r.get("resource_name", "")).lower().strip()
        geoid = str(r.get("geoid", "")).strip()
        yr = _extract_year(r.get("report_date"))
        val = r.get("value")
        if yr is None or val is None or geoid not in NSJV_GEOIDS:
            continue
        fval = float(val)
        if rname == target_res:
            rpr_raw_by_yr_geoid[(yr, geoid)] = fval
            primary_by_yr_geoid[(yr, geoid)] = {
                "geoid": geoid,
                "county_name": NSJV_GEOIDS[geoid],
                "estimated_volume_tons": fval,
                "volume_min": None,
                "volume_max": None,
                "primary_crop_volume": None,
                "crop_acres": None,
                "production_unit": "tons",
                "residue_factor": 1.0,
                "factor_min": None,
                "factor_max": None,
                "estimate_method": "resource_production_record",
                "biomass_unit": "tons",
            }
        elif coproduct_res and rname == coproduct_res:
            coprod_by_yr_geoid[(yr, geoid)] = fval
        elif secondary_coprod_res and rname == secondary_coprod_res:
            secondary_coprod_by_yr_geoid[(yr, geoid)] = fval

    # 3. Tier 2 (USDA Census bearing/harvested acreage supplement): mv_usda_county_production
    for r in usda_rows:
        rname = str(r.get("resource_name", "")).lower().strip()
        geoid = str(r.get("geoid", "")).strip()
        yr = _extract_year(r.get("dataset_year"))
        est = r.get("calculated_estimate_volume")
        if yr is None or est is None or geoid not in NSJV_GEOIDS:
            continue
        fest = float(est)
        if fest <= 0:
            continue
        if rname == target_res:
            if meta["resource_id"] is None and r.get("resource_id") is not None:
                meta["resource_id"] = int(r["resource_id"])
            if not primary_product and r.get("primary_ag_product"):
                primary_product = str(r["primary_ag_product"])
            acres = float(r["production_acres"]) if r.get("production_acres") is not None else None
            pvol = float(r["primary_product_volume"]) if r.get("primary_product_volume") is not None else None
            factor_ac = round(fest / acres, 3) if acres and acres > 0 else (avail_info.get("dry_tons_per_acre") or 1.0)
            primary_by_yr_geoid[(yr, geoid)] = {
                "geoid": geoid,
                "county_name": str(r.get("county") or NSJV_GEOIDS[geoid]).lower(),
                "estimated_volume_tons": fest,
                "volume_min": None,
                "volume_max": None,
                "primary_crop_volume": pvol,
                "crop_acres": acres,
                "production_unit": "acres" if acres else str(r.get("volume_unit") or "tons"),
                "residue_factor": float(factor_ac),
                "factor_min": None,
                "factor_max": None,
                "estimate_method": "usda_census_acreage",
                "biomass_unit": "dry_tons",
            }
        elif coproduct_res and rname == coproduct_res:
            coprod_by_yr_geoid[(yr, geoid)] = fest
        elif secondary_coprod_res and rname == secondary_coprod_res:
            secondary_coprod_by_yr_geoid[(yr, geoid)] = fest

    # 4. Tier 1 (Primary canonical view): mv_biomass_volume_estimate
    detected_unit = "tons"
    detected_source = "commodity_direct"
    detected_f_min: float | None = None
    detected_f_mid: float | None = None
    detected_f_max: float | None = None

    for r in mv_vol_rows:
        rname = str(r.get("resource_name", "")).lower().strip()
        geoid = str(r.get("geoid", "")).strip()
        yr = _extract_year(r.get("dataset_year"))
        est = r.get("estimated_residue_volume_mid")
        if yr is None or geoid not in NSJV_GEOIDS:
            continue
        if rname == target_res:
            if meta["resource_id"] is None and r.get("resource_id") is not None:
                meta["resource_id"] = int(r["resource_id"])
            b_unit = str(r.get("biomass_unit") or "tons")
            v_src = str(r.get("volume_source") or "production_based")
            f_mid = float(r["factor_mid"]) if r.get("factor_mid") is not None else 1.0
            f_min = float(r["factor_min"]) if r.get("factor_min") is not None else None
            f_max = float(r["factor_max"]) if r.get("factor_max") is not None else None
            detected_f_mid = f_mid
            detected_f_min = f_min
            detected_f_max = f_max

            if est is None:
                # Merge Tier 1 factor metadata into Tier 2 entry when Path D omits 'area bearing'
                existing = primary_by_yr_geoid.get((yr, geoid))
                if existing is not None:
                    existing["factor_min"] = f_min
                    existing["factor_max"] = f_max
                    if existing.get("residue_factor") is None:
                        existing["residue_factor"] = f_mid
                    if (
                        existing.get("crop_acres")
                        and f_min is not None
                        and f_max is not None
                    ):
                        existing["volume_min"] = float(existing["crop_acres"]) * f_min
                        existing["volume_max"] = float(existing["crop_acres"]) * f_max
                continue

            fest = float(est)
            detected_unit = b_unit
            detected_source = v_src

            vmin = (
                float(r["estimated_residue_volume_min"])
                if r.get("estimated_residue_volume_min") is not None
                else None
            )
            vmax = (
                float(r["estimated_residue_volume_max"])
                if r.get("estimated_residue_volume_max") is not None
                else None
            )
            pvol = (
                float(r["production_volume"])
                if r.get("production_volume") is not None
                else None
            )
            cacres = (
                float(r["county_crop_acres"])
                if r.get("county_crop_acres") is not None
                else None
            )

            primary_by_yr_geoid[(yr, geoid)] = {
                "geoid": geoid,
                "county_name": str(r.get("county") or NSJV_GEOIDS[geoid]).lower(),
                "estimated_volume_tons": fest,
                "volume_min": vmin,
                "volume_max": vmax,
                "primary_crop_volume": pvol,
                "crop_acres": cacres,
                "production_unit": str(r.get("production_unit") or "tons"),
                "residue_factor": f_mid,
                "factor_min": f_min,
                "factor_max": f_max,
                "estimate_method": v_src,
                "biomass_unit": b_unit,
            }
        elif est is not None:
            fest = float(est)
            if coproduct_res and rname == coproduct_res:
                coprod_by_yr_geoid[(yr, geoid)] = fest
            elif secondary_coprod_res and rname == secondary_coprod_res:
                secondary_coprod_by_yr_geoid[(yr, geoid)] = fest

    # Check unit from primary_by_yr_geoid if Tier 2 was used
    for item in primary_by_yr_geoid.values():
        if item.get("biomass_unit") == "dry_tons":
            detected_unit = "dry_tons"
            detected_source = item.get("estimate_method", detected_source)
            if detected_f_mid is None:
                detected_f_mid = item.get("residue_factor")

    unit_label = "dry tons" if detected_unit == "dry_tons" else "tons"
    unit_short = "dry t" if detected_unit == "dry_tons" else "t"
    wet_tons_per_acre = (
        float(avail_info["wet_tons_per_acre"])
        if avail_info.get("wet_tons_per_acre") is not None
        else None
    )

    # Build human-readable factor description if not preset
    if not meta.get("factor_description"):
        crop_lbl = primary_product if primary_product else "primary crop"
        if detected_source == "usda_census_acreage":
            wet_note = (
                f" ({wet_tons_per_acre:g} wet t/ac • {crop_lbl}, USDA Census)"
                if wet_tons_per_acre
                else f" ({crop_lbl}, USDA Census)"
            )
            meta["factor_description"] = (
                f"{detected_f_mid or 1.0:g} {unit_label} / bearing acre{wet_note}"
            )
        elif (
            detected_f_min is not None
            and detected_f_max is not None
            and detected_f_min != detected_f_max
        ):
            meta["factor_description"] = (
                f"{detected_f_mid:g} {unit_label} / ton {crop_lbl} (range {detected_f_min:g}–{detected_f_max:g}, {detected_source})"
            )
        elif detected_f_mid is not None:
            meta["factor_description"] = (
                f"{detected_f_mid:g} {unit_label} / ton {crop_lbl} ({detected_source})"
            )
        else:
            meta["factor_description"] = f"{detected_source} ({unit_label})"

    # 5. Collect pricing by year and county (or NSJV regional average) for the target resource
    price_by_yr_geoid: dict[tuple[int, str], dict[str, Any]] = {}
    regional_price_by_yr: dict[int, float] = {}
    for r in price_rows:
        rname = str(r.get("resource_name", "almond hulls")).lower().strip()
        if rname != target_res:
            continue
        yr = _extract_year(r.get("report_date"))
        pavg = r.get("price_avg")
        if yr is None or pavg is None:
            continue
        geoid = str(r.get("geoid") or "").strip()
        fp = round(float(pavg), 2)
        if geoid in NSJV_GEOIDS:
            price_by_yr_geoid[(yr, geoid)] = {
                "price_usd": fp,
                "location": str(r.get("sale_type") or "county report"),
            }
        else:
            regional_price_by_yr[yr] = fp

    has_pricing = bool(price_by_yr_geoid or regional_price_by_yr)

    years = sorted({yr for (yr, _) in primary_by_yr_geoid.keys()})
    if not years:
        raise ValueError(
            f"No NSJV rows found for resource '{resource_name}' inmv_biomass_volume_estimate or mv_usda_county_production!"
        )
    latest_year = max(years)

    # Compute dynamic thresholds if not predefined
    thresholds = meta.get("thresholds")
    legend_bins = meta.get("legend_bins")
    if not thresholds:
        latest_vals = [
            primary_by_yr_geoid[(latest_year, g)]["estimated_volume_tons"]
            for g in NSJV_GEOIDS.keys()
            if (latest_year, g) in primary_by_yr_geoid
        ]
        all_vals = [
            c["estimated_volume_tons"]
            for c in primary_by_yr_geoid.values()
            if c["estimated_volume_tons"] > 0
        ]
        thresholds, legend_bins = _compute_clean_thresholds(
            latest_vals, all_vals, unit_short=unit_short
        )

    by_year: dict[str, dict[str, Any]] = {}
    for yr in years:
        yr_str = str(yr)
        yr_counties_raw = [
            primary_by_yr_geoid[(yr, g)]
            for g in sorted(NSJV_GEOIDS.keys())
            if (yr, g) in primary_by_yr_geoid
        ]
        total_tons = sum(c["estimated_volume_tons"] for c in yr_counties_raw)
        total_min_tons = sum(
            c["volume_min"] for c in yr_counties_raw if c.get("volume_min") is not None
        )
        total_max_tons = sum(
            c["volume_max"] for c in yr_counties_raw if c.get("volume_max") is not None
        )
        has_range = any(
            c.get("volume_min") is not None
            and c.get("volume_max") is not None
            and c.get("volume_min") != c.get("volume_max")
            for c in yr_counties_raw
        )
        total_primary_crop = sum(
            c["primary_crop_volume"]
            for c in yr_counties_raw
            if c.get("primary_crop_volume") is not None
        )
        total_crop_acres = sum(
            c["crop_acres"]
            for c in yr_counties_raw
            if c.get("crop_acres") is not None
        )
        total_wet_tons = (
            round(total_crop_acres * wet_tons_per_acre, 1)
            if total_crop_acres > 0 and wet_tons_per_acre
            else None
        )
        total_rpr_tons = sum(
            rpr_raw_by_yr_geoid.get((yr, g), 0.0) for g in NSJV_GEOIDS.keys()
        )
        total_coprod = sum(
            coprod_by_yr_geoid.get((yr, g), 0.0) for g in NSJV_GEOIDS.keys()
        )
        total_sec_coprod = sum(
            secondary_coprod_by_yr_geoid.get((yr, g), 0.0) for g in NSJV_GEOIDS.keys()
        )
        total_shells = (
            total_sec_coprod
            if secondary_coprod_res and "shells" in secondary_coprod_res
            else total_coprod
        )

        yr_c_prices = [
            price_by_yr_geoid[(yr, g)]["price_usd"]
            for g in NSJV_GEOIDS.keys()
            if (yr, g) in price_by_yr_geoid
        ]
        reg_avg_price = regional_price_by_yr.get(yr)
        if reg_avg_price is None and yr_c_prices:
            reg_avg_price = round(sum(yr_c_prices) / len(yr_c_prices), 2)

        counties_dict: dict[str, Any] = {}
        for c in yr_counties_raw:
            geoid = c["geoid"]
            tons = c["estimated_volume_tons"]
            rpr_tons = rpr_raw_by_yr_geoid.get((yr, geoid))
            share_pct = round((tons / total_tons * 100.0), 2) if total_tons else 0.0
            p_info = price_by_yr_geoid.get((yr, geoid), {})
            c_price = p_info.get("price_usd", reg_avg_price)
            c_price_loc = p_info.get("location", "NSJV regional avg")
            c_coprod = round(coprod_by_yr_geoid.get((yr, geoid), 0.0), 1)
            c_sec_coprod = round(secondary_coprod_by_yr_geoid.get((yr, geoid), 0.0), 1)
            c_shells = (
                c_sec_coprod
                if secondary_coprod_res and "shells" in secondary_coprod_res
                else c_coprod
            )
            c_wet = (
                round(c["crop_acres"] * wet_tons_per_acre, 1)
                if c.get("crop_acres") is not None and wet_tons_per_acre
                else None
            )

            counties_dict[geoid] = {
                "geoid": geoid,
                "county_name": c["county_name"],
                "display_name": c["county_name"].title(),
                "estimated_volume_tons": round(tons, 1),
                "estimated_wet_tons": c_wet,
                "volume_min": round(c["volume_min"], 1) if c.get("volume_min") is not None else None,
                "volume_max": round(c["volume_max"], 1) if c.get("volume_max") is not None else None,
                "primary_crop_volume": (
                    round(c["primary_crop_volume"], 1)
                    if c.get("primary_crop_volume") is not None
                    else None
                ),
                "crop_acres": (
                    round(c["crop_acres"], 1)
                    if c.get("crop_acres") is not None
                    else None
                ),
                "rpr_reported_tons": round(rpr_tons, 1) if rpr_tons is not None else None,
                "residue_factor": c["residue_factor"],
                "factor_min": c.get("factor_min"),
                "factor_max": c.get("factor_max"),
                "share_pct": share_pct,
                "coproduct_tons": c_coprod,
                "secondary_coproduct_tons": c_sec_coprod,
                "shell_tons": c_shells,
                "price_usd": c_price,
                "price_location": c_price_loc,
                "estimate_method": c["estimate_method"],
            }

        by_year[yr_str] = {
            "year": yr,
            "total_tons": round(total_tons, 1),
            "total_wet_tons": total_wet_tons,
            "total_min_tons": round(total_min_tons, 1) if has_range else None,
            "total_max_tons": round(total_max_tons, 1) if has_range else None,
            "has_range": has_range,
            "total_primary_crop_tons": round(total_primary_crop, 1) if total_primary_crop > 0 else None,
            "total_crop_acres": round(total_crop_acres, 1) if total_crop_acres > 0 else None,
            "total_rpr_tons": round(total_rpr_tons, 1),
            "total_coproduct_tons": round(total_coprod, 1),
            "total_secondary_coproduct_tons": round(total_sec_coprod, 1),
            "total_shells_tons": round(total_shells, 1),
            "regional_avg_price_usd": reg_avg_price,
            "counties": counties_dict,
        }

    res_id_str = (
        f"id={meta['resource_id']}" if meta.get("resource_id") is not None else "data_portal"
    )
    res_code_str = str(meta.get("resource_code") or target_res)

    # Format composition summary string
    comp_parts: list[str] = []
    if search_summary.get("moisture_percent") is not None:
        comp_parts.append(f"Moisture {float(search_summary['moisture_percent']):.1f}%")
    if search_summary.get("lignin_percent") is not None:
        comp_parts.append(f"Lignin {float(search_summary['lignin_percent']):.1f}%")
    if search_summary.get("ash_percent") is not None:
        comp_parts.append(f"Ash {float(search_summary['ash_percent']):.1f}%")
    composition_str = " • ".join(comp_parts) if comp_parts else "Lab analysis pending"

    primary_title = primary_product.title() if primary_product else "Primary Crop"
    primary_short = primary_title
    if primary_product.lower() == "tomatoes for processing":
        primary_short = "Processing Tomatoes"
    elif primary_product.lower() == "olives - processing":
        primary_short = "Processing Olives"
    elif " - " in primary_title:
        primary_short = primary_title.split(" - ")[0].strip()

    source_view = (
        "data_portal.mv_usda_county_production"
        if detected_source == "usda_census_acreage"
        else "data_portal.mv_biomass_volume_estimate"
    )
    subtitle_src = (
        f"{source_view} + mv_biomass_volume_estimate"
        if detected_source == "usda_census_acreage"
        else source_view
    )

    return {
        "title": f"North San Joaquin Valley — {meta['display_title']} Production",
        "subtitle": f"Source: {subtitle_src} ({res_code_str}, {res_id_str})",
        "source_view": source_view,
        "resource_name": target_res,
        "resource_id": meta.get("resource_id"),
        "resource_code": res_code_str,
        "primary_product": primary_title,
        "primary_product_short": primary_short,
        "primary_product_lower": primary_product.lower() if primary_product else "crop",
        "display_title": meta["display_title"],
        "plural_label": meta["plural_label"],
        "short_kpi_label": meta["short_kpi_label"],
        "factor_description": meta["factor_description"],
        "residue_factor_mid": detected_f_mid,
        "residue_factor_min": detected_f_min,
        "residue_factor_max": detected_f_max,
        "wet_tons_per_acre": wet_tons_per_acre,
        "volume_source": detected_source,
        "biomass_unit": detected_unit,
        "unit_label": unit_label,
        "unit_short": unit_short,
        "has_pricing": has_pricing,
        "season_label": season_label,
        "composition_str": composition_str,
        "coproduct_short": meta.get("coproduct_short"),
        "coproduct_unit_short": coproduct_unit_short,
        "secondary_coproduct_short": meta.get("secondary_coproduct_short"),
        "thresholds": thresholds,
        "legend_bins": legend_bins,
        "search_summary": search_summary,
        "availability": avail_info,
        "region_focus": "north san joaquin valley",
        "latest_year": latest_year,
        "years": years,
        "by_year": by_year,
    }


def build_nsjv_almond_dataset(raw_query_data: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible wrapper for Almond Hull dataset builder."""
    return build_nsjv_dataset(raw_query_data, resource_name="almond hulls")


def render_widget_html(
    svg_geo: dict[str, Any],
    dataset: dict[str, Any],
    standalone: bool = False,
) -> str:
    """Render self-contained interactive HTML/SVG widget that adapts across all resources."""
    payload_json = json.dumps(
        {
            "geo": svg_geo,
            "data": dataset,
        },
        separators=(",", ":"),
        default=_json_default,
    )

    display_title = dataset.get("display_title", "Almond Hull")
    plural_label = dataset.get("plural_label", "Almond Hulls")
    short_kpi_label = dataset.get("short_kpi_label", f"NSJV {display_title} Total")
    res_code = dataset.get("resource_code", "almhu")
    res_id = dataset.get("resource_id", 32)
    source_view = dataset.get("source_view", "data_portal.mv_biomass_volume_estimate")
    factor_desc = dataset.get("factor_description", "1.0 ton / ton commodity")
    legend_bins = dataset.get("legend_bins") or ["Low", "Medium", "High"]
    latest_yr = str(dataset.get("latest_year", 2024))
    min_yr = str(min(dataset.get("years", [2017])))
    unit_label = dataset.get("unit_label", "tons")

    body_class = (
        "bg-[var(--background)] text-[var(--foreground)] antialiased p-6"
        if standalone
        else "bg-transparent text-[var(--foreground)] antialiased p-2"
    )

    standalone_style = ""
    if standalone:
        standalone_style = """
  <style>
    :root {
      --background: #f8fafc;
      --card: #ffffff;
      --foreground: #0f172a;
      --muted-foreground: #475569;
      --border: #e2e8f0;
      --primary: #00313C;
      --accent: #00B5E2;
    }
    html.dark {
      --background: #0b1319;
      --card: #111d26;
      --foreground: #f1f5f9;
      --muted-foreground: #94a3b8;
      --border: #1e293b;
      --primary: #00B5E2;
      --accent: #FDB515;
    }
  </style>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{dataset["title"]}</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>{standalone_style}
  <style>
    .county-path {{
      transition: fill 180ms ease, stroke-width 150ms ease, opacity 180ms ease;
      vector-effect: non-scaling-stroke;
    }}
    .county-path:hover {{
      filter: brightness(1.1);
    }}
    #ca-map-svg {{
      transition: all 260ms cubic-bezier(0.22, 1, 0.36, 1);
    }}
  </style>
</head>
<body class="{body_class}">
  <div class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-xl p-3.5 shadow-sm max-w-5xl mx-auto">
    <!-- Top Header & Controls -->
    <div class="flex flex-wrap items-center justify-between gap-2 pb-2.5 mb-2.5 border-b border-[var(--border)]">
      <div>
        <div class="flex items-center gap-2 flex-wrap">
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-[#00313C] text-white">
            NSJV • CA Counties
          </span>
          <h2 class="text-[var(--foreground)] font-semibold text-base tracking-tight">
            {display_title} Production by County (<span id="hdr-year">{latest_yr}</span>)
          </h2>
          <span class="text-xs px-2 py-0.5 rounded border border-[var(--border)] text-[var(--muted-foreground)] font-mono">
            EPSG:4326 / EPSG:3310
          </span>
        </div>
        <p class="text-[var(--muted-foreground)] text-xs mt-0.5">
          <code class="font-mono">{source_view}</code> (<code class="font-mono">{res_code}</code>, <code class="font-mono">id={res_id}</code>) • Factor: <span class="font-medium">{factor_desc}</span>
        </p>
      </div>

      <!-- Interactive View & Year Controls -->
      <div class="flex items-center gap-1.5 flex-wrap">
        <div class="inline-flex rounded-lg border border-[var(--border)] p-0.5 bg-[var(--background)]">
          <button id="btn-view-nsjv" type="button" class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors bg-[#00313C] text-white">
            NSJV Zoom
          </button>
          <button id="btn-view-cv" type="button" class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
            Central Valley
          </button>
          <button id="btn-view-state" type="button" class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
            All California (58)
          </button>
        </div>

        <label class="inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-lg border border-[var(--border)] bg-[var(--background)]">
          <span class="text-[var(--muted-foreground)]">Year:</span>
          <select id="select-year" class="bg-transparent text-[var(--foreground)] font-semibold focus:outline-none cursor-pointer"></select>
        </label>
      </div>
    </div>

    <!-- Main 2-Column Content (Compact height for inline <agent-embed>) -->
    <div class="grid grid-cols-12 gap-3 items-stretch">
      <!-- Left: Interactive SVG Map Canvas -->
      <div class="col-span-12 md:col-span-6 relative rounded-lg border border-[var(--border)] bg-[var(--background)] overflow-hidden flex flex-col justify-between" style="height: 365px;">
        <!-- Floating Map Status / Hover Banner -->
        <div class="z-10 flex items-center justify-between px-2.5 py-1.5 border-b border-[var(--border)] bg-[var(--card)]/90 backdrop-blur-sm">
          <div id="map-hover-Readout" class="text-xs font-medium truncate">
            Showing <span class="font-semibold text-[#0082A6]">North San Joaquin Valley</span> (3 of 58 CA counties)
          </div>
          <button id="btn-clear-selection" type="button" style="display: none;" class="text-xs px-2 py-0.5 rounded border border-[var(--border)] hover:bg-[var(--background)] text-[var(--muted-foreground)]">
            Reset Filter
          </button>
        </div>

        <!-- SVG Map Viewport -->
        <div class="relative flex-1 w-full flex items-center justify-center overflow-hidden">
          <svg id="ca-map-svg" class="w-full h-full select-none" viewBox="191.3 340.9 170.7 202.2" preserveAspectRatio="xMidYMid meet">
            <g id="map-counties-layer"></g>
            <g id="map-labels-layer" class="pointer-events-none"></g>
          </svg>
        </div>

        <!-- Map Legend Footer -->
        <div class="z-10 px-2.5 py-1.5 border-t border-[var(--border)] bg-[var(--card)]/90 flex items-center justify-between gap-2 text-xs">
          <div class="flex items-center gap-1.5 flex-wrap">
            <span class="text-[var(--muted-foreground)]">{plural_label}:</span>
            <span class="inline-block w-3 h-2.5 rounded-sm" style="background:#00B5E2"></span>
            <span class="text-[var(--muted-foreground)]">{legend_bins[0]}</span>
            <span class="inline-block w-3 h-2.5 rounded-sm" style="background:#007A99"></span>
            <span class="text-[var(--muted-foreground)]">{legend_bins[1]}</span>
            <span class="inline-block w-3 h-2.5 rounded-sm" style="background:#00313C"></span>
            <span class="text-[var(--muted-foreground)]">{legend_bins[2]}</span>
          </div>
          <span class="text-[var(--muted-foreground)]">Click county to inspect</span>
        </div>
      </div>

      <!-- Right: KPI Summary + County Breakdown + Adaptive Trend/Resource Profile -->
      <div class="col-span-12 md:col-span-6 flex flex-col justify-between gap-2.5" style="height: 365px;">
        <!-- KPI Row -->
        <div class="grid grid-cols-3 gap-2">
          <div class="rounded-lg border border-[var(--border)] bg-[var(--background)] px-2.5 py-2">
            <div class="text-xs text-[var(--muted-foreground)] truncate">{short_kpi_label}</div>
            <div id="kpi-total-tons" class="text-base font-bold tracking-tight mt-0.5">—</div>
            <div id="kpi-yoy" class="text-xs text-[var(--muted-foreground)] truncate">—</div>
          </div>
          <div class="rounded-lg border border-[var(--border)] bg-[var(--background)] px-2.5 py-2">
            <div class="text-xs text-[var(--muted-foreground)] truncate">Top NSJV County</div>
            <div id="kpi-top-county" class="text-base font-bold tracking-tight mt-0.5">—</div>
            <div id="kpi-top-share" class="text-xs text-[#0082A6] font-medium truncate">—</div>
          </div>
          <div class="rounded-lg border border-[var(--border)] bg-[var(--background)] px-2.5 py-2">
            <div id="kpi-third-label" class="text-xs text-[var(--muted-foreground)] truncate">Market Price</div>
            <div id="kpi-price" class="text-base font-bold tracking-tight mt-0.5">—</div>
            <div id="kpi-coproduct" class="text-xs text-[var(--muted-foreground)] truncate">—</div>
          </div>
        </div>

        <!-- County Ranking Cards (Clickable) -->
        <div class="rounded-lg border border-[var(--border)] bg-[var(--background)] p-2.5 flex-1 flex flex-col justify-between">
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              NSJV Counties (Click to filter)
            </span>
            <span id="selected-county-pill" class="text-xs font-medium text-[#0082A6]">
              Scope: NSJV Regional Total
            </span>
          </div>
          <div id="county-bars-container" class="space-y-1.5"></div>
        </div>

        <!-- Adaptive Bottom Panel: Multi-Year Sparkbar OR Sparse-History Comparison + Resource Profile -->
        <div class="rounded-lg border border-[var(--border)] bg-[var(--background)] px-2.5 py-2">
          <div class="flex items-center justify-between mb-1">
            <span id="trend-title" class="text-xs font-semibold text-[var(--foreground)] truncate">
              {min_yr}–{latest_yr} {plural_label} ({unit_label}) — NSJV Regional Total
            </span>
            <span id="trend-peak" class="text-xs text-[var(--muted-foreground)] shrink-0">—</span>
          </div>
          <div id="bottom-panel-body" class="pt-0.5" style="height: 58px;"></div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const PAYLOAD = {payload_json};
    const GEO = PAYLOAD.geo;
    const DATA = PAYLOAD.data;
    const UNIT_SHORT = DATA.unit_short || "t";
    const UNIT_LABEL = DATA.unit_label || "tons";

    let currentYear = String(DATA.latest_year || 2024);
    let currentView = "nsjv"; // "nsjv" | "cv" | "state"
    let selectedGeoid = null; // null = all NSJV

    const svgEl = document.getElementById("ca-map-svg");
    const countiesLayer = document.getElementById("map-counties-layer");
    const labelsLayer = document.getElementById("map-labels-layer");
    const selectYearEl = document.getElementById("select-year");
    const hoverReadoutEl = document.getElementById("map-hover-Readout");
    const clearBtn = document.getElementById("btn-clear-selection");

    // Populate year selector (descending)
    const yearsDesc = [...DATA.years].sort((a, b) => b - a);
    yearsDesc.forEach((yr) => {{
      const opt = document.createElement("option");
      opt.value = String(yr);
      opt.textContent = yr === DATA.latest_year ? `${{yr}} (Latest)` : String(yr);
      if (String(yr) === currentYear) opt.selected = true;
      selectYearEl.appendChild(opt);
    }});

    function getChoroplethColor(tons) {{
      if (!tons || tons <= 0) return "#cbd5e1";
      const [t1, t2] = DATA.thresholds || [15000, 45000];
      if (tons >= t2) return "#00313C"; // LBNL Deep Teal (High)
      if (tons >= t1) return "#007A99"; // LBNL Ocean Teal (Medium)
      return "#00B5E2";                 // LBNL Bright Cyan (Low)
    }}

    function formatTons(val) {{
      if (val === null || val === undefined) return "—";
      if (val > 0 && val < 100) return val.toFixed(1);
      return Math.round(val).toLocaleString("en-US");
    }}

    function formatShortK(val) {{
      if (!val || val <= 0) return "0";
      if (val >= 100000) return `${{Math.round(val / 1000)}}k`;
      if (val >= 1000) return `${{(val / 1000).toFixed(1)}}k`;
      return String(Math.round(val));
    }}

    function setViewMode(mode) {{
      currentView = mode;
      const views = {{
        nsjv: GEO.regions["north san joaquin valley"].viewBox,
        cv: GEO.regions["central valley"].viewBox,
        state: GEO.regions["statewide"].viewBox,
      }};
      svgEl.setAttribute("viewBox", views[mode] || views.nsjv);

      ["nsjv", "cv", "state"].forEach((m) => {{
        const btn = document.getElementById(`btn-view-${{m}}`);
        if (m === mode) {{
          btn.className = "px-2.5 py-1 rounded-md text-xs font-medium transition-colors bg-[#00313C] text-white";
        }} else {{
          btn.className = "px-2.5 py-1 rounded-md text-xs font-medium transition-colors text-[var(--muted-foreground)] hover:text-[var(--foreground)]";
        }}
      }});
      renderMap();
    }}

    function selectCounty(geoid) {{
      selectedGeoid = selectedGeoid === geoid ? null : geoid;
      clearBtn.style.display = selectedGeoid ? "inline-block" : "none";
      renderAll();
    }}

    function renderMap() {{
      const yrData = DATA.by_year[currentYear];
      const nsjvCounties = yrData ? yrData.counties : {{}};

      countiesLayer.innerHTML = "";
      labelsLayer.innerHTML = "";

      // Render non-NSJV counties first, then NSJV counties on top so active borders are never clipped
      const sortedCounties = [...GEO.counties].sort((a, b) => {{
        const aNsjv = a.region_name === "north san joaquin valley" ? 1 : 0;
        const bNsjv = b.region_name === "north san joaquin valley" ? 1 : 0;
        return aNsjv - bNsjv;
      }});

      sortedCounties.forEach((c) => {{
        const isNsjv = c.region_name === "north san joaquin valley";
        const cStats = nsjvCounties[c.geoid];
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", c.svg_path);
        path.setAttribute("class", "county-path cursor-pointer");

        const isSelected = selectedGeoid === c.geoid;
        if (isNsjv && cStats) {{
          const fillHex = getChoroplethColor(cStats.estimated_volume_tons);
          const strokeHex = isSelected ? "#FDB515" : "#ffffff";
          const strokeW = isSelected ? "2.8" : "1.5";
          const opac = selectedGeoid && !isSelected ? "0.6" : "1";
          path.setAttribute("fill", fillHex);
          path.setAttribute("stroke", strokeHex);
          path.setAttribute("stroke-width", strokeW);
          path.setAttribute("opacity", opac);
          path.style.fill = fillHex;
          path.style.stroke = strokeHex;
          path.style.strokeWidth = strokeW;
          path.style.opacity = opac;
        }} else {{
          path.setAttribute("fill", "rgba(148, 163, 184, 0.16)");
          path.setAttribute("stroke", "rgba(100, 116, 139, 0.42)");
          path.setAttribute("stroke-width", "0.9");
          path.setAttribute("opacity", "1");
          path.style.fill = "rgba(148, 163, 184, 0.16)";
          path.style.stroke = "rgba(100, 116, 139, 0.42)";
          path.style.strokeWidth = "0.9";
          path.style.opacity = "1";
        }}

        path.addEventListener("mouseenter", () => {{
          if (cStats) {{
            let extraTxt = "";
            if (cStats.price_usd) {{
              extraTxt = ` • $${{cStats.price_usd.toFixed(2)}}/t (${{cStats.price_location}})`;
            }} else if (cStats.primary_crop_volume) {{
              extraTxt = ` • ${{formatTons(cStats.primary_crop_volume)}} t ${{DATA.primary_product_lower}} × ${{cStats.residue_factor}}`;
            }} else if (cStats.crop_acres) {{
              extraTxt = ` • ${{formatTons(cStats.crop_acres)}} bearing ac × ${{cStats.residue_factor}} ${{UNIT_SHORT}}/ac`;
            }}
            hoverReadoutEl.innerHTML = `<span class="font-semibold text-[#0082A6]">${{c.full_name}} (${{c.geoid}})</span>: <strong>${{formatTons(cStats.estimated_volume_tons)}} ${{UNIT_LABEL}}</strong> (${{cStats.share_pct}}% of NSJV)${{extraTxt}}`;
          }} else {{
            hoverReadoutEl.innerHTML = `<span class="font-semibold">${{c.full_name}} (${{c.geoid}})</span> • ${{c.region_display}} (Context County)`;
          }}
        }});

        path.addEventListener("mouseleave", () => {{
          updateDefaultBanner();
        }});

        path.addEventListener("click", () => {{
          if (isNsjv && cStats) {{
            selectCounty(c.geoid);
          }}
        }});

        countiesLayer.appendChild(path);

        // Render on-map labels for NSJV counties (and neighboring context in NSJV zoom)
        if (isNsjv && cStats) {{
          const fontSize = currentView === "nsjv" ? "7.2" : currentView === "cv" ? "11.5" : "16";
          const subSize = currentView === "nsjv" ? "6.4" : currentView === "cv" ? "10" : "13";

          const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
          const nameTxt = document.createElementNS("http://www.w3.org/2000/svg", "text");
          nameTxt.setAttribute("x", c.label_x);
          nameTxt.setAttribute("y", c.label_y - (currentView === "nsjv" ? 3.2 : 5));
          nameTxt.setAttribute("text-anchor", "middle");
          nameTxt.setAttribute("fill", "#ffffff");
          nameTxt.setAttribute("font-size", fontSize);
          nameTxt.setAttribute("font-weight", "700");
          nameTxt.setAttribute("style", "paint-order: stroke; stroke: #002129; stroke-width: 2.2px; stroke-linejoin: round;");
          nameTxt.textContent = c.display_name;
          g.appendChild(nameTxt);

          if (currentView !== "state") {{
            const valTxt = document.createElementNS("http://www.w3.org/2000/svg", "text");
            valTxt.setAttribute("x", c.label_x);
            valTxt.setAttribute("y", c.label_y + (currentView === "nsjv" ? 5.2 : 8));
            valTxt.setAttribute("text-anchor", "middle");
            valTxt.setAttribute("fill", "#FDB515");
            valTxt.setAttribute("font-size", subSize);
            valTxt.setAttribute("font-weight", "700");
            valTxt.setAttribute("style", "paint-order: stroke; stroke: #002129; stroke-width: 2px; stroke-linejoin: round;");
            valTxt.textContent = `${{formatShortK(cStats.estimated_volume_tons)}} ${{UNIT_SHORT}}`;
            g.appendChild(valTxt);
          }}

          labelsLayer.appendChild(g);
        }} else if (currentView === "nsjv") {{
          // Neighbor county subtle labels in NSJV zoom
          const [bx, by, bw, bh] = c.bbox;
          if (bx + bw > 175 && bx < 370 && by + bh > 325 && by < 555) {{
            const neighborTxt = document.createElementNS("http://www.w3.org/2000/svg", "text");
            neighborTxt.setAttribute("x", c.label_x);
            neighborTxt.setAttribute("y", c.label_y);
            neighborTxt.setAttribute("text-anchor", "middle");
            neighborTxt.setAttribute("fill", "var(--muted-foreground)");
            neighborTxt.setAttribute("font-size", "5.2");
            neighborTxt.setAttribute("opacity", "0.75");
            neighborTxt.textContent = c.display_name;
            labelsLayer.appendChild(neighborTxt);
          }}
        }}
      }});
    }}

    function updateDefaultBanner() {{
      const yrData = DATA.by_year[currentYear];
      if (selectedGeoid && yrData && yrData.counties[selectedGeoid]) {{
        const c = yrData.counties[selectedGeoid];
        hoverReadoutEl.innerHTML = `Selected: <span class="font-semibold text-[#0082A6]">${{c.display_name}} County (${{c.geoid}})</span> — <strong>${{formatTons(c.estimated_volume_tons)}} ${{UNIT_LABEL}}</strong> (${{c.share_pct}}% of NSJV)`;
      }} else {{
        const activeCount = yrData ? Object.keys(yrData.counties).length : 3;
        hoverReadoutEl.innerHTML = `Showing <span class="font-semibold text-[#0082A6]">North San Joaquin Valley</span> (${{activeCount}} of 58 CA counties)`;
      }}
    }}

    function renderRightPanel() {{
      document.getElementById("hdr-year").textContent = currentYear;
      const yrData = DATA.by_year[currentYear];
      if (!yrData) return;

      // Find previous available year in DATA.years (handles both consecutive 2023->2024 and census 2017->2022)
      const sortedYrs = [...DATA.years].sort((a, b) => a - b);
      const curIdx = sortedYrs.indexOf(Number(currentYear));
      const prevYr = curIdx > 0 ? String(sortedYrs[curIdx - 1]) : null;
      const prevData = prevYr ? DATA.by_year[prevYr] : null;

      const countiesArr = Object.values(yrData.counties).sort(
        (a, b) => b.estimated_volume_tons - a.estimated_volume_tons
      );

      // Update KPI 1: Total Volume & YoY (with min-max range when present)
      document.getElementById("kpi-total-tons").textContent = `${{formatTons(yrData.total_tons)}} ${{UNIT_SHORT}}`;
      if (prevData && prevData.total_tons > 0) {{
        const pct = ((yrData.total_tons - prevData.total_tons) / prevData.total_tons) * 100;
        const sign = pct >= 0 ? "+" : "";
        const rangeSuffix = yrData.has_range
          ? ` • ${{formatShortK(yrData.total_min_tons)}}–${{formatShortK(yrData.total_max_tons)}}`
          : "";
        document.getElementById("kpi-yoy").textContent = `${{sign}}${{pct.toFixed(1)}}% vs ${{prevYr}}${{rangeSuffix}}`;
      }} else if (yrData.has_range) {{
        document.getElementById("kpi-yoy").textContent = `Range: ${{formatShortK(yrData.total_min_tons)}}–${{formatShortK(yrData.total_max_tons)}} ${{UNIT_SHORT}}`;
      }} else {{
        document.getElementById("kpi-yoy").textContent = `Baseline year (${{currentYear}})`;
      }}

      // Update KPI 2: Top County
      if (countiesArr.length > 0) {{
        document.getElementById("kpi-top-county").textContent = countiesArr[0].display_name;
        document.getElementById("kpi-top-share").textContent = `${{countiesArr[0].share_pct.toFixed(1)}}% (${{formatShortK(countiesArr[0].estimated_volume_tons)}} ${{UNIT_SHORT}})`;
      }}

      // Update KPI 3: Adaptive (Market Price when available, else Primary Crop / Bearing Acres / Harvest Window)
      const kpiThirdLabel = document.getElementById("kpi-third-label");
      const kpiPriceEl = document.getElementById("kpi-price");
      const kpiCoprodEl = document.getElementById("kpi-coproduct");
      const cropShort = DATA.primary_product_short || DATA.primary_product;
      const coprodUnit = DATA.coproduct_unit_short || "t";
      const selCountyForKpi = selectedGeoid && yrData.counties[selectedGeoid] ? yrData.counties[selectedGeoid] : null;

      if (DATA.has_pricing && yrData.regional_avg_price_usd) {{
        kpiThirdLabel.textContent = "Market Price";
        kpiPriceEl.textContent = `$${{yrData.regional_avg_price_usd.toFixed(2)}}/t`;
        const coprodShort = DATA.coproduct_short || "co-product";
        kpiCoprodEl.textContent =
          yrData.total_coproduct_tons > 0
            ? `+${{formatShortK(yrData.total_coproduct_tons)}} ${{coprodUnit}} ${{coprodShort}}`
            : `${{DATA.plural_label}} (NSJV)`;
      }} else if (yrData.total_primary_crop_tons) {{
        const dispCrop = selCountyForKpi && selCountyForKpi.primary_crop_volume ? selCountyForKpi.primary_crop_volume : yrData.total_primary_crop_tons;
        kpiThirdLabel.textContent = cropShort.length > 12 ? `${{cropShort}}` : `Primary Crop (${{cropShort}})`;
        kpiPriceEl.textContent = `${{formatTons(dispCrop)}} t`;
        kpiCoprodEl.textContent = `Harvest: ${{DATA.season_label}} • ×${{DATA.residue_factor_mid || 1}}`;
      }} else if (yrData.total_crop_acres) {{
        const dispAcres = selCountyForKpi && selCountyForKpi.crop_acres ? selCountyForKpi.crop_acres : yrData.total_crop_acres;
        const seasonPrefix = DATA.volume_source === "usda_census_acreage" ? "Pruning" : "Harvest";
        kpiThirdLabel.textContent = `${{cropShort}} Bearing Acres`;
        kpiPriceEl.textContent = `${{formatTons(dispAcres)}} ac`;
        kpiCoprodEl.textContent = `${{seasonPrefix}}: ${{DATA.season_label}} • ×${{DATA.residue_factor_mid || 1}} ${{UNIT_SHORT}}/ac`;
      }} else {{
        kpiThirdLabel.textContent = "Harvest Window";
        kpiPriceEl.textContent = DATA.season_label || "Seasonal";
        kpiCoprodEl.textContent = DATA.composition_str || `${{DATA.plural_label}}`;
      }}

      // Update County Ranking Bars
      const maxTons = Math.max(...countiesArr.map((c) => c.estimated_volume_tons), 1);
      const barsContainer = document.getElementById("county-bars-container");
      barsContainer.innerHTML = "";

      countiesArr.forEach((c) => {{
        const isSel = selectedGeoid === c.geoid;
        const widthPct = Math.max(8, Math.round((c.estimated_volume_tons / maxTons) * 100));
        const fillHex = getChoroplethColor(c.estimated_volume_tons);
        const row = document.createElement("div");
        row.className = `p-1.5 rounded-md border transition-colors cursor-pointer ${{
          isSel
            ? "border-[#FDB515] bg-[var(--card)] shadow-sm"
            : "border-transparent hover:border-[var(--border)] hover:bg-[var(--card)]/60"
        }}`;
        row.addEventListener("click", () => selectCounty(c.geoid));

        // Adaptive secondary metadata badge in county row (never shows "$—/t")
        let secondaryBadge = "";
        if (c.price_usd) {{
          secondaryBadge = `<span class="text-[var(--muted-foreground)]">$${{c.price_usd.toFixed(2)}}/t</span>`;
        }} else if (c.volume_min !== null && c.volume_max !== null && c.volume_min !== c.volume_max) {{
          secondaryBadge = `<span class="text-[var(--muted-foreground)]" title="Min–Max residue estimate range">${{formatShortK(c.volume_min)}}–${{formatShortK(c.volume_max)}} ${{UNIT_SHORT}}</span>`;
        }} else if (c.primary_crop_volume) {{
          secondaryBadge = `<span class="text-[var(--muted-foreground)]" title="Primary crop production (${{DATA.primary_product}})">${{formatTons(c.primary_crop_volume)}} t crop</span>`;
        }} else if (c.crop_acres) {{
          secondaryBadge = `<span class="text-[var(--muted-foreground)]" title="Bearing/harvested acreage">${{formatTons(c.crop_acres)}} ac</span>`;
        }}

        row.innerHTML = `
          <div class="flex items-center justify-between text-xs mb-1">
            <div class="flex items-center gap-1.5">
              <span class="inline-block w-3 h-3 rounded-sm border border-black/10" style="background:${{fillHex}}"></span>
              <span class="font-semibold">${{c.display_name}} County</span>
              <span class="text-[var(--muted-foreground)] font-mono">(${{c.geoid}})</span>
            </div>
            <div class="flex items-center gap-2">
              ${{secondaryBadge}}
              <span class="font-bold">${{formatTons(c.estimated_volume_tons)}} ${{UNIT_SHORT}}</span>
              <span class="text-[#0082A6] font-semibold w-11 text-right">${{c.share_pct.toFixed(1)}}%</span>
            </div>
          </div>
          <div class="w-full h-2 rounded-full bg-[var(--card)] overflow-hidden border border-[var(--border)]">
            <div class="h-full rounded-full transition-all duration-300" style="width:${{widthPct}}%; background:${{fillHex}}"></div>
          </div>
        `;
        barsContainer.appendChild(row);
      }});

      // Update Bottom Panel: Multi-Year Sparkbar (>=5 years) OR Comparative Strip + Resource Profile (<=4 years)
      const pillEl = document.getElementById("selected-county-pill");
      const trendTitleEl = document.getElementById("trend-title");
      const trendPeakEl = document.getElementById("trend-peak");
      const bottomBodyEl = document.getElementById("bottom-panel-body");
      bottomBodyEl.innerHTML = "";

      const series = DATA.years.map((yr) => {{
        const yObj = DATA.by_year[String(yr)];
        if (!yObj) return {{ year: yr, val: 0 }};
        if (selectedGeoid && yObj.counties[selectedGeoid]) {{
          return {{ year: yr, val: yObj.counties[selectedGeoid].estimated_volume_tons }};
        }}
        return {{ year: yr, val: yObj.total_tons }};
      }});

      const selCountyObj = selectedGeoid && yrData.counties[selectedGeoid] ? yrData.counties[selectedGeoid] : null;
      const selName = selCountyObj ? `${{selCountyObj.display_name}} County` : "NSJV Regional Total";
      pillEl.textContent = `Scope: ${{selName}}`;
      const minYr = Math.min(...DATA.years);
      const maxYr = Math.max(...DATA.years);
      trendTitleEl.textContent = `${{minYr}}–${{maxYr}} ${{DATA.plural_label}} (${{UNIT_LABEL}}) — ${{selName}}`;

      const peakObj = series.reduce((acc, cur) => (cur.val > acc.val ? cur : acc), series[0]);
      trendPeakEl.textContent = `Peak: ${{peakObj.year}} (${{formatTons(peakObj.val)}} ${{UNIT_SHORT}})`;

      const maxSeries = Math.max(...series.map((s) => s.val), 1);

      if (DATA.years.length >= 5) {{
        // Full multi-year sparkbar chart
        const gridEl = document.createElement("div");
        gridEl.className = "grid gap-1.5 items-end h-full";
        gridEl.style.gridTemplateColumns = `repeat(${{DATA.years.length}}, minmax(0, 1fr))`;

        series.forEach((pt) => {{
          const isCurYr = String(pt.year) === currentYear;
          const hPct = Math.max(15, Math.round((pt.val / maxSeries) * 100));
          const col = document.createElement("div");
          col.className = "flex flex-col items-center justify-end h-full cursor-pointer group";
          col.title = `${{pt.year}}: ${{formatTons(pt.val)}} ${{UNIT_LABEL}}`;
          col.addEventListener("click", () => {{
            currentYear = String(pt.year);
            selectYearEl.value = currentYear;
            renderAll();
          }});
          col.innerHTML = `
            <div class="text-xs leading-none mb-1 font-mono ${{isCurYr ? "font-bold text-[var(--foreground)]" : "text-[var(--muted-foreground)]"}}">
              ${{Math.round(pt.val / 1000)}}k
            </div>
            <div class="w-full rounded-t transition-all ${{isCurYr ? "bg-[#00B5E2]" : "bg-[#00313C] opacity-75 group-hover:opacity-100"}}" style="height:${{Math.round((hPct / 100) * 26)}}px"></div>
            <div class="text-xs leading-none mt-1 font-mono ${{isCurYr ? "font-bold text-[#0082A6]" : "text-[var(--muted-foreground)]"}}">
              '${{String(pt.year).slice(-2)}}
            </div>
          `;
          gridEl.appendChild(col);
        }});
        bottomBodyEl.appendChild(gridEl);
      }} else {{
        // Sparse-history layout (1-4 years): Left = Year comparison bars, Right = Resource & Co-Product Profile
        const splitEl = document.createElement("div");
        splitEl.className = "grid grid-cols-12 gap-2.5 items-center h-full";

        const barsWrap = document.createElement("div");
        barsWrap.className = "col-span-5 grid gap-2 items-end h-full pr-2 border-r border-[var(--border)]";
        barsWrap.style.gridTemplateColumns = `repeat(${{DATA.years.length}}, minmax(0, 1fr))`;

        series.forEach((pt) => {{
          const isCurYr = String(pt.year) === currentYear;
          const hPct = Math.max(18, Math.round((pt.val / maxSeries) * 100));
          const col = document.createElement("div");
          col.className = "flex flex-col items-center justify-end h-full cursor-pointer group";
          col.title = `${{pt.year}}: ${{formatTons(pt.val)}} ${{UNIT_LABEL}}`;
          col.addEventListener("click", () => {{
            currentYear = String(pt.year);
            selectYearEl.value = currentYear;
            renderAll();
          }});
          col.innerHTML = `
            <div class="text-xs leading-none mb-1 font-mono ${{isCurYr ? "font-bold text-[var(--foreground)]" : "text-[var(--muted-foreground)]"}}">
              ${{formatShortK(pt.val)}}
            </div>
            <div class="w-full max-w-[44px] rounded-t transition-all ${{isCurYr ? "bg-[#00B5E2]" : "bg-[#00313C] opacity-75 group-hover:opacity-100"}}" style="height:${{Math.round((hPct / 100) * 26)}}px"></div>
            <div class="text-xs leading-none mt-1 font-mono ${{isCurYr ? "font-bold text-[#0082A6]" : "text-[var(--muted-foreground)]"}}">
              ${{pt.year}}
            </div>
          `;
          barsWrap.appendChild(col);
        }});

        // Build 3-line Resource Profile for Right Side
        const metaWrap = document.createElement("div");
        metaWrap.className = "col-span-7 flex flex-col justify-between h-full text-xs py-0.5";

        let line1Label = "Basis";
        let line1Val = `${{DATA.volume_source}}`;
        const fRangeSuffix =
          DATA.residue_factor_min && DATA.residue_factor_max && DATA.residue_factor_min !== DATA.residue_factor_max
            ? ` (×${{DATA.residue_factor_min}}–${{DATA.residue_factor_max}})`
            : "";
        const wetSuffix = DATA.wet_tons_per_acre ? ` (${{DATA.wet_tons_per_acre}} wet t/ac)` : "";
        if (selCountyObj && selCountyObj.volume_min !== null && selCountyObj.volume_max !== null && selCountyObj.volume_min !== selCountyObj.volume_max) {{
          line1Label = "Est. Range";
          line1Val = `${{formatTons(selCountyObj.volume_min)}}–${{formatTons(selCountyObj.volume_max)}} ${{UNIT_SHORT}}${{fRangeSuffix}}`;
        }} else if (!selCountyObj && yrData.has_range) {{
          line1Label = "Est. Range";
          line1Val = `${{formatTons(yrData.total_min_tons)}}–${{formatTons(yrData.total_max_tons)}} ${{UNIT_SHORT}}${{fRangeSuffix}}`;
        }} else if (selCountyObj && selCountyObj.primary_crop_volume) {{
          line1Label = `${{cropShort}} Crop`;
          line1Val = `${{formatTons(selCountyObj.primary_crop_volume)}} t × ${{selCountyObj.residue_factor}}`;
        }} else if (yrData.total_primary_crop_tons) {{
          line1Label = `${{cropShort}} Crop`;
          line1Val = `${{formatTons(yrData.total_primary_crop_tons)}} t × ${{DATA.residue_factor_mid}}`;
        }} else if (selCountyObj && selCountyObj.crop_acres) {{
          line1Label = `${{cropShort}} Bearing Area`;
          line1Val = `${{formatTons(selCountyObj.crop_acres)}} ac × ${{selCountyObj.residue_factor}} ${{UNIT_SHORT}}/ac${{wetSuffix}}`;
        }} else if (yrData.total_crop_acres) {{
          line1Label = `${{cropShort}} Bearing Area`;
          line1Val = `${{formatTons(yrData.total_crop_acres)}} ac × ${{DATA.residue_factor_mid}} ${{UNIT_SHORT}}/ac${{wetSuffix}}`;
        }}

        let line2Label = "Co-Product";
        let line2Val = "None reported";
        const coprodTons = selCountyObj ? selCountyObj.coproduct_tons : yrData.total_coproduct_tons;
        const secCoprodTons = selCountyObj ? selCountyObj.secondary_coproduct_tons : yrData.total_secondary_coproduct_tons;
        if (DATA.coproduct_short && coprodTons > 0 && DATA.secondary_coproduct_short && secCoprodTons > 0) {{
          line2Label = "Sibling Co-Products";
          line2Val = `${{formatShortK(coprodTons)}} ${{coprodUnit}} ${{DATA.coproduct_short}} • ${{formatShortK(secCoprodTons)}} ${{coprodUnit}} ${{DATA.secondary_coproduct_short}}`;
        }} else if (DATA.coproduct_short && coprodTons > 0) {{
          line2Label = `Co-Product (${{DATA.coproduct_short}})`;
          line2Val = `${{formatTons(coprodTons)}} ${{coprodUnit}}`;
        }} else if (line1Label === "Est. Range" && selCountyObj && selCountyObj.primary_crop_volume) {{
          line2Label = `${{cropShort}}`;
          line2Val = `${{formatTons(selCountyObj.primary_crop_volume)}} t × ${{selCountyObj.residue_factor}} (${{DATA.season_label}})`;
        }} else if (line1Label === "Est. Range" && yrData.total_primary_crop_tons) {{
          line2Label = `${{cropShort}}`;
          line2Val = `${{formatTons(yrData.total_primary_crop_tons)}} t × ${{DATA.residue_factor_mid}} (${{DATA.season_label}})`;
        }} else {{
          line2Label = "Season";
          line2Val = `${{DATA.season_label}} harvest window`;
        }}

        const line3Label = "Composition";
        const line3Val = DATA.composition_str || "Lab analysis pending";

        metaWrap.innerHTML = `
          <div class="flex items-center justify-between gap-1 truncate">
            <span class="text-[var(--muted-foreground)]">${{line1Label}}:</span>
            <span class="font-semibold font-mono text-[var(--foreground)] truncate">${{line1Val}}</span>
          </div>
          <div class="flex items-center justify-between gap-1 truncate">
            <span class="text-[var(--muted-foreground)] truncate">${{line2Label}}:</span>
            <span class="font-semibold text-[#0082A6] truncate">${{line2Val}}</span>
          </div>
          <div class="flex items-center justify-between gap-1 truncate">
            <span class="text-[var(--muted-foreground)]">${{line3Label}}:</span>
            <span class="font-medium text-[var(--foreground)] truncate">${{line3Val}}</span>
          </div>
        `;

        splitEl.appendChild(barsWrap);
        splitEl.appendChild(metaWrap);
        bottomBodyEl.appendChild(splitEl);
      }}
    }}

    function renderAll() {{
      updateDefaultBanner();
      renderMap();
      renderRightPanel();
    }}

    // Wire events
    document.getElementById("btn-view-nsjv").addEventListener("click", () => setViewMode("nsjv"));
    document.getElementById("btn-view-cv").addEventListener("click", () => setViewMode("cv"));
    document.getElementById("btn-view-state").addEventListener("click", () => setViewMode("state"));
    clearBtn.addEventListener("click", () => selectCounty(null));
    selectYearEl.addEventListener("change", (e) => {{
      currentYear = e.target.value;
      renderAll();
    }});

    renderAll();
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--resource",
        type=str,
        default="almond hulls",
        help="Target biomass resource name (e.g., 'walnut hulls', 'almond shells', 'tomato pomace')",
    )
    parser.add_argument(
        "--svg-json",
        type=Path,
        default=DEFAULT_SVG_JSON,
        help="Path to data/static/ca_counties_svg.json",
    )
    parser.add_argument(
        "--data-json",
        type=Path,
        default=None,
        help="Optional pre-queried JSON file (if omitted, queries PostgreSQL directly)",
    )
    parser.add_argument(
        "--save-data-json",
        type=Path,
        default=None,
        help="Optional output path to save the queried raw + structured JSON payload",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for standalone HTML widget (defaults to exports/plots/geospatial/nsjv_<resource_slug>_map.html)",
    )
    parser.add_argument(
        "--inline-output",
        type=Path,
        default=None,
        help="Optional output path for inline <agent-embed> HTML artifact",
    )
    args = parser.parse_args()

    svg_geo = load_svg_geometries(args.svg_json)

    if args.data_json and args.data_json.exists():
        raw_data = json.loads(args.data_json.read_text(encoding="utf-8"))
    else:
        raw_data = query_resource_from_db(resource_name=args.resource)

    dataset = build_nsjv_dataset(raw_data, resource_name=args.resource)

    latest_yr = str(dataset.get("latest_year", ""))
    latest_summary = dataset.get("by_year", {}).get(latest_yr, {})
    print(
        f"Resource: {dataset['resource_name']} (id={dataset['resource_id']}, code={dataset['resource_code']}) | "
        f"Latest year: {latest_yr} | Total volume: {latest_summary.get('total_tons', 0):,.1f} {dataset['unit_label']} | "
        f"Source: {dataset['volume_source']} ({dataset['factor_description']})"
    )

    if args.save_data_json:
        args.save_data_json.parent.mkdir(parents=True, exist_ok=True)
        out_payload = {"dataset": dataset, **{k: v for k, v in raw_data.items() if k != "dataset"}}
        args.save_data_json.write_text(
            json.dumps(out_payload, indent=2, default=_json_default),
            encoding="utf-8",
        )
        print(f"Wrote data JSON payload: {args.save_data_json} ({args.save_data_json.stat().st_size:,} bytes)")

    output_path = args.output
    if output_path is None:
        slug = _slugify_resource(args.resource)
        output_path = Path(f"exports/plots/geospatial/nsjv_{slug}_map.html")

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        standalone_html = render_widget_html(svg_geo, dataset, standalone=True)
        output_path.write_text(standalone_html, encoding="utf-8")
        print(f"Wrote standalone widget: {output_path} ({output_path.stat().st_size:,} bytes)")

    if args.inline_output:
        args.inline_output.parent.mkdir(parents=True, exist_ok=True)
        inline_html = render_widget_html(svg_geo, dataset, standalone=False)
        args.inline_output.write_text(inline_html, encoding="utf-8")
        print(f"Wrote inline artifact widget: {args.inline_output} ({args.inline_output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
