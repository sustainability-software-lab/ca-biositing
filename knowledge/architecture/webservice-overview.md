---
type: Architecture
title: Webservice package layout and app factory
description: "How the FastAPI app in ca_biositing.webservice is assembled: main.py wiring, v1 router tree, services layer, and the datamodels dependency."
tags: [webservice, fastapi, api, architecture]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:45Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/main.py", "src/ca_biositing/webservice/ca_biositing/webservice/config.py", "src/ca_biositing/webservice/ca_biositing/webservice/dependencies.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/router.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/portal_auth.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/qc_ledger_service.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/gsheet_sync_service.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/dashboard_loader.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/endpoints/qc_review.py"]
sources: ["commit e41d00d", "commit 203b787", "commit e289fd1", "https://github.com/sustainability-software-lab/ca-biositing/pull/139", "https://github.com/sustainability-software-lab/ca-biositing/pull/248", "docs/api/openapi.json", "commit 00a7146", "commit 7af19de", "commit 811255f", "https://github.com/sustainability-software-lab/ca-biositing/pull/524"]
---

## Purpose
FastAPI REST API that serves USDA census/survey data, feedstock analysis results, resource availability, and user/API-key auth for the CA Biositing project. Read-only data endpoints over DB views, plus auth management endpoints. Since Oct 2026 it also serves the BioCirV dashboard suite and the two-stage QC review API, both behind a separate portal auth system.

## Key files
| Path | Role |
|---|---|
| `src/ca_biositing/webservice/ca_biositing/webservice/main.py:1` | App object `app`, CORS middleware, exception handlers, root/`/hello`/`/health` routes, mounts v1 router |
| `.../webservice/config.py:1` | `WebServiceConfig` (pydantic-settings, env prefix `API_`), module-level `config` instance |
| `.../webservice/dependencies.py:1` | `SessionDep`, `pagination_params`, `get_jwt_user`, `get_current_user`, `get_current_admin_user` and their `Annotated` aliases |
| `.../webservice/exceptions.py:1` | HTTPException subclasses (404/422/500) used by services |
| `.../webservice/v1/router.py:1` | Builds `/v1` router: open `/v1/health`, open auth router, feedstocks router behind `get_current_user` |
| `.../webservice/v1/auth/router.py:1` | `/v1/auth/*` login, register, refresh, logout, API-key CRUD |
| `.../webservice/v1/feedstocks/` | `analysis.py`, `availability.py`, `usda/census.py`, `usda/survey.py`, `schemas.py` |
| `.../webservice/services/` | Query logic per domain; `_canonical_views.py` picks DB view vs SQLAlchemy fallback |
| `.../webservice/services/portal_auth.py` | Isolated portal auth: Google ID token check, allowlist, 2-role resolution, `biocirv_portal_token` cookie (`:1-381`) |
| `.../webservice/services/qc_ledger_service.py` | Stage 1 QC decisions: upsert into `qc_review_decision`, apply to record tables, seed CSV mirror (`record_stage1_decision` at line 499) |
| `.../webservice/services/gsheet_sync_service.py` | Stage 2 GSheet writeback for `/v1/qc/decisions/*/sync-gsheet` |
| `.../webservice/services/dashboard_loader.py` | Local-first then GCS dashboard asset loader with TTL and ETag cache |
| `.../webservice/v1/endpoints/qc_review.py` | All 15 `/v1/qc/*` routes |
| `src/ca_biositing/webservice/main.py` | Stale 2-line stub (`@app.get("/hello")`), NOT the real app. Do not import it. |

## How it works
```mermaid
flowchart LR
  Client --> CORS[CORSMiddleware]
  CORS --> Main[main.py app]
  Main --> Root[/ , /hello, /health/]
  Main --> V1[/v1 router]
  V1 --> H[/v1/health open]
  V1 --> Auth[/v1/auth open router]
  V1 --> Feed[/v1/feedstocks gated by get_current_user]
  Feed --> Svc[services/*]
  Svc --> Views[(ca_biositing views or tables via datamodels)]
```
- `main.py` builds `FastAPI(docs_url=/docs, redoc_url=/redoc, openapi_url=/openapi.json)`, adds `CORSMiddleware` from `config`, registers two exception handlers, then `include_router(v1_router.router)`.
- Auth is applied at router-include time for feedstocks (`dependencies=[Depends(get_current_user)]`), not per endpoint.
- Portal routes: `/v1/dashboards/*` is served by `main.py` (`_serve_authenticated_dashboard`, line 141). `/v1/qc/*` is included through `v1/router.py:36` with no router-level dependency, so each route declares its own portal dependency (`PortalAnalystDep` or `PortalAdminDep`). The `/v1/qc/github-issue` route declares none.
- Services are static-method classes (`AnalysisService`, `UsdaCensusService`, `UsdaSurveyService`, `AvailabilityService`, plus `auth_service` functions) called from endpoint bodies; endpoints only convert dicts into Pydantic response models.

## Interfaces
- Inputs: HTTP requests; DB via `ca_biositing.datamodels.database.get_session` / `get_engine` (see `architecture/datamodels-database-session`).
- Outputs: JSON; OpenAPI at `/openapi.json`, committed snapshot at `docs/api/openapi.json`.
- Callers: frontend (`architecture/frontend`), deployment (Cloud Run, see `architecture/webservice-deployment-cloud-run`).

## Gotchas
- Two files named `main.py`: the real one is `ca_biositing/webservice/main.py` inside the package. The top-level `src/ca_biositing/webservice/main.py` is an obsolete stub.
- `AGENTS.md` and the package README show example code (`test_main.py`, `tests/README.md`, `test_package.py`) that does not exist in the repo. Treat those docs as aspirational.
- Version pin drift: `pyproject.toml` and `pixi.toml` pin `fastapi>=0.111,<0.115`, while `AGENTS.md` says `>=0.115`. Code follows the pin.

## History
- `ab8fa6c` (2025-11-05) PEP 420 namespace split; `cd1b9bd` (2025-12-16) full CRUD namespace package; `815d5ee`/`1880284`/`f0ceacd`/`b4b4ccb` (Feb 2026) USDA census/survey and analysis endpoints (PRs #105, #106, #116, #117); `203b787` (2026-02-26) JWT auth (PR #139); `eb0c2a1` (2026-03-31) root redirect to /docs (PR #241); `e289fd1` (2026-04-03) API keys (PR #248); `00a7146` (2026-10-19) isolated portal OIDC auth and `/v1/qc` (PR #524); `7af19de` (PR #529) GCS REST adapter and Google Sign-In button; `811255f` (PR #532) admin list.

## Open questions
- Whether the stub `src/ca_biositing/webservice/main.py` should be deleted (inferred; confirm with maintainers, no importer found in this slice).

# Related Concepts
- [System overview (start here)](system-overview.md): Webservice is one of the three namespace packages (datamodels, pipeline, webservice) in the system
- [Full webservice endpoint table (36 routes)](webservice-endpoints.md): Full endpoint table for the routers described here
- [Datamodels DB engine and session management (database.py)](datamodels-database-session.md): get_session and get_engine are the DB seam used by every endpoint
- [/v1/qc API: routes, auth, request and response shapes](qc-review-api-v1-qc.md): the /v1/qc router in this package
- [BioCirV portal auth: Google OIDC, 2-role RBAC, isolated cookie](portal-oidc-auth-and-rbac.md): portal auth module
