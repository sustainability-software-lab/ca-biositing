from prefect import flow
from ca_biositing.pipeline.utils.lineage import create_etl_run_record, create_lineage_group

@flow(name="Static Resource Info ETL", log_prints=True)
def static_resource_info_flow():
    """
    Orchestrates the ETL process for Static Resource Information (LandIQ Mapping & Availability).
    """
    # Lazy imports to avoid module-level hangs
    from ca_biositing.pipeline.etl.extract import static_resource_info as extract_mod
    from ca_biositing.pipeline.etl.transform.resource_information import static_resource_info as transform_mod
    from ca_biositing.pipeline.etl.load import static_resource_info as load_mod
    from prefect import get_run_logger, task

    logger = get_run_logger()
    logger.info("Starting Static Resource Info ETL flow...")

    # 0. Lineage Tracking Setup
    etl_run_id = create_etl_run_record.fn(pipeline_name="Static Resource Info ETL")
    lineage_group_id = create_lineage_group.fn(
        etl_run_id=etl_run_id,
        note="Static resource information from Google Sheets"
    )

    # 1. Extract
    logger.info("Extracting static resource info from Google Sheets...")
    raw_df = extract_mod.extract.fn()

    # Update local CSV asset
    if raw_df is not None and not raw_df.empty:
        try:
            csv_path = "resources/assets/resource_info.csv"
            raw_df.to_csv(csv_path, index=False)
            logger.info(f"Updated local asset: {csv_path}")
        except Exception as e:
            logger.warning(f"Failed to update local CSV asset: {e}")

    if raw_df is None or raw_df.empty:
        logger.error("No data extracted. Aborting flow.")
        return

    # 2. Transform
    logger.info("Transforming static resource data...")
    transformed_data = transform_mod.transform_static_resource_info.fn(
        data_sources={"static_resource_info": raw_df},
        etl_run_id=etl_run_id,
        lineage_group_id=lineage_group_id
    )

    # 3. Load
    logger.info("Loading LandIQ Resource Mappings...")
    load_mod.load_landiq_resource_mapping.fn(transformed_data.get("landiq_resource_mapping"))

    logger.info("Loading Resource Availability records...")
    load_mod.load_resource_availability.fn(transformed_data.get("resource_availability"))

    logger.info("Static Resource Info ETL flow completed successfully.")

if __name__ == "__main__":
    static_resource_info_flow()
