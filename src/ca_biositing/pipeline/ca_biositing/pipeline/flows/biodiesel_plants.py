# File: src/ca_biositing/pipeline/flows/biodiesel_plants.py
from prefect import flow, get_run_logger
from ca_biositing.pipeline.etl.extract.biodiesel_plants import extract
from ca_biositing.pipeline.etl.transform.infrastructure.biodiesel_plants import transform
from ca_biositing.pipeline.etl.load.biodiesel_plants import load
from ca_biositing.pipeline.utils.lineage import create_etl_run_record, create_lineage_group

@flow(name="Biodiesel Plants ETL", log_prints=True)
def biodiesel_plants_flow():
    """
    Orchestrates the ETL for biodiesel plants data.
    """
    logger = get_run_logger()
    logger.info("=" * 70)
    logger.info("Biodiesel Plants Flow Started")
    logger.info("=" * 70)

    # Step 0: Create lineage tracking
    logger.info("\n[Step 0] Creating lineage tracking...")
    etl_run_id = create_etl_run_record.fn(pipeline_name="Biodiesel Plants ETL")
    lineage_group_id = create_lineage_group.fn(
        etl_run_id=etl_run_id,
        note="Infrastructure/Biodiesel Plant Data",
    )
    logger.info(f"✓ etl_run_id={etl_run_id}, lineage_group_id={lineage_group_id}")

    # Step 1: Extract
    logger.info("\n[Step 1] Extracting Biodiesel Plant data...")
    raw_data = extract()
    if raw_data is None or raw_data.empty:
        logger.error("✗ Extract failed")
        return False
    logger.info(f"✓ Extracted {len(raw_data)} records")

    # Step 2: Transform
    logger.info("\n[Step 2] Transforming data...")
    cleaned_data = transform(
        data_sources={"biodiesel_plants": raw_data},
        etl_run_id=etl_run_id,
        lineage_group_id=lineage_group_id,
    )
    if cleaned_data is None or cleaned_data.empty:
        logger.error("✗ Transform failed")
        return False
    logger.info(f"✓ Transformed {len(cleaned_data)} records")

    # Step 3: Load
    logger.info("\n[Step 3] Loading data...")
    load_success = load(cleaned_data)
    if not load_success:
        logger.error("✗ Load failed")
        return False
    logger.info("✓ Load complete")

    logger.info("\n" + "=" * 70)
    logger.info("✓ Biodiesel Plant Flow Completed Successfully")
    logger.info("=" * 70)

    return True

if __name__ == "__main__":
    biodiesel_plants_flow()
