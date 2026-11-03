---
type: Architecture
title: "Resource information: biomass resource, residue factors, availability, prices, end uses"
description: "The resource table is the feedstock identity; siblings hold residue factors, availability windows, production, price, storage, transport, end use and counterfactual data."
tags: [datamodels, resource, feedstock, residue, availability, pricing]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:06Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/*.py"]
sources: ["commit a9a86eb", "commit 7a41e0e", "commit 99cbfcd", "commit d961724", "commit bd0ec5e", "https://github.com/sustainability-software-lab/ca-biositing/pull/84", "https://github.com/sustainability-software-lab/ca-biositing/pull/258", "https://github.com/sustainability-software-lab/ca-biositing/pull/288", "https://github.com/sustainability-software-lab/ca-biositing/pull/371", "docs/architecture.md", "docs/datamodels/CONTRIBUTING.md"]
governance: context
---

## Purpose
Defines what a biomass feedstock ’resource’ is (crop residue, orchard prunings, almond shells and similar) and attaches supply-side facts: residue yield factors, seasonal availability, production, price, storage, transport, end uses, and the counterfactual disposal pathway.

## Key files
| Path:line | Role |
|---|---|
| models/resource_information/resource.py:18 | `resource`: name, primary_ag_product_id, resource_class_id, resource_subclass_id, resource_code, description, uri |
| resource.py:35 / :40 | `resource_subclass`, `resource_class` (LookupBase hierarchy) |
| resource.py:7 | `resource_morphology`: resource_id, morphology_uri (plain SQLModel, own id) |
| resource_information/primary_ag_product.py | `primary_ag_product` (LookupBase): agricultural product, e.g. almond |
| resource_information/residue_factor.py:14 | `residue_factor`: resource_id (NOT NULL), factor_type, factor_min/mid/max, prune_trim_yield and unit. Unique (resource_id, factor_type) for UPSERT |
| resource_information/resource_availability.py | `resource_availability`: resource_id, geoid, from_month/to_month, year_round, residue factors per acre (dry/wet) |
| resource_information/resource_counterfactual.py | `resource_counterfactual`: per-county percent split of current disposal (bedding, feed, bioelectricity, burn, compost, landfill) with source ids |
| resource_information/resource_production_record.py | `resource_production_record`: dataset_id, geoid, primary_ag_product_id, resource_id, report_date, scenario |
| resource_information/resource_price_record.py | `resource_price_record`: dataset_id, geoid, resource_id, source_id, report_start/end_date, freight_terms, transport_mode |
| resource_information/resource_storage_record.py | `resource_storage_record`: storage_description (required), dataset_id, method_id |
| resource_information/resource_transport_record.py | `resource_transport_record`: transport_description (required), dataset_id, method_id |
| resource_information/resource_end_use_record.py | `resource_end_use_record`: dataset_id, method_id, use_case_id (FK use_case) |
| resource_information/use_case.py | `use_case` (LookupBase) |
| resource_information/resource_image.py | `resource_image`: resource_id, image_url, sort_order. Unique (resource_name, image_url, sort_order), nulls not distinct |

Tables: resource, resource_class, resource_subclass, resource_morphology, primary_ag_product, residue_factor, resource_availability, resource_counterfactual, resource_production_record, resource_price_record, resource_storage_record, resource_transport_record, resource_end_use_record, use_case, resource_image (15 tables).

## How it works
`resource` is the hub. Field samples, Aim 1/Aim 2 records, LandIQ and USDA mappings, and Billion Ton records all FK to it. The `*_record` supply tables are one row per (dataset, place, product) observation and carry dataset_id and method_id to say where a number came from. Most of them leave resource_id unconstrained (see the FK decision).

## Interfaces
- Readers: data_portal views (mv_biomass_search, mv_biomass_availability, mv_biomass_pricing, mv_biomass_end_uses) and webservice feedstock endpoints (docs/architecture.md).
- Writers: resource ETL flows in the pipeline slice.

## Gotchas
- residue_factor.resource_id is NOT NULL and enforced by FK; resource_price_record.resource_id is not.
- resource_end_use_record.use_case_id is FK-constrained, while the other end-use style fields are not.
- docs/architecture.md and docs/datamodels/CONTRIBUTING.md list `Strain` under resource_information. It is actually in aim2_records/strain.py.
- resource_morphology has its own integer id and no BaseEntity fields (no lineage).

## History
- residue_factor: 99cbfcd (PR #288, Residue Factor ETL). resource_image: introduced in bd0ec5e (PR #260, verified with git log -S).
- resource_price_record and resource_end_use_record: d961724 (PR #258), the same commit that first added the commented-out FK comments.
- resource_image unique key fix: bd0a35c (PR #371, ’Resource image fix’).

## Open questions
- resource_counterfactual has no ETL references at e41d00d (inferred from class-name grep; confirm).
- Whether resource_storage_record and resource_transport_record should FK to resource (they are unconstrained today).

# Related Concepts
- [Sample chain: field samples, collection and storage, then prepared samples and preparation methods](datamodels-sample-chain.md): field_sample.resource_id and prepared samples tie physical samples back to the resource
- [External data: LandIQ crop map, USDA census and survey and market, Billion Ton, county ag reports](datamodels-external-data.md): LandIQ, USDA and Billion Ton tables map their crops onto resource and primary_ag_product
- [General analysis: observation (long-format measurements), dataset, analysis type, dimension type](datamodels-general-analysis.md): Supply quantities and prices are also expressed as observation rows in some pipelines
- [Domain terms as used in the datamodels: resource, field sample, prepared sample, analysis record, observation, parameter, unit, method, dataset](../facts/domain-core-terms.md): Defines resource, residue factor and availability as used in this codebase
- [Places tables: place (GEOID natural key), location_address, multilinestring](datamodels-places.md): Most supply records are keyed by geoid (county) from the places slice
- [System overview (start here)](system-overview.md): Hub for the overall datamodels to ETL to API picture
