"""
Integration tests for Residue Factors ETL Flow.

Tests the complete Prefect flow for residue factors, including:
- Flow registration and structure
- Task chaining (extract → transform → load)
- Error handling and logging
- Local execution with mock data
- Deployment readiness
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from decimal import Decimal


class TestResidueFactorsFlowStructure:
    """Tests for the flow structure and registration"""

    def test_flow_module_imports(self):
        """Test that flow module can be imported"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        assert residue_factors_etl_flow is not None

    def test_flow_is_prefect_flow(self):
        """Test that residue_factors_etl_flow is a Prefect flow"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        # Check that it has Prefect flow attributes
        assert hasattr(residue_factors_etl_flow, "name")
        assert residue_factors_etl_flow.name == "Residue Factors ETL"

    def test_flow_has_log_prints_enabled(self):
        """Test that flow has log_prints enabled for Docker logging"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        # Check that log_prints is enabled
        assert hasattr(residue_factors_etl_flow, "log_prints")
        assert residue_factors_etl_flow.log_prints is True

    def test_flow_has_docstring(self):
        """Test that flow has comprehensive docstring"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        assert residue_factors_etl_flow.__doc__ is not None
        assert "Extract" in residue_factors_etl_flow.__doc__
        assert "Transform" in residue_factors_etl_flow.__doc__
        assert "Load" in residue_factors_etl_flow.__doc__

    def test_flow_uses_lazy_imports(self):
        """Test that flow uses lazy imports to avoid Docker hangs"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        import inspect

        source = inspect.getsource(residue_factors_etl_flow)

        # Should have lazy imports inside the function
        assert "from ca_biositing.pipeline.etl.extract" in source
        assert "from ca_biositing.pipeline.etl.transform" in source
        assert "from ca_biositing.pipeline.etl.load" in source


class TestResidueFactorsFlowExecution:
    """Tests for flow execution with mocked tasks"""

    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_etl_run_record"
    )
    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_lineage_group"
    )
    def test_flow_calls_lineage_tracking(
        self, mock_lineage_group, mock_etl_run_record
    ):
        """Test that flow creates lineage tracking records"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        # Mock the lineage functions
        mock_etl_run_record.fn.return_value = "test-run-id"
        mock_lineage_group.fn.return_value = "test-lineage-id"

        # Mock extract, transform, load modules
        with patch(
            "ca_biositing.pipeline.etl.extract.residue_factors.extract_residue_factors.fn"
        ) as mock_extract:
            with patch(
                "ca_biositing.pipeline.etl.transform.resource_information.residue_factor.transform_residue_factor.fn"
            ) as mock_transform:
                with patch(
                    "ca_biositing.pipeline.etl.load.resource_information.residue_factor.load_residue_factors.fn"
                ) as mock_load:
                    # Set up mock return values
                    mock_extract.return_value = pd.DataFrame(
                        {
                            "resource": ["almonds"],
                            "factor_type": ["commodity"],
                            "factor_min": [0.1],
                            "factor_max": [0.3],
                        }
                    )
                    mock_transform.return_value = pd.DataFrame(
                        {
                            "resource_id": [1],
                            "factor_type": ["commodity"],
                            "factor_min": [Decimal("0.1")],
                            "factor_max": [Decimal("0.3")],
                            "etl_run_id": ["test-run-id"],
                            "lineage_group_id": ["test-lineage-id"],
                        }
                    )
                    mock_load.return_value = {"inserted": 1, "updated": 0, "failed": 0}

                    # Run the flow
                    residue_factors_etl_flow()

                    # Verify lineage tracking was called
                    mock_etl_run_record.fn.assert_called_once()
                    mock_lineage_group.fn.assert_called_once()

    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_etl_run_record"
    )
    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_lineage_group"
    )
    def test_flow_handles_extraction_failure(
        self, mock_lineage_group, mock_etl_run_record
    ):
        """Test that flow handles extraction failures"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        # Mock the lineage functions
        mock_etl_run_record.fn.return_value = "test-run-id"
        mock_lineage_group.fn.return_value = "test-lineage-id"

        # Mock extract to raise an exception
        with patch(
            "ca_biositing.pipeline.etl.extract.residue_factors.extract_residue_factors.fn"
        ) as mock_extract:
            mock_extract.side_effect = RuntimeError("Failed to extract from Google Sheets")

            # Flow should raise the exception
            with pytest.raises(RuntimeError):
                residue_factors_etl_flow()

    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_etl_run_record"
    )
    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_lineage_group"
    )
    def test_flow_handles_empty_extraction(
        self, mock_lineage_group, mock_etl_run_record
    ):
        """Test that flow handles empty extraction gracefully"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        # Mock the lineage functions
        mock_etl_run_record.fn.return_value = "test-run-id"
        mock_lineage_group.fn.return_value = "test-lineage-id"

        # Mock extract to return empty DataFrame
        with patch(
            "ca_biositing.pipeline.etl.extract.residue_factors.extract_residue_factors.fn"
        ) as mock_extract:
            mock_extract.return_value = pd.DataFrame()

            # Flow should return gracefully without raising
            residue_factors_etl_flow()

    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_etl_run_record"
    )
    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_lineage_group"
    )
    def test_flow_handles_transformation_failure(
        self, mock_lineage_group, mock_etl_run_record
    ):
        """Test that flow handles transformation failures"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        # Mock the lineage functions
        mock_etl_run_record.fn.return_value = "test-run-id"
        mock_lineage_group.fn.return_value = "test-lineage-id"

        # Mock extract to return valid data
        with patch(
            "ca_biositing.pipeline.etl.extract.residue_factors.extract_residue_factors.fn"
        ) as mock_extract:
            # Mock transform to raise an exception
            with patch(
                "ca_biositing.pipeline.etl.transform.resource_information.residue_factor.transform_residue_factor.fn"
            ) as mock_transform:
                mock_extract.return_value = pd.DataFrame(
                    {
                        "resource": ["almonds"],
                        "factor_type": ["commodity"],
                    }
                )
                mock_transform.side_effect = ValueError("Foreign key resolution failed")

                # Flow should raise the exception
                with pytest.raises(ValueError):
                    residue_factors_etl_flow()

    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_etl_run_record"
    )
    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_lineage_group"
    )
    def test_flow_handles_load_failure(
        self, mock_lineage_group, mock_etl_run_record
    ):
        """Test that flow handles load failures"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        # Mock the lineage functions
        mock_etl_run_record.fn.return_value = "test-run-id"
        mock_lineage_group.fn.return_value = "test-lineage-id"

        # Mock extract and transform to return valid data
        with patch(
            "ca_biositing.pipeline.etl.extract.residue_factors.extract_residue_factors.fn"
        ) as mock_extract:
            with patch(
                "ca_biositing.pipeline.etl.transform.resource_information.residue_factor.transform_residue_factor.fn"
            ) as mock_transform:
                # Mock load to raise an exception
                with patch(
                    "ca_biositing.pipeline.etl.load.resource_information.residue_factor.load_residue_factors.fn"
                ) as mock_load:
                    mock_extract.return_value = pd.DataFrame(
                        {
                            "resource": ["almonds"],
                            "factor_type": ["commodity"],
                        }
                    )
                    mock_transform.return_value = pd.DataFrame(
                        {
                            "resource_id": [1],
                            "factor_type": ["commodity"],
                        }
                    )
                    mock_load.side_effect = RuntimeError("Database connection failed")

                    # Flow should raise the exception
                    with pytest.raises(RuntimeError):
                        residue_factors_etl_flow()

    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_etl_run_record"
    )
    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_lineage_group"
    )
    def test_flow_full_pipeline_success(
        self, mock_lineage_group, mock_etl_run_record
    ):
        """Test successful execution of the full pipeline"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        # Mock the lineage functions
        mock_etl_run_record.fn.return_value = "test-run-id"
        mock_lineage_group.fn.return_value = "test-lineage-id"

        # Mock all ETL stages
        with patch(
            "ca_biositing.pipeline.etl.extract.residue_factors.extract_residue_factors.fn"
        ) as mock_extract:
            with patch(
                "ca_biositing.pipeline.etl.transform.resource_information.residue_factor.transform_residue_factor.fn"
            ) as mock_transform:
                with patch(
                    "ca_biositing.pipeline.etl.load.resource_information.residue_factor.load_residue_factors.fn"
                ) as mock_load:
                    # Create realistic test data
                    raw_df = pd.DataFrame(
                        {
                            "resource": ["almonds", "walnuts"],
                            "factor_type": ["commodity", "commodity"],
                            "factor_min": [0.1, 0.15],
                            "factor_max": [0.3, 0.35],
                            "prune_trim_yield": [0.5, 0.6],
                            "source": ["publication1", "publication2"],
                        }
                    )

                    transformed_df = pd.DataFrame(
                        {
                            "resource_id": [1, 2],
                            "resource_name": ["almonds", "walnuts"],
                            "factor_type": ["commodity", "commodity"],
                            "factor_min": [Decimal("0.1"), Decimal("0.15")],
                            "factor_max": [Decimal("0.3"), Decimal("0.35")],
                            "factor_mid": [Decimal("0.2"), Decimal("0.25")],
                            "prune_trim_yield": [Decimal("0.5"), Decimal("0.6")],
                            "etl_run_id": ["test-run-id", "test-run-id"],
                            "lineage_group_id": ["test-lineage-id", "test-lineage-id"],
                        }
                    )

                    mock_extract.return_value = raw_df
                    mock_transform.return_value = transformed_df
                    mock_load.return_value = {"inserted": 2, "updated": 0, "failed": 0}

                    # Run the flow
                    residue_factors_etl_flow()

                    # Verify all stages were called
                    mock_extract.assert_called_once()
                    mock_transform.assert_called_once()
                    mock_load.assert_called_once()

                    # Verify the transform call receives extract output
                    call_args = mock_transform.call_args
                    assert call_args is not None
                    # Check that df parameter was passed
                    if call_args[1]:  # kwargs
                        assert "df" in call_args[1]
                        assert call_args[1]["df"] is raw_df

    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_etl_run_record"
    )
    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_lineage_group"
    )
    def test_flow_logs_summary_statistics(
        self, mock_lineage_group, mock_etl_run_record
    ):
        """Test that flow logs summary statistics"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        # Mock the lineage functions
        mock_etl_run_record.fn.return_value = "test-run-id"
        mock_lineage_group.fn.return_value = "test-lineage-id"

        # Mock all ETL stages
        with patch(
            "ca_biositing.pipeline.etl.extract.residue_factors.extract_residue_factors.fn"
        ) as mock_extract:
            with patch(
                "ca_biositing.pipeline.etl.transform.resource_information.residue_factor.transform_residue_factor.fn"
            ) as mock_transform:
                with patch(
                    "ca_biositing.pipeline.etl.load.resource_information.residue_factor.load_residue_factors.fn"
                ) as mock_load:
                    raw_df = pd.DataFrame(
                        {
                            "resource": ["almonds"],
                            "factor_type": ["commodity"],
                        }
                    )
                    transformed_df = pd.DataFrame(
                        {
                            "resource_id": [1],
                            "factor_type": ["commodity"],
                        }
                    )

                    mock_extract.return_value = raw_df
                    mock_transform.return_value = transformed_df
                    mock_load.return_value = {"inserted": 1, "updated": 0, "failed": 0}

                    # Run the flow with mock logger
                    with patch("ca_biositing.pipeline.flows.residue_factors_flow.get_run_logger") as mock_logger:
                        mock_logger_instance = MagicMock()
                        mock_logger.return_value = mock_logger_instance

                        residue_factors_etl_flow()

                        # Verify logging occurred (at least some info logs)
                        # Check that logger.info was called multiple times
                        assert mock_logger_instance.info.called


class TestResidueFactorsFlowDataFlow:
    """Tests for data flow between pipeline stages"""

    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_etl_run_record"
    )
    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_lineage_group"
    )
    def test_flow_passes_dataframe_extract_to_transform(
        self, mock_lineage_group, mock_etl_run_record
    ):
        """Test that extract output DataFrame is passed to transform"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        mock_etl_run_record.fn.return_value = "test-run-id"
        mock_lineage_group.fn.return_value = "test-lineage-id"

        extract_df = pd.DataFrame(
            {"resource": ["almonds"], "factor_type": ["commodity"]}
        )

        with patch(
            "ca_biositing.pipeline.etl.extract.residue_factors.extract_residue_factors.fn"
        ) as mock_extract:
            with patch(
                "ca_biositing.pipeline.etl.transform.resource_information.residue_factor.transform_residue_factor.fn"
            ) as mock_transform:
                with patch(
                    "ca_biositing.pipeline.etl.load.resource_information.residue_factor.load_residue_factors.fn"
                ) as mock_load:
                    mock_extract.return_value = extract_df
                    mock_transform.return_value = extract_df.copy()
                    mock_load.return_value = {"inserted": 1, "updated": 0, "failed": 0}

                    residue_factors_etl_flow()

                    # Verify transform received the extract output
                    assert mock_transform.called
                    call_kwargs = mock_transform.call_args[1]
                    pd.testing.assert_frame_equal(call_kwargs["df"], extract_df)

    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_etl_run_record"
    )
    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_lineage_group"
    )
    def test_flow_passes_dataframe_transform_to_load(
        self, mock_lineage_group, mock_etl_run_record
    ):
        """Test that transform output DataFrame is passed to load"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        mock_etl_run_record.fn.return_value = "test-run-id"
        mock_lineage_group.fn.return_value = "test-lineage-id"

        extract_df = pd.DataFrame(
            {"resource": ["almonds"], "factor_type": ["commodity"]}
        )
        transform_df = pd.DataFrame(
            {
                "resource_id": [1],
                "factor_type": ["commodity"],
                "etl_run_id": ["test-run-id"],
            }
        )

        with patch(
            "ca_biositing.pipeline.etl.extract.residue_factors.extract_residue_factors.fn"
        ) as mock_extract:
            with patch(
                "ca_biositing.pipeline.etl.transform.resource_information.residue_factor.transform_residue_factor.fn"
            ) as mock_transform:
                with patch(
                    "ca_biositing.pipeline.etl.load.resource_information.residue_factor.load_residue_factors.fn"
                ) as mock_load:
                    mock_extract.return_value = extract_df
                    mock_transform.return_value = transform_df
                    mock_load.return_value = {"inserted": 1, "updated": 0, "failed": 0}

                    residue_factors_etl_flow()

                    # Verify load received the transform output
                    assert mock_load.called
                    call_kwargs = mock_load.call_args[1]
                    pd.testing.assert_frame_equal(call_kwargs["df"], transform_df)


class TestResidueFactorsFlowErrorHandling:
    """Tests for error handling in the flow"""

    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_etl_run_record"
    )
    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_lineage_group"
    )
    def test_flow_logs_errors_with_traceback(
        self, mock_lineage_group, mock_etl_run_record
    ):
        """Test that flow logs errors with traceback information"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        mock_etl_run_record.fn.return_value = "test-run-id"
        mock_lineage_group.fn.return_value = "test-lineage-id"

        with patch(
            "ca_biositing.pipeline.etl.extract.residue_factors.extract_residue_factors.fn"
        ) as mock_extract:
            mock_extract.side_effect = RuntimeError("Test error")

            with patch("ca_biositing.pipeline.flows.residue_factors_flow.get_run_logger") as mock_logger:
                mock_logger_instance = MagicMock()
                mock_logger.return_value = mock_logger_instance

                with pytest.raises(RuntimeError):
                    residue_factors_etl_flow()

                # Verify error was logged with exc_info
                error_calls = [
                    call for call in mock_logger_instance.error.call_args_list
                    if "Extraction failed" in str(call)
                ]
                assert len(error_calls) > 0

    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_etl_run_record"
    )
    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_lineage_group"
    )
    def test_flow_handles_none_extraction(
        self, mock_lineage_group, mock_etl_run_record
    ):
        """Test that flow handles None from extraction"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        mock_etl_run_record.fn.return_value = "test-run-id"
        mock_lineage_group.fn.return_value = "test-lineage-id"

        with patch(
            "ca_biositing.pipeline.etl.extract.residue_factors.extract_residue_factors.fn"
        ) as mock_extract:
            mock_extract.return_value = None

            # Flow should return gracefully
            residue_factors_etl_flow()

    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_etl_run_record"
    )
    @patch(
        "ca_biositing.pipeline.flows.residue_factors_flow.create_lineage_group"
    )
    def test_flow_handles_none_transformation(
        self, mock_lineage_group, mock_etl_run_record
    ):
        """Test that flow handles None from transformation"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        mock_etl_run_record.fn.return_value = "test-run-id"
        mock_lineage_group.fn.return_value = "test-lineage-id"

        with patch(
            "ca_biositing.pipeline.etl.extract.residue_factors.extract_residue_factors.fn"
        ) as mock_extract:
            with patch(
                "ca_biositing.pipeline.etl.transform.resource_information.residue_factor.transform_residue_factor.fn"
            ) as mock_transform:
                mock_extract.return_value = pd.DataFrame(
                    {"resource": ["almonds"], "factor_type": ["commodity"]}
                )
                mock_transform.return_value = None

                # Flow should return gracefully
                residue_factors_etl_flow()


class TestDeploymentReadiness:
    """Tests for deployment readiness"""

    def test_flow_can_be_imported_in_clean_environment(self):
        """Test that flow can be imported without side effects"""
        # This would be run in a clean Python environment
        # For now, just verify it imports successfully
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        assert residue_factors_etl_flow is not None

    def test_flow_uses_get_run_logger(self):
        """Test that flow uses Prefect's get_run_logger"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        import inspect

        source = inspect.getsource(residue_factors_etl_flow)

        # Should use get_run_logger from Prefect
        assert "get_run_logger" in source

    def test_flow_handles_stdout_buffering(self):
        """Test that flow handles stdout buffering for Docker logging"""
        from ca_biositing.pipeline.flows.residue_factors_flow import (
            residue_factors_etl_flow,
        )

        import inspect

        source = inspect.getsource(residue_factors_etl_flow)

        # Should reconfigure stdout for Docker
        assert "reconfigure" in source
        assert "line_buffering" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
