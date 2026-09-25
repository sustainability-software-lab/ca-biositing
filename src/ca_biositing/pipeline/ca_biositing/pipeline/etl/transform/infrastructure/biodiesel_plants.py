#Modified ETL Transform for Biodiesel.

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes
from ca_biositing.pipeline.utils.geo_utils import parse_addresses


# --- CONFIGURATION ---
# List the names of the extract modules this transform depends on.
# The pipeline runner provides these in the `data_sources` dictionary.
EXTRACT_SOURCES: List[str] = ["biodiesel_plants"]

# List the unique address information needed to find the geocoded address.
MERGE_COLUMNS = ["company", "city", "state"]

# don't edit
geocoded_columns = ["geocoded_status", "closest_address_line_1", "closest_address_line_2", "closest_city", "closest_county", "closest_state", "closest_postal_code", "closest_latitude", "closest_longitude", "closest_geoid", "closest_state_name", "closest_state_fips", "closest_county_name", "closest_county_fips"]

@task
def transform(
    data_sources: Dict[str, pd.DataFrame],
    geocoded_df: pd.DataFrame,
    etl_run_id: int = None,
    lineage_group_id: int = None,
) -> Optional[pd.DataFrame]:
    """
    Transforms raw biodiesel plants data.

    Args:
        data_sources: Dictionary where keys are source names and values are DataFrames.
        geocoded_df: DataFrame containing geocoded addresses from Google Sheets.
        etl_run_id: ID of the current ETL run.
        lineage_group_id: ID of the lineage group.

    Returns:
        A DataFrame ready for loading into infrastructure_biodiesel_plants.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    # CRITICAL: Lazy import models inside the task to avoid Docker import hangs
    from ca_biositing.datamodels.models import (
        LocationAddress,
        Place
        # Add other models needed for normalization here (e.g., Resource, Unit)
    )

    # 1. Input Validation
    for source_name in EXTRACT_SOURCES:
        if source_name not in data_sources:
            logger.error(f"Required data source '{source_name}' not found.")
            return None

    logger.info(f"Transforming data from sources: {EXTRACT_SOURCES}")

    # 2. Cleaning & Coercion
    processed_dfs = []
    for source_name in EXTRACT_SOURCES:
        df = data_sources[source_name].copy()

        if df.empty:
            continue

        # Standardize column names (snake_case) and basic string cleaning
        cleaned_df = cleaning_mod.standard_clean(df)

        # Add lineage tracking metadata
        cleaned_df['etl_run_id'] = etl_run_id
        cleaned_df['lineage_group_id'] = lineage_group_id


        # Coerce data types (Update these lists based on your schema)
        coerced_df = coercion_mod.coerce_columns(
            cleaned_df,
            int_cols=["capacity_mmg_per_y", "bbi_index"],
            float_cols=[],
            datetime_cols=['created_at', 'updated_at']
        )

        processed_dfs.append(coerced_df)

    if not processed_dfs:
        return pd.DataFrame()

    # Combine sources if necessary, or handle them individually
    combined_df = pd.concat(processed_dfs, ignore_index=True)

    # 3. Merge geocoded information with incoming data

    geocoded_df = cleaning_mod.standard_clean(geocoded_df)

    GEOCODED_DF_FILTER = MERGE_COLUMNS + geocoded_columns

    added_address_df = pd.merge(combined_df, geocoded_df[GEOCODED_DF_FILTER], on=MERGE_COLUMNS, how='left')

    # 4. Normalization (Name-to-ID Swapping)
    # Format: 'dataframe_column': (SQLAlchemyModel, 'lookup_field_in_db')
    normalize_columns = {

    }


    # Manual normalization for Place (County) to avoid NotNullViolation on geoid
    # and provide a resilient lookup that defaults to state-level GEOID.
    from ca_biositing.pipeline.utils.geo_utils import get_geoid
    from sqlmodel import Session, select
    from ca_biositing.pipeline.utils.engine import engine

    with Session(engine) as session:
        places = session.exec(select(Place.geoid, Place.county_name)).all()
        county_to_geoid = {p.county_name.lower(): p.geoid for p in places if p.county_name}

    logger.info("Normalizing data (swapping names for IDs)...")
    normalized_df = normalize_dataframes(added_address_df, normalize_columns)[0]


    # Bridge County (Place) to LocationAddress
    # We need to find or create a generic LocationAddress for each County
    # ALSO handle cases where geoid is '00000' but we have lat/lon coordinates
    if 'closest_geoid' in normalized_df.columns:
        logger.info("Bridging County (Place) to LocationAddress...")
        from sqlmodel import Session, select
        from ca_biositing.pipeline.utils.engine import engine

        with Session(engine) as session:
            # Get unique county_ids (these are geoids from Place table)
            place_to_address_map = {}

            # Convert pandas NA to None for database insertion
            def to_none_if_na(value):
                return None if pd.isna(value) else value

            for index, row in normalized_df.iterrows():
                geoid = row["closest_geoid"]
                has_valid_geoid = geoid is not pd.NA and geoid is not None and geoid != "" and geoid != "00000"

                # Check if we have lat/lon coordinates for this record
                # Note: geocoded data may have these as strings, need to try convert
                lat_val = row.get("closest_latitude")
                lon_val = row.get("closest_longitude")

                # Try to convert to float if they're strings
                try:
                    if pd.notna(lat_val) and lat_val != "":
                        lat_val = float(lat_val)
                    else:
                        lat_val = None
                except (ValueError, TypeError):
                    lat_val = None

                try:
                    if pd.notna(lon_val) and lon_val != "":
                        lon_val = float(lon_val)
                    else:
                        lon_val = None
                except (ValueError, TypeError):
                    lon_val = None

                has_latlon = (lat_val is not None and lon_val is not None)

                # Skip if no valid geoid AND no lat/lon
                if not has_valid_geoid and not has_latlon:
                    logger.warning(f"Row {index}: No valid geoid or lat/lon, skipping")
                    continue

                # Use index as a unique key for records without valid geoid
                map_key = geoid if has_valid_geoid else f"latlon_{index}"

                # If already processed this geoid/key, reuse the address_id
                if map_key in place_to_address_map:
                    continue

                place = None
                address = None

                if has_valid_geoid:
                    # Standard path: we have a valid geoid
                    stmt1 = select(Place).where(Place.geoid == geoid)
                    place = session.exec(stmt1).first()

                    stmt2 = select(LocationAddress).where(
                        LocationAddress.geography_id == geoid,
                    )
                    address = session.exec(stmt2).first()

                    if not place:
                        logger.info(f"Creating new Place for county geoid: {geoid}")
                        place = Place(
                            geoid=geoid,
                            state_name=row["closest_state_name"],
                            state_fips=row["closest_state_fips"],
                            county_name=row["closest_county_name"],
                            county_fips=row["closest_county_fips"],
                        )
                        session.add(place)
                        session.flush()
                else:
                    # No valid geoid, but we have lat/lon
                    # Check if we already have a LocationAddress with these exact coordinates
                    if lat_val is not None and lon_val is not None:
                        stmt2 = select(LocationAddress).where(
                            LocationAddress.lat == lat_val,
                            LocationAddress.lon == lon_val,
                            LocationAddress.geography_id.is_(None)
                        )
                        address = session.exec(stmt2).first()

                if not address:
                    # Create new LocationAddress
                    log_msg = f"Creating new LocationAddress for geoid: {geoid}" if has_valid_geoid else f"Creating new LocationAddress with lat/lon only (row {index})"
                    logger.info(log_msg)

                    address = LocationAddress(
                        geography_id=geoid if has_valid_geoid else None,
                        address_line1=to_none_if_na(row["closest_address_line_1"]),
                        address_line2=to_none_if_na(row["closest_address_line_2"]),
                        city=to_none_if_na(row["closest_city"]),
                        zip=to_none_if_na(row["closest_postal_code"]),
                        lat=lat_val,
                        lon=lon_val,
                        is_anonymous=False
                    )
                    session.add(address)
                    session.flush()

                place_to_address_map[map_key] = address.id

            session.commit()

            # Map address_ids back to the dataframe
            # For rows with valid geoid, map by geoid
            # For rows without valid geoid, map by index-based key
            def get_address_id(row_idx, row):
                geoid = row["closest_geoid"]
                has_valid_geoid = geoid is not pd.NA and geoid is not None and geoid != "" and geoid != "00000"
                map_key = geoid if has_valid_geoid else f"latlon_{row_idx}"
                return place_to_address_map.get(map_key)

            normalized_df['address_id'] = [
                get_address_id(idx, row)
                for idx, row in normalized_df.iterrows()
            ]

            logger.info(f"Created/mapped {len(place_to_address_map)} LocationAddress records")
            valid_addresses = normalized_df['address_id'].notna().sum()
            logger.info(f"Successfully assigned address_id to {valid_addresses}/{len(normalized_df)} records")



    # 5. Final Mapping & Selection
    # TODO: Update this list to match the columns in your target database table
    try:
        # Ensure lineage columns exist even if not provided in input
        if etl_run_id:
            normalized_df['etl_run_id'] = etl_run_id
        if lineage_group_id:
            normalized_df['lineage_group_id'] = lineage_group_id

        final_df = normalized_df[[
            "company",
            "bbi_index",
            "city",
            "state",
            "capacity_mmg_per_y",
            "feedstock",
            "status",
            "address_id",
            "coordinates",
            "latitude",
            "longitude",
            "source",
            'etl_run_id',
            'lineage_group_id',
        ]].copy()

        logger.info(f"Successfully transformed {len(final_df)} records.")
        return final_df

    except KeyError as e:
        logger.error(f"Missing required column during transform: {e}")
        return normalized_df
