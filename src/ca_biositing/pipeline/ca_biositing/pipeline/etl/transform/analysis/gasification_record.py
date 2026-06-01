import pandas as pd
import numpy as np
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes

@task
def transform_gasification_record(
    thermo_data_df: pd.DataFrame,
    thermo_experiment_df: pd.DataFrame,
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None
) -> pd.DataFrame:
    """
    Transforms raw Thermochem data into the GasificationRecord table format.
    Includes cleaning, coercion, and normalization.
    """
    from ca_biositing.datamodels.models import (
        Resource,
        PreparedSample,
        Method,
        Contact,
        Dataset,
        Experiment,
        FileObjectMetadata,
        DeconVessel,
    )
    logger = get_run_logger()
    logger.info("Transforming raw data for GasificationRecord table")

    if thermo_data_df is None or thermo_data_df.empty:
        logger.warning("thermo_data_df is None or empty for GasificationRecord transform")
        return pd.DataFrame()

    # 1. Cleaning & Initial Setup
    # Aggressive pre-cleaning of column names
    thermo_data_df.columns = [str(c).strip() for c in thermo_data_df.columns]
    thermo_experiment_df.columns = [str(c).strip() for c in thermo_experiment_df.columns]

    # Use standard_clean for consistent behavior (janitor + lowercase values)
    # We exclude raw_data_url and experiment_setup_url from lowercasing because GSheet keys are case-sensitive
    exclude_cols = ["raw_data_url", "experiment_setup_url"]
    data_df = cleaning_mod.standard_clean(thermo_data_df.copy(), exclude_lowercase=exclude_cols)
    exp_df = cleaning_mod.standard_clean(thermo_experiment_df.copy(), exclude_lowercase=exclude_cols)

    if data_df is None or exp_df is None:
        logger.error("standard_clean returned None for GasificationRecord")
        return pd.DataFrame()

    # Map experiment metadata to data
    if 'experiment_id' not in data_df.columns:
         logger.warning("'experiment_id' column missing from data_df")
         return pd.DataFrame()

    # determine join key in exp_df (standard_clean makes it snake_case)
    exp_join_col = 'experiment_guid' if 'experiment_guid' in exp_df.columns else 'therm_exp_id' if 'therm_exp_id' in exp_df.columns else None

    if exp_join_col:
        merged_df = data_df.merge(
            exp_df[[exp_join_col, 'thermo_exp_title', 'method_id', 'reactor_id', 'analyst_email']],
            left_on='experiment_id',
            right_on=exp_join_col,
            how='left',
            suffixes=('', '_exp')
        )
    else:
        logger.warning("Could not find join key in thermo_experiment_df")
        merged_df = data_df.copy()

    # 2. Field Mapping (Latest requirements)
    # record_id -> record_id (mapped in flow from Record_id)
    # repl_no -> technical_replicate_no
    # raw_data_url -> raw_data_id (via normalization)
    # note -> note

    # We want unique records based on record_id
    if 'record_id' not in merged_df.columns:
        logger.error("record_id missing from merged_df in transform_gasification_record")
        return pd.DataFrame()

    final_df = merged_df.drop_duplicates(subset=['record_id']).copy()

    # Preserve resource name before normalization
    if 'resource' in final_df.columns:
        final_df['resource_name'] = final_df['resource']

    # 3. Normalization
    final_df['dataset'] = 'biocirv'

    normalize_columns = {
        'resource': (Resource, 'name'),
        'prepared_sample': (PreparedSample, 'name'),
        'method_id': (Method, 'name'),
        'experiment_id': (Experiment, 'name'),
        'analyst_email': (Contact, 'email'),
        'dataset': (Dataset, 'name'),
        'raw_data_url': (FileObjectMetadata, 'uri'),
        'reactor_id': (DeconVessel, 'name'),
    }

    normalized_dfs = normalize_dataframes([final_df], normalize_columns)
    df = normalized_dfs[0]

    # 4. Final Mapping & Coercion
    df = coercion_mod.coerce_columns(
        df,
        int_cols=['repl_no'],
        datetime_cols=['created_at', 'updated_at', 'experiment_date']
    )

    rename_map = {
        'record_id': 'record_id',
        'repl_no': 'technical_replicate_no',
        'note': 'note',
        'qc_result': 'qc_pass',
        'etl_run_id': 'etl_run_id',
        'lineage_group_id': 'lineage_group_id',
        'resource_name': 'resource_name'
    }

    # Lineage inheritance
    df['etl_run_id'] = etl_run_id
    df['lineage_group_id'] = lineage_group_id

    # Handle normalized columns
    for col in normalize_columns.keys():
        norm_col = f"{col}_id"
        if norm_col in df.columns:
            target_name = 'analyst_id' if col == 'analyst_email' else \
                          'dataset_id' if col == 'dataset' else \
                          'raw_data_id' if col == 'raw_data_url' else \
                          'experiment_id' if col == 'experiment_id' else \
                          'method_id' if col == 'method_id' else \
                          'reactor_type_id' if col == 'reactor_id' else \
                          norm_col
            rename_map[norm_col] = target_name

    available_cols = [c for c in rename_map.keys() if c in df.columns]

    try:
        record_df = df[available_cols].rename(columns=rename_map).copy()

        # Filter out placeholder or empty record_id values
        record_df = record_df[~record_df['record_id'].astype(str).str.strip().isin(['-', 'nan', 'none', ''])]
        record_df = record_df.dropna(subset=['record_id'])

        return record_df
    except Exception as e:
        logger.error(f"Error during GasificationRecord transform: {e}")
        return pd.DataFrame()
