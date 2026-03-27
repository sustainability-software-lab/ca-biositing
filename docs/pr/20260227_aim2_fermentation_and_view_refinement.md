# PR Description: Aim 2 Fermentation ETL and Analytical View Refinement

## Overview

This PR encapsulates a series of enhancements and bug fixes focused on the Aim 2
(Bioconversion) ETL pipeline and the refinement of analytical materialized
views. Key highlights include the implementation of fermentation record
processing, the introduction of experimental vessel tracking, and critical fixes
to database views used for analysis.

## Changes

### 1. Aim 2 (Bioconversion) Pipeline Enhancements

- **Fermentation Record ETL:**
  - Implemented transformation logic in
    `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/fermentation_record.py`
    to handle complex fermentation data, including parameter mapping and
    validation.
  - Added loading logic in
    `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/fermentation_record.py`.
  - Integrated fermentation record processing into the `aim2_bioconversion` and
    `analysis_records` Prefect flows.
- **Vessel Tracking:**
  - Introduced the `DeconVessel` model to track experimental vessels used in
    pretreatment and fermentation.
  - Added `vessel_id` foreign key relationships to both `PretreatmentRecord` and
    `FermentationRecord`.
- **Pretreatment Refinement:**
  - Fixed `eh_method_id` column mapping in the pretreatment transformation
    logic.

### 2. Database Schema and Migrations

- Added several migrations to support the new schema changes:
  - `311148551786_add_deconvessel_model_and_vessel_id_to_...py`: Creates the
    `decon_vessel` table and adds the link to pretreatment.
  - `6f4fbb_add_vessel_id_fk_to_fermentation_record.py`: Adds the link to
    fermentation.
  - `17fab0e1d312_remove_volumes_from_fermentation_record.py`: Cleaned up
    redundant volume columns.
  - `fix_analysis_view_joins.py`: Standardized joins across analytical views.

### 3. Materialized View Refinement

- Updated `src/ca_biositing/datamodels/ca_biositing/datamodels/views.py` and
  `resources/sql/create_analytical_views.sql`.
- Fixed joins in `analysis_data_view` to ensure correct resource and geoid
  mapping.
- Improved filtering logic in `analysis_data_view` (e.g., handling specific
  dataset IDs).

### 4. Testing

- Added a comprehensive test suite for fermentation ETL in
  `src/ca_biositing/pipeline/tests/test_fermentation_etl.py`.
- Updated existing pretreatment ETL tests to verify the new vessel linkages.

## Key Files Modified

- `src/ca_biositing/datamodels/ca_biositing/datamodels/models/aim2_records/fermentation_record.py`
- `src/ca_biositing/datamodels/ca_biositing/datamodels/models/experiment_equipment/decon_vessel.py`
- `src/ca_biositing/datamodels/ca_biositing/datamodels/views.py`
- `src/ca_biositing/pipeline/ca_biositing/pipeline/flows/aim2_bioconversion.py`
- `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/fermentation_record.py`
- `alembic/versions/*` (Multiple migration files)

## Verification

- Ran `pixi run test` to verify ETL logic and database migrations.
- Manually inspected the refreshed materialized views to confirm data accuracy.
