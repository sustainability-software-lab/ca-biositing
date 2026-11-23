---
type: Bug
title: "#507: Corn stover silage vs grain overestimate (43.5x) and substream double counting"
description: Corn stover volume is overestimated 43.5x because it routes to silage tonnage; substreams double count.
tags: [bug, residue-factors-volumes]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:23Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/residue_factor.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/507"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #507 (https://github.com/sustainability-software-lab/ca-biositing/issues/507). Symptom: Corn stover is routed to silage-derived tonnage, giving a 43.5x overestimate for 2022 NSJV; substreams double count (1.826x). Proposed: link stover to ’corn - grain’ by name, flag substreams.

**Status.** Open on GitHub (created 2026-10-16; assignee unassigned). Part of theme `facts/issues-residue-factors-volumes`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py` | (Path A/E routing) |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/residue_factor.py` | see path |

**How it works.** Overestimate numbers are from the issue body and were not recomputed. Routing logic location is verified only at the file level.

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-10-16 as #507. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: residue factors, volume estimates and new MV products](../facts/issues-residue-factors-volumes.md): Theme inventory that lists #507
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
