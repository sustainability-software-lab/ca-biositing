from typing import List

import pandas as pd
from prefect import get_run_logger, task


@task
def build_gasification_archive_records(
    gas_rec_df: pd.DataFrame,
    raw_data_df: pd.DataFrame,
) -> List[dict]:
    """
    Builds the deduplicated list of records ready for the gasification
    archival subflow, matching each transformed GasificationRecord row back
    to its raw GSheet URL.
    """
    logger = get_run_logger()

    archive_data = []
    logger.info(f"Preparing archival for {len(gas_rec_df)} records...")

    for _, row in gas_rec_df.iterrows():
        rid = row["record_id"]
        # Case-insensitive match for record_id to account for default cleaning behavior
        match = raw_data_df[raw_data_df["record_id"].astype(str).str.lower() == str(rid).lower()]

        if not match.empty:
            gsheet_url = None
            # Search across possible URL column names (raw or cleaned)
            # Note: We now preserve casing for raw_data_url in transform
            for col in [
                "raw_data_url",
                "Raw_data_url",
                "Raw_Data_URL",
                "Experiment_setup_url",
                "Experiment_Setup_URL",
            ]:
                if col in match.columns:
                    val = match.iloc[0].get(col)
                    if val and str(val).startswith("http"):
                        gsheet_url = str(val)
                        break

            if gsheet_url:
                archive_data.append(
                    {
                        "record_id": rid,
                        "gsheet_url": gsheet_url,
                        "resource_id": row.get("resource_id"),
                        "experiment_id": row.get("experiment_id"),
                        "resource_name": row.get("resource_name"),
                        "reactor_name": row.get("reactor_name"),
                        "reactor_type_id": row.get("reactor_type_id"),
                    }
                )

    # Deduplicate by gsheet_url to ensure we only trigger archival once per unique spreadsheet
    unique_archive = []
    seen_urls = set()
    for item in archive_data:
        if item["gsheet_url"] not in seen_urls:
            unique_archive.append(item)
            seen_urls.add(item["gsheet_url"])

    return unique_archive
