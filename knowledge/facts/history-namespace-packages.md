---
type: Decision
title: "Refactor: PEP 420 namespace packages split (PR #66, 2025-11-05)"
description: "Nov 2025 split of the ca_biositing namespace into datamodels, pipeline, and webservice distributions; the reason for the current import layout."
tags: [namespace-packages, refactor, packaging]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:59Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/pyproject.toml", "src/ca_biositing/pipeline/pyproject.toml", "src/ca_biositing/webservice/pyproject.toml"]
sources: ["commit ab8fa6c", "commit 2ce7e3e", "commit 8262877", "https://github.com/sustainability-software-lab/ca-biositing/pull/66"]
governance: context
---

## Purpose
Explains why the repo has three independent distributions sharing the `ca_biositing` namespace.

## Key files
| Path | Role |
|---|---|
| src/ca_biositing/datamodels/ | Distribution 1 (models, views, migrations helpers) |
| src/ca_biositing/pipeline/ | Distribution 2 (ETL, flows) |
| src/ca_biositing/webservice/ | Distribution 3 (FastAPI) |

## How it works
Commit ab8fa6c (PR #66, authored by Copilot, merged 2025-11-05) reorganized into PEP 420 namespace packages. Later commit 2ce7e3e (PR #151, 2026-03-18) activated PyPI releases for these namespace packages, and 8262877 (PR #200) added path filters to CD for them. Docs consolidation (c6a15a6, PR #67) followed the same week.

## Interfaces
Imports are `ca_biositing.<pkg>...`; pixi installs all three as editable packages (see AGENTS.md).

## Gotchas
- Installed PyPI releases and editable installs can shadow each other; the layout is a source of import errors noted in AGENTS.md.
- Path-based CI filters (8262877) must be updated when a new distribution appears.

## History
- ab8fa6c 2025-11-05 PR #66: reorganization.
- 2ce7e3e 2026-03-18 PR #151: PyPI activation.
- 8262877 2026-03-23 PR #200: CD path filters.

## Open questions
- Whether the split was preceded by a separate discussion issue (not visible in git; confirm on GitHub).

# Related Concepts
- [System overview (start here)](../architecture/system-overview.md): describes the three-distribution layout
- [Project history eras (2025-08 to 2026-10)](history-eras.md): sits at the E3 to E4 boundary
