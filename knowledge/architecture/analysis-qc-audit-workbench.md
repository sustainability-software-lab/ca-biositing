---
type: Architecture
title: "Product 4 QC Audit Workbench: Stage 1 decisions, Stage 2 Sheets sync, tray handoff"
description: "Product 4 is a self-contained HTML QC workbench that saves decisions via /v1/qc/decisions, syncs open tabs with BroadcastChannel, and receives tray selections from Pages 2-3."
tags: [qc, workbench, dashboards, broadcastchannel, google-sheets]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:14Z" }
status: stable
code_refs: ["analysis/metadata/resource_audit_workbench.py", "analysis/metadata/resource_analysis_dashboard.py", "tests/analysis/test_resource_audit_workbench.py", "tests/analysis/test_live_qc_overlay_and_tray.py", "tests/fixtures/minimal_dashboard_snapshot.json", "src/ca_biositing/webservice/ca_biositing/webservice/v1/endpoints/qc_review.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/525", "https://github.com/sustainability-software-lab/ca-biositing/pull/526", "https://github.com/sustainability-software-lab/ca-biositing/pull/530", "https://github.com/sustainability-software-lab/ca-biositing/pull/535", "https://github.com/sustainability-software-lab/ca-biositing/issues/515", "commit c4cbf2d", "commit 587c1cb", "commit f4e9f5a", "commit a2c8de8"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Product 4 is where analysts review flagged resource records and record a QC decision. The HTML is generated from a snapshot, and all state changes go through the webservice `/v1/qc` API. Stage 1 writes to PostgreSQL; Stage 2 (admin only) writes to Google Sheets.

## Key files
| Path:line | Role |
| --- | --- |
| analysis/metadata/resource_audit_workbench.py:38 | `DEFAULT_SNAPSHOT_PATH` = exports/plots/metadata/dashboard_data_snapshot.json |
| analysis/metadata/resource_audit_workbench.py:66 | `_fetch_live_resource_data()`: imports `fetch_all_resource_data` without leaving sys.path changed |
| analysis/metadata/resource_audit_workbench.py:89 | `load_snapshot()`: file, then live fetch and snapshot write, then tests/fixtures/minimal_dashboard_snapshot.json |
| analysis/metadata/resource_audit_workbench.py:257 | `build_workbench_payload()` |
| analysis/metadata/resource_audit_workbench.py:602 | `render_workbench_html()`: the inline HTML/JS application |
| analysis/metadata/resource_audit_workbench.py:1737-1741 | `BroadcastChannel("biocirv_qc_decisions")` |
| analysis/metadata/resource_audit_workbench.py:2689 | `refreshQcStateFromApi()`: GET `/v1/qc/auth/me` and `/v1/qc/decisions` |
| analysis/metadata/resource_audit_workbench.py:2896 | Stage 1 save: POST `/v1/qc/decisions` |
| analysis/metadata/resource_audit_workbench.py:3074, 3127 | Stage 2: POST `/v1/qc/decisions/{id}/sync-gsheet` and `/sync-gsheet-batch` (admin) |
| analysis/metadata/resource_audit_workbench.py:3442-3443 | GitHub issue submit via `BIOCIRV_API_BASE` (default `http://localhost:8000`) |
| analysis/metadata/resource_audit_workbench.py:3516, 3557 | `build_resource_audit_workbench()` and `main()` |
| analysis/metadata/resource_analysis_dashboard.py:2757 | Pages 1-3 tray export: POST `/v1/qc/tray-to-workbench` |
| analysis/metadata/resource_analysis_dashboard.py:3047 | Pages 1-3 live overlay: GET `/v1/qc/decisions?limit=500` |
| analysis/metadata/resource_analysis_dashboard.py:7006 | `SELECTION_TRAY_KEY` = `biocirv_qc_selection_tray_v1` (localStorage mirror) |
| src/ca_biositing/webservice/ca_biositing/webservice/v1/endpoints/qc_review.py:485 | `/v1/qc/tray-to-workbench` (see architecture/webservice-qc-review-api) |

## How it works
- **Queue and facets:** tabs for assigned to me, unassigned, all open, in review, resolved (pending Sheets sync), and synced. Facets: resource, domain, parameter, flag type, analyst.
- **Stage 1:** the analyst picks a replicate scope (whole group or single points), gives a rationale and a required note, and saves. The page POSTs to `/v1/qc/decisions`, then posts the saved decision on the BroadcastChannel so other open tabs of the same browser update.
- **Stage 2:** admins can sync one decision or a batch to Google Sheets. The UI shows a four-step provenance timeline.
- **Live overlay (587c1cb):** Pages 1-3 load `GET /v1/qc/decisions` on open and on "Refresh QC State", patch `qc_status` in memory, and re-render. There is no polling.
- **Tray handoff:** Pages 2-3 POST the selected items to `/v1/qc/tray-to-workbench`, mirror them to localStorage key `biocirv_qc_selection_tray_v1`, and redirect to `/v1/dashboards/metadata/resource_audit_workbench.html?decision_id=...` (qc_review.py:556-559).
- **Snapshot fallback (f4e9f5a):** if the default snapshot is missing, `load_snapshot` fetches live, writes the snapshot, and returns it. If that fails it logs a warning and uses the minimal fixture.

## Interfaces
- **Inputs:** the snapshot JSON; `/v1/qc/*` endpoints on the same origin (relative URLs) or on `BIOCIRV_API_BASE`.
- **Outputs:** `resource_audit_workbench.html`; decisions in the database (via API); Sheets rows (Stage 2).
- **Callers:** `pixi run build-resource-audit-workbench` and `refresh-dashboards`; the dashboard-artifacts workflow; Pages 2-3 links.

## Gotchas
- **Same-origin only for Stage 1.** Auth, load and save use relative paths (lines 2691, 2709, 2896). Only the GitHub issue submit uses `BIOCIRV_API_BASE`. The page therefore works from the webservice `/v1/dashboards/` route, not from a static preview (inferred from the code; not exercised).
- **Port collision by default.** `serve-gallery` runs `http.server 8000` (pixi.toml:261), and the webservice runs `uvicorn` with no port flag (pixi.toml:266-269), so both default to 8000 and the `http://localhost:8000` default points at whichever is running (inferred).
- **BroadcastChannel is same-browser only.** Other analysts’ decisions appear only after "Refresh QC State" (see the skill, section 5).
- **Doc drift:** `.agents/skills/resource-analysis-dashboards/SKILL.md` says the tray mirrors to `localStorage["biocirv_qc_audit_tray_v1"]`. The code uses `biocirv_qc_selection_tray_v1` (resource_analysis_dashboard.py:7006).
- **Date filters (issue #515, closed):** covered by `test_issue_515_date_filtering_and_default_start_date` in tests/test_resource_slice_export.py:568.
- The Report a Bug link in this page points to uw-ssec (line 3348). See bugs/dashboards-report-bug-github-repo-mismatch.

## History
- c4cbf2d (PR #525, 2026-10-19): created the workbench.
- 587c1cb (PR #526, 2026-10-19): live overlay, BroadcastChannel sync, tray-to-workbench.
- f4e9f5a (PR #530, 2026-10-21): live fallback in `load_snapshot`.
- a2c8de8 (PR #535, 2026-10-22): Report a Bug modal and `POST /v1/qc/github-issue` on the workbench.

## Open questions
- Whether a static copy of the workbench (for example a GCS `latest` link) should ever run Stage 1 writes; today it would need a configured API base (inferred).

# Related Concepts
- [/v1/qc API: routes, auth, request and response shapes](qc-review-api-v1-qc.md): the /v1/qc endpoints this page calls for auth, decisions, tray and Sheets sync
- [BioCirV portal auth: Google OIDC, 2-role RBAC, isolated cookie](portal-oidc-auth-and-rbac.md): session and role (analyst or admin) that gate Stage 2
- [Five-product BioCirV resource dashboard suite and how each is generated](analysis-resource-dashboard-suite.md): snapshot producer and sibling products
- [Report a Bug links and the bug-issue API default point at uw-ssec/ca-biositing, not the origin repo](../bugs/dashboards-report-bug-github-repo-mismatch.md): Report a Bug link targets a different repo than Products 1-3
- [Analysis chart exclusions must match the portal QC definitions](../requirements/analysis-qc-filter-parity.md): QC pass or fail definitions shown in the workbench must match the portal
