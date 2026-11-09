---
name: resource-analysis-dashboards
description:
  Use when generating and refreshing the reproducible BioCIRV Resource Analysis,
  Statistical QC & Outlier Screening, and Multi-Resource Side-by-Side Comparison
  Explorer interactive HTML dashboards and AI insights sidecar from PostgreSQL
  or an offline database snapshot.
---

# Resource Analysis & Statistical QC Dashboards Skill (`resource-analysis-dashboards`)

Use this skill whenever the user asks to generate, refresh, customize, or share
any of the Aim 1 / Aim 2 biomass characterization, bioconversion, statistical
replicate precision ($\text{RSD}_{\text{within}}$ vs.
$\text{RSD}_{\text{between}}$), outlier screening (`Dixon's Q`, `RSD > 20%`,
`>3×SD_pooled`), or multi-resource comparison dashboards.

## 1. Architecture & Modular Dashboard Suite Overview

All dashboards in the suite are generated reproducibly by standalone Python CLI
scripts that query the PostgreSQL database (`ca_biositing.datamodels.database`)
or an offline snapshot (`--from-snapshot`), compute statistical & AI insights
into a versioned JSON sidecar (`data/insights/resource_ai_insights.json`), and
embed a compressed dictionary-encoded payload directly into self-contained
`.html` files that open in any browser (Safari, Chrome, Edge, Firefox) via
`file://` or HTTP without a backend server.

| Suite Page / Asset                                          | Generator Script                                   | Output HTML / File Path                                     | Purpose                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| :---------------------------------------------------------- | :------------------------------------------------- | :---------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **AI & Statistical Insights Sidecar**                       | `analysis/metadata/resource_insights_engine.py`    | `data/insights/resource_ai_insights.json`                   | Mines free-text bench notes (`observation.note`, `experiment.note`, `prepared_sample.note`, `field_sample.note`), computes within-group ($\text{RSD}_{\text{within}}$) vs. method-stratified between-group ($\text{RSD}_{\text{between}}$, $\text{SD}_{\text{between}}$) replicate precision, runs 3-test outlier screening (`Dixon's Q` guarded by $\text{RSD} \ge 10\%$, `RSD > 20%`, `>3×SD_pooled`), and computes proximate mass-balance closure (`95–105%`). |
| **Page 1: Resource Characterization & AI Brief**            | `analysis/metadata/resource_analysis_dashboard.py` | `exports/plots/metadata/resource_analysis_dashboard.html`   | Clean, focused single-resource characterization dashboard with sticky left filter sidebar, 10 individual analytical domain pills, KPI cards, proximate mass-balance closure parity with `mv_biomass_proximate_data.py`, and contextual `"👁 Show me"` flag mini-plots.                                                                                                                                                                                             |
| **Page 2: Statistical Snapshot (QC, Outliers & Lab Notes)** | `analysis/metadata/resource_analysis_dashboard.py` | `exports/plots/metadata/resource_qc_outlier_dashboard.html` | Dedicated statistical quality control & audit workspace featuring within-group vs. method-stratified between-group RSD/SD scatter/ratio charts, 10 individual domain filter pills, interactive outlier screening table (`Dixon's Q` guarded by $\text{RSD} \ge 10\%$, `RSD > 20%`, `>3×SD_pooled`), mined bench notes audit trail, and `"👁 Show me"` flag mini-plots.                                                                                             |
| **Page 3: Interactive Data Visualizer**                     | `analysis/metadata/resource_explorer_dashboard.py` | `exports/plots/metadata/resource_explorer_dashboard.html`   | High-DPI HTML5 `<canvas>` visualizer with 2D rectangular brush zoom (`#canvas-zoom-brush`), sticky left filter sidebar, 3-section statistical screening & lab notes drawer (`#explorer-lab-notes-panel`), canonical 6-part `replicate_group_key` point selection, `"📤 Export Slice (.HTML)"` collaborator export, and `"👁 Show me"` `?highlight_rk=` pulse-ring deep-linking.                                                                                    |
| **Product 4: Resource QC & Data Audit Workbench**           | `analysis/metadata/resource_audit_workbench.py`    | `exports/plots/metadata/resource_audit_workbench.html`      | Default dark-mode Stage 1 QC decision workbench (`in_review` default workflow state, auto-filled analyst assignee, multi-row bulk assignment up to 500 items, contextual `"👁 Show me"` mini-plots, and admin-only Stage 2 Google Sheets writeback).                                                                                                                                                                                                               |
| **Product 5: Multi-Environment DB Drift Assessment**        | `analysis/audit/db_environment_drift.py`           | `exports/plots/audit/db_environment_drift_dashboard.html`   | 4-layer PostgreSQL environment drift dashboard comparing `local`, `staging`, and `production` across schema/migrations, 21 core tables, 19 materialized views, lineage sets, and parameter distributions.                                                                                                                                                                                                                                                         |
| **Unified Suite Landing Gallery & Login Portal**            | `scripts/generate_dashboard_gallery.py`            | `exports/plots/index.html`, `exports/plots/login.html`      | Single entry-point landing page linking all 5 dashboard products (`resource_analysis_dashboard.html`, `resource_qc_outlier_dashboard.html`, `resource_explorer_dashboard.html`, `resource_audit_workbench.html`, and `db_environment_drift_dashboard.html`).                                                                                                                                                                                                      |

## 2. One-Command Workflow (Pixi Tasks)

To refresh the entire suite from the live local PostgreSQL database
(`localhost:5432`):

```bash
# Refresh AI insights sidecar + all modular HTML dashboards + gallery index
pixi run refresh-dashboards
```

Or run individual steps via Pixi tasks:

```bash
# Step 1: Recompute statistical outlier screening, RSD variance decomposition, and bench-note synthesis
pixi run refresh-resource-insights

# Step 2: Regenerate Page 1 (Characterization & AI Brief) + Page 2 (Statistical QC & Lab Notes Audit)
pixi run build-resource-analysis-dashboard

# Step 3: Regenerate Page 3 (Multi-Resource Side-by-Side Canvas Explorer)
pixi run build-resource-explorer-dashboard

# Step 4: Regenerate Unified Gallery
pixi run python scripts/generate_dashboard_gallery.py
```

## 3. Single-Pass Live Extraction & Snapshot Execution Mode (`--from-snapshot`)

### Single-Pass Live Database Extraction Pattern (CI `live_db` & Cloud SQL Tunnel Builds)

When refreshing against a live PostgreSQL instance or Cloud SQL Auth Proxy
tunnel (such as Staging `:5434` via `biocirv_readonly` during the nightly
`0 9 * * *` cron, post-ETL `workflow_run`, or
`gh workflow run dashboard-artifacts.yml -f data_source=live_db`), extract the
database payload **once** via `resource_explorer_dashboard.py` and feed that
snapshot into the remaining generators and insights sidecar:

```bash
# 1. Single-pass live SQL extraction + Page 3 HTML build (writes exports/plots/metadata/dashboard_data_snapshot.json)
pixi run python analysis/metadata/resource_explorer_dashboard.py \
  --output-dir exports/plots/metadata
cp exports/plots/metadata/dashboard_data_snapshot.json \
  audit/output/env_fingerprints/baseline_records_snapshot.json

# 2. Recompute deterministic insights sidecar & build Pages 1 & 2 from the extracted snapshot
pixi run python analysis/metadata/resource_insights_engine.py \
  --from-snapshot audit/output/env_fingerprints/baseline_records_snapshot.json \
  --output data/insights/resource_ai_insights.json

pixi run python analysis/metadata/resource_analysis_dashboard.py \
  --from-snapshot audit/output/env_fingerprints/baseline_records_snapshot.json \
  --sidecar data/insights/resource_ai_insights.json \
  --write-sidecar \
  --output-dir exports/plots/metadata

# 3. Build Product 4 (Resource QC & Data Audit Workbench) from the same snapshot
pixi run python analysis/metadata/resource_audit_workbench.py \
  --from-snapshot audit/output/env_fingerprints/baseline_records_snapshot.json \
  --output exports/plots/metadata/resource_audit_workbench.html

# 4. Write the verified snapshot and freshly computed sidecar back to GCS (CI live_db mode)
gcloud storage cp audit/output/env_fingerprints/baseline_records_snapshot.json \
  gs://biocirv-staging-dashboards/snapshots/staging/latest/baseline_records_snapshot.json
gcloud storage cp data/insights/resource_ai_insights.json \
  gs://biocirv-staging-dashboards/snapshots/staging/latest/resource_ai_insights.json
```

### Offline / Snapshot-Only Execution Mode (`--from-snapshot`)

When running inside a sandboxed environment, on `push` to `main` /
`pull_request` CI (`mode=snapshot`), or when PostgreSQL is offline, all
generator scripts support `--from-snapshot <path_to_db_snapshot.json>`:

```bash
# 1. Recompute data/insights/resource_ai_insights.json from snapshot
python3 analysis/metadata/resource_insights_engine.py \
  --from-snapshot scratch/db_snapshot.json \
  --output data/insights/resource_ai_insights.json

# 2. Build Page 1 (resource_analysis_dashboard.html) & Page 2 (resource_qc_outlier_dashboard.html)
python3 analysis/metadata/resource_analysis_dashboard.py \
  --from-snapshot scratch/db_snapshot.json \
  --sidecar data/insights/resource_ai_insights.json \
  --write-sidecar \
  --output-dir exports/plots/metadata

# 3. Build Page 3 (resource_explorer_dashboard.html)
python3 analysis/metadata/resource_explorer_dashboard.py \
  --from-snapshot scratch/db_snapshot.json \
  --output-dir exports/plots/metadata
```

## 4. Multi-Resource Collaborator Slice `.html` & `.csv` Exporter

You can export a physically isolated, standalone single- or multi-resource
`.html` dashboard and accompanying `.csv` data slice for external collaborators
(containing zero rows, zero dictionary entries, and zero AI insights from
unselected resources in `window.__BIOCIRV_DATA__`, while preserving anonymous
provider codenames and masking analyst emails by default):

### CLI Export

```bash
# Export a leak-free single-resource slice HTML (defaults to qc_pass = pass)
pixi run python analysis/metadata/resource_analysis_dashboard.py \
  --from-snapshot scratch/db_snapshot.json \
  --slice-resource "almond hulls" \
  --slice-qc-status pass \
  --slice-output exports/slices/almond_hulls_slice.html

# Include both pass and fail records in the exported collaborator slice
pixi run python analysis/metadata/resource_analysis_dashboard.py \
  --from-snapshot scratch/db_snapshot.json \
  --slice-resource "almond hulls" \
  --slice-qc-status pass,fail \
  --slice-output exports/slices/almond_hulls_pass_and_fail_slice.html
```

### In-App Modal Export

- Click **"📤 Export Slice (.html)"** in the header of Page 1, Page 2, or Page
  3, select one or more target resources, choose which dashboard pages
  (`Page 1`, `Page 2`, `Page 3`) and active parameter/sample/method/date filters
  to include, and download the self-contained `.html` slice and `.csv` bundle
  directly in the browser.

## 5. Interactive QC Filtering, Live QC Overlay, Audit Escalation & Issue Reporting

- **Default `qc_pass = pass`**: All analytical dashboards (Page 1, Page 2, and
  Page 3) default their initial load and reset state to `qc_pass = pass`, while
  Product 4 (**QC Audit Workbench**) defaults to dark mode (`theme = "dark"`)
  and `decision_status = "in_review"`.
- **Canonical 6-Part Replicate Group Key & Cohort Selection**:
  - Every replicate cohort across Python generators, FastAPI `/v1/qc/*` routes,
    and browser overlays uses the canonical 6-part key
    `{resource}::{sample}::{domain_slug}::{param}::{context_label}::{experiment}`
    (`build_canonical_replicate_key` / `window.normalizeReplicateGroupKey`).
  - Clicking an outlier candidate or point in Page 2
    (`resource_qc_outlier_dashboard.html`) or Page 3
    (`resource_explorer_dashboard.html`) defaults the selection scope to
    **`Entire Replicate Group`** (`scope = "group"`), with a 1-click toggle to
    **`Single Point Only`** (`scope = "single"`).
- **Direct Audit Workbench Escalation (`⚖️ Export to Audit Workbench`) & Header
  Slice Export (`📤 Export Slice (.HTML)`)**:
  - The legacy floating CSV selection tray (`#selection-export-tray`) has been
    retired. Collaborator slices are exported via the header
    **`📤 Export Slice (.HTML)`** modal, and flagged cohorts/points escalate
    directly via **`⚖️ Export to Audit Workbench`**
    (`POST /v1/qc/tray-to-workbench` with `localStorage` fallback), auto-filling
    the signed-in analyst's email and defaulting
    `decision_status = "in_review"`.
  - In Product 4 (`resource_audit_workbench.html`), analysts can select multiple
    queue items via row checkboxes and bulk-assign them in a single transaction
    (`POST /v1/qc/decisions/assign-batch`, capped at 500 items).
- **Contextual `"👁 Show me"` Flag Mini-Plot Popover
  (`#audit-flag-show-me-popover`)**:
  - Every QC flag row and badge across Pages 1, 2, 3, and Product 4 includes a
    **`"👁 Show me"`** trigger (`window.openAuditFlagShowMePopover`) that renders
    an interactive mini-plot inside `#audit-flag-show-me-popover`:
    - **1D Strip + Box/Whisker + Mean ± SD Overlay** for `dixon_q`, `high_rsd`,
      `exceeds_3sd_pooled`, `physically_impossible`, `icp_above_cap`, and
      `analyst_flagged` / `manual_override` flags.
    - **100% Mass-Balance Stacked Horizontal Bar** (`95–105%` target band) for
      `proximate_sum` / `sum_exceeds_100` flags, computed with exact portal
      parity (averaging replicates per component within
      `(resource_name, experiment, prep_method)` before summing).
  - Clicking **`↗ Open in Data Visualizer`** deep-links to
    `resource_explorer_dashboard.html?highlight_rk=<6-part-key>`, auto-scrolling
    to the target cohort and rendering an animated gold highlight pulse ring.
- **Live QC State Overlay (`GET /v1/qc/decisions`) & Cross-Tab
  `BroadcastChannel` (`FINAL_DECISION.md` §2.2)**:
  - On page load and whenever the user clicks **`↻ Refresh QC State`**
    (`#btn-refresh-qc-state`), Pages 1, 2, and 3 fetch `GET /v1/qc/decisions`
    (with `localStorage` fallback), patch `row.qc_status` / `row.qc_pass` in
    memory (`window.__BIOCIRV_DATA__.rows`, `ALL_RECORDS`, and `ALL_ROWS`), and
    re-render all charts, KPIs, and tables without regenerating static `.html`
    files.
  - **Same-Browser vs. Cross-Analyst Synchronization Caveat**:
    `BroadcastChannel("biocirv_qc_decisions")` synchronizes open tabs in the
    **same browser** immediately when a Stage 1 QC decision or tray export is
    saved in Product 4 or Pages 2/3. **Cross-analyst updates** (decisions made
    by another user on a different machine or browser) are fetched on initial
    page load or on-demand via the explicit **`↻ Refresh QC State`** header
    button, with zero background `setInterval` polling.
- **Submit Issue (`🐛 Submit Issue`) & PostgreSQL Bug Persistence**:
  - Every dashboard header includes a unified **"🐛 Submit Issue"** modal that
    captures active page/resource/filter context and persists the report in
    PostgreSQL via `POST /v1/qc/github-issue`
    (`record_table="portal_bug_report"`, `flag_type="bug_report"`, queryable at
    `GET /v1/qc/bug-issues`), while optionally forwarding to GitHub Issues when
    `GITHUB_ISSUES_TOKEN` is set.

## 6. Key Domain Rules & Guardrails

1. **All 10 Aim 1 & Aim 2 Analytical Record Tables Included**:
   - Always include `compositional_record`, `proximate_record`,
     `ultimate_record`, `xrf_record`, `icp_record`, `calorimetry_record`,
     `xrd_record`, `pretreatment_record`, `fermentation_record`, and
     `gasification_record`.
2. **Standard Chemical Element Symbol Capitalization (`ICP` & `XRF`)**:
   - Raw database parameter strings store element symbols in lowercase (`ca`,
     `fe`, `mg`, `si`, `na`, `k`, `zn`, `cu`, `mn`, `al`, `p`, `s`, `cl`, `ti`,
     `sr`, `ba`, `cr`, `ni`, `pb`, `cd`, `as`, `co`, `mo`, `se`, `v`, `zr`,
     `rb`, `br`). Always format them via `CHEMICAL_SYMBOLS` (`Ca`, `Fe`, `Mg`,
     `Si`, etc.) in charts, tables, and filter checklists.
3. **Statistical Outlier Screening & Low-Abundance Trace Cutoffs**:
   - **Within-Group vs. Between-Group RSD**:
     - $\text{RSD}_{\text{within}}$ measures analytical repeatability across
       technical replicates of the same
       `(resource, analysis_type, parameter, prepared_sample, method_or_strain)`.
     - $\text{RSD}_{\text{between}}$ measures sample-to-sample heterogeneity
       across distinct prepared samples/methods of the same
       `(resource, analysis_type, parameter)`.
   - **Trace-Level Minimum Cutoffs**:
     - For `icp analysis`: groups with $|\bar{x}| < 100\text{ ppm}$ (`mg/kg`)
       are marked `below_cutoff = True` so near-detection-limit noise does not
       trigger false-positive high-RSD or Dixon's Q flags.
     - For `xrf analysis`: groups with $|\bar{x}| < 0.5\%$ are marked
       `below_cutoff = True`.
4. **Analyst Privacy in Exports**:
   - Never expose `analyst_id` or personal analyst identifiers in exported CSV,
     TSV, collaborator `.html` slices (by default), or `.xlsx` files. Provider
     codenames are already anonymous and are preserved as-is.
5. **No Implicit Sidecar Writes During HTML Build**:
   - `resource_analysis_dashboard.py` does not write to
     `data/insights/resource_ai_insights.json` unless `--write-sidecar` is
     explicitly passed, and both `resource_analysis_dashboard.py` and
     `resource_explorer_dashboard.py` accept `--output <file.html>` for clean
     single-file/temporary generation.
6. **JavaScript Validation**:
   - Whenever modifying inline `<script>` templates in the Python generators,
     always extract the generated `<script>` block and run `node --check` to
     verify zero syntax errors.
7. **Zero Synthetic or Fallback Data Rendered to Users**:
   - Never hardcode demo resources (e.g., `"almond hulls"`), synthetic record
     IDs, or fallback proximate percentages in any dashboard renderer, popover,
     or mini-plot. If a requested `replicate_group_key`, `decision_id`, or
     filter slice has no matching records in the loaded database snapshot,
     render a clear empty-state message and zero counts (synthetic data in test
     suites is fine, but never in user-facing UI).
