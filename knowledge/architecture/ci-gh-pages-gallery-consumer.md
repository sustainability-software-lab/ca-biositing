---
type: Architecture
title: "gh-pages.yml: builds the public Pages gallery from the GCS latest bundle"
description: "Pages deploy that runs after the dashboards workflow, reads dashboards/staging/latest with the read-only SA, and copies only the GH_PAGES_GALLERY_GLOB allowlist into the site."
tags: [ci, github-pages, dashboards, gcs, privacy]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:22Z" }
status: stable
code_refs: [".github/workflows/gh-pages.yml", "resources/assets/index.html", "scripts/generate_dashboard_gallery.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/521", "commit 1fcadb4", ".github/workflows/gh-pages.yml"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Deploys the public GitHub Pages site. Since #519 (PR #521, commit 1fcadb4) the gallery comes from GCS instead of the committed exports/plots/ tree.

## Key files
| path:line | role |
|---|---|
| .github/workflows/gh-pages.yml:3-17 | push and pull_request triggers on resources/assets and gallery scripts; exports/plots/** was removed from the path list |
| .github/workflows/gh-pages.yml:18-24 | workflow_run on Build & Export BioCirV Dashboards & Drift Audit, branch main |
| .github/workflows/gh-pages.yml:37-44 | DASHBOARDS_ENV staging, bucket, reader SA (line 40), default GH_PAGES_GALLERY_GLOB (line 44) |
| .github/workflows/gh-pages.yml:47-57 | validate job (header mapping check) |
| .github/workflows/gh-pages.yml:59-68 | build-and-deploy gated to main and to a successful workflow_run |
| .github/workflows/gh-pages.yml:72-78 | GCP auth as the reader SA, continue-on-error |
| .github/workflows/gh-pages.yml:88-118 | fetch latest/* to /tmp/gcs_gallery, then allowlist copy into _site/gallery |
| .github/workflows/gh-pages.yml:107-112 | denylist case for four internal pages |
| .github/workflows/gh-pages.yml:120-144 | placeholder gallery index when none was staged |
| .github/workflows/gh-pages.yml:146-151 | upload-pages-artifact and deploy-pages |

## How it works
1. The workflow runs after the dashboards workflow completes successfully on main, or on a push or PR that touches its own paths.
2. The reader SA fetches dashboards/staging/latest/* (line 99). The copy uses 2>/dev/null and || true, so failures are silent.
3. For each entry in GALLERY_GLOB (repo variable GH_PAGES_GALLERY_GLOB, else the env default), copy the matching file into _site/gallery/. The denylist case removes four pages.
4. If index.html is not staged, write a placeholder page.
5. Upload the Pages artifact and deploy.

## Gotchas
- Default allowlist publishes Product 1 (metadata/resource_analysis_dashboard.html) and the root index.html publicly (line 44). deployment/README.md:1039-1052 says the opposite for a broader set. See bugs/doc-drift-dashboard-privacy-gate.
- The denylist (lines 107-112) names only four pages. The glob is the real gate.
- If GCP auth fails (continue-on-error, line 74), the deploy still succeeds with the placeholder page. There is no failing signal.
- Staging only (line 37). The public site never shows production dashboards.
- The allowlist copies only from the latest/ prefix. Dated snapshots are not read here.

## History
- 1fcadb4 (2026-10-19, PR #521): the exports/plots/** copy was replaced with the GCS fetch, the allowlist, and the workflow_run trigger.
- Before #519: the gh-pages workflow copied exports/plots/* into _site/gallery (see decisions/analysis-static-html-gallery).

## Open questions
- Should the default glob stay on Product 1 or drop to index.html only? (owner decision)

# Related Concepts
- [dashboard-artifacts.yml: builds the dashboard suite and publishes it to GCS](ci-dashboard-artifacts-publisher.md): the upstream workflow whose completion triggers this deploy
- [GCS dashboards bucket, its service accounts, WIF bindings, and runtime reads](infra-dashboards-gcs-bucket.md): the bucket and reader SA this workflow reads
- [Publish analysis as committed static HTML instead of a live dashboard](../decisions/analysis-static-html-gallery.md): the committed-HTML design this workflow replaced
- [deployment/README.md describes a dashboard privacy gate and bucket settings the code does not implement](../bugs/doc-drift-dashboard-privacy-gate.md): README privacy-gate text that does not match this workflow
