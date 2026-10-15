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

All geospatial storage, static boundary files, and analytical views follow these
standards:

- **Canonical Storage & Interchange SRID (`EPSG:4326` / WGS 84, SRID `4326`)**:
  - All `.geojson` files in the repository (including
    `data/static/ca_counties.geojson`) and PostGIS `geometry` columns use
    `EPSG:4326`.
  - Raw agency shapefiles in `EPSG:4269` (NAD83, such as LandIQ crop mapping or
    US Census TIGER/Line) must be reprojected to `EPSG:4326`
    (`gdf.to_crs("EPSG:4326")`) when standardized.
- **Planar Analysis & Cartographic Projection SRID (`EPSG:3310` / NAD83
  California Albers, SRID `3310`)**:
  - Equal-area conic projection for California used for computing accurate
    planar polygon areas (`area_sq_km`, `area_acres`), interior label
    coordinates (`representative_point()`), and pre-projected SVG paths
    (`data/static/ca_counties_svg.json`).
- **Canonical California County Boundaries & Joins**:
  - Always use `data/static/ca_counties.csv`, `data/static/ca_counties.geojson`
    (`EPSG:4326`), or `data/static/ca_counties_svg.json` (`EPSG:3310`) for
    county and regional boundary mapping—never use the field-level LandIQ
    shapefile (`data/landiq/i15_Crop_Mapping_*.shp`) for county boundaries.
  - Join county records using the 5-digit FIPS `geoid` (`06001`–`06115`) or
    lowercase `county_name` (without the `" County"` suffix), and group regions
    using lowercase `region_name` (e.g., `"north san joaquin valley"`).
