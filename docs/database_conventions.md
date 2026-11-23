# Database Conventions

This project uses the following conventions for qualitative ETL data and related
lookup tables:

- Lookup names are stored in lowercase.
- Parameter names use lowercase words separated by spaces, not snake case.
  - Example: `resource_use_perc_low` → `resource use perc low`
- Qualitative use case values are loaded from the `use_case_name` column in the
  source sheet.
- When a source sheet provides multiple labels for the same concept, the
  canonical database value is the lowercase `use_case_name` value.
- ETL lineage fields should be populated when the model supports them:
  - `etl_run_id`
  - `lineage_group_id`

These conventions are intended to keep lookup matching stable across ETL runs
and to align source labels with database queries that compare against lowercase
names.

## Geospatial & SRID Conventions

All geospatial pipelines, database tables, static boundary files, and
visualizations follow a three-tier Coordinate Reference System (CRS / SRID)
architecture:

| Tier                                   | Authority Code  | SRID   | Name / Datum                       | Canonical Usage in `ca-biositing`                                                                                                                                                                                                                               |
| :------------------------------------- | :-------------- | :----- | :--------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Storage & Interchange (Default)** | **`EPSG:4326`** | `4326` | WGS 84 (Geographic lon/lat)        | **Project Standard** for all `.geojson` files (`data/static/ca_counties.geojson`), PostGIS `geometry` columns, `data/test/test_landiq.shp`, and web mapping libraries (Plotly, MapLibre, Leaflet).                                                              |
| **2. Planar Analysis & Cartography**   | **`EPSG:3310`** | `3310` | NAD83 / California Albers (Meters) | Equal-area conic projection for California. Required whenever computing polygon areas (`area_sq_km`, `area_acres`), planar distances/buffers, interior label points (`representative_point()`), or pre-projected SVG maps (`data/static/ca_counties_svg.json`). |
| **3. Raw Agency Ingestion**            | **`EPSG:4269`** | `4269` | NAD83 (Geographic lon/lat)         | Source CRS of raw US Census TIGER/Line and California DWR / LandIQ (`i15_Crop_Mapping_*.shp`) shapefiles. **Always reproject to `EPSG:4326` on ingest** (`gdf.to_crs("EPSG:4326")`).                                                                            |

### Canonical California County Boundaries & Joins

- Always use `data/static/ca_counties.csv`, `data/static/ca_counties.geojson`
  (`EPSG:4326`), or `data/static/ca_counties_svg.json` (`EPSG:3310`) for county
  and regional boundary mapping—never use the field-level LandIQ shapefile
  (`data/landiq/i15_Crop_Mapping_*.shp`) to derive or plot county boundaries.
- To rebuild the static geospatial assets from `data/static/ca_counties.csv`:
  `pixi run python scripts/build_ca_counties_geo.py`.
- Join county records across `data_portal` materialized views using the 5-digit
  FIPS `geoid` (`06001`–`06115`, or `06000` for unresolved state-level fallback)
  or lowercase `county_name` (without the `" County"` suffix), and group regions
  using lowercase `region_name` (e.g., `"north san joaquin valley"`).
