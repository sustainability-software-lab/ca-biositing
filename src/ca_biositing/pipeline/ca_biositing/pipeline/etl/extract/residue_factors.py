"""
ETL Extract: Residue Factors

Extracts residue factor data from Google Sheets.
Returns raw DataFrame with all columns from the worksheet.
Uses sheet ID directly for reliable access.
"""

from typing import Optional
import os
import pandas as pd
from prefect import task, get_run_logger

# Configuration
GSHEET_ID = "13rwxml9JEC2BJOrZ7m5tRDj2zf-6tNRHEY0KvIauNOA"
WORKSHEET_NAME = "Data Views"

@task(name="extract_residue_factors", retries=3, retry_delay_seconds=10)
def extract_residue_factors(project_root: Optional[str] = None) -> pd.DataFrame:
    """
    Extracts residue factor data from Google Sheets by sheet ID.

    Args:
        project_root: Optional root directory of the project.

    Returns:
        A pandas DataFrame containing the raw data.
    """
    import gspread
    from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound, APIError

    logger = get_run_logger()

    credentials_path = os.getenv("CREDENTIALS_PATH", "credentials.json")
    if project_root:
        credentials_path = os.path.join(project_root, credentials_path)

    logger.info(f"Extracting residue factors from sheet ID '{GSHEET_ID}' (worksheet '{WORKSHEET_NAME}')...")

    try:
        gc = gspread.service_account(filename=credentials_path)

        try:
            logger.info(f"Opening spreadsheet by ID: {GSHEET_ID}")
            spreadsheet = gc.open_by_key(GSHEET_ID)
        except (SpreadsheetNotFound, Exception) as e:
            msg = f"Failed to open spreadsheet with ID {GSHEET_ID}: {e}"
            logger.error(msg)
            raise RuntimeError(msg) from e

        try:
            logger.info(f"Opening worksheet '{WORKSHEET_NAME}'")
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        except WorksheetNotFound as e:
            msg = f"Worksheet '{WORKSHEET_NAME}' not found in spreadsheet"
            logger.error(msg)
            raise RuntimeError(msg) from e

        logger.info("Fetching all values from worksheet...")
        all_values = worksheet.get_all_values(value_render_option='FORMATTED_VALUE')

        if not all_values:
            logger.warning("Worksheet is empty")
            return pd.DataFrame()

        # Use first row as header, rest as data
        df = pd.DataFrame(all_values[1:], columns=all_values[0])

        # De-duplicate columns, keeping first occurrence
        df = df.loc[:, ~df.columns.duplicated()]

        logger.info(f"Successfully extracted {len(df)} rows with columns: {list(df.columns)}")
        return df

    except APIError as e:
        msg = f"Google API Error: {e}"
        logger.error(msg)
        raise RuntimeError(msg) from e
    except Exception as e:
        msg = f"Failed to extract residue factors: {e}"
        logger.error(msg)
        raise RuntimeError(msg) from e
