---
type: Decision
title: ETL orchestrated by Prefect inside Docker Compose services
description: "Prefect server, worker and Postgres run as Docker Compose services started by pixi tasks; flows run inside containers, not on the host."
tags: [prefect, etl, docker, decision]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:52Z" }
status: stable
code_refs: ["docs/pipeline/PREFECT_WORKFLOW.md", "pixi.toml", "docs/architecture.md"]
sources: ["docs/pipeline/PREFECT_WORKFLOW.md", "docs/architecture.md", "https://github.com/sustainability-software-lab/ca-biositing/pull/440", "commit a9a86eb"]
governance: context
---

## Purpose
Record that Prefect is the workflow orchestrator and that the ETL runs in containers managed by Compose.

## Key files
| Path | Role |
|---|---|
| `docs/pipeline/PREFECT_WORKFLOW.md:1-25` | Start services with `pixi run start-services`, check with `service-status` |
| `docs/architecture.md:44`, `:106` | "Orchestrated by Prefect + Docker"; "Workflow Orchestration: Prefect" |
| `pixi.toml:81` | `start-services` task |
| `pixi.toml:147-150` | `run-single-flow` and `list-flows` tasks |
| `README.md:91` | Pipeline described as Prefect-orchestrated |

## How it works
Compose starts Postgres, Prefect server and a worker. `run-single-flow <module>` triggers a flow by module name. Inside containers the DB host is `db` (AGENTS.md "Docker Networking").

## Interfaces
- Input: flow module name. Output: Prefect runs and rows in the ETL DB.

## Gotchas
- AGENTS.md requires heavy imports to happen inside `@task`/`@flow` bodies to avoid Docker hangs.
- The docs contain `prefect deployment run` commands; they depend on the worker being up.

## History
- Pipeline and Prefect layout came in with the Berkeley upstream integration (commit a9a86eb, 2026-02-05, PR #84) (inferred from file history; not verified line by line).
- Unified static-resource task added in commit be75727 (PR #440).

## Rejected alternatives
None recorded in the repo.

## Open questions
- Why Prefect rather than another orchestrator is not written down (unknown).

# Related Concepts
- [System overview (start here)](../architecture/system-overview.md): Pipeline component sits behind this orchestration choice
- [Pixi is the only sanctioned environment and task runner](pixi-environment-manager.md): Pixi tasks start and manage the containers
