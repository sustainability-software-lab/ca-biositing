from prefect import flow, get_run_logger
from ca_biositing.pipeline.etl.extract.msw_to_energy_anaerobic_digesters import extract
from ca_biositing.pipeline.etl.transform.infrastructure.msw_to_energy_anaerobic_digesters import transform
from ca_biositing.pipeline.etl.load.infrastructure.msw_to_energy_anaerobic_digesters import load
from ca_biositing.pipeline.utils.lineage import create_etl_run_record, create_lineage_group


@flow(name="MSW-to-Energy Anaerobic Digesters ETL", log_prints=True)
def msw_to_energy_anaerobic_digesters_flow():
    """Orchestrates the ETL for MSW-to-energy anaerobic digesters data."""
    logger = get_run_logger()
    logger.info("=" * 70)
    logger.info("MSW-to-Energy Anaerobic Digesters Flow Started")
    logger.info("=" * 70)

    logger.info("\n[Step 0] Creating lineage tracking...")
    etl_run_id = create_etl_run_record.fn(pipeline_name="MSW-to-Energy Anaerobic Digesters ETL")
    lineage_group_id = create_lineage_group.fn(
        etl_run_id=etl_run_id,
        note="Infrastructure/MSW-to-Energy Anaerobic Digesters Data",
    )
    logger.info(f"✓ etl_run_id={etl_run_id}, lineage_group_id={lineage_group_id}")

    logger.info("\n[Step 1] Extracting MSW-to-Energy Anaerobic Digesters data...")
    raw_data = extract()
    if raw_data is None or raw_data.empty:
        logger.error("✗ Extract failed")
        return False
    logger.info(f"✓ Extracted {len(raw_data)} records")

    logger.info("\n[Step 2] Transforming data...")
    cleaned_data = transform(
        data_sources={"msw_to_energy_anaerobic_digesters": raw_data},
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
    logger.info("✓ MSW-to-Energy Anaerobic Digesters Flow Completed Successfully")
    logger.info("=" * 70)
    return True


if __name__ == "__main__":
    msw_to_energy_anaerobic_digesters_flow()
