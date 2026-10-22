---
type: Decision
title: "History: webservice auth, API keys, and DB hardening (2026)"
description: "Chronology of JWT auth (#139), per-client API keys with rate limiting (#248), Prefect UI oauth2-proxy, and the May 2026 Postgres hardening commits."
tags: [webservice, auth, api-keys, security, history]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:49Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/services/portal_auth.py", "src/ca_biositing/webservice/ca_biositing/webservice/config.py"]
sources: ["commit 203b787", "commit e289fd1", "commit bbaf938", "commit dffbaba", "commit e74c5b8", "commit 1189a05", "https://github.com/sustainability-software-lab/ca-biositing/pull/248", "https://github.com/sustainability-software-lab/ca-biositing/pull/524", "https://github.com/sustainability-software-lab/ca-biositing/pull/529", "https://github.com/sustainability-software-lab/ca-biositing/pull/532"]
---

## Purpose
Dates each security control so a reader can find which PR introduced it.

## Key files
| Path | Role |
|---|---|
| src/ca_biositing/webservice/ca_biositing/webservice | FastAPI service where auth lives (webservice churn: 13 Vraj Rajpura, 7 Don Setiawan) |
| SECURITY.md | Security policy added in 7a27ee8 (PR #253) |
| alembic/versions_old/b3f2d1c8e9a0_add_api_key_table.py | API key table migration |
| alembic/versions_old/eacbc6544a10_add_api_user_table.py | API user table migration |

## How it works
- 203b787 (PR #139, Don Setiawan, 2026-02-26): JWT authentication on the webservice.
- 72439c5 / f3ca6dd / 09787cd (PRs #221, #222, #223, 2026-03-27): oauth2-proxy added to local Compose and Cloud Run to front the Prefect UI.
- e289fd1 (PR #248, Tyler Huntington, 2026-04-03): per-client API keys with per-key rate limiting; bbaf938 (PR #257) rejects unknown PATCH fields with 422.
- 00a7146 (PR #524, Peter Smith, 2026-10-19): isolated BioCirV portal OIDC auth (`biocirv_portal_token`), 2-role RBAC (analyst/admin), and the `/v1/qc` API. Separate from JWT and API keys. See `architecture/portal-oidc-auth-and-rbac`.
- 7af19de (PR #529, 2026-10-19): google-auth REST GCS adapter for dashboards and the Google Sign-In button.
- 811255f (PR #532, 2026-10-21): dashboard admin defaults grow from 1 to 3 accounts (`config.py:91-102`).
- 1189a05 (PR #129, 2026-02-23): pg_trgm, unaccent, btree_gin extensions.
- dffbaba (PR #363) and e74c5b8 (PR #366), 2026-05-18: Postgres security hardening.
- IAM fixes for the deployer service account are covered in facts/history-gcp-staging-deployment.

## Interfaces
Inputs: Authorization headers or API keys. Callers: v1 endpoints under webservice/v1/endpoints.

## Gotchas
- Migrations for API keys and users were squashed or moved into the archive; check alembic/versions_old when debugging old revisions.
- Rate limiting is per key, so unauthenticated paths behave differently.

## History
Listed above with SHAs and PRs.

## Open questions
- Whether JWT and API keys are both active paths (inferred from both commits; confirm in webservice code).

# Related Concepts
- [JWT login, cookie transport, and refresh in the webservice](../architecture/webservice-auth-jwt.md): current auth design (id prefix architecture/webservice-*)
- [History: GCP staging and production deployment automation (Feb to Apr 2026)](history-gcp-staging-deployment.md): IAM fixes that surround these controls
- [Project history eras (2025-08 to 2026-10)](history-eras.md): E6 and E7 eras
- [BioCirV portal auth: Google OIDC, 2-role RBAC, isolated cookie](../architecture/portal-oidc-auth-and-rbac.md): current design of portal auth
