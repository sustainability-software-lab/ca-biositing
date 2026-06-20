# USDA ETL Pipeline Status Document

**Date:** February 11, 2026 (historical snapshot; see USDA_ETL_GUIDE.md for
current architecture) **Status:** ✅ **WORKING**

## Current Status: WORKING ETL PIPELINE

The USDA ETL pipeline is now **fully functional** with comprehensive testing and
diagnostic capabilities. All major issues have been resolved and the pipeline
successfully processes all available commodities.

## Current Pipeline Performance

### Extract Step ✅ WORKING

- **Input:** 15 commodity codes from USDA NASS API (SILAGE handled via CORN)
- **Output:** 15 commodities successfully extracted (~10,000+ records)
- **Success Rate:** 100% (SILAGE is included in CORN responses, not queried
  separately)

### Transform Step ✅ WORKING

- **Input:** 15 commodities (~10,000+ records)
- **Output:** All commodities processed with proper mapping
- **Data Quality:** Excellent mapping success for commodity, parameter, and unit
  IDs
- **Filtering:** Intelligent filtering removes invalid/incomplete records
  (expected ~54% retention)

### Load Step ✅ WORKING

- **Input:** Transformed valid records
- **Output:** Successfully loads all valid records into database
- **Deduplication:** Proper handling of existing records (shows 0 new insertions
  when re-running)
- **Database Integration:** Full integration with lineage tracking and ETL run
  management

## Current Database State

### ETL Tracking Tables

- **data_source**: 1 record (expected)
- **dataset**: Multiple records for different ETL runs
- **usda_census_record**: 241 unique records
- **usda_survey_record**: 802 unique records
- **Total observations**: 4,504 (988 census + 3,516 survey)

### Commodity Coverage

- **15 commodities configured** in usda_commodity table (SILAGE mapped to CORN)
- **15 commodities active** in ETL (SILAGE included via CORN)
- **Major crops**: ALMONDS, CORN (includes SILAGE), COTTON, GRAPES, HAY, OLIVES,
  PEACHES, PISTACHIOS, RICE, TOMATOES, WALNUTS, WHEAT
- **Coverage**: Census records (15 commodities), Survey records (5 commodities)

### Parameters & Units Added

The ETL has successfully added USDA-specific parameters and units:

- **Parameters**: YIELD, PRODUCTION, AREA HARVESTED, AREA PLANTED, AREA BEARING,
  OPERATIONS, PRICE RECEIVED, SALES
- **Units**: BUSHELS, TONS, ACRES, DOLLARS, BU, LB, BALES, CWT, OPERATIONS

## Validation & Testing Tools

### ⭐ Recommended Post-ETL Validation

**File**: `src/ca_biositing/pipeline/tests/test_usda_comprehensive.py`

**Usage**:

```bash
# Run ETL
pixi run run-etl

# Validate results
pixi run python src/ca_biositing/pipeline/tests/test_usda_comprehensive.py
```

**Provides comprehensive analysis**:

- ETL tracking tables record counts
- USDA database records analysis
- Commodity mapping with resource linkage
- Parameters and units verification
- API connectivity testing

### Additional Testing Tools

- **`test_seeding.py`**: Commodity mapping seeding
- **`test_api_names.py`**: API connectivity and mappings
- **`scripts/USDA/usda_availability.py`**: Data availability by commodity/county
- **SQL scripts**: Various diagnostic queries

## Infrastructure Status ✅ WORKING

### Database

- **Status**: Fully operational PostgreSQL on Docker
- **Connection**: Port 5432 internal, 9090 external
- **Constraints**: Updated observation table with proper unique constraints
- **Migration**: All migrations applied via Alembic

### Docker Environment

- **Services**: Prefect Server + Worker + PostgreSQL all running
- **Debug Access**: CSV files available via `/app/data` volume mount
- **Monitoring**: Service status via `pixi run service-status`

### Commands for Operations

```bash
# Start services
pixi run start-services

# Run ETL with full diagnostics
pixi run run-etl

# Validate ETL results
pixi run python src/ca_biositing/pipeline/tests/test_usda_comprehensive.py

# Check service status
pixi run service-status

# View logs
pixi run service-logs

# Rebuild after code changes
pixi run rebuild-services
```

## Issues Resolved ✅

### Transform Step Fixed

- **Root Cause**: Fruit/nut commodities used different parameters ("AREA
  BEARING" vs "AREA HARVESTED") and units not in database
- **Solution**: Added comprehensive parameter and unit configurations in
  transform step
- **Result**: All commodity types now process successfully

### Load Step Working

- **"Zero insertions" explained**: ETL correctly reports only NEW records, not
  total (deduplication working)
- **Database integration**: Proper lineage tracking and ETL run management
- **Verification**: Database contains expected record counts

### Diagnostic Capabilities Enhanced

- **Transform diagnostics**: Detailed logging of mapping success/failures, null
  value analysis
- **Comprehensive testing**: Full validation suite for post-ETL verification
- **API connectivity**: Smaller test queries to avoid 413 errors

## Current Data Quality Metrics

### Extract Success

- **Commodity Coverage**: 94% (15/16 commodities)
- **Data Availability**: Historical data from 1950s-2023 depending on commodity
- **Geographic Coverage**: All 58 California counties (list driven by
  `data/static/ca_counties.csv`)

### Transform Success

- **Mapping Quality**: Excellent (commodity, parameter, unit mappings working)
- **Data Filtering**: ~54% retention rate (expected due to data quality filters)
- **Value Processing**: USDA special code handling via numeric conversion:
  - **Special Codes Detected**: `(D)` (withheld data), `(Z)` (less than 0.5),
    `(NA)` (not available)
  - **Conversion Process**: Uses `pd.to_numeric(errors='coerce')` - numeric
    values convert, special codes become null
  - **Current Limitation**: Original special codes are **not preserved** in
    database (only `value` decimal field exists in schema)
  - **Filtering**: Records with special codes filtered out during required field
    validation
  - **Result**: Only numeric data makes it to final database; special codes are
    lost but logged during ETL process

### Load Success

- **Deduplication**: Prevents duplicate records on re-runs
- **Data Integrity**: Proper foreign key relationships maintained
- **Observation Linking**: Parent records correctly linked to observations

## Future Enhancements & Maintenance

### Optional Improvements (Non-Critical)

#### Database Schema Improvements (Medium Priority)

- **commodity_code field naming**: Consider renaming `commodity_code` to
  `commodity_id` for clarity
  - Currently requires casting
    (`commodity_code::text = usda_commodity.usda_code`)
  - **Risk**: HIGH - Would break existing queries across many scripts
  - **Impact**: Requires comprehensive audit of all references before
    implementation

- **USDA special code preservation**: Add `value_text` column to observation
  table to preserve original USDA values
  - **Current limitation**: Special codes `(D)`, `(Z)`, `(NA)` are converted to
    null and lost
  - **Proposed solution**: Add `value_text TEXT` column to observation schema
    via LinkML
  - **Benefits**: Preserves data provenance, enables analysis of data
    availability patterns
  - **Implementation**: Update LinkML observation.yaml → regenerate models →
    create migration
  - **Risk**: Low (additive change, won't break existing functionality)

#### Database Constraint Improvements (Low Priority)

- **Additional unique constraints** for data integrity:

  ```sql
  ALTER TABLE usda_census_record ADD CONSTRAINT usda_census_record_unique UNIQUE (geoid, year, commodity_code);
  ALTER TABLE usda_survey_record ADD CONSTRAINT usda_survey_record_unique UNIQUE (geoid, year, commodity_code);
  ```

  - **Benefits**: Prevents duplicates from parallel ETL runs
  - **Risk**: Low (current analysis shows 0 duplicates)

#### Data Type Consistency (Low Priority)

- **Mixed data types**: Some ID columns use text vs integer inconsistently
  - **Impact**: Requires `::integer` casting in some queries
  - **Benefits**: Improved query performance and consistency

### Operational Considerations

#### Regular Maintenance

- **API Key Rotation**: USDA NASS API keys should be rotated periodically
- **Data Quality Monitoring**: Use comprehensive test after each ETL run
- **Performance Monitoring**: Track ETL execution time and success rates

#### Scaling Considerations

- **Geographic Expansion**: Successfully expanded to all 58 California counties.
  County scope is now managed via `data/static/ca_counties.csv` rather than
  hardcoded constants.
- **Temporal Expansion**: Historical data available back to 1950s for some
  commodities
- **Commodity Expansion**: Additional commodities can be added via resource
  mapping

## Deferred Decisions & TODOs (March 2026)

The following decisions were deferred pending design confirmation and additional
work. See [USDA_ETL_GUIDE.md](USDA_ETL_GUIDE.md) for current operational status.

### **High Priority**

- **Database Schema Enhancements**:
  - Add `UNIQUE (name)` on `usda_commodity` for safe upsert semantics (deferred
    until AMS integration design is finalized)
  - Switch seeder from check-then-insert to atomic `ON CONFLICT` upsert once the
    uniqueness decision is finalized

### **Medium Priority**

- **Comprehensive Commodity Mapping Maintenance**:
  - Continue review/curation of `OFFICIAL_API_MAPPINGS` and
    `DISABLED_API_MAPPINGS`
  - Periodically validate mappings against live QuickStats commodity list
  - Keep mapper export + seed workflow as the operational source of truth

### **Template Improvements**

- Update Google Sheets extraction templates to use actual sheet names
- Replace placeholder TODOs in template files with real configuration

## Documentation References

- **Main Guide**: `docs/pipeline/USDA/USDA_ETL_GUIDE.md` - Comprehensive
  pipeline documentation
- **Testing Guide**: Post-ETL validation workflow using
  `test_usda_comprehensive.py`
- **Configuration**: Environment variables in `.env` file for API keys
- **Architecture**: PEP 420 namespace packages, Pixi environment management

## Success Criteria ✅ ACHIEVED

- **Functional ETL Pipeline**: Extract, Transform, Load all working
- **High Data Quality**: Excellent mapping success rates
- **Robust Testing**: Comprehensive validation tools
- **Documentation**: Complete guides and handoff materials
- **Infrastructure**: Stable Docker + Prefect + PostgreSQL environment
- **Monitoring**: Detailed diagnostic and logging capabilities
