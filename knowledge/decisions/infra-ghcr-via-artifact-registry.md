---
type: Decision
title: "Decision: images built to GHCR, pulled by Cloud Run through Artifact Registry proxies"
description: "Why images are built to GHCR but Cloud Run pulls them through shared Artifact Registry proxy repos (ghcr-proxy, quayio-proxy), and what replaced Cloud Build."
tags: [decision, images, ghcr, artifact-registry, cloud-run]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:33Z" }
status: stable
code_refs: ["deployment/cloud/gcp/infrastructure/artifact_registry.py", "deployment/cloud/gcp/infrastructure/config.py", ".github/workflows/docker-build.yml", "deployment/cloud/gcp/cloudbuild.yaml"]
sources: ["commit 4e271b6", "commit 12b3592", "commit ca4d573", "commit f6ee2ee", "https://github.com/sustainability-software-lab/ca-biositing/pull/192", "https://github.com/sustainability-software-lab/ca-biositing/pull/193"]
governance: context
---

## Decision
- Images (`pipeline`, `webservice`) are built by `docker-build.yml` and pushed to `ghcr.io/sustainability-software-lab/ca-biositing/<name>`.
- Cloud Run references `us-west1-docker.pkg.dev/biocirv-470318/ghcr-proxy/...`, a Docker remote repo that proxies GHCR. Quay.io images (oauth2-proxy) use `quayio-proxy` the same way.

## Context and reasoning
- 5bdefc9 / 13675d8 (PR #189): CI first built images with Cloud Build into `gcr.io/$PROJECT_ID` (cloudbuild.yaml still shows this).
- 4e271b6 (PR #192, 2026-03-20): dropped the Cloud Build step. Cloud Build could not run because `.git` was excluded from the upload and hatch-vcs needed it. "Since docker-build.yml already pushes identical images to GHCR and the repo is public, Cloud Run can pull directly from GHCR."
- 12b3592 (PR #193): "Cloud Run rejects direct GHCR URLs — it only accepts images from gcr.io, docker.pkg.dev, or docker.io." So an AR remote repo was added.
- ca4d573 (PR #194), f6ee2ee (PR #196), 9ea84ed, d2bde31: deployer SA needed `artifactregistry.admin` and ordering so the AR repo exists before Cloud Run.

## Alternatives considered
- Pull GHCR directly: rejected by Cloud Run’s registry allow-list (commit 12b3592).
- Push to Artifact Registry directly from CI: not chosen in the history; the GHCR build is reused for local and cloud.
- Cloud Build: removed from the deploy path (4e271b6).

## Trade-offs
- Gain: one build artifact shared by local, staging, production; no GCP build credits or Cloud Build bucket dependency for images.
- Cost: AR remote repos proxy GHCR at pull time, so a GHCR outage or a tag move affects Cloud Run pulls; the repo must stay public or the proxy needs GHCR credentials (repo is public per 4e271b6; inferred for the proxy case).
- Cost: image refs in Pulumi are strings with a tag, so `:latest` needs an explicit redeploy (see architecture/infra-cloud-topology Gotchas).

## Open questions
- Whether the `cloudbuild.yaml` in deployment/cloud/gcp is still needed (it targets gcr.io and is not referenced by any workflow; see bugs/doc-drift-infra).

# Related Concepts
- [GCP cloud topology per environment (Cloud Run, Cloud SQL, AR proxies, GCS, WIF)](../architecture/infra-cloud-topology.md): The AR repos are part of the topology.
- [GitHub Actions deploy chain: docker-build, staging/production deploy, migrations, ETL trigger](../architecture/infra-ci-cd-pipelines.md): docker-build.yml is the producer of the images.
- [System overview (start here)](../architecture/system-overview.md): Images are the deployable artifacts of the system.
