---
type: Bug
title: "#509: Tree nut and orchard residue factors are not on a dry basis"
description: Tree-nut and orchard residue factors mix wet and dry basis; needs data correction and basis flags.
tags: [bug, residue-factors-volumes]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:24Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/residue_factor.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/resource_availability.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/509"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #509 (https://github.com/sustainability-software-lab/ca-biositing/issues/509). Symptom: Factors for walnut shells/hulls, pistachio hulls/shells, grape stem and almond woodchips need correcting to dry basis in residue_factor and resource_availability. Resolves #414.

**Status.** Open on GitHub (created 2026-10-16; assignee unassigned). Part of theme `facts/issues-residue-factors-volumes`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/residue_factor.py` | see path |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/resource_availability.py` | see path |

**How it works.** Models verified to exist; the factor values live in data (not read here).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-10-16 as #509. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: residue factors, volume estimates and new MV products](../facts/issues-residue-factors-volumes.md): Theme inventory that lists #509
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
