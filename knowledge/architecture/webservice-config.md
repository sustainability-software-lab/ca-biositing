---
type: Architecture
title: Webservice settings and API_ environment variables
description: "Every setting in WebServiceConfig with its env var name, default, and the Cloud Run value that overrides it."
tags: [webservice, config, env, settings]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:43Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/config.py", "src/ca_biositing/webservice/ca_biositing/webservice/main.py", "deployment/cloud/gcp/infrastructure/cloud_run.py"]
sources: ["commit 203b787", "commit 844ef97", "deployment/cloud/gcp/infrastructure/cloud_run.py", "commit 00a7146", "commit 811255f", "https://github.com/sustainability-software-lab/ca-biositing/pull/532"]
---

## Purpose
All runtime knobs for the API come from one pydantic-settings class. Env vars use the prefix `API_` (case-insensitive). A `.env` file in the working directory is read if present.

## Key file
`src/ca_biositing/webservice/ca_biositing/webservice/config.py:1` (`WebServiceConfig`, instantiated as module-level `config`). Module-level instantiation means env must be set before import.

## Variables
| Env var | Field | Default | Notes |
|---|---|---|---|
| `API_TITLE` | api_title | "CA Biositing API" | OpenAPI title |
| `API_DESCRIPTION` | api_description | "REST API for CA Biositing bioeconomy data" | |
| `API_VERSION` | api_version | package `_version` (from git tag via hatch-vcs) | |
| `API_CORS_ORIGINS` | cors_origins | localhost 3000, 5173, 8080 | list; Cloud Run sets it from `CORS_ORIGINS` when non-empty |
| `API_CORS_ALLOW_CREDENTIALS` | cors_allow_credentials | true | |
| `API_CORS_ALLOW_METHODS` / `_HEADERS` | | `["*"]` | |
| `API_JWT_SECRET_KEY` | jwt_secret_key | dev value, min length 32 | Prod: from Secret Manager `jwt-secret` |
| `API_JWT_ALGORITHM` | jwt_algorithm | HS256 | |
| `API_JWT_EXPIRE_MINUTES` | jwt_expire_minutes | 30 | |
| `API_JWT_COOKIE_SECURE` | jwt_cookie_secure | false | Cloud Run sets `true` |
| `API_GOOGLE_CLIENT_ID` (also `GOOGLE_CLIENT_ID`) | google_client_id | "" | Portal Google OIDC audience. Cloud Run injects it from secret `oauth2-client-id` (`cloud_run.py`, webservice args) |
| `API_DASHBOARD_ALLOWED_DOMAINS` (also `DASHBOARD_ALLOWED_DOMAINS`) | dashboard_allowed_domains | `lbl.gov`, `ucdavis.edu`, `beamcircular.org` | `config.py:75-82`. Domain-wide analyst access |
| `API_DASHBOARD_ALLOWED_EMAILS` | dashboard_allowed_emails | `[]` | Individual analyst allowlist (`config.py:83-90`) |
| `API_DASHBOARD_ADMIN_EMAILS` | dashboard_admin_emails | 3 hardcoded admin accounts (addresses not recorded here) | `config.py:91-102`. Was 1 before #532 (2026-10-21). Admins are also allowlisted |
| `API_REQUIRE_DASHBOARD_AUTH` | require_dashboard_auth | true | When false, `portal_auth.py:327-335` returns a dev analyst for every request |
| `API_DASHBOARDS_BUCKET_NAME` | dashboards_bucket_name | "" | Cloud Run sets `DASHBOARDS_BUCKET_NAME`. Empty falls back to `biocirv-dashboards` in `dashboard_loader.py` |
| `API_DASHBOARDS_GCS_PREFIX` | dashboards_gcs_prefix | `dashboards/staging/latest` | Cloud Run sets `dashboards/{stack}/latest` (`cloud_run.py`) |

## Gotchas
- The portal signs `biocirv_portal_token` with the same `API_JWT_SECRET_KEY` as the API JWTs, but uses a different payload (`token_use`, `role`). See `architecture/portal-oidc-auth-and-rbac`.
- The admin list is hardcoded in source. Override it with `API_DASHBOARD_ADMIN_EMAILS` (list parsing is pydantic-settings’ job; check the format before relying on it).
- Database settings are not here. They come from the datamodels package (`ca_biositing.datamodels.config`, `DB_*`/`POSTGRES_*` style variables; see `architecture/datamodels-database-session`).
- `main.py` logs a warning when the JWT secret is the dev default. It does not refuse to start, so a missing prod secret is silent except for the log line.
- The `.env` file is read from the current working directory, so `pixi run start-webservice` (cwd `src`) and uvicorn from the repo root read different files.
- `CORS_ORIGINS` in Cloud Run (`deployment/cloud/gcp/infrastructure/config.py`) is a deploy-time value, not the field name `API_CORS_ORIGINS` itself. Confirm the mapping when changing origins.

# Related Concepts
- [JWT login, cookie transport, and refresh in the webservice](webservice-auth-jwt.md): JWT settings are read here
- [Webservice deployment on GCP Cloud Run](webservice-deployment-cloud-run.md): Cloud Run env values for these settings
- [Datamodels DB engine and session management (database.py)](datamodels-database-session.md): DB connection settings are a separate config class
- [BioCirV portal auth: Google OIDC, 2-role RBAC, isolated cookie](portal-oidc-auth-and-rbac.md): portal settings consumed here
- [Dashboard snapshot loader: local-first, then GCS with TTL and ETag cache](dashboard-snapshot-loader-gcs.md): dashboard bucket and prefix settings
