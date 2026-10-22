---
type: Decision
title: "Decision: keyless GitHub Actions to GCP via Workload Identity Federation"
description: "Why CI authenticates to GCP with WIF and a deployer service account instead of a stored JSON key, and which roles the deployer holds."
tags: [decision, security, wif, github-actions, iam]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:13Z" }
status: stable
governance: context
code_refs: ["deployment/cloud/gcp/infrastructure/wif.py", "deployment/cloud/gcp/infrastructure/config.py", ".github/workflows/deploy-staging.yml", ".github/workflows/deploy-production.yml", ".github/workflows/dashboard-artifacts.yml", ".github/workflows/gh-pages.yml"]
sources: ["deployment/cloud/gcp/infrastructure/wif.py", "commit 13675d8", "commit 701fd3a", "commit 7c86993", "commit d2bde31", "https://github.com/sustainability-software-lab/ca-biositing/pull/189", "https://github.com/sustainability-software-lab/ca-biositing/pull/249", "commit 752a80d", "https://github.com/sustainability-software-lab/ca-biositing/pull/520"]
---

## Decision
GitHub Actions obtains a GCP token by exchanging its OIDC token through a Workload Identity Pool (github-actions-{env}) and provider (github-oidc-{env}) and impersonates SAs. The deployer SA is biocirv-{sa-env}-gh-deploy. Since #520, the dashboards publisher and reader SAs are also impersonable through the same pool. No service account key is stored in GitHub secrets (deployment/README.md, Authentication).

## Context and reasoning
- 13675d8 (PR #189, 2026-03-20): WIF Pulumi module added for keyless auth.
- Provider attribute condition: assertion.repository == the repo (wif.py:55). The principal set is keyed on attribute.repository only (wif.py:124-130).
- Deployer roles (wif.py:76-87): cloudbuild.builds.editor, iam.serviceAccountUser, run.admin, viewer, cloudsql.admin, iam.serviceAccountAdmin, secretmanager.admin, resourcemanager.projectIamAdmin, artifactregistry.admin, storage.admin. Bucket-level storage.admin on the Pulumi state bucket (wif.py:104-111) and the Cloud Build staging bucket (wif.py:115-122).
- Impersonation bindings: deployer (wif.py:133-138); dashboards publisher and reader (wif.py:140-149, added by 752a80d).
- 701fd3a (PR #249) removed over-broad runtime SA roles. The deployer’s roles were not reduced.

## Alternatives considered
- JSON key in GitHub secrets: not used (deployment/README.md says keyless is the design).
- Per-environment WIF pools: yes, the pool id includes the stack name (config.py:72).
- Separate pool for dashboards SAs: not done. Both publisher and reader share the repo-wide principal set.

## Trade-offs
- Gain: no long-lived credential; the token is scoped to the repo attribute.
- Cost: the deployer holds powerful project roles, and the publisher SA can write the dashboards bucket. Any workflow in the repo that can request an ID token can act as one of these identities. See bugs/infra-deployer-trust-scope.

## Open questions
- Whether attribute.ref or environment conditions should narrow impersonation to main or production runs. Not configured today; confirm the intent.

# Related Concepts
- [GitHub Actions deploy chain: docker-build, staging/production deploy, migrations, ETL trigger](../architecture/infra-ci-cd-pipelines.md): Every deploy job uses this auth.
- [Open risk: deployer SA trusts any workflow in the repo; PR runs authenticate to GCP](../bugs/infra-deployer-trust-scope.md): Risk that follows from the repo-wide trust scope.
- [GCP cloud topology per environment (Cloud Run, Cloud SQL, AR proxies, GCS, WIF)](../architecture/infra-cloud-topology.md): Deployer SA and WIF are part of the GCP identity layer.
- [GCS dashboards bucket, its service accounts, WIF bindings, and runtime reads](../architecture/infra-dashboards-gcs-bucket.md): the publisher and reader SAs bound through this pool
- [dashboard-artifacts.yml: builds the dashboard suite and publishes it to GCS](../architecture/ci-dashboard-artifacts-publisher.md): the dashboards workflow that authenticates with this pool
