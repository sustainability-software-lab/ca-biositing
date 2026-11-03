---
type: Architecture
title: "JWT login, cookie transport, and refresh in the webservice"
description: "How /v1/auth/token issues HS256 JWTs, how Bearer or access_token cookie is resolved, and why logout does not revoke tokens."
tags: [webservice, auth, jwt, security]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:47Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/v1/auth/router.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/auth_service.py", "src/ca_biositing/webservice/ca_biositing/webservice/dependencies.py", "src/ca_biositing/webservice/ca_biositing/webservice/config.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/portal_auth.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/auth/"]
sources: ["commit 203b787", "commit f8ab620", "https://github.com/sustainability-software-lab/ca-biositing/pull/139", "https://github.com/sustainability-software-lab/ca-biositing/pull/141", "deployment/cloud/gcp/infrastructure/cloud_run.py", "commit 00a7146"]
---

## Purpose
User authentication for the API: username/password login issues a signed JWT (`sub` = username). The token is accepted from `Authorization: Bearer` or the HTTP-only `access_token` cookie.

## Key files
| Path | Role |
|---|---|
| `.../webservice/v1/auth/router.py:55` | `login` (POST /token), `refresh`, `logout`, `_set_access_cookie` |
| `.../webservice/services/auth_service.py` | Argon2 hashing (`pwdlib`), `authenticate_user` with dummy-hash timing guard, `create_access_token`, `decode_access_token` (PyJWT) |
| `.../webservice/dependencies.py` | `_resolve_jwt_user`, `get_jwt_user`, `get_current_user`, `get_current_admin_user` |
| `.../webservice/config.py` | `jwt_secret_key` (min 32 chars, dev default), `jwt_algorithm` HS256, `jwt_expire_minutes` 30, `jwt_cookie_secure` false |
| `src/ca_biositing/datamodels/.../models/auth/` | `ApiUser` table (username, hashed_password, is_admin, disabled) |

## How it works
```mermaid
sequenceDiagram
  Client->>/v1/auth/token: POST form username,password
  /v1/auth/token->>DB: select ApiUser by username
  /v1/auth/token-->>Client: 200 {access_token} + Set-Cookie access_token (HttpOnly, SameSite=Lax)
  Client->>/v1/feedstocks/*: Authorization Bearer (or cookie)
  get_current_user->>decode: verify HS256 signature + exp
  get_current_user->>DB: ApiUser by sub; reject if disabled
```
- Login failures (wrong password, unknown user, disabled user) all return the same 401 `Incorrect username or password`. Unknown users still run an Argon2 verify against `DUMMY_HASH`.
- Token lifetime is `API_JWT_EXPIRE_MINUTES` (30). No server-side session; every request re-reads the user row, so disabling a user takes effect immediately for JWTs.
- `refresh` re-issues a token for the current user and rewrites the cookie.
- `logout` only deletes the cookie. The JWT stays valid until `exp`.

## Interfaces
- Input: form-encoded login body (`OAuth2PasswordRequestForm`), Bearer header, or cookie.
- Output: `Token` {access_token, token_type="bearer"}; `Set-Cookie: access_token`.
- Cookie `secure` flag comes from `API_JWT_COOKIE_SECURE`; Cloud Run sets it to `true` (`deployment/cloud/gcp/infrastructure/cloud_run.py`).

## Gotchas
- Portal auth (`biocirv_portal_token`, `/v1/qc/*`, `/v1/dashboards/*`) is a separate system. `decode_portal_token` rejects an `access_token` JWT because it lacks a portal `email` and `role` claim (`portal_auth.py:240-244`). It shares only the signing key. See `architecture/portal-oidc-auth-and-rbac`.
- An invalid or expired Bearer token returns 401 even if a valid X-API-Key is also sent, because JWT is checked first and raises on a bad token.
- `/v1/auth/refresh` depends on `CurrentUserDep`, which also accepts X-API-Key. So an API key can mint a JWT (inferred to be unintended; confirm with the auth owner).
- Cookie auth applies to all feedstock GET routes too, so browser clients are authenticated by cookie without a CSRF token. SameSite=Lax is the only mitigation (inferred risk; confirm).
- The default `jwt_secret_key` is a dev value; main.py logs a warning when it is in use. Production must set `API_JWT_SECRET_KEY` (GCP Secret Manager secret `jwt-secret`).
- Refresh and logout give no revocation. Rotating the secret is the only global kill switch.

## History
- `203b787` (2026-02-26), PR #139: introduced JWT auth, ApiUser model + migration `eacbc6544a10`, Argon2, dual Bearer/cookie transport, and `scripts/create_admin.py`. Commit message says the signing key is stored as GCP secret `biocirv-staging-jwt-secret-key`.
- `f8ab620` (PR #141) fixed an observation query mismatch in the analysis path; not auth-related.

## Open questions
- Should `/v1/auth/refresh` accept X-API-Key? (inferred gap)
- Is there a plan for token revocation or a shorter cookie lifetime?

# Related Concepts
- [Per-client X-API-Key auth with rate limiting](webservice-api-keys.md): Second credential type; resolved in the same get_current_user chain
- [Full webservice endpoint table (36 routes)](webservice-endpoints.md): Lists which routes use each credential
- [Auth tables: api_user (JWT login) and api_key (hashed keys with DB rate limit)](datamodels-auth.md): ApiUser model and password hash storage live in datamodels
- [Webservice deployment on GCP Cloud Run](webservice-deployment-cloud-run.md): Prod secret injection and secure cookie flag
- [BioCirV portal auth: Google OIDC, 2-role RBAC, isolated cookie](portal-oidc-auth-and-rbac.md): the parallel portal JWT system
