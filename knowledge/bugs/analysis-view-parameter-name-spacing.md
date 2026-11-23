---
type: Bug
title: Analysis MVs filter parameters by underscore names in 0009 but space names in 0015 and 0017
description: "Open question: the resource end-use parameter filter changed from underscore names to space names between revisions 0009 and 0015, which may silently drop rows."
tags: [alembic, materialized-views, data-quality, bug, open-question]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:44Z" }
status: stable
code_refs: ["alembic/versions/0009_almond_etl_mv_edits.py", "alembic/versions/0015_implement_qc_filters_for_analysis_views.py", "alembic/versions/0017_standardize_geography_and_update_volume_estimates.py", "alembic/versions/0024_centralize_qc_constants_across_data_portal_views.py"]
sources: ["commit 9697eeb", "commit 5ab52b8", "commit 85373ad", "https://github.com/sustainability-software-lab/ca-biositing/pull/382"]
governance: context
stale_after: "2026-12-31"
---

## Symptom
In `mv_biomass_end_uses`-style SQL, `lower(parameter.name)` is compared against underscore names in `0009_almond_etl_mv_edits.py` (e.g. `"resource_use_perc_low"`, `"resource_value_multiplier_low"`). In `0015_implement_qc_filters_for_analysis_views.py` (around line 393) and `0017_standardize_geography_and_update_volume_estimates.py` (around line 413) the same comparisons use spaces (`"resource use perc low"`, `"resource value multiplier low"`).

## Impact
If the stored parameter names use one form only, the other form yields NULL averages and the end-use percentages and values disappear from the view. The revisions were written in different commits (`9697eeb` 2026-05-19 and `5ab52b8` 2026-06-01). Why the naming differs is not established.

## Root cause (unverified)
Not determined. Confirm which form the `parameter` table uses at HEAD (for example `SELECT DISTINCT name FROM parameter WHERE name ILIKE "%use%perc%"`).

## Status
Open question. `0024` may have inherited the 0017 form. Verify before editing any revision (see `requirements/never-edit-applied-migrations`).

## Open questions
- Which parameter-name form is stored in the database today? (inferred: the space form, since later revisions use it and the ETL was probably changed in #382; confirm with a query.)
- Did `0024` keep the spaces? (inferred: yes; grep `0024_centralize_qc_constants_across_data_portal_views.py` for `resource use perc`.)

# Related Concepts
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): The MV revisions that carry this filter.
- [Decision: migrations embed frozen compiled SQL instead of importing view expressions](../decisions/views-compiled-sql-snapshots.md): Frozen SQL means a wrong literal persists until a new revision fixes it.
