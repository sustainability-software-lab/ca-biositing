"""
ETL Transform for County Ag Report Observations.

Transforms raw production and value data from Sheet 07.7a into Observation format.
Each observation links back to a CountyAgReportRecord.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes

# List the names of the extract modules this transform depends on.
EXTRACT_SOURCES: List[str] = ["pp_production_value"]

@task
def transform_county_ag_report_observations(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None
) -> Optional[pd.DataFrame]:
    """
    Transforms wide-format production/value data into Observation format.

    Args:
        data_sources: Dictionary where keys are source names and values are DataFrames.
        etl_run_id: ID of the current ETL run.
        lineage_group_id: ID of the lineage group.

    Returns:
        Transformed DataFrame ready for loading into the Observation table.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    # CRITICAL: Lazy import models inside the task to avoid Docker import hangs
    from ca_biositing.datamodels.models import Parameter, Unit, Dataset

    # 1. Input Validation
    if "pp_production_value" not in data_sources:
        logger.error("Required data source 'pp_production_value' not found.")
        return None

    df_metrics = data_sources["pp_production_value"].copy()
    if df_metrics.empty:
        logger.warning("Data source 'pp_production_value' is empty.")
        return pd.DataFrame()

    logger.info("Transforming wide metrics into observations...")

    # 2. Standard Cleaning
    df_metrics = cleaning_mod.standard_clean(df_metrics)

    # 3. Melting Wide Format to Long Format
    counties = ["Merced", "San Joaquin", "Stanislaus"]

    # Dataset name mapping (resolved via normalize_dataframes to avoid hardcoded IDs)
    county_dataset_name_map = {
        ("merced", 2023): "MERCED_COUNTY_2023_REPORT_ON_AGRICULTURE",
        ("san joaquin", 2023): "SAN_JOAQUIN_COUNTY_CROP_REPORT_2023",
        ("stanislaus", 2023): "STANISLAUS_COUNTY_AGRICULTURAL_REPORT_2023",
        ("merced", 2024): "MERCED_COUNTY_2024_REPORT_ON_AGRICULTURE",
        ("san joaquin", 2024): "SAN_JOAQUIN_COUNTY_CROP_REPORT_2024",
        ("stanislaus", 2024): "STANISLAUS_COUNTY_AGRICULTURAL_REPORT_2024",
    }

    observations = []

    for _, row in df_metrics.iterrows():
        prod_nbr = row.get("prod_nbr")
        data_year = row.get("data_year")

        if pd.isna(prod_nbr) or str(prod_nbr).strip() == "" or pd.isna(data_year):
            continue

        for county in counties:
            county_lower = county.lower().strip()
            county_slug = county_lower.replace(' ', '')

            # Parent record_id matches the one generated in county_ag_report_record transform
            parent_record_id = f"{prod_nbr}-{county_slug}-{int(data_year)}"

            # Determine canonical dataset_name by (county_lower, int(data_year))
            dataset_name = county_dataset_name_map.get((county_lower, int(data_year)))

            # --- Production Observation ---
            prodn_col = f"prodn_{county_slug}"
            prodn_val = row.get(prodn_col)

            # Clean numeric value (handle commas etc)
            if pd.notna(prodn_val) and str(prodn_val).strip() != "":
                try:
                    # Remove commas and convert to float
                    val_str = str(prodn_val).replace(',', '').strip()
                    if val_str:
                        observations.append({
                            "record_id": parent_record_id,
                            "record_type": "county_ag_report_record",
                            "parameter_name": "production",
                            "unit_name": "tons",
                            "value": float(val_str),
                            "dataset_name": dataset_name,
                            "note": row.get("prodn_value_note")
                        })
                except ValueError:
                    logger.warning(f"Could not convert production value '{prodn_val}' for {parent_record_id}")

            # --- Value Observation ---
            value_col = f"value_m_{county_slug}"
            value_val = row.get(value_col)

            if pd.notna(value_val) and str(value_val).strip() != "":
                try:
                    val_str = str(value_val).replace(',', '').strip()
                    if val_str:
                        observations.append({
                            "record_id": parent_record_id,
                            "record_type": "county_ag_report_record",
                            "parameter_name": "value",
                            "unit_name": "$M",
                            "value": float(val_str),
                            "dataset_name": dataset_name,
                            "note": row.get("prodn_value_note")
                        })
                except ValueError:
                    logger.warning(f"Could not convert value '{value_val}' for {parent_record_id}")

    df_obs = pd.DataFrame(observations)

    if df_obs.empty:
        logger.warning("No observations found after melting wide metrics.")
        return pd.DataFrame()

    # 4. Normalization (Parameter, Unit, and Dataset IDs by name)
    normalize_columns = {
        'parameter_name': (Parameter, 'name'),
        'unit_name': (Unit, 'name'),
        'dataset_name': (Dataset, 'name'),
    }

    logger.info("Normalizing observations (parameter_id, unit_id, and dataset_id)...")
    normalized_dfs = normalize_dataframes(df_obs, normalize_columns)
    df_normalized = normalized_dfs[0]

    # Map the output of normalize_dataframes to the expected column names
    rename_map = {
        "parameter_name_id": "parameter_id",
        "unit_name_id": "unit_id",
        "dataset_name_id": "dataset_id",
    }
    df_normalized = df_normalized.rename(columns=rename_map)

    # 5. Final Preparation
    df_normalized["etl_run_id"] = etl_run_id
    df_normalized["lineage_group_id"] = lineage_group_id

    # Select columns that match Observation model
    model_columns = [
        "record_id", "record_type", "parameter_id", "value", "unit_id",
        "dataset_id", "note", "etl_run_id", "lineage_group_id"
    ]

    final_df = df_normalized[[col for col in model_columns if col in df_normalized.columns]]

    logger.info(f"Transformed {len(final_df)} observations.")
    return final_df
