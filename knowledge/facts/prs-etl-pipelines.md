---
type: Fact
title: "Merged PRs: ETL pipelines and source loads"
description: "Index of merged PRs for ETL pipelines and loaders (geocoding, Google Sheets, USDA, infrastructure), grouped by merge month; merged rows through 2026-10-22 included."
tags: [pipeline, etl, history, prs]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:28Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/pipeline/**"]
stale_after: "2026-11-15"
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/493", "https://github.com/sustainability-software-lab/ca-biositing/pull/490", "https://github.com/sustainability-software-lab/ca-biositing/pull/462", "https://github.com/sustainability-software-lab/ca-biositing/pull/456", "https://github.com/sustainability-software-lab/ca-biositing/pull/451", "https://github.com/sustainability-software-lab/ca-biositing/pulls?q=is%3Apr+is%3Amerged", "https://github.com/sustainability-software-lab/ca-biositing/pull/514"]
---

## Purpose
ETL PRs that added or changed source-data pipelines (USDA, LandIQ, Billion Ton, analytical suite, fermentation, gasification, biodiesel, almond, cotton/wheat resource fixes) under src/ca_biositing/pipeline.

Scope: 40 merged PRs. Authors: @petercarbsmith (31), @mglbleta (5), @lsetiawan (2), @avi9664 (1). Grouped by merge month, newest first. Rows merged from 2026-10-17 through 2026-10-22 were added on 2026-10-22; author counts above predate them. "areas" is the top three path categories touched, computed from the PR file list (not reviewed line by line).

## Key files
Areas in this theme are described by the linked architecture concept (`architecture/pipeline-*`). PR bodies, not files, are the primary source for this index.

## How it works
Index only. Each row links to the PR on GitHub. Re-run `gh pr list --state merged` to refresh; this snapshot is as of HEAD a2c8de8 (2026-10-22).

## Interfaces
- Inputs: GitHub PR metadata (`gh pr list --repo sustainability-software-lab/ca-biositing`).
- Outputs: none. This concept is a lookup table.

## Gotchas
- Titles are as merged; some PRs were re-filed (e.g. #422 and #431 share a title; #247 and #256 are a closed duplicate of #248/#257).
- Merge months use `mergedAt`; PRs that were never merged are in `facts/prs-closed-unmerged`.

## History
40 PRs in this theme. Earliest merged 2025-08 (#10); latest 2026-10-22 (#514).

## Open questions
- Whether the author list reflects current ownership (inferred from PR authorship only; confirm with maintainers).

## Merged PRs by month

### 2026-10 (3)
- #514 [feat (etl): add infrastructure ETL pipelines (second attempt)](https://github.com/sustainability-software-lab/ca-biositing/pull/514) · @avi9664 · 2026-10-22
- #493 [refactor(pipeline): extract gasification archival-prep into transform task](https://github.com/sustainability-software-lab/ca-biositing/pull/493) · @petercarbsmith · 2026-10-08 · areas: pipeline
- #490 [fix: create provider table in analysis test fixture](https://github.com/sustainability-software-lab/ca-biositing/pull/490) · @petercarbsmith · 2026-10-02 · areas: tests

### 2026-09 (1)
- #456 [feat(etl): separate geocoding and etl pipelines](https://github.com/sustainability-software-lab/ca-biositing/pull/456) · @avi9664 · 2026-09-09 · areas: other, pipeline, docs

### 2026-07 (3)
- #462 [Fix: Map experiment_id in fermentation_record transform](https://github.com/sustainability-software-lab/ca-biositing/pull/462) · @petercarbsmith · 2026-07-28 · areas: other, pipeline
- #451 [fix: resolve missing cotton volumes and automate mapping sync](https://github.com/sustainability-software-lab/ca-biositing/pull/451) · @petercarbsmith · 2026-07-08 · areas: analysis/exports, pipeline, other
- #443 [Fix field sample collection timestamp mapping for 2024 dates](https://github.com/sustainability-software-lab/ca-biositing/pull/443) · @petercarbsmith · 2026-07-06 · areas: pipeline

### 2026-06 (8)
- #441 [Do not include wheat straw in totals](https://github.com/sustainability-software-lab/ca-biositing/pull/441) · @petercarbsmith · 2026-06-23 · areas: deploy/resources
- #436 [Dynamic top commodity discovery for USDA pipeline and resource_info.json revamp](https://github.com/sustainability-software-lab/ca-biositing/pull/436) · @petercarbsmith · 2026-06-23 · areas: pipeline, deploy/resources, scripts
- #434 [Ag expand indexes](https://github.com/sustainability-software-lab/ca-biositing/pull/434) · @petercarbsmith · 2026-06-22 · areas: alembic, scripts, pipeline
- #432 [Expand USDA ETL to all California counties](https://github.com/sustainability-software-lab/ca-biositing/pull/432) · @petercarbsmith · 2026-06-20 · areas: docs, agent-skills, pipeline
- #406 [fix(etl): include static data in production docker image](https://github.com/sustainability-software-lab/ca-biositing/pull/406) · @petercarbsmith · 2026-06-10 · areas: deploy/resources
- #395 [adding reactor name to the gasification_timeseries](https://github.com/sustainability-software-lab/ca-biositing/pull/395) · @petercarbsmith · 2026-06-09 · areas: pipeline, alembic, datamodels
- #376 [fix: File object metadata unique url fix](https://github.com/sustainability-software-lab/ca-biositing/pull/376) · @petercarbsmith · 2026-06-02 · areas: scripts, pipeline, tests
- #377 [Gasification etl](https://github.com/sustainability-software-lab/ca-biositing/pull/377) · @petercarbsmith · 2026-06-01 · areas: pipeline, datamodels, other

### 2026-05 (9)
- #381 [Fix: Field sample duplicates leading to incorrect sample counts](https://github.com/sustainability-software-lab/ca-biositing/pull/381) · @petercarbsmith · 2026-05-28 · areas: other, deploy/resources, scripts
- #380 [commenting out the biodiesel_plants etl](https://github.com/sustainability-software-lab/ca-biositing/pull/380) · @petercarbsmith · 2026-05-27 · areas: deploy/resources
- #373 [Feat: Change LandIQ Data to 2024 Provisional](https://github.com/sustainability-software-lab/ca-biositing/pull/373) · @petercarbsmith · 2026-05-22 · areas: pipeline, other, deploy/resources
- #370 [Bioconversion ETL and View Improvements](https://github.com/sustainability-software-lab/ca-biositing/pull/370) · @petercarbsmith · 2026-05-22 · areas: pipeline, datamodels, alembic
- #320 [Almond ETL](https://github.com/sustainability-software-lab/ca-biositing/pull/320) · @mglbleta · 2026-05-19 · areas: pipeline, scripts, datamodels
- #360 [fix: Nulls to Zero or XRF an ICP](https://github.com/sustainability-software-lab/ca-biositing/pull/360) · @petercarbsmith · 2026-05-18 · areas: pipeline
- #358 [Feat: ETL for AIM1 exper_id’s and better proximate analysis filter for mv_biomass_composition](https://github.com/sustainability-software-lab/ca-biositing/pull/358) · @petercarbsmith · 2026-05-14 · areas: pipeline, alembic, other
- #344 [Avi biodiesel_etl](https://github.com/sustainability-software-lab/ca-biositing/pull/344) · @petercarbsmith · 2026-05-14 · areas: pipeline, datamodels, deploy/resources
- #268 [mv_biomass_fermentation fixes](https://github.com/sustainability-software-lab/ca-biositing/pull/268) · @mglbleta · 2026-05-01 · areas: pipeline, datamodels, tests

### 2026-04 (4)
- #288 [Feat: Residue Factor ETL, ResourceImage and data fixes, mv_biomass_search refinement](https://github.com/sustainability-software-lab/ca-biositing/pull/288) · @petercarbsmith · 2026-04-29 · areas: scripts, datamodels, pipeline
- #265 [Qualitative data ETL & MVs](https://github.com/sustainability-software-lab/ca-biositing/pull/265) · @mglbleta · 2026-04-23 · areas: pipeline, datamodels, scripts
- #260 [feat: Multiple ETL refinements and fixes](https://github.com/sustainability-software-lab/ca-biositing/pull/260) · @petercarbsmith · 2026-04-14 · areas: pipeline, datamodels, tests
- #217 [Feat: Gasification ETL Pipeline](https://github.com/sustainability-software-lab/ca-biositing/pull/217) · @petercarbsmith · 2026-04-01 · areas: pipeline, docs, datamodels

### 2026-03 (3)
- #173 [more resources mapped to USDA commodities and mapping system improvements](https://github.com/sustainability-software-lab/ca-biositing/pull/173) · @mglbleta · 2026-03-19 · areas: pipeline, docs, other
- #154 [Aim 2 Fermentation ETL and Analytical View Refinement](https://github.com/sustainability-software-lab/ca-biositing/pull/154) · @petercarbsmith · 2026-03-18 · areas: pipeline, alembic, scripts
- #149 [feat: Fix Analysis API Blocking due to empty `location_address` table](https://github.com/sustainability-software-lab/ca-biositing/pull/149) · @petercarbsmith · 2026-03-18 · areas: pipeline, other

### 2026-02 (7)
- #138 [fix: move USDA diagnostic scripts out of tests to fix CI](https://github.com/sustainability-software-lab/ca-biositing/pull/138) · @lsetiawan · 2026-02-24 · areas: pipeline
- #127 [fix: staging cloud run ETL flow parity and validation](https://github.com/sustainability-software-lab/ca-biositing/pull/127) · @lsetiawan · 2026-02-23 · areas: pipeline, deploy/resources, other
- #124 [Usda manual fix](https://github.com/sustainability-software-lab/ca-biositing/pull/124) · @mglbleta · 2026-02-19 · areas: pipeline, docs, other
- #123 [feat: comprehensive analytical suite ETL implementation (ICP, XRF, Calorimetry, XRD)](https://github.com/sustainability-software-lab/ca-biositing/pull/123) · @petercarbsmith · 2026-02-19 · areas: pipeline, docs, alembic
- #122 [fix: Land IQ ETL Normalization and Casing Fixes](https://github.com/sustainability-software-lab/ca-biositing/pull/122) · @petercarbsmith · 2026-02-19 · areas: pipeline, docs, deploy/resources
- #121 [feat: Implementation of Billion Ton 2023 Agricultural ETL Pipeline](https://github.com/sustainability-software-lab/ca-biositing/pull/121) · @petercarbsmith · 2026-02-19 · areas: pipeline, alembic, docs
- #84 [Berkeley Upstream integration](https://github.com/sustainability-software-lab/ca-biositing/pull/84) · @petercarbsmith · 2026-02-05 · areas: deploy/resources, docs, other

### 2025-10 (2)
- #53 [feat: Prefect implementation and directory reorg](https://github.com/sustainability-software-lab/ca-biositing/pull/53) · @petercarbsmith · 2025-10-29 · areas: other, alembic, docs
- #26 [Peter’s ETL Pipeline Merge](https://github.com/sustainability-software-lab/ca-biositing/pull/26) · @petercarbsmith · 2025-10-13 · areas: other, docs, tests

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state hub for the repo.
