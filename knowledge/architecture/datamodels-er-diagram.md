---
type: Architecture
title: "ER diagram: core, places, people, auth and infrastructure tables with verified FKs"
description: "Mermaid ER diagram of the slice’s tables and foreign keys, each edge tied to its model file:line. Use it to see which tables reference place, contact and etl_run."
tags: [datamodels, er-diagram, foreign-keys, schema]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:00Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/base.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/core/lineage.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/places/location_address.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/places/multilinestring.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/auth/api_key.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/facility_record.py"]
sources: ["commit 7a41e0e", "https://github.com/sustainability-software-lab/ca-biositing/pull/112"]
governance: context
---

## Purpose
Entity-relationship view of the core, places, people, auth and infrastructure tables. Only FKs verified in code (`foreign_key=` in the model files) are drawn. Tables from other domains (`dataset`, `resource`) are stubs.

## Diagram
```mermaid
erDiagram
  etl_run ||--o{ lineage_group : "etl_run_id"
  lineage_group ||--o{ entity_lineage : "lineage_group_id (no FK in code)"
  place ||--o{ location_address : "geography_id -> geoid"
  place ||--o{ location_address : "geography (relationship)"
  api_user ||--o{ api_key : "api_user_id"
  location_address ||--o{ facility_record : "location_id"
  dataset ||--o{ facility_record : "dataset_id"
  resource ||--o{ facility_record : "resource_id"
  dataset ||--o{ multilinestring : "dataset_id"
  etl_run }o..o{ contact : "etl_run_id (BaseEntity, not drawn per table)"
  etl_run }o..o{ provider : "etl_run_id (BaseEntity)"
  etl_run }o..o{ location_address : "etl_run_id (BaseEntity)"
  etl_run }o..o{ multilinestring : "etl_run_id (BaseEntity)"
  etl_run }o..o{ facility_record : "etl_run_id (BaseEntity)"
  place {
    varchar geoid PK
    varchar state_name
    varchar county_name
  }
  location_address {
    int id PK
    varchar geography_id FK
    float lat
    float lon
  }
  multilinestring {
    int id PK
    varchar geoid
    geometry geom
    int dataset_id FK
  }
  contact {
    int id PK
    varchar name
    varchar email
  }
  provider {
    int id PK
    varchar codename
  }
  etl_run {
    int id PK
    varchar run_id
    varchar status
  }
  lineage_group {
    int id PK
    int etl_run_id FK
  }
  entity_lineage {
    int id PK
    int lineage_group_id
    varchar source_table
  }
  api_user {
    int id PK
    varchar username
    varchar hashed_password
  }
  api_key {
    int id PK
    int api_user_id FK
    varchar key_prefix
    varchar key_hash
  }
  facility_record {
    int id PK
    int dataset_id FK
    int location_id FK
    int resource_id FK
  }
  infrastructure_standalone {
    text note "14 tables, no FKs; see infrastructure concept"
  }
  dataset {
    int id PK "external: general_analysis"
  }
  resource {
    int id PK "external: resource_information"
  }
```

## Verified FK list (source of the diagram)
| Child column | Target | Code location |
|---|---|---|
| `base.py` `etl_run_id` (BaseEntity) | `etl_run.id` | `models/base.py:23` |
| `lineage_group.etl_run_id` | `etl_run.id` | `models/core/lineage.py:9` |
| `location_address.geography_id` | `place.geoid` | `models/places/location_address.py:10` |
| `multilinestring.dataset_id` | `dataset.id` | `models/places/multilinestring.py:14` |
| `api_key.api_user_id` | `api_user.id` | `models/auth/api_key.py:29` |
| `facility_record.dataset_id` / `location_id` / `resource_id` | `dataset.id` / `location_address.id` / `resource.id` | `models/infrastructure/facility_record.py:11,13,15` |

Notes: `contact` and `provider` have no FKs of their own; they are only targets. Incoming FKs from other domains: `field_sample` and `experiment` and `prepared_sample` (to contact/provider/location_address), and `usda_census`, `billion_ton`, `resource_availability` (to place). Those are outside this slice.

# Related Concepts
- [Places tables: place (GEOID natural key), location_address, multilinestring](datamodels-places.md): diagram details place and location_address
- [Infrastructure tables (infrastructure_* facility datasets, facility_record)](datamodels-infrastructure.md): facility_record edges and standalone infra tables
- [System overview (start here)](system-overview.md): hub: schema overview
