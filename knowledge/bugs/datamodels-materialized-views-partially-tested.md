---
type: Bug
title: 5 of 12 materialized views have only SQL-text tests; 7 have none
description: "Only 5 views are checked by compiled-SQL string assertions; no test runs any MV against a database, and 7 MV modules have no test at all."
tags: [testing, views, materialized-views, coverage]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:49Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/*.py", "src/ca_biositing/datamodels/tests/test_view_filters.py", "plans/phase3_materialized_views_assessment.md"]
sources: ["commit 5ab52b8", "https://github.com/sustainability-software-lab/ca-biositing/pull/382", "commit e6ee628", "https://github.com/sustainability-software-lab/ca-biositing/pull/268", "plans/phase3_materialized_views_assessment.md"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Risk note: materialized view definitions are the data-portal contract, yet most are untested and none is executed in a test.

## Evidence
- Views in src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/: 12 mv_* modules plus common.py and __init__.py.
- Tested (string checks on compiled SQL in src/ca_biositing/datamodels/tests/test_view_filters.py): mv_biomass_composition (:77-95), mv_biomass_fermentation (:96-103), mv_biomass_gasification (:104-111), mv_biomass_sample_stats (:112-117), mv_usda_county_production (:118-128), and ANALYSIS_DATA_VIEW (:44-76).
- No test reference at all: mv_billion_ton_county_production, mv_biomass_availability, mv_biomass_county_production, mv_biomass_end_uses, mv_biomass_pricing, mv_biomass_search, mv_biomass_volume_estimate.
- Module-name grep over tests/ returned no hit for these seven (text match, HEAD e41d00d).
- Test checks are structural (e.g. "contains WHERE ...") and do not verify join correctness, row counts or NULL handling.

## Impact
A change to a view’s join or filter can pass CI, because CI runs src/ca_biositing/datamodels only (facts/testing-ci-scope). The 5 tested views are guarded only for filter presence.

## History
- 5ab52b8 (2026-06-01, PR #382): centralized data-quality filters; touched the v1 conftest. test_view_filters.py docstring points to plans/jiggly-crafting-planet.md for its phased plan (file not checked).
- e6ee628 (2026-04-30, PR #268): mv_biomass_fermentation fixes; no test added for the fix (inferred from diff scope; confirm).
- The plans/ file plans/phase3_materialized_views_assessment.md lists "Unit test coverage: all-fail, mixed, no-data" as unchecked (line 308).

## Open questions
- Whether a live-Postgres view test is planned; plans/phase3 suggests test data but no implementation found.

# Related Concepts
- [Test suite layout, how to run each suite, and fixture map](../architecture/testing.md): test-layout parent
- [DB tests use SQLite in-memory with selected tables, not Postgres or testcontainers](../decisions/testing-sqlite-in-memory-fixtures.md): SQLite strategy is why views are never executed
- [System overview (start here)](../architecture/system-overview.md): MVs back the data portal
