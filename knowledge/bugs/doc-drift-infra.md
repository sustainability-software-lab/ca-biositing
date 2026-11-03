---
type: Bug
title: Known infra documentation drift and dead config (snapshot at e41d00d)
description: "Infra docs and config that no longer match the code at e41d00d (PostgreSQL version, migrate job name, Cloud Build path, missing DEPLOYMENT.md, migration name, Pulumi pins)."
tags: [docs, drift, infra, snapshot]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:20Z" }
status: stable
governance: context
code_refs: ["resources/AGENTS.md", "resources/README.md", "deployment/README.md", "docs/operations/DB_RESET.md", "deployment/cloud/gcp/cloudbuild.yaml", "resources/prefect/prefect.yaml", "resources/docker/docker-compose.yml", "deployment/cloud/gcp/infrastructure/Dockerfile", "pixi.toml", "alembic/versions/0002_permissions.py"]
stale_after: "2027-01-16"
sources: ["resources/AGENTS.md", "deployment/README.md", "docs/operations/DB_RESET.md", "deployment/cloud/gcp/cloudbuild.yaml", "commit 4e271b6", "commit 5bdefc9", "commit 13675d8", "commit a2c8de8", "https://github.com/sustainability-software-lab/ca-biositing/issues/491"]
---

## Fact
As of HEAD a2c8de8 (2026-10-22), these statements in docs or config disagree with the code. The e41d00d snapshot items were re-checked in this slice. Rows not listed here were not re-checked.

| Where | Says | Code actually does (a2c8de8) |
|---|---|---|
| resources/AGENTS.md:57 | db is "PostgreSQL 13" | docker-compose.yml uses postgis/postgis:17-3.5 (since 5bdefc9) |
| deployment/README.md:458, 464 | job biocirv-alembic-migrate | job is biocirv-{env}-migrate (config.py:37) |
| deployment/README.md:662 | build step submits a Cloud Build that tags images with latest and SHA | docker-build.yml pushes to GHCR; Cloud Build removed (4e271b6) |
| deployment/README.md:505 | alembic migration 0002_grant_readonly_permissions | file is alembic/versions/0002_permissions.py |
| deployment/README.md:703, 711-712 | frontend has its own Cloud Build triggers; Cloud Build failures | Cloud Build not used by repo workflows; text is historical |
| docs/operations/DB_RESET.md:176 | references docs/pipeline/DEPLOYMENT.md | file does not exist (docs/pipeline has ALEMBIC, CONTRIBUTING, DOCKER, ETL, GCP_SETUP, PREFECT, README) |
| deployment/cloud/gcp/cloudbuild.yaml | builds gcr.io webservice and pipeline :latest | file exists and no workflow or pixi task references it (grep); dead config |
| deployment/cloud/gcp/infrastructure/Dockerfile:10 | PULUMI_GCP_VERSION=9.16.0 | pixi.toml:424 pulumi-gcp >=9,<10; two pins to reconcile (see issue #491, still open) |
| resources/README.md ("Development vs Production") | production should use managed Postgres and Prefect Cloud | production uses Cloud SQL and self-hosted Prefect on Cloud Run |
| resources/prefect/prefect.yaml | prefect-version 3.4.23 | pixi cloud feature is a range; server image floats prefecthq/prefect:3-python3.12 |
| deployment/README.md (Architecture) | Prefect Worker: Cloud Run Service, internal | matches cloud_run.py:508-518; docs/architecture.md worker-as-job text is a future option, not implemented |
| deployment/README.md:990-1052 (new in 3eba913) | public access prevention, opt-in glob, denylist | see bugs/doc-drift-dashboard-privacy-gate |

## Source
Compare the files above with the code paths in the table.

## Stale-by note
Re-verify before editing docs; several items were true at earlier commits.

# Related Concepts
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Snapshot of what is true now; this list corrects several docs against it.
- [GCP cloud topology per environment (Cloud Run, Cloud SQL, AR proxies, GCS, WIF)](../architecture/infra-cloud-topology.md): The code-true version of the cloud statements.
- [Database reset tool (scripts/db_reset.py): three SQL phases, safety checks, env targets](../architecture/infra-db-reset.md): DB_RESET.md drift is detailed there.
- [System overview (start here)](../architecture/system-overview.md): Overview docs also reference these infra statements.
- [deployment/README.md describes a dashboard privacy gate and bucket settings the code does not implement](doc-drift-dashboard-privacy-gate.md): the dashboard section drift added after this snapshot
