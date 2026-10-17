---
name: ca-county-map
description:
  Generate reproducible interactive California county and regional (e.g., North
  San Joaquin Valley, Central Valley, Bay Area) choropleth maps and inline
  generative UI widgets from ca-biositing data_portal materialized views using
  canonical EPSG:4326 and EPSG:3310 county boundary assets.
---

# California County Geospatial Map Skill (`ca-county-map`)

Use this skill whenever the user asks to map California counties or regions
(such as the North San Joaquin Valley, South San Joaquin Valley, Sacramento
Valley, or statewide 58 counties), visualize county-level biomass
production/pricing/availability from `data_portal` materialized views, or build
an interactive geospatial widget.

## 1. Canonical Geospatial Assets (Never Use Field-Level LandIQ Shapefiles for Counties)

> [!IMPORTANT] **Do NOT use `data/landiq/i15_Crop_Mapping_*.shp` for county
> boundary maps.** The LandIQ shapefile is a large (>400 MB) field-level polygon
> dataset. Always use the lightweight canonical static county assets in
> `data/static/`:

| File                                                                            | CRS / SRID                    | Size    | Purpose                                                                                                                                                                                                     |
| :------------------------------------------------------------------------------ | :---------------------------- | :------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`data/static/ca_counties.csv`](../../../data/static/ca_counties.csv)           | Tabular                       | ~3 KB   | Canonical 58-county lookup (`geoid`, `county_name`, `county_fips`, `state_fips`, `region_name`)                                                                                                             |
| [`data/static/ca_counties.geojson`](../../../data/static/ca_counties.geojson)   | **`EPSG:4326`** (SRID `4326`) | ~274 KB | Canonical RFC 7946 GeoJSON with top-level `"id": geoid` and enriched properties (`area_sq_km`, `area_acres`, `centroid_lon`, `centroid_lat`, `region_name`) for GeoPandas, Plotly, Folium, and PostGIS      |
| [`data/static/ca_counties_svg.json`](../../../data/static/ca_counties_svg.json) | **`EPSG:3310`** (SRID `3310`) | ~110 KB | Pre-projected California Albers equal-area SVG paths (`viewBox="0 0 800 920"`), interior label coordinates, and regional zoom `viewBox` presets for zero-dependency inline `<agent-embed>` HTML/SVG widgets |

To rebuild or refresh the static county geo assets from
`data/static/ca_counties.csv`:

```bash
pixi run python scripts/build_ca_counties_geo.py
```

## 2. Project Coordinate Reference System (CRS / SRID) Standards

Always enforce and document the project's three-tier CRS convention:

1. **Canonical Storage & Interchange CRS — `EPSG:4326` (WGS 84, SRID `4326`)**:
   - Standard for all repository `.geojson` files
     (`data/static/ca_counties.geojson`), PostGIS `geometry(Geometry, 4326)`
     columns, and web mapping APIs.
2. **Planar Analysis & Cartographic Projection CRS — `EPSG:3310` (NAD83 /
   California Albers, SRID `3310`)**:
   - Equal-area conic projection for California. Always reproject to `EPSG:3310`
     (`gdf.to_crs("EPSG:3310")`) before calculating polygon areas (`area_sq_km`,
     `area_acres`), distances, interior `representative_point()` coordinates, or
     static/SVG cartographic projections.
3. **Raw Agency Source CRS — `EPSG:4269` (NAD83, SRID `4269`)**:
   - Common in raw US Census TIGER/Line and California DWR/LandIQ shapefiles.
     Always reproject to `EPSG:4326` on ingest (`gdf.to_crs("EPSG:4326")`).

### macOS Apple Silicon `PROJ_LIB` Rule

Before importing `geopandas` or `pyogrio` in any Python script, always set
`PROJ_LIB`:

```python
import os, pyproj
os.environ["PROJ_LIB"] = pyproj.datadir.get_data_dir()
import geopandas as gpd
```

## 3. Joining `data_portal` Views to California Counties (Multi-Tier Resource Waterfall)

Most biomass resources in `data_portal` do **not** have market pricing
(`mv_biomass_pricing`) or 8-year direct production records
(`public.resource_production_record`).
[`scripts/viz/generate_ca_county_widget.py`](../../../scripts/viz/generate_ca_county_widget.py)
automatically executes a **3-tier county volume waterfall + metadata
enrichment** across all `data_portal` views so any resource works out of the
box:

### Volume Estimation Tiers

1. **Tier 1 — `data_portal.mv_biomass_volume_estimate` _(Primary Canonical
   County Volume View)_**:
   - **Columns**: `id`, `resource_id`, `resource_name`, `geoid` (5-digit FIPS,
     e.g. `'06099'`), `county` (lowercase, e.g. `'stanislaus'`), `county_fips`,
     `state`, `dataset_year`, `production_volume` (primary crop tons),
     `county_crop_acres`, `production_unit`, `factor_min`, `factor_mid`,
     `factor_max`, `estimated_residue_volume_min`,
     `estimated_residue_volume_mid`, `estimated_residue_volume_max`,
     `volume_source`, `biomass_unit` (`'dry_tons'` or `'tons'`).
   - **Estimation Paths (`volume_source`)**:
     - `commodity_direct` (2023–2024): Direct county ag commissioner reporting
       (`almond hulls`, `almond shells`).
     - `production_based` (2023–2024): Primary crop production
       (`production_volume` tons) $\times$ residue conversion factor
       (`factor_mid`), covering **`walnut hulls`**, **`walnut shells`**,
       **`walnut shelling fines`**, **`pistachio shells`**,
       **`pistachio hulls`**, **`tomato pomace`**, **`grape pomace`**,
       **`peach pomace`**, **`olive pomace`**, **`sweet potato culls`**,
       **`rice hulls`**, and **`rice straw`** (2023–2024).
     - `census_production_based` (2017, 2022): USDA Census production $\times$
       conversion factor (**`corn stover whole`**, **`corn stover stalks`**,
       **`corn stover cobs`**, **`corn stover husks`**).
     - `prune_acres` / `acreage_based` (2017, 2022): Acreage-based pruning/field
       residue rows (**`grape vines`**, **`grape stem`**, **`almond branches`**,
       **`walnut tree sticks`**, **`cotton stem mix`** — supplemented by Tier 2
       `mv_usda_county_production`).
2. **Tier 2 — `data_portal.mv_usda_county_production` _(Orchard Bearing-Acreage
   & Census Fallback)_**:
   - **Columns**: `id`, `resource_id`, `resource_name`, `primary_ag_product`,
     `geoid`, `county`, `county_fips`, `state`, `dataset_year`,
     `primary_product_volume`, `volume_unit`, `production_acres` (coalesced from
     `'area bearing & non-bearing'`, `'area bearing'`, and `'area harvested'`),
     `calculated_estimate_volume` (`production_acres * dry_tons_per_acre`).
   - **When Used**: Automatically fills county volumes and bearing acreage when
     `mv_biomass_volume_estimate.estimated_residue_volume_mid` is `NULL`
     (because `mv_biomass_volume_estimate` Path D queries
     `parameter_id IN (7, 3)` and omits `parameter_id = 5` `'area bearing'`,
     which USDA NASS Census reports for tree/vine crops such as
     **`almond branches`**, **`walnut tree sticks`**, **`grape vines`**,
     **`grape stem`**, and **`olive prunings`**, as well as `'area harvested'`
     for **`cucumber culls`**, **`cotton stem mix`**, and 2017/2022
     **`rice straw`**).
3. **Tier 3 — `public.resource_production_record` _(Historical Direct
   Series)_**:
   - Provides 2017–2022 historical county volumes for `almond hulls`,
     `almond shells`, and `almond hash` (overlaid by Tier 1
     `mv_biomass_volume_estimate` in 2023–2024 per
     [Issue #496](https://github.com/sustainability-software-lab/ca-biositing/issues/496)).

### Metadata & Enrichment Views

- **`data_portal.mv_biomass_search`** _(Regional Search, Co-Products & Chemical
  Composition)_:
  - **Columns**: `id` (resource ID), `resource_code`, `resource` (resource
    name), `primary_product`, `region` (lowercase region name), `county_count`,
    `total_annual_volume`, `total_annual_volume_year`,
    `calculated_estimate_volume_mid`, `volume_estimate_year`,
    `moisture_percent`, `ash_percent`, `lignin_percent`, `cellulose_percent`,
    `hemicellulose_percent`, `hhv`, `lhv`, `carbon_percent`.
  - Used to identify the `primary_product` (e.g. `'almonds'` for
    `almond branches` or `'walnuts'` for `walnut hulls`), discover **primary and
    secondary sibling co-product resources** sharing the same `primary_product`
    (e.g. `almond hulls`, `almond shells`, `almond hash`), and surface
    proximate/ultimate composition (`moisture_percent`, `ash_percent`,
    `lignin_percent`).
  - **Data Quality Note
    ([Issue #496](https://github.com/sustainability-software-lab/ca-biositing/issues/496))**:
    Always prefer `calculated_estimate_volume_mid` over `total_annual_volume`
    (except for Tier 2 `'area bearing'` resources where
    `calculated_estimate_volume_mid` is `NULL` and
    `mv_usda_county_production.calculated_estimate_volume` is authoritative).
- **`data_portal.mv_biomass_availability`** _(Seasonal Harvest/Pruning Window &
  Per-Acre Residue Factors)_:
  - **Columns**: `id`, `resource_id`, `resource_name`, `from_month` (`1`–`12`),
    `to_month` (`1`–`12`), `year_round` (`bool`), `kg_per_acre`,
    `dry_tons_per_acre`, `wet_tons_per_acre`.
  - **Schema Note**: This view has **1 row per `resource_id` and no `geoid` or
    `county` column** (harvest/pruning seasonality and per-acre dry/wet residue
    factors are defined per biomass resource).
- **`data_portal.mv_biomass_pricing`** _(USDA AMS Market Pricing)_:
  - **Columns**: `resource_id`, `resource_name`, `geoid` (`'06099'` or regional
    `'NSJV'`), `county`, `report_date`, `report_source`, `market_type_category`,
    `sale_type`, `price_min`, `price_max`, `price_avg`, `price_unit`.
  - Available for `almond hulls`, `almond shells`, and `almond hash`. When a
    resource has no pricing rows (e.g. `walnut hulls`),
    `generate_ca_county_widget.py` automatically adapts KPI Card 3, county
    ranking badges, and the bottom panel to display **Primary Crop Tonnage +
    Conversion Factor** (`×0.524 dry t/t`), **Seasonal Harvest Window**
    (`Sep–Nov`), **Sibling Co-Product Totals**, and **Chemical Composition**
    (`Lignin 35.1%`)—never rendering `"$—/t"` or `"Market Price: N/A"`.

### California Regions (`region_name` in `data/static/ca_counties.csv`)

All 12 canonical regions have precomputed zoom `viewBox` bounding boxes in
`data/static/ca_counties_svg.json` (plus `"statewide"` and `"central valley"`):

- `north san joaquin valley` (`06047` Merced, `06077` San Joaquin, `06099`
  Stanislaus)
- `south san joaquin valley` (`06019` Fresno, `06029` Kern, `06031` Kings,
  `06039` Madera, `06107` Tulare)
- `sacramento valley` (`06007` Butte, `06011` Colusa, `06021` Glenn, `06067`
  Sacramento, `06089` Shasta, `06093` Siskiyou, `06101` Sutter, `06103` Tehama,
  `06113` Yolo, `06115` Yuba)
- `bay area`, `central coast`, `sierra nevada`, `north coast`, `inland empire`,
  `los angeles`, `orange county`, `san diego`, `modoc plateau`

## 4. Generating Interactive County Map Widgets (One-Step CLI Workflow)

### Option A: Zero-Dependency Interactive SVG/HTML Widget (Recommended for `<agent-embed>` & Quick Dashboards)

Because external JS CDNs (like `cdn.plot.ly` or `unpkg.com/leaflet`) are blocked
by Content Security Policy (CSP) inside `<agent-embed>` iframes, use
`data/static/ca_counties_svg.json` + Tailwind CSS
(`https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js`) via
[`scripts/viz/generate_ca_county_widget.py`](../../../scripts/viz/generate_ca_county_widget.py).

**You do NOT need to write a separate exploratory SQL script first.** Running
`generate_ca_county_widget.py` with `--resource "<resource_name>"` and
`--save-data-json <path>` queries all `data_portal` views, resolves the
multi-tier waterfall, prints a summary (`Latest year`, `Total volume`,
`Source`), saves the full structured JSON payload (so you can inspect exact
county figures), and writes both the standalone and inline HTML files in a
single step:

```bash
# Single command to query PostgreSQL (requires BypassSandbox: true for localhost:5432 socket access),
# save the structured JSON summary, and generate both standalone and inline HTML for ANY resource:
.pixi/envs/default/bin/python scripts/viz/generate_ca_county_widget.py \
  --resource "walnut hulls" \
  --save-data-json /tmp/nsjv_walnut_hull_data.json \
  --output exports/plots/geospatial/nsjv_walnut_hull_map.html \
  --inline-output exports/plots/geospatial/nsjv_walnut_hull_map_inline.html
```

> [!TIP] **Fastest Agent Workflow & Sandbox Rule:**
>
> 1. In Standard Sandbox Mode (`BypassSandbox: false`), invoking `pixi`
>    (`~/.pixi/bin/pixi`) or connecting to `localhost:5432` is blocked by macOS
>    Seatbelt. Always invoke `.pixi/envs/default/bin/python` directly (from the
>    repo root).
> 2. Run the single command above (attempting `BypassSandbox: false` first per
>    sandbox rules, then retrying the exact same command with
>    `BypassSandbox: true` and identical `toolAction`/`toolSummary` when
>    `localhost:5432` connection is blocked).
> 3. View the saved `--save-data-json` file (e.g.
>    `/tmp/nsjv_walnut_hull_data.json`) with `view_file` to read the exact
>    county volumes, primary crop tonnages, conversion factors, co-products, and
>    availability window for your response—zero ad-hoc SQL scripts required!
> 4. If you subsequently tweak HTML/UI rendering, pass
>    `--data-json /tmp/nsjv_walnut_hull_data.json` instead of `--resource`,
>    which runs 100% offline inside Standard Sandbox Mode
>    (`BypassSandbox: false`) without touching PostgreSQL.

Follow the `generative_ui` skill rules when embedding inline:

1. Always register the target HTML file in
   `<appDataDir>/brain/<conversation-id>/` using `write_to_file` with
   `ArtifactMetadata` (`UserFacing: true`). If updating an already-embedded
   widget in the same conversation, write to a **new filename** (e.g.
   `*_v2.html`) so the chat webview does not serve a cached iframe for the
   previous `src` URL.
2. Keep inline widget height comfortably under `500px` (`~450px` total height)
   and `<body class="bg-transparent text-[var(--foreground)] antialiased p-2">`.
3. Never declare `:root` color overrides in inline artifacts; use semantic CSS
   variables (`--card`, `--background`, `--foreground`, `--muted-foreground`,
   `--border`) and set both `path.setAttribute("fill", ...)` and
   `path.style.fill = ...` on SVG paths.
4. Embed in your response using:
   ```html
   <agent-embed
     src="file:///path/to/artifact_dir/nsjv_walnut_hull_map.html"
   ></agent-embed>
   ```

### Option B: Plotly Choropleth with Canonical Local GeoJSON (`EPSG:4326`)

For standalone Plotly dashboards in `analysis/geospatial/`, load
`data/static/ca_counties.geojson` locally (never fetch remote GitHub GeoJSON
URLs at runtime):

```python
import json
import pandas as pd
import plotly.express as px

with open("data/static/ca_counties.geojson", encoding="utf-8") as f:
    ca_counties_geojson = json.load(f)

fig = px.choropleth(
    df,
    geojson=ca_counties_geojson,
    locations="geoid",
    featureidkey="id",
    color="estimated_volume_tons",
    scope="usa",
    hover_name="county_name",
)
fig.update_geos(fitbounds="locations", visible=False)
```
