---
type: Requirement
title: Google Sheets extracts need a service-account credentials.json
description: "gspread reads a service-account JSON at CREDENTIALS_PATH (default ./credentials.json); missing or wrong file surfaces as a retried RuntimeError, not a clear auth error."
tags: [pipeline, requirement, gsheet, credentials, gcp]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:53Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/factory.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gsheet_to_pandas.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gcs_utils.py", "resources/docker/docker-compose.yml"]
sources: ["docs/pipeline/GCP_SETUP.md", "commit cf8b07f", "https://github.com/sustainability-software-lab/ca-biositing/pull/385", ".gitignore"]
governance: constraint
---

## Requirement
Any extract that calls `gsheet_to_df` (including every `create_extractor` task) needs a Google service-account JSON file.
- Path: env `CREDENTIALS_PATH`, default `credentials.json`, resolved against the process cwd (`src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/factory.py:25-27`).
- Docker: bind-mounted to `/app/credentials.json` in the worker (`resources/docker/docker-compose.yml:81`).
- Cloud Run: fix in `cf8b07f` (PR #385).
- The file is gitignored (`.gitignore:61`).

## Failure mode
`gsheet_to_df` catches `Exception` and returns `None` (`src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gsheet_to_pandas.py:106-111`). The factory raises `RuntimeError` (`factory.py:36-39`). Prefect retries 3 times. The log shows the RuntimeError, while the underlying "No such file" error is only printed.

## Setup reference
`docs/pipeline/GCP_SETUP.md` (create the service account, generate `credentials.json`, share the sheet with the service-account email).

## Open questions
- Whether `gcs_utils.upload_to_gcs` (default `credentials.json`) has the same dependency (inferred yes; the default is the same string).

# Related Concepts
- [Google Sheets extraction: factory, gsheet_to_df, and retries](../architecture/pipeline-gsheet-extraction.md): The code that reads this file.
- [System overview (start here)](../architecture/system-overview.md): Credentials are part of deployment setup.
