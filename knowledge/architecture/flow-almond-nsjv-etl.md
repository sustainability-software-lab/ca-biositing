---
type: Architecture
title: Almond NSJV county ag report ETL flow
description: "Loads almond price and production county ag report data for the North San Joaquin Valley from one GSheet into DataSource, Dataset, Parameter, price/production records and Observation."
tags: [pipeline, etl, prefect, flow, almond, county-ag-report, gsheet]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:56Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/almond_nsjv_etl.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/almond_nsjv.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/almond_nsjv.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/almond_nsjv.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/factory.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lineage.py", "src/ca_biositing/pipeline/tests/test_flows.py", "tests/pipeline/test_almond_nsjv_load.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/320", "commit 9697eeb", "alembic/versions/0009_almond_etl_mv_edits.py", "alembic/versions/0021_remove_almond_meats_from_volume_estimate.py", "resources/prefect/run_prefect_flow.py"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
ETL for almond county agricultural report data (North San Joaquin Valley: Merced, San Joaquin, Stanislaus). Flow name ’Almond NSJV ETL’, entry point almond_nsjv_etl_flow (persist_result=False).

## Source
Google Sheet addressed by its key, not its title: 1vHCpd14aa-Vc_WzWXxUlU6FxcI5IOR30Bi6v3Wjqon8. Three worksheets: ’parameters’, ’price_freight_terms’, ’price_production_county_ag_reports’. Extracted with create_extractor (retries=3). gsheet_to_df falls back to opening the sheet by key.

## Key files
| path:line | role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/almond_nsjv_etl.py:4 | @flow and orchestration |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/almond_nsjv.py | three extractor tasks |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/almond_nsjv.py:216 | transform_county_ag_parameters |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/almond_nsjv.py:289 | transform_county_ag_records |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/almond_nsjv.py:439 | transform_county_ag_observations |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/almond_nsjv.py:560 | transform_almond_nsjv_payloads (wrapper, calls .fn of the three tasks) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/almond_nsjv.py:627 | load_county_ag_reports, returns a counts dict |
| src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lineage.py | create_etl_run_record, create_lineage_group |
| src/ca_biositing/pipeline/tests/test_flows.py | import-only smoke test |
| tests/pipeline/test_almond_nsjv_load.py | load tests (repo-root tests dir) |

## How it works
1. create_etl_run_record.fn and create_lineage_group.fn (task bodies called directly).
2. Extract the three worksheets into data_sources.
3. transform_almond_nsjv_payloads returns {parameter, records, observation}.
4. load_county_ag_reports upserts DataSource (ALMOND_DATA_SOURCE_NAME), method category and method (’manual extraction of values from PDF report’), datasets (’BEAM whitepaper county ag report almond prices’ and ’... production’), parameters (’price received’, ’price production weighted average’), ResourcePriceRecord, ResourceProductionRecord, and Observation. It returns a count per table.

## Interfaces
- Input: the GSheet above, CREDENTIALS_PATH.
- Output: DataSource, Method, Dataset, Parameter, ResourcePriceRecord, ResourceProductionRecord, Observation, plus EtlRun and LineageGroup.
- Transform reads Place rows (_load_place_lookup, almond transform around line 123) to map county names to GEOIDs.

## Gotchas
- Transform uses hard-coded county maps (_COUNTY_TO_GEOID, _ALLOWED_COUNTIES = merced, san joaquin, nsjv, stanislaus). Adding a county means editing code.
- The county-to-GEOID lookup depends on Place rows. Run the geography flow first (inferred; confirm by checking whether unresolved counties are dropped or fail).
- The flow uses .fn calls on tasks, so task retries and task-level logging do not apply to those calls.
- Load is one session; a failure in the middle rolls the whole load back (inferred from the try block; confirm).
- Overlaps the same DataSource and Observation tables as county_ag_report_etl, with different data sources.

## History
- 9697eeb (2026-05-19, PR #320) Almond ETL added. This is the only commit in the flow file’s history.
- Related alembic migrations: 0009_almond_etl_mv_edits.py and 0021_remove_almond_meats_from_volume_estimate.py in alembic/versions/.

## Open questions
- Whether the sheet key should move to a configured name (no code evidence either way).

# Related Concepts
- [County Ag Report ETL flow (three-sheet, ordered load)](flow-county-ag-report-etl.md): Writes into the same DataSource and Observation tables for county ag data; ordering between the two is not enforced in code.
- [Geography ETL flow (CA counties to Place)](flow-geography.md): Transform resolves county names to GEOIDs from the Place table that the geography flow populates.
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Uses the shared extract factory and lineage helpers described there.
- [System overview (start here)](system-overview.md): Source of almond price and production observations for the data portal.
