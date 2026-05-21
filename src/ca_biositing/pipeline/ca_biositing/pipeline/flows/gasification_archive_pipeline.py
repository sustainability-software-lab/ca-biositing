from prefect import flow, task, get_run_logger
import pandas as pd
import io
import hashlib
from typing import Optional, List
from ca_biositing.pipeline.utils.gsheet_to_pandas import parse_gsheet_url
from ca_biositing.pipeline.utils.gcs_utils import upload_to_gcs
from ca_biositing.pipeline.utils.engine import get_engine
from sqlalchemy.orm import Session
from sqlalchemy import select
import gspread

@task
def process_gsheet_to_csv(url: str, record_id: str, credentials_path: str = "credentials.json") -> pd.DataFrame:
    logger = get_run_logger()
    logger.info(f"Processing GSheet URL: {url} for record {record_id}")

    key, gid = parse_gsheet_url(url)
    if not key:
        raise ValueError(f"Could not parse spreadsheet key from URL: {url}")

    # Authenticate and fetch worksheet
    gc = gspread.service_account(filename=credentials_path)
    sh = gc.open_by_key(key)
    if gid is None:
        raise ValueError(f"No worksheet ID (gid) found in URL: {url}")

    ws = sh.get_worksheet_by_id(gid)
    all_values = ws.get_all_values()

    if not all_values or len(all_values) < 4:
        raise ValueError(f"Worksheet {gid} in {key} has insufficient data (less than 4 rows)")

    # Requirement: Row 4 (index 3) is the header, data starts at Row 5 (index 4)
    header = all_values[3]
    data = all_values[4:]

    if not header:
        raise ValueError(f"Header row (row 4) is empty in worksheet {gid}")

    processed_df = pd.DataFrame(data, columns=header)
    # Remove duplicate columns
    processed_df = processed_df.loc[:, ~processed_df.columns.duplicated()]

    return processed_df

@task
def archive_to_gcs(df: pd.DataFrame, filename: str, bucket_name: str) -> dict:
    logger = get_run_logger()
    logger.info(f"Archiving to GCS: {bucket_name}/{filename}")

    # Convert to CSV bytes for metadata calculation
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_content = csv_buffer.getvalue().encode('utf-8')

    file_size = len(csv_content)
    md5_hash = hashlib.md5(csv_content).hexdigest()

    # upload_to_gcs handles the actual upload
    gcs_path = upload_to_gcs(
        bucket_name=bucket_name,
        destination_blob_name=filename,
        data=df
    )

    return {
        "bucket_path": gcs_path,
        "file_size": file_size,
        "checksum_md5": md5_hash,
        "file_format": "csv"
    }

@task
def record_metadata_db(
    metadata: dict,
    record_id: str,
    gsheet_url: str,
    resource_id: Optional[int],
    experiment_id: Optional[int],
    resource_name: Optional[str],
    reactor_type_id: Optional[int],
    etl_run_id: int,
    lineage_group_id: int
):
    from ca_biositing.datamodels.models import GasificationTimeseries

    engine = get_engine()
    with Session(engine) as session:
        # Check if record already exists for this resource/experiment combination
        existing = session.execute(
            select(GasificationTimeseries).where(
                GasificationTimeseries.resource_id == resource_id,
                GasificationTimeseries.experiment_id == experiment_id
            )
        ).scalar_one_or_none()

        if existing:
            # Update existing record
            existing.bucket_path = metadata["bucket_path"]
            existing.file_size = metadata["file_size"]
            existing.checksum_md5 = metadata["checksum_md5"]
            existing.etl_run_id = etl_run_id
            existing.lineage_group_id = lineage_group_id
            existing.resource_name = resource_name
            existing.reactor_type_id = reactor_type_id
            existing.gsheet_url = gsheet_url
        else:
            new_record = GasificationTimeseries(
                resource_id=resource_id,
                experiment_id=experiment_id,
                resource_name=resource_name,
                reactor_type_id=reactor_type_id,
                gsheet_url=gsheet_url,
                bucket_path=metadata["bucket_path"],
                file_size=metadata["file_size"],
                file_format=metadata["file_format"],
                checksum_md5=metadata["checksum_md5"],
                etl_run_id=etl_run_id,
                lineage_group_id=lineage_group_id
            )
            session.add(new_record)

        session.commit()

@flow(name="Gasification Timeseries Archiver", log_prints=True)
def gasification_archive_subflow(
    records_to_archive: List[dict],
    etl_run_id: int,
    lineage_group_id: int,
    bucket_name: str = "biocirv-staging-gasification-data"
):
    """
    Sub-flow to archive gasification timeseries data.
    records_to_archive is a list of dicts with keys:
    - record_id
    - gsheet_url
    - resource_id
    - experiment_id
    - resource_name
    - reactor_type_id
    """
    logger = get_run_logger()
    logger.info(f"Starting archival for {len(records_to_archive)} records")

    for record in records_to_archive:
        record_id = record["record_id"]
        gsheet_url = record["gsheet_url"]

        if not gsheet_url:
            logger.warning(f"No GSheet URL for record {record_id}, skipping archival.")
            continue

        try:
            # Use unique filename based on resource_name and experiment_id
            # Requirement: {resource_name}_EXP_{experiment_id}.csv
            res_name = record.get("resource_name")
            exp_id = record.get("experiment_id")
            if res_name and exp_id:
                # Clean resource name: lowercase, replace spaces/special chars with underscores
                import re
                clean_name = re.sub(r'[^a-zA-Z0-9]', '_', str(res_name)).strip('_').lower()
                # Format experiment ID
                exp_str = str(int(float(exp_id))) if exp_id is not None else "UNK"
                filename = f"{clean_name}_EXP_{exp_str}.csv"
            else:
                filename = f"{record_id}.csv"

            df = process_gsheet_to_csv(gsheet_url, record_id)
            metadata = archive_to_gcs(df, filename, bucket_name)
            record_metadata_db(
                metadata=metadata,
                record_id=record_id,
                gsheet_url=gsheet_url,
                resource_id=record.get("resource_id"),
                experiment_id=exp_id,
                resource_name=res_name,
                reactor_type_id=record.get("reactor_type_id"),
                etl_run_id=etl_run_id,
                lineage_group_id=lineage_group_id
            )
            logger.info(f"Successfully archived {record_id} as {filename}")
        except Exception as e:
            logger.error(f"Failed to archive record {record_id}: {e}")

if __name__ == "__main__":
    # For testing, we still need etl_run_id/lineage_group_id
    from ca_biositing.pipeline.utils.lineage import create_etl_run_record, create_lineage_group
    run_id = create_etl_run_record("Test Archival")
    lg_id = create_lineage_group(run_id, "Test")

    test_records = [{
        "record_id": "GAS_EXP_TEST_001",
        "gsheet_url": "https://docs.google.com/spreadsheets/d/1IVDOlIcSTlxqqz-agkmrSZRg4umJqL26ZlsalE2hntg/edit?gid=1852803182#gid=1852803182",
        "resource_name": "Test Feedstock"
    }]
    gasification_archive_subflow(test_records, int(run_id), int(lg_id))
