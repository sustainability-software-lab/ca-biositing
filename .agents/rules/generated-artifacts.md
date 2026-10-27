# Generated Artifacts

**Load when:** Generating HTML dashboards, environment fingerprints, drift
reports, or AI insights JSONs, or editing CI artifact workflows.

## Core Rule: Never Commit Generated Dashboards or Audit Snapshots

Self-contained Plotly HTML dashboards, environment database fingerprints, drift
reports, and LLM insights caches are **build/publish outputs**, not source code.
They must never be committed to git or bypassed into the index via `git add -f`.

### Forbidden Paths in Git

The following generated artifact paths are ignored in
[`.gitignore`](../../.gitignore) and actively blocked by the
`forbid-generated-artifacts` pre-commit hook:

- `exports/plots/**` and `exports/*.html` — All generated HTML dashboards,
  collaborator slices, and PNG charts (including `exports/plots/index.html`,
  `exports/plots/login.html`, `exports/plots/metadata/*.html`,
  `exports/plots/audit/*.html`, and top-level `exports/*.html`).
- `data/insights/resource_ai_insights.json` — Generated BioCirV AI / LLM
  synthesis cache.
- `audit/output/env_fingerprints/*.json` — Per-environment database schema/row
  fingerprint snapshots (`local_fingerprint.json`, `staging_fingerprint.json`,
  `production_fingerprint.json`, and `baseline_records_snapshot.json`).
- `audit/output/drift_report.md` — Generated multi-environment database drift
  markdown summary.

> **Exception for Human-Curated Seed Data:** Small, human-curated seed CSVs such
> as `data/qc/qc_review_decisions_seed.csv` are explicitly allowlisted in
> [`.gitignore`](../../.gitignore) (`!data/qc/` and
> `!data/qc/qc_review_decisions_seed.csv`) and are tracked in git.

## Where Generated Artifacts Live Instead

1. **Google Cloud Storage (`gs://biocirv-{env}-dashboards/`):**
   - `.github/workflows/dashboard-artifacts.yml` builds the 5-product dashboard
     suite and publishes to both:
     - `gs://biocirv-{env}-dashboards/dashboards/{env}/{YYYY-MM-DD}-{short_sha}/`
       (immutable dated snapshot, retained for 90 days via bucket lifecycle
       rules)
     - `gs://biocirv-{env}-dashboards/dashboards/{env}/latest/` (canonical
       latest bundle consumed by `.github/workflows/gh-pages.yml` and the
       FastAPI `/v1/dashboards/*` portal route)
   - Non-git data caches used for deterministic CI builds live under
     `gs://biocirv-{env}-dashboards/snapshots/{env}/latest/`.
   - **Two-Tier CI Refresh Model:**
     - **Tier 1 — Cloud-Autonomous Live Refresh (`mode=live_db`):** Triggered on
       the nightly cron schedule (`0 9 * * *`), `workflow_run` after
       `Trigger Staging ETL` or `Trigger Production ETL` completes, and manual
       dispatch
       (`gh workflow run dashboard-artifacts.yml -f data_source=live_db`).
       Authenticates via workflow-scoped Workload Identity Federation to
       `biocirv-{env}-dash-pub` (Pulumi resource `sa-dashboards-publisher`),
       opens Cloud SQL Auth Proxy tunnels to Staging (`:5434`) and Production
       (`:5435`) using strictly read-only credentials (`biocirv_readonly`),
       performs a single-pass live data extraction (`LIVE_SNAPSHOT_EXTRACTED`),
       recomputes `data/insights/resource_ai_insights.json`, extracts verified
       live `staging_fingerprint.json` and `production_fingerprint.json`
       (`--extract-env <env> --verify-readonly-grants --fail-on-unmeasured`),
       builds all 5 HTML products, and writes the fresh snapshot, insights
       sidecar, and verified staging/production fingerprints back to
       `gs://biocirv-{env}-dashboards/snapshots/{env}/latest/` (only overwriting
       a fingerprint in GCS when its live extraction succeeded).
     - **Tier 2 — Fast Offline Snapshot Re-render (`mode=snapshot`):**
       - On `push` to `main` (and `workflow_dispatch -f data_source=snapshot`),
         authenticates to GCS, pulls the latest cached snapshot, insights
         sidecar, and environment fingerprints from
         `gs://biocirv-{env}-dashboards/snapshots/{env}/latest/`, re-renders all
         5 HTML products in ~2 minutes without opening Cloud SQL tunnels, and
         publishes the updated HTML bundle to GCS.
       - On `pull_request`, skips GCP authentication and GCS writes altogether,
         falling back to the tracked minimal fixtures in
         `tests/fixtures/minimal_*` to validate HTML and inline JavaScript
         generation offline.
   - **Manual Local Baseline Fingerprint Lifecycle (`local_fingerprint.json`):**
     - Automated CI runs never overwrite `local_fingerprint.json` in GCS.
       `local_fingerprint.json` is only re-uploaded manually by a developer when
       the local development baseline intentionally changes (e.g., after an
       Alembic migration or seed update) via:
       ```bash
       pixi run python analysis/audit/db_environment_drift.py --extract-env local --fail-on-unmeasured
       gcloud storage cp audit/output/env_fingerprints/local_fingerprint.json \
         gs://biocirv-staging-dashboards/snapshots/staging/latest/env_fingerprints/local_fingerprint.json
       ```
2. **Compact CI Test Fixtures (`tests/fixtures/minimal_*`):**
   - Pull request CI and unit tests validate dashboard and drift generators
     against compact, deterministic synthetic fixtures
     (`tests/fixtures/minimal_dashboard_snapshot.json` `< 35 KB` and
     `tests/fixtures/minimal_env_fingerprint.json` `< 15 KB`) rather than
     multi-megabyte database dumps.
3. **Local Developer Workflow:**
   - Generating files locally into `exports/plots/` is encouraged for
     development and inspection; the FastAPI service serves local
     `exports/plots/` files when present on disk and falls back to GCS
     otherwise. Leave local `exports/plots/` outputs untracked.

## Enforcement Guardrails

Two pre-commit and CI hooks in
[`.pre-commit-config.yaml`](../../.pre-commit-config.yaml) enforce this rule:

1. **`forbid-generated-artifacts`
   ([`scripts/check_no_generated_artifacts.py`](../../scripts/check_no_generated_artifacts.py)):**
   - Inspects both staged/passed filenames and `git ls-files` and fails if any
     file matches the forbidden paths above.
   - Run manually with:
     ```bash
     pixi run python scripts/check_no_generated_artifacts.py
     ```
2. **`check-added-large-files` (`--maxkb=500`):**
   - Rejects any newly staged file larger than `500 KB`, without an exclusion
     for `exports/plots/`.

If you accidentally stage a generated artifact (`git add -f`), untrack it before
committing:

```bash
git rm --cached <file>
```
