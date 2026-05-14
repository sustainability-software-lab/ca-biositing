import pandas as pd
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes
# from ca_biositing.datamodels.models import *

@task
def transform_ultimate_record(
    raw_df: pd.DataFrame,
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None
) -> pd.DataFrame:
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
        FileObjectMetadata,
        Experiment,
    )
    """
    Transforms raw DataFrame into the UltimateRecord table format.
    Includes cleaning, coercion, and normalization.
    """
    logger = get_run_logger()
    logger.info("Transforming raw data for UltimateRecord table")

    # 1. Cleaning & Coercion
    df_copy = raw_df.copy()
    df_copy['dataset'] = 'biocirv'
    cleaned_df = cleaning_mod.standard_clean(df_copy)

    # Add ETL and Lineage IDs if provided
    if etl_run_id:
        cleaned_df['etl_run_id'] = etl_run_id
    if lineage_group_id:
        cleaned_df['lineage_group_id'] = lineage_group_id

    coerced_df = coercion_mod.coerce_columns(
        cleaned_df,
        int_cols=['repl_no'],
        float_cols=['value'],
        datetime_cols=['created_at', 'updated_at']
    )

    # 2. Normalization
    normalize_columns = {
        'resource': (Resource, 'name'),
        'prepared_sample': (PreparedSample, 'name'),
        'preparation_method': (Method, 'name'),
        'parameter': (Parameter, 'name'),
        'unit': (Unit, 'name'),
        'sample_unit': (Unit, 'name'),
        'analyst_email': (Contact, 'email'),
        'primary_ag_product': (PrimaryAgProduct, 'name'),
        'provider_code': (Provider, 'codename'),
        'dataset': (Dataset, 'name'),
        'raw_data_url': (FileObjectMetadata, 'uri'),
        'exper_abbrev': (Experiment, 'name'),
    }
    normalized_dfs = normalize_dataframes(coerced_df, normalize_columns)
    normalized_df = normalized_dfs[0]

    # 3. Table Specific Mapping
    rename_map = {
        'record_id': 'record_id',
        'repl_no': 'technical_replicate_no',
        'qc_result': 'qc_pass',
        'note': 'note',
        'etl_run_id': 'etl_run_id',
        'lineage_group_id': 'lineage_group_id'
    }

    for col in normalize_columns.keys():
        norm_col = f"{col}_id"
        if norm_col in normalized_df.columns:
            target_name = 'analyst_id' if col == 'analyst_email' else \
                          'method_id' if col == 'preparation_method' else \
                          'raw_data_id' if col == 'raw_data_url' else \
                          'experiment_id' if col == 'exper_abbrev' else norm_col
            rename_map[norm_col] = target_name

    available_cols = [c for c in rename_map.keys() if c in normalized_df.columns]
    final_rename = {k: v for k, v in rename_map.items() if k in available_cols}

    try:
        record_df = normalized_df[available_cols].copy().rename(columns=final_rename)

        if 'record_id' in record_df.columns:
            record_df = record_df.dropna(subset=['record_id'])
            # Remove duplicates based on record_id to avoid ON CONFLICT errors
            if record_df.duplicated(subset=['record_id']).any():
                dupes = record_df[record_df.duplicated(subset=['record_id'])]['record_id'].unique().tolist()
                logger.warning(f"UltimateRecord: Removing duplicate record_ids from transform output: {dupes}")
                record_df = record_df.drop_duplicates(subset=['record_id'], keep='first')
        else:
            logger.error("record_id missing from UltimateRecord transform")
            return pd.DataFrame()

        return record_df
    except Exception as e:
        logger.error(f"Error during UltimateRecord transform: {e}")
        return pd.DataFrame()
