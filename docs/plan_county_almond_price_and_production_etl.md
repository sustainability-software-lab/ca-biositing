# Plan: County Agricultural Reports Price & Production ETL

**Status:** Planning phase **Date:** April 28, 2026 **Target Integration:**
Qualitative ETL Flow **Data Source:** Google Sheets (multi-tab ingest)

---

## Overview

This ETL ingests county-level agricultural price and production data from a
Google Sheet, transforms it into normalized parameters and observations, and
integrates it into the hourglass schema (parameters → records → observations).

**Key Characteristics:**

- Multi-sheet ingest (extract all except `etl_notes` and
  `almond_hull_prices_usda_AMS`)
- Parameter definitions stored in the `parameters` sheet with a
  "price_production_county_ag_reports" marker
- Observation values extracted from columns D-K (price columns with
  county-specific headers)
- County information parsed from header (convention: `county_parameter`) in the
  transform. Melt the county price columns into a long format, use a county
  dictionary {"merced_price": "Merced", "stanislaus_price": "Stanislaus",
  "san_joaquin_price": "San Joaquin"} to map the column headers to clean county
  names, and dynamically query the place table to resolve the geoid.
- Year, resource, and county/geoid mapped to `resource_price_record` or
  `resource_production_record` as appropriate
- Integrated into the existing `qualitative_etl_flow` as a sub-flow
- **USDA AMS data deferred:** Currently excluding `almond_hull_prices_usda_AMS`
  for fast delivery; thorough AMS data download planned separately

---

## Data Source Specification

**Google Sheet URL:**
`https://docs.google.com/spreadsheets/d/1vHCpd14aa-Vc_WzWXxUlU6FxcI5IOR30Bi6v3Wjqon8/edit?gid=2121157186#gid=2121157186`

**Sheets to Ingest:**

- `parameters` → Extract parameter definitions (filter by
  "price_production_county_ag_reports" in column A)
- `almond_county_prices` and `almond_production` tabs

**Sheet Exclusions:**

- `etl_notes`: Internal documentation, not data
- `almond_hull_prices_usda_AMS`: Deferred; requires separate thorough AMS data
  download workflow

---

## Transformation Rules & Data Mapping

### Parameters Sheet → Parameters Table

**Source:** Rows in the `parameters` sheet with
"price_production_county_ag_reports" marker in column A

**Target:** `Parameter` table in datamodels

**Columns:**

- Parameter name
- Description
- Calculated flag (if applicable)
- Standard unit ID (resolved via name-to-ID mapping)

**Deduplication:** Idempotent by parameter name (normalized); update existing if
name matches, insert if new.

**Filter** Add a primary crop filter: df = df[df['primary_ag_product'] !=
'Meat/Kernel']

**Melt** Use pd.melt() to unpivot the wide county columns into a long format,
use a hardcoded dictionary to map the column headers to clean county strings,
and dynamically query the place table to resolve the geoid.

### Price Columns (D-K) → Observations + Records

**Header Convention:** `county_parameter` **Example:** `san_joaquin_price`,
`merced_production`

**Transformation Steps:**

1. **Header Parsing:** Split `county_parameter` into county name and parameter
   name
2. **County → Geoid:** Map county name to geoid (will need lookup table or user
   clarification on existing geoid mappings)
3. **Parameter Resolution:** Normalize parameter name and resolve to
   `parameter_id` via database lookup
4. **Record Classification:**
   - If parameter contains "price" → `resource_price_record`
   - If parameter contains "production" or "acreage" →
     `resource_production_record`
5. **Observation Construction:**
   - `dataset_id`: From provenance (see Provenance section below)
   - `method_id`: From provenance
   - `geoid`: Parsed from header
   - `year`: From source data row
   - `resource`: From source data row
   - `parameter_id`: Resolved via lookup
   - `value`: Cell value (D-K columns)
   - `unit_id`: From parameter definition

### Provenance Mapping

**Required Tables (must already exist in database):**

- `Dataset` : Two new datasets should be inserted
  - name: "BEAM whitepaper county ag report almond prices", "BEAM whitepaper
    county ag report almond production" Future grape ETL will have something
    akin to "Grape production manually extracted from NSJV county ag reports"
    and "Grape resource prices calculated from NSJV county ag reports"
  - record_type: "resource_price_record" and "resource_production_record" as is
    appropriate
  - source_id: "1" corresponding with "Market and End-Use Analysis for the
    Biomass Feedstock Landscape in the North San Joaquin Valley"
  - start_date: 2017-01-01
  - end_date: 2024-12-31
  - description: "Almond resource prices manually extracted from NSJV county ag
    reports" , "Almond production manually extracted from NSJV county ag
    reports"

- `Method` : 1 single new entry for all data with info below
  - created_at/updated_at/etl_run_id/lineage_group_id: follow existing etl
    patterns
  - method_category_id: "w" corresponding with "manual extraction of values from
    PDF report"
  - source_id: "1" corresponding with "Market and End-Use Analysis for the
    Biomass Feedstock Landscape in the North San Joaquin Valley"
- `MethodCategory`: 1 single new entry for all data with info below
  - name: "manual extraction of values from PDF report"
  - description: "manual meaning extracted "by-hand" by human(s)"

- `Place` : For county geoid records, no new counties not already in the
  database should be added.
- `DataSource` : "1" corresponding with "Market and End-Use Analysis for the
  Biomass Feedstock Landscape in the North San Joaquin Valley"

**Current Status:** TBD by Transform Agent **Action Item for Next Agent:** When
implementing the **Transform** task, prompt user to clarify anything that seems
important and unclear.

---

## ETL Architecture: 5 Agent Tasks

This ETL will be implemented across **5 separate agent tasks**, each with its
own task list. Each agent receives this plan as context and builds their own
checklist.

### Task 1: Plan (This Document)

- ✅ Define data source and sheet ingestion strategy
- ✅ Map source columns to target tables and fields
- ✅ Specify transformation rules (county parsing, parameter mapping, record
  classification)
- ✅ Identify provenance dependencies and decision points
- ✅ Define validation approach

**Handoff:** Planning document complete. Next agent: **Extract**

---

### Task 2: Extract

**Goal:** Pull raw data from Google Sheet and validate row counts per sheet.

**Deliverable:**
`src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/almond_nsjv.py`

**Requirements:**

1. Use the factory pattern (see `extract/factory.py`) to create extractors for
   each sheet
2. Call all required sheets in parallel and return a dict keyed by sheet name
3. Exclude `etl_notes` and `almond_hull_prices_usda_AMS` sheets
4. Each extractor task should log the row count; validation task checks min/max
   thresholds
5. Return dictionary structure:
   ```python
   {
       "parameters": pd.DataFrame,
       "sheet_name_2": pd.DataFrame,
       "sheet_name_3": pd.DataFrame,
       # ... etc
   }
   ```

**Validation:**

- After extraction, log row counts for each sheet
- Validate non-empty DataFrames (fail if any sheet is empty when expected)
- Check for required columns (to be validated by Transform agent)

**Testing:** Mock Google Sheet data in unit tests with representative rows.

**Handoff:** Extract module and tests complete. Pass raw dataframes dict to
**Transform**.

---

### Task 3: Transform

**Goal:** Clean, normalize, and reshape raw data into payloads for Parameters,
Records, and Observations.

**Deliverable:**
`src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/almond_nsjv.py`

**BLOCKING DECISION POINT:** **Before starting:** Prompt user to clarify
understanding based on transformation section above.

**Requirements:**

1. Create separate transform tasks for:
   - `transform_county_ag_parameters()` → DataFrame for parameter table
   - `transform_county_ag_records()` → Dict of DataFrames for price/production
     records
   - `transform_county_ag_observations()` → DataFrame for observation table
2. **Parameters task:**
   - Filter `parameters` sheet by "price_production_county_ag_reports" in column
     A
   - Normalize parameter names and descriptions
   - Resolve standard unit IDs via lookup
   - Return DataFrame with columns: name, description, calculated,
     standard_unit_id, etl_run_id, lineage_group_id
3. **Records task:**
   - Parse headers (D-K columns) using `county_parameter` convention
   - Split into county name and parameter type
   - Map county name to geoid (from Place table or user-provided lookup)
   - Classify by parameter type (price → resource_price_record, production →
     resource_production_record)
   - Return nested dict:
     ```python
     {
         "resource_price_record": DataFrame,
         "resource_production_record": DataFrame
     }
     ```
4. **Observations task:**
   - Extract values from price columns
   - Resolve parameter_id via normalized name lookup
   - Resolve geoid via county name lookup
   - Construct observation rows with dataset_id, method_id, geoid, parameter_id,
     value, unit_id
   - Return DataFrame with all required observation columns
5. **Temporary output:** During development, use `print()` or logger to dump
   intermediate DataFrames to terminal (schema, first 5 rows, shape). Remove
   before final delivery.
6. **Use `normalize_dataframes()` utility** (from pipeline utils) to resolve any
   name-to-ID mappings for foreign keys.

**Testing:** Mock extracted DataFrames; test each transform function
independently with patch decorators.

**Handoff:** Transform module and tests complete. Return payload dict to
**Load**.

---

### Task 4: Load

**Goal:** Insert transformed payloads into database tables with idempotent
upserts and error handling.

**Deliverable:**
`src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/almond_nsjv.py`

**Requirements:**

1. Create load task `load_county_ag_reports()` that accepts transformed payload
   dict
2. Load in dependency order:
   - Parameters (if new, insert; if exists by name, update description/unit)
   - Records (price and production records, keyed by
     resource/geoid/year/parameter combination)
   - Observations (keyed by dataset/method/geoid/parameter/year/resource
     combination)
   - Do not to use the Dual-ID linkage and to link only to the resource_id
3. **Error handling:**
   - If geoid lookup fails, log clear error and skip row (do not insert partial
     data)
   - If parameter_id missing, log and skip
   - If dataset_id/method_id missing, fail with descriptive error (precondition
     violation)
4. **Return:** Dict of row counts per table (e.g.,
   `{"parameter": 5, "observation": 150, ...}`)
5. **After load completion:** Run a spot-check query on observation table to
   verify a sample was inserted

**Testing:** Mock database session with in-memory SQLite; verify rows are
inserted/updated as expected.

**Handoff:** Load module and tests complete. Return counts to **Flow**.

---

### Task 5: Flow Integration

**Goal:** Wire Extract → Transform → Load into the existing a new ETL flow.

**Deliverable:** Create a new
`src/ca_biositing/pipeline/ca_biositing/pipeline/flows/BEAM_analysis.py` to call
the new ETL

**Requirements:**

1. Define a main orchestrator function decorated with Prefect's @flow (e.g.,
   county_ag_reports_etl_flow()).
2. Import the extract, transform, and load tasks from your newly created
   county_ag_reports modules.
3. Wire the tasks sequentially (Extract → Transform → Load), ensuring it
   successfully passes the Almond pricing and production data through the
   pipeline.
4. Use get_run_logger() to update the ETL run logging to output the row counts
   at the end of the flow.
5. Full Prefect test: Deploy the flow locally and run it end-to-end. Verify the
   Prefect UI (http://localhost:4200) shows the flow completing successfully.

**Handoff:** Flow integrated and tested. Ready for PR.

---

## Validation & Testing Strategy

### Extract Validation

- ✅ **Row count checks:** Log count per sheet; fail if count < threshold or
  empty
- ✅ **Unit tests:** Mock Google Sheet with 5-10 representative rows per sheet;
  verify DataFrame structure

### Transform Validation

- ✅ **Temporary DataFrame outputs:** During development, print intermediate
  DataFrame schemas and first 5 rows to terminal
- ✅ **Unit tests:** Mock extracted DataFrames; verify transform outputs match
  expected schema and values
- ✅ **Decision blocking:** Cannot proceed without user clarification on
  dataset/method/place

### Load Validation

- ✅ **Database spot check:** After load, run sample SELECT query on observation
  table; verify inserted rows have expected values
- ✅ **Unit tests:** In-memory SQLite session; verify upsert behavior (new rows
  inserted, existing rows updated)

### Full Flow Validation

- ✅ **End-to-end Prefect run:** Deploy flow locally; execute via Prefect UI or
  CLI (`pixi run run-etl`)
- ✅ **Flow logs:** Verify extract, transform, load tasks all complete with
  expected row counts
- ✅ **Database state:** Query production tables (parameters, observations,
  records) to confirm data consistency

---

## Open Decisions

### 1. Upsert Strategy (TBD by Transform + Load Agents)

**Question:** Should observations be:

- **Option A (Append-only):** Always insert new rows; deduplicate at query time
  or via separate cleanup task
- **Option B (Idempotent upsert):** Use natural keys (dataset + method + geoid +
  parameter + year + resource) to determine insert-or-update

**Current assumption:** Option B (idempotent upsert), matching qualitative flow
pattern. **Clarify with user if needed.**

### 2. County-to-Geoid Mapping (TBD by Transform Agent)

**Options:**

- Use existing `Place` table records (assume all counties already have entries)
- Create missing county/geoid entries during transform
- Prompt user for mapping table/lookup

**Current assumption:** Use existing Place table; fail if county not found.
**Clarify with user.**

---

## Files to Create/Modify

### New Files

- `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/county_ag_reports.py`
- `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_reports.py`
- `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/county_ag_reports.py`
- `src/ca_biositing/pipeline/tests/test_county_ag_reports_etl.py`

### Modified Files

- `src/ca_biositing/pipeline/ca_biositing/pipeline/flows/qualitative.py` (add
  sub-flow call)

---

## Dependencies & Prerequisites

- Google Sheets API credentials already configured (`credentials.json` in root)
- Target Google Sheet shared with service account
- Database tables exist: `Parameter`, `Dataset`, `Method`, `MethodCategory`,
  `Place`, `ResourcePriceRecord`, `ResourceProductionRecord`, `Observation`
- Existing utilities available:
  - `extract/factory.py` (sheet extractor factory)
  - `utils/normalize_dataframes()` (name-to-ID resolution)
  - `utils/cleaning_functions.py` (data cleaning)
  - `utils/engine.py` (database session/engine)

---

## Timeline & Handoff Sequence

| Agent | Task      | Deliverable                                       | Est. Duration                            |
| ----- | --------- | ------------------------------------------------- | ---------------------------------------- |
| 1     | Plan      | This document ✅                                  | Done                                     |
| 2     | Extract   | `extract/county_ag_reports.py` + tests            | ~1-2 hours                               |
| 3     | Transform | `transform/analysis/county_ag_reports.py` + tests | ~3-4 hours (includes user clarification) |
| 4     | Load      | `load/analysis/county_ag_reports.py` + tests      | ~2-3 hours                               |
| 5     | Flow      | Updated `qualitative.py` + E2E test               | ~1-2 hours                               |

**Total:** ~8-12 hours (blocks on Transform agent getting user input)

---

## Related Documentation

- [AGENTS.md](../../AGENTS.md) — Project overview and setup
- [agent_docs/](../../agent_docs/) — Cross-cutting patterns
- [docs/pipeline/ETL_WORKFLOW.md](../pipeline/ETL_WORKFLOW.md) — ETL
  architecture
- [src/ca_biositing/pipeline/AGENTS.md](../../src/ca_biositing/pipeline/AGENTS.md)
  — Pipeline package patterns
- [src/ca_biositing/pipeline/ca_biositing/pipeline/flows/qualitative.py](../../src/ca_biositing/pipeline/ca_biositing/pipeline/flows/qualitative.py)
  — Reference flow (integration target)
