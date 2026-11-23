---
type: Bug
title: live_db runs can copy seeded minimal fingerprints into the GCS snapshot cache
description: "In live_db mode the #533 guard does not block the snapshots/ upload, so missing staging or production fingerprints seeded from the CI fixture can be written back to GCS and reused."
tags: [bug, dashboards, ci, fixtures, gcs]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:25Z" }
status: stable
code_refs: [".github/workflows/dashboard-artifacts.yml", "tests/fixtures/minimal_env_fingerprint.json"]
sources: ["commit bd72222", "https://github.com/sustainability-software-lab/ca-biositing/pull/533", ".github/workflows/dashboard-artifacts.yml"]
governance: context
stale_after: "2026-12-31"
---

## Symptom (code path; not reproduced)
In live_db mode, the publish step skips the #533 guard (dashboard-artifacts.yml:305 checks mode != live_db), then copies every audit/output/env_fingerprints/*_fingerprint.json to snapshots/staging/latest/env_fingerprints/. That glob includes files that were seeded from the minimal fixture.

## Evidence
- .github/workflows/dashboard-artifacts.yml:147-154: when local, staging or production fingerprint files are missing, each is copied from tests/fixtures/minimal_env_fingerprint.json and USED_MINIMAL_FIXTURE is set.
- .github/workflows/dashboard-artifacts.yml:133-134: the pull step restores env_fingerprints/*_fingerprint.json from GCS only when present.
- .github/workflows/dashboard-artifacts.yml:305-308: the guard exempts live_db runs.
- .github/workflows/dashboard-artifacts.yml:325-326: in live_db mode the glob copies all *_fingerprint.json back to GCS.
- tests/fixtures/minimal_env_fingerprint.json: is_measured false, capture_mode unmeasured_offline, captured_at 2026-10-18.

## Impact (inferred)
A first live_db run, or any run after the GCS env_fingerprints folder is emptied, can write seeded staging and production fingerprints into the cache. Later runs read them back as if they were measured. The drift dashboard labels them unmeasured, which limits the damage, but the cache itself is wrong.

## Fix direction
Upload only the freshly extracted local fingerprint in live_db mode, or skip any fingerprint whose is_measured is false.

## Status
Open at a2c8de8 (commit bd72222 added the live_db sync and did not add this filter).

# Related Concepts
- [dashboard-artifacts.yml: builds the dashboard suite and publishes it to GCS](../architecture/ci-dashboard-artifacts-publisher.md): the workflow whose live_db sync this bug is in
- [Open risk: deployer SA trusts any workflow in the repo; PR runs authenticate to GCP](infra-deployer-trust-scope.md): a different gap in the same publish path
