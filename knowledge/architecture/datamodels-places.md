---
type: Architecture
title: "Places tables: place (GEOID natural key), location_address, multilinestring"
description: place uses geoid as its PK and is the FK target for geography columns across domains; location_address must reference an existing place.
tags: [datamodels, geography, geoid, places, postgis]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:26:57Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/places/place.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/places/location_address.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/places/multilinestring.py"]
sources: ["commit 7a41e0e", "commit db578ad", "https://github.com/sustainability-software-lab/ca-biositing/pull/112", "https://github.com/sustainability-software-lab/ca-biositing/pull/340"]
governance: context
---

## Purpose
Geographic reference data. `place` is the county/state key (Census GEOID) that many external-data and resource tables join on.

## Key files
| Path:line | Role |
|---|---|
| `models/places/place.py:5` | `Place` table `place`: PK `geoid` (str, natural key), `state_name`, `state_fips`, `county_name`, `county_fips`, `region_name`, `agg_level_desc`. Not a `BaseEntity`. |
| `models/places/location_address.py:7` | `LocationAddress(BaseEntity)` table `location_address`: `geography_id` FK `place.geoid` (`:10`), address lines, `city`, `zip`, `lat`, `lon`, `is_anonymous`; `geography` relationship |
| `models/places/multilinestring.py:9` | `MultiLineString(BaseEntity)` table `multilinestring`: `geoid` (str, no FK), `geom` Geometry (`:13`, `spatial_index=False`), `dataset_id` FK `dataset.id`; `dataset` relationship |

## Interfaces
- `place.geoid` is referenced by: `external_data/usda_census.py:25`, `external_data/usda_survey.py:65`, `external_data/billion_ton.py:17`, `external_data/county_ag_report_record.py:10`, `resource_information/resource_availability.py:11`, `resource_information/resource_counterfactual.py:11`.
- `location_address.id` is referenced by `field_sampling/field_sample.py:19,23,28`, `field_sampling/soil.py:15`, `experiment_equipment/experiment.py:17`, `experiment_equipment/equipment.py:9`, `external_data/usda_survey.py:16`, `infrastructure/facility_record.py:13`.
- Writers: pipeline loaders under `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/places.py` and `.../load/location_address.py` (not read in full for this note).

## Gotchas
- Inserting a `location_address` whose `geography_id` is not in `place` raises an FK violation. Commit `db578ad` (PR #340) fixed this by pre-creating `Place` rows in the load step, including a fallback geoid `06000`.
- `Place` has no `id` and no ETL columns; it cannot be reached through `BaseEntity` helpers.
- `multilinestring.geoid` is a plain string with no FK to `place`.
- `spatial_index=False` on `MultiLineString.geom`: whether a GiST index exists in the DB is not verified here (check the migration history).

## History
- `7a41e0e` (PR #112): SQLModel versions of these tables.
- `db578ad` (PR #340, 2026-05-08): ensure Place records exist before LocationAddress/FieldSample inserts.

## Open questions
- Where the spatial index on `multilinestring.geom` is defined, if anywhere.

# Related Concepts
- [Datamodels base mixins (BaseEntity, LookupBase, Aim1/Aim2RecordBase)](datamodels-base.md): location_address and multilinestring inherit BaseEntity
- [ER diagram: core, places, people, auth and infrastructure tables with verified FKs](datamodels-er-diagram.md): FK edges drawn there
- [System overview (start here)](system-overview.md): hub: geography as a shared key
