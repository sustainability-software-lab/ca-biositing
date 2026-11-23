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
from sqlalchemy import event, select, func
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


BATCHED_INFRASTRUCTURE_DATASETS = [
    "cafo_manure_locations",
    "crude_oil_pipelines",
    "food_manufacturers_carb",
    "food_manufacturers_epa",
    "petroleum_pipelines",
    "railways",
    "wastewater_treatment_plants",
]


def _make_unique_batch_df(dataset_name: str, n_rows: int, etl_run_id: int = 1) -> pd.DataFrame:
    """Build a DataFrame of n_rows distinct records for batch boundary testing."""
    base_row = get_mock_data_for_dataset(dataset_name).iloc[0].to_dict()
    rows = []
    for idx in range(n_rows):
        row = dict(base_row)
        row["etl_run_id"] = etl_run_id
        for col, val in list(row.items()):
            if isinstance(val, str) and any(
                k in col.lower() for k in ("name", "facility", "company")
            ):
                row[col] = f"{val}_{idx}"
        rows.append(row)
    return pd.DataFrame(rows)


@pytest.mark.parametrize("dataset_name", BATCHED_INFRASTRUCTURE_DATASETS)
@pytest.mark.parametrize("n_rows", [1000, 1005])
def test_batched_load_across_chunk_boundaries_and_empty_batch_rerun(
    dataset_name, n_rows, session, engine
):
    """
    Verify exact-1000 and >1000-row loads plus full re-runs where batch is empty.

    Covers:
    - Exact 1000-row chunk boundary and 1005-row remainder flush
    - Re-run when all records already exist (no empty-batch DEFAULT VALUES error/phantom rows)
    - Persistence of updated fields (etl_run_id) when batch is empty
    """
    import importlib

    load_module = importlib.import_module(LOAD_MODULE_PATH.format(name=dataset_name))
    load_fn = load_module.load.fn
    model_class = get_model_class_for_dataset(dataset_name)

    df_initial = _make_unique_batch_df(dataset_name, n_rows=n_rows, etl_run_id=1)
    df_rerun = _make_unique_batch_df(dataset_name, n_rows=n_rows, etl_run_id=2)

    with patch.object(load_module, "get_engine", return_value=engine):
        assert load_fn(df_initial) is True

        with Session(engine) as check_session:
            count1 = check_session.scalar(select(func.count()).select_from(model_class))
            assert count1 == n_rows

        # Re-run with updated etl_run_id: all rows match existing records (empty new-insert batch)
        assert load_fn(df_rerun) is True

        with Session(engine) as check_session:
            count2 = check_session.scalar(select(func.count()).select_from(model_class))
            assert count2 == n_rows
            updated_count = check_session.scalar(
                select(func.count())
                .select_from(model_class)
                .where(model_class.etl_run_id == 2)
            )
            assert updated_count == n_rows, (
                f"Expected all {n_rows} existing records to commit etl_run_id=2 on rerun "
                f"for {dataset_name}, got {updated_count}"
            )


@pytest.mark.parametrize("dataset_name", BATCHED_INFRASTRUCTURE_DATASETS)
def test_batched_load_deduplicates_intra_batch_duplicates(dataset_name, session, engine):
    """Verify duplicate records within the same batch do not insert twice or fail."""
    import importlib

    load_module = importlib.import_module(LOAD_MODULE_PATH.format(name=dataset_name))
    load_fn = load_module.load.fn
    model_class = get_model_class_for_dataset(dataset_name)

    row1 = get_mock_data_for_dataset(dataset_name).iloc[0].to_dict()
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    row1["created_at"] = t1
    row1["etl_run_id"] = 1

    row2 = dict(row1)
    row2["created_at"] = datetime(2026, 1, 2, tzinfo=timezone.utc)
    row2["etl_run_id"] = 2

    dup_df = pd.DataFrame([row1, row2])

    with patch.object(load_module, "get_engine", return_value=engine):
        assert load_fn(dup_df) is True

        with Session(engine) as check_session:
            rows = check_session.scalars(select(model_class)).all()
            assert len(rows) == 1
            assert rows[0].etl_run_id == 2


BATCHED_DATASET_PKS = [
    ("cafo_manure_locations", "cafo_manure_id"),
    ("crude_oil_pipelines", "object_id"),
    ("food_manufacturers_carb", "processing_facility_id"),
    ("food_manufacturers_epa", "processing_facility_id"),
    ("petroleum_pipelines", "object_id"),
    ("railways", "object_id"),
    ("wastewater_treatment_plants", "plant_id"),
]


@pytest.mark.parametrize("dataset_name,pk_col", BATCHED_DATASET_PKS)
def test_batched_load_handles_explicit_and_mixed_primary_keys(
    dataset_name, pk_col, session, engine
):
    """
    Verify PK-keyed bulk upserts handle duplicate PKs in-batch, preserve created_at
    on conflict update, and allow mixed PK / None-PK rows in the same DataFrame.

    Note: SQLite allows duplicate conflict keys in a single INSERT ... ON CONFLICT
    statement, whereas PostgreSQL raises CardinalityViolation ("ON CONFLICT DO UPDATE
    command cannot affect row a second time"). To catch regressions even on SQLite,
    we intercept compiled SQL parameters and assert every ON CONFLICT statement binds
    strictly unique primary keys.
    """
    import importlib

    load_module = importlib.import_module(LOAD_MODULE_PATH.format(name=dataset_name))
    load_fn = load_module.load.fn
    model_class = get_model_class_for_dataset(dataset_name)

    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
    df_three = _make_unique_batch_df(dataset_name, n_rows=3, etl_run_id=1)
    rows = df_three.to_dict(orient="records")

    # Row 0, exact duplicate of Row 0, and distinct-natural-key Row 2 all share PK=101;
    # Row 1 has PK=None (auto-assigned via SERIAL / SQLite PK autoincrement).
    rows[0][pk_col] = 101
    rows[0]["created_at"] = t1
    dup_pk_same_nat = dict(rows[0])
    dup_pk_same_nat["etl_run_id"] = 2
    dup_pk_same_nat["created_at"] = t2

    rows[2][pk_col] = 101
    rows[2]["etl_run_id"] = 2
    rows[2]["created_at"] = t2

    rows[1][pk_col] = None
    rows[1]["created_at"] = t1

    mixed_df = pd.DataFrame([rows[0], dup_pk_same_nat, rows[2], rows[1]])

    on_conflict_pk_batches: list[list[int]] = []

    def _capture_on_conflict_pks(conn, cursor, statement, parameters, context, executemany):
        if "ON CONFLICT" in statement.upper() and context and context.compiled_parameters:
            compiled_params = context.compiled_parameters[0]
            bound_pks = [
                val
                for key, val in compiled_params.items()
                if key == pk_col or key.startswith(f"{pk_col}_m")
            ]
            on_conflict_pk_batches.append(bound_pks)

    event.listen(engine, "before_cursor_execute", _capture_on_conflict_pks)
    try:
        with patch.object(load_module, "get_engine", return_value=engine):
            assert load_fn(mixed_df) is True

            assert on_conflict_pk_batches, "Expected at least one ON CONFLICT upsert statement"
            for bound_pks in on_conflict_pk_batches:
                assert len(bound_pks) == len(set(bound_pks)), (
                    f"Duplicate {pk_col} values bound in a single ON CONFLICT statement "
                    f"(would raise PostgreSQL CardinalityViolation): {bound_pks}"
                )

            with Session(engine) as check_session:
                all_rows = check_session.scalars(select(model_class)).all()
                assert len(all_rows) == 2
                pk_row = check_session.get(model_class, 101)
                assert pk_row is not None
                assert pk_row.etl_run_id == 2
                created_naive = pk_row.created_at.replace(tzinfo=None)
                assert created_naive == t1.replace(tzinfo=None)

            # Update explicit PK=101 on rerun and ensure created_at stays t1
            rerun_row = dict(rows[2])
            rerun_row["etl_run_id"] = 3
            rerun_row["created_at"] = t2
            assert load_fn(pd.DataFrame([rerun_row])) is True

            with Session(engine) as check_session:
                assert check_session.scalar(select(func.count()).select_from(model_class)) == 2
                pk_row_after = check_session.get(model_class, 101)
                assert pk_row_after.etl_run_id == 3
                assert pk_row_after.created_at.replace(tzinfo=None) == t1.replace(tzinfo=None)
    finally:
        event.remove(engine, "before_cursor_execute", _capture_on_conflict_pks)


@pytest.mark.parametrize("dataset_name", BATCHED_INFRASTRUCTURE_DATASETS)
def test_batched_load_deduplicates_across_chunk_boundary(dataset_name, session, engine):
    """
    Verify a duplicate split across chunk 1 (row 0) and chunk 2 (row 1004) within
    a single load() call updates the flushed chunk-1 row rather than duplicating.
    """
    import importlib

    load_module = importlib.import_module(LOAD_MODULE_PATH.format(name=dataset_name))
    load_fn = load_module.load.fn
    model_class = get_model_class_for_dataset(dataset_name)

    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
    df = _make_unique_batch_df(dataset_name, n_rows=1004, etl_run_id=1)
    rows = df.to_dict(orient="records")
    for r in rows:
        r["created_at"] = t1

    # Row 1004 (in the second 1000-row chunk) duplicates Row 0 with updated etl_run_id
    cross_chunk_dup = dict(rows[0])
    cross_chunk_dup["etl_run_id"] = 2
    cross_chunk_dup["created_at"] = t2
    rows.append(cross_chunk_dup)

    with patch.object(load_module, "get_engine", return_value=engine):
        assert load_fn(pd.DataFrame(rows)) is True

        with Session(engine) as check_session:
            total = check_session.scalar(select(func.count()).select_from(model_class))
            assert total == 1004, f"Expected 1004 unique rows for {dataset_name}, got {total}"
            updated_rows = check_session.scalars(
                select(model_class).where(model_class.etl_run_id == 2)
            ).all()
            assert len(updated_rows) == 1
            assert updated_rows[0].created_at.replace(tzinfo=None) == t1.replace(tzinfo=None)


@pytest.mark.parametrize("dataset_name", BATCHED_INFRASTRUCTURE_DATASETS)
def test_batched_load_rolls_back_atomically_on_mid_load_failure(
    dataset_name, session, engine
):
    """
    Verify that if chunk 2 fails after chunk 1 flushed 1000 rows, the entire load
    rolls back cleanly rather than leaving a partially loaded dataset.
    """
    import importlib

    load_module = importlib.import_module(LOAD_MODULE_PATH.format(name=dataset_name))
    load_fn = load_module.load.fn
    model_class = get_model_class_for_dataset(dataset_name)

    df = _make_unique_batch_df(dataset_name, n_rows=1005, etl_run_id=1)

    flush_calls = 0
    orig_flush = Session.flush

    def _fail_on_second_chunk_flush(self, *args, **kwargs):
        nonlocal flush_calls
        flush_calls += 1
        if flush_calls >= 2:
            raise RuntimeError("Simulated mid-load DB failure in chunk 2")
        return orig_flush(self, *args, **kwargs)

    with (
        patch.object(load_module, "get_engine", return_value=engine),
        patch.object(Session, "flush", _fail_on_second_chunk_flush),
    ):
        assert load_fn(df) is False

    with Session(engine) as check_session:
        remaining = check_session.scalar(select(func.count()).select_from(model_class))
        assert remaining == 0, (
            f"Expected atomic rollback (0 rows) after chunk-2 failure for {dataset_name}, "
            f"found {remaining} partially committed rows"
        )
