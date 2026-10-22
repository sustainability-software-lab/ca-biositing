---
type: Architecture
title: "Sample chain: field samples, collection and storage, then prepared samples and preparation methods"
description: field_sample is the collected physical sample; prepared_sample is its processed derivative. Each has method lookups and condition or characteristic side tables.
tags: [datamodels, field-sampling, sample-preparation, provenance]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:07Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/field_sampling/*.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/sample_preparation/*.py"]
sources: ["commit a9a86eb", "commit 7a41e0e", "commit bd0ec5e", "https://github.com/sustainability-software-lab/ca-biositing/pull/84", "https://github.com/sustainability-software-lab/ca-biositing/pull/260", "docs/pipeline/USDA/ANALYTICS_HANDOFF.md", "docs/architecture.md"]
governance: context
---

## Purpose
Models the physical chain of custody for feedstock material: a collected field sample (where, when, how, by whom, with what condition), then the prepared sample derived from it (drying, grinding, sieving), which is what analysis records measure.

## Key files
| Path:line | Role |
|---|---|
| field_sampling/field_sample.py:9 | `field_sample`: name, resource_id, provider_id, collector_id, amount_collected (+unit), sampling_location_id, field_storage_method_id, field_storage_duration (+unit), field_storage_location_id, collection_timestamp, collection_method_id, harvest_method_id, harvest_date, field_sample_storage_location_id |
| field_sampling/field_sample_condition.py:8 | `field_sample_condition`: field_sample_id, ag_treatment_id, last_application_date, treatment_amount_per_acre, processing_method_id |
| field_sampling/physical_characteristic.py | `physical_characteristic`: field_sample_id, particle length/width/height (Decimal) and particle_unit_id |
| field_sampling/soil.py | `soil_type` (LookupBase) and `location_soil_type` (location_id, soil_type_id) |
| field_sampling/ag_treatment.py, collection_method.py, harvest_method.py, field_storage_method.py, processing_method.py | LookupBase method and treatment vocabularies |
| sample_preparation/prepared_sample.py:8 | `prepared_sample`: name, field_sample_id, prep_method_id, prep_date, preparer_id (contact), note |
| sample_preparation/preparation_method.py:8 | `preparation_method`: name, description, prep_method_abbrev_id, prep_temp_c, uri, drying_step (bool) |
| sample_preparation/preparation_method.py:22 | `preparation_method_abbreviation` (LookupBase) |

Tables: field_sample, field_sample_condition, physical_characteristic, soil_type, location_soil_type, ag_treatment, collection_method, harvest_method, field_storage_method, processing_method, prepared_sample, preparation_method, preparation_method_abbreviation (13 tables).

## How it works
```
resource --> field_sample --> prepared_sample --> analysis record (Aim1 / Aim2 prepared_sample_id)
               |-- field_sample_condition (ag treatment, processing)
               |-- physical_characteristic (particle size)
```
prepared_sample.field_sample_id links the chain. Aim 1 and Aim 2 records carry prepared_sample_id (see Aim1RecordBase in base.py:39). Pretreatment_setup holds prepared sample ids as a JSON list instead of an FK.

## Interfaces
- Writers: field sample ETL in the pipeline (flows/field_sample_etl.py, transform/field_sampling/field_sample*.py).
- Readers: mv_biomass_sample_stats and the analysis views (sample counts and suppliers).

## Gotchas
- field_sample has several FKs to unit and location_address (amount_collected_unit_id, field_storage_duration_unit_id, sampling_location_id, field_storage_location_id, field_sample_storage_location_id). Its Relationship() entries need explicit foreign_keys hints, which the model provides.
- Several sample tables (field_sample_condition, physical_characteristic, soil_type, location_soil_type, ag_treatment, collection_method, harvest_method, processing_method, field_storage_method) have no ETL or view references at e41d00d; see facts/domain-models-usage-snapshot.

## History
- field_sample_condition, physical_characteristic and preparation_method: introduced in a9a86eb (PR #84, Berkeley Upstream integration, verified with git log -S). 7a41e0e (PR #112) is the SQLModel migration.
- The ANALYTICS_HANDOFF doc (docs/pipeline/USDA/ANALYTICS_HANDOFF.md) describes the same chain and is dated February 2026.

## Open questions
- Whether physical_characteristic should be populated from sample_desc particle dimensions (the extract comments say so, but no ETL writes it, inferred; confirm in pipeline etl/extract/sample_desc.py).

# Related Concepts
- [Resource information: biomass resource, residue factors, availability, prices, end uses](datamodels-resource-information.md): field_sample.resource_id links each collected sample to the feedstock resource
- [Aim 1 analytical record tables (proximate, ultimate, XRF, ICP, etc.)](datamodels-aim1-records.md): Analysis records reference prepared_sample_id
- [Aim 2 processing and conversion tables (pretreatment, fermentation, gasification)](datamodels-aim2-records.md): Aim 2 pretreatment_setup stores prepared sample ids as JSON
- [Core ETL run and lineage tables (etl_run, lineage_group, entity_lineage)](datamodels-core.md): Contact (collector, preparer, analyst) and provider FKs point into core people tables (slice 02)
- [Domain terms as used in the datamodels: resource, field sample, prepared sample, analysis record, observation, parameter, unit, method, dataset](../facts/domain-core-terms.md): Defines field sample versus prepared sample
- [System overview (start here)](system-overview.md): Hub for the ETL-to-database-to-API flow
