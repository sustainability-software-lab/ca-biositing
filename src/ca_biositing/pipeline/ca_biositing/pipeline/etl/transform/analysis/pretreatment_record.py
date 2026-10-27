"""
PretreatmentRecord transformation module.
"""
import pandas as pd
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes

@task
def transform_pretreatment_record(
    raw_df: pd.DataFrame,
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None
) -> pd.DataFrame:
    """
    Transforms raw pretreatment analysis data into the PretreatmentRecord table format.
    """
    from ca_biositing.datamodels.models import (
        Contact,
        Method,
        Resource,
        PreparedSample,
        Dataset,
        Equipment,
        Experiment,
        DeconVessel,
        FileObjectMetadata
    )
    logger = get_run_logger()

    if raw_df is None or raw_df.empty:
        logger.warning("No raw data provided to PretreatmentRecord transform")
        return pd.DataFrame()

    # 1. Cleaning & Coercion
    df = raw_df.copy()
    logger.info(f"PretreatmentRecord: raw_df columns: {df.columns.tolist()}")

    cleaned_df = cleaning_mod.standard_clean(df)

    if cleaned_df is None:
        logger.error("cleaning_mod.standard_clean returned None for PretreatmentRecord")
        return pd.DataFrame()

    logger.info(f"PretreatmentRecord: after standard_clean columns: {cleaned_df.columns.tolist()}")

    # Add lineage IDs
    if etl_run_id is not None:
        cleaned_df['etl_run_id'] = etl_run_id
    if lineage_group_id is not None:
        cleaned_df['lineage_group_id'] = lineage_group_id

    coerced_df = coercion_mod.coerce_columns(
        cleaned_df,
        int_cols=['repl_number'],
        datetime_cols=['created_at', 'updated_at']
    )
    logger.info(f"PretreatmentRecord: after coerce_columns columns: {coerced_df.columns.tolist()}")

    df = coerced_df
    df['dataset'] = 'biocirv'

    # 2. Normalization
    normalize_columns = {
        'analyst_email': (Contact, "email"),
        'preparation_method': Method,
        'pretreatment_exper_name': (Experiment, "experiment_name"),
        'decon_method_id': Method,
        'eh_method_id': Method,
        'reaction_block_id': Equipment,
        'vessel_id': DeconVessel,
        'raw_data_url': (FileObjectMetadata, "uri"),
        'resource': (Resource, 'name'),
        'prepared_sample': (PreparedSample, 'name'),
        'dataset': (Dataset, 'name'),
    }

    normalized_dfs = normalize_dataframes(df, normalize_columns)
    normalized_df = normalized_dfs[0]
    logger.info(f"PretreatmentRecord: after normalize_dataframes columns: {normalized_df.columns.tolist()}")

    # 3. Table Specific Mapping
    rename_map = {
        'record_id': 'record_id',
        'repl_number': 'technical_replicate_no',
        'block_position': 'block_position',
        'temperature': 'temperature',
        'qc_result': 'qc_pass',
        'note': 'note',
        'etl_run_id': 'etl_run_id',
        'lineage_group_id': 'lineage_group_id',
        'reaction_block_id': 'reaction_block_id',
        'resource_id': 'resource_id',
        'prepared_sample_id': 'prepared_sample_id',
        'dataset_id': 'dataset_id',
    }

    # Handle normalized columns
    for col in normalize_columns.keys():
        norm_col = f"{col}_id"
        if norm_col in normalized_df.columns:
            target_name = 'analyst_id' if col == 'analyst_email' else \
                          'method_id' if col == 'preparation_method' else \
                          'experiment_id' if col == 'pretreatment_exper_name' else \
                          'pretreatment_method_id' if col == 'decon_method_id' else \
                          'eh_method_id' if col == 'eh_method_id' else \
                          'reaction_block_id' if col == 'reaction_block_id' else \
                          'vessel_id' if col == 'vessel_id' else \
                          'raw_data_id' if col == 'raw_data_url' else \
                          'resource_id' if col == 'resource' else \
                          'prepared_sample_id' if col == 'prepared_sample' else \
                          'dataset_id' if col == 'dataset' else norm_col
            rename_map[norm_col] = target_name

    available_cols = [c for c in rename_map.keys() if c in normalized_df.columns]
    final_rename = {k: v for k, v in rename_map.items() if k in available_cols}
    logger.info(f"PretreatmentRecord: available_cols for mapping: {available_cols}")
    logger.info(f"PretreatmentRecord: final_rename map: {final_rename}")

    try:
        record_df = normalized_df[available_cols].rename(columns=final_rename).copy()
        logger.info(f"PretreatmentRecord: record_df columns after rename: {record_df.columns.tolist()}")

        # Add replicate_no as well if technical_replicate_no exists
        if 'technical_replicate_no' in record_df.columns:
            record_df['replicate_no'] = record_df['technical_replicate_no']

        if 'record_id' in record_df.columns:
            # Filter out placeholder or empty record_id values (like '-' or '')
            # These are often found in trailing empty rows of the spreadsheet
            record_df = record_df[~record_df['record_id'].astype(str).str.strip().isin(['-', 'nan', 'None', ''])]
            record_df = record_df.dropna(subset=['record_id'])
        else:
            logger.error("record_id missing from PretreatmentRecord transform")
            return pd.DataFrame()

        return record_df
    except Exception as e:
        logger.exception(f"Error during PretreatmentRecord transform: {e}")
        raise
