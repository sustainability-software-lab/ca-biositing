---
name: db-drift-assessment
description:
  Use when extracting 4-layer PostgreSQL environment fingerprints across local
  (:5432), staging (:5434 Cloud SQL Auth Proxy), and production (:5435 Cloud SQL
  Auth Proxy), auditing schema/row-count/lineage/parameter parity, or generating
  the interactive Multi-Environment Database Drift Assessment Dashboard
  (`exports/plots/audit/db_environment_drift_dashboard.html`) and Markdown
  report (`audit/output/drift_report.md`).
---

# Multi-Environment Database Drift Assessment (`db-drift-assessment`)

Use this skill whenever the user asks to:

- Compare `local`, `staging`, and `production` PostgreSQL databases for schema,
  row-count, sample lineage, or materialized view drift.
- Diagnose why data portal materialized views (`data_portal.mv_*` or
  `ca_biositing.analysis_data_view`) return different counts across
  environments.
- Audit unpromoted Aim 1 / Aim 2 analytical batches, missing `field_sample` /
  `prepared_sample` lineage, or `qc_pass` ruling discrepancies prior to a
  production release.
- Generate or refresh `exports/plots/audit/db_environment_drift_dashboard.html`
  and `audit/output/drift_report.md`.

---

## 1. Architecture & 4-Layer Fingerprint Model

The CLI script
[`analysis/audit/db_environment_drift.py`](../../../analysis/audit/db_environment_drift.py)
reads connection defaults from
[`resources/config/db_reset.yaml`](../../../resources/config/db_reset.yaml) and
produces a self-contained JSON fingerprint for each environment
(`audit/output/env_fingerprints/<env>_fingerprint.json`) covering four layers:

1. **Layer 1 — Schema, Alembic & Materialized View Freshness**:
   - Queries `public.alembic_version` (`version_num`) and maps to the repository
     migration chain (`0001` &rarr; `0024`).
   - Computes column-signature hashes across `information_schema.columns` for
     all 21 core `public` tables (`91` total base tables).
   - Queries `pg_matviews` across `ca_biositing` (8 views) and `data_portal` (11
     views) to verify `ispopulated`, definition hash parity, and **MV Stale
     Alert** status (when base tables are updated by ETL flows without running
     `pixi run refresh-views`).
2. **Layer 2 — Core Table & Materialized View Row Counts**:
   - Captures exact row counts across all **21 core `public` tables**
     (`resource`, `primary_ag_product`, `provider`, `field_sample`,
     `prepared_sample`, `experiment`, `observation`, 8 Aim 1 analytical tables,
     3 Aim 2 conversion tables, and 3 USDA market/census tables) and all **19
     analytical/portal views**.
3. **Layer 3 — Resource &times; Analysis-Type Coverage, Lineage Sets & QC
   Pass/Fail Split**:
   - Builds the **45 active resources &times; 10 analysis types** coverage
     matrix with per-cell record counts, `qc_pass` (`pass` / `fail` / `other`)
     breakdown, sample record IDs, and deterministic cell content hashes.
   - Extracts full entity lineage sets (`resource.name`, `field_sample.name`,
     `prepared_sample.name`, `experiment.name`) for set-difference auditing
     (`Local Only`, `In Local & Staging (Unpromoted to Prod)`,
     `Prod Only (Legacy)`, `Synced Across All 3`).
4. **Layer 4 — Parameter Value Distributions & Portal Filter Funnel Attrition**:
   - Computes `n`, `mean`, `SD`, `median`, `min`, and `max` per
     `(analysis_type, parameter_name, unit)` and flags any parameter whose mean
     shifts by **`>5%`** between environments.
   - Tracks step-by-step row attrition through the
     `ca_biositing.analysis_data_view` filter funnel (`Raw Candidate Pool`
     &rarr; `qc_pass != 'fail'` &rarr; `EXCLUDED_RESOURCES` &rarr;
     `EXCLUDED_PROVIDERS` &rarr; `ULTIMATE_PARAMETERS` &rarr; `Final View Rows`
     & `Retention Ratio`).

---

## 2. Step-by-Step Workflow

### Step 1: Start Local DB or Cloud SQL Auth Proxy Tunnels

Connection defaults are defined in `resources/config/db_reset.yaml` and can be
overridden per environment via environment variables (`load_db_reset_config()`
re-applies environment overrides after parsing `db_reset.yaml` so read-only CI
users like `biocirv_readonly` are preserved):

| Environment      | Default Host | Default Port | Database Name        | Default User   | Environment Variable Overrides                                                                                                                                                                              |
| :--------------- | :----------- | :----------- | :------------------- | :------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`local`**      | `127.0.0.1`  | `5432`       | `biocirv_db`         | `biocirv_user` | `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`                                                                                                                                        |
| **`staging`**    | `127.0.0.1`  | `5434`       | `biocirv-staging`    | `biocirv_user` | `AUDITOR_STAGING_DATABASE_URL` / `STAGING_DATABASE_URL`, `DB_HOST_STAGING`, `DB_PORT_STAGING`, `DB_NAME_STAGING`, `DB_USER_STAGING`, `DB_PASSWORD_STAGING` (`BIOCIRV_STAGING_USER_PW`)                      |
| **`production`** | `127.0.0.1`  | `5435`       | `biocirv-production` | `biocirv_user` | `AUDITOR_PRODUCTION_DATABASE_URL` / `AUDITOR_PROD_DATABASE_URL`, `DB_HOST_PROD`, `DB_PORT_PROD`, `DB_NAME_PROD`, `DB_USER_PROD`, `DB_PASSWORD_PROD` (`BIOCIRV_PROD_USER_PW` / `BIOCIRV_PRODUCTION_USER_PW`) |

To open Cloud SQL Auth Proxy tunnels for `staging` (`:5434`) and `production`
(`:5435`):

```bash
# Start local Docker PostgreSQL (:5432)
pixi run start-services

# In separate terminals (or backgrounded), start Cloud SQL Auth Proxy for Staging & Production:
cloud-sql-proxy <PROJECT_ID>:<REGION>:biocirv-staging --port 5434
cloud-sql-proxy <PROJECT_ID>:<REGION>:biocirv-production --port 5435
```

### Step 2: Extract Live Fingerprints & Enforce Read-Only / Query-Error Guards

Extract live 4-layer fingerprints directly from the running PostgreSQL
databases:

```bash
# Extract all 3 environments (Local :5432, Staging :5434, Production :5435)
pixi run python analysis/audit/db_environment_drift.py --extract-all

# Extract multiple target environments with read-only privilege verification and strict failure guards (CI pattern):
DB_HOST_STAGING=127.0.0.1 DB_PORT_STAGING=5434 DB_USER_STAGING=biocirv_readonly DB_PASSWORD_STAGING="<staging_ro_pw>" \
DB_HOST_PROD=127.0.0.1 DB_PORT_PROD=5435 DB_USER_PROD=biocirv_readonly DB_PASSWORD_PROD="<prod_ro_pw>" \
  pixi run python analysis/audit/db_environment_drift.py \
    --extract-envs staging,production \
    --verify-readonly-grants \
    --fail-on-unmeasured

# Or extract specific environments individually:
pixi run python analysis/audit/db_environment_drift.py --extract-env local --fail-on-unmeasured
pixi run python analysis/audit/db_environment_drift.py --extract-env staging --port 5434 --verify-readonly-grants --fail-on-unmeasured
pixi run python analysis/audit/db_environment_drift.py --extract-env production --port 5435 --verify-readonly-grants --fail-on-unmeasured
```

- **Graceful Offline Default vs. Strict CI Mode (`--fail-on-unmeasured`):** If
  an environment's Cloud SQL Auth Proxy tunnel is offline during local runs
  without `--fail-on-unmeasured`, `--extract-all` / `--extract-env` /
  `--extract-envs` records an explicit `unmeasured_offline`
  (`is_measured: false`) state rather than fabricating data. When
  `--fail-on-unmeasured` is passed, the command exits non-zero (`SystemExit(2)`)
  whenever `not fp.get("is_measured")` **or**
  `len(fp.get("query_errors", [])) > 0`.
- **Query Error Recording (`query_errors` & `cnt = -1`):** If `SELECT COUNT(*)`
  on any of the 21 core `public` tables (`CORE_TABLE_METADATA`) or 19
  analytical/portal materialized views (`ALL_19_VIEWS`), or any Layer 3 / Layer
  4 query, raises a SQL exception (such as `InsufficientPrivilege` or a broken
  view definition), `extract_live_fingerprint()` rolls back the transaction,
  sets that table or view's row count to `cnt = -1` (never silently `0`), and
  appends a descriptive string entry (e.g., `"table:<t_name>: <exc>"`,
  `"view:<v_name>: <exc>"`, `"lineage_coverage: <exc>"`,
  `"parameter_distributions: <exc>"`) to top-level `fp["query_errors"]`. In
  addition, `compute_pair_comparison()` marks any table or view with `cnt < 0`
  as `"QUERY ERROR"` (rather than `"SYNCED"` or bogus percentage drift). Both
  `--fail-on-unmeasured` and `--verify-readonly-grants` catch these failures so
  broken or permission-denied queries never overwrite valid fingerprints in GCS.
- **Read-Only Grant Verification (`--verify-readonly-grants`):** Verifies that
  every evaluated environment was measured (`is_measured: true`), recorded zero
  `query_errors`, and returned non-negative row counts (`cnt >= 0`) across all
  21 core `public` tables and 19 analytical/portal materialized views, exiting
  non-zero (`SystemExit(2)`) if any table or view is missing `SELECT` privilege
  or produced a query error.
- **Updating the Cached Local Baseline in GCS & Triggering Live CI Refresh:**

  ```bash
  # Extract verified local fingerprint and upload to gs://biocirv-staging-dashboards/snapshots/staging/latest/env_fingerprints/local_fingerprint.json
  pixi run python analysis/audit/db_environment_drift.py --extract-env local --fail-on-unmeasured
  gcloud storage cp audit/output/env_fingerprints/local_fingerprint.json \
    gs://biocirv-staging-dashboards/snapshots/staging/latest/env_fingerprints/local_fingerprint.json

  # Trigger an on-demand cloud-autonomous live refresh in GitHub Actions
  gh workflow run dashboard-artifacts.yml -f data_source=live_db
  ```

### Step 3: Run Multi-Environment Drift Comparison & Build Artifacts

```bash
pixi run python analysis/audit/db_environment_drift.py --compare
```

You can also combine live extraction and comparison in a single command:

```bash
pixi run python analysis/audit/db_environment_drift.py --extract-all --compare
```

This generates:

1. `audit/output/env_fingerprints/local_fingerprint.json`
2. `audit/output/env_fingerprints/staging_fingerprint.json`
3. `audit/output/env_fingerprints/production_fingerprint.json`
4. `audit/output/drift_report.md` — Executive Markdown scorecard, 21-table &
   19-view waterfall tables, lineage set-diffs, filter funnel comparison, and
   remediation checklist.
5. `exports/plots/audit/db_environment_drift_dashboard.html` — Standalone
   interactive HTML5 dashboard (Tailwind CSS + Plotly) featuring:
   - **Environment Pair Selector** (`Local vs. Staging`,
     `Staging vs. Production`, `Local vs. Production`, and `3-Way Matrix`)
   - **Custom Fingerprint JSON Upload** (`📂 Upload Custom Fingerprint JSON`)
     for instant in-browser recomputation
   - **Tab 1**: Table & Materialized View Parity Waterfall + Searchable
     40-Object Diff Table
   - **Tab 2**: 45 Resources &times; 10 Analysis Types Drift Heatmap with
     Click-to-Inspect Cell Drilldown
   - **Tab 3**: Sample & Entity Lineage Set-Difference Explorer
     (`prepared_samples`, `field_samples`, `resources`, `experiments`)
   - **Tab 4**: Parameter Value Shift (`>5%` flagged) & `analysis_data_view`
     Filter Funnel Audit

---

## 3. Standard Drift Remediation Playbook

| Drift Symptom                                                | Root Cause                                                                                                                                         | Remediation Command                                                                   |
| :----------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------ |
| **`MV STALE` badge on Staging/Prod views**                   | ETL flows updated base analytical tables (`compositional_record`, `xrf_record`, `gasification_record`), but materialized views were not refreshed. | `POSTGRES_PORT=5434 POSTGRES_DB=biocirv-staging pixi run refresh-views`               |
| **Alembic head mismatch (`0021` or `0023` vs `0024`)**       | Target environment is behind on Alembic migrations (e.g., missing `0022_exclude_jaguar_provider` or `0024_centralize_qc_constants`).               | `POSTGRES_PORT=5435 POSTGRES_DB=biocirv-production pixi run migrate`                  |
| **Missing analytical batches (`Calorimetry`, `XRD`, `XRF`)** | Latest Google Sheets ETL pipeline runs have not been executed against Staging/Production.                                                          | `pixi run run-single-flow aim1_etl` and `pixi run run-single-flow aim2_etl`           |
| **View SQLAlchemy definition drift (`DEF DRIFT`)**           | Local `data_portal_views/` SQL expressions were updated without compiling or applying the view migration.                                          | `pixi run compile-mv-fixes -m "Sync view definitions"` followed by `pixi run migrate` |

---

## 4. Verification & Eval Contract

After generating or updating the drift assessment artifacts, always verify:

1. **Zero JavaScript Syntax Errors**: Extract the `<script>` block from
   `exports/plots/audit/db_environment_drift_dashboard.html` and run
   `node --check`.
2. **All 4 Layers Populated**: Confirm `local_fingerprint.json`,
   `staging_fingerprint.json`, and `production_fingerprint.json` each contain
   `layer1_schema`, `layer2_row_counts`, `layer3_coverage_and_lineage`, and
   `layer4_parameters_and_funnels`.
3. **Strict Theme & Contrast Compliance**: Verify that
   `exports/plots/audit/db_environment_drift_dashboard.html` defines semantic
   CSS variables for both `[data-theme="light"]` and `[data-theme="dark"]` and
   includes the top `BioCirV Suite` navigation bar linking all 5 dashboard
   products and `../index.html`.
