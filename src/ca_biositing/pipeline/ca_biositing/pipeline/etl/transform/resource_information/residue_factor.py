"""
ETL Transform: Residue Factors

Transforms raw residue factor data from Google Sheets into database-ready format.

8-step normalization process:
1. Input validation & cleaning
2. Data type coercion (Decimal for numeric fields)
3. Foreign key resolution (resource, data_source, unit lookups)
4. Factor calculations (factor_mid = (min + max) / 2 if NULL)
5. Column mapping & selection
6. Lineage & metadata assignment
7. Output validation
8. Summary statistics logging
"""

import pandas as pd
import numpy as np
from decimal import Decimal
from typing import Optional, Dict
from prefect import task, get_run_logger

from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes


@task
def transform_residue_factor(
    df: pd.DataFrame,
    etl_run_id: Optional[str] = None,
    lineage_group_id: Optional[str] = None,
) -> Optional[pd.DataFrame]:
    """
    Transform raw residue factor data into database-ready format.

    Args:
        df: Raw DataFrame from extractor (Google Sheets)
        etl_run_id: Current ETL run identifier
        lineage_group_id: Lineage group identifier

    Returns:
        Transformed DataFrame ready for loading to database, or None if validation fails
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging

        logger = logging.getLogger(__name__)

    # ========================================
    # Step 1: Input Validation & Cleaning
    # ========================================
    if df is None or df.empty:
        logger.error("Input DataFrame is None or empty")
        return None

    logger.info(f"Starting transformation with {len(df)} rows")

    # CRITICAL: Lazy import models inside the task to avoid Docker import hangs
    from ca_biositing.datamodels.models import Resource, DataSource, Unit

    # Make a copy to avoid modifying the original
    df = df.copy()

    # Apply standard cleaning (lowercase column names, basic string cleaning)
    logger.info("Step 1: Cleaning and normalizing column names")
    df = cleaning_mod.standard_clean(df)

    # Log initial data quality
    logger.info(f"Columns after cleaning: {list(df.columns)}")
    logger.info(f"Null count by column:\n{df.isnull().sum()}")

    # ========================================
    # Step 2: Data Type Coercion
    # ========================================
    logger.info("Step 2: Coercing numeric columns to Decimal")

    decimal_cols = ["factor_min", "factor_max", "factor_mid", "prune_trim_yield"]
    for col in decimal_cols:
        if col in df.columns:
            # Convert to Decimal, preserving NaN
            def safe_decimal_convert(x):
                if pd.isna(x):
                    return None
                str_val = str(x).strip()
                if not str_val or str_val.lower() in ('nan', 'none', ''):
                    return None
                try:
                    return Decimal(str_val)
                except Exception as e:
                    logger.warning(f"Could not convert '{str_val}' to Decimal: {e}")
                    return None

            df[col] = df[col].apply(safe_decimal_convert)

    # ========================================
    # Step 3: Foreign Key Resolution
    # ========================================
    logger.info("Step 3: Resolving foreign keys (resource, data_source, unit)")

    # Resource Normalization (resource → resource_id)
    # Also capture resource_name from Resource.name for denormalization
    normalize_columns = {
        "resource": (Resource, "name"),
    }

    normalized_dfs = normalize_dataframes(df, normalize_columns)
    df = normalized_dfs[0]

    # After normalization, 'resource' is dropped and 'resource_id' is created
    # Now we need to denormalize resource_name
    logger.info("Denormalizing resource_name from Resource table")
    from ca_biositing.pipeline.utils.engine import engine
    from sqlalchemy.orm import Session
    from sqlalchemy import select

    with Session(engine) as session:
        # Fetch resource names
        resource_rows = session.execute(
            select(Resource.id, Resource.name)
        ).all()
        id_to_name_map = {row[0]: row[1] for row in resource_rows}
        df["resource_name"] = df["resource_id"].map(id_to_name_map)

        # Data Source Normalization (source URL → data_source_id)
        if "source" in df.columns:
            logger.info("Normalizing data_source (source URL → data_source_id)")
            # Map URLs to DataSource IDs (DataSource.uri is the field name)
            ds_rows = session.execute(select(DataSource.id, DataSource.uri)).all()
            url_to_id_map = {
                row[1]: row[0] for row in ds_rows if row[1] is not None
            }

            # Case-insensitive matching for URLs
            df["data_source_id"] = df["source"].apply(
                lambda x: (
                    url_to_id_map.get(str(x).strip())
                    if pd.notna(x) and str(x).strip()
                    else None
                )
            )

            # Log unmatched URLs
            unmatched = df[df["source"].notna() & df["data_source_id"].isna()]
            if not unmatched.empty:
                logger.warning(
                    f"Found {len(unmatched)} records with unmatched data source URLs: "
                    f"{unmatched['source'].unique().tolist()}"
                )

        # Unit Normalization (prune_trim_yield_unit → prune_trim_yield_unit_id)
        if "prune_trim_yield_unit" in df.columns:
            logger.info("Normalizing unit (prune_trim_yield_unit → prune_trim_yield_unit_id)")
            unit_rows = session.execute(select(Unit.id, Unit.name)).all()
            unit_name_to_id_map = {row[1]: row[0] for row in unit_rows if row[1] is not None}

            # Case-insensitive matching for units
            df["prune_trim_yield_unit_id"] = df["prune_trim_yield_unit"].apply(
                lambda x: (
                    unit_name_to_id_map.get(str(x).lower().strip())
                    if pd.notna(x) and str(x).strip()
                    else None
                )
            )

            unmatched_units = df[
                df["prune_trim_yield_unit"].notna() & df["prune_trim_yield_unit_id"].isna()
            ]
            if not unmatched_units.empty:
                logger.warning(
                    f"Found {len(unmatched_units)} records with unmatched units: "
                    f"{unmatched_units['prune_trim_yield_unit'].unique().tolist()}"
                )

    # ========================================
    # Step 4: Factor Calculations
    # ========================================
    logger.info("Step 4: Calculating factor_mid if missing")

    # Calculate factor_mid = (factor_min + factor_max) / 2 if NULL
    mask = df["factor_mid"].isna() & df["factor_min"].notna() & df["factor_max"].notna()
    calculated_count = mask.sum()

    if calculated_count > 0:
        df.loc[mask, "factor_mid"] = (
            (df.loc[mask, "factor_min"] + df.loc[mask, "factor_max"]) / 2
        )
        logger.info(f"Calculated factor_mid for {calculated_count} records")

    # ========================================
    # Step 5: Column Mapping & Selection
    # ========================================
    logger.info("Step 5: Mapping and selecting required columns")

    # Rename columns to match ResidueFactor model schema
    rename_map = {
        # source is already processed → data_source_id
        # prune_trim_yield_unit is already processed → prune_trim_yield_unit_id
    }
    df = df.rename(columns=rename_map)

    # Select only ResidueFactor model columns
    required_columns = [
        "resource_id",
        "resource_name",
        "data_source_id",
        "factor_type",
        "factor_min",
        "factor_max",
        "factor_mid",
        "prune_trim_yield",
        "prune_trim_yield_unit_id",
        "notes",
    ]

    available_cols = [col for col in required_columns if col in df.columns]
    df = df[available_cols]

    # Add missing required columns as NULL
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    # Reorder to match required columns
    df = df[required_columns]

    # ========================================
    # Step 6: Lineage & Metadata Assignment
    # ========================================
    logger.info("Step 6: Adding lineage and metadata")

    if etl_run_id:
        df["etl_run_id"] = etl_run_id
    else:
        df["etl_run_id"] = None

    if lineage_group_id:
        df["lineage_group_id"] = lineage_group_id
    else:
        df["lineage_group_id"] = None

    # ========================================
    # Step 7: Output Validation
    # ========================================
    logger.info("Step 7: Validating output")

    # Verify resource_id is not NULL (required foreign key)
    null_resource_count = df["resource_id"].isna().sum()
    if null_resource_count > 0:
        logger.error(f"Found {null_resource_count} records with NULL resource_id")
        logger.error("Dropping records with NULL resource_id (required field)")
        df = df[df["resource_id"].notna()]

    if df.empty:
        logger.error("No valid records remaining after validation")
        return None

    # ========================================
    # Step 8: Summary Statistics
    # ========================================
    logger.info("Step 8: Logging summary statistics")

    logger.info(f"Output DataFrame shape: {df.shape}")
    logger.info(f"Output rows: {len(df)}")
    logger.info(
        f"Null counts:\n{df.isnull().sum()}"
    )

    # Log match rates for foreign keys
    if "resource_id" in df.columns:
        fk_match_rate = (df["resource_id"].notna().sum() / len(df)) * 100
        logger.info(f"Resource FK match rate: {fk_match_rate:.1f}%")

    if "data_source_id" in df.columns:
        ds_match_rate = (
            (df["data_source_id"].notna().sum() / len(df)) * 100
            if df["data_source_id"].notna().sum() > 0
            else 0
        )
        logger.info(f"DataSource FK match rate: {ds_match_rate:.1f}%")

    if "prune_trim_yield_unit_id" in df.columns:
        unit_match_rate = (
            (df["prune_trim_yield_unit_id"].notna().sum() / len(df)) * 100
            if df["prune_trim_yield_unit_id"].notna().sum() > 0
            else 0
        )
        logger.info(f"Unit FK match rate: {unit_match_rate:.1f}%")

    logger.info("Transformation complete")

    return df
