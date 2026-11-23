---
type: Architecture
title: "BioCirV portal auth: Google OIDC, 2-role RBAC, isolated cookie"
description: "How /v1/qc and /v1/dashboards authenticate: Google ID token or portal JWT, domain and email allowlist, analyst vs admin roles, and why it never touches access_token or X-API-Key."
tags: [auth, portal, oidc, rbac, webservice]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:05Z" }
status: stable
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/services/portal_auth.py", "src/ca_biositing/webservice/ca_biositing/webservice/config.py", "src/ca_biositing/webservice/ca_biositing/webservice/main.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/endpoints/qc_review.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/dashboard_loader.py", "tests/webservice/test_portal_auth_and_rbac.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/524", "https://github.com/sustainability-software-lab/ca-biositing/pull/529", "https://github.com/sustainability-software-lab/ca-biositing/pull/532", "commit 00a7146", "commit 811255f"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
A second auth system for the internal BioCirV dashboards and QC API. It is isolated from the feedstock API. It has its own cookie, its own dependencies, and its own role model.

## Key files
| path:line | role |
|---|---|
| services/portal_auth.py:35 | `PORTAL_COOKIE_NAME = "biocirv_portal_token"` |
| services/portal_auth.py:38-57 | `PortalUser` (email, role analyst/admin, auth_mode) |
| services/portal_auth.py:64-91 | `is_email_allowed`: admin list, email list, or domain match |
| services/portal_auth.py:94-106 | `resolve_portal_role`: admin if in admin list, else analyst |
| services/portal_auth.py:140-197 | `verify_google_id_token`: `google.oauth2.id_token.verify_oauth2_token` with audience `google_client_id` |
| services/portal_auth.py:200-256 | `create_portal_token` (HS256, `token_use=biocirv_portal`, `exp`) and `decode_portal_token` (requires email and role claim) |
| services/portal_auth.py:292-337 | `get_optional_portal_user`: resolution order below |
| services/portal_auth.py:340-381 | `require_portal_analyst`, `require_portal_admin`, `PortalAnalystDep`, `PortalAdminDep` |
| config.py:68-126 | portal and dashboard settings (see `architecture/webservice-config`) |
| main.py:141-173 | `_serve_authenticated_dashboard`: login exemption and admin-only subpaths |

## How it works
Resolution order in `get_optional_portal_user`:
1. `biocirv_portal_token` cookie, decoded and re-checked against the allowlist.
2. `X-Auth-Request-Email` header. Returns a user with `auth_mode=oauth2_proxy`.
3. `Authorization: Bearer <portal JWT>`.
4. If `require_dashboard_auth` is false, a fixed dev analyst (`auth_mode=disabled`).
5. None, which means 401 for `/v1/qc` and a 302 to login for dashboards.

Login flow: the built-in `login.html` (`services/dashboard_loader.py` `BUILTIN_LOGIN_HTML`) loads Google Identity Services, reads `/v1/qc/auth/config` for the client id, then POSTs the credential to `/v1/qc/auth/google`. The server sets the cookie (`httponly`, `samesite=lax`, `secure` from `API_JWT_COOKIE_SECURE`, max age `jwt_expire_minutes`).

Roles: `admin` if the email is in `dashboard_admin_emails`, otherwise `analyst`. Admin accounts must also pass the allowlist (`is_email_allowed` includes the admin list). Admin-only: Stage 2 sync routes, `/v1/dashboards/audit/*`, and `db_environment_drift_dashboard.html`.

Admin configuration: three admin accounts are hardcoded in `config.py:91-102` (up from one before #532). They can be replaced with `API_DASHBOARD_ADMIN_EMAILS`. Addresses are deliberately not written in this concept.

## Isolation
- Does not import `dependencies.py`, `ApiUser`, or `auth_service` (test `test_calbioscape_cookie_and_endpoints_remain_isolated`, `tests/webservice/test_portal_auth_and_rbac.py:87`).
- A CalBioScape `access_token` cookie is ignored by `get_optional_portal_user`. A JWT without email and role claims is rejected (`portal_auth.py:240-244`).
- Shares only the signing key `API_JWT_SECRET_KEY` with the API JWTs.
- `test_webservice_has_zero_pipeline_imports` (line 385) keeps the webservice free of `ca_biositing.pipeline` imports.

## Gotchas
- Token audience: when `google_client_id` is empty, `audience` is `None` (`portal_auth.py:168`) and the ID token audience is not checked. Any Google ID token with a verified allowlisted email passes. Set `API_GOOGLE_CLIENT_ID` in every deployed environment.
- Verifier fallback: if `google.auth` cannot be imported, `verify_oauth2_token` raises `ValueError`, which surfaces as 401 (`portal_auth.py:29-30`). `google-auth` is present in the webservice pixi env (`pixi.lock`), though it is not listed in the webservice `pyproject.toml` (inferred from the lock).
- Dashboard requests without a session get a 302 to login regardless of `Accept` header. The README says API clients get 401; the code does not do that.

## History
- 00a7146 (2026-10-19, PR #524, Peter Smith): portal auth, RBAC, `/v1/qc`.
- 7af19de (PR #529): accepts the Google Sign-In `credential` field; adds REST GCS adapter.
- 811255f (PR #532): admin defaults grow to three.

## Open questions
- Who should be able to add or remove admins without a code change (inferred: nobody, beyond the env var).

# Related Concepts
- [JWT login, cookie transport, and refresh in the webservice](webservice-auth-jwt.md): the separate JWT login this sits beside
- [Per-client X-API-Key auth with rate limiting](webservice-api-keys.md): X-API-Key is not accepted here
- [Why the webservice has both JWT users and per-client API keys](../decisions/webservice-jwt-and-api-key-split.md): same isolation reasoning
- [Webservice settings and API_ environment variables](webservice-config.md): setting names and defaults
