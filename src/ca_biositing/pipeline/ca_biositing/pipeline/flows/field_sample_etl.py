from prefect import flow, get_run_logger
from ca_biositing.pipeline.etl.extract.sample_ids import extract as extract_sample_ids
from ca_biositing.pipeline.etl.extract.sample_desc import extract as extract_sample_desc
from ca_biositing.pipeline.etl.extract.qty_field_storage import extract as extract_qty_field_storage
from ca_biositing.pipeline.etl.extract.producers import extract as extract_producers
from ca_biositing.pipeline.etl.extract.provider_info import extract as extract_provider
from ca_biositing.pipeline.etl.transform.field_sampling.location_address import transform_location_address
from ca_biositing.pipeline.etl.transform.field_sampling.field_sample import transform_field_sample
from ca_biositing.pipeline.etl.load.location_address import load_location_address
from ca_biositing.pipeline.etl.load.field_sample import load_field_sample
from ca_biositing.pipeline.utils.lineage import create_lineage_group, create_etl_run_record
from ca_biositing.datamodels.views import refresh_all_views
from ca_biositing.pipeline.utils.engine import engine

@flow(name="Field Sample ETL")
def field_sample_etl_flow():
    """
    Field Sample ETL Flow -  (SampleMetadata-BioCirV multi-worksheet strategy)

    This flow implements a multi-way left-join strategy across four worksheets:
    - 01_Sample_IDs: Base dataset (137 rows) - serves as left-join key
    - 02_Sample_Desc: Sampling location and particle dimensions (104 rows)
    - 03_Qty_FieldStorage: Quantity, sample container, field storage location (142 rows)
    - 04_Producers: Producer/facility location and extended metadata (64 rows)

    The join sequence preserves all records from 01_Sample_IDs (left-join on sample_name).

    Workflow:
    1. Extract all four worksheets in parallel (independent Prefect tasks)
    2. Transform LocationAddress (both collection-site and lab/facility storage locations)
    3. Load LocationAddress records
    4. Transform FieldSample (multi-way join with unit extraction, extended fields)
    5. Load FieldSample records
    6. Refresh materialized views
    """
    logger = get_run_logger()
    logger.info("Starting Field Sample ETL flow ( - multi-worksheet strategy)...")

    # 1. Lineage Tracking
    etl_run_id = create_etl_run_record("Field Sample ETL")
    lineage_group_id = create_lineage_group(etl_run_id)

    # 2. Extract all four worksheets in parallel (no dependencies between tasks)
    logger.info("Extracting data from four worksheets of SampleMetadata-BioCirV...")
    sample_ids_df = extract_sample_ids()
    sample_desc_df = extract_sample_desc()
    qty_field_storage_df = extract_qty_field_storage()
    producers_df = extract_producers()
    provider_df = extract_provider()

    # Combine all data sources
    data_sources = {
        "sample_ids": sample_ids_df,
        "sample_desc": sample_desc_df,
        "qty_field_storage": qty_field_storage_df,
        "producers": producers_df,
        "provider_info": provider_df
    }

    # 3. Transform & Load LocationAddress (both collection-site and lab/facility)
    logger.info("Transforming LocationAddress data (multi-source extraction)...")
    location_df = transform_location_address(
        data_sources=data_sources,
        etl_run_id=etl_run_id,
        lineage_group_id=lineage_group_id
    )

    if location_df is not None and not location_df.empty:
        logger.info(f"Loading {len(location_df)} LocationAddress records into database...")
        load_location_address(location_df)
    else:
        logger.warning("No LocationAddress data to load.")

    # 4. Transform FieldSample (multi-way left-join on sample_name)
    logger.info("Transforming FieldSample data (multi-way left-join with unit extraction)...")
    transformed_df = transform_field_sample(
        data_sources=data_sources,
        etl_run_id=etl_run_id,
        lineage_group_id=lineage_group_id
    )

    # 5. Load FieldSample
    if transformed_df is not None and not transformed_df.empty:
        logger.info(f"Loading {len(transformed_df)} FieldSample records into database...")
        load_field_sample(transformed_df)
    else:
        logger.warning("No FieldSample data to load.")

    # 6. Refresh Materialized Views
    logger.info("Refreshing materialized views...")
    try:
        refresh_all_views(engine)
        logger.info("Successfully refreshed materialized views.")
    except Exception as e:
        logger.error(f"Failed to refresh materialized views: {e}")
        raise

    logger.info("Field Sample ETL flow completed successfully.")

if __name__ == "__main__":
    field_sample_etl_flow()
