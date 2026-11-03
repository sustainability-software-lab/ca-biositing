---
type: Decision
title: "Refactor: MV compile system and data portal view churn (PRs #258, #362, #422)"
description: "2026 series of data portal materialized-view changes culminating in a compile-to-migration tool, which explains why view code churns heavily."
tags: [materialized-views, data-portal, alembic, history]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:00Z" }
status: stable
code_refs: ["scripts/compile_mv_fixes.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py", "plans/phase3_materialized_views_assessment.md"]
sources: ["commit 2576d03", "commit 85373ad", "commit c0f0b62", "commit d4f6b33", "plans/phase3_materialized_views_assessment.md", "https://github.com/sustainability-software-lab/ca-biositing/pull/362"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Why view definitions change often and how they are now compiled into migrations.

## Key files
| Path | Role |
|---|---|
| scripts/compile_mv_fixes.py | Compiles view fixes into an Alembic revision (`pixi run compile-mv-fixes`) |
| src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py | Shared view helpers (7 changes) |
| src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py | Most-changed view (9 changes) |
| plans/phase3_materialized_views_assessment.md | 2026-04-20 plan to align nine views and fix has_* flags (QC filtering) |

## How it works
Timeline: 930d868 (PR #220) added data portal schema with views; plans/phase3 (2026-04-20) scoped boolean-indicator and volume-strategy fixes; 4ce9559 (PR #326) audits and view fixes; 2576d03 (PR #362, 2026-05-19) added the new MatView compiling system; c0f0b62 (PRs #422/#431) fixed five view issues; b646a9e (PR #399) added a commodity-direct volume path; 85373ad (PR #492, 2026-10-08) centralized data-quality filters into common.py.

## Interfaces
Inputs: view expressions in data_portal_views/. Outputs: Alembic revisions and `data_portal` materialized views. Callers: webservice analysis endpoints and the frontend visualizations.

## Gotchas
- Views are defined in code but applied through migrations; forgetting to compile leaves DB and code out of sync.
- Provider exclusions (d4f6b33, PR #472) and county filters (12ff1b8, PR #438) were added as ad hoc view edits, a recurring source of churn.

## History
See the commits above; PR numbers are from the subjects.

## Open questions
- Whether plans/phase3 items are all complete (not verified; the plan is dated 2026-04-20 and may be stale).

# Related Concepts
- [Decision: SQL-first pgschema workflow replaced by SQLModel plus Alembic](../decisions/views-sql-first-to-alembic.md): precursor SQL-first path
- [data_portal materialized views: modules, grain, and consumers](../architecture/views-data-portal-matviews.md): current view layer (id prefix architecture/views-*)
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): where compiled view fixes land
