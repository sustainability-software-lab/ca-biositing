---
type: Requirement
title: "Observation upserts depend on the (record_id, record_type, parameter_id, unit_id) unique key"
description: "Keep observation_unique_key and the ETL on_conflict index_elements in sync; the transform dedupes on the same four columns, so changing one without the others breaks loads."
tags: [datamodels, observation, constraint, etl, upsert]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:53Z" }
status: stable
governance: constraint
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/general_analysis/observation.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/observation.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/observation.py", "alembic/versions/0003_core_tables.py"]
sources: ["commit 7a41e0e", "commit a9a86eb", "alembic/versions/0003_core_tables.py", "commit ca71a99"]
---

## Rule
The unique constraint `observation_unique_key` on observation (record_id, record_type, parameter_id, unit_id) must stay in place, and any change to it must be made together with:
- the ETL upsert in pipeline etl/load/analysis/observation.py (on_conflict_do_update index_elements = [’record_id’, ’record_type’, ’parameter_id’, ’unit_id’]), and
- the dedupe subset in pipeline etl/transform/analysis/observation.py (subset = [’record_id’, ’record_type’, ’parameter_id’, ’unit_id’]).

## Why
Postgres ON CONFLICT needs a matching unique index. The transform removes duplicates on the same subset to avoid ON CONFLICT errors within one batch.

## Source
- models/general_analysis/observation.py:13-21 defines the constraint.
- The migration that creates it is alembic/versions/0003_core_tables.py (around line 1541).

## How to check
1. Edit the model, then run `pixi run migrate-autogenerate -m ...` and review the migration.
2. Grep the pipeline for `index_elements` and `subset =` on observation and confirm they still match.
3. Run the observation load tests in the pipeline test suite.

## Exceptions
None recorded. Any change to the key also changes which rows the views treat as the same measurement.

# Related Concepts
- [General analysis: observation (long-format measurements), dataset, analysis type, dimension type](../architecture/datamodels-general-analysis.md): The table and key this rule protects
- [Measurements as a long observation table instead of one column per analysis](../decisions/datamodels-observation-long-table.md): Why the key carries the whole identity of a measurement
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): Changes to the key must be made as an Alembic migration
- [System overview (start here)](../architecture/system-overview.md): Hub for the ETL-to-database-to-API picture
- [QC review decision ledger (qc_review_decision table, lifecycle, seed CSV)](../architecture/qc-review-decision-ledger.md): QC upsert guard covers the record tables, not observation
