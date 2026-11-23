---
type: Bug
title: "#400: Review data currently filtered out by QC"
description: No process exists yet to review rows dropped by QC filters; log_filter_summary gives counts only.
tags: [bug, qc-data-quality]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:16Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/400"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #400 (https://github.com/sustainability-software-lab/ca-biositing/issues/400). Symptom: Need a review of rows dropped by QC filters so analysts can recover them and improve data flowing to the portal; possibly quarterly.

**Status.** Open on GitHub (created 2026-06-04; assignee unassigned). Part of theme `facts/issues-qc-data-quality`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py:107` | get_qc_status_filter |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py:340` | log_filter_summary (before/after counts) |

**How it works.** Verified log_filter_summary reports removed counts per filter. The dropped-row review is a process task; no code change is specified (inferred scope).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-06-04 as #400. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: data-quality audits and QC filters](../facts/issues-qc-data-quality.md): Theme inventory that lists #400
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
