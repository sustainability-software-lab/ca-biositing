"""
ETL Transform Template.


This module provides a template for transforming raw data from multiple sources.
It includes standard cleaning, coercion, and normalization patterns used in the pipeline.
"""

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

@task
def transform(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: int = None,
    lineage_group_id: int = None
) -> Optional[pd.DataFrame]:
    """
    Transforms raw data from multiple sources into a structured format.

    Args:
        data_sources: Dictionary where keys are source names and values are DataFrames.
        etl_run_id: ID of the current ETL run.
        lineage_group_id: ID of the lineage group.
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

        # if address = null add state + city
        cleaned_df["address"] = np.where(cleaned_df["address"].isna(), cleaned_df["city"] + " " + cleaned_df["state"], cleaned_df["address"])

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

    address_df, geoid_df = parse_addresses(combined_df, address_column="address", lat="latitude", long="longitude")

    added_address_df = pd.concat([combined_df, address_df, geoid_df], axis=1)

    # 3. Normalization (Name-to-ID Swapping)
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
    if 'closest_geoid' in normalized_df.columns:
        logger.info("Bridging County (Place) to LocationAddress...")
        from sqlmodel import Session, select
        from ca_biositing.pipeline.utils.engine import engine

        with Session(engine) as session:
            # Get unique county_ids (these are geoids from Place table)
            county_ids = normalized_df['closest_geoid'].dropna().unique()
            place_to_address_map = {}

            for index, row in normalized_df.iterrows():
                # Find or create LocationAddress and Place where geography_id = geoid
                geoid = row["closest_geoid"]
                if geoid != None:
                    stmt1 = select(Place).where(
                        Place.geoid == geoid
                    )
                    place = session.exec(stmt1).first()

                    stmt2 = select(LocationAddress).where(
                        LocationAddress.geography_id == geoid,
                        # LocationAddress.address_line1 == None
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

                    if not address:
                        logger.info(f"Creating new generic LocationAddress for county geoid: {geoid}")

                        address = LocationAddress(
                            geography_id=geoid,
                            address_line1=row["closest_address_line_1"],
                            address_line2=row["closest_address_line_2"],
                            city=row["closest_city"],
                            zip=row["closest_postal_code"],
                            lat=row["closest_latitude"],
                            lon=row["closest_longitude"],
                            is_anonymous=False
                            )
                        session.add(address)
                        session.flush()

                    place_to_address_map[geoid] = address.id

            session.commit()

            # Map county_id (Place.geoid) to sampling_location_id (LocationAddress.id)
            normalized_df['address'] = normalized_df['closest_geoid'].map(place_to_address_map)
            logger.info(f"Mapped {len(place_to_address_map)} counties to LocationAddresses")


    # 4. Column Renaming
    # TODO: Update this dictionary to match your source-to-target mapping

    rename_columns = {

    }
    normalized_df = normalized_df.rename(columns=rename_columns)

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
            "address",
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
