---
type: Architecture
title: "Jupyter notebook inventory (17 notebooks, outside analysis/)"
description: "All 17 .ipynb files live under datamodels and pipeline, not analysis/; several import a schemas.generated package that does not exist in the tree."
tags: [notebooks, jupyter, tutorials, pixi-kernel]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:40Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/utils/database_joins.ipynb", "src/ca_biositing/pipeline/docs/**/*.ipynb", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/**/*.ipynb", "docs/notebook_setup.md"]
sources: ["docs/notebook_setup.md", "commit f66e296", "commit dc98b30"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Teaching and debugging notebooks. There are no notebooks under `analysis/`, `exports/`, or `visualization/`.

## Inventory (17 files, grouped by purpose)
| Group | Count | Location | Examples |
|---|---|---|---|
| Datamodels walkthrough | 1 | `src/ca_biositing/datamodels/utils/database_joins.ipynb` | Denormalized joins with SQLAlchemy |
| Pipeline dev references | 4 | `src/ca_biositing/pipeline/docs/dev-references/` | `import_test`, `gsheet_inventory`, `get_sheet_names`, `test_lookup_utils` |
| Pipeline tutorials | 10 | `src/ca_biositing/pipeline/docs/tutorials/` | `etl_notebook`, `etl_class_example`, `gsheet_extraction_notebook`, `cleaning_functions`, `geospatial_cleaning`, `geopandas_shapefile_extraction`, `load_fips`, `tl_geojson`, `database_interaction`, `external_etl_notebook` |
| Pipeline utilities | 2 | `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/` | `geocode_to_drive.ipynb`, `cleaning_functions/cleaning_functions.ipynb` |

## Setup
- `docs/notebook_setup.md`: run `pixi install`, then `pixi run register-jupyter-kernel`, then `pixi run jupyter-lab` (`pixi.toml:63`). Kernel: pixi-kernel, so the editable namespace packages import without PYTHONPATH.

## Gotchas
- Notebooks in `datamodels/utils` and most pipeline tutorials import `ca_biositing.datamodels.schemas.generated.ca_biositing`. The `schemas/` directory is absent from `src/ca_biositing/datamodels/ca_biositing/datamodels/` (verified), and AGENTS.md says there is no code-generation step. These notebooks are likely stale (inferred; confirm by running one).
- Notebooks are not run in CI (inferred; no workflow references `.ipynb`).

## History
- `f66e296` (PR #344, 2026-05-13) and `dc98b30` (PR #108, 2026-02-11) touched the pipeline tutorials area; `a9a86eb` (PR #84) added the Berkeley Upstream integration.

## Open questions
- Which notebooks should be kept or deleted after the SQL-first schema move (inferred; needs an owner decision).

# Related Concepts
- [System overview (start here)](system-overview.md): Notebooks are a secondary entry point to the datamodels and pipeline packages
- [Analysis visualization scripts (analysis/) and how they query the DB](analysis-visualization-scripts.md): Analysis is script-based; notebooks here are documentation and debugging aids
