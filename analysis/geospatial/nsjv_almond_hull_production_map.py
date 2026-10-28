# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # North San Joaquin Valley (NSJV) — Almond Hull Production Map
#
# Reproducible geospatial visualization of almond hull (`resource_id=32`, `almhu`)
# and co-product almond shell (`resource_id=5`, `almsh`) production across the
# three counties of the **North San Joaquin Valley**:
# - **Stanislaus County** (`06099`)
# - **Merced County** (`06047`)
# - **San Joaquin County** (`06077`)
#
# **Coordinate Reference System (CRS / SRID) Standards:**
# - Canonical Storage / GeoJSON: `EPSG:4326` (WGS 84, SRID `4326`) via `data/static/ca_counties.geojson`
# - Planar Cartographic Projection: `EPSG:3310` (NAD83 / California Albers, SRID `3310`) via `data/static/ca_counties_svg.json`

# %%
from pathlib import Path
import os
import sys

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

os.environ.setdefault("POSTGRES_HOST", "localhost")

from scripts.viz.generate_ca_county_widget import (
    build_nsjv_almond_dataset,
    load_svg_geometries,
    query_resource_from_db,
    render_widget_html,
)

# %% [markdown]
# ## 1. Query `data_portal` Materialized Views
#
# Queries `data_portal.mv_biomass_volume_estimate` and `data_portal.mv_biomass_pricing`
# for `almond hulls` and `almond shells` in `north san joaquin valley`.

# %%
raw_query_payload = query_resource_from_db()
dataset = build_nsjv_almond_dataset(raw_query_payload)
print(
    f"Loaded NSJV Almond Hull dataset for years {dataset['years']} "
    f"(Latest year {dataset['latest_year']}: "
    f"{dataset['by_year'][str(dataset['latest_year'])]['total_tons']:,.0f} tons)"
)

# %% [markdown]
# ## 2. Load Canonical California County Geometries & Render Interactive HTML Widget

# %%
svg_geo = load_svg_geometries(repo_root / "data/static/ca_counties_svg.json")
output_path = repo_root / "exports/plots/geospatial/nsjv_almond_hull_map.html"
output_path.parent.mkdir(parents=True, exist_ok=True)

html_doc = render_widget_html(svg_geo, dataset, standalone=True)
output_path.write_text(html_doc, encoding="utf-8")
print(f"Saved interactive NSJV Almond Hull county map to {output_path}")
