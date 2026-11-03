---
type: Architecture
title: "Pixi tasks for Alembic migrations, materialized views, DB reset, audits and pgschema"
description: "The pixi task family that generates and applies Alembic migrations, compiles MV fixes, refreshes views, resets databases, runs audits and calls the pgschema validation tools."
tags: [tooling, pixi, alembic, migrations, views, database]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:26:44Z" }
status: stable
code_refs: ["pixi.toml", "scripts/db_reset.py", "scripts/compile_mv_fixes.py", "alembic/versions", "alembic/versions_old", "src/ca_biositing/datamodels/ca_biositing/datamodels/views.py", "audit/main.py"]
sources: ["pixi.toml", "alembic.ini", "commit 81a27bf", "https://github.com/sustainability-software-lab/ca-biositing/pull/164", "commit 707afa8", ".agents/rules/schema-and-migrations.md"]
governance: context
---

## Purpose
Database lifecycle commands. Schema truth is the SQLModel code; Alembic applies it; pgschema is validation only.

## Key files
| Path:line | Role |
| --- | --- |
| pixi.toml:66-80 | `initial-migration`: docker-compose run `setup-db` service, `alembic revision --autogenerate -m "Initial migration"` |
| pixi.toml:205-212 | `migrate` (`alembic upgrade head`), `migrate-autogenerate`, `compile-mv-fixes` (scripts/compile_mv_fixes.py) |
| pixi.toml:214-220 | `db-reset-{local,staging,production}` and `-force` variants -> scripts/db_reset.py |
| pixi.toml:223-226 | `audit`, `audit-staging` (audit/main.py), `filter-baseline-snapshot` (scripts/filter_funnel_snapshot.py) |
| pixi.toml:228-240 | `install-pgschema` (scripts/install-pgschema.sh), `schema-dump`, `schema-plan`, `schema-analytics-plan` |
| pixi.toml:242-244 | `schema-analytics-list`, `refresh-views` (calls `refresh_all_views(get_engine())` from datamodels.views) |
| alembic.ini, alembic/ | Alembic configuration; `alembic/versions_old/` holds retired revisions |
| src/ca_biositing/datamodels/ca_biositing/datamodels/sql_schemas/main.sql | Reference SQL dumped by `schema-dump` |

## How it works
- Model change: edit SQLModel -> `pixi run migrate-autogenerate -m "..."` -> review `alembic/versions/` -> `pixi run migrate`.
- MV change: edit view in `data_portal_views/` -> `pixi run compile-mv-fixes -m "..."` -> new manual revision; refresh with `pixi run refresh-views`.
- `schema-plan` and `schema-analytics-plan` diff the live DB against `main.sql` using a shadow DB (`biocirv_db_shadow`); they do not change anything.

## Interfaces
- Inputs: running `db` container (`localhost:5432`, user `biocirv_user`, db `biocirv_db`).
- Outputs: Alembic revisions, DB state, audit output under `audit/output/`.
- Callers: developers; `.github/workflows/migrations.yml` runs `alembic upgrade head`, `check` and `downgrade base` directly; cloud migrations run `scripts/cloud-migrate-ci.sh` (see architecture/tooling-task-cloud-deployment).

## Gotchas
- Plaintext local credential `biocirv_dev_password` appears in `schema-dump`, `schema-plan`, `schema-analytics-plan` (pixi.toml:234-240). It is a local-dev password, but it is committed in the manifest.
- `db-reset-staging` and `db-reset-production` prompt for confirmation; the `-force` variants skip it. Read the `db_reset.py` guard before using them.
- `schema-*` tasks depend on the `pgschema` binary, which is not on conda-forge and must come from `install-pgschema`.
- `initial-migration` declares `outputs = ["alembic/versions/*_initial_migration.py"]`; re-running it creates a second initial revision unless the first is removed (inferred from the autogenerate behavior; confirm before use).
- `refresh-views` needs a populated DB; a refresh before loads gives empty MVs.

## History
- Alembic migrations and CI checks: `81a27bf` (#164, 2026-03-02). Analytics schema and MV tasks: `707afa8` (#442) and earlier. `alembic/versions_old/` retains pre-consolidation revisions. Audit scripts in `audit/` carry their own AGENTS.md.

## Open questions
- Whether `schema-plan` and `schema-analytics-plan` still point at the right reference file after the Alembic-first migration (they are described as validation only).

# Related Concepts
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](migrations.md): Alembic revision history and conventions in the datamodels slice
- [data_portal materialized views: modules, grain, and consumers](views-data-portal-matviews.md): The materialized views these tasks refresh (slice prefix)
- [ER diagram: core, places, people, auth and infrastructure tables with verified FKs](datamodels-er-diagram.md): SQLModel classes that migrations are generated from
- [System overview (start here)](system-overview.md): Hub
