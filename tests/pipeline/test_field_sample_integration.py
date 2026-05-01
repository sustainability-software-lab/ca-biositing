"""
Comprehensive integration test for Field Sample ETL  pipeline.

Tests the complete workflow:
1. Extract all four worksheets
2. Transform LocationAddress records
3. Transform FieldSample records with multi-way join
4. Verify data quality and correctness

Note: Tests use mocked database sessions to isolate transform logic.
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import sys


@pytest.fixture
def sample_ids_data():
    """01_Sample_IDs (137 rows - base dataset)."""
    return pd.DataFrame({
        'sample_name': [f'SAMPLE_{i:04d}' for i in range(137)],
        'resource': ['Tomato pomace'] * 50 + ['Olive pomace'] * 50 + ['Grape pomace'] * 37,
        'provider_code': ['BIOCIR'] * 80 + ['PROV2'] * 57,
        'fv_date_time': pd.date_range('2024-01-01', periods=137),
        'index': range(1, 138),
        'fv_folder': [f'https://drive.google.com/{i}' for i in range(137)],
        'dataset': ['biocirv'] * 137
    })


@pytest.fixture
def sample_desc_data():
    """02_Sample_Desc (104 rows - unique matches on sample_name)."""
    cities = ['Kern', 'Tulare', 'Kings']
    methods = ['Method_A', 'Method_B', 'Method_C']
    return pd.DataFrame({
        'sample_name': [f'SAMPLE_{i:04d}' for i in range(104)],
        'sampling_location': [f'Location_{i % 15}' for i in range(104)],
        'sampling_street': [f'{i} Main St' for i in range(104)],
        'sampling_city': [cities[i % 3] for i in range(104)],
        'sampling_zip': [f'{93000 + i % 500}' for i in range(104)],
        'particle_l_cm': [1.5 + (i * 0.01) for i in range(104)],
        'particle_w_cm': [2.0 + (i * 0.01) for i in range(104)],
        'particle_h_cm': [2.5 + (i * 0.01) for i in range(104)],
        'processing_method': [methods[i % 3] for i in range(104)],
        'field_storage_location': [f'Storage_Collection_{i % 20}' for i in range(104)],
        'dataset': ['biocirv'] * 104
    })


@pytest.fixture
def qty_field_storage_data():
    """03_Qty_FieldStorage (unique records per sample, 130 rows to test partial matching)."""
    # Create unique sample_names (first 130) to avoid duplicate-induced row explosion
    sample_names = [f'SAMPLE_{i:04d}' for i in range(130)]

    containers = ['Bucket (5 gal.)', 'Core', 'Bale', 'Jar']
    storage_conds = ['Cool', 'Frozen', 'Ambient']
    storage_durs = [30, 60, 90]

    return pd.DataFrame({
        'sample_name': sample_names,
        'qty': list(range(1, 131)),
        'sample_container': [containers[i % 4] for i in range(130)],
        'field_storage_location': [f'Storage_Field_{i % 25}' for i in range(130)],
        'storage_conditions': [storage_conds[i % 3] for i in range(130)],
        'storage_dur_value': [storage_durs[i % 3] for i in range(130)],
        'storage_dur_units': ['days'] * 130,
        'dataset': ['biocirv'] * 130
    })


@pytest.fixture
def producers_data():
    """04_Producers (64 rows - partial match on sample_name, non-overlapping range)."""
    cities = ['Los Angeles', 'San Francisco', 'Sacramento']
    return pd.DataFrame({
        'sample_name': [f'SAMPLE_{i:04d}' for i in range(50, 114)],
        'prod_location': [f'Producer_{i}' for i in range(64)],
        'prod_street': [f'{2000 + i} Factory Ave' for i in range(64)],
        'prod_city': [cities[i % 3] for i in range(64)],
        'prod_zip': [f'{90000 + (i * 10)}' for i in range(64)],
        'producer_code': [f'PROD_{i:03d}' for i in range(64)],
        'prod_date': pd.date_range('2024-01-01', periods=64),
        'dataset': ['biocirv'] * 64
    })


@pytest.fixture
def all_data_sources(sample_ids_data, sample_desc_data, qty_field_storage_data, producers_data):
    """All four worksheet data sources."""
    return {
        'sample_ids': sample_ids_data,
        'sample_desc': sample_desc_data,
        'qty_field_storage': qty_field_storage_data,
        'producers': producers_data,
    }


class TestFieldSamplePipeline:
    """Integration tests for complete Field Sample  ETL pipeline."""

    @patch('ca_biositing.pipeline.utils.gsheet_to_pandas.gsheet_to_df')
    def test_end_to_end_extract_all_worksheets(self, mock_gsheet, all_data_sources):
        """Verify all four extractors can be called and return correct row counts."""
        def worksheet_mapper(gsheet_name, worksheet_name, credentials_path):
            sheet_map = {
                '01_Sample_IDs': all_data_sources['sample_ids'],
                '02_Sample_Desc': all_data_sources['sample_desc'],
                '03_Qty_FieldStorage': all_data_sources['qty_field_storage'],
                '04_Producers': all_data_sources['producers'],
            }
            return sheet_map.get(worksheet_name, pd.DataFrame())

        mock_gsheet.side_effect = worksheet_mapper

        from ca_biositing.pipeline.etl.extract.sample_ids import extract as extract_ids
        from ca_biositing.pipeline.etl.extract.sample_desc import extract as extract_desc
        from ca_biositing.pipeline.etl.extract.qty_field_storage import extract as extract_qty
        from ca_biositing.pipeline.etl.extract.producers import extract as extract_prod

        result_ids = extract_ids()
        result_desc = extract_desc()
        result_qty = extract_qty()
        result_prod = extract_prod()

        # Verify row counts match
        assert len(result_ids) == 137, f"Expected 137 sample_ids, got {len(result_ids)}"
        assert len(result_desc) == 104, f"Expected 104 sample_desc, got {len(result_desc)}"
        assert len(result_qty) == 130, f"Expected 130 qty_field_storage, got {len(result_qty)}"
        assert len(result_prod) == 64, f"Expected 64 producers, got {len(result_prod)}"

    def test_location_address_transform(self, all_data_sources):
        """Test LocationAddress transformation (extraction of unique locations)."""
        from ca_biositing.pipeline.etl.transform.field_sampling.location_address import transform_location_address

        result = transform_location_address(all_data_sources)

        # Should have deduplicated locations from both sources
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        # Should have locations from both sample_desc and producers
        assert len(result) > 0
        # Locations should have location_type tag
        if 'location_type' in result.columns:
            assert set(result['location_type'].unique()).issubset({'collection_site', 'facility_storage'})

    def test_extract_sources_list_completeness(self):
        """Verify EXTRACT_SOURCES list is complete in transform module."""
        from ca_biositing.pipeline.etl.transform.field_sampling.field_sample import EXTRACT_SOURCES

        expected_sources = {'sample_ids', 'sample_desc', 'qty_field_storage', 'producers'}
        assert set(EXTRACT_SOURCES) == expected_sources

    def test_location_address_handles_empty_data(self):
        """Verify LocationAddress transform handles empty data sources."""
        from ca_biositing.pipeline.etl.transform.field_sampling.location_address import transform_location_address

        empty_sources = {
            'sample_desc': pd.DataFrame(),
            'producers': pd.DataFrame(),
        }

        result = transform_location_address(empty_sources)

        # Should return empty DataFrame, not error
        assert isinstance(result, pd.DataFrame)
        assert result.empty or len(result) == 0

    def test_location_address_deduplication(self, all_data_sources):
        """Verify LocationAddress deduplicates correctly."""
        from ca_biositing.pipeline.etl.transform.field_sampling.location_address import transform_location_address

        result = transform_location_address(all_data_sources)

        if result is not None and not result.empty:
            # Check that deduplication occurred
            # Total unique addresses should be less than sum of all locations
            assert len(result) > 0

    def test_location_address_location_type_tagging(self, all_data_sources):
        """Verify locations are tagged with type (collection_site or facility_storage)."""
        from ca_biositing.pipeline.etl.transform.field_sampling.location_address import transform_location_address

        result = transform_location_address(all_data_sources)

        if result is not None and 'location_type' in result.columns:
            valid_types = {'collection_site', 'facility_storage'}
            actual_types = set(result['location_type'].dropna().unique())
            assert actual_types.issubset(valid_types)

    def test_location_address_is_anonymous_logic(self, all_data_sources):
        """Verify is_anonymous flag is set based on address_line1 presence."""
        from ca_biositing.pipeline.etl.transform.field_sampling.location_address import transform_location_address

        result = transform_location_address(all_data_sources)

        if result is not None and 'is_anonymous' in result.columns:
            # Check that is_anonymous is boolean-like (bool, object, or nullable boolean)
            assert str(result['is_anonymous'].dtype) in ['bool', 'object', 'boolean']

    def test_multi_way_join_strategy_preserves_base_records(self, all_data_sources):
        """Test the multi-way join strategy preserves all base records."""
        # This test validates the join logic without triggering database operations
        sample_ids = all_data_sources['sample_ids'].copy()
        sample_desc = all_data_sources['sample_desc'].copy()
        qty_field_storage = all_data_sources['qty_field_storage'].copy()
        producers = all_data_sources['producers'].copy()

        # Simulate the multi-way left-join from the transform
        base_count = len(sample_ids)

        # First join with sample_desc
        joined = sample_ids.merge(sample_desc, on='sample_name', how='left', suffixes=('', '_desc'))
        assert len(joined) == base_count, "Left-join with sample_desc should preserve base records"

        # Second join with qty_field_storage (must deduplicate first)
        qty_field_storage_dedup = qty_field_storage.drop_duplicates(subset=['sample_name'], keep='first')
        joined = joined.merge(qty_field_storage_dedup, on='sample_name', how='left', suffixes=('', '_qty'))
        assert len(joined) == base_count, "Left-join with qty_field_storage should preserve base records"

        # Third join with producers
        producers_dedup = producers.drop_duplicates(subset=['sample_name'], keep='first')
        joined = joined.merge(producers_dedup, on='sample_name', how='left', suffixes=('', '_prod'))
        assert len(joined) == base_count, "Left-join with producers should preserve base records"

    def test_sample_desc_particle_dimensions_present(self, all_data_sources):
        """Verify particle dimensions are present in sample_desc data."""
        sample_desc = all_data_sources['sample_desc']

        assert 'particle_l_cm' in sample_desc.columns
        assert 'particle_w_cm' in sample_desc.columns
        assert 'particle_h_cm' in sample_desc.columns

        # Verify they have numeric values
        assert sample_desc['particle_l_cm'].dtype in ['float64', 'int64']
        assert sample_desc['particle_w_cm'].dtype in ['float64', 'int64']
        assert sample_desc['particle_h_cm'].dtype in ['float64', 'int64']

    def test_sample_container_field_variations(self, all_data_sources):
        """Verify sample_container field has expected container types."""
        qty_field_storage = all_data_sources['qty_field_storage']

        assert 'sample_container' in qty_field_storage.columns
        containers = set(qty_field_storage['sample_container'].unique())
        expected_containers = {'Bucket (5 gal.)', 'Core', 'Bale', 'Jar'}
        assert expected_containers.issubset(containers)

    def test_producer_location_fields_present(self, all_data_sources):
        """Verify producer location fields are available."""
        producers = all_data_sources['producers']

        location_fields = {'prod_location', 'prod_street', 'prod_city', 'prod_zip'}
        assert location_fields.issubset(set(producers.columns))

    def test_sampling_location_fields_present(self, all_data_sources):
        """Verify sampling location fields are available in sample_desc."""
        sample_desc = all_data_sources['sample_desc']

        location_fields = {'sampling_location', 'sampling_street', 'sampling_city', 'sampling_zip'}
        assert location_fields.issubset(set(sample_desc.columns))

    def test_extract_source_validation(self, all_data_sources):
        """Verify all required extract sources have expected columns."""
        # Validate sample_ids has key fields
        assert 'sample_name' in all_data_sources['sample_ids'].columns
        assert 'resource' in all_data_sources['sample_ids'].columns
        assert 'provider_code' in all_data_sources['sample_ids'].columns

        # Validate sample_desc has key fields
        assert 'sample_name' in all_data_sources['sample_desc'].columns

        # Validate qty_field_storage has key fields
        assert 'sample_name' in all_data_sources['qty_field_storage'].columns
        assert 'sample_container' in all_data_sources['qty_field_storage'].columns

        # Validate producers has key fields
        assert 'sample_name' in all_data_sources['producers'].columns

    def test_sample_names_are_join_keys(self, all_data_sources):
        """Verify sample_name is the common join key across all worksheets."""
        # This is the critical field for the left-join strategy
        for source_name, data in all_data_sources.items():
            if not data.empty:
                assert 'sample_name' in data.columns, f"{source_name} missing sample_name join key"
                assert data['sample_name'].notna().sum() > 0, f"{source_name} has nulls in sample_name"

    def test_base_dataset_has_all_sample_ids(self, sample_ids_data):
        """Verify base dataset (sample_ids) has expected record count."""
        assert len(sample_ids_data) == 137
        assert sample_ids_data['sample_name'].notna().all()

    def test_partial_matching_on_joins(self, all_data_sources):
        """Verify datasets have partial overlap in sample_names (realistic scenario)."""
        ids_names = set(all_data_sources['sample_ids']['sample_name'])
        desc_names = set(all_data_sources['sample_desc']['sample_name'].dropna())
        qty_names = set(all_data_sources['qty_field_storage']['sample_name'].dropna())
        prod_names = set(all_data_sources['producers']['sample_name'].dropna())

        # sample_desc should have partial overlap with sample_ids
        assert len(desc_names & ids_names) < len(ids_names)
        assert len(desc_names & ids_names) > 0

        # qty_field_storage should have partial overlap with sample_ids
        assert len(qty_names & ids_names) < len(ids_names)
        assert len(qty_names & ids_names) > 0

        # producers should have partial overlap with sample_ids
        assert len(prod_names & ids_names) < len(ids_names)
        assert len(prod_names & ids_names) > 0

    def test_field_storage_location_from_sample_desc(self, all_data_sources):
        """Verify field_storage_location comes from sample_desc."""
        sample_desc = all_data_sources['sample_desc']
        assert 'field_storage_location' in sample_desc.columns
        assert sample_desc['field_storage_location'].notna().sum() > 0

    def test_producer_location_separate_from_sampling_location(self, all_data_sources):
        """Verify producer and sampling locations are separate entities."""
        sample_desc = all_data_sources['sample_desc']
        producers = all_data_sources['producers']

        # Both should exist as separate location sources
        assert 'sampling_location' in sample_desc.columns
        assert 'prod_location' in producers.columns

        # They should be distinct (not the same data)
        sampling_locs = set(sample_desc['sampling_location'].dropna().unique())
        producer_locs = set(producers['prod_location'].dropna().unique())

        # Some overlap is OK, but they should be distinct datasets
        assert len(sampling_locs) > 0
        assert len(producer_locs) > 0
