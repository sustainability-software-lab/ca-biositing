---
type: Bug
title: "Open bug: analysis_data_view geoid is NULL, so geoid-based analysis returns nothing"
description: "analysis_data_view.geoid is NULL for analysis rows, so AnalysisService.list_geoids (a DISTINCT non-NULL query) returns [] and geoid-scoped analysis endpoints find nothing."
tags: [bug, views, analysis, geoid, webservice, analysis-view, open]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:36Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/views.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/analysis_service.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/feedstocks/analysis.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/_canonical_views.py", "src/ca_biositing/webservice/tests/test_smoke.py", "alembic/versions/0023_centralize_qc_constants_and_fix_icp_ppm_cap_drift_in_analysis_data_view.py"]
sources: ["src/ca_biositing/webservice/ca_biositing/webservice/services/analysis_service.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/feedstocks/analysis.py", "commit 85373ad", "commit e41d00d", "commit 5ab52b8"]
governance: context
stale_after: "2026-12-31"
---

## Symptom
- `analysis_service.py` (around line 223) documents "known analysis_data_view bug where geoids are NULL" and returns `[]`.
- `v1/feedstocks/analysis.py:40` returns an empty list "until the known analysis_data_view geoid bug is resolved".

## Where the geoid comes from
`views.py:118` in `_analysis_base`: `LocationAddress.geography_id.label("geoid")`. In `ANALYSIS_DATA_VIEW` (line 282) it is passed through. `LocationAddress` is reached through the record table chain, so rows whose record type has no location path would be NULL (inferred; not verified row by row).

## Reproduction
Not done in this slice. Suggested check: `SELECT count(*) FILTER (WHERE geoid IS NULL), count(*) FROM ca_biositing.analysis_data_view;` against a loaded local DB (requires `pixi run start-services`).

## Root cause
Unknown. Candidates to test: missing location joins for some record types in `_analysis_base`; geography ids that do not match `place.geoid` (inferred).

## Related
- Filters that cut rows are in `common.py`; the geoid bug is independent of QC.
- Status of the workaround: stubbed in the webservice, not fixed in the view.

## Open questions
- Which record types produce NULL geoids.
- Whether `mv_biomass_composition` (which carries geoid from field samples) has the same issue (not checked).

## Merged detail: analysis_data_view geoid is NULL, so /analysis/geoids returns []

### Symptom
`AnalysisService.list_geoids` returns `[]`, so `GET /v1/feedstocks/analysis/geoids` is empty. The service code says so directly (`src/ca_biositing/webservice/ca_biositing/webservice/services/analysis_service.py:221-223`: "Returns [] currently (known analysis_data_view bug where geoids are NULL)").

### Where geoid comes from
- The view’s `geoid` column is selected from `location_address.geography_id` in the analysis-view SQL (see the migration `alembic/versions/0023_centralize_qc_constants_and_fix_icp_ppm_cap_drift_in_analysis_data_view.py`, the `AS geoid` projections).
- The webservice reads it through `get_analysis_data_view` (`_canonical_views.py:32-40`).

### Root cause
Not confirmed. Inferred: records whose resource or sample has no `location_address` join produce NULL geoid. Confirm with `SELECT count(*) FROM analysis_data_view WHERE geoid IS NULL` against the local DB.

### Impact
- `tests/`/`src/ca_biositing/webservice/tests/test_smoke.py:130` asserts geoids are non-empty, so the smoke test fails until the view is fixed.
- Any frontend geography picker built on this endpoint is empty (see `architecture/frontend`).

### Status
Open as of HEAD `e41d00d`; no tracking issue number is recorded in the repo.

## Merged detail: Analysis geoid discovery returns an empty list

### Symptom
`GET /v1/feedstocks/analysis/geoids` returns `{"values": []}` regardless of data. Analysis parameter routes that take a geoid as input are not affected by this list being empty (inferred from the code path; not tested live).

### Location
- `src/ca_biositing/webservice/ca_biositing/webservice/services/analysis_service.py` (`list_geoids`, filters `geoid IS NOT NULL`).
- `src/ca_biositing/webservice/ca_biositing/webservice/v1/feedstocks/analysis.py` (docstring: "Returns an empty list until the known analysis_data_view geoid bug is resolved").
- Root cause expected in datamodels view definition `ANALYSIS_DATA_VIEW` in `src/ca_biositing/datamodels/ca_biositing/datamodels/views.py:275` (inferred; not verified against the live DB).

### Root cause
The view’s geoid column is NULL for analysis rows. The service code is correct; it filters out NULLs.

### Workaround
Possibly use the availability, census or survey geoid lists for FIPS codes (those are separate views; not verified to contain the same geoids).

### Status
Open per the code comments at HEAD e41d00d. Re-check with a live query on `ca_biositing.analysis_data_view` before acting.

# Related Concepts
- [analysis_data_view and analysis_average_view: observation-level analysis layer](../architecture/views-analysis-data-view.md): The view whose geoid column is affected.
- [ca_biositing schema views in views.py: definitions, order, and consumers](../architecture/views-ca-biositing-schema.md): Parent list of ca_biositing views.
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Current-state hub; open bugs should be listed there.
- [frontend/ git submodule (cal-bioscape-frontend), pin, and API consumption](../architecture/frontend.md): Frontend geography selection depends on this endpoint
- [Full webservice endpoint table (36 routes)](../architecture/webservice-endpoints.md): The /v1/feedstocks/analysis discovery routes return empty
- [System overview (start here)](../architecture/system-overview.md): Analysis view is the shared data contract between ETL and API
- [Service layer behind feedstock queries and canonical view selection](../architecture/webservice-usda-query-services.md): Service that returns the empty list
