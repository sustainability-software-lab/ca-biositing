---
type: Fact
title: "Merged PRs: infrastructure, GCP deployment, and GitHub workflows"
description: "Index of merged PRs for Pulumi, GCP deployment, Cloud Run, buckets and CI deploy workflows, grouped by merge month; merged rows through 2026-10-22 included."
tags: [infra, deploy, pulumi, gcp, ci, prs]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:30Z" }
status: stable
governance: context
code_refs: [".github/workflows/**", "deployment/**"]
stale_after: "2026-11-15"
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/464", "https://github.com/sustainability-software-lab/ca-biositing/pull/392", "https://github.com/sustainability-software-lab/ca-biositing/pull/387", "https://github.com/sustainability-software-lab/ca-biositing/pull/385", "https://github.com/sustainability-software-lab/ca-biositing/pull/371", "https://github.com/sustainability-software-lab/ca-biositing/pulls?q=is%3Apr+is%3Amerged", "https://github.com/sustainability-software-lab/ca-biositing/pull/533", "https://github.com/sustainability-software-lab/ca-biositing/pull/522", "https://github.com/sustainability-software-lab/ca-biositing/pull/521", "https://github.com/sustainability-software-lab/ca-biositing/pull/520"]
---

## Purpose
Infrastructure PRs: Pulumi IaC (migrated from OpenTofu), Cloud Run staging then production, GHCR/Artifact Registry images, oauth2-proxy for Prefect UI, DB hardening and reset scripts, and workflow triggers.

Scope: 47 merged PRs. Authors: @lsetiawan (30), @petercarbsmith (8), @nikiburggraf (2), @Vraj1234 (2), @tylerhuntington (1). Grouped by merge month, newest first. Rows merged from 2026-10-17 through 2026-10-22 were added on 2026-10-22; author counts above predate them. "areas" is the top three path categories touched, computed from the PR file list (not reviewed line by line).

## Key files
Areas in this theme are described by the linked architecture concept (`architecture/infra-*`). PR bodies, not files, are the primary source for this index.

## How it works
Index only. Each row links to the PR on GitHub. Re-run `gh pr list --state merged` to refresh; this snapshot is as of HEAD a2c8de8 (2026-10-22).

## Interfaces
- Inputs: GitHub PR metadata (`gh pr list --repo sustainability-software-lab/ca-biositing`).
- Outputs: none. This concept is a lookup table.

## Gotchas
- Titles are as merged; some PRs were re-filed (e.g. #422 and #431 share a title; #247 and #256 are a closed duplicate of #248/#257).
- Merge months use `mergedAt`; PRs that were never merged are in `facts/prs-closed-unmerged`.

## History
47 PRs in this theme. Earliest merged 2025-08 (#10); latest 2026-10-21 (#533).

## Open questions
- Whether the author list reflects current ownership (inferred from PR authorship only; confirm with maintainers).

## Merged PRs by month

### 2026-10 (4)
- #520 [feat(infra): provision GCS dashboards bucket and WIF SAs (#519)](https://github.com/sustainability-software-lab/ca-biositing/pull/520) · @petercarbsmith · 2026-10-19
- #521 [ci(dashboards): wire GCS workflows and minimal fixtures (#519)](https://github.com/sustainability-software-lab/ca-biositing/pull/521) · @petercarbsmith · 2026-10-19
- #522 [chore(repo): untrack generated artifacts and add guard (#519)](https://github.com/sustainability-software-lab/ca-biositing/pull/522) · @petercarbsmith · 2026-10-19
- #533 [fix(ci): prevent dashboard-artifacts workflow from overwriting GCS latest with seed fixtures](https://github.com/sustainability-software-lab/ca-biositing/pull/533) · @petercarbsmith · 2026-10-21

### 2026-09 (1)
- #464 [fix: db reset script database connection and safety checks](https://github.com/sustainability-software-lab/ca-biositing/pull/464) · @petercarbsmith · 2026-09-29 · areas: docs, deploy/resources, scripts

### 2026-06 (3)
- #392 [Db fix again](https://github.com/sustainability-software-lab/ca-biositing/pull/392) · @petercarbsmith · 2026-06-02 · areas: deploy/resources
- #387 [Db reset](https://github.com/sustainability-software-lab/ca-biositing/pull/387) · @petercarbsmith · 2026-06-01 · areas: scripts, other, alembic
- #385 [fixing issue where cloud run can’t find credentials.json](https://github.com/sustainability-software-lab/ca-biositing/pull/385) · @petercarbsmith · 2026-06-01 · areas: deploy/resources, pipeline

### 2026-05 (3)
- #371 [Resource image fix](https://github.com/sustainability-software-lab/ca-biositing/pull/371) · @petercarbsmith · 2026-05-22 · areas: deploy/resources, other, alembic
- #366 [Db secure](https://github.com/sustainability-software-lab/ca-biositing/pull/366) · @petercarbsmith · 2026-05-18 · areas: other
- #363 [Postgres DB Security hardening](https://github.com/sustainability-software-lab/ca-biositing/pull/363) · @petercarbsmith · 2026-05-18 · areas: other, deploy/resources

### 2026-04 (2)
- #249 [fix: remove over-privileged IAM role bindings and add dedicated frontend SA](https://github.com/sustainability-software-lab/ca-biositing/pull/249) · @tylerhuntington · 2026-04-03 · areas: deploy/resources
- #245 [docs: update contributing links and add alembic to docker-build triggers](https://github.com/sustainability-software-lab/ca-biositing/pull/245) · @lsetiawan · 2026-04-02 · areas: ci, docs

### 2026-03 (27)
- #240 [feat: wait for docker-build before deploying production](https://github.com/sustainability-software-lab/ca-biositing/pull/240) · @lsetiawan · 2026-03-30 · areas: ci
- #238 [feat: add trigger-etl workflow for production](https://github.com/sustainability-software-lab/ca-biositing/pull/238) · @lsetiawan · 2026-03-30 · areas: ci
- #239 [feat: add Pulumi preview job to deploy-production workflow](https://github.com/sustainability-software-lab/ca-biositing/pull/239) · @lsetiawan · 2026-03-30 · areas: ci
- #228 [feat: bootstrap production environment alongside staging](https://github.com/sustainability-software-lab/ca-biositing/pull/228) · @lsetiawan · 2026-03-30 · areas: deploy/resources, ci
- #227 [refactor: separate ETL trigger into its own workflow](https://github.com/sustainability-software-lab/ca-biositing/pull/227) · @lsetiawan · 2026-03-30 · areas: ci
- #226 [fix: use volume-mounted secrets for oauth2-proxy](https://github.com/sustainability-software-lab/ca-biositing/pull/226) · @lsetiawan · 2026-03-30 · areas: deploy/resources
- #216 [feat: trigger ETL pipeline automatically after staging deploy](https://github.com/sustainability-software-lab/ca-biositing/pull/216) · @Vraj1234 · 2026-03-27 · areas: ci, other, deploy/resources
- #223 [feat: rename auth-proxy to prefect-auth and skip login page](https://github.com/sustainability-software-lab/ca-biositing/pull/223) · @lsetiawan · 2026-03-27 · areas: deploy/resources, scripts
- #222 [feat: add oauth2-proxy Cloud Run service for Prefect UI auth](https://github.com/sustainability-software-lab/ca-biositing/pull/222) · @lsetiawan · 2026-03-27 · areas: deploy/resources
- #221 [feat: add oauth2-proxy to local Docker Compose for Prefect UI auth](https://github.com/sustainability-software-lab/ca-biositing/pull/221) · @lsetiawan · 2026-03-27 · areas: deploy/resources
- #203 [feat: parameterize infrastructure for multi-environment deployment](https://github.com/sustainability-software-lab/ca-biositing/pull/203) · @lsetiawan · 2026-03-24 · areas: deploy/resources, scripts, ci
- #202 [Create biocirv_bucket GCS bucket](https://github.com/sustainability-software-lab/ca-biositing/pull/202) · @petercarbsmith · 2026-03-23 · areas: deploy/resources
- #200 [ci: add path filters to CD workflow for namespace packages](https://github.com/sustainability-software-lab/ca-biositing/pull/200) · @lsetiawan · 2026-03-23 · areas: ci
- #196 [fix: add AR admin IAM role and dependency ordering for deployer SA](https://github.com/sustainability-software-lab/ca-biositing/pull/196) · @lsetiawan · 2026-03-20 · areas: deploy/resources
- #195 [Update workflow paths for Docker build triggers](https://github.com/sustainability-software-lab/ca-biositing/pull/195) · @lsetiawan · 2026-03-20 · areas: ci
- #194 [fix: grant deployer SA AR admin role and add Cloud Run→AR dependency](https://github.com/sustainability-software-lab/ca-biositing/pull/194) · @lsetiawan · 2026-03-20 · areas: deploy/resources
- #193 [fix: route GHCR images through Artifact Registry remote repo](https://github.com/sustainability-software-lab/ca-biositing/pull/193) · @lsetiawan · 2026-03-20 · areas: deploy/resources, scripts, other
- #192 [feat: pull Cloud Run images from GHCR instead of GCR](https://github.com/sustainability-software-lab/ca-biositing/pull/192) · @lsetiawan · 2026-03-20 · areas: deploy/resources, scripts, ci
- #191 [fix: grant deployer SA storage access to Cloud Build bucket](https://github.com/sustainability-software-lab/ca-biositing/pull/191) · @lsetiawan · 2026-03-20 · areas: deploy/resources
- #190 [fix: move CI pixi tasks to shell scripts for cross-platform compatibility](https://github.com/sustainability-software-lab/ca-biositing/pull/190) · @lsetiawan · 2026-03-20 · areas: scripts, other
- #189 [feat: automate GCP staging deployment via GitHub Actions](https://github.com/sustainability-software-lab/ca-biositing/pull/189) · @lsetiawan · 2026-03-20 · areas: deploy/resources, ci, other
- #187 [build: fix Docker builds broken by pixi lock file removal](https://github.com/sustainability-software-lab/ca-biositing/pull/187) · @lsetiawan · 2026-03-19 · areas: deploy/resources, other
- #185 [build: Remove pixi lock file](https://github.com/sustainability-software-lab/ca-biositing/pull/185) · @lsetiawan · 2026-03-19 · areas: other, pipeline
- #183 [chore: update frontend submodule to latest main](https://github.com/sustainability-software-lab/ca-biositing/pull/183) · @lsetiawan · 2026-03-19 · areas: other
- #175 [feat: seed admin user via Pulumi and Cloud Run job](https://github.com/sustainability-software-lab/ca-biositing/pull/175) · @lsetiawan · 2026-03-18 · areas: deploy/resources, other
- #151 [feat: activate PyPI releases for namespace packages](https://github.com/sustainability-software-lab/ca-biositing/pull/151) · @Vraj1234 · 2026-03-18 · areas: datamodels, pipeline, webservice
- #164 [ci: add Alembic migrations validation workflow](https://github.com/sustainability-software-lab/ca-biositing/pull/164) · @lsetiawan · 2026-03-03 · areas: alembic, ci, datamodels

### 2026-02 (5)
- #130 [feat: add freeform general issue template](https://github.com/sustainability-software-lab/ca-biositing/pull/130) · @lsetiawan · 2026-02-23 · areas: ci
- #126 [fix: Fix prefect flows after merging all (local-only)](https://github.com/sustainability-software-lab/ca-biositing/pull/126) · @lsetiawan · 2026-02-20 · areas: alembic, deploy/resources, pipeline
- #125 [feat: GCP staging deployment via Pulumi + Cloud Run](https://github.com/sustainability-software-lab/ca-biositing/pull/125) · @lsetiawan · 2026-02-20 · areas: deploy/resources, pipeline, docs
- #114 [feat: add resource_info assets and GitHub Pages site](https://github.com/sustainability-software-lab/ca-biositing/pull/114) · @lsetiawan · 2026-02-13 · areas: deploy/resources, scripts, ci
- #110 [feat: migrate infrastructure-as-code from OpenTofu to Pulumi Python](https://github.com/sustainability-software-lab/ca-biositing/pull/110) · @lsetiawan · 2026-02-12 · areas: deploy/resources, other, docs

### 2025-12 (2)
- #78 [feat, docs: Add GCP backend and cloud documentation](https://github.com/sustainability-software-lab/ca-biositing/pull/78) · @nikiburggraf · 2025-12-05 · areas: docs, deploy/resources, other
- #75 [feat: Add cloud staging database](https://github.com/sustainability-software-lab/ca-biositing/pull/75) · @nikiburggraf · 2025-12-01 · areas: other, deploy/resources

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state hub for the repo.
