---
type: Architecture
title: "dashboard-artifacts.yml: builds the dashboard suite and publishes it to GCS"
description: "Workflow triggers, snapshot and fingerprint fallbacks, the #533 guard against publishing seed fixtures, and the dated and latest publish layout for the staging bucket."
tags: [ci, github-actions, dashboards, gcs, publish]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:21Z" }
status: stable
code_refs: [".github/workflows/dashboard-artifacts.yml", "scripts/generate_dashboard_gallery.py", "tests/fixtures/minimal_dashboard_snapshot.json", "tests/fixtures/minimal_env_fingerprint.json", "tests/analysis/test_resource_audit_workbench.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/521", "https://github.com/sustainability-software-lab/ca-biositing/pull/533", "commit 1fcadb4", "commit bd72222", ".github/workflows/dashboard-artifacts.yml"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Builds the BioCirV drift dashboard and the Product 1 to 5 analysis dashboards, then publishes them to gs://biocirv-staging-dashboards. Introduced by #519 (PR #521, commit 1fcadb4), guarded by #533 (commit bd72222).

## Key files
| path:line | role |
|---|---|
| .github/workflows/dashboard-artifacts.yml:21-22 | schedule, Mondays 09:00 UTC |
| .github/workflows/dashboard-artifacts.yml:23-58 | push to main and pull_request path filters, workflow_run after Trigger Staging ETL or Trigger Production ETL |
| .github/workflows/dashboard-artifacts.yml:64-72 | env: staging only (DASHBOARDS_ENV line 68), bucket name, WIF provider, publisher SA, snapshot path |
| .github/workflows/dashboard-artifacts.yml:103-111 | GCP auth as the publisher SA, skipped on pull_request (line 105) |
| .github/workflows/dashboard-artifacts.yml:118-134 | pull the snapshot cache, fingerprints and insights from GCS |
| .github/workflows/dashboard-artifacts.yml:136-155 | fallback to tests/fixtures/minimal_* and set USED_MINIMAL_FIXTURE |
| .github/workflows/dashboard-artifacts.yml:157-186 | source mode: a TCP probe to POSTGRES_HOST:POSTGRES_PORT selects live_db, else snapshot |
| .github/workflows/dashboard-artifacts.yml:188-289 | drift report, Product 1 to 4 builds, gallery, node --check of inline scripts |
| .github/workflows/dashboard-artifacts.yml:300-327 | publish step, including the #533 skip (305-308) and the live_db snapshot copy (320-327) |
| .github/workflows/dashboard-artifacts.yml:329-344 | 30-day Actions artifact with the same HTML |
| tests/fixtures/minimal_dashboard_snapshot.json | 37 rows, 3 resources, about 15.8 KB |
| tests/fixtures/minimal_env_fingerprint.json | synthetic fingerprint, is_measured false, about 9.5 KB |
| tests/analysis/test_resource_audit_workbench.py (end of file) | string-match test that the YAML contains the guard lines (added in bd72222) |

## How it works
1. Auth to GCP (continue-on-error). If auth fails, no publish happens.
2. Cache pull: snapshots/staging/latest/baseline_records_snapshot.json, falling back to dashboards/staging/latest/metadata/dashboard_data_snapshot.json; also resource_ai_insights.json and env_fingerprints/*_fingerprint.json.
3. Fallback: if the snapshot is still missing, use the minimal dashboard fixture. Missing local, staging and production fingerprints are seeded from the minimal fingerprint fixture. Either path sets USED_MINIMAL_FIXTURE=true in GITHUB_ENV.
4. Source mode: snapshot unless a live PostgreSQL answers the probe. In live_db mode the local fingerprint is extracted and drift is compared against the live DB.
5. Publish (not on pull_request, and only if auth succeeded):
   - Skip with exit 0 and a warning if USED_MINIMAL_FIXTURE is true and mode is not live_db (305-308). This is the #533 guard.
   - Probe the bucket. If unreachable, warn and exit 0 (309-312).
   - rsync exports/plots/ to gs://biocirv-staging-dashboards/dashboards/staging/{YYYY-MM-DD}-{sha8}/ and to .../latest/ (318-319).
   - In live_db mode only, copy dashboard_data_snapshot.json to snapshots/staging/latest/baseline_records_snapshot.json, plus insights and all *_fingerprint.json files (320-327).

## Gotchas
- The #533 guard covers only the latest/ rsync. It does not cover the snapshots/ copy at lines 320-327, which can receive seeded fingerprints in live_db mode. See bugs/dashboard-seed-fingerprints-cached-in-live-db.
- Silent green runs: the publish step can exit 0 while publishing nothing (auth failure, unreachable bucket, or the #533 skip). Check the ::warning:: lines in the run log.
- rsync runs without a delete flag (line 318-319), so objects removed from a build stay in latest/ (inferred from the flags).
- Only staging is published. DASHBOARDS_ENV is hard-coded (line 68).
- The #533 test is a string-match test on the YAML. It does not run the workflow, so it would not catch a logic regression.
- Pull requests never authenticate here (line 105), so PR builds validate and upload the Actions artifact only.

## History
- 1fcadb4 (2026-10-19, PR #521): workflow wired to GCS, minimal fixtures added.
- c4cbf2d (PR #525): Product 4 workbench and 5-product gallery added to the build.
- bd72222 (2026-10-21, PR #533): three safeguards: secondary GCS snapshot fallback, USED_MINIMAL_FIXTURE guard on latest/, and live_db snapshot sync.
- a2c8de8 (2026-10-22, PR #535): HEAD for this slice; the Report a Bug modal change does not touch the publish path.

## Open questions
- Should the live_db snapshot sync skip fingerprints that are not measured (is_measured false)? (inferred need)
- Is a production publish intended? (see bugs/dashboards-production-latest-unpublished)

# Related Concepts
- [GCS dashboards bucket, its service accounts, WIF bindings, and runtime reads](infra-dashboards-gcs-bucket.md): the bucket and publisher SA this workflow writes to
- [gh-pages.yml: builds the public Pages gallery from the GCS latest bundle](ci-gh-pages-gallery-consumer.md): consumes latest/ after this workflow completes
- [GitHub Actions workflows: what runs on PRs, main, releases and deploys](tooling-ci-workflows.md): the workflow map this job belongs to
- [Generated dashboards, fingerprints, drift reports and insights are never committed to git](../requirements/generated-artifacts-never-committed.md): the rule that makes CI publishing the only home for these outputs
- [Decision: keyless GitHub Actions to GCP via Workload Identity Federation](../decisions/infra-wif-keyless-ci.md): the WIF auth this job uses
