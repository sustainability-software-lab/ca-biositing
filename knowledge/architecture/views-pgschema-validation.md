---
type: Architecture
title: "pgschema diff tasks: read-only validation of the live DB against reference SQL"
description: "What the schema-plan, schema-analytics-plan, schema-analytics-list and schema-dump pixi tasks do, which credentials they hardcode, and the caveats that come from the stale reference dump."
tags: [pgschema, validation, pixi, schema, sql-first]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:29Z" }
status: stable
code_refs: ["pixi.toml", "src/ca_biositing/datamodels/ca_biositing/datamodels/sql_schemas/main.sql", "docs/datamodels/SQL_FIRST_WORKFLOW.md", "scripts/install-pgschema.sh"]
sources: ["commit dc98b30", "commit 7a41e0e", "commit cb3d782", "docs/datamodels/SQL_FIRST_WORKFLOW.md", "https://github.com/sustainability-software-lab/ca-biositing/pull/108", "https://github.com/sustainability-software-lab/ca-biositing/pull/112"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Optional diff tooling. `pgschema` compares the live database against `sql_schemas/main.sql`. It never applies changes. Operational schema management is Alembic (see decisions/views-sql-first-to-alembic).

## Key files
| Path | Task / role |
|---|---|
| `pixi.toml:228-230` | `install-pgschema` task (`scripts/install-pgschema.sh`); binary is not on conda-forge |
| `pixi.toml:234` | `schema-dump`: `pgschema dump` writes to `sql_schemas/main.sql` (overwrites) |
| `pixi.toml:237` | `schema-plan`: diff `--schema public` |
| `pixi.toml:240` | `schema-analytics-plan`: diff `--schema ca_biositing` |
| `pixi.toml:243` | `schema-analytics-list`: runs `access-db` (docker-compose) to list `pg_matviews` |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/sql_schemas/main.sql` | The reference file (pgschema dump) |

## How it works
Each plan task runs `pgschema plan` against `localhost:5432`, user `biocirv_user`, database `biocirv_db`, with `--plan-db biocirv_db_shadow` as the shadow DB, `PGSSLMODE=disable`, and the password inline in `pixi.toml`.

## Interfaces
- Inputs: a running local Postgres (`pixi run start-services`) and the `pgschema` binary.
- Outputs: a textual plan on stdout. No DB writes.

## Gotchas
- Credentials (`biocirv_dev_password`) are written in plain text in `pixi.toml`. Local-dev only; treat any other use as a concern.
- `main.sql` contains **zero** materialized views and **zero** references to `ca_biositing.` or `data_portal.` (checked). `schema-analytics-plan` therefore compares a schema against a file with no objects in it (inferred: plan will show everything as to-be-created; confirm by running).
- `schema-dump` overwrites the reference file; run it only when you intend to replace the reference.
- `main.sql` was last changed in 7a41e0e (2026-02-12), before any view migration.

## History
- dc98b30 (PR #108, 2026-02-11): SQL-first workflow with pgschema as primary tool, which created `sql_schemas/`.
- 7a41e0e (PR #112, 2026-02-12): pgschema demoted to validation only; `docs/datamodels/SQL_FIRST_WORKFLOW.md` updated (cb3d782, PR #225).

## Open questions
- Whether anyone still runs `schema-analytics-plan` in CI or only by hand (no CI reference found in this slice).

# Related Concepts
- [Decision: SQL-first pgschema workflow replaced by SQLModel plus Alembic](../decisions/views-sql-first-to-alembic.md): Why pgschema is only a diff tool now.
- [Status of view SQL reference files and docs: what is stale or orphaned](../facts/views-sql-artifacts-status.md): Detail on how stale the reference SQL files are.
- [Materialized view system: two schemas, one compile-and-refresh loop](views-overview.md): Diffs do not cover the materialized view definitions.
