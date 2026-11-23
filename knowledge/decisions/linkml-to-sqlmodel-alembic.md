---
type: Decision
title: "Why datamodels moved from LinkML codegen to hand-written SQLModel + Alembic (PR #112)"
description: "Records the February 2026 switch from LinkML-generated SQLAlchemy models to hand-written SQLModel classes managed by Alembic, and what it replaced."
tags: [datamodels, sqlmodel, alembic, linkml, decision, migration]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:41Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models", "alembic/env.py", "alembic/versions/0003_core_tables.py", "alembic/versions_old/f5c8c031aef9_initial_migration_sqlmodel.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/base.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/__init__.py", "docs/datamodels/SCHEMA_DRIFT.md", "docs/datamodels/SQL_FIRST_WORKFLOW.md", "AGENTS.md"]
sources: ["commit 7a41e0e", "https://github.com/sustainability-software-lab/ca-biositing/pull/112", "commit ab8fa6c", "commit dc98b30", "docs/datamodels/SCHEMA_DRIFT.md", "commit 5ebbe4f", "https://github.com/sustainability-software-lab/ca-biositing/pull/108"]
governance: context
---

## Purpose
Record why schema management is SQLModel plus Alembic rather than LinkML code generation.

## Key files
| path:line | role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/models/` | 88 hand-written `table=True` modules across domain subdirectories |
| `alembic/env.py:44` | `target_metadata = SQLModel.metadata` (introduced by this change) |
| `alembic/versions/0003_core_tables.py` | current consolidated table creation |

## What changed (PR #112, commit `7a41e0e`, merged 2026-02-12)
- Replaced LinkML-generated SQLAlchemy models with hand-written SQLModel classes. The commit says 91 models in 15 subdirectories; at HEAD, 88 files under `models/` contain `table=True`, so the count is not directly comparable.
- Replaced the LinkML orchestration and generated code (about 6,700 lines per the PR body).
- Rewrote `alembic/env.py` (removed `sys.path.insert`, uses `SQLModel.metadata`).
- Created a single fresh initial revision `f5c8c031aef9` for all tables, replacing 12+ LinkML-era revisions.
- Materialized views moved to SQLAlchemy Core in `views.py` and a dedicated revision `9c5c72c6d059`.

## Alternatives and trade-offs
- Keep LinkML codegen: schema defined once in YAML, but generated code was hard to review and needed a separate build step.
- Chosen: hand-written SQLModel. Gains: one Python source of truth readable by ETL and webservice. Cost: no generator, so models and migrations can drift (hence `alembic check` in CI and the review requirement).
- Views in SQLAlchemy Core were kept for compilation, but migrations stopped importing them later (see decisions/views-compiled-sql-snapshots).

## Interfaces
- Consumers changed import paths from `ca_biositing.datamodels.schemas.generated.ca_biositing` to `ca_biositing.datamodels.models` (31 files in the commit).

## Gotchas
- Legacy names survive in comments and in `env.py:47` `MAT_VIEW_NAMES`.

## History
- `7a41e0e` (PR #112, 2026-02-12): the switch. PR body links research issue uw-ssec/ca-biositing#113 (outside this repo’s issue history).
- `ab8fa6c` (2025-11-05, PR #66): earlier namespace reorganization that set the `datamodels` layout.

## Open questions
- Whether any LinkML artifacts remain in the repo (inferred: none by name; confirm with `git grep -i linkml` at HEAD).

## Merged detail: Datamodels moved from LinkML-generated code to hand-written SQLModel + Alembic (Feb 2026)

### Purpose
Record the choice to abandon LinkML code generation for the datamodels and manage all schema changes through SQLModel classes plus Alembic migrations.

### Key files
| Path | Role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/models/` | Hand-written SQLModel classes (current source of truth) |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/models/base.py` | Shared bases (`BaseEntity`, `LookupBase`, `Aim1RecordBase`, `Aim2RecordBase`), all `SQLModel` subclasses without `table=True` |
| `docs/datamodels/SCHEMA_DRIFT.md:1-30` | Measures drift between old LinkML-generated SQL and the new SQLModel schema |
| `resources/linkml/` | Gone; last touched by commit 7a41e0e |

### How it works
Models are edited by hand, `pixi run migrate-autogenerate` produces an Alembic revision, `pixi run migrate` applies it (see `architecture/migrations`). There is no generate step: the `generate-models` pixi task was removed (`docs/datamodels/SQL_FIRST_WORKFLOW.md`, "Removed Tasks").

### Interfaces
- Input: developer edits to SQLModel classes.
- Output: `alembic/versions/*.py` revisions; models imported by pipeline, webservice and analysis code.

### Gotchas
- Old LinkML schema materialized four abstract base classes as real tables; SQLModel base classes are non-table, so those 4 tables are gone (SCHEMA_DRIFT.md section 1).
- `text` became `varchar` on about 250 columns across 80 tables. Functionally identical in PostgreSQL (SCHEMA_DRIFT.md section 2).
- Autogenerate only sees models imported in `models/__init__.py`.

### History
- Commit 7a41e0e (2026-02-12), PR #112: "Migrate datamodels from LinkML to SQLModel with Alembic". This is the decision.
- Commit dc98b30 (2026-02-11), PR #108: an earlier SQL-first workflow built on pgschema, which this superseded (see decisions/views-sql-first-to-alembic).
- Sources: https://github.com/sustainability-software-lab/ca-biositing/pull/112

### Rejected alternatives
Keeping LinkML as the schema source (implied by the migration title; the docs do not record the reasoning, so the rationale below is inferred).

### Open questions
- The rationale for dropping LinkML is not written down anywhere in the repo (inferred; confirm with the PR #112 description).
- Docs still reference LinkML modules: see bugs/doc-drift-missing-referenced-artifacts.

## Merged detail: Decision: replace LinkML concrete base tables with SQLModel mixins

### Decision
Adopt SQLModel as the hand-written model layer with Alembic migrations (commit `7a41e0e`, PR #112, 2026-02-12). Shared fields move into non-table mixins (`BaseEntity`, `LookupBase`, `Aim1RecordBase`, `Aim2RecordBase`) instead of concrete base tables.

### Trade-offs (from docs and code)
- Gained: no empty `base_entity`/`lookup_base`/`aim*_record_base` tables; hand-written models are easier to edit.
- Cost: column order changed (inherited columns now first; see `docs/datamodels/SCHEMA_DRIFT.md`, "Column Ordering").
- Cost: `text` to `varchar` drift on about 250 columns across 80 tables (SCHEMA_DRIFT.md section 2; judged no-impact in PostgreSQL).

### Alternatives
Not documented in any file reviewed (open question). The docs only state the outcome.

### Open questions
- Was keeping LinkML output with a regeneration step considered and rejected? No record found.

## Merged detail: Decision: replace LinkML codegen with hand-written SQLModel + Alembic (PR #112)

### Purpose
Records why the schema pipeline moved off LinkML code generation. Current schema rules live in AGENTS.md and architecture/migrations.

### Key files
| Path | Role |
|---|---|
| src/ca_biositing/datamodels/ca_biositing/datamodels/models/ | Hand-written SQLModel classes (91 models, 15 subdirs) introduced by 7a41e0e |
| src/ca_biositing/datamodels/ca_biositing/datamodels/models/__init__.py | Model import registry, touched 12 times in history |
| alembic/versions_old/f5c8c031aef9_initial_migration_sqlmodel.py | Fresh initial migration for all 91 tables created in 7a41e0e |
| resources/linkml/ | Removed by 7a41e0e (ca_biositing.yaml and modules/*) |

### How it works
Commit 7a41e0e (PR #112, Don Setiawan, 2026-02-12) phased the change: Phase 1 SQLModel models plus mixins (BaseEntity, LookupBase, Aim1/Aim2 record bases) and fixes for 45+ table names missing underscores that LinkML generation produced; Phase 2 rewrote database.py and alembic/env.py to use SQLModel.metadata; Phase 3 added Relationship() declarations; Phase 4 materialized views in Alembic. A follow-up 5ebbe4f removed docs/pr/linkml_and_sqla.md.

### Interfaces
Callers: Alembic (`pixi run migrate`, `migrate-autogenerate`), pipeline loaders and webservice, which import models from ca_biositing.datamodels.

### Gotchas
- LinkML-era naming quirks (missing underscores in tablenames) were corrected in this change; older data loads may reference the old names only in archived migrations.
- Pre-squash revisions are archived under alembic/versions_old/, not in the live chain.

### History
- 7a41e0e (2026-02-12) PR #112 (Don Setiawan): LinkML to SQLModel, 91 models.
- dc98b30 (2026-02-11) PR #108 (petercarbsmith): SQL-first workflow with PgSchema, the precursor.
- 5ebbe4f (2026-02-19) PR #123 later touched LinkML doc removal.
- Trade-off recorded implicitly: LinkML gave a single schema source and codegen; SQLModel gives direct Python classes and Alembic autogenerate at the cost of hand-maintained models.

### Open questions
- The rejected LinkML alternative is not documented in a decision record in this repo (inferred from absence of docs; confirm in PR #112 discussion).

# Related Concepts
- [Why alembic history was squashed to 0001-0004 and old revisions moved to versions_old/](squash-migration-history.md): The squash later replaced the chain that this switch started.
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): The Alembic env built by this change.
- [Glossary](../facts/glossary.md): Defines SQLModel and LinkML terms used here.
- [Decision: SQL-first pgschema workflow replaced by SQLModel plus Alembic](views-sql-first-to-alembic.md): Replaced the pgschema-driven SQL-first workflow that preceded it
- [System overview (start here)](../architecture/system-overview.md): Datamodels layer is the shared schema for all components
- [Datamodels base mixins (BaseEntity, LookupBase, Aim1/Aim2RecordBase)](../architecture/datamodels-base.md): the mixins this decision created
- [Project history eras (2025-08 to 2026-10)](../facts/history-eras.md): this change opens the E5 schema pivot
