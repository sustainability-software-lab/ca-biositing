"""
EnzymaticHydrolysisMethod transformation module.
"""
import pandas as pd
import uuid
from typing import Optional
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod

@task
def transform_enz_hydr_method(
    raw_df: pd.DataFrame,
    etl_run_id: Optional[str] = None,
    lineage_group_id: Optional[int] = None
) -> pd.DataFrame:
    """
    Transforms raw enzymatic hydrolysis method data into the EnzymaticHydrolysisMethod table format.
    """
    logger = get_run_logger()

    if raw_df is None or raw_df.empty:
        logger.warning("No raw data provided to EnzymaticHydrolysisMethod transform")
        return pd.DataFrame()

    df = raw_df.copy()
    logger.info(f"EnzymaticHydrolysisMethod: raw_df columns: {df.columns.tolist()}")

    # Standard cleaning
    # Exclude notes and description from lowercasing
    cleaned_df = cleaning_mod.standard_clean(df, lowercase=False)
    if cleaned_df is not None:
        lowercase_cols = [c for c in cleaned_df.columns if 'note' not in c.lower() and 'description' not in c.lower()]
        cleaned_df = cleaning_mod.to_lowercase_df(cleaned_df, columns=lowercase_cols)

    if cleaned_df is None:
        logger.error("cleaning_mod.standard_clean returned None for EnzymaticHydrolysisMethod")
        return pd.DataFrame()

    # Add lineage IDs
    if etl_run_id is not None:
        cleaned_df['etl_run_id'] = etl_run_id
    if lineage_group_id is not None:
        cleaned_df['lineage_group_id'] = lineage_group_id

    # Coercion for float columns
    coerced_df = coercion_mod.coerce_columns(
        cleaned_df,
        float_cols=['reaction_volume_ul', 'temperature_c', 'time_h'],
        datetime_cols=['created_at', 'updated_at']
    )

    # Generate UUIDs for new records if not present
    if 'eh_uuid' not in coerced_df.columns:
        coerced_df['eh_uuid'] = [str(uuid.uuid4()) for _ in range(len(coerced_df))]

    return coerced_df
