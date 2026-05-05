"""
ETL Transform for LocationAddress (v03 workflow).

Transforms raw sample metadata from four worksheets into unique LocationAddress records.
Handles two types of locations:
1. Collection-site locations (from 02_Sample_Desc sampling_location fields)
2. Lab/facility storage locations (from 04_Producers producer location fields)
"""

import pandas as pd
from typing import Optional, Dict
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod

@task
def transform_location_address_v03(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None
) -> Optional[pd.DataFrame]:
    """
    Extracts unique locations from multi-worksheet sample metadata.

    Combines:
    - Collection locations from 02_Sample_Desc (sampling_location, sampling_street, sampling_city, sampling_zip)
    - Producer/facility locations from 04_Producers (prod_location, prod_street, prod_city, prod_zip)

    Returns deduplicated LocationAddress records for both location types.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    # Expect both sample_desc and producers in data_sources
    sample_desc = data_sources.get("sample_desc", pd.DataFrame())
    producers = data_sources.get("producers", pd.DataFrame())

    if sample_desc.empty and producers.empty:
        logger.warning("Both 'sample_desc' and 'producers' data sources are empty.")
        return pd.DataFrame()

    logger.info("Extracting unique LocationAddress records from multi-worksheet sources...")
    logger.info(f"  - sample_desc: {len(sample_desc)} rows")
    logger.info(f"  - producers: {len(producers)} rows")

    # Clean both data sources
    clean_sample_desc = cleaning_mod.standard_clean(sample_desc) if not sample_desc.empty else pd.DataFrame()
    clean_producers = cleaning_mod.standard_clean(producers) if not producers.empty else pd.DataFrame()

    locations_list = []

    # 1. Extract collection-site locations from sample_desc
    if not clean_sample_desc.empty:
        logger.info("Extracting collection-site locations from sample_desc...")
        location_cols = ['sampling_location', 'sampling_street', 'sampling_city', 'sampling_zip']
        available_cols = [c for c in location_cols if c in clean_sample_desc.columns]

        if available_cols:
            collection_locations = clean_sample_desc[available_cols].drop_duplicates().dropna(how='all')

            if not collection_locations.empty:
                # Rename to LocationAddress model fields
                rename_map = {
                    'sampling_street': 'address_line1',
                    'sampling_city': 'city',
                    'sampling_zip': 'zip'
                }
                available_rename = {k: v for k, v in rename_map.items() if k in collection_locations.columns}
                collection_locations = collection_locations.rename(columns=available_rename)

                # Add location type indicator
                collection_locations['location_type'] = 'collection_site'

                locations_list.append(collection_locations)
                logger.info(f"Extracted {len(collection_locations)} unique collection-site locations")

    # 2. Extract producer/facility locations from producers
    if not clean_producers.empty:
        logger.info("Extracting producer/facility locations from producers...")
        producer_cols = ['prod_location', 'prod_street', 'prod_city', 'prod_zip']
        available_cols = [c for c in producer_cols if c in clean_producers.columns]

        if available_cols:
            producer_locations = clean_producers[available_cols].drop_duplicates().dropna(how='all')

            if not producer_locations.empty:
                # Rename to LocationAddress model fields
                rename_map = {
                    'prod_street': 'address_line1',
                    'prod_city': 'city',
                    'prod_zip': 'zip',
                    'prod_location': 'location_name'  # Keep producer name for reference
                }
                available_rename = {k: v for k, v in rename_map.items() if k in producer_locations.columns}
                producer_locations = producer_locations.rename(columns=available_rename)

                # Add location type indicator
                producer_locations['location_type'] = 'facility_storage'

                locations_list.append(producer_locations)
                logger.info(f"Extracted {len(producer_locations)} unique producer/facility locations")

    # Combine all locations
    if locations_list:
        all_locations = pd.concat(locations_list, ignore_index=True)
        all_locations = all_locations.drop_duplicates().dropna(how='all')

        logger.info(f"Total unique locations after deduplication: {len(all_locations)}")

        # Determine is_anonymous: True if address_line1 is missing/empty
        if 'address_line1' in all_locations.columns:
            all_locations['is_anonymous'] = all_locations['address_line1'].isna() | (all_locations['address_line1'] == "")
        else:
            all_locations['is_anonymous'] = True

    else:
        logger.warning("No location data found in any source.")
        all_locations = pd.DataFrame()

    # Add lineage tracking metadata
    if not all_locations.empty:
        if etl_run_id:
            all_locations['etl_run_id'] = etl_run_id
        if lineage_group_id:
            all_locations['lineage_group_id'] = lineage_group_id

    logger.info(f"Successfully transformed {len(all_locations)} unique location candidate records.")
    return all_locations
