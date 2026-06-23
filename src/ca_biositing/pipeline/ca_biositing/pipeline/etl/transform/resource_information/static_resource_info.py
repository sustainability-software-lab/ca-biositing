"""
ETL Transform for Static Resource Information.

Transforms raw static resource info into LandiqResourceMapping and ResourceAvailability tables.
"""

import pandas as pd
from typing import List, Optional, Dict
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes

# List the names of the extract modules this transform depends on.
EXTRACT_SOURCES: List[str] = ["static_resource_info"]

@task
def transform_static_resource_info(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None
) -> Dict[str, pd.DataFrame]:
    """
    Transforms raw static resource info into:
    1. LandiqResourceMapping
    2. ResourceAvailability
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    # CRITICAL: Lazy import models inside the task to avoid Docker import hangs
    from ca_biositing.datamodels.models import (
        Resource,
        PrimaryAgProduct
    )

    # 1. Input Validation
    if "static_resource_info" not in data_sources:
        logger.error("Required data source 'static_resource_info' not found.")
        return {}

    df = data_sources["static_resource_info"].copy()
    if df.empty:
        logger.warning("Source 'static_resource_info' is empty.")
        return {
            "landiq_resource_mapping": pd.DataFrame(),
            "resource_availability": pd.DataFrame()
        }

    logger.info("Transforming static resource information...")

    # 2. Cleaning & Coercion
    # standard_clean will convert "Resource" to "resource", etc.
    clean_df = cleaning_mod.standard_clean(df)

    # Coerce numeric columns
    # Expected cleaned names (from janitor.clean_names):
    # From Month -> from_month
    # To Month -> to_month
    # Residue Yield (Wet Ton/Ac) -> residue_yield_wet_ton_ac_
    # Residue Yield (Dry Ton/Ac) -> residue_yield_dry_ton_ac_
    # Include In Totals -> include_in_totals
    coerced_df = coercion_mod.coerce_columns(
        clean_df,
        int_cols=['from_month', 'to_month'],
        float_cols=['residue_yield_wet_ton_ac_', 'residue_yield_dry_ton_ac_'],
        bool_cols=['include_in_totals']
    )

    # 3. Normalization (Name-to-ID Swapping)
    # Map 'resource' column to Resource.name to get resource_id
    # Map 'landiq_crop_name' column to PrimaryAgProduct.name to get landiq_crop_name_id
    normalize_columns = {
        'resource': (Resource, 'name'),
        'landiq_crop_name': (PrimaryAgProduct, 'name')
    }

    logger.info("Normalizing data (swapping names for IDs)...")
    normalized_dfs = normalize_dataframes(coerced_df, normalize_columns)
    normalized_df = normalized_dfs[0]

    # 4. Create LandiqResourceMapping DataFrame
    # Target slots: landiq_crop_name (ID), resource_id
    landiq_mapping_df = pd.DataFrame()
    if 'landiq_crop_name_id' in normalized_df.columns and 'resource_id' in normalized_df.columns:
        landiq_mapping_df = normalized_df[['landiq_crop_name_id', 'resource_id']].copy()
        landiq_mapping_df = landiq_mapping_df.rename(columns={
            'landiq_crop_name_id': 'landiq_crop_name'
        })
        # Drop rows where landiq_crop_name (the ID) is null
        landiq_mapping_df = landiq_mapping_df.dropna(subset=['landiq_crop_name'])

        if etl_run_id:
            landiq_mapping_df['etl_run_id'] = etl_run_id
        if lineage_group_id:
            landiq_mapping_df['lineage_group_id'] = lineage_group_id

        logger.info(f"Created {len(landiq_mapping_df)} LandiqResourceMapping records.")

    # 5. Create ResourceAvailability DataFrame
    # Target slots: resource_id, from_month, to_month, residue_factor_dry_tons_acre, residue_factor_wet_tons_acre
    availability_df = pd.DataFrame()

    availability_rename_map = {
        'resource_id': 'resource_id',
        'from_month': 'from_month',
        'to_month': 'to_month',
        'residue_yield_dry_ton_ac_': 'residue_factor_dry_tons_acre',
        'residue_yield_wet_ton_ac_': 'residue_factor_wet_tons_acre'
    }

    # Filter for columns that actually exist in normalized_df
    available_cols = [k for k in availability_rename_map.keys() if k in normalized_df.columns]

    if 'resource_id' in normalized_df.columns:
        availability_df = normalized_df[available_cols].rename(columns=availability_rename_map).copy()

        # Add default geoid "06000" for state of California
        availability_df['geoid'] = "06000"

        if etl_run_id:
            availability_df['etl_run_id'] = etl_run_id
        if lineage_group_id:
            availability_df['lineage_group_id'] = lineage_group_id

        logger.info(f"Created {len(availability_df)} ResourceAvailability records.")

    return {
        "landiq_resource_mapping": landiq_mapping_df,
        "resource_availability": availability_df
    }
