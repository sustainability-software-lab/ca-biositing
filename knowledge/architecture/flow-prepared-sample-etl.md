---
type: Architecture
title: Prepared Sample ETL flow (Google Sheet 02-Preparation to prepared_sample)
description: Loads the 02-Preparation worksheet of the Aim 1 feedstock sheet into prepared_sample; run as a sub-flow of samples_etl after field samples load.
tags: [pipeline, etl, flow, google-sheets, samples]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:05Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/prepared_sample_etl.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/preparation.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/factory.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/prepared_sample.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/prepared_sample.py"]
sources: ["commit dc98b30", "https://github.com/sustainability-software-lab/ca-biositing/pull/108", "resources/prefect/run_prefect_flow.py"]
governance: context
stale_after: "2026-12-31"
---

**Purpose**
Extracts preparation records (feedstock preparation methods) from the Aim 1 Google Sheet and upserts them into `prepared_sample`. It links to field samples, so it must run after the field sample flow.

**Key files**

| Path:line | Role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/prepared_sample_etl.py:7-8 | `@flow(name="Prepared Sample ETL")` `prepared_sample_etl_flow()` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/preparation.py:7-8 | GSheet `Aim 1-Feedstock Collection and Processing Data-BioCirV`, worksheet `02-Preparation` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/factory.py:10 | `create_extractor` builds the Prefect extract task (3 retries, 10s delay) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/prepared_sample.py:18 | `transform(data_sources, etl_run_id, lineage_group_id)`; EXTRACT_SOURCES=["preparation"] (line 12) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/prepared_sample.py:9 | `load_prepared_sample` upserts PreparedSample |

**How it works**
1. Lineage record and group.
2. `extract()` (factory task) returns raw DataFrame; None aborts the flow.
3. `transform` cleans with `utils/cleaning_functions` and resolves FKs against FieldSample, PreparationMethod and Contact (lazy-imported inside the task, transform/prepared_sample.py:28-33).
4. Load only if the result is non-empty.

**Interfaces**
- Input: GSheet tab `02-Preparation`, credentials from `CREDENTIALS_PATH` (default `credentials.json`).
- Output: `prepared_sample` rows.
- Callers: `samples_etl` (flows/samples_etl.py:18). The flow is commented out of the master registry (run_prefect_flow.py:26), so it runs through samples_etl.

**Gotchas**
- The transform fails soft: missing `preparation` key returns None and empty data returns an empty DataFrame; the flow logs and exits without raising.
- Depends on FieldSample rows existing; running it alone on an empty DB yields unresolved FKs (inferred from the transform imports; confirm with a test run).

**History**
- dc98b30 (2026-02-11, PR #108 SQL-first workflow): flow and modules introduced.
- https://github.com/sustainability-software-lab/ca-biositing/pull/108

**Open questions**
- Whether unresolved FK rows are dropped silently in the transform (not verified in this pass).

# Related Concepts
- [System overview (start here)](system-overview.md): Google Sheets source feeding the sample-tracking tables
- [Samples ETL wrapper flow (field samples then prepared samples)](flow-samples-etl.md): samples_etl runs this flow after field samples
- [Field Sample ETL flow (four-worksheet join)](flow-field-sample-etl.md): Supplies the FieldSample rows that preparation records reference
