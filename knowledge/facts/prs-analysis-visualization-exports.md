---
type: Fact
title: "Merged PRs: analysis, visualizations, and exports"
description: "Index of merged PRs that changed analysis/ and exports/ visualizations, dashboards, QC workbench and reports, grouped by merge month; merged rows through 2026-10-22 included."
tags: [analysis, visualization, exports, prs]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:29Z" }
status: stable
governance: context
code_refs: ["analysis/**", "exports/**"]
stale_after: "2026-11-15"
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/486", "https://github.com/sustainability-software-lab/ca-biositing/pull/483", "https://github.com/sustainability-software-lab/ca-biositing/pull/481", "https://github.com/sustainability-software-lab/ca-biositing/pull/469", "https://github.com/sustainability-software-lab/ca-biositing/pull/468", "https://github.com/sustainability-software-lab/ca-biositing/pulls?q=is%3Apr+is%3Amerged", "https://github.com/sustainability-software-lab/ca-biositing/pull/535", "https://github.com/sustainability-software-lab/ca-biositing/pull/530", "https://github.com/sustainability-software-lab/ca-biositing/pull/526", "https://github.com/sustainability-software-lab/ca-biositing/pull/525", "https://github.com/sustainability-software-lab/ca-biositing/pull/518", "https://github.com/sustainability-software-lab/ca-biositing/pull/517"]
---

## Purpose
Analysis PRs: pretreatment variance, fermentation distribution, provider and pretreatment filters, and the visualization gallery.

Scope: 14 merged PRs. Authors: @petercarbsmith (8). Grouped by merge month, newest first. Rows merged from 2026-10-17 through 2026-10-22 were added on 2026-10-22; author counts above predate them. "areas" is the top three path categories touched, computed from the PR file list (not reviewed line by line).

## Key files
Areas in this theme are described by the linked architecture concept (`architecture/analysis-*`). PR bodies, not files, are the primary source for this index.

## How it works
Index only. Each row links to the PR on GitHub. Re-run `gh pr list --state merged` to refresh; this snapshot is as of HEAD a2c8de8 (2026-10-22).

## Interfaces
- Inputs: GitHub PR metadata (`gh pr list --repo sustainability-software-lab/ca-biositing`).
- Outputs: none. This concept is a lookup table.

## Gotchas
- Titles are as merged; some PRs were re-filed (e.g. #422 and #431 share a title; #247 and #256 are a closed duplicate of #248/#257).
- Merge months use `mergedAt`; PRs that were never merged are in `facts/prs-closed-unmerged`.

## History
14 PRs in this theme. Earliest merged 2025-08 (#10); latest 2026-10-22 (#535).

## Open questions
- Whether the author list reflects current ownership (inferred from PR authorship only; confirm with maintainers).

## Merged PRs by month

### 2026-10 (6)
- #517 [feat(audit): add 4-layer live DB drift assessment and dashboard](https://github.com/sustainability-software-lab/ca-biositing/pull/517) · @petercarbsmith · 2026-10-19
- #518 [feat(dashboards): add 3-page resource analytics and slice exporter](https://github.com/sustainability-software-lab/ca-biositing/pull/518) · @petercarbsmith · 2026-10-19
- #525 [feat(dashboards): add Product 4 QC Audit Workbench and gallery](https://github.com/sustainability-software-lab/ca-biositing/pull/525) · @petercarbsmith · 2026-10-19
- #526 [feat(qc): add live QC overlay and tray-to-workbench export](https://github.com/sustainability-software-lab/ca-biositing/pull/526) · @petercarbsmith · 2026-10-19
- #530 [fix(viz): write dashboard snapshot in explorer and fallback in workbench](https://github.com/sustainability-software-lab/ca-biositing/pull/530) · @petercarbsmith · 2026-10-21
- #535 [fix(viz): restore Report a Bug modal across full BioCirV dashboard suite](https://github.com/sustainability-software-lab/ca-biositing/pull/535) · @petercarbsmith · 2026-10-22

### 2026-09 (3)
- #486 [Add experiment_name filter to composition distribution visualizations](https://github.com/sustainability-software-lab/ca-biositing/pull/486) · @petercarbsmith · 2026-09-24 · areas: analysis/exports
- #483 [feat(viz): click-to-export audit tool for Vega-Lite dashboards](https://github.com/sustainability-software-lab/ca-biositing/pull/483) · @petercarbsmith · 2026-09-17 · areas: analysis/exports, scripts
- #481 [Fix XRF distribution visualization](https://github.com/sustainability-software-lab/ca-biositing/pull/481) · @petercarbsmith · 2026-09-08 · areas: analysis/exports

### 2026-08 (2)
- #469 [fix: add missing html and gallery updates for pretreatment variance](https://github.com/sustainability-software-lab/ca-biositing/pull/469) · @petercarbsmith · 2026-08-17 · areas: analysis/exports
- #468 [feat: add pretreatment variance visualization](https://github.com/sustainability-software-lab/ca-biositing/pull/468) · @petercarbsmith · 2026-08-17 · areas: analysis/exports

### 2026-07 (3)
- #463 [Update fermentation distribution visualization parameters and yields](https://github.com/sustainability-software-lab/ca-biositing/pull/463) · @petercarbsmith · 2026-07-31 · areas: analysis/exports
- #452 [feat(viz): add provider and refined pretreatment method filters](https://github.com/sustainability-software-lab/ca-biositing/pull/452) · @petercarbsmith · 2026-07-13 · areas: analysis/exports
- #442 [Feat: Analysis Visualization Gallery and Automated Deployment](https://github.com/sustainability-software-lab/ca-biositing/pull/442) · @petercarbsmith · 2026-07-06 · areas: analysis/exports, other, scripts

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state hub for the repo.
