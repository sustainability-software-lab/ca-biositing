---
type: Bug
title: "#471: Chart axes and filters lack units (% dry weight, dry tons/year, $/ton)"
description: Portal charts and filters lack units; labels need to be added.
tags: [bug, frontend-portal]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:20Z" }
status: stable
code_refs: ["frontend/"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/471"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #471 (https://github.com/sustainability-software-lab/ca-biositing/issues/471). Symptom: Ultimate chart should say ’% dry weight’; volume and pricing charts lack units; explore parameter/product filters lack context.

**Status.** Open on GitHub (created 2026-08-24; assignee unassigned). Part of theme `facts/issues-frontend-portal`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `frontend/` | (chart axis labels; submodule not populated) |

**How it works.** Frontend-only; no backend unit metadata verified (inferred).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-08-24 as #471. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: frontend data portal (UI, charts, labels, content)](../facts/issues-frontend-portal.md): Theme inventory that lists #471
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
