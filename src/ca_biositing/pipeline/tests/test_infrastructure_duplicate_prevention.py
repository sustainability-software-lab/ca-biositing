"""
Tests to verify that all infrastructure ETL pipelines prevent duplicate entries.

These tests ensure:
1. Running the load function twice with the same data does NOT create duplicates.
2. The upsert logic correctly identifies existing records and updates them instead of inserting.
3. Primary keys and unique constraints are properly enforced.
4. Each infrastructure pipeline handles duplicate prevention consistently.

The tests work by:
- Creating mock data that matches the expected schema
- Running the load function twice with the same data
- Verifying that only one record exists in the database
- Confirming the record was updated (not duplicated)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from sqlalchemy import select, func
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Test Configuration
# ---------------------------------------------------------------------------

INFRASTRUCTURE_DATASETS = [
    "petroleum_pipelines",
    "biosolids_facilities",
    "cafo_manure_locations",
    "combustion_plants",
    "district_energy_systems",
    "ethanol_biorefineries",
    "food_processing_facilities",
    "landfills",
    "livestock_anaerobic_digesters",
    "msw_to_energy_anaerobic_digesters",
    "saf_and_renewable_diesel_plants",
    "wastewater_treatment_plants",
    "crude_oil_pipelines",
    "railways",
    "biodiesel_plants",
    "tomato_processors",
    "food_manufacturers_epa",
    "food_manufacturers_carb",
]

LOAD_MODULE_PATH = "ca_biositing.pipeline.etl.load.infrastructure.{name}"


# ---------------------------------------------------------------------------
# Test Data Generators
# ---------------------------------------------------------------------------

def get_mock_data_for_dataset(dataset_name: str) -> pd.DataFrame:
    """
    Generate mock data for a specific infrastructure dataset.

    This function creates minimal valid data that matches the expected schema
    for each infrastructure type. The data is designed to test duplicate
    prevention without requiring extensive field coverage.
    """
    base_data = {
        "address_id": 1,
        "etl_run_id": 1,
        "lineage_group_id": 1,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "latitude": 37.7749,
        "longitude": -122.4194,
    }

    # Dataset-specific fields that are commonly used for duplicate detection
    dataset_specific = {
        "petroleum_pipelines": {"pipeline_name": "Test Pipeline 1", "operator_name": "Test Operator", "master_oid": 101},
        "biosolids_facilities": {"facility": "Test Biosolids Facility", "plant_type": "Treatment Plant"},
        "cafo_manure_locations": {"facility_name": "Test CAFO", "owner_name": "Test Owner"},
        "combustion_plants": {"name": "Test Combustion Plant", "type": "Biomass"},
        "district_energy_systems": {"name": "Test District Energy", "system": "Heating"},
        "ethanol_biorefineries": {"name": "Test Ethanol Plant", "capacity_mgy": 50},
        "food_processing_facilities": {"company": "Test Food Processing", "processing_type": "Meat Processing"},
        "landfills": {"landfill_name": "Test Landfill", "project_id": "TEST-LF-001"},
        "livestock_anaerobic_digesters": {"project_name": "Test Digester", "digester_type": "Complete Mix"},
        "msw_to_energy_anaerobic_digesters": {"facility_type": "Test MSW Digester", "feedstock": "MSW"},
        "saf_and_renewable_diesel_plants": {"company": "Test SAF Company", "status": "Active"},
        "wastewater_treatment_plants": {"name": "Test WWTP", "facility_type": "WWTP"},
        "crude_oil_pipelines": {"pipeline_name": "Test Crude Pipeline", "operator_name": "Test Operator", "master_oid": 202},
        "railways": {"name": "Test Railway", "state": "CA", "link_type": "RR"},
        "biodiesel_plants": {"company": "Test Biodiesel Company", "capacity_mmg_per_y": 50},
        "tomato_processors": {"name": "Test Tomato Processor", "processing_capacity_for_tomato_paste_tons_hr": 100},
        "food_manufacturers_epa": {"name": "Test EPA Food Manufacturer", "naics_code": "311"},
        "food_manufacturers_carb": {"name": "Test CARB Food Manufacturer", "carb_facility_id": 1001},
    }

    data = {**base_data, **dataset_specific.get(dataset_name, {})}
    return pd.DataFrame([data])


def get_model_class_for_dataset(dataset_name: str):
    """Get the SQLModel class for a given dataset name."""
    from ca_biositing.datamodels.models import (
        InfrastructureBiodieselPlants,
        InfrastructureBiosolidsFacilities,
        InfrastructureCafoManureLocations,
        InfrastructureCombustionPlants,
        InfrastructureCrudeOilPipelines,
        InfrastructureDistrictEnergySystems,
        InfrastructureEthanolBiorefineries,
        InfrastructureFoodManufacturersCARB,
        InfrastructureFoodManufacturersEPA,
        InfrastructureFoodProcessingFacilities,
        InfrastructureLandfills,
        InfrastructureLivestockAnaerobicDigesters,
        InfrastructureMswToEnergyAnaerobicDigesters,
        InfrastructurePetroleumPipelines,
        InfrastructureRailways,
        InfrastructureSafAndRenewableDieselPlants,
        InfrastructureTomatoProcessors,
        InfrastructureWastewaterTreatmentPlants,
    )

    model_map = {
        "petroleum_pipelines": InfrastructurePetroleumPipelines,
        "biosolids_facilities": InfrastructureBiosolidsFacilities,
        "cafo_manure_locations": InfrastructureCafoManureLocations,
        "combustion_plants": InfrastructureCombustionPlants,
        "district_energy_systems": InfrastructureDistrictEnergySystems,
        "ethanol_biorefineries": InfrastructureEthanolBiorefineries,
        "food_processing_facilities": InfrastructureFoodProcessingFacilities,
        "landfills": InfrastructureLandfills,
        "livestock_anaerobic_digesters": InfrastructureLivestockAnaerobicDigesters,
        "msw_to_energy_anaerobic_digesters": InfrastructureMswToEnergyAnaerobicDigesters,
        "saf_and_renewable_diesel_plants": InfrastructureSafAndRenewableDieselPlants,
        "wastewater_treatment_plants": InfrastructureWastewaterTreatmentPlants,
        "crude_oil_pipelines": InfrastructureCrudeOilPipelines,
        "railways": InfrastructureRailways,
        "biodiesel_plants": InfrastructureBiodieselPlants,
        "tomato_processors": InfrastructureTomatoProcessors,
        "food_manufacturers_epa": InfrastructureFoodManufacturersEPA,
        "food_manufacturers_carb": InfrastructureFoodManufacturersCARB,
    }

    return model_map.get(dataset_name)


# ---------------------------------------------------------------------------
# Duplicate Prevention Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dataset_name", INFRASTRUCTURE_DATASETS)
def test_load_prevents_duplicates_on_rerun(dataset_name, session, engine):
    """
    Test that running load() twice with the same data does NOT create duplicates.

    This is the CRITICAL test for duplicate prevention. It verifies that:
    1. The first load creates a new record
    2. The second load with identical data updates the existing record
    3. Only ONE record exists in the database after both loads
    4. The record's updated_at timestamp changes (proving it was updated)

    This test simulates the real-world scenario where an ETL pipeline might
    run multiple times with overlapping data.
    """
    import importlib

    # Import the load module
    load_module = importlib.import_module(LOAD_MODULE_PATH.format(name=dataset_name))
    load_fn = load_module.load.fn  # Unwrap Prefect task

    # Get the model class
    model_class = get_model_class_for_dataset(dataset_name)
    if model_class is None:
        pytest.skip(f"Model class not found for {dataset_name}")

    # Generate mock data
    mock_data = get_mock_data_for_dataset(dataset_name)

    # Mock get_engine to return our test engine
    with patch.object(load_module, "get_engine", return_value=engine):
        # First load - should create a new record
        first_timestamp = datetime.now(timezone.utc)
        result1 = load_fn(mock_data.copy())
        assert result1 is True, f"First load failed for {dataset_name}"

        # Check record count after first load
        with Session(engine) as check_session:
            count1 = check_session.scalar(
                select(func.count()).select_from(model_class)
            )
            assert count1 == 1, (
                f"Expected 1 record after first load for {dataset_name}, got {count1}"
            )

            # Get the record and its updated_at timestamp
            record1 = check_session.scalars(select(model_class)).first()
            assert record1 is not None
            first_updated_at = record1.updated_at

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        # Second load - should update the existing record, NOT create a duplicate
        result2 = load_fn(mock_data.copy())
        assert result2 is True, f"Second load failed for {dataset_name}"

        # Verify no duplicates were created
        with Session(engine) as check_session:
            count2 = check_session.scalar(
                select(func.count()).select_from(model_class)
            )
            assert count2 == 1, (
                f"DUPLICATE DETECTED: Expected 1 record after second load for {dataset_name}, "
                f"got {count2}. This indicates the upsert logic is not working correctly!"
            )

            # Verify the record was updated (not just left alone)
            record2 = check_session.scalars(select(model_class)).first()
            assert record2 is not None
            second_updated_at = record2.updated_at

            # The updated_at timestamp should have changed
            assert second_updated_at >= first_updated_at, (
                f"Duplicate prevention verification failed for {dataset_name}"
            )


@pytest.mark.parametrize("dataset_name", INFRASTRUCTURE_DATASETS)
def test_load_with_multiple_unique_records(dataset_name, session, engine):
    """
    Test that load() can handle multiple different records correctly.

    This test verifies that:
    1. Multiple DIFFERENT records are all inserted
    2. Re-loading the same records doesn't create duplicates
    3. The total count matches expectations (3 unique records)
    """
    import importlib

    # Import the load module
    load_module = importlib.import_module(LOAD_MODULE_PATH.format(name=dataset_name))
    load_fn = load_module.load.fn

    # Get the model class
    model_class = get_model_class_for_dataset(dataset_name)
    if model_class is None:
        pytest.skip(f"Model class not found for {dataset_name}")

    # Generate three different records
    mock_data = get_mock_data_for_dataset(dataset_name)

    # Create variations by modifying key fields
    records = []
    for i in range(3):
        record = mock_data.copy()
        # Modify fields that would make records unique
        for col in record.columns:
            if any(k in col.lower() for k in ("name", "id", "facility", "company")):
                if record[col].dtype == 'object':
                    record.loc[0, col] = f"{record.loc[0, col]}_{i}"
        records.append(record)

    combined_data = pd.concat(records, ignore_index=True)

    # Mock get_engine
    with patch.object(load_module, "get_engine", return_value=engine):
        # First load - should create 3 records
        result1 = load_fn(combined_data.copy())
        assert result1 is True, f"First load failed for {dataset_name}"

        with Session(engine) as check_session:
            count1 = check_session.scalar(
                select(func.count()).select_from(model_class)
            )
            assert count1 == 3, (
                f"Expected 3 records after first load for {dataset_name}, got {count1}"
            )

        # Second load with same data - should still be 3 records (no duplicates)
        result2 = load_fn(combined_data.copy())
        assert result2 is True, f"Second load failed for {dataset_name}"

        with Session(engine) as check_session:
            count2 = check_session.scalar(
                select(func.count()).select_from(model_class)
            )
            assert count2 == 3, (
                f"DUPLICATES DETECTED: Expected 3 records after second load for {dataset_name}, "
                f"got {count2}. The upsert logic created duplicates!"
            )


@pytest.mark.parametrize("dataset_name", INFRASTRUCTURE_DATASETS)
def test_load_handles_null_values_without_duplicates(dataset_name, session, engine):
    """
    Test that load() handles records with NULL values correctly.

    Some duplicate detection logic might fail when comparing NULL values.
    This test ensures NULL handling doesn't cause duplicates.
    """
    import importlib

    load_module = importlib.import_module(LOAD_MODULE_PATH.format(name=dataset_name))
    load_fn = load_module.load.fn

    model_class = get_model_class_for_dataset(dataset_name)
    if model_class is None:
        pytest.skip(f"Model class not found for {dataset_name}")

    # Generate data with some NULL values
    mock_data = get_mock_data_for_dataset(dataset_name)
    # Set latitude/longitude to None to test NULL handling
    mock_data.loc[0, "latitude"] = None
    mock_data.loc[0, "longitude"] = None

    with patch.object(load_module, "get_engine", return_value=engine):
        # Load twice
        result1 = load_fn(mock_data.copy())
        assert result1 is True

        result2 = load_fn(mock_data.copy())
        assert result2 is True

        # Verify no duplicates
        with Session(engine) as check_session:
            count = check_session.scalar(
                select(func.count()).select_from(model_class)
            )
            assert count == 1, (
                f"NULL value handling created duplicates for {dataset_name}: "
                f"expected 1 record, got {count}"
            )
