"""
ETL Transform: Crude Oil Pipelines.

Transforms raw GeoJSON data from the US Crude Oil Pipelines dataset into a
structured format matching InfrastructureCrudeOilPipelines.

The pipeline geometry (MULTILINESTRING) is converted from GeoDataFrame WKB
to a hex-encoded WKB string that PostGIS accepts on insert.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes

EXTRACT_SOURCES: List[str] = ["crude_oil_pipelines"]


@task
def transform(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: int = None,
    lineage_group_id: int = None,
) -> Optional[pd.DataFrame]:
    """
    Transforms raw crude oil pipeline GeoJSON data.

    Args:
        data_sources: Dict keyed by source name containing raw GeoDataFrames.
        etl_run_id: ID of the current ETL run.
        lineage_group_id: ID of the lineage group.

    Returns:
        A DataFrame ready for loading into infrastructure_crude_oil_pipelines.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

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

        # Convert geometry column to WKB hex string for PostGIS insert
        if "geometry" in df.columns:
            df["geom"] = df["geometry"].apply(
                lambda g: g.wkb_hex if g is not None else None
            )
            df = df.drop(columns=["geometry"])

        # Standardize column names to snake_case
        cleaned_df = cleaning_mod.standard_clean(df)

        cleaned_df["etl_run_id"] = etl_run_id
        cleaned_df["lineage_group_id"] = lineage_group_id

        coerced_df = coercion_mod.coerce_columns(
            cleaned_df,
            int_cols=["artificial", "objectid"],
            float_cols=["master_oid", "volume", "capacity", "shape_length", "vcr", "length"],
            datetime_cols=["created_at", "updated_at"],
        )
        processed_dfs.append(coerced_df)

    if not processed_dfs:
        return pd.DataFrame()

    combined_df = pd.concat(processed_dfs, ignore_index=True)

    # 4. Normalization
    normalize_columns = {}
    logger.info("Normalizing data (swapping names for IDs)...")
    normalized_df = normalize_dataframes(combined_df, normalize_columns)[0]

    # 4b. Column Renaming — map post-clean source names to DB column names
    rename_columns = {
        "objectid": "object_id",
        "opername": "operator_name",
        "pipename": "pipeline_name",
        "type": "pipeline_type"
    }
    normalized_df = normalized_df.rename(columns=rename_columns)

    # 5. Final Column Selection — matches InfrastructurePetroleumPipelines fields
    try:
        if etl_run_id:
            normalized_df["etl_run_id"] = etl_run_id
        if lineage_group_id:
            normalized_df["lineage_group_id"] = lineage_group_id

        final_df = normalized_df[
            [
                "object_id",
                "operator_name",
                "pipeline_name",
                "source",
                "pipeline_type",
                "notes",
                "artificial",
                "master_oid",
                "commodity",
                "volume",
                "capacity",
                "vcr",
                "shape_length",
                "mode_type",
                "length",
                "geom",
            ]
        ].copy()

        logger.info(f"Successfully transformed {len(final_df)} records.")
        return final_df

    except KeyError as e:
        logger.error(f"Missing required column during transform: {e}")
        return combined_df
