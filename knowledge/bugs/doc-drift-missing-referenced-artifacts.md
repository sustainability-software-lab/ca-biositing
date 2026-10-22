---
type: Bug
title: "Docs reference files that do not exist: plans/sql_first_workflow.md, scripts/extract_view_sql.py, resources/linkml, migration 9e8f7a6b5c4e"
description: Several docs and one commit body point to paths absent from HEAD e41d00d. Each dead link is listed with the referring file and line.
tags: [docs, drift, broken-links, alembic, bug, stale]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:57Z" }
status: stable
code_refs: ["docs/datamodels/SCHEMA_DRIFT.md", "alembic/AGENTS.md", "alembic/VIEW_SQL_REFERENCE.md", "docs/pipeline/USDA/ANALYTICS_HANDOFF.md", "docs/pipeline/USDA/USDA_ETL_HANDOFF.md", "alembic/env.py", "alembic/versions/0003_core_tables.py", "alembic/versions/0001_initial_infra.py", "docs/pipeline/ALEMBIC_WORKFLOW.md"]
sources: ["docs/datamodels/SCHEMA_DRIFT.md:88", "alembic/AGENTS.md:111", "docs/pipeline/USDA/ANALYTICS_HANDOFF.md:320", "commit 85373ad", "commit d961724", "commit db578ad", "commit 2576d03", "alembic/AGENTS.md"]
governance: context
stale_after: "2026-11-16"
---

## Purpose
List dead references in docs so readers do not chase them.

## Evidence (all verified absent at HEAD e41d00d)
| Missing path | Referenced from |
|---|---|
| `plans/sql_first_workflow.md` | `docs/datamodels/SCHEMA_DRIFT.md:88` |
| `plans/jiggly-crafting-planet.md` | commit 85373ad message (not in repo; `plans/` has only `phase3_materialized_views_assessment.md`) |
| `scripts/extract_view_sql.py` | `alembic/AGENTS.md:111`, `alembic/VIEW_SQL_REFERENCE.md:63,78,92,160,169` |
| `alembic/versions/9e8f7a6b5c4e_recreate_mv_biomass_search_with_raw_sql.py` | `alembic/AGENTS.md` (template example) |
| `resources/linkml/modules/` | `docs/pipeline/USDA/ANALYTICS_HANDOFF.md:320-322`, `docs/pipeline/USDA/USDA_ETL_HANDOFF.md:207-210` |

## Impact
Migration authors following `alembic/AGENTS.md` cannot extract view SQL. The LinkML references are historical; they describe a removed layer (see decisions/linkml-to-sqlmodel-alembic).

## Fix
Remove or update each reference. For the LinkML lines, add a "historical" note.

## Merged detail: Alembic docs and comments reference files and names that no longer exist

### Symptom
Following the docs fails or leads to the wrong place:
- `alembic/AGENTS.md` tells you to run `pixi run python scripts/extract_view_sql.py` and `scripts/generate_raw_sql_migration.py`. Neither exists at HEAD (`scripts/` has no such file).
- `alembic/AGENTS.md` cites `alembic/versions/9e8f7a6b5c4e_recreate_mv_biomass_search_with_raw_sql.py`. No such file exists in `versions/` (it was described in commit `d961724` but is not in the live chain).
- `alembic/AGENTS.md` links `docs/pipeline/ALEMBIC_WORKFLOW.md`, which says MVs are defined in `src/.../datamodels/ca_biositing/datamodels/views.py`. That file holds the 7 legacy views. The 9 current `mv_*` definitions are in `data_portal_views/`.
- `alembic/VIEW_SQL_REFERENCE.md` exists but is a reference document, not a loader.
- `views.py` docstring says 7 MVs (correct for that file); `data_portal_views` has 9 (per `alembic/AGENTS.md`).
- `alembic/env.py:47-55` `MAT_VIEW_NAMES` lists legacy names.
- `0003_core_tables.py:2` header says `Revision ID: 87835166014d` but the variable is `"0003"`.
- `0001_initial_infra.py:4` `Create Date: 2024-05-08` predates the squash.
- `0008_prox_exper_id_filter.py` and `0005_mv_view_fixes.py` headers say ’Recreate all 9 materialized views’ (copy-paste from earlier).

### Root cause
The squash (`db578ad`) and the view refactor (`d961724`, `2576d03`) changed the layout, and docs were not all updated. Revision headers were copied from earlier files.

### Impact
Agents may run non-existent scripts or edit the wrong view file. The header mismatch does not affect Alembic (it reads the variable).

### Fix
Update `alembic/AGENTS.md` to point at `scripts/compile_mv_fixes.py` and `data_portal_views/`. Remove or correct the 7-vs-9 and `views.py` references. Correct the 0003 header.

### Status
Open at HEAD `e41d00d`.

# Related Concepts
- [Why datamodels moved from LinkML codegen to hand-written SQLModel + Alembic (PR #112)](../decisions/linkml-to-sqlmodel-alembic.md): The LinkML references are leftovers of that migration
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): Migration guidance points to missing scripts
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Dead-link list is a snapshot
- [Decision: migrations embed frozen compiled SQL instead of importing view expressions](../decisions/views-compiled-sql-snapshots.md): The workflow that the stale references describe.
