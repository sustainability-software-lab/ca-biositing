---
type: Architecture
title: "MkDocs site and Read the Docs build: mkdocs.yml, readthedocs.yaml and the docs environment"
description: "How the MkDocs Material site is configured (mkdocstrings for datamodels and pipeline, awesome-pages nav, git revision dates) and built on Read the Docs via pixi."
tags: [tooling, docs, mkdocs, readthedocs]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:26:50Z" }
status: stable
code_refs: ["mkdocs.yml", "readthedocs.yaml", "docs", "docs/api/openapi.json"]
sources: ["mkdocs.yml", "readthedocs.yaml", "commit 66cb070", "https://github.com/sustainability-software-lab/ca-biositing/pull/204", "commit c6a15a6", "commit 235a738"]
governance: context
---

## Purpose
Publishes `docs/` plus selected root files (README, CONTRIBUTING, CHANGELOG, AI_POLICY, SECURITY, LICENSE) as a static site, with API reference generated from docstrings.

## Key files
| Path | Role |
| --- | --- |
| mkdocs.yml | Theme (material, `custom_dir: docs/overrides`), plugins (search, git-revision-date-localized, awesome-pages, mkdocstrings), markdown extensions, nav |
| readthedocs.yaml | RTD build: asdf-installed pixi, `pixi install --frozen -e docs`, `HATCH_VCS_VERSION=$(./scripts/get_version.sh)`, `pixi run rtd-publish` |
| pixi.toml:370-388 | `docs` feature, `docs-serve`, `docs-build`, `rtd-publish` |
| docs/ | Content: architecture.md, pipeline/, datamodels/, webservice/, deployment/, resources/, api/, overrides/, stylesheets/ |

## How it works
- mkdocstrings renders API pages from `src/ca_biositing/datamodels` and `src/ca_biositing/pipeline` (paths in `mkdocs.yml`); the webservice API uses the checked-in `docs/api/openapi.json`.
- Mermaid is supported through the superfences custom fence.
- Every `nav` target in `mkdocs.yml` exists under `docs/` at the time of this review (checked).

## Interfaces
- Inputs: `docs/`, root markdown files, `mkdocs.yml`.
- Outputs: static site under `site/` locally or `$READTHEDOCS_OUTPUT/html` on RTD.
- Callers: Read the Docs; developers via `pixi run docs-serve`.

## Gotchas
- `check-yaml` is excluded for `mkdocs.yml` because of `!!python/name` in the superfences config.
- `readthedocs.yaml` is excluded from prettier, and `docs/api/` is excluded too.
- `mkdocs.yml` `nav` points at `api/index.md` etc.; a file rename breaks the build.
- The optional OKF-to-mkdocs wiring in `.agents/rules/mkdocs-okf-knowledge-bundle.md` is not active: `knowledge/` is not rendered.

## History
- Read the Docs config `c6a15a6` (#67, 2025-11-17); mkdocs config `729e0b6` (#85), local setup docs; API reference and changelog `66cb070` (#204, 2026-04-13); RTD env var fix `235a738` (#381) on readthedocs.yaml.

## Open questions
- Whether `docs-build` should run in CI (no workflow runs it today; the RTD build is the only docs build).

# Related Concepts
- [Pixi tasks for tests, coverage, webservice, docs, gallery and frontend](tooling-task-quality-docs-and-webservice.md): Tasks that generate the OpenAPI file and build docs
- [pixi.toml: workspace, features and environment composition](tooling-pixi-manifest.md): The docs environment this build uses
- [System overview (start here)](system-overview.md): Hub
