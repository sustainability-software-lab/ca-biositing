"""
Tests for EnzymaticHydrolysisMethod transformation logic.
"""
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch
from ca_biositing.pipeline.etl.transform.analysis.enz_hydr_method import transform_enz_hydr_method

class TestEnzymaticHydrolysisMethodTransform:
    def test_transform_enz_hydr_method_basic(self):
        # Sample raw data
        raw_df = pd.DataFrame({
            "eh_id": ["EH001"],
            "method_id": ["M001"],
            "name": ["Method 1"],
            "enzyme_formulation": ["Form 1"],
            "reaction_volume_ul": ["1000.5"],
            "temperature_c": ["50.0"],
            "time_h": ["24"]
        })

        with patch("ca_biositing.pipeline.etl.transform.analysis.enz_hydr_method.get_run_logger"):
            result = transform_enz_hydr_method.fn(raw_df)

        assert not result.empty
        assert result["reaction_volume_ul"].iloc[0] == 1000.5
        assert result["temperature_c"].iloc[0] == 50.0
        assert result["time_h"].iloc[0] == 24.0
        assert "eh_uuid" in result.columns

    def test_transform_enz_hydr_method_empty(self):
        with patch("ca_biositing.pipeline.etl.transform.analysis.enz_hydr_method.get_run_logger"):
            result = transform_enz_hydr_method.fn(pd.DataFrame())
        assert result.empty
