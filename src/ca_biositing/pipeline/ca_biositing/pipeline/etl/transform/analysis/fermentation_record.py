import pandas as pd
import numpy as np
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes

@task
def transform_fermentation_record(
    raw_df: pd.DataFrame,
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None
) -> pd.DataFrame:
    """
    Transforms raw DataFrame into the FermentationRecord table format.
    Includes cleaning, coercion, and normalization.
    """
    from ca_biositing.datamodels.models import (
        Resource,
        PreparedSample,
        Method,
        Strain,
        Contact,
        Dataset,
        FileObjectMetadata,
        Experiment,
        Equipment,
        DeconVessel,
        BioconversionMethod
    )
    logger = get_run_logger()
    logger.info("Transforming raw data for FermentationRecord table")

    if raw_df is None or raw_df.empty:
        logger.warning("raw_df is None or empty for FermentationRecord transform")
        return pd.DataFrame()

    # Handle duplicate columns
    raw_df.columns = [str(c).strip() for c in raw_df.columns]
    if "" in raw_df.columns:
        raw_df = raw_df.drop(columns=[""])

    # Pre-clean names
    raw_df = cleaning_mod.clean_names_df(raw_df)

    # Map legacy/variant column names
    col_map = {}
    for c in list(raw_df.columns):
        lc = str(c).lower().strip()
        if 'bioconv' in lc or 'bioconversion' in lc or lc in ('bio_conv_method', 'bioconv_method'):
            col_map[c] = 'bioconversion_method'
        if 'pretreatment' in lc or 'decon' in lc:
            col_map[c] = 'decon_method'
        if 'enzyme' in lc or lc in ('eh_method', 'enzyme_method'):
            col_map[c] = 'eh_method'

    if col_map:
        raw_df = raw_df.rename(columns=col_map)

    # 1. Cleaning & Coercion
    df_copy = raw_df.copy()
    df_copy['dataset'] = 'bioconversion'
    cleaned_df = cleaning_mod.standard_clean(df_copy)

    if cleaned_df is None:
        return pd.DataFrame()

    # Add lineage IDs
    if etl_run_id is not None:
        cleaned_df['etl_run_id'] = etl_run_id
    if lineage_group_id is not None:
        cleaned_df['lineage_group_id'] = lineage_group_id

    coerced_df = coercion_mod.coerce_columns(
        cleaned_df,
        int_cols=['replicate_no'],
        datetime_cols=['created_at', 'updated_at']
    )

    # 2. Normalization
    normalize_columns = {
        'resource': (Resource, 'name'),
        'prepared_sample': (PreparedSample, 'name'),
        'bioconversion_method': (BioconversionMethod, 'name'),
        'decon_method': (Method, 'name'),
        'eh_method': (Method, 'name'),
        'exp_id': (Experiment, 'name'),
        'analyst_email': (Contact, 'email'),
        'dataset': (Dataset, 'name'),
        'raw_data_url': (FileObjectMetadata, 'uri'),
        'reactor_vessel': (DeconVessel, 'name'),
        'analysis_equipment': (Equipment, 'name')
    }

    normalized_dfs = normalize_dataframes(coerced_df, normalize_columns)
    normalized_df = normalized_dfs[0]

    # 3. Fetch Strain ID from BioconversionMethod
    # We want the strain_id to come from the BioconversionMethod table
    if 'bioconversion_method_id' in normalized_df.columns:
        try:
            from ca_biositing.pipeline.utils.engine import engine as etl_engine
            from sqlmodel import Session, select
            with Session(etl_engine) as db:
                # Get mapping of BioconversionMethod.id -> BioconversionMethod.strain_id
                stmt = select(BioconversionMethod.id, BioconversionMethod.strain_id)
                mapping_rows = db.exec(stmt).all()
                bcm_to_strain = {r[0]: r[1] for r in mapping_rows if r[0] is not None}

                normalized_df['strain_id'] = normalized_df['bioconversion_method_id'].map(bcm_to_strain)
                logger.info(f"Mapped strain_id from bioconversion_method_id for {normalized_df['strain_id'].notna().sum()} rows")
        except Exception as e:
            logger.warning(f"Could not map strain_id from BioconversionMethod table: {e}")

    # 4. Table Specific Mapping
    rename_map = {
        'record_id': 'record_id',
        'replicate_no': 'technical_replicate_no',
        'well_position': 'well_position',
        'qc_result': 'qc_pass',
        'note': 'note',
        'etl_run_id': 'etl_run_id',
        'lineage_group_id': 'lineage_group_id',
        'bioconversion_method_id': 'bioconversion_method_id',
        'decon_method_id': 'pretreatment_method_id',
        'eh_method_id': 'eh_method_id',
        'resource_id': 'resource_id',
        'prepared_sample_id': 'prepared_sample_id',
        'exp_id_id': 'experiment_id',
        'analyst_email_id': 'analyst_id',
        'dataset_id': 'dataset_id',
        'raw_data_url_id': 'raw_data_id',
        'reactor_vessel_id': 'vessel_id',
        'analysis_equipment_id': 'analyte_detection_equipment_id',
        'strain_id': 'strain_id'
    }

    available_cols = [c for c in rename_map.keys() if c in normalized_df.columns]
    final_rename = {k: v for k, v in rename_map.items() if k in available_cols}

    try:
        record_df = normalized_df[available_cols].rename(columns=final_rename).copy()

        if 'record_id' in record_df.columns:
            record_df = record_df[~record_df['record_id'].astype(str).str.strip().isin(['-', 'nan', 'None', ''])]
            record_df = record_df.dropna(subset=['record_id'])
        else:
            return pd.DataFrame()

        return record_df
    except Exception as e:
        logger.error(f"Error during FermentationRecord transform: {e}")
        return pd.DataFrame()
