---
type: Requirement
title: Admin and key-management routes must stay JWT-only
description: "Any new admin endpoint must depend on get_jwt_user or get_current_admin_user, never get_current_user, so a leaked X-API-Key cannot manage keys or users."
tags: [webservice, auth, security, constraint]
generated: { by: "claude-code:claude-opus-5-5", at: "2026-10-22T21:29:11Z" }
status: stable
governance: constraint
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/dependencies.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/auth/router.py", "tests/webservice/v1/test_api_keys.py"]
sources: ["commit e289fd1", "commit 203b787", "https://github.com/sustainability-software-lab/ca-biositing/pull/524"]
---

## Rule
Admin operations (user registration, API key create/list/update/revoke) must authenticate with a JWT only, through `AdminUserDep` (which wraps `get_jwt_user`). `X-API-Key` must not be accepted on these routes.

## Why
`dependencies.py` documents the reason: API keys are for data consumers; a leaked key must not be able to manage other keys even if the owning account is an admin. `get_current_admin_user` therefore excludes API-key auth on purpose.

## Where it is enforced
- `src/ca_biositing/webservice/ca_biositing/webservice/dependencies.py` (`get_jwt_user`, `get_current_admin_user`, `AdminUserDep`).
- `src/ca_biositing/webservice/ca_biositing/webservice/v1/auth/router.py` (`register`, `create_api_key`, `list_api_keys`, `revoke_api_key`, `update_api_key`).
- Tests: `tests/webservice/v1/test_api_keys.py` (`test_valid_api_key_blocked_from_admin_endpoints` expects 401).

## Do
- Use `AdminUserDep` for any new admin route.

## Do not
- Do not use `CurrentUserDep` on admin routes. That dependency accepts API keys.
- Do not add `X-API-Key` header parameters to admin routes.

## Caveat
`/v1/auth/refresh` uses `CurrentUserDep` and does accept keys. That is not an admin route, but it lets a key obtain a JWT for its owner. Confirm before relying on this boundary.

## Scope (added 2026-10-22)
Since #524 the portal admin routes under `/v1/qc` (for example the Stage 2 sync) depend on `require_portal_admin` (`v1/endpoints/qc_review.py:52`), a separate portal RBAC that never reads `X-API-Key`. They do not use `AdminUserDep`. The intent (an API key can never reach an admin action) still holds, but the literal rule above covers only the `/v1/auth` admin routes. Whether portal admin routes should follow this rule or their own is an open question for the maintainers.

# Related Concepts
- [Per-client X-API-Key auth with rate limiting](../architecture/webservice-api-keys.md): Explains why key routes reject API keys
- [JWT login, cookie transport, and refresh in the webservice](../architecture/webservice-auth-jwt.md): Defines the JWT dependency this rule relies on
- [Why the webservice has both JWT users and per-client API keys](../decisions/webservice-jwt-and-api-key-split.md): Decision record that this constraint came from
- [BioCirV portal auth: Google OIDC, 2-role RBAC, isolated cookie](../architecture/portal-oidc-auth-and-rbac.md): Portal admin routes use a separate RBAC
