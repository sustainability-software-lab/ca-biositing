---
type: Decision
title: "Decision: SQL-first pgschema workflow replaced by SQLModel plus Alembic"
description: "Why schema changes moved from a SQL-first pgschema workflow (Feb 2026) to hand-written SQLModel classes with Alembic, leaving pgschema as a diff-only validator."
tags: [decision, pgschema, alembic, sqlmodel, sql-first, datamodels, validation, sql, materialized-views, workflow]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:31Z" }
status: stable
code_refs: ["docs/datamodels/SQL_FIRST_WORKFLOW.md", "pixi.toml", "src/ca_biositing/datamodels/ca_biositing/datamodels/sql_schemas/main.sql", "alembic/", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views", "scripts/compile_mv_fixes.py"]
sources: ["commit dc98b30", "commit 7a41e0e", "commit cb3d782", "docs/datamodels/SQL_FIRST_WORKFLOW.md", "https://github.com/sustainability-software-lab/ca-biositing/pull/108", "https://github.com/sustainability-software-lab/ca-biositing/pull/112", "https://github.com/sustainability-software-lab/ca-biositing/pull/225", "commit 6aa44b6", "commit d961724"]
governance: context
---

## Decision
Hand-written SQLModel classes plus Alembic migrations are the source of truth for schema. `pgschema` is kept only to diff the live DB against reference SQL. The "SQL-first" path (edit SQL, apply with pgschema) was removed.

## Timeline
1. dc98b30 (PR #108, 2026-02-11): "SQL-first workflow implementation with PgSchema and some MatViews/ETL". Added `sql_schemas/`, pgschema tasks, and an early materialized view path.
2. 7a41e0e (PR #112, 2026-02-12): "Migrate datamodels from LinkML to SQLModel with Alembic". Removed `generate-models`, `update-schema`, `schema-apply`, `schema-analytics-apply`, `schema-analytics-refresh` (table in `docs/datamodels/SQL_FIRST_WORKFLOW.md`). MVs were moved into Alembic migrations.
3. cb3d782 (PR #225, 2026-04-13): docs updated to say pgschema is validation-only.

## Alternatives considered (from docs and history)
- Keep pgschema as the apply tool: rejected. The doc says the workflow was "replaced" and pgschema is "retained solely for diffing".
- LinkML code generation: rejected in #112 ("eliminates the LinkML dependency").
- Let Alembic autogenerate handle views: not possible for MVs (AGENTS.md CRITICAL note), which is why the compile step exists (see decisions/views-compiled-sql-snapshots).

## Trade-offs
- Gained: one migration chain for all DDL; models stay in Python; reviewable revisions.
- Cost: MVs need a separate, manual compile path; the reference SQL file is no longer maintained and is stale (facts/views-sql-artifacts-status).

## Governance
Context. Mark as a constraint only if the team wants the rule "all schema changes go through Alembic" enforced; the docs state it but no check was found in this slice.

## Merged detail: pgschema demoted to read-only diff validation; Alembic owns all DDL

### Purpose
Explain why pgschema tasks exist but never modify the database, and why `sql_schemas/main.sql` is not the source of truth.

### Key files
| Path | Role |
|---|---|
| `pixi.toml:234` | `schema-dump` writes `sql_schemas/main.sql` |
| `pixi.toml:237` | `schema-plan` diffs the `public` schema |
| `pixi.toml:240` | `schema-analytics-plan` diffs the `ca_biositing` schema |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/sql_schemas/main.sql` | Reference SQL snapshot (validation only) |
| `docs/datamodels/SQL_FIRST_WORKFLOW.md` | States the decision and lists removed tasks |

### How it works
Source of truth is SQLModel classes plus `alembic/versions/`. `pgschema plan` compares a live DB to `main.sql`. Nothing in the Alembic path calls pgschema.

### Interfaces
- Inputs: local Postgres on localhost:5432, reference SQL file.
- Outputs: a printed diff. `schema-dump` overwrites the reference file.

### Gotchas
- `schema-dump` overwrites `sql_schemas/` silently (SQL_FIRST_WORKFLOW.md "Note").
- Removed tasks: `generate-models`, `update-schema`, `schema-apply`, `schema-analytics-apply`, `schema-analytics-refresh`.
- Known drift between `main.sql` and models is recorded in `docs/datamodels/SCHEMA_DRIFT.md`.

### History
- Commit dc98b30 (2026-02-11), PR #108: SQL-first workflow using pgschema as the primary tool.
- Commit 7a41e0e (2026-02-12), PR #112: pgschema demoted to validation when Alembic became primary.

### Open questions
- Whether `main.sql` is still refreshed after each migration is not enforced anywhere (inferred from the absence of a CI check; confirm in `.github/workflows`).

## Merged detail: Refactor: SQL-first schema iteration with PgSchema and materialized views (PR #108)

### Purpose
Explains the reason for docs/datamodels/SQL_FIRST_WORKFLOW.md and why view SQL is compiled from Python expressions later.

### Key files
| Path | Role |
|---|---|
| docs/datamodels/SQL_FIRST_WORKFLOW.md | Rapid schema iteration path (linked from AGENTS.md) |
| src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/ | Materialized view definitions (9 views) |
| scripts/compile_mv_fixes.py | Later compile step for MV fixes into Alembic (7 changes) |

### How it works
Commit dc98b30 (PR #108, petercarbsmith, 2026-02-11) added the SQL-first workflow with PgSchema diffing and early materialized views. It was followed by 6aa44b6 (PR #159, 2026-03-03), which queried data model views rather than rebuilding joins, and d961724 (PR #258, 2026-04-09), which fixed the view creation and iteration Alembic workflow.

### Interfaces
Inputs: SQL or SQLAlchemy view expressions. Outputs: materialized views in the `data_portal` schema. Callers: pixi tasks refresh-views, schema-plan.

### Gotchas
- Two paths coexist (SQL-first and Alembic migrations); AGENTS.md treats Alembic as the source of truth for schema changes.
- View fixes repeatedly needed follow-up commits (c0f0b62, 22507cc, 12ff1b8).

### History
- dc98b30 2026-02-11 PR #108; 6aa44b6 2026-03-03 PR #159; d961724 2026-04-09 PR #258.

### Open questions
- Whether the SQL-first doc and the MV compile system (2576d03) should be merged into one path (inferred; confirm with maintainers).

# Related Concepts
- [pgschema diff tasks: read-only validation of the live DB against reference SQL](../architecture/views-pgschema-validation.md): The diff-only tooling that remained after this decision.
- [Decision: migrations embed frozen compiled SQL instead of importing view expressions](views-compiled-sql-snapshots.md): Follow-on decision for views, which Alembic autogenerate cannot handle.
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): The Alembic chain this decision made the source of truth.
- [Why datamodels moved from LinkML codegen to hand-written SQLModel + Alembic (PR #112)](linkml-to-sqlmodel-alembic.md): Same migration; this is the pgschema half of it
- [Glossary](../facts/glossary.md): Defines SQL-first and reference SQL terms
- [data_portal materialized views: modules, grain, and consumers](../architecture/views-data-portal-matviews.md): current MV layer (id prefix architecture/views-*)
- [Refactor: MV compile system and data portal view churn (PRs #258, #362, #422)](../facts/history-mv-compile-system.md): later compile-to-migration system
