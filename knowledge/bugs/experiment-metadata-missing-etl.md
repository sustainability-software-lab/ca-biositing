---
type: Bug
title: "#356: Experiment metadata not fully included in the ETL"
description: "Experiment metadata beyond what #341 added is still not loaded into the experiment field."
tags: [bug, etl-ingestion]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:15Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/356"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #356 (https://github.com/sustainability-software-lab/ca-biositing/issues/356). Symptom: Follow-up to #341: the rest of the experiment metadata is not yet loaded into the experiment field.

**Status.** Open on GitHub (created 2026-05-13; assignee unassigned). Part of theme `facts/issues-etl-ingestion`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/` | (analysis transforms) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/` | (analysis loaders) |

**How it works.** Location inferred from the layout; the experiment field is not located by grep in this pass (inferred; confirm by grepping for ’experiment’ in etl/load/analysis).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-05-13 as #356. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: ETL and data ingestion (pipeline)](../facts/issues-etl-ingestion.md): Theme inventory that lists #356
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
