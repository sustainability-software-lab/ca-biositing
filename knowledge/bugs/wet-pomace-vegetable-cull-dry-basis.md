---
type: Bug
title: "#510: Wet-basis pomace and vegetable cull factors overstate dry tonnage 3.3x to 7.4x"
description: Pomace and cull residue factors are wet basis; dry tonnage is overstated 3.3x to 7.4x.
tags: [bug, residue-factors-volumes]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:24Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/residue_factor.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/510"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #510 (https://github.com/sustainability-software-lab/ca-biositing/issues/510). Symptom: Tomato, grape, peach, olive, orange pomace and sweet potato culls are stored wet-basis in residue_factor, overstating dry tons in the MV.

**Status.** Open on GitHub (created 2026-10-16; assignee unassigned). Part of theme `facts/issues-residue-factors-volumes`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/residue_factor.py` | see path |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py` | see path |

**How it works.** Overstatement factors are from the issue body (not recomputed here).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-10-16 as #510. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: residue factors, volume estimates and new MV products](../facts/issues-residue-factors-volumes.md): Theme inventory that lists #510
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
