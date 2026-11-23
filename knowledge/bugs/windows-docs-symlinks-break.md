---
type: Bug
title: "#178: Tracked docs symlinks become unreadable on Windows after checkout"
description: Docs files stored as git symlinks break on Windows checkouts.
tags: [bug, tooling-devex-ci]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:11Z" }
status: stable
code_refs: ["docs/AI_POLICY.md", "docs/CHANGELOG.md", "docs/CODE_OF_CONDUCT.md"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/178"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #178 (https://github.com/sustainability-software-lab/ca-biositing/issues/178). Symptom: On Windows, several docs files tracked as symlinks break after checkout/restore/branch switch; links look present but open fails.

**Status.** Open on GitHub (created 2026-03-16; assignee unassigned). Part of theme `facts/issues-tooling-devex-ci`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `docs/AI_POLICY.md` | (git mode 120000, symlink) |
| `docs/CHANGELOG.md` | (git mode 120000) |
| `docs/CODE_OF_CONDUCT.md` | (git mode 120000) |
| `.gitattributes` | (repo root) |

**How it works.** Verified: `git ls-files -s docs` shows symlink entries (mode 120000) for the docs files above. Windows symlink support depends on core.symlinks and developer mode (inferred; confirm on a Windows clone).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-03-16 as #178. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: developer environment, CI and agent tooling](../facts/issues-tooling-devex-ci.md): Theme inventory that lists #178
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
