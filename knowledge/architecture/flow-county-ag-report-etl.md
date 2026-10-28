---
type: Architecture
title: "County Ag Report ETL flow (three-sheet, ordered load)"
description: "Loads county ag report primary products, data sources, datasets, records and observations from three Aim 1 tabs in a fixed order; records must load before observations."
tags: [pipeline, etl, prefect, flow, county-ag-report, gsheet, fk-ordering]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:00Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/county_ag_report_etl.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/county_ag_report.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/data_source.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_datasets.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_report_record.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_report_observation.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/data_source.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/county_ag_datasets.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/county_ag_report_record.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/observation.py", "tests/pipeline/test_county_ag_report_etl.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/260", "commit bd0ec5e", "plans/phase3_materialized_views_assessment.md", "resources/prefect/run_prefect_flow.py"]
governance: constraint
stale_after: "2026-12-31"
---

## Purpose
ETL for county agricultural report data (Merced, San Joaquin, Stanislaus, 2023-2024) into DataSource, Dataset, CountyAgReportRecord and Observation. Entry point county_ag_report_flow. Active in the master runner.

## Source
Google Sheet ’Aim 1-Feedstock Collection and Processing Data-BioCirV’, three tabs via etl/extract/county_ag_report.py: 07.7-Primary_products, 07.7a-PP_Prodn_Value, 07.7b-PP_Data_sources (each create_extractor with retries=3).

## Key files
| path:line | role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/county_ag_report_etl.py:4 | @flow with ordered steps 1 to 7 in the docstring |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/county_ag_report.py | three extractor tasks |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/data_source.py:17 | transform_data_sources (from pp_data_sources) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/data_source.py:19 | load_data_sources (upsert on id) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_datasets.py:17 | transform_county_ag_datasets (from pp_data_sources) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/county_ag_datasets.py:18 | load_county_ag_datasets |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_report_record.py:19 | transform_county_ag_report_records (primary_products and pp_production_value) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/county_ag_report_record.py:18 | load_county_ag_report_records (creates missing Place rows, upsert on record_id) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_report_observation.py:19 | transform_county_ag_report_observations (pp_production_value) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/observation.py:10 | load_observation |
| tests/pipeline/test_county_ag_report_etl.py | flow test (repo-root tests dir) |

## How it works
1. create_etl_run_record and create_lineage_group (note lists the three counties and years).
2. Extract all three tabs.
3. Transform and load data sources.
4. Transform and load datasets.
5. Transform base records (from primary_products and pp_production_value), then load them. This must finish before step 7.
6. Transform observations from pp_production_value, then load them.

## Interfaces
- Input: three tabs above, CREDENTIALS_PATH.
- Output: DataSource, Dataset, CountyAgReportRecord, Place (created if missing), Observation, EtlRun, LineageGroup.
- Callers: master flow (AVAILABLE_FLOWS ’county_ag_report’), or run directly. The almond flow writes to the same DataSource and Observation tables.

## Gotchas
- Ordering invariant: the code comment says records MUST load before observations because of a foreign key. Do not reorder steps 5 and 7.
- Records load creates missing Place rows itself, so this flow does not depend on the geography flow to succeed (verified in the load code). Place rows built this way may lack the full geography columns (inferred).
- The base-record transform reads two different tabs, and an empty pp_production_value makes both the record and observation steps empty.
- The flow is one of the few that does not guard empty frames before each load step (inferred from code; confirm).

## History
- bd0ec5e (2026-04-14, PR #260) multiple ETL refinements (latest flow-file change).
- The county-record logic is also used in the views’ volume estimate (plans/phase3_materialized_views_assessment.md, county_ag_report_record x residue factors).

## Open questions
- Whether the 2023-2024 scope in the lineage note still matches the sheet contents (no code check).

# Related Concepts
- [Almond NSJV county ag report ETL flow](flow-almond-nsjv-etl.md): Writes to the same DataSource and Observation tables for overlapping county ag data.
- [Geography ETL flow (CA counties to Place)](flow-geography.md): Place rows for counties; this flow creates missing ones itself, so the link is soft.
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Standard extract, transform, load layout used here.
- [System overview (start here)](system-overview.md): Source of county production and price inputs for volume estimates.
