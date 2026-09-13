"""
ETL Transform: MSW-to-Energy Anaerobic Digesters.

Transforms raw CSV data from the MSW-to-Energy Anaerobic Digesters dataset into a
structured format matching InfrastructureMswToEnergyAnaerobicDigesters. City and county
columns are merged and geocoded via parse_addresses to populate LocationAddress and Place.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes
from ca_biositing.pipeline.utils.geo_utils import parse_addresses

EXTRACT_SOURCES: List[str] = ["msw_to_energy_anaerobic_digesters"]


@task
def transform(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: int = None,
    lineage_group_id: int = None,
) -> Optional[pd.DataFrame]:
    """
    Transforms raw MSW-to-energy anaerobic digesters data.

    Args:
        data_sources: Dict keyed by source name containing raw DataFrames.
        etl_run_id: ID of the current ETL run.
        lineage_group_id: ID of the lineage group.

    Returns:
        A DataFrame ready for loading into infrastructure_msw_to_energy_anaerobic_digesters.
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
            int_cols=[],
            float_cols=[
                "equivalent_generation",
                "dayload",
                "dayloadbdt",
                "latitude",
                "longitude",
            ],
            datetime_cols=[],
        )
        processed_dfs.append(coerced_df)

    if not processed_dfs:
        return pd.DataFrame()

    combined_df = pd.concat(processed_dfs, ignore_index=True)

    # 3. Geocode addresses — city and county are available
    address_df, geoid_df = parse_addresses(
        combined_df,
        merge_columns=["city", "county"],
        lat="latitude",
        long="longitude",
    )

    added_address_df = pd.concat([combined_df, address_df, geoid_df], axis=1)

    # 4. Normalization
    normalize_columns = {}
    logger.info("Normalizing data (swapping names for IDs)...")
    normalized_df = normalize_dataframes(added_address_df, normalize_columns)[0]

    # 4b. Column Renaming — map post-clean source names to DB column names
    rename_columns = {
        "dayloadbdt": "dayload_bdt",
    }
    normalized_df = normalized_df.rename(columns=rename_columns)

    # 5. Bridge County (Place) to LocationAddress
    if "closest_geoid" in normalized_df.columns:
        logger.info("Bridging County (Place) to LocationAddress...")
        from sqlmodel import Session, select
        from ca_biositing.pipeline.utils.engine import engine

        with Session(engine) as session:
            place_to_address_map = {}

            # Helper function to convert pandas NA/NaN to None for database insertion
            def to_none_if_na(value):
                """Convert pandas NA, NaN, None, or empty string to None."""
                if value is None:
                    return None
                if pd.isna(value):
                    return None
                if isinstance(value, str) and value.strip() == "":
                    return None
                return value

            for index, row in normalized_df.iterrows():
                geoid = row.get("closest_geoid")
                # Properly handle all types of NA/NaN values
                if pd.isna(geoid) or geoid is None or geoid == "" or geoid == "00000":
                    continue

                # Convert to string to ensure proper comparison
                geoid = str(geoid).strip()
                if not geoid or geoid == "00000":
                    continue

                stmt1 = select(Place).where(Place.geoid == geoid)
                place = session.exec(stmt1).first()

                stmt2 = select(LocationAddress).where(
                    LocationAddress.geography_id == geoid
                )
                address = session.exec(stmt2).first()

                if not place:
                    place = Place(
                        geoid=geoid,
                        state_name=to_none_if_na(row.get("closest_state_name")),
                        state_fips=to_none_if_na(row.get("closest_state_fips")),
                        county_name=to_none_if_na(row.get("closest_county_name")),
                        county_fips=to_none_if_na(row.get("closest_county_fips")),
                    )
                    session.add(place)
                    session.flush()

                if not address:
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

    # 6. Final Column Selection — matches InfrastructureMswToEnergyAnaerobicDigesters
    try:
        if etl_run_id:
            normalized_df["etl_run_id"] = etl_run_id
        if lineage_group_id:
            normalized_df["lineage_group_id"] = lineage_group_id

        final_df = normalized_df[
            [
                "equivalent_generation",
                "feedstock",
                "dayload",
                "dayload_bdt",
                "facility_type",
                "status",
                "notes",
                "source",
                "type",
                "wkt_geom",
                "geom",
                "latitude",
                "longitude",
                "address_id",
            ]
        ].copy()

        logger.info(f"Successfully transformed {len(final_df)} records.")
        return final_df

    except KeyError as e:
        logger.error(f"Missing required column during transform: {e}")
        return normalized_df
