import re

import gspread
import pandas as pd
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound, APIError


def _dedupe_columns(columns: list) -> list:
    """Rename duplicate column names by appending _2, _3, … suffixes.

    Unlike pandas' ``df.columns.duplicated()`` which simply drops duplicates,
    this preserves every column while making names unique.  This is critical
    for sheets like the food-processing facilities sheet where multiple columns
    share the same header (e.g. five ``Quantity (tons/year)`` columns).
    """
    seen: dict = {}
    result = []
    for col in columns:
        if col not in seen:
            seen[col] = 1
            result.append(col)
        else:
            seen[col] += 1
            result.append(f"{col}_{seen[col]}")
    return result

def gsheet_to_df(gsheet_name: str, worksheet_name: str, credentials_path: str) -> pd.DataFrame:
    """
    Extracts data from a specific tab in a Google Sheet into a pandas DataFrame.

    Args:
        gsheet_name: The name of the Google Sheet.
        worksheet_name: The name of the worksheet/tab.
        credentials_path: The path to the Google Cloud service account credentials JSON file.

    Returns:
        A pandas DataFrame containing the data from the specified worksheet, or None on error.
    """
    print(f"DEBUG: gsheet_to_df called for {gsheet_name} / {worksheet_name}")
    try:
        print(f"DEBUG: Authenticating with {credentials_path}")
        gc = gspread.service_account(filename=credentials_path)

        try:
            print(f"DEBUG: Opening spreadsheet {gsheet_name}")
            spreadsheet = gc.open(gsheet_name)
        except SpreadsheetNotFound:
            # Fallback: allow passing a Google Sheet key directly.
            # Keys are typically URL-safe tokens (often 44 chars) containing letters, digits, _ and -.
            if re.fullmatch(r"[A-Za-z0-9_-]{20,}", gsheet_name):
                try:
                    print(f"DEBUG: Spreadsheet not found by title; trying open_by_key for {gsheet_name}")
                    spreadsheet = gc.open_by_key(gsheet_name)
                except SpreadsheetNotFound:
                    print(f"Error: Spreadsheet '{gsheet_name}' not found by title or key.")
                    print("Please make sure the spreadsheet name/key is correct and that you have shared it with the service account email.")
                    return None
            else:
                print(f"Error: Spreadsheet '{gsheet_name}' not found.")
                print("Please make sure the spreadsheet name is correct and that you have shared it with the service account email.")
                return None

        try:
            print(f"DEBUG: Opening worksheet {worksheet_name}")
            worksheet = spreadsheet.worksheet(worksheet_name)
        except WorksheetNotFound:
            print(f"Error: Worksheet '{worksheet_name}' not found in the spreadsheet.")
            print("Please make sure the worksheet name is correct.")
            return None

        # Get values directly to ensure we get calculated values, not formulas.
        # 'FORMATTED_VALUE' gets the value as you see it in the sheet.
        print(f"DEBUG: Fetching all values from {worksheet_name}")
        all_values = worksheet.get_all_values(value_render_option='FORMATTED_VALUE')
        print(f"DEBUG: Successfully fetched {len(all_values)} rows")
        if not all_values:
            return pd.DataFrame() # Return empty DataFrame if sheet is empty

        # Use the first row as header and the rest as data.
        # Rename duplicate headers with numeric suffixes (_2, _3, …) so that
        # every column is preserved.  Dropping duplicates (the old behaviour)
        # silently discarded data — e.g. the five "Quantity (tons/year)" columns
        # in the food-processing facilities sheet were reduced to one.
        deduped_headers = _dedupe_columns(all_values[0])
        df = pd.DataFrame(all_values[1:], columns=deduped_headers)

        return df

    except APIError as e:
        print(f"Google API Error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


if __name__ == '__main__':
    # This part is for direct execution of this file, which is not the primary use case.
    # The main test logic is in test_gsheet_to_pandas.py
    pass
