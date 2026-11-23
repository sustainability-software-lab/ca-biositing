---
type: Bug
title: "Production webservice reads dashboards/production/latest, which no workflow writes"
description: "Production Cloud Run gets DASHBOARDS_GCS_PREFIX=dashboards/production/latest, but dashboard-artifacts.yml publishes only the staging prefix, so production portal dashboards have no source."
tags: [bug, dashboards, gcs, production, cloud-run]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:24Z" }
status: stable
code_refs: ["deployment/cloud/gcp/infrastructure/cloud_run.py", ".github/workflows/dashboard-artifacts.yml", "src/ca_biositing/webservice/ca_biositing/webservice/services/dashboard_loader.py"]
sources: ["commit 752a80d", "commit 1fcadb4", "https://github.com/sustainability-software-lab/ca-biositing/issues/519"]
governance: context
stale_after: "2026-12-31"
---

## Symptom
The production stack sets the webservice prefix from its stack name (cloud_run.py:110-117), so production reads dashboards/production/latest. No workflow writes that prefix:
- dashboard-artifacts.yml hard-codes DASHBOARDS_ENV to staging (line 68) and has no production job or matrix.
- gh-pages.yml reads staging only (line 37).
- A grep of .github/workflows for dashboards/ finds only the staging paths.

## Evidence
- deployment/cloud/gcp/infrastructure/cloud_run.py:115-116: value f"dashboards/{STACK_NAME}/latest".
- .github/workflows/dashboard-artifacts.yml:68-69: DASHBOARDS_ENV staging, DASHBOARDS_BUCKET biocirv-staging-dashboards.

## Impact (inferred; not checked against live GCP)
- The production container has no exports/plots (exports/plots/ is gitignored and absent from CI checkouts), so dashboard_loader.py:305-347 falls through to GCS.
- The GCS read misses, so only the built-in login page (dashboard_loader.py:341-343) is served and every other /v1/dashboards/ asset returns 404.

## Status
Open since 752a80d (2026-10-19). Probably by design for the first staging-only rollout (#519 Phase 2 targeted staging). No issue or decision in the repo records the plan.

## Fix direction
Add a production publish path with the production publisher SA (biocirv-prod-dash-pub, created by the production stack), or document that production dashboards are intentionally absent.

# Related Concepts
- [GCS dashboards bucket, its service accounts, WIF bindings, and runtime reads](../architecture/infra-dashboards-gcs-bucket.md): the production prefix and bucket this bug concerns
- [dashboard-artifacts.yml: builds the dashboard suite and publishes it to GCS](../architecture/ci-dashboard-artifacts-publisher.md): the workflow that lacks a production publish
