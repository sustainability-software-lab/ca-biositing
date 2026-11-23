---
type: Bug
title: "#264: Recently added resources lack primary ag product linkages"
description: Resources added by some ETL have no primary_ag_product mapping; mapping approach undecided.
tags: [bug, etl-ingestion]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:14Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/reviewed_api_mappings.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/interactive_commodity_mapper.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/seed_commodity_mappings.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/264"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #264 (https://github.com/sustainability-software-lab/ca-biositing/issues/264). Symptom: New resources (from an unidentified ETL) have no primary ag product mapping. Options: reuse the USDA mapping system, a new mapping script, or manual mapping.

**Status.** Open on GitHub (created 2026-04-16; assignee unassigned). Part of theme `facts/issues-etl-ingestion`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/reviewed_api_mappings.py` | see path |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/interactive_commodity_mapper.py` | see path |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/seed_commodity_mappings.py` | see path |

**How it works.** Mapping helpers exist in utils/. Which ETL created the unmapped resources is not identified in the issue; inferred that the gap is in commodity mapping seeds (inferred; confirm by querying resources without primary_ag_product).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-04-16 as #264. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: ETL and data ingestion (pipeline)](../facts/issues-etl-ingestion.md): Theme inventory that lists #264
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
