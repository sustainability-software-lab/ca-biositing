---
name: resource-analysis-dashboards
description:
  Generate and refresh the reproducible BioCIRV Resource Analysis, Statistical
  QC & Outlier Screening, Multi-Resource Side-by-Side Comparison Explorer, and
  Pretreatment Variance interactive HTML dashboards and AI insights sidecar from
  PostgreSQL or an offline database snapshot.
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
embed a compressed dictionary-encoded payload directly into self-contained `.html`
files that open in any browser (Safari, Chrome, Edge, Firefox) via `file://` or
HTTP without a backend server.

| Suite Page / Asset | Generator Script | Output HTML / File Path | Purpose |
| :--- | :--- | :--- | :--- |
| **AI & Statistical Insights Sidecar** | `analysis/metadata/resource_insights_engine.py` | `data/insights/resource_ai_insights.json` | Mines free-text bench notes (`observation.note`, `experiment.note`, `prepared_sample.note`, `field_sample.note`), computes within-group ($\text{RSD}_{\text{within}}$) vs. between-group ($\text{RSD}_{\text{between}}$) replicate precision, runs 3-test outlier screening with trace-element cutoffs (`<100 ppm` ICP / `<0.5%` XRF), and generates per-resource executive synthesis briefs. |
| **Page 1: Resource Characterization & AI Brief** | `analysis/metadata/resource_analysis_dashboard.py` | `exports/plots/metadata/resource_analysis_dashboard.html` | Clean, focused single-resource characterization dashboard with compact 2-card Executive AI Brief, 4 KPI cards, and 5 domain visualization tabs (`Proximate & Mass Balance`, `Compositional & Ultimate`, `Calorimetry & XRD`, `Elemental (ICP & XRF)`, `Conversion: Pretreatment, Ferm & Gasification`). |
| **Page 2: Statistical QC, Outlier Screening & Lab Notes Audit** | `analysis/metadata/resource_analysis_dashboard.py` | `exports/plots/metadata/resource_qc_outlier_dashboard.html` | Dedicated statistical quality control & audit workspace featuring within-group vs. between-group RSD scatter/ratio charts, interactive outlier screening table (`Dixon's Q`, `RSD > 20%`, `>3×SD_pooled` with trace-level suppression toggle), mined bench notes audit trail, and full anonymized CSV export. |
| **Page 3: Multi-Resource Side-by-Side Comparison Explorer** | `analysis/metadata/resource_explorer_dashboard.py` | `exports/plots/metadata/resource_explorer_dashboard.html` | High-DPI HTML5 `<canvas>` explorer with searchable **Multi-Select Checklist Popovers** (`Resources`, `Prepared Samples`, `Parameters`, `Methods / Preps / Strains`) and a `Compare By:` grouping selector (`Resource`, `Prepared Sample`, `Method / Prep`) for side-by-side visual and numeric comparison. |
| **Legacy v1 Monolith (Preserved Reference)** | Preserved artifact | `exports/plots/metadata/resource_analysis_dashboard_v1_monolith.html` | Original 7-tab all-in-one single-page dashboard preserved for backward compatibility. |
| **Standalone Pretreatment Variance Explorer** | `analysis/conversion/pretreatment_variance_dashboard.py` | `exports/plots/conversion/pretreatment_variance_dashboard.html` | Dedicated HTML5 `<canvas>` scatter and replicate strip plot for `glucose_yld` and `xylose_yld` across pretreatment methods with Pinned Point Inspector and Export Tray. |
| **Sargassum Deep-Dive Dashboards & Anonymized Excel** | `analysis/sargassum/generate_sargassum_report.py` | `exports/plots/sargassum/sargassum_analysis_dashboards.html`, `exports/sargassum_analytical_report.xlsx` | Resource-specific deep-dive report and multi-sheet Excel workbook (with `analyst_id` excluded for external sharing). |
| **Unified Suite Landing Gallery** | `scripts/generate_dashboard_gallery.py` | `exports/plots/index.html` | Single entry-point landing page linking all modular dashboards, quick widgets, and the DB Environment Drift Audit dashboard. |

## 2. One-Command Workflow (Pixi Tasks)

To refresh the entire suite from the live local PostgreSQL database (`localhost:5432`):

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

# Step 3: Regenerate Page 3 (Multi-Resource Side-by-Side Canvas Explorer & Quick Widget)
pixi run build-resource-explorer-dashboard

# Step 4: Regenerate Standalone Pretreatment Variance Dashboard + Unified Gallery
pixi run python analysis/conversion/pretreatment_variance_dashboard.py
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

# 3. Build Page 3 (resource_explorer_dashboard.html & resource_quick_widget.html)
python3 analysis/metadata/resource_explorer_dashboard.py \
  --from-snapshot scratch/db_snapshot.json \
  --output-dir exports/plots/metadata \
  --artifact-dir exports
```

## 4. Key Domain Rules & Guardrails

1. **All 10 Aim 1 & Aim 2 Analytical Record Tables Included**:
   - Always include `compositional_record`, `proximate_record`, `ultimate_record`,
     `xrf_record`, `icp_record`, `calorimetry_record`, `xrd_record`,
     `pretreatment_record`, `fermentation_record`, and `gasification_record`.
2. **Standard Chemical Element Symbol Capitalization (`ICP` & `XRF`)**:
   - Raw database parameter strings store element symbols in lowercase (`ca`,
     `fe`, `mg`, `si`, `na`, `k`, `zn`, `cu`, `mn`, `al`, `p`, `s`, `cl`, `ti`,
     `sr`, `ba`, `cr`, `ni`, `pb`, `cd`, `as`, `co`, `mo`, `se`, `v`, `zr`,
     `rb`, `br`). Always format them via `CHEMICAL_SYMBOLS` (`Ca`, `Fe`, `Mg`,
     `Si`, etc.) in charts, tables, and filter checklists.
3. **Statistical Outlier Screening & Low-Abundance Trace Cutoffs**:
   - **Within-Group vs. Between-Group RSD**:
     - $\text{RSD}_{\text{within}}$ measures analytical repeatability across
       technical replicates of the same `(resource, analysis_type, parameter,
       prepared_sample, method_or_strain)`.
     - $\text{RSD}_{\text{between}}$ measures sample-to-sample heterogeneity
       across distinct prepared samples/methods of the same `(resource,
       analysis_type, parameter)`.
   - **Trace-Level Minimum Cutoffs**:
     - For `icp analysis`: groups with $|\bar{x}| < 100\text{ ppm}$ (`mg/kg`) are
       marked `below_cutoff = True` so near-detection-limit noise does not
       trigger false-positive high-RSD or Dixon's Q flags.
     - For `xrf analysis`: groups with $|\bar{x}| < 0.5\%$ are marked
       `below_cutoff = True`.
4. **Analyst Privacy in Exports**:
   - Never expose `analyst_id` or personal analyst identifiers in exported CSV,
     TSV, or `.xlsx` files.
5. **JavaScript Validation**:
   - Whenever modifying inline `<script>` templates in the Python generators,
     always extract the generated `<script>` block and run `node --check` to
     verify zero syntax errors.
