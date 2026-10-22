---
type: Bug
title: "#454: Bioconversion compare figure overlaps on mobile (iPhone Safari)"
description: Bioconversion compare chart text overlaps on mobile Safari.
tags: [bug, frontend-portal]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:19Z" }
status: stable
code_refs: ["frontend/"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/454"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #454 (https://github.com/sustainability-software-lab/ca-biositing/issues/454). Symptom: Text is squeezed and overlaps in the bioconversion compare figure on mobile (reported on iPhone 16, Safari).

**Status.** Open on GitHub (created 2026-07-10; assignee unassigned). Part of theme `facts/issues-frontend-portal`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `frontend/` | (bioconversion compare chart; submodule not populated) |

**How it works.** Frontend-only symptom; no backend location (inferred).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-07-10 as #454. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: frontend data portal (UI, charts, labels, content)](../facts/issues-frontend-portal.md): Theme inventory that lists #454
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
