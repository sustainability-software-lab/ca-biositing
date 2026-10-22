---
type: Architecture
title: Full webservice endpoint table (36 routes)
description: "Every HTTP route in the webservice with auth, query/path params, response model, backing view or table, and service function."
tags: [webservice, api, endpoints, reference]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:42Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/main.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/auth/router.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/endpoints/qc_review.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/feedstocks/analysis.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/feedstocks/availability.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/feedstocks/usda/census.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/feedstocks/usda/survey.py"]
sources: ["commit e41d00d", "commit 2bf84df", "docs/api/openapi.json", "https://github.com/sustainability-software-lab/ca-biositing/pull/197", "commit 00a7146", "commit 587c1cb", "commit 7af19de", "commit 811255f", "https://github.com/sustainability-software-lab/ca-biositing/pull/524"]
---

## Purpose
Authoritative route inventory, verified by reading each router file. Paths shown are full paths. Feedstock routes all require a valid credential (JWT, cookie, or X-API-Key). Auth = who can call it.

### Root and health (main.py)
| Method | Path | Auth | Params | Response | Backing | Service |
|---|---|---|---|---|---|---|
| GET | `/` | open | none | 307 redirect to `/docs` (hidden from schema) | none | none |
| GET | `/hello` | open | none | `{"message": "Hello, world"}` | none | none |
| GET | `/health` | open | none | `{"status":"healthy","database":"connected"}` or 503 `unhealthy` | `SELECT 1` via `get_engine()` | none |
| GET | `/v1/health` | open | none | `{"status":"ok"}` (no DB check) | none | none |

### Auth (`v1/auth/router.py`, prefix `/v1/auth`, open router)
| Method | Path | Auth | Params / body | Response | Backing | Service |
|---|---|---|---|---|---|---|
| POST | `/v1/auth/token` | username+password | form: `username`, `password` | `Token` {access_token, token_type}; also sets `access_token` cookie | `api_user` | `authenticate_user`, `create_access_token` |
| POST | `/v1/auth/register` | admin JWT only | JSON `UserCreate` | 201 `UserResponse` (409 on duplicate) | `api_user` | inline in router |
| POST | `/v1/auth/refresh` | any credential (JWT, cookie, or X-API-Key) | none | `Token`, resets cookie | `api_user` | `create_access_token` |
| POST | `/v1/auth/logout` | open | none | `{"message":"Logged out"}`, clears cookie | none | none |
| POST | `/v1/auth/api-keys` | admin JWT only | JSON `ApiKeyCreate` {name, api_user_id, rate_limit_per_minute=60} | 201 `ApiKeyCreateResponse` with `raw_key` shown once (404 if owner missing) | `api_key` | `generate_api_key` |
| GET | `/v1/auth/api-keys` | admin JWT only | query `api_user_id`?, `limit` 1-1000 default 100, `offset` default 0 | `List[ApiKeyResponse]` (no hash) | `api_key` | inline |
| DELETE | `/v1/auth/api-keys/{key_id}` | admin JWT only | path `key_id` | `{"message":"API key revoked"}` (soft: is_active=false) | `api_key` | inline |
| PATCH | `/v1/auth/api-keys/{key_id}` | admin JWT only | JSON `ApiKeyUpdate` {name?, rate_limit_per_minute?}, extra fields = 422 | `ApiKeyResponse` | `api_key` | inline |

### Feedstocks data (all gated by `get_current_user`, prefix `/v1/feedstocks`)
**Analysis** (`v1/feedstocks/analysis.py`, prefix `/analysis`)
| Method | Path suffix | Params | Response | Backing view | Service fn |
|---|---|---|---|---|---|
| GET | `/resources` | none | `DiscoveryResponse` | `analysis_data_view` | `AnalysisService.list_resources` |
| GET | `/geoids` | none | `DiscoveryResponse` (currently always empty) | `analysis_data_view` | `AnalysisService.list_geoids` |
| GET | `/parameters` | none | `DiscoveryResponse` | `analysis_data_view` | `AnalysisService.list_parameters` |
| GET | `/resources/{resource}/geoid/{geoid}/parameters/{parameter}` | path only | `AnalysisDataResponse` | `Resource` + `analysis_data_view` | `AnalysisService.get_by_resource` |
| GET | `/resources/{resource}/geoid/{geoid}/parameters` | path only | `AnalysisListResponse` | `Resource` + `analysis_data_view` | `AnalysisService.list_by_resource` |

**Availability** (`v1/feedstocks/availability.py`, prefix `/availability`)
| Method | Path suffix | Params | Response | Backing | Service fn |
|---|---|---|---|---|---|
| GET | `/resources` | none | `DiscoveryResponse` | `resource` JOIN `resource_availability` | `AvailabilityService.list_resources` |
| GET | `/geoids` | none | `DiscoveryResponse` | `resource_availability` | `AvailabilityService.list_geoids` |
| GET | `/resources/{resource}/geoid/{geoid}` | path only | `AvailabilityResponse` {from_month, to_month} | `resource` + `resource_availability` | `AvailabilityService.get_by_resource` |

**USDA census** (`v1/feedstocks/usda/census.py`, prefix `/usda/census`)
| Method | Path suffix | Params | Response | Backing | Service fn |
|---|---|---|---|---|---|
| GET | `/crops` | none | `DiscoveryResponse` | `usda_census_view` | `UsdaCensusService.list_crops` |
| GET | `/resources` | none | `DiscoveryResponse` | `usda_census_view` + `usda_resource_commodity_view` | `UsdaCensusService.list_resources` |
| GET | `/geoids` | none | `DiscoveryResponse` | `usda_census_view` | `UsdaCensusService.list_geoids` |
| GET | `/parameters` | none | `DiscoveryResponse` | `usda_census_view` | `UsdaCensusService.list_parameters` |
| GET | `/crops/{crop}/geoid/{geoid}/parameters/{parameter}` | path only | `CensusDataResponse` | `UsdaCommodity` + `usda_census_view` | `get_by_crop` |
| GET | `/resources/{resource}/geoid/{geoid}/parameters/{parameter}` | path only | `CensusDataResponse` | `Resource` + `ResourceUsdaCommodityMap` + `usda_census_view` | `get_by_resource` |
| GET | `/crops/{crop}/geoid/{geoid}/parameters` | path only | `CensusListResponse` | `UsdaCommodity` + `usda_census_view` | `list_by_crop` |
| GET | `/resources/{resource}/geoid/{geoid}/parameters` | path only | `CensusListResponse` | as above | `list_by_resource` |

**USDA survey** (`v1/feedstocks/usda/survey.py`, prefix `/usda/survey`): same 8-route shape as census, with `usda_survey_view`, response models `SurveyDataResponse` / `SurveyListResponse` (adds survey_program_id, survey_period, reference_month, seasonal_flag). Discovery routes are `/crops`, `/resources`, `/geoids`, `/parameters`. Service class `UsdaSurveyService`.

### Totals
36 routes in the root/health, auth and feedstocks families (4 root/health, 8 auth, 24 feedstocks data: 5 analysis + 3 availability + 8 census + 8 survey). The BioCirV portal routes added in Oct 2026 are listed separately below. Verify with `docs/api/openapi.json` or `GET /openapi.json`.

### Portal, dashboard and QC routes (added in #524, #526)
These use the isolated `biocirv_portal_token` cookie or a portal JWT in `Authorization: Bearer`. They never read `access_token` or X-API-Key. Details: `architecture/portal-oidc-auth-and-rbac`, `architecture/qc-review-api-v1-qc`, `architecture/dashboard-snapshot-loader-gcs`.

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/v1/dashboards`, `/v1/dashboards/{subpath:path}` | analyst or admin; admin only for `audit/*` and `db_environment_drift_dashboard.html` | Unauthenticated requests get 302 to `/v1/dashboards/login.html?next=...` (`main.py:141-185`) |
| GET | `/dashboards`, `/dashboards/{subpath:path}` | open | 307 redirect to `/v1/dashboards/...` (`main.py:188-209`) |
| GET | `/v1/qc/auth/config` | open | Public Google client id and allowed domains |
| POST | `/v1/qc/auth/google` | Google ID token in body (`id_token` or `credential`) | Sets `biocirv_portal_token` |
| POST | `/v1/qc/auth/dev-login` | local development only | Sets cookie |
| GET | `/v1/qc/auth/me` | analyst | Identity, role, assigned open count |
| POST | `/v1/qc/auth/logout` | open | Clears cookie |
| GET | `/v1/qc/decisions` | analyst | Filters: assigned_to, status, decision_status, flag_type, resource_name, analysis_type, parameter_name, synced_to_gsheet |
| POST | `/v1/qc/decisions` | analyst | Stage 1 upsert |
| POST | `/v1/qc/tray-to-workbench` | analyst | Creates open flags from the Selection tray |
| PATCH | `/v1/qc/decisions/{decision_id}/assign` | analyst | Assign or unassign |
| GET | `/v1/qc/summary` | analyst | Queue counts |
| GET | `/v1/qc/export.csv` | analyst | CSV of filtered ledger rows |
| POST | `/v1/qc/decisions/{decision_id}/sync-gsheet` | admin | Stage 2, single |
| POST | `/v1/qc/decisions/sync-gsheet-batch` | admin | Stage 2, batch |
| POST | `/v1/qc/github-issue` | see `architecture/qc-review-api-v1-qc` | Files a GitHub issue from the Report a Bug modal |

`qc_review.py` registers 15 routes under `/v1/qc`. `main.py` adds the 2 dashboard routes and 2 legacy redirects. The Product 2/3 dashboard client also calls routes that do not exist (see `bugs/dashboard-client-calls-missing-qc-routes`).

## Gotchas
- Path parameters with spaces (e.g. `almond hulls`) are passed raw; the services normalize case, spaces and underscores.
- Analysis parameter lookup returns the first observation only (ordered by id); `list_by_resource` returns all.
- `ParameterErrorException` (422) is defined but never raised by any endpoint or service.

# Related Concepts
- [Webservice package layout and app factory](webservice-overview.md): Router wiring that produces these paths
- [JWT login, cookie transport, and refresh in the webservice](webservice-auth-jwt.md): Explains the credential types referenced in the Auth column
- [Per-client X-API-Key auth with rate limiting](webservice-api-keys.md): Admin key-management endpoints and X-API-Key path
- [Service layer behind feedstock queries and canonical view selection](webservice-usda-query-services.md): Service functions and view selection behind feedstock routes
- [System overview (start here)](system-overview.md): Hub for the overall system
- [/v1/qc API: routes, auth, request and response shapes](qc-review-api-v1-qc.md): full /v1/qc route detail
- [BioCirV portal auth: Google OIDC, 2-role RBAC, isolated cookie](portal-oidc-auth-and-rbac.md): auth used by the portal routes
