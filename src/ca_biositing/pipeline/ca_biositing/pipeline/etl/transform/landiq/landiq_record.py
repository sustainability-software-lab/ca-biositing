"""
ETL Transform for Land IQ Data.


This module provides functionality for transforming Land IQ GeoDataFrames into the LandiqRecord table format.
"""

import os
import pandas as pd
import geopandas as gpd
from prefect import task, get_run_logger
import ca_biositing.pipeline.utils.cleaning_functions.cleaning as cleaning_mod
import ca_biositing.pipeline.utils.cleaning_functions.coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes

@task(persist_result=False)
def transform_landiq_record(
    gdf: gpd.GeoDataFrame,
    etl_run_id: str = None,
    lineage_group_id: int = None
) -> pd.DataFrame:
    """
    Transforms Land IQ GeoDataFrame into the LandiqRecord table format.

    Args:
        gdf: Raw GeoDataFrame from Land IQ shapefile.
        etl_run_id: ID of the current ETL run.
        lineage_group_id: ID of the lineage group.

    Returns:
        A pandas DataFrame formatted for the landiq_record table.
    """
    from ca_biositing.datamodels.models import (
        Dataset,
        Polygon,
        PrimaryAgProduct,
    )

    logger = get_run_logger()
    logger.info("Transforming Land IQ data for LandiqRecord table")

    if gdf is None or gdf.empty:
        logger.error("Input GeoDataFrame is empty or None")
        return pd.DataFrame()

    # 1. Initial Cleaning & Preparation
    # Convert GeoDataFrame to regular DataFrame to avoid issues with standard_clean
    df = pd.DataFrame(gdf.copy())

    # Set dataset name and version as requested
    df['dataset'] = 'landiq_2024'
    df['version'] = 'land use 2024'

    # Map shapefile columns to model fields
    # MAIN_CROP is the main crop for single cropped fields
    if 'MAIN_CROP' in df.columns:
        df['main_crop'] = df['MAIN_CROP']
    if 'CLASS1' in df.columns:
        df['secondary_crop'] = df['CLASS1']
    if 'CLASS2' in df.columns:
        df['tertiary_crop'] = df['CLASS2']
    if 'CLASS3' in df.columns:
        df['quaternary_crop'] = df['CLASS3']

    # Map county column
    if 'COUNTY' in df.columns:
        df['county'] = df['COUNTY']

    # Map percentage columns
    for i in range(1, 5):
        col_name = f'PCNT{i}'
        if col_name in df.columns:
            df[f'pct{i}'] = df[col_name]


    # Load crop mapping
    crop_map = {}
    # Handle both package and notebook contexts
    try:
        # Try to get the directory of the current file
        base_path = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        # Fallback for notebook context or when __file__ is not defined
        # We use the workspace root and the known relative path
        base_path = os.path.join(os.getcwd(), 'src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/landiq')

    mapping_path = os.path.join(base_path, 'crops_classification.csv')

    # If the path doesn't exist, try one more fallback for common notebook execution locations
    if not os.path.exists(mapping_path):
        # Try relative to workspace root if we are in a notebook
        workspace_path = os.path.join(os.getcwd(), 'src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/landiq/crops_classification.csv')
        if os.path.exists(workspace_path):
            mapping_path = workspace_path

    try:
        if os.path.exists(mapping_path):
            mapping_df = pd.read_csv(mapping_path)
            crop_map = {str(k).strip().upper(): v for k, v in zip(mapping_df['crop_code'], mapping_df['crop'])}
            logger.info(f"Loaded {len(crop_map)} crop mappings from {mapping_path}")

            # Convert crop codes to text
            for col in ['main_crop', 'secondary_crop', 'tertiary_crop', 'quaternary_crop']:
                if col in df.columns:
                    # Ensure we handle potential whitespace and case sensitivity in codes
                    df[col] = df[col].astype(str).str.strip().str.upper().map(crop_map).fillna(df[col])
        else:
            logger.warning(f"Crop mapping file not found at {mapping_path}")
    except Exception as e:
        # Use print as fallback if logger isn't initialized in some contexts
        msg = f"Could not load or apply crop mapping: {e}"
        try:
            logger.warning(msg)
        except:
            print(msg)

    # Map UniqueID to record_id for lineage and upsert
    if 'UniqueID' in df.columns:
        df['record_id'] = df['UniqueID']
    elif 'UNIQUEID' in df.columns:
        df['record_id'] = df['UNIQUEID']

    # Handle Irrigation status (IRR_TYP1PA/IRR_TYP2PA etc)
    if 'IRR_TYP1PA' in df.columns:
        df['irrigated'] = df['IRR_TYP1PA'].astype(str).str.lower().str.contains('irrigated')
    else:
        df['irrigated'] = False

    # 2. Standard Clean (Bypassed)
    # We bypass the cleaning module entirely to avoid persistent AttributeError issues
    # in the notebook environment. We use the DataFrame as-is.
    cleaned_df = df.copy()

    # Handle non-numeric values like '**' in percentage columns before cleaning names
    # to ensure they are preserved as numeric or null
    for i in range(1, 5):
        col = f'pct{i}'
        if col in cleaned_df.columns:
            cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')

    # Ensure column names are cleaned (snake_case) as expected by the rest of the pipeline
    # but without the buggy to_lowercase_df call
    cleaned_df = cleaning_mod.clean_names_df(cleaned_df)

    # CRITICAL: Remove duplicate columns after clean_names_df
    # This prevents AttributeError: 'DataFrame' object has no attribute 'str'
    # and ValueError: Cannot set a DataFrame with multiple columns
    cleaned_df = cleaned_df.loc[:, ~cleaned_df.columns.duplicated()].copy()

    # Re-apply mapping to ensure correct values and ensure results are lowercase
    for col in ['main_crop', 'secondary_crop', 'tertiary_crop', 'quaternary_crop']:
        if col in cleaned_df.columns and crop_map:
            # Ensure we are working with a Series
            series = cleaned_df[col]
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]
            # Map the code to the crop name, or keep the value if mapping fails, then lowercase
            cleaned_df[col] = series.astype(str).str.strip().str.upper().map(crop_map).fillna(series).astype(str).str.lower().str.strip()

    # Manually lowercase string columns and handle empty strings
    for col in cleaned_df.columns:
        series = cleaned_df[col]
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]

        if series.dtype == "object" or pd.api.types.is_string_dtype(series):
            # CRITICAL: We lowercase all string columns to ensure consistency
            # with the lowercased lookup tables (primary_ag_product, dataset, etc.)
            # EXCEPT 'dataset' which we want to match specifically if it's already defined
            # as 'landiq_2023'. However, in this case 'landiq_2023' is already lowercase.
            cleaned_df[col] = series.astype(str).str.lower().str.strip().replace(r"^\s*$", None, regex=True)

    # Add lineage IDs
    if etl_run_id:
        cleaned_df['etl_run_id'] = etl_run_id
    if lineage_group_id:
        cleaned_df['lineage_group_id'] = lineage_group_id

    # 3. Coercion
    coerced_df = coercion_mod.coerce_columns(
        cleaned_df,
        float_cols=['acres', 'pct1', 'pct2', 'pct3', 'pct4'],
        int_cols=['confidence'] if 'confidence' in cleaned_df.columns else []
    )

    # 4. Normalization (Bypassed for Bulk Loading)
    # We no longer use normalize_dataframes here because the bulk load step
    # handles ID resolution in memory to avoid N+1 queries.
    # We just prepare the columns for the load step.

    # 5. Table Specific Mapping
    rename_map = {
        'record_id': 'record_id',
        'acres': 'acres',
        'version': 'version',
        'etl_run_id': 'etl_run_id',
        'lineage_group_id': 'lineage_group_id',
        'irrigated': 'irrigated',
        'confidence': 'confidence',
        'dataset': 'dataset_id',
        'main_crop': 'main_crop',
        'secondary_crop': 'secondary_crop',
        'tertiary_crop': 'tertiary_crop',
        'quaternary_crop': 'quaternary_crop',
        'pct1': 'pct1',
        'pct2': 'pct2',
        'pct3': 'pct3',
        'pct4': 'pct4',
        'county': 'county'
    }

    available_cols = [c for c in rename_map.keys() if c in coerced_df.columns]
    final_rename = {k: v for k, v in rename_map.items() if k in available_cols}

    try:
        record_df = coerced_df[available_cols].copy().rename(columns=final_rename)

        # Ensure record_id exists for lineage tracking
        if 'record_id' in record_df.columns:
            record_df = record_df.dropna(subset=['record_id'])
        else:
            logger.warning("record_id (UniqueID) missing from Land IQ transform")

        # Add geometry for polygon handling in load step
        # We use the original gdf geometry to ensure we have the geometry objects
        if 'geometry' in gdf.columns:
            # Align indices to ensure correct mapping if rows were dropped
            record_df['geometry'] = gdf.loc[record_df.index, 'geometry']

        logger.info(f"Successfully transformed {len(record_df)} Land IQ records")
        return record_df

    except Exception as e:
        logger.error(f"Error during Land IQ transform: {e}", exc_info=True)
        return pd.DataFrame()
