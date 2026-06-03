"""Tests for the food processing facilities ETL pipeline."""

from unittest.mock import MagicMock, patch
import pandas as pd


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


class TestFoodProcessingFacilitiesTransform:
    def test_transform_returns_dataframe(self):
        from ca_biositing.pipeline.etl.transform.infrastructure import food_processing_facilities

        raw_df = pd.DataFrame(
            [
                [
                    "ID1",
                    "Acme Foods",
                    "123 Main St\nSuite 5",
                    "Fresno",
                    "93721-1234",
                    "Fresno",
                    "San Joaquin",
                    "drying",
                    "tomato",
                    "Pomace",
                    "100",
                    "Seeds",
                    "50",
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                ],
                [
                    "ID2",
                    "Brew Co",
                    "500 Beer Rd",
                    "Sacramento",
                    "95814",
                    "Sacramento",
                    "Bay Area",
                    "fermentation",
                    "beer",
                    "Spent grain",
                    "200",
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                ],
            ],
            columns=[
                "Facility ID",
                "Name",
                "Address",
                "City",
                "Zip",
                "County",
                "Air district",
                "Process",
                "Associated food",
                "Byproduct 1",
                "Quantity (tons/year)",
                "Byproduct 2",
                "Quantity (tons/year)",
                "Byproduct 3",
                "Quantity (tons/year)",
                "Byproduct 4",
                "Quantity (tons/year)",
                "Byproduct 5",
                "Quantity (tons/year)",
            ],
        )

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
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session

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
        assert mock_session.commit.called


class TestFoodProcessingFacilitiesFlow:
    def test_flow_exists(self):
        from ca_biositing.pipeline.flows.food_processing_facilities import food_processing_facilities_flow

        assert food_processing_facilities_flow is not None
        assert food_processing_facilities_flow.name == "Food Processing Facilities ETL"
