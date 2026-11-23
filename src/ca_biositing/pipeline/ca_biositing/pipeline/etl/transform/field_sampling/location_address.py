"""
ETL Transform for LocationAddress (FieldSample county-only workflow).

Transforms raw sample metadata from SampleMetadata worksheets into unique
county-level anonymous LocationAddress records using the 6-tier offline-first
county resolver (`resolve_county_geoid`).
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import pandas as pd
from prefect import get_run_logger, task

from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.geo_utils import resolve_county_geoid


def _is_non_empty(val: object) -> bool:
    """Return True when ``val`` contains a non-missing, non-blank value."""
    if val is None:
        return False
    try:
        if pd.isna(val):
            return False
    except Exception:
        pass
    s = str(val).strip()
    return bool(s) and s.lower() not in {"nan", "none", "null", "n/a", "na", "-", "<na>"}


def _build_anonymous_row(geoid: str, location_type: str) -> dict[str, object]:
    """Construct a county-only anonymous LocationAddress record dict."""
    return {
        "geography_id": geoid,
        "address_line1": None,
        "address_line2": None,
        "city": None,
        "zip": None,
        "lat": None,
        "lon": None,
        "is_anonymous": True,
        "location_type": location_type,
    }


@task
def transform_location_address(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None,
) -> Optional[pd.DataFrame]:
    """Extract unique county-level anonymous LocationAddress records from sample metadata.

    Combines county resolution across:
    - Collection locations from ``02_Sample_Desc``
    - Producer/facility locations from ``04_Producers``
    - Field storage locations from ``03_Qty_FieldStorage``

    All sub-county columns are unconditionally set to ``None`` and
    ``is_anonymous`` is forced to ``True``. Raw sub-county columns are never
    included in the returned DataFrame or logged.
    """
    try:
        logger = get_run_logger()
    except Exception:
        logger = logging.getLogger(__name__)

    sample_desc = data_sources.get("sample_desc", pd.DataFrame())
    producers = data_sources.get("producers", pd.DataFrame())
    qty_field_storage = data_sources.get("qty_field_storage", pd.DataFrame())

    if sample_desc.empty and producers.empty and qty_field_storage.empty:
        logger.warning("LocationAddress data sources are empty.")
        return pd.DataFrame()

    logger.info("Extracting unique county-level LocationAddress records from multi-worksheet sources...")
    logger.info(f"  - sample_desc: {len(sample_desc)} rows")
    logger.info(f"  - producers: {len(producers)} rows")
    logger.info(f"  - qty_field_storage: {len(qty_field_storage)} rows")

    clean_sample_desc = (
        cleaning_mod.standard_clean(sample_desc) if not sample_desc.empty else pd.DataFrame()
    )
    clean_producers = (
        cleaning_mod.standard_clean(producers) if not producers.empty else pd.DataFrame()
    )
    clean_qty_storage = (
        cleaning_mod.standard_clean(qty_field_storage)
        if not qty_field_storage.empty
        else pd.DataFrame()
    )

    candidate_rows: list[dict[str, object]] = []

    # 1. Extract collection-site counties from sample_desc
    if not clean_sample_desc.empty:
        sample_cols = [
            "sampling_county",
            "sampling_latlong",
            "sampling_zip",
            "sampling_city",
            "sampling_street",
            "sampling_location",
        ]
        available_cols = [c for c in sample_cols if c in clean_sample_desc.columns]
        if available_cols:
            subset = clean_sample_desc[available_cols].drop_duplicates().dropna(how="all")
            for _, row in subset.iterrows():
                if not any(_is_non_empty(row.get(c)) for c in available_cols):
                    continue
                geoid = resolve_county_geoid(
                    county=row.get("sampling_county"),
                    latlong=row.get("sampling_latlong"),
                    zip_code=row.get("sampling_zip"),
                    city=row.get("sampling_city"),
                    street=row.get("sampling_street"),
                    location_desc=row.get("sampling_location"),
                )
                candidate_rows.append(_build_anonymous_row(geoid, "collection_site"))

    # 2. Extract producer/facility counties from producers
    if not clean_producers.empty:
        producer_cols = [
            "prod_county",
            "prod_latlong",
            "prod_zip",
            "prod_city",
            "prod_street",
            "prod_location",
        ]
        available_cols = [c for c in producer_cols if c in clean_producers.columns]
        if available_cols:
            subset = clean_producers[available_cols].drop_duplicates().dropna(how="all")
            for _, row in subset.iterrows():
                if not any(_is_non_empty(row.get(c)) for c in available_cols):
                    continue
                geoid = resolve_county_geoid(
                    county=row.get("prod_county"),
                    latlong=row.get("prod_latlong"),
                    zip_code=row.get("prod_zip"),
                    city=row.get("prod_city"),
                    street=row.get("prod_street"),
                    location_desc=row.get("prod_location"),
                )
                candidate_rows.append(_build_anonymous_row(geoid, "facility_storage"))

    # 3. Extract field storage counties from qty_field_storage
    if not clean_qty_storage.empty:
        storage_cols = ["fieldstorage_location", "field_storage_location"]
        available_cols = [c for c in storage_cols if c in clean_qty_storage.columns]
        if available_cols:
            subset = clean_qty_storage[available_cols].drop_duplicates().dropna(how="all")
            for _, row in subset.iterrows():
                val = next(
                    (row.get(c) for c in available_cols if _is_non_empty(row.get(c))),
                    None,
                )
                if val is None:
                    continue
                geoid = resolve_county_geoid(county=val, city=val, location_desc=val)
                candidate_rows.append(_build_anonymous_row(geoid, "collection_site"))

    if not candidate_rows:
        logger.warning("No location data found in any source.")
        return pd.DataFrame()

    all_locations = (
        pd.DataFrame(candidate_rows)
        .drop_duplicates(subset=["geography_id"], keep="first")
        .reset_index(drop=True)
    )
    all_locations["is_anonymous"] = True

    if etl_run_id:
        all_locations["etl_run_id"] = etl_run_id
    if lineage_group_id:
        all_locations["lineage_group_id"] = lineage_group_id

    logger.info(
        f"Successfully transformed {len(all_locations)} unique anonymous county location records."
    )
    return all_locations
