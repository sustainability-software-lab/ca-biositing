---
type: Bug
title: "#446: Pie chart palette has low contrast on some displays"
description: Pie chart colors have low contrast on some displays.
tags: [bug, frontend-portal]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:18Z" }
status: stable
code_refs: ["frontend/"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/446"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #446 (https://github.com/sustainability-software-lab/ca-biositing/issues/446). Symptom: On a screen share or alternate display, the light blue and light gray slices are hard to see against the white background.

**Status.** Open on GitHub (created 2026-07-01; assignee unassigned). Part of theme `facts/issues-frontend-portal`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `frontend/` | (chart palette; submodule not populated in this worktree) |

**How it works.** Location inferred to the frontend chart palette; not verifiable in this checkout (inferred; confirm in the frontend submodule).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-07-01 as #446. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: frontend data portal (UI, charts, labels, content)](../facts/issues-frontend-portal.md): Theme inventory that lists #446
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
