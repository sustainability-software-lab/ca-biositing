---
type: Bug
title: "#487: Shortened ’Structural Carb.’ label should be spelled out"
description: Portal shows the abbreviation ’Structural Carb.’ in several places.
tags: [bug, frontend-portal]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:21Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/487"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #487 (https://github.com/sustainability-software-lab/ca-biositing/issues/487). Symptom: Where ’Structural Carb.’ is shown, spell it out as ’Structural Carbohydrates’.

**Status.** Open on GitHub (created 2026-09-28; assignee unassigned). Part of theme `facts/issues-frontend-portal`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `frontend/` | (portal labels; submodule not populated) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/` | (no match for the label in src/ by grep) |

**How it works.** Grep of src/ and frontend/src returned no hits; the label is probably frontend-only (inferred).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-09-28 as #487. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: frontend data portal (UI, charts, labels, content)](../facts/issues-frontend-portal.md): Theme inventory that lists #487
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
