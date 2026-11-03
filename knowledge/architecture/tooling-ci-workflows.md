---
type: Architecture
title: "GitHub Actions workflows: what runs on PRs, main, releases and deploys"
description: "Map of the 10 workflows in .github/workflows (CI, migrations, CD to PyPI, Docker build, staging/production deploy, ETL triggers, Pages, Copilot setup) with triggers and the pixi tasks they call."
tags: [tooling, ci, github-actions, deployment]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:16Z" }
status: stable
governance: context
code_refs: [".github/workflows/ci.yml", ".github/workflows/cd.yml", ".github/workflows/deploy-staging.yml", ".github/workflows/deploy-production.yml", ".github/workflows/migrations.yml", ".github/workflows/trigger-etl.yml", ".github/workflows/dashboard-artifacts.yml", ".github/workflows/gh-pages.yml"]
stale_after: "2026-12-31"
sources: [".github/workflows", "commit e41d00d", "commit 102afdf", "https://github.com/sustainability-software-lab/ca-biositing/pull/150", "https://github.com/sustainability-software-lab/ca-biositing/pull/151", "https://github.com/sustainability-software-lab/ca-biositing/pull/164", "https://github.com/sustainability-software-lab/ca-biositing/pull/228", "https://github.com/sustainability-software-lab/ca-biositing/pull/240", "https://github.com/sustainability-software-lab/ca-biositing/pull/497", "commit 1fcadb4", "commit bd72222", "https://github.com/sustainability-software-lab/ca-biositing/pull/521", "https://github.com/sustainability-software-lab/ca-biositing/pull/533"]
---

## Purpose
Automation for checks, package publishing, container builds, cloud deploys, ETL triggers, dashboards and Pages. Almost every job installs pixi with prefix-dev/setup-pixi (pinned to v0.10.2) and calls a pixi task.

## Key files
| Workflow | Triggers (verified in file) | What it does |
| --- | --- | --- |
| ci.yml | workflow_dispatch, pull_request, push to main | harness job (agent-harness pytest, no lock install); checks matrix py312 and py313 on ubuntu-latest and macos-14 |
| migrations.yml | workflow_dispatch, pull_request, push | py312: alembic upgrade head, alembic check, alembic downgrade base |
| cd.yml | workflow_dispatch, pull_request and push (path-filtered to the three packages), release published | builds three packages; publishes to TestPyPI and PyPI |
| docker-build.yml | push to main, release, pull_request | buildx build and push for the service images |
| deploy-staging.yml | pull_request (preview), workflow_run of Docker build on main, workflow_dispatch | preview with cloud-plan-direct; deploy with cloud-deploy-direct, cloud-migrate-ci, cloud-update-services and validate-deployment.sh (environment staging) |
| deploy-production.yml | workflow_run of Docker build (main, v*), push to main, workflow_dispatch | same chain, environment production |
| trigger-etl.yml (name Trigger Staging ETL) and trigger-etl-production.yml (name Trigger Production ETL) | workflow_run of the deploy workflows on main, workflow_dispatch | check-etl-changes job, then cloud-trigger-etl if ETL files changed |
| dashboard-artifacts.yml (name Build & Export BioCirV Dashboards & Drift Audit) | workflow_dispatch, schedule Mondays 09:00 UTC, push to main and pull_request on path filters, workflow_run of both ETL triggers | builds dashboards and drift report, publishes to GCS staging bucket (see architecture/ci-dashboard-artifacts-publisher) |
| gh-pages.yml | push and pull_request on resource paths, workflow_run of the dashboards workflow on main, workflow_dispatch | validates resources/assets headers, runs csv_to_json.py, pulls the public gallery subset from GCS latest/, deploys Pages (see architecture/ci-gh-pages-gallery-consumer) |
| copilot-setup-steps.yml | push and pull_request to main, workflow_dispatch | sets up pixi from the lock and runs pre-commit install-hooks for Copilot agents; actions pinned by SHA |

## How it works
- Image tag: the Docker build publishes a short-SHA tag; deploy workflows reuse it (IMAGE_TAG).
- Auth: google-github-actions/auth@v3 with Workload Identity Federation (see decisions/infra-wif-keyless-ci). Dashboards use the publisher SA; Pages uses the reader SA.
- concurrency groups cancel superseded runs of the same workflow and ref.

## Interfaces
- Inputs: repository events, GitHub environments (staging, production, testpypi, pypi, etl-staging, etl-production) with their secrets and variables.
- Outputs: TestPyPI and PyPI releases, Docker images, Pulumi-managed cloud updates, ETL runs, GCS dashboard objects, Pages site.
- Callers: none (top-level automation).

## Gotchas
- The harness job in ci.yml skips pixi install, so a too-new pixi.lock is reported by test_lockfile.py rather than by setup-pixi.
- deploy-staging.yml and deploy-production.yml carry NOTE comments about WIF pool names and the first production deploy; those are time-bound.
- dashboard-artifacts.yml can finish green with nothing published (auth failure, unreachable bucket, or the #533 skip). Check its warnings.
- Workflow action versions are mixed: most use tags, copilot-setup uses commit SHAs.

## History
- Initial CI d8b1ad4 (#25); PyPI releases 2ce7e3e (#151); path filters for CD 8262877 (#200); migrations check 81a27bf (#164); production bootstrap d4f3a33 (#228); production waits for Docker build 4a27f23 (#240); pixi pins moved to v0.63.2 102afdf (#150); harness job split e41d00d (#497).
- 1fcadb4 (2026-10-19, PR #521): dashboard-artifacts.yml added; gh-pages.yml changed to GCS.
- bd72222 (2026-10-21, PR #533): publish guard added to dashboard-artifacts.yml.

## Open questions
- deploy-staging.yml workflow_run branch filter and the Docker-build workflow name should be re-checked after any rename of Build and Push Docker Images.

# Related Concepts
- [Cloud deployment pixi tasks: Docker-wrapped vs direct Pulumi, migrations, ETL trigger](tooling-task-cloud-deployment.md): The pixi tasks these workflows call
- [pixi.toml: workspace, features and environment composition](tooling-pixi-manifest.md): Environments the jobs select with -e
- [GCP cloud topology per environment (Cloud Run, Cloud SQL, AR proxies, GCS, WIF)](infra-cloud-topology.md): Cloud resources the deploy jobs change (slice prefix)
- [System overview (start here)](system-overview.md): Hub
- [dashboard-artifacts.yml: builds the dashboard suite and publishes it to GCS](ci-dashboard-artifacts-publisher.md): the dashboards workflow added to this map
- [gh-pages.yml: builds the public Pages gallery from the GCS latest bundle](ci-gh-pages-gallery-consumer.md): the Pages workflow whose trigger and source changed
