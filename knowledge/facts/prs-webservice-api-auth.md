---
type: Fact
title: "Merged PRs: webservice (FastAPI), API keys, and auth"
description: "Index of merged PRs touching the FastAPI webservice: endpoints, JWT, API keys, portal OIDC auth, GCS adapter and MCP server, grouped by merge month; through 2026-10-22."
tags: [webservice, api, auth, prs]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:29Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/webservice/**"]
stale_after: "2026-11-15"
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/497", "https://github.com/sustainability-software-lab/ca-biositing/pull/257", "https://github.com/sustainability-software-lab/ca-biositing/pull/248", "https://github.com/sustainability-software-lab/ca-biositing/pull/241", "https://github.com/sustainability-software-lab/ca-biositing/pull/197", "https://github.com/sustainability-software-lab/ca-biositing/pulls?q=is%3Apr+is%3Amerged", "https://github.com/sustainability-software-lab/ca-biositing/pull/532", "https://github.com/sustainability-software-lab/ca-biositing/pull/529", "https://github.com/sustainability-software-lab/ca-biositing/pull/524"]
---

## Purpose
Webservice PRs: namespace-package endpoint CRUD, JWT and API-key auth with rate limiting, view-backed queries, and the MCP server (closed PR #484 is listed separately).

Scope: 18 merged PRs. Authors: @Vraj1234 (10), @lsetiawan (2), @tylerhuntington (2), @app/copilot-swe-agent (1). Grouped by merge month, newest first. Rows merged from 2026-10-17 through 2026-10-22 were added on 2026-10-22; author counts above predate them. "areas" is the top three path categories touched, computed from the PR file list (not reviewed line by line).

## Key files
Areas in this theme are described by the linked architecture concept (`architecture/webservice-*`). PR bodies, not files, are the primary source for this index.

## How it works
Index only. Each row links to the PR on GitHub. Re-run `gh pr list --state merged` to refresh; this snapshot is as of HEAD a2c8de8 (2026-10-22).

## Interfaces
- Inputs: GitHub PR metadata (`gh pr list --repo sustainability-software-lab/ca-biositing`).
- Outputs: none. This concept is a lookup table.

## Gotchas
- Titles are as merged; some PRs were re-filed (e.g. #422 and #431 share a title; #247 and #256 are a closed duplicate of #248/#257).
- Merge months use `mergedAt`; PRs that were never merged are in `facts/prs-closed-unmerged`.

## History
18 PRs in this theme. Earliest merged 2025-08 (#10); latest 2026-10-21 (#532).

## Open questions
- Whether the author list reflects current ownership (inferred from PR authorship only; confirm with maintainers).

## Merged PRs by month

### 2026-10 (4)
- #524 [feat(webservice): add isolated portal OIDC auth and /v1/qc API](https://github.com/sustainability-software-lab/ca-biositing/pull/524) · @petercarbsmith · 2026-10-19
- #529 [fix(webservice): add google-auth REST GCS adapter and Google Sign-In button](https://github.com/sustainability-software-lab/ca-biositing/pull/529) · @petercarbsmith · 2026-10-19
- #532 [chore(webservice): add two dashboard admin accounts (emails omitted)](https://github.com/sustainability-software-lab/ca-biositing/pull/532) · @petercarbsmith · 2026-10-21
- #497 [feat(agents): adopt the SSEC project-template agent harness](https://github.com/sustainability-software-lab/ca-biositing/pull/497) · @lsetiawan · 2026-10-16 · areas: docs, other, tests

### 2026-04 (2)
- #257 [fix: reject unknown fields on PATCH /v1/auth/api-keys with 422](https://github.com/sustainability-software-lab/ca-biositing/pull/257) · @tylerhuntington · 2026-04-07 · areas: webservice, tests
- #248 [feat: per-client API keys with per-key rate limiting](https://github.com/sustainability-software-lab/ca-biositing/pull/248) · @tylerhuntington · 2026-04-03 · areas: webservice, datamodels, alembic

### 2026-03 (5)
- #241 [feat: redirect root to /docs](https://github.com/sustainability-software-lab/ca-biositing/pull/241) · @Vraj1234 · 2026-03-31 · areas: webservice
- #197 [feat: add availability discovery endpoints and full test coverage](https://github.com/sustainability-software-lab/ca-biositing/pull/197) · @Vraj1234 · 2026-03-25 · areas: tests, webservice
- #170 [Feat: Api implementation improvements](https://github.com/sustainability-software-lab/ca-biositing/pull/170) · @Vraj1234 · 2026-03-09 · areas: webservice, ci, alembic
- #159 [feat: query data model views instead of rebuilding joins](https://github.com/sustainability-software-lab/ca-biositing/pull/159) · @Vraj1234 · 2026-03-03 · areas: webservice, tests, alembic
- #155 [Resolve #140 via USDA crop normalization and complete api_name transition groundwork (#156, #157 - work done b](https://github.com/sustainability-software-lab/ca-biositing/pull/155) · @Vraj1234 · 2026-03-02 · areas: webservice, tests, alembic

### 2026-02 (6)
- #141 [fix: observation query mismatch](https://github.com/sustainability-software-lab/ca-biositing/pull/141) · @Vraj1234 · 2026-02-26 · areas: tests, webservice
- #139 [feat: add JWT authentication to webservice](https://github.com/sustainability-software-lab/ca-biositing/pull/139) · @lsetiawan · 2026-02-26 · areas: webservice, tests, datamodels
- #117 [Feat/feedstock analysis 99 101](https://github.com/sustainability-software-lab/ca-biositing/pull/117) · @Vraj1234 · 2026-02-17 · areas: webservice, tests
- #116 [Feat/usda survey 95 98](https://github.com/sustainability-software-lab/ca-biositing/pull/116) · @Vraj1234 · 2026-02-17 · areas: webservice, tests
- #106 [Feat/usda census 91 94](https://github.com/sustainability-software-lab/ca-biositing/pull/106) · @Vraj1234 · 2026-02-12 · areas: webservice, tests
- #105 [Feat/api foundation 87 89](https://github.com/sustainability-software-lab/ca-biositing/pull/105) · @Vraj1234 · 2026-02-12 · areas: webservice, tests

### 2025-12 (1)
- #68 [Complete webservice namespace package with full CRUD endpoints](https://github.com/sustainability-software-lab/ca-biositing/pull/68) · @app/copilot-swe-agent · 2025-12-16 · areas: webservice, other, docs

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state hub for the repo.
