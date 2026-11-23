---
type: Architecture
title: Dashboard gallery index and login portal (scripts/generate_dashboard_gallery.py)
description: "The generator writes exports/plots/index.html and login.html; it auto-lists category HTML, hides Product 5 from non-admins in the page, and the webservice enforces admin on audit paths."
tags: [gallery, portal, login, dashboards, rbac]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:15Z" }
status: stable
code_refs: ["scripts/generate_dashboard_gallery.py", "src/ca_biositing/webservice/ca_biositing/webservice/main.py", ".github/workflows/gh-pages.yml", "tests/analysis/test_resource_audit_workbench.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/525", "https://github.com/sustainability-software-lab/ca-biositing/pull/535", "https://github.com/sustainability-software-lab/ca-biositing/pull/442", "https://github.com/sustainability-software-lab/ca-biositing/pull/521", "commit c4cbf2d", "commit a2c8de8", "commit 707afa8"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Builds the landing page for the BioCirV analysis outputs and a sign-in page for the dashboards. The gallery links the five products and lists every other HTML file in the category folders.

## Key files
| Path:line | Role |
| --- | --- |
| scripts/generate_dashboard_gallery.py:12 | `DESCRIPTIONS`: one-line card text for each of the five products |
| scripts/generate_dashboard_gallery.py:40 | `render_login_html()`: the login portal page (analyst vs admin copy) |
| scripts/generate_dashboard_gallery.py:432 | `generate_gallery()`: scans metadata, audit, conversion, composition, geospatial, lineage |
| scripts/generate_dashboard_gallery.py:585 | Hero text with literal counts ("384 prepared samples", "11,974 observations") |
| scripts/generate_dashboard_gallery.py:627-700 | Hand-written Product 1-5 cards with fixed links (metadata/... and audit/...) |
| scripts/generate_dashboard_gallery.py:793-815 | Client-side role check that shows or hides Product 5 cards |
| scripts/generate_dashboard_gallery.py:886, 974 | Report a Bug repo URL and API base (same pattern as the other generators) |
| scripts/generate_dashboard_gallery.py:1028 | `main()` with `--base-dir` and `--output-dir` |
| src/ca_biositing/webservice/ca_biositing/webservice/main.py:141 | `_serve_authenticated_dashboard()`: login redirect for /v1/dashboards |
| src/ca_biositing/webservice/ca_biositing/webservice/main.py:159 | Admin-only check for `audit/` and `db_environment_drift_dashboard.html` (403 otherwise) |
| .github/workflows/gh-pages.yml:44 | `GH_PAGES_GALLERY_GLOB`: the public allowlist (index.html and the resource analysis page by default) |
| .github/workflows/gh-pages.yml:108 | Skip list for internal dashboards on public Pages |

## How it works
`generate_gallery()` walks the six category folders under exports/plots, sorts the HTML files, skips names containing `monolith`, `pretreatment_variance` or `resource_quick_widget`, and writes one card per file with a description from `DESCRIPTIONS` (or a generic one). It then writes the hand-written five-product block above those sections and `login.html` next to `index.html`.

Role gating: the page calls `GET /v1/qc/auth/me` and toggles the Product 5 card and link (`data-admin-only`, `data-role-state`). The webservice serves `/v1/dashboards/...` only to a signed-in portal user and returns 403 for non-admins on `audit/` paths.

## Interfaces
- **Inputs:** the HTML already under exports/plots/<category>/.
- **Outputs:** exports/plots/index.html and exports/plots/login.html (gitignored with exports/plots).
- **Callers:** `pixi run update-gallery`, `refresh-dashboards`, `update-plots`, the dashboard-artifacts workflow.

## Gotchas
- **The client-side gate is cosmetic.** Hiding a card does not protect the file; the protection is the webservice route (main.py:159). GitHub Pages is protected only by its allowlist (gh-pages.yml:44 and :108), which excludes the workbench, drift page, QC outlier page and explorer.
- **Product 2 card depends on Product 1’s run.** The card links `metadata/resource_qc_outlier_dashboard.html`, which only exists after the Page 1 script runs (resource_analysis_dashboard.py:7904-7907).
- **Hard-coded counts** in the hero text (line 585) will go stale; they are not read from the database.
- **Auto-listing has no cleanup.** Orphan HTML stays listed until deleted (see bugs/analysis-gallery-stale-entries).
- The Product 4 and 5 cards are built from literal paths, so renaming an output file breaks the gallery without any error.

## History
- 707afa8 (PR #442, 2026-07-06): original gallery index.
- c4cbf2d (PR #525, 2026-10-19): five-product gallery and login portal.
- a2c8de8 (PR #535, 2026-10-22): Report a Bug modal on the gallery (repo URL points to uw-ssec; see bugs/dashboards-report-bug-github-repo-mismatch).

## Open questions
- Whether the public Pages allowlist should also drop the resource analysis page now that the portal is the access path (inferred; a product decision).

# Related Concepts
- [BioCirV portal auth: Google OIDC, 2-role RBAC, isolated cookie](portal-oidc-auth-and-rbac.md): sign-in and role check behind /v1/dashboards and the login page
- [Five-product BioCirV resource dashboard suite and how each is generated](analysis-resource-dashboard-suite.md): the five products this gallery links
- [Plot regeneration, HTML gallery index, and GitHub Pages deploy](analysis-regeneration-and-gallery.md): update-plots and the GitHub Pages publish path
- [Publish analysis as committed static HTML instead of a live dashboard](../decisions/analysis-static-html-gallery.md): static gallery decision this generator implements
- [exports/gallery.md and analysis outputs reference scripts that do not exist](../bugs/analysis-gallery-stale-entries.md): hand-maintained gallery.md is separate and stale
