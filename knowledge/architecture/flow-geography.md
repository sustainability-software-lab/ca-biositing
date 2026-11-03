---
type: Architecture
title: Geography ETL flow (CA counties to Place)
description: Reads the static data/static/ca_counties.csv and upserts Place rows keyed by geoid; first in the master runner because later flows depend on Place.
tags: [pipeline, etl, prefect, flow, geography, place, static-data]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:03Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/geography.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/geography.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/places.py", "data/static/ca_counties.csv", "resources/prefect/run_prefect_flow.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/399", "commit b646a9e", "alembic/versions/0017_standardize_geography_and_update_volume_estimates.py", "resources/prefect/run_prefect_flow.py"]
governance: constraint
stale_after: "2026-12-31"
---

## Purpose
Loads California county reference data into the Place table, keyed by geoid. This is the reference table other flows use to resolve counties. Flow name ’geography_etl_flow’, entry point geography_etl_flow. There is no transform step.

## Source
Static CSV data/static/ca_counties.csv, tracked in git. It is read as a relative path (Path(’data/static/ca_counties.csv’)) with geoid, state_fips and county_fips forced to str.

## Key files
| path:line | role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/geography.py:9 | @flow geography_etl_flow |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/geography.py:10 | extract_ca_counties task |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/places.py:7 | load_places task (upsert on geoid, column filter from Place.__table__) |
| data/static/ca_counties.csv | source data |
| resources/prefect/run_prefect_flow.py | master runner, geography listed first |

## How it works
1. extract_ca_counties reads the CSV. Missing file raises FileNotFoundError.
2. load_places filters columns to the Place table, converts NaN to None, and upserts in batches with progress logs.

## Interfaces
- Input: data/static/ca_counties.csv (no credentials).
- Output: Place rows.
- Callers: master flow runs it first. Other flows read Place (almond transform lookup, field_sample, biodiesel, billion_ton load, county_ag load).

## Gotchas
- The CSV path is relative to the current working directory. Running from a different directory fails with FileNotFoundError.
- Master-runner order is a hard dependency. The dict comment says foundational flows must run first. Keep geography first.
- No etl_run or lineage record is created for this flow (verified: the flow does not call lineage helpers).
- Flow name uses snake_case (’geography_etl_flow’) unlike the other flows’ display names. Use the file-based run command, not a display name.

## History
- The flow file’s git history shows only b646a9e (2026-06-10, PR #399), which changed the materialized views for commodity-direct volume estimates, not the flow itself. Earlier history of the Place data is in the alembic migration 0017_standardize_geography_and_update_volume_estimates.py (inferred from the file name; not read).

## Open questions
- Whether the 0017 migration’s geography standardisation and this CSV agree on column set (not checked).

# Related Concepts
- [Almond NSJV county ag report ETL flow](flow-almond-nsjv-etl.md): Almond transform resolves county names to geoid from Place, so geography must run first.
- [Field Sample ETL flow (four-worksheet join)](flow-field-sample-etl.md): Field sample and location loads reference Place rows for counties.
- [County Ag Report ETL flow (three-sheet, ordered load)](flow-county-ag-report-etl.md): County records create missing Place rows, but geography provides the canonical set.
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Master-runner registry ordering is defined there and in resources/prefect.
- [System overview (start here)](system-overview.md): Foundational reference table for all geographic joins.
