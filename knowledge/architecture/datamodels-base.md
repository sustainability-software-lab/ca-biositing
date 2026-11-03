---
type: Architecture
title: "Datamodels base mixins (BaseEntity, LookupBase, Aim1/Aim2RecordBase)"
description: "Shared column conventions every domain table inherits: int id, created_at/updated_at, etl_run_id, lineage_group_id. Mixins are not tables."
tags: [datamodels, sqlmodel, base-class, conventions]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:26:54Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/base.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/auth/api_user.py"]
sources: ["commit 7a41e0e", "https://github.com/sustainability-software-lab/ca-biositing/pull/112", "docs/datamodels/SCHEMA_DRIFT.md", "alembic/versions/0003_core_tables.py"]
governance: context
---

## Purpose
Non-table SQLModel mixins that supply shared columns to domain tables. They replaced LinkML-generated concrete base tables (see decisions/linkml-to-sqlmodel-alembic).

## Key files
| Path:line | Role |
|---|---|
| `models/base.py:14` | `BaseEntity`: `id` (int PK), `created_at`, `updated_at` (Optional datetime, no default), `etl_run_id` (FK `etl_run.id`, `base.py:23`), `lineage_group_id` (plain int, no FK, `base.py:24`) |
| `models/base.py:27` | `LookupBase`: `id`, `name`, `description`, `uri`. No ETL columns. |
| `models/base.py:39` | `Aim1RecordBase(BaseEntity)`: `record_id` (unique str), FKs `dataset`, `experiment`, `resource`, `prepared_sample`, `method`, `contact` (as `analyst_id`), `file_object_metadata` (as `raw_data_id`); `qc_pass`, `note` |
| `models/base.py:59` | `Aim2RecordBase(BaseEntity)`: same field list as Aim1 (duplicated text) |

## How it works
Mixins subclass `SQLModel` without `table=True`. A concrete table inherits the fields, e.g. `class LocationAddress(BaseEntity, table=True)` (`models/places/location_address.py:7`). Inherited columns appear first in column order.

## Interfaces
- Inputs: none; these are declarations only.
- Callers: essentially every domain table in `models/*/` that subclasses `BaseEntity`, `LookupBase`, or the Aim mixins.
- ETL loaders set timestamps themselves in some paths, e.g. `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/biodiesel_plants.py:48-49` and `.../load/billion_ton.py:69`.

## Gotchas
- The mixin declares no `server_default`. Migration `alembic/versions/0003_core_tables.py` does set `CURRENT_TIMESTAMP` on some tables (around lines 47-48 and 571-572), so DB-side defaults are per-table, not guaranteed by the mixin. An ORM insert without a timestamp gets `None` where no DB default exists.
- `LookupBase` has no `etl_run_id`, so lookup tables are not traceable to an ETL run through this mixin.
- `ApiUser` deliberately does not inherit `BaseEntity` (`models/auth/api_user.py:18-21`).
- `Aim1RecordBase` and `Aim2RecordBase` field lists are textually identical (inferred duplication; a change to one must be mirrored; confirm whether divergence is intended).

## History
- `7a41e0e` (2026-02-12, PR #112): LinkML to SQLModel migration introduced these mixins.
- `docs/datamodels/SCHEMA_DRIFT.md` (section 1) records that the old `base_entity`, `lookup_base`, `aim1_record_base`, `aim2_record_base` tables were dropped; they held no data.

## Open questions
- Should the Aim1/Aim2 mixins be merged into one shared base? (not decided in any doc found)

# Related Concepts
- [Core ETL run and lineage tables (etl_run, lineage_group, entity_lineage)](datamodels-core.md): EtlRun/LineageGroup are the targets of the etl_run_id and lineage columns defined here
- [Why datamodels moved from LinkML codegen to hand-written SQLModel + Alembic (PR #112)](../decisions/linkml-to-sqlmodel-alembic.md): why these are mixins rather than tables
- [System overview (start here)](system-overview.md): hub: datamodels layer in the overall system
