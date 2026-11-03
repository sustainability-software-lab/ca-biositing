---
type: Bug
title: "#361: State and county name inconsistencies in mv_biomass_volume_estimate"
description: State/county names differ in form across rows of mv_biomass_volume_estimate; the mapping is split across utils and the view.
tags: [bug, residue-factors-volumes]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:15Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/us_state_abbrev.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/geo_utils.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/361"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #361 (https://github.com/sustainability-software-lab/ca-biositing/issues/361). Symptom: States and counties are represented inconsistently (for example abbreviations versus full names) in mv_biomass_volume_estimate rows.

**Status.** Open on GitHub (created 2026-05-15; assignee unassigned). Part of theme `facts/issues-residue-factors-volumes`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/us_state_abbrev.py` | (state name to abbreviation map) |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py` | (county_ds_map and county joins) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/geo_utils.py` | see path |

**How it works.** Verified the abbreviation map and the view file exist. county_ds_map is referenced in county_ag_report_record.py and county_ag_report_observation.py; exact mismatch not reproduced (inferred cause).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-05-15 as #361. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: residue factors, volume estimates and new MV products](../facts/issues-residue-factors-volumes.md): Theme inventory that lists #361
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
