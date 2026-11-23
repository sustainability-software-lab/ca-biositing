---
type: Fact
title: "Issues: deployment, cloud infrastructure and environments"
description: "GitHub issue inventory for infrastructure, deployment and CI/CD, as of 2026-10-22; open issues first."
tags: [deployment, infra, gcp, pulumi]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:22Z" }
status: stable
governance: context
code_refs: ["deployment/cloud/gcp/infrastructure/", "deployment/README.md", "resources/"]
stale_after: "2026-11-15"
sources: ["gh issue list --repo sustainability-software-lab/ca-biositing --state all (2026-10-16)", "https://github.com/sustainability-software-lab/ca-biositing/issues", "https://github.com/sustainability-software-lab/ca-biositing/issues/519", "gh issue view 519 (2026-10-22)", "gh issue list --state open (2026-10-22)"]
---

**Purpose.** GCP/Pulumi infrastructure, staging and production deploys, Cloud Run/Cloud SQL, secrets, and production data pushes.

**Counts.** 21 issues: 8 open, 13 closed. Open issues are listed first. Snapshot as of 2026-10-22 (HEAD a2c8de8); lists come from `gh issue list --state all`.

**Key files.**

| Path | Role |
|---|---|
| `deployment/cloud/gcp/infrastructure/config.py` | Image refs and IMAGE_TAG default (L81-86) |
| `deployment/cloud/gcp/infrastructure/` | Pulumi program: cloud_run.py, secret_manager.py, iam.py, storage.py, deploy.py |
| `deployment/README.md` | Deployment runbook (CI tasks read IMAGE_TAG, defaults to latest ~L689) |

**How it works.** Issues are the work queue for this area. Each line below is one GitHub issue; bug-type open issues also have their own `bugs/` concept.

**Interfaces.** Inputs: GitHub issues on sustainability-software-lab/ca-biositing. Outputs: none in-repo; status changes are tracked on GitHub.

**Gotchas.** Production has no auto-seeded frontend API key (see bugs/infra-frontend-api-key-not-seeded). Image tag default of ’latest’ is a known drift source (bugs/deploy-image-tag-latest-drift).

**History.** Issue numbers are the history index; see `facts/current-state` for the current-state snapshot. Commit refs where verified: 85373ad (#476, #480 centralization), e289fd1 (#248 per-client API keys), 203b787 (#139 JWT).

**Open questions.** Which open items are still wanted after the 2026 cleanup (for example #157 `name` to `api_name`, #147 lowercase validation) is not stated in the issues; confirm with the owners listed.

**Update 2026-10-22.** Added #519 (closed 2026-10-19; stop committing large dashboards and publish via GCS). Its work landed in #520, #521 and #522.

## Issues (21)

- #22 [OPEN] feat: Staging stack skeleton (@lsetiawan) https://github.com/sustainability-software-lab/ca-biositing/issues/22
- #144 [OPEN] ci: Create pipeline to deploy new releases (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/144
- #182 [OPEN] ci: Setup production deployment (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/182
- #205 [OPEN] Production environment bootstrap (post-merge from #203) (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/205
- #218 [OPEN] [Feature]: Trigger ETL pipeline automatically after staging deploy (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/218
- #235 [OPEN] [Feature]: Set min-instances=1 and tune Uvicorn workers on the webservice Cloud Run service (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/235
- #428 [OPEN] Auto-seed (or fail-loud on) the frontend API key so a prod DB reset can’t silently break the frontend (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/428
- #491 [OPEN] Deploy tooling: IMAGE_TAG defaults to ’latest’ and Pulumi GCP provider version drift cause spurious cloud-deploy diffs (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/491
- #17 [CLOSED] chore: GCP access (@nikiburggraf) https://github.com/sustainability-software-lab/ca-biositing/issues/17
- #19 [CLOSED] feat: IaC skeleton (@nikiburggraf) https://github.com/sustainability-software-lab/ca-biositing/issues/19
- #70 [CLOSED] [Feature]: Cloud database creation (@nikiburggraf) https://github.com/sustainability-software-lab/ca-biositing/issues/70
- #77 [CLOSED] feat[cloud]: GCP backend for statefile + documentation (@nikiburggraf) https://github.com/sustainability-software-lab/ca-biositing/issues/77
- #104 [CLOSED] feat: Create staging deployment with Pulumi (@lsetiawan) https://github.com/sustainability-software-lab/ca-biositing/issues/104
- #120 [CLOSED] [Feature]: Postgres Extension Requirements (@lsetiawan) https://github.com/sustainability-software-lab/ca-biositing/issues/120
- #181 [CLOSED] ci: Setup staging deployment with GH Action (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/181
- #219 [CLOSED] [Feature]: Auth for prefect server (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/219
- #244 [CLOSED] [Bug]: Simple Alembic Migrations to Staging Not Working (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/244
- #311 [CLOSED] Stale Data in Staging Database (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/311
- #372 [CLOSED] [Feature]: Push M2 First Round Data to Production (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/372
- #418 [CLOSED] [Feature]: Push remaining data to production (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/418
- #519 [CLOSED] refactor(ci,infra): stop committing large dashboards, publish via GCS (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/519

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state snapshot this issue inventory belongs to
- [GCP cloud topology per environment (Cloud Run, Cloud SQL, AR proxies, GCS, WIF)](../architecture/infra-cloud-topology.md): Deployment targets these issues describe
- [Pulumi Automation API program: modules, stacks, naming, and commands](../architecture/infra-pulumi-program.md): Pulumi program used for staging/prod
- [Decision: store generated dashboards in a GCS bucket instead of committing them to git (#519)](../decisions/dashboards-gcs-over-committed-exports.md): the decision behind issue #519
