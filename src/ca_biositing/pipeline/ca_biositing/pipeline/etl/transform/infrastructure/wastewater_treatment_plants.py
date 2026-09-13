"""
ETL Transform: Wastewater Treatment Plants.

Transforms raw CSV data from the Wastewater Treatment Plants dataset into a structured
format matching InfrastructureWastewaterTreatmentPlants. City, county, and state columns
are merged and geocoded via parse_addresses to populate LocationAddress and Place.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes
from ca_biositing.pipeline.utils.geo_utils import parse_addresses

EXTRACT_SOURCES: List[str] = ["wastewater_treatment_plants"]

MERGE_COLUMNS = ["name_1", "city", "state", "county", "zipcode"]

# don't edit
geocoded_columns = ["geocoded_status", "closest_address_line_1", "closest_address_line_2", "closest_city", "closest_county", "closest_state", "closest_postal_code", "closest_latitude", "closest_longitude", "closest_geoid", "closest_state_name", "closest_state_fips", "closest_county_name", "closest_county_fips","address_id"]

@task
def transform(
    data_sources: Dict[str, pd.DataFrame],
    geocoded_df: pd.DataFrame,
    etl_run_id: int = None,
    lineage_group_id: int = None,
) -> Optional[pd.DataFrame]:
    """
    Transforms raw wastewater treatment plants data.

    Args:
        data_sources: Dict keyed by source name containing raw DataFrames.
        geocoded_df: DataFrame containing geocoded addresses from Google Sheets.
        etl_run_id: ID of the current ETL run.
        lineage_group_id: ID of the lineage group.

    Returns:
        A DataFrame ready for loading into infrastructure_wastewater_treatment_plants.
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
                "flow_design_adjusted_mgd",
                "flow_average_mgd",
                "biosolids_bdt_yr",
                "excess_flow_mgd",
                "_excess_mass_loading_rate_bdt_d_",
                "_excess_mass_loading_rate_wet_t_d_",
                "_methane_production_ft3_d_",
                "energy_content_btu_d",
                "_electric_kw_",
                "thermal_mmbtu_d",
                "_electric_kwh_",
                "thermal_annual_mmbtu_y",
                "dayloadbdt",
                "dayload",
                "equivalent_generation",
                "latitude",
                "longitude",
            ],
            datetime_cols=[],
        )
        processed_dfs.append(coerced_df)

    if not processed_dfs:
        return pd.DataFrame()

    combined_df = pd.concat(processed_dfs, ignore_index=True)

    # 3. Merge geocoded information with incoming data

    geocoded_df = cleaning_mod.standard_clean(geocoded_df)
    GEOCODED_DF_FILTER = MERGE_COLUMNS + geocoded_columns

    added_address_df = pd.merge(combined_df, geocoded_df[GEOCODED_DF_FILTER], on=MERGE_COLUMNS, how='left')

    # 4. Normalization
    normalize_columns = {}
    logger.info("Normalizing data (swapping names for IDs)...")
    normalized_df = normalize_dataframes(added_address_df, normalize_columns)[0]

    # 4b. Column Renaming — map post-clean source names to DB column names
    rename_columns = {
        "name_1": "name",
        "flow_average_mgd": "flow_average",
        "biosolids_bdt_yr": "biosolids",
        "excess_flow_mgd": "excess_flow",
        "_excess_mass_loading_rate_bdt_d_": "excess_mass_loading_rate",
        "_excess_mass_loading_rate_wet_t_d_": "excess_mass_loading_rate_wet",
        "_methane_production_ft3_d_": "methane_production",
        "energy_content_btu_d": "energy_content",
        "_electric_kw_": "electric_kw",
        "_electric_kwh_": "electric_kwh",
        "dayloadbdt": "dayload_bdt"
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
                            address_line1=to_none_if_na(row["closest_address_line_1"]),
                            address_line2=to_none_if_na(row["closest_address_line_2"]),
                            city=to_none_if_na(row["closest_city"]),
                            zip=to_none_if_na(row["closest_postal_code"]),
                            lat=to_none_if_na(row["closest_latitude"]),
                            lon=to_none_if_na(row["closest_longitude"]),
                            is_anonymous=False
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

    # 6. Final Column Selection — matches InfrastructureWastewaterTreatmentPlants fields
    try:
        if etl_run_id:
            normalized_df["etl_run_id"] = etl_run_id
        if lineage_group_id:
            normalized_df["lineage_group_id"] = lineage_group_id

        final_df = normalized_df[
            [
                "name",
                "codigestion",
                "flow_design_adjusted",
                "flow_average",
                "biosolids",
                "excess_flow",
                "biogas_utilized",
                "flaring",
                "excess_mass_loading_rate",
                "excess_mass_loading_rate_wet",
                "methane_production",
                "energy_content",
                "electric_kw",
                "thermal_mmbtu_d",
                "electric_kwh",
                "thermal_annual_mmbtu_y",
                "anaerobic_digestion_facility",
                "dayload_bdt",
                "dayload",
                "equivalent_generation",
                "facility_type",
                "feedstock",
                "type",
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
