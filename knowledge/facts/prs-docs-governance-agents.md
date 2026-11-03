---
type: Fact
title: "Merged PRs: docs, governance, and agent tooling"
description: "Index of merged PRs for README/CITATION/SECURITY/CHANGELOG, MkDocs and agent docs, AGENTS.md and agent-skills tooling, grouped by merge month; through 2026-10-22."
tags: [docs, agents, governance, prs]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:30Z" }
status: stable
governance: context
code_refs: ["AGENTS.md", "agent_docs/**", ".agents/skills/**"]
stale_after: "2026-11-15"
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/440", "https://github.com/sustainability-software-lab/ca-biositing/pull/402", "https://github.com/sustainability-software-lab/ca-biositing/pull/398", "https://github.com/sustainability-software-lab/ca-biositing/pull/259", "https://github.com/sustainability-software-lab/ca-biositing/pull/255", "https://github.com/sustainability-software-lab/ca-biositing/pulls?q=is%3Apr+is%3Amerged", "https://github.com/sustainability-software-lab/ca-biositing/pull/527"]
---

## Purpose
Docs and governance PRs: AGENTS.md and agent_docs, Declarative Agent Skills (skills.json/skills.py), CalVer and CHANGELOG, Zenodo/CITATION, and the SSEC agent harness (#497, 2026-10-16).

Scope: 28 merged PRs. Authors: @lsetiawan (11), @Vraj1234 (8), @petercarbsmith (3), @nikiburggraf (3), @app/pre-commit-ci (1), @app/copilot-swe-agent (1). Grouped by merge month, newest first. Rows merged from 2026-10-17 through 2026-10-22 were added on 2026-10-22; author counts above predate them. "areas" is the top three path categories touched, computed from the PR file list (not reviewed line by line).

## Key files
Areas in this theme are described by the linked architecture concept (`facts/tooling-*`). PR bodies, not files, are the primary source for this index.

## How it works
Index only. Each row links to the PR on GitHub. Re-run `gh pr list --state merged` to refresh; this snapshot is as of HEAD a2c8de8 (2026-10-22).

## Interfaces
- Inputs: GitHub PR metadata (`gh pr list --repo sustainability-software-lab/ca-biositing`).
- Outputs: none. This concept is a lookup table.

## Gotchas
- Titles are as merged; some PRs were re-filed (e.g. #422 and #431 share a title; #247 and #256 are a closed duplicate of #248/#257).
- Merge months use `mergedAt`; PRs that were never merged are in `facts/prs-closed-unmerged`.

## History
28 PRs in this theme. Earliest merged 2025-08 (#10); latest 2026-10-19 (#527).

## Open questions
- Whether the author list reflects current ownership (inferred from PR authorship only; confirm with maintainers).

## Merged PRs by month

### 2026-10 (1)
- #527 [docs(qc,dashboards): document GCS store, portal auth, and QC workbench](https://github.com/sustainability-software-lab/ca-biositing/pull/527) · @petercarbsmith · 2026-10-19

### 2026-06 (3)
- #440 [Add unified update-static-resource-info task](https://github.com/sustainability-software-lab/ca-biositing/pull/440) · @petercarbsmith · 2026-06-23 · areas: deploy/resources, docs, other
- #398 [✨ Integrate Declarative Agent Skills Management](https://github.com/sustainability-software-lab/ca-biositing/pull/398) · @petercarbsmith · 2026-06-12 · areas: agent-skills, docs, other
- #402 [Preserve case for resource description and note fields](https://github.com/sustainability-software-lab/ca-biositing/pull/402) · @petercarbsmith · 2026-06-11 · areas: docs, other, scripts

### 2026-04 (9)
- #259 [fix: update contributing links in README for MkDocs compatibility](https://github.com/sustainability-software-lab/ca-biositing/pull/259) · @Vraj1234 · 2026-04-14 · areas: docs, other, datamodels
- #225 [docs: address reviewer feedback from issues #208-#215](https://github.com/sustainability-software-lab/ca-biositing/pull/225) · @Vraj1234 · 2026-04-13 · areas: docs, webservice
- #204 [Docs/changelog and static api reference](https://github.com/sustainability-software-lab/ca-biositing/pull/204) · @Vraj1234 · 2026-04-13 · areas: docs, other, scripts
- #255 [Add DOI to CITATION.cff file](https://github.com/sustainability-software-lab/ca-biositing/pull/255) · @lsetiawan · 2026-04-06 · areas: other
- #252 [docs: Revise README with new badges and acknowledgments](https://github.com/sustainability-software-lab/ca-biositing/pull/252) · @lsetiawan · 2026-04-06 · areas: docs
- #251 [docs: add CITATION.cff](https://github.com/sustainability-software-lab/ca-biositing/pull/251) · @lsetiawan · 2026-04-06 · areas: other
- #253 [docs: add SECURITY.md, CHANGELOG.md, and adopt CalVer](https://github.com/sustainability-software-lab/ca-biositing/pull/253) · @lsetiawan · 2026-04-06 · areas: docs, other
- #250 [Update copyright year in LICENSE file](https://github.com/sustainability-software-lab/ca-biositing/pull/250) · @lsetiawan · 2026-04-03 · areas: other
- #237 [docs: overhaul README for Zenodo publication](https://github.com/sustainability-software-lab/ca-biositing/pull/237) · @lsetiawan · 2026-04-01 · areas: docs

### 2026-03 (4)
- #188 [docs: add package CONTRIBUTING guides and update repo URLs](https://github.com/sustainability-software-lab/ca-biositing/pull/188) · @Vraj1234 · 2026-03-19 · areas: docs, other
- #184 [docs: streamline namespace package READMEs for PyPI](https://github.com/sustainability-software-lab/ca-biositing/pull/184) · @lsetiawan · 2026-03-19 · areas: datamodels, pipeline, webservice
- #180 [refactor: Update old repo links](https://github.com/sustainability-software-lab/ca-biositing/pull/180) · @lsetiawan · 2026-03-19 · areas: docs, datamodels, pipeline
- #142 [docs: Update documentation and rendering](https://github.com/sustainability-software-lab/ca-biositing/pull/142) · @Vraj1234 · 2026-03-02 · areas: pipeline, docs, other

### 2026-02 (1)
- #111 [chore: Clean old artifacts](https://github.com/sustainability-software-lab/ca-biositing/pull/111) · @lsetiawan · 2026-02-12 · areas: other, webservice

### 2026-01 (1)
- #85 [docs: add local setup guide and update mkdocs config](https://github.com/sustainability-software-lab/ca-biositing/pull/85) · @Vraj1234 · 2026-01-27 · areas: docs, other, deploy/resources

### 2025-11 (1)
- #67 [Consolidation documentation & configuring Mkdocs to host on ReadtheDocs](https://github.com/sustainability-software-lab/ca-biositing/pull/67) · @Vraj1234 · 2025-11-17 · areas: docs, other, pipeline

### 2025-10 (5)
- #49 [ module(frontend): add github frontend submodule](https://github.com/sustainability-software-lab/ca-biositing/pull/49) · @Vraj1234 · 2025-10-30 · areas: other, docs
- #65 [fix: Fix link to pixi](https://github.com/sustainability-software-lab/ca-biositing/pull/65) · @lsetiawan · 2025-10-29 · areas: other
- #51 [feat: add GitHub Codespaces devcontainer configuration](https://github.com/sustainability-software-lab/ca-biositing/pull/51) · @app/copilot-swe-agent · 2025-10-27 · areas: other
- #42 [chore: update pre-commit hooks](https://github.com/sustainability-software-lab/ca-biositing/pull/42) · @app/pre-commit-ci · 2025-10-27 · areas: docs, other
- #31 [feat: Add AGENTS.md and copilot env setup](https://github.com/sustainability-software-lab/ca-biositing/pull/31) · @lsetiawan · 2025-10-14 · areas: ci, docs

### 2025-09 (2)
- #25 [ci: Add CI/CD actions](https://github.com/sustainability-software-lab/ca-biositing/pull/25) · @nikiburggraf · 2025-09-11 · areas: other, ci, docs
- #24 [chore: Add community health files](https://github.com/sustainability-software-lab/ca-biositing/pull/24) · @nikiburggraf · 2025-09-10 · areas: ci, other, docs

### 2025-08 (1)
- #10 [chore: Create LICENSE](https://github.com/sustainability-software-lab/ca-biositing/pull/10) · @nikiburggraf · 2025-08-28 · areas: other

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state hub for the repo.
