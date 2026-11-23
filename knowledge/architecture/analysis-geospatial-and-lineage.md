---
type: Architecture
title: County biomass map and sample-lineage Sankey scripts
description: "Two non-categorized analysis scripts: a plotly county choropleth from ca_counties.csv and a Sankey of resource to analysis lineage; the lineage one is not run by update-plots."
tags: [geospatial, sankey, lineage, counties, plotly]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:39Z" }
status: stable
code_refs: ["analysis/geospatial/viz_county_biomass.py", "analysis/sample_lineage_flow_viz.py", "data/static/ca_counties.csv", "data/test/test_landiq.shp"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/442", "commit 707afa8"]
governance: context
---

## Purpose
Two analysis outputs that do not fit the altair composition/conversion pattern.

## Key files
| Path:line | Role |
|---|---|
| `analysis/geospatial/viz_county_biomass.py:41` | Module-level `engine = get_engine()` (runs at import) |
| `analysis/geospatial/viz_county_biomass.py:56` | `pd.read_sql` biomass query |
| `analysis/geospatial/viz_county_biomass.py:68` | Reads `data/static/ca_counties.csv` (FIPS list) |
| `analysis/geospatial/viz_county_biomass.py:113-117` | Writes `exports/plots/ca_county_biomass.html` (docstring says `exports/plots/geospatial/`; code does not) |
| `analysis/sample_lineage_flow_viz.py:45-` | UNION ALL of ten `*_record` tables joined to `prepared_sample`, `field_sample`, `resource`, `primary_ag_product` |
| `analysis/sample_lineage_flow_viz.py:209-213` | Writes `exports/plots/lineage/sample_lineage_flow.html` |
| `data/static/ca_counties.csv` | County FIPS list; also read by the pipeline (`src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/geography.py:18`, `usda_census_survey.py:63`) |
| `data/test/test_landiq.{shp,shx,dbf,prj,cpg}` | LandIQ shapefile fixture; no reference found in `analysis/` or `src/` (inferred test data; confirm with the pipeline LandIQ tests) |

## How it works
Lineage Sankey: the 10 record types (compositional, proximate, ultimate, icp, xrf, xrd, calorimetry, pretreatment, fermentation, gasification) are unioned into rows of (primary_ag_product, resource, field_sample, prepared_sample, analysis_type). Levels are linked as Resource → Field Sample → Prepared Sample → Analysis and colored by primary ag product.

## Interfaces
- **Inputs:** Postgres (via `get_engine`), `data/static/ca_counties.csv`.
- **Outputs:** two HTML files under `exports/plots/`.
- **Callers:** manual runs only. The lineage script is not in the `update-plots` categories.

## Gotchas
- `viz_county_biomass.py` runs DB I/O at import time. Importing it from any other code connects to the database.
- The lineage script sets `POSTGRES_HOST=localhost` before importing `get_engine`.
- The lineage query does not apply `EXCLUDED_*` filters used by the composition charts (verified by reading the SQL); its counts will differ from the portal.

## History
- Gallery work (`707afa8`, PR #442) brought these into `exports/plots`. `analysis/geospatial` was last touched in the same commit.

## Open questions
- Whether the lineage chart should adopt the QC/exclusion filters (inferred as a gap; confirm with the maintainers).

# Related Concepts
- [Analysis visualization scripts (analysis/) and how they query the DB](analysis-visualization-scripts.md): Same DB-to-HTML pattern, different chart library and filters
- [Plot regeneration, HTML gallery index, and GitHub Pages deploy](analysis-regeneration-and-gallery.md): Lineage script is missing from the regeneration categories
- [System overview (start here)](system-overview.md): Pipeline geography extract also reads data/static/ca_counties.csv (src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/geography.py)
