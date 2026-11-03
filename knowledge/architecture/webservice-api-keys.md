---
type: Architecture
title: Per-client X-API-Key auth with rate limiting
description: "How X-API-Key is validated (prefix lookup plus Argon2), how the fixed 60s window rate limit works, and which endpoints reject keys."
tags: [webservice, auth, api-key, rate-limit]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:48Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/services/auth_service.py", "src/ca_biositing/webservice/ca_biositing/webservice/dependencies.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/auth/router.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/auth/schemas.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/auth/api_key.py", "tests/webservice/v1/test_api_keys.py"]
sources: ["commit e289fd1", "commit bbaf938", "https://github.com/sustainability-software-lab/ca-biositing/pull/248", "https://github.com/sustainability-software-lab/ca-biositing/pull/257", "commit 00a7146"]
---

## Purpose
Lets each consumer (frontend, researcher, partner) hold an individually revocable key. Raw key is shown once at creation; only an Argon2 hash and an 8-character prefix are stored.

## Key files
| Path | Role |
|---|---|
| `.../webservice/services/auth_service.py` | `generate_api_key` (token_urlsafe 32, prefix = first 8 chars), `validate_api_key`, `check_and_increment_rate_limit` |
| `.../webservice/dependencies.py` | `get_current_user` Path 3 (X-API-Key header); `get_jwt_user` and `get_current_admin_user` exclude keys |
| `.../webservice/v1/auth/router.py` | Admin CRUD: POST/GET `/v1/auth/api-keys`, DELETE/PATCH `/v1/auth/api-keys/{key_id}` |
| `.../webservice/v1/auth/schemas.py` | `ApiKeyCreate`, `ApiKeyCreateResponse` (only place `raw_key` appears), `ApiKeyResponse`, `ApiKeyUpdate` (extra=forbid) |
| `src/ca_biositing/datamodels/.../models/auth/api_key.py` | `ApiKey` table: api_user_id, key_prefix, key_hash, is_active, rate_limit_per_minute, rate_window_start, rate_window_count, last_used_at |

## How it works
1. Client sends `X-API-Key: <raw>` (only if no JWT Bearer or cookie was present).
2. Length must be 8 to 128 chars. Candidates are `ApiKey` rows with the same prefix and `is_active`.
3. Each candidate is verified with Argon2. If no candidates exist, a dummy verify still runs (timing guard).
4. Owner `ApiUser` must exist and not be disabled.
5. `check_and_increment_rate_limit`: `SELECT ... FOR UPDATE` on the key row. Fixed 60-second window. Over limit gives 429 with `Retry-After: 60`. `rate_limit_per_minute = 0` means unlimited, but `last_used_at` is still updated.

## Interfaces
- Accepted on: every `/v1/feedstocks/*` route, and `/v1/auth/refresh`.
- Rejected on: `/v1/auth/register` and all `/v1/auth/api-keys*` routes (JWT-only admin dependency).
- Not accepted on `/v1/qc/*` or `/v1/dashboards/*`. Portal auth reads only the portal cookie, the `X-Auth-Request-Email` header, or a portal JWT in Bearer (`portal_auth.py:292-337`).
- Errors: 401 invalid/revoked/disabled, 429 rate limit.

## Gotchas
- Revocation is soft (`DELETE` sets `is_active=false`). Re-activation is not possible through the API; issue a new key.
- The rate limiter applies only to the X-API-Key path. JWT and cookie requests are not limited.
- The row lock makes the counter correct on Postgres. On SQLite (unit tests) `FOR UPDATE` is not enforced; do not rely on tests for concurrency.
- Fixed window allows roughly 2N requests across a window boundary (documented in the docstring as acceptable).
- `PATCH` only changes name and rate limit. Sending `is_active` returns 422 (commit `bbaf938`, PR #257).

## History
- `e289fd1` (2026-04-03), PR #248 by Tyler Huntington: introduced X-API-Key, admin key endpoints, rate limiting, migration with `down_revision=eacbc6544a10`, 14 tests in `tests/webservice/v1/test_api_keys.py`.
- `bbaf938` (2026-04-07), PR #257: strict PATCH body.

## Open questions
- Should keys be allowed to call `/v1/auth/refresh`? See `architecture/webservice-auth-jwt`.

# Related Concepts
- [JWT login, cookie transport, and refresh in the webservice](webservice-auth-jwt.md): Same get_current_user dependency resolves JWT first, then X-API-Key
- [Why the webservice has both JWT users and per-client API keys](../decisions/webservice-jwt-and-api-key-split.md): Rationale for keeping key management JWT-only
- [Auth tables: api_user (JWT login) and api_key (hashed keys with DB rate limit)](datamodels-auth.md): ApiKey table definition and migration history
- [BioCirV portal auth: Google OIDC, 2-role RBAC, isolated cookie](portal-oidc-auth-and-rbac.md): portal routes do not accept X-API-Key
