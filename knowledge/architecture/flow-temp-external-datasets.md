---
type: Architecture
title: "temp_external_datasets folder: staged external geospatial/CSV inputs"
description: "Historical: the temp_external_datasets/ folder was removed in f8c9353 (PR #514); extractors now read Google Drive files in memory and the folder path they still pass is unused."
tags: [pipeline, etl, external-data, geospatial, google-drive, data]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:31Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/food_processing_facilities.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/railways.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gdrive_to_pandas.py", ".gitignore"]
stale_after: "2026-12-31"
sources: ["commit 5f995e5", "commit a9a86eb", "commit f66e296", "https://github.com/sustainability-software-lab/ca-biositing/pull/84", "https://github.com/sustainability-software-lab/ca-biositing/pull/344", "resources/prefect/run_prefect_flow.py", "commit f8c9353", "https://github.com/sustainability-software-lab/ca-biositing/pull/514"]
---

## Purpose
Records what the `temp_external_datasets/` folder was and what replaced it. The folder held external geospatial and CSV inputs that were pulled from Google Drive. It no longer exists at HEAD.

## What changed
- Commit `f8c9353` (PR #514, 2026-10-22) deleted all 5 committed files: `Biodiesel_Plants.csv` (79 lines), `CA_proc_points.csv` (713 lines), `CA_proc_points.zip`, `US_Freight_Terminals.geojson` (9 lines), `US_Petroleum_Pipelines.geojson` (126,618 lines). The directory `src/ca_biositing/pipeline/ca_biositing/pipeline/temp_external_datasets/` is absent at HEAD.
- `etl/extract/ca_proc_points.py` is gone. Its Drive file `CA_proc_points.zip` is now read by `etl/extract/food_processing_facilities.py` (`FILE_NAME = "CA_proc_points.zip"`).
- `US_Freight_Terminals.geojson` has no reader at HEAD and no reference in code.
- Each extractor still sets `DATASET_FOLDER = ".../temp_external_datasets/"` (for example `etl/extract/railways.py:25`). `utils/gdrive_to_pandas.py:15-19` accepts `dataset_folder` but its body does not use it: it parses the file in memory, so the folder is never written.
- ZIP inputs are unpacked into a `tempfile.TemporaryDirectory()` and deleted after reading (`gdrive_to_pandas.py`).

## Current sources (replacement)
Every dataset reads its file by exact name from Google Drive. See the dataset table in architecture/pipeline-infrastructure-etl-family.

## Gotchas
- A reader that expects a file under `temp_external_datasets/` finds nothing. Only the Drive path works now.
- `.gitignore` still whitelists `temp_external_datasets/*.csv|*.zip|*.geojson` (`.gitignore:51-53`). Harmless, but the paths are dead.
- The Drive file must still be shared with the service account; a missing file gives a `FileNotFoundError` message and `gdrive_to_df` returns None.

## History
- a9a86eb (2026-02-05, PR #84 Berkeley Upstream integration): folder and first extractors.
- f66e296 (PR #344, Avi biodiesel_etl): biodiesel extractor and flow.
- 5f995e5 (2026-05-26): biodiesel flow disabled.
- f8c9353 (2026-10-22, PR #514): folder removed; in-memory Drive reads for all 18 infrastructure extractors.

## Open questions
- Whether `US_Freight_Terminals.geojson` should be removed from Drive too (not checked).

# Related Concepts
- [System overview (start here)](system-overview.md): External reference inputs staged outside the database
- [Land IQ ETL flow (shapefile to landiq_record and polygon)](flow-landiq-etl.md): Other geospatial external input for the same pipeline area
- [Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern](pipeline-infrastructure-etl-family.md): the family that replaced this folder
- [Google Sheets extraction: factory, gsheet_to_df, and retries](pipeline-gsheet-extraction.md): the other Google source reader
