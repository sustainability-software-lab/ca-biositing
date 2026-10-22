---
type: Bug
title: "#174: 38 of 96 field samples have no resource (stub rows from prepared_sample normalization)"
description: 38 of 96 field samples lack a resource because normalization inserts stub rows; fix belongs at the source sheet.
tags: [bug, etl-ingestion]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:12Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/prepared_sample.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/174"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #174 (https://github.com/sustainability-software-lab/ca-biositing/issues/174). Symptom: Field samples are inserted as stubs by the normalization function in the prepared_sample ETL flow, so they have no resource link.

**Status.** Open on GitHub (created 2026-03-10; assignee unassigned). Part of theme `facts/issues-etl-ingestion`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/prepared_sample.py` | (transform entrypoint; normalization helper imported from utils/name_id_swap.py) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py` | (normalize_dataframes) |

**How it works.** The stub-creation path is inferred from the issue text (the function name in the issue is not found by grep); confirm by tracing normalize_dataframes callers in prepared_sample.py. Fix per the issue is at the Google Sheets source (resource -> field_sample -> prepared_sample).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-03-10 as #174. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: ETL and data ingestion (pipeline)](../facts/issues-etl-ingestion.md): Theme inventory that lists #174
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
