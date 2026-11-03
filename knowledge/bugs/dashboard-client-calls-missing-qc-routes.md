---
type: Bug
title: Dashboard client calls /v1/qc routes that do not exist; failures fall back to local-only state
description: "The Product 2/3 dashboard client posts to /v1/qc/decisions/approve, /v1/qc/decisions/{id}/revert and /v1/qc/auth-config, none of which are registered, and reports success from localStorage."
tags: [qc, dashboard, frontend, bug]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:08Z" }
status: stable
code_refs: ["analysis/metadata/resource_analysis_dashboard.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/endpoints/qc_review.py"]
sources: ["commit 587c1cb", "commit 3eba913"]
governance: context
stale_after: "2026-12-31"
---

## Symptom
An analyst clicks revert or approve in the shipped Product 2/3 page. The server never sees the change. The UI shows a local success (`status: "reverted_offline"`, `source: "local"`), so the decision looks saved but is not in `qc_review_decision`.

## Location
- `analysis/metadata/resource_analysis_dashboard.py:2571`: `fetch(`${id.apiBase}/v1/qc/decisions/approve`)`. No such route. Router has `POST /v1/qc/decisions` only (`qc_review.py:426`).
- `analysis/metadata/resource_analysis_dashboard.py:2620`: `fetch(.../v1/qc/decisions/${id}/revert)`. No such route.
- `analysis/metadata/resource_analysis_dashboard.py:2587-2600` and `:2630-2648`: on `!resp.ok` or exception, the code writes to localStorage and returns `ok: true`.
- `analysis/metadata/resource_analysis_dashboard.py:3135`: `/v1/qc/auth-config`. The router path is `/v1/qc/auth/config` (`qc_review.py:163`).

## Evidence and status
Read from code. The generator is `analysis/metadata/resource_analysis_dashboard.py`, which embeds this JS. Not run in a browser. Whether the Product 2/3 page is currently published with this client is inferred, not checked.

## Suggested fix (not applied)
Either add the two routes to `qc_review.py` or point the client at the existing `POST /v1/qc/decisions` with a revert payload. Fix the auth-config path. Stop reporting `ok: true` for offline-only writes, or show them as unsaved.

## Status
Open at HEAD a2c8de8 (inferred from code).

# Related Concepts
- [/v1/qc API: routes, auth, request and response shapes](../architecture/qc-review-api-v1-qc.md): the registered routes
- [Metadata and summary dashboards (analysis/metadata)](../architecture/analysis-metadata-dashboards.md): generator that embeds the client
