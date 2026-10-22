---
type: Architecture
title: "Dashboard snapshot loader: local-first, then GCS with TTL and ETag cache"
description: "How /v1/dashboards serves BioCirV HTML from exports/plots or the dashboards GCS bucket, including the google-auth REST fallback used when google-cloud-storage is not installed."
tags: [dashboards, gcs, webservice, cache]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:07Z" }
status: stable
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/services/dashboard_loader.py", "src/ca_biositing/webservice/ca_biositing/webservice/main.py", "src/ca_biositing/webservice/ca_biositing/webservice/config.py", "resources/docker/webservice.dockerfile", "pixi.lock"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/524", "https://github.com/sustainability-software-lab/ca-biositing/pull/529", "commit 00a7146", "commit 7af19de"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Serves the dashboard suite (`index.html`, `login.html`, `metadata/*.html`, `audit/*`) from a local directory in development and from a GCS snapshot in Cloud Run. The snapshot is written by CI (`bd72222`, `1fcadb4`, see `facts/history-gcp-staging-deployment` for the bucket).

## Key files
| path:line | role |
|---|---|
| services/dashboard_loader.py:115-148 | `sanitize_dashboard_subpath`: rejects NUL, backslash, absolute, `.` and `..` segments |
| services/dashboard_loader.py:107-112 | `get_exports_plots_dir` (env `BIOSITING_DASHBOARDS_LOCAL_DIR`, default `exports/plots`) |
| services/dashboard_loader.py:166-236 | `_RestBlob`, `_RestBucket`, `_AuthorizedRestGcsClient` (google-auth `AuthorizedSession`, scope `devstorage.read_only`) |
| services/dashboard_loader.py:239-246 | `get_gcs_storage_client`: `google.cloud.storage` if importable, else the REST adapter |
| services/dashboard_loader.py:249-302 | `_fetch_from_gcs`: TTL cache, exists check, ETag reload |
| services/dashboard_loader.py:305-362 | `load_dashboard_asset`: local first, then GCS, then built-in login fallback, then 404 |
| main.py:141-173 | `_serve_authenticated_dashboard`: auth and admin gate, sets `X-Dashboard-Source` header |

## How it works
1. Sanitise the subpath. Map a directory to its `index.html`.
2. Look for the file under the local directory. Resolve symlinks and require the result to stay under it (`is_relative_to`).
3. If `DASHBOARDS_BUCKET_NAME` is set, or a client is injected, fetch `gs://<bucket>/<prefix>/<subpath>`. Prefix comes from `DASHBOARDS_GCS_PREFIX` (Cloud Run: `dashboards/<stack>/latest`).
4. Cache: 60 s TTL by default (`ttl_seconds=60`). After TTL, the blob’s ETag is re-read and content is reused on a match.
5. `login.html` falls back to `BUILTIN_LOGIN_HTML` if absent in GCS. Anything else gives 404.
6. Response header `X-Dashboard-Source` is one of `local`, `gcs`, `gcs_cache`, `builtin_fallback`.

## Gotchas
- Every failure inside `_fetch_from_gcs` (client construction, metadata, download) returns None, so the caller gives 404. A permissions error on the bucket looks like a missing dashboard. `_RestBlob.exists` also swallows errors and returns False.
- `get_gcs_storage_client()` builds a new client on each cache miss.
- `config.py` default prefix is `dashboards/staging/latest`. The README says `DASHBOARD_CACHE_TTL_SECONDS` defaults to 300. Code uses 60 s and has no such env var (`dashboard_loader.py:_fetch_from_gcs`).
- The google-cloud-storage package is not in the webservice pixi env (`pixi.lock`, webservice section), so the REST adapter is the path that runs in the container (inferred from the lock; not run).

## History
- 00a7146 (2026-10-19, PR #524): loader and GCS fallback.
- 7af19de (PR #529): REST adapter for the webservice env (no google-cloud-storage); Google Sign-In button on the built-in login.
- 811255f (PR #532): admin defaults used by the admin-only dashboard gate.

## Open questions
- Whether dashboards should fail closed (503) on GCS errors instead of 404 (open).

# Related Concepts
- [Webservice deployment on GCP Cloud Run](webservice-deployment-cloud-run.md): Cloud Run env that sets the bucket and prefix
- [BioCirV portal auth: Google OIDC, 2-role RBAC, isolated cookie](portal-oidc-auth-and-rbac.md): gate in front of every dashboard route
- [Metadata and summary dashboards (analysis/metadata)](analysis-metadata-dashboards.md): the generators whose HTML is served
