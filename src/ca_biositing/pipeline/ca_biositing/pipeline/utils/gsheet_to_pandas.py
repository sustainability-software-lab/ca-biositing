import re
from typing import Optional, Tuple

import gspread
import pandas as pd
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound, APIError


def parse_gsheet_url(url: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Parses a Google Sheet URL to extract the spreadsheet key and worksheet ID (gid).

    Args:
        url: The full Google Sheet URL.

    Returns:
        A tuple containing (spreadsheet_key, worksheet_id).
    """
    # Spreadsheet key is usually between /d/ and /edit
    key_match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    # gid is usually in the query parameters or fragment
    gid_match = re.search(r"gid=([0-9]+)", url)

    spreadsheet_key = key_match.group(1) if key_match else None
    worksheet_id = int(gid_match.group(1)) if gid_match else None

    return spreadsheet_key, worksheet_id


def gsheet_to_df(
    gsheet_name: str,
    worksheet_name: Optional[str] = None,
    credentials_path: str = "credentials.json",
    worksheet_id: Optional[int] = None,
) -> Optional[pd.DataFrame]:
    """
    Extracts data from a specific tab in a Google Sheet into a pandas DataFrame.

    Args:
        gsheet_name: The name of the Google Sheet (or its key).
        worksheet_name: The name of the worksheet/tab.
        credentials_path: The path to the Google Cloud service account credentials JSON file.
        worksheet_id: Optional numeric ID of the worksheet (gid). If provided, takes precedence over worksheet_name.

    Returns:
        A pandas DataFrame containing the data from the specified worksheet, or None on error.
    """
    print(f"DEBUG: gsheet_to_df called for {gsheet_name} / {worksheet_id or worksheet_name}")
    try:
        print(f"DEBUG: Authenticating with {credentials_path}")
        gc = gspread.service_account(filename=credentials_path)

        try:
            print(f"DEBUG: Opening spreadsheet {gsheet_name}")
            spreadsheet = gc.open(gsheet_name)
        except SpreadsheetNotFound:
            # Fallback: allow passing a Google Sheet key directly.
            if re.fullmatch(r"[A-Za-z0-9_-]{20,}", gsheet_name):
                try:
                    print(
                        f"DEBUG: Spreadsheet not found by title; trying open_by_key for {gsheet_name}"
                    )
                    spreadsheet = gc.open_by_key(gsheet_name)
                except SpreadsheetNotFound:
                    print(f"Error: Spreadsheet '{gsheet_name}' not found by title or key.")
                    return None
            else:
                print(f"Error: Spreadsheet '{gsheet_name}' not found.")
                return None

        try:
            if worksheet_id is not None:
                print(f"DEBUG: Opening worksheet by ID: {worksheet_id}")
                # gspread 3.x+ has get_worksheet_by_id. gid 0 is valid.
                worksheet = spreadsheet.get_worksheet_by_id(worksheet_id)
                if worksheet is None:
                    print(f"Error: Worksheet ID {worksheet_id} not found.")
                    return None
            elif worksheet_name is not None:
                print(f"DEBUG: Opening worksheet by name: {worksheet_name}")
                worksheet = spreadsheet.worksheet(worksheet_name)
            else:
                print("Error: Either worksheet_name or worksheet_id must be provided.")
                return None
        except WorksheetNotFound:
            print(
                f"Error: Worksheet '{worksheet_name or worksheet_id}' not found in the spreadsheet."
            )
            return None

        # Get values directly to ensure we get calculated values, not formulas.
        print(f"DEBUG: Fetching all values from worksheet")
        all_values = worksheet.get_all_values(value_render_option="FORMATTED_VALUE")
        print(f"DEBUG: Successfully fetched {len(all_values)} rows")
        if not all_values:
            return pd.DataFrame()  # Return empty DataFrame if sheet is empty

        # Use the first row as header and the rest as data
        df = pd.DataFrame(all_values[1:], columns=all_values[0])

        # De-duplicate columns, keeping the first occurrence
        df = df.loc[:, ~df.columns.duplicated()]

        return df

    except APIError as e:
        print(f"Google API Error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


if __name__ == "__main__":
    # Test URL parsing
    test_url = "https://docs.google.com/spreadsheets/d/1IVDOlIcSTlxqqz-agkmrSZRg4umJqL26ZlsalE2hntg/edit?gid=1852803182#gid=1852803182"
    key, gid = parse_gsheet_url(test_url)
    print(f"Parsed Key: {key}")
    print(f"Parsed GID: {gid}")
