---
type: Architecture
title: Five-product BioCirV resource dashboard suite and how each is generated
description: "Five static HTML products (Pages 1-2, Page 3 explorer, Product 4 workbench, Product 5 drift) generated from live PostgreSQL or a JSON snapshot, with a gallery and login portal on top."
tags: [dashboards, analysis, qc, html, snapshot, pixi]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:13Z" }
status: stable
code_refs: ["analysis/metadata/resource_analysis_dashboard.py", "analysis/metadata/resource_explorer_dashboard.py", "analysis/metadata/resource_insights_engine.py", "analysis/metadata/resource_audit_workbench.py", "analysis/audit/db_environment_drift.py", "scripts/generate_dashboard_gallery.py", ".github/workflows/dashboard-artifacts.yml", "tests/fixtures/minimal_dashboard_snapshot.json", ".agents/skills/resource-analysis-dashboards/SKILL.md"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/518", "https://github.com/sustainability-software-lab/ca-biositing/pull/525", "https://github.com/sustainability-software-lab/ca-biositing/pull/526", "https://github.com/sustainability-software-lab/ca-biositing/pull/530", "https://github.com/sustainability-software-lab/ca-biositing/pull/531", "https://github.com/sustainability-software-lab/ca-biositing/pull/535", "commit d290906", "commit c4cbf2d", "commit 587c1cb", "commit f4e9f5a", "commit f954bd3", "commit a2c8de8"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
The BioCirV analysis dashboards are standalone HTML files built by Python scripts in `analysis/metadata/` and `analysis/audit/`. Together they make up the five-product suite that the gallery links to. Products 1-3 only read the data, apart from the tray-to-workbench export from Pages 2-3 and the live overlay read; Product 4 writes QC decisions through the API; Product 5 is admin-only.

## Key files
| Path:line | Role |
| --- | --- |
| analysis/metadata/resource_analysis_dashboard.py:7779 | `main()`: writes Page 1 (Characterization & AI Brief) and Page 2 (Statistical QC & Lab Notes Audit) |
| analysis/metadata/resource_analysis_dashboard.py:49 | `DEFAULT_OUTPUT_DIR` = exports/plots/metadata |
| analysis/metadata/resource_analysis_dashboard.py:7904-7907 | Page 1 and Page 2 file writes (Page 2 is named `resource_qc_outlier_dashboard.html`) |
| analysis/metadata/resource_explorer_dashboard.py:67 | `fetch_all_resource_data()`: the live PostgreSQL query via `get_engine()` |
| analysis/metadata/resource_explorer_dashboard.py:5376 | `main()` for Page 3 (Multi-Resource Explorer); writes the snapshot at :5429 |
| analysis/metadata/resource_insights_engine.py:1293 | `main()`: builds the AI insights sidecar (`--from-snapshot`, `--output`) |
| analysis/metadata/resource_audit_workbench.py:3557 | `main()` for Product 4; see architecture/analysis-qc-audit-workbench |
| analysis/audit/db_environment_drift.py:3963 | `main()` for Product 5; see architecture/analysis-db-drift-assessment |
| scripts/generate_dashboard_gallery.py:432 | `generate_gallery()`: index.html and login.html |
| .github/workflows/dashboard-artifacts.yml | CI build of the whole suite and the GCS publish |

## How it works
| Product | Generator | Output under exports/plots/ | Data source |
| --- | --- | --- | --- |
| 1 Characterization & AI Brief | resource_analysis_dashboard.py | metadata/resource_analysis_dashboard.html | live DB, or `--from-snapshot` JSON; AI sidecar at data/insights/resource_ai_insights.json |
| 2 Statistical QC & Lab Notes Audit | resource_analysis_dashboard.py (same run) | metadata/resource_qc_outlier_dashboard.html | same as Product 1 |
| 3 Multi-Resource Side-by-Side Explorer | resource_explorer_dashboard.py | metadata/resource_explorer_dashboard.html | live DB, or `--from-snapshot`; live runs also write metadata/dashboard_data_snapshot.json |
| 4 QC Audit Workbench | resource_audit_workbench.py | metadata/resource_audit_workbench.html | snapshot file, with live DB fallback (see the workbench concept) |
| 5 DB Drift (admin) | db_environment_drift.py | audit/db_environment_drift_dashboard.html | three PostgreSQL fingerprints |
| Gallery and login | scripts/generate_dashboard_gallery.py | index.html, login.html | scans the category folders |

Commands (pixi.toml:253-259): `refresh-resource-insights`, `build-resource-analysis-dashboard`, `build-resource-explorer-dashboard`, `build-resource-audit-workbench`, `update-gallery`, and `refresh-dashboards`, which runs insights, Page 1/2, Page 3, Product 4 and the gallery in that order. The drift page is not in `refresh-dashboards`; it is built by `db-drift-compare`.

Snapshot mode: `--from-snapshot <json>` replaces the live query in the insights engine, Pages 1-2 and Page 3. Page 1 and Page 2 can also write a collaborator slice (`--slice-resource`, default `qc_status=pass`, analyst emails masked).

CI: .github/workflows/dashboard-artifacts.yml runs on `workflow_dispatch`, on pushes to main that touch the generator files, on a Monday 09:00 UTC cron, and after the staging and production ETL workflows complete. Its data-source step picks `live_db` or snapshot ("auto" tries live first). When it falls back to tests/fixtures/minimal_dashboard_snapshot.json, the GCS publish step is skipped.

## Interfaces
- **Inputs:** PostgreSQL through `ca_biositing.datamodels.database.get_engine()` (POSTGRES_HOST defaults to localhost), or a snapshot JSON; the AI sidecar in data/insights/.
- **Outputs:** HTML under exports/plots/ (gitignored, .gitignore:142). CI publishes to gs://<bucket>/dashboards/<env>/<date-sha> and .../latest.
- **Callers:** pixi tasks above; the dashboard-artifacts workflow; `scripts/regenerate_all_plots.py` (the metadata category globs every `*.py` there, so the resource scripts run with no arguments, i.e. against live DB).

## Gotchas
- Page 2 has no generator of its own. Page 1’s script writes both, and the Page 1 HTML links to Page 2 by file name.
- The snapshot `exports/plots/metadata/dashboard_data_snapshot.json` is no longer tracked (ae147f6, #522). Product 4 now fetches live data when it is missing (f4e9f5a, #530).
- The Report a Bug target differs by product: Products 1-3 use sustainability-software-lab, Products 4-5 and the gallery use uw-ssec (see bugs/dashboards-report-bug-github-repo-mismatch).
- Default API base is `http://localhost:8000` in four generators, which is also the `serve-gallery` port (pixi.toml:261). See the workbench concept.
- The suite is static HTML with data embedded in the page. Products 1-3 are not gated by the webservice unless they are served from /v1/dashboards, which is the only route with the login check (src/ca_biositing/webservice/ca_biositing/webservice/main.py:141).

## History
- d290906 (PR #518, 2026-10-19): three resource pages, the explorer, the slice exporter, and the insights engine.
- c4cbf2d (PR #525, 2026-10-19): Product 4 workbench, login portal, and the five-product gallery.
- 587c1cb (PR #526, 2026-10-19): live QC overlay and tray-to-workbench export in Pages 1-3.
- f4e9f5a (PR #530, 2026-10-21): explorer writes the snapshot; workbench falls back to live DB.
- f954bd3 (PR #531, 2026-10-21): BroadcastChannel unref and test timeouts.
- a2c8de8 (PR #535, 2026-10-22): Report a Bug modal restored on all products and the gallery; `POST /v1/qc/github-issue`.

## Open questions
- Whether the Product 4 `refresh-dashboards` step should also run the drift assessment (inferred: not intended; drift is admin-only and needs fingerprints).

# Related Concepts
- [Multi-environment DB drift assessment (4 layers, local/staging/production)](analysis-db-drift-assessment.md): Product 5 generator and its fingerprint model
- [Product 4 QC Audit Workbench: Stage 1 decisions, Stage 2 Sheets sync, tray handoff](analysis-qc-audit-workbench.md): Product 4 generator, API calls and snapshot fallback
- [Dashboard gallery index and login portal (scripts/generate_dashboard_gallery.py)](analysis-dashboard-gallery-and-portal.md): gallery and login portal that link the five products
- [Metadata and summary dashboards (analysis/metadata)](analysis-metadata-dashboards.md): older metadata summary scripts in the same folder
- [Plot regeneration, HTML gallery index, and GitHub Pages deploy](analysis-regeneration-and-gallery.md): update-plots and the publish path for these outputs
- [GitHub Actions workflows: what runs on PRs, main, releases and deploys](tooling-ci-workflows.md): dashboard-artifacts.yml builds and publishes the suite
- [/v1/qc API: routes, auth, request and response shapes](qc-review-api-v1-qc.md): endpoints called by Products 2-4 for QC state and tray export
- [Publish analysis as committed static HTML instead of a live dashboard](../decisions/analysis-static-html-gallery.md): the static-HTML publishing choice this suite follows
