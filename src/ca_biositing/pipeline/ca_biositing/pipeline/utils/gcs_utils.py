"""
GCS Utilities for Pipeline.
"""

import io
import os
from typing import Union

import pandas as pd
from google.cloud import storage


def upload_to_gcs(
    bucket_name: str,
    destination_blob_name: str,
    data: Union[pd.DataFrame, bytes, str],
    credentials_path: str = "credentials.json",
) -> str:
    """
    Uploads data to a GCS bucket.

    Args:
        bucket_name: The name of the GCS bucket.
        destination_blob_name: The name of the file in GCS.
        data: The data to upload (DataFrame, bytes, or string).
        credentials_path: Path to the GCP service account JSON.

    Returns:
        The GCS path (gs://bucket/blob)
    """
    # Try to get Prefect logger if running in a flow, otherwise use standard logging
    try:
        from prefect import get_run_logger

        logger = get_run_logger()
    except Exception:
        import logging

        logger = logging.getLogger(__name__)

    logger.info(f"Uploading to gs://{bucket_name}/{destination_blob_name}...")

    # Ensure credentials path is set for the client
    if os.path.exists(credentials_path):
        client = storage.Client.from_service_account_json(credentials_path)
    else:
        # Fallback to default credentials (e.g. Workload Identity in Cloud Run)
        client = storage.Client()

    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    if isinstance(data, pd.DataFrame):
        # Convert DF to CSV in memory
        csv_buffer = io.StringIO()
        data.to_csv(csv_buffer, index=False)
        blob.upload_from_string(csv_buffer.getvalue(), content_type="text/csv")
    elif isinstance(data, bytes):
        blob.upload_from_string(data)
    elif isinstance(data, str):
        blob.upload_from_string(data)
    else:
        raise ValueError("Unsupported data type for upload")

    gcs_path = f"gs://{bucket_name}/{destination_blob_name}"
    logger.info(f"Successfully uploaded to {gcs_path}")
    return gcs_path
