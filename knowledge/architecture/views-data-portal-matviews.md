---
type: Architecture
title: "data_portal materialized views: modules, grain, and consumers"
description: "Per-view catalogue of the data_portal MVs: module file, row grain, QC/resource filtering, and who reads each one. Includes the two legacy views."
tags: [views, data-portal, materialized-views, grain]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:23Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_*.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/__init__.py", "analysis/composition/moisture_vs_ash_viz.py", "scripts/view_diagnostics.py"]
sources: ["commit c0f0b62", "commit d4f6b33", "commit 99cbfcd", "commit 35423d1", "alembic/versions/0024_centralize_qc_constants_across_data_portal_views.py", "https://github.com/sustainability-software-lab/ca-biositing/pull/431", "https://github.com/sustainability-software-lab/ca-biositing/pull/472", "https://github.com/sustainability-software-lab/ca-biositing/pull/288"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Ten current MVs in schema `data_portal`, one module each in `data_portal_views/`, plus two legacy MVs kept for compatibility. Grain below is taken from `group_by` / `row_number` ordering in each module; "inferred" marks where the grain was read from code rather than stated.

## Key files
| Module | Expression (line) | Grain (row = ...) | Notes |
|---|---|---|---|
| `mv_biomass_search.py` | `mv_biomass_search` (248) | one resource (inferred from `FROM resource` with LEFT JOINs to aggregates) | Full-text `search_vector`, `has_*` flags, volume tags. Filters via `get_resource_filter`. Joins availability and composition logic. |
| `mv_biomass_composition.py` | line 160 | resource x geoid x analysis_type x parameter x unit (row_number order, line 161) | Aggregates 9 analysis record types. Ultimate/ICP/QC/sum-constraint filters. |
| `mv_biomass_volume_estimate.py` | `union_all` (435) | resource x county x dataset_year (indexes on resource_id, geoid, year) | Four volume paths A-D (production x residue factor, census x prune/trim yield, commodity-direct, acreage). Uses `get_min_year_filter` (2017). |
| `mv_biomass_availability.py` | line 16 | one resource (`group_by(Resource.id)`, line 27) | Seasonal availability plus average residue factors. Unique index on resource_id. |
| `mv_biomass_sample_stats.py` | line 57 | one resource (`group_by(Resource.id)`, line 71) | Counts of samples/records with `qc_pass` filter. |
| `mv_biomass_fermentation.py` | line 101 | resource x geography x strain x pretreatment x enzyme x BCM x elapsed time x parameter x unit | `having` clause on line 168. QC and provider filters. |
| `mv_biomass_gasification.py` | line 29 | resource x geography x reactor (DeconVessel) x parameter x unit | QC and provider filters. |
| `mv_biomass_pricing.py` | line 117 | one USDA market or resource price row (inferred from `combined` union; `row_number` on resource_id) | Combines `usda_market_record` and `resource_price_record`. Resource filter only. |
| `mv_biomass_end_uses.py` | line 104 | resource x use_case (unique index, line 9) | From `ResourceEndUseRecord`. |
| `mv_usda_county_production.py` | line 57 | resource x commodity x county x year (`group_by`, line 84) | Deliberately **no** resource/provider/QC filters; only `year >= 2017`. |
| `mv_biomass_county_production.py` | line 22 | county x scenario (Billion Ton) | LEGACY. Not re-exported from `__init__.py`; not in compile list. |
| `mv_billion_ton_county_production.py` | line 32 | county x scenario | DEPRECATED/LEGACY per its docstring. Not in compile list. |

## How it works
Each module exports one `select()` object. `data_portal_views/__init__.py` re-exports 11 of them. `scripts/compile_mv_fixes.py` compiles 10 of the current views (plus 3 ca_biositing views) into the migration. The two legacy modules are not compiled; their DB state depends on the original migration 0004.

## Interfaces
- Consumers in this repo: `analysis/composition/moisture_vs_ash_viz.py` (reads `data_portal.mv_biomass_search`), `analysis/geospatial/viz_county_biomass.py`, `analysis/metadata/database_metadata_dashboard.py`, and the `exports/*.sql|md` artifacts.
- The webservice does **not** query these data_portal MVs (no matches under `src/ca_biositing/webservice`). It uses the ca_biositing views (see views-ca-biositing-schema).
- Test/tooling imports: `src/ca_biositing/datamodels/tests/test_view_filters.py`, `scripts/filter_funnel_snapshot.py`, `src/ca_biositing/pipeline/tests/test_fermentation_record_etl.py`.

## Gotchas
- `scripts/view_diagnostics.py` (lines 19-22) queries `ca_biositing.mv_biomass_search`, but the module lives in `data_portal`. Treat that script as stale for this view (confirm before use).
- `mv_biomass_composition` docstring says "pass only"; `common.py` excludes only `fail`. Use the code (`get_qc_status_filter`) as the rule.
- The compiled SQL for `mv_biomass_search` in migration 0024 is self-contained (no `FROM data_portal.mv_biomass_composition` reference), so each MV carries its own inlined copy of shared logic. Creation order therefore does not break, but shared logic is duplicated and refreshed separately (inferred from the 0024 SQL scan).
- Every data_portal MV must have a unique index for `REFRESH ... CONCURRENTLY` (see views-refresh).

## History
- 930d868 (#220), d961724 (#258): modules created. 99cbfcd (#288), 35423d1 (#265): residue factors and qualitative data. c0f0b62 (PR #431, closes #396/#389/#413/#419/#409): gasification label, high/low volume tags, corn-stover volume path, exclusions. d4f6b33 (#472): jaguar provider excluded.

## Open questions
- Is `mv_biomass_search` grain exactly one row per `resource.id`? The `id` column is not labeled explicitly in its module; confirm against migration 0024 SQL.
- Which downstream clients beyond this repo read the data_portal MVs (frontend submodule not present here).

# Related Concepts
- [Materialized view system: two schemas, one compile-and-refresh loop](views-overview.md): Parent overview of the two view families and the compile loop.
- [common.py: the single gatekeeper for view data-quality filters](views-data-quality-filters.md): Shared filter helpers every data_portal module draws from.
- [analysis_data_view and analysis_average_view: observation-level analysis layer](views-analysis-data-view.md): ca_biositing analysis view that composition and fermentation logic parallels.
- [Status of view SQL reference files and docs: what is stale or orphaned](../facts/views-sql-artifacts-status.md): Stale docs that list different view sets and counts.
- [System overview (start here)](system-overview.md): Where the portal and analysis consumers sit in the system.
