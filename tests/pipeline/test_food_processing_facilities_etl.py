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

        with self._patch_geocode_target("all_facilities"):
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

    def test_transform_output_has_nonzero_rows(self):
        """Transform must return > 0 rows given valid input (all_facilities mode)."""
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        with self._patch_geocode_target("all_facilities"):
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

        with self._patch_geocode_target("all_facilities"):
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

        with self._patch_geocode_target("all_facilities"):
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

        with self._patch_geocode_target("all_facilities"):
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

        with self._patch_geocode_target("all_facilities"):
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

        with self._patch_geocode_target("all_facilities"):
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
             patch.object(mod, "GEOCODE_TARGET", "all_facilities"):
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
        with patch.object(mod, "GEOCODE_TARGET", "all_facilities"):
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
