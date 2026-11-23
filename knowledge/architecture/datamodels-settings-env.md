---
type: Architecture
title: Datamodels settings and DB environment variables (config.py)
description: "Pydantic Settings loading DB env vars from resources/docker/.env; DATABASE_URL > Cloud SQL socket > TCP host. Lists each variable and its default."
tags: [datamodels, config, env, postgres, cloud-sql]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:26:56Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/config.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/database.py", "resources/docker/.env.example", "alembic/env.py"]
sources: ["commit 5bdefc9", "commit 3edcb17", "https://github.com/sustainability-software-lab/ca-biositing/pull/125", "https://github.com/sustainability-software-lab/ca-biositing/pull/127", "resources/docker/.env.example"]
governance: context
stale_after: "2026-11-16"
---

## Purpose
Builds the PostgreSQL connection URL from environment variables and an optional `.env` file.

## Key files
| Path:line | Role |
|---|---|
| `config.py:8-15` | Walks up from the file until a directory containing `pixi.toml` is found; env file is `<root>/resources/docker/.env` |
| `config.py:18-41` | `class Settings(BaseSettings)`: fields and `SettingsConfigDict(env_file=..., case_sensitive=True, extra="ignore")` |
| `config.py:43-72` | `database_url` property with priority: explicit `DATABASE_URL`, then Cloud SQL Unix socket, then TCP |
| `config.py:75` | `settings = Settings()` at import time |

## Environment variables
| Variable | Default in code | Notes |
|---|---|---|
| `POSTGRES_USER` | `postgres` | |
| `POSTGRES_PASSWORD` | `postgres` | URL-encoded only in socket mode |
| `POSTGRES_DB` | `biositing` | `.env.example` uses `biocirv_db`; see gotcha |
| `POSTGRES_HOST` | `db` | Docker-network hostname; use `localhost` from the host |
| `POSTGRES_PORT` | `5432` | |
| `DATABASE_URL` | unset | Wins over everything; used by Alembic and Compose |
| `INSTANCE_CONNECTION_NAME` | unset | Enables `/cloudsql/<name>` socket URL |
| `DB_USER`, `DB_PASS` | unset | Override POSTGRES_USER/PASSWORD in socket mode only |

## How it works
`database_url` returns `DATABASE_URL` if set. Otherwise, if `INSTANCE_CONNECTION_NAME` is set, it builds `postgresql://user:quoted_pw@/db?host=/cloudsql/<name>` by string formatting (not `URL.create`, because that percent-encodes the socket path; see comment at `config.py:57-60`). Otherwise it uses `URL.create(...)` with host and port.

## Interfaces
- Consumed by: `database.py:13-14` (`_get_engine`) and `alembic/env.py:33-37`.
- Compose/env template: `resources/docker/.env.example` (contains `DATABASE_URL=postgresql+psycopg2://...` and `POSTGRES_DB=biocirv_db`).

## Gotchas
- Defaults are Docker-oriented (`POSTGRES_HOST=db`). Host-side commands need `POSTGRES_HOST=localhost` (AGENTS.md; `src/ca_biositing/datamodels/AGENTS.md` pitfalls).
- Name mismatch: code default `POSTGRES_DB=biositing` vs `.env.example` `biocirv_db`. If the `.env` file is missing, the code default is used (inferred from values; confirm which DB name the running stack expects).
- `case_sensitive=True`: variable names must match exactly.
- `settings = Settings()` runs at import of `config.py`. `database.py` deliberately imports it lazily to avoid this at import time (`database.py:13`).
- `.env` lookup depends on finding `pixi.toml` upward; if the package is installed outside the repo, `_project_root` falls back to the filesystem root and the env file is not found (inferred from the loop at lines 10-14).

## History
- `a9a86eb` (PR #84) and `ab8fa6c` (PR #66, namespace reorg) shaped the package layout.
- `5bdefc9` (PR #125) added `INSTANCE_CONNECTION_NAME`, `DB_USER`, `DB_PASS` and the socket branch for Cloud Run.
- `3edcb17` (PR #127) fixed the project-root search (now stops at filesystem root) and socket credential fallback.

## Open questions
- Whether `.env.example`’s `biocirv_db` should match the `biositing` code default (not changed in any commit reviewed).

# Related Concepts
- [Datamodels DB engine and session management (database.py)](datamodels-database-session.md): consumer of settings.database_url
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](migrations.md): Alembic reads the same URL resolution
- [System overview (start here)](system-overview.md): hub: env wiring for local vs Cloud Run
