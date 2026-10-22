---
type: Bug
title: "#488: Unready data is shown; bioconversion should be greyed out and gasification tagged beta"
description: "Unready tabs are visible in the portal and need [beta] or [coming soon] tags."
tags: [bug, frontend-portal]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:21Z" }
status: stable
code_refs: ["frontend/"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/488"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #488 (https://github.com/sustainability-software-lab/ca-biositing/issues/488). Symptom: Bioconversion tab should be greyed out with [coming soon]; gasification tab needs [beta] and request-a-sample flow.

**Status.** Open on GitHub (created 2026-09-28; assignee unassigned). Part of theme `facts/issues-frontend-portal`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `frontend/` | (tab rendering; submodule not populated) |

**How it works.** Frontend-only; the gating is not in this backend (inferred).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-09-28 as #488. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: frontend data portal (UI, charts, labels, content)](../facts/issues-frontend-portal.md): Theme inventory that lists #488
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
