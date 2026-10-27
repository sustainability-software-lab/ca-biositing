"""
Test suite for County Ag Report ETL pipeline (Phase 4).

Tests extract, transform, and load steps for county_ag_report workflow.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone


class TestCountyAgReportExtract:
    """Test the extract step for county ag reports."""

    def test_extract_module_exists(self):
        """Verify that the extract module can be imported."""
        from ca_biositing.pipeline.etl.extract import county_ag_report
        assert county_ag_report is not None
        assert hasattr(county_ag_report, 'primary_products')
        assert hasattr(county_ag_report, 'pp_production_value')
        assert hasattr(county_ag_report, 'pp_data_sources')

    def test_extract_has_correct_sheet_names(self):
        """Verify the extract module uses correct Google Sheet names."""
        from ca_biositing.pipeline.etl.extract import county_ag_report
        assert county_ag_report.GSHEET_NAME == "Aim 1-Feedstock Collection and Processing Data-BioCirV"


class TestCountyAgReportTransform:
    """Test the transform steps for county ag reports."""

    def test_transform_records_returns_dataframe(self):
        """Test that record transform returns a DataFrame with correct columns and record IDs."""
        from ca_biositing.pipeline.etl.transform.analysis import county_ag_report_record

        # Mock input data
        meta_data = pd.DataFrame({
            'Prod_Nbr': ['pc-001', 'pc-002'],
            'Primary_product': ['Almonds', 'Walnuts'],
            'Produced_NSJV': ['Yes', 'No'],
            'Processed_NSJV': ['Yes', 'Yes'],
        })

        metrics_data = pd.DataFrame({
            'Prod_Nbr': ['pc-001', 'pc-001'],
            'Data_Year': [2023, 2024],
            'Prodn_Merced': [100, 110],
            'Value_$M_Merced': [50, 55],
            'Prodn_Value_note': ['Note 1', 'Note 2']
        })

        with patch('ca_biositing.pipeline.etl.transform.analysis.county_ag_report_record.normalize_dataframes') as mock_normalize:
            # Create a normalized DataFrame matching normalize_dataframes output (*_id suffix)
            normalized_df = pd.DataFrame({
                'record_id': ['pc-001-merced-2023', 'pc-001-merced-2024'],
                'geoid': ['06047', '06047'],
                'primary_product_id': [1, 1],
                'data_year': [2023, 2024],
                'data_source_name_id': [1, 5],
                'produced_nsjv': [True, True],
                'processed_nsjv': [True, True],
            })
            mock_normalize.return_value = [normalized_df]

            result = county_ag_report_record.transform_county_ag_report_records.fn(
                data_sources={
                    "primary_products": meta_data,
                    "pp_production_value": metrics_data
                },
                etl_run_id="test-run",
                lineage_group_id=1
            )

            # Verify name-based normalization input
            call_df, call_cols = mock_normalize.call_args[0]
            assert "data_source_name" in call_cols
            assert list(call_df["data_source_name"]) == [
                "merced county 2023 report on agriculture",
                "merced county 2024 report on agriculture",
            ]

            assert result is not None
            assert not result.empty
            assert 'record_id' in result.columns
            assert 'data_source_id' in result.columns
            assert list(result['data_source_id']) == [1, 5]
            assert result.iloc[0]['record_id'] == 'pc-001-merced-2023'
            assert bool(result.iloc[0]['produced_nsjv']) is True

    def test_transform_observations_returns_dataframe(self):
        """Test that observation transform correctly melts wide data and resolves dataset_name by name."""
        from ca_biositing.pipeline.etl.transform.analysis import county_ag_report_observation

        metrics_data = pd.DataFrame({
            'Prod_Nbr': ['pc-001'],
            'Data_Year': [2023],
            'Prodn_Merced': [100],
            'Value_M_Merced': [50],
            'Prodn_SanJoaquin': [200],
        })

        with patch('ca_biositing.pipeline.etl.transform.analysis.county_ag_report_observation.normalize_dataframes') as mock_normalize:
            # Resulting melted data should have 3 observations (Merced prodn + value, San Joaquin prodn)
            normalized_df = pd.DataFrame({
                'record_id': ['pc-001-merced-2023', 'pc-001-merced-2023', 'pc-001-sanjoaquin-2023'],
                'parameter_name_id': [79, 80, 79],
                'unit_name_id': [1, 2, 1],
                'dataset_name_id': [1, 1, 2],
                'value': [100.0, 50.0, 200.0],
            })
            mock_normalize.return_value = [normalized_df]

            result = county_ag_report_observation.transform_county_ag_report_observations.fn(
                data_sources={"pp_production_value": metrics_data},
                etl_run_id="test-run",
                lineage_group_id=1
            )

            call_df, call_cols = mock_normalize.call_args[0]
            assert "dataset_name" in call_cols
            assert list(call_df["dataset_name"]) == [
                "MERCED_COUNTY_2023_REPORT_ON_AGRICULTURE",
                "MERCED_COUNTY_2023_REPORT_ON_AGRICULTURE",
                "SAN_JOAQUIN_COUNTY_CROP_REPORT_2023",
            ]

            assert result is not None
            assert len(result) == 3
            assert 'record_id' in result.columns
            assert 'dataset_id' in result.columns
            assert list(result['dataset_id']) == [1, 1, 2]
            assert 'value' in result.columns

    def test_transform_data_sources_filters_placeholder_rows(self):
        """Rows with an index but blank source metadata should be dropped."""
        from ca_biositing.pipeline.etl.transform.analysis import data_source as ds_transform

        raw_sources = pd.DataFrame(
            {
                "Index": ["001", "002", "008", "009"],
                "SourceName": ["Merced Report", "SJ Report", "", pd.NA],
                "Author": ["County A", "County B", "", pd.NA],
                "Date": ["2023", "2024", "", pd.NA],
                "URL": ["http://a", "http://b", "", pd.NA],
            }
        )

        result = ds_transform.transform_data_sources.fn(
            data_sources={"pp_data_sources": raw_sources},
            etl_run_id="test-run",
            lineage_group_id=1,
        )

        assert result is not None
        assert len(result) == 2
        assert list(result["id"]) == [1, 2]
        assert list(result["name"]) == ["merced report", "sj report"]


class TestCountyAgReportLoad:
    """Test the load step for county ag reports."""

    @patch('ca_biositing.pipeline.utils.engine.get_engine')
    def test_load_records_calls_execute(self, mock_get_engine):
        """Verify load_county_ag_report_records calls database execution."""
        from ca_biositing.pipeline.etl.load.analysis import county_ag_report_record

        mock_session = MagicMock()
        mock_conn = MagicMock()
        mock_get_engine.return_value.connect.return_value.__enter__.return_value = mock_conn

        # Mock Session to work with 'with' statement
        with patch('ca_biositing.pipeline.etl.load.analysis.county_ag_report_record.Session', return_value=mock_session):
            df = pd.DataFrame({
                'record_id': ['test-1'],
                'geoid': ['06047'],
                'data_year': [2023]
            })

            county_ag_report_record.load_county_ag_report_records.fn(df)

            assert mock_session.__enter__.return_value.execute.called
            assert mock_session.__enter__.return_value.commit.called


class TestCountyAgReportFlow:
    """Test the Prefect flow for county ag reports."""

    def test_flow_imports_correctly(self):
        """Verify the flow can be imported and has the correct name."""
        from ca_biositing.pipeline.flows.county_ag_report_etl import county_ag_report_flow
        assert county_ag_report_flow.name == "County Ag Report ETL"
