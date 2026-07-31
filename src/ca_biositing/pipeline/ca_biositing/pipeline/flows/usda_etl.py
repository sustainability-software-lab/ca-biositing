# File: src/ca_biositing/pipeline/flows/usda_etl.py
from prefect import flow, get_run_logger, task
from ca_biositing.pipeline.etl.extract.usda_census_survey import extract
from ca_biositing.pipeline.etl.transform.usda.usda_census_survey import transform
from ca_biositing.pipeline.etl.load.usda.usda_census_survey import load
from ca_biositing.pipeline.utils.lineage import create_etl_run_record, create_lineage_group


@task(name="Sync Commodity Mappings")
def sync_commodity_mappings():
    """Unconditionally sync commodity mappings from CSV to database."""
    from ca_biositing.pipeline.utils.seed_commodity_mappings import (
        seed_commodity_mappings_from_csv,
        check_seeding_prerequisites,
    )
    from ca_biositing.pipeline.utils.engine import get_engine

    logger = get_run_logger()
    logger.info("🔄 Syncing commodity mappings from CSV...")

    engine = get_engine()
    status = check_seeding_prerequisites(engine)
    if not status.get("prerequisites_met"):
        logger.warning(
            "⚠️ Prerequisites not met for mapping sync (resource/primary_ag_product tables empty). skipping."
        )
        return False

    success = seed_commodity_mappings_from_csv(engine=engine)
    if success:
        logger.info("✅ Commodity mappings synchronized successfully")
    else:
        logger.error("❌ Failed to synchronize commodity mappings")
    return success


@flow(name="USDA Census Survey ETL", log_prints=True)
def usda_etl_flow():
    """
    Orchestrates ETL for USDA agricultural data.

    Now with:
    - Integrated dataset creation in load task
    - Automatic etl_run_id and lineage_group_id tracking
    - Cleaner orchestration (no separate linking step)
    """
    logger = get_run_logger()

    logger.info("=" * 70)
    logger.info("USDA ETL Flow Started")
    logger.info("=" * 70)

    # Step 0: Create lineage tracking
    logger.info("\n[Step 0] Creating lineage tracking...")
    etl_run_id = create_etl_run_record.fn(pipeline_name="USDA ETL")
    lineage_group_id = create_lineage_group.fn(
        etl_run_id=etl_run_id, note="USDA Census/Survey agricultural data - all CA counties"
    )
    logger.info(f"✓ etl_run_id={etl_run_id}, lineage_group_id={lineage_group_id}")

    # Step 0.5: Sync mappings
    logger.info("\n[Step 0.5] Synchronizing commodity mappings...")
    sync_commodity_mappings.fn()

    # Step 1: Extract
    logger.info("\n[Step 1] Extracting USDA data...")
    raw_data = extract()
    if raw_data is None:
        logger.error("✗ Extract failed")
        return False
    logger.info(f"✓ Extracted {len(raw_data)} records")

    # Step 2: Transform
    logger.info("\n[Step 2] Transforming data...")
    cleaned_data = transform(
        data_sources={"usda": raw_data},
        etl_run_id=etl_run_id,
        lineage_group_id=lineage_group_id
    )
    if cleaned_data is None:
        logger.error("✗ Transform failed")
        return False
    logger.info(f"✓ Transformed {len(cleaned_data)} records")

    # Step 3: Load (now includes dataset creation + linking)
    logger.info("\n[Step 3] Loading data...")
    success = load(
        transformed_df=cleaned_data,
        etl_run_id=etl_run_id,
        lineage_group_id=lineage_group_id
    )
    if not success:
        logger.error("✗ Load failed")
        return False
    logger.info("✓ Load complete")

    logger.info("\n" + "=" * 70)
    logger.info("✓ USDA ETL Flow Completed Successfully")
    logger.info("=" * 70)

    return True


if __name__ == "__main__":
    usda_etl_flow()
