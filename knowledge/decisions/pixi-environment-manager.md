---
type: Decision
title: Pixi is the only sanctioned environment and task runner
description: Project rule that all local dev runs through pixi (no bare pip/conda/venv); lists the environments and why commands go through pixi run.
tags: [pixi, tooling, decision, environments]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:52Z" }
status: stable
code_refs: ["pixi.toml", "AGENTS.md", "CONTRIBUTING.md", "docs/architecture.md"]
sources: ["AGENTS.md", "CONTRIBUTING.md", "docs/architecture.md", "pixi.toml"]
governance: constraint
---

## Purpose
Record the decision to use Pixi for dependencies, environments and task running, and to forbid direct conda/pip/venv use for local development.

## Key files
| Path | Role |
|---|---|
| `pixi.toml` | Features, environments and the `[tasks]` table (`[tasks.test]`, `[tasks.start-webservice]`, plus feature-scoped tasks such as `[feature.cloud.tasks.*]`) |
| `AGENTS.md` ("Build System & Environment Management") | Rule: ALWAYS use Pixi |
| `CONTRIBUTING.md:43-78` | Setup: `pixi install`, `pixi run pre-commit-install` |
| `docs/architecture.md` ("Pixi Environment Configuration") | Environment list (default, gis, etl, webservice, frontend, py312/py313, docs) |

## How it works
`pixi install` materializes all features. Tasks wrap Docker services, Alembic, pytest, pre-commit, flows and deployment. Pixi tasks are the public interface for every command in the docs.

## Interfaces
- Callers: developers, CI, agents. Commands look like `pixi run <task>`.

## Gotchas
- Pixi appends extra CLI args to string-command tasks, so `pixi run migrate-autogenerate -m "msg"` works (verified 2026-10-16: it runs `alembic revision --autogenerate -m msg`).
- Docs also mention `deploy`, `cloud-*`, and `py312`/`py313` features, which are defined in feature tables of `pixi.toml`.

## History
- No adoption commit or PR was checked in this pass. The pip/conda rejection is an inference from AGENTS.md wording, not a recorded decision.

## Open questions
- No document records alternatives considered (conda, uv, poetry). Rationale is inferred (confirm with maintainers).

# Related Concepts
- [System overview (start here)](../architecture/system-overview.md): Pixi is the entry point for every component
- [ca_biositing is a PEP 420 namespace shared by three distributions](pep420-namespace-packages.md): Editable installs of the three packages depend on pixi
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Environment list is a current-state fact
