---
type: Decision
title: "History: GCP staging and production deployment automation (Feb to Apr 2026)"
description: "How Cloud Run staging then production, Artifact Registry, GHCR routing, and GitHub Actions deploy were built in a burst of Feb to Apr 2026 commits."
tags: [deployment, gcp, cloud-run, github-actions, history]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:00Z" }
status: stable
code_refs: [".github/workflows/deploy-staging.yml", ".github/workflows/deploy-production.yml", ".github/workflows/cd.yml", "deployment/README.md", "deployment/cloud/gcp/infrastructure/wif.py"]
sources: ["commit 5bdefc9", "commit 13675d8", "commit 12b3592", "commit 9ea84ed", "commit cf8b07f", "https://github.com/sustainability-software-lab/ca-biositing/pull/189", "https://github.com/sustainability-software-lab/ca-biositing/pull/228"]
governance: context
---

## Purpose
Explains the cloud deploy workflows and the many IAM and image fixes that shaped them.

## Key files
| Path | Role |
|---|---|
| .github/workflows/deploy-staging.yml | Staging deploy (11 changes) |
| .github/workflows/deploy-production.yml | Production deploy (8 changes) |
| .github/workflows/cd.yml | CD with namespace-package path filters (8) |
| deployment/README.md | Deployment overview |

## How it works
- b9ee91e (PR #78, Niki Burggraf, 2025-12-04): GCP backend and cloud docs; 5ab7c44 (PR #75): cloud staging DB.
- 5bdefc9 (PR #125, 2026-02-19): staging via Pulumi and Cloud Run; 3edcb17 (PR #127): staging ETL parity.
- 13675d8 (PR #189, 2026-03-20): GitHub Actions automation; images moved from GCR to GHCR (4e271b6, #192) then routed through an Artifact Registry remote repo (12b3592, #193).
- Many IAM fixes in one week (7c86993, ca4d573, f6ee2ee, 9ea84ed, d2bde31): deployer SA needed storage.admin and AR admin.
- 27252ae (PR #216): ETL triggered after staging deploy; 14f5740 (PR #238) production trigger-etl; 4a27f23 (PR #240) waits for docker-build.
- 8317ee8 (PR #175): admin user seeded via Pulumi and a Cloud Run job.
- 9ea84ed and d2bde31 have no PR number in their subjects.

## Interfaces
Inputs: GitHub Actions secrets, GCP WIF, GHCR images. Outputs: Cloud Run services and the staging/production databases. Callers: CI on push and workflow_dispatch.

## Gotchas
- Several commits are "fix:" chains that show trial-and-error on IAM; the final IAM model is in deployment/cloud/gcp/infrastructure/wif.py.
- Image tags can be resolved from the latest docker-build run on workflow_dispatch (87e6f0d), a source of confusion.
- credentials.json must be present for ETL tasks in Cloud Run; cf8b07f fixed this on 2026-06-01.

## History
Key SHAs and PRs are listed above; the burst is 2026-03-19 to 2026-03-30.

## Open questions
- Current production database hosting details are not in git (inferred; confirm in deployment docs).

# Related Concepts
- [Decision: Pulumi Python instead of OpenTofu/HCL for GCP infrastructure](../decisions/infra-pulumi-over-opentofu.md): the IaC that these workflows run
- [GCP cloud topology per environment (Cloud Run, Cloud SQL, AR proxies, GCS, WIF)](../architecture/infra-cloud-topology.md): current infrastructure described by this history (id prefix architecture/infra-*)
- [Project history eras (2025-08 to 2026-10)](history-eras.md): E4 and E6 eras
