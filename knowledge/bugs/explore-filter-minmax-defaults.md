---
type: Bug
title: "#470: Explore filter min/max defaults should be 0.1 when unset"
description: Explore filters with no min/max should default min to 0.1.
tags: [bug, frontend-portal]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:19Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_search.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/470"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #470 (https://github.com/sustainability-software-lab/ca-biositing/issues/470). Symptom: When no min/max is given on apply, default min should be 0.1 so users can see items that have the parameter, for both parameter and product filters.

**Status.** Open on GitHub (created 2026-08-24; assignee unassigned). Part of theme `facts/issues-frontend-portal`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `frontend/` | (explore filter apply logic; submodule not populated) |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_search.py` | (percentile_cont 0.1 low-value columns, ~L150-156) |

**How it works.** Frontend location inferred; the backend percentile columns are verified but are not the default-min logic (inferred).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-08-24 as #470. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: frontend data portal (UI, charts, labels, content)](../facts/issues-frontend-portal.md): Theme inventory that lists #470
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
