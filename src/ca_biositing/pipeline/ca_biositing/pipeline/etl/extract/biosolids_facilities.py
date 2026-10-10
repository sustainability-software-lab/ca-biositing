from typing import Optional
import pandas as pd
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df
from ca_biositing.pipeline.etl.extract.factory import create_extractor
import os
import gspread

@task
def extract(project_root: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Extracts raw biosolids facilities data from a .csv file on Google Drive.

    This function serves as the 'Extract' step in an ETL pipeline. It connects
    to the data source and returns the data as is, without transformation.

    Args:
        project_root: Optional absolute path to project root for resolving credentials
            and dataset folder paths. Used primarily in notebook contexts.

    Returns:
        A tuple of (raw_df, geocoded_extractor) where:
            - raw_df: pandas DataFrame containing the raw data, or None if extraction fails.
            - geocoded_extractor: Callable that extracts geocoded addresses from Google Sheets.
    """
    logger = get_run_logger()


    FILE_NAME = "Biosolids_Facilities.csv"
    MIME_TYPE = "text/csv"
    CREDENTIALS_PATH = os.getenv("CREDENTIALS_PATH", "credentials.json")
    DATASET_FOLDER = "src/ca_biositing/pipeline/ca_biositing/pipeline/temp_external_datasets/"
    logger.info(f"Extracting raw data from '{FILE_NAME}'...")

    # If project_root is provided (e.g., from a notebook), construct an absolute path.
    # Otherwise, use the default relative path (for the main pipeline).
    credentials_path = CREDENTIALS_PATH
    dataset_folder = DATASET_FOLDER
    if project_root:
        credentials_path = os.path.join(project_root, CREDENTIALS_PATH)
        dataset_folder = os.path.join(project_root, DATASET_FOLDER)

    # The gdrive_to_df function handles authentication, data fetching, and error handling.
    raw_df = gdrive_to_df(FILE_NAME, MIME_TYPE, credentials_path, dataset_folder)

    if raw_df is None:
        logger.error("Failed to extract data. Aborting.")
        return None

    logger.info("Successfully extracted raw data.")

    GSHEET_NAME = "address-to-geocoded"
    WORKSHEET_NAME = "Biosolids Facilities"
    logger.info(f"Creating extractor for Google Sheet '{GSHEET_NAME}' (worksheet '{WORKSHEET_NAME}')...")

    geocoded_extractor = create_extractor(GSHEET_NAME, WORKSHEET_NAME)

    return raw_df, geocoded_extractor
