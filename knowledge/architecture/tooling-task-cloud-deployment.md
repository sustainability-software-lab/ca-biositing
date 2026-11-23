---
type: Architecture
title: "Cloud deployment pixi tasks: Docker-wrapped vs direct Pulumi, migrations, ETL trigger"
description: "The `cloud` feature’s tasks for GCP infrastructure (Pulumi), Cloud Run service updates, Alembic migrations, backups and ETL triggers, and why there are two variants of each."
tags: [tooling, pixi, deployment, gcp, pulumi, cloud-run]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:26:45Z" }
status: stable
code_refs: ["pixi.toml", "scripts/pulumi-docker.sh", "scripts/cloud-migrate-ci.sh", "deployment/cloud/gcp/infrastructure/deploy.py", "scripts/validate-deployment.sh"]
sources: ["pixi.toml", "commit 844ef97", "https://github.com/sustainability-software-lab/ca-biositing/pull/203", "https://github.com/sustainability-software-lab/ca-biositing/pull/228", "https://github.com/sustainability-software-lab/ca-biositing/pull/240", "commit 4a27f23"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Operations for the GCP environments (staging and production). The `deployment` environment (feature `cloud`) holds the CLIs; each task reads `DEPLOY_ENV` for its target.

## Key files
| Path:line | Role |
| --- | --- |
| pixi.toml:392-393 | `[feature.cloud.activation]` runs `scripts/activate-gcloud.sh` |
| pixi.toml:395-412 | `install-gcloud`, `install-pulumi`, cloud deps (postgresql, prefect>=3,<4, pulumi>=3,<4, pulumi-gcp, pulumi-random) |
| pixi.toml:415-453 | Docker-wrapped variants: `cloud-bootstrap`, `cloud-build`, `cloud-plan`, `cloud-deploy`, `cloud-destroy`, `cloud-outputs`, `cloud-refresh`, `cloud-backup` (scripts/pulumi-docker.sh) |
| pixi.toml:459-477 | Direct variants: `cloud-plan-direct`, `cloud-deploy-direct`, `cloud-refresh-direct`, `cloud-outputs-direct` -> `deployment/cloud/gcp/infrastructure/deploy.py` with `PULUMI_CONFIG_PASSPHRASE=""` |
| pixi.toml:479-495 | CI tasks: `cloud-migrate-ci` (scripts/cloud-migrate-ci.sh), `cloud-update-services` (scripts/cloud-update-services.sh), `cloud-validate`, `cloud-trigger-etl` (scripts/cloud-trigger-etl.sh) |
| deployment/cloud/gcp/infrastructure/ | Pulumi program (cloud_run.py, cloud_sql.py, iam.py, wif.py, storage.py, networking.py, its own config.py) |

## How it works
- Preview/deploy: `cloud-plan-direct` runs on PRs in `deploy-staging.yml`; `cloud-deploy-direct` runs in the deploy jobs after the Docker build succeeds (see architecture/tooling-ci-workflows).
- Image pinning: `IMAGE_TAG` (default `latest`) selects images for `cloud-update-services` and `cloud-migrate-ci`; CI sets it to the 7-character short SHA of the release or main commit.
- Local operators use the Docker-wrapped variants, which avoid a macOS gRPC/fork crash (comment at pixi.toml:414).

## Interfaces
- Inputs: `DEPLOY_ENV` (staging or production), `IMAGE_TAG`, GCP credentials (Workload Identity in CI; `gcloud` locally).
- Outputs: Cloud Run services, Cloud SQL, migration job runs, Pulumi state in `gs://biocirv-470318-pulumi-state` (hard-coded in `cloud-bootstrap`).
- Callers: `.github/workflows/deploy-staging.yml`, `deploy-production.yml`, `trigger-etl*.yml`.

## Gotchas
- The direct variants set an empty `PULUMI_CONFIG_PASSPHRASE`; state encryption therefore depends on the backend, not a passphrase (inferred from the env setting; confirm in `deploy.py`).
- `cloud-backup` writes a SQL export to the backup bucket; it is not a restore path.
- `cloud-validate` and `scripts/validate-deployment.sh` are the post-deploy health gate; a deploy can succeed in Pulumi and still fail here.

## History
- Multi-environment Pulumi parameterization `844ef97` (#203, 2026-03-24); production bootstrap `d4f3a33` (#228, 2026-03-30); production waits on the Docker build `4a27f23` (#240).

## Open questions
- The Pulumi passphrase handling for the direct variants (see Gotchas).

# Related Concepts
- [GCP cloud topology per environment (Cloud Run, Cloud SQL, AR proxies, GCS, WIF)](infra-cloud-topology.md): Infrastructure slice (prefix): what Pulumi provisions
- [GitHub Actions workflows: what runs on PRs, main, releases and deploys](tooling-ci-workflows.md): Workflows that call these tasks
- [System overview (start here)](system-overview.md): Hub
