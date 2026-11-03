---
type: Architecture
title: "Pixi tasks for tests, coverage, webservice, docs, gallery and frontend"
description: "The non-ETL pixi tasks: pytest entry points, coverage, uvicorn start, OpenAPI generation, admin creation, MkDocs, the dashboard gallery and refresh tasks, drift tasks, QGIS and frontend."
tags: [tooling, pixi, testing, webservice, docs, gallery]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:06Z" }
status: stable
governance: context
code_refs: ["pixi.toml", "scripts/generate_openapi.py", "scripts/regenerate_all_plots.py", "scripts/generate_dashboard_gallery.py", "mkdocs.yml"]
sources: ["pixi.toml", "commit 707afa8", "https://github.com/sustainability-software-lab/ca-biositing/pull/442", "commit 66cb070", "https://github.com/sustainability-software-lab/ca-biositing/pull/204", "commit dffea8d", "commit 4f3e0be", "commit d290906", "commit c4cbf2d", "pixi.toml (2026-10-22)"]
---

## Purpose
Developer-facing commands that are not database or cloud related: running tests, serving the API, building docs, and regenerating the analysis dashboards and gallery.

## Key files
| Path:line | Role |
| --- | --- |
| pixi.toml:271-273 | `test` (`python -m pytest tests/ --verbose`) |
| pixi.toml:275-277 | `test-cov` (html + term coverage over `src/ca_biositing`) |
| pixi.toml:266-269 | `start-webservice`: `uvicorn ca_biositing.webservice.main:app --reload` with cwd `src` (no port flag, so port 8000) |
| pixi.toml:375-383 | `generate-openapi` (scripts/generate_openapi.py -> docs/api/openapi.json) and `create-admin` (scripts/create_admin.py), in the webservice feature |
| pixi.toml:396-404 | `docs-serve`, `docs-build` (mkdocs) and `rtd-publish` |
| pixi.toml:247-250 | `db-drift-extract-local`, `-staging`, `-prod`, `db-drift-compare` (see architecture/analysis-db-drift-assessment) |
| pixi.toml:253-256 | `refresh-resource-insights`, `build-resource-analysis-dashboard`, `build-resource-explorer-dashboard`, `build-resource-audit-workbench` |
| pixi.toml:257-261 | `update-gallery`, `refresh-dashboards`, `update-resource-dashboard` (alias), `update-plots` (scripts/regenerate_all_plots.py), `serve-gallery` (http.server on exports/plots, port 8000) |
| pixi.toml:263-264 | `qgis` (depends on `run-qgis` in the gis environment) |
| pixi.toml:279-280 | `submodule-frontend-init` (git submodule update) |
| pixi.toml:316-318 | `frontend-install`, `frontend-dev`, `frontend-build` (npm in `frontend/`) |
| pixi.toml:62-63 | `register-jupyter-kernel`, `jupyter-lab` |

## How it works
- `test` runs the whole `tests/` tree. CI does not use it: `ci.yml` runs pytest per package directory (`src/ca_biositing/{datamodels,pipeline,webservice}`) with coverage, and excludes the `integration` marker for the webservice.
- `start-webservice` needs `src` as cwd because the package is a namespace package (see architecture/webservice-overview).
- Gallery: `update-plots` re-runs the analysis scripts and then `update-gallery`. `refresh-dashboards` is the one-command refresh for the resource suite and gallery (insights, Pages 1-2, Page 3, Product 4, gallery). Neither task builds the drift page; `db-drift-compare` does. `serve-gallery` is local preview only.
- Dashboards viewed through `serve-gallery` call `/v1/qc/*` on `http://localhost:8000` by default (see architecture/analysis-qc-audit-workbench), so a local preview and a local uvicorn cannot both use port 8000 without setting `BIOCIRV_API_BASE`.

## Interfaces
- `docs/api/openapi.json` is generated and checked in; `.pre-commit-config.yaml` excludes `docs/api/` from prettier.
- `mkdocs.yml` `nav` references `api/*.md` and `docs/api/openapi.json` is served by the API reference pages.

## Gotchas
- `pixi run test` collects only `tests/` (which has `agent_harness`, `analysis`, `audit`, `datamodels`, `pipeline`, `webservice` subfolders and loose test files). CI runs pytest against `src/ca_biositing/<package>` paths instead; whether both sets are identical was not checked (confirm with `pytest --collect-only -q`).
- `docs-build` needs the `docs` environment; `pixi run docs-build` from `default` fails if the feature is missing (inferred from `no-default-feature`).
- `qgis` needs the `gis` environment and a desktop session; it is not useful in CI or the devcontainer.
- `generate-openapi` writes a checked-in file, so run it and commit the diff.
- `update-plots` is not run by any workflow; `dashboard-artifacts.yml` runs the dashboard generators directly.

## History
- Gallery and dashboards: `707afa8` (#442, 2026-07-06). Static OpenAPI and docs: `66cb070` (#204, 2026-04-13). Webservice improvements: `dffea8d` (#170).
- Drift tasks: `4f3e0be` (#517, 2026-10-19). Resource dashboard tasks: `d290906` (#518). Five-product gallery: `c4cbf2d` (#525).

## Open questions
- Whether `update-plots` should be part of CI (it re-runs every analysis script and needs fresh data).

# Related Concepts
- [Test suite layout, how to run each suite, and fixture map](testing.md): Test layout and markers (slice prefix)
- [Webservice package layout and app factory](webservice-overview.md): API that start-webservice launches
- [Analysis visualization scripts (analysis/) and how they query the DB](analysis-visualization-scripts.md): Analysis scripts that the gallery regenerates (slice prefix)
- [System overview (start here)](system-overview.md): Hub
- [Five-product BioCirV resource dashboard suite and how each is generated](analysis-resource-dashboard-suite.md): tasks that build the resource suite
- [Multi-environment DB drift assessment (4 layers, local/staging/production)](analysis-db-drift-assessment.md): drift tasks
