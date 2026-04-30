"""
ETL Transform for FieldSample using SampleMetadata_v03-BioCirV multi-worksheet extraction.

Refactored to use four separate worksheets with multi-way join strategy:
- 01_Sample_IDs: Base dataset (sample_name, resource, provider, fv_date_time)
- 02_Sample_Desc: Location and description details (sampling location, particle dimensions, methods)
- 03_Qty_FieldStorage: Quantity, unit, and field storage (amount, container, field storage location)
- 04_Producers: Producer/origin information (producer location for field_sample_storage_location_id)

Join strategy: Left-join all worksheets on 'sample_name' to preserve all records from 01_Sample_IDs.
"""

import pandas as pd
from typing import List, Optional, Dict
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes

# List the names of the extract modules this transform depends on.
EXTRACT_SOURCES: List[str] = [
    "sample_ids",        # 01_Sample_IDs
    "sample_desc",       # 02_Sample_Desc
    "qty_field_storage", # 03_Qty_FieldStorage
    "producers"          # 04_Producers
]


@task
def transform_field_sample_v03(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None
) -> Optional[pd.DataFrame]:
    """
    Transforms raw sample metadata from four worksheets into FieldSample table format.

    Multi-way join on 'sample_name' column across all four worksheets.
    Left-join preserves all records from 01_Sample_IDs base dataset.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    # CRITICAL: Lazy import models inside the task to avoid Docker import hangs
    from ca_biositing.datamodels.models import (
        Resource,
        Provider,
        Contact,
        Unit,
        Dataset,
        SoilType,
        LocationAddress,
        PrimaryAgProduct,
        PreparedSample,
        Method,
        FieldStorageMethod,
        Place
    )

    # 1. Input Validation
    for source in EXTRACT_SOURCES:
        if source not in data_sources:
            logger.error(f"Required data source '{source}' not found.")
            return None

    sample_ids_df = data_sources["sample_ids"].copy()
    sample_desc_df = data_sources["sample_desc"].copy()
    qty_field_storage_df = data_sources["qty_field_storage"].copy()
    producers_df = data_sources["producers"].copy()

    if sample_ids_df.empty:
        logger.warning("Source 'sample_ids' (01_Sample_IDs) is empty.")
        return pd.DataFrame()

    logger.info(f"Transforming FieldSample data from multi-worksheet sources...")
    logger.info(f"  - 01_Sample_IDs: {len(sample_ids_df)} rows")
    logger.info(f"  - 02_Sample_Desc: {len(sample_desc_df)} rows")
    logger.info(f"  - 03_Qty_FieldStorage: {len(qty_field_storage_df)} rows")
    logger.info(f"  - 04_Producers: {len(producers_df)} rows")

    # 2. Cleaning & Coercion
    # Apply dataset tag and clean all worksheets
    sample_ids_df['dataset'] = 'biocirv'
    sample_desc_df['dataset'] = 'biocirv'
    qty_field_storage_df['dataset'] = 'biocirv'
    producers_df['dataset'] = 'biocirv'

    clean_ids = cleaning_mod.standard_clean(sample_ids_df)
    clean_desc = cleaning_mod.standard_clean(sample_desc_df)
    clean_qty = cleaning_mod.standard_clean(qty_field_storage_df)
    clean_prod = cleaning_mod.standard_clean(producers_df)

    # Coerce columns to appropriate types
    coerced_ids = coercion_mod.coerce_columns(
        clean_ids,
        datetime_cols=['fv_date_time', 'created_at', 'updated_at']
    )

    coerced_desc = coercion_mod.coerce_columns(
        clean_desc,
        float_cols=['particle_l_cm', 'particle_w_cm', 'particle_h_cm'],
        datetime_cols=['sample_ts', 'created_at', 'updated_at']
    )

    coerced_qty = coercion_mod.coerce_columns(
        clean_qty,
        int_cols=['qty'],
        datetime_cols=['created_at', 'updated_at']
    )

    coerced_prod = coercion_mod.coerce_columns(
        clean_prod,
        datetime_cols=['prod_date', 'created_at', 'updated_at']
    )

    # 3. Handle Duplicates in Base Dataset
    # Keep only first occurrence of each sample_name
    if 'sample_name' in coerced_ids.columns:
        initial_count = len(coerced_ids)
        coerced_ids = coerced_ids.drop_duplicates(subset=['sample_name'], keep='first')
        logger.info(f"Base dataset: dropped duplicates from {initial_count} to {len(coerced_ids)} records")

    # 4. Multi-way Join on sample_name
    # Left-join all worksheets to preserve all records from 01_Sample_IDs
    logger.info("Performing multi-way left-join on 'sample_name'...")

    joined_df = coerced_ids.copy()

    # Join 02_Sample_Desc
    if not coerced_desc.empty:
        joined_df = joined_df.merge(
            coerced_desc,
            on='sample_name',
            how='left',
            suffixes=('', '_desc')
        )
        logger.info(f"After joining 02_Sample_Desc: {len(joined_df)} records")

    # Join 03_Qty_FieldStorage
    if not coerced_qty.empty:
        joined_df = joined_df.merge(
            coerced_qty,
            on='sample_name',
            how='left',
            suffixes=('', '_qty')
        )
        logger.info(f"After joining 03_Qty_FieldStorage: {len(joined_df)} records")

    # Join 04_Producers
    if not coerced_prod.empty:
        joined_df = joined_df.merge(
            coerced_prod,
            on='sample_name',
            how='left',
            suffixes=('', '_prod')
        )
        logger.info(f"After joining 04_Producers: {len(joined_df)} records")

    logger.info(f"Join complete: {len(joined_df)} total records")

    # 5. Unit Extraction from Sample_Container
    # Extract unit from fields like "Bucket (5 gal.)", "Core", "Bale"
    # Map to Unit model
    logger.info("Extracting units from sample_container field...")
    if 'sample_container' in joined_df.columns:
        # Simple extraction: look for parenthesized unit indicator
        # For now, we'll preserve the container name and let normalization handle it
        joined_df['container_unit'] = joined_df['sample_container'].fillna('')
        logger.info(f"Extracted container units from {joined_df['sample_container'].notna().sum()} records")

    # 6. Normalization (Name-to-ID Swapping)
    normalize_columns = {
        'resource': (Resource, 'name'),
        'providercode': (Provider, 'codename'),  # Note: GSheet cleaning converts "ProviderCode" to "providercode" (no underscore)
        'primary_collector': (Contact, 'name'),
        'storage_dur_units': (Unit, 'name'),
        'particle_units': (Unit, 'name'),
        'container_unit': (Unit, 'name'),  # New: unit from sample_container
        'prepared_sample': (PreparedSample, 'name'),
        'soil_type': (SoilType, 'name'),
        'storage_mode': (FieldStorageMethod, 'name'),
        'field_storage_method': (FieldStorageMethod, 'name'),
        'processing_method': (Method, 'name'),  # New: methods column
        'primary_ag_product': (PrimaryAgProduct, 'name'),
        'dataset': (Dataset, 'name'),
        'fieldstorage_location': (LocationAddress, 'address_line1'),  # Collection-site storage
        'prod_location': (LocationAddress, 'address_line1'),  # Producer location -> field_sample_storage_location
    }

    logger.info("Normalizing joined data (swapping names for IDs)...")

    # Manual normalization for Place (County) to avoid NotNullViolation on geoid
    # and provide a resilient lookup that defaults to state-level GEOID.
    from ca_biositing.pipeline.utils.geo_utils import get_geoid
    from sqlmodel import Session, select
    from ca_biositing.pipeline.utils.engine import engine

    with Session(engine) as session:
        places = session.exec(select(Place.geoid, Place.county_name)).all()
        county_to_geoid = {p.county_name.lower(): p.geoid for p in places if p.county_name}

    # Handle county mapping from sampling location (02_Sample_Desc)
    if 'sampling_city' in joined_df.columns:
        joined_df['county'] = joined_df['sampling_city'].fillna('')
        joined_df['county_id'] = joined_df['county'].apply(lambda x: get_geoid(x, county_to_geoid))

    normalized_dfs = normalize_dataframes(joined_df, normalize_columns)
    normalized_df = normalized_dfs[0]

    # 6b. Bridge County (Place) to LocationAddress
    # Create generic LocationAddress for each County
    if 'county_id' in normalized_df.columns:
        logger.info("Bridging County (Place) to LocationAddress...")
        from sqlmodel import Session, select
        from ca_biositing.pipeline.utils.engine import engine

        with Session(engine) as session:
            county_ids = normalized_df['county_id'].dropna().unique()
            place_to_address_map = {}

            for geoid in county_ids:
                stmt = select(LocationAddress).where(
                    LocationAddress.geography_id == geoid,
                    LocationAddress.address_line1 == None
                )
                address = session.exec(stmt).first()

                if not address:
                    logger.info(f"Creating new generic LocationAddress for county geoid: {geoid}")
                    address = LocationAddress(geography_id=geoid, address_line1=None)
                    session.add(address)
                    session.flush()

                place_to_address_map[geoid] = address.id

            session.commit()

            normalized_df['sampling_location_id'] = normalized_df['county_id'].map(place_to_address_map)
            logger.info(f"Mapped {len(place_to_address_map)} counties to LocationAddresses")

    # 7. Select and Rename Columns
    # Extended mapping to include particle dimensions and new fields
    rename_map = {
        'sample_name': 'name',
        'resource_id': 'resource_id',
        'providercode_id': 'provider_id',  # Note: normalized from 'providercode' (no underscore)
        'primary_collector_id': 'collector_id',
        'sample_source': 'sample_collection_source',
        'qty': 'amount_collected',
        'container_unit_id': 'amount_collected_unit_id',
        'sampling_location_id': 'sampling_location_id',
        'storage_mode_id': 'field_storage_method_id',
        'field_storage_method_id': 'field_storage_method_id',
        'storage_dur_value': 'field_storage_duration_value',
        'storage_dur_units_id': 'field_storage_duration_unit_id',
        'fieldstorage_location_id': 'field_storage_location_id',  # Collection-site storage
        'prod_location_id': 'field_sample_storage_location_id',  # Lab/facility storage
        'sample_ts': 'collection_timestamp',
        'sample_notes': 'note',
        'processing_method_id': 'methods_id',  # New methods column
        # Extended fields: particle dimensions
        'particle_l_cm': 'particle_length_cm',
        'particle_w_cm': 'particle_width_cm',
        'particle_h_cm': 'particle_height_cm',
    }

    # Preserve raw location info for linking
    location_link_cols = ['sampling_location', 'sampling_street', 'sampling_city', 'sampling_zip']
    for col in location_link_cols:
        if col in normalized_df.columns:
            rename_map[col] = col

    # Filter rename_map to only include columns that exist
    available_rename = {k: v for k, v in rename_map.items() if k in normalized_df.columns}

    try:
        final_df = normalized_df[list(available_rename.keys())].rename(columns=available_rename).assign(
            collection_method=None,
            harvest_datemethod=None,
            harvest_date=None
        )

        # 8. Lineage Tracking
        if etl_run_id:
            final_df['etl_run_id'] = etl_run_id
        if lineage_group_id:
            final_df['lineage_group_id'] = lineage_group_id

        if 'dataset_id' in normalized_df.columns:
            final_df['dataset_id'] = normalized_df['dataset_id']

        logger.info(f"Successfully transformed {len(final_df)} FieldSample records (v03).")
        return final_df

    except Exception as e:
        logger.error(f"Error during FieldSample v03 transform: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return pd.DataFrame()
