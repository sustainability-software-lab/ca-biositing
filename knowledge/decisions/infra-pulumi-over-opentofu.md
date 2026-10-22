---
type: Decision
title: "Decision: Pulumi Python instead of OpenTofu/HCL for GCP infrastructure"
description: "Why infrastructure moved from OpenTofu HCL to Pulumi Python in Feb 2026 (PR #110), what was given up, and what remained from the OpenTofu era."
tags: [decision, iac, pulumi, opentofu, gcp, deployment]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:31Z" }
status: stable
code_refs: ["deployment/cloud/gcp/infrastructure/deploy.py", "deployment/cloud/gcp/infrastructure/config.py", "pixi.toml", "deployment/cloud/gcp/infrastructure/cloud_run.py", "deployment/cloud/gcp/infrastructure/wif.py", ".github/workflows/cd.yml"]
sources: ["commit 96a4eec", "commit b9ee91e", "commit 5bdefc9", "https://github.com/sustainability-software-lab/ca-biositing/pull/110", "https://github.com/sustainability-software-lab/ca-biositing/pull/78", "commit 844ef97", "commit 60374d8", "commit b6459cd", "commit d4f3a33"]
governance: context
---

## Decision
Infrastructure-as-code for GCP is Pulumi (Python, Automation API), not OpenTofu/Terraform HCL.

## Context and reasoning (from history)
- The original infra was OpenTofu with a GCS backend (b9ee91e, PR #78, 2025-12-04).
- Commit 96a4eec (PR #110, 2026-02-11, body reproduced from PR #104 message): "Replace HCL-based OpenTofu infrastructure definitions with Pulumi Python so maintainers familiar with Python can work with IaC without learning HCL." It also added the `install-pulumi` pixi task and `cloud-bootstrap` for the state bucket.
- Later Pulumi work followed the same line: the staging stack moved to a modular Automation API program (5bdefc9, PR #125).

## Alternatives considered
- OpenTofu/Terraform HCL: the prior state. Rejected by the project’s Python-first maintainers (commit message reasoning). No rejection record beyond that message was found in `docs/` or `plans/`.
- Ansible, gcloud scripts, or Kubernetes: not evaluated in the repo. `resources/README.md` mentions Kubernetes and managed Postgres for production as a later option, but that is a doc suggestion, not a decision.

## Trade-offs
- Gain: one language for app code and IaC; programmatic stack configuration (`configure_stack`); outputs consumed by CI as values.
- Cost: Pulumi CLI plus a Python provider version pinned in two places (Dockerfile `PULUMI_GCP_VERSION=9.16.0` and pixi `pulumi-gcp >=9,<10`); a macOS-specific runtime crash that forced the Docker wrapper (decisions/infra-pulumi-run-in-docker).
- Cost: a Pulumi state backend that is a GCS bucket with a passphrase convention (`.pulumi-passphrase` is git-ignored but the wrapper passes an empty passphrase; see Open questions).
- The OpenTofu-era state bucket name `biocirv-470318-pulumi-state` is still in use (config.py:10), which suggests state was carried over rather than recreated (inferred; confirm with `pulumi stack history`).

## Evidence
- deployment/cloud/gcp/infrastructure/*.py (Pulumi), no HCL files remain in the repo (verified by file listing).
- pixi.toml `[feature.cloud]` pins `pulumi >=3,<4`, `pulumi-gcp >=9,<10`, `pulumi-random >=4,<5`.

## Open questions
- Whether the team will revisit the state passphrase handling (empty passphrase in pulumi-docker.sh) before production is widely used (confirm with the owner).

## Merged detail: Refactor: infrastructure moved from OpenTofu HCL to Pulumi Python (PR #110)

### Purpose
Why infrastructure code is Python under deployment/cloud/gcp/infrastructure/ and what changed afterwards.

### Key files
| Path | Role |
|---|---|
| deployment/cloud/gcp/infrastructure/deploy.py | Pulumi entry logic (14 changes in history) |
| deployment/cloud/gcp/infrastructure/config.py | Stack config, most-churned deployment file (17) |
| deployment/cloud/gcp/infrastructure/cloud_run.py | Cloud Run services (12) |
| deployment/cloud/gcp/infrastructure/wif.py | Workload identity federation (7) |

### How it works
Commit 96a4eec (PR #110, Don Setiawan, 2026-02-11, body references #104) replaced OpenTofu HCL with Pulumi Python, added Pulumi.yaml and Pulumi.staging.yaml, pixi tasks for preview/up/destroy/login, install-pulumi, and cloud-bootstrap (GCS state bucket). Then 844ef97 (PR #203, 2026-03-24) parameterized for multiple environments; d4f3a33 (PR #228) bootstrapped production; 60374d8 pinned pulumi-gcp below 9.16 to avoid a Cloud Run env var oneof bug; b6459cd switched Cloud Run env vars to volume-mounted secrets.

### Interfaces
Inputs: Pulumi stack config, GCP credentials via WIF. Callers: .github/workflows/deploy-staging.yml, deploy-production.yml, cd.yml; pixi tasks for Pulumi.

### Gotchas
- pulumi-gcp is pinned (<9.16); upgrading it can reintroduce the env var bug (60374d8).
- Earlier GCP work (b9ee91e, #78) used OpenTofu; references to it in old docs are stale.

### History
- 96a4eec 2026-02-11 PR #110: OpenTofu to Pulumi.
- 844ef97 2026-03-24 PR #203: multi-environment.
- 60374d8 / b6459cd 2026-03-25: pin and secrets fixes.
- d4f3a33 2026-03-30 PR #228: production bootstrap.

### Open questions
- Whether the OpenTofu state was migrated or recreated (not visible in git; confirm with the maintainer).

# Related Concepts
- [Pulumi Automation API program: modules, stacks, naming, and commands](../architecture/infra-pulumi-program.md): The program that embodies this decision.
- [Decision: run Pulumi in a Linux Docker container locally, directly in CI](infra-pulumi-run-in-docker.md): Execution-environment consequence of choosing Pulumi.
- [System overview (start here)](../architecture/system-overview.md): IaC choice underpins the cloud deployment described in the overview.
- [GCP cloud topology per environment (Cloud Run, Cloud SQL, AR proxies, GCS, WIF)](../architecture/infra-cloud-topology.md): current GCP infrastructure built on this IaC choice (id prefix architecture/infra-*)
- [History: GCP staging and production deployment automation (Feb to Apr 2026)](../facts/history-gcp-staging-deployment.md): the CI/CD automation that runs this IaC
- [Project history eras (2025-08 to 2026-10)](../facts/history-eras.md): E5 and E6 boundary
