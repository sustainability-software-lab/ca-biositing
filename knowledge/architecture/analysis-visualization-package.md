---
type: Architecture
title: ca_biositing.visualization package and LBNL theme
description: "Small src/ca_biositing/visualization package providing LBNL colors, a categorical palette, and matplotlib/plotly theme helpers used by all analysis scripts."
tags: [visualization, theme, matplotlib, plotly, pixi-viz]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:38Z" }
status: stable
code_refs: ["src/ca_biositing/visualization/ca_biositing/visualization/theme.py", "src/ca_biositing/visualization/pyproject.toml", "src/ca_biositing/visualization/README.md"]
sources: ["commit 707afa8", "pixi.toml"]
governance: context
---

## Purpose
Shared styling for the analysis layer so every chart uses the same LBNL palette and layout.

## Key files
| Path:line | Role |
|---|---|
| `src/ca_biositing/visualization/ca_biositing/visualization/theme.py:35` | `set_lbnl_theme_mpl()`: sets matplotlib rcParams (cycle, grid, spines) |
| `src/ca_biositing/visualization/ca_biositing/visualization/theme.py:68` | `get_lbnl_template_plotly()`: returns a Plotly layout template |
| `src/ca_biositing/visualization/ca_biositing/visualization/theme.py` (top) | `LBNL_COLORS` dict and `LBNL_PALETTE` list (deep blue, teal, gold, orange, green, red, gray) |
| `src/ca_biositing/visualization/pyproject.toml` | Package `ca-biositing-visualization` 0.1.0; depends on `ca-biositing-datamodels`; hatchling build |
| `src/ca_biositing/visualization/README.md` | Install note; says it lives in the `viz` pixi env |
| `pixi.toml:27` | `viz = features [datamodels, visualization, kernel]` |

## How it works
Pure Python, no DB access. Importing it imports matplotlib and plotly. Analysis scripts import `LBNL_PALETTE`, `set_lbnl_theme_mpl`, `get_lbnl_template_plotly`, or `LBNL_COLORS`.

## Interfaces
- **Inputs:** none.
- **Outputs:** constants and theme-setting functions.
- **Callers:** all `analysis/**/*.py` scripts; `analysis/geospatial/viz_county_biomass.py` imports `get_lbnl_template_plotly` and `LBNL_COLORS`.
- The package is not referenced from the root by a symlink (unlike datamodels, pipeline, webservice).

## Gotchas
- `database_metadata_dashboard.py` imports `set_lbnl_theme_mpl` but uses only Plotly (unused import; the comment says "if needed").
- The `viz` env is the only pixi environment that installs this package; the `default` env does not (inferred from the feature list; confirm with `pixi list -e default`).

## History
- Added with the analysis gallery work (`707afa8`, PR #442); the package’s own history is in the same window.

## Open questions
- Whether the LBNL palette is the official brand palette (inferred from the hex names; not documented in-repo).

# Related Concepts
- [Analysis visualization scripts (analysis/) and how they query the DB](analysis-visualization-scripts.md): Primary consumers of the theme helpers
- [System overview (start here)](system-overview.md): Part of the three-package-plus-visualization workspace layout
