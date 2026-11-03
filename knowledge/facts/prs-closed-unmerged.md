---
type: Fact
title: Closed-unmerged PRs (28)
description: "The 28 PRs closed without merging as of 2026-10-22, with the superseding PR where the thread names one; use before re-proposing similar work."
tags: [prs, history, closed]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:28Z" }
status: stable
governance: context
code_refs: ["AGENTS.md"]
stale_after: "2026-11-15"
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/484", "https://github.com/sustainability-software-lab/ca-biositing/pull/433", "https://github.com/sustainability-software-lab/ca-biositing/pull/393", "https://github.com/sustainability-software-lab/ca-biositing/pull/315", "https://github.com/sustainability-software-lab/ca-biositing/pull/267", "https://github.com/sustainability-software-lab/ca-biositing/pull/500", "https://github.com/sustainability-software-lab/ca-biositing/pull/499", "https://github.com/sustainability-software-lab/ca-biositing/pull/495", "https://github.com/sustainability-software-lab/ca-biositing/pull/473", "https://github.com/sustainability-software-lab/ca-biositing/pull/458", "https://github.com/sustainability-software-lab/ca-biositing/pull/455"]
---

## Purpose
Record of PRs closed without merge, so readers do not assume they landed. As of 2026-10-22 there are 28 such PRs; six closed on 2026-10-18 and 2026-10-19.

## Key files
None; PR records only. Relevant code is in the merged themes (see `facts/prs-*`).

## How it works
Closed without merge; the title-matched re-files below are verified by identical titles only: #247 and #248 both titled "feat: per-client API keys with per-key rate limiting"; #256 and #257 both titled "fix: reject unknown fields on PATCH /v1/auth/api-keys with 422". Other closures were not traced to a replacement; check the closing comments before assuming supersession.

## Interfaces
- Inputs: `gh pr list --state closed`.

## Gotchas
- Closed is not necessarily "rejected": #247 and #256 were re-filed under the same titles as #248 and #257, which merged.
- #495 and #499 were closed with a stated reason (dependabot "no longer needed"; author split into a stack); #455, #458 and #473 closed with no reason in their threads. Closed is not always superseded.
- Closed dependabot group PRs (#206, #224, #242) were not merged; later group bumps merged (e.g. #262, #445). Check the current lockfile rather than these.

## History
28 closed-unmerged PRs as of 2026-10-22, opened from 2025-10 to 2026-10; six were closed on 2026-10-18 and 2026-10-19 (#455, #458, #473, #495, #499, #500). Snapshot as of HEAD a2c8de8 (2026-10-22). Most recent opened PR among the closed set: #484 (MCP server refine, opened 2026-09-18). Closed Prefect/etl_merge PRs (#34, #43, #45, #46, Oct 2025) ran alongside the merged #26 and #53 ETL merge.

## Open questions
- Whether #79 (LinkML + SQLAlchemy integration, closed) work was carried into the merged LinkML-to-SQLModel migration #112 (inferred from titles; confirm with the PR discussion).
- Whether #433 (usda_census_view performance) and #393 (geoid standardization) were reimplemented elsewhere (not traced; confirm).

## Closed PRs
- #500 [feat(sargassum): add Sargassum analytical dashboards, Excel workbook & visual reports](https://github.com/sustainability-software-lab/ca-biositing/pull/500) · @petercarbsmith · opened 2026-10-16 · closed 2026-10-19 (superseded by the #520 to #527 stack (author comment))
- #499 [feat(dashboards,audit): add BioCirV DB environment drift monitor, modular resource explorer & CI/CD pipeline](https://github.com/sustainability-software-lab/ca-biositing/pull/499) · @petercarbsmith · opened 2026-10-16 · closed 2026-10-18 (split into a two-PR stack (author comment; #517 and #518 inferred by title))
- #495 [chore(deps): bump prefix-dev/setup-pixi from 0.10.2 to 0.11.0 in the actions group across 1 directory](https://github.com/sustainability-software-lab/ca-biositing/pull/495) · @app/dependabot · opened 2026-10-14 · closed 2026-10-19 (dependabot: bump "no longer needed")
- #473 [feat: add cotton and sweet potato biomass report](https://github.com/sustainability-software-lab/ca-biositing/pull/473) · @petercarbsmith · opened 2026-08-26 · closed 2026-10-19 (no reason in thread)
- #458 [feat: CA Biositing Audit Platform (Phase 1 & 2)](https://github.com/sustainability-software-lab/ca-biositing/pull/458) · @petercarbsmith · opened 2026-07-17 · closed 2026-10-19 (no reason in thread)
- #455 [feat: Skill-Based Data Auditor Phase 1](https://github.com/sustainability-software-lab/ca-biositing/pull/455) · @petercarbsmith · opened 2026-07-13 · closed 2026-10-19 (no reason in thread)
- #484 [feat(webservice): Refine and verify MCP server implementation](https://github.com/sustainability-software-lab/ca-biositing/pull/484) · @petercarbsmith · opened 2026-09-18 · areas: webservice, deploy/resources, docs
- #433 [Performance optimization for usda_census_view](https://github.com/sustainability-software-lab/ca-biositing/pull/433) · @petercarbsmith · opened 2026-06-20 · areas: pipeline
- #393 [Feat: Standardize geoid/county names with new static resource for seeding place table and modify views](https://github.com/sustainability-software-lab/ca-biositing/pull/393) · @petercarbsmith · opened 2026-06-02 · areas: pipeline, other, datamodels
- #315 [feat: add biodiesel plants ETL](https://github.com/sustainability-software-lab/ca-biositing/pull/315) · @avi9664 · opened 2026-05-01 · areas: pipeline, deploy/resources, datamodels
- #267 [feat: load biodiesel-plants, LocationAddress, and Places into database](https://github.com/sustainability-software-lab/ca-biositing/pull/267) · @avi9664 · opened 2026-04-22 · areas: datamodels, docs, alembic
- #256 [fix: reject unknown fields on PATCH /v1/auth/api-keys with 422](https://github.com/sustainability-software-lab/ca-biositing/pull/256) · @tylerhuntington · opened 2026-04-06 · areas: webservice, tests
- #247 [feat: per-client API keys with per-key rate limiting](https://github.com/sustainability-software-lab/ca-biositing/pull/247) · @tylerhuntington · opened 2026-04-03 · areas: webservice, datamodels, alembic
- #246 [[feature] Added transport, storage, production, end use, pricing schema and MVs](https://github.com/sustainability-software-lab/ca-biositing/pull/246) · @mglbleta · opened 2026-04-03 · areas: datamodels, alembic, docs
- #242 [chore(deps): bump the actions group across 1 directory with 6 updates](https://github.com/sustainability-software-lab/ca-biositing/pull/242) · @app/dependabot · opened 2026-04-01 · areas: ci
- #224 [chore(deps): bump the actions group across 1 directory with 5 updates](https://github.com/sustainability-software-lab/ca-biositing/pull/224) · @app/dependabot · opened 2026-03-27 · areas: ci
- #206 [chore(deps): bump the actions group with 4 updates](https://github.com/sustainability-software-lab/ca-biositing/pull/206) · @app/dependabot · opened 2026-03-25 · areas: ci
- #201 [Feat gcs bucket](https://github.com/sustainability-software-lab/ca-biositing/pull/201) · @petercarbsmith · opened 2026-03-23 · areas: deploy/resources, other
- #199 [feat: Create biocirv_bucket for GCP bucket storage](https://github.com/sustainability-software-lab/ca-biositing/pull/199) · @petercarbsmith · opened 2026-03-23 · areas: deploy/resources, other
- #160 [feat: Cloud SQL Public IP Allowlist via Pulumi Secrets](https://github.com/sustainability-software-lab/ca-biositing/pull/160) · @petercarbsmith · opened 2026-03-02 · areas: deploy/resources, docs
- #148 [changed to lowecase, altered material view pointer to api_name](https://github.com/sustainability-software-lab/ca-biositing/pull/148) · @mglbleta · opened 2026-02-26 · areas: docs, alembic, other
- #128 [fix: restore migrate DATABASE_URL and deduplicate analysis loaders](https://github.com/sustainability-software-lab/ca-biositing/pull/128) · @Vraj1234 · opened 2026-02-22 · areas: pipeline, other
- #109 [USDA ETL feat](https://github.com/sustainability-software-lab/ca-biositing/pull/109) · @mglbleta · opened 2026-02-11 · areas: pipeline, docs, other
- #79 [feat: LinkML and SQLAlchemy Schema Integration](https://github.com/sustainability-software-lab/ca-biositing/pull/79) · @petercarbsmith · opened 2025-12-09 · areas: datamodels, docs, other
- #46 [feat: Prefect implementation and alembic reset](https://github.com/sustainability-software-lab/ca-biositing/pull/46) · @petercarbsmith · opened 2025-10-22 · areas: other, docs, alembic
- #45 [Peter testing](https://github.com/sustainability-software-lab/ca-biositing/pull/45) · @petercarbsmith · opened 2025-10-22 · areas: other, docs
- #43 [Peter alembic fix](https://github.com/sustainability-software-lab/ca-biositing/pull/43) · @petercarbsmith · opened 2025-10-22 · areas: other, docs
- #34 [Update GCP_SETUP.md](https://github.com/sustainability-software-lab/ca-biositing/pull/34) · @mglbleta · opened 2025-10-15 · areas: docs

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state hub.
- [Merged PRs: datamodels, Alembic migrations, and materialized views](prs-datamodels-migrations-views.md): Merged schema PRs that replaced several closed LinkML and schema attempts.
