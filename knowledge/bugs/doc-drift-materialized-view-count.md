---
type: Bug
title: "Docs disagree on materialized view count: 7, 9, 10 and ’nine’ vs 12 data_portal modules plus 7 ca_biositing views"
description: "Verified counts: 7 ca_biositing views in views.py, 12 data_portal mv_* modules, 11 data_portal views created by migrations; docs say 7, 9, 10 or nine."
tags: [docs, drift, materialized-views]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:55Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/views.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views", "alembic/versions", ".agents/rules/schema-and-migrations.md", "audit/README.md", "docs/datamodels/ALEMBIC_VIEW_WORKFLOW.md", "README.md"]
sources: [".agents/rules/schema-and-migrations.md:32", "audit/README.md:55", "docs/datamodels/ALEMBIC_VIEW_WORKFLOW.md:45", "README.md:96", "src/ca_biositing/datamodels/README.md:8"]
governance: context
stale_after: "2026-11-16"
---

## Purpose
Give the true view counts and list every doc that disagrees.

## Evidence
- `views.py:1-12` docstring and `VIEW_DEFINITIONS` (`views.py:523-532`) define 6 ca_biositing views plus `usda_resource_commodity_view` refreshed separately (`views.py:568`) = 7.
- `data_portal_views/mv_*.py`: 12 modules (`mv_biomass_availability`, `_composition`, `billion_ton_county_production`, `_county_production`, `_end_uses`, `_fermentation`, `_gasification`, `_pricing`, `_sample_stats`, `_search`, `_volume_estimate`, `usda_county_production`).
- Migrations: 11 distinct `CREATE MATERIALIZED VIEW data_portal.*` statements (no `billion_ton_county_production`) and 8 `ca_biositing.*`, 19 total (grep over `alembic/versions`).
- Docs:
  - `.agents/rules/schema-and-migrations.md:32` says "Nine materialized views are defined in data_portal_views/".
  - `audit/README.md:55` says "9 materialized views" in data_portal.
  - `docs/datamodels/ALEMBIC_VIEW_WORKFLOW.md:45` says "10 data portal materialized views" and its table omits `mv_biomass_volume_estimate` and `mv_billion_ton_county_production`.
  - `README.md:96` says "Seven materialized views" (ca_biositing schema only).
  - `src/ca_biositing/datamodels/README.md:8` says "7 materialized analytical views".
  - `src/ca_biositing/datamodels/AGENTS.md:42` says views.py has "7 views" (correct for views.py).
  - `plans/phase3_materialized_views_assessment.md` says "9 views".

## Fix
State both counts explicitly: 7 in `views.py` and 12 in `data_portal_views/` (11 migrated). Or generate the list from `pg_matviews`.

# Related Concepts
- [Decision: migrations embed frozen compiled SQL instead of importing view expressions](../decisions/views-compiled-sql-snapshots.md): The view workflow these counts describe
- [mv_billion_ton_county_production has no migration and is missing from the package export; mv_biomass_county_production is not exported](mv-billion-ton-county-production-unmigrated.md): One of the 12 modules has no migration
- [System overview (start here)](../architecture/system-overview.md): Views feed the data portal
