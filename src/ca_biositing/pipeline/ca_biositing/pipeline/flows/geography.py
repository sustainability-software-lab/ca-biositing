"""
Geography ETL Flow
"""

from prefect import flow, get_run_logger
from ca_biositing.pipeline.etl.extract.geography import extract_ca_counties
from ca_biositing.pipeline.etl.load.places import load_places

@flow(name="geography_etl_flow")
def geography_etl_flow():
    """
    Orchestrates the geography ETL process.
    """
    logger = get_run_logger()
    logger.info("Starting Geography ETL Flow...")

    # 1. Extract
    df = extract_ca_counties()

    # 2. Load
    load_places(df)

    logger.info("Geography ETL Flow completed successfully.")

if __name__ == "__main__":
    geography_etl_flow()
