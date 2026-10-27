from prefect import flow, get_run_logger
from ca_biositing.pipeline.etl.extract.district_energy_systems import extract
from ca_biositing.pipeline.etl.transform.infrastructure.district_energy_systems import transform
from ca_biositing.pipeline.etl.load.infrastructure.district_energy_systems import load
from ca_biositing.pipeline.utils.lineage import create_etl_run_record, create_lineage_group


@flow(name="District Energy Systems ETL", log_prints=True)
def district_energy_systems_flow():
    """Orchestrates the ETL for district energy systems data."""
    logger = get_run_logger()
    logger.info("=" * 70)
    logger.info("District Energy Systems Flow Started")
    logger.info("=" * 70)

    logger.info("\n[Step 0] Creating lineage tracking...")
    etl_run_id = create_etl_run_record.fn(pipeline_name="District Energy Systems ETL")
    lineage_group_id = create_lineage_group.fn(
        etl_run_id=etl_run_id,
        note="Infrastructure/District Energy Systems Data",
    )
    logger.info(f"✓ etl_run_id={etl_run_id}, lineage_group_id={lineage_group_id}")

    logger.info("\n[Step 1] Extracting District Energy Systems data...")
    raw_data, geocoded_extractor = extract()
    if raw_data is None or raw_data.empty:
        logger.error("✗ Extracting raw data failed")
        return False
    geocoded_data = geocoded_extractor()
    if geocoded_data is None or geocoded_data.empty:
        logger.error("✗ Extracting geocoded data failed")
        return False
    logger.info(f"✓ Extracted {len(raw_data)} records")

    logger.info("\n[Step 2] Transforming data...")
    cleaned_data = transform(
        data_sources={"district_energy_systems": raw_data},
        etl_run_id=etl_run_id,
        lineage_group_id=lineage_group_id,
        geocoded_df=geocoded_data
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
    logger.info("✓ District Energy Systems Flow Completed Successfully")
    logger.info("=" * 70)
    return True


if __name__ == "__main__":
    district_energy_systems_flow()
