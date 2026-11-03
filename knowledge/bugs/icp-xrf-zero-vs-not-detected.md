---
type: Bug
title: "#375: ICP/XRF value of exactly 0 should mean not detected, not zero"
description: ICP/XRF zero values are ambiguous (not detected vs real zero); a NULL plus flag design is proposed but undecided.
tags: [bug, qc-data-quality]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:16Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/375"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #375 (https://github.com/sustainability-software-lab/ca-biositing/issues/375). Symptom: Frontend treats exact 0 in ICP/XRF charts as ND with a tooltip. Proposed long-term fix: store NULL in the MV for not-detected and add a below_detection_limit flag column.

**Status.** Open on GitHub (created 2026-05-21; assignee unassigned). Part of theme `facts/issues-qc-data-quality`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py:254` | get_icp_filter |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py:90` | (XRF branch) and ICP branch near L211 |
| `frontend/` | (ND tooltip; submodule not populated here) |

**How it works.** Verified the ICP filter and the XRF/ICP branches exist. Current MV behaviour for zero values is inferred from the issue (confirm by querying mv_biomass_composition for value = 0 in icp/xrf rows). Related closed issue #332 included zeros.

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-05-21 as #375. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: data-quality audits and QC filters](../facts/issues-qc-data-quality.md): Theme inventory that lists #375
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
