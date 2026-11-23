---
type: Decision
title: ca_biositing is a PEP 420 namespace shared by three distributions
description: "Why src/ca_biositing has no __init__.py and how datamodels, pipeline and webservice are separate installable packages under one namespace."
tags: [namespace-packages, packaging, decision]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:51Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/AGENTS.md", "src/ca_biositing/datamodels/ca_biositing/datamodels", "src/ca_biositing/pipeline", "src/ca_biositing/webservice", ".agents/rules/namespace-packages.md"]
sources: ["README.md", "src/ca_biositing/datamodels/AGENTS.md", ".agents/rules/namespace-packages.md"]
governance: constraint
---

## Purpose
Record the packaging choice: one shared `ca_biositing` namespace split across three independently installed distributions.

## Key files
| Path | Role |
|---|---|
| `README.md:86` | Describes the PEP 420 namespace with three packages |
| `src/ca_biositing/datamodels/AGENTS.md:57` | Rule: `ca_biositing/` must NOT contain `__init__.py` |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/` | Datamodels implementation |
| `src/ca_biositing/pipeline/`, `src/ca_biositing/webservice/` | Other two distributions |
| `.agents/rules/namespace-packages.md` | Import and structure rules for agents |

## How it works
Each distribution is installed editable into the Pixi env, so `ca_biositing.datamodels`, `ca_biositing.pipeline` and `ca_biositing.webservice` import together without PYTHONPATH tweaks (root AGENTS.md "Pathing & Namespace Packages"). Verified: no `__init__.py` exists at `src/ca_biositing/` or `src/ca_biositing/datamodels/ca_biositing/`.

## Interfaces
- Callers import `ca_biositing.datamodels.models`, `ca_biositing.datamodels.database`, and so on.

## Gotchas
- Adding an `__init__.py` at the namespace level breaks the three-way split (AGENTS.md "CRITICAL").
- Import errors usually mean the command was run outside `pixi run` (datamodels AGENTS.md "Import errors").

## History
- Docs predate the current layout; the namespace split was introduced with the three packages (exact PR not verified; check `git log -- src/ca_biositing/*/pyproject.toml`).

## Open questions
- Which PR first introduced the namespace split is not recorded (unverified).

# Related Concepts
- [System overview (start here)](../architecture/system-overview.md): Explains how the three components share one import root
- [Pixi is the only sanctioned environment and task runner](pixi-environment-manager.md): Pixi installs the editable packages that make the namespace work
