---
type: Architecture
title: "Pulumi Automation API program: modules, stacks, naming, and commands"
description: "How deployment/cloud/gcp/infrastructure is organized: module-per-resource-group, DEPLOY_ENV stack selection, the GCS state backend, and the preview/up/destroy/refresh/outputs commands."
tags: [infra, pulumi, iac, gcp, stacks]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:09Z" }
status: stable
governance: context
code_refs: ["deployment/cloud/gcp/infrastructure/deploy.py", "deployment/cloud/gcp/infrastructure/config.py", "deployment/cloud/gcp/infrastructure/apis.py", "deployment/cloud/gcp/infrastructure/iam.py", "deployment/cloud/gcp/infrastructure/secret_manager.py", "deployment/cloud/gcp/infrastructure/storage.py"]
sources: ["deployment/cloud/gcp/infrastructure/deploy.py", "deployment/cloud/gcp/infrastructure/config.py", "commit 96a4eec", "commit 5bdefc9", "commit 844ef97", "commit 9ea84ed", "https://github.com/sustainability-software-lab/ca-biositing/pull/110", "commit 752a80d", "https://github.com/sustainability-software-lab/ca-biositing/pull/520"]
---

## Purpose
The GCP infrastructure is one Python Pulumi program run through the Pulumi Automation API. deploy.py builds a stack, configures it programmatically, and runs one command. There is no Pulumi.yaml in the repo; project settings are built in code (deploy.py:get_stack at line 135).

## Key files
| Path:line | Role |
|---|---|
| deployment/cloud/gcp/infrastructure/deploy.py:29-132 | pulumi_program(): ordered module calls with depends_on |
| deploy.py:89-132 | exports (db names, secret names, SA emails, WIF provider, service URLs, job names, bucket names including dashboards_bucket_name at line 132) |
| deploy.py:135-150 | get_stack(): auto.create_or_select_stack, project ca-biositing-infrastructure, backend gs://biocirv-470318-pulumi-state |
| deploy.py:153-200 | CLI: preview, up (runs refresh first, non-fatal, lines 163-172), destroy, refresh, outputs |
| config.py:1-30 | project and stack constants (STACK_NAME from DEPLOY_ENV, line 9) |
| config.py:102-105 | configure_stack() sets gcp:project and gcp:region only |
| apis.py | enables GCP APIs with disable_on_destroy=False |
| iam.py:29-95 | eight SA definitions: six runtime SAs plus dashboards-publisher and dashboards-reader (no project roles) |
| secret_manager.py | random passwords for db, ro user, postgres, JWT, admin, oauth2 cookie, prefect-auth |
| storage.py | buckets: image, backups, gasification, and dashboards (see architecture/infra-dashboards-gcs-bucket) |
| cloud_sql.py, cloud_run.py, networking.py, artifact_registry.py, wif.py | resource groups (see architecture/infra-cloud-topology) |
| deployment/cloud/gcp/infrastructure/.gitignore | excludes .pulumi-passphrase and __pycache__ |

## How it works
Module order in pulumi_program() (deploy.py:32-82):
1. APIs (line 32)
2. IAM service accounts (line 35), now before WIF
3. WIF for GitHub Actions (line 41), given the SA dict
4. Artifact Registry GHCR proxy (line 48) and Quay proxy (line 56)
5. Cloud SQL (line 63) and secrets (line 66)
6. Storage buckets (line 71), NAT (line 79), Cloud Run (line 82)

Stack name equals DEPLOY_ENV, so staging and production are independent state files in one bucket. Logical resource names are reused across stacks; the URN includes the stack.

## Interfaces
- Invoke: pixi run -e deployment cloud-plan, cloud-deploy, cloud-refresh, cloud-outputs (Docker-wrapped on macOS) or the -direct variants on Linux and CI.
- Env: DEPLOY_ENV (staging default), IMAGE_TAG, image overrides, CORS_ORIGINS, LANDIQ_SHAPEFILE_URL.
- Auth: Application Default Credentials locally; WIF in CI.

## Gotchas
- up runs refresh before up and continues if refresh fails (deploy.py:166-170). This clears interrupted runs but can hide refresh problems.
- Cloud SQL deletion_protection=True (cloud_sql.py:33) blocks deleting the DB instance through the API.
- Shared resources use import_ and retain_on_delete=True: AR repos on non-staging stacks (artifact_registry.py:30-32), Cloud Router and NAT on every stack (networking.py:52, 66).
- pulumi_program is inline in deploy.py, so pulumi CLI commands outside the Automation API do not see it.
- Some resources hard-code names: biocirv-470318-pulumi-state (wif.py:106), biocirv-470318_cloudbuild (wif.py:117), and the deployer SA’s project number in CI env vars.
- storage.py still grants objectViewer on the gasification bucket to a hard-coded external data-portal SA (manual access, not otherwise managed).

## History
- b9ee91e (PR #78, 2025-12-04): GCS backend for the earlier OpenTofu code.
- 96a4eec (PR #110, 2026-02-11): OpenTofu replaced by Pulumi Python.
- 5bdefc9 (PR #125, 2026-02-19): modular Automation API program.
- 844ef97 (PR #203) and d4f3a33 (PR #228): DEPLOY_ENV parameterization and aliases for pre-existing staging names.
- 9ea84ed and d2bde31 (2026-03-20): auto-refresh of pending operations and storage.admin on the state bucket.
- 752a80d (2026-10-19, PR #520): dashboards bucket, two dashboards SAs, WIF bindings for them, and the export. IAM moved ahead of WIF.

## Open questions
- Stack config is not in a Pulumi.yaml, so pulumi config values set manually in the backend would not be reproducible (inferred; confirm the stack has no extra config).

# Related Concepts
- [System overview (start here)](system-overview.md): Pulumi is the IaC layer that provisions the cloud half of the system.
- [GCP cloud topology per environment (Cloud Run, Cloud SQL, AR proxies, GCS, WIF)](infra-cloud-topology.md): Diagram of the resources this program creates.
- [Decision: Pulumi Python instead of OpenTofu/HCL for GCP infrastructure](../decisions/infra-pulumi-over-opentofu.md): Why the program is Pulumi Python rather than HCL.
- [Decision: run Pulumi in a Linux Docker container locally, directly in CI](../decisions/infra-pulumi-run-in-docker.md): How the program is executed on macOS versus Linux.
- [GCS dashboards bucket, its service accounts, WIF bindings, and runtime reads](infra-dashboards-gcs-bucket.md): the dashboards resources this program now creates
