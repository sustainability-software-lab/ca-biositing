---
type: Architecture
title: Webservice deployment on GCP Cloud Run
description: "How the API container is deployed by Pulumi to Cloud Run: port, probes, secrets, cookie flag, public invoker IAM, and the CI workflow that rolls revisions."
tags: [webservice, deployment, cloud-run, gcp, infra]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:17Z" }
status: stable
governance: context
code_refs: ["deployment/cloud/gcp/infrastructure/cloud_run.py", "deployment/cloud/gcp/infrastructure/config.py", "deployment/cloud/gcp/infrastructure/storage.py", ".github/workflows/deploy-production.yml", ".github/workflows/deploy-staging.yml", "scripts/validate-deployment.sh", "src/ca_biositing/webservice/ca_biositing/webservice/services/dashboard_loader.py"]
stale_after: "2026-12-31"
sources: ["commit 203b787", "commit 844ef97", "commit eb0c2a1", "deployment/cloud/gcp/infrastructure/cloud_run.py", "https://github.com/sustainability-software-lab/ca-biositing/pull/203", "https://github.com/sustainability-software-lab/ca-biositing/pull/241", "commit 752a80d", "commit 7af19de", "https://github.com/sustainability-software-lab/ca-biositing/pull/520"]
---

## Purpose
Production and staging host for the API. Deployed by the Pulumi program in deployment/, not by any file in the webservice package.

## Key files
| Path | Role |
|---|---|
| deployment/cloud/gcp/infrastructure/cloud_run.py:60 | gcp.cloudrunv2.Service("webservice") definition |
| cloud_run.py:67 | service account iam.service_accounts["webservice"] |
| cloud_run.py:80 | container command, with the GOOGLE_CLIENT_ID export |
| cloud_run.py:110-117 | DASHBOARDS_BUCKET_NAME and DASHBOARDS_GCS_PREFIX env vars |
| cloud_run.py:234-238 | ServiceIamMember granting roles/run.invoker to allUsers |
| cloud_run.py:243 | Alembic migration Cloud Run job |
| .github/workflows/deploy-production.yml and deploy-staging.yml | plan, infra deploy, migrate (cloud-migrate-ci), force new revisions (cloud-update-services), validate-deployment.sh |
| scripts/cloud-update-services.sh, scripts/validate-deployment.sh | revision roll and post-deploy health check |
| src/ca_biositing/webservice/ca_biositing/webservice/services/dashboard_loader.py:305 | runtime GCS read of dashboards (see architecture/infra-dashboards-gcs-bucket) |

## How it works
- Image from WEBSERVICE_IMAGE (Artifact Registry). Container command: export DB_PASS from /secrets/db-password, export API_JWT_SECRET_KEY from /secrets/jwt-secret, export GOOGLE_CLIENT_ID from /secrets/oauth2-client-id, then exec uvicorn ca_biositing.webservice.main:app --host 0.0.0.0 --port 8080.
- Resources: 1 CPU, 512Mi, cpu_idle=False, startup_cpu_boost=True.
- Env: POSTGRES_DB, INSTANCE_CONNECTION_NAME (Cloud SQL socket), API_JWT_COOKIE_SECURE=true, DASHBOARDS_BUCKET_NAME and DASHBOARDS_GCS_PREFIX, the GSheets credentials path, and API_CORS_ORIGINS when configured. GOOGLE_APPLICATION_CREDENTIALS is deliberately unset so ADC uses the Cloud Run SA.
- Secret volumes (cloud_run.py:148-153 mounts, 206-221 volumes): db-password, jwt-secret, oauth2-client-id, gsheets-credentials (the last two added by 752a80d).
- Startup probe: HTTP GET /health on 8080 (failure threshold 30 x 10 s). Liveness probe: GET / every 30 s. These settings were not re-verified in this slice.
- Public: allUsers has run.invoker, so the API is internet-reachable. Auth is the gate for /v1/feedstocks/*.

## Gotchas
- The liveness probe hits /, which redirects to /docs (307). Probes that do not follow redirects still see a 3xx and pass (inferred; confirm in logs).
- Secrets are read from files mounted under /secrets/, not env vars. Changing a secret needs a new revision (cloud-update-services).
- The deploy workflow pins a production project and deployer SA in plain env values; check before editing.
- The webservice SA is bound to roles/storage.objectViewer on the dashboards bucket (storage.py:150-159), and it has no write grant there.

## History
- 203b787 (PR #139): JWT signing key moved to Secret Manager.
- 844ef97 (2026-03-24, PR #203): parameterized infrastructure for multi-environment deploy.
- eb0c2a1 (PR #241): / redirect to /docs added.
- 752a80d (2026-10-19, PR #520): dashboards env vars, bucket grant, oauth2-client-id and gsheets-credentials mounts, GOOGLE_CLIENT_ID export.

## Open questions
- Is the / liveness probe intentional given the redirect? (inferred; confirm)

# Related Concepts
- [System overview (start here)](system-overview.md): Cloud deployment is part of the overall system
- [Webservice settings and API_ environment variables](webservice-config.md): Env values set here override defaults in config.py
- [JWT login, cookie transport, and refresh in the webservice](webservice-auth-jwt.md): Secret injection and secure cookie flag for JWT
- [Catch-all 500 handler returns raw exception text](../bugs/webservice-500-leaks-exception-text.md): Public exposure of the catch-all handler
- [GCS dashboards bucket, its service accounts, WIF bindings, and runtime reads](infra-dashboards-gcs-bucket.md): the dashboards read path this revision uses
