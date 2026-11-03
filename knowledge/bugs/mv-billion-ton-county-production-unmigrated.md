---
type: Bug
title: mv_billion_ton_county_production has no migration and is missing from the package export; mv_biomass_county_production is not exported
description: "A view module exists but no Alembic revision creates it, and data_portal_views/__init__ omits mv_biomass_county_production. Docs still describe the billion-ton view as live."
tags: [bug, materialized-views, alembic, data-portal]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:57Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_billion_ton_county_production.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/__init__.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_county_production.py", "alembic/versions"]
sources: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/__init__.py", "src/ca_biositing/datamodels/README.md:57"]
governance: context
stale_after: "2026-11-16"
---

## Purpose
Record a verified gap between view code, the migration chain and the package exports.

## Evidence
- `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_billion_ton_county_production.py:32` defines the view.
- `grep -rn billion_ton_county_production alembic/` returns nothing: no migration creates it.
- `data_portal_views/__init__.py` imports and exports `mv_billion_ton_county_production` (lines 16 and 29) but has 0 references to `mv_biomass_county_production`, which migrations do create (`alembic/versions/0004_views_and_indexes.py` and later revisions).
- `src/ca_biositing/datamodels/README.md:57-58` says `mv_billion_ton_county_production` deliberately applies no filters, implying it is live.

## Impact
Fresh databases built from `alembic upgrade head` will not have the billion-ton view, so any `refresh-views` run or code that reads it will fail or miss data. Code that imports `mv_biomass_county_production` from the package will fail.

## Next step
Confirm against a live DB with `pixi run schema-analytics-list`, then either add a migration (via `compile-mv-fixes`) or remove the module. Behavior unverified in the database.

# Related Concepts
- [Decision: migrations embed frozen compiled SQL instead of importing view expressions](../decisions/views-compiled-sql-snapshots.md): The compile-and-migrate path that should have created this view
- [Docs disagree on materialized view count: 7, 9, 10 and ’nine’ vs 12 data_portal modules plus 7 ca_biositing views](doc-drift-materialized-view-count.md): Count drift that hides this gap
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): Revision chain is where the view is missing
