---
type: Bug
title: "#316: County ag report dataset names not standardized (snake_case vs lowercase)"
description: "County ag report dataset names need to be lowercase, not snake_case."
tags: [bug, etl-ingestion]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:13Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_datasets.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/county_ag_report_etl.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/316"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #316 (https://github.com/sustainability-software-lab/ca-biositing/issues/316). Symptom: County ag report dataset names are not standardized; expected lowercase, currently snake case.

**Status.** Open on GitHub (created 2026-05-01; assignee @mglbleta). Part of theme `facts/issues-etl-ingestion`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_datasets.py` | see path |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/flows/county_ag_report_etl.py` | (flow entry, imports dataset transform at L21) |

**How it works.** Verified that county_ag_report_etl.py imports county_ag_datasets as dataset_transform. Name normalization logic not read (inferred location).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-05-01 as #316. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: ETL and data ingestion (pipeline)](../facts/issues-etl-ingestion.md): Theme inventory that lists #316
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
