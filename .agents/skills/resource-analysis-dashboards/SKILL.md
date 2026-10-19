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

| Suite Page / Asset                                              | Generator Script                                   | Output HTML / File Path                                     | Purpose                                                                                                                                                                                                                                                                                                                                                                                       |
| :-------------------------------------------------------------- | :------------------------------------------------- | :---------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **AI & Statistical Insights Sidecar**                           | `analysis/metadata/resource_insights_engine.py`    | `data/insights/resource_ai_insights.json`                   | Mines free-text bench notes (`observation.note`, `experiment.note`, `prepared_sample.note`, `field_sample.note`), computes within-group ($\text{RSD}_{\text{within}}$) vs. between-group ($\text{RSD}_{\text{between}}$) replicate precision, runs 3-test outlier screening with trace-element cutoffs (`<100 ppm` ICP / `<0.5%` XRF), and generates per-resource executive synthesis briefs. |
| **Page 1: Resource Characterization & AI Brief**                | `analysis/metadata/resource_analysis_dashboard.py` | `exports/plots/metadata/resource_analysis_dashboard.html`   | Clean, focused single-resource characterization dashboard with compact 2-card Executive AI Brief, 4 KPI cards, and 5 domain visualization tabs (`Proximate & Mass Balance`, `Compositional & Ultimate`, `Calorimetry & XRD`, `Elemental (ICP & XRF)`, `Conversion: Pretreatment, Ferm & Gasification`).                                                                                       |
| **Page 2: Statistical QC, Outlier Screening & Lab Notes Audit** | `analysis/metadata/resource_analysis_dashboard.py` | `exports/plots/metadata/resource_qc_outlier_dashboard.html` | Dedicated statistical quality control & audit workspace featuring within-group vs. between-group RSD scatter/ratio charts, interactive outlier screening table (`Dixon's Q`, `RSD > 20%`, `>3×SD_pooled` with trace-level suppression toggle), mined bench notes audit trail, and full anonymized CSV export.                                                                                 |
| **Page 3: Multi-Resource Side-by-Side Comparison Explorer**     | `analysis/metadata/resource_explorer_dashboard.py` | `exports/plots/metadata/resource_explorer_dashboard.html`   | High-DPI HTML5 `<canvas>` explorer with searchable **Multi-Select Checklist Popovers** (`Resources`, `Prepared Samples`, `Parameters`, `Methods / Preps / Strains`) and a `Compare By:` grouping selector (`Resource`, `Prepared Sample`, `Field Sample`, `Experiment`, `Method / Prep`) for side-by-side visual and numeric comparison.                                                      |
| **Unified Suite Landing Gallery**                               | `scripts/generate_dashboard_gallery.py`            | `exports/plots/index.html`                                  | Single entry-point landing page linking the 4 core products (`resource_analysis_dashboard.html`, `resource_qc_outlier_dashboard.html`, `resource_explorer_dashboard.html`, and `db_environment_drift_dashboard.html`).                                                                                                                                                                        |

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

## 3. Offline / Snapshot Execution Mode (`--from-snapshot`)

When running inside a sandboxed environment or when PostgreSQL is offline, all
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
  --output-dir exports/plots/metadata \
  --artifact-dir exports

# 3. Build Page 3 (resource_explorer_dashboard.html)
python3 analysis/metadata/resource_explorer_dashboard.py \
  --from-snapshot scratch/db_snapshot.json \
  --output-dir exports/plots/metadata \
  --artifact-dir exports
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

## 5. Interactive QC Filtering, Live QC Overlay, Tray-to-Workbench & Issue Reporting

- **Default `qc_pass = pass`**: All dashboards (Page 1, Page 2, and Page 3)
  default their initial load and reset state to `qc_pass = pass`.
- **Replicate-Group-Default Selection**:
  - Clicking an outlier candidate or point in Page 2
    (`resource_qc_outlier_dashboard.html`) or Page 3
    (`resource_explorer_dashboard.html`) defaults the selection scope to
    **`Entire Replicate Group`** (`scope = "group"`, highlighting all sibling
    replicates sharing
    `(resource, analysis_type, parameter, prepared_sample, method_or_strain)`),
    with a 1-click toggle to **`Single Point Only`** (`scope = "single"`).
- **Unified Export Tray & Audit Workbench Handoff
  (`⚖️ Export to Audit Workbench`)**:
  - Both Page 2 and Page 3 provide a unified selection tray with three actions:
    1. `⬇ Export Tray (.CSV)` — downloads the selected records/groups as CSV.
    2. `📤 Export Slice (.HTML)` — opens the leak-free collaborator slice modal
       pre-populated with the selected resources.
    3. `⚖️ Export to Audit Workbench` — dispatches
       `POST /v1/qc/tray-to-workbench` (and mirrors to
       `localStorage["biocirv_qc_audit_tray_v1"]` for offline `file://` mode) so
       selected replicate groups or individual records appear immediately in the
       Product 4 **QC Audit Workbench** (`resource_audit_workbench.html`).
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
- **Replicate Mean ± SD & Field Sample / Experiment Grouping**:
  - Toggle between `Individual Points` and `Replicate Mean ± SD` error bars, and
    group by `Field Sample` or `Experiment / Run` to compare replicate cohorts.
- **Report a Bug (`🐛 Report a Bug`)**:
  - Every dashboard header includes a **"🐛 Report a Bug"** modal that captures
    active page/resource/filter context and opens a pre-populated GitHub Issue
    URL.

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
