---
type: Architecture
title: Land IQ ETL flow (shapefile to landiq_record and polygon)
description: "Chunked Prefect flow loading the Land IQ 2024 crop-mapping shapefile into polygon and landiq_record; disabled in the master registry, run standalone."
tags: [pipeline, etl, flow, geospatial, landiq, prefect]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:04Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/landiq_etl.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/landiq.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/landiq/landiq_record.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/landiq.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lineage.py", "resources/prefect/run_prefect_flow.py"]
sources: ["commit 3edcb17", "commit a9a86eb", "https://github.com/sustainability-software-lab/ca-biositing/pull/84", "https://github.com/sustainability-software-lab/ca-biositing/pull/127", "src/ca_biositing/pipeline/README.md"]
governance: context
stale_after: "2026-12-31"
---

**Purpose**
Loads Land IQ crop-mapping polygons (geometry + crop attributes) from a local shapefile or a zip downloaded from `LANDIQ_SHAPEFILE_URL`. Reads features in chunks (default 10000) with pyogrio to bound memory. Lineage record and group are created first.

**Key files**

| Path:line | Role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/landiq_etl.py:21-22 | `@flow(name="Land IQ ETL")` `landiq_etl_flow(shapefile_path, chunk_size=10000)` |
| flows/landiq_etl.py:49-57 | Source resolution: arg path, else URL download, else `DEFAULT_SHAPEFILE_PATH` |
| flows/landiq_etl.py:75-107 | Chunk loop: `pyogrio.read_info` then `read_dataframe(skip_features, max_features)` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/landiq.py:21 | `DEFAULT_SHAPEFILE_PATH = data/landiq/i15_Crop_Mapping_2024_Provisional.shp` |
| etl/extract/landiq.py:25 | `LANDIQ_SHAPEFILE_URL` read from env at import time |
| etl/extract/landiq.py:28 | `download_shapefile(url, logger)` returns (shp_path, tmp_dir) or None |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/landiq/landiq_record.py:16 | `transform_landiq_record`, sets `dataset="landiq_2024"` (line 51) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/landiq.py:134 | `load_landiq_record`: polygon insert then landiq_record upsert |
| etl/load/landiq.py:101 | `bulk_upsert_landiq_records` (on_conflict_do_update) |
| etl/load/landiq.py:20 | `bulk_insert_polygons_ignore` (on_conflict_do_nothing on md5(geom), dataset_id) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lineage.py:9,42 | `create_etl_run_record`, `create_lineage_group` |

**How it works**
1. Set `PROJ_LIB` from pyproj data dir, then import pyogrio (flows/landiq_etl.py:29-34).
2. Create etl_run record and lineage group (note: "Land IQ 2023 Crop Mapping (Chunked)").
3. For each chunk: extract GeoDataFrame, `transform_landiq_record`, `load_landiq_record`, then `del` the chunk.
4. Remove any temp dir from URL download in `finally`.

**Interfaces**
- Input: shapefile (.shp with companions) at a path, a URL to a zip, or the default path under `data/` (the compose mount `../../data:/app/data` makes it visible in the worker).
- Output: rows in `polygon` (Polygon, FK dataset) and `landiq_record` (LandiqRecord). Dataset name `landiq_2024`.
- Callers: `pixi run run-single-flow landiq_etl`. Not in the master registry (commented out at resources/prefect/run_prefect_flow.py:23).

**Gotchas**
- Errors inside the chunk loop are caught and only logged (flows/landiq_etl.py:109-110); the flow then returns normally, so Prefect can show Completed after partial failure.
- `LANDIQ_SHAPEFILE_URL` is read at module import (extract/landiq.py:25), not at flow run time.
- Module-level `sys.stdout.reconfigure` and debug `print`s run at import (flows/landiq_etl.py:5-9).
- Naming mismatch: lineage note says 2023, default file and dataset name say 2024. Confirm which vintage is authoritative.
- Local/Docker: the default shapefile is not in the repo; README says users must download it from landiq.com and place it under data/landiq/.

**History**
- a9a86eb (2026-02-05, PR #84 Berkeley Upstream integration): initial flow.
- 3edcb17 (2026-02-23, PR #127 staging Cloud Run ETL parity): added URL download path via `LANDIQ_SHAPEFILE_URL`.
- https://github.com/sustainability-software-lab/ca-biositing/pull/84 and https://github.com/sustainability-software-lab/ca-biositing/pull/127

**Open questions**
- Why is landiq_etl disabled in the master registry while static_resource_info depends on LandIQ crop names? (inferred: the Land IQ load is run manually; confirm with the maintainers.)
- Does the chunk loop need to fail the run on error? Currently it does not.

# Related Concepts
- [System overview (start here)](system-overview.md): Land IQ is one of the external-source ETL flows in the system
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Flow follows the shared extract/transform/load and lineage framework
- [Static Resource Info ETL flow and update-static-resource-info pixi task](flow-static-resource-info.md): static_resource_info maps LandIQ crop names to resources; that mapping depends on primary_ag_product, not on this flow, but both concern LandIQ data
- [temp_external_datasets folder: staged external geospatial/CSV inputs](flow-temp-external-datasets.md): Other geospatial external inputs staged in the same data area
