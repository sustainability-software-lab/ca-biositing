import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from ca_biositing.pipeline.etl.extract.usda_census_survey import _extract_survey_yield_data, extract

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

    commodity_ids = ["CORN"]
    years = [2022, 2025]

    result = _extract_survey_yield_data("fake_key", commodity_ids, years)

    # Should have called usda_nass_to_df 1 time (optimized)
    assert mock_usda_nass.call_count == 1
    assert isinstance(result, pd.DataFrame)
    # The mock returns 1 record for 2022 STATE, which matches our filter
    assert len(result) == 1
    assert "agg_level_desc" in result.columns

def test_transform_survey_geoid_fallbacks():
    from ca_biositing.pipeline.etl.transform.usda.usda_census_survey import _normalize_geoid

    df = pd.DataFrame({
        "agg_level_desc": ["COUNTY", "STATE", "NATIONAL"],
        "county_code": ["077", "000", "000"],
        "state_fips_code": ["06", "06", "00"]
    })

    result = _normalize_geoid(df)

    assert result.loc[0, "geoid"] == "06077"
    assert result.loc[1, "geoid"] == "06000"
    assert result.loc[2, "geoid"] == "00000"

@patch("ca_biositing.pipeline.etl.load.usda.usda_census_survey.get_engine")
def test_load_state_national_place_guard(mock_get_engine):
    from ca_biositing.pipeline.etl.load.usda.usda_census_survey import _ensure_state_national_place_exists

    mock_conn = MagicMock()
    mock_engine = MagicMock()
    # Mock the context manager for engine.begin()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    mock_get_engine.return_value = mock_engine

    # Patch the pg_insert directly in the sqlalchemy module since it's re-imported inside the function
    with patch("sqlalchemy.dialects.postgresql.insert") as mock_pg_insert:
        # Mock the chainable methods: pg_insert().values().on_conflict_do_nothing()
        mock_stmt = MagicMock()
        mock_pg_insert.return_value.values.return_value.on_conflict_do_nothing.return_value = mock_stmt

        _ensure_state_national_place_exists(mock_engine)

        # Verify pg_insert was called
        assert mock_pg_insert.called
        # Verify it was executed on the connection
        assert mock_conn.execute.called
    args, kwargs = mock_pg_insert.call_args
    # First arg is the table, second is values
    # Actually pg_insert(Table).values(data)
    # So we check if .values() was called with our places
