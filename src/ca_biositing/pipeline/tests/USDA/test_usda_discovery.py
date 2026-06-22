import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from ca_biositing.pipeline.utils.usda_discovery import discover_top_commodities

@pytest.fixture
def mock_usda_nass_to_df():
    with patch('ca_biositing.pipeline.utils.usda_discovery.usda_nass_to_df') as mock:
        yield mock

def test_discover_top_commodities_empty_api_key():
    """Test that an empty API key returns an empty list."""
    result = discover_top_commodities(api_key="")
    assert result == []

def test_discover_top_commodities_no_data(mock_usda_nass_to_df):
    """Test behavior when API returns no data."""
    mock_usda_nass_to_df.return_value = pd.DataFrame()

    result = discover_top_commodities(api_key="test_key")

    assert result == []
    assert mock_usda_nass_to_df.call_count == 2

def test_discover_top_commodities_success(mock_usda_nass_to_df):
    """Test successful discovery of top commodities."""

    # Mock data for AREA HARVESTED
    df_acres = pd.DataFrame({
        'county_code': ['001', '001', '001', '002', '002'],
        'commodity_desc': ['ALMONDS', 'GRAPES', 'WALNUTS', 'CORN', 'WHEAT'],
        'Value': ['10,000', '5,000', '(D)', '20,000', '15,000']
    })

    # Mock data for PRODUCTION
    df_tons = pd.DataFrame({
        'county_code': ['001', '001', '002', '002'],
        'commodity_desc': ['ALMONDS', 'TOMATOES', 'CORN', 'SOYBEANS'],
        'Value': ['50,000', '100,000', '80,000', '40,000']
    })

    # Configure mock to return different data based on statisticcat_desc
    def side_effect(**kwargs):
        if kwargs.get('statisticcat_desc') == 'AREA HARVESTED':
            return df_acres
        elif kwargs.get('statisticcat_desc') == 'PRODUCTION':
            return df_tons
        return pd.DataFrame()

    mock_usda_nass_to_df.side_effect = side_effect

    # Request top 2 commodities per county per metric
    result = discover_top_commodities(api_key="test_key", top_n=2)

    # Expected logic:
    # County 001 Acres: ALMONDS (10000), GRAPES (5000) -> WALNUTS is 0 due to (D)
    # County 002 Acres: CORN (20000), WHEAT (15000)
    # County 001 Tons: TOMATOES (100000), ALMONDS (50000)
    # County 002 Tons: CORN (80000), SOYBEANS (40000)
    # Unique set: ALMONDS, GRAPES, CORN, WHEAT, TOMATOES, SOYBEANS

    expected = sorted(['ALMONDS', 'GRAPES', 'CORN', 'WHEAT', 'TOMATOES', 'SOYBEANS'])

    assert result == expected
    assert mock_usda_nass_to_df.call_count == 2
