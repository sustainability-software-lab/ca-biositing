"""
IcpRecord transformation module.
"""
import pandas as pd
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes

@task
def transform_icp_record(
    raw_df: pd.DataFrame,
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None
) -> pd.DataFrame:
    """
    Transforms raw ICP analysis data into the IcpRecord table format.
    """
    from ca_biositing.datamodels.models import (
        Contact,
        Method,
        Resource,
        PreparedSample,
        Dataset,
        FileObjectMetadata
    )
    logger = get_run_logger()

    if raw_df is None or raw_df.empty:
        logger.warning("No raw data provided to IcpRecord transform")
        return pd.DataFrame()

    # 1. Cleaning & Coercion
    df = raw_df.copy()
    df = cleaning_mod.standard_clean(df)

    # Add ETL and Lineage IDs if provided
    if etl_run_id:
        df['etl_run_id'] = etl_run_id
    if lineage_group_id:
        df['lineage_group_id'] = lineage_group_id

    # 2. Normalization
    normalize_columns = {
        'analyst_email': (Contact, "email"),
        'method_id': Method,
        'resource': Resource,
        'prepared_sample': PreparedSample,
        'dataset': Dataset,
        'raw_data_url': (FileObjectMetadata, 'uri')
    }

    normalized_dfs = normalize_dataframes(df, normalize_columns)
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

    # Handle normalized columns
    for col in normalize_columns.keys():
        norm_col = f"{col}_id"
        if norm_col in normalized_df.columns:
            target_name = 'analyst_id' if col == 'analyst_email' else \
                          'method_id' if col == 'method_id' else \
                          'resource_id' if col == 'resource' else \
                          'prepared_sample_id' if col == 'prepared_sample' else \
                          'dataset_id' if col == 'dataset' else \
                          'raw_data_id' if col == 'raw_data_url' else norm_col
            rename_map[norm_col] = target_name

    available_cols = [c for c in rename_map.keys() if c in normalized_df.columns]
    final_rename = {k: v for k, v in rename_map.items() if k in available_cols}

    record_df = normalized_df[available_cols].rename(columns=final_rename).copy()

    if 'record_id' in record_df.columns:
        record_df = record_df.dropna(subset=['record_id'])

        # 1. Remove exact duplicates (entire row is identical)
        initial_count = len(record_df)
        record_df = record_df.drop_duplicates(keep='first')
        after_exact_count = len(record_df)
        if initial_count > after_exact_count:
            logger.info(f"IcpRecord: Dropped {initial_count - after_exact_count} exact row duplicates.")

        # 2. Detect record_id collisions with differing payloads
        if record_df.duplicated(subset=['record_id']).any():
            dupe_ids = record_df[record_df.duplicated(subset=['record_id'])]['record_id'].unique().tolist()
            logger.warning(f"IcpRecord: Detected {len(dupe_ids)} duplicate record_ids with differing payloads. Keeping first occurrence. Duplicates: {dupe_ids}")
            # Log specific differences for the first few duplicates to help debugging
            for rid in dupe_ids[:5]:
                conflicting_rows = record_df[record_df['record_id'] == rid]
                logger.warning(f"Conflicting payloads for record_id '{rid}':\n{conflicting_rows.to_string()}")

            # Keep the first occurrence of each record_id
            record_df = record_df.drop_duplicates(subset=['record_id'], keep='first')
    else:
        logger.error("record_id missing from IcpRecord transform")
        return pd.DataFrame()

    return record_df
