"""
Tests for PretreatmentSetup transformation logic.
"""
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from ca_biositing.pipeline.etl.transform.analysis.pretreatment_setup import transform_pretreatment_setup

class TestPretreatmentSetupTransform:
    def test_transform_pretreatment_setup_basic(self):
        # Sample raw data
        raw_df = pd.DataFrame({
            "pretreatment_exper_id": ["EXP001"],
            "pretreatment_exper_name": ["Exp 1"],
            "resources": ["Res1, Res2"],
            "prepared_samples": ["Samp1, Samp2"],
            "experiment_date": ["2023-01-01"],
            "analyst_email": ["test@example.com"],
            "decon_method_id": ["Method A"],
            "decon_vessel_id": ["Vessel 1"],
            "eh_method_id": ["EH Method 1"],
            "pretr_notes": ["Do NOT lowercase this"],
            "description": ["KEEP THIS AS IS"]
        })

        # Mock dependencies
        def mock_normalize(df, normalize_columns):
            out = df.copy()
            for col in normalize_columns:
                out[f"{col}_id"] = 1
            return [out]

        # Use patch to mock normalize_dataframes and get_run_logger
        with patch("ca_biositing.pipeline.etl.transform.analysis.pretreatment_setup.get_run_logger") as mock_logger, \
             patch("ca_biositing.pipeline.etl.transform.analysis.pretreatment_setup.normalize_dataframes", side_effect=mock_normalize):

            result = transform_pretreatment_setup.fn(raw_df)

        assert not result.empty
        assert isinstance(result["resources"].iloc[0], list)
        # standard_clean likely lowercases values
        assert [r.lower() for r in result["resources"].iloc[0]] == ["res1", "res2"]
        assert isinstance(result["prepared_samples"].iloc[0], list)
        assert [s.lower() for s in result["prepared_samples"].iloc[0]] == ["samp1", "samp2"]
        assert result["experiment_date"].iloc[0] == date(2023, 1, 1)
        assert "analyst_id" in result.columns
        assert "pretreatment_uuid" in result.columns
        assert result["pretr_notes"].iloc[0] == "Do NOT lowercase this"
        assert result["description"].iloc[0] == "KEEP THIS AS IS"

    def test_transform_pretreatment_setup_empty(self):
        with patch("ca_biositing.pipeline.etl.transform.analysis.pretreatment_setup.get_run_logger"):
            result = transform_pretreatment_setup.fn(pd.DataFrame())
        assert result.empty
