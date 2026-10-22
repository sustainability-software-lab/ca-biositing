---
type: Bug
title: "#506: Volume view uses hard-coded integer IDs instead of name joins"
description: "Volume view depends on hard-coded row IDs, breaking across databases; needs name joins (epic #505)."
tags: [bug, residue-factors-volumes]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:22Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/506"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #506 (https://github.com/sustainability-software-lab/ca-biositing/issues/506). Symptom: mv_biomass_volume_estimate and transforms use integer lookup IDs (acreage unit, bearing, BNB, harvested, county_ds_map, dataset_id=1). Proposed: name joins plus bearing_acres COALESCE fallback for suppressed (D) rows.

**Status.** Open on GitHub (created 2026-10-16; assignee unassigned). Part of theme `facts/issues-residue-factors-volumes`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py` | (Path D COALESCE, ~L15) |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py` | (ID lookups; exact lines not pinned) |

**How it works.** Verified the view file and COALESCE logic. Exact hard-coded ID lines were not individually pinned in this pass (inferred location for each).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-10-16 as #506. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: residue factors, volume estimates and new MV products](../facts/issues-residue-factors-volumes.md): Theme inventory that lists #506
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
