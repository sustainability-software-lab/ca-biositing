"""
General observation transformation module.
"""
import pandas as pd
from prefect import task, get_run_logger
from typing import List
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes
# from ca_biositing.datamodels.models import *

@task
def transform_observation(
    raw_dfs: List[pd.DataFrame],
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None
) -> pd.DataFrame:
    """
    Transforms raw DataFrames into the Observation table format.
    Includes cleaning, coercion, and normalization.
    """
    from ca_biositing.datamodels.models import (
        Resource,
        PreparedSample,
        Method,
        Parameter,
        Unit,
        Contact,
        PrimaryAgProduct,
        Provider,
        Dataset,
    )
    logger = get_run_logger()
    logger.info(f"Transforming {len(raw_dfs)} raw dataframes for Observation table")

    # 1. Cleaning & Coercion
    coerced_data = []
    for i, df in enumerate(raw_dfs):
        if df is None:
            logger.warning(f"DataFrame at index {i} is None. Skipping.")
            continue

        # Aggressive pre-cleaning of column names to avoid duplicates before janitor
        df.columns = [str(c).strip() for c in df.columns]
        df = df.loc[:, df.columns.notnull()]
        df = df.loc[:, (df.columns != '')]

        # Use standard_clean for consistent behavior across pipelines
        # This handles name cleaning (janitor), duplicate columns, empty->NA, and lowercasing data
        df = cleaning_mod.standard_clean(df)
        if df is None:
            continue

        # Basic coercion for Observation fields
        if 'value' in df.columns:
            df = coercion_mod.coerce_columns(df, float_cols=['value'])
            # User request: treat null as 0 for XRF and ICP if record_id is present
            if 'analysis_type' in df.columns and 'record_id' in df.columns:
                mask = df['analysis_type'].isin(['xrf analysis', 'icp analysis']) & df['record_id'].notna()
                # Exception for ICP: do not convert nulls to 0 for "y-axial" and "y-radial" parameters
                if 'parameter' in df.columns:
                    icp_exception_mask = (df['analysis_type'] == 'icp analysis') & df['parameter'].isin(['y-axial', 'y-radial'])
                    mask = mask & ~icp_exception_mask
                df.loc[mask, 'value'] = df.loc[mask, 'value'].fillna(0)

        # Add lineage tracking if available
        df['etl_run_id'] = etl_run_id
        df['lineage_group_id'] = lineage_group_id

        coerced_data.append(df)

    # 2. Normalization (Resource, Sample, Parameter, Unit, etc.)
    normalize_columns = {
        'resource': Resource,
        'prepared_sample': PreparedSample,
        'method_id': Method,
        'parameter': Parameter,
        'unit': Unit,
        'analyst_email': (Contact, "email"),
        'main_crop': PrimaryAgProduct,
        'provider': Provider,
        'dataset': Dataset,
    }

    normalized_dfs = normalize_dataframes(coerced_data, normalize_columns)

    # 3. Final Mapping to Observation table
    required_cols = [
        'dataset_id',
        'analysis_type',
        'record_id',
        'parameter_id',
        'value',
        'unit_id',
        'note',
        'etl_run_id',
        'lineage_group_id'
    ]

    observation_data = []
    for i, normalized_df in enumerate(normalized_dfs):
        if not isinstance(normalized_df, pd.DataFrame):
            logger.error(f"Normalized item #{i+1} is not a DataFrame: {type(normalized_df)}")
            continue

        # Ensure required columns exist even if all-null
        for col in required_cols:
            if col not in normalized_df.columns:
                normalized_df[col] = pd.NA

        try:
            obs_df = normalized_df[required_cols].copy().rename(columns={'analysis_type': 'record_type'})

            # Normalize record_id to lowercase to match parent record tables
            if 'record_id' in obs_df.columns:
                obs_df['record_id'] = obs_df['record_id'].astype(str).str.lower()

            initial_count = len(obs_df)
            obs_df = obs_df.dropna(subset=['record_id', 'parameter_id', 'value'])
            final_count = len(obs_df)

            if initial_count > 0 and final_count == 0:
                logger.warning(f"Observation: All {initial_count} rows dropped due to missing record_id, parameter_id, or value.")
                # Log some sample values to help debug
                sample = normalized_df[['record_id', 'parameter_id', 'value']].head(3)
                logger.info(f"Sample data before dropna:\n{sample}")

            # Remove duplicates based on (record_id, record_type, parameter_id, unit_id) to avoid ON CONFLICT errors
            # CodeRabbit Review: include unit_id in the subset
            subset = ['record_id', 'record_type', 'parameter_id', 'unit_id']
            # Filter subset to only include columns that are actually present in obs_df
            present_subset = [c for c in subset if c in obs_df.columns]

            if obs_df.duplicated(subset=present_subset).any():
                dupes_count = obs_df.duplicated(subset=present_subset).sum()
                logger.warning(f"Observation: Removing {dupes_count} duplicate observations from transform output.")
                obs_df = obs_df.drop_duplicates(subset=present_subset, keep='first')

            observation_data.append(obs_df)
        except KeyError as e:
            logger.error(f"Missing required column for observation transform: {e}")
            continue

    if not observation_data:
        logger.warning("No observation data produced during transform")
        return pd.DataFrame()

    final_obs_df = pd.concat(observation_data, ignore_index=True)

    # Final check across all source dataframes
    subset = ['record_id', 'record_type', 'parameter_id', 'unit_id']
    present_subset = [c for c in subset if c in final_obs_df.columns]
    if final_obs_df.duplicated(subset=present_subset).any():
        dupes_count = final_obs_df.duplicated(subset=present_subset).sum()
        logger.warning(f"Observation: Removing {dupes_count} duplicate observations across all source dataframes.")
        final_obs_df = final_obs_df.drop_duplicates(subset=present_subset, keep='first')

    return final_obs_df
