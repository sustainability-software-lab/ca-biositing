---
type: Decision
title: Why the webservice has both JWT users and per-client API keys
description: "Decision record: JWT for browser and admin sessions, hashed revocable API keys with rate limits for consumers. Rejected alternatives and trade-offs."
tags: [webservice, auth, decision]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:16Z" }
status: stable
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/dependencies.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/auth_service.py"]
sources: ["commit 203b787", "commit e289fd1", "https://github.com/sustainability-software-lab/ca-biositing/pull/139", "https://github.com/sustainability-software-lab/ca-biositing/pull/248"]
governance: context
---

## Decision
Two credential types. (1) JWT (Bearer or HttpOnly cookie) for named users and the SPA, issued from username/password. (2) `X-API-Key` for machine or partner clients, each key individually revocable and rate limited.

## Context from history
- PR #139 (`203b787`, Feb 2026) added JWT only, protecting all `/v1/feedstocks/*` routes. Tokens go in both JSON body and cookie "to support API clients and browser SPAs".
- PR #248 (`e289fd1`, Apr 2026) added keys so "each consumer (frontend, external researcher, partner) gets an individually revocable key with per-key sliding-window rate limiting". Existing JWT/cookie auth was left unchanged.

## Alternatives visible in the code
- Keys only, no JWT: rejected implicitly; JWT is still needed for admin login and the SPA cookie.
- Keys stored in plaintext or reversible encryption: rejected. Only Argon2 hashes and an 8-char prefix are stored, and the raw key is returned once.
- Keys for admin ops too: rejected by design (see `requirements/webservice-admin-endpoints-jwt-only`).
- Server-side sessions: not used. Stateless JWT is verified per request.

## Trade-offs
- Stateless JWT cannot be revoked before `exp` (30 min). Logout only clears the cookie.
- Fixed-window rate limit is simple and DB-backed but allows boundary bursts and only applies to keys.
- Prefix lookup plus Argon2 costs one hash verify per request. Acceptable for this traffic level (inferred).

## Open questions
- Whether the frontend should move from cookie JWT to keys or stay on cookies (not determinable from this slice; confirm with frontend owners).

# Related Concepts
- [Per-client X-API-Key auth with rate limiting](../architecture/webservice-api-keys.md): Implementation of the key half of this decision
- [JWT login, cookie transport, and refresh in the webservice](../architecture/webservice-auth-jwt.md): Implementation of the JWT half of this decision
- [Admin and key-management routes must stay JWT-only](../requirements/webservice-admin-endpoints-jwt-only.md): Constraint that follows from the split
