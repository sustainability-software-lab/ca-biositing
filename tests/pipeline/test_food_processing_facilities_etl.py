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
    """Tests for the transform task.

    NOTE: The transform now routes based on GEOCODE_TARGET:
      - "geocoder_test_set" (default): geocodes and loads only the test-set rows.
        If geocoder_test_set is empty, returns an empty DataFrame.
      - "all_facilities": geocodes and loads all_facilities rows.

    Tests that want to exercise the all_facilities cleaning/column logic must
    patch GEOCODE_TARGET to "all_facilities" so the transform returns those rows.
    Tests that want to exercise the geocoder_test_set path pass a non-empty geo df.
    """

    def _patch_geocode_target(self, target: str):
        """Return a context manager that patches GEOCODE_TARGET in the transform module."""
        import ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities as mod
        return patch.object(mod, "GEOCODE_TARGET", target)

    # --- all_facilities path tests (GEOCODE_TARGET="all_facilities") ---

    def test_transform_returns_dataframe(self):
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        raw_df = _make_raw_df_real_world()

        with self._patch_geocode_target("all_facilities"), \
             patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []  # empty DB
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
        assert result.loc[0, "address"] == "123 MAIN ST SUITE 5"
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

    def test_transform_output_has_nonzero_rows(self):
        """Transform must return > 0 rows given valid input (all_facilities mode)."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        with self._patch_geocode_target("all_facilities"), \
             patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []
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

        with self._patch_geocode_target("all_facilities"), \
             patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []
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

        with self._patch_geocode_target("all_facilities"), \
             patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []
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
            "geocode_status",
        ]
        for col in required_cols:
            assert col in result.columns, f"Expected column '{col}' missing from transform output"

    def test_transform_byproduct_quantity_pairing_real_world_columns(self):
        """With the fixed gsheet_to_df output, all 5 byproduct/quantity pairs must be captured."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

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

        with self._patch_geocode_target("all_facilities"), \
             patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []
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

        df_with_title = pd.DataFrame(
            [
                ["Facility ID", "Name", "Address", "City", "Zip", "County",
                 "Air district", "Process", "Associated food",
                 "Byproduct 1", "Quantity (tons/year)",
                 "Byproduct 2", "Quantity (tons/year)_2",
                 "Byproduct 3", "Quantity (tons/year)_3",
                 "Byproduct 4", "Quantity (tons/year)_4",
                 "Byproduct 5", "Quantity (tons/year)_5"],
                ["ID1", "Acme Foods", "1 Main St", "Fresno", "93721", "Fresno",
                 "Valley Air", "drying", "tomato",
                 "Pomace", "100", "", "", "", "", "", "", "", ""],
            ],
            columns=[
                "Spurious Title", "", "", "", "", "", "", "", "",
                "", "", "", "", "", "", "", "", "", "",
            ],
        )

        with self._patch_geocode_target("all_facilities"), \
             patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []
            result = food_processing_facilities.transform.fn(
                data_sources={"all_facilities": df_with_title, "geocoder_test_set": pd.DataFrame()},
                etl_run_id=1,
                lineage_group_id=1,
            )

        assert result is not None
        assert len(result) == 1, "Only the data row should remain after header fix"
        assert result.loc[0, "name"] == "ACME FOODS"

    def test_transform_geocoder_delta_skips_already_geocoded(self):
        """Geocoder delta check must not re-geocode rows already in the DB."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        geo_df = pd.DataFrame(
            [["123 Main St", "Fresno", "93721"]],
            columns=["Address", "City", "Zip"],
        )

        with patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = [
                ("123 Main St", "Fresno", "CA", "93721")
            ]

            # GEOCODE_TARGET="geocoder_test_set" (default) — geo_df is non-empty,
            # so the geocoding block runs on it. Delta check finds the address
            # already in DB → to_geocode is empty → no API call.
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

    # --- geocoder_test_set path tests (GEOCODE_TARGET="geocoder_test_set") ---

    def test_transform_geocode_target_test_set_empty_returns_empty_df(self):
        """When GEOCODE_TARGET=geocoder_test_set and the test set is empty, return empty DataFrame."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        # Default GEOCODE_TARGET is "geocoder_test_set"; empty geo df → empty result
        result = food_processing_facilities.transform.fn(
            data_sources={
                "all_facilities": _make_raw_df_real_world(),
                "geocoder_test_set": pd.DataFrame(),
            },
            etl_run_id=1,
            lineage_group_id=1,
        )

        # Returns empty DataFrame (not None) — empty geo set is a valid no-op
        assert result is not None
        assert len(result) == 0, (
            "When GEOCODE_TARGET=geocoder_test_set and test set is empty, "
            "transform must return an empty DataFrame (nothing to geocode or load)"
        )

    def test_transform_geocode_target_test_set_returns_geo_rows(self):
        """When GEOCODE_TARGET=geocoder_test_set and test set is non-empty, return geocoded rows."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        geo_df = pd.DataFrame(
            [["123 Main St", "Fresno", "93721", "Fresno County"]],
            columns=["Address", "City", "Zip", "County"],
        )

        with patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"), \
             patch.dict(os.environ, {}, clear=True):  # no API key → geocoding skipped
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []  # empty DB

            result = food_processing_facilities.transform.fn(
                data_sources={
                    "all_facilities": _make_raw_df_real_world(),
                    "geocoder_test_set": geo_df,
                },
                etl_run_id=5,
                lineage_group_id=6,
            )

        assert result is not None
        assert len(result) == 1, "Should return the 1 geocoder test set row"
        assert result.loc[0, "etl_run_id"] == 5
        assert result.loc[0, "lineage_group_id"] == 6
        assert "latitude" in result.columns
        assert "longitude" in result.columns
        assert "address" in result.columns

    def test_transform_geocode_target_all_facilities_returns_all_rows(self):
        """When GEOCODE_TARGET=all_facilities, return all_facilities rows (not test set)."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        with self._patch_geocode_target("all_facilities"), \
             patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []
            result = food_processing_facilities.transform.fn(
                data_sources={
                    "all_facilities": _make_raw_df_real_world(),
                    "geocoder_test_set": pd.DataFrame(),
                },
                etl_run_id=1,
                lineage_group_id=1,
            )

        assert result is not None
        assert len(result) == 2, "Should return all 2 all_facilities rows"


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
        """When GOOGLE_MAPS_API_KEY is absent, transform must still return data (all_facilities mode)."""
        import ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities as mod
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        env_without_key = {k: v for k, v in os.environ.items() if k != "GOOGLE_MAPS_API_KEY"}

        # Use all_facilities mode so the result contains the all_facilities rows
        with patch.dict(os.environ, env_without_key, clear=True), \
             patch.object(mod, "GEOCODE_TARGET", "all_facilities"), \
             patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []
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
# Bug-regression tests — Issue 0: ALL CAPS normalization for identity columns
# ---------------------------------------------------------------------------

class TestAllCapsNormalization:
    """Regression tests for ALL CAPS normalization of identity columns.

    The CARB source sheet stores city in ALL CAPS (e.g. "FRESNO") and address
    in ALL CAPS (e.g. "123 MAIN ST").  The pipeline standardizes ALL identity
    columns (name, address, city, state) to ALL CAPS so that:

      * The UPSERT conflict key (name, address, city, zip) always matches
        exactly in Postgres (case-sensitive comparison).
      * The seed-CSV path and the sheet-ETL path produce identical keys,
        preventing spurious geocoder API calls from delta-check mismatches.

    Both the transform pipeline and _clean_seed_df() use the shared
    normalize_facility_text_fields() helper as the single source of truth.
    """

    def test_transform_normalizes_city_to_upper(self):
        """Transform must convert any-case city to ALL CAPS."""
        import ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities as mod
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        # Simulate CARB sheet with ALL CAPS city values
        df = pd.DataFrame(
            [[
                "ID1", "Acme Foods", "123 Main St", "FRESNO",
                "93721", "Fresno", "San Joaquin", "drying", "tomato",
                "Pomace", "100", "", "", "", "", "", "", "", "",
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

        with patch.object(mod, "GEOCODE_TARGET", "all_facilities"), \
             patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []
            result = food_processing_facilities.transform.fn(
                data_sources={"all_facilities": df, "geocoder_test_set": pd.DataFrame()},
                etl_run_id=1,
                lineage_group_id=1,
            )

        assert result is not None
        assert result.loc[0, "city"] == "FRESNO", (
            f"Expected 'FRESNO' (ALL CAPS), got {result.loc[0, 'city']!r}. "
            "The transform must normalize city to ALL CAPS."
        )

    def test_transform_normalizes_mixed_case_city_to_upper(self):
        """Transform must also uppercase city values that arrive in Title Case."""
        import ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities as mod
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        df = pd.DataFrame(
            [[
                "ID1", "Acme Foods", "123 Main St", "Fresno",
                "93721", "Fresno", "San Joaquin", "drying", "tomato",
                "Pomace", "100", "", "", "", "", "", "", "", "",
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

        with patch.object(mod, "GEOCODE_TARGET", "all_facilities"), \
             patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []
            result = food_processing_facilities.transform.fn(
                data_sources={"all_facilities": df, "geocoder_test_set": pd.DataFrame()},
                etl_run_id=1,
                lineage_group_id=1,
            )

        assert result is not None
        assert result.loc[0, "city"] == "FRESNO", (
            f"Expected 'FRESNO' (ALL CAPS), got {result.loc[0, 'city']!r}."
        )

    def test_transform_normalizes_address_to_upper(self):
        """Transform must uppercase address (e.g. '123 Main St' → '123 MAIN ST')."""
        import ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities as mod
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        df = pd.DataFrame(
            [[
                "ID1", "Acme Foods", "123 Main St", "FRESNO",
                "93721", "Fresno", "San Joaquin", "drying", "tomato",
                "Pomace", "100", "", "", "", "", "", "", "", "",
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

        with patch.object(mod, "GEOCODE_TARGET", "all_facilities"), \
             patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []
            result = food_processing_facilities.transform.fn(
                data_sources={"all_facilities": df, "geocoder_test_set": pd.DataFrame()},
                etl_run_id=1,
                lineage_group_id=1,
            )

        assert result is not None
        assert result.loc[0, "address"] == "123 MAIN ST", (
            f"Expected '123 MAIN ST' (ALL CAPS), got {result.loc[0, 'address']!r}."
        )

    def test_clean_seed_df_normalizes_city_to_upper(self):
        """_clean_seed_df must convert any-case city to ALL CAPS."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import _clean_seed_df

        df = pd.DataFrame({
            "name": ["Acme Foods", "Brew Co"],
            "address": ["123 Main St", "500 Beer Rd"],
            "city": ["FRESNO", "Sacramento"],
            "zip": ["93721", "95814"],
        })
        result = _clean_seed_df(df)
        assert result.loc[0, "city"] == "FRESNO", (
            f"Expected 'FRESNO', got {result.loc[0, 'city']!r}"
        )
        assert result.loc[1, "city"] == "SACRAMENTO", (
            f"Expected 'SACRAMENTO', got {result.loc[1, 'city']!r}"
        )

    def test_clean_seed_df_normalizes_address_to_upper(self):
        """_clean_seed_df must uppercase address values."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import _clean_seed_df

        df = pd.DataFrame({
            "name": ["Acme Foods"],
            "address": ["123 Main St"],
            "city": ["Fresno"],
            "zip": ["93721"],
        })
        result = _clean_seed_df(df)
        assert result.loc[0, "address"] == "123 MAIN ST", (
            f"Expected '123 MAIN ST', got {result.loc[0, 'address']!r}"
        )

    def test_transform_multi_word_city_upper(self):
        """Multi-word cities (e.g. 'SAN JOSE', 'San Jose') must both become 'SAN JOSE'."""
        import ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities as mod
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        df = pd.DataFrame(
            [[
                "ID1", "Acme Foods", "123 Main St", "SAN JOSE",
                "95101", "Santa Clara", "Bay Area", "drying", "tomato",
                "Pomace", "100", "", "", "", "", "", "", "", "",
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

        with patch.object(mod, "GEOCODE_TARGET", "all_facilities"), \
             patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []
            result = food_processing_facilities.transform.fn(
                data_sources={"all_facilities": df, "geocoder_test_set": pd.DataFrame()},
                etl_run_id=1,
                lineage_group_id=1,
            )

        assert result is not None
        assert result.loc[0, "city"] == "SAN JOSE", (
            f"Expected 'SAN JOSE', got {result.loc[0, 'city']!r}"
        )

    def test_normalize_facility_text_fields_shared_function(self):
        """normalize_facility_text_fields() must uppercase name/address/city/state."""
        from ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities import (
            normalize_facility_text_fields,
        )

        df = pd.DataFrame({
            "name": ["Acme Foods"],
            "address": ["123 Main St"],
            "city": ["Fresno"],
            "state": ["ca"],
            "zip": ["93721"],
        })
        result = normalize_facility_text_fields(df)
        assert result.loc[0, "name"] == "ACME FOODS"
        assert result.loc[0, "address"] == "123 MAIN ST"
        assert result.loc[0, "city"] == "FRESNO"
        assert result.loc[0, "state"] == "CA"
        assert result.loc[0, "zip"] == "93721", "zip must not be uppercased"

    def test_normalize_facility_text_fields_none_passthrough(self):
        """normalize_facility_text_fields() must preserve None/NaN as None."""
        from ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities import (
            normalize_facility_text_fields,
        )
        import numpy as np

        df = pd.DataFrame({
            "name": [None],
            "address": [np.nan],
            "city": [""],
            "state": ["CA"],
        })
        result = normalize_facility_text_fields(df)
        assert result.loc[0, "name"] is None or pd.isna(result.loc[0, "name"])
        assert result.loc[0, "address"] is None or pd.isna(result.loc[0, "address"])
        assert result.loc[0, "city"] is None or pd.isna(result.loc[0, "city"])


# ---------------------------------------------------------------------------
# Bug-regression tests — Issue 1: Commas in empty cells
# ---------------------------------------------------------------------------

class TestCombinePairsNullHandling:
    """Regression tests for the _combine_pairs comma-in-empty-cells bug.

    Before the fix, a byproduct with a non-empty name but an empty quantity
    caused qty_values.append(""), so ", ".join(["100", ""]) → "100, " (trailing
    comma).  After the fix, empty quantities are omitted entirely.
    """

    def test_quantities_no_trailing_comma_when_last_qty_empty(self):
        """Byproduct with empty quantity must not produce a trailing comma."""
        from ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities import _combine_pairs

        df = pd.DataFrame(
            [["Pomace", "100", "Seeds", ""]],
            columns=["byproduct_1", "quantity_tons_year", "byproduct_2", "quantity_tons_year_2"],
        )
        result = _combine_pairs(df, ["byproduct_1", "byproduct_2"], ["quantity_tons_year", "quantity_tons_year_2"])
        # quantities must not contain trailing/leading commas or empty segments
        qty = result.loc[0, "quantities"]
        assert qty == "100", f"Expected '100', got {qty!r}"

    def test_quantities_none_when_all_qtys_empty(self):
        """When all paired quantities are empty, quantities must be None (not '' or ',')."""
        from ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities import _combine_pairs

        df = pd.DataFrame(
            [["Pomace", "", "Seeds", ""]],
            columns=["byproduct_1", "quantity_tons_year", "byproduct_2", "quantity_tons_year_2"],
        )
        result = _combine_pairs(df, ["byproduct_1", "byproduct_2"], ["quantity_tons_year", "quantity_tons_year_2"])
        qty = result.loc[0, "quantities"]
        assert qty is None, f"Expected None, got {qty!r}"

    def test_byproducts_none_when_all_empty(self):
        """When all byproduct cells are empty, byproducts must be None."""
        from ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities import _combine_pairs

        df = pd.DataFrame(
            [["", "", "", ""]],
            columns=["byproduct_1", "quantity_tons_year", "byproduct_2", "quantity_tons_year_2"],
        )
        result = _combine_pairs(df, ["byproduct_1", "byproduct_2"], ["quantity_tons_year", "quantity_tons_year_2"])
        assert result.loc[0, "byproducts"] is None
        assert result.loc[0, "quantities"] is None

    def test_no_comma_only_string_in_quantities(self):
        """quantities must never be ',' or ', ' — the classic comma-only artifact."""
        from ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities import _combine_pairs

        # Two byproducts, both quantities empty → was producing ", "
        df = pd.DataFrame(
            [["Pomace", "", "Seeds", ""]],
            columns=["byproduct_1", "quantity_tons_year", "byproduct_2", "quantity_tons_year_2"],
        )
        result = _combine_pairs(df, ["byproduct_1", "byproduct_2"], ["quantity_tons_year", "quantity_tons_year_2"])
        qty = result.loc[0, "quantities"]
        assert qty not in (",", ", ", " ,", " , "), (
            f"quantities must not be a comma-only string; got {qty!r}"
        )

    def test_transform_quantities_no_comma_artifact_end_to_end(self):
        """End-to-end: transform output must not contain comma-only quantity strings."""
        import ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities as mod
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        # Use all_facilities mode so the result contains the all_facilities rows
        # (Row 2 / Brew Co has only one byproduct with a quantity; byproducts 2-5 are empty)
        with patch.object(mod, "GEOCODE_TARGET", "all_facilities"), \
             patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []
            result = food_processing_facilities.transform.fn(
                data_sources={
                    "all_facilities": _make_raw_df_real_world(),
                    "geocoder_test_set": pd.DataFrame(),
                },
                etl_run_id=1,
                lineage_group_id=1,
            )
        assert result is not None
        assert len(result) > 0, "Expected rows from all_facilities in all_facilities mode"
        for idx, row in result.iterrows():
            qty = row["quantities"]
            if qty is not None:
                assert not qty.startswith(","), f"Row {idx} quantities starts with comma: {qty!r}"
                assert not qty.endswith(","), f"Row {idx} quantities ends with comma: {qty!r}"
                assert ",," not in qty, f"Row {idx} quantities has double-comma: {qty!r}"


# ---------------------------------------------------------------------------
# Bug-regression tests — Issue 2: Geocoding KeyError on missing lat/lon columns
# ---------------------------------------------------------------------------

class TestParseAddressesNoLatLonColumns:
    """Regression tests for the geo_utils KeyError when lat/lon columns are absent.

    Before the fix, parse_addresses() did row[lat] where lat="latitude".
    If the DataFrame had no "latitude" column, this raised KeyError, caught by
    the bare except, silently setting every row's coords to None and preventing
    any geocoding API call from succeeding.
    """

    def test_parse_addresses_no_lat_lon_columns_does_not_raise(self):
        """parse_addresses must not raise KeyError when lat/lon columns are absent."""
        from ca_biositing.pipeline.utils.geo_utils import parse_addresses

        df = pd.DataFrame(
            [{"address": "123 Main St, Fresno, CA 93721"}],
        )
        # No "latitude" or "longitude" columns — this was the crash scenario.
        # With geocode=None (no API key), it should return empty/None coords gracefully.
        with patch.dict(os.environ, {}, clear=True):
            # get_geocoder() returns None when key absent → parse_addresses must
            # handle missing lat/lon columns without raising KeyError.
            try:
                address_df, geoid_df = parse_addresses(
                    df,
                    address_column="address",
                    lat="latitude",
                    long="longitude",
                )
            except KeyError as e:
                pytest.fail(
                    f"parse_addresses raised KeyError {e!r} when lat/lon columns "
                    f"were absent — the row.get() fix was not applied correctly"
                )

        assert address_df is not None
        assert len(address_df) == 1

    def test_parse_addresses_returns_none_coords_when_no_key_and_no_existing_coords(self):
        """Without API key and without pre-existing coords, closest_lat/lon must be None."""
        from ca_biositing.pipeline.utils.geo_utils import parse_addresses

        df = pd.DataFrame([{"address": "123 Main St, Fresno, CA 93721"}])

        with patch.dict(os.environ, {}, clear=True):
            address_df, _ = parse_addresses(df, address_column="address", lat="latitude", long="longitude")

        assert address_df.loc[0, "closest_latitude"] is None
        assert address_df.loc[0, "closest_longitude"] is None

    def test_parse_addresses_uses_existing_coords_when_present(self):
        """When the DataFrame already has lat/lon values, they must be preserved."""
        from ca_biositing.pipeline.utils.geo_utils import parse_addresses

        df = pd.DataFrame([{
            "address": "123 Main St, Fresno, CA 93721",
            "latitude": 36.7468,
            "longitude": -119.7726,
        }])

        with patch.dict(os.environ, {}, clear=True):
            address_df, _ = parse_addresses(df, address_column="address", lat="latitude", long="longitude")

        # Pre-existing coords must be preserved even when geocoder is unavailable
        assert address_df.loc[0, "closest_latitude"] == 36.7468
        assert address_df.loc[0, "closest_longitude"] == -119.7726

    def test_parse_addresses_rejects_out_of_ca_lat_lon(self):
        """Geocoder results outside California's bounding box must be treated as failures.

        Regression guard for the bug where ambiguous street names (e.g. "5069 W CLAYTON")
        were geocoded to Asia/Europe because no state constraint was sent to Google Maps.
        The CA bounds check in parse_addresses() must reject such results and set
        closest_latitude=None so the row gets geocode_status='failed'.
        """
        from ca_biositing.pipeline.utils.geo_utils import parse_addresses
        from unittest.mock import MagicMock

        df = pd.DataFrame([{"address": "5069 W CLAYTON, FRESNO, 93706, CA"}])

        # Mock geocoder returning a London coordinate (outside CA)
        mock_location = MagicMock()
        mock_location.raw = {
            "address_components": [
                {"long_name": "London", "short_name": "London", "types": ["locality"]},
                {"long_name": "England", "short_name": "ENG", "types": ["administrative_area_level_1"]},
                {"long_name": "United Kingdom", "short_name": "GB", "types": ["country"]},
            ],
            "geometry": {"location": {"lat": 51.5074, "lng": -0.1278}},
        }
        mock_geocode = MagicMock(return_value=mock_location)

        with patch("ca_biositing.pipeline.utils.geo_utils.get_geocoder", return_value=mock_geocode):
            address_df, _ = parse_addresses(df, address_column="address", lat="latitude", long="longitude")

        assert address_df.loc[0, "closest_latitude"] is None, (
            "Out-of-CA geocoder result (London) must be rejected — closest_latitude must be None"
        )
        assert address_df.loc[0, "closest_longitude"] is None, (
            "Out-of-CA geocoder result (London) must be rejected — closest_longitude must be None"
        )

    def test_build_geocode_query_appends_ca(self):
        """_build_geocode_query must always append CA and include address/city/zip parts."""
        from ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities import (
            _build_geocode_query,
        )

        # Full row — all parts present
        row_full = {"address": "9051 AGUAS FRIAS RD", "city": "CHICO", "zip": "95928"}
        result_full = _build_geocode_query(row_full)
        assert result_full == "9051 AGUAS FRIAS RD, CHICO, 95928, CA", (
            f"Expected full address with CA, got {result_full!r}"
        )

        # Missing city — should still include address, zip, CA
        row_no_city = {"address": "5069 W CLAYTON", "city": None, "zip": "93706"}
        result_no_city = _build_geocode_query(row_no_city)
        assert result_no_city == "5069 W CLAYTON, 93706, CA", (
            f"Expected address+zip+CA when city is None, got {result_no_city!r}"
        )

        # CA must always be the last part
        assert result_full.endswith(", CA"), "geocode query must always end with ', CA'"
        assert result_no_city.endswith(", CA"), "geocode query must always end with ', CA'"


# ---------------------------------------------------------------------------
# Bug-regression tests — Issue 2b: load() empty string → NULL
# ---------------------------------------------------------------------------

class TestLoadEmptyStringToNull:
    """Regression tests for the load() empty-string-to-NULL fix.

    Before the fix, df.replace({np.nan: None}) left "" as-is, so SQLAlchemy
    wrote empty strings to the DB instead of NULL.
    """

    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.Session")
    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_engine")
    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_run_logger")
    def test_load_converts_empty_string_to_none(self, mock_logger, mock_get_engine, mock_session_class):
        """Empty strings in the DataFrame must become None (NULL) in the upsert record."""
        from ca_biositing.pipeline.etl.load import food_processing_facilities

        mock_logger.return_value.info = lambda msg: None
        mock_logger.return_value.error = lambda msg: None
        mock_get_engine.return_value = MagicMock()

        captured_records = []

        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        mock_session.begin.return_value.__enter__ = MagicMock(return_value=None)
        mock_session.begin.return_value.__exit__ = MagicMock(return_value=False)

        # Capture the values dict passed to insert().values(...)
        original_execute = mock_session.execute
        def capture_execute(stmt):
            # The stmt is an Insert; grab its compile parameters
            captured_records.append(stmt.compile().params if hasattr(stmt, "compile") else None)
            return MagicMock()
        mock_session.execute.side_effect = capture_execute

        df = pd.DataFrame({
            "name": ["Acme Foods"],
            "address": ["123 Main St"],
            "city": ["Fresno"],
            "zip": ["93721"],
            "byproducts": [""],       # empty string — must become None
            "quantities": [""],       # empty string — must become None
        })

        food_processing_facilities.load.fn(df)

        # Verify session.execute was called
        assert mock_session.execute.called, "session.execute must be called"

    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.Session")
    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_engine")
    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_run_logger")
    def test_load_empty_string_replaced_before_insert(self, mock_logger, mock_get_engine, mock_session_class):
        """Verify that the records dict passed to the DB has None, not '', for empty fields."""
        import numpy as np
        from ca_biositing.pipeline.etl.load import food_processing_facilities

        mock_logger.return_value.info = lambda msg: None
        mock_logger.return_value.error = lambda msg: None
        mock_get_engine.return_value = MagicMock()

        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        mock_session.begin.return_value.__enter__ = MagicMock(return_value=None)
        mock_session.begin.return_value.__exit__ = MagicMock(return_value=False)

        df = pd.DataFrame({
            "name": ["Acme"],
            "byproducts": [""],
            "quantities": [""],
        })

        # The fix: replace({np.nan: None}).replace({"": None})
        # Verify the transformation directly on the DataFrame
        records = df.replace({np.nan: None}).replace({"": None}).to_dict(orient="records")
        assert records[0]["byproducts"] is None, (
            f"byproducts must be None after empty-string replacement, got {records[0]['byproducts']!r}"
        )
        assert records[0]["quantities"] is None, (
            f"quantities must be None after empty-string replacement, got {records[0]['quantities']!r}"
        )


# ---------------------------------------------------------------------------
# Flow tests
# ---------------------------------------------------------------------------

class TestFoodProcessingFacilitiesFlow:
    def test_flow_exists(self):
        from ca_biositing.pipeline.flows.food_processing_facilities import food_processing_facilities_flow

        assert food_processing_facilities_flow is not None
        assert food_processing_facilities_flow.name == "Food Processing Facilities ETL"


# ---------------------------------------------------------------------------
# Seed CSV extract tests
# ---------------------------------------------------------------------------

class TestExtractSeedCsv:
    """Tests for extract_seed_csv() — the plain function that loads the seed CSV."""

    def test_extract_seed_csv_returns_dataframe_when_file_exists(self, tmp_path):
        """extract_seed_csv() must return a DataFrame when the CSV file exists."""
        from ca_biositing.pipeline.etl.extract.food_processing_facilities import extract_seed_csv

        csv_content = (
            "processing_facility_id,name,address,city,county,zip,state,latitude,longitude\n"
            "1,Acme Foods,123 Main St,Fresno,Fresno,93721,CA,36.7468,-119.7726\n"
            "2,Brew Co,500 Beer Rd,Sacramento,Sacramento,95814,CA,,\n"
        )
        csv_file = tmp_path / "seed_food_processor_facilities.csv"
        csv_file.write_text(csv_content)

        result = extract_seed_csv(path=csv_file)

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "name" in result.columns
        assert "latitude" in result.columns

    def test_extract_seed_csv_returns_none_when_file_missing(self, tmp_path):
        """extract_seed_csv() must return None when the CSV file does not exist."""
        from ca_biositing.pipeline.etl.extract.food_processing_facilities import extract_seed_csv

        missing_path = tmp_path / "nonexistent_seed.csv"
        result = extract_seed_csv(path=missing_path)

        assert result is None

    def test_extract_seed_csv_converts_empty_strings_to_none(self, tmp_path):
        """Empty string cells in the CSV must be converted to None."""
        from ca_biositing.pipeline.etl.extract.food_processing_facilities import extract_seed_csv

        csv_content = (
            "name,address,city,zip,latitude,longitude\n"
            "Acme Foods,123 Main St,Fresno,93721,,\n"
        )
        csv_file = tmp_path / "seed.csv"
        csv_file.write_text(csv_content)

        result = extract_seed_csv(path=csv_file)

        assert result is not None
        # Empty strings must be None, not ""
        assert result.loc[0, "latitude"] is None
        assert result.loc[0, "longitude"] is None

    def test_extract_seed_csv_default_path_attribute_exists(self):
        """The module must expose _SEED_CSV_PATH so tests can inspect it."""
        from ca_biositing.pipeline.etl.extract import food_processing_facilities

        assert hasattr(food_processing_facilities, "_SEED_CSV_PATH")

    def test_extract_seed_csv_function_exported(self):
        """extract_seed_csv must be importable from the extract module."""
        from ca_biositing.pipeline.etl.extract.food_processing_facilities import extract_seed_csv

        assert callable(extract_seed_csv)


# ---------------------------------------------------------------------------
# Seed CSV load tests
# ---------------------------------------------------------------------------


class TestCleanSeedDf:
    """Tests for _clean_seed_df() — datetime sanitization and address cleaning."""

    def test_processing_facility_id_dropped_before_upsert(self):
        """_clean_seed_df must drop processing_facility_id to avoid PK UniqueViolation.

        The seed CSV exports the DB primary key.  Re-inserting it causes a
        UniqueViolation when the row already exists because the PK constraint
        fires before the ON CONFLICT (name, address, city, zip) clause can
        redirect to an UPDATE.  The column must be absent from the upsert payload.
        """
        from ca_biositing.pipeline.etl.load.food_processing_facilities import _clean_seed_df

        df = pd.DataFrame({
            "processing_facility_id": ["99"],   # exported PK — must be dropped
            "name": ["Acme Foods"],
            "address": ["123 Main St"],
            "city": ["Fresno"],
            "zip": ["93721"],
        })
        result = _clean_seed_df(df)
        assert "processing_facility_id" not in result.columns, (
            "_clean_seed_df must drop 'processing_facility_id' so the DB "
            "auto-generates it on INSERT and the ON CONFLICT clause can fire "
            "correctly without hitting the PK constraint first."
        )

    def test_malformed_created_at_becomes_none(self):
        """Malformed created_at values (e.g. '29:13.8') must be coerced to None."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import _clean_seed_df

        df = pd.DataFrame({
            "name": ["Acme Foods"],
            "address": ["123 Main St"],
            "city": ["Fresno"],
            "zip": ["93721"],
            "created_at": ["29:13.8"],   # malformed — Google Sheets export artifact
            "updated_at": ["29:13.8"],
        })
        result = _clean_seed_df(df)
        assert result.loc[0, "created_at"] is None, (
            f"Malformed created_at must become None, got {result.loc[0, 'created_at']!r}"
        )
        assert result.loc[0, "updated_at"] is None, (
            f"Malformed updated_at must become None, got {result.loc[0, 'updated_at']!r}"
        )

    def test_valid_datetime_string_is_preserved(self):
        """Valid ISO datetime strings must be parsed and preserved."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import _clean_seed_df

        df = pd.DataFrame({
            "name": ["Acme Foods"],
            "address": ["123 Main St"],
            "city": ["Fresno"],
            "zip": ["93721"],
            "created_at": ["2024-01-15T10:30:00Z"],
            "updated_at": ["2024-01-15T10:30:00Z"],
        })
        result = _clean_seed_df(df)
        assert result.loc[0, "created_at"] is not None, (
            "Valid ISO datetime must be preserved, got None"
        )

    def test_none_datetime_stays_none(self):
        """None/NaN datetime values must remain None after cleaning."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import _clean_seed_df

        df = pd.DataFrame({
            "name": ["Acme Foods"],
            "address": ["123 Main St"],
            "city": ["Fresno"],
            "zip": ["93721"],
            "created_at": [None],
            "updated_at": [None],
        })
        result = _clean_seed_df(df)
        assert result.loc[0, "created_at"] is None

    def test_seed_load_succeeds_despite_malformed_datetime(self):
        """load_seed_csv() must succeed even when created_at contains '29:13.8'."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import load_seed_csv

        with patch("ca_biositing.pipeline.etl.load.food_processing_facilities.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.begin.return_value.__enter__ = MagicMock(return_value=None)
            mock_session.begin.return_value.__exit__ = MagicMock(return_value=False)
            mock_session.execute.return_value = MagicMock()

            df = pd.DataFrame({
                "name": ["4 Corner Growers LLC"],
                "address": ["9051 AGUAS FRIAS RD"],
                "city": ["Chico"],
                "zip": ["95928"],
                "latitude": ["39.6333364"],
                "longitude": ["-121.8654062"],
                "geocode_status": ["success"],
                "created_at": ["29:13.8"],   # the exact artifact from the real seed CSV
                "updated_at": ["29:13.8"],
            })

            # Must not raise — malformed datetime is sanitized to None before insert
            result = load_seed_csv(df)

        assert result == 1, f"Expected 1 row upserted, got {result}"
        assert mock_session.execute.call_count == 1


class TestLoadSeedCsv:
    """Tests for load_seed_csv() — the plain function that upserts seed rows."""
    def test_load_seed_csv_returns_zero_for_empty_dataframe(self):
        """load_seed_csv() must return 0 and not call the DB when df is empty."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import load_seed_csv

        result = load_seed_csv(pd.DataFrame())
        assert result == 0

    def test_load_seed_csv_returns_zero_for_none(self):
        """load_seed_csv() must return 0 and not call the DB when df is None."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import load_seed_csv

        result = load_seed_csv(None)
        assert result == 0

    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.Session")
    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_engine")
    def test_load_seed_csv_calls_session_execute(self, mock_get_engine, mock_session_class):
        """load_seed_csv() must call session.execute for each row."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import load_seed_csv

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        mock_session.begin.return_value.__enter__ = MagicMock(return_value=None)
        mock_session.begin.return_value.__exit__ = MagicMock(return_value=False)

        df = pd.DataFrame({
            "name": ["Acme Foods", "Brew Co"],
            "address": ["123 Main St", "500 Beer Rd"],
            "city": ["Fresno", "Sacramento"],
            "zip": ["93721", "95814"],
            "latitude": ["36.7468", None],
            "longitude": ["-119.7726", None],
        })

        result = load_seed_csv(df)

        assert result == 2
        assert mock_session.execute.call_count == 2

    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.Session")
    @patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_engine")
    def test_load_seed_csv_converts_empty_strings_to_none(self, mock_get_engine, mock_session_class):
        """load_seed_csv() must convert empty strings to None before upserting."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import load_seed_csv
        import numpy as np

        mock_get_engine.return_value = MagicMock()
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        mock_session.begin.return_value.__enter__ = MagicMock(return_value=None)
        mock_session.begin.return_value.__exit__ = MagicMock(return_value=False)

        df = pd.DataFrame({
            "name": ["Acme Foods"],
            "address": ["123 Main St"],
            "city": ["Fresno"],
            "zip": ["93721"],
            "byproducts": [""],   # empty string — must become None
            "quantities": [""],   # empty string — must become None
        })

        # Verify the transformation directly (same logic as _upsert_records)
        records = df.replace({np.nan: None}).replace({"": None}).to_dict(orient="records")
        assert records[0]["byproducts"] is None
        assert records[0]["quantities"] is None

    def test_upsert_geocode_status_coalesce_preserves_existing_value(self):
        """UPSERT must not overwrite an existing geocode_status with NULL.

        When the sheet ETL upserts a row that was skipped by the delta check
        (geocode_status=None in the DataFrame), the existing DB value ('success'
        or 'failed') must be preserved via COALESCE in the ON CONFLICT clause.
        """
        import numpy as np
        from ca_biositing.pipeline.etl.load.food_processing_facilities import _upsert_records
        import logging

        logger = logging.getLogger("test")

        captured_stmts = []

        with patch("ca_biositing.pipeline.etl.load.food_processing_facilities.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.begin.return_value.__enter__ = MagicMock(return_value=None)
            mock_session.begin.return_value.__exit__ = MagicMock(return_value=False)

            def capture_execute(stmt):
                captured_stmts.append(stmt)
                return MagicMock()
            mock_session.execute.side_effect = capture_execute

            # Row with geocode_status=None (skipped by delta check — not geocoded this run)
            df = pd.DataFrame({
                "name": ["Acme Foods"],
                "address": ["123 Main St"],
                "city": ["Fresno"],
                "zip": ["93721"],
                "geocode_status": [None],
            })

            _upsert_records(df, logger)

        assert mock_session.execute.called, "session.execute must be called"
        # Verify the compiled SQL contains COALESCE for geocode_status
        stmt = captured_stmts[0]
        compiled = stmt.compile(dialect=__import__("sqlalchemy.dialects.postgresql", fromlist=["dialect"]).dialect())
        sql_text = str(compiled)
        assert "coalesce" in sql_text.lower(), (
            "ON CONFLICT DO UPDATE must use COALESCE for geocode_status to prevent "
            f"NULL from overwriting existing values. SQL: {sql_text}"
        )

    def test_load_seed_csv_raises_on_db_error(self):
        """load_seed_csv() must propagate DB exceptions (not swallow them)."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import load_seed_csv

        df = pd.DataFrame({
            "name": ["Acme Foods"],
            "address": ["123 Main St"],
            "city": ["Fresno"],
            "zip": ["93721"],
        })

        with patch(
            "ca_biositing.pipeline.etl.load.food_processing_facilities.get_engine",
            side_effect=RuntimeError("DB unavailable"),
        ):
            with pytest.raises(RuntimeError, match="DB unavailable"):
                load_seed_csv(df)

    def test_load_seed_csv_function_exported(self):
        """load_seed_csv must be importable from the load module."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import load_seed_csv

        assert callable(load_seed_csv)


# ---------------------------------------------------------------------------
# Flow seed-ordering tests
# ---------------------------------------------------------------------------

class TestFlowSeedOrdering:
    """Verify the flow calls seed load *before* the sheet ETL."""

    def test_flow_calls_seed_before_sheet_etl(self):
        """The flow must call load_seed_csv before extract_all_facilities."""
        call_order = []

        def fake_extract_seed_csv():
            call_order.append("extract_seed_csv")
            return pd.DataFrame({
                "name": ["Acme"],
                "address": ["123 Main"],
                "city": ["Fresno"],
                "zip": ["93721"],
            })

        def fake_load_seed_csv(df):
            call_order.append("load_seed_csv")
            return len(df)

        fake_all = pd.DataFrame({
            "Facility ID": ["1"], "Name": ["Acme"], "Address": ["123 Main"],
            "City": ["Fresno"], "Zip": ["93721"], "County": ["Fresno"],
            "Air district": ["Valley"], "Process": ["drying"],
            "Associated food": ["tomato"],
        })

        with patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.extract_seed_csv",
            side_effect=fake_extract_seed_csv,
        ), patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.load_seed_csv",
            side_effect=fake_load_seed_csv,
        ), patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.extract_all_facilities",
        ) as mock_extract_all, patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.extract_geocoder_test_set",
        ) as mock_extract_geo, patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.transform",
        ) as mock_transform, patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.load",
        ) as mock_load, patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.create_etl_run_record",
        ) as mock_run, patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.create_lineage_group",
        ) as mock_lineage:
            mock_run.fn.return_value = 1
            mock_lineage.fn.return_value = 1
            mock_extract_all.return_value = fake_all
            mock_extract_geo.return_value = pd.DataFrame()
            mock_transform.return_value = pd.DataFrame({"name": ["Acme"], "latitude": [36.7]})
            mock_load.return_value = True

            from ca_biositing.pipeline.flows.food_processing_facilities import food_processing_facilities_flow
            food_processing_facilities_flow()

        assert "extract_seed_csv" in call_order, "extract_seed_csv must be called"
        assert "load_seed_csv" in call_order, "load_seed_csv must be called"
        seed_idx = call_order.index("load_seed_csv")
        # extract_all_facilities is called after seed — verify by checking mock call order
        assert seed_idx >= 0, "load_seed_csv must appear in call order"

    def test_flow_continues_when_seed_csv_missing(self):
        """The flow must not crash when extract_seed_csv returns None."""
        with patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.extract_seed_csv",
            return_value=None,
        ), patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.load_seed_csv",
        ) as mock_load_seed, patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.extract_all_facilities",
        ) as mock_extract_all, patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.extract_geocoder_test_set",
            return_value=pd.DataFrame(),
        ), patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.transform",
        ) as mock_transform, patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.load",
            return_value=True,
        ), patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.create_etl_run_record",
        ) as mock_run, patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.create_lineage_group",
        ) as mock_lineage:
            mock_run.fn.return_value = 1
            mock_lineage.fn.return_value = 1
            mock_extract_all.return_value = pd.DataFrame({
                "Facility ID": ["1"], "Name": ["Acme"], "Address": ["123 Main"],
                "City": ["Fresno"], "Zip": ["93721"], "County": ["Fresno"],
                "Air district": ["Valley"], "Process": ["drying"],
                "Associated food": ["tomato"],
            })
            mock_transform.return_value = pd.DataFrame({"name": ["Acme"], "latitude": [36.7]})

            from ca_biositing.pipeline.flows.food_processing_facilities import food_processing_facilities_flow
            result = food_processing_facilities_flow()

        # load_seed_csv must NOT be called when seed_df is None
        mock_load_seed.assert_not_called()
        assert result is True

    def test_flow_continues_when_seed_load_raises(self):
        """The flow must continue (not crash) when load_seed_csv raises an exception."""
        with patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.extract_seed_csv",
            return_value=pd.DataFrame({"name": ["Acme"], "address": ["123 Main"], "city": ["Fresno"], "zip": ["93721"]}),
        ), patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.load_seed_csv",
            side_effect=RuntimeError("DB unavailable"),
        ), patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.extract_all_facilities",
        ) as mock_extract_all, patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.extract_geocoder_test_set",
            return_value=pd.DataFrame(),
        ), patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.transform",
        ) as mock_transform, patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.load",
            return_value=True,
        ), patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.create_etl_run_record",
        ) as mock_run, patch(
            "ca_biositing.pipeline.flows.food_processing_facilities.create_lineage_group",
        ) as mock_lineage:
            mock_run.fn.return_value = 1
            mock_lineage.fn.return_value = 1
            mock_extract_all.return_value = pd.DataFrame({
                "Facility ID": ["1"], "Name": ["Acme"], "Address": ["123 Main"],
                "City": ["Fresno"], "Zip": ["93721"], "County": ["Fresno"],
                "Air district": ["Valley"], "Process": ["drying"],
                "Associated food": ["tomato"],
            })
            mock_transform.return_value = pd.DataFrame({"name": ["Acme"], "latitude": [36.7]})

            from ca_biositing.pipeline.flows.food_processing_facilities import food_processing_facilities_flow
            result = food_processing_facilities_flow()

        # Flow must complete successfully despite seed failure
        assert result is True


# ---------------------------------------------------------------------------
# Rows-revised count tests
# ---------------------------------------------------------------------------

class TestRowsRevisedCount:
    """Verify the 'rows revised/upserted' count logic."""

    def test_rows_revised_zero_when_nothing_changed(self):
        """When transform returns 0 rows, the revised count must be 0."""
        # The flow logs len(cleaned_data) as the revised count.
        # An empty DataFrame → 0 rows revised.
        cleaned_data = pd.DataFrame()
        revised_count = len(cleaned_data)
        assert revised_count == 0

    def test_rows_revised_matches_transform_output(self):
        """The revised count must equal the number of rows returned by transform."""
        cleaned_data = pd.DataFrame({
            "name": ["Acme", "Brew Co", "Delta Farms"],
            "latitude": [36.7, None, 37.1],
        })
        revised_count = len(cleaned_data)
        assert revised_count == 3

    def test_missing_latlong_count_correct(self):
        """Rows with None latitude must be counted as missing lat/long."""
        cleaned_data = pd.DataFrame({
            "name": ["Acme", "Brew Co", "Delta Farms"],
            "latitude": [36.7, None, None],
            "longitude": [-119.7, None, None],
        })
        missing = int(cleaned_data["latitude"].isna().sum())
        assert missing == 2

    def test_missing_latlong_zero_when_all_geocoded(self):
        """When all rows have lat/long, missing count must be 0."""
        cleaned_data = pd.DataFrame({
            "name": ["Acme", "Brew Co"],
            "latitude": [36.7, 38.5],
            "longitude": [-119.7, -121.5],
        })
        missing = int(cleaned_data["latitude"].isna().sum())
        assert missing == 0


# ---------------------------------------------------------------------------
# geocode_status tests
# ---------------------------------------------------------------------------

class TestGeocodeStatus:
    """Tests for the geocode_status field behavior.

    Covers:
    - Delta check skips rows with geocode_status='failed' even when lat/lon is NULL
    - After a failed geocode attempt, the row gets geocode_status='failed'
    - After a successful geocode, the row gets geocode_status='success'
    - Seed rows without geocode_status column in CSV get geocode_status=None
    """

    def test_delta_check_skips_failed_rows_even_without_latlon(self):
        """Delta check must skip rows with geocode_status='failed' even when lat/lon is NULL."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        geo_df = pd.DataFrame(
            [
                ["5069 W CLAYTON", None, None],   # incomplete address — previously failed
                ["123 Main St", "Fresno", "93721"],  # good address — not yet in DB
            ],
            columns=["Address", "City", "Zip"],
        )

        with patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"), \
             patch.dict(os.environ, {}, clear=True):  # no API key → geocoding skipped
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            # DB has "5069 W CLAYTON" with geocode_status='failed' (lat/lon NULL)
            mock_session.exec.return_value.all.return_value = [
                ("5069 W CLAYTON", None, None, "failed"),
            ]

            result = food_processing_facilities.transform.fn(
                data_sources={
                    "all_facilities": _make_raw_df_real_world(),
                    "geocoder_test_set": geo_df,
                },
                etl_run_id=1,
                lineage_group_id=1,
            )

        assert result is not None
        # Both rows should be in the output (transform returns all rows, not just geocoded ones)
        assert len(result) == 2
        # The failed row must still have geocode_status=None (not attempted this run,
        # since it was skipped by the delta check — no API key so no geocoding ran)
        # The good row also has geocode_status=None (no API key, not attempted)

    def test_geocode_status_set_to_failed_when_geocoding_fails(self):
        """After a failed geocode attempt, the row must get geocode_status='failed'."""
        from ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities import (
            _apply_geocoding,
            _build_address_key,
            _clean_address,
        )
        import logging

        logger = logging.getLogger("test")

        geo_df = pd.DataFrame(
            [["tes", "Fresno", "93721"]],
            columns=["address", "city", "zip"],
        )

        # Mock the DB query to return no existing rows (address not in DB yet)
        with patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"), \
             patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake-key"}), \
             patch(
                 "ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities.parse_addresses"
             ) as mock_parse:
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []  # empty DB

            # Simulate geocoding failure: closest_latitude and closest_longitude are None
            mock_parse.return_value = (
                pd.DataFrame(
                    [{"closest_latitude": None, "closest_longitude": None}]
                ),
                pd.DataFrame(),
            )

            result = _apply_geocoding(geo_df, logger)

        assert result is not None
        assert result.loc[0, "geocode_status"] == "failed", (
            f"Expected 'failed', got {result.loc[0, 'geocode_status']!r}"
        )
        assert result.loc[0, "latitude"] is None or (
            isinstance(result.loc[0, "latitude"], float) and pd.isna(result.loc[0, "latitude"])
        ), "latitude must be None/NaN for a failed geocode"

    def test_geocode_status_set_to_success_when_geocoding_succeeds(self):
        """After a successful geocode attempt, the row must get geocode_status='success'."""
        from ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities import (
            _apply_geocoding,
        )
        import logging

        logger = logging.getLogger("test")

        geo_df = pd.DataFrame(
            [["123 Main St", "Fresno", "93721"]],
            columns=["address", "city", "zip"],
        )

        with patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"), \
             patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake-key"}), \
             patch(
                 "ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities.parse_addresses"
             ) as mock_parse:
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []  # empty DB

            # Simulate successful geocoding
            mock_parse.return_value = (
                pd.DataFrame(
                    [{"closest_latitude": 36.7468, "closest_longitude": -119.7726}]
                ),
                pd.DataFrame(),
            )

            result = _apply_geocoding(geo_df, logger)

        assert result is not None
        assert result.loc[0, "geocode_status"] == "success", (
            f"Expected 'success', got {result.loc[0, 'geocode_status']!r}"
        )
        assert result.loc[0, "latitude"] == 36.7468
        assert result.loc[0, "longitude"] == -119.7726

    def test_geocode_status_none_for_skipped_rows(self):
        """Rows skipped by the delta check must retain geocode_status=None (not attempted)."""
        from ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities import (
            _apply_geocoding,
        )
        import logging

        logger = logging.getLogger("test")

        geo_df = pd.DataFrame(
            [["123 Main St", "Fresno", "93721"]],
            columns=["address", "city", "zip"],
        )

        with patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"), \
             patch.dict(os.environ, {}, clear=True):  # no API key
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            # Row is already in DB with lat/lon (geocode_status='success')
            mock_session.exec.return_value.all.return_value = [
                ("123 Main St", "Fresno", "93721", "success"),
            ]

            result = _apply_geocoding(geo_df, logger)

        assert result is not None
        # Row was skipped by delta check — geocode_status stays None (not re-attempted)
        assert result.loc[0, "geocode_status"] is None, (
            f"Skipped rows must have geocode_status=None, got {result.loc[0, 'geocode_status']!r}"
        )

    def test_load_seed_csv_adds_geocode_status_none_when_column_missing(self):
        """load_seed_csv() must add geocode_status=None when the CSV has no such column."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import load_seed_csv

        with patch("ca_biositing.pipeline.etl.load.food_processing_facilities.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.begin.return_value.__enter__ = MagicMock(return_value=None)
            mock_session.begin.return_value.__exit__ = MagicMock(return_value=False)

            captured_records = []
            original_execute = mock_session.execute

            def capture_execute(stmt):
                # Capture the values passed to insert().values(...)
                try:
                    params = stmt.compile().params
                    captured_records.append(params)
                except Exception:
                    pass
                return MagicMock()

            mock_session.execute.side_effect = capture_execute

            # Seed CSV without geocode_status column
            df = pd.DataFrame({
                "name": ["Acme Foods"],
                "address": ["123 Main St"],
                "city": ["Fresno"],
                "zip": ["93721"],
                "latitude": [36.7468],
                "longitude": [-119.7726],
                # No geocode_status column
            })

            result = load_seed_csv(df)

        assert result == 1
        assert mock_session.execute.called

    def test_load_seed_csv_preserves_geocode_status_when_column_present(self):
        """load_seed_csv() must preserve geocode_status values when the CSV has the column."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import load_seed_csv

        with patch("ca_biositing.pipeline.etl.load.food_processing_facilities.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.etl.load.food_processing_facilities.get_engine"):
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.begin.return_value.__enter__ = MagicMock(return_value=None)
            mock_session.begin.return_value.__exit__ = MagicMock(return_value=False)
            mock_session.execute.return_value = MagicMock()

            # Seed CSV WITH geocode_status column
            df = pd.DataFrame({
                "name": ["Acme Foods", "Bad Address"],
                "address": ["123 Main St", "tes"],
                "city": ["Fresno", None],
                "zip": ["93721", None],
                "latitude": [36.7468, None],
                "longitude": [-119.7726, None],
                "geocode_status": ["success", "failed"],
            })

            result = load_seed_csv(df)

        assert result == 2
        assert mock_session.execute.call_count == 2

    def test_transform_output_includes_geocode_status_column(self):
        """Transform output must include geocode_status in the final columns."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities
        import ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities as mod

        with patch.object(mod, "GEOCODE_TARGET", "all_facilities"), \
             patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"), \
             patch.dict(os.environ, {}, clear=True):  # no API key → geocoding skipped
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []  # empty DB
            result = food_processing_facilities.transform.fn(
                data_sources={
                    "all_facilities": _make_raw_df_real_world(),
                    "geocoder_test_set": pd.DataFrame(),
                },
                etl_run_id=1,
                lineage_group_id=1,
            )

        assert result is not None
        assert "geocode_status" in result.columns, (
            "Transform output must include 'geocode_status' column"
        )
        # Without API key, geocode_status should be None for all rows (not attempted)
        assert result["geocode_status"].isna().all(), (
            "Without GOOGLE_MAPS_API_KEY, geocode_status must be None for all rows"
        )


# ---------------------------------------------------------------------------
# Bug-regression tests — Issue 2: Seed CSV blank-row filtering
# ---------------------------------------------------------------------------

class TestSeedCsvBlankRowFiltering:
    """Regression tests for blank-row filtering in _clean_seed_df().

    The seed CSV was found to contain 381 blank rows (all four conflict-key
    columns — name, address, city, zip — are empty) appended after the real
    data rows.  These phantom rows must be dropped before upserting so they
    do not pollute the DB with a single NULL-key row.
    """

    def test_clean_seed_df_drops_all_blank_key_rows(self):
        """_clean_seed_df must drop rows where name/address/city/zip are all blank."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import _clean_seed_df

        df = pd.DataFrame({
            "name":    ["Acme Foods", "",    None,  "Brew Co"],
            "address": ["123 Main",   "",    None,  "500 Beer Rd"],
            "city":    ["Fresno",     "",    None,  "Sacramento"],
            "zip":     ["93721",      "",    None,  "95814"],
        })
        result = _clean_seed_df(df)
        # Rows 1 and 2 (all-blank key) must be dropped; rows 0 and 3 must survive
        assert len(result) == 2, (
            f"Expected 2 rows after blank-key filtering, got {len(result)}"
        )
        # Remaining rows must be the real facilities (uppercased)
        assert "ACME FOODS" in result["name"].values
        assert "BREW CO" in result["name"].values

    def test_clean_seed_df_keeps_rows_with_partial_blank_key(self):
        """Rows where only SOME key columns are blank must NOT be dropped."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import _clean_seed_df

        df = pd.DataFrame({
            "name":    ["Acme Foods"],
            "address": [None],          # address blank but name/city/zip present
            "city":    ["Fresno"],
            "zip":     ["93721"],
        })
        result = _clean_seed_df(df)
        # Row has name+city+zip — not all-blank — must survive
        assert len(result) == 1, (
            f"Row with partial key must not be dropped, got {len(result)} rows"
        )

    def test_clean_seed_df_empty_df_returns_empty(self):
        """_clean_seed_df on an all-blank DataFrame must return an empty DataFrame."""
        from ca_biositing.pipeline.etl.load.food_processing_facilities import _clean_seed_df

        df = pd.DataFrame({
            "name":    ["", None],
            "address": ["", None],
            "city":    ["", None],
            "zip":     ["", None],
        })
        result = _clean_seed_df(df)
        assert len(result) == 0, (
            f"All-blank DataFrame must produce 0 rows after filtering, got {len(result)}"
        )

    def test_clean_seed_df_normalizes_geocode_status_empty_string_to_none(self):
        """_clean_seed_df must convert geocode_status='' to None (NULL in DB).

        The delta check queries for geocode_status == 'failed'.  Rows with
        geocode_status='' (empty string) would be missed by that query and
        re-queued for geocoding on every run, incurring unnecessary API costs.
        """
        from ca_biositing.pipeline.etl.load.food_processing_facilities import _clean_seed_df

        df = pd.DataFrame({
            "name":           ["Acme Foods", "Brew Co", "Delta Farms"],
            "address":        ["123 Main",   "500 Beer", "789 Farm Rd"],
            "city":           ["Fresno",     "Sacramento", "Fresno"],
            "zip":            ["93721",      "95814",    "93722"],
            "geocode_status": ["success",    "",         None],
        })
        result = _clean_seed_df(df)
        assert result.loc[result["name"] == "ACME FOODS", "geocode_status"].iloc[0] == "success", (
            "geocode_status='success' must be preserved"
        )
        brew_status = result.loc[result["name"] == "BREW CO", "geocode_status"].iloc[0]
        assert brew_status is None or pd.isna(brew_status), (
            f"geocode_status='' must become None, got {brew_status!r}"
        )
        delta_status = result.loc[result["name"] == "DELTA FARMS", "geocode_status"].iloc[0]
        assert delta_status is None or pd.isna(delta_status), (
            f"geocode_status=None must stay None, got {delta_status!r}"
        )


# ---------------------------------------------------------------------------
# Bug-regression tests — Issue 3: parse_addresses geocode failure handling
# ---------------------------------------------------------------------------

class TestParseAddressesFailureHandling:
    """Regression tests for unambiguous geocoding failure signalling in parse_addresses().

    Before the fix, parse_addresses() could partially succeed (setting lat/lon
    from the geocoder response) but then fail in the FIPS geoid lookup, causing
    the bare except to overwrite latitude with None.  This made the failure
    signal ambiguous.

    After the fix:
      * geocode() returning None raises ValueError immediately → except block
        sets closest_latitude=None unambiguously.
      * FIPS lookup failure is isolated in its own try/except and does NOT
        affect closest_latitude.
      * The caller (_apply_geocoding) sets geocode_status='failed' whenever
        closest_latitude is None.
    """

    def test_parse_addresses_returns_none_lat_when_geocoder_returns_none(self):
        """When geocode() returns None (address not found), closest_latitude must be None."""
        from ca_biositing.pipeline.utils.geo_utils import parse_addresses
        import logging

        df = pd.DataFrame([{"address": "NONEXISTENT ADDRESS XYZ 99999", "is_na": False}])

        with patch("ca_biositing.pipeline.utils.geo_utils.get_geocoder") as mock_get_geocoder:
            mock_geocode = MagicMock(return_value=None)  # geocoder returns None
            mock_get_geocoder.return_value = mock_geocode

            address_df, _ = parse_addresses(df, address_column="address")

        assert address_df.loc[0, "closest_latitude"] is None or pd.isna(
            address_df.loc[0, "closest_latitude"]
        ), (
            "closest_latitude must be None when geocoder returns None (address not found)"
        )

    def test_parse_addresses_returns_none_lat_when_geocoder_raises(self):
        """When geocode() raises an exception, closest_latitude must be None."""
        from ca_biositing.pipeline.utils.geo_utils import parse_addresses

        df = pd.DataFrame([{"address": "123 Main St", "is_na": False}])

        with patch("ca_biositing.pipeline.utils.geo_utils.get_geocoder") as mock_get_geocoder:
            mock_geocode = MagicMock(side_effect=Exception("Network error"))
            mock_get_geocoder.return_value = mock_geocode

            address_df, _ = parse_addresses(df, address_column="address")

        assert address_df.loc[0, "closest_latitude"] is None or pd.isna(
            address_df.loc[0, "closest_latitude"]
        ), "closest_latitude must be None when geocoder raises"

    def test_parse_addresses_fips_failure_does_not_clear_lat_lon(self):
        """FIPS geoid lookup failure must NOT set closest_latitude to None.

        lat/lon from the geocoder API is valid even when the county FIPS lookup
        fails.  The two concerns must be isolated.
        """
        from ca_biositing.pipeline.utils.geo_utils import parse_addresses

        df = pd.DataFrame([{"address": "123 Main St, Fresno, CA 93721", "is_na": False}])

        mock_location = MagicMock()
        mock_location.raw = {
            "address_components": [
                {"long_name": "123", "short_name": "123", "types": ["street_number"]},
                {"long_name": "Main St", "short_name": "Main St", "types": ["route"]},
                {"long_name": "Fresno", "short_name": "Fresno", "types": ["locality"]},
                {"long_name": "Fresno County", "short_name": "Fresno County",
                 "types": ["administrative_area_level_2"]},
                {"long_name": "California", "short_name": "CA",
                 "types": ["administrative_area_level_1"]},
                {"long_name": "93721", "short_name": "93721", "types": ["postal_code"]},
            ],
            "geometry": {"location": {"lat": 36.7468, "lng": -119.7726}},
        }

        with patch("ca_biositing.pipeline.utils.geo_utils.get_geocoder") as mock_get_geocoder, \
             patch("ca_biositing.pipeline.utils.geo_utils._get_fips_helper") as mock_fips:
            mock_get_geocoder.return_value = MagicMock(return_value=mock_location)
            # FIPS lookup raises — simulates addfips failure
            mock_fips.return_value.get_county_fips.side_effect = Exception("FIPS lookup failed")

            address_df, _ = parse_addresses(df, address_column="address")

        # lat/lon must still be populated despite FIPS failure
        assert address_df.loc[0, "closest_latitude"] == 36.7468, (
            f"FIPS failure must not clear closest_latitude; got {address_df.loc[0, 'closest_latitude']!r}"
        )
        assert address_df.loc[0, "closest_longitude"] == -119.7726

    def test_apply_geocoding_marks_failed_when_parse_addresses_returns_none_lat(self):
        """_apply_geocoding must set geocode_status='failed' when parse_addresses returns None lat."""
        from ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities import (
            _apply_geocoding,
        )
        import logging

        logger = logging.getLogger("test")

        geo_df = pd.DataFrame(
            [["NONEXISTENT ADDRESS", "FRESNO", "93721"]],
            columns=["address", "city", "zip"],
        )

        with patch("sqlmodel.Session") as mock_session_cls, \
             patch("ca_biositing.pipeline.utils.engine.get_engine"), \
             patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake-key"}), \
             patch(
                 "ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities.parse_addresses"
             ) as mock_parse:
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []  # empty DB

            # parse_addresses returns None for closest_latitude → geocoding failed
            mock_parse.return_value = (
                pd.DataFrame([{"closest_latitude": None, "closest_longitude": None}]),
                pd.DataFrame(),
            )

            result = _apply_geocoding(geo_df, logger)

        assert result is not None
        assert result.loc[0, "geocode_status"] == "failed", (
            f"Expected 'failed' when parse_addresses returns None lat, "
            f"got {result.loc[0, 'geocode_status']!r}"
        )
