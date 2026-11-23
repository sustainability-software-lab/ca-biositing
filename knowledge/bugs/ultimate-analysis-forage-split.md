---
type: Bug
title: "#324: UC Davis forage analysis shows up as ultimate analysis"
description: UC Davis forage parameters are classified as ultimate analysis in the portal views.
tags: [bug, qc-data-quality]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:14Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/almond_nsjv.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/324"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #324 (https://github.com/sustainability-software-lab/ca-biositing/issues/324). Symptom: Almond-hull parameters from the UC Davis analysis are labelled ultimate analysis; they should be a separate analysis type (forage_analysis) with their own visual.

**Status.** Open on GitHub (created 2026-05-05; assignee unassigned). Part of theme `facts/issues-qc-data-quality`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py:233` | get_ultimate_filter (analysis_type gate) |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py` | (ultimate branch) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/almond_nsjv.py` | (almond source data) |

**How it works.** Verified that get_ultimate_filter gates by analysis type. Whether the UC Davis rows are tagged ’ultimate’ at load time is inferred (confirm by querying analysis_type for almond hull rows).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-05-05 as #324. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: data-quality audits and QC filters](../facts/issues-qc-data-quality.md): Theme inventory that lists #324
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
