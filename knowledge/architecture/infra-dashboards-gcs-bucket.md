---
type: Architecture
title: "GCS dashboards bucket, its service accounts, WIF bindings, and runtime reads"
description: "Pulumi-managed biocirv-{env}-dashboards bucket (private, 90-day lifecycle on dated prefixes), bucket-scoped publisher and reader SAs, and the webservice read path."
tags: [infra, gcs, dashboards, iam, wif, pulumi, webservice]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:19Z" }
status: stable
code_refs: ["deployment/cloud/gcp/infrastructure/storage.py", "deployment/cloud/gcp/infrastructure/iam.py", "deployment/cloud/gcp/infrastructure/wif.py", "deployment/cloud/gcp/infrastructure/config.py", "deployment/cloud/gcp/infrastructure/cloud_run.py", "deployment/cloud/gcp/infrastructure/deploy.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/dashboard_loader.py", "src/ca_biositing/webservice/ca_biositing/webservice/main.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/519", "https://github.com/sustainability-software-lab/ca-biositing/pull/520", "https://github.com/sustainability-software-lab/ca-biositing/pull/529", "https://github.com/sustainability-software-lab/ca-biositing/pull/527", "commit 752a80d", "commit 7af19de", "commit 3eba913"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Holds the generated BioCirV dashboards and the DB snapshot cache outside git. Created by the Pulumi program per stack (staging and production). CI writes to it, the public Pages build and the webservice read from it. Added by #519 (PR #520, commit 752a80d); the webservice read side came with PR #529 (commit 7af19de).

## Key files
| path:line | role |
|---|---|
| deployment/cloud/gcp/infrastructure/config.py:30 | DASHBOARDS_BUCKET_NAME = biocirv-{STACK_NAME}-dashboards |
| deployment/cloud/gcp/infrastructure/config.py:68-69 | SA ids biocirv-{sa-env}-dash-pub (publisher) and biocirv-{sa-env}-dash-read (reader), within the 30-char limit |
| deployment/cloud/gcp/infrastructure/storage.py:110-126 | dashboards bucket: uniform access, force_destroy only on staging (line 115), lifecycle Delete for prefix dashboards/{env}/20 at age 90 (lines 116-124) |
| deployment/cloud/gcp/infrastructure/storage.py:128-148 | objectAdmin for the publisher SA, objectViewer for the reader SA |
| deployment/cloud/gcp/infrastructure/storage.py:150-159 | objectViewer for the webservice SA |
| deployment/cloud/gcp/infrastructure/iam.py:83-94 | dashboards-publisher and dashboards-reader SA definitions with no project-level roles |
| deployment/cloud/gcp/infrastructure/wif.py:124-130 | principal set keyed on attribute.repository only |
| deployment/cloud/gcp/infrastructure/wif.py:140-149 | WIF impersonation bindings for the publisher and reader SAs |
| deployment/cloud/gcp/infrastructure/cloud_run.py:110-117 | webservice env DASHBOARDS_BUCKET_NAME and DASHBOARDS_GCS_PREFIX = dashboards/{env}/latest |
| deployment/cloud/gcp/infrastructure/deploy.py:132 | export dashboards_bucket_name |
| src/ca_biositing/webservice/ca_biositing/webservice/services/dashboard_loader.py:305 | load_dashboard_asset: local exports/plots first, then GCS |
| src/ca_biositing/webservice/ca_biositing/webservice/services/dashboard_loader.py:249 | _fetch_from_gcs: blob read with 60 s TTL and ETag cache |
| src/ca_biositing/webservice/ca_biositing/webservice/main.py:182-185 | /v1/dashboards/{subpath} route, auth gate at main.py:141-174 |

## How it works
1. Pulumi creates the bucket and three IAM layers: the publisher SA (write), the reader SA (read), and the webservice SA (read). The bucket has no allUsers binding.
2. CI authenticates with WIF as the publisher SA and writes dated and latest prefixes (see architecture/ci-dashboard-artifacts-publisher).
3. The Pages build authenticates as the reader SA and copies an allowlisted subset (see architecture/ci-gh-pages-gallery-consumer).
4. The webservice reads with its own Cloud Run identity through Application Default Credentials. dashboard_loader.py:224-236 builds a google-auth REST client with the devstorage.read_only scope when google-cloud-storage is not used. Local exports/plots/ wins if present (dashboard_loader.py:305-345), which is the normal case on a developer machine. Cloud Run containers have no exports/plots, so they fall through to GCS.
5. Layout: dashboards/{env}/{YYYY-MM-DD}-{sha8}/ (dated, expires at 90 days), dashboards/{env}/latest/ (rolling pointer), snapshots/{env}/latest/ (DB snapshot and insights cache, never expired).

## Gotchas
- Not public. The issue #519 proposal asked for public read. The code is private: no allUsers binding on this bucket (storage.py:110-148). deployment/README.md:1000 says public access prevention is "enforced", but storage.py sets no public_access_prevention argument. See bugs/doc-drift-dashboard-privacy-gate.
- The deployer SA holds project-level roles/storage.admin (wif.py:86), so it can also read and write this bucket. The publisher and reader SAs are not the only identities with access.
- The lifecycle rule matches only the prefix dashboards/{env}/20 (storage.py:121). A dated folder whose name does not start with 20 would never expire. latest/ and snapshots/ are safe.
- force_destroy is true only on staging (storage.py:115). Production bucket objects block a stack destroy.
- Production has no writer. The production stack creates the bucket and reads dashboards/production/latest, but CI publishes only staging. See bugs/dashboards-production-latest-unpublished.
- The GOOGLE_APPLICATION_CREDENTIALS variable is deliberately not set on the webservice (comment above cloud_run.py:118-123), so the ADC path uses the attached Cloud Run SA.

## History
- 752a80d (2026-10-19, PR #520, issue #519): bucket, dashboards SAs, WIF bindings, webservice env vars, and the dashboards_bucket_name export.
- 7af19de (2026-10-19, PR #529): google-auth REST GCS adapter in dashboard_loader.py. This commit is not a deployment change; its infra effect is the webservice read path above.
- 3eba913 (PR #527): docs for the store in deployment/README.md. Partly stale (see bugs/doc-drift-dashboard-privacy-gate).
- Issue #519 closed 2026-10-19.

## Open questions
- Should production get its own publish path (matrix or a second job) or should the webservice prefix stay staging-only? (owner decision)

# Related Concepts
- [GCP cloud topology per environment (Cloud Run, Cloud SQL, AR proxies, GCS, WIF)](infra-cloud-topology.md): the bucket and its SAs are one more box in the per-environment topology
- [Pulumi Automation API program: modules, stacks, naming, and commands](infra-pulumi-program.md): the program that creates the bucket, SAs and bindings
- [Decision: keyless GitHub Actions to GCP via Workload Identity Federation](../decisions/infra-wif-keyless-ci.md): the publisher and reader SAs are impersonated through the same WIF pool
- [dashboard-artifacts.yml: builds the dashboard suite and publishes it to GCS](ci-dashboard-artifacts-publisher.md): the CI job that writes the dated and latest prefixes
- [gh-pages.yml: builds the public Pages gallery from the GCS latest bundle](ci-gh-pages-gallery-consumer.md): the Pages build that reads latest/ as the reader SA
- [Decision: store generated dashboards in a GCS bucket instead of committing them to git (#519)](../decisions/dashboards-gcs-over-committed-exports.md): the decision (#519) that created this store
- [Webservice deployment on GCP Cloud Run](webservice-deployment-cloud-run.md): the webservice revision that receives the dashboards env vars
