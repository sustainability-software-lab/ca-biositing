"""
ETL Flow: Residue Factors

Orchestrates the complete ETL pipeline for Residue Factors data:
- Extract: Reads residue factor data from Google Sheets ("Residue Factors" → "Data_Views")
- Transform: Normalizes data, resolves foreign keys, calculates derived fields
- Load: UPSERTs data into residue_factor table using composite key (resource_id, factor_type)

The flow implements lineage tracking for audit trails and includes comprehensive
error handling and logging for each stage.
"""

import sys
from prefect import flow, get_run_logger
from ca_biositing.pipeline.utils.lineage import create_etl_run_record, create_lineage_group


@flow(name="Residue Factors ETL", log_prints=True, persist_result=False)
def residue_factors_etl_flow():
    """
    Orchestrates the ETL process for Residue Factors data.

    Pipeline stages:
    1. **Extract**: Reads residue factor data from Google Sheets
    2. **Transform**: Normalizes columns, resolves foreign keys, calculates fields
    3. **Load**: UPSERTs data into database with composite key handling

    Expected Google Sheet:
    - Name: "Residue Factors"
    - Worksheet: "Data_Views"
    - Columns: resource, factor_type, primary_product, factor_min, factor_max,
               factor_mid, prune_trim_yield, prune_trim_yield_unit, source, notes

    The flow uses lazy imports to avoid module-level hangs in Docker environments.
    All models and utilities are imported within task contexts.

    Returns:
        None. Status logged via Prefect logging system.

    Raises:
        Prefect task failures are captured and logged; flow continues or aborts
        based on extraction success.
    """
    # Lazy imports to avoid module-level hangs in Docker
    from ca_biositing.pipeline.etl.extract import residue_factors as extract_mod
    from ca_biositing.pipeline.etl.transform.resource_information import residue_factor as transform_mod
    from ca_biositing.pipeline.etl.load.resource_information import residue_factor as load_mod

    logger = get_run_logger()

    # Force stdout/stderr to flush immediately for Docker logging
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    logger.info("=" * 80)
    logger.info("Starting Residue Factors ETL Flow")
    logger.info("=" * 80)

    # ========================================
    # 0. Lineage Tracking Setup
    # ========================================
    try:
        logger.info("Creating ETL run record for lineage tracking...")
        etl_run_id = create_etl_run_record.fn(pipeline_name="Residue Factors ETL")
        logger.info(f"ETL Run ID: {etl_run_id}")

        lineage_group_id = create_lineage_group.fn(
            etl_run_id=etl_run_id,
            note="Residue factor data from Google Sheets"
        )
        logger.info(f"Lineage Group ID: {lineage_group_id}")
    except Exception as e:
        logger.error(f"Failed to create lineage tracking: {e}")
        raise

    # ========================================
    # 1. Extract
    # ========================================
    logger.info("-" * 80)
    logger.info("STAGE 1: EXTRACT - Reading from Google Sheets")
    logger.info("-" * 80)

    try:
        logger.info('Extracting from Google Sheet "Residue Factors" (worksheet "Data_Views")...')
        raw_df = extract_mod.extract_residue_factors()

        if raw_df is None:
            logger.error("Extraction returned None")
            return

        if raw_df.empty:
            logger.warning("Extraction returned empty DataFrame")
            logger.info("Flow completed with no data to process.")
            return

        logger.info(f"✓ Extraction successful: {len(raw_df)} rows extracted")
        logger.info(f"  Columns: {list(raw_df.columns)}")
        logger.info(f"  Data types:\n{raw_df.dtypes}")

    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        raise

    # ========================================
    # 2. Transform
    # ========================================
    logger.info("-" * 80)
    logger.info("STAGE 2: TRANSFORM - Normalizing and preparing data")
    logger.info("-" * 80)

    try:
        logger.info(f"Starting transformation of {len(raw_df)} rows...")
        transformed_df = transform_mod.transform_residue_factor(
            df=raw_df,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_id
        )

        if transformed_df is None:
            logger.error("Transformation returned None")
            logger.info("Flow completed with no transformed data.")
            return

        if transformed_df.empty:
            logger.warning("Transformation returned empty DataFrame")
            logger.info("Flow completed with no data to load.")
            return

        logger.info(f"✓ Transformation successful: {len(transformed_df)} rows ready for loading")
        logger.info(f"  Output columns: {list(transformed_df.columns)}")
        logger.info(f"  Null counts:\n{transformed_df.isnull().sum()}")

    except Exception as e:
        logger.error(f"Transformation failed: {e}", exc_info=True)
        raise

    # ========================================
    # 3. Load
    # ========================================
    logger.info("-" * 80)
    logger.info("STAGE 3: LOAD - Upserting into database")
    logger.info("-" * 80)

    try:
        logger.info(f"Loading {len(transformed_df)} residue factor records...")
        load_result = load_mod.load_residue_factors(df=transformed_df)

        inserted = load_result.get("inserted", 0)
        updated = load_result.get("updated", 0)
        failed = load_result.get("failed", 0)

        logger.info(f"✓ Load completed:")
        logger.info(f"  - Inserted: {inserted}")
        logger.info(f"  - Updated: {updated}")
        logger.info(f"  - Failed: {failed}")

        if failed > 0:
            logger.warning(f"⚠ {failed} records failed to load")

    except Exception as e:
        logger.error(f"Load failed: {e}", exc_info=True)
        raise

    # ========================================
    # Summary
    # ========================================
    logger.info("=" * 80)
    logger.info("Residue Factors ETL Flow Completed Successfully")
    logger.info("=" * 80)
    logger.info(f"Total records processed: {len(raw_df)}")
    logger.info(f"Records loaded: {inserted + updated}")
    logger.info(f"ETL Run ID: {etl_run_id}")
    logger.info(f"Lineage Group ID: {lineage_group_id}")


if __name__ == "__main__":
    residue_factors_etl_flow()
