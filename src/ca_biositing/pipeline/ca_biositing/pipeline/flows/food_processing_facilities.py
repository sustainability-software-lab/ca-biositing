"""
Prefect flow for CARB food processing facilities ETL.
"""

from prefect import flow, get_run_logger

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables being set externally

from ca_biositing.pipeline.etl.extract.food_processing_facilities import (
    extract_all_facilities,
    extract_geocoder_test_set,
)
from ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities import transform
from ca_biositing.pipeline.etl.load.food_processing_facilities import load
from ca_biositing.pipeline.utils.lineage import create_etl_run_record, create_lineage_group


@flow(name="Food Processing Facilities ETL", log_prints=True)
def food_processing_facilities_flow():
    """
    Orchestrates the ETL for CARB food processing facilities data.
    """
    logger = get_run_logger()
    logger.info("=" * 70)
    logger.info("Food Processing Facilities Flow Started")
    logger.info("=" * 70)

    logger.info("\n[Step 0] Creating lineage tracking...")
    etl_run_id = create_etl_run_record.fn(pipeline_name="Food Processing Facilities ETL")
    lineage_group_id = create_lineage_group.fn(
        etl_run_id=etl_run_id,
        note="Infrastructure/Food Processing Facilities Data",
    )
    logger.info(f"✓ etl_run_id={etl_run_id}, lineage_group_id={lineage_group_id}")

    logger.info("\n[Step 1] Extracting food processing facilities data...")
    all_facilities = extract_all_facilities()
    geocoder_test_set = extract_geocoder_test_set()

    if all_facilities is None or all_facilities.empty:
        logger.error("✗ Extract failed for all facilities")
        return False

    logger.info(f"✓ Extracted {len(all_facilities)} all-facilities records")
    if geocoder_test_set is None or geocoder_test_set.empty:
        logger.info("✓ Geocoder test set is empty or missing")

    logger.info("\n[Step 2] Transforming data...")
    cleaned_data = transform(
        data_sources={
            "all_facilities": all_facilities,
            "geocoder_test_set": geocoder_test_set if geocoder_test_set is not None else all_facilities.iloc[0:0],
        },
        etl_run_id=etl_run_id,
        lineage_group_id=lineage_group_id,
    )

    if cleaned_data is None or cleaned_data.empty:
        logger.error("✗ Transform failed")
        return False

    logger.info(f"✓ Transformed {len(cleaned_data)} records")

    logger.info("\n[Step 3] Loading data...")
    load_success = load(cleaned_data)
    if not load_success:
        logger.error("✗ Load failed")
        return False

    logger.info("✓ Load complete")

    logger.info("\n" + "=" * 70)
    logger.info("✓ Food Processing Facilities Flow Completed Successfully")
    logger.info("=" * 70)

    return True


if __name__ == "__main__":
    print("Food Processing Facilities ETL is disabled; re-enable it in resources/prefect/run_prefect_flow.py before running.")
