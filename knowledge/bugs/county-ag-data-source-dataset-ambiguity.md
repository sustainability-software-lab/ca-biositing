---
type: Bug
title: "#263: CountyAgRecord: data_source (6 entries) vs dataset ambiguity"
description: county ag report writes data_source and dataset rows that overlap; modeling decision still open.
tags: [bug, etl-ingestion]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:13Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_datasets.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_report_record.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/263"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #263 (https://github.com/sustainability-software-lab/ca-biositing/issues/263). Symptom: data_source table has 6 entries that arguably should be modeled as datasets; the two tables overlap.

**Status.** Open on GitHub (created 2026-04-15; assignee unassigned). Part of theme `facts/issues-etl-ingestion`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_datasets.py` | see path |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_report_record.py` | see path |

**How it works.** Verified that these transform modules exist and are the county ag dataset/record writers; the exact data_source handling was not read in this pass (inferred location).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-04-15 as #263. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: ETL and data ingestion (pipeline)](../facts/issues-etl-ingestion.md): Theme inventory that lists #263
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
