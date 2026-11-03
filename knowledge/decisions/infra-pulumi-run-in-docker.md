---
type: Decision
title: "Decision: run Pulumi in a Linux Docker container locally, directly in CI"
description: "Why Pulumi commands on macOS are wrapped in the ca-biositing-pulumi Docker image (macOS gRPC crash), while GitHub Actions runs the same program directly on Linux."
tags: [decision, pulumi, docker, macos, ci]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:32Z" }
status: stable
code_refs: ["scripts/pulumi-docker.sh", "deployment/cloud/gcp/infrastructure/Dockerfile", "pixi.toml"]
sources: ["scripts/pulumi-docker.sh", "deployment/cloud/gcp/infrastructure/Dockerfile", "commit 5bdefc9", "commit 60374d8", "commit b6459cd", "commit 79f9344"]
governance: context
---

## Decision
Local Pulumi runs go through `scripts/pulumi-docker.sh` (`cloud-plan`, `cloud-deploy`, `cloud-refresh`, `cloud-outputs`, `cloud-destroy`). CI and Linux workstations use the `*-direct` tasks, which call `python deployment/cloud/gcp/infrastructure/deploy.py` on the host.

## Context and reasoning
- Commit 5bdefc9 (PR #125, 2026-02-19): "All Pulumi commands run inside Docker to avoid macOS Sequoia gRPC crash (exit -1)."
- The Dockerfile (deployment/cloud/gcp/infrastructure/Dockerfile) is `python:3.12-slim` plus the Pulumi CLI and `pulumi-gcp==9.16.0`, `pulumi-random`, running as user `pulumi`.
- Same Dockerfile carries the pulumi-gcp pin history: 60374d8 pinned `<9.16` to avoid a Cloud Run env var `value`/`valueSource` oneof bug; b6459cd removed the pin after switching to volume-mounted secrets; 79f9344 pinned `==9.16.0` explicitly.

## Alternatives considered
- Run Pulumi natively on macOS: rejected at the time because of the gRPC crash (commit message).
- Run everything in CI only: not chosen for local preview work; the `-direct` tasks exist for that reason.

## Trade-offs
- Gain: reproducible Linux runtime for local runs; no host Python/Pulumi setup beyond Docker.
- Cost: two code paths (`cloud-*` vs `cloud-*-direct`), each must be kept in sync; the Docker image pins its own pulumi-gcp, while the pixi `cloud` feature pins a range (`>=9,<10`), so local-direct and Docker runs can resolve different provider versions (inferred from the two pins; confirm with `pixi list` vs the image).
- The wrapper mounts `~/.config/gcloud` read-only and uses Application Default Credentials; secrets never enter the image.

## Open questions
- Whether the Docker image should be rebuilt in CI rather than only locally via `cloud-build` (pixi task `cloud-build`); no workflow builds it (verified by grep).

# Related Concepts
- [Pulumi Automation API program: modules, stacks, naming, and commands](../architecture/infra-pulumi-program.md): The program run by this wrapper.
- [Decision: Pulumi Python instead of OpenTofu/HCL for GCP infrastructure](infra-pulumi-over-opentofu.md): Parent decision to use Pulumi.
- [GitHub Actions deploy chain: docker-build, staging/production deploy, migrations, ETL trigger](../architecture/infra-ci-cd-pipelines.md): CI uses the -direct path.
