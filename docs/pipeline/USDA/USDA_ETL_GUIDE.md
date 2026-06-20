# USDA ETL Pipeline Guide

**Component Documentation for USDA NASS API Integration**

**Last Updated**: February 13, 2026

## Overview

The USDA ETL pipeline extracts agricultural data from the USDA NASS QuickStats
API, transforms it for database storage, and loads it into PostgreSQL with full
deduplication and validation.

### 🚨 Recent Improvements (2026)

- **API Error Handling:** Comprehensive test now gracefully handles empty
  responses and JSON parsing errors
- **Test Output:** Debug output for TOMATOES only shown on error, summary output
  is regularized for all 58 California counties
- **Commodity Coverage:** Confirmed robust handling for all mapped commodities

### 🔑 **Key Dependencies & Prerequisites**

The pipeline relies on a sophisticated **commodity mapping system** that bridges
our internal resource database with USDA API commodity names:

1. **Resource & Primary Ag Product Tables**: The system first checks the
   database for existing `resource` entries and `primary_ag_product` mappings
2. **Commodity Seeding**: If prerequisites aren't met (missing
   resources/products), the system automatically seeds the `usda_commodity`
   table from the backup CSV
3. **CSV Backup**: `commodity_mappings.csv` serves as the authoritative source
   for commodity mappings when database is empty
4. **Dynamic Fetching**: Once seeded, the `fetch_mapped_commodities` module
   dynamically queries mapped commodities from the database

**SILAGE Handling:**

- SILAGE is no longer queried as a separate commodity in the API.
- SILAGE data is extracted from CORN responses ("CORN FOR SILAGE" mapped to
  "CORN" in the API).
- The ETL now processes 15 commodities directly from the API, with SILAGE
  included via CORN.

This ensures the ETL can bootstrap itself on fresh databases while maintaining
data integrity on established systems.

## Pipeline Architecture

### 🏗️ **Component Structure**

```text
USDA ETL Pipeline Components:
├── 🔍 Prerequisites Check
│   ├── Database prerequisite validation (46+ resources, 18+ ag products)
│   ├── Commodity seeding from CSV backup (if needed)
│   └── Dynamic commodity fetching (fetch_mapped_commodities.py)
├── Extract (usda/usda_census_survey.py)
│   ├── API Configuration & Authentication (.env integration)
│   ├── Multi-year data fetching (1924-2024)
│   └── Debug CSV output (/data/usda_raw_extracted_debug_TIMESTAMP.csv)
├── Transform (usda/usda_census_survey.py)
│   ├── Geospatial ID normalization (FIPS codes)
│   ├── Commodity/Parameter/Unit mapping (database lookups)
│   ├── Data type conversion & cleaning
│   └── Debug CSV output (/data/usda_transformed_debug_TIMESTAMP.csv)
└── Load (usda/usda_census_survey.py)
    ├── Dataset creation & linking
    ├── 3-level deduplication strategy
    └── Parent record → Observation linking
```

### 🔗 **Data Flow**

1. **Extract**: API → Raw CSV (~20,000+ raw records from 15 commodities across
   all 58 California counties)
2. **Transform**: Raw CSV → Cleaned CSV (filtered and deduplicated for database
   insertion)
3. **Load**: Cleaned CSV → Database (1,048 parent records: 241 census + 807
   survey; 4,524 observations)

## Key Components

### **🔍 Prerequisites & Commodity Mapping System**

**Purpose**: Ensure database has required resources and commodity mappings
before ETL execution

**Migration Best Practice:**

- Always run `pixi run migrate` to apply schema changes. The task is now
  configured to use the correct port from Docker.
- Unique constraints are required for atomic upsert logic (e.g., ON CONFLICT
  (name) DO UPDATE SET).

**Components**:

- **`seed_commodity_mappings.py`**: Seeds `usda_commodity` table from CSV backup
  when database is empty
- **`commodity_mappings_corrected.csv`**: Authoritative mapping source (40
  commodity mappings)
- **`fetch_mapped_commodities.py`**: Dynamic fetcher that queries database for
  mapped commodities
- **Prerequisite checks**: Validates 46+ resources and 18+ primary ag products
  exist
- **SILAGE Mapping**: "CORN FOR SILAGE" is mapped to "CORN" in the API; no
  separate SILAGE query

**Logic Flow**:

1. **Check Prerequisites**: Query database for required resources and ag
   products
2. **Conditional Seeding**: If prerequisites fail, automatically seed from CSV
   backup
3. **Commodity Fetching**: Dynamically fetch mapped commodities from seeded
   database
4. **ETL Execution**: Proceed with extract using fetched commodity list

This system ensures the ETL can bootstrap itself on fresh databases while
maintaining data integrity.

### **Extract Step**

- **Purpose**: Fetch data from USDA NASS QuickStats API
- **Output**: Raw CSV with all API fields (timestamped for debugging)
- **Key Features**:
  - **All-County Expansion**: Now queries all 58 California counties, driven by
    `data/static/ca_counties.csv`.
  - Multi-commodity extraction (16 mapped commodities)
  - Multi-year coverage (1924-2024)
  - **Efficient Batching**: Queries all counties in a single state-level API
    call per commodity, then filters.
  - **Performance**: Runtime is approximately `N_commodities × 1 second`.
  - Automatic retry logic and improved error handling for empty responses and
    JSON parsing

  ### **Testing & Diagnostics**
  - Comprehensive test script (`test_usda_comprehensive.py`) now:
    - Handles empty API responses and JSON parsing errors gracefully
    - Only prints debug output for TOMATOES if an error occurs
    - Provides regularized summary output for all commodities across all 58
      counties
    - Confirms robust data coverage for TOMATOES and all mapped commodities
  - Environment variable integration (.env file support)
  - Optional debug CSV generation with timestamps

### **Transform Step**

- **Purpose**: Clean and map raw data to database schema
- **Key Operations**:
  - FIPS code → geoid conversion
  - Commodity name → commodity_code mapping via `usda_commodity` table
  - Statistic description → parameter_id mapping via `parameter` table
  - Unit description → unit_id mapping via `unit` table
  - Data type conversion and validation
  - Fruit-specific parameter handling (AREA BEARING, AREA NON-BEARING)
- **Output**: Timestamped debug CSV for troubleshooting
- **Filtering**: Removes records without required fields or valid mappings

### **Load Step**

- **Purpose**: Insert data with deduplication
- **3-Level Deduplication**:
  1. **Level 1**: Query existing records from database
  2. **Level 2**: Skip duplicates within current batch
  3. **Level 3**: PostgreSQL `ON CONFLICT DO NOTHING`

## Database Integration

### **Tables Populated**

- `usda_census_record` - Census agricultural records
- `usda_survey_record` - Survey agricultural records
- `observation` - Individual measurements linked to records
- `dataset` - ETL run tracking and data lineage

### **Mapping Tables Used**

- `usda_commodity` - API commodity names → database commodity codes
- `parameter` - Statistic descriptions → parameter IDs
- `unit` - Unit descriptions → unit IDs

## Configuration

### **Commodity Support**

Currently supports 16+ commodities including:

- **Grains**: Corn (including silage), Wheat, Rice
- **Fiber**: Cotton (Upland)
- **Tree Nuts**: Almonds, Pistachios, Walnuts
- **Fruits**: Grapes, Peaches, Olives
- **Forage**: Alfalfa Hay

**Note**: Corn silage data is retrieved via the CORN commodity (USDA includes
corn silage records within the main CORN commodity descriptor).

### **Parameter Types**

Supports diverse agricultural measurements:

- **Area**: Harvested, Planted, Bearing, Non-Bearing
- **Production**: Volume/weight outputs
- **Sales**: Number of operations
- **Chemical**: Compositional analysis (moisture, ash, lignin, etc.)

## Debugging & Operations

### **Debug Outputs**

- `usda_raw_extracted_debug_YYYYMMDD_HHMMSS.csv` - Raw API data with timestamp
- `usda_transformed_debug_YYYYMMDD_HHMMSS.csv` - Processed data ready for load
  with timestamp

**Note**: Debug CSV generation is **optional** and disabled by default. To
enable:

1. Uncomment debug blocks in extract/transform code
2. CSV files will include timestamps for tracking multiple runs
3. Re-comment blocks when debugging is complete

### **Testing & Validation Tools**

Located in `src/ca_biositing/pipeline/tests/USDA/`:

- **`test_usda_comprehensive.py`**: **⭐ RECOMMENDED** - Complete diagnostic
  suite for post-ETL validation. Best tool for checking database state after ETL
  run. Provides detailed analysis of:
  - ETL tracking tables (data_source, dataset counts)
  - USDA-specific database records (usda_census_record, usda_survey_record
    counts)
  - Parameters and units added by ETL
  - Commodity mappings with resource linkage
  - API connectivity verification
- **`test_seeding.py`**: Test commodity mapping seeding functionality
- **`test_api_names.py`**: Verify API commodity mappings and database
  connectivity
- **`test_usda_availability.py`**: Check USDA API data availability by
  commodity/county
- **SQL Scripts**: Various validation and diagnostic queries

**Database Connection**: All test scripts include automatic port fallback
(configured port → 5432) for compatibility across environments.

**💡 Post-ETL Validation Workflow**:

1. Run ETL: `pixi run run-etl`
2. Validate results:
   `pixi run python src/ca_biositing/pipeline/tests/USDA/test_usda_comprehensive.py`
3. Review comprehensive diagnostics output for data quality and completeness

### **Success Metrics**

- **Extract Success**: 15/15 commodities (100% - all mapped) across 58 counties
- **Transform Success**: ~55% raw records survive filtering (approx. 85,000+
  observations retained project-wide)
- **Load Success**: 100% of valid transformed records loaded
- **Database Seeding**: 15 mapped commodities (all with valid api_name)

### **Common Issues**

- **API Rate Limits**: Handled with automatic retry and proper delays
- **Missing Mappings**: New parameters/units require database updates
- **Geoid Formatting**: Automatic FIPS code standardization
- **Port Configuration**: Database connection issues resolved with port fallback
- **Environment Variables**: `.env` file loading required for API keys

### **Environment Requirements**

- **USDA_NASS_API_KEY**: Required in `.env` file for API access
- **DATABASE_URL**: Optional, with automatic fallback to configured ports
- **python-dotenv**: Automatic environment variable loading
- **Database Prerequisites**: 46+ resources, 18+ primary ag products for full
  operation

## Monitoring

The pipeline provides detailed logging at key stages:

- Record counts at each step
- Mapping success rates
- Error reporting with context
- Performance timing

For operational troubleshooting and historical context, see
[USDA ETL Handoff Document](USDA_ETL_HANDOFF.md).
