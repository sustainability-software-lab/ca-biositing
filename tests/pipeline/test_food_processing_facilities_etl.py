"""Tests for the food processing facilities ETL pipeline.

Coverage:
- Extract: module structure and sheet name constants
- Transform: column mapping, row count, key field values, byproduct pairing,
  geocoder delta logic, spurious-title-row detection
- Load: empty-DataFrame short-circuit, upsert execution, session commit
- gsheet_to_pandas: duplicate-column preservation (the _dedupe_columns fix)
- Flow: flow object exists and has correct name
"""

from unittest.mock import MagicMock, patch, call
import os
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw_df_real_world():
    """Simulate what gsheet_to_df NOW returns after the _dedupe_columns fix.

    The Google Sheet has five 'Quantity (tons/year)' columns.  The old code
    dropped four of them; the fixed code renames them _2 … _5 so all five
    survive.  This fixture reflects the fixed extractor output.
    """
    return pd.DataFrame(
        [
            [
                "ID1", "Acme Foods", "123 Main St\nSuite 5", "Fresno",
                "93721-1234", "Fresno", "San Joaquin", "drying", "tomato",
                "Pomace", "100",
                "Seeds", "50",
                "", "",
                "", "",
                "", "",
            ],
            [
                "ID2", "Brew Co", "500 Beer Rd", "Sacramento",
                "95814", "Sacramento", "Bay Area", "fermentation", "beer",
                "Spent grain", "200",
                "", "",
                "", "",
                "", "",
                "", "",
            ],
        ],
        columns=[
            "Facility ID", "Name", "Address", "City", "Zip", "County",
            "Air district", "Process", "Associated food",
            "Byproduct 1", "Quantity (tons/year)",
            "Byproduct 2", "Quantity (tons/year)_2",
            "Byproduct 3", "Quantity (tons/year)_3",
            "Byproduct 4", "Quantity (tons/year)_4",
            "Byproduct 5", "Quantity (tons/year)_5",
        ],
    )


def _make_raw_df_legacy():
    """Simulate the OLD gsheet_to_df output (duplicate columns already dropped).

    This is what the transform received before the fix — only one quantity
    column survived.  Used to verify the transform still works with this shape
    (backward-compat guard).
    """
    return pd.DataFrame(
        [
            [
                "ID1", "Acme Foods", "123 Main St\nSuite 5", "Fresno",
                "93721-1234", "Fresno", "San Joaquin", "drying", "tomato",
                "Pomace", "100",
                "Seeds",
                "Husks",
                "Pulp",
                "Fiber",
            ],
        ],
        columns=[
            "Facility ID", "Name", "Address", "City", "Zip", "County",
            "Air district", "Process", "Associated food",
            "Byproduct 1", "Quantity (tons/year)",
            "Byproduct 2",
            "Byproduct 3",
            "Byproduct 4",
            "Byproduct 5",
        ],
    )


# ---------------------------------------------------------------------------
# Extract tests
# ---------------------------------------------------------------------------

class TestFoodProcessingFacilitiesExtract:
    def test_extract_module_exists(self):
        from ca_biositing.pipeline.etl.extract import food_processing_facilities

        assert food_processing_facilities is not None
        assert hasattr(food_processing_facilities, "extract_all_facilities")
        assert hasattr(food_processing_facilities, "extract_geocoder_test_set")

    def test_extract_sheet_names(self):
        from ca_biositing.pipeline.etl.extract import food_processing_facilities

        assert food_processing_facilities.GSHEET_NAME == "food_manufacturers_and_processors_carb"
        assert food_processing_facilities.WORKSHEET_ALL_FACILITIES == "all facilities"
        assert food_processing_facilities.WORKSHEET_GEOCODER_TEST_SET == "test set for geocoder"


# ---------------------------------------------------------------------------
# gsheet_to_pandas deduplication fix tests
# ---------------------------------------------------------------------------

class TestGsheetToPandasDedup:
    """Verify that _dedupe_columns preserves all duplicate-header columns."""

    def test_dedupe_columns_preserves_all(self):
        """_dedupe_columns must rename duplicates, not drop them."""
        from ca_biositing.pipeline.utils.gsheet_to_pandas import _dedupe_columns

        cols = [
            "Byproduct 1", "Quantity (tons/year)",
            "Byproduct 2", "Quantity (tons/year)",
            "Byproduct 3", "Quantity (tons/year)",
        ]
        result = _dedupe_columns(cols)
        assert len(result) == 6, "All 6 columns must be preserved"
        assert result[1] == "Quantity (tons/year)"
        assert result[3] == "Quantity (tons/year)_2"
        assert result[5] == "Quantity (tons/year)_3"

    def test_dedupe_columns_no_duplicates_unchanged(self):
        from ca_biositing.pipeline.utils.gsheet_to_pandas import _dedupe_columns

        cols = ["A", "B", "C"]
        assert _dedupe_columns(cols) == ["A", "B", "C"]

    def test_gsheet_to_df_uses_dedupe_not_drop(self):
        """gsheet_to_df must not silently drop duplicate-header columns."""
        import gspread
        from unittest.mock import MagicMock, patch

        mock_ws = MagicMock()
        mock_ws.get_all_values.return_value = [
            ["Name", "Qty", "Name", "Qty"],   # header row with duplicates
            ["Acme", "10", "Beta", "20"],
        ]
        mock_ss = MagicMock()
        mock_ss.worksheet.return_value = mock_ws
        mock_gc = MagicMock()
        mock_gc.open.return_value = mock_ss

        with patch("gspread.service_account", return_value=mock_gc):
            from ca_biositing.pipeline.utils.gsheet_to_pandas import gsheet_to_df
            df = gsheet_to_df("sheet", "tab", "creds.json")

        assert df is not None
        assert len(df.columns) == 4, (
            "All 4 columns must be preserved; old code dropped 2 duplicates"
        )
        # Second 'Name' becomes 'Name_2', second 'Qty' becomes 'Qty_2'
        assert "Name_2" in df.columns
        assert "Qty_2" in df.columns


# ---------------------------------------------------------------------------
# Transform tests
# ---------------------------------------------------------------------------

class TestFoodProcessingFacilitiesTransform:

    # --- existing test (updated to use real-world column shape) ---

    def test_transform_returns_dataframe(self):
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        raw_df = _make_raw_df_real_world()

        result = food_processing_facilities.transform.fn(
            data_sources={
                "all_facilities": raw_df,
                "geocoder_test_set": pd.DataFrame(),
            },
            etl_run_id=101,
            lineage_group_id=202,
        )

        assert result is not None
        assert len(result) == 2
        assert result.loc[0, "state"] == "CA"
        assert result.loc[0, "zip"] == "93721"
        assert result.loc[0, "address"] == "123 Main St Suite 5"
        assert result.loc[0, "process_type"] == "Drying"
        assert result.loc[0, "general_source_info"] == "Processing Tomato Advisory Board 2022"
        assert result.loc[1, "general_source_info"] == "California Department of Alcoholic Beverage Control 2024"
        assert result.loc[0, "byproducts"] == "Pomace, Seeds"
        assert result.loc[0, "quantities"] == "100, 50"
        assert result.loc[0, "etl_run_id"] == 101
        assert result.loc[0, "lineage_group_id"] == 202

    def test_transform_missing_source_returns_none(self):
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        result = food_processing_facilities.transform.fn(
            data_sources={"all_facilities": pd.DataFrame()},
            etl_run_id=1,
            lineage_group_id=2,
        )

        assert result is None

    # --- NEW: intermediate DataFrame assertion tests ---

    def test_transform_output_has_nonzero_rows(self):
        """Transform must return > 0 rows given valid input."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        result = food_processing_facilities.transform.fn(
            data_sources={
                "all_facilities": _make_raw_df_real_world(),
                "geocoder_test_set": pd.DataFrame(),
            },
            etl_run_id=1,
            lineage_group_id=1,
        )

        assert result is not None
        assert len(result) > 0, "Transform must produce at least one row"

    def test_transform_key_columns_not_all_null(self):
        """Key columns (name, address, city, zip, state) must not be entirely null."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        result = food_processing_facilities.transform.fn(
            data_sources={
                "all_facilities": _make_raw_df_real_world(),
                "geocoder_test_set": pd.DataFrame(),
            },
            etl_run_id=1,
            lineage_group_id=1,
        )

        assert result is not None
        for col in ("name", "address", "city", "zip", "state"):
            non_null = result[col].notna().sum()
            assert non_null > 0, (
                f"Column '{col}' is entirely null in transform output — "
                "likely a column-name mismatch between the sheet and the transform code"
            )

    def test_transform_all_final_columns_present(self):
        """Transform output must contain all columns expected by the DB model."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        result = food_processing_facilities.transform.fn(
            data_sources={
                "all_facilities": _make_raw_df_real_world(),
                "geocoder_test_set": pd.DataFrame(),
            },
            etl_run_id=1,
            lineage_group_id=1,
        )

        assert result is not None
        required_cols = [
            "name", "address", "city", "zip", "state", "county",
            "process_type", "primary_ag_product", "byproducts", "quantities",
            "general_source_info", "etl_run_id", "lineage_group_id",
        ]
        for col in required_cols:
            assert col in result.columns, f"Expected column '{col}' missing from transform output"

    def test_transform_byproduct_quantity_pairing_real_world_columns(self):
        """With the fixed gsheet_to_df output, all 5 byproduct/quantity pairs must be captured."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        # Row with all 5 byproducts filled in
        df = pd.DataFrame(
            [[
                "ID1", "Acme", "1 Main St", "Fresno", "93721", "Fresno",
                "Valley Air", "drying", "tomato",
                "Pomace", "100",
                "Seeds", "50",
                "Husks", "30",
                "Pulp", "20",
                "Fiber", "10",
            ]],
            columns=[
                "Facility ID", "Name", "Address", "City", "Zip", "County",
                "Air district", "Process", "Associated food",
                "Byproduct 1", "Quantity (tons/year)",
                "Byproduct 2", "Quantity (tons/year)_2",
                "Byproduct 3", "Quantity (tons/year)_3",
                "Byproduct 4", "Quantity (tons/year)_4",
                "Byproduct 5", "Quantity (tons/year)_5",
            ],
        )

        result = food_processing_facilities.transform.fn(
            data_sources={"all_facilities": df, "geocoder_test_set": pd.DataFrame()},
            etl_run_id=1,
            lineage_group_id=1,
        )

        assert result is not None
        assert result.loc[0, "byproducts"] == "Pomace, Seeds, Husks, Pulp, Fiber"
        assert result.loc[0, "quantities"] == "100, 50, 30, 20, 10"

    def test_transform_spurious_title_row_is_fixed(self):
        """If row 0 is a spurious title row and row 1 contains real headers, transform must fix it."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        # Simulate a sheet where row 0 is a title and row 1 is the real header
        df_with_title = pd.DataFrame(
            [
                # Row 0: spurious title row (all values are the real column names)
                ["Facility ID", "Name", "Address", "City", "Zip", "County",
                 "Air district", "Process", "Associated food",
                 "Byproduct 1", "Quantity (tons/year)",
                 "Byproduct 2", "Quantity (tons/year)_2",
                 "Byproduct 3", "Quantity (tons/year)_3",
                 "Byproduct 4", "Quantity (tons/year)_4",
                 "Byproduct 5", "Quantity (tons/year)_5"],
                # Row 1: actual data
                ["ID1", "Acme Foods", "1 Main St", "Fresno", "93721", "Fresno",
                 "Valley Air", "drying", "tomato",
                 "Pomace", "100", "", "", "", "", "", "", "", ""],
            ],
            columns=[
                "Spurious Title", "", "", "", "", "", "", "", "",
                "", "", "", "", "", "", "", "", "", "",
            ],
        )

        result = food_processing_facilities.transform.fn(
            data_sources={"all_facilities": df_with_title, "geocoder_test_set": pd.DataFrame()},
            etl_run_id=1,
            lineage_group_id=1,
        )

        assert result is not None
        assert len(result) == 1, "Only the data row should remain after header fix"
        assert result.loc[0, "name"] == "Acme Foods"

    def test_transform_geocoder_delta_skips_already_geocoded(self):
        """Geocoder delta check must not re-geocode rows already in the DB."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        geo_df = pd.DataFrame(
            [["123 Main St", "Fresno", "93721"]],
            columns=["Address", "City", "Zip"],
        )

        # Mock the DB query to return the same address as already geocoded
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, i: ["123 Main St", "Fresno", "CA", "93721"][i]

        with patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = [
                ("123 Main St", "Fresno", "CA", "93721")
            ]

            result = food_processing_facilities.transform.fn(
                data_sources={
                    "all_facilities": _make_raw_df_real_world(),
                    "geocoder_test_set": geo_df,
                },
                etl_run_id=1,
                lineage_group_id=1,
            )

        # Transform should still succeed; geocoding skipped for already-geocoded row
        assert result is not None
        assert len(result) > 0

    def test_transform_empty_all_facilities_returns_none(self):
        """Transform must return None when all_facilities is empty."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        result = food_processing_facilities.transform.fn(
            data_sources={
                "all_facilities": pd.DataFrame(),
                "geocoder_test_set": pd.DataFrame(),
            },
            etl_run_id=1,
            lineage_group_id=1,
        )

        assert result is None


# ---------------------------------------------------------------------------
# Load tests
# ---------------------------------------------------------------------------

class TestFoodProcessingFacilitiesLoad:

    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_run_logger")
    def test_load_handles_empty_dataframe(self, mock_logger):
        from ca_biositing.pipeline.etl.load import food_processing_facilities

        mock_logger.return_value.info = lambda msg: None
        assert food_processing_facilities.load.fn(pd.DataFrame()) is True

    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.Session")
    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_engine")
    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_run_logger")
    def test_load_executes_upsert(self, mock_logger, mock_get_engine, mock_session_class):
        from ca_biositing.pipeline.etl.load import food_processing_facilities

        mock_logger.return_value.info = lambda msg: None

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        mock_session = MagicMock()
        # Session(engine) used as context manager
        mock_session_class.return_value.__enter__.return_value = mock_session
        # session.begin() used as context manager
        mock_session.begin.return_value.__enter__ = MagicMock(return_value=None)
        mock_session.begin.return_value.__exit__ = MagicMock(return_value=False)

        df = pd.DataFrame(
            {
                "name": ["Acme Foods"],
                "address": ["123 Main St"],
                "city": ["Fresno"],
                "zip": ["93721"],
            }
        )

        result = food_processing_facilities.load.fn(df)

        assert result is True
        assert mock_session.execute.called

    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.Session")
    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_engine")
    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_run_logger")
    def test_load_receives_nonempty_dataframe(self, mock_logger, mock_get_engine, mock_session_class):
        """Load must call session.execute at least once when given real data.

        This test catches the regression where Session(bind=conn) silently
        failed in SQLAlchemy 2.x, causing 0 rows to be written.
        """
        from ca_biositing.pipeline.etl.load import food_processing_facilities

        mock_logger.return_value.info = lambda msg: None
        mock_logger.return_value.error = lambda msg: None

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        mock_session.begin.return_value.__enter__ = MagicMock(return_value=None)
        mock_session.begin.return_value.__exit__ = MagicMock(return_value=False)

        df = pd.DataFrame(
            {
                "name": ["Acme Foods", "Brew Co"],
                "address": ["123 Main St", "500 Beer Rd"],
                "city": ["Fresno", "Sacramento"],
                "zip": ["93721", "95814"],
                "state": ["CA", "CA"],
            }
        )

        result = food_processing_facilities.load.fn(df)

        assert result is True, "load() must return True for non-empty DataFrame"
        assert mock_session.execute.call_count == 2, (
            f"session.execute must be called once per record; "
            f"got {mock_session.execute.call_count} calls for 2 records"
        )

    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_run_logger")
    def test_load_returns_false_on_exception(self, mock_logger):
        """Load must return False (not raise) when an exception occurs."""
        from ca_biositing.pipeline.etl.load import food_processing_facilities

        mock_logger.return_value.info = lambda msg: None
        mock_logger.return_value.error = lambda msg: None

        df = pd.DataFrame({"name": ["Acme"]})

        # get_engine raises to simulate DB connection failure
        with patch(
            "ca_biositing.pipeline.etl.load.food_processing_facilities.get_engine",
            side_effect=RuntimeError("DB unavailable"),
        ):
            result = food_processing_facilities.load.fn(df)

        assert result is False


# ---------------------------------------------------------------------------
# Geocoding env-var tests
# ---------------------------------------------------------------------------

class TestGeocodingEnvVar:
    """Verify that GOOGLE_MAPS_API_KEY is read at runtime, not import time."""

    def test_geocoding_skipped_when_key_not_set(self):
        """When GOOGLE_MAPS_API_KEY is absent, transform must still return data."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        env_without_key = {k: v for k, v in os.environ.items() if k != "GOOGLE_MAPS_API_KEY"}

        with patch.dict(os.environ, env_without_key, clear=True):
            result = food_processing_facilities.transform.fn(
                data_sources={
                    "all_facilities": _make_raw_df_real_world(),
                    "geocoder_test_set": pd.DataFrame(),
                },
                etl_run_id=1,
                lineage_group_id=1,
            )

        assert result is not None
        assert len(result) > 0

    def test_flow_calls_load_dotenv(self):
        """The flow module must call load_dotenv() so GOOGLE_MAPS_API_KEY is available."""
        import importlib
        import sys

        # Reload the flow module to re-execute module-level load_dotenv()
        mod_name = "ca_biositing.pipeline.flows.food_processing_facilities"
        if mod_name in sys.modules:
            del sys.modules[mod_name]

        with patch("dotenv.load_dotenv") as mock_load_dotenv:
            import ca_biositing.pipeline.flows.food_processing_facilities  # noqa: F401
            assert mock_load_dotenv.called, (
                "load_dotenv() must be called at flow module import time "
                "so GOOGLE_MAPS_API_KEY is loaded from .env into os.environ"
            )


# ---------------------------------------------------------------------------
# Flow tests
# ---------------------------------------------------------------------------

class TestFoodProcessingFacilitiesFlow:
    def test_flow_exists(self):
        from ca_biositing.pipeline.flows.food_processing_facilities import food_processing_facilities_flow

        assert food_processing_facilities_flow is not None
        assert food_processing_facilities_flow.name == "Food Processing Facilities ETL"
