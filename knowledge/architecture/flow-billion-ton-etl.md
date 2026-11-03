---
type: Architecture
title: Billion Ton 2023 ETL flow (Google Drive CSV)
description: Downloads the Billion Ton 2023 agricultural CSV from a fixed Drive file ID and loads BillionTon2023Record plus Place rows; commented out of the master runner.
tags: [pipeline, etl, prefect, flow, billion-ton, google-drive, legacy]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:59Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/billion_ton_etl.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/billion_ton.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/billion_ton.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/billion_ton.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gdrive_to_pandas.py", "src/ca_biositing/pipeline/tests/test_billion_ton_etl.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/121", "https://github.com/sustainability-software-lab/ca-biositing/pull/385", "commit 447162c", "commit cf8b07f", "plans/phase3_materialized_views_assessment.md", "resources/prefect/run_prefect_flow.py"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
ETL for the Billion Ton 2023 agricultural dataset, a Google Drive CSV. Entry point billion_ton_etl_flow, with default file_id 11xLy_kPTHvoqciUMy3SYA3DLCDIjkOGa and file_name billionton_23_agri_download.csv.

## Source
Google Drive file, MIME text/csv, located by file_id (preferred over name lookup in gdrive_to_df). Read through utils/gdrive_to_pandas.py using CREDENTIALS_PATH. The file is downloaded into a temp directory on each run.

## Key files
| path:line | role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/billion_ton_etl.py:14 | @flow billion_ton_etl_flow; defines local create_etl_run_record_task and create_lineage_group_task wrappers |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/billion_ton.py | Drive download; swallows exceptions and returns None |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/billion_ton.py | transform, expects data_sources[’billion_ton’] |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/billion_ton.py | load, writes BillionTon2023Record and ensures Place rows (on_conflict_do_nothing on geoid) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gdrive_to_pandas.py | Drive download and CSV, ZIP, GeoJSON parsing |
| src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lineage.py | EtlRun and LineageGroup creation |

## How it works
1. Set stdout and stderr to line buffering.
2. Extract. If the result is None or empty, log an error and return. No EtlRun is created in that case.
3. Create the EtlRun and lineage group (note ’Billion Ton 2023 Agricultural Data’).
4. Transform with data_sources={’billion_ton’: raw_df}. If the result is empty, return.
5. Load.

## Interfaces
- Input: Drive file above, CREDENTIALS_PATH.
- Output: billion_ton2023_record table, Place rows, EtlRun, LineageGroup.
- Callers: not in the master runner (commented out). It runs directly.

## Gotchas
- The extract catches all exceptions and returns None, so auth and download failures appear only as the ’Aborting’ log line.
- Because the extract runs before the EtlRun is created, a failed extract leaves no run record.
- The Drive file ID is hard-coded as a default argument.
- The flow is disabled in the master runner (see History), so nothing runs it automatically.

## History
- 447162c (2026-02-19, PR #121) Billion Ton 2023 ETL implemented.
- cf8b07f (2026-06-01, PR #385) credentials fix. This commit also commented out billion_ton in resources/prefect/run_prefect_flow.py.
- plans/phase3_materialized_views_assessment.md describes billion_ton_2023 as the legacy volume source that is kept for backward compatibility.

## Open questions
- Whether the flow should be re-enabled. The planning doc suggests it is kept for compatibility, not active use (inferred; confirm with the team).

# Related Concepts
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Flow uses the shared Drive loader and lineage helpers and runs outside the master registry.
- [Geography ETL flow (CA counties to Place)](flow-geography.md): Load writes Place rows itself, so the geography flow is not required for this flow to succeed (inferred).
- [System overview (start here)](system-overview.md): Legacy external dataset feeding the billion-ton volume estimates.
