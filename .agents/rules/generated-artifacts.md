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

- `exports/plots/**` — All generated HTML dashboards, collaborator slices, and
  PNG charts (including `exports/plots/index.html`, `exports/plots/login.html`,
  `exports/plots/metadata/*.html`, and `exports/plots/audit/*.html`).
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
   - On `push` to `main`, scheduled runs, and manual dispatch,
     `.github/workflows/dashboard-artifacts.yml` builds the dashboard suite and
     publishes to both:
     - `gs://biocirv-{env}-dashboards/dashboards/{env}/{YYYY-MM-DD}-{short_sha}/`
       (immutable dated snapshot, retained for 90 days via bucket lifecycle
       rules)
     - `gs://biocirv-{env}-dashboards/dashboards/{env}/latest/` (canonical
       latest bundle consumed by `.github/workflows/gh-pages.yml` and the
       FastAPI `/v1/dashboards/*` portal route)
   - Non-git data caches used for deterministic CI builds live under
     `gs://biocirv-{env}-dashboards/snapshots/{env}/latest/`.
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
