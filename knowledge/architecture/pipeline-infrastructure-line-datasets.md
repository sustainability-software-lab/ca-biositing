---
type: Architecture
title: "Infrastructure line datasets: crude oil pipelines, petroleum pipelines and railways (GeoJSON to geom)"
description: "Three GeoJSON MULTILINESTRING datasets skip geocoding, store geometry as WKB hex in a geom column, and have no address FK; they differ from the other 15 in extract, transform and load."
tags: [pipeline, infrastructure, geospatial, postgis, geojson, geometry]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:26:56Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/railways.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/petroleum_pipelines.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/crude_oil_pipelines.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/petroleum_pipelines.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/crude_oil_pipelines.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/infrastructure/railways.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/railways.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/petroleum_pipelines.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/crude_oil_pipelines.py"]
sources: ["commit f8c9353", "https://github.com/sustainability-software-lab/ca-biositing/pull/514"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Crude oil pipelines, petroleum pipelines and railways are line features, not facilities. They arrive as GeoJSON with geometry already set, so they skip the address-to-geocoded sheet. Their tables store the line in a PostGIS `geom` column.

## Key files
| Path:line | Role |
|---|---|
| `etl/extract/railways.py:25` | `FILE_NAME = "US_Railways.geojson"`, MIME `application/geo+json`; returns a GeoDataFrame |
| `etl/extract/petroleum_pipelines.py`, `etl/extract/crude_oil_pipelines.py` | Same pattern, `US_Petroleum_Pipelines.geojson` and `US_Crude_Oil_Pipelines.geojson` |
| `etl/transform/infrastructure/petroleum_pipelines.py:61-66` | Converts the GeoDataFrame `geometry` column to WKB hex in `geom`, then drops `geometry` (same in crude oil at `:61-66` and railways) |
| `etl/transform/infrastructure/crude_oil_pipelines.py:136` | `except KeyError` returns the unselected `combined_df` |
| `etl/load/infrastructure/railways.py:45`, `:78` | Batch log line, then `on_conflict_do_update(index_elements=["object_id"])` |
| `datamodels/.../models/infrastructure/railways.py:25` | `geom: Optional[Any] = Field(default=None, sa_column=Column(Geometry("MULTILINESTRING")))` (also petroleum `:27`, crude oil `:27`) |

## How it works
1. Extract: `gdrive_to_df` parses GeoJSON with `gpd.read_file(io.StringIO(...))`.
2. Transform: `standard_clean` and coercion on the attribute columns (for example `float_cols` in `petroleum_pipelines.py`), then WKB conversion. No `to_crs` call appears in these transforms, so the source CRS is passed through unchanged (inferred; confirm against the source file).
3. Load: the `geom` strings are inserted as PostGIS geometry; the upsert key is `object_id`.
4. No `location_address` or `place` row is created. The model has no `address_id` (grep of the three models).

## Interfaces
- Input: three GeoJSON files on Drive.
- Output: `infrastructure_railways`, `infrastructure_petroleum_pipelines`, `infrastructure_crude_oil_pipelines`, each with `geom`, `etl_run_id` and `lineage_group_id`.

## Gotchas
- The load expects WKB hex strings, not shapely objects (`load` docstring, e.g. `railways.py:16`). Passing raw geometries fails at insert.
- Like the other 15 transforms, `crude_oil_pipelines.py:136` returns the unselected frame on `KeyError`.
- The `temp_external_datasets/US_Petroleum_Pipelines.geojson` copy that existed before f8c9353 has been removed; the Drive file is now the only source.

## History
- f8c9353 (PR #514, 2026-10-22): added the three flows and models. The 126,618-line committed GeoJSON was deleted in the same commit.

## Open questions
- Whether `object_id` is stable across Drive re-exports of the GeoJSON (not verified; the re-run test only proves idempotence on the same input).

# Related Concepts
- [Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern](pipeline-infrastructure-etl-family.md): the family these three flows belong to
- [Infrastructure tables (infrastructure_* facility datasets, facility_record)](datamodels-infrastructure.md): the line tables and their geom column
- [Land IQ ETL flow (shapefile to landiq_record and polygon)](flow-landiq-etl.md): another geospatial polygon and line load that writes PostGIS geometry
- [Places tables: place (GEOID natural key), location_address, multilinestring](datamodels-places.md): the MULTILINESTRING geometry type used here
