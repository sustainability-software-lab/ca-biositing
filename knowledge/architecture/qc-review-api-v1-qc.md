---
type: Architecture
title: "/v1/qc API: routes, auth, request and response shapes"
description: "All 15 routes under /v1/qc: portal auth, Stage 1 decisions, tray flagging, assignment, summary, CSV export, admin Stage 2 sync, and the bug-report issue endpoint."
tags: [qc, api, webservice, routes]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:04Z" }
status: stable
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/v1/endpoints/qc_review.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/qc_ledger_service.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/gsheet_sync_service.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/router.py", "tests/webservice/test_qc_review.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/524", "https://github.com/sustainability-software-lab/ca-biositing/pull/526", "commit 00a7146", "commit 7af19de"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Backend of the QC Audit Workbench (Product 4) and the Selection tray (Products 2 and 3). Every route uses the portal cookie through `portal_auth.py`. None of them touch `dependencies.py` or X-API-Key. Router prefix `/qc`, tag `qc-review`, included from `v1/router.py:36`.

## Key files
| path:line | role |
|---|---|
| v1/endpoints/qc_review.py:48 | `router = APIRouter(prefix="/qc")` |
| v1/endpoints/qc_review.py:50-52 | `SessionDep`, `AnalystDep` (`require_portal_analyst`), `AdminDep` (`require_portal_admin`) |
| v1/endpoints/qc_review.py:55-143 | request models: `GoogleAuthRequest`, `DevLoginRequest`, `Stage1DecisionRequest`, `TrayToWorkbenchRequest`, `AssignDecisionRequest`, `BatchGSheetSyncRequest` |
| v1/endpoints/qc_review.py:719-810 | `GitHubIssueRequest` and `/github-issue` |
| services/qc_ledger_service.py:499 | `record_stage1_decision` (behind POST /decisions and tray) |
| services/gsheet_sync_service.py:375, 431 | `sync_single_decision_to_gsheet`, `sync_pending_decisions_batch_to_gsheet` |

## Routes
| Method | Path | Auth | Request | Response | Service |
|---|---|---|---|---|---|
| GET | `/v1/qc/auth/config` | open | none | `google_client_id`, `allowed_domains`, `require_dashboard_auth` | config |
| POST | `/v1/qc/auth/google` | ID token | `{id_token}` or `{credential}` | `{status, email, name, role, auth_mode, assigned_open_count, token, user{}}` plus cookie | `verify_google_id_token`, `authorize_portal_email` |
| POST | `/v1/qc/auth/dev-login` | local development only | `{email, name?}` | same as above, `auth_mode=dev_login` | `authorize_portal_email` |
| GET | `/v1/qc/auth/me` | analyst | none | identity and `assigned_open_count` | none |
| POST | `/v1/qc/auth/logout` | open | none | `{status, authenticated:false}`; clears cookie | none |
| GET | `/v1/qc/decisions` | analyst | query: `assigned_to` (`me`, `unassigned`, or email), `status` or `decision_status` (comma list), `flag_type`, `resource_name`, `analysis_type`, `parameter_name`, `synced_to_gsheet` | `{count, decisions[], items[]}` (same list, two keys) | `_query_filtered_decisions` |
| POST | `/v1/qc/decisions` | analyst | `Stage1DecisionRequest`: `record_table` (default `proximate_record`), `record_id` or `record_ids`, `new_qc_pass`, `decision_action`, `decision_status` or `status`, `review_note`, `rationale_chips`, `assigned_to_email` (`me` allowed) | `{decision, updated_record_ids, synced_to_gsheet:false}`; 400 if no record id | `record_stage1_decision` |
| POST | `/v1/qc/tray-to-workbench` | analyst | `{items[]}` or a single item; each needs `record_id` or `record_ids` | `{created_count, decision_id, decision_ids[], workbench_url, decisions[]}`; creates `open` flags with `decision_action=flag_for_review` | `record_stage1_decision` per id |
| PATCH | `/v1/qc/decisions/{decision_id}/assign` | analyst | `{assigned_to_email}` (`me`, empty, `unassigned`, `none`, `null`) | `{decision}`; 404 if missing | direct ORM update, writes seed CSV |
| GET | `/v1/qc/summary` | analyst | none | totals, `assigned_open_count`, `unassigned_open_count`, `pending_gsheet_sync_count`, `synced_to_gsheet_count`, `by_status`, `by_flag_type`, `by_resource` | ORM scan |
| GET | `/v1/qc/export.csv` | analyst | same filters as list | CSV attachment `qc_review_decisions.csv` | `export_decisions_to_csv_string` |
| POST | `/v1/qc/decisions/{decision_id}/sync-gsheet` | admin | none | `{decision_id, already_synced, synced_to_gsheet, gsheet_synced_at, gsheet_writeback_target, sheet_note, decision}`; 404 if missing | `sync_single_decision_to_gsheet` |
| POST | `/v1/qc/decisions/sync-gsheet-batch` | admin | optional `{decision_ids[]}`; without ids, all resolved unsynced | `{synced_count, synced_decision_ids, results[]}` | `sync_pending_decisions_batch_to_gsheet` |
| POST | `/v1/qc/github-issue` | **none** | `{title, category, description, expected_behavior, page, resource, domain_tab, qc_filter, query_string, create_via_api}` | `{created_via_api, issue_url}` or `{issue_number, issue_url}`; labels `bug,dashboard` | GitHub REST if `GITHUB_TOKEN` is set |

Role matrix: analyst can do everything except the two sync routes (403 for analyst, tested in `tests/webservice/test_qc_review.py:261-300`).

## How it works
- Stage 1 always sets `synced_to_gsheet = false` and `gsheet_synced_at = null`, so the decision re-enters the admin queue.
- Stage 1 writes to the analytical record and to the CSV before it returns. A failed CSV write is not caught in the endpoint path (inferred from `append_or_update_seed_csv`; not exercised).
- Stage 2 is idempotent: a second call returns `already_synced: true` and does not duplicate the `[QC_AUDIT id=...]` tag (regex replace).
- `resolved_by_email` is set to the admin on Stage 2 if it was empty.

## Gotchas
- `/v1/qc/auth/google` returns the portal JWT in the JSON body as well as the cookie (`qc_review.py:209`). Any script that reads the body holds a valid session token.
- Dashboard JS calls `/v1/qc/decisions/approve`, `/v1/qc/decisions/{id}/revert`, and `/v1/qc/auth-config`. None of these exist here. See `bugs/dashboard-client-calls-missing-qc-routes`.
- `_query_filtered_decisions` loads every row and filters in Python. Fine at current size; not paginated.

## History
- 00a7146 (2026-10-19, PR #524): router and portal auth.
- 7af19de (PR #529): `credential` alias accepted on `/auth/google`.
- 587c1cb (PR #526) and 3eba913 (PR #527): tray route and docs.
- 811255f (PR #532): admin list change, affects which accounts pass `require_portal_admin`.

## Open questions
- Whether the `/github-issue` route should require analyst auth (inferred: yes, the only caller is the dashboard, which is behind portal auth).

# Related Concepts
- [Full webservice endpoint table (36 routes)](webservice-endpoints.md): full route inventory including these
- [BioCirV portal auth: Google OIDC, 2-role RBAC, isolated cookie](portal-oidc-auth-and-rbac.md): auth dependencies used by every route
- [QC review decision ledger (qc_review_decision table, lifecycle, seed CSV)](qc-review-decision-ledger.md): table behind the routes
- [Stage 2 Google Sheets writeback: webservice path and dormant pipeline copy](gsheet-qc-writeback.md): Stage 2 implementation
