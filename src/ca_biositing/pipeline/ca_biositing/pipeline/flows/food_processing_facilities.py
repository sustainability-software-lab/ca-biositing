"""
Prefect flow for CARB food processing facilities ETL.

Execution order
---------------
1. [seed]  Load previously geocoded rows from the local seed CSV into the DB.
           This restores lat/long data instantly without re-running the geocoder.
2. [etl]   Extract from Google Sheets → transform (delta check + geocode new rows)
           → upsert into DB.

The seed step is idempotent: running it twice does not duplicate rows because
the UPSERT uses the same conflict key (name, address, city, zip) as the normal
load step.
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
    extract_seed_csv,
)
from ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities import transform
from ca_biositing.pipeline.etl.load.food_processing_facilities import load, load_seed_csv
from ca_biositing.pipeline.utils.lineage import create_etl_run_record, create_lineage_group


@flow(name="Food Processing Facilities ETL", log_prints=True)
def food_processing_facilities_flow():
    """
    Orchestrates the ETL for CARB food processing facilities data.

    Step 0  — Create lineage tracking records.
    Step 0.5— Seed the DB from the local CSV (restores previously geocoded rows).
    Step 1  — Extract from Google Sheets.
    Step 2  — Transform (clean, geocode new rows, delta check).
    Step 3  — Load transformed rows into the DB.
    """
    logger = get_run_logger()
    logger.info("=" * 70)
    logger.info("Food Processing Facilities Flow Started")
    logger.info("=" * 70)

    # ------------------------------------------------------------------
    # Step 0: Lineage tracking
    # ------------------------------------------------------------------
    logger.info("\n[Step 0] Creating lineage tracking...")
    etl_run_id = create_etl_run_record.fn(pipeline_name="Food Processing Facilities ETL")
    lineage_group_id = create_lineage_group.fn(
        etl_run_id=etl_run_id,
        note="Infrastructure/Food Processing Facilities Data",
    )
    logger.info(f"✓ etl_run_id={etl_run_id}, lineage_group_id={lineage_group_id}")

    # ------------------------------------------------------------------
    # Step 0.5: Seed DB from local CSV
    # ------------------------------------------------------------------
    logger.info("\n[Step 0.5] Seeding DB from local CSV...")
    seed_df = extract_seed_csv()
    if seed_df is not None and not seed_df.empty:
        logger.info(f"[seed] Loaded {len(seed_df)} rows from seed CSV")
        try:
            seeded_count = load_seed_csv(seed_df)
            logger.info(f"[seed] Upserted {seeded_count} rows into infrastructure_food_processing_facilities")
        except Exception as exc:
            logger.warning(f"[seed] Seed step failed (non-fatal): {exc} — continuing with sheet ETL")
    else:
        logger.info("[seed] No seed CSV found or CSV is empty — skipping seed step")

    # ------------------------------------------------------------------
    # Step 1: Extract from Google Sheets
    # ------------------------------------------------------------------
    logger.info("\n[Step 1] Extracting food processing facilities data...")
    all_facilities = extract_all_facilities()
    geocoder_test_set = extract_geocoder_test_set()

    if all_facilities is None or all_facilities.empty:
        logger.error("✗ Extract failed for all facilities")
        return False

    logger.info(f"✓ Extracted {len(all_facilities)} all-facilities records")
    if geocoder_test_set is None or geocoder_test_set.empty:
        logger.info("✓ Geocoder test set is empty or missing")

    # ------------------------------------------------------------------
    # Step 2: Transform (clean + geocode)
    # ------------------------------------------------------------------
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

    sheet_row_count = len(cleaned_data)
    logger.info(f"[etl] Sheet returned {sheet_row_count} rows after transform")

    # Count rows missing lat/long — these were queued for geocoding
    missing_latlong = int(
        cleaned_data["latitude"].isna().sum()
        if "latitude" in cleaned_data.columns
        else 0
    )
    logger.info(f"[etl] {missing_latlong} addresses missing lat/long — queued for geocoding")

    # ------------------------------------------------------------------
    # Step 3: Load transformed rows
    # ------------------------------------------------------------------
    logger.info("\n[Step 3] Loading data...")
    load_success = load(cleaned_data)
    if not load_success:
        logger.error("✗ Load failed")
        return False

    logger.info(f"[etl] {sheet_row_count} rows revised/upserted (sheet ETL)")
    logger.info("✓ Load complete")

    logger.info("\n" + "=" * 70)
    logger.info("✓ Food Processing Facilities Flow Completed Successfully")
    logger.info("=" * 70)

    return True


if __name__ == "__main__":
    print("Food Processing Facilities ETL is disabled; re-enable it in resources/prefect/run_prefect_flow.py before running.")
