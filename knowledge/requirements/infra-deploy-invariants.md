---
type: Requirement
title: Deploy and infra invariants a change must keep
description: "Hard infra rules to keep: internal Prefect ingress, min-1 worker, AR image paths, Cloud SQL deletion protection, shared-resource retention, secret handling, DB reset target check."
tags: [requirements, infra, invariants, security, cloud-run, cloud-sql]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:19Z" }
status: stable
governance: constraint
code_refs: ["deployment/cloud/gcp/infrastructure/cloud_run.py", "deployment/cloud/gcp/infrastructure/cloud_sql.py", "deployment/cloud/gcp/infrastructure/networking.py", "deployment/cloud/gcp/infrastructure/artifact_registry.py", "deployment/cloud/gcp/infrastructure/storage.py", "deployment/cloud/gcp/infrastructure/iam.py", "scripts/db_reset.py", "resources/docker/docker-compose.yml", ".github/workflows/deploy-staging.yml"]
sources: ["deployment/cloud/gcp/infrastructure/cloud_run.py", "deployment/README.md", "scripts/db_reset.py", "commit 12b3592", "commit b656a19", "commit dffbaba", "commit d4f3a33", "commit 752a80d", "https://github.com/sustainability-software-lab/ca-biositing/pull/520"]
---

## Requirement
A change to deployment/, resources/, .github/workflows/deploy-*, .github/workflows/dashboard-artifacts.yml, .github/workflows/gh-pages.yml, or scripts/cloud-* must keep these properties. Each is enforced in code or stated in the docs as a design rule.

1. **Prefect server stays internal-only.** prefect-server ingress is INGRESS_TRAFFIC_INTERNAL_ONLY (cloud_run.py:412). Public access goes through prefect-auth. The service also has an allUsers run.invoker binding (cloud_run.py:496-501); do not rely on IAM for protection and do not widen ingress.
2. **Worker and server are single instances.** prefect-server and prefect-worker are min=max=1 (cloud_run.py:415-418, 516-518). The worker must stay at min 1 because it polls for runs.
3. **Cloud Run images come from AR remote repos.** Cloud Run rejects direct GHCR references (decisions/infra-ghcr-via-artifact-registry). Image refs must start with us-west1-docker.pkg.dev/biocirv-470318/ghcr-proxy/ or quayio-proxy/.
4. **Database and identity protections stay on.** Cloud SQL deletion_protection=True (cloud_sql.py:33) and ENCRYPTED_ONLY SSL (cloud_sql.py:40).
5. **Shared resources are not per-stack.** Cloud Router biocirv-router, Cloud NAT biocirv-nat, and the AR repos keep retain_on_delete=True and environment-neutral names. Renaming them breaks other stacks.
6. **Stack name equals DEPLOY_ENV.** Resource names derive from DEPLOY_ENV (config.py). Production SA IDs use prod to fit the 30-char limit (config.py:60).
7. **Secrets never in git.** .env, credentials.json and .pulumi-passphrase stay out of the repo (resources/AGENTS.md; deployment/cloud/gcp/infrastructure/.gitignore). Manually set secrets must be written with printf or echo -n to avoid a trailing newline (deployment/README.md).
8. **DB reset matches the target.** db_reset.py must keep the current_database() equals target check before each phase (db_reset.py:280-286, PR #464).
9. **Local Postgres stays on loopback.** The compose port mapping keeps the 127.0.0.1: prefix (resources/docker/docker-compose.yml, PR #363).
10. **Deploy order.** Pulumi, then migrations, then service updates, then validation (deploy-staging.yml needs chain). Services must not get new images before the schema migrates.
11. **Dashboards bucket stays private and bucket-scoped.** The bucket has no allUsers binding (storage.py:110-148). The publisher and reader SAs get only bucket-level roles, and the dashboards SAs get no project roles (iam.py:83-94). Adding public read needs an explicit decision (the issue #519 proposal asked for it; the code does not do it).

## Evidence
- Each item is cited above. Items 1, 2, 4, 8 and 11 are also called out in code comments or docs.

## Open questions
- No automated test enforces these invariants. A Pulumi policy pack or a preview check in CI would make them mechanical (inferred need; not present in repo).

# Related Concepts
- [System overview (start here)](../architecture/system-overview.md): These rules protect the production shape of the system.
- [GCP cloud topology per environment (Cloud Run, Cloud SQL, AR proxies, GCS, WIF)](../architecture/infra-cloud-topology.md): The resources the invariants refer to.
- [Database reset tool (scripts/db_reset.py): three SQL phases, safety checks, env targets](../architecture/infra-db-reset.md): Item 8 is enforced in the reset tool.
- [Decision: images built to GHCR, pulled by Cloud Run through Artifact Registry proxies](../decisions/infra-ghcr-via-artifact-registry.md): Rationale for invariant 3.
- [GCS dashboards bucket, its service accounts, WIF bindings, and runtime reads](../architecture/infra-dashboards-gcs-bucket.md): the dashboards bucket covered by invariant 11
