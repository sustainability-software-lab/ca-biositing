---
type: Architecture
title: "common.py: the single gatekeeper for view data-quality filters"
description: "Lists every filter dimension, its constant, and its helper in data_portal_views/common.py, with the current exclusion values and the places that call them."
tags: [views, data-quality, filters, qc, common.py, pipeline, datamodels, fact]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:26Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py", "src/ca_biositing/datamodels/tests/test_view_filters.py", "scripts/filter_funnel_snapshot.py"]
sources: ["commit 85373ad", "commit d4f6b33", "commit 5ab52b8", "commit c0f0b62", "commit 4ce9559", "https://github.com/sustainability-software-lab/ca-biositing/pull/472", "https://github.com/sustainability-software-lab/ca-biositing/pull/492", "src/ca_biositing/datamodels/README.md", "https://github.com/sustainability-software-lab/ca-biositing/pull/476", "https://github.com/sustainability-software-lab/ca-biositing/pull/480", "audit/output/filter_baseline/phase0_baseline.json"]
governance: constraint
---

## Purpose
`data_portal_views/common.py` is where every record-exclusion rule for the views lives. Its docstring states the rule: add exclusions here, then run `pixi run compile-mv-fixes`; do not add inline literals to view modules.

## Key files
| Path:line | Symbol | Current value / role |
|---|---|---|
| `common.py:42` | `EXCLUDED_RESOURCES` | 7 entries: sargassum, #n/a, lab media, alfalfa, almond hulls and shells mix, almond shells and hulls mix, almond woodchips |
| `common.py:57` | `EXCLUDED_PRIMARY_AG_PRODUCTS` | empty |
| `common.py:64` / `:72` | `EXCLUDED_EXPERIMENTS`, `EXCLUDED_REPLICATES` | empty placeholders |
| `common.py:78` | `EXCLUDED_PROVIDERS` | `["jaguar"]` |
| `common.py:88` / `:91` | `MIN_PRODUCTION_DATA_YEAR = 2017`, `get_min_year_filter` | used by `mv_usda_county_production` and `mv_biomass_volume_estimate` |
| `common.py:104` / `:107` | `EXCLUDED_QC_STATUSES = ["fail"]`, `get_qc_status_filter` | used widely |
| `common.py:117-120` | `PROXIMATE_SUM_*` (95-105), `COMPOSITIONAL_SUM_*` (40-105), `ICP_MAX_PPM` (500000), `ULTIMATE_MAX_PERCENT` (100) | value checks |
| `common.py:123` | `ULTIMATE_PARAMETERS` | carbon, nitrogen, oxygen, sulfur, hydrogen |
| `common.py:130`, `:148` | `analysis_metrics`, `resource_analysis_map` | shared subqueries (QC applied in the union) |
| `common.py:218` / `:225` | `get_resource_filter`, `get_provider_filter` | resource and provider exclusions |
| `common.py:233` / `:254` | `get_ultimate_filter`, `get_icp_filter` | parameter whitelist, value caps |
| `common.py:277` | `get_sum_constraints_subquery` | per-experiment proximate and compositional sums |
| `common.py:340` | `log_filter_summary` | prints rows removed per filter (used by `refresh_all_views(log_summary=True)`) |

Structural tests: `src/ca_biositing/datamodels/tests/test_view_filters.py` (assertions on compiled SQL).

## How it works
Each view module imports the helpers it needs. Examples: `mv_biomass_fermentation.py` uses `get_qc_status_filter` and `get_provider_filter`; `mv_biomass_composition.py` uses the ultimate and ICP helpers; `views.py` (lines 300-310) uses the analysis helpers.

## Interfaces
- Inputs: model columns (`qc_pass`, `name`, `codename`, `year`, `value`, `unit`).
- Outputs: SQLAlchemy boolean clauses. Excluded data never reaches the MV, so a filter change requires recompiling and migrating the affected views.

## Gotchas
- Several comments still say "Not yet wired into call sites (Phase 2/3)". The helpers are now used (for example `get_qc_status_filter` and `get_min_year_filter`). Trust the call sites, not those comments.
- Most `EXCLUDED_RESOURCES` entries say "rationale undocumented" (2026-05). Dates and issue references are only partly recorded.
- `usda_census_view`, `mv_usda_county_production` and `mv_billion_ton_county_production` apply none of these filters by design (README "Data-Quality Filters" section).
- Filter changes are not retroactive: they show up only after `compile-mv-fixes`, `migrate`, and `refresh-views`.

## History
- 5ab52b8 (PR #382, 2026-06-01): filters added to analysis tables. 4ce9559 (PR #326): audits.
- c0f0b62 (PR #431, closes #409 and others): alfalfa, almond exclusions.
- d4f6b33 (PR #472, 2026-09-02): jaguar provider excluded (migration 0022).
- 85373ad (PR #492, closes #476/#480, 2026-10-08): centralization and a baseline funnel snapshot (`scripts/filter_funnel_snapshot.py`, `pixi run filter-baseline-snapshot`).

## Open questions
- Whether `MIN_PRODUCTION_DATA_YEAR` is used in every place the old literal 2017 appeared (grep showed it used in two modules; verify no remaining magic `2017`).

## Merged detail: Data-quality filters (common.py) live in datamodels, not the pipeline

### Fact
- File: `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py`.
- Commit `85373ad` (Centralize data-quality filters, PRs #476/#480 merged as #492, 2026-10-08) changed this file, not a pipeline file.
- The pipeline package has no `utils/common.py`. A grep of `src/ca_biositing/pipeline/ca_biositing` found no import of `data_portal_views`. The only reference is a test, `tests/test_fermentation_record_etl.py`.
- The filters apply at the materialized-view layer (`ANALYSIS_DATA_VIEW` and others). Pipeline transforms load raw records and do not apply them (inferred from the import check; confirm by reading the view definitions).
- Baseline snapshot: `audit/output/filter_baseline/phase0_baseline.json`.

### Why it matters
Someone looking for "data-quality filters" in the ETL code will not find them there. Changing a filter does not change what the ETL loads.

### Open questions
- None for this slice. Covered by the datamodels slice.

# Related Concepts
- [Decision: centralize data-quality exclusions in common.py (not per-view literals)](../decisions/views-centralized-qc-filters.md): Why filters were moved here and the history behind each exclusion.
- [data_portal materialized views: modules, grain, and consumers](views-data-portal-matviews.md): Views whose WHERE clauses come from this module.
- [compile_mv_fixes.py: turning view expressions into an Alembic migration](views-compile-workflow.md): Filter edits take effect only through compile, migrate, and refresh.
- [Materialized view system: two schemas, one compile-and-refresh loop](views-overview.md): Parent overview.
- [System overview (start here)](system-overview.md): Places the filter layer in the overall data flow.
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Explains why the pipeline does not own these filters.
