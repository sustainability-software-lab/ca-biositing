"""
Tests for gdrive_to_pandas.gdrive_to_df using infrastructure datasets.

Infrastructure datasets exercised by these tests (mirrors the real ETL extract
modules under ca_biositing/pipeline/etl/extract/):

  text/csv
    CAFO_Locations_and_Manure_Production.csv  → cafo_manure_locations
    Livestock_Anaerobic_Digesters.csv         → livestock_anaerobic_digesters
    Wastewater_Treatment_Plants.csv           → wastewater_treatment_plants
    Biodiesel_Plants.csv                      → biodiesel_plants
    Ethanol_Biorefineries.csv                 → ethanol_biorefineries
    saf_and_renewable_diesel_plants.csv       → saf_and_renewable_diesel_plants
    Biosolids_Facilities.csv                  → biosolids_facilities
    Landfills.csv                             → landfills

  application/zip
    CA_comb_points.zip   → combustion_plants  (inner CSV same stem)
    CA_proc_points.zip   → food_processing_facilities / ca_proc_points
    CA_des_points.zip    → district_energy_systems
    CA_wte_points.zip    → msw_to_energy_anaerobic_digesters

  application/geo+json
    US_Petroleum_Pipelines.geojson → petroleum_pipelines

Download strategy
-----------------
GetContentString() downloads file content as a decoded string.
Content is then converted to the appropriate type based on mime_type:
  - text/csv        → pd.read_csv(io.StringIO(...))   — no disk I/O
  - application/zip → latin-1 round-trip back to bytes → temp dir extraction
  - application/geo+json → gpd.read_file(io.StringIO(...)) — no disk I/O
"""

import io
import json
import zipfile

import geopandas as gpd
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gauth_mock():
    """Mock GoogleAuth that succeeds without real credentials."""
    m = MagicMock()
    m.ServiceAuth.return_value = None
    return m


def _make_drive_mock(file_entry_mock):
    """Mock GoogleDrive whose CreateFile/ListFile both return file_entry_mock."""
    drive = MagicMock()
    drive.CreateFile.return_value = file_entry_mock
    drive.ListFile.return_value.GetList.return_value = [file_entry_mock]
    return drive


def _make_file_entry(content_bytes: bytes, encoding: str = "utf-8") -> MagicMock:
    """
    Mock GoogleDriveFile whose GetContentString returns the content decoded with
    the given encoding, matching the real pydrive2 API.

    GetContentString(mimetype=..., encoding=...) returns a str.
    For ZIP files pass encoding='latin-1' so binary bytes round-trip intact.
    """
    entry = MagicMock()
    entry.FetchMetadata.return_value = None
    _enc = encoding  # capture for closure

    def _return_string(mimetype=None, encoding=_enc, **kwargs):
        return content_bytes.decode(_enc)

    entry.GetContentString.side_effect = _return_string
    return entry


def _make_zip_bytes(csv_stem: str, csv_content: bytes) -> bytes:
    """Build an in-memory ZIP containing a single CSV file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{csv_stem}.csv", csv_content)
    return buf.getvalue()


# Patch targets
_PATCH_GAUTH = "ca_biositing.pipeline.utils.gdrive_to_pandas.GoogleAuth"
_PATCH_GDRIVE = "ca_biositing.pipeline.utils.gdrive_to_pandas.GoogleDrive"


def _assert_get_content_string_used(file_entry):
    """Regression guard: GetContentString must be called; GetContentFile must not."""
    file_entry.GetContentString.assert_called_once()
    file_entry.GetContentFile.assert_not_called()


# ---------------------------------------------------------------------------
# CSV infrastructure datasets
# ---------------------------------------------------------------------------

class TestInfrastructureCSV:
    """
    Tests for text/csv infrastructure datasets.

    Each parametrized case corresponds to one real extract module so failures
    are immediately traceable to a specific ETL source.
    CSV is parsed in-memory from io.StringIO — no disk I/O.
    """

    # (file_name, representative columns, csv bytes)
    CSV_DATASETS = [
        (
            "CAFO_Locations_and_Manure_Production.csv",
            ["facility_name", "county", "manure_tons_per_year"],
            b"facility_name,county,manure_tons_per_year\nDairy A,Fresno,1200\nDairy B,Tulare,3400\n",
        ),
        (
            "Livestock_Anaerobic_Digesters.csv",
            ["digester_name", "county", "capacity_kw"],
            b"digester_name,county,capacity_kw\nDigester 1,Kings,500\nDigester 2,Merced,800\n",
        ),
        (
            "Wastewater_Treatment_Plants.csv",
            ["plant_name", "city", "flow_mgd"],
            b"plant_name,city,flow_mgd\nPlant X,Fresno,12.5\nPlant Y,Bakersfield,8.0\n",
        ),
        (
            "Biodiesel_Plants.csv",
            ["plant_name", "capacity_mgy"],
            b"plant_name,capacity_mgy\nBioPlant A,3.5\nBioPlant B,10.0\n",
        ),
        (
            "Ethanol_Biorefineries.csv",
            ["refinery_name", "state"],
            b"refinery_name,state\nRefinery 1,CA\nRefinery 2,CA\n",
        ),
        (
            "saf_and_renewable_diesel_plants.csv",
            ["plant_name", "fuel_type"],
            b"plant_name,fuel_type\nSAF Plant 1,SAF\nRD Plant 1,RD\n",
        ),
        (
            "Biosolids_Facilities.csv",
            ["facility_name", "county"],
            b"facility_name,county\nFacility A,Alameda\nFacility B,Contra Costa\n",
        ),
        (
            "Landfills.csv",
            ["landfill_name", "county"],
            b"landfill_name,county\nLandfill 1,Sacramento\nLandfill 2,Placer\n",
        ),
    ]

    @pytest.mark.parametrize("file_name,expected_cols,csv_bytes", CSV_DATASETS)
    def test_returns_dataframe(self, tmp_path, file_name, expected_cols, csv_bytes):
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        file_entry = _make_file_entry(csv_bytes)
        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=_make_drive_mock(file_entry)):
            df = gdrive_to_df(file_name, "text/csv", "credentials.json", str(tmp_path))

        assert isinstance(df, pd.DataFrame), f"{file_name}: expected DataFrame"

    @pytest.mark.parametrize("file_name,expected_cols,csv_bytes", CSV_DATASETS)
    def test_correct_row_count(self, tmp_path, file_name, expected_cols, csv_bytes):
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        file_entry = _make_file_entry(csv_bytes)
        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=_make_drive_mock(file_entry)):
            df = gdrive_to_df(file_name, "text/csv", "credentials.json", str(tmp_path))

        assert len(df) == 2, f"{file_name}: expected 2 rows"

    @pytest.mark.parametrize("file_name,expected_cols,csv_bytes", CSV_DATASETS)
    def test_expected_columns_present(self, tmp_path, file_name, expected_cols, csv_bytes):
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        file_entry = _make_file_entry(csv_bytes)
        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=_make_drive_mock(file_entry)):
            df = gdrive_to_df(file_name, "text/csv", "credentials.json", str(tmp_path))

        for col in expected_cols:
            assert col in df.columns, f"{file_name}: missing column '{col}'"

    @pytest.mark.parametrize("file_name,expected_cols,csv_bytes", CSV_DATASETS)
    def test_uses_get_content_string_not_get_content_file(
        self, tmp_path, file_name, expected_cols, csv_bytes
    ):
        """Regression: GetContentString must be called; GetContentFile must not."""
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        file_entry = _make_file_entry(csv_bytes)
        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=_make_drive_mock(file_entry)):
            gdrive_to_df(file_name, "text/csv", "credentials.json", str(tmp_path))

        _assert_get_content_string_used(file_entry)

    def test_csv_parsed_without_disk_io(self, tmp_path):
        """CSV is parsed in-memory from StringIO — no file written to tmp_path."""
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        csv_bytes = b"facility_name,county\nDairy A,Fresno\n"
        file_entry = _make_file_entry(csv_bytes)
        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=_make_drive_mock(file_entry)):
            df = gdrive_to_df(
                "CAFO_Locations_and_Manure_Production.csv",
                "text/csv",
                "credentials.json",
                str(tmp_path),
            )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert list(tmp_path.iterdir()) == []

    def test_deduplicates_columns(self, tmp_path):
        """Duplicate column labels in the DataFrame are dropped (first occurrence kept).

        pandas >=2.0 mangles duplicate CSV header names at read time so we
        patch pd.read_csv to return a DataFrame that already has genuinely
        duplicate column labels — the scenario gdrive_to_df's dedup logic
        handles.
        """
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        dup_df = pd.DataFrame(
            [[1, 2, 3]], columns=["facility_name", "county", "facility_name"]
        )

        file_entry = _make_file_entry(b"facility_name,county,facility_name\n1,2,3\n")
        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=_make_drive_mock(file_entry)), \
             patch(
                 "ca_biositing.pipeline.utils.gdrive_to_pandas.pd.read_csv",
                 return_value=dup_df,
             ):
            df = gdrive_to_df(
                "CAFO_Locations_and_Manure_Production.csv",
                "text/csv",
                "credentials.json",
                str(tmp_path),
            )

        assert list(df.columns) == ["facility_name", "county"]
        assert len(df) == 1

    def test_lookup_by_file_id(self, tmp_path):
        """When file_id is provided, CreateFile is used instead of ListFile."""
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        csv_bytes = b"facility_name,county\nDairy A,Fresno\n"
        file_entry = _make_file_entry(csv_bytes)
        drive_mock = _make_drive_mock(file_entry)

        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=drive_mock):
            df = gdrive_to_df(
                "CAFO_Locations_and_Manure_Production.csv",
                "text/csv",
                "credentials.json",
                str(tmp_path),
                file_id="abc123",
            )

        drive_mock.CreateFile.assert_called_once_with({"id": "abc123"})
        drive_mock.ListFile.assert_not_called()
        assert isinstance(df, pd.DataFrame)

    def test_returns_none_when_file_not_found(self, tmp_path):
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        drive_mock = MagicMock()
        drive_mock.ListFile.return_value.GetList.return_value = []

        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=drive_mock):
            result = gdrive_to_df(
                "CAFO_Locations_and_Manure_Production.csv",
                "text/csv",
                "credentials.json",
                str(tmp_path),
            )

        assert result is None


# ---------------------------------------------------------------------------
# ZIP infrastructure datasets
# ---------------------------------------------------------------------------

class TestInfrastructureZIP:
    """
    Tests for application/zip infrastructure datasets.

    ZIP is binary; GetContentString uses latin-1 encoding so every byte
    round-trips intact through the str → bytes conversion.
    Extraction happens in a temp directory (outside OneDrive).
    """

    ZIP_DATASETS = [
        (
            "CA_comb_points.zip",
            ["facility", "county", "type"],
            b"facility,county,type\nPlant 1,Fresno,Biomass\nPlant 2,Kern,Biomass\n",
        ),
        (
            "CA_proc_points.zip",
            ["facility", "county", "sic_code"],
            b"facility,county,sic_code\nProcessor 1,Tulare,2011\nProcessor 2,Kings,2013\n",
        ),
        (
            "CA_des_points.zip",
            ["system_name", "city", "capacity_mw"],
            b"system_name,city,capacity_mw\nDES 1,Sacramento,5.0\nDES 2,San Jose,3.2\n",
        ),
        (
            "CA_wte_points.zip",
            ["facility", "county", "technology"],
            b"facility,county,technology\nWTE 1,Los Angeles,AD\nWTE 2,San Bernardino,Landfill Gas\n",
        ),
    ]

    def _zip_entry(self, file_name, csv_bytes):
        """Build a file entry with latin-1 encoding (required for binary ZIP round-trip)."""
        csv_stem = file_name[:-4]
        return _make_file_entry(_make_zip_bytes(csv_stem, csv_bytes), encoding="latin-1")

    @pytest.mark.parametrize("file_name,expected_cols,csv_bytes", ZIP_DATASETS)
    def test_returns_dataframe(self, tmp_path, file_name, expected_cols, csv_bytes):
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        file_entry = self._zip_entry(file_name, csv_bytes)
        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=_make_drive_mock(file_entry)):
            df = gdrive_to_df(file_name, "application/zip", "credentials.json", str(tmp_path))

        assert isinstance(df, pd.DataFrame), f"{file_name}: expected DataFrame"

    @pytest.mark.parametrize("file_name,expected_cols,csv_bytes", ZIP_DATASETS)
    def test_correct_row_count(self, tmp_path, file_name, expected_cols, csv_bytes):
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        file_entry = self._zip_entry(file_name, csv_bytes)
        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=_make_drive_mock(file_entry)):
            df = gdrive_to_df(file_name, "application/zip", "credentials.json", str(tmp_path))

        assert len(df) == 2, f"{file_name}: expected 2 rows"

    @pytest.mark.parametrize("file_name,expected_cols,csv_bytes", ZIP_DATASETS)
    def test_expected_columns_present(self, tmp_path, file_name, expected_cols, csv_bytes):
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        file_entry = self._zip_entry(file_name, csv_bytes)
        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=_make_drive_mock(file_entry)):
            df = gdrive_to_df(file_name, "application/zip", "credentials.json", str(tmp_path))

        for col in expected_cols:
            assert col in df.columns, f"{file_name}: missing column '{col}'"

    @pytest.mark.parametrize("file_name,expected_cols,csv_bytes", ZIP_DATASETS)
    def test_uses_get_content_string_not_get_content_file(
        self, tmp_path, file_name, expected_cols, csv_bytes
    ):
        """Regression: GetContentString must be called; GetContentFile must not."""
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        file_entry = self._zip_entry(file_name, csv_bytes)
        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=_make_drive_mock(file_entry)):
            gdrive_to_df(file_name, "application/zip", "credentials.json", str(tmp_path))

        _assert_get_content_string_used(file_entry)


# ---------------------------------------------------------------------------
# GeoJSON infrastructure dataset
# ---------------------------------------------------------------------------

class TestInfrastructureGeoJSON:
    """Tests for application/geo+json (petroleum_pipelines ETL).

    GeoJSON is text; parsed in-memory from io.StringIO — no disk I/O.
    """

    FILE_NAME = "US_Petroleum_Pipelines.geojson"
    MIME_TYPE = "application/geo+json"

    GEOJSON_BYTES = json.dumps({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-120.5, 37.3], [-119.8, 38.1]],
                },
                "properties": {"name": "Pipeline A", "operator": "Acme Oil"},
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-118.2, 34.0], [-117.5, 35.2]],
                },
                "properties": {"name": "Pipeline B", "operator": "Beta Energy"},
            },
        ],
    }).encode()

    def _run(self, tmp_path):
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        file_entry = _make_file_entry(self.GEOJSON_BYTES)
        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=_make_drive_mock(file_entry)):
            return gdrive_to_df(
                self.FILE_NAME,
                self.MIME_TYPE,
                "credentials.json",
                str(tmp_path),
            )

    def test_returns_geodataframe(self, tmp_path):
        df = self._run(tmp_path)
        assert isinstance(df, gpd.GeoDataFrame)

    def test_correct_row_count(self, tmp_path):
        df = self._run(tmp_path)
        assert len(df) == 2

    def test_has_geometry_column(self, tmp_path):
        df = self._run(tmp_path)
        assert "geometry" in df.columns

    def test_property_columns_present(self, tmp_path):
        df = self._run(tmp_path)
        assert "name" in df.columns
        assert "operator" in df.columns

    def test_geojson_parsed_without_disk_io(self, tmp_path):
        """GeoJSON is parsed in-memory from StringIO — no file written to disk."""
        self._run(tmp_path)
        assert list(tmp_path.iterdir()) == []

    def test_uses_get_content_string_not_get_content_file(self, tmp_path):
        """Regression: GetContentString must be called; GetContentFile must not."""
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        file_entry = _make_file_entry(self.GEOJSON_BYTES)
        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=_make_drive_mock(file_entry)):
            gdrive_to_df(
                self.FILE_NAME,
                self.MIME_TYPE,
                "credentials.json",
                str(tmp_path),
            )

        _assert_get_content_string_used(file_entry)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestGdriveToDfErrors:
    """Error handling paths in gdrive_to_df."""

    def test_returns_none_on_auth_error(self, tmp_path):
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df
        from pydrive2.auth import AuthenticationError

        with patch(_PATCH_GAUTH, side_effect=AuthenticationError("bad creds")):
            result = gdrive_to_df(
                "CAFO_Locations_and_Manure_Production.csv",
                "text/csv",
                "credentials.json",
                str(tmp_path),
            )
        assert result is None

    def test_returns_none_on_api_request_error(self, tmp_path):
        """A Drive API error during ListFile must result in None being returned."""
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df
        from pydrive2.files import ApiRequestError

        drive_mock = MagicMock()
        api_err = MagicMock(spec=ApiRequestError)
        drive_mock.ListFile.return_value.GetList.side_effect = api_err

        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=drive_mock):
            result = gdrive_to_df(
                "Wastewater_Treatment_Plants.csv",
                "text/csv",
                "credentials.json",
                str(tmp_path),
            )
        assert result is None

    def test_returns_none_on_unsupported_mime(self, tmp_path):
        """Unsupported MIME type must return None (exception caught internally)."""
        from ca_biositing.pipeline.utils.gdrive_to_pandas import gdrive_to_df

        file_entry = _make_file_entry(b"binary content")
        with patch(_PATCH_GAUTH, return_value=_make_gauth_mock()), \
             patch(_PATCH_GDRIVE, return_value=_make_drive_mock(file_entry)):
            result = gdrive_to_df(
                "something.pdf",
                "application/pdf",
                "credentials.json",
                str(tmp_path),
            )
        assert result is None
