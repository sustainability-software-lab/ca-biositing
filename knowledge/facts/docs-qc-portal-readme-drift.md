---
type: Fact
title: "Docs for the portal and QC API disagree with the code (webservice README, ETL workflow)"
description: "The webservice README and ETL_WORKFLOW QC section, added Oct 2026, name routes, settings and CLI commands that do not exist; this lists them so readers can trust the architecture concepts instead."
tags: [docs, qc, webservice, drift]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:09Z" }
status: stable
code_refs: ["src/ca_biositing/webservice/README.md", "docs/pipeline/ETL_WORKFLOW.md", "src/ca_biositing/webservice/ca_biositing/webservice/v1/endpoints/qc_review.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/qc_ledger_seed.py"]
sources: ["commit 3eba913", "https://github.com/sustainability-software-lab/ca-biositing/pull/527"]
governance: context
stale_after: "2026-12-31"
---

## What is documented vs the code
Source: `src/ca_biositing/webservice/README.md` (added in 3eba913, lines 56-140) and `docs/pipeline/ETL_WORKFLOW.md` lines 95-160 (3eba913).

| Documented | At HEAD |
|---|---|
| `POST /v1/dashboards/auth/google`, `/v1/dashboards/auth/dev-login` | Routes are `/v1/qc/auth/google` and `/v1/qc/auth/dev-login` (`qc_review.py:174, 220`) |
| `POST /v1/qc/decisions/approve`, `POST /v1/qc/decisions/{id}/revert` | Not registered (see `bugs/dashboard-client-calls-missing-qc-routes`) |
| `POST /v1/qc/sync-gsheet` (admin) | Per-id and batch routes: `/v1/qc/decisions/{id}/sync-gsheet`, `/v1/qc/decisions/sync-gsheet-batch` |
| `GET /v1/qc/export-seed-csv`, `POST /v1/qc/import-seed-csv` | Not registered. `GET /v1/qc/export.csv` exports the ledger; the seed CSV is written by the service but not exposed |
| `GOOGLE_OAUTH_CLIENT_ID`, `DASHBOARD_SESSION_SECRET`, `DASHBOARD_GCS_BUCKET`, `DASHBOARD_CACHE_TTL_SECONDS`, `DASHBOARD_LOCAL_DIR`, `ENVIRONMENT=local`, `DASHBOARD_DEV_AUTH_BYPASS` | Code uses `GOOGLE_CLIENT_ID` / `API_GOOGLE_CLIENT_ID`, `API_DASHBOARDS_BUCKET_NAME`, a 60 s TTL, `BIOSITING_DASHBOARDS_LOCAL_DIR`, and `ENV` (`config.py`, `dashboard_loader.py`, `qc_review.py:228`) |
| Default allowed domains `lbl.gov,berkeley.edu` | Code default is `lbl.gov`, `ucdavis.edu`, `beamcircular.org` (`config.py:75-82`) |
| Unauthenticated API requests get 401 | Dashboard requests get a 302 to login for any client (`main.py:147-157`) |
| `POST /v1/qc/sync-gsheet` also refreshes materialized views | No MV refresh in the sync code (`gsheet_sync_service.py`) |
| ETL_WORKFLOW: `qc_ledger_seed export --output data/seeds/...` and `import --input ...` | CLI flags are `--export` and `--csv-path`; default path is `data/qc/qc_review_decisions_seed.csv` (`qc_ledger_seed.py:36-41, 391-411`) |
| ETL_WORKFLOW: `build_qc_aware_update_dict(insert_stmt, update_columns, protected_record_ids, model_table)` | Signature is `(model_cls, stmt, protected_record_ids, record_id=None)` (`qc_protected_records.py:65-70`) |
| ETL_WORKFLOW: `sync_qc_decisions_to_gsheet`, worksheet `qc_Waiting_Decisions`, `qc_audit_note` column | Not in code. Real names: `writeback_qc_decision_to_gsheet` and `writeback_batch_to_gsheet`; note column `note` |

The README role matrix (analyst cannot sync, admin can) matches the code (`AdminDep`).

## Gotchas
- Trust `architecture/portal-oidc-auth-and-rbac` and `architecture/qc-review-api-v1-qc` over these two docs.
- Fix the docs in a separate change, not as part of a code change.

## History
- 3eba913 (2026-10-19, PR #527): added both sections.

# Related Concepts
- [/v1/qc API: routes, auth, request and response shapes](../architecture/qc-review-api-v1-qc.md): accurate route list
- [BioCirV portal auth: Google OIDC, 2-role RBAC, isolated cookie](../architecture/portal-oidc-auth-and-rbac.md): accurate auth description
