---
type: Bug
title: "#405: Almond hulls show only N for ultimate analysis (no C, O, H)"
description: Almond hull ultimate analysis shows nitrogen only; C and O rows are missing from the view.
tags: [bug, qc-data-quality]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:17Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/almond_nsjv.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/405"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #405 (https://github.com/sustainability-software-lab/ca-biositing/issues/405). Symptom: For almond hulls only nitrogen appears under ultimate analysis; C and O (and likely H) are expected.

**Status.** Open on GitHub (created 2026-06-10; assignee unassigned). Part of theme `facts/issues-qc-data-quality`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py:233` | get_ultimate_filter (parameter whitelist) |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py:201-213` | carbon/hydrogen/nitrogen avg expressions |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/almond_nsjv.py` | (almond source load) |

**How it works.** Verified the carbon/hydrogen/nitrogen average helpers exist in common.py. Whether the whitelist or the load drops C/O for almond hulls is inferred (confirm by querying the analysis rows for almond hulls).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-06-10 as #405. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: data-quality audits and QC filters](../facts/issues-qc-data-quality.md): Theme inventory that lists #405
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
