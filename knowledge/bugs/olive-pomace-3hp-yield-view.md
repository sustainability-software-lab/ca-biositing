---
type: Bug
title: "#453: Olive pomace 3HP yields in the portal are unclear and implausible"
description: Olive pomace 3HP yields are implausible and have undefined units in the portal; proposed removal from the MV.
tags: [bug, frontend-portal]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:18Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/453"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #453 (https://github.com/sustainability-software-lab/ca-biositing/issues/453). Symptom: 3HP yield for olive pomace (and other residues) reports more than 8 g 3HP per g of an unspecified denominator; units unclear. Remove from the materialized view.

**Status.** Open on GitHub (created 2026-07-10; assignee unassigned). Part of theme `facts/issues-frontend-portal`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/` | (bioconversion views; exact file not located by grep for ’3HP’) |
| `frontend/` | (units label) |

**How it works.** The 3HP string was not found in src/ (grep returned no hits), so the view or table holding it is inferred (confirm by grepping the DB or the ETL for ’3hp’ / ’hydroxypropionic’).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-07-10 as #453. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: frontend data portal (UI, charts, labels, content)](../facts/issues-frontend-portal.md): Theme inventory that lists #453
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
