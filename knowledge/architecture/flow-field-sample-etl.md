---
type: Architecture
title: Field Sample ETL flow (four-worksheet join)
description: "Joins four SampleMetadata worksheets on sample_name into LocationAddress and FieldSample, then refreshes all materialized views; disabled in the master runner since #340."
tags: [pipeline, etl, prefect, flow, field-sample, gsheet, materialized-views]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:01Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/field_sample_etl.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/sample_ids.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/sample_desc.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/qty_field_storage.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/producers.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/provider_info.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/field_sampling/location_address.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/field_sampling/field_sample.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/field_sampling/*_v03.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/location_address.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/field_sample.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/views.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/443", "https://github.com/sustainability-software-lab/ca-biositing/pull/340", "https://github.com/sustainability-software-lab/ca-biositing/pull/260", "https://github.com/sustainability-software-lab/ca-biositing/pull/149", "https://github.com/sustainability-software-lab/ca-biositing/pull/108", "commit 23a34f3", "commit db578ad", "resources/prefect/run_prefect_flow.py"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Loads field samples from the SampleMetadata_v03-BioCirV spreadsheet, joining four worksheets on sample_name, then loads LocationAddress and FieldSample and refreshes all materialized views. Entry point field_sample_etl_flow.

## Source
- Google Sheet ’SampleMetadata_v03-BioCirV’: 01_Sample_IDs (sample_ids), 02_Sample_Desc (sample_desc), 03_Qty_FieldStorage (qty_field_storage), 04_Producers (producers). Each via a factory extractor with retries=3.
- Google Sheet ’Sampling_data_redacted’, tab ’provider_info’ (etl/extract/provider_info.py). It is passed in data_sources but no transform reads it (verified by grep of data_sources keys). Its extract module still has TODO template comments.

## Key files
| path:line | role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/field_sample_etl.py:15 | @flow (no log_prints) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/sample_ids.py, sample_desc.py, qty_field_storage.py, producers.py, provider_info.py | extractors |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/field_sampling/location_address.py:16 | transform_location_address (reads sample_desc and producers) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/field_sampling/field_sample.py:30 | transform_field_sample, multi-way left join on sample_name, unit extraction, county to Place, timestamp coalesce |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/location_address.py:11 | load_location_address |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/field_sample.py:11 | load_field_sample |
| src/ca_biositing/datamodels/ca_biositing/datamodels/views.py:541 | refresh_all_views(engine) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/field_sampling/field_sample_v03.py, location_address_v03.py | older v03 variants, not imported by any flow |

## How it works
1. create_etl_run_record(’Field Sample ETL’) and create_lineage_group(etl_run_id) with no note.
2. Extract the five sources.
3. Transform LocationAddress, then load it if non-empty.
4. Transform FieldSample, then load it if non-empty.
5. refresh_all_views(engine). A failure is logged and re-raised, so the flow fails.

## Interfaces
- Input: sheets above, CREDENTIALS_PATH.
- Output: LocationAddress, FieldSample, Place (county references), EtlRun, LineageGroup, refreshed materialized views.
- Callers: not in the master runner (commented out in db578ad). It runs directly.

## Gotchas
- Module-level imports: the flow imports the datamodels views module and the pipeline engine at import time (lines 10-12). AGENTS.md says heavy model and engine imports must stay inside tasks, so this is a likely Docker import-hang risk (inferred; not reproduced).
- The refresh affects every materialized view, not only the ones this flow feeds.
- The v03 variants look like dead code. No flow imports them.
- Field-sample rows whose sample_name is missing from 01_Sample_IDs are dropped by the left join (the base is 01_Sample_IDs).

## History
- dc98b30 (2026-02-11, PR #108) SQL-first workflow and first field-sample ETL.
- f5ab169 (2026-03-18, PR #149) fix for the empty location_address table that blocked the Analysis API.
- bd0ec5e (2026-04-14, PR #260) ETL refinements.
- e6ee628 (2026-04-30, PR #268) mv_biomass_fermentation fixes.
- db578ad (2026-05-08, PR #340) database maintenance staging reset. This is when field_sample was commented out in the master runner.
- 23a34f3 (2026-07-06, PR #443) fixing field sampling issue (latest change to the transforms).

## Open questions
- Whether field_sample should return to the master runner (no evidence either way in code).

# Related Concepts
- [Geography ETL flow (CA counties to Place)](flow-geography.md): FieldSample and LocationAddress reference Place rows for counties.
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Uses the extract factory, lineage helpers and the materialized-view refresh step described there.
- [System overview (start here)](system-overview.md): Primary source of field sample and location metadata for the data model.
- [Analysis Records ETL flow (proximate, ultimate, compositional, ICP, XRF, calorimetry, XRD)](flow-analysis-records.md): Downstream analytical records reference the samples this flow creates (inferred link through FieldSample).
