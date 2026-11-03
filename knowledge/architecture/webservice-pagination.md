---
type: Architecture
title: "Pagination: unused PaginationDep versus per-route limit/offset"
description: Only the admin API-key list paginates (limit/offset). The shared pagination_params dependency exists but no route uses it; data endpoints return full lists.
tags: [webservice, pagination, api]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:18Z" }
status: stable
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/dependencies.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/auth/router.py"]
sources: ["commit e289fd1", "commit e41d00d"]
governance: context
---

## Purpose
Documents what pagination the API actually offers, so callers and new endpoints do not assume a convention that is not there.

## What exists
- `dependencies.py` defines `pagination_params` (`skip` >= 0 default 0; `limit` 1..100 default 100) and `PaginationDep`. Grep finds no route that uses `PaginationDep`.
- `GET /v1/auth/api-keys` uses its own query params: `limit` 1..1000 default 100, `offset` >= 0 default 0, plus an optional `api_user_id` filter. It does not use `skip`.
- All feedstock endpoints return complete lists of distinct values (discovery) or single records. They have no pagination.

## Gotchas
- The two conventions disagree: `skip` with max 100 (unused) versus `offset` with max 1000 (used). Any new list endpoint should pick one; the used one is `limit`/`offset`.
- Discovery lists are unbounded `SELECT DISTINCT`. Size grows with the views; watch response size as data grows (inferred risk).

## Open questions
- Should `PaginationDep` be deleted or wired to the feedstock list routes? (not decided in code or history)

# Related Concepts
- [Full webservice endpoint table (36 routes)](webservice-endpoints.md): Shows which routes take pagination params
- [Webservice package layout and app factory](webservice-overview.md): Where the dependency lives in the package
