---
type: Architecture
title: "Infrastructure tables (infrastructure_* facility datasets, facility_record)"
description: "19 infrastructure tables under models/infrastructure/: 18 facility and line datasets from #514 plus facility_record, most with etl_run and location_address foreign keys."
tags: [datamodels, infrastructure, facilities, geospatial]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:29Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/facility_record.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/biodiesel_plants.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/petroleum_pipelines.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/landfills.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/food_manufacturing_epa.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/__init__.py"]
sources: ["commit 7a41e0e", "commit f66e296", "https://github.com/sustainability-software-lab/ca-biositing/pull/112", "https://github.com/sustainability-software-lab/ca-biositing/pull/344", "alembic/versions/0006_add_petroleum_pipelines.py", "commit f8c9353", "https://github.com/sustainability-software-lab/ca-biositing/pull/514", "alembic/versions/0026_add_food_processing_infrastructure_datasets.py"]
---

## Purpose
Point, polygon and line data about California bioeconomy facilities (biodiesel plants, landfills, wastewater plants, food manufacturers, pipelines, railways, and others), plus `facility_record`, a cross-domain join record.

## Key files
| Path:line | Role |
|---|---|
| `models/infrastructure/facility_record.py:8` | `FacilityRecord(BaseEntity)`, table `facility_record`: `dataset_id` FK, `location_id` FK `location_address.id`, `resource_id` FK `resource.id`; `capacity_mw`, `facility_name`, `operator`, `start_year`, `note` |
| `models/infrastructure/biodiesel_plants.py:7-29` | `InfrastructureBiodieselPlants`: `biodiesel_plant_id` PK; `address_id` FK `location_address.id` (`:19`); `etl_run_id` FK (`:24`); `lineage_group_id` plain int (`:25`); `address` relationship (`:29`). The integer `address` column from revision 0006 is gone. |
| `models/infrastructure/petroleum_pipelines.py:27` | `geom: Geometry("MULTILINESTRING")`; `etl_run_id` FK; no `address_id` |
| `models/infrastructure/landfills.py` | `InfrastructureLandfills`: `project_id` (str) as the upsert key |
| `models/infrastructure/food_manufacturing_epa.py:7-23` | `InfrastructureFoodManufacturersEPA`: `processing_facility_id` PK, `unique_identifier`, `name`, `address_id` FK |
| `models/infrastructure/__init__.py` | Re-exports (19 lines) |

## Interfaces
- Writers: the 18 loaders in `etl/load/infrastructure/` (see architecture/pipeline-infrastructure-etl-family for the dataset table).
- Readers: data-portal views and webservice (not inspected here).

## Gotchas
- Column names mirror source spreadsheets (e.g. `potw_biosolids_generated`, `class_b_land_app`), so they are not normalised.
- Geocoded tables store the address as `address_id` to `location_address`; line tables (crude oil, petroleum, railways) store `geom` only.
- No shared base class for the 18 dataset tables: primary-key names and types differ (`str` for landfills, `int` for most others).
- Migration 0026 (f8c9353) added the `address_id` and `etl_run_id` foreign keys and dropped older address columns (see bugs/infra-migration-0026-drops-populated-columns).

## History
- `7a41e0e` (PR #112): SQLModel versions of the infrastructure tables; `facility_record` is also here.
- `f66e296` (2026-05-13, PR #344): biodiesel and petroleum models changed.
- f8c9353 (PR #514, 2026-10-22): 18 dataset models added or rewritten with lineage and address FKs; migration 0026.

## Open questions
- Whether `facility_record` is populated by any loader (not checked in this slice).

# Related Concepts
- [Places tables: place (GEOID natural key), location_address, multilinestring](datamodels-places.md): facility_record.location_id points at location_address, which points at place
- [ER diagram: core, places, people, auth and infrastructure tables with verified FKs](datamodels-er-diagram.md): facility_record FKs drawn there
- [System overview (start here)](system-overview.md): hub: facility data domain
- [Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern](pipeline-infrastructure-etl-family.md): the loaders that write these tables
- [Migration 0026 drops source address and city columns from 7 infrastructure tables without copying data](../bugs/infra-migration-0026-drops-populated-columns.md): the migration that changed these tables
