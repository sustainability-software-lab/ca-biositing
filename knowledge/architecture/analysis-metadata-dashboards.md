---
type: Architecture
title: Metadata and summary dashboards (analysis/metadata)
description: "analysis/metadata holds two legacy summary scripts (matplotlib counts; a Plotly DB dashboard that writes at import time) beside the resource dashboard suite added in #518-#535."
tags: [metadata, dashboard, plotly, matplotlib, qc]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:54Z" }
status: stable
governance: context
code_refs: ["analysis/metadata/data_summary_viz.py", "analysis/metadata/database_metadata_dashboard.py", "analysis/metadata/audit_profiling_output.txt", "analysis/metadata/resource_analysis_dashboard.py", "analysis/metadata/resource_explorer_dashboard.py", "analysis/metadata/resource_insights_engine.py", "analysis/metadata/resource_audit_workbench.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/442", "commit 707afa8", "https://github.com/sustainability-software-lab/ca-biositing/pull/518", "https://github.com/sustainability-software-lab/ca-biositing/pull/535", "commit a2c8de8"]
---

## Purpose
Database-wide summaries used for the gallery’s Aim 1 / Aim 2 counts, the QC filter-quality chart, and the legacy metadata dashboard. The folder now also holds the resource dashboard suite; see architecture/analysis-resource-dashboard-suite.

## Key files
| Path:line | Role |
| --- | --- |
| analysis/metadata/data_summary_viz.py:20 | `generate_visualizations()`: record counts by aim |
| analysis/metadata/data_summary_viz.py:37, 53, 70 | Saves `aim1_record_counts.png`, `aim2_record_counts.png`, `filter_quality_assessment.png` (dpi 300) |
| analysis/metadata/data_summary_viz.py:75 | `if __name__ == "__main__":` guard |
| analysis/metadata/database_metadata_dashboard.py:35 | `get_dashboard_data()` runs 4 SQL queries |
| analysis/metadata/database_metadata_dashboard.py:238-245 | Top-level `os.makedirs` and five `write_html` calls (no guard) |
| analysis/metadata/audit_profiling_output.txt | Captured failed run: `scripts/audit_profiling.sql` not found |
| analysis/metadata/resource_analysis_dashboard.py:7779 | Resource suite Pages 1-2 (see the suite concept) |
| analysis/metadata/resource_explorer_dashboard.py:5376 | Resource suite Page 3 |
| analysis/metadata/resource_insights_engine.py:1293 | AI insights sidecar used by Page 1 |
| analysis/metadata/resource_audit_workbench.py:3557 | Product 4 workbench |

## How it works
`data_summary_viz.py` is a standard script. `database_metadata_dashboard.py` builds Plotly figures from DB queries and writes five HTML files (`database_analysis_type_dist`, `database_resource_stats`, `database_resource_hierarchy`, `database_samples_over_time`, `database_samples_over_time_ag`) into `exports/plots/metadata/`. The resource scripts take their data from live PostgreSQL or from a snapshot (see the suite concept).

## Interfaces
- **Inputs:** Postgres via `get_engine`.
- **Outputs:** PNGs and HTML under `exports/plots/metadata/`.
- **Callers:** `scripts/regenerate_all_plots.py` runs every `*.py` in the metadata category with no arguments (regenerate_all_plots.py:26), so the resource scripts also run against live DB there; the dashboard workflow and `refresh-dashboards` call the resource scripts directly.

## Gotchas
- `database_metadata_dashboard.py` does all work at import time, so `import` or pytest collection triggers DB queries and file writes. Wrap it in `main()` before reusing it.
- Its `set_lbnl_theme_mpl` import is unused.
- `audit_profiling_output.txt` is a log, not an input; it shows a failed run from 2026-04-30 caused by a missing SQL file.
- Because the metadata folder is globbed, a resource script with a required argument would fail the whole `update-plots` category (inferred from the runner).

## History
- Added with the gallery (`707afa8`, PR #442).
- Resource dashboard suite added beside them: `d290906` (PR #518), `c4cbf2d` (PR #525), `587c1cb` (PR #526), `f4e9f5a` (PR #530), `a2c8de8` (PR #535), 2026-10-19 to 2026-10-22.

## Open questions
- Whether `data_summary_viz.py` is the source of the numbers in `exports/data_summary_report.md` (inferred from the Aim 1 / Aim 2 labels; confirm by running it).

# Related Concepts
- [Plot regeneration, HTML gallery index, and GitHub Pages deploy](analysis-regeneration-and-gallery.md): Runner executes these scripts as the metadata category
- [exports/ directory: committed SQL, reports, and plot outputs](analysis-exports-artifacts.md): Writes the metadata plots and feeds the dated summary report
- [Five-product BioCirV resource dashboard suite and how each is generated](analysis-resource-dashboard-suite.md): the resource suite now sharing this folder
