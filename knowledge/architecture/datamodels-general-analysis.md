---
type: Architecture
title: "General analysis: observation (long-format measurements), dataset, analysis type, dimension type"
description: "observation holds every measured value as one row keyed by record_id, record_type, parameter and unit; dataset groups import batches; analysis_type and dimension_type are lookups."
tags: [datamodels, observation, dataset, analysis-type, eav, measurements]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:12Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/general_analysis/*.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/observation.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/observation.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/views.py"]
sources: ["commit a9a86eb", "commit 7a41e0e", "commit a4e6fc9", "commit 35423d1", "https://github.com/sustainability-software-lab/ca-biositing/pull/84", "https://github.com/sustainability-software-lab/ca-biositing/pull/217", "https://github.com/sustainability-software-lab/ca-biositing/pull/265", "docs/datamodels/ALEMBIC_VIEW_WORKFLOW.md", "docs/datamodels/SCHEMA_DRIFT.md"]
governance: context
---

## Purpose
The measurement layer. Instead of one column per measured quantity, each numeric result is an `observation` row. Each observation says which record it belongs to, which parameter was measured, the value and unit, and optionally a second dimension such as time or temperature.

## Key files
| Path:line | Role |
|---|---|
| general_analysis/observation.py:11 | `observation`: record_id (str, NOT NULL), dataset_id, record_type (str), parameter_id, value (Decimal), unit_id, dimension_type_id, dimension_value, dimension_unit_id, note |
| general_analysis/observation.py:13-21 | UniqueConstraint `observation_unique_key` on (record_id, record_type, parameter_id, unit_id). The ETL upserts on this key |
| general_analysis/dataset.py:8 | `dataset`: name, record_type, source_id (data_source), start_date, end_date, description |
| general_analysis/analysis_type.py | `analysis_type` (LookupBase): technique names, e.g. ’proximate analysis’ |
| general_analysis/dimension_type.py | `dimension_type` (LookupBase): the second axis, e.g. time or temperature |

Tables: observation, dataset, analysis_type, dimension_type (4 tables).

## How it works
```
Aim record or external record (record_id, record_type) --< observation >-- parameter (what)
                                                       >-- unit (how measured)
                                                       >-- dimension_type + dimension_value + dimension_unit (optional axis)
                                                       >-- dataset (import batch) --> data_source
```
Record_type takes two conventions in practice. The Aim analysis transform writes the analysis_type label (for example ’xrf analysis’, ’proximate analysis’), while USDA and county records use the table name (’usda_census_record’, ’county_ag_report_record’). views.py accepts both spellings for proximate and ultimate.

## Interfaces
- Writers: pipeline transform/analysis/observation.py (rename analysis_type to record_type, drop rows missing record_id, parameter_id or value, dedupe on the unique key) and load/analysis/observation.py (upsert with on_conflict on the unique key).
- Readers: materialized views (views.py joins Observation to records and parameter; mv_biomass_volume_estimate filters by record_type) and webservice analysis services.

## Gotchas
- The dimension_* columns are read by views.py and webservice schemas, but no pipeline code in src/ca_biositing/pipeline writes them at e41d00d. Treat dimension data as currently unpopulated by ETL (inferred from grep; confirm).
- Observation has no FK on record_id, so orphan observations are possible if a record row is deleted.
- The unique key includes unit_id, so the same parameter in two units is two rows.
- The load’s `index_elements` must match the unique constraint; changing one without the other breaks upserts.
- The observation loader is decorated `@task(retries=3, retry_delay_seconds=10)(retries=3, retry_delay_seconds=10)` in load/analysis/observation.py (double call, unverified whether it errors at import; confirm).

## History
- Observation and Dataset: Observation class introduced in a9a86eb (PR #84, verified with git log -S); Dataset also a9a86eb (verified). The unique constraint is in the 0003 core-tables migration (inferred to date from the 7a41e0e SQLModel migration).
- Gasification feedstock and run values moved to observation in a4e6fc9 (PR #217).
- Qualitative data ETL writing observations: 35423d1 (PR #265, ’Qualitative data ETL & MVs’).

## Open questions
- Is record_type intended to be a controlled vocabulary? Two naming schemes coexist today (inferred from transform and view code; confirm with the analytics team).

# Related Concepts
- [Measurements as a long observation table instead of one column per analysis](../decisions/datamodels-observation-long-table.md): Why measurements are stored in a long observation table
- [Observation upserts depend on the (record_id, record_type, parameter_id, unit_id) unique key](../requirements/datamodels-observation-upsert-key.md): The ETL upsert depends on this unique key being preserved
- [Methods, parameters, units and technical assumptions: the measurement vocabulary](datamodels-methods-parameters-units.md): observation.parameter_id and unit_id reference parameter and unit
- [Aim 1 analytical record tables (proximate, ultimate, XRF, ICP, etc.)](datamodels-aim1-records.md): Aim 1 record_id values are the keys observations attach to
- [External data: LandIQ crop map, USDA census and survey and market, Billion Ton, county ag reports](datamodels-external-data.md): Census and county records also write observation rows
- [System overview (start here)](system-overview.md): Hub for the ETL-to-database-to-API flow
