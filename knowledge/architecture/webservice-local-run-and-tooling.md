---
type: Architecture
title: Running the webservice locally and generating OpenAPI
description: pixi start-webservice runs uvicorn from src; generate-openapi writes docs/api/openapi.json; create-admin seeds the first user. Includes the docs and health endpoints to check.
tags: [webservice, local-dev, pixi, uvicorn, openapi]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:21Z" }
status: stable
code_refs: ["pixi.toml", "scripts/generate_openapi.py", "scripts/create_admin.py", "docs/api/openapi.json", "docs/api/webservice.md"]
sources: ["commit e41d00d", "commit 203b787", "docs/api/webservice.md", "AGENTS.md"]
governance: context
---

## Purpose
Quick start for a developer or agent who needs the API running.

## Commands
| Command | What it does | Where |
|---|---|---|
| `pixi install` | Installs envs, including editable `ca-biositing-webservice` | `pixi.toml:354` |
| `pixi run start-webservice` | `uvicorn ca_biositing.webservice.main:app --reload`, cwd `src` | `pixi.toml:254` |
| `pixi run -e webservice generate-openapi` | Runs `scripts/generate_openapi.py`, writes `docs/api/openapi.json`, no DB needed | `pixi.toml:362` |
| `pixi run create-admin` | Runs `scripts/create_admin.py` to seed an admin user (per commit 203b787 message, password is not a CLI arg) | `pixi.toml:366` |
| `pixi run pytest src/ca_biositing/webservice -m "not integration"` | CI-style unit run | `.github/workflows/ci.yml:75` |

## Local URLs
- API root redirects to `http://localhost:8000/docs`.
- `/health` needs a reachable DB (`db` host inside Docker, `localhost` outside, per AGENTS.md).
- `/v1/health` returns OK without DB.
- Auth: `POST /v1/auth/token` with the admin account from `create-admin`.

## Gotchas
- Because the task uses `cwd = src`, a `.env` in the repo root is probably not read by `config.py` (inferred from pydantic-settings’ cwd-relative `env_file=".env"`). Put `API_*` vars in the environment to be safe.
- The default JWT secret is used unless `API_JWT_SECRET_KEY` is set; a warning is logged.
- `docs/api/webservice.md` renders `docs/api/openapi.json` with rapi-doc. Regenerate the JSON after adding or changing routes.
- Local DB must be running (`pixi run start-services`) or `/health` returns 503 and feedstock routes error.

## Open questions
- None blocking. Verify the pinned FastAPI version before upgrading (`architecture/webservice-overview` gotcha).

# Related Concepts
- [Webservice deployment on GCP Cloud Run](webservice-deployment-cloud-run.md): Same app, different entrypoint and port
- [Webservice settings and API_ environment variables](webservice-config.md): Env vars read at startup
- [System overview (start here)](system-overview.md): Hub entry for running the system
