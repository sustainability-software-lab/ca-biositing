# Infrastructure Duplicate Prevention Tests

## Overview

This test file (`test_infrastructure_duplicate_prevention.py`) contains
comprehensive tests to verify that all infrastructure ETL pipelines correctly
prevent duplicate entries when loading data.

## Purpose

The tests ensure that:

1. Running the load function twice with identical data does NOT create
   duplicates
2. The upsert logic correctly identifies existing records and updates them
3. Primary keys and unique constraints are properly enforced
4. Each of the 18 infrastructure pipelines handles duplicate prevention
   consistently

## Test Coverage

The tests cover all 18 infrastructure datasets:

- petroleum_pipelines
- biosolids_facilities
- cafo_manure_locations
- combustion_plants
- district_energy_systems
- ethanol_biorefineries
- food_processing_facilities
- landfills
- livestock_anaerobic_digesters
- msw_to_energy_anaerobic_digesters
- saf_and_renewable_diesel_plants
- wastewater_treatment_plants
- crude_oil_pipelines
- railways
- biodiesel_plants
- tomato_processors
- food_manufacturers_epa
- food_manufacturers_carb

## Test Functions

### 1. `test_load_prevents_duplicates_on_rerun`

**Purpose**: Core duplicate prevention test

**Scenario**: Simulates an ETL pipeline running twice with the same data

**Verification**:

- First load creates exactly 1 record
- Second load with identical data updates the existing record
- Final count is still 1 (no duplicates)
- The `updated_at` timestamp is tracked

**Why it matters**: This is the most common real-world scenario where ETL
pipelines are re-run for various reasons (failures, data refresh, etc.)

### 2. `test_load_with_multiple_unique_records`

**Purpose**: Test handling of multiple distinct records

**Scenario**: Load 3 different records, then reload the same 3 records

**Verification**:

- First load creates exactly 3 records
- Second load updates existing records without creating duplicates
- Final count is still 3

**Why it matters**: Ensures the upsert logic works correctly for batch
operations

### 3. `test_load_handles_null_values_without_duplicates`

**Purpose**: Test NULL value handling in duplicate detection

**Scenario**: Load records with NULL latitude/longitude twice

**Verification**:

- NULL values don't break duplicate detection logic
- Final count is 1 (no duplicates)

**Why it matters**: NULL comparisons can be tricky in SQL; this ensures they're
handled correctly

## Running the Tests

### Run all infrastructure duplicate prevention tests:

```bash
pixi run pytest src/ca_biositing/pipeline/tests/test_infrastructure_duplicate_prevention.py -v
```

### Run tests for a specific dataset:

```bash
pixi run pytest src/ca_biositing/pipeline/tests/test_infrastructure_duplicate_prevention.py -k "biodiesel_plants" -v
```

### Run just the core duplicate prevention test:

```bash
pixi run pytest src/ca_biositing/pipeline/tests/test_infrastructure_duplicate_prevention.py -k "test_load_prevents_duplicates_on_rerun" -v
```

### Run with verbose output and stop on first failure:

```bash
pixi run pytest src/ca_biositing/pipeline/tests/test_infrastructure_duplicate_prevention.py -v -x
```

## Test Statistics

- **Total test functions**: 3
- **Total infrastructure datasets**: 18
- **Total parameterized tests**: 54 (3 functions × 18 datasets)

## How It Works

### Mock Data Generation

The `get_mock_data_for_dataset()` function creates minimal valid data for each
infrastructure type. It includes:

- Common fields: `address_id`, `etl_run_id`, `lineage_group_id`, timestamps,
  coordinates
- Dataset-specific fields: unique identifiers and key fields used for duplicate
  detection

### Test Database

Tests use an in-memory SQLite database (via pytest fixtures from `conftest.py`)
to:

- Avoid affecting the real database
- Run quickly
- Provide clean state for each test
- Support concurrent test execution

### Mock Engine

The `get_engine()` function from `ca_biositing.pipeline.utils.engine` is mocked
to return the test database engine, ensuring all database operations happen in
the test environment.

## Expected Behavior

### ✅ PASS: Upsert logic is working correctly

- First load creates new records
- Second load with same data updates existing records
- No duplicates are created
- Total record count matches expectations

### ❌ FAIL: Duplicate detection is broken

If a test fails with "DUPLICATE DETECTED", it means:

1. The load function's duplicate checking logic (e.g., the `SELECT` statement
   checking for existing records) is not working
2. The `on_conflict_do_update` clause might be misconfigured
3. The primary key or unique constraint is not properly enforced

## Debugging Failed Tests

If a test fails:

1. **Check the error message** - It will specify which dataset failed and how
   many duplicates were created
2. **Examine the load function** - Look at
   `src/ca_biositing/pipeline/etl/load/infrastructure/{dataset_name}.py`
3. **Verify the duplicate detection query** - Check the `SELECT` statement that
   looks for existing records
4. **Check the upsert statement** - Ensure `on_conflict_do_update` uses the
   correct primary key
5. **Review the model** - Verify the primary key and unique constraints in the
   datamodel

## Integration with CI/CD

These tests should be run:

- Before merging any changes to infrastructure load functions
- As part of pre-commit checks
- In continuous integration pipelines
- Before production deployments

## Related Files

- Load functions: `src/ca_biositing/pipeline/etl/load/infrastructure/*.py`
- Data models:
  `src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/*.py`
- Flow definitions: `src/ca_biositing/pipeline/flows/*.py`
- Test fixtures: `src/ca_biositing/pipeline/tests/conftest.py`
