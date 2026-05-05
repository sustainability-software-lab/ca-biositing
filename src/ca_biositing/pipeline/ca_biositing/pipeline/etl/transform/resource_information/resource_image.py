"""
ETL Transform for Resource Images.

Transforms raw resource image data into ResourceImage table format.
"""

import pandas as pd
from typing import List, Optional, Dict
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes

# List the names of the extract modules this transform depends on.
EXTRACT_SOURCES: List[str] = ["resource_images"]

@task
def transform_resource_images(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None
) -> Optional[pd.DataFrame]:
    """
    Transforms raw resource image data into ResourceImage format.

    Args:
        data_sources: Dictionary where keys are source names and values are DataFrames.
        etl_run_id: ID of the current ETL run.
        lineage_group_id: ID of the lineage group.

    Returns:
        Transformed DataFrame with columns: resource_id, resource_name, image_url,
        sort_order, etl_run_id, lineage_group_id, created_at, updated_at
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    # CRITICAL: Lazy import models inside the task to avoid Docker import hangs
    from ca_biositing.datamodels.models import Resource

    # 1. Input Validation
    if "resource_images" not in data_sources:
        logger.error("Required data source 'resource_images' not found.")
        return None

    df = data_sources["resource_images"].copy()
    if df.empty:
        logger.warning("Source 'resource_images' is empty.")
        return pd.DataFrame()

    logger.info("Transforming resource image data...")

    # 2. Cleaning & Coercion
    # standard_clean will convert column names to snake_case
    clean_df = cleaning_mod.standard_clean(df)

    if clean_df is None:
        logger.error("Standard clean returned None")
        return pd.DataFrame()

    # Drop existing resource_id if present, as it might be stale/incorrect in the source
    if 'resource_id' in clean_df.columns:
        logger.info("Dropping existing resource_id from source data to ensure fresh lookup.")
        clean_df = clean_df.drop(columns=['resource_id'])

    # Ensure we have the 'resource' column for name-to-ID lookup
    if 'resource' not in clean_df.columns:
        logger.error(f"Required column 'resource' missing for lookup. Available: {clean_df.columns.tolist()}")
        return pd.DataFrame()

    # 3. Preserve the resource name and perform ID lookup
    # Copy 'resource' to 'resource_name' before normalization renames it to 'resource_id'
    clean_df['resource_name'] = clean_df['resource']

    # Coerce columns before normalization
    coerced_df = coercion_mod.coerce_columns(
        clean_df,
        int_cols=['sort_order'],
        float_cols=[],
        datetime_cols=['created_at', 'updated_at']
    )

    normalize_columns = {
        'resource': (Resource, 'name'),
    }

    logger.info("Normalizing data (looking up fresh resource_ids from names)...")
    normalized_dfs = normalize_dataframes(coerced_df, normalize_columns)
    normalized_df = normalized_dfs[0]

    # 4. Prepare output DataFrame
    # Expected output columns: resource_id, resource_name, image_url, sort_order, etl_run_id, lineage_group_id
    output_columns = ['resource_id', 'resource_name', 'image_url', 'sort_order']

    # Filter for columns that exist
    available_cols = [col for col in output_columns if col in normalized_df.columns]
    result_df = normalized_df[available_cols].copy()

    # Add lineage tracking metadata
    if etl_run_id:
        result_df['etl_run_id'] = etl_run_id
    if lineage_group_id:
        result_df['lineage_group_id'] = lineage_group_id

    logger.info(f"Transformed {len(result_df)} resource image records.")
    return result_df
