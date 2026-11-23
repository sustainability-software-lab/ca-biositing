---
type: Fact
title: "Merged PRs: datamodels, Alembic migrations, and materialized views"
description: "Index of merged PRs that changed SQLModel models, Alembic revisions, or data_portal materialized views, grouped by merge month; merged rows through 2026-10-22 included."
tags: [datamodels, alembic, views, prs]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:29Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/datamodels/**"]
stale_after: "2026-11-15"
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/492", "https://github.com/sustainability-software-lab/ca-biositing/pull/472", "https://github.com/sustainability-software-lab/ca-biositing/pull/439", "https://github.com/sustainability-software-lab/ca-biositing/pull/438", "https://github.com/sustainability-software-lab/ca-biositing/pull/431", "https://github.com/sustainability-software-lab/ca-biositing/pulls?q=is%3Apr+is%3Amerged", "https://github.com/sustainability-software-lab/ca-biositing/pull/523"]
---

## Purpose
Schema and view PRs: LinkML to SQLModel migration, materialized-view compilation system, view fixes, and data-quality filters.

Scope: 21 merged PRs. Authors: @petercarbsmith (16), @lsetiawan (2), @mglbleta (1), @app/copilot-swe-agent (1). Grouped by merge month, newest first. Rows merged from 2026-10-17 through 2026-10-22 were added on 2026-10-22; author counts above predate them. "areas" is the top three path categories touched, computed from the PR file list (not reviewed line by line).

## Key files
Areas in this theme are described by the linked architecture concept (`architecture/datamodels-*`). PR bodies, not files, are the primary source for this index.

## How it works
Index only. Each row links to the PR on GitHub. Re-run `gh pr list --state merged` to refresh; this snapshot is as of HEAD a2c8de8 (2026-10-22).

## Interfaces
- Inputs: GitHub PR metadata (`gh pr list --repo sustainability-software-lab/ca-biositing`).
- Outputs: none. This concept is a lookup table.

## Gotchas
- Titles are as merged; some PRs were re-filed (e.g. #422 and #431 share a title; #247 and #256 are a closed duplicate of #248/#257).
- Merge months use `mergedAt`; PRs that were never merged are in `facts/prs-closed-unmerged`.

## History
21 PRs in this theme. Earliest merged 2025-08 (#10); latest 2026-10-19 (#523).

## Open questions
- Whether the author list reflects current ownership (inferred from PR authorship only; confirm with maintainers).

## Merged PRs by month

### 2026-10 (2)
- #523 [feat(qc): add QcReviewDecision model and ETL upsert guard](https://github.com/sustainability-software-lab/ca-biositing/pull/523) · @petercarbsmith · 2026-10-19
- #492 [Centralize data-quality filters into common.py (#476, #480)](https://github.com/sustainability-software-lab/ca-biositing/pull/492) · @petercarbsmith · 2026-10-08 · areas: datamodels, audit, alembic

### 2026-09 (1)
- #472 [Exclude jaguar provider from materialized views and plots](https://github.com/sustainability-software-lab/ca-biositing/pull/472) · @petercarbsmith · 2026-09-02 · areas: analysis/exports, datamodels, alembic

### 2026-06 (7)
- #439 [Fix duplicate almond hulls in volume estimate view](https://github.com/sustainability-software-lab/ca-biositing/pull/439) · @petercarbsmith · 2026-06-23 · areas: alembic, datamodels
- #438 [Filter mv_biomass_volume_estimate by San Joaquin, Stanislaus, and Merced counties](https://github.com/sustainability-software-lab/ca-biositing/pull/438) · @petercarbsmith · 2026-06-23 · areas: alembic, datamodels
- #431 [Fix multiple data portal view issues (#396, #389, #413, #419, #409) (…](https://github.com/sustainability-software-lab/ca-biositing/pull/431) · @petercarbsmith · 2026-06-18 · areas: datamodels, alembic
- #422 [Fix multiple data portal view issues (#396, #389, #413, #419, #409)](https://github.com/sustainability-software-lab/ca-biositing/pull/422) · @petercarbsmith · 2026-06-18 · areas: datamodels, alembic
- #399 [feat: add commodity-direct path to mv_biomass_volume_estimate](https://github.com/sustainability-software-lab/ca-biositing/pull/399) · @petercarbsmith · 2026-06-10 · areas: pipeline, other, agent-skills
- #386 [food_processing_facilities datamodel ready](https://github.com/sustainability-software-lab/ca-biositing/pull/386) · @mglbleta · 2026-06-01 · areas: datamodels
- #382 [implementing filters into the ca_biositing anlaysis tables](https://github.com/sustainability-software-lab/ca-biositing/pull/382) · @petercarbsmith · 2026-06-01 · areas: datamodels, tests, alembic

### 2026-05 (4)
- #362 [feat: New MatView compiling system and some specific materialized view fixes](https://github.com/sustainability-software-lab/ca-biositing/pull/362) · @petercarbsmith · 2026-05-20 · areas: datamodels, alembic, docs
- #326 [Audits and View Fixes](https://github.com/sustainability-software-lab/ca-biositing/pull/326) · @petercarbsmith · 2026-05-12 · areas: audit, datamodels, scripts
- #340 [Database Maintenance](https://github.com/sustainability-software-lab/ca-biositing/pull/340) · @petercarbsmith · 2026-05-09 · areas: alembic, deploy/resources, other
- #310 [Strain name fix](https://github.com/sustainability-software-lab/ca-biositing/pull/310) · @petercarbsmith · 2026-05-01 · areas: alembic, datamodels, tests

### 2026-04 (3)
- #258 [Fix: View Creation and Iteration Alembic Workflow](https://github.com/sustainability-software-lab/ca-biositing/pull/258) · @petercarbsmith · 2026-04-09 · areas: datamodels, docs, alembic
- #243 [Granting biocirv_read_only Access to Data Portal Schema](https://github.com/sustainability-software-lab/ca-biositing/pull/243) · @petercarbsmith · 2026-04-01 · areas: alembic
- #220 [Feat:Data-portal-schema With Views](https://github.com/sustainability-software-lab/ca-biositing/pull/220) · @petercarbsmith · 2026-04-01 · areas: pipeline, docs, datamodels

### 2026-02 (3)
- #129 [feat: add pg_trgm, unaccent, and btree_gin PostgreSQL extensions](https://github.com/sustainability-software-lab/ca-biositing/pull/129) · @lsetiawan · 2026-02-23 · areas: alembic, deploy/resources
- #112 [refactor: Migrate datamodels from LinkML to SQLModel with Alembic](https://github.com/sustainability-software-lab/ca-biositing/pull/112) · @lsetiawan · 2026-02-12 · areas: alembic, deploy/resources, docs
- #108 [feat: SQL-first workflow implementation with PgSchema and some MatViews/ETL](https://github.com/sustainability-software-lab/ca-biositing/pull/108) · @petercarbsmith · 2026-02-12 · areas: alembic, deploy/resources, docs

### 2025-11 (1)
- #66 [refactor: Reorganize into PEP 420 namespace packages for datamodels, pipeline, webservice](https://github.com/sustainability-software-lab/ca-biositing/pull/66) · @app/copilot-swe-agent · 2025-11-05 · areas: pipeline, datamodels, deploy/resources

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state hub for the repo.
- [PR #513 (open): replace hardcoded IDs with name joins in the volume view and ETL transforms](pr-513.md): open view-ID fix PR touching mv_biomass_volume_estimate, as of 2026-10-22
