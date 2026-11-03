---
type: Architecture
title: "ca_biositing schema views in views.py: definitions, order, and consumers"
description: "The ca_biositing-schema views (analysis, USDA, LandIQ, Billion Ton) defined in views.py, their VIEW_DEFINITIONS refresh order, and the webservice code that reads them."
tags: [views, ca_biositing-schema, webservice, usda, landiq]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:24Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/views.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/_canonical_views.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/analysis_service.py"]
sources: ["commit 6aa44b6", "commit 83d42dc", "commit 5ab52b8", "https://github.com/sustainability-software-lab/ca-biositing/pull/159", "https://github.com/sustainability-software-lab/ca-biositing/pull/382", "src/ca_biositing/datamodels/ca_biositing/datamodels/views.py"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
`views.py` holds the materialized views in schema `ca_biositing`. The webservice reads them directly (PostgreSQL) and falls back to the SQLAlchemy expressions on SQLite in tests.

## Key files
| Path:line | Symbol | Role |
|---|---|---|
| `views.py:76` | `LANDIQ_RECORD_VIEW` | LandIQ records joined to polygon and primary crop |
| `views.py:92` | `LANDIQ_TILESET_VIEW` | LandIQ tile aggregation |
| `views.py:107` | `_analysis_base` / `ANALYSIS_DATA_VIEW` (275) | Observation-level analysis view (see views-analysis-data-view) |
| `views.py:339` | `USDA_CENSUS_VIEW` (377), `USDA_CENSUS_VIEW_V1` | USDA census joined to commodity and place. V1 is kept for the initial migration. |
| `views.py:405` | `USDA_SURVEY_VIEW` (433), `_V1` | USDA survey, same pattern |
| `views.py:465` | `USDA_RESOURCE_COMMODITY_VIEW` | Resource-to-USDA-commodity map. Not in `VIEW_DEFINITIONS`. |
| `views.py:481` | `BILLION_TON_TILESET_VIEW` | Billion Ton 2023 tileset |
| `views.py:497` | `ANALYSIS_AVERAGE_VIEW` (500) | Aggregated analysis statistics; depends on analysis_data_view |
| `views.py:523` | `VIEW_DEFINITIONS` | Ordered list; `analysis_average_view` is last by design |
| `views.py:535` | `SPATIAL_VIEW_INDEXES` | GIST indexes for the two LandIQ geometry views |
| `views.py:541` | `refresh_all_views` | Refresh logic (see views-refresh) |

## How it works
`VIEW_DEFINITIONS` order is the refresh order: landiq_record, landiq_tileset, analysis_data, usda_census (V1), usda_survey (V1), billion_ton_tileset, analysis_average. `refresh_all_views` then refreshes `usda_resource_commodity_view` explicitly.

Only three of these are recompiled by `compile_mv_fixes.py` (`analysis_data_view`, `analysis_average_view`, `usda_census_view`). The others were last written by older migrations (for example 0004, 0017-0019). Confirm the latest DDL per view with `grep -l <view> alembic/versions/*.py`.

## Interfaces
- Readers: `src/ca_biositing/webservice/.../services/_canonical_views.py` (`get_analysis_data_view`, `get_usda_census_view`, `get_usda_survey_view`, `get_usda_resource_commodity_view`), `analysis_service.py` (line 74 onward), `usda_census_service.py`, `usda_survey_service.py`.
- Writers: none at runtime. Views are rebuilt only by migrations.

## Gotchas
- `views.py` module docstring says "7 views" and says the analysis average view is "raw SQL". Both are stale: the code is `select()` and there are 8 definitions plus one extra.
- `_canonical_views.py` queries the views with `table(name, ..., schema="ca_biositing")`, so renaming a view or column breaks the webservice without a Python import error.
- Adding a new ca_biositing view requires an edit to `VIEW_DEFINITIONS` (otherwise refresh skips it). Data_portal views are discovered automatically.

## History
- 83d42dc (PR #155) and 6aa44b6 (PR #159): webservice switched to querying canonical views instead of rebuilding joins.
- 5ab52b8 (PR #382): QC and resource filters added to the ca_biositing analysis tables.

## Open questions
- Whether `landiq_*` and `billion_ton_tileset_view` are still needed by the webservice (no reader found in this slice).

# Related Concepts
- [Materialized view system: two schemas, one compile-and-refresh loop](views-overview.md): Parent overview; explains the schema split and compile loop.
- [analysis_data_view and analysis_average_view: observation-level analysis layer](views-analysis-data-view.md): Detail on the most-read view in this family.
- [refresh_all_views: refresh order, concurrency, and callers](views-refresh.md): Refresh order that VIEW_DEFINITIONS controls.
- [Decision: views split across ca_biositing and data_portal schemas](../decisions/views-two-schemas.md): Why these views live in ca_biositing rather than data_portal.
