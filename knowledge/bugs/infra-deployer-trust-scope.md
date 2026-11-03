---
type: Bug
title: "Open risk: deployer SA trusts any workflow in the repo; PR runs authenticate to GCP"
description: "Open risk: WIF trust is repo-wide and the deployer SA holds run.admin, projectIamAdmin, and secretmanager.admin; PR workflows can request it. Mitigation unverified."
tags: [security, wif, iam, github-actions, open-risk]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:14Z" }
status: stable
governance: context
code_refs: ["deployment/cloud/gcp/infrastructure/wif.py", "deployment/cloud/gcp/infrastructure/storage.py", ".github/workflows/deploy-staging.yml", ".github/workflows/dashboard-artifacts.yml"]
stale_after: "2027-01-16"
sources: ["deployment/cloud/gcp/infrastructure/wif.py", ".github/workflows/deploy-staging.yml", "commit 13675d8", "commit 701fd3a", "https://github.com/sustainability-software-lab/ca-biositing/pull/189", "https://github.com/sustainability-software-lab/ca-biositing/pull/249", "commit 752a80d", "commit 1fcadb4"]
---

## Status
Open, unverified in the live GitHub or GCP settings. Derived from the code at a2c8de8.

## Symptom / risk
- The attribute condition matches only assertion.repository (wif.py:55). The principal set is keyed on attribute.repository alone (wif.py:124-130). No branch, ref or environment condition is set.
- The deployer SA holds roles/run.admin, roles/resourcemanager.projectIamAdmin, roles/secretmanager.admin, roles/iam.serviceAccountAdmin, roles/cloudsql.admin, roles/artifactregistry.admin and roles/storage.admin at project level (wif.py:76-107). These roles can read secrets and grant IAM.
- The dashboards publisher SA has roles/storage.objectAdmin on the dashboards bucket (storage.py:128-137), and the reader SA can read the private dashboards (storage.py:139-148). Both are impersonable from the same principal set (wif.py:140-149).
- deploy-staging.yml runs a preview job on pull_request with WIF and id-token: write. Any same-repo PR branch runs that job with the same identity. The job runs a preview, not an apply, but a workflow edited in a PR can run arbitrary steps under the token.
- dashboard-artifacts.yml obtains the publisher token only when github.event_name is not pull_request (line 105). That condition is the only gate. A same-repo branch that edits the workflow file, for example to delete the condition, would obtain the publisher token (inferred from GitHub’s behaviour of running the PR head’s workflow file; not tested).
- Fork PRs get a different assertion.repository and should be rejected by the condition. That is inferred from GitHub’s OIDC claim behaviour, not tested here.

## Reproduction / evidence
- Read wif.py, storage.py, dashboard-artifacts.yml and deploy-staging.yml at a2c8de8. No test or policy exists.

## Likely root cause
Trust was set up for the deploy path (WIF commit 13675d8, PR #189) and not narrowed when PR previews (deploy-staging preview) or the dashboards SAs (752a80d) were added.

## Open questions
- Are GitHub environment protection rules set on staging and production, and do they restrict branches? The environment keys help only if rules are configured.
- Suggested fix direction (not implemented): add attribute.ref or assertion.event_name conditions to the provider, or use separate pools for preview, publish and deploy.

# Related Concepts
- [Decision: keyless GitHub Actions to GCP via Workload Identity Federation](../decisions/infra-wif-keyless-ci.md): The decision whose trust scope this bug describes.
- [GitHub Actions deploy chain: docker-build, staging/production deploy, migrations, ETL trigger](../architecture/infra-ci-cd-pipelines.md): Where the PR preview job authenticates.
- [System overview (start here)](../architecture/system-overview.md): Deploy identity protects the cloud data and secrets of the system.
- [dashboard-artifacts.yml: builds the dashboard suite and publishes it to GCS](../architecture/ci-dashboard-artifacts-publisher.md): the publish job whose gate is the event condition
