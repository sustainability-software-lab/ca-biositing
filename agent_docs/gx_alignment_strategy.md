# Phase 2: Great Expectations (GX) Alignment Strategy

This document outlines the strategy for translating hard SQL filtering rules
currently implemented in materialized views into Great Expectations (GX) suites.
Moving these checks to the "raw" data layer (Level 1/2) ensures data quality
issues are caught before they propagate to the data portal views.

## 1. Identified SQL Filtering Rules

Based on the review of
`src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/`, the
following hard filtering rules were identified:

### A. Biomass Composition (`mv_biomass_composition.py`)

- **Global QC Filter**: Exclude any record where `qc_pass == "fail"`.
- **Ultimate Analysis Whitelist**: Only include parameters in
  `["carbon", "nitrogen", "oxygen", "sulfur", "hydrogen"]`.
- **Ultimate Analysis Value Bound**: `Observation.value <= 100`.
- **ICP Analysis Unit Filter**: Only include observations where `unit == "ppm"`.
- **ICP Analysis Outlier Filter**: Exclude experiments where
  `max_icp_ppm > 500,000`.
- **Proximate Sum Constraint**: For `analysis_type == "proximate"`, the sum of
  `moisture + ash solids + (volatile solids OR 100 - fixed carbon)` must be
  between **95-105** (or 0 if no data).
- **Compositional Sum Constraint**: For `analysis_type == "compositional"`, the
  sum of `glucan + xylan + (lignin OR lignin+)` must be between **40-105** (or 0
  if no data).

### B. Biomass Volume Estimation (`mv_biomass_volume_estimate.py`)

- **Year Filter**: `dataset_year >= 2017`.
- **County Filter**: Currently hardcoded to
  `["san joaquin", "stanislaus", "merced"]` (this is likely a temporary dev
  restriction that should be monitored).
- **Factor Type Filter**: Ensure `ResidueFactor.factor_type` matches the
  expected path (weight vs. area).

### C. Resource Pricing (`mv_biomass_pricing.py`)

- **Parameter Synonyms**: Whitelist of valid price parameters
  (`"price received"`, `"price paid"`, etc.).
- **Value Presence**: `Observation.value.is_not(None)`.

### D. Global Filters (`common.py`)

- **Excluded Resources**: Hardcoded list of resources to exclude (`"sargassum"`,
  `"#n/a"`, `"lab media"`, etc.).

## 2. GX Translation Strategy

These SQL rules will be translated into GX Expectation Suites targeting the raw
PostgreSQL tables.

### Level 1: Table-Level Expectations (Schema & Volume)

_Target: `observation`, `proximate_record`, `compositional_record`, etc._

| SQL Rule                  | GX Expectation                                                                | Notes                                                          |
| :------------------------ | :---------------------------------------------------------------------------- | :------------------------------------------------------------- |
| `qc_pass != "fail"`       | `expect_column_values_to_not_be_in_set(column="qc_pass", value_set=["fail"])` | Applied to all analysis record tables.                         |
| `dataset_year >= 2017`    | `expect_column_values_to_be_between(column="data_year", min_value=2017)`      | Applied to `county_ag_report_record` and `usda_census_record`. |
| `value <= 100` (Ultimate) | `expect_column_values_to_be_between(column="value", max_value=100)`           | Conditioned on `analysis_type`.                                |

### Level 2: Cross-Record Expectations (Aggregate Validations)

_Target: Grouped observations per experiment/record._

| SQL Rule                       | GX Expectation Type                        | Strategy                                                                                                             |
| :----------------------------- | :----------------------------------------- | :------------------------------------------------------------------------------------------------------------------- |
| **Proximate Sum (95-105)**     | `expect_multicolumn_sum_to_equal` (custom) | Query-backed expectation that aggregates observations per `experiment_id` and checks the sum of specific parameters. |
| **Compositional Sum (40-105)** | `expect_multicolumn_sum_to_equal` (custom) | Similar to proximate sum, targeting glucan/xylan/lignin.                                                             |
| **ICP Outlier (>500k)**        | `expect_column_max_to_be_between`          | Checks if any observation for a given experiment exceeds the ppm threshold.                                          |

### Level 3: Reference Data Alignment

_Target: `resource`, `parameter`, `unit`._

| SQL Rule                | GX Expectation                          | Notes                                                                             |
| :---------------------- | :-------------------------------------- | :-------------------------------------------------------------------------------- |
| **Excluded Resources**  | `expect_column_values_to_not_be_in_set` | Validates `resource.name` against the blacklist in `common.py`.                   |
| **Parameter Whitelist** | `expect_column_values_to_be_in_set`     | Validates that parameters used in specific views exist and are spelled correctly. |

## 3. Implementation Plan for Phase 2

1.  **Refactor `common.py`**: Extract the hardcoded constants (Excluded
    Resources, Parameter Whitelists, Sum Bounds) into a central YAML or JSON
    configuration file that both SQLViews and GX Suites can reference.
2.  **Create GX Suites**: Implement the Level 1 and Level 2 expectations in the
    `ca_biositing.pipeline` audit flows.
3.  **Alerting**: Integrate GX validation results into the Prefect dashboard to
    flag "Fail" records before the `refresh-views` task is triggered.
4.  **Data Cleaning**: Use the GX "evidences" to identify specific records in
    Google Sheets that need manual correction.
