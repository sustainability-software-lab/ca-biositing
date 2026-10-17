"""
ETL Transform for County Ag Report Records.

Transforms raw county ag report data from three worksheets into CountyAgReportRecord format.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes

# List the names of the extract modules this transform depends on.
EXTRACT_SOURCES: List[str] = ["primary_products", "pp_production_value"]

@task
def transform_county_ag_report_records(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None
) -> Optional[pd.DataFrame]:
    """
    Transforms raw county ag report data into CountyAgReportRecord format.

    Args:
        data_sources: Dictionary where keys are source names and values are DataFrames.
        etl_run_id: ID of the current ETL run.
        lineage_group_id: ID of the lineage group.

    Returns:
        Transformed DataFrame ready for loading.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    # CRITICAL: Lazy import models inside the task to avoid Docker import hangs
    from ca_biositing.datamodels.models import Place, PrimaryAgProduct, DataSource, CountyAgReportRecord

    # 1. Input Validation
    if "primary_products" not in data_sources or "pp_production_value" not in data_sources:
        logger.error("Required data sources 'primary_products' or 'pp_production_value' not found.")
        return None

    df_meta = data_sources["primary_products"].copy()
    df_metrics = data_sources["pp_production_value"].copy()

    if df_meta.empty or df_metrics.empty:
        logger.warning("One or more required data sources are empty.")
        return pd.DataFrame()

    logger.info("Transforming county ag report records...")

    # 2. Standard Cleaning
    df_meta = cleaning_mod.standard_clean(df_meta)
    df_metrics = cleaning_mod.standard_clean(df_metrics)

    # 3. Melting Sheet 07.7a (Metrics) to Long Format for Records
    # We need to create one record per product-county-year combination.
    # The production and value will be observations, but the base record is for the combination.

    # Counties to process
    counties = ["Merced", "San Joaquin", "Stanislaus"]

    # We only want to melt columns that indicate presence in a county.
    # Looking at the wide format analysis, we have Prodn_Merced, Value_$M_Merced etc.
    # If any of these have values, it means a record exists for that county/year/product.

    melted_records = []

    for _, row in df_metrics.iterrows():
        prod_nbr = row.get("prod_nbr")
        data_year = row.get("data_year")

        if pd.isna(prod_nbr) or str(prod_nbr).strip() == "" or pd.isna(data_year):
            continue

        for county in counties:
            # Check if there is any data for this county (production or value)
            prodn_col = f"prodn_{county.lower().replace(' ', '')}"
            value_col = f"value_m_{county.lower().replace(' ', '')}"

            # Note: standard_clean converts Value_$M_Merced to value_m_merced
            has_prodn = pd.notna(row.get(prodn_col)) and row.get(prodn_col) != ""
            has_value = pd.notna(row.get(value_col)) and row.get(value_col) != ""

            if has_prodn or has_value:
                record = {
                    "prod_nbr": prod_nbr,
                    "data_year": int(data_year),
                    "county": county,
                    "prodn_value_note": row.get("prodn_value_note")
                }
                melted_records.append(record)

    df_melted = pd.DataFrame(melted_records)

    if df_melted.empty:
        logger.warning("No records found after melting wide format.")
        return pd.DataFrame()

    # 4. Join with Metadata from Sheet 07.7
    # Match on prod_nbr
    df_combined = df_melted.merge(df_meta, on="prod_nbr", how="left")

    # 5. Type Coercion
    # Convert Produced_NSJV / Processed_NSJV to boolean
    # standard_clean makes them produced_nsjv / processed_nsjv
    df_combined = coercion_mod.coerce_columns(
        df_combined,
        int_cols=["data_year"],
        float_cols=[],
        datetime_cols=[]
    )

    # Manual boolean coercion for Checkboxes/Yes/No
    for col in ["produced_nsjv", "processed_nsjv"]:
        if col in df_combined.columns:
            def coerce_bool(val):
                if pd.isna(val):
                    return None
                s = str(val).strip().lower()
                if s in ['yes', 'true', 'checked', 'x']:
                    return True
                if s in ['no', 'false', 'unchecked', '']:
                    return False
                return None
            df_combined[col] = df_combined[col].apply(coerce_bool)

    # 6. Record ID Generation
    # Format: {prod_nbr}-{county_slug}-{year}
    df_combined["record_id"] = df_combined.apply(
        lambda x: f"{x['prod_nbr']}-{x['county'].lower().replace(' ', '')}-{x['data_year']}",
        axis=1
    )

    # 7. Data Source Name Mapping (resolved via normalize_dataframes to avoid hardcoded IDs)
    county_ds_name_map = {
        ("merced", 2023): "merced county 2023 report on agriculture",
        ("san joaquin", 2023): "san joaquin county crop report, 2023",
        ("stanislaus", 2023): "stanislaus county agricultural report, 2023",
        ("merced", 2024): "merced county 2024 report on agriculture",
        ("san joaquin", 2024): "san joaquin county crop report, 2024",
        ("stanislaus", 2024): "stanislaus county agricultural report, 2024",
    }

    def get_ds_name(row):
        return county_ds_name_map.get((row["county"].lower().strip(), int(row["data_year"])))

    df_combined["data_source_name"] = df_combined.apply(get_ds_name, axis=1)

    # 8. Normalization (Foreign Keys)
    # Institutionalize geoid mapping based on county (lowercase to match database convention)
    geoid_map = {
        "merced": "06047",
        "san joaquin": "06077",
        "stanislaus": "06099"
    }
    df_combined["geoid"] = df_combined["county"].str.lower().map(geoid_map)

    # Normalize PrimaryAgProduct and DataSource by name
    normalize_columns = {
        'primary_product': (PrimaryAgProduct, 'name'),
        'data_source_name': (DataSource, 'name'),
    }

    logger.info("Normalizing data (primary_ag_product_id and data_source_id)...")
    normalized_dfs = normalize_dataframes(df_combined, normalize_columns)
    df_normalized = normalized_dfs[0]

    # Map the output of normalize_dataframes to the expected column names
    rename_map = {
        "primary_product_id": "primary_ag_product_id",
        "data_source_name_id": "data_source_id",
    }
    df_normalized = df_normalized.rename(columns=rename_map)

    # 9. Final Preparation
    df_normalized["etl_run_id"] = etl_run_id
    df_normalized["lineage_group_id"] = lineage_group_id

    # Select columns that match CountyAgReportRecord
    model_columns = [
        "record_id", "geoid", "primary_ag_product_id", "description",
        "resource_type", "data_year", "data_source_id", "produced_nsjv",
        "processed_nsjv", "note", "prodn_value_note",
        "etl_run_id", "lineage_group_id"
    ]

    final_df = df_normalized[[col for col in model_columns if col in df_normalized.columns]]

    logger.info(f"Transformed {len(final_df)} records.")
    return final_df
