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

# --- CONFIGURATION ---
# List the names of the extract modules this transform depends on.
# The pipeline runner provides these in the `data_sources` dictionary.
EXTRACT_SOURCES: List[str] = ["resources"]

@task
def transform(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None
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
        Resource,
        ResourceClass,
        ResourceSubclass,
        PrimaryAgProduct
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
        # Exclude description and note from lowercasing to preserve case
        cleaned_df = cleaning_mod.standard_clean(df, exclude_lowercase=['description', 'note'])

        # Add lineage tracking metadata
        cleaned_df['etl_run_id'] = etl_run_id
        cleaned_df['lineage_group_id'] = lineage_group_id

        # Coerce data types (Update these lists based on your schema)
        coerced_df = coercion_mod.coerce_columns(
            cleaned_df,
            int_cols=[],
            float_cols=[],
            datetime_cols=['created_at', 'updated_at']
        )
        processed_dfs.append(coerced_df)

    if not processed_dfs:
        return pd.DataFrame()

    # Combine sources if necessary, or handle them individually
    combined_df = pd.concat(processed_dfs, ignore_index=True)

    # 3. Normalization (Name-to-ID Swapping)
    # Format: 'dataframe_column': (SQLAlchemyModel, 'lookup_field_in_db')
    normalize_columns = {
        'resource_class': (ResourceClass, 'name'),
        'resource_subclass': (ResourceSubclass, 'name'),
        'primary_ag_product': (PrimaryAgProduct, 'name'),
        # Example: 'unit': (Unit, 'name'),
    }

    logger.info("Normalizing data (swapping names for IDs)...")
    normalized_dfs = normalize_dataframes(combined_df, normalize_columns)
    normalized_df = normalized_dfs[0]

    # 4. Column Renaming
    # TODO: Update this dictionary to match your source-to-target mapping
    rename_columns = {
        'resource': 'name'

        # 'source_col': 'target_col',
    }
    normalized_df = normalized_df.rename(columns=rename_columns)

    # 4.2 Ensure names are lowercased (Requirement: resource and primary_ag_product names should be lowercase)
    if 'name' in normalized_df.columns:
        # Convert to string and handle common representations of null/empty
        normalized_df['name'] = normalized_df['name'].astype(str).str.strip()
        # Case-insensitive replacement of null-like strings
        null_like = ['none', 'nan', '<na>', '', '#n/a']
        normalized_df.loc[normalized_df['name'].str.lower().isin(null_like), 'name'] = np.nan
        # Finally, lowercase the valid names
        normalized_df['name'] = normalized_df['name'].str.lower()

    # 4.5 Filter invalid names
    if 'name' in normalized_df.columns:
        initial_count = len(normalized_df)
        normalized_df = normalized_df[
            normalized_df['name'].notna() &
            (normalized_df['name'].astype(str).str.strip() != "") &
            (normalized_df['name'].astype(str).str.lower() != "#n/a")
        ]
        filtered_count = initial_count - len(normalized_df)
        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} records with invalid names (empty or '#n/a').")

    # 5. Final Mapping & Selection
    # Ensure lineage columns exist even if not provided in input
    if etl_run_id:
        normalized_df['etl_run_id'] = etl_run_id
    if lineage_group_id:
        normalized_df['lineage_group_id'] = lineage_group_id

    required_columns = [
        'name',
        'primary_ag_product_id',
        'resource_class_id',
        'resource_subclass_id',
        'description',
        'resource_code',
        'etl_run_id',
        'lineage_group_id',
    ]
    optional_columns = [
        'note',
    ]

    # Add optional columns only if present in the data
    for col in optional_columns:
        if col not in normalized_df.columns:
            normalized_df[col] = None

    final_df = normalized_df[required_columns + optional_columns].copy()

    logger.info(f"Successfully transformed {len(final_df)} records.")
    return final_df
