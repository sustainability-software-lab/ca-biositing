---
type: Requirement
title: DATABASE_URL uses host db inside containers; localhost on host
description: "Containers must reach PostgreSQL at host db; the pipeline rewrites @db to localhost only outside Docker and Cloud Run, so new DB code must go through _get_database_url."
tags: [pipeline, requirement, docker, database, networking]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:53Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/engine.py", "resources/docker/docker-compose.yml", "src/ca_biositing/pipeline/.env.example"]
sources: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/engine.py", "resources/docker/docker-compose.yml", "src/ca_biositing/pipeline/.env.example", "AGENTS.md"]
governance: constraint
---

## Requirement
- Inside Docker Compose, `DATABASE_URL` must use host `db` on port 5432 (`src/ca_biositing/pipeline/.env.example` section 3).
- Outside Docker, the pipeline replaces `@db:` with `localhost:<POSTGRES_PORT>` (`src/ca_biositing/pipeline/ca_biositing/pipeline/utils/engine.py:22-24`).
- Any new code that builds a DB URL must go through `_get_database_url()` or `get_engine()`, not a hard-coded host.

## Evidence
- `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/engine.py:12-25` (rewrite logic and `/.dockerenv` and `INSTANCE_CONNECTION_NAME` guards).
- `resources/docker/docker-compose.yml:69-94`: worker mounts code and `credentials.json`, and sets `PREFECT_API_URL=http://prefect-server:4200/api`. The DB service name is `db`.
- Root `AGENTS.md` ("Docker Networking: Inside containers, use the db hostname").

## Caveats
- The rewrite only matches the literal `@db`. A different host name is not rewritten.
- The guard checks for `/.dockerenv`. Other container runtimes without that file would get the rewrite wrongly applied (inferred; confirm on the target runtime).

## Open questions
- None recorded in code or git history.

# Related Concepts
- [Database engines and DATABASE_URL host rewriting](../architecture/pipeline-engine-and-db-url.md): Implements this rule.
- [System overview (start here)](../architecture/system-overview.md): Docker topology this depends on.
