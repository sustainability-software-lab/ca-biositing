---
type: Architecture
title: Qualitative ETL flow (four-sheet qualitative market and end-use workbook)
description: "Reads four worksheets of a qualitative market/end-use Google Sheet and writes datasets, observations, storage, transport and end-use records with lineage."
tags: [pipeline, etl, flow, google-sheets, analysis, qualitative]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:06Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/qualitative.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/qualitative.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/factory.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/qualitative.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/qualitative.py"]
sources: ["commit 35423d1", "https://github.com/sustainability-software-lab/ca-biositing/pull/265", "resources/prefect/run_prefect_flow.py"]
governance: context
stale_after: "2026-12-31"
---

**Purpose**
Loads qualitative market and end-use profiles for resources (storage, transport and end-use records, plus observations and provenance). It is the largest transform in this slice.

**Key files**

| Path:line | Role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/qualitative.py:4-5 | `@flow(name="Qualitative ETL")` `qualitative_etl_flow()` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/qualitative.py:10-15 | GSheet ID `1Hip4BfzqJFQmPctYKtSskRvIS_rGnEzd8zxYTGYYJ-c`; worksheets `data_source`, `parameters`, `use_case_enum`, `qualitative_data` |
| etl/extract/qualitative.py:23 | `extract_qualitative_sheets` returns dict of 4 DataFrames |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/qualitative.py:756 | `transform_qualitative_payloads` (sub-tasks at 198, 260, 321, 368, 431, 603) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/qualitative.py:136 | `load_qualitative_payloads` |

**How it works**
1. Lineage record and group (note: "Qualitative market and end-use analysis").
2. Extract four sheets into a dict.
3. Transform into payloads keyed by `dataset`, `provenance`, storage, transport and end-use. Includes parsing of decimal ranges and trend mapping.
4. Load: lookup-like upserts, Dataset creation, then ResourceStorageRecord, ResourceTransportRecord, ResourceEndUseRecord and Observation rows with `on_conflict_do_update`.

**Interfaces**
- Input: GSheet above (credentials as for other GSheet extracts).
- Output: `dataset`, `observation`, `resource_storage_record`, `resource_transport_record`, `resource_end_use_record`, plus parameter and method lookups.
- Returns the load result. Enabled in master registry (run_prefect_flow.py:20).

**Gotchas**
- Transform is about 790 lines with many helper normalizers; name canonicalization (`_RESOURCE_CANONICAL_MAP`) and forward-filling of columns are behavior-critical (transform lines 17, 72).
- Dataset identity is by name normalization in load; changing sheet naming can create duplicate datasets (inferred from load lines 317-347).

**History**
- 35423d1 (2026-04-23, PR #265 Qualitative data ETL and MVs): flow and modules introduced.
- https://github.com/sustainability-software-lab/ca-biositing/pull/265

**Open questions**
- Sheet ID is hard-coded in the extract; the name of the source workbook is not recorded in code.

# Related Concepts
- [System overview (start here)](system-overview.md): Qualitative analysis data is one of the analysis domains loaded from Google Sheets
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Uses the shared lineage and extractor-factory conventions
- [Resource Information ETL flow (resources, then resource images)](flow-resource-information.md): Storage, transport and end-use rows reference resources created by resource_information
