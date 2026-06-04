"""
Transform CARB food processing facilities data into DB-ready records.

GEOCODE_TARGET controls which sheet is geocoded and loaded in a given ETL run.
The two modes are NEVER run in the same ETL execution — you manually change this
constant between runs:

  Step 1 — set GEOCODE_TARGET = "geocoder_test_set"  (the default below)
            Run the ETL. ~12 test-set rows are geocoded and loaded into the DB.
            Verify the DB looks correct (lat/lon populated, addresses clean).

  Step 2 — change GEOCODE_TARGET = "all_facilities"
            Run the ETL again. The full ~6,000-row sheet is geocoded and loaded.
            The delta check skips rows already geocoded in Step 1.
            The circuit breaker (GEOCODE_ROW_LIMIT) caps net-new geocoding per run.

To switch modes: edit the GEOCODE_TARGET line below. No env var needed.
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

# Safety cap: maximum number of addresses sent to the geocoding API in one run.
# Prevents accidental mass-geocoding. Raise or remove this limit deliberately
# once you have verified the geocoder works correctly on the test set.
GEOCODE_ROW_LIMIT = 50

# ── GEOCODE_TARGET ────────────────────────────────────────────────────────────
# Controls which sheet is geocoded and loaded. Edit this line to switch modes
#
#   "geocoder_test_set"  → geocode ~12 test rows, load only those rows (SAFE DEFAULT)
#   "all_facilities"     → geocode the full sheet, load all rows (run after verifying test set)
# ─────────────────────────────────────────────────────────────────────────────
GEOCODE_TARGET: str = "geocoder_test_set"


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
            # Only append quantity when it is non-empty; empty quantities
            # must be omitted entirely so ", ".join() never produces "100, "
            # or ", ," artifacts in the DB.
            if not (pd.isna(qty_val) or str(qty_val).strip() == ""):
                qty_values.append(str(qty_val).strip())

        byproducts.append(", ".join(bp_values) if bp_values else None)
        # If every paired quantity was empty, write None (NULL) not ""
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


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply standard cleaning pipeline to a raw sheet DataFrame."""
    df = cleaning_mod.clean_names_df(df)
    df = _dedupe_columns(df)
    df = cleaning_mod.replace_empty_with_na(df)
    return df


def _apply_geocoding(
    geocode_df: pd.DataFrame,
    logger,
) -> pd.DataFrame:
    """
    Apply delta check, circuit breaker, and geocoding to geocode_df.

    Returns geocode_df with latitude/longitude populated for rows that were
    successfully geocoded. Rows already in the DB (delta check) are skipped.
    Raises RuntimeError if the circuit breaker fires.
    """
    # Lazy imports — never at module level (avoids Docker import hangs)
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
    logger.info(f"Delta check: {len(existing_keys)} rows already geocoded in DB.")

    # Ensure lat/lon columns exist before we try to write into them
    if "latitude" not in geocode_df.columns:
        geocode_df["latitude"] = None
    if "longitude" not in geocode_df.columns:
        geocode_df["longitude"] = None

    geocode_df["address_key"] = geocode_df.apply(
        lambda r: _build_address_key(r.get("address"), r.get("city"), "CA", r.get("zip")),
        axis=1,
    )

    to_geocode = geocode_df[~geocode_df["address_key"].isin(existing_keys)].copy()
    to_geocode = to_geocode[to_geocode["address"].notna()]

    logger.info(f"Rows queued for geocoding after delta check: {len(to_geocode)}")

    if len(to_geocode) > GEOCODE_ROW_LIMIT:
        raise RuntimeError(
            f"Safety limit reached: {len(to_geocode)} rows queued for geocoding "
            f"(cap {GEOCODE_ROW_LIMIT}). Reduce the batch or raise GEOCODE_ROW_LIMIT."
        )

    if not os.getenv("GOOGLE_MAPS_API_KEY"):
        logger.info("GOOGLE_MAPS_API_KEY not set; skipping geocoding.")
        return geocode_df

    if to_geocode.empty:
        logger.info("No new rows to geocode (all already in DB).")
        return geocode_df

    address_df, _ = parse_addresses(
        to_geocode,
        address_column="address",
        lat="latitude",
        long="longitude",
    )

    to_geocode = pd.concat(
        [to_geocode.reset_index(drop=True), address_df.reset_index(drop=True)],
        axis=1,
    )
    to_geocode["latitude"] = to_geocode["closest_latitude"]
    to_geocode["longitude"] = to_geocode["closest_longitude"]

    # Write geocoded lat/lon back into geocode_df by address_key
    lat_map = to_geocode.set_index("address_key")["latitude"].to_dict()
    lon_map = to_geocode.set_index("address_key")["longitude"].to_dict()

    geocode_df["latitude"] = geocode_df["latitude"].fillna(
        geocode_df["address_key"].map(lat_map)
    )
    geocode_df["longitude"] = geocode_df["longitude"].fillna(
        geocode_df["address_key"].map(lon_map)
    )

    geocoded_count = geocode_df["latitude"].notna().sum()
    logger.info(f"Geocoding complete: {geocoded_count} rows now have coordinates.")

    return geocode_df


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

    # Clean both DataFrames
    cleaned_all = _clean_dataframe(raw_all)
    cleaned_geo = _clean_dataframe(raw_geo) if not raw_geo.empty else pd.DataFrame()

    # Add lineage tracking metadata (only to all_facilities — it carries the full record set)
    cleaned_all["etl_run_id"] = etl_run_id
    cleaned_all["lineage_group_id"] = lineage_group_id

    # Normalize address whitespace
    if "address" in cleaned_all.columns:
        cleaned_all["address"] = cleaned_all["address"].apply(_clean_address)
    if not cleaned_geo.empty and "address" in cleaned_geo.columns:
        cleaned_geo["address"] = cleaned_geo["address"].apply(_clean_address)

    # Hardcode state
    cleaned_all["state"] = "CA"
    if not cleaned_geo.empty:
        cleaned_geo["state"] = "CA"

    # ZIP cleanup
    if "zip" in cleaned_all.columns:
        cleaned_all["zip"] = cleaned_all["zip"].astype(str).str.extract(r"(\d{5})")[0]
    if not cleaned_geo.empty and "zip" in cleaned_geo.columns:
        cleaned_geo["zip"] = cleaned_geo["zip"].astype(str).str.extract(r"(\d{5})")[0]

    # Process type capitalization (all_facilities only — test set may not have this column)
    if "process" in cleaned_all.columns:
        cleaned_all["process"] = cleaned_all["process"].astype("string").str.title()

    # Combine byproducts and quantities (all_facilities only)
    byproduct_cols = [c for c in cleaned_all.columns if c.startswith("byproduct_")]
    byproduct_cols = sorted(byproduct_cols, key=lambda c: int(c.split("_")[-1]) if c.split("_")[-1].isdigit() else 999)
    quantity_cols = [c for c in cleaned_all.columns if c.startswith("quantity_tons_year")]

    if byproduct_cols:
        cleaned_all = _combine_pairs(cleaned_all, byproduct_cols, quantity_cols)
    else:
        cleaned_all["byproducts"] = None
        cleaned_all["quantities"] = None

    # Assign general_source_info (all_facilities only)
    if "associated_food" in cleaned_all.columns:
        cleaned_all["general_source_info"] = cleaned_all["associated_food"].apply(_assign_general_source_info)
    else:
        cleaned_all["general_source_info"] = "CARB 2024"

    # --- Geocoding ---
    # GEOCODE_TARGET selects which DataFrame is geocoded and returned for loading.
    # "geocoder_test_set" → geocode ~12 test rows, load only those rows.
    #                       Verify the DB, then switch to "all_facilities".
    # "all_facilities"    → geocode the full sheet (delta check + circuit breaker),
    #                       load all rows.
    # No cross-sheet propagation — each mode geocodes its own rows only.

    logger.info(f"GEOCODE_TARGET = {GEOCODE_TARGET!r}")

    if GEOCODE_TARGET == "geocoder_test_set":
        if cleaned_geo.empty:
            logger.warning(
                "GEOCODE_TARGET='geocoder_test_set' but the geocoder test set sheet is empty. "
                "Nothing to geocode or load. Switch GEOCODE_TARGET to 'all_facilities' to load "
                "the full dataset."
            )
            return pd.DataFrame()

        try:
            cleaned_geo = _apply_geocoding(cleaned_geo, logger)
        except Exception as exc:
            logger.error(f"Geocoding step failed: {exc}")
            raise

        # Add lineage to the test-set rows too
        cleaned_geo["etl_run_id"] = etl_run_id
        cleaned_geo["lineage_group_id"] = lineage_group_id
        cleaned_geo["general_source_info"] = "CARB 2024"

        target_df = cleaned_geo

    else:
        # GEOCODE_TARGET == "all_facilities"
        try:
            cleaned_all = _apply_geocoding(cleaned_all, logger)
        except Exception as exc:
            logger.error(f"Geocoding step failed: {exc}")
            raise

        target_df = cleaned_all

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

    target_df = target_df.rename(columns=rename_columns)

    # Coerce numeric lat/long if present
    target_df = coercion_mod.coerce_columns(
        target_df,
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
        if col not in target_df.columns:
            target_df[col] = None

    final_df = target_df[final_columns].copy()

    logger.info(f"Successfully transformed {len(final_df)} records (GEOCODE_TARGET={GEOCODE_TARGET!r}).")
    return final_df
