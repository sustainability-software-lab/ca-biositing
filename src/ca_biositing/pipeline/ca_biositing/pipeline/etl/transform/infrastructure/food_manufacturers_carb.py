"""
ETL Transform: Food Manufacturers (CARB).

Transforms raw CSV data from the Food Manufacturers CARB dataset into a structured
format matching InfrastructureFoodManufacturersCARB. Facility name, address, city, county, state, and zip columns
are merged with geocoded data to populate LocationAddress and Place.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes
from ca_biositing.pipeline.utils.geo_utils import parse_addresses

EXTRACT_SOURCES: List[str] = ["food_manufacturers_carb"]

MERGE_COLUMNS = ["name", "address", "city", "county", "state", "zip"]

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
    Transforms raw Food Manufacturers CARB data.

    Args:
        data_sources: Dict keyed by source name containing raw DataFrames.
        geocoded_df: DataFrame containing geocoded addresses from Google Sheets.
        etl_run_id: ID of the current ETL run.
        lineage_group_id: ID of the lineage group.

    Returns:
        A DataFrame ready for loading into infrastructure_food_manufacturing_carb.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    # CRITICAL: Lazy import models inside the task to avoid Docker import hangs
    from ca_biositing.datamodels.models import LocationAddress, Place

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

        cleaned_df = cleaning_mod.standard_clean(df)
        cleaned_df["etl_run_id"] = etl_run_id
        cleaned_df["lineage_group_id"] = lineage_group_id

        coerced_df = coercion_mod.coerce_columns(
            cleaned_df,
            int_cols=["processing_facility_id", "carb_facility_id"],
            float_cols=["latitude", "longitude"],
            datetime_cols=[],
        )
        processed_dfs.append(coerced_df)

    if not processed_dfs:
        return pd.DataFrame()

    combined_df = pd.concat(processed_dfs, ignore_index=True)

    # 3. Merge geocoded information with incoming data

    # Ensure consistent data types for merge columns to avoid type mismatch errors
    # Convert zips to string in both dataframes
    if 'zip' in combined_df.columns:
        combined_df['zip'] = combined_df['zip'].astype(str).str.strip()
        combined_df['zip'] = combined_df['zip'].replace(['nan', 'None', ''], pd.NA)

    geocoded_df = cleaning_mod.standard_clean(geocoded_df)
    if 'zip' in geocoded_df.columns:
        geocoded_df['zip'] = geocoded_df['zip'].astype(str).str.strip()
        geocoded_df['zip'] = geocoded_df['zip'].replace(['nan', 'None', ''], pd.NA)


    GEOCODED_DF_FILTER = MERGE_COLUMNS + geocoded_columns

    added_address_df = pd.merge(combined_df, geocoded_df[GEOCODED_DF_FILTER], on=MERGE_COLUMNS, how='left')

    # 4. Normalization
    normalize_columns = {}
    logger.info("Normalizing data (swapping names for IDs)...")
    normalized_df = normalize_dataframes(added_address_df, normalize_columns)[0]

    # 4b. Column Renaming — map post-clean source names to DB column names
    rename_columns = {
        # none
    }
    normalized_df = normalized_df.rename(columns=rename_columns)

    # 5. Bridge County (Place) to LocationAddress
    if "closest_geoid" in normalized_df.columns:
        logger.info("Bridging County (Place) to LocationAddress...")
        from sqlmodel import Session, select
        from ca_biositing.pipeline.utils.engine import engine

        with Session(engine) as session:
            place_to_address_map = {}

            for index, row in normalized_df.iterrows():
                geoid = row.get("closest_geoid")
                if geoid is not pd.NA and geoid is not None and geoid != "" and geoid != "00000":
                    stmt1 = select(Place).where(Place.geoid == geoid)
                    place = session.exec(stmt1).first()

                    stmt2 = select(LocationAddress).where(
                        LocationAddress.geography_id == geoid
                    )
                    address = session.exec(stmt2).first()

                    if not place:
                        place = Place(
                            geoid=geoid,
                            state_name=row.get("closest_state_name"),
                            state_fips=row.get("closest_state_fips"),
                            county_name=row.get("closest_county_name"),
                            county_fips=row.get("closest_county_fips"),
                        )
                        session.add(place)
                        session.flush()

                    if not address:
                        # Convert pandas NA to None for database insertion
                        def to_none_if_na(value):
                            return None if pd.isna(value) else value

                        address = LocationAddress(
                            geography_id=geoid,
                            address_line1=to_none_if_na(row.get("closest_address_line_1")),
                            address_line2=to_none_if_na(row.get("closest_address_line_2")),
                            city=to_none_if_na(row.get("closest_city")),
                            zip=to_none_if_na(row.get("closest_postal_code")),
                            lat=to_none_if_na(row.get("closest_latitude")),
                            lon=to_none_if_na(row.get("closest_longitude")),
                            is_anonymous=False,
                        )
                        session.add(address)
                        session.flush()

                    place_to_address_map[geoid] = address.id

            session.commit()
            normalized_df["address_id"] = normalized_df["closest_geoid"].map(
                place_to_address_map
            )
            logger.info(
                f"Mapped {len(place_to_address_map)} counties to LocationAddresses"
            )

    # 6. Final Column Selection — matches InfrastructureEthanolBiorefineries fields
    try:
        if etl_run_id:
            normalized_df["etl_run_id"] = etl_run_id
        if lineage_group_id:
            normalized_df["lineage_group_id"] = lineage_group_id

        final_df = normalized_df[
            [
                "name",
                "processing_facility_id",
                "primary_ag_product",
                "process_type",
                "byproducts",
                "quantities",
                "general_source_info",
                "carb_facility_id",
                "air_district",
                "address_id",
                'etl_run_id',
                'lineage_group_id',
            ]
        ].copy()

        logger.info(f"Successfully transformed {len(final_df)} records.")
        return final_df

    except KeyError as e:
        logger.error(f"Missing required column during transform: {e}")
        return normalized_df
