---
type: Architecture
title: "refresh_all_views: refresh order, concurrency, and callers"
description: "How refresh_all_views refreshes ca_biositing views (non-concurrent, ordered) then discovers and refreshes data_portal views CONCURRENTLY in one transaction."
tags: [views, refresh, materialized-views, prefect, pixi]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:28Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/views.py", "pixi.toml", "resources/prefect/run_prefect_flow.py"]
sources: ["commit 930d868", "commit 85373ad", "commit 2576d03", "https://github.com/sustainability-software-lab/ca-biositing/pull/220", "https://github.com/sustainability-software-lab/ca-biositing/pull/492"]
governance: context
---

## Purpose
Populated materialized views go stale after each data load. `refresh_all_views` refreshes all of them in a fixed order, from one connection, committing once at the end.

## Key files
| Path:line | Symbol | Role |
|---|---|---|
| `views.py:541-592` | `refresh_all_views(engine, log_summary=False)` | Core logic |
| `views.py:523` | `VIEW_DEFINITIONS` | ca_biositing refresh order |
| `pixi.toml:244` | `refresh-views` | `python -c ... refresh_all_views(get_engine())` |
| `resources/prefect/run_prefect_flow.py:31-40` | refresh task | Calls `refresh_all_views(engine)` after loads ("including data_portal schema") |

## How it works
1. For each entry in `VIEW_DEFINITIONS`: `REFRESH MATERIALIZED VIEW ca_biositing.<name>` (non-concurrent, takes a lock that blocks reads).
2. Refresh `ca_biositing.usda_resource_commodity_view` explicitly (not in `VIEW_DEFINITIONS`).
3. Query `pg_matviews` for schema `data_portal` and refresh each with `REFRESH MATERIALIZED VIEW CONCURRENTLY`.
4. `conn.commit()` once at the end, so a failure partway leaves the previous data in place (all work is in one transaction).

With `log_summary=True`, row counts before and after each refresh are printed via `log_filter_summary`.

## Interfaces
- Input: a SQLAlchemy engine (`ca_biositing.datamodels.database.get_engine`).
- Output: none. Side effect is refreshed data.
- Callers: `pixi run refresh-views`; Prefect refresh task; ad-hoc use (docstring example).

## Gotchas
- `CONCURRENTLY` needs a unique index on every data_portal MV. A new MV without one fails at step 3. Migrations create them (see compile workflow).
- New data_portal MVs are picked up automatically (dynamic discovery). New ca_biositing MVs are not: they must be added to `VIEW_DEFINITIONS` in dependency order (analysis_average_view after analysis_data_view).
- `refresh_all_views` is not a DB-level cascade. Refreshing `analysis_data_view` does not refresh `analysis_average_view` unless the list order does it.
- The Prefect task and `pixi run refresh-views` do the same thing; the pixi task passes no `log_summary`.

## History
- 930d868 (PR #220): "fixing refresh-views for data portal too" added the data_portal pass.
- 2576d03 (PR #362) and 85373ad (PR #492): log_summary and filter visibility added.

## Open questions
- Whether `REFRESH ... CONCURRENTLY` on `usda_resource_commodity_view` is needed (it is non-concurrent here; not verified).

# Related Concepts
- [ca_biositing schema views in views.py: definitions, order, and consumers](views-ca-biositing-schema.md): VIEW_DEFINITIONS order is defined there.
- [data_portal materialized views: modules, grain, and consumers](views-data-portal-matviews.md): Dynamically discovered schema refreshed here.
- [Materialized view system: two schemas, one compile-and-refresh loop](views-overview.md): Final step of the overall loop.
- [System overview (start here)](system-overview.md): Prefect and data loads that trigger refresh.
