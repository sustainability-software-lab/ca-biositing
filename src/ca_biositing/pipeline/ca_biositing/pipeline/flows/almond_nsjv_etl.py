from prefect import flow, get_run_logger


@flow(name="Almond NSJV ETL", log_prints=True, persist_result=False)
def almond_nsjv_etl_flow():
    """Orchestrate the almond NSJV county agricultural report ETL."""

    from ca_biositing.pipeline.etl.extract import almond_nsjv as almond_extract
    from ca_biositing.pipeline.etl.load.analysis.almond_nsjv import load_county_ag_reports
    from ca_biositing.pipeline.etl.transform.analysis.almond_nsjv import transform_almond_nsjv_payloads
    from ca_biositing.pipeline.utils.lineage import create_etl_run_record, create_lineage_group

    logger = get_run_logger()
    logger.info("Starting Almond NSJV ETL flow...")

    etl_run_id = create_etl_run_record.fn(pipeline_name="Almond NSJV ETL")
    lineage_group_id = create_lineage_group.fn(
        etl_run_id=etl_run_id,
        note="Almond county agricultural report data for the North San Joaquin Valley",
    )

    data_sources = {
        "parameters": almond_extract.parameters(),
        "price_production_county_ag_reports": almond_extract.price_production_county_ag_reports(),
    }

    payloads = transform_almond_nsjv_payloads(
        data_sources=data_sources,
        etl_run_id=etl_run_id,
        lineage_group_id=lineage_group_id,
    )

    counts = load_county_ag_reports(payloads)
    logger.info("Almond NSJV ETL completed with counts: %s", counts)
    return counts


if __name__ == "__main__":
    almond_nsjv_etl_flow()
