---
type: Architecture
title: "Multi-environment DB drift assessment (4 layers, local/staging/production)"
description: "analysis/audit/db_environment_drift.py extracts 4-layer fingerprints from local :5432, staging :5434 and production :5435 (Cloud SQL proxy), then writes a drift report and HTML dashboard."
tags: [audit, drift, postgres, dashboard, alembic, admin]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:11Z" }
status: stable
code_refs: ["analysis/audit/db_environment_drift.py", "tests/audit/test_db_environment_drift.py", "resources/config/db_reset.yaml", ".agents/skills/db-drift-assessment/SKILL.md", ".github/workflows/dashboard-artifacts.yml", "tests/fixtures/minimal_env_fingerprint.json"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/517", "https://github.com/sustainability-software-lab/ca-biositing/pull/535", "https://github.com/sustainability-software-lab/ca-biositing/pull/522", "commit 4f3e0be", "commit a2c8de8", "commit ae147f6"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Admin audit that compares the local, staging and production PostgreSQL databases layer by layer (schema, row counts, lineage, parameter values, and the analysis_data_view filter funnel). It writes a Markdown drift report and an interactive HTML dashboard. It only reads from the databases.

## Key files
| Path:line | Role |
| --- | --- |
| analysis/audit/db_environment_drift.py:80 | `ANALYSIS_TYPE_TO_TABLE`: 11 analysis types mapped to `*_record` tables |
| analysis/audit/db_environment_drift.py:409 | `DEFAULT_ENV_CONFIGS`: local 5432, staging 5434, production 5435 |
| analysis/audit/db_environment_drift.py:440 | `ANALYTICAL_TABLE_LABELS`: the 11 labels used as matrix columns |
| analysis/audit/db_environment_drift.py:487 | `load_db_reset_config()`: reads resources/config/db_reset.yaml and .env over the defaults |
| analysis/audit/db_environment_drift.py:657 | `_build_unmeasured_fingerprint()`: placeholder with `is_measured: False` |
| analysis/audit/db_environment_drift.py:778 | `extract_live_fingerprint()`: SQLAlchemy psycopg2 connect (connect_timeout 10), builds the 4 layers |
| analysis/audit/db_environment_drift.py:1210 | Zero-fill of the resource x analysis-type matrix |
| analysis/audit/db_environment_drift.py:1341 | Connection failure writes an unmeasured fingerprint instead of raising |
| analysis/audit/db_environment_drift.py:1347 | `compute_pair_comparison()` |
| analysis/audit/db_environment_drift.py:1717 | `generate_markdown_drift_report()` writes audit/output/drift_report.md |
| analysis/audit/db_environment_drift.py:1913 | `build_drift_dashboard_html()` writes exports/plots/audit/db_environment_drift_dashboard.html |
| analysis/audit/db_environment_drift.py:3934, 3963 | `run_compare()` and `main()` (CLI) |
| tests/audit/test_db_environment_drift.py:73 | Test that an unreachable DB yields the unmeasured fallback |

## How it works
Each environment yields one fingerprint JSON with four layers:
1. **Layer 1, schema:** `public.alembic_version`, column-signature hashes for the 21 core public tables, and `pg_matviews` freshness for the 19 views in `ALL_19_VIEWS` (ca_biositing and data_portal).
2. **Layer 2, row counts:** the 21 core tables, the 19 views, and totals such as `aim1_aim2_records`.
3. **Layer 3, coverage and lineage:** resource x analysis-type matrix with qc_pass / fail / other counts and record hashes, plus lineage sets for resource, field_sample, prepared_sample and experiment.
4. **Layer 4, parameters and funnels:** n, mean, SD, median, min and max per analysis type, parameter and unit; flags mean shifts above 5%; and the analysis_data_view funnel from candidate pool to final rows.

`--compare` builds three pairwise comparisons (local vs staging, staging vs production, local vs production). If a fingerprint file is missing, `run_compare` extracts it live first (analysis/audit/db_environment_drift.py:3934).

| Env | Default host:port | Database | Defaults come from |
| --- | --- | --- | --- |
| local | 127.0.0.1:5432 | biocirv_db | POSTGRES_* env vars (host forced to 127.0.0.1) |
| staging | 127.0.0.1:5434 (Cloud SQL Auth Proxy) | biocirv-staging | resources/config/db_reset.yaml; user `postgres`; password from DB_PASSWORD_STAGING or BIOCIRV_STAGING_USER_PW |
| production | 127.0.0.1:5435 (Cloud SQL Auth Proxy) | biocirv-production | same pattern as staging (DB_*_PROD, BIOCIRV_PRODUCTION_USER_PW) |

Commands: `pixi run db-drift-extract-local`, `db-drift-extract-staging`, `db-drift-extract-prod` and `db-drift-compare` (pixi.toml:247-250). The CLI takes `--extract-env {local,staging,production}` with `--host/--port/--dbname/--user/--password` overrides, plus `--extract-all` and `--compare`.

The fingerprint’s `connection` block holds host, port, database, user and schemas only; the password is not written to the JSON (analysis/audit/db_environment_drift.py:~695-702).

## Interfaces
- **Inputs:** the three PostgreSQL endpoints, resources/config/db_reset.yaml, `.env` and environment variables.
- **Outputs:** audit/output/env_fingerprints/<env>_fingerprint.json, audit/output/drift_report.md (both gitignored, .gitignore:152-153) and exports/plots/audit/db_environment_drift_dashboard.html (exports/plots is gitignored, .gitignore:142).
- **Callers:** `pixi run db-drift-compare`, and .github/workflows/dashboard-artifacts.yml. The workflow runs `--extract-env local` then `--compare`, and restores staging and production fingerprints from the GCS snapshot cache, or from tests/fixtures/minimal_env_fingerprint.json when the cache is empty.

## Gotchas
- **Analysis-type count is 11, not 10.** `ANALYTICAL_TABLE_LABELS` (line 440) has 11 labels and the zero-fill loop (line 1210) fills all of them, but the comment at line 1210 and `.agents/skills/db-drift-assessment/SKILL.md` both say 10.
- **Unmeasured is a state, not a zero-row database.** A failed connection writes `is_measured: false` with every count at zero. `compute_pair_comparison` checks `is_measured` (lines 1350-1351).
- **The HTML has no login of its own.** The webservice enforces admin on `audit/` paths and on `db_environment_drift_dashboard.html` (src/ca_biositing/webservice/ca_biositing/webservice/main.py:159). Copies published elsewhere are not covered by that check (inferred from the code; see architecture/analysis-dashboard-gallery-and-portal).
- The dashboard’s Report a Bug modal posts to the uw-ssec repo (analysis/audit/db_environment_drift.py:3805), unlike Products 1-3. See bugs/dashboards-report-bug-github-repo-mismatch.
- CI only extracts local live. Staging and production values in CI come from cache or fixture (inferred from the workflow steps).

## History
- 4f3e0be (PR #517, 2026-10-19): added the script, the db-drift-assessment skill, the pixi tasks, and tests/audit.
- ae147f6 (PR #522, 2026-10-19): audit/output and exports/plots stopped being tracked; the outputs are gitignored.
- a2c8de8 (PR #535, 2026-10-22): added the Report a Bug modal and HTML escaping of issue fields to the drift dashboard.

## Open questions
- Whether the staging and production fingerprints in the weekly workflow are ever refreshed live, or only from the GCS cache (inferred; confirm from a workflow run log).

# Related Concepts
- [Five-product BioCirV resource dashboard suite and how each is generated](analysis-resource-dashboard-suite.md): Product 5 of the five-product dashboard suite
- [Dashboard gallery index and login portal (scripts/generate_dashboard_gallery.py)](analysis-dashboard-gallery-and-portal.md): gallery card and webservice admin gate for this page
- [analysis_data_view and analysis_average_view: observation-level analysis layer](views-analysis-data-view.md): layer 4 funnel mirrors the analysis_data_view filters
- [Analysis chart exclusions must match the portal QC definitions](../requirements/analysis-qc-filter-parity.md): funnel exclusion lists must match the portal definitions
- [Pixi tasks for Alembic migrations, materialized views, DB reset, audits and pgschema](tooling-task-db-migrations-and-views.md): layer 1 compares alembic head and materialized view definitions
- [GitHub Actions workflows: what runs on PRs, main, releases and deploys](tooling-ci-workflows.md): dashboard-artifacts.yml runs this script in CI
- [Report a Bug links and the bug-issue API default point at uw-ssec/ca-biositing, not the origin repo](../bugs/dashboards-report-bug-github-repo-mismatch.md): drift page modal targets a different GitHub repo than Products 1-3
