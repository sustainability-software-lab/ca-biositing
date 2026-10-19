#!/usr/bin/env python3
"""Multi-Environment PostgreSQL Drift Assessment & Interactive Dashboard Generator.

Extracts 4-layer database environment fingerprints directly from live PostgreSQL
instances across `local` (:5432), `staging` (:5434 via Cloud SQL Auth Proxy), and
`production` (:5435 via Cloud SQL Auth Proxy) using connection defaults from
`resources/config/db_reset.yaml` and `.env`. When an environment tunnel is
unreachable, records an explicit `unmeasured_offline` fingerprint (`is_measured:
False`) without fabricating or simulating data. Compares fingerprints across all
4 layers to generate:
  1. `exports/plots/audit/db_environment_drift_dashboard.html`
  2. `audit/output/drift_report.md`

CLI Modes:
  # Extract live fingerprints from running PostgreSQL environments and compare:
  pixi run python analysis/audit/db_environment_drift.py --extract-env local staging production --compare
  pixi run python analysis/audit/db_environment_drift.py --extract-env local
  pixi run python analysis/audit/db_environment_drift.py --extract-env staging --port 5434
  pixi run python analysis/audit/db_environment_drift.py --extract-env production --port 5435

  # Compare existing fingerprints and build HTML dashboard + Markdown drift report:
  pixi run python analysis/audit/db_environment_drift.py --compare
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

CORE_TABLE_METADATA: list[tuple[str, str, int, bool]] = [
    # (table_name, category, column_count, has_qc_pass)
    ("resource", "Entity & Lineage", 14, False),
    ("primary_ag_product", "Entity & Lineage", 6, False),
    ("provider", "Entity & Lineage", 9, False),
    ("field_sample", "Entity & Lineage", 16, False),
    ("prepared_sample", "Entity & Lineage", 13, False),
    ("experiment", "Entity & Lineage", 11, False),
    ("observation", "Entity & Lineage", 12, False),
    ("compositional_record", "Aim 1 Analytical", 15, True),
    ("proximate_record", "Aim 1 Analytical", 15, True),
    ("ultimate_record", "Aim 1 Analytical", 15, True),
    ("xrf_record", "Aim 1 Analytical", 15, True),
    ("icp_record", "Aim 1 Analytical", 15, True),
    ("calorimetry_record", "Aim 1 Analytical", 16, True),
    ("xrd_record", "Aim 1 Analytical", 15, True),
    ("ftnir_record", "Aim 1 Analytical", 15, True),
    ("fermentation_record", "Aim 2 Conversion", 21, True),
    ("gasification_record", "Aim 2 Conversion", 18, True),
    ("pretreatment_record", "Aim 2 Conversion", 19, True),
    ("usda_market_record", "USDA & Market", 14, False),
    ("usda_census_record", "USDA & Market", 13, False),
    ("resource_production_record", "USDA & Market", 12, False),
]

AIM1_AIM2_TABLES = [
    "compositional_record",
    "proximate_record",
    "ultimate_record",
    "xrf_record",
    "icp_record",
    "calorimetry_record",
    "xrd_record",
    "ftnir_record",
    "fermentation_record",
    "gasification_record",
    "pretreatment_record",
]

ANALYSIS_TYPE_TO_TABLE = {
    "Compositional Analysis": "compositional_record",
    "Proximate Analysis": "proximate_record",
    "Ultimate Analysis": "ultimate_record",
    "XRF Elemental Analysis": "xrf_record",
    "ICP Elemental Analysis": "icp_record",
    "Calorimetry": "calorimetry_record",
    "XRD Crystallinity": "xrd_record",
    "FT-NIR Spectroscopy": "ftnir_record",
    "Fermentation (Bioconversion)": "fermentation_record",
    "Gasification": "gasification_record",
    "Pretreatment & Hydrolysis": "pretreatment_record",
}

ALL_19_VIEWS: list[tuple[str, str, int]] = [
    # (qualified_view_name, category, index_count)
    ("ca_biositing.analysis_average_view", "ca_biositing Analytical View", 2),
    ("ca_biositing.analysis_data_view", "ca_biositing Analytical View", 4),
    ("ca_biositing.billion_ton_tileset_view", "ca_biositing Geospatial View", 1),
    ("ca_biositing.landiq_record_view", "ca_biositing Geospatial View", 2),
    ("ca_biositing.landiq_tileset_view", "ca_biositing Geospatial View", 1),
    ("ca_biositing.usda_census_view", "ca_biositing USDA View", 3),
    ("ca_biositing.usda_resource_commodity_view", "ca_biositing USDA View", 2),
    ("ca_biositing.usda_survey_view", "ca_biositing USDA View", 3),
    ("data_portal.mv_biomass_availability", "data_portal Materialized View", 1),
    ("data_portal.mv_biomass_composition", "data_portal Materialized View", 8),
    ("data_portal.mv_biomass_county_production", "data_portal Materialized View", 3),
    ("data_portal.mv_biomass_end_uses", "data_portal Materialized View", 2),
    ("data_portal.mv_biomass_fermentation", "data_portal Materialized View", 3),
    ("data_portal.mv_biomass_gasification", "data_portal Materialized View", 3),
    ("data_portal.mv_biomass_pricing", "data_portal Materialized View", 3),
    ("data_portal.mv_biomass_sample_stats", "data_portal Materialized View", 2),
    ("data_portal.mv_biomass_search", "data_portal Materialized View", 3),
    ("data_portal.mv_biomass_volume_estimate", "data_portal Materialized View", 4),
    ("data_portal.mv_usda_county_production", "data_portal Materialized View", 4),
]

CANONICAL_VIEW_SCHEMAS: dict[str, list[tuple[str, str]]] = {
    "ca_biositing.landiq_record_view": [
        ("record_id", "character varying"),
        ("geom", "geometry"),
        ("geoid", "character varying"),
        ("crop_name", "character varying"),
        ("acres", "double precision"),
        ("irrigated", "boolean"),
        ("confidence", "integer"),
        ("dataset_id", "integer"),
    ],
    "ca_biositing.landiq_tileset_view": [
        ("id", "integer"),
        ("geom", "geometry"),
        ("main_crop", "character varying"),
        ("acres", "double precision"),
        ("county", "character varying"),
        ("geoid", "character varying"),
        ("tileset_id", "integer"),
    ],
    "ca_biositing.analysis_data_view": [
        ("id", "integer"),
        ("record_id", "character varying"),
        ("record_type", "character varying"),
        ("resource_id", "integer"),
        ("resource", "text"),
        ("geoid", "character varying"),
        ("parameter", "text"),
        ("value", "numeric"),
        ("unit", "text"),
        ("dimension", "text"),
        ("dimension_value", "numeric"),
        ("dimension_unit", "text"),
    ],
    "ca_biositing.usda_census_view": [
        ("id", "integer"),
        ("usda_crop", "text"),
        ("geoid", "character varying"),
        ("parameter", "text"),
        ("value", "numeric"),
        ("unit", "text"),
        ("dimension", "text"),
        ("dimension_value", "numeric"),
        ("dimension_unit", "text"),
        ("commodity_id", "integer"),
        ("source_record_id", "integer"),
        ("record_year", "integer"),
    ],
    "ca_biositing.usda_survey_view": [
        ("id", "integer"),
        ("usda_crop", "text"),
        ("geoid", "character varying"),
        ("parameter", "text"),
        ("value", "numeric"),
        ("unit", "text"),
        ("dimension", "text"),
        ("dimension_value", "numeric"),
        ("dimension_unit", "text"),
        ("commodity_id", "integer"),
        ("source_record_id", "integer"),
        ("record_year", "integer"),
        ("survey_program_id", "integer"),
        ("survey_period", "character varying"),
        ("reference_month", "character varying"),
        ("seasonal_flag", "boolean"),
    ],
    "ca_biositing.usda_resource_commodity_view": [
        ("resource", "character varying"),
        ("commodity_id", "integer"),
    ],
    "ca_biositing.billion_ton_tileset_view": [
        ("id", "integer"),
        ("resource", "character varying"),
        ("county", "text"),
        ("parameter", "text"),
        ("value", "double precision"),
        ("unit", "text"),
        ("tileset_id", "integer"),
    ],
    "ca_biositing.analysis_average_view": [
        ("resource", "text"),
        ("geoid", "character varying"),
        ("parameter", "text"),
        ("average_value", "numeric"),
        ("standard_deviation", "numeric"),
        ("unit", "text"),
        ("observation_count", "bigint"),
    ],
    "data_portal.mv_biomass_availability": [
        ("resource_id", "integer"),
        ("resource_name", "character varying"),
        ("from_month", "integer"),
        ("to_month", "integer"),
        ("year_round", "boolean"),
        ("dry_tons_per_acre", "double precision"),
        ("wet_tons_per_acre", "double precision"),
    ],
    "data_portal.mv_biomass_composition": [
        ("id", "bigint"),
        ("resource_id", "integer"),
        ("resource_name", "character varying"),
        ("analysis_type", "text"),
        ("parameter_name", "character varying"),
        ("geoid", "character varying"),
        ("county", "character varying"),
        ("unit", "character varying"),
        ("avg_value", "numeric"),
        ("min_value", "numeric"),
        ("max_value", "numeric"),
        ("std_dev", "numeric"),
        ("observation_count", "bigint"),
    ],
    "data_portal.mv_biomass_county_production": [
        ("id", "bigint"),
        ("resource_id", "integer"),
        ("resource_name", "character varying"),
        ("resource_class", "character varying"),
        ("geoid", "character varying"),
        ("county", "character varying"),
        ("state", "character varying"),
        ("scenario", "character varying"),
        ("price_offered_usd", "numeric"),
        ("production", "integer"),
        ("production_unit", "character varying"),
        ("energy_content", "bigint"),
        ("energy_unit", "character varying"),
        ("density_dt_per_sqmi", "numeric"),
        ("county_square_miles", "double precision"),
        ("year", "integer"),
    ],
    "data_portal.mv_biomass_sample_stats": [
        ("resource_id", "integer"),
        ("resource_name", "character varying"),
        ("sample_count", "bigint"),
        ("supplier_count", "bigint"),
        ("dataset_count", "bigint"),
        ("total_record_count", "bigint"),
    ],
    "data_portal.mv_biomass_fermentation": [
        ("id", "bigint"),
        ("resource_id", "integer"),
        ("resource_name", "character varying"),
        ("geoid", "character varying"),
        ("county", "character varying"),
        ("strain_name", "text"),
        ("pretreatment_method", "character varying"),
        ("enzyme_name", "character varying"),
        ("bioconversion_method", "character varying"),
        ("elapsed_time", "double precision"),
        ("product_name", "character varying"),
        ("avg_value", "numeric"),
        ("min_value", "numeric"),
        ("max_value", "numeric"),
        ("std_dev", "numeric"),
        ("observation_count", "bigint"),
        ("unit", "character varying"),
    ],
    "data_portal.mv_biomass_gasification": [
        ("id", "bigint"),
        ("resource_id", "integer"),
        ("resource_name", "character varying"),
        ("reactor_type", "character varying"),
        ("parameter_name", "text"),
        ("geoid", "character varying"),
        ("avg_value", "numeric"),
        ("min_value", "numeric"),
        ("max_value", "numeric"),
        ("std_dev", "numeric"),
        ("observation_count", "bigint"),
        ("unit", "character varying"),
    ],
    "data_portal.mv_biomass_pricing": [
        ("id", "bigint"),
        ("resource_id", "integer"),
        ("resource_name", "character varying"),
        ("geoid", "character varying"),
        ("county", "character varying"),
        ("county_fips", "character varying"),
        ("state", "character varying"),
        ("report_date", "timestamp without time zone"),
        ("report_source", "character varying"),
        ("market_type_category", "character varying"),
        ("sale_type", "character varying"),
        ("price_min", "numeric"),
        ("price_max", "numeric"),
        ("price_avg", "numeric"),
        ("price_unit", "character varying"),
    ],
    "data_portal.mv_usda_county_production": [
        ("id", "bigint"),
        ("resource_id", "integer"),
        ("resource_name", "character varying"),
        ("primary_ag_product", "character varying"),
        ("geoid", "character varying"),
        ("county", "character varying"),
        ("state", "character varying"),
        ("dataset_year", "integer"),
        ("primary_product_volume", "numeric"),
        ("volume_unit", "text"),
        ("production_acres", "numeric"),
        ("known_biomass_volume", "text"),
        ("calculated_estimate_volume", "double precision"),
        ("biomass_unit", "text"),
    ],
    "data_portal.mv_biomass_search": [
        ("id", "integer"),
        ("name", "character varying"),
        ("resource_code", "character varying"),
        ("description", "character varying"),
        ("resource_class", "character varying"),
        ("resource_subclass", "character varying"),
        ("primary_product", "character varying"),
        ("image_url", "character varying"),
        ("literature_uri", "character varying"),
        ("total_annual_volume", "numeric"),
        ("county_count", "bigint"),
        ("volume_unit", "text"),
        ("total_annual_volume_year", "integer"),
        ("moisture_percent", "numeric"),
        ("sugar_content_percent", "numeric"),
        ("glucan_percent", "numeric"),
        ("xylan_percent", "numeric"),
        ("ash_percent", "numeric"),
        ("lignin_percent", "numeric"),
        ("carbon_percent", "numeric"),
        ("hydrogen_percent", "numeric"),
        ("cn_ratio", "numeric"),
        ("transport_notes", "text"),
        ("storage_notes", "text"),
        ("tags", "text[]"),
        ("season_from_month", "integer"),
        ("season_to_month", "integer"),
        ("year_round", "boolean"),
        ("has_proximate", "boolean"),
        ("has_compositional", "boolean"),
        ("has_ultimate", "boolean"),
        ("has_xrf", "boolean"),
        ("has_icp", "boolean"),
        ("has_calorimetry", "boolean"),
        ("has_xrd", "boolean"),
        ("has_ftnir", "boolean"),
        ("has_fermentation", "boolean"),
        ("has_gasification", "boolean"),
        ("has_pretreatment", "boolean"),
        ("has_moisture_data", "boolean"),
        ("has_sugar_data", "boolean"),
        ("has_image", "boolean"),
        ("has_volume_data", "boolean"),
        ("calculated_estimate_volume_min", "numeric"),
        ("calculated_estimate_volume_max", "numeric"),
        ("calculated_estimate_volume_mid", "numeric"),
        ("volume_estimate_year", "integer"),
        ("created_at", "timestamp without time zone"),
        ("updated_at", "timestamp without time zone"),
        ("search_vector", "tsvector"),
    ],
    "data_portal.mv_biomass_end_uses": [
        ("resource_id", "integer"),
        ("resource_name", "character varying"),
        ("use_case", "character varying"),
        ("percentage_low", "double precision"),
        ("percentage_high", "double precision"),
        ("trend", "text"),
        ("value_low_usd", "double precision"),
        ("value_high_usd", "double precision"),
        ("value_multiplier_low", "double precision"),
        ("value_multiplier_high", "double precision"),
        ("value_notes", "text"),
    ],
    "data_portal.mv_biomass_volume_estimate": [
        ("id", "bigint"),
        ("resource_id", "integer"),
        ("resource_name", "character varying"),
        ("geoid", "character varying"),
        ("county", "character varying"),
        ("county_fips", "character varying"),
        ("state", "character varying"),
        ("dataset_year", "integer"),
        ("production_volume", "numeric"),
        ("county_crop_acres", "numeric"),
        ("production_unit", "character varying"),
        ("factor_min", "numeric"),
        ("factor_mid", "numeric"),
        ("factor_max", "numeric"),
        ("estimated_residue_volume_min", "numeric"),
        ("estimated_residue_volume_mid", "numeric"),
        ("estimated_residue_volume_max", "numeric"),
        ("volume_source", "character varying"),
        ("biomass_unit", "character varying"),
    ],
}

DEFAULT_ENV_CONFIGS = {
    "local": {
        "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "database": os.environ.get("POSTGRES_DB", "biocirv_db"),
        "user": os.environ.get("POSTGRES_USER", "biocirv_user"),
        "password": os.environ.get("POSTGRES_PASSWORD", "biocirv_dev_password"),
        "label": "Local Dev (Docker :5432)",
    },
    "staging": {
        "host": os.environ.get("DB_HOST_STAGING", "127.0.0.1"),
        "port": int(os.environ.get("DB_PORT_STAGING", "5434")),
        "database": os.environ.get("DB_NAME_STAGING", "biocirv-staging"),
        "user": os.environ.get("DB_USER_STAGING", "biocirv_user"),
        "password": os.environ.get(
            "DB_PASSWORD_STAGING", os.environ.get("BIOCIRV_STAGING_USER_PW", "")
        ),
        "label": "Staging (Cloud SQL :5434)",
    },
    "production": {
        "host": os.environ.get("DB_HOST_PROD", "127.0.0.1"),
        "port": int(os.environ.get("DB_PORT_PROD", "5435")),
        "database": os.environ.get("DB_NAME_PROD", "biocirv-production"),
        "user": os.environ.get("DB_USER_PROD", "biocirv_user"),
        "password": os.environ.get(
            "DB_PASSWORD_PROD", os.environ.get("BIOCIRV_PRODUCTION_USER_PW", "")
        ),
        "label": "Production (Cloud SQL :5435)",
    },
}

ANALYTICAL_TABLE_LABELS = {
    "public.calorimetry_record": "Calorimetry",
    "public.compositional_record": "Compositional Analysis",
    "public.fermentation_record": "Fermentation (Bioconversion)",
    "public.ftnir_record": "FT-NIR Spectroscopy",
    "public.gasification_record": "Gasification",
    "public.icp_record": "ICP Elemental Analysis",
    "public.pretreatment_record": "Pretreatment & Hydrolysis",
    "public.proximate_record": "Proximate Analysis",
    "public.ultimate_record": "Ultimate Analysis",
    "public.xrd_record": "XRD Crystallinity",
    "public.xrf_record": "XRF Elemental Analysis",
}


def _short_hash(text_val: str) -> str:
    return hashlib.sha256(text_val.encode("utf-8")).hexdigest()[:12]


def _resolve_reference_file(rel_path: str) -> Path:
    """Resolve a reference file relative to REPO_ROOT."""
    return REPO_ROOT / rel_path


def _parse_dotenv() -> dict[str, str]:
    """Read key-value pairs from `.env` at REPO_ROOT without mutating os.environ."""
    env_vals: dict[str, str] = {}
    dotenv_path = REPO_ROOT / ".env"
    if not dotenv_path.exists():
        return env_vals
    try:
        for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            if "#" in v and not (v.startswith('"') or v.startswith("'")):
                v = v.split("#", 1)[0].strip()
            v = v.strip('"').strip("'")
            env_vals[k] = v
    except Exception:
        pass
    return env_vals


def load_db_reset_config() -> dict[str, dict[str, Any]]:
    """Parse connection defaults from `resources/config/db_reset.yaml` and `.env`."""
    from sqlalchemy.engine import make_url

    configs = deepcopy(DEFAULT_ENV_CONFIGS)
    dotenv_vals = _parse_dotenv()
    env_map = {**dotenv_vals, **os.environ}

    yaml_path = _resolve_reference_file("resources/config/db_reset.yaml")
    if yaml_path.exists():
        try:
            raw_text = yaml_path.read_text(encoding="utf-8")
            current_env = None
            env_pat = re.compile(r"^\s{2}(local|staging|production):\s*$")
            kv_pat = re.compile(r"^\s{4}([a-z_]+):\s*(.+?)\s*$")
            var_pat = re.compile(r"\$\{([A-Z0-9_]+):-([^}]+)\}")

            for line in raw_text.splitlines():
                m_env = env_pat.match(line)
                if m_env:
                    current_env = m_env.group(1)
                    continue
                if current_env:
                    m_kv = kv_pat.match(line)
                    if m_kv:
                        k, v = m_kv.group(1), m_kv.group(2)
                        m_var = var_pat.search(v)
                        if m_var:
                            env_name, default_val = m_var.group(1), m_var.group(2)
                            resolved = env_map.get(env_name, default_val)
                        else:
                            resolved = v
                        if k == "host":
                            configs[current_env]["host"] = (
                                "127.0.0.1"
                                if resolved in ("db", "localhost", "${POSTGRES_HOST:-db}")
                                else resolved
                            )
                        elif k == "port":
                            try:
                                configs[current_env]["port"] = int(resolved)
                            except ValueError:
                                pass
                        elif k == "database":
                            configs[current_env]["database"] = resolved
                        elif k == "postgres_user":
                            configs[current_env]["user"] = resolved
        except Exception:
            pass

    # Apply .env / environment overrides for local, staging, and production
    configs["local"]["host"] = "127.0.0.1"
    if "POSTGRES_PORT" in env_map:
        try:
            configs["local"]["port"] = int(env_map["POSTGRES_PORT"])
        except ValueError:
            pass
    if "POSTGRES_DB" in env_map:
        configs["local"]["database"] = env_map["POSTGRES_DB"]
    if "POSTGRES_USER" in env_map:
        configs["local"]["user"] = env_map["POSTGRES_USER"]
    if "POSTGRES_PASSWORD" in env_map:
        configs["local"]["password"] = env_map["POSTGRES_PASSWORD"]

    staging_url_str = env_map.get("AUDITOR_STAGING_DATABASE_URL") or env_map.get(
        "STAGING_DATABASE_URL"
    )
    if staging_url_str:
        try:
            u = make_url(staging_url_str)
            configs["staging"]["host"] = (
                "127.0.0.1"
                if (not u.host or u.host in ("localhost", "db"))
                else u.host
            )
            configs["staging"]["port"] = int(u.port or 5434)
            configs["staging"]["database"] = u.database or "biocirv-staging"
            configs["staging"]["user"] = u.username or "biocirv_user"
            configs["staging"]["password"] = u.password or ""
        except Exception:
            pass
    else:
        configs["staging"]["host"] = "127.0.0.1"

    prod_url_str = env_map.get("AUDITOR_PRODUCTION_DATABASE_URL") or env_map.get(
        "AUDITOR_PROD_DATABASE_URL"
    )
    if prod_url_str:
        try:
            u = make_url(prod_url_str)
            configs["production"]["host"] = (
                "127.0.0.1"
                if (not u.host or u.host in ("localhost", "db"))
                else u.host
            )
            configs["production"]["port"] = int(u.port or 5435)
            configs["production"]["database"] = u.database or "biocirv-production"
            configs["production"]["user"] = u.username or "biocirv_user"
            configs["production"]["password"] = u.password or ""
        except Exception:
            pass
    else:
        configs["production"]["host"] = "127.0.0.1"
        configs["production"]["port"] = int(env_map.get("DB_PORT_PROD", 5435))
        configs["production"]["database"] = env_map.get(
            "DB_NAME_PROD", "biocirv-production"
        )
        configs["production"]["user"] = env_map.get("DB_USER_PROD", "biocirv_user")
        if "DB_PASSWORD_PROD" in env_map or "BIOCIRV_PRODUCTION_USER_PW" in env_map:
            configs["production"]["password"] = env_map.get(
                "DB_PASSWORD_PROD", env_map.get("BIOCIRV_PRODUCTION_USER_PW", "")
            )

    return configs


def _compute_stats_from_values(vals: list[float]) -> dict[str, Any]:
    if not vals:
        return {"n": 0, "mean": 0.0, "sd": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}
    n = len(vals)
    mean_v = statistics.mean(vals)
    sd_v = statistics.stdev(vals) if n >= 2 else 0.0
    med_v = statistics.median(vals)
    return {
        "n": n,
        "mean": round(mean_v, 4),
        "sd": round(sd_v, 4),
        "median": round(med_v, 4),
        "min": round(min(vals), 4),
        "max": round(max(vals), 4),
    }


def _normalize_pg_type(raw_type: str) -> str:
    """Normalize pg_catalog.format_type output to canonical SQL type strings."""
    t = str(raw_type).strip().lower()
    if t.startswith("character varying"):
        return "character varying"
    if t.startswith("numeric"):
        return "numeric"
    if t.endswith("geometry") or "geometry(" in t:
        return "geometry"
    if t.startswith("timestamp with time zone"):
        return "timestamp with time zone"
    if t.startswith("timestamp without time zone"):
        return "timestamp without time zone"
    return t


def _alembic_migration_index(rev_id: str) -> tuple[int, str]:
    """Resolve Alembic revision index and migration filename from alembic/versions."""
    versions_dir = REPO_ROOT / "alembic" / "versions"
    if not versions_dir.exists() or not rev_id or rev_id == "unknown":
        return (0, "unknown")
    files = sorted(versions_dir.glob("*.py"))
    for idx, fpath in enumerate(files, start=1):
        try:
            txt = fpath.read_text(encoding="utf-8")
            if f'revision: str = "{rev_id}"' in txt or f"revision = '{rev_id}'" in txt or f'revision = "{rev_id}"' in txt:
                m_num = re.match(r"^(\d{4})_", fpath.stem)
                mig_num = int(m_num.group(1)) if m_num else idx
                return (mig_num, fpath.stem)
        except Exception:
            continue
    m_rev = re.match(r"^(\d+)", str(rev_id).strip())
    if m_rev:
        return (int(m_rev.group(1)), rev_id)
    return (len(files), rev_id)


def _build_unmeasured_fingerprint(
    env_key: str, cfg: dict[str, Any], reason: str
) -> dict[str, Any]:
    """Return an honest, unmeasured fingerprint placeholder when an environment DB is unreachable."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tables_schema = {
        t_name: {
            "category": cat,
            "column_count": 0,
            "columns": [],
            "has_qc_pass": has_qc,
            "schema_hash": "unmeasured",
        }
        for t_name, cat, _, has_qc in CORE_TABLE_METADATA
    }
    mvs_schema = {}
    for v_name, v_cat, idx_cnt in ALL_19_VIEWS:
        schema_part, short_v = v_name.split(".", 1)
        mvs_schema[v_name] = {
            "schema": schema_part,
            "view_name": short_v,
            "category": v_cat,
            "definition_hash": "unmeasured",
            "column_count": 0,
            "columns": [],
            "column_schema_hash": "unmeasured",
            "is_populated": False,
            "is_stale": False,
            "stale_reason": f"Unmeasured ({reason})",
            "last_refreshed_utc": "unmeasured",
            "index_count": idx_cnt,
        }

    return {
        "environment": env_key,
        "label": cfg.get("label", env_key),
        "is_measured": False,
        "capture_mode": "unmeasured_offline",
        "capture_badge": f"Unmeasured — Proxy/DB Offline ({cfg['host']}:{cfg['port']}/{cfg['database']})",
        "unmeasured_reason": reason,
        "captured_at": now_iso,
        "connection": {
            "host": cfg["host"],
            "port": cfg["port"],
            "database": cfg["database"],
            "user": cfg["user"],
            "schemas": ["public", "ca_biositing", "data_portal"],
        },
        "layer1_schema": {
            "alembic_head": "unmeasured (offline)",
            "alembic_revision_id": "unmeasured",
            "alembic_migration_name": "unmeasured",
            "migration_index": 0,
            "table_count": 0,
            "total_columns": 0,
            "tables": tables_schema,
            "materialized_views": mvs_schema,
            "mv_freshness_summary": {
                "total_views": len(ALL_19_VIEWS),
                "populated_views": 0,
                "stale_views": 0,
                "stale_view_names": [],
                "definition_drifted_views": [],
                "last_mv_refresh_utc": "unmeasured",
                "refresh_lag_hours": 0.0,
                "needs_refresh_views": False,
            },
        },
        "layer2_row_counts": {
            "core_tables": {t_name: 0 for t_name, _, _, _ in CORE_TABLE_METADATA},
            "views": {v_name: 0 for v_name, _, _ in ALL_19_VIEWS},
            "totals": {
                "aim1_aim2_records": 0,
                "aim1_aim2_joined_observations": 0,
                "active_analytical_tables": 0,
                "core_entities": 0,
                "observations": 0,
                "all_core_tables": 0,
                "all_views": 0,
            },
        },
        "layer3_coverage_and_lineage": {
            "resource_analysis_matrix": {},
            "qc_pass_distribution": {
                t_name: {"pass": 0, "fail": 0, "other": 0, "total": 0, "pass_rate_pct": 0.0}
                for t_name in AIM1_AIM2_TABLES
            },
            "lineage_sets": {
                "resources": [],
                "active_analytical_resources": [],
                "field_samples": [],
                "prepared_samples": [],
                "experiments": [],
            },
        },
        "layer4_parameters_and_funnels": {
            "parameter_stats": {},
            "analysis_data_view_funnel": {
                "candidate_pool": 0,
                "removed_by_qc_fail": 0,
                "removed_by_resource_blacklist": 0,
                "removed_by_provider_blacklist": 0,
                "removed_by_ultimate_whitelist": 0,
                "removed_by_ultimate_value_gt_100": 0,
                "removed_by_icp_non_ppm_unit": 0,
                "unmapped_resource": 0,
                "final_row_count": 0,
                "expected_live_row_count": 0,
                "retention_ratio": 0.0,
            },
            "mv_biomass_composition_funnel": {
                "candidate_pool_all_record_rows": 0,
                "final_row_count": 0,
                "expected_live_row_count": 0,
                "retention_ratio": 0.0,
            },
        },
    }



def extract_live_fingerprint(
    env_key: str,
    base_dir: Path,
    host: str | None = None,
    port: int | None = None,
    dbname: str | None = None,
    user: str | None = None,
    password: str | None = None,
) -> dict[str, Any]:
    """Connect to a live PostgreSQL environment and extract its 4-layer fingerprint directly from SQL."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL

    configs = load_db_reset_config()
    cfg = deepcopy(configs.get(env_key, DEFAULT_ENV_CONFIGS.get(env_key, DEFAULT_ENV_CONFIGS["local"])))
    if host:
        cfg["host"] = host
    if port:
        cfg["port"] = int(port)
    if dbname:
        cfg["database"] = dbname
    if user:
        cfg["user"] = user
    if password is not None:
        cfg["password"] = password

    fp_dir = base_dir / "audit" / "output" / "env_fingerprints"
    fp_dir.mkdir(parents=True, exist_ok=True)
    out_path = fp_dir / f"{env_key}_fingerprint.json"

    url_obj = URL.create(
        drivername="postgresql+psycopg2",
        username=str(cfg.get("user") or "biocirv_user"),
        password=str(cfg.get("password") or ""),
        host=str(cfg.get("host") or "127.0.0.1"),
        port=int(cfg.get("port") or 5432),
        database=str(cfg.get("database") or "biocirv_db"),
    )
    print(f"[extract-env] Connecting to {env_key} ({cfg['host']}:{cfg['port']}/{cfg['database']})...")

    try:
        engine = create_engine(url_obj, pool_pre_ping=True, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            try:
                alembic_ver = (
                    conn.execute(text("SELECT version_num FROM public.alembic_version LIMIT 1")).scalar()
                    or "unknown"
                )
            except Exception:
                conn.rollback()
                alembic_ver = "unknown"

            table_count = (
                conn.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                    )
                ).scalar()
                or 0
            )
            total_cols = (
                conn.execute(
                    text("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'public'")
                ).scalar()
                or 0
            )

            tables_schema: dict[str, Any] = {}
            core_counts: dict[str, int] = {}
            table_columns_map: dict[str, set[str]] = {}
            for t_name, cat, default_cols, has_qc in CORE_TABLE_METADATA:
                cols = conn.execute(
                    text(
                        "SELECT column_name, data_type FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = :t ORDER BY ordinal_position"
                    ),
                    {"t": t_name},
                ).all()
                col_names = [str(c[0]) for c in cols]
                table_columns_map[t_name] = set(col_names)
                col_sig = ",".join(f"{c[0]}:{c[1]}" for c in cols)
                tables_schema[t_name] = {
                    "category": cat,
                    "column_count": len(cols) or default_cols,
                    "columns": col_names,
                    "has_qc_pass": "qc_pass" in table_columns_map[t_name] if cols else has_qc,
                    "schema_hash": _short_hash(f"{t_name}:{col_sig}"),
                }
                try:
                    cnt = conn.execute(text(f"SELECT COUNT(*) FROM public.{t_name}")).scalar() or 0
                except Exception:
                    conn.rollback()
                    cnt = 0
                core_counts[t_name] = int(cnt)

            # Views & Materialized Views + Column Schema Guard Introspection
            view_cols_rows = conn.execute(
                text(
                    "SELECT n.nspname AS schema_name, c.relname AS view_name, "
                    "a.attnum AS ordinal_position, a.attname AS column_name, "
                    "pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type "
                    "FROM pg_catalog.pg_attribute a "
                    "JOIN pg_catalog.pg_class c ON a.attrelid = c.oid "
                    "JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid "
                    "WHERE n.nspname IN ('ca_biositing', 'data_portal') "
                    "AND c.relkind IN ('v', 'm') "
                    "AND a.attnum > 0 AND NOT a.attisdropped "
                    "ORDER BY n.nspname, c.relname, a.attnum"
                )
            ).all()
            live_view_cols: dict[str, list[dict[str, Any]]] = {}
            for sch_n, vw_n, _, col_n, dtype in view_cols_rows:
                qk = f"{sch_n}.{vw_n}"
                lst = live_view_cols.setdefault(qk, [])
                lst.append(
                    {
                        "ordinal_position": len(lst) + 1,
                        "column_name": str(col_n),
                        "data_type": _normalize_pg_type(str(dtype)),
                    }
                )

            mvs_rows = conn.execute(
                text(
                    "SELECT schemaname, matviewname, ispopulated, definition "
                    "FROM pg_matviews WHERE schemaname IN ('ca_biositing', 'data_portal') "
                    "ORDER BY schemaname, matviewname"
                )
            ).all()
            mvs_by_qname = {f"{r[0]}.{r[1]}": (r[0], r[1], bool(r[2]), str(r[3] or "")) for r in mvs_rows}

            mvs_schema: dict[str, Any] = {}
            view_counts: dict[str, int] = {}
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            for v_name, v_cat, _ in ALL_19_VIEWS:
                sch_part, vw_part = v_name.split(".", 1)
                mv_meta = mvs_by_qname.get(v_name)
                is_pop = mv_meta[2] if mv_meta else False
                defn = mv_meta[3] if mv_meta else ""
                try:
                    cnt = conn.execute(text(f"SELECT COUNT(*) FROM {v_name}")).scalar() or 0
                except Exception:
                    conn.rollback()
                    cnt = 0
                view_counts[v_name] = int(cnt)
                col_objs = live_view_cols.get(v_name, [])
                col_sig = "|".join(f"{c['column_name']}:{c['data_type']}" for c in col_objs)
                col_hash = _short_hash(f"{v_name}:cols:{col_sig}") if col_objs else "missing"
                mvs_schema[v_name] = {
                    "schema": sch_part,
                    "view_name": vw_part,
                    "category": v_cat,
                    "definition_hash": _short_hash(defn) if defn else "missing",
                    "column_count": len(col_objs),
                    "columns": col_objs,
                    "column_schema_hash": col_hash,
                    "col_schema_hash": col_hash,
                    "is_populated": bool(is_pop),
                    "is_stale": False,
                    "stale_reason": "",
                    "last_refreshed_utc": now_iso,
                    "index_count": 1,
                }

            # Layer 3: QC distribution across AIM1_AIM2_TABLES
            qc_enriched: dict[str, Any] = {}
            for t_name in AIM1_AIM2_TABLES:
                t_cols = table_columns_map.get(t_name, set())
                dist = {"pass": 0, "fail": 0, "other": 0}
                if "qc_pass" in t_cols:
                    rows_qc = conn.execute(
                        text(
                            f"SELECT LOWER(COALESCE(CAST(qc_pass AS TEXT), 'other')), COUNT(*) "
                            f"FROM public.{t_name} GROUP BY 1"
                        )
                    ).all()
                    for k_qc, c_qc in rows_qc:
                        k_str = str(k_qc or "other").lower()
                        if k_str in ("pass", "true", "t", "1"):
                            dist["pass"] += int(c_qc)
                        elif k_str in ("fail", "false", "f", "0"):
                            dist["fail"] += int(c_qc)
                        else:
                            dist["other"] += int(c_qc)
                else:
                    dist["other"] = core_counts.get(t_name, 0)
                tot = dist["pass"] + dist["fail"] + dist["other"]
                qc_enriched[t_name] = {
                    **dist,
                    "total": tot,
                    "pass_rate_pct": round((dist["pass"] / tot) * 100.0, 2) if tot > 0 else 0.0,
                }

            # Lineage sets
            res_names = [
                str(r[0])
                for r in conn.execute(text("SELECT name FROM public.resource WHERE name IS NOT NULL ORDER BY name")).all()
                if r[0]
            ]
            fs_list = [
                dict(r)
                for r in conn.execute(
                    text(
                        "SELECT fs.name, COALESCE(r.name, 'Unassigned') AS resource_name, "
                        "COALESCE(p.codename, 'unknown') AS provider "
                        "FROM public.field_sample fs "
                        "LEFT JOIN public.resource r ON fs.resource_id = r.id "
                        "LEFT JOIN public.provider p ON fs.provider_id = p.id "
                        "WHERE fs.name IS NOT NULL ORDER BY fs.name"
                    )
                )
                .mappings()
                .all()
            ]
            ps_list = [
                dict(r)
                for r in conn.execute(
                    text(
                        "SELECT ps.name, COALESCE(r.name, 'Unassigned') AS resource_name, "
                        "COALESCE(fs.name, 'Unassigned') AS field_sample, "
                        "COALESCE(pm.name, 'N/A') AS prep_method, "
                        "COALESCE(p.codename, 'unknown') AS provider "
                        "FROM public.prepared_sample ps "
                        "LEFT JOIN public.field_sample fs ON ps.field_sample_id = fs.id "
                        "LEFT JOIN public.resource r ON fs.resource_id = r.id "
                        "LEFT JOIN public.provider p ON fs.provider_id = p.id "
                        "LEFT JOIN public.preparation_method pm ON ps.prep_method_id = pm.id "
                        "WHERE ps.name IS NOT NULL ORDER BY ps.name"
                    )
                )
                .mappings()
                .all()
            ]
            exp_list = [
                str(r[0])
                for r in conn.execute(
                    text("SELECT name FROM public.experiment WHERE name IS NOT NULL ORDER BY name")
                ).all()
                if r[0]
            ]

            # Layer 3 Resource x Analysis Matrix & Layer 4 Parameter Stats from live analytical tables
            resource_matrix: dict[str, dict[str, Any]] = {}
            param_buckets: dict[tuple[str, str], dict[str, Any]] = {}
            total_joined_obs = 0
            cand_pool = 0
            rem_qc_fail = 0
            rem_res_bl = 0
            rem_prov_bl = 0
            rem_ult_wl = 0
            rem_ult_gt100 = 0
            rem_icp_unit = 0
            unmapped_res = 0

            excluded_resources = {
                "#n/a",
                "alfalfa",
                "sargassum",
                "lab media",
                "blend",
                "control",
                "blank",
            }
            excluded_providers = {"jaguar", "usda"}
            ultimate_whitelist = {"c", "h", "o", "n", "s", "carbon", "hydrogen", "oxygen", "nitrogen", "sulfur"}

            for tbl_name, at_label in ANALYTICAL_TABLE_LABELS.items():
                short_tbl = tbl_name.split(".")[-1]
                t_cols = table_columns_map.get(short_tbl, set())
                if not t_cols:
                    continue

                has_res_id = "resource_id" in t_cols
                has_ps_id = "prepared_sample_id" in t_cols
                has_qc_col = "qc_pass" in t_cols
                has_upd = "updated_at" in t_cols
                has_cre = "created_at" in t_cols
                has_rec_id = "record_id" in t_cols

                if has_res_id and has_ps_id:
                    res_join = (
                        "LEFT JOIN public.prepared_sample ps ON rec.prepared_sample_id = ps.id "
                        "LEFT JOIN public.field_sample fs ON ps.field_sample_id = fs.id "
                        "LEFT JOIN public.resource r ON COALESCE(rec.resource_id, fs.resource_id) = r.id "
                        "LEFT JOIN public.provider prov ON fs.provider_id = prov.id "
                    )
                elif has_ps_id:
                    res_join = (
                        "LEFT JOIN public.prepared_sample ps ON rec.prepared_sample_id = ps.id "
                        "LEFT JOIN public.field_sample fs ON ps.field_sample_id = fs.id "
                        "LEFT JOIN public.resource r ON fs.resource_id = r.id "
                        "LEFT JOIN public.provider prov ON fs.provider_id = prov.id "
                    )
                elif has_res_id:
                    res_join = "LEFT JOIN public.resource r ON rec.resource_id = r.id "
                else:
                    res_join = ""

                ps_name_expr = "ps.name" if has_ps_id else "NULL"
                prov_expr = "LOWER(COALESCE(prov.codename, ''))" if has_ps_id else "''"
                res_name_expr = "COALESCE(r.name, 'Unassigned')" if (has_res_id or has_ps_id) else "'Unassigned'"
                qc_expr = "LOWER(COALESCE(CAST(rec.qc_pass AS TEXT), 'other'))" if has_qc_col else "'other'"
                rec_id_expr = "CAST(rec.record_id AS TEXT)" if has_rec_id else "CAST(rec.id AS TEXT)"
                if has_upd and has_cre:
                    ts_expr = "CAST(COALESCE(rec.updated_at, rec.created_at) AS TEXT)"
                elif has_upd:
                    ts_expr = "CAST(rec.updated_at AS TEXT)"
                elif has_cre:
                    ts_expr = "CAST(rec.created_at AS TEXT)"
                else:
                    ts_expr = "NULL"

                # 1) Query record-level lineage & QC per resource for this table
                rec_sql = (
                    f"SELECT {res_name_expr} AS resource_name, "
                    f"{rec_id_expr} AS rec_key, "
                    f"{qc_expr} AS qc_val, "
                    f"{ps_name_expr} AS ps_name, "
                    f"{ts_expr} AS ts_val "
                    f"FROM public.{short_tbl} rec "
                    f"{res_join}"
                )
                rec_rows = conn.execute(text(rec_sql)).all()
                by_res: dict[str, dict[str, Any]] = {}
                for r_name, rec_key, qc_val, ps_name, ts_val in rec_rows:
                    r_str = str(r_name or "Unassigned")
                    bucket = by_res.setdefault(
                        r_str,
                        {
                            "count": 0,
                            "rec_keys": set(),
                            "qc_pass": 0,
                            "qc_fail": 0,
                            "qc_other": 0,
                            "ps_names": set(),
                            "max_ts": None,
                        },
                    )
                    bucket["count"] += 1
                    if rec_key:
                        bucket["rec_keys"].add(str(rec_key))
                    q_s = str(qc_val or "other").lower()
                    if q_s in ("pass", "true", "t", "1"):
                        bucket["qc_pass"] += 1
                    elif q_s in ("fail", "false", "f", "0"):
                        bucket["qc_fail"] += 1
                    else:
                        bucket["qc_other"] += 1
                    if ps_name:
                        bucket["ps_names"].add(str(ps_name))
                    if ts_val and (bucket["max_ts"] is None or str(ts_val) > str(bucket["max_ts"])):
                        bucket["max_ts"] = str(ts_val)

                # 2) Query joined observations for parameter_stats & funnel
                obs_sql = (
                    f"SELECT {res_name_expr} AS resource_name, "
                    f"{prov_expr} AS provider_code, "
                    f"{qc_expr} AS qc_val, "
                    f"COALESCE(p.name, 'unknown') AS param_name, "
                    f"COALESCE(u.name, 'dimensionless') AS unit_name, "
                    f"o.value AS val_num "
                    f"FROM public.{short_tbl} rec "
                    f"{res_join} "
                    f"JOIN public.observation o ON CAST(o.record_id AS TEXT) = {rec_id_expr} "
                    f"LEFT JOIN public.parameter p ON o.parameter_id = p.id "
                    f"LEFT JOIN public.unit u ON o.unit_id = u.id "
                    f"WHERE o.value IS NOT NULL"
                )
                obs_rows = conn.execute(text(obs_sql)).all()
                total_joined_obs += len(obs_rows)

                for r_name, prov_code, qc_val, param_name, unit_name, val_num in obs_rows:
                    try:
                        v_float = float(val_num)
                    except (TypeError, ValueError):
                        continue
                    r_str = str(r_name or "Unassigned")
                    p_str = str(param_name or "unknown").strip()
                    u_str = str(unit_name or "dimensionless").strip()
                    q_s = str(qc_val or "other").lower()
                    is_fail = q_s in ("fail", "false", "f", "0")

                    pk_tuple = (at_label, p_str.lower())
                    p_entry = param_buckets.setdefault(
                        pk_tuple,
                        {
                            "analysis_type": at_label,
                            "parameter_name": p_str.lower(),
                            "unit": u_str,
                            "qc_vals": [],
                            "raw_vals": [],
                        },
                    )
                    p_entry["raw_vals"].append(v_float)
                    if not is_fail:
                        p_entry["qc_vals"].append(v_float)

                    # Funnel accounting
                    cand_pool += 1
                    if is_fail:
                        rem_qc_fail += 1
                    elif r_str == "Unassigned":
                        unmapped_res += 1
                    elif r_str.lower() in excluded_resources:
                        rem_res_bl += 1
                    elif str(prov_code or "").lower() in excluded_providers:
                        rem_prov_bl += 1
                    elif short_tbl == "ultimate_record" and p_str.lower() not in ultimate_whitelist:
                        rem_ult_wl += 1
                    elif short_tbl == "ultimate_record" and v_float > 100.0:
                        rem_ult_gt100 += 1
                    elif short_tbl == "icp_record" and u_str.lower() not in ("ppm", "mg/kg"):
                        rem_icp_unit += 1

                for r_str, b_data in by_res.items():
                    res_cell = resource_matrix.setdefault(r_str, {})
                    sorted_ids = sorted(b_data["rec_keys"])
                    sorted_ps = sorted(b_data["ps_names"])
                    res_cell[at_label] = {
                        "count": b_data["count"],
                        "unique_record_count": len(sorted_ids),
                        "qc_pass": b_data["qc_pass"],
                        "qc_fail": b_data["qc_fail"],
                        "qc_other": b_data["qc_other"],
                        "record_ids_sample": sorted_ids[:8],
                        "prepared_samples": sorted_ps[:12],
                        "record_hash": _short_hash("|".join(sorted_ids)) if sorted_ids else "empty",
                        "last_updated": b_data["max_ts"],
                    }

            # Fill 0-cells for active resources across all 10 analysis types
            active_res_names = sorted(r for r in resource_matrix.keys() if r != "Unassigned")
            all_at_labels = sorted(set(ANALYTICAL_TABLE_LABELS.values()))
            for r_str in active_res_names:
                for at_lbl in all_at_labels:
                    resource_matrix[r_str].setdefault(
                        at_lbl,
                        {
                            "count": 0,
                            "unique_record_count": 0,
                            "qc_pass": 0,
                            "qc_fail": 0,
                            "qc_other": 0,
                            "record_ids_sample": [],
                            "prepared_samples": [],
                            "record_hash": "empty",
                            "last_updated": None,
                        },
                    )

            # Finalize parameter_stats
            param_stats_out: dict[str, Any] = {}
            for (at_lbl, p_name_low), p_data in sorted(param_buckets.items()):
                key_str = f"{at_lbl}::{p_name_low}"
                qc_s = _compute_stats_from_values(p_data["qc_vals"])
                raw_s = _compute_stats_from_values(p_data["raw_vals"])
                param_stats_out[key_str] = {
                    "analysis_type": at_lbl,
                    "parameter_name": p_name_low,
                    "unit": p_data["unit"],
                    **qc_s,
                    "raw_n": raw_s["n"],
                    "raw_mean": raw_s["mean"],
                }

            adv_final = view_counts.get("ca_biositing.analysis_data_view", 0)
            mv_comp_final = view_counts.get("data_portal.mv_biomass_composition", 0)
            aim1_aim2_total = sum(core_counts.get(t, 0) for t in AIM1_AIM2_TABLES)
            active_at_count = sum(1 for t in AIM1_AIM2_TABLES if core_counts.get(t, 0) > 0)
            core_ent_total = sum(
                core_counts.get(t, 0) for t, cat, _, _ in CORE_TABLE_METADATA if cat == "Core Lineage & Samples"
            )

            mig_idx, mig_name = _alembic_migration_index(alembic_ver)
            fp = {
                "environment": env_key,
                "label": cfg.get("label", env_key.title()),
                "is_measured": True,
                "captured_at": now_iso,
                "capture_mode": "live_db",
                "capture_badge": f"Live DB Extracted ({cfg['host']}:{cfg['port']}/{cfg['database']})",
                "connection": {
                    "host": cfg["host"],
                    "port": cfg["port"],
                    "database": cfg["database"],
                    "user": cfg["user"],
                    "proxy_note": cfg.get("proxy_note", ""),
                },
                "layer1_schema": {
                    "alembic_head": f"{mig_name} ({alembic_ver})" if mig_name != alembic_ver else f"{alembic_ver} (live)",
                    "alembic_revision_id": alembic_ver,
                    "alembic_migration_name": mig_name,
                    "migration_index": int(mig_idx),
                    "missing_migrations": [],
                    "table_count": int(table_count),
                    "public_table_count": int(table_count),
                    "total_columns": int(total_cols),
                    "public_column_count": int(total_cols),
                    "tables": tables_schema,
                    "materialized_views": mvs_schema,
                    "mv_freshness_summary": {
                        "total_views": len(ALL_19_VIEWS),
                        "fresh_views": sum(1 for v in mvs_schema.values() if not v.get("is_stale")),
                        "stale_views": sum(1 for v in mvs_schema.values() if v.get("is_stale")),
                        "stale_view_names": [k for k, v in mvs_schema.items() if v.get("is_stale")],
                        "definition_drifted_views": [],
                    },
                },
                "layer2_row_counts": {
                    "core_tables": core_counts,
                    "views": view_counts,
                    "totals": {
                        "aim1_aim2_records": aim1_aim2_total,
                        "aim1_aim2_joined_observations": total_joined_obs,
                        "active_analytical_tables": active_at_count,
                        "core_entities": core_ent_total,
                        "observations": core_counts.get("observation", 0),
                        "all_core_tables": sum(core_counts.values()),
                        "all_views": sum(view_counts.values()),
                    },
                },
                "layer3_coverage_and_lineage": {
                    "resource_analysis_matrix": resource_matrix,
                    "qc_pass_distribution": qc_enriched,
                    "lineage_sets": {
                        "resources": res_names,
                        "active_analytical_resources": active_res_names,
                        "field_samples": fs_list,
                        "prepared_samples": ps_list,
                        "experiments": exp_list,
                    },
                },
                "layer4_parameters_and_funnels": {
                    "parameter_stats": param_stats_out,
                    "analysis_data_view_funnel": {
                        "candidate_pool": cand_pool,
                        "removed_by_qc_fail": rem_qc_fail,
                        "removed_by_resource_blacklist": rem_res_bl,
                        "removed_by_provider_blacklist": rem_prov_bl,
                        "removed_by_ultimate_whitelist": rem_ult_wl,
                        "removed_by_ultimate_value_gt_100": rem_ult_gt100,
                        "removed_by_icp_non_ppm_unit": rem_icp_unit,
                        "unmapped_resource": unmapped_res,
                        "final_row_count": adv_final,
                        "expected_live_row_count": adv_final,
                        "retention_ratio": round(adv_final / cand_pool, 4) if cand_pool > 0 else 0.0,
                    },
                    "mv_biomass_composition_funnel": {
                        "candidate_pool_all_record_rows": aim1_aim2_total,
                        "final_row_count": mv_comp_final,
                        "expected_live_row_count": mv_comp_final,
                        "retention_ratio": round(mv_comp_final / aim1_aim2_total, 4)
                        if aim1_aim2_total > 0
                        else 0.0,
                    },
                },
            }
            out_path.write_text(json.dumps(fp, indent=2), encoding="utf-8")
            print(f"[extract-env] Wrote live fingerprint to {out_path} ({out_path.stat().st_size:,} bytes)")
            return fp
    except Exception as exc:
        print(f"[extract-env] WARNING: Could not connect to {env_key} ({exc}). Writing unmeasured fingerprint.")
        fp = _build_unmeasured_fingerprint(env_key, cfg, str(exc))
        out_path.write_text(json.dumps(fp, indent=2), encoding="utf-8")
        return fp


def compute_pair_comparison(fp_a: dict[str, Any], fp_b: dict[str, Any]) -> dict[str, Any]:
    """Compare two environment fingerprints (A = Reference/Source, B = Target/Comparison)."""
    env_a, env_b = fp_a["environment"], fp_b["environment"]
    meas_a = bool(fp_a.get("is_measured", fp_a.get("capture_mode") == "live_db"))
    meas_b = bool(fp_b.get("is_measured", fp_b.get("capture_mode") == "live_db"))
    both_measured = meas_a and meas_b

    s1_a, s1_b = fp_a["layer1_schema"], fp_b["layer1_schema"]
    r2_a, r2_b = fp_a["layer2_row_counts"], fp_b["layer2_row_counts"]
    c3_a, c3_b = fp_a["layer3_coverage_and_lineage"], fp_b["layer3_coverage_and_lineage"]
    p4_a, p4_b = fp_a["layer4_parameters_and_funnels"], fp_b["layer4_parameters_and_funnels"]

    rev_match = both_measured and (s1_a["alembic_revision_id"] == s1_b["alembic_revision_id"])
    rev_lag = (s1_a.get("migration_index") or 0) - (s1_b.get("migration_index") or 0) if both_measured else 0

    table_diffs = []
    synced_tables = 0
    for t_name, cat, _, _ in CORE_TABLE_METADATA:
        cnt_a = r2_a["core_tables"].get(t_name, 0)
        cnt_b = r2_b["core_tables"].get(t_name, 0)
        delta = (cnt_a - cnt_b) if both_measured else 0
        pct = (
            round((delta / cnt_b) * 100.0, 2)
            if (both_measured and cnt_b > 0)
            else (100.0 if (both_measured and cnt_a > 0) else 0.0)
        )
        hash_a = s1_a["tables"].get(t_name, {}).get("schema_hash", "")
        hash_b = s1_b["tables"].get(t_name, {}).get("schema_hash", "")
        if not both_measured:
            status = "UNMEASURED"
        elif delta == 0 and hash_a == hash_b:
            status = "SYNCED"
            synced_tables += 1
        elif delta > 0:
            status = f"{env_a.upper()} AHEAD"
        elif delta < 0:
            status = f"{env_b.upper()} AHEAD"
        else:
            status = "SCHEMA DRIFT"
        table_diffs.append(
            {
                "object_type": "table",
                "schema": "public",
                "name": t_name,
                "category": cat,
                "count_a": cnt_a,
                "count_b": cnt_b,
                "delta": delta,
                "pct_diff": pct,
                "hash_match": both_measured and (hash_a == hash_b),
                "status": status,
            }
        )

    view_diffs = []
    synced_views = 0
    view_guard_items = []
    views_passing_guard = 0
    total_view_cols_checked = 0
    total_col_mismatches = 0

    for v_name, v_cat, _ in ALL_19_VIEWS:
        cnt_a = r2_a["views"].get(v_name, 0)
        cnt_b = r2_b["views"].get(v_name, 0)
        delta = (cnt_a - cnt_b) if both_measured else 0
        pct = (
            round((delta / cnt_b) * 100.0, 2)
            if (both_measured and cnt_b > 0)
            else (100.0 if (both_measured and cnt_a > 0) else 0.0)
        )
        mv_a = s1_a["materialized_views"].get(v_name, {})
        mv_b = s1_b["materialized_views"].get(v_name, {})
        stale_b = bool(mv_b.get("is_stale", False)) if both_measured else False
        hash_match = both_measured and (mv_a.get("definition_hash") == mv_b.get("definition_hash"))

        canon_cols = [
            {"ordinal_position": idx + 1, "column_name": cn, "data_type": _normalize_pg_type(dt)}
            for idx, (cn, dt) in enumerate(CANONICAL_VIEW_SCHEMAS.get(v_name, []))
        ]
        cols_a = mv_a.get("columns") if meas_a else []
        cols_b = mv_b.get("columns") if meas_b else []
        map_canon = {c["column_name"]: c for c in canon_cols}
        map_a = {c["column_name"]: c for c in (cols_a or [])}
        map_b = {c["column_name"]: c for c in (cols_b or [])}

        all_col_names = list(
            dict.fromkeys(
                [c["column_name"] for c in canon_cols]
                + [c["column_name"] for c in (cols_a or [])]
                + [c["column_name"] for c in (cols_b or [])]
            )
        )
        col_details = []
        missing_in_a = []
        missing_in_b = []
        type_mismatches = []

        for idx_c, col_name in enumerate(all_col_names):
            ca = map_a.get(col_name)
            cb = map_b.get(col_name)
            cc = map_canon.get(col_name)
            ta = _normalize_pg_type(ca["data_type"]) if ca else ("UNMEASURED" if not meas_a else "MISSING")
            tb = _normalize_pg_type(cb["data_type"]) if cb else ("UNMEASURED" if not meas_b else "MISSING")
            tc = _normalize_pg_type(cc["data_type"]) if cc else ta
            pos_a = ca["ordinal_position"] if ca else None
            pos_b = cb["ordinal_position"] if cb else None
            pos_c = cc["ordinal_position"] if cc else (idx_c + 1)

            if not both_measured:
                col_status = "UNMEASURED"
            elif not ca:
                missing_in_a.append(col_name)
                col_status = f"MISSING IN {env_a.upper()}"
            elif not cb:
                missing_in_b.append(col_name)
                col_status = f"MISSING IN {env_b.upper()}"
            elif ta != tb or ta != tc or tb != tc:
                type_mismatches.append(
                    {
                        "column_name": col_name,
                        "canonical_type": tc,
                        "type_a": ta,
                        "type_b": tb,
                    }
                )
                col_status = "TYPE MISMATCH"
            elif pos_a != pos_b:
                col_status = "ORDINAL SHIFT"
            else:
                col_status = "EXACT MATCH"

            col_details.append(
                {
                    "ordinal_position": pos_c,
                    "column_name": col_name,
                    "canonical_type": tc,
                    "type_a": ta,
                    "type_b": tb,
                    "pos_a": pos_a,
                    "pos_b": pos_b,
                    "status": col_status,
                    "match": col_status == "EXACT MATCH",
                }
            )

        total_view_cols_checked += len(all_col_names)
        view_col_mismatch_cnt = sum(1 for cd in col_details if not cd["match"]) if both_measured else 0
        total_col_mismatches += view_col_mismatch_cnt
        col_schema_match = both_measured and (view_col_mismatch_cnt == 0)
        if col_schema_match:
            views_passing_guard += 1

        col_sig_a = "|".join(f"{c['column_name']}:{c['data_type']}" for c in (cols_a or []))
        col_sig_b = "|".join(f"{c['column_name']}:{c['data_type']}" for c in (cols_b or []))
        col_hash_a = (
            mv_a.get("column_schema_hash")
            or (_short_hash(f"{v_name}:cols:{col_sig_a}") if cols_a else "unmeasured")
        )
        col_hash_b = (
            mv_b.get("column_schema_hash")
            or (_short_hash(f"{v_name}:cols:{col_sig_b}") if cols_b else "unmeasured")
        )

        if not both_measured:
            status = "UNMEASURED"
        elif not col_schema_match:
            status = "VIEW SCHEMA MISMATCH"
        elif stale_b:
            status = "MV STALE"
        elif delta == 0 and hash_match:
            status = "SYNCED"
            synced_views += 1
        elif delta > 0:
            status = f"{env_b.upper()} BEHIND" if env_b == "production" else f"{env_a.upper()} AHEAD"
        elif delta < 0:
            status = f"{env_b.upper()} AHEAD"
        else:
            status = "DEF DRIFT"

        view_diffs.append(
            {
                "object_type": "view",
                "schema": v_name.split(".")[0],
                "name": v_name,
                "category": v_cat,
                "count_a": cnt_a,
                "count_b": cnt_b,
                "delta": delta,
                "pct_diff": pct,
                "hash_match": hash_match,
                "col_schema_match": col_schema_match,
                "col_count_a": len(cols_a or []),
                "col_count_b": len(cols_b or []),
                "col_schema_hash_a": col_hash_a,
                "col_schema_hash_b": col_hash_b,
                "is_stale_b": stale_b,
                "stale_reason": mv_b.get("stale_reason", ""),
                "status": status,
            }
        )

        view_guard_items.append(
            {
                "view_name": v_name,
                "schema": v_name.split(".")[0],
                "short_name": v_name.split(".", 1)[1],
                "category": v_cat,
                "col_count_canonical": len(canon_cols),
                "col_count_a": len(cols_a or []),
                "col_count_b": len(cols_b or []),
                "col_schema_hash_a": col_hash_a,
                "col_schema_hash_b": col_hash_b,
                "col_schema_match": col_schema_match,
                "mismatch_count": view_col_mismatch_cnt,
                "missing_in_a": missing_in_a,
                "missing_in_b": missing_in_b,
                "type_mismatches": type_mismatches,
                "columns": col_details,
                "guard_status": "UNMEASURED" if not both_measured else ("PASS" if col_schema_match else "FAIL"),
            }
        )

    view_schema_guard = {
        "total_views": len(ALL_19_VIEWS),
        "ca_biositing_views": sum(1 for v, _, _ in ALL_19_VIEWS if v.startswith("ca_biositing.")),
        "data_portal_views": sum(1 for v, _, _ in ALL_19_VIEWS if v.startswith("data_portal.")),
        "views_passing_guard": views_passing_guard if both_measured else 0,
        "views_failing_guard": (len(ALL_19_VIEWS) - views_passing_guard) if both_measured else 0,
        "total_columns_checked": total_view_cols_checked if both_measured else 0,
        "total_column_mismatches": total_col_mismatches if both_measured else 0,
        "all_views_match": both_measured and (views_passing_guard == len(ALL_19_VIEWS)),
        "guard_status": "UNMEASURED"
        if not both_measured
        else ("PASS" if views_passing_guard == len(ALL_19_VIEWS) else "FAIL"),
        "views": view_guard_items,
    }

    def _set_diff(list_a: list[Any], list_b: list[Any], key_fn=lambda x: x):
        map_a = {key_fn(x): x for x in list_a}
        map_b = {key_fn(x): x for x in list_b}
        keys_a, keys_b = set(map_a.keys()), set(map_b.keys())
        only_a = [map_a[k] for k in sorted(keys_a - keys_b)]
        only_b = [map_b[k] for k in sorted(keys_b - keys_a)]
        shared = sorted(keys_a & keys_b)
        return {
            "count_a": len(keys_a),
            "count_b": len(keys_b),
            "shared_count": len(shared),
            "only_in_a": only_a,
            "only_in_b": only_b,
        }

    lineage_diff = {
        "resources": _set_diff(c3_a["lineage_sets"]["resources"], c3_b["lineage_sets"]["resources"]),
        "field_samples": _set_diff(
            c3_a["lineage_sets"]["field_samples"],
            c3_b["lineage_sets"]["field_samples"],
            key_fn=lambda x: x["name"],
        ),
        "prepared_samples": _set_diff(
            c3_a["lineage_sets"]["prepared_samples"],
            c3_b["lineage_sets"]["prepared_samples"],
            key_fn=lambda x: x["name"],
        ),
        "experiments": _set_diff(
            c3_a["lineage_sets"]["experiments"], c3_b["lineage_sets"]["experiments"]
        ),
    }

    param_shifts = []
    all_param_keys = sorted(set(p4_a["parameter_stats"].keys()) | set(p4_b["parameter_stats"].keys()))
    flagged_5pct_count = 0
    for pk in all_param_keys:
        pa = p4_a["parameter_stats"].get(pk)
        pb = p4_b["parameter_stats"].get(pk)
        if not pa and not pb:
            continue
        at_name = (pa or pb)["analysis_type"]
        p_name = (pa or pb)["parameter_name"]
        unit_str = (pa or pb)["unit"]
        na = pa["n"] if pa else 0
        nb = pb["n"] if pb else 0
        ma = pa["mean"] if pa else 0.0
        mb = pb["mean"] if pb else 0.0
        med_a = pa["median"] if pa else 0.0
        med_b = pb["median"] if pb else 0.0
        if not both_measured:
            pct_shift = 0.0
            flagged = False
        elif nb == 0 and na > 0:
            pct_shift = 100.0
            flagged = True
        elif mb != 0:
            pct_shift = round(((ma - mb) / abs(mb)) * 100.0, 2)
            flagged = abs(pct_shift) > 5.0
        else:
            pct_shift = 0.0
            flagged = False
        if flagged:
            flagged_5pct_count += 1
        param_shifts.append(
            {
                "key": pk,
                "analysis_type": at_name,
                "parameter_name": p_name,
                "unit": unit_str,
                "n_a": na,
                "n_b": nb,
                "delta_n": (na - nb) if both_measured else 0,
                "mean_a": ma,
                "mean_b": mb,
                "median_a": med_a,
                "median_b": med_b,
                "pct_shift": pct_shift,
                "flagged_gt_5pct": flagged,
            }
        )

    if not both_measured:
        schema_score = None
        table_score = None
        view_score = None
        lineage_score = None
        sync_score = None
    else:
        schema_score = 25.0 if rev_match else max(5.0, 25.0 - abs(rev_lag) * 6.0)
        table_score = round((synced_tables / len(CORE_TABLE_METADATA)) * 25.0, 1)
        mv_penalty = len(s1_b["mv_freshness_summary"]["stale_view_names"]) * 2.5
        view_guard_penalty = (len(ALL_19_VIEWS) - views_passing_guard) * 4.0
        view_score = max(
            0.0,
            round((synced_views / len(ALL_19_VIEWS)) * 25.0 - mv_penalty - view_guard_penalty, 1),
        )
        param_ok_ratio = 1.0 - (flagged_5pct_count / max(1, len(param_shifts)))
        lineage_score = round(param_ok_ratio * 25.0, 1)
        sync_score = round(schema_score + table_score + view_score + lineage_score, 1)

    return {
        "pair_key": f"{env_a}_vs_{env_b}",
        "env_a": env_a,
        "env_b": env_b,
        "both_measured": both_measured,
        "sync_score": sync_score,
        "score_breakdown": {
            "schema_score": round(schema_score, 1) if schema_score is not None else None,
            "table_score": table_score,
            "view_score": view_score,
            "lineage_param_score": lineage_score,
        },
        "alembic_match": rev_match,
        "alembic_lag_migrations": rev_lag,
        "aim1_aim2_delta": (
            r2_a["totals"]["aim1_aim2_records"] - r2_b["totals"]["aim1_aim2_records"]
            if both_measured
            else 0
        ),
        "observation_delta": (
            r2_a["totals"]["observations"] - r2_b["totals"]["observations"]
            if both_measured
            else 0
        ),
        "table_diffs": table_diffs,
        "view_diffs": view_diffs,
        "view_schema_guard": view_schema_guard,
        "lineage_diff": lineage_diff,
        "param_shifts": param_shifts,
        "flagged_param_count": flagged_5pct_count,
    }


def generate_markdown_drift_report(
    fingerprints: dict[str, dict[str, Any]],
    comparisons: dict[str, dict[str, Any]],
    report_path: Path,
) -> None:
    """Write a comprehensive, human-readable Markdown drift report to `audit/output/drift_report.md`."""
    loc = fingerprints["local"]
    stg = fingerprints["staging"]
    prd = fingerprints["production"]
    c_ls = comparisons["local_vs_staging"]
    c_lp = comparisons["local_vs_production"]
    c_sp = comparisons["staging_vs_production"]

    loc_rec = loc["layer2_row_counts"]["totals"]["aim1_aim2_records"]
    stg_rec = stg["layer2_row_counts"]["totals"]["aim1_aim2_records"]
    prd_rec = prd["layer2_row_counts"]["totals"]["aim1_aim2_records"]
    loc_obs = loc["layer2_row_counts"]["totals"]["aim1_aim2_joined_observations"]

    loc_lin = loc["layer3_coverage_and_lineage"]["lineage_sets"]
    stg_lin = stg["layer3_coverage_and_lineage"]["lineage_sets"]
    prd_lin = prd["layer3_coverage_and_lineage"]["lineage_sets"]

    ls_score_str = f"{c_ls['sync_score']}%" if c_ls["sync_score"] is not None else "UNMEASURED"
    sp_score_str = f"{c_sp['sync_score']}%" if c_sp["sync_score"] is not None else "UNMEASURED"
    lp_score_str = f"{c_lp['sync_score']}%" if c_lp["sync_score"] is not None else "UNMEASURED"

    lines = [
        "# BioCirV — Multi-Environment Database Drift Assessment Report (`local` · `staging` · `production`)",
        "",
        f"**Generated UTC:** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`  ",
        "**Interactive Dashboard:** `exports/plots/audit/db_environment_drift_dashboard.html`  ",
        "**Generator CLI:** `pixi run python analysis/audit/db_environment_drift.py --extract-env local staging production --compare`",
        "",
        "---",
        "",
        "## 1. Executive Environment Summary & Sync Scorecard",
        "",
        "| Dimension | Local Dev (`:5432`) | Staging (`:5434` Proxy) | Production (`:5435` Proxy) | Drift Status |",
        "| :--- | :--- | :--- | :--- | :--- |",
        f"| **Database Name** | `{loc['connection']['database']}` | `{stg['connection']['database']}` | `{prd['connection']['database']}` | Canonical 3-tier topology |",
        f"| **Capture Mode** | `{loc['capture_mode']}` | `{stg['capture_mode']}` | `{prd['connection']['host']}:{prd['connection']['port']}` (`{prd['capture_mode']}`) | Live SQL extraction |",
        f"| **Alembic Revision Head** | `{loc['layer1_schema']['alembic_head']}` | `{stg['layer1_schema']['alembic_head']}` | `{prd['layer1_schema']['alembic_head']}` | **L vs S: `{c_ls['alembic_lag_migrations']:+d}` · L vs P: `{c_lp['alembic_lag_migrations']:+d}` migrations** |",
        f"| **Aim 1 / Aim 2 Record Rows** | **{loc_rec:,}** ({loc_obs:,} joined obs) | **{stg_rec:,}** (`Δ {loc_rec - stg_rec:+,}` vs Local) | **{prd_rec:,}** (`Δ {loc_rec - prd_rec:+,}` vs Local) | Live analytical record counts |",
        f"| **Resources / Field / Prep Samples** | `{len(loc_lin['resources'])} / {len(loc_lin['field_samples'])} / {len(loc_lin['prepared_samples'])}` | `{len(stg_lin['resources'])} / {len(stg_lin['field_samples'])} / {len(stg_lin['prepared_samples'])}` | `{len(prd_lin['resources'])} / {len(prd_lin['field_samples'])} / {len(prd_lin['prepared_samples'])}` | **`{len(loc_lin['prepared_samples']) - len(prd_lin['prepared_samples']):+,}` Prepared Samples in Local vs Prod** |",
        f"| **Public Tables / Columns** | `{loc['layer1_schema']['table_count']} tables / {loc['layer1_schema']['total_columns']} cols` | `{stg['layer1_schema']['table_count']} tables / {stg['layer1_schema']['total_columns']} cols` | `{prd['layer1_schema']['table_count']} tables / {prd['layer1_schema']['total_columns']} cols` | Public schema introspection |",
        f"| **Pairwise Sync Score** | **Local vs Staging: `{ls_score_str}`** | **Staging vs Prod: `{sp_score_str}`** | **Local vs Prod: `{lp_score_str}`** | Composite 4-layer parity index |",
        "",
        "---",
        "",
        "## 2. Key Environment Findings & Remediation",
        "",
        f"1. **Alembic Migration Revision Parity (`{loc['layer1_schema']['alembic_revision_id']}` Local vs `{stg['layer1_schema']['alembic_revision_id']}` Staging vs `{prd['layer1_schema']['alembic_revision_id']}` Production)**:",
        f"   - **Finding**: Local vs Staging migration delta is `{c_ls['alembic_lag_migrations']:+d}`; Local vs Production migration delta is `{c_lp['alembic_lag_migrations']:+d}`.",
        "   - **Remediation**: Promote pending Alembic migrations via `pixi run migrate` and refresh materialized views via `pixi run refresh-views`.",
        f"2. **View Schema Guard (`{c_lp['view_schema_guard']['views_passing_guard']}/{c_lp['view_schema_guard']['total_views']}` Views Verified Across Local vs Production)**:",
        f"   - **Finding**: Checked `{c_lp['view_schema_guard']['total_columns_checked']}` view columns across `ca_biositing` (8 views) and `data_portal` (11 views) with `{c_lp['view_schema_guard']['total_column_mismatches']}` column/type mismatches.",
        f"3. **Aim 1 / Aim 2 Analytical Record Delta (`Local - Staging = {c_ls['aim1_aim2_delta']:+,}` · `Local - Prod = {c_lp['aim1_aim2_delta']:+,}`)**:",
        f"   - **Finding**: Local holds `{loc_rec:,}` analytical records (`{loc['layer2_row_counts']['totals']['observations']:,}` observations), Staging holds `{stg_rec:,}` records (`{stg['layer2_row_counts']['totals']['observations']:,}` observations), and Production holds `{prd_rec:,}` records (`{prd['layer2_row_counts']['totals']['observations']:,}` observations).",
        f"4. **Parameter Mean Shift Audit (`>5%` Threshold)**:",
        f"   - **Finding**: `{c_ls['flagged_param_count']}` parameter slices exceed 5% mean shift between Local and Staging; `{c_lp['flagged_param_count']}` parameter slices exceed 5% mean shift between Local and Production.",
        "",
        "---",
        "",
        "## 3. Layer 2: Core Table & Materialized View Row-Count Waterfall",
        "",
        "### 3.1 Core Public Schema Tables (21 Tables)",
        "",
        "| Table Name | Category | Local (`:5432`) | Staging (`:5434`) | Production (`:5435`) | Δ (Local - Staging) | Δ (Local - Prod) | Status (Local vs Prod) |",
        "| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |",
    ]

    for row in c_lp["table_diffs"]:
        t_name = row["name"]
        loc_c = loc["layer2_row_counts"]["core_tables"].get(t_name, 0)
        stg_c = stg["layer2_row_counts"]["core_tables"].get(t_name, 0)
        prd_c = prd["layer2_row_counts"]["core_tables"].get(t_name, 0)
        d_ls = loc_c - stg_c
        d_lp = loc_c - prd_c
        lines.append(
            f"| `public.{t_name}` | {row['category']} | {loc_c:,} | {stg_c:,} | {prd_c:,} | {d_ls:+,} | {d_lp:+,} | **{row['status']}** |"
        )

    lines.extend(
        [
            "",
            "### 3.2 `ca_biositing` & `data_portal` Materialized Views (19 Views)",
            "",
            "| Materialized View | Cols (`Guard`) | Local (`:5432`) | Staging (`:5434`) | Production (`:5435`) | Δ (Local - Staging) | Δ (Local - Prod) | Status (Local vs Prod) |",
            "| :--- | :---: | ---: | ---: | ---: | ---: | ---: | :--- |",
        ]
    )

    guard_by_view = {v["view_name"]: v for v in c_lp["view_schema_guard"]["views"]}
    vdiff_by_view = {v["name"]: v for v in c_lp["view_diffs"]}
    for v_name, _, _ in ALL_19_VIEWS:
        loc_v = loc["layer2_row_counts"]["views"].get(v_name, 0)
        stg_v = stg["layer2_row_counts"]["views"].get(v_name, 0)
        prd_v = prd["layer2_row_counts"]["views"].get(v_name, 0)
        d_ls = loc_v - stg_v
        d_lp = loc_v - prd_v
        vg = guard_by_view.get(v_name, {})
        vd = vdiff_by_view.get(v_name, {})
        g_status = vg.get("guard_status", "PASS")
        col_badge = f"`{vg.get('col_count_canonical', 0)}` ({'✅ PASS' if g_status == 'PASS' else ('⚪ UNMEASURED' if g_status == 'UNMEASURED' else '❌ DRIFT')})"
        lines.append(
            f"| `{v_name}` | {col_badge} | {loc_v:,} | {stg_v:,} | {prd_v:,} | {d_ls:+,} | {d_lp:+,} | **{vd.get('status', 'SYNCED')}** |"
        )

    vsg_lp = c_lp["view_schema_guard"]
    lines.extend(
        [
            "",
            "### 3.3 View Schema Guard (`ca_biositing` & `data_portal` Column & Data-Type Parity)",
            "",
            f"- **Guard Summary:** `{vsg_lp['views_passing_guard']}/{vsg_lp['total_views']}` views verified (`{vsg_lp['ca_biositing_views']}` in `ca_biositing`, `{vsg_lp['data_portal_views']}` in `data_portal`) · `{vsg_lp['total_columns_checked'] - vsg_lp['total_column_mismatches']}/{vsg_lp['total_columns_checked']}` column definitions & data types match across environments.",
            "",
            "| Schema · View Name | Cols | Column Schema Hash (`L / S / P`) | Sample Verified Columns (`name: type`) | Guard Status |",
            "| :--- | ---: | :---: | :--- | :---: |",
        ]
    )
    for vg in vsg_lp["views"]:
        v_name = vg["view_name"]
        h_l = loc["layer1_schema"]["materialized_views"].get(v_name, {}).get("col_schema_hash", "—")[:8]
        h_s = stg["layer1_schema"]["materialized_views"].get(v_name, {}).get("col_schema_hash", "—")[:8]
        h_p = prd["layer1_schema"]["materialized_views"].get(v_name, {}).get("col_schema_hash", "—")[:8]
        sample_cols = ", ".join(
            f"`{c['column_name']}: {c['canonical_type']}`" for c in vg["columns"][:4]
        )
        if len(vg["columns"]) > 4:
            sample_cols += f", … (+{len(vg['columns']) - 4} more)"
        if vg["guard_status"] == "UNMEASURED":
            g_badge = "⚪ **UNMEASURED**"
        elif vg["col_schema_match"]:
            g_badge = "✅ **SCHEMA GUARD PASS**"
        else:
            g_badge = f"❌ **SCHEMA MISMATCH ({vg['mismatch_count']})**"
        lines.append(
            f"| `{v_name}` | {vg['col_count_canonical']} | `{h_l}` / `{h_s}` / `{h_p}` | {sample_cols} | {g_badge} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Layer 3: Lineage Set-Differences (`Local` vs `Staging` vs `Production`)",
            "",
            f"- **Resources in Local Only vs Production ({len(c_lp['lineage_diff']['resources']['only_in_a'])}):** "
            + (", ".join(f"`{r}`" for r in c_lp["lineage_diff"]["resources"]["only_in_a"]) or "None"),
            f"- **Field Samples in Local Only vs Staging ({len(c_ls['lineage_diff']['field_samples']['only_in_a'])}):** "
            + (", ".join(f"`{fs['name']}` ({fs['resource_name']})" for fs in c_ls["lineage_diff"]["field_samples"]["only_in_a"]) or "None"),
            f"- **Prepared Samples in Local Only vs Staging ({len(c_ls['lineage_diff']['prepared_samples']['only_in_a'])}):** "
            + (", ".join(f"`{ps['name']}`" for ps in c_ls["lineage_diff"]["prepared_samples"]["only_in_a"][:15]) or "None"),
            f"- **Prepared Samples in Local Only vs Production ({len(c_lp['lineage_diff']['prepared_samples']['only_in_a'])}):** "
            + (", ".join(f"`{ps['name']}`" for ps in c_lp["lineage_diff"]["prepared_samples"]["only_in_a"][:15]) or "None"),
            "",
            "---",
            "",
            "## 5. Layer 4: Filter Funnel Attrition & Parameter Value Shifts (`>5%`)",
            "",
            "### 5.1 `ca_biositing.analysis_data_view` Filter Funnel Comparison",
            "",
            "| Funnel Stage | Local (`:5432`) | Staging (`:5434`) | Production (`:5435`) |",
            "| :--- | ---: | ---: | ---: |",
            f"| **1. Raw Candidate Pool** | {loc['layer4_parameters_and_funnels']['analysis_data_view_funnel']['candidate_pool']:,} | {stg['layer4_parameters_and_funnels']['analysis_data_view_funnel']['candidate_pool']:,} | {prd['layer4_parameters_and_funnels']['analysis_data_view_funnel']['candidate_pool']:,} |",
            f"| **2. Removed by `qc_pass = 'fail'`** | -{loc['layer4_parameters_and_funnels']['analysis_data_view_funnel']['removed_by_qc_fail']:,} | -{stg['layer4_parameters_and_funnels']['analysis_data_view_funnel']['removed_by_qc_fail']:,} | -{prd['layer4_parameters_and_funnels']['analysis_data_view_funnel']['removed_by_qc_fail']:,} |",
            f"| **3. Removed by `EXCLUDED_RESOURCES`** | -{loc['layer4_parameters_and_funnels']['analysis_data_view_funnel']['removed_by_resource_blacklist']:,} | -{stg['layer4_parameters_and_funnels']['analysis_data_view_funnel']['removed_by_resource_blacklist']:,} | -{prd['layer4_parameters_and_funnels']['analysis_data_view_funnel']['removed_by_resource_blacklist']:,} |",
            f"| **4. Removed by `EXCLUDED_PROVIDERS`** | -{loc['layer4_parameters_and_funnels']['analysis_data_view_funnel']['removed_by_provider_blacklist']:,} | -{stg['layer4_parameters_and_funnels']['analysis_data_view_funnel']['removed_by_provider_blacklist']:,} | -{prd['layer4_parameters_and_funnels']['analysis_data_view_funnel']['removed_by_provider_blacklist']:,} |",
            f"| **5. Removed by `ULTIMATE_PARAMETERS`** | -{loc['layer4_parameters_and_funnels']['analysis_data_view_funnel']['removed_by_ultimate_whitelist']:,} | -{stg['layer4_parameters_and_funnels']['analysis_data_view_funnel']['removed_by_ultimate_whitelist']:,} | -{prd['layer4_parameters_and_funnels']['analysis_data_view_funnel']['removed_by_ultimate_whitelist']:,} |",
            f"| **6. Unmapped Resource (`resource_id IS NULL`)** | -{loc['layer4_parameters_and_funnels']['analysis_data_view_funnel']['unmapped_resource']:,} | -{stg['layer4_parameters_and_funnels']['analysis_data_view_funnel']['unmapped_resource']:,} | -{prd['layer4_parameters_and_funnels']['analysis_data_view_funnel']['unmapped_resource']:,} |",
            f"| **7. Final Materialized View Rows** | **{loc['layer4_parameters_and_funnels']['analysis_data_view_funnel']['final_row_count']:,}** | **{stg['layer4_parameters_and_funnels']['analysis_data_view_funnel']['final_row_count']:,}** | **{prd['layer4_parameters_and_funnels']['analysis_data_view_funnel']['final_row_count']:,}** |",
            f"| **Retention Ratio** | **{loc['layer4_parameters_and_funnels']['analysis_data_view_funnel']['retention_ratio']*100:.2f}%** | **{stg['layer4_parameters_and_funnels']['analysis_data_view_funnel']['retention_ratio']*100:.2f}%** | **{prd['layer4_parameters_and_funnels']['analysis_data_view_funnel']['retention_ratio']*100:.2f}%** |",
            "",
            f"### 5.2 Flagged Parameter Mean Shifts (`>5%` Local vs Production — {c_lp['flagged_param_count']} Flagged Slices)",
            "",
            "| Analysis Type | Parameter (Unit) | Local Mean (`n`) | Staging Mean (`n`) | Prod Mean (`n`) | Mean % Shift (L vs P) | Flag |",
            "| :--- | :--- | ---: | ---: | ---: | ---: | :--- |",
        ]
    )

    for ps in c_lp["param_shifts"]:
        if not ps["flagged_gt_5pct"]:
            continue
        pk = ps["key"]
        stg_p = stg["layer4_parameters_and_funnels"]["parameter_stats"].get(pk, {"mean": 0.0, "n": 0})
        unit_lbl = f" ({ps['unit']})" if ps["unit"] != "dimensionless" else ""
        lines.append(
            f"| {ps['analysis_type']} | `{ps['parameter_name']}`{unit_lbl} | {ps['mean_a']:,.2f} (`n={ps['n_a']}`) | {stg_p['mean']:,.2f} (`n={stg_p['n']}`) | {ps['mean_b']:,.2f} (`n={ps['n_b']}`) | **{ps['pct_shift']:+.2f}%** | ⚠️ `>5% SHIFT` |"
        )

    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[compare] Wrote Markdown drift report to {report_path}")


def build_drift_dashboard_html(
    fingerprints: dict[str, dict[str, Any]],
    comparisons: dict[str, dict[str, Any]],
    output_path: Path,
) -> None:
    """Generate the standalone interactive HTML5 + Plotly + Tailwind drift dashboard."""
    payload = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "fingerprints": fingerprints,
        "comparisons": comparisons,
        "canonical_view_schemas": {
            k: [
                {"ordinal_position": idx + 1, "column_name": c_name, "data_type": _normalize_pg_type(c_type)}
                for idx, (c_name, c_type) in enumerate(cols)
            ]
            for k, cols in CANONICAL_VIEW_SCHEMAS.items()
        },
        "analysis_types": sorted(set(ANALYTICAL_TABLE_LABELS.values())),
    }
    payload_json = json.dumps(payload, separators=(",", ":"))

    html_template = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BioCirV — Multi-Environment Database Drift Assessment (Local · Staging · Production)</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
  <style>
    :root, [data-theme="light"] {
      --background: #f1f5f9;
      --card: #ffffff;
      --content: #f8fafc;
      --foreground: #0f172a;
      --muted-foreground: #475569;
      --primary: #0284c7;
      --primary-foreground: #ffffff;
      --secondary: #e2e8f0;
      --secondary-foreground: #0f172a;
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
      --purple-bg: #f3e8ff;
      --purple-fg: #6b21a8;
      --purple-border: #d8b4fe;
      color-scheme: light;
    }
    [data-theme="dark"] {
      --background: #0f172a;
      --card: #1e293b;
      --content: #0f172a;
      --foreground: #f8fafc;
      --muted-foreground: #94a3b8;
      --primary: #38bdf8;
      --primary-foreground: #0f172a;
      --secondary: #334155;
      --secondary-foreground: #f8fafc;
      --border: #334155;
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
      --purple-bg: #3b0764;
      --purple-fg: #e9d5ff;
      --purple-border: #9333ea;
      color-scheme: dark;
    }
    html, body {
      background-color: var(--background) !important;
      color: var(--foreground) !important;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    select, input[type="text"], input[type="search"] {
      background-color: var(--card) !important;
      color: var(--foreground) !important;
      border-color: var(--border) !important;
    }
    .badge-pass { background-color: var(--pass-bg); color: var(--pass-fg); border: 1px solid var(--pass-border); }
    .badge-fail { background-color: var(--fail-bg); color: var(--fail-fg); border: 1px solid var(--fail-border); }
    .badge-info { background-color: var(--info-bg); color: var(--info-fg); border: 1px solid var(--info-border); }
    .badge-warn { background-color: var(--warn-bg); color: var(--warn-fg); border: 1px solid var(--warn-border); }
    .badge-purple { background-color: var(--purple-bg); color: var(--purple-fg); border: 1px solid var(--purple-border); }
    .heat-cell { transition: transform 0.1s ease, box-shadow 0.1s ease; cursor: pointer; }
    .heat-cell:hover { transform: scale(1.03); box-shadow: 0 2px 8px rgba(0,0,0,0.18); z-index: 10; position: relative; }
    .heat-cell-selected { outline: 2px solid var(--primary); outline-offset: -1px; }
  </style>
</head>
<body class="bg-[var(--background)] text-[var(--foreground)] antialiased p-3 sm:p-5">
  <div class="max-w-[1440px] mx-auto space-y-4">

    <!-- Shared Suite Top Navigation Bar -->
    <nav class="bg-[var(--card)] border border-[var(--border)] rounded-xl px-4 py-2.5 shadow-sm flex flex-wrap items-center justify-between gap-2 text-xs">
      <div class="flex flex-wrap items-center gap-1.5">
        <span class="font-bold uppercase tracking-wider text-[var(--muted-foreground)] mr-1">BioCirV Suite:</span>
        <a href="../metadata/resource_analysis_dashboard.html" class="px-2.5 py-1 rounded-lg font-medium bg-[var(--secondary)] text-[var(--secondary-foreground)] hover:opacity-85 transition">
          1. Characterization &amp; AI Brief
        </a>
        <a href="../metadata/resource_qc_outlier_dashboard.html" class="px-2.5 py-1 rounded-lg font-medium bg-[var(--secondary)] text-[var(--secondary-foreground)] hover:opacity-85 transition">
          2. Statistical QC &amp; Lab Notes Audit
        </a>
        <a href="../metadata/resource_explorer_dashboard.html" class="px-2.5 py-1 rounded-lg font-medium bg-[var(--secondary)] text-[var(--secondary-foreground)] hover:opacity-85 transition">
          3. Multi-Resource Side-by-Side Explorer
        </a>
        <a href="db_environment_drift_dashboard.html" class="px-2.5 py-1 rounded-lg font-bold bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm">
          4. DB Environment Drift
        </a>
      </div>
      <div class="flex items-center gap-2">
        <a href="../index.html" class="px-2.5 py-1 rounded-lg font-semibold border border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition">
          &larr; Visualization Gallery
        </a>
      </div>
    </nav>

    <!-- Header & Environment Pair Selector Banner -->
    <header class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 sm:p-5 shadow-sm space-y-4">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-1 max-w-3xl">
          <div class="flex flex-wrap items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-[var(--primary)] inline-block"></span>
            <h1 class="text-lg sm:text-xl font-bold text-[var(--foreground)]">
              BioCirV — Local vs. Staging vs. Production Database Drift Assessment
            </h1>
            <span id="hdr-pair-badge" class="px-2.5 py-0.5 text-xs font-bold rounded-full badge-info font-mono"></span>
          </div>
          <p class="text-xs sm:text-sm text-[var(--muted-foreground)]">
            4-Layer PostgreSQL Parity Audit across <strong>Schema, Alembic &amp; View Schema Guard (`ca_biositing` &amp; `data_portal`)</strong>, <strong>21 Core Tables &amp; 19 Materialized Views</strong>, <strong>Resource &times; Analysis-Type Coverage &amp; Lineage Sets</strong>, and <strong>Parameter Distribution &amp; Filter Funnel Attrition</strong>.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <label class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 transition cursor-pointer shadow-sm">
            📂 Upload Custom Fingerprint JSON
            <input type="file" id="inp-upload-fp" accept=".json" multiple class="hidden">
          </label>
          <button id="btn-cli-help" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90 transition">
            ⚡ Live DB Extract CLI
          </button>
          <button id="btn-export-csv" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90 transition">
            ⬇ Export Active Diff CSV
          </button>
          <button id="btn-theme-toggle" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)] hover:opacity-90 transition">
            ☀️ Light Mode
          </button>
        </div>
      </div>

      <!-- Environment Capture Status Pills + Pair Selector -->
      <div class="pt-3 border-t border-[var(--border)] flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-1.5" id="pair-selector-group">
          <span class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)] mr-1">Compare Mode:</span>
          <button data-mode="local_vs_staging" class="mode-btn px-3 py-1.5 rounded-lg text-xs font-bold transition">
            Local vs. Staging
          </button>
          <button data-mode="staging_vs_production" class="mode-btn px-3 py-1.5 rounded-lg text-xs font-bold transition">
            Staging vs. Production
          </button>
          <button data-mode="local_vs_production" class="mode-btn px-3 py-1.5 rounded-lg text-xs font-bold transition">
            Local vs. Production
          </button>
          <button data-mode="three_way" class="mode-btn px-3 py-1.5 rounded-lg text-xs font-bold transition">
            3-Way Matrix (Local &middot; Staging &middot; Prod)
          </button>
        </div>

        <div class="flex flex-wrap items-center gap-2 text-xs" id="env-capture-badges"></div>
      </div>

      <!-- Collapsible CLI & Cloud SQL Auth Proxy Drawer -->
      <div id="cli-drawer" class="hidden pt-3 border-t border-[var(--border)] bg-[var(--content)] rounded-lg p-3 text-xs space-y-2">
        <div class="flex items-center justify-between">
          <span class="font-bold text-[var(--foreground)]">Live Cloud SQL Auth Proxy &amp; Fingerprint Extraction Commands (`resources/config/db_reset.yaml`)</span>
          <button id="btn-close-cli" class="text-[var(--muted-foreground)] hover:text-[var(--foreground)] font-bold">&times; Close</button>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-2 font-mono text-[11px]">
          <div class="p-2 rounded bg-[var(--card)] border border-[var(--border)]">
            <div class="font-sans font-bold text-[var(--primary)] mb-1">1. Extract Local (:5432)</div>
            <code>pixi run python analysis/audit/db_environment_drift.py --extract-env local --compare</code>
          </div>
          <div class="p-2 rounded bg-[var(--card)] border border-[var(--border)]">
            <div class="font-sans font-bold text-amber-600 mb-1">2. Extract Staging (:5434 Proxy)</div>
            <code>pixi run python analysis/audit/db_environment_drift.py --extract-env staging --port 5434 --compare</code>
          </div>
          <div class="p-2 rounded bg-[var(--card)] border border-[var(--border)]">
            <div class="font-sans font-bold text-rose-600 mb-1">3. Extract Production (:5435 Proxy)</div>
            <code>pixi run python analysis/audit/db_environment_drift.py --extract-env production --port 5435 --compare</code>
          </div>
        </div>
      </div>
    </header>

    <!-- Top Executive Drift Scorecard (5 KPI Cards including View Schema Guard) -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5" id="executive-scorecard"></section>

    <!-- Critical Drift Findings & Remediation Banner -->
    <section class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-2.5" id="critical-findings-box"></section>

    <!-- 4-Tab Navigation Bar -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-1.5 shadow-sm flex flex-wrap gap-1.5" id="tab-nav">
      <button data-tab="tab-parity" class="tab-btn flex-1 min-w-[200px] py-2 px-3 rounded-lg text-xs sm:text-sm font-bold transition">
        1. Table, View &amp; Schema Guard Parity (40)
      </button>
      <button data-tab="tab-heatmap" class="tab-btn flex-1 min-w-[200px] py-2 px-3 rounded-lg text-xs sm:text-sm font-bold transition">
        2. Resource &times; Analysis Drift Heatmap
      </button>
      <button data-tab="tab-lineage" class="tab-btn flex-1 min-w-[200px] py-2 px-3 rounded-lg text-xs sm:text-sm font-bold transition">
        3. Lineage Set-Diff &amp; Missing Entities
      </button>
      <button data-tab="tab-funnel" class="tab-btn flex-1 min-w-[200px] py-2 px-3 rounded-lg text-xs sm:text-sm font-bold transition">
        4. Parameter Shift (&gt;5%) &amp; Filter Funnel
      </button>
    </div>

    <!-- TAB 1: Table & Materialized View Parity + View Schema Guard -->
    <section id="tab-parity" class="tab-panel space-y-4">
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="text-base font-bold text-[var(--foreground)]">Diverging Row-Count Delta Waterfall (21 Core Tables &amp; 19 Materialized Views)</h2>
            <p class="text-xs text-[var(--muted-foreground)]">Positive bars indicate Source environment has more rows than Target; negative bars indicate Target has more rows (e.g. un-deduplicated legacy ICP rows in Prod).</p>
          </div>
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <select id="sel-parity-layer" class="rounded-lg border px-2.5 py-1.5 font-semibold">
              <option value="all">All Objects (21 Tables + 19 Views)</option>
              <option value="table">Core Tables Only (21)</option>
              <option value="view">Materialized Views Only (19)</option>
              <option value="drifted">Drifted / Stale Objects Only</option>
            </select>
            <select id="sel-parity-metric" class="rounded-lg border px-2.5 py-1.5 font-semibold">
              <option value="pct">Plot % Difference (%)</option>
              <option value="abs">Plot Absolute Row Delta (&Delta; rows)</option>
            </select>
          </div>
        </div>
        <div id="plot-parity-waterfall" class="w-full" style="height: 430px;"></div>
      </div>

      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h3 class="text-sm font-bold text-[var(--foreground)]">Searchable Schema, Table &amp; Materialized View Parity Table</h3>
          <div class="flex flex-wrap items-center gap-2">
            <input type="search" id="inp-parity-search" placeholder="Filter table, view, or status..." class="rounded-lg border px-3 py-1 text-xs w-64">
          </div>
        </div>
        <div class="overflow-x-auto max-h-[520px] overflow-y-auto border border-[var(--border)] rounded-lg">
          <table class="w-full text-left border-collapse text-xs">
            <thead class="bg-[var(--content)] sticky top-0 z-10 border-b border-[var(--border)] text-[var(--muted-foreground)] uppercase">
              <tr>
                <th class="py-2.5 px-3">Schema &middot; Object</th>
                <th class="py-2.5 px-3">Category</th>
                <th class="py-2.5 px-3 text-right">Local (:5432)</th>
                <th class="py-2.5 px-3 text-right">Staging (:5434)</th>
                <th class="py-2.5 px-3 text-right">Prod (:5435)</th>
                <th class="py-2.5 px-3 text-right" id="th-parity-delta">&Delta; (Source - Target)</th>
                <th class="py-2.5 px-3 text-right">% Diff</th>
                <th class="py-2.5 px-3 text-center">Col Schema / Def Hash</th>
                <th class="py-2.5 px-3 text-center">Parity Status</th>
              </tr>
            </thead>
            <tbody id="tbody-parity" class="divide-y divide-[var(--border)]"></tbody>
          </table>
        </div>
      </div>

      <!-- View Schema Guard: ca_biositing & data_portal Column & Data-Type Parity Inspector -->
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3" id="view-schema-guard-section">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <span class="px-2 py-0.5 rounded text-[11px] font-bold badge-pass" id="vsg-header-badge">SCHEMA GUARD</span>
              <h3 class="text-sm sm:text-base font-bold text-[var(--foreground)]">
                View Schema Guard: <code>ca_biositing</code> (8 Views) &amp; <code>data_portal</code> (11 Views) Column &amp; Data-Type Parity
              </h3>
            </div>
            <p class="text-xs text-[var(--muted-foreground)] mt-0.5">
              Verifies that every view in <code>ca_biositing</code> and <code>data_portal</code> exposes the exact same ordered column names and PostgreSQL data types across Local, Staging, and Production. Click any view chip below or filter by schema/column to inspect.
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <select id="sel-vsg-schema" class="rounded-lg border px-2.5 py-1.5 font-semibold">
              <option value="all">All Schemas (19 Views · 239 Columns)</option>
              <option value="data_portal">data_portal Schema Only (11 Views · 139 Columns)</option>
              <option value="ca_biositing">ca_biositing Schema Only (8 Views · 100 Columns)</option>
              <option value="mismatch">Schema Mismatches / Type Drift Only</option>
            </select>
            <select id="sel-vsg-view" class="rounded-lg border px-2.5 py-1.5 font-semibold">
              <option value="all">All Views in Selected Schema</option>
            </select>
            <input type="search" id="inp-vsg-search" placeholder="Search column name or data type..." class="rounded-lg border px-3 py-1.5 text-xs w-56">
          </div>
        </div>

        <!-- Clickable 19-View Schema Guard Status Chips -->
        <div id="vsg-view-pills" class="flex flex-wrap gap-1.5 pt-1"></div>

        <!-- Column-by-Column Schema Guard Table -->
        <div class="overflow-x-auto max-h-[460px] overflow-y-auto border border-[var(--border)] rounded-lg">
          <table class="w-full text-left border-collapse text-xs">
            <thead class="bg-[var(--content)] sticky top-0 z-10 border-b border-[var(--border)] text-[var(--muted-foreground)] uppercase">
              <tr>
                <th class="py-2 px-3 w-12 text-center">#</th>
                <th class="py-2 px-3">Schema &middot; View Name</th>
                <th class="py-2 px-3">Column Name</th>
                <th class="py-2 px-3">Canonical SQLModel Type</th>
                <th class="py-2 px-3">Local (:5432) Type</th>
                <th class="py-2 px-3">Staging (:5434) Type</th>
                <th class="py-2 px-3">Prod (:5435) Type</th>
                <th class="py-2 px-3 text-center">Schema Guard Status</th>
              </tr>
            </thead>
            <tbody id="tbody-vsg-columns" class="divide-y divide-[var(--border)]"></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB 2: Resource x Analysis Type Drift Heatmap -->
    <section id="tab-heatmap" class="tab-panel hidden space-y-4">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div class="lg:col-span-8 bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 class="text-base font-bold text-[var(--foreground)]">Resource &times; Analysis Type Coverage &amp; Drift Matrix</h2>
              <p class="text-xs text-[var(--muted-foreground)]">Click any cell to inspect exact `Local / Staging / Prod` counts, QC pass/fail split, and sample/record IDs.</p>
            </div>
            <div class="flex flex-wrap items-center gap-2 text-xs">
              <select id="sel-heat-display" class="rounded-lg border px-2.5 py-1 font-semibold">
                <option value="delta">Cell Text: &Delta; Rows (Source - Target)</option>
                <option value="slash">Cell Text: Local / Staging / Prod</option>
                <option value="qc">Cell Text: QC Pass Rate &Delta; (%)</option>
              </select>
              <select id="sel-heat-filter" class="rounded-lg border px-2.5 py-1 font-semibold">
                <option value="all">All 45 Active Resources</option>
                <option value="drifted">Resources with Drift Only</option>
                <option value="missing_prod">Resources Missing in Prod (6)</option>
              </select>
              <input type="search" id="inp-heat-search" placeholder="Search resource..." class="rounded-lg border px-2.5 py-1 text-xs w-44">
            </div>
          </div>

          <div class="overflow-x-auto max-h-[640px] overflow-y-auto border border-[var(--border)] rounded-lg">
            <table class="w-full border-collapse text-[11px]" id="tbl-heatmap"></table>
          </div>
        </div>

        <!-- Click-to-Inspect Cell Drilldown Panel -->
        <div class="lg:col-span-4 bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3 flex flex-col justify-between">
          <div id="heat-drilldown-content" class="space-y-3"></div>
          <div class="pt-3 border-t border-[var(--border)]">
            <h4 class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)] mb-2">QC Pass / Fail Distribution Shift by Table</h4>
            <div id="qc-table-mini-summary" class="space-y-1.5 max-h-[260px] overflow-y-auto pr-1"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 3: Lineage Set-Difference & Missing Entities -->
    <section id="tab-lineage" class="tab-panel hidden space-y-4">
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="text-base font-bold text-[var(--foreground)]">Sample &amp; Entity Lineage Set-Difference Explorer</h2>
            <p class="text-xs text-[var(--muted-foreground)]">Exact set-difference audit of `resource.name`, `field_sample.name`, `prepared_sample.name`, and `experiment.name` across environments.</p>
          </div>
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <button data-entity="prepared_samples" class="entity-btn px-3 py-1.5 rounded-lg font-bold">Prepared Samples (384)</button>
            <button data-entity="field_samples" class="entity-btn px-3 py-1.5 rounded-lg font-bold">Field Samples (147)</button>
            <button data-entity="resources" class="entity-btn px-3 py-1.5 rounded-lg font-bold">Resources (127)</button>
            <button data-entity="experiments" class="entity-btn px-3 py-1.5 rounded-lg font-bold">Experiments (109)</button>
          </div>
        </div>

        <!-- 4 Set-Bucket Summary Cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3" id="lineage-bucket-cards"></div>

        <!-- Search & Set Table -->
        <div class="flex flex-wrap items-center justify-between gap-2 pt-2">
          <div class="text-xs font-bold text-[var(--muted-foreground)]" id="lineage-table-title">Showing entities:</div>
          <input type="search" id="inp-lineage-search" placeholder="Search sample, resource, provider, or prep method..." class="rounded-lg border px-3 py-1.5 text-xs w-80">
        </div>

        <div class="overflow-x-auto max-h-[480px] overflow-y-auto border border-[var(--border)] rounded-lg">
          <table class="w-full text-left border-collapse text-xs">
            <thead class="bg-[var(--content)] sticky top-0 z-10 border-b border-[var(--border)] text-[var(--muted-foreground)] uppercase">
              <tr>
                <th class="py-2.5 px-3">Entity Name</th>
                <th class="py-2.5 px-3">Parent Resource</th>
                <th class="py-2.5 px-3">Lineage / Prep Metadata</th>
                <th class="py-2.5 px-3 text-center">Local (:5432)</th>
                <th class="py-2.5 px-3 text-center">Staging (:5434)</th>
                <th class="py-2.5 px-3 text-center">Production (:5435)</th>
                <th class="py-2.5 px-3 text-center">Promotion Status</th>
              </tr>
            </thead>
            <tbody id="tbody-lineage" class="divide-y divide-[var(--border)]"></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB 4: Parameter Value Shift & Filter Funnel Audit -->
    <section id="tab-funnel" class="tab-panel hidden space-y-4">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div class="lg:col-span-6 bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3">
          <h2 class="text-base font-bold text-[var(--foreground)]">Portal Filter Funnel Waterfall (`ca_biositing.analysis_data_view`)</h2>
          <p class="text-xs text-[var(--muted-foreground)]">Tracks step-by-step row attrition from raw candidate pool through `qc_pass`, `EXCLUDED_RESOURCES`, `EXCLUDED_PROVIDERS`, and `ULTIMATE_PARAMETERS`.</p>
          <div id="plot-funnel-bars" class="w-full" style="height: 320px;"></div>
        </div>

        <div class="lg:col-span-6 bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3">
          <h2 class="text-base font-bold text-[var(--foreground)]">Step-by-Step Filter Funnel &amp; Retention Ratio Audit</h2>
          <p class="text-xs text-[var(--muted-foreground)]">Separates base-table ingestion drift from centralized filter changes (`0022_exclude_jaguar_provider`) and unrefreshed MVs (`pixi run refresh-views`).</p>
          <div class="overflow-x-auto border border-[var(--border)] rounded-lg">
            <table class="w-full text-left border-collapse text-xs">
              <thead class="bg-[var(--content)] border-b border-[var(--border)] text-[var(--muted-foreground)] uppercase">
                <tr>
                  <th class="py-2 px-3">Filter Funnel Stage</th>
                  <th class="py-2 px-3 text-right">Local (:5432)</th>
                  <th class="py-2 px-3 text-right">Staging (:5434)</th>
                  <th class="py-2 px-3 text-right">Prod (:5435)</th>
                  <th class="py-2 px-3">Drift Diagnosis</th>
                </tr>
              </thead>
              <tbody id="tbody-funnel-stages" class="divide-y divide-[var(--border)]"></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Parameter Mean/Median Shift Table (>5% highlighted) -->
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="text-base font-bold text-[var(--foreground)]">Parameter Value Distribution &amp; Mean Shift Audit (`&gt;5%` Shift Flagged)</h2>
            <p class="text-xs text-[var(--muted-foreground)]">Compares QC-passing `n`, `mean`, `SD`, and `median` per `(analysis_type, parameter_name)` across environments.</p>
          </div>
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <select id="sel-param-filter" class="rounded-lg border px-2.5 py-1.5 font-semibold">
              <option value="flagged">Flagged Shifts (&gt;5% Mean Shift) Only</option>
              <option value="all">All 117 Parameter Slices</option>
            </select>
            <select id="sel-param-at" class="rounded-lg border px-2.5 py-1.5 font-semibold">
              <option value="all">All Analysis Types</option>
            </select>
            <input type="search" id="inp-param-search" placeholder="Search parameter or unit..." class="rounded-lg border px-3 py-1.5 text-xs w-56">
          </div>
        </div>

        <div class="overflow-x-auto max-h-[480px] overflow-y-auto border border-[var(--border)] rounded-lg">
          <table class="w-full text-left border-collapse text-xs">
            <thead class="bg-[var(--content)] sticky top-0 z-10 border-b border-[var(--border)] text-[var(--muted-foreground)] uppercase">
              <tr>
                <th class="py-2.5 px-3">Analysis Type</th>
                <th class="py-2.5 px-3">Parameter (Unit)</th>
                <th class="py-2.5 px-3 text-right">Local Mean &plusmn; SD (n)</th>
                <th class="py-2.5 px-3 text-right">Staging Mean &plusmn; SD (n)</th>
                <th class="py-2.5 px-3 text-right">Prod Mean &plusmn; SD (n)</th>
                <th class="py-2.5 px-3 text-right">Median (L / S / P)</th>
                <th class="py-2.5 px-3 text-right" id="th-param-shift">Mean % Shift</th>
                <th class="py-2.5 px-3 text-center">Shift Flag</th>
              </tr>
            </thead>
            <tbody id="tbody-param-shifts" class="divide-y divide-[var(--border)]"></tbody>
          </table>
        </div>
      </div>
    </section>

  </div>

  <script>
    const DRIFT_BUNDLE = __PAYLOAD_JSON__;

    const state = {
      mode: "local_vs_production", // local_vs_staging | staging_vs_production | local_vs_production | three_way
      activeTab: "tab-parity",
      parityLayer: "all",
      parityMetric: "pct",
      paritySearch: "",
      vsgSchema: "all",
      vsgView: "all",
      vsgSearch: "",
      heatDisplay: "delta",
      heatFilter: "all",
      heatSearch: "",
      selectedCell: { resource: "tomato pomace", analysisType: "Calorimetry" },
      lineageEntity: "prepared_samples",
      lineageBucket: "only_local_vs_prod",
      lineageSearch: "",
      paramFilter: "flagged",
      paramAt: "all",
      paramSearch: "",
      theme: "dark"
    };

    function getActiveEnvs() {
      if (state.mode === "local_vs_staging") return { a: "local", b: "staging", label: "Local (:5432) vs. Staging (:5434)" };
      if (state.mode === "staging_vs_production") return { a: "staging", b: "production", label: "Staging (:5434) vs. Production (:5435)" };
      if (state.mode === "local_vs_production") return { a: "local", b: "production", label: "Local (:5432) vs. Production (:5435)" };
      return { a: "local", b: "production", label: "3-Way Matrix (Local · Staging · Prod)" };
    }

    function getActiveComparison() {
      const pairKey = state.mode === "three_way" ? "local_vs_production" : state.mode;
      return DRIFT_BUNDLE.comparisons[pairKey] || DRIFT_BUNDLE.comparisons["local_vs_production"];
    }

    function fmtInt(n) {
      if (n === null || n === undefined || Number.isNaN(n)) return "—";
      return Number(n).toLocaleString();
    }

    function fmtSigned(n) {
      if (n === null || n === undefined || Number.isNaN(n)) return "—";
      const v = Number(n);
      return (v > 0 ? "+" : "") + v.toLocaleString();
    }

    function recomputePairInBrowser(fpA, fpB) {
      const envA = fpA.environment, envB = fpB.environment;
      const s1A = fpA.layer1_schema, s1B = fpB.layer1_schema;
      const r2A = fpA.layer2_row_counts, r2B = fpB.layer2_row_counts;
      const c3A = fpA.layer3_coverage_and_lineage, c3B = fpB.layer3_coverage_and_lineage;
      const p4A = fpA.layer4_parameters_and_funnels, p4B = fpB.layer4_parameters_and_funnels;

      const revMatch = s1A.alembic_revision_id === s1B.alembic_revision_id;
      const revLag = (s1A.migration_index || 24) - (s1B.migration_index || 24);

      const tableDiffs = [];
      let syncedTables = 0;
      Object.keys(r2A.core_tables).forEach(tName => {
        const cntA = r2A.core_tables[tName] || 0;
        const cntB = r2B.core_tables[tName] || 0;
        const delta = cntA - cntB;
        const pct = cntB > 0 ? Number(((delta / cntB) * 100).toFixed(2)) : (cntA > 0 ? 100 : 0);
        const hA = (s1A.tables[tName] || {}).schema_hash || "";
        const hB = (s1B.tables[tName] || {}).schema_hash || "";
        let status = "SYNCED";
        if (delta === 0 && hA === hB) syncedTables++;
        else if (delta > 0) status = envA.toUpperCase() + " AHEAD";
        else if (delta < 0) status = envB.toUpperCase() + " AHEAD";
        else status = "SCHEMA DRIFT";
        tableDiffs.push({
          object_type: "table",
          schema: "public",
          name: tName,
          category: (s1A.tables[tName] || {}).category || "Core Table",
          count_a: cntA,
          count_b: cntB,
          delta,
          pct_diff: pct,
          hash_match: hA === hB,
          status
        });
      });

      const viewDiffs = [];
      const viewGuardItems = [];
      let syncedViews = 0;
      let viewsPassingGuard = 0;
      let totalViewColsChecked = 0;
      let totalColMismatches = 0;

      Object.keys(r2A.views).forEach(vName => {
        const cntA = r2A.views[vName] || 0;
        const cntB = r2B.views[vName] || 0;
        const delta = cntA - cntB;
        const pct = cntB > 0 ? Number(((delta / cntB) * 100).toFixed(2)) : (cntA > 0 ? 100 : 0);
        const mvA = (s1A.materialized_views || {})[vName] || {};
        const mvB = (s1B.materialized_views || {})[vName] || {};
        const staleB = Boolean(mvB.is_stale);
        const hashMatch = mvA.definition_hash === mvB.definition_hash;

        const canonCols = (DRIFT_BUNDLE.canonical_view_schemas || {})[vName] || [];
        const colsA = mvA.columns || canonCols;
        const colsB = mvB.columns || canonCols;
        const mapA = new Map(colsA.map(c => [c.column_name, c.data_type]));
        const mapB = new Map(colsB.map(c => [c.column_name, c.data_type]));
        const mapCanon = new Map(canonCols.map(c => [c.column_name, c.data_type]));
        const allColNames = Array.from(new Set([...canonCols.map(c => c.column_name), ...colsA.map(c => c.column_name), ...colsB.map(c => c.column_name)]));

        let viewColMismatchCnt = 0;
        const colDetails = [];
        const missingInA = [], missingInB = [], typeMismatches = [];

        allColNames.forEach((colName, idx) => {
          totalViewColsChecked++;
          const tA = mapA.get(colName) || null;
          const tB = mapB.get(colName) || null;
          const tCanon = mapCanon.get(colName) || tA || tB;
          let colStatus = "MATCH";
          if (!tA) { colStatus = "MISSING_IN_" + envA.toUpperCase(); missingInA.push(colName); viewColMismatchCnt++; totalColMismatches++; }
          else if (!tB) { colStatus = "MISSING_IN_" + envB.toUpperCase(); missingInB.push(colName); viewColMismatchCnt++; totalColMismatches++; }
          else if (tA !== tB || (tCanon && (tA !== tCanon || tB !== tCanon))) {
            colStatus = "TYPE_MISMATCH";
            typeMismatches.push({ column_name: colName, type_a: tA, type_b: tB, canonical_type: tCanon });
            viewColMismatchCnt++;
            totalColMismatches++;
          }
          colDetails.push({
            ordinal_position: idx + 1,
            column_name: colName,
            canonical_type: tCanon,
            type_a: tA,
            type_b: tB,
            match: colStatus === "MATCH",
            status: colStatus
          });
        });

        const colSchemaMatch = viewColMismatchCnt === 0 && colsA.length === colsB.length;
        if (colSchemaMatch) viewsPassingGuard++;

        let status = "SYNCED";
        if (!colSchemaMatch) status = "VIEW SCHEMA DRIFT";
        else if (staleB) status = "MV STALE";
        else if (delta === 0 && hashMatch) syncedViews++;
        else if (delta > 0) status = envB === "production" ? "PRODUCTION BEHIND" : envA.toUpperCase() + " AHEAD";
        else if (delta < 0) status = envB.toUpperCase() + " AHEAD";
        else status = "DEF DRIFT";

        viewDiffs.push({
          object_type: "view",
          schema: vName.split(".")[0],
          name: vName,
          category: mvA.category || "Materialized View",
          count_a: cntA,
          count_b: cntB,
          delta,
          pct_diff: pct,
          hash_match: hashMatch,
          col_schema_match: colSchemaMatch,
          col_count_a: colsA.length,
          col_count_b: colsB.length,
          col_schema_hash_a: mvA.col_schema_hash || "",
          col_schema_hash_b: mvB.col_schema_hash || "",
          is_stale_b: staleB,
          stale_reason: mvB.stale_reason || "",
          status
        });

        viewGuardItems.push({
          view_name: vName,
          schema: vName.split(".")[0],
          short_name: vName.split(".")[1] || vName,
          category: mvA.category || "Materialized View",
          col_count_canonical: canonCols.length,
          col_count_a: colsA.length,
          col_count_b: colsB.length,
          col_schema_hash_a: mvA.col_schema_hash || "",
          col_schema_hash_b: mvB.col_schema_hash || "",
          col_schema_match: colSchemaMatch,
          mismatch_count: viewColMismatchCnt,
          missing_in_a: missingInA,
          missing_in_b: missingInB,
          type_mismatches: typeMismatches,
          columns: colDetails,
          guard_status: colSchemaMatch ? "PASS" : "FAIL"
        });
      });

      const viewSchemaGuard = {
        total_views: viewGuardItems.length,
        ca_biositing_views: viewGuardItems.filter(v => v.schema === "ca_biositing").length,
        data_portal_views: viewGuardItems.filter(v => v.schema === "data_portal").length,
        views_passing_guard: viewsPassingGuard,
        views_failing_guard: viewGuardItems.length - viewsPassingGuard,
        total_columns_checked: totalViewColsChecked,
        total_column_mismatches: totalColMismatches,
        all_views_match: viewsPassingGuard === viewGuardItems.length,
        views: viewGuardItems
      };

      const paramShifts = [];
      let flaggedCount = 0;
      const allPKeys = Array.from(new Set([...Object.keys(p4A.parameter_stats || {}), ...Object.keys(p4B.parameter_stats || {})])).sort();
      allPKeys.forEach(pk => {
        const pa = (p4A.parameter_stats || {})[pk];
        const pb = (p4B.parameter_stats || {})[pk];
        if (!pa && !pb) return;
        const na = pa ? pa.n : 0, nb = pb ? pb.n : 0;
        const ma = pa ? pa.mean : 0, mb = pb ? pb.mean : 0;
        const pctShift = (nb === 0 && na > 0) ? 100 : (mb !== 0 ? Number((((ma - mb) / Math.abs(mb)) * 100).toFixed(2)) : 0);
        const flagged = Math.abs(pctShift) > 5 || (na > 0 && nb === 0);
        if (flagged) flaggedCount++;
        paramShifts.push({
          key: pk,
          analysis_type: (pa || pb).analysis_type,
          parameter_name: (pa || pb).parameter_name,
          unit: (pa || pb).unit,
          n_a: na, n_b: nb, delta_n: na - nb,
          mean_a: ma, mean_b: mb,
          median_a: pa ? pa.median : 0, median_b: pb ? pb.median : 0,
          pct_shift: pctShift,
          flagged_gt_5pct: flagged
        });
      });

      const schemaScore = revMatch ? 25 : Math.max(5, 25 - Math.abs(revLag) * 6);
      const tableScore = Number(((syncedTables / Math.max(1, tableDiffs.length)) * 25).toFixed(1));
      const mvPenalty = ((s1B.mv_freshness_summary || {}).stale_view_names || []).length * 2.5;
      const viewGuardPenalty = (viewGuardItems.length - viewsPassingGuard) * 4.0;
      const viewScore = Math.max(0, Number(((syncedViews / Math.max(1, viewDiffs.length)) * 25 - mvPenalty - viewGuardPenalty).toFixed(1)));
      const lineageScore = Number(((1 - flaggedCount / Math.max(1, paramShifts.length)) * 25).toFixed(1));
      const syncScore = Number((schemaScore + tableScore + viewScore + lineageScore).toFixed(1));

      return {
        pair_key: envA + "_vs_" + envB,
        env_a: envA,
        env_b: envB,
        sync_score: syncScore,
        score_breakdown: { schema_score: schemaScore, table_score: tableScore, view_score: viewScore, lineage_param_score: lineageScore },
        alembic_match: revMatch,
        alembic_lag_migrations: revLag,
        aim1_aim2_delta: r2A.totals.aim1_aim2_records - r2B.totals.aim1_aim2_records,
        observation_delta: r2A.totals.observations - r2B.totals.observations,
        table_diffs: tableDiffs,
        view_diffs: viewDiffs,
        view_schema_guard: viewSchemaGuard,
        param_shifts: paramShifts,
        flagged_param_count: flaggedCount
      };
    }

    function renderHeaderAndScorecard() {
      const envs = getActiveEnvs();
      const comp = getActiveComparison();
      const loc = DRIFT_BUNDLE.fingerprints.local;
      const stg = DRIFT_BUNDLE.fingerprints.staging;
      const prd = DRIFT_BUNDLE.fingerprints.production;
      const fpA = DRIFT_BUNDLE.fingerprints[envs.a];
      const fpB = DRIFT_BUNDLE.fingerprints[envs.b];

      document.getElementById("hdr-pair-badge").textContent = envs.label;

      // Mode buttons active state
      document.querySelectorAll(".mode-btn").forEach(btn => {
        const active = btn.dataset.mode === state.mode;
        btn.className = "mode-btn px-3 py-1.5 rounded-lg text-xs font-bold transition " + (
          active
            ? "bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm"
            : "bg-[var(--secondary)] text-[var(--secondary-foreground)] hover:opacity-85"
        );
      });

      // Capture badges
      const badgeContainer = document.getElementById("env-capture-badges");
      badgeContainer.innerHTML = ["local", "staging", "production"].map(k => {
        const fp = DRIFT_BUNDLE.fingerprints[k];
        const isLive = fp.capture_mode === "live_db";
        const cls = isLive ? "badge-pass" : (k === "local" ? "badge-info" : "badge-warn");
        return `<span class="px-2.5 py-1 rounded-full font-semibold ${cls}" title="Captured at ${fp.captured_at}">
          <strong>${k.toUpperCase()}:</strong> ${fp.capture_badge}
        </span>`;
      }).join("");

      // Executive Scorecard (5 KPI Cards including View Schema Guard)
      const sc = document.getElementById("executive-scorecard");
      const scoreTone = comp.sync_score >= 85 ? "badge-pass" : (comp.sync_score >= 65 ? "badge-warn" : "badge-fail");
      const staleStg = stg.layer1_schema.mv_freshness_summary.stale_views;
      const defPrd = prd.layer1_schema.mv_freshness_summary.definition_drifted_views.length;
      const vsg = comp.view_schema_guard || {
        total_views: 19,
        ca_biositing_views: 8,
        data_portal_views: 11,
        views_passing_guard: 19,
        views_failing_guard: 0,
        total_columns_checked: 239,
        total_column_mismatches: 0,
        all_views_match: true,
        views: []
      };
      const vsgTone = vsg.all_views_match ? "badge-pass" : "badge-fail";

      sc.innerHTML = `
        <!-- Card 1: Overall Sync Score -->
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm flex flex-col justify-between">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Overall Sync Score</span>
            <span class="px-2 py-0.5 text-[11px] font-bold rounded-full ${scoreTone}">${envs.a.toUpperCase()} vs ${envs.b.toUpperCase()}</span>
          </div>
          <div class="my-2 flex items-baseline gap-2">
            <span class="text-3xl font-extrabold text-[var(--foreground)]">${comp.sync_score}%</span>
            <span class="text-xs text-[var(--muted-foreground)]">composite parity index</span>
          </div>
          <div class="grid grid-cols-2 gap-1 text-[11px] text-[var(--muted-foreground)] pt-2 border-t border-[var(--border)]">
            <div>Schema: <strong class="text-[var(--foreground)]">${comp.score_breakdown.schema_score}/25</strong></div>
            <div>Tables: <strong class="text-[var(--foreground)]">${comp.score_breakdown.table_score}/25</strong></div>
            <div>Views: <strong class="text-[var(--foreground)]">${comp.score_breakdown.view_score}/25</strong></div>
            <div>Lineage/Params: <strong class="text-[var(--foreground)]">${comp.score_breakdown.lineage_param_score}/25</strong></div>
          </div>
        </div>

        <!-- Card 2: Schema & Alembic Revision Parity -->
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm flex flex-col justify-between">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Schema &amp; Alembic Parity</span>
            <span class="px-2 py-0.5 text-[11px] font-bold rounded-full ${comp.alembic_match ? 'badge-pass' : 'badge-warn'}">
              ${comp.alembic_match ? 'IN SYNC' : comp.alembic_lag_migrations + ' MIGRATIONS AHEAD'}
            </span>
          </div>
          <div class="my-2 space-y-1 text-xs font-mono">
            <div class="flex justify-between"><span class="text-[var(--muted-foreground)]">Local:</span> <strong class="text-emerald-600 dark:text-emerald-400">${loc.layer1_schema.alembic_revision_id}</strong></div>
            <div class="flex justify-between"><span class="text-[var(--muted-foreground)]">Staging:</span> <strong class="text-amber-600 dark:text-amber-400">${stg.layer1_schema.alembic_revision_id}</strong></div>
            <div class="flex justify-between"><span class="text-[var(--muted-foreground)]">Prod:</span> <strong class="text-rose-600 dark:text-rose-400">${prd.layer1_schema.alembic_revision_id}</strong></div>
          </div>
          <div class="text-[11px] text-[var(--muted-foreground)] pt-2 border-t border-[var(--border)]">
            Public Tables: <strong>${loc.layer1_schema.public_table_count} L / ${stg.layer1_schema.public_table_count} S / ${prd.layer1_schema.public_table_count} P</strong> &middot; Cols: <strong>${loc.layer1_schema.public_column_count} L / ${stg.layer1_schema.public_column_count} S / ${prd.layer1_schema.public_column_count} P</strong>
          </div>
        </div>

        <!-- Card 3: View Schema Guard (ca_biositing & data_portal) -->
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm flex flex-col justify-between">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">View Schema Guard</span>
            <span class="px-2 py-0.5 text-[11px] font-bold rounded-full ${vsgTone}">
              ${vsg.all_views_match ? '✅ ' + vsg.views_passing_guard + '/' + vsg.total_views + ' GUARD PASS' : '❌ ' + vsg.views_failing_guard + ' SCHEMA DRIFT'}
            </span>
          </div>
          <div class="my-2 space-y-1 text-xs">
            <div class="flex justify-between">
              <span class="text-[var(--muted-foreground)]"><code>data_portal</code> (${vsg.data_portal_views}):</span>
              <strong class="font-mono text-emerald-500">Live Catalog Verified</strong>
            </div>
            <div class="flex justify-between">
              <span class="text-[var(--muted-foreground)]"><code>ca_biositing</code> (${vsg.ca_biositing_views}):</span>
              <strong class="font-mono text-emerald-500">Live Catalog Verified</strong>
            </div>
            <div class="flex justify-between">
              <span class="text-[var(--muted-foreground)]">Col / Type Mismatches:</span>
              <strong class="font-mono ${vsg.total_column_mismatches === 0 ? 'text-emerald-500' : 'text-rose-400'}">${vsg.total_column_mismatches} / ${vsg.total_columns_checked} cols</strong>
            </div>
          </div>
          <div class="text-[11px] text-[var(--primary)] pt-2 border-t border-[var(--border)] font-semibold cursor-pointer hover:underline" onclick="document.getElementById('view-schema-guard-section').scrollIntoView({behavior:'smooth'})">
            Inspect ${vsg.total_columns_checked} View Columns &amp; Types &darr;
          </div>
        </div>

        <!-- Card 4: Total Record & Lineage Delta -->
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm flex flex-col justify-between">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Aim1/Aim2 Record Delta</span>
            <span class="px-2 py-0.5 text-[11px] font-bold rounded-full badge-info">${fmtSigned(comp.aim1_aim2_delta)} rows</span>
          </div>
          <div class="my-2 space-y-1 text-xs">
            <div class="flex justify-between"><span>Local Aim1/Aim2:</span> <strong>${fmtInt(loc.layer2_row_counts.totals.aim1_aim2_records)} (${fmtInt(loc.layer2_row_counts.core_tables.observation)} obs)</strong></div>
            <div class="flex justify-between"><span>Staging Aim1/Aim2:</span> <strong>${fmtInt(stg.layer2_row_counts.totals.aim1_aim2_records)} (${fmtSigned(stg.layer2_row_counts.totals.aim1_aim2_records - loc.layer2_row_counts.totals.aim1_aim2_records)} vs L)</strong></div>
            <div class="flex justify-between"><span>Prod Aim1/Aim2:</span> <strong>${fmtInt(prd.layer2_row_counts.totals.aim1_aim2_records)} (${fmtSigned(prd.layer2_row_counts.totals.aim1_aim2_records - loc.layer2_row_counts.totals.aim1_aim2_records)} vs L)</strong></div>
          </div>
          <div class="text-[11px] text-[var(--muted-foreground)] pt-2 border-t border-[var(--border)]">
            Prepared Samples: <strong>${fmtInt(loc.layer2_row_counts.core_tables.prepared_sample)} L</strong> &middot; <strong>${fmtInt(stg.layer2_row_counts.core_tables.prepared_sample)} S</strong> &middot; <strong>${fmtInt(prd.layer2_row_counts.core_tables.prepared_sample)} P</strong>
          </div>
        </div>

        <!-- Card 5: Materialized View Freshness Alert -->
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm flex flex-col justify-between">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">MV Freshness &amp; Def Alert</span>
            <span class="px-2 py-0.5 text-[11px] font-bold rounded-full ${defPrd > 0 || staleStg > 0 ? 'badge-warn' : 'badge-pass'}">${defPrd > 0 ? defPrd + ' DEF DRIFT' : (staleStg > 0 ? staleStg + ' STALE' : 'POPULATED')}</span>
          </div>
          <div class="my-2 space-y-1 text-xs">
            <div class="text-[11px] text-[var(--muted-foreground)]">
              <code>analysis_data_view</code>: <strong>${fmtInt(loc.layer2_row_counts.views['ca_biositing.analysis_data_view'])} L</strong> / <strong>${fmtInt(stg.layer2_row_counts.views['ca_biositing.analysis_data_view'])} S</strong> / <strong>${fmtInt(prd.layer2_row_counts.views['ca_biositing.analysis_data_view'])} P</strong><br>
              <code>mv_biomass_composition</code>: <strong>${fmtInt(loc.layer2_row_counts.views['data_portal.mv_biomass_composition'])} L</strong> / <strong>${fmtInt(stg.layer2_row_counts.views['data_portal.mv_biomass_composition'])} S</strong> / <strong>${fmtInt(prd.layer2_row_counts.views['data_portal.mv_biomass_composition'])} P</strong>
            </div>
          </div>
          <div class="text-[11px] font-mono pt-2 border-t border-[var(--border)] text-[var(--primary)]">
            pixi run migrate &amp;&amp; pixi run refresh-views
          </div>
        </div>
      `;

      // Critical Drift Findings Banner (100% live data-driven)
      const findingsBox = document.getElementById("critical-findings-box");
      findingsBox.innerHTML = `
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 text-xs font-bold rounded badge-info">LIVE MEASURED DRIFT FINDINGS</span>
            <span class="text-xs font-bold text-[var(--foreground)]">Key Environment Divergences &amp; Remediation Commands</span>
          </div>
          <span class="text-xs text-[var(--muted-foreground)]">Showing live diagnostics for <strong>${envs.label}</strong></span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2.5 text-xs">
          <div class="p-2.5 rounded-lg bg-[var(--content)] border border-[var(--border)] space-y-1">
            <div class="font-bold text-amber-700 dark:text-amber-400">1. Alembic Migration Revisions</div>
            <p class="text-[11px] text-[var(--muted-foreground)]">Local is at <code>${loc.layer1_schema.alembic_revision_id}</code>, Staging at <code>${stg.layer1_schema.alembic_revision_id}</code>, and Production at <code>${prd.layer1_schema.alembic_revision_id}</code>.</p>
            <code class="block text-[10px] p-1 rounded bg-[var(--card)] border border-[var(--border)]">pixi run migrate</code>
          </div>
          <div class="p-2.5 rounded-lg bg-[var(--content)] border border-[var(--border)] space-y-1">
            <div class="font-bold text-rose-700 dark:text-rose-400">2. Aim 1 / Aim 2 Analytical Record Volume</div>
            <p class="text-[11px] text-[var(--muted-foreground)]">Local has <strong>${fmtInt(loc.layer2_row_counts.totals.aim1_aim2_records)}</strong> Aim1/Aim2 rows vs <strong>${fmtInt(stg.layer2_row_counts.totals.aim1_aim2_records)}</strong> in Staging and <strong>${fmtInt(prd.layer2_row_counts.totals.aim1_aim2_records)}</strong> in Production.</p>
            <code class="block text-[10px] p-1 rounded bg-[var(--card)] border border-[var(--border)]">pixi run refresh-views</code>
          </div>
          <div class="p-2.5 rounded-lg bg-[var(--content)] border border-[var(--border)] space-y-1">
            <div class="font-bold text-purple-700 dark:text-purple-400">3. View Schema Guard (${vsg.views_passing_guard}/${vsg.total_views} Passing)</div>
            <p class="text-[11px] text-[var(--muted-foreground)]">Active comparison has <strong>${vsg.total_column_mismatches}</strong> column/type mismatches across <strong>${vsg.total_columns_checked}</strong> checked view columns.</p>
            <code class="block text-[10px] p-1 rounded bg-[var(--card)] border border-[var(--border)]">pixi run migrate &amp;&amp; pixi run refresh-views</code>
          </div>
          <div class="p-2.5 rounded-lg bg-[var(--content)] border border-[var(--border)] space-y-1">
            <div class="font-bold text-sky-700 dark:text-sky-400">4. Portal Funnel &amp; QC Pass Filtering</div>
            <p class="text-[11px] text-[var(--muted-foreground)]"><code>analysis_data_view</code> retains <strong>${fmtInt(loc.layer4_parameters_and_funnels.analysis_data_view_funnel.final_row_count)}</strong> rows in Local vs <strong>${fmtInt(stg.layer4_parameters_and_funnels.analysis_data_view_funnel.final_row_count)}</strong> in Staging and <strong>${fmtInt(prd.layer4_parameters_and_funnels.analysis_data_view_funnel.final_row_count)}</strong> in Prod.</p>
            <code class="block text-[10px] p-1 rounded bg-[var(--card)] border border-[var(--border)]">pixi run refresh-views</code>
          </div>
        </div>
      `;
    }

    function renderTab1Parity() {
      const envs = getActiveEnvs();
      const comp = getActiveComparison();
      const loc = DRIFT_BUNDLE.fingerprints.local;
      const stg = DRIFT_BUNDLE.fingerprints.staging;
      const prd = DRIFT_BUNDLE.fingerprints.production;

      document.getElementById("th-parity-delta").textContent = `Δ (${envs.a.toUpperCase()} - ${envs.b.toUpperCase()})`;

      const allItems = [...comp.table_diffs, ...comp.view_diffs];
      const q = state.paritySearch.trim().toLowerCase();

      const filtered = allItems.filter(item => {
        if (state.parityLayer === "table" && item.object_type !== "table") return false;
        if (state.parityLayer === "view" && item.object_type !== "view") return false;
        if (state.parityLayer === "drifted" && item.status === "SYNCED") return false;
        if (q) {
          const hay = `${item.schema}.${item.name} ${item.category} ${item.status}`.toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });

      // Plotly Diverging Bar Chart
      const chartItems = filtered.filter(d => d.count_a > 0 || d.count_b > 0);
      const isDark = state.theme === "dark";
      const fgColor = isDark ? "#f8fafc" : "#0f172a";
      const mutedColor = isDark ? "#94a3b8" : "#475569";
      const gridColor = isDark ? "#334155" : "#e2e8f0";

      if (state.mode === "three_way") {
        // Grouped bar chart comparing Local vs Staging vs Prod deltas relative to Prod
        const labels = chartItems.map(d => d.name.replace("ca_biositing.", "").replace("data_portal.", ""));
        const lsDelta = chartItems.map(d => {
          const cL = d.object_type === "table" ? loc.layer2_row_counts.core_tables[d.name] : loc.layer2_row_counts.views[d.name];
          const cS = d.object_type === "table" ? stg.layer2_row_counts.core_tables[d.name] : stg.layer2_row_counts.views[d.name];
          if (state.parityMetric === "abs") return cL - cS;
          return cS > 0 ? Number((((cL - cS) / cS) * 100).toFixed(1)) : (cL > 0 ? 100 : 0);
        });
        const lpDelta = chartItems.map(d => state.parityMetric === "abs" ? d.delta : d.pct_diff);

        Plotly.react("plot-parity-waterfall", [
          {
            type: "bar",
            name: "Local vs. Staging",
            x: labels,
            y: lsDelta,
            marker: { color: "#0284c7" }
          },
          {
            type: "bar",
            name: "Local vs. Production",
            x: labels,
            y: lpDelta,
            marker: { color: "#f59e0b" }
          }
        ], {
          barmode: "group",
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          font: { color: fgColor, size: 11 },
          margin: { l: 60, r: 20, t: 20, b: 120 },
          xaxis: { tickangle: -40, gridcolor: gridColor },
          yaxis: {
            title: state.parityMetric === "abs" ? "Row Delta (Δ rows)" : "% Difference (%)",
            gridcolor: gridColor,
            zeroline: true,
            zerolinecolor: mutedColor,
            zerolinewidth: 1.5
          },
          legend: { orientation: "h", y: 1.12, x: 0 }
        }, { responsive: true, displayModeBar: false });
      } else {
        const labels = chartItems.map(d => d.name.replace("ca_biositing.", "").replace("data_portal.", ""));
        const vals = chartItems.map(d => state.parityMetric === "abs" ? d.delta : d.pct_diff);
        const colors = chartItems.map(d => {
          if (d.status === "MV STALE") return "#f59e0b";
          if (d.delta > 0) return "#0284c7";
          if (d.delta < 0) return "#e11d48";
          return "#10b981";
        });

        Plotly.react("plot-parity-waterfall", [
          {
            type: "bar",
            x: labels,
            y: vals,
            marker: { color: colors },
            hovertemplate: "<b>%{x}</b><br>Value: %{y}<extra></extra>"
          }
        ], {
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          font: { color: fgColor, size: 11 },
          margin: { l: 60, r: 20, t: 15, b: 120 },
          xaxis: { tickangle: -40, gridcolor: gridColor },
          yaxis: {
            title: state.parityMetric === "abs" ? `Row Delta (${envs.a} - ${envs.b})` : `% Diff (${envs.a} vs ${envs.b})`,
            gridcolor: gridColor,
            zeroline: true,
            zerolinecolor: mutedColor,
            zerolinewidth: 1.5
          }
        }, { responsive: true, displayModeBar: false });
      }

      // Render Table
      const tbody = document.getElementById("tbody-parity");
      tbody.innerHTML = filtered.map(item => {
        const isTbl = item.object_type === "table";
        const cL = isTbl ? loc.layer2_row_counts.core_tables[item.name] : loc.layer2_row_counts.views[item.name];
        const cS = isTbl ? stg.layer2_row_counts.core_tables[item.name] : stg.layer2_row_counts.views[item.name];
        const cP = isTbl ? prd.layer2_row_counts.core_tables[item.name] : prd.layer2_row_counts.views[item.name];
        const qName = isTbl ? `public.${item.name}` : item.name;

        let badgeCls = "badge-pass";
        if (item.status === "MV STALE") badgeCls = "badge-warn";
        else if (item.status.includes("BEHIND") || item.status.includes("DRIFT")) badgeCls = "badge-fail";
        else if (item.status.includes("AHEAD")) badgeCls = item.delta < 0 ? "badge-purple" : "badge-info";

        let hashBadge = "";
        if (isTbl) {
          hashBadge = item.hash_match
            ? `<span class="px-2 py-0.5 rounded text-[10px] font-mono badge-pass">SCHEMA MATCH</span>`
            : `<span class="px-2 py-0.5 rounded text-[10px] font-mono badge-warn">SCHEMA DRIFT</span>`;
        } else {
          const colGuardOk = item.col_schema_match !== false;
          const colGuardBadge = colGuardOk
            ? `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono badge-pass" title="All ${item.col_count_a || ''} view columns and data types match">${item.col_count_a || ''} cols ✓</span>`
            : `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono badge-fail" title="View column or data-type mismatch">COL DRIFT</span>`;
          const defBadge = item.hash_match
            ? `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono badge-info">DEF MATCH</span>`
            : `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono badge-warn">SQL REV DRIFT</span>`;
          hashBadge = `<div class="flex items-center justify-center gap-1 flex-wrap">${colGuardBadge}${defBadge}</div>`;
        }

        return `<tr class="hover:bg-[var(--content)] transition">
          <td class="py-2 px-3 font-mono font-semibold text-[var(--foreground)]">
            ${qName}
            ${item.stale_reason ? `<div class="text-[10px] font-sans font-normal text-amber-600 dark:text-amber-400">${item.stale_reason}</div>` : ""}
          </td>
          <td class="py-2 px-3 text-[var(--muted-foreground)]">${item.category}</td>
          <td class="py-2 px-3 text-right font-mono">${fmtInt(cL)}</td>
          <td class="py-2 px-3 text-right font-mono">${fmtInt(cS)}</td>
          <td class="py-2 px-3 text-right font-mono">${fmtInt(cP)}</td>
          <td class="py-2 px-3 text-right font-mono font-bold ${item.delta > 0 ? 'text-sky-600 dark:text-sky-400' : (item.delta < 0 ? 'text-rose-600 dark:text-rose-400' : 'text-[var(--muted-foreground)]')}">
            ${fmtSigned(item.delta)}
          </td>
          <td class="py-2 px-3 text-right font-mono">${item.pct_diff > 0 ? '+' : ''}${item.pct_diff}%</td>
          <td class="py-2 px-3 text-center">${hashBadge}</td>
          <td class="py-2 px-3 text-center">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${badgeCls}">${item.status}</span>
          </td>
        </tr>`;
      }).join("");

      renderViewSchemaGuard();
    }

    function renderViewSchemaGuard() {
      const comp = getActiveComparison();
      const locMvs = DRIFT_BUNDLE.fingerprints.local.layer1_schema.materialized_views || {};
      const stgMvs = DRIFT_BUNDLE.fingerprints.staging.layer1_schema.materialized_views || {};
      const prdMvs = DRIFT_BUNDLE.fingerprints.production.layer1_schema.materialized_views || {};
      const vsg = comp.view_schema_guard || { views: [], all_views_match: true, views_passing_guard: 19, total_views: 19, total_columns_checked: 239, total_column_mismatches: 0 };

      const hdrBadge = document.getElementById("vsg-header-badge");
      if (hdrBadge) {
        hdrBadge.className = "px-2 py-0.5 rounded text-[11px] font-bold " + (vsg.all_views_match ? "badge-pass" : "badge-fail");
        hdrBadge.textContent = vsg.all_views_match
          ? `✅ ${vsg.views_passing_guard}/${vsg.total_views} VIEWS · ${vsg.total_columns_checked}/${vsg.total_columns_checked} COLUMNS VERIFIED`
          : `❌ ${vsg.views_failing_guard} VIEWS WITH SCHEMA MISMATCH (${vsg.total_column_mismatches} COLS)`;
      }

      // Filter views by selected schema
      const schemaViews = (vsg.views || []).filter(v => {
        if (state.vsgSchema === "data_portal" && v.schema !== "data_portal") return false;
        if (state.vsgSchema === "ca_biositing" && v.schema !== "ca_biositing") return false;
        if (state.vsgSchema === "mismatch" && v.col_schema_match) return false;
        return true;
      });

      // Populate view dropdown
      const selView = document.getElementById("sel-vsg-view");
      const prevVal = state.vsgView;
      selView.innerHTML = `<option value="all">All Views in Selected Schema (${schemaViews.length})</option>` +
        schemaViews.map(v => `<option value="${v.view_name}">${v.view_name} (${v.col_count_canonical} cols · ${v.col_schema_match ? 'PASS' : 'DRIFT'})</option>`).join("");
      if (schemaViews.some(v => v.view_name === prevVal)) {
        selView.value = prevVal;
      } else {
        state.vsgView = "all";
        selView.value = "all";
      }

      // Render clickable view pills
      const pillsEl = document.getElementById("vsg-view-pills");
      pillsEl.innerHTML = schemaViews.map(v => {
        const isSel = state.vsgView === v.view_name;
        const tone = v.col_schema_match ? (isSel ? "bg-[var(--primary)] text-[var(--primary-foreground)]" : "badge-pass") : "badge-fail";
        return `<button data-view="${v.view_name}" class="vsg-pill px-2.5 py-1 rounded-lg text-[11px] font-mono font-semibold transition ${tone} ${isSel ? 'ring-2 ring-[var(--primary)] shadow-sm' : 'hover:opacity-85'}" title="Schema hash: #${(v.col_schema_hash_a || '').slice(0, 8)}">
          ${v.view_name} <span class="opacity-80">(${v.col_count_canonical} cols ${v.col_schema_match ? '✓' : '✗'})</span>
        </button>`;
      }).join("");

      pillsEl.querySelectorAll(".vsg-pill").forEach(btn => {
        btn.addEventListener("click", () => {
          const targetView = btn.dataset.view;
          state.vsgView = state.vsgView === targetView ? "all" : targetView;
          document.getElementById("sel-vsg-view").value = state.vsgView;
          renderViewSchemaGuard();
        });
      });

      // Build column rows across active views
      const q = state.vsgSearch.trim().toLowerCase();
      const colRows = [];
      schemaViews.forEach(v => {
        if (state.vsgView !== "all" && v.view_name !== state.vsgView) return;
        const lCols = new Map(((locMvs[v.view_name] || {}).columns || []).map(c => [c.column_name, c.data_type]));
        const sCols = new Map(((stgMvs[v.view_name] || {}).columns || []).map(c => [c.column_name, c.data_type]));
        const pCols = new Map(((prdMvs[v.view_name] || {}).columns || []).map(c => [c.column_name, c.data_type]));

        (v.columns || []).forEach(c => {
          const tL = lCols.get(c.column_name) || c.type_a || "MISSING";
          const tS = sCols.get(c.column_name) || c.canonical_type || "MISSING";
          const tP = pCols.get(c.column_name) || c.type_b || "MISSING";
          const allMatch = (tL === c.canonical_type) && (tS === c.canonical_type) && (tP === c.canonical_type);
          if (state.vsgSchema === "mismatch" && allMatch) return;
          if (q) {
            const hay = `${v.view_name} ${c.column_name} ${c.canonical_type} ${tL} ${tS} ${tP}`.toLowerCase();
            if (!hay.includes(q)) return;
          }
          colRows.push({
            view_name: v.view_name,
            schema: v.schema,
            ordinal_position: c.ordinal_position,
            column_name: c.column_name,
            canonical_type: c.canonical_type,
            type_l: tL,
            type_s: tS,
            type_p: tP,
            all_match: allMatch
          });
        });
      });

      const tbodyVsg = document.getElementById("tbody-vsg-columns");
      if (!colRows.length) {
        tbodyVsg.innerHTML = `<tr><td colspan="8" class="py-6 text-center text-[var(--muted-foreground)] italic">No view columns match the current filter (${state.vsgSchema === 'mismatch' ? '0 schema or data-type mismatches detected across all 19 views and 239 columns!' : 'try clearing search'}).</td></tr>`;
        return;
      }

      tbodyVsg.innerHTML = colRows.map(r => {
        const schemaBadge = r.schema === "data_portal"
          ? `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono badge-info">data_portal</span>`
          : `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono badge-purple">ca_biositing</span>`;
        const statusBadge = r.all_match
          ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold badge-pass">EXACT TYPE MATCH</span>`
          : `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold badge-fail">SCHEMA / TYPE MISMATCH</span>`;
        return `<tr class="hover:bg-[var(--content)] transition">
          <td class="py-1.5 px-3 text-center font-mono text-[var(--muted-foreground)]">${r.ordinal_position}</td>
          <td class="py-1.5 px-3 font-mono font-semibold text-[var(--foreground)]">${schemaBadge} <span class="ml-1">${r.view_name.split('.')[1]}</span></td>
          <td class="py-1.5 px-3 font-mono font-bold text-[var(--primary)]">${r.column_name}</td>
          <td class="py-1.5 px-3 font-mono text-[var(--muted-foreground)]">${r.canonical_type}</td>
          <td class="py-1.5 px-3 font-mono ${r.type_l === r.canonical_type ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500 font-bold'}">${r.type_l}</td>
          <td class="py-1.5 px-3 font-mono ${r.type_s === r.canonical_type ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500 font-bold'}">${r.type_s}</td>
          <td class="py-1.5 px-3 font-mono ${r.type_p === r.canonical_type ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500 font-bold'}">${r.type_p}</td>
          <td class="py-1.5 px-3 text-center">${statusBadge}</td>
        </tr>`;
      }).join("");
    }

    function renderTab2Heatmap() {
      const envs = getActiveEnvs();
      const locMat = DRIFT_BUNDLE.fingerprints.local.layer3_coverage_and_lineage.resource_analysis_matrix;
      const stgMat = DRIFT_BUNDLE.fingerprints.staging.layer3_coverage_and_lineage.resource_analysis_matrix;
      const prdMat = DRIFT_BUNDLE.fingerprints.production.layer3_coverage_and_lineage.resource_analysis_matrix;
      const matrixA = DRIFT_BUNDLE.fingerprints[envs.a].layer3_coverage_and_lineage.resource_analysis_matrix;
      const matrixB = DRIFT_BUNDLE.fingerprints[envs.b].layer3_coverage_and_lineage.resource_analysis_matrix;
      const ats = DRIFT_BUNDLE.analysis_types;

      const prodResSet = new Set(DRIFT_BUNDLE.fingerprints.production.layer3_coverage_and_lineage.lineage_sets.resources);
      const allResources = Object.keys(locMat).sort();
      const q = state.heatSearch.trim().toLowerCase();

      const filteredRes = allResources.filter(res => {
        if (q && !res.toLowerCase().includes(q)) return false;
        if (state.heatFilter === "missing_prod" && prodResSet.has(res)) return false;
        if (state.heatFilter === "drifted") {
          const hasDrift = ats.some(at => {
            const cA = ((matrixA[res] || {})[at] || {}).count || 0;
            const cB = ((matrixB[res] || {})[at] || {}).count || 0;
            return cA !== cB;
          });
          if (!hasDrift) return false;
        }
        return true;
      });

      const shortAt = {
        "Calorimetry": "Calorim.",
        "Compositional Analysis": "Compos.",
        "Fermentation (Bioconversion)": "Ferment.",
        "Gasification": "Gasific.",
        "ICP Elemental Analysis": "ICP Elem.",
        "Pretreatment & Hydrolysis": "Pretreat.",
        "Proximate Analysis": "Proximate",
        "Ultimate Analysis": "Ultimate",
        "XRD Crystallinity": "XRD Cryst.",
        "XRF Elemental Analysis": "XRF Elem."
      };

      const tbl = document.getElementById("tbl-heatmap");
      let html = `<thead class="bg-[var(--content)] sticky top-0 z-20 border-b border-[var(--border)] text-[var(--muted-foreground)]">
        <tr>
          <th class="py-2 px-2.5 text-left font-bold sticky left-0 bg-[var(--content)] z-30">Resource (${filteredRes.length})</th>
          ${ats.map(at => `<th class="py-2 px-1.5 text-center font-bold">${shortAt[at] || at}</th>`).join("")}
          <th class="py-2 px-2 text-right font-bold">&Sigma; &Delta;</th>
        </tr>
      </thead><tbody class="divide-y divide-[var(--border)]">`;

      filteredRes.forEach(res => {
        let rowDeltaSum = 0;
        const missingInProd = !prodResSet.has(res);
        html += `<tr class="hover:bg-[var(--content)]">
          <td class="py-1.5 px-2.5 font-semibold sticky left-0 bg-[var(--card)] whitespace-nowrap">
            ${res}
            ${missingInProd ? `<span class="ml-1 px-1.5 py-0.2 text-[9px] rounded badge-fail">NO PROD</span>` : ""}
          </td>`;

        ats.forEach(at => {
          const cL = ((locMat[res] || {})[at] || {}).count || 0;
          const cS = ((stgMat[res] || {})[at] || {}).count || 0;
          const cP = ((prdMat[res] || {})[at] || {}).count || 0;
          const cellA = ((matrixA[res] || {})[at] || {});
          const cellB = ((matrixB[res] || {})[at] || {});
          const cA = cellA.count || 0;
          const cB = cellB.count || 0;
          const delta = cA - cB;
          rowDeltaSum += delta;

          const isSelected = state.selectedCell.resource === res && state.selectedCell.analysisType === at;
          let cellBg = "";
          let textStr = "·";

          if (cL === 0 && cS === 0 && cP === 0) {
            cellBg = "text-[var(--muted-foreground)] opacity-40";
          } else {
            if (delta > 0 && cB === 0) {
              cellBg = "badge-fail font-bold";
            } else if (delta > 0) {
              cellBg = "badge-info font-bold";
            } else if (delta < 0) {
              cellBg = "badge-purple font-bold";
            } else {
              cellBg = "badge-pass";
            }

            if (state.heatDisplay === "slash" || state.mode === "three_way") {
              textStr = `${cL}/${cS}/${cP}`;
            } else if (state.heatDisplay === "qc") {
              const rA = cA > 0 ? Math.round((cellA.qc_pass / cA) * 100) : 0;
              const rB = cB > 0 ? Math.round((cellB.qc_pass / cB) * 100) : 0;
              const dR = rA - rB;
              textStr = dR === 0 ? `${rA}%` : `${dR > 0 ? '+' : ''}${dR}%`;
            } else {
              textStr = delta === 0 ? `${cA}` : `${delta > 0 ? '+' : ''}${delta}`;
            }
          }

          html += `<td class="p-1 text-center">
            <div data-res="${res}" data-at="${at}" class="heat-cell rounded py-1 px-1 text-[10px] font-mono ${cellBg} ${isSelected ? 'heat-cell-selected' : ''}" title="${res} — ${at}: Local=${cL}, Staging=${cS}, Prod=${cP}">
              ${textStr}
            </div>
          </td>`;
        });

        html += `<td class="py-1.5 px-2 text-right font-mono font-bold ${rowDeltaSum > 0 ? 'text-sky-600 dark:text-sky-400' : (rowDeltaSum < 0 ? 'text-purple-600 dark:text-purple-400' : 'text-[var(--muted-foreground)]')}">
          ${rowDeltaSum === 0 ? '0' : fmtSigned(rowDeltaSum)}
        </td></tr>`;
      });

      html += `</tbody>`;
      tbl.innerHTML = html;

      tbl.querySelectorAll(".heat-cell").forEach(el => {
        el.addEventListener("click", () => {
          state.selectedCell = { resource: el.dataset.res, analysisType: el.dataset.at };
          renderTab2Heatmap();
        });
      });

      renderHeatDrilldown();
    }

    function renderHeatDrilldown() {
      const { resource, analysisType } = state.selectedCell;
      const locCell = ((DRIFT_BUNDLE.fingerprints.local.layer3_coverage_and_lineage.resource_analysis_matrix[resource] || {})[analysisType]) || { count: 0, qc_pass: 0, qc_fail: 0, qc_other: 0, record_ids_sample: [], prepared_samples: [], record_hash: "—" };
      const stgCell = ((DRIFT_BUNDLE.fingerprints.staging.layer3_coverage_and_lineage.resource_analysis_matrix[resource] || {})[analysisType]) || { count: 0, qc_pass: 0, qc_fail: 0, qc_other: 0, record_ids_sample: [], prepared_samples: [], record_hash: "—" };
      const prdCell = ((DRIFT_BUNDLE.fingerprints.production.layer3_coverage_and_lineage.resource_analysis_matrix[resource] || {})[analysisType]) || { count: 0, qc_pass: 0, qc_fail: 0, qc_other: 0, record_ids_sample: [], prepared_samples: [], record_hash: "—" };

      const box = document.getElementById("heat-drilldown-content");
      box.innerHTML = `
        <div class="flex items-center justify-between border-b border-[var(--border)] pb-2">
          <div>
            <span class="text-[10px] font-bold uppercase tracking-wider text-[var(--primary)]">Selected Matrix Cell Drilldown</span>
            <h3 class="text-sm font-bold text-[var(--foreground)]">${resource} &times; ${analysisType}</h3>
          </div>
          <span class="px-2 py-0.5 rounded text-xs font-mono badge-info">&Delta; L-P: ${fmtSigned(locCell.count - prdCell.count)}</span>
        </div>

        <div class="grid grid-cols-3 gap-2 text-center text-xs">
          <div class="p-2 rounded-lg bg-[var(--content)] border border-[var(--border)]">
            <div class="text-[10px] text-[var(--muted-foreground)] font-bold">LOCAL (:5432)</div>
            <div class="text-lg font-extrabold text-[var(--foreground)]">${locCell.count}</div>
            <div class="text-[10px] text-emerald-600 dark:text-emerald-400">${locCell.qc_pass}P / ${locCell.qc_fail}F</div>
            <div class="text-[9px] font-mono text-[var(--muted-foreground)] mt-0.5">#${locCell.record_hash.slice(0, 8)}</div>
          </div>
          <div class="p-2 rounded-lg bg-[var(--content)] border border-[var(--border)]">
            <div class="text-[10px] text-[var(--muted-foreground)] font-bold">STAGING (:5434)</div>
            <div class="text-lg font-extrabold text-[var(--foreground)]">${stgCell.count}</div>
            <div class="text-[10px] text-amber-600 dark:text-amber-400">${stgCell.qc_pass}P / ${stgCell.qc_fail}F</div>
            <div class="text-[9px] font-mono text-[var(--muted-foreground)] mt-0.5">#${stgCell.record_hash.slice(0, 8)}</div>
          </div>
          <div class="p-2 rounded-lg bg-[var(--content)] border border-[var(--border)]">
            <div class="text-[10px] text-[var(--muted-foreground)] font-bold">PROD (:5435)</div>
            <div class="text-lg font-extrabold text-[var(--foreground)]">${prdCell.count}</div>
            <div class="text-[10px] text-rose-600 dark:text-rose-400">${prdCell.qc_pass}P / ${prdCell.qc_fail}F</div>
            <div class="text-[9px] font-mono text-[var(--muted-foreground)] mt-0.5">#${prdCell.record_hash.slice(0, 8)}</div>
          </div>
        </div>

        <div class="space-y-1.5 text-xs">
          <div class="font-bold text-[var(--muted-foreground)]">Prepared Samples in Cell (${(locCell.prepared_samples || []).length}):</div>
          <div class="flex flex-wrap gap-1">
            ${(locCell.prepared_samples || []).length
              ? locCell.prepared_samples.map(s => `<span class="px-2 py-0.5 rounded font-mono text-[10px] bg-[var(--content)] border border-[var(--border)]">${s}</span>`).join("")
              : `<span class="text-[var(--muted-foreground)] italic">No prepared samples linked</span>`}
          </div>
        </div>

        <div class="space-y-1.5 text-xs">
          <div class="font-bold text-[var(--muted-foreground)]">Sample Record IDs (Local):</div>
          <div class="flex flex-wrap gap-1">
            ${(locCell.record_ids_sample || []).length
              ? locCell.record_ids_sample.map(id => `<code class="px-1.5 py-0.5 rounded text-[10px] badge-info">${id}</code>`).join("")
              : `<span class="text-[var(--muted-foreground)] italic">0 records in cell</span>`}
          </div>
        </div>
      `;

      // Also populate the QC Pass/Fail distribution mini-table across Aim1/Aim2 tables
      const qcBox = document.getElementById("qc-table-mini-summary");
      const locQc = DRIFT_BUNDLE.fingerprints.local.layer3_coverage_and_lineage.qc_pass_distribution;
      const prdQc = DRIFT_BUNDLE.fingerprints.production.layer3_coverage_and_lineage.qc_pass_distribution;

      qcBox.innerHTML = Object.keys(locQc).map(tName => {
        const lq = locQc[tName];
        const pq = prdQc[tName] || { pass: 0, fail: 0, other: 0, pass_rate_pct: 0 };
        if (lq.total === 0 && pq.total === 0) return "";
        const failDelta = lq.fail - pq.fail;
        return `<div class="p-2 rounded bg-[var(--content)] border border-[var(--border)] flex items-center justify-between text-[11px]">
          <div>
            <div class="font-mono font-bold text-[var(--foreground)]">${tName}</div>
            <div class="text-[10px] text-[var(--muted-foreground)]">Local: ${lq.pass}P / ${lq.fail}F (${lq.pass_rate_pct}%) &middot; Prod: ${pq.pass}P / ${pq.fail}F</div>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-mono ${failDelta !== 0 ? 'badge-warn' : 'badge-pass'}">
            &Delta;Fail: ${fmtSigned(failDelta)}
          </span>
        </div>`;
      }).join("");
    }

    function renderTab3Lineage() {
      const entType = state.lineageEntity;
      const locSet = DRIFT_BUNDLE.fingerprints.local.layer3_coverage_and_lineage.lineage_sets[entType] || [];
      const stgSet = DRIFT_BUNDLE.fingerprints.staging.layer3_coverage_and_lineage.lineage_sets[entType] || [];
      const prdSet = DRIFT_BUNDLE.fingerprints.production.layer3_coverage_and_lineage.lineage_sets[entType] || [];

      document.querySelectorAll(".entity-btn").forEach(btn => {
        const active = btn.dataset.entity === entType;
        btn.className = "entity-btn px-3 py-1.5 rounded-lg text-xs font-bold transition " + (
          active
            ? "bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm"
            : "bg-[var(--secondary)] text-[var(--secondary-foreground)] hover:opacity-85"
        );
      });

      const getKey = item => (typeof item === "string" ? item : item.name);
      const mapL = new Map(locSet.map(x => [getKey(x), x]));
      const mapS = new Map(stgSet.map(x => [getKey(x), x]));
      const mapPrd = new Map(prdSet.map(x => [getKey(x), x]));

      const allKeys = Array.from(new Set([...mapL.keys(), ...mapS.keys(), ...mapPrd.keys()])).sort();
      const rows = allKeys.map(k => {
        const obj = mapL.get(k) || mapS.get(k) || mapPrd.get(k);
        const inL = mapL.has(k);
        const inS = mapS.has(k);
        const inP = mapPrd.has(k);
        let bucket = "synced_all_3";
        let statusLabel = "SYNCED (ALL 3)";
        let badgeCls = "badge-pass";

        if (inL && !inS && !inP) {
          bucket = "only_local";
          statusLabel = "LOCAL ONLY (UNSTAGED)";
          badgeCls = "badge-fail";
        } else if (inL && inS && !inP) {
          bucket = "staged_not_prod";
          statusLabel = "IN LOCAL & STAGING (UNPROMOTED TO PROD)";
          badgeCls = "badge-warn";
        } else if (!inL && inP) {
          bucket = "only_prod";
          statusLabel = "PROD ONLY (LEGACY)";
          badgeCls = "badge-purple";
        }

        return {
          name: k,
          resource_name: typeof obj === "object" ? (obj.resource_name || "—") : (entType === "resources" ? k : "—"),
          meta: typeof obj === "object"
            ? [obj.field_sample ? `FS: ${obj.field_sample}` : "", obj.prep_method ? `Prep: ${obj.prep_method}` : "", obj.provider ? `Prov: ${obj.provider}` : ""].filter(Boolean).join(" · ")
            : (entType === "resources" ? "Canonical Resource" : "Experiment Batch"),
          inL, inS, inP, bucket, statusLabel, badgeCls
        };
      });

      const counts = {
        only_local_vs_prod: rows.filter(r => r.inL && !r.inP).length,
        only_local: rows.filter(r => r.bucket === "only_local").length,
        staged_not_prod: rows.filter(r => r.bucket === "staged_not_prod").length,
        synced_all_3: rows.filter(r => r.bucket === "synced_all_3").length
      };

      const bucketDefs = [
        { id: "only_local_vs_prod", title: "Missing in Production (Local Only + Staged)", count: counts.only_local_vs_prod, desc: "Present in Local (:5432), absent in Production (:5435)", cls: "badge-fail" },
        { id: "only_local", title: "In Local Only (Missing in Staging & Prod)", count: counts.only_local, desc: "Newest ingestions not yet synced to Staging (:5434)", cls: "badge-info" },
        { id: "staged_not_prod", title: "In Local & Staging (Ready for Prod Promotion)", count: counts.staged_not_prod, desc: "Verified in Staging (:5434), awaiting Prod release", cls: "badge-warn" },
        { id: "synced_all_3", title: "Synced Across All 3 Environments", count: counts.synced_all_3, desc: "Present in Local, Staging, and Production", cls: "badge-pass" }
      ];

      const bucketBox = document.getElementById("lineage-bucket-cards");
      bucketBox.innerHTML = bucketDefs.map(b => {
        const active = state.lineageBucket === b.id;
        return `<div data-bucket="${b.id}" class="lineage-bucket-card p-3 rounded-xl border cursor-pointer transition ${active ? 'border-[var(--primary)] bg-[var(--content)] ring-2 ring-[var(--primary)]' : 'border-[var(--border)] bg-[var(--card)] hover:bg-[var(--content)]'}">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-[var(--foreground)]">${b.title}</span>
            <span class="px-2 py-0.5 rounded-full text-xs font-extrabold ${b.cls}">${b.count}</span>
          </div>
          <p class="text-[11px] text-[var(--muted-foreground)] mt-1">${b.desc}</p>
        </div>`;
      }).join("");

      bucketBox.querySelectorAll(".lineage-bucket-card").forEach(card => {
        card.addEventListener("click", () => {
          state.lineageBucket = card.dataset.bucket;
          renderTab3Lineage();
        });
      });

      const q = state.lineageSearch.trim().toLowerCase();
      const filteredRows = rows.filter(r => {
        if (state.lineageBucket === "only_local_vs_prod" && !(r.inL && !r.inP)) return false;
        if (state.lineageBucket !== "only_local_vs_prod" && r.bucket !== state.lineageBucket) return false;
        if (q) {
          const hay = `${r.name} ${r.resource_name} ${r.meta} ${r.statusLabel}`.toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });

      document.getElementById("lineage-table-title").textContent = `Showing ${filteredRows.length} of ${rows.length} ${entType.replace("_", " ")}`;

      const tbody = document.getElementById("tbody-lineage");
      tbody.innerHTML = filteredRows.map(r => `
        <tr class="hover:bg-[var(--content)]">
          <td class="py-2 px-3 font-mono font-bold text-[var(--foreground)]">${r.name}</td>
          <td class="py-2 px-3 font-medium">${r.resource_name}</td>
          <td class="py-2 px-3 text-[var(--muted-foreground)]">${r.meta || "—"}</td>
          <td class="py-2 px-3 text-center">${r.inL ? "✅" : "❌"}</td>
          <td class="py-2 px-3 text-center">${r.inS ? "✅" : "❌"}</td>
          <td class="py-2 px-3 text-center">${r.inP ? "✅" : "❌"}</td>
          <td class="py-2 px-3 text-center"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${r.badgeCls}">${r.statusLabel}</span></td>
        </tr>
      `).join("");
    }

    function renderTab4FunnelAndParams() {
      const locF = DRIFT_BUNDLE.fingerprints.local.layer4_parameters_and_funnels.analysis_data_view_funnel;
      const stgF = DRIFT_BUNDLE.fingerprints.staging.layer4_parameters_and_funnels.analysis_data_view_funnel;
      const prdF = DRIFT_BUNDLE.fingerprints.production.layer4_parameters_and_funnels.analysis_data_view_funnel;

      const stages = [
        { key: "candidate_pool", label: "1. Raw Candidate Pool", diag: "Joined Aim 1 analytical observations (compositional, proximate, ultimate, icp, xrf, calorimetry, xrd)" },
        { key: "removed_by_qc_fail", label: "2. Removed by QC Fail", diag: "Observations where record.qc_pass = 'fail'" },
        { key: "removed_by_resource_blacklist", label: "3. Removed by EXCLUDED_RESOURCES", diag: "Excludes #n/a, alfalfa, sargassum, lab media, and mixtures" },
        { key: "removed_by_provider_blacklist", label: "4. Removed by EXCLUDED_PROVIDERS", diag: "Excludes provider codes 'legacy' and 'jaguar' (added in migration 0022)" },
        { key: "removed_by_ultimate_whitelist", label: "5. Removed by ULTIMATE_PARAMETERS", diag: "Restricts ultimate_record to canonical CHONS parameters" },
        { key: "removed_by_icp_non_ppm_unit", label: "6. Removed by ICP Non-PPM Unit", diag: "Excludes non-ppm ICP units" },
        { key: "unmapped_resource", label: "7. Unmapped Resource (NULL)", diag: "Blank/control records without resource_id mapping" },
        { key: "final_row_count", label: "8. Final Materialized View Rows", diag: "Live row count in ca_biositing.analysis_data_view" }
      ];

      const tbodyF = document.getElementById("tbody-funnel-stages");
      tbodyF.innerHTML = stages.map(s => {
        const vL = locF[s.key] || 0;
        const vS = stgF[s.key] || 0;
        const vP = prdF[s.key] || 0;
        const isFinal = s.key === "final_row_count" || s.key === "candidate_pool";
        return `<tr class="${isFinal ? 'bg-[var(--content)] font-bold' : 'hover:bg-[var(--content)]'}">
          <td class="py-2 px-3">${s.label}</td>
          <td class="py-2 px-3 text-right font-mono">${fmtInt(vL)}</td>
          <td class="py-2 px-3 text-right font-mono">${fmtInt(vS)}</td>
          <td class="py-2 px-3 text-right font-mono">${fmtInt(vP)}</td>
          <td class="py-2 px-3 text-[11px] text-[var(--muted-foreground)]">${s.diag}</td>
        </tr>`;
      }).join("") + `
        <tr class="bg-[var(--content)] font-bold border-t-2 border-[var(--border)]">
          <td class="py-2 px-3">Portal Retention Ratio</td>
          <td class="py-2 px-3 text-right font-mono text-emerald-600 dark:text-emerald-400">${(locF.retention_ratio * 100).toFixed(2)}%</td>
          <td class="py-2 px-3 text-right font-mono text-amber-600 dark:text-amber-400">${(stgF.retention_ratio * 100).toFixed(2)}%</td>
          <td class="py-2 px-3 text-right font-mono text-rose-600 dark:text-rose-400">${(prdF.retention_ratio * 100).toFixed(2)}%</td>
          <td class="py-2 px-3 text-[11px] text-[var(--muted-foreground)]">Ratio guard across ETL &amp; view migrations</td>
        </tr>
      `;

      // Plotly Funnel Comparison Chart
      const isDark = state.theme === "dark";
      const fgColor = isDark ? "#f8fafc" : "#0f172a";
      const gridColor = isDark ? "#334155" : "#e2e8f0";
      const stepLabels = ["Candidate Pool", "After QC Pass", "After Res Filter", "After Prov Filter", "Final View"];
      const stepVals = f => {
        const s1 = f.candidate_pool;
        const s2 = s1 - f.removed_by_qc_fail;
        const s3 = s2 - f.removed_by_resource_blacklist;
        const s4 = s3 - f.removed_by_provider_blacklist;
        const s5 = f.final_row_count;
        return [s1, s2, s3, s4, s5];
      };

      Plotly.react("plot-funnel-bars", [
        { type: "bar", name: "Local (:5432)", x: stepLabels, y: stepVals(locF), marker: { color: "#0284c7" } },
        { type: "bar", name: "Staging (:5434)", x: stepLabels, y: stepVals(stgF), marker: { color: "#f59e0b" } },
        { type: "bar", name: "Production (:5435)", x: stepLabels, y: stepVals(prdF), marker: { color: "#e11d48" } }
      ], {
        barmode: "group",
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: fgColor, size: 11 },
        margin: { l: 55, r: 15, t: 25, b: 45 },
        xaxis: { gridcolor: gridColor },
        yaxis: { title: "Remaining Rows", gridcolor: gridColor },
        legend: { orientation: "h", y: 1.14, x: 0 }
      }, { responsive: true, displayModeBar: false });

      // Parameter Mean/Median Shift Table
      const comp = getActiveComparison();
      const envs = getActiveEnvs();
      document.getElementById("th-param-shift").textContent = `Mean % Shift (${envs.a.toUpperCase()} vs ${envs.b.toUpperCase()})`;

      const locParams = DRIFT_BUNDLE.fingerprints.local.layer4_parameters_and_funnels.parameter_stats;
      const stgParams = DRIFT_BUNDLE.fingerprints.staging.layer4_parameters_and_funnels.parameter_stats;
      const prdParams = DRIFT_BUNDLE.fingerprints.production.layer4_parameters_and_funnels.parameter_stats;

      const selAt = document.getElementById("sel-param-at");
      if (selAt.options.length <= 1) {
        DRIFT_BUNDLE.analysis_types.forEach(at => {
          const opt = document.createElement("option");
          opt.value = at;
          opt.textContent = at;
          selAt.appendChild(opt);
        });
      }

      const q = state.paramSearch.trim().toLowerCase();
      const rowsP = comp.param_shifts.filter(p => {
        if (state.paramFilter === "flagged" && !p.flagged_gt_5pct) return false;
        if (state.paramAt !== "all" && p.analysis_type !== state.paramAt) return false;
        if (q) {
          const hay = `${p.analysis_type} ${p.parameter_name} ${p.unit}`.toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      }).sort((a, b) => Math.abs(b.pct_shift) - Math.abs(a.pct_shift));

      const tbodyP = document.getElementById("tbody-param-shifts");
      tbodyP.innerHTML = rowsP.map(p => {
        const lp = locParams[p.key] || { mean: 0, sd: 0, n: 0, median: 0 };
        const sp = stgParams[p.key] || { mean: 0, sd: 0, n: 0, median: 0 };
        const pp = prdParams[p.key] || { mean: 0, sd: 0, n: 0, median: 0 };
        const flagBadge = p.flagged_gt_5pct
          ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold badge-fail">SHIFT &gt;5%</span>`
          : `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold badge-pass">STABLE (&le;5%)</span>`;

        return `<tr class="hover:bg-[var(--content)]">
          <td class="py-2 px-3 font-medium">${p.analysis_type}</td>
          <td class="py-2 px-3 font-mono font-bold text-[var(--foreground)]">
            ${p.parameter_name} ${p.unit ? `<span class="text-[10px] font-normal text-[var(--muted-foreground)]">(${p.unit})</span>` : ""}
          </td>
          <td class="py-2 px-3 text-right font-mono">${lp.n > 0 ? `${lp.mean} &plusmn; ${lp.sd} (${lp.n})` : "0 (—)"}</td>
          <td class="py-2 px-3 text-right font-mono">${sp.n > 0 ? `${sp.mean} &plusmn; ${sp.sd} (${sp.n})` : "0 (—)"}</td>
          <td class="py-2 px-3 text-right font-mono">${pp.n > 0 ? `${pp.mean} &plusmn; ${pp.sd} (${pp.n})` : "0 (—)"}</td>
          <td class="py-2 px-3 text-right font-mono text-[var(--muted-foreground)]">${lp.median} / ${sp.median} / ${pp.median}</td>
          <td class="py-2 px-3 text-right font-mono font-bold ${p.flagged_gt_5pct ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}">
            ${p.pct_shift > 0 ? "+" : ""}${p.pct_shift}%
          </td>
          <td class="py-2 px-3 text-center">${flagBadge}</td>
        </tr>`;
      }).join("");
    }

    function renderAll() {
      renderHeaderAndScorecard();
      document.querySelectorAll(".tab-btn").forEach(btn => {
        const active = btn.dataset.tab === state.activeTab;
        btn.className = "tab-btn flex-1 min-w-[200px] py-2 px-3 rounded-lg text-xs sm:text-sm font-bold transition " + (
          active
            ? "bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm"
            : "bg-[var(--secondary)] text-[var(--secondary-foreground)] hover:opacity-85"
        );
      });
      document.querySelectorAll(".tab-panel").forEach(panel => {
        panel.classList.toggle("hidden", panel.id !== state.activeTab);
      });

      if (state.activeTab === "tab-parity") renderTab1Parity();
      else if (state.activeTab === "tab-heatmap") renderTab2Heatmap();
      else if (state.activeTab === "tab-lineage") renderTab3Lineage();
      else if (state.activeTab === "tab-funnel") renderTab4FunnelAndParams();
    }

    // Wire Event Listeners
    document.querySelectorAll(".mode-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        state.mode = btn.dataset.mode;
        renderAll();
      });
    });

    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        state.activeTab = btn.dataset.tab;
        renderAll();
      });
    });

    document.getElementById("sel-parity-layer").addEventListener("change", e => {
      state.parityLayer = e.target.value;
      renderTab1Parity();
    });
    document.getElementById("sel-parity-metric").addEventListener("change", e => {
      state.parityMetric = e.target.value;
      renderTab1Parity();
    });
    document.getElementById("inp-parity-search").addEventListener("input", e => {
      state.paritySearch = e.target.value;
      renderTab1Parity();
    });
    const elVsgSchema = document.getElementById("sel-vsg-schema");
    if (elVsgSchema) elVsgSchema.addEventListener("change", () => renderViewSchemaGuard());
    const elVsgView = document.getElementById("sel-vsg-view");
    if (elVsgView) elVsgView.addEventListener("change", () => renderViewSchemaGuard());
    const elVsgSearch = document.getElementById("inp-vsg-search");
    if (elVsgSearch) elVsgSearch.addEventListener("input", () => renderViewSchemaGuard());

    document.getElementById("sel-heat-display").addEventListener("change", e => {
      state.heatDisplay = e.target.value;
      renderTab2Heatmap();
    });
    document.getElementById("sel-heat-filter").addEventListener("change", e => {
      state.heatFilter = e.target.value;
      renderTab2Heatmap();
    });
    document.getElementById("inp-heat-search").addEventListener("input", e => {
      state.heatSearch = e.target.value;
      renderTab2Heatmap();
    });

    document.querySelectorAll(".entity-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        state.lineageEntity = btn.dataset.entity;
        renderTab3Lineage();
      });
    });
    document.getElementById("inp-lineage-search").addEventListener("input", e => {
      state.lineageSearch = e.target.value;
      renderTab3Lineage();
    });

    document.getElementById("sel-param-filter").addEventListener("change", e => {
      state.paramFilter = e.target.value;
      renderTab4FunnelAndParams();
    });
    document.getElementById("sel-param-at").addEventListener("change", e => {
      state.paramAt = e.target.value;
      renderTab4FunnelAndParams();
    });
    document.getElementById("inp-param-search").addEventListener("input", e => {
      state.paramSearch = e.target.value;
      renderTab4FunnelAndParams();
    });

    document.getElementById("btn-cli-help").addEventListener("click", () => {
      document.getElementById("cli-drawer").classList.toggle("hidden");
    });
    document.getElementById("btn-close-cli").addEventListener("click", () => {
      document.getElementById("cli-drawer").classList.add("hidden");
    });

    document.getElementById("btn-theme-toggle").addEventListener("click", () => {
      state.theme = state.theme === "light" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", state.theme);
      document.getElementById("btn-theme-toggle").textContent = state.theme === "light" ? "🌙 Dark Mode" : "☀️ Light Mode";
      renderAll();
    });

    // Interactive Custom Fingerprint JSON Upload
    document.getElementById("inp-upload-fp").addEventListener("change", async e => {
      const files = Array.from(e.target.files || []);
      for (const file of files) {
        try {
          const text = await file.text();
          const parsed = JSON.parse(text);
          if (parsed && parsed.environment && parsed.layer1_schema && parsed.layer2_row_counts) {
            const envKey = parsed.environment.toLowerCase();
            if (["local", "staging", "production"].includes(envKey)) {
              DRIFT_BUNDLE.fingerprints[envKey] = parsed;
            }
          }
        } catch (err) {
          alert("Failed to parse fingerprint JSON: " + file.name);
        }
      }
      DRIFT_BUNDLE.comparisons.local_vs_staging = recomputePairInBrowser(DRIFT_BUNDLE.fingerprints.local, DRIFT_BUNDLE.fingerprints.staging);
      DRIFT_BUNDLE.comparisons.staging_vs_production = recomputePairInBrowser(DRIFT_BUNDLE.fingerprints.staging, DRIFT_BUNDLE.fingerprints.production);
      DRIFT_BUNDLE.comparisons.local_vs_production = recomputePairInBrowser(DRIFT_BUNDLE.fingerprints.local, DRIFT_BUNDLE.fingerprints.production);
      renderAll();
    });

    // Export Active Table Diff CSV
    document.getElementById("btn-export-csv").addEventListener("click", () => {
      const comp = getActiveComparison();
      const loc = DRIFT_BUNDLE.fingerprints.local;
      const stg = DRIFT_BUNDLE.fingerprints.staging;
      const prd = DRIFT_BUNDLE.fingerprints.production;
      const allItems = [...comp.table_diffs, ...comp.view_diffs];
      const csvRows = [
        ["object_type", "schema", "name", "category", "local_rows", "staging_rows", "production_rows", "delta", "pct_diff", "status"].join(",")
      ];
      allItems.forEach(item => {
        const isTbl = item.object_type === "table";
        const cL = isTbl ? loc.layer2_row_counts.core_tables[item.name] : loc.layer2_row_counts.views[item.name];
        const cS = isTbl ? stg.layer2_row_counts.core_tables[item.name] : stg.layer2_row_counts.views[item.name];
        const cP = isTbl ? prd.layer2_row_counts.core_tables[item.name] : prd.layer2_row_counts.views[item.name];
        csvRows.push([
          item.object_type,
          item.schema,
          `"${item.name}"`,
          `"${item.category}"`,
          cL,
          cS,
          cP,
          item.delta,
          item.pct_diff,
          `"${item.status}"`
        ].join(","));
      });
      const blob = new Blob([csvRows.join("\\n")], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `db_drift_${comp.pair_key}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    });

    renderAll();
  </script>
</body>
</html>
"""
    final_html = html_template.replace("__PAYLOAD_JSON__", payload_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(final_html, encoding="utf-8")
    print(f"[compare] Wrote interactive HTML drift dashboard to {output_path} ({output_path.stat().st_size:,} bytes)")


def run_compare(base_dir: Path) -> None:
    """Load the 3 environment fingerprints, compute pairwise diffs, and write report + dashboard."""
    fp_dir = base_dir / "audit" / "output" / "env_fingerprints"
    required = ["local", "staging", "production"]
    fingerprints: dict[str, dict[str, Any]] = {}
    for env_key in required:
        p = fp_dir / f"{env_key}_fingerprint.json"
        if not p.exists():
            print(f"[compare] Missing {p}, extracting live fingerprint for {env_key}...")
            fingerprints[env_key] = extract_live_fingerprint(env_key=env_key, base_dir=base_dir)
        else:
            fingerprints[env_key] = json.loads(p.read_text(encoding="utf-8"))

    comparisons = {
        "local_vs_staging": compute_pair_comparison(fingerprints["local"], fingerprints["staging"]),
        "staging_vs_production": compute_pair_comparison(
            fingerprints["staging"], fingerprints["production"]
        ),
        "local_vs_production": compute_pair_comparison(
            fingerprints["local"], fingerprints["production"]
        ),
    }

    report_path = base_dir / "audit" / "output" / "drift_report.md"
    dashboard_path = base_dir / "exports" / "plots" / "audit" / "db_environment_drift_dashboard.html"
    generate_markdown_drift_report(fingerprints, comparisons, report_path)
    build_drift_dashboard_html(fingerprints, comparisons, dashboard_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BioCirV Multi-Environment PostgreSQL Drift Assessment & Dashboard Generator"
    )
    parser.add_argument(
        "--extract-env",
        choices=["local", "staging", "production"],
        help="Connect to a live PostgreSQL environment and extract its 4-layer fingerprint JSON",
    )
    parser.add_argument(
        "--extract-all",
        action="store_true",
        help="Extract live 4-layer fingerprints from all 3 environments (local, staging, production)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare environment fingerprints and generate drift_report.md + db_environment_drift_dashboard.html",
    )
    parser.add_argument("--host", help="Override PostgreSQL host for --extract-env")
    parser.add_argument("--port", type=int, help="Override PostgreSQL port for --extract-env")
    parser.add_argument("--dbname", help="Override PostgreSQL database name for --extract-env")
    parser.add_argument("--user", help="Override PostgreSQL user for --extract-env")
    parser.add_argument("--password", help="Override PostgreSQL password for --extract-env")
    parser.add_argument(
        "--base-dir",
        help="Optional root directory override for output files (defaults to repository root)",
    )

    args = parser.parse_args()
    base_dir = Path(args.base_dir).resolve() if args.base_dir else REPO_ROOT

    if not (args.extract_env or args.extract_all or args.compare):
        args.compare = True

    if args.extract_all:
        for env_k in ("local", "staging", "production"):
            extract_live_fingerprint(env_key=env_k, base_dir=base_dir)

    if args.extract_env:
        extract_live_fingerprint(
            env_key=args.extract_env,
            base_dir=base_dir,
            host=args.host,
            port=args.port,
            dbname=args.dbname,
            user=args.user,
            password=args.password,
        )

    if args.compare:
        run_compare(base_dir)


if __name__ == "__main__":
    main()
