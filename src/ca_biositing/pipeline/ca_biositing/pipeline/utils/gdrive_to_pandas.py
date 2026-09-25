import io
import os
import tempfile
import pyproj
# CRITICAL: Set PROJ_LIB before importing any geospatial libraries to avoid macOS version conflicts
os.environ['PROJ_LIB'] = pyproj.datadir.get_data_dir()

import pandas as pd
from pydrive2.auth import GoogleAuth, AuthenticationError
from pydrive2.drive import GoogleDrive
from pydrive2.files import ApiRequestError
import zipfile
import geopandas as gpd

def gdrive_to_df(
    file_name: str,
    mime_type: str,
    credentials_path: str,
    dataset_folder: str,
    file_id: str | None = None
) -> pd.DataFrame | gpd.GeoDataFrame:
    """
    Extracts data from a CSV, ZIP, or GEOJSON file into a pandas DataFrame.

    Uses GetContentString() to download file content as a string, then converts
    to the appropriate in-memory type based on mime_type:
      - text/csv          → parsed directly with pd.read_csv via io.StringIO
      - application/zip   → re-encoded to bytes (latin-1 round-trip preserves
                            binary), extracted via zipfile in a temp directory
      - application/geo+json → parsed directly with gpd.read_file via io.StringIO

    Args:
        file_name: The name of the requested file (used as local filename).
        mime_type: The MIME type - according to https://mime-type.com/
        credentials_path: The path to the Google Cloud service account credentials JSON file.
        dataset_folder: the folder where the extracted file is stored.
        file_id: Optional Google Drive File ID. If provided, used instead of searching by name.

    Returns:
        A pandas DataFrame or GeoDataFrame, or None on error.
    """
    try:
        settings = {
                "client_config_backend": "service",
                "service_config": {
                    "client_json_file_path": credentials_path,
                }
            }
        # Create instance of GoogleAuth
        gauth = GoogleAuth(settings=settings)
        gauth.ServiceAuth()
        drive = GoogleDrive(gauth)

        try:
            if file_id:
                file_entry = drive.CreateFile({'id': file_id})
                # Fetch metadata to ensure it exists and get title if file_name is not ideal
                file_entry.FetchMetadata()
            else:
                file_entries = drive.ListFile({"q": f"title = '{file_name}' and mimeType= '{mime_type}'"}).GetList()
                if len(file_entries) == 0:
                    raise FileNotFoundError(f"Error: File '{file_name}' not found. \n Please make sure the name and mimeType is correct and that you have shared it with the service account email.")
                file_entry = file_entries[0]

            # ZIP is a binary format; use latin-1 so every byte round-trips
            # perfectly through encode/decode without corruption.
            # CSV and GeoJSON are text; utf-8 is the correct encoding.
            encoding = "latin-1" if mime_type == "application/zip" else "utf-8"
            content_str = file_entry.GetContentString(mimetype=mime_type, encoding=encoding)

        except ApiRequestError as e:
            print(f"An unexpected error occurred: {e}")
            return None

        # --- Convert string content to the appropriate DataFrame type ---

        if mime_type == "text/csv":
            # Parse CSV directly from the downloaded string — no disk I/O needed.
            df = pd.read_csv(io.StringIO(content_str))

        elif mime_type == "application/zip":
            # ZIP is binary: re-encode the latin-1 string back to the original
            # bytes, write to a temp file (outside OneDrive to avoid lock
            # issues), then extract the inner CSV.
            # THIS CODE ASSUMES THE ZIP CONTAINS ONE CSV WITH THE SAME STEM NAME.
            zip_bytes = content_str.encode("latin-1")
            csv_name = file_name[:-4] + ".csv"
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_zip = os.path.join(tmp_dir, file_name)
                with open(tmp_zip, "wb") as fh:
                    fh.write(zip_bytes)
                with zipfile.ZipFile(tmp_zip, "r") as zip_ref:
                    zip_ref.extractall(tmp_dir)
                df = pd.read_csv(os.path.join(tmp_dir, csv_name))

        elif mime_type == "application/geo+json":
            # Parse GeoJSON directly from the downloaded string — no disk I/O needed.
            df = gpd.read_file(io.StringIO(content_str))

        else:
            raise Exception("Can't handle this MIME type. Sorry.")

        # De-duplicate columns, keeping the first occurrence
        df = df.loc[:, ~df.columns.duplicated()]

        return df

    except AuthenticationError as e:
        print(f"Google Authentication Error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


if __name__ == '__main__':
    # This part is for direct execution of this file, which is not the primary use case.
    # The main test logic is in test_gsheet_to_pandas.py
    pass
