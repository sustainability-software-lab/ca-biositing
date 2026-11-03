---
type: Bug
title: "#368: Resources table missing primary_ag_product, class_id and other fields for many resources"
description: Resource rows are missing primary_ag_product and class_id; resources table needs a QC pass.
tags: [bug, etl-ingestion]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:16Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource_information/"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/368"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #368 (https://github.com/sustainability-software-lab/ca-biositing/issues/368). Symptom: Almond hash and other resources lack primary_ag_product, resource class_id and other columns; suspected cause is many ETLs creating resources without these fields.

**Status.** Open on GitHub (created 2026-05-19; assignee @mglbleta). Part of theme `facts/issues-etl-ingestion`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource.py` | (resource writer) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource_information/` | (resource metadata transforms) |

**How it works.** Suspected cause is in the issue; verified that resource.py and resource_information/ exist. Which loader writes each resource is not traced (inferred; confirm by querying null columns on the resource table).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-05-19 as #368. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: ETL and data ingestion (pipeline)](../facts/issues-etl-ingestion.md): Theme inventory that lists #368
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
