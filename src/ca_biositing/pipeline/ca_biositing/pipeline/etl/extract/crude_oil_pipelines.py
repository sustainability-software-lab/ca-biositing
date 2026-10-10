from typing import Optional
import pandas as pd
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df
import geopandas as gpd
import os

@task
def extract(project_root: Optional[str] = None) -> Optional[gpd.GeoDataFrame]:
    """
    Extracts raw crude oil pipeline data from a .geojson file on Google Drive.

    This function serves as the 'Extract' step in an ETL pipeline. It connects
    to the data source and returns the data as is, without transformation.

    Args:
        project_root: Optional absolute path to project root for resolving credentials
            and dataset folder paths. Used primarily in notebook contexts.

    Returns:
        A GeoDataFrame containing the raw geospatial data, or None if extraction fails.
    """
    logger = get_run_logger()

    FILE_NAME = "US_Crude_Oil_Pipelines.geojson"
    MIME_TYPE = "application/geo+json"
    CREDENTIALS_PATH = os.getenv("CREDENTIALS_PATH", "credentials.json")
    DATASET_FOLDER = "src/ca_biositing/pipeline/ca_biositing/pipeline/temp_external_datasets/"
    logger.info(f"Extracting raw data from '{FILE_NAME}'...")

    # If project_root is provided (e.g., from a notebook), construct an absolute path
    # Otherwise, use the default relative path (for the main pipeline)
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
    return raw_df
