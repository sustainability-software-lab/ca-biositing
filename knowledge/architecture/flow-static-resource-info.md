---
type: Architecture
title: Static Resource Info ETL flow and update-static-resource-info pixi task
description: "Pulls the static_resource_info tab, writes resources/assets/resource_info.csv, loads LandIQ mappings and resource availability; pixi task then regenerates resource_info.json and validates headers."
tags: [pipeline, etl, flow, static-assets, pixi, google-sheets]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:09Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/static_resource_info.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/static_resource_info.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource_information/static_resource_info.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/static_resource_info.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/seed_commodity_mappings.py", "scripts/csv_to_json.py", "scripts/validate_headers.py", "scripts/run_flow.py", "resources/assets/resource_info.csv", "resources/assets/resource_info.json", "resources/assets/resource_info_header_mapping.json", "pixi.toml", "resources/docker/docker-compose.yml"]
sources: ["commit 6b575b1", "commit dc98b30", "https://github.com/sustainability-software-lab/ca-biositing/pull/436", "pixi.toml (task update-static-resource-info)"]
governance: context
stale_after: "2026-12-31"
---

**Purpose**
Keeps the database mapping tables (LandIQ crop to resource, and resource availability) in sync with a Google Sheet, and mirrors the same sheet into local JSON assets consumed outside the pipeline.

**Key files**

| Path:line | Role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/static_resource_info.py:4-5 | `@flow(name="Static Resource Info ETL")` `static_resource_info_flow()` |
| flows/static_resource_info.py:31-36 | Writes `resources/assets/resource_info.csv` (CWD-relative) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/static_resource_info.py:21-25 | GSheet `Static_resource_information`, tab `static_resource_info`. TODO comments remain at lines 21 and 24 |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource_information/static_resource_info.py:17 | `transform_static_resource_info` returns dict with `landiq_resource_mapping` and `resource_availability` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/static_resource_info.py:40 | `load_landiq_resource_mapping` (LandiqResourceMapping) |
| etl/load/static_resource_info.py:96 | `load_resource_availability` (ResourceAvailability; geoid default "06000" for CA in transform line 122) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/utils/seed_commodity_mappings.py | Run by the pixi task after the flow |
| scripts/csv_to_json.py:1-40 | Converts `resources/assets/resource_info.csv` to `resources/assets/resource_info.json` (booleans, blanks to null) |
| scripts/validate_headers.py | Checks CSV headers against `resources/assets/resource_info_header_mapping.json` |
| pixi.toml (task `update-static-resource-info`) | `python scripts/run_flow.py run static_resource_info && python .../seed_commodity_mappings.py && python scripts/csv_to_json.py && python scripts/validate_headers.py` (depends on start-services) |

**How it works**
1. Lineage record and group.
2. Extract the sheet. Write the CSV (warning, not failure, on write error).
3. Transform, then load both mapping tables. Abort if empty.

**Interfaces**
- Input: GSheet above.
- Local JSON assets written or refreshed: `resources/assets/resource_info.csv` (by the flow), then `resources/assets/resource_info.json` (by csv_to_json.py). `resources/assets/resource_info_header_mapping.json` is read-only input for validation. Docker mounts `resources/assets` into the worker at `/app/resources/assets` (resources/docker/docker-compose.yml), so the CSV write reaches the host.
- Outputs: `landiq_resource_mapping`, `resource_availability` tables.
- Callers: `pixi run update-static-resource-info`; master registry (run_prefect_flow.py:16).

**Gotchas**
- The pixi task runs the flow inside Docker, but the JSON conversion and validation run on the host. Both steps use CWD-relative paths, so run from the repo root.
- The task chain uses `&&`; if the flow fails the JSON is not regenerated, and a stale resource_info.json remains.
- The sheet names in extract are still template placeholders (TODO comments in extract/static_resource_info.py:21, 24). Confirm they match the live sheet.
- Requires primary_ag_product rows for landiq_crop_name lookups (transform lines 75-78).

**History**
- dc98b30 (2026-02-11, PR #108): flow introduced.
- 6b575b1 (2026-06-23, PR #436 dynamic top commodity discovery and resource_info.json revamp): JSON asset refresh path.
- https://github.com/sustainability-software-lab/ca-biositing/pull/436

**Open questions**
- No in-repo consumer of resource_info.json was found under src/ or frontend/ (grep). Consumer is probably outside this repo; confirm.

# Related Concepts
- [System overview (start here)](system-overview.md): Bridges Google Sheets reference data to both the database and local JSON assets
- [Land IQ ETL flow (shapefile to landiq_record and polygon)](flow-landiq-etl.md): Maps LandIQ crop names that the Land IQ data uses
- [Resource Information ETL flow (resources, then resource images)](flow-resource-information.md): Mapping and availability reference resources created by resource_information
- [Primary Ag Product ETL flow (basic sample info to primary_ag_product)](flow-primary-ag-product.md): Crop-name lookups require primary_ag_product
