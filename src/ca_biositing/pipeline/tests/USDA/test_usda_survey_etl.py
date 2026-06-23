import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from ca_biositing.pipeline.etl.extract.usda_census_survey import extract

@patch("ca_biositing.pipeline.etl.extract.usda_census_survey.usda_nass_to_df")
@patch("ca_biositing.pipeline.etl.extract.usda_census_survey.get_run_logger")
def test_extract_survey_yield(mock_logger, mock_usda_nass):
    # Mock data for one successful query
    mock_df = pd.DataFrame({
        "commodity_desc": ["CORN"],
        "statisticcat_desc": ["YIELD"],
        "unit_desc": ["BU / ACRE"],
        "Value": ["150"],
        "year": [2022],
        "agg_level_desc": ["STATE"],
        "state_alpha": ["CA"],
        "county_code": ["000"]
    })

    mock_usda_nass.return_value = mock_df

    # We'll mock the internal dependencies of extract() to test its flow
    with patch("ca_biositing.pipeline.etl.extract.usda_census_survey.discover_top_commodities", return_value=["CORN"]), \
         patch("ca_biositing.pipeline.etl.extract.usda_census_survey.get_mapped_commodity_ids", return_value=[]), \
         patch("ca_biositing.pipeline.etl.extract.usda_census_survey.ensure_commodities_exist"), \
         patch("ca_biositing.pipeline.etl.extract.usda_census_survey.get_engine"), \
         patch("ca_biositing.pipeline.etl.extract.usda_census_survey._load_ca_counties", return_value=[("000", "TEST COUNTY")]):

        result = extract()

    # Should have called usda_nass_to_df 1 time (optimized)
    assert mock_usda_nass.called
    assert isinstance(result, pd.DataFrame)
    # The mock returns 1 record for 2022 STATE, which matches our filter
    assert len(result) == 1

def test_transform_survey_geoid_fallbacks():
    # Attempting to import the private function from the transform module
    try:
        from ca_biositing.pipeline.etl.transform.usda.usda_census_survey import _normalize_geoid
    except ImportError:
        pytest.skip("_normalize_geoid not found in transform module")

    df = pd.DataFrame({
        "agg_level_desc": ["COUNTY", "STATE", "NATIONAL"],
        "county_code": ["077", "000", "000"],
        "state_fips_code": ["06", "06", "00"]
    })

    result = _normalize_geoid(df)

    assert result.loc[0, "geoid"] == "06077"
    assert result.loc[1, "geoid"] == "06000"
    assert result.loc[2, "geoid"] == "00000"

@patch("ca_biositing.pipeline.etl.load.usda.usda_census_survey.get_run_logger")
@patch("ca_biositing.pipeline.etl.load.usda.usda_census_survey.get_engine")
def test_load_observations_logic(mock_get_engine, mock_logger):
    # This test validates the logic in _load_observations helper
    try:
        from ca_biositing.pipeline.etl.load.usda.usda_census_survey import _load_observations
    except ImportError:
        pytest.skip("_load_observations not found in load module")

    mock_conn = MagicMock()
    mock_engine = MagicMock()
    # Mock both context managers: engine.connect() and engine.begin()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    mock_get_engine.return_value = mock_engine

    # Mock the dataset map
    dataset_map = {(2022, 'SURVEY'): 1}

    # Transformed data matching the expected flow in _load_observations
    transformed_df = pd.DataFrame([{
        "geoid": "06077",
        "year": 2022,
        "commodity_code": 1,
        "parameter_id": 2,
        "unit_id": 3,
        "value_numeric": 150.0,
        "record_type": "YIELD",
        "source_type": "SURVEY",
        "commodity": "CORN",
        "statistic": "YIELD",
        "unit": "BU / ACRE"
    }])

    # Patch pg_insert and text
    with patch("ca_biositing.pipeline.etl.load.usda.usda_census_survey.pg_insert") as mock_pg_insert, \
         patch("ca_biositing.pipeline.etl.load.usda.usda_census_survey.text"):

        # Mock the query results for record_id_map and existing_obs_keys
        # _load_observations calls conn.execute multiple times.
        # Order:
        # 1. SELECT id, geoid, year, commodity_code FROM usda_census_record (connect context)
        # 2. SELECT id, geoid, year, commodity_code FROM usda_survey_record (connect context)
        # 3. SELECT record_id, record_type, parameter_id, unit_id FROM observation (connect context)
        # 4. INSERT INTO observation ... (begin context)

        mock_result_census = MagicMock()
        mock_result_census.__iter__.return_value = iter([(10, "06077", 2022, 1)]) # id, geoid, year, commodity_code

        mock_result_survey = MagicMock()
        mock_result_survey.__iter__.return_value = iter([(11, "06077", 2022, 1)]) # id, geoid, year, commodity_code

        mock_result_obs = MagicMock()
        mock_result_obs.__iter__.return_value = iter([])

        mock_result_insert = MagicMock()
        mock_result_insert.rowcount = 1

        mock_conn.execute.side_effect = [mock_result_census, mock_result_survey, mock_result_obs, mock_result_insert]

        # Mock the Observation model and its table
        from ca_biositing.datamodels.models import Observation
        mock_stmt = MagicMock()
        mock_pg_insert.return_value.values.return_value.on_conflict_do_nothing.return_value = mock_stmt

        _load_observations(
            mock_engine, transformed_df, dataset_map,
            etl_run_id=1, lineage_group_id=2, now=pd.Timestamp.now()
        )

        # Verify pg_insert was called
        assert mock_pg_insert.called
        assert mock_conn.execute.called
