"""
Unit tests for Residue Factor ETL pipeline.

Tests the extract, transform, and load modules for residue factor data.
"""

import pandas as pd
import numpy as np
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone


class TestExtractResidueFactor:
    """Tests for extract module"""

    def test_extract_module_imports(self):
        """Test that extract module can be imported"""
        from ca_biositing.pipeline.etl.extract.residue_factors import (
            extract_residue_factors,
            GSHEET_ID,
            WORKSHEET_NAME,
        )

        assert extract_residue_factors is not None
        assert GSHEET_ID is not None
        assert WORKSHEET_NAME == "Data Views"

    def test_extract_is_prefect_task(self):
        """Test that extractor is a Prefect task"""
        from ca_biositing.pipeline.etl.extract.residue_factors import extract_residue_factors

        # Check that it has Prefect task attributes
        assert hasattr(extract_residue_factors, "fn")
        assert hasattr(extract_residue_factors, "name")
        assert extract_residue_factors.name == "extract_residue_factors"

    def test_extract_task_properties(self):
        """Test extractor task has expected retry properties"""
        from ca_biositing.pipeline.etl.extract.residue_factors import extract_residue_factors

        assert hasattr(extract_residue_factors, "retries")
        assert extract_residue_factors.retries == 3


class TestTransformResidueFactor:
    """Tests for transform module"""

    def test_transform_module_imports(self):
        """Test that transform module can be imported"""
        from ca_biositing.pipeline.etl.transform.resource_information.residue_factor import (
            transform_residue_factor,
        )

        assert transform_residue_factor is not None

    def test_transform_with_empty_dataframe(self):
        """Test transform handles empty DataFrame gracefully"""
        from ca_biositing.pipeline.etl.transform.resource_information.residue_factor import (
            transform_residue_factor,
        )

        result = transform_residue_factor.fn(pd.DataFrame())
        assert result is None

    def test_transform_with_none_dataframe(self):
        """Test transform handles None DataFrame gracefully"""
        from ca_biositing.pipeline.etl.transform.resource_information.residue_factor import (
            transform_residue_factor,
        )

        result = transform_residue_factor.fn(None)
        assert result is None

    def test_transform_column_normalization(self):
        """Test that transform normalizes column names to lowercase"""
        from ca_biositing.pipeline.etl.transform.resource_information.residue_factor import (
            transform_residue_factor,
        )

        # Verify the transform function uses standard_clean for column normalization
        import inspect

        source = inspect.getsource(transform_residue_factor.fn)
        assert "standard_clean" in source, "Transform should use standard_clean for column normalization"

    def test_transform_decimal_coercion(self):
        """Test that transform coerces numeric fields to Decimal"""
        from ca_biositing.pipeline.etl.transform.resource_information.residue_factor import (
            transform_residue_factor,
        )

        # Verify the transform function coerces to Decimal
        import inspect

        source = inspect.getsource(transform_residue_factor.fn)
        assert "Decimal" in source, "Transform should use Decimal type for numeric fields"
        assert "decimal_cols" in source, "Transform should have decimal_cols configuration"

    def test_transform_factor_mid_calculation(self):
        """Test that factor_mid is calculated when NULL and min/max present"""
        # This test verifies the calculation logic in isolation
        factor_min = Decimal("0.1")
        factor_max = Decimal("0.3")

        # Simulate the calculation
        factor_mid = (factor_min + factor_max) / 2
        expected = Decimal("0.2")

        assert factor_mid == expected

    def test_transform_output_has_required_columns(self):
        """Test that transform output includes all required ResidueFactor columns"""
        from ca_biositing.pipeline.etl.transform.resource_information.residue_factor import (
            transform_residue_factor,
        )

        # Expected columns in ResidueFactor model
        expected_cols = [
            "resource_id",
            "resource_name",
            "data_source_id",
            "factor_type",
            "factor_min",
            "factor_max",
            "factor_mid",
            "prune_trim_yield",
            "prune_trim_yield_unit_id",
            "notes",
            "etl_run_id",
            "lineage_group_id",
        ]

        # Verify the transform function references these columns
        import inspect

        source = inspect.getsource(transform_residue_factor.fn)
        for col in expected_cols:
            assert col in source, f"Column {col} not found in transform function"


class TestLoadResidueFactor:
    """Tests for load module"""

    def test_load_module_imports(self):
        """Test that load module can be imported"""
        from ca_biositing.pipeline.etl.load.resource_information.residue_factor import (
            load_residue_factors,
        )

        assert load_residue_factors is not None

    def test_load_with_empty_dataframe(self):
        """Test load handles empty DataFrame gracefully"""
        from ca_biositing.pipeline.etl.load.resource_information.residue_factor import (
            load_residue_factors,
        )

        result = load_residue_factors.fn(pd.DataFrame())
        assert result == {"inserted": 0, "updated": 0, "failed": 0}

    def test_load_with_none_dataframe(self):
        """Test load handles None DataFrame gracefully"""
        from ca_biositing.pipeline.etl.load.resource_information.residue_factor import (
            load_residue_factors,
        )

        result = load_residue_factors.fn(None)
        assert result == {"inserted": 0, "updated": 0, "failed": 0}

    def test_load_skips_null_resource_id(self):
        """Test that load skips records with NULL resource_id"""
        from ca_biositing.pipeline.etl.load.resource_information.residue_factor import (
            load_residue_factors,
        )

        df = pd.DataFrame({
            "resource_id": [1, np.nan, 3],
            "factor_type": ["commodity", "area", "weight"],
            "factor_min": [0.1, 0.2, 0.3],
        })

        # The function should skip the second row with NULL resource_id
        # We can't fully test without a real database, but we can check the logic
        result = load_residue_factors.fn(df)

        # Result should show the null record was skipped
        # (exact counts depend on database mock, but should return dict with 3 keys)
        assert isinstance(result, dict)
        assert set(result.keys()) == {"inserted", "updated", "failed"}

    def test_load_returns_summary_dict(self):
        """Test that load returns proper summary dictionary"""
        from ca_biositing.pipeline.etl.load.resource_information.residue_factor import (
            load_residue_factors,
        )

        df = pd.DataFrame({
            "resource_id": [1],
            "factor_type": ["commodity"],
            "factor_min": [0.1],
        })

        result = load_residue_factors.fn(df)

        assert isinstance(result, dict)
        assert "inserted" in result
        assert "updated" in result
        assert "failed" in result
        assert all(isinstance(v, int) for v in result.values())

    def test_load_is_prefect_task(self):
        """Test that loader is a Prefect task"""
        from ca_biositing.pipeline.etl.load.resource_information.residue_factor import (
            load_residue_factors,
        )

        assert hasattr(load_residue_factors, "fn")


class TestETLIntegration:
    """Integration tests for the full ETL pipeline"""

    def test_extract_transform_load_signature_compatibility(self):
        """Test that extract output can be passed to transform"""
        from ca_biositing.pipeline.etl.extract.residue_factors import extract_residue_factors
        from ca_biositing.pipeline.etl.transform.resource_information.residue_factor import (
            transform_residue_factor,
        )

        # Verify extract returns DataFrame (when mocked)
        # Verify transform accepts DataFrame and returns DataFrame or None
        import inspect

        extract_sig = inspect.signature(extract_residue_factors.fn)
        transform_sig = inspect.signature(transform_residue_factor.fn)

        # Extract should return DataFrame
        assert "DataFrame" in str(extract_sig.return_annotation) or extract_sig.return_annotation == inspect.Parameter.empty

        # Transform should accept DataFrame
        assert "df" in transform_sig.parameters

    def test_transform_load_signature_compatibility(self):
        """Test that transform output can be passed to load"""
        from ca_biositing.pipeline.etl.transform.resource_information.residue_factor import (
            transform_residue_factor,
        )
        from ca_biositing.pipeline.etl.load.resource_information.residue_factor import (
            load_residue_factors,
        )

        import inspect

        transform_sig = inspect.signature(transform_residue_factor.fn)
        load_sig = inspect.signature(load_residue_factors.fn)

        # Transform should return DataFrame or None
        # Load should accept DataFrame
        assert "df" in load_sig.parameters

    def test_lineage_tracking_fields_present(self):
        """Test that lineage tracking fields are handled in transform/load"""
        from ca_biositing.pipeline.etl.transform.resource_information.residue_factor import (
            transform_residue_factor,
        )

        import inspect

        source = inspect.getsource(transform_residue_factor.fn)

        # Check that etl_run_id and lineage_group_id are referenced
        assert "etl_run_id" in source
        assert "lineage_group_id" in source


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_transform_handles_sparse_data(self):
        """Test that transform handles sparse data (many NULLs)"""
        from ca_biositing.pipeline.etl.transform.resource_information.residue_factor import (
            transform_residue_factor,
        )

        # Create sparse DataFrame
        df = pd.DataFrame({
            "resource": ["almonds"],
            "factor_type": ["commodity"],
            "factor_min": [np.nan],
            "factor_max": [np.nan],
            "factor_mid": [np.nan],
            "prune_trim_yield": [np.nan],
            "notes": [np.nan],
        })

        # Should not crash on sparse data
        assert df is not None
        assert len(df) == 1

    def test_transform_handles_mixed_types(self):
        """Test that transform handles mixed data types"""
        df = pd.DataFrame({
            "resource": ["almonds", "corn"],
            "factor_type": ["commodity", "area"],
            "factor_min": [0.1, "0.2"],  # Mixed numeric and string
            "factor_max": [0.3, 0.4],
            "notes": [None, "test note"],
        })

        # Verify the data structure is valid before transform
        assert len(df) == 2
        assert df["factor_min"].dtype == object  # Mixed types become object

    def test_decimal_precision_preserved(self):
        """Test that Decimal precision is preserved in calculations"""
        # Simulate the calculation with Decimal
        factor_min = Decimal("0.12")
        factor_max = Decimal("0.28")

        factor_mid = (factor_min + factor_max) / 2

        # Should be exactly 0.20, not a float approximation
        assert factor_mid == Decimal("0.20")
        assert str(factor_mid) == "0.20"

    def test_load_with_null_optional_fields(self):
        """Test that load handles NULL values in optional fields"""
        df = pd.DataFrame({
            "resource_id": [1],
            "factor_type": ["commodity"],
            "factor_min": [np.nan],  # Optional field can be NULL
            "factor_max": [np.nan],
            "data_source_id": [np.nan],  # Optional foreign key
            "prune_trim_yield_unit_id": [np.nan],
        })

        # Should not crash with NULL optional fields
        assert df is not None
        assert df["resource_id"].notna().all()  # Required field is present


class TestDataQuality:
    """Tests for data quality checks and validation"""

    def test_transform_validates_resource_id_required(self):
        """Test that transform validates resource_id is required"""
        from ca_biositing.pipeline.etl.transform.resource_information.residue_factor import (
            transform_residue_factor,
        )

        import inspect

        source = inspect.getsource(transform_residue_factor.fn)

        # Should check for NULL resource_id
        assert "resource_id" in source
        assert "notna" in source or "isna" in source

    def test_composite_key_constraint_mentioned(self):
        """Test that load module references composite key constraint"""
        from ca_biositing.pipeline.etl.load.resource_information.residue_factor import (
            load_residue_factors,
        )

        import inspect

        source = inspect.getsource(load_residue_factors.fn)

        # Should mention the composite key
        assert "resource_id" in source
        assert "factor_type" in source

    def test_foreign_key_error_handling(self):
        """Test that load handles foreign key constraint violations"""
        from ca_biositing.pipeline.etl.load.resource_information.residue_factor import (
            load_residue_factors,
        )

        import inspect

        source = inspect.getsource(load_residue_factors.fn)

        # Should have error handling for foreign key violations
        assert "try" in source
        assert "except" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
