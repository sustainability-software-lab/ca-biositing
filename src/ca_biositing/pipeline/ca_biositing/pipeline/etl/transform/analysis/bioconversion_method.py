import pandas as pd
import numpy as np
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes

@task
def transform_bioconversion_method(
    raw_df: pd.DataFrame,
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None
) -> pd.DataFrame:
    """
    Transforms raw BioConversion Methods data into the BioconversionMethod table format.
    """
    from ca_biositing.datamodels.models import Strain
    logger = get_run_logger()
    logger.info("Transforming raw data for BioconversionMethod table")

    if raw_df is None or raw_df.empty:
        return pd.DataFrame()

    # 1. Cleaning
    df = cleaning_mod.standard_clean(raw_df.copy())

    # 2. Normalization (map strain_name to strain_id)
    # Standard clean makes headers snake_case.
    # 'Strain_name' in sheet becomes 'strain_name'
    if 'strain_name' in df.columns:
        df['strain_name_raw'] = df['strain_name']

    normalize_columns = {
        'strain_name': (Strain, 'name')
    }

    normalized_dfs = normalize_dataframes(df, normalize_columns)
    df = normalized_dfs[0]

    # 3. Field Mapping
    # The sheet columns (after standard_clean):
    # 'method_id' -> 'name' (the unique code for the method)
    # 'strain_name_id' -> 'strain_id' (from normalization)
    # 'strain_name_raw' -> 'strain_name'
    # 'inoculum_volume_l_' -> 'inoculum_volume_L' (janitor adds trailing underscore for parens)
    # 'reaction_volume_l_' -> 'reaction_volume_L'
    # 'temperature_c_' -> 'temperature_C'
    # 'time_h_' -> 'time_h'

    rename_map = {
        'method_id': 'name',
        'strain_name_id': 'strain_id',
        'strain_name_raw': 'strain_name',
        'inoculum_volume_l_': 'inoculum_volume_L',
        'reaction_volume_l_': 'reaction_volume_L',
        'temperature_c_': 'temperature_C',
        'time_h_': 'time_h',
        'description': 'description',
        'note': 'note',
        'protocol_url': 'protocol_url'
    }

    # Also handle variants without trailing underscores if janitor behavior differs
    for col in list(df.columns):
        if col == 'inoculum_volume_l': rename_map[col] = 'inoculum_volume_L'
        if col == 'reaction_volume_l': rename_map[col] = 'reaction_volume_L'
        if col == 'temperature_c': rename_map[col] = 'temperature_C'
        if col == 'time_h': rename_map[col] = 'time_h'

    # 4. Coercion
    # Identify which numeric columns actually exist
    numeric_cols = [c for c in ['inoculum_volume_l_', 'reaction_volume_l_', 'temperature_c_', 'time_h_',
                               'inoculum_volume_l', 'reaction_volume_l', 'temperature_c', 'time_h']
                    if c in df.columns]

    df = coercion_mod.coerce_columns(
        df,
        float_cols=numeric_cols
    )

    # Lineage
    df['etl_run_id'] = etl_run_id
    df['lineage_group_id'] = lineage_group_id

    available_cols = [c for c in rename_map.keys() if c in df.columns]
    record_df = df[available_cols].rename(columns=rename_map).copy()

    # Drop rows without a method name
    if 'name' in record_df.columns:
        record_df = record_df.dropna(subset=['name'])
        record_df = record_df[record_df['name'] != '']

    return record_df
