---
type: Architecture
title: Gasification Timeseries Archiver subflow
description: Subflow called by thermochem_etl that copies each gasification GSheet worksheet to a GCS CSV and upserts GasificationTimeseries metadata; it never fails on a single record.
tags: [pipeline, etl, prefect, subflow, gasification, gcs, gsheet]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:02Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/gasification_archive_pipeline.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/thermochem_etl.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/gasification_archive.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gcs_utils.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/aim2_records/gasification_timeseries.py", "src/ca_biositing/pipeline/tests/test_gasification_archive_transform.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/493", "https://github.com/sustainability-software-lab/ca-biositing/pull/395", "https://github.com/sustainability-software-lab/ca-biositing/pull/385", "https://github.com/sustainability-software-lab/ca-biositing/pull/377", "commit c5a592e", "commit 45b98d1", "commit cf8b07f", "commit b328b5f"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Archives the raw GSheet worksheet behind each gasification experiment to a GCS bucket as CSV, then records the path, size and MD5 in GasificationTimeseries. Entry point gasification_archive_subflow. It is not in the master runner. The thermochem_etl flow calls it.

## Source
- Input is a list of records (dicts) with record_id, gsheet_url, resource_id, experiment_id, resource_name, reactor_name, reactor_type_id. These come from the thermochem gasification sheet via the transform.
- Each unique gsheet_url is opened with gspread (service account at CREDENTIALS_PATH, default credentials.json). The worksheet is found by gid from the URL. Header row is row 4, data starts at row 5, and the sheet must have at least 4 rows.

## Key files
| path:line | role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/gasification_archive_pipeline.py:152 | gasification_archive_subflow |
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/gasification_archive_pipeline.py:15 | process_gsheet_to_csv task |
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/gasification_archive_pipeline.py:51 | archive_to_gcs task (upload_to_gcs, MD5 of CSV bytes) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/gasification_archive_pipeline.py:81 | record_metadata_db task (upsert GasificationTimeseries) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/gasification_archive_pipeline.py:136 | check_record_exists task |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/gasification_archive.py:8 | build_gasification_archive_records (moved here by c5a592e) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/thermochem_etl.py | caller, invocation near lines 99-116 |
| src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gcs_utils.py | upload_to_gcs |
| src/ca_biositing/datamodels/ca_biositing/datamodels/models/aim2_records/gasification_timeseries.py | GasificationTimeseries model |
| src/ca_biositing/pipeline/tests/test_gasification_archive_transform.py | tests for the transform (added by c5a592e) |

## How it works
1. For each record: if force_refresh is off and a row exists for (resource_id, experiment_id), skip.
2. Skip records with no gsheet_url.
3. Build the filename: {resource_name cleaned to lowercase underscores}_EXP_{experiment_id}.csv, or {record_id}.csv if either is missing.
4. process_gsheet_to_csv, then archive_to_gcs into bucket biocirv-staging-gasification-data (default), then record_metadata_db.
5. Any exception in the per-record block is logged with logger.error and the loop continues.

## Interfaces
- Input: list of dicts above, etl_run_id (int), lineage_group_id (int), bucket_name, force_refresh.
- Output: GCS objects, GasificationTimeseries rows (bucket_path, file_size, file_format csv, checksum_md5, resource and experiment IDs, etl_run_id, lineage_group_id).
- Caller: thermochem_etl.py passes force_refresh from its own parameter. The subflow runs only when the transform returns at least one gasification record and at least one unique URL.

## Gotchas
- Errors never fail the subflow. Check the logs for ’Failed to archive record’, not the flow state.
- record_metadata_db filters with == None when resource_id or experiment_id is None. SQLAlchemy turns that into IS NULL, which can overwrite an unrelated NULL-keyed row (inferred from SQLAlchemy semantics; not tested). check_record_exists returns False for None keys, so those records are re-archived on every run.
- The worksheet layout is hard-coded (header on row 4). A layout change breaks every archive silently into the per-record error log.
- archive_to_gcs computes size and MD5 from its own CSV serialization, while the upload takes the DataFrame directly. The stored checksum may not match the uploaded bytes (inferred; confirm in utils/gcs_utils.upload_to_gcs).
- The __main__ block points at a real test sheet and writes an EtlRun to whichever database is configured.

## History
- b328b5f (2026-06-01, PR #377) gasification ETL added.
- cf8b07f (2026-06-01, PR #385) credentials fix for Cloud Run (CREDENTIALS_PATH).
- 45b98d1 (2026-06-09, PR #395) reactor_name added to gasification_timeseries.
- c5a592e (2026-10-08, PR #493) archival prep moved from thermochem_etl.py into etl/transform/analysis/gasification_archive.py. The commit also added the transform tests and an audit filter-funnel snapshot.

## Open questions
- Whether the GCS bucket default should be configurable (it is hard-coded as a default argument).

# Related Concepts
- [Thermochemical Conversion ETL flow (Aim 2 sheet to experiment, observation, gasification)](flow-thermochem-etl.md): Caller. Thermochem builds the record list and triggers this subflow; the thermochem flow ID is inferred from its file name and belongs to another slice.
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Subflow pattern and per-record task layout described there.
- [System overview (start here)](system-overview.md): Archive copies of raw gasification experiment sheets stored in GCS.
