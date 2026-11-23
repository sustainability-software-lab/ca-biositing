---
type: Architecture
title: Inventory of scripts/ (deploy and ops scripts vs analysis and audit helpers)
description: "What each script in scripts/ does, grouped into cloud operations, local tooling, DB and schema helpers, and audit or analysis, so a reader knows which ones are safe to ignore."
tags: [scripts, ops, tooling, cloud, db]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:30Z" }
status: stable
code_refs: ["scripts/pulumi-docker.sh", "scripts/cloud-backup.sh", "scripts/cloud-migrate-ci.sh", "scripts/cloud-update-services.sh", "scripts/cloud-trigger-etl.sh", "scripts/validate-deployment.sh", "scripts/db_reset.py", "scripts/create_admin.py"]
sources: ["scripts/", "pixi.toml", "commit 05062d4", "commit b452d81", "commit 6912294", "commit 0ccbb0f", "commit b656a19"]
governance: context
stale_after: "2027-01-16"
---

## Purpose
`scripts/` mixes deploy operations, local developer helpers, database utilities, and one-off analysis or audit tools. Pixi tasks in pixi.toml are the usual entry points. This inventory was built from file headers and skim reads; scripts marked "skim" were not read end to end.

## Key files
### Cloud operations (deployment)
| Path | Role |
|---|---|
| scripts/pulumi-docker.sh | Runs `deploy.py <cmd>` inside the `ca-biositing-pulumi` image with the infra folder mounted; passes an empty `PULUMI_CONFIG_PASSPHRASE` and `DEPLOY_ENV` (see decisions/infra-pulumi-run-in-docker) |
| scripts/cloud-backup.sh | `gcloud sql export sql --offload` of `biocirv-{env}` to `gs://biocirv-{env}-backups/YYYYMMDD-...sql` |
| scripts/cloud-migrate-ci.sh | Points the `biocirv-{env}-migrate` job at the pipeline image for `IMAGE_TAG`, then executes it with `--wait` |
| scripts/cloud-update-services.sh | `gcloud run services update` of `prefect-worker` and `webservice` to the SHA-tagged images |
| scripts/cloud-seed-admin.sh | Executes the `biocirv-{env}-seed-admin` job |
| scripts/cloud-trigger-etl.sh | Creates or updates and runs the `biocirv-{env}-trigger-etl` job (register + trigger Master ETL); see architecture/infra-prefect-cloud-run |
| scripts/validate-deployment.sh | Polls webservice `/health`, prefect-auth `/api/health`, and the worker Ready condition for up to 300 s |
| scripts/activate-gcloud.sh | pixi `cloud` feature activation: adds gcloud to PATH and sets `CLOUDSDK_CORE_PROJECT=biocirv-470318` |
| scripts/install-pgschema.sh | Downloads pgschema 1.6.2 into the pixi env (used by schema-plan tasks) |
| scripts/get_version.sh | Reads `version =` from pixi.toml |

### Database and reset
| Path | Role |
|---|---|
| scripts/db_reset.py, scripts/sql/db_reset_*.sql | Destructive reset (architecture/infra-db-reset) |
| scripts/create_admin.py | Creates an API admin user; password from `ADMIN_PASSWORD` env (used by the seed-admin job and pixi `create-admin`) |
| scripts/compile_mv_fixes.py | Compiles materialized-view fixes into an Alembic migration (pixi `compile-mv-fixes`) |
| scripts/view_diagnostics.py, scripts/check_counts.py, scripts/test_db_queries.py, scripts/get_schema.py, scripts/get_schema_details.py | Read-only diagnostics and schema listing (skim) |
| scripts/generate_openapi.py | Writes a static OpenAPI spec from the FastAPI app (webservice env) |

### Local developer tooling
| Path | Role |
|---|---|
| scripts/run_flow.py | Lists ETL flows by scanning `pipeline/flows` and triggers one by module name (`pixi run-single-flow`) |
| scripts/register_jupyter_kernel.py | Registers the active Pixi env as a Jupyter kernel |
| scripts/fix_symlinks.py | Recreates symlinks listed in its table, relative to repo root (skim) |
| scripts/csv_to_json.py, scripts/validate_headers.py | Keep `resources/assets/resource_info.csv` and its JSON and header mapping in sync (`update-static-resource-info`) |
| scripts/viz/ | Injects click-export JS into generated dashboard HTML (skim) |

### Analysis, audit, and reporting (not deployment)
| Path | Role |
|---|---|
| scripts/audit_*.sql, scripts/audit_sample_lineage.sql | Data-quality profiling and lineage queries |
| scripts/filter_funnel_snapshot.py | Writes a filter-funnel baseline under `audit/output/` |
| scripts/data_summary_report.py, scripts/generate_sample_visualizations.py, scripts/regenerate_all_plots.py, scripts/generate_dashboard_gallery.py | Reports, plots, and gallery generation |

## How it works
Cloud scripts assume `DEPLOY_ENV` (default staging) and `IMAGE_TAG` (default latest) from the environment. Most call `gcloud` with region us-west1 and project biocirv-470318. Scripts that connect to Postgres from the host override `POSTGRES_HOST=localhost`.

## Interfaces
- Callers: pixi tasks in pixi.toml `[feature.cloud.tasks]` and the GitHub workflows (architecture/infra-ci-cd-pipelines).
- Dependencies: `gcloud`, `docker`, `jq` (validate-deployment.sh), `curl`.

## Gotchas
- `cloud-backup.sh` expects the Cloud SQL instance and bucket to already exist; it does not create them.
- `cloud-update-services.sh` only updates worker and webservice; it does not touch prefect-server, migrate, or seed-admin images. Those rely on Pulumi or the migrate script.
- `validate-deployment.sh` does not check the `frontend` service.
- `cloud-trigger-etl.sh` hard-codes the worker SA for the environment (`biocirv-{sa_env}-cr-worker`).

## History
- 05062d4 (2026-03-24): `validate-deployment.sh` switched to jq for service status.
- b452d81 and 6912294 (2026-03-30): trigger script moved to a Cloud Run job.
- 0ccbb0f and b656a19 (2026-06 and 2026-09): db_reset tooling.
- befff21 and 5146f20 (2026-07): audit artifacts restored, not deployment.

## Open questions
- Whether `fix_symlinks.py` and `scripts/viz/` are still used (no pixi task found in this slice; confirm with grep across `.github` and `docs`).

# Related Concepts
- [System overview (start here)](system-overview.md): Scripts are the operator-facing edge of the deployed system.
- [GitHub Actions deploy chain: docker-build, staging/production deploy, migrations, ETL trigger](infra-ci-cd-pipelines.md): CI calls the cloud-*.sh and validate scripts.
- [Database reset tool (scripts/db_reset.py): three SQL phases, safety checks, env targets](infra-db-reset.md): db_reset.py is documented separately.
- [Prefect on Cloud Run: server, always-on worker, auth proxy, and ETL trigger job](infra-prefect-cloud-run.md): cloud-trigger-etl.sh registers and triggers the Prefect flow.
