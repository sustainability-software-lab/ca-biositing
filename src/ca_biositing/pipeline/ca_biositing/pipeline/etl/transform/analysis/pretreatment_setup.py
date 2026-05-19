"""
PretreatmentSetup transformation module.
"""
import pandas as pd
import uuid
from typing import Optional
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes

@task
def transform_pretreatment_setup(
    raw_df: pd.DataFrame,
    etl_run_id: Optional[str] = None,
    lineage_group_id: Optional[int] = None
) -> pd.DataFrame:
    """
    Transforms raw pretreatment setup data into the PretreatmentSetup table format.
    """
    from ca_biositing.datamodels.models import (
        Contact,
        Method,
        DeconVessel
    )
    logger = get_run_logger()

    if raw_df is None or raw_df.empty:
        logger.warning("No raw data provided to PretreatmentSetup transform")
        return pd.DataFrame()

    df = raw_df.copy()
    logger.info(f"PretreatmentSetup: raw_df columns: {df.columns.tolist()}")

    # Standard cleaning
    # Exclude notes and description from lowercasing
    cleaned_df = cleaning_mod.standard_clean(df, lowercase=False)
    if cleaned_df is not None:
        lowercase_cols = [c for c in cleaned_df.columns if 'note' not in c.lower() and 'description' not in c.lower()]
        cleaned_df = cleaning_mod.to_lowercase_df(cleaned_df, columns=lowercase_cols)

    if cleaned_df is None:
        logger.error("cleaning_mod.standard_clean returned None for PretreatmentSetup")
        return pd.DataFrame()

    # Add lineage IDs
    if etl_run_id is not None:
        cleaned_df['etl_run_id'] = etl_run_id
    if lineage_group_id is not None:
        cleaned_df['lineage_group_id'] = lineage_group_id

    # Handle comma-separated strings to lists for Resources and Prepared_samples
    def split_comma_string(val):
        if pd.isna(val) or val == "":
            return []
        return [item.strip() for item in str(val).split(',') if item.strip()]

    if 'resources' in cleaned_df.columns:
        cleaned_df['resources'] = cleaned_df['resources'].apply(split_comma_string)
    if 'prepared_samples' in cleaned_df.columns:
        cleaned_df['prepared_samples'] = cleaned_df['prepared_samples'].apply(split_comma_string)

    # Coercion
    coerced_df = coercion_mod.coerce_columns(
        cleaned_df,
        datetime_cols=['experiment_date', 'created_at', 'updated_at']
    )

    # Ensure experiment_date is date object if it's datetime
    if 'experiment_date' in coerced_df.columns:
        # Avoid .dt.date on non-datetime columns or Series with mixed types
        coerced_df['experiment_date'] = pd.to_datetime(coerced_df['experiment_date'], errors='coerce').apply(lambda x: x.date() if pd.notnull(x) else None)

    # Normalization
    normalize_columns = {
        'analyst_email': (Contact, "email"),
        'decon_method_id': Method,
        'decon_vessel_id': DeconVessel,
        'eh_method_id': Method,
    }

    normalized_dfs = normalize_dataframes(coerced_df, normalize_columns)
    normalized_df = normalized_dfs[0]

    # Map normalized column IDs to correct field names
    rename_map = {}
    for col in normalize_columns.keys():
        norm_col = f"{col}_id"
        if norm_col in normalized_df.columns:
            target_name = 'analyst_id' if col == 'analyst_email' else norm_col
            rename_map[norm_col] = target_name

    if rename_map:
        normalized_df = normalized_df.rename(columns=rename_map)

    # Generate UUIDs for new records if not present
    if 'pretreatment_uuid' not in normalized_df.columns:
        normalized_df['pretreatment_uuid'] = [str(uuid.uuid4()) for _ in range(len(normalized_df))]

    return normalized_df
