---
type: Architecture
title: "Auth tables: api_user (JWT login) and api_key (hashed keys with DB rate limit)"
description: "ApiUser and ApiKey models; raw keys never stored, only an Argon2 hash plus a plaintext 8-char prefix; rate-limit window state lives on the key row."
tags: [datamodels, auth, api-key, jwt, rate-limit, argon2]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:26:58Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/auth/api_key.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/auth/api_user.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/auth_service.py", "src/ca_biositing/webservice/ca_biositing/webservice/dependencies.py"]
sources: ["commit e289fd1", "commit 203b787", "commit db578ad", "https://github.com/sustainability-software-lab/ca-biositing/pull/248", "https://github.com/sustainability-software-lab/ca-biositing/pull/139", "https://github.com/sustainability-software-lab/ca-biositing/pull/340", "alembic/versions/0003_core_tables.py"]
governance: constraint
stale_after: "2026-11-16"
---

## Purpose
Persistence for webservice authentication: password-based users issuing JWTs, and per-client API keys.

## Key files
| Path:line | Role |
|---|---|
| `models/auth/api_user.py:12` | `ApiUser` table `api_user`: `username` (unique, indexed), `hashed_password`, `email`, `full_name`, `is_admin`, `disabled`, timestamps with `server_default=CURRENT_TIMESTAMP` and an ORM-side `onupdate` |
| `models/auth/api_key.py:12` | `ApiKey` table `api_key`: `api_user_id` FK `api_user.id` (indexed), `name`, `key_prefix` (indexed, first 8 chars), `key_hash` (unique), `is_active`, `rate_limit_per_minute` (default 60), `rate_window_start` (timestamptz), `rate_window_count`, `last_used_at` (timestamptz) |
| `webservice/.../services/auth_service.py:23` | `PasswordHash.recommended()` (Argon2) |
| `webservice/.../services/auth_service.py:106-116` | `generate_api_key()` returns `(raw, prefix, hash)`; raw shown once |
| `webservice/.../services/auth_service.py:119-146` | `validate_api_key()`: lookup by prefix, then hash verify; dummy hash on miss |
| `webservice/.../services/auth_service.py:148-163` | `check_and_increment_rate_limit()`, uses `with_for_update()` at `:163` |
| `webservice/.../dependencies.py:45-127` | JWT and API-key resolution for FastAPI deps |

## How it works
1. Key creation: generate raw key, store prefix and Argon2 hash, return raw key once.
2. Request: match `key_prefix`, verify raw key against `key_hash`, then increment the fixed 60-second window counter under row lock. Window resets when 60 s have elapsed since `rate_window_start`.

## Interfaces
- Input: raw key (header) or username/password (JWT login).
- Output: `ApiUser` / `ApiKey` ORM rows; JWT access token.

## Gotchas
- The raw key must never be persisted (docstring, `api_key.py:13-16`). Keep it that way in any new endpoint.
- Fixed window allows roughly 2N requests in a short burst at a window boundary (documented in `api_key.py:19-23`).
- `updated_at` `onupdate` is SQLAlchemy-side; raw SQL updates will not bump it (inferred).
- `ApiUser` does not use `BaseEntity` on purpose (`api_user.py:18-21`).
- Migrations: the `api_key` table is created inside the squashed `alembic/versions/0003_core_tables.py` (squash in `db578ad`, PR #340). The original standalone migration `b3f2d1c8e9a0_add_api_key_table.py` (from `e289fd1`, PR #248) now lives under `alembic/versions_old/`. `api_user` is in `versions_old/eacbc6544a10_add_api_user_table.py`.

## History
- `203b787` (PR #139): JWT auth for the webservice (added `ApiUser`).
- `e289fd1` (PR #248, 2026-04-03): per-client API keys with DB-based rate limiting.
- `db578ad` (PR #340): squashed migrations.

## Open questions
- Whether the rate limit should move to Redis if the instance count grows (docstring says acceptable for research API).

# Related Concepts
- [JWT login, cookie transport, and refresh in the webservice](webservice-auth-jwt.md): webservice consumes these models (prefix-level ID; confirm exact ID in webservice slice)
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](migrations.md): api_key/api_user table history across squashed and old migrations
- [Datamodels base mixins (BaseEntity, LookupBase, Aim1/Aim2RecordBase)](datamodels-base.md): ApiUser intentionally departs from the BaseEntity pattern
