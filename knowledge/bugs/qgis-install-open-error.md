---
type: Bug
title: "#176: QGIS install/open fails after `pixi run qgis`"
description: pixi run qgis opens a window with an error on the reporter’s machine; cause not in the issue text.
tags: [bug, tooling-devex-ci]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:11Z" }
status: stable
code_refs: ["frontend/"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/176"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #176 (https://github.com/sustainability-software-lab/ca-biositing/issues/176). Symptom: Running `pixi run qgis` launches a window that shows an error (screenshot only; body text truncated in the issue).

**Status.** Open on GitHub (created 2026-03-12; assignee unassigned). Part of theme `facts/issues-tooling-devex-ci`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `pixi.toml:16` | gis feature (qgis, raster, vector, kernel) |
| `pixi.toml:251-252` | [tasks.qgis] depends on run-qgis in the gis environment |

**How it works.** Symptom details are only in an image; root cause not identified. Location is the gis env definition (inferred; confirm by reproducing on macOS arm64 with `pixi run qgis`).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-03-12 as #176. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: developer environment, CI and agent tooling](../facts/issues-tooling-devex-ci.md): Theme inventory that lists #176
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
