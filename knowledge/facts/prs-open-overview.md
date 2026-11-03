---
type: Fact
title: "Open PRs: overview (7)"
description: "Index of the 7 open PRs as of 2026-10-22 (4 non-draft, 3 draft) with red checks, merge conflicts, and open questions; per-PR detail is in facts/pr-<n>."
tags: [prs, open, index]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:28Z" }
status: stable
governance: context
code_refs: [".github/workflows/ci.yml"]
stale_after: "2026-11-15"
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/500", "https://github.com/sustainability-software-lab/ca-biositing/pull/499", "https://github.com/sustainability-software-lab/ca-biositing/pull/482", "https://github.com/sustainability-software-lab/ca-biositing/pull/513", "https://github.com/sustainability-software-lab/ca-biositing/pull/528"]
---

## Purpose
Index of the 7 open PRs as of 2026-10-22 (main at a2c8de8), with merge blockers. Per-PR detail is in `facts/pr-<n>`.

## Key files
None (PR index).

## How it works
Open PRs by author: @petercarbsmith (#498, #513), @avi9664 (#482), @mglbleta (#401 and #177, both drafts), @lsetiawan (#254, draft), and @app/dependabot (#528). Three drafts (#177, #254, #401) and four non-draft PRs (#482, #498, #513, #528).

## Interfaces
- Source: `gh pr list --repo sustainability-software-lab/ca-biositing --state open`, and `gh pr list --state all --search "updated:>=2026-10-16"` for the closures and merges below.

## Gotchas
- Conflicting with main (mergeStateStatus DIRTY): #177, #254, #401, #482, #498. Only #513 and #528 are mergeable and clean.
- Red checks at 2026-10-22: #482 (Alembic, Pulumi Preview, Python py312 and py313, TestPyPI publish; some are reruns), #254 (dependency vulnerability scan), #401 (pre-commit.ci and RTD), #177 (pre-commit.ci), #498 (pre-commit.ci). #513 and #528 have no red checks.
- Closed without merge since 2026-10-16: #499 (2026-10-18), #455, #458, #473, #495 and #500 (2026-10-19). See `facts/prs-closed-unmerged`.
- Merged since 2026-10-16: #514 (2026-10-22, infrastructure ETL second attempt), and the 2026-10-18 to 2026-10-22 dashboard, QC, GCS and webservice stack (#517, #518, #520 to #527, #529 to #533, #535).
- Neither #513 nor #528 has a review.

## History
Open PRs dated 2026-03-13 (#177) through 2026-10-19 (#528). The 2026-10-16 snapshot listed 11 open or draft PRs; the change from 11 to 7 is 6 closures (#455, #458, #473, #495, #499, #500) and 2 new open PRs (#513, #528), with #482 and #498 still open. Snapshot as of 2026-10-22 (HEAD a2c8de8).

## Open questions
- Whether #482 should close now that #514 has merged (inferred overlap; not compared).
- #513 body says "Resolves #506" and "Part of #505"; #505 and children #507 to #512 remain open.
- Whether the three drafts (#177, #254, #401) should be closed or revived; none has had activity since April or June.

## Open PRs
- #528 [chore(deps): bump the actions group across 1 directory with 3 updates](https://github.com/sustainability-software-lab/ca-biositing/pull/528) · @app/dependabot · created 2026-10-19
- #513 [fix(views,etl): replace hardcoded IDs with name joins and add bearing_acres fallback](https://github.com/sustainability-software-lab/ca-biositing/pull/513) · @petercarbsmith · created 2026-10-17
- #498 [feat(skills,viz): add ca-county-map & generative_ui skills and canonical CA county boundary assets](https://github.com/sustainability-software-lab/ca-biositing/pull/498) · @petercarbsmith · created 2026-10-15
- #482 [feat (etl): Add Infrastructure ETL Pipelines](https://github.com/sustainability-software-lab/ca-biositing/pull/482) · @avi9664 · created 2026-09-13
- #401 [food processor etl + geocoding](https://github.com/sustainability-software-lab/ca-biositing/pull/401) · @mglbleta · draft · created 2026-06-05
- #254 [ci: add pip-audit and fix 15 dependency CVEs](https://github.com/sustainability-software-lab/ca-biositing/pull/254) · @lsetiawan · draft · created 2026-04-06
- #177 [[optional] Thorough docs review PR](https://github.com/sustainability-software-lab/ca-biositing/pull/177) · @mglbleta · draft · created 2026-03-13

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state hub.
- [PR #482 (open, conflicting): Infrastructure ETL pipelines (18 datasets) with geocoding](pr-482.md): Per-PR detail.
- [PR #458 (closed unmerged 2026-10-19): CA Biositing Audit Platform, Phase 1 and 2](pr-458.md): Per-PR detail.
- [PR #513 (open): replace hardcoded IDs with name joins in the volume view and ETL transforms](pr-513.md): new open PR in the overview
- [PR #528 (open): dependabot GitHub Actions group bump (setup-pixi 0.11.2, setup-node 7, upload-artifact 7)](pr-528.md): new open PR in the overview
