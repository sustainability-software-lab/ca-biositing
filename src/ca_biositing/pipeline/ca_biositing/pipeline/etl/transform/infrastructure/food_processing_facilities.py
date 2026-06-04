"""
Transform CARB food processing facilities data into DB-ready records.
"""

from __future__ import annotations

from typing import Dict, Optional, List
import os
import pandas as pd
import numpy as np
from prefect import task, get_run_logger

from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.geo_utils import parse_addresses

EXTRACT_SOURCES: List[str] = ["all_facilities", "geocoder_test_set"]

GEOCODE_ROW_LIMIT = 50


def _dedupe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure column names are unique by appending numeric suffixes."""
    cols = []
    seen = {}
    for col in df.columns:
        if col not in seen:
            seen[col] = 1
            cols.append(col)
            continue
        seen[col] += 1
        cols.append(f"{col}_{seen[col]}")
    df = df.copy()
    df.columns = cols
    return df


def _clean_address(text: Optional[str]) -> Optional[str]:
    if text is None or pd.isna(text):
        return None
    cleaned = str(text).replace("\n", " ").replace("\r", " ")
    cleaned = " ".join(cleaned.split())
    return cleaned.strip() if cleaned.strip() else None


def _normalize_text(text: Optional[str]) -> str:
    if text is None or pd.isna(text):
        return ""
    return " ".join(str(text).strip().lower().split())


def _build_address_key(address: Optional[str], city: Optional[str], state: Optional[str], zip_code: Optional[str]) -> str:
    parts = [address, city, state, zip_code]
    norm_parts = [_normalize_text(p) for p in parts]
    return "|".join(norm_parts)


def _combine_pairs(df: pd.DataFrame, byproduct_cols: List[str], quantity_cols: List[str]) -> pd.DataFrame:
    byproducts = []
    quantities = []

    for _, row in df.iterrows():
        bp_values = []
        qty_values = []
        for idx, bp_col in enumerate(byproduct_cols):
            bp_val = row.get(bp_col)
            qty_col = quantity_cols[idx] if idx < len(quantity_cols) else None
            qty_val = row.get(qty_col) if qty_col else None

            if pd.isna(bp_val) or str(bp_val).strip() == "":
                continue

            bp_values.append(str(bp_val).strip())
            # FIX: only append quantity when it is non-empty; empty quantities
            # must be omitted entirely so ", ".join() never produces "100, "
            # or ", ," artifacts in the DB.
            if not (pd.isna(qty_val) or str(qty_val).strip() == ""):
                qty_values.append(str(qty_val).strip())

        byproducts.append(", ".join(bp_values) if bp_values else None)
        # FIX: if every paired quantity was empty, write None (NULL) not ""
        quantities.append(", ".join(qty_values) if qty_values else None)

    out = df.copy()
    out["byproducts"] = byproducts
    out["quantities"] = quantities
    return out


def _assign_general_source_info(associated_food: Optional[str]) -> str:
    food_norm = _normalize_text(associated_food)
    if "tomato" in food_norm:
        return "Processing Tomato Advisory Board 2022"
    if "grape" in food_norm or "wine" in food_norm or "beer" in food_norm:
        return "California Department of Alcoholic Beverage Control 2024"
    return "CARB 2024"


# Expected real header names (lowercase, stripped) that should appear in the header row.
_EXPECTED_HEADERS = {"facility id", "name", "address", "city", "zip", "county"}


def _fix_header_row(df: pd.DataFrame) -> pd.DataFrame:
    """Detect and fix sheets where row 0 is a spurious title row and row 1 contains real headers.

    Some Google Sheets have a frozen/merged title row at the top. When gsheet_to_df reads
    all_values[0] as the header, it picks up the title row instead of the real column names.
    This function detects that pattern by checking if the first data row looks like real headers,
    and if so promotes it to be the column names.
    """
    if df.empty or len(df) < 2:
        return df
    first_row_values = {str(v).strip().lower() for v in df.iloc[0].values if str(v).strip()}
    if _EXPECTED_HEADERS.issubset(first_row_values):
        # First data row contains the real headers — promote it
        new_df = df.iloc[1:].copy()
        new_df.columns = [str(v).strip() for v in df.iloc[0].values]
        new_df = new_df.reset_index(drop=True)
        return new_df
    return df


@task
def transform(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: int | None = None,
    lineage_group_id: int | None = None,
) -> Optional[pd.DataFrame]:
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    for source_name in EXTRACT_SOURCES:
        if source_name not in data_sources:
            logger.error(f"Required data source '{source_name}' not found.")
            return None

    raw_all = data_sources["all_facilities"].copy()
    raw_geo = data_sources["geocoder_test_set"].copy()

    if raw_all.empty:
        logger.error("All facilities sheet is empty.")
        return None

    # Detect and fix sheets where a spurious title row precedes the real headers.
    raw_all = _fix_header_row(raw_all)
    if raw_all.empty:
        logger.error("All facilities sheet is empty after header-row fix.")
        return None

    # Clean column names without lowercasing values.
    cleaned_all = cleaning_mod.clean_names_df(raw_all)
    cleaned_all = _dedupe_columns(cleaned_all)
    cleaned_all = cleaning_mod.replace_empty_with_na(cleaned_all)

    cleaned_geo = cleaning_mod.clean_names_df(raw_geo)
    cleaned_geo = _dedupe_columns(cleaned_geo)
    cleaned_geo = cleaning_mod.replace_empty_with_na(cleaned_geo)

    # Add lineage tracking metadata
    cleaned_all["etl_run_id"] = etl_run_id
    cleaned_all["lineage_group_id"] = lineage_group_id

    # Normalize address whitespace
    if "address" in cleaned_all.columns:
        cleaned_all["address"] = cleaned_all["address"].apply(_clean_address)
    if "address" in cleaned_geo.columns:
        cleaned_geo["address"] = cleaned_geo["address"].apply(_clean_address)

    # Hardcode state when missing
    cleaned_all["state"] = "CA"

    # ZIP cleanup
    if "zip" in cleaned_all.columns:
        cleaned_all["zip"] = cleaned_all["zip"].astype(str).str.extract(r"(\d{5})")[0]

    # Process type capitalization
    if "process" in cleaned_all.columns:
        cleaned_all["process"] = cleaned_all["process"].astype("string").str.title()

    # Combine byproducts and quantities
    byproduct_cols = [c for c in cleaned_all.columns if c.startswith("byproduct_")]
    byproduct_cols = sorted(byproduct_cols, key=lambda c: int(c.split("_")[-1]) if c.split("_")[-1].isdigit() else 999)
    quantity_cols = [c for c in cleaned_all.columns if c.startswith("quantity_tons_year")]

    if byproduct_cols:
        cleaned_all = _combine_pairs(cleaned_all, byproduct_cols, quantity_cols)
    else:
        cleaned_all["byproducts"] = None
        cleaned_all["quantities"] = None

    # Assign general_source_info
    if "associated_food" in cleaned_all.columns:
        cleaned_all["general_source_info"] = cleaned_all["associated_food"].apply(_assign_general_source_info)
    else:
        cleaned_all["general_source_info"] = "CARB 2024"

    # Geocoding safeguards: only test tab + delta check + circuit breaker
    if not cleaned_geo.empty:
        try:
            from sqlmodel import Session, select
            from ca_biositing.pipeline.utils.engine import get_engine
            from ca_biositing.datamodels.models import InfrastructureFoodProcessingFacilities

            engine = get_engine()
            with Session(engine) as session:
                rows = session.exec(
                    select(
                        InfrastructureFoodProcessingFacilities.address,
                        InfrastructureFoodProcessingFacilities.city,
                        InfrastructureFoodProcessingFacilities.state,
                        InfrastructureFoodProcessingFacilities.zip,
                    ).where(
                        InfrastructureFoodProcessingFacilities.latitude.isnot(None),
                        InfrastructureFoodProcessingFacilities.longitude.isnot(None),
                    )
                ).all()

            existing_keys = {
                _build_address_key(r[0], r[1], r[2], r[3]) for r in rows
            }

            cleaned_geo["address_key"] = cleaned_geo.apply(
                lambda r: _build_address_key(r.get("address"), r.get("city"), "CA", r.get("zip")),
                axis=1,
            )

            to_geocode = cleaned_geo[~cleaned_geo["address_key"].isin(existing_keys)].copy()
            to_geocode = to_geocode[to_geocode["address"].notna()]

            if len(to_geocode) > GEOCODE_ROW_LIMIT:
                raise RuntimeError(
                    f"Safety limit reached: {len(to_geocode)} rows queued for geocoding (cap {GEOCODE_ROW_LIMIT})."
                )

            if os.getenv("GOOGLE_MAPS_API_KEY"):
                address_df, _ = parse_addresses(
                    to_geocode,
                    address_column="address",
                    lat="latitude",
                    long="longitude",
                )

                to_geocode = pd.concat([to_geocode.reset_index(drop=True), address_df.reset_index(drop=True)], axis=1)
                to_geocode["latitude"] = to_geocode["closest_latitude"]
                to_geocode["longitude"] = to_geocode["closest_longitude"]

                lat_map = to_geocode.set_index("address_key")["latitude"].to_dict()
                lon_map = to_geocode.set_index("address_key")["longitude"].to_dict()

                cleaned_all["address_key"] = cleaned_all.apply(
                    lambda r: _build_address_key(r.get("address"), r.get("city"), "CA", r.get("zip")),
                    axis=1,
                )

                cleaned_all["latitude"] = cleaned_all["latitude"].fillna(cleaned_all["address_key"].map(lat_map))
                cleaned_all["longitude"] = cleaned_all["longitude"].fillna(cleaned_all["address_key"].map(lon_map))

            else:
                logger.info("GOOGLE_MAPS_API_KEY not set; skipping geocoding.")

        except Exception as exc:
            logger.error(f"Geocoding step failed: {exc}")
            raise

    # Final rename mapping
    rename_columns = {
        "facility_id": "CARB_facility_id",
        "air_district": "air_district",
        "name": "name",
        "address": "address",
        "city": "city",
        "county": "county",
        "zip": "zip",
        "process": "process_type",
        "associated_food": "primary_ag_product",
    }

    cleaned_all = cleaned_all.rename(columns=rename_columns)

    # Coerce numeric lat/long if present
    cleaned_all = coercion_mod.coerce_columns(
        cleaned_all,
        float_cols=["latitude", "longitude"],
    )

    final_columns = [
        "CARB_facility_id",
        "name",
        "address",
        "city",
        "zip",
        "county",
        "air_district",
        "process_type",
        "primary_ag_product",
        "byproducts",
        "quantities",
        "processing_capacity_products",
        "processing_capacity_ton_hr",
        "general_source_info",
        "source_url",
        "state",
        "latitude",
        "longitude",
        "geom",
        "EPA_facility_id",
        "NAICS_code",
        "NAICS_code_description",
        "phone_number",
        "website",
        "excess_food_estimate_low",
        "excess_food_estimate_high",
        "created_at",
        "updated_at",
        "etl_run_id",
        "lineage_group_id",
    ]

    for col in final_columns:
        if col not in cleaned_all.columns:
            cleaned_all[col] = None

    final_df = cleaned_all[final_columns].copy()

    logger.info(f"Successfully transformed {len(final_df)} records.")
    return final_df
