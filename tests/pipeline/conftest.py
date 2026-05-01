"""
Pytest configuration and fixtures for Field Sample ETL  tests.
"""

import pytest
import pandas as pd
import os
from unittest.mock import MagicMock, patch
from pathlib import Path


@pytest.fixture
def sample_ids_fixture():
    """Mock data for 01_Sample_IDs worksheet (137 rows expected)."""
    return pd.DataFrame({
        'sample_name': [f'S_{i:03d}' for i in range(137)],
        'resource': ['Tomato pomace', 'Olive pomace', 'Grape pomace'] * 45 + ['Tomato pomace'],
        'provider_code': ['BIOCIR', 'BIOCIR2', 'PROV3'] * 45 + ['BIOCIR'],
        'fv_date_time': pd.date_range('2024-01-01', periods=137, freq='D'),
        'index': range(1, 138),
        'fv_folder': [f'https://drive.google.com/folder_{i}' for i in range(137)],
        'dataset': ['biocirv'] * 137
    })


@pytest.fixture
def sample_desc_fixture():
    """Mock data for 02_Sample_Desc worksheet (104 rows expected)."""
    # Not all sample_ids will have corresponding desc records (simulating left-join)
    sample_names = [f'S_{i:03d}' for i in range(104)]
    return pd.DataFrame({
        'sample_name': sample_names,
        'sampling_location': [f'Location_{i}' for i in range(104)],
        'sampling_street': [f'{i} Main St' for i in range(104)],
        'sampling_city': [f'County_{i % 10}' for i in range(104)],
        'sampling_zip': [f'{90210 + i}' for i in range(104)],
        'particle_l_cm': [1.5 + i * 0.01 for i in range(104)],
        'particle_w_cm': [2.0 + i * 0.01 for i in range(104)],
        'particle_h_cm': [2.5 + i * 0.01 for i in range(104)],
        'processing_method': ['Method_A', 'Method_B', 'Method_C'] * 34 + ['Method_A'],
        'field_storage_location': [f'Storage_{i}' for i in range(104)],
        'dataset': ['biocirv'] * 104
    })


@pytest.fixture
def qty_field_storage_fixture():
    """Mock data for 03_Qty_FieldStorage worksheet (142 rows expected)."""
    # Some sample_names repeated (multiple quantity records per sample)
    sample_names = []
    for i in range(80):
        sample_names.append(f'S_{i:03d}')
    # Add some duplicates to simulate multiple records per sample
    sample_names.extend([f'S_{i:03d}' for i in range(42)])

    return pd.DataFrame({
        'sample_name': sample_names,
        'qty': list(range(1, 143)),
        'sample_container': ['Bucket (5 gal.)', 'Core', 'Bale', 'Jar'] * 35 + ['Bucket (5 gal.)'],
        'field_storage_location': [f'FieldStorage_{i}' for i in range(142)],
        'storage_conditions': ['Cool', 'Frozen', 'Ambient', 'Cool'] * 35 + ['Cool'],
        'storage_dur_value': [30, 60, 90] * 47 + [30],
        'storage_dur_units': ['days', 'days', 'days'] * 47 + ['days'],
        'dataset': ['biocirv'] * 142
    })


@pytest.fixture
def producers_fixture():
    """Mock data for 04_Producers worksheet (64 rows expected)."""
    sample_names = [f'S_{i:03d}' for i in range(50, 114)]  # Overlap with other datasets
    return pd.DataFrame({
        'sample_name': sample_names,
        'prod_location': [f'Producer_{i}' for i in range(64)],
        'prod_street': [f'{i} Factory Ave' for i in range(64)],
        'prod_city': [f'ProducerCity_{i % 5}' for i in range(64)],
        'prod_zip': [f'{95000 + i}' for i in range(64)],
        'producer_code': [f'PROD_{i:03d}' for i in range(64)],
        'prod_date': pd.date_range('2024-01-01', periods=64, freq='D'),
        'dataset': ['biocirv'] * 64
    })


@pytest.fixture
def all_data_sources(sample_ids_fixture, sample_desc_fixture, qty_field_storage_fixture, producers_fixture):
    """Complete data sources dictionary for integration tests."""
    return {
        'sample_ids': sample_ids_fixture,
        'sample_desc': sample_desc_fixture,
        'qty_field_storage': qty_field_storage_fixture,
        'producers': producers_fixture
    }


@pytest.fixture
def mock_prefect_logger(monkeypatch):
    """Mock Prefect logger for tasks."""
    mock_logger = MagicMock()

    def mock_get_run_logger():
        return mock_logger

    # Patch both possible import locations
    monkeypatch.setattr('prefect.get_run_logger', mock_get_run_logger)

    return mock_logger


@pytest.fixture
def mock_database_session(monkeypatch):
    """Mock database session for lookup operations."""
    mock_session = MagicMock()
    mock_session.exec.return_value.all.return_value = []
    mock_session.exec.return_value.first.return_value = None

    return mock_session
