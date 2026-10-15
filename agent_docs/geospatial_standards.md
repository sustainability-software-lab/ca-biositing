# Geospatial & Coordinate Reference System (CRS / SRID) Standards

This document defines the canonical Coordinate Reference System (CRS / SRID)
conventions, static boundary datasets, and join patterns for geospatial analysis
and mapping in `ca-biositing`.

## 1. Coordinate Reference System (SRID) Standards

All geospatial pipelines, database tables, static GeoJSON assets, and
visualizations must adhere to the following three-tier CRS architecture:

| Tier                                   | Authority Code  | SRID   | Name / Datum                       | Canonical Usage in `ca-biositing`                                                                                                                                                                                                                               |
| :------------------------------------- | :-------------- | :----- | :--------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Storage & Interchange (Default)** | **`EPSG:4326`** | `4326` | WGS 84 (Geographic lon/lat)        | **Project Standard** for all `.geojson` files (`data/static/ca_counties.geojson`), PostGIS `geometry` columns, `data/test/test_landiq.shp`, and web mapping libraries (Plotly, MapLibre, Leaflet).                                                              |
| **2. Planar Analysis & Cartography**   | **`EPSG:3310`** | `3310` | NAD83 / California Albers (Meters) | Equal-area conic projection for California. Required whenever computing polygon areas (`area_sq_km`, `area_acres`), planar distances/buffers, interior label points (`representative_point()`), or pre-projected SVG maps (`data/static/ca_counties_svg.json`). |
| **3. Raw Agency Ingestion**            | **`EPSG:4269`** | `4269` | NAD83 (Geographic lon/lat)         | Source CRS of raw US Census TIGER/Line and California DWR / LandIQ (`i15_Crop_Mapping_*.shp`) shapefiles. **Always reproject to `EPSG:4326` on ingest** (`gdf.to_crs("EPSG:4326")`).                                                                            |

## 2. Canonical California County Boundary Assets

> [!IMPORTANT] **Never use field-level LandIQ shapefiles
> (`data/landiq/i15_Crop_Mapping_*.shp`) to derive or plot county boundaries.**
> The LandIQ dataset is a large (>400 MB) agricultural parcel layer. Always use
> the canonical county assets in `data/static/`:

- **[`data/static/ca_counties.csv`](../data/static/ca_counties.csv)**:
  - Canonical 58-county tabular lookup (`geoid`, `state_name`, `state_fips`,
    `county_name`, `county_fips`, `agg_level_desc`, `region_name`).
- **[`data/static/ca_counties.geojson`](../data/static/ca_counties.geojson)**:
  - Canonical RFC 7946 GeoJSON in **`EPSG:4326` (SRID `4326`)** containing all
    58 California counties, enriched with all `ca_counties.csv` attributes plus
    planar `area_sq_km` and `area_acres` (computed in `EPSG:3310`) and interior
    `centroid_lon`/`centroid_lat`.
  - Each feature sets top-level `"id": geoid` (e.g., `"06099"` for Stanislaus
    County) so Plotly choropleths can join directly with `locations="geoid"` and
    `featureidkey="id"`.
- **[`data/static/ca_counties_svg.json`](../data/static/ca_counties_svg.json)**:
  - Pre-projected **`EPSG:3310` (California Albers)** SVG paths
    (`viewBox="0 0 800 920"`), interior label placement points, and regional
    bounding boxes (`north san joaquin valley`, `south san joaquin valley`,
    `sacramento valley`, `central valley`, `bay area`, etc.) for zero-dependency
    interactive HTML/SVG widgets.

To rebuild both static geospatial files from `data/static/ca_counties.csv`:

```bash
pixi run python scripts/build_ca_counties_geo.py
```

## 3. Joining `data_portal` Views to County Geometries

- **Primary Join Key (`geoid`)**: 5-digit FIPS string (`"06001"` through
  `"06115"`). Available directly on `data_portal.mv_biomass_volume_estimate`,
  `data_portal.mv_biomass_pricing`, `data_portal.mv_biomass_search`,
  `data_portal.mv_biomass_composition`, and
  `data_portal.mv_biomass_sample_stats`.
- **Secondary Join Key (`county_name`)**: Lowercase county name without the
  `" County"` suffix (e.g., `"stanislaus"`, `"merced"`, `"san joaquin"`).
- **Regional Grouping (`region_name`)**: Lowercase canonical California region
  (e.g., `"north san joaquin valley"`, `"south san joaquin valley"`,
  `"sacramento valley"`).

## 4. macOS Apple Silicon `PROJ_LIB` Requirement

Before importing `geopandas` or `pyogrio` in any script, always point `PROJ_LIB`
to the active Pixi environment's PROJ data directory:

```python
import os
import pyproj

os.environ["PROJ_LIB"] = pyproj.datadir.get_data_dir()
import geopandas as gpd
```
