---
type: Architecture
title: ETL run and lineage group tracking
description: create_etl_run_record and create_lineage_group write EtlRun and LineageGroup rows; flows call them first and transforms stamp the ids onto each row.
tags: [pipeline, lineage, etl-run, provenance]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:50Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lineage.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/prepared_sample_etl.py"]
sources: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lineage.py", "commit 7a41e0e", "commit a9a86eb", "https://github.com/sustainability-software-lab/ca-biositing/pull/112"]
governance: context
---

## Purpose
Records which Prefect run and which lineage group produced each loaded row. Used for provenance across the analytical tables.

## Key files
| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lineage.py:9-39` | `create_etl_run_record(pipeline_name)` task. Uses `FlowRunContext` for the Prefect run id. Idempotent by `run_id`. Inserts `EtlRun` with `status="RUNNING"`. |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lineage.py:42-60` | `create_lineage_group(etl_run_id, note)` task. Inserts `LineageGroup` and returns its integer id. |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lineage.py:6` | `from ... engine import engine` at module level (import-time engine). |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/prepared_sample.py:104` (conditional stamp) and `etl/templates/transform_template.py:68-69` | Stamp `etl_run_id` and `lineage_group_id` columns. |

## How it works
1. Flow calls `create_etl_run_record("<name>")`. It raises `RuntimeError` if not run inside a flow or task context (line 17).
2. Flow calls `create_lineage_group(etl_run_id)`.
3. Both ids are passed to transform and written into each output row.

## Interfaces
- `etl_run_id`: string in signatures, `str(EtlRun.id)`.
- `lineage_group_id`: int.
- Callers: almost every flow in `flows/` imports these at module level. Verified in `usda_etl.py:6`, `biodiesel_plants.py:6`, `field_sample_etl.py:11`, `prepared_sample_etl.py:5`, and others.

## Gotchas
- Nothing in `utils/lineage.py` updates `EtlRun.status` after the run. `RUNNING` may be the final value (inferred from grep; confirm in the DB).
- Because `lineage.py` builds the engine at import, every flow that imports it at top level pays the settings-load cost at import.

## History
- `7a41e0e` (PR #112): models migrated to SQLModel. `lineage.py` changed in the same window (git log --follow).
- `a9a86eb` (PR #84): Berkeley Upstream integration. `lineage.py` changed (git log --follow; exact content change not reviewed).

## Open questions
- Whether EtlRun status should be finalized on flow completion (inferred; confirm with the datamodels EtlRun owners).

# Related Concepts
- [How a pipeline flow wires extract, transform, and load](pipeline-flow-wiring.md): Lineage is step 1 of every flow.
- [Import models and settings inside task or flow bodies](../requirements/pipeline-lazy-model-and-settings-imports.md): Top-level engine import in this module conflicts with that rule.
- [System overview (start here)](system-overview.md): Lineage tables are part of the data model.
