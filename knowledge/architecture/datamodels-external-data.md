---
type: Architecture
title: "External data: LandIQ crop map, USDA census and survey and market, Billion Ton, county ag reports"
description: "Imported public datasets, each with its own record table, plus crop and commodity mapping tables that tie them to resource and primary_ag_product."
tags: [datamodels, external-data, usda, landiq, billion-ton, geospatial]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:08Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/external_data/*.py"]
sources: ["commit 447162c", "commit 3918d29", "commit a9a86eb", "commit 7a41e0e", "commit bd0ec5e", "https://github.com/sustainability-software-lab/ca-biositing/pull/84", "https://github.com/sustainability-software-lab/ca-biositing/pull/112", "https://github.com/sustainability-software-lab/ca-biositing/pull/121", "https://github.com/sustainability-software-lab/ca-biositing/pull/124", "docs/datamodels/SCHEMA_DRIFT.md", "docs/data_dictionary.md"]
governance: context
---

## Purpose
Stores third-party datasets as they arrive: LandIQ parcel-level crop mapping, USDA NASS census and survey statistics, USDA market reports, DOE Billion Ton 2023 county projections, county agricultural reports, and polygon geometries. The mapping tables translate source crop names onto this project’s resource and primary_ag_product lookups.

## Key files
| Path:line | Role |
|---|---|
| external_data/landiq_record.py:7 | `landiq_record`: record_id (unique), dataset_id, polygon_id, main/secondary/tertiary/quaternary crop (each FK primary_ag_product), confidence, irrigated, acres, county, version, pct1-4 |
| external_data/landiq_resource_mapping.py:7 | `landiq_resource_mapping`: landiq_crop_name (int FK to primary_ag_product), resource_id |
| external_data/polygon.py:9 | `polygon`: geoid, geom (PostGIS geometry), dataset_id. Unique index on md5(geom::text), dataset_id |
| external_data/usda_census.py:7 | `usda_commodity` (LookupBase, parent_commodity self-FK), `usda_census_record` (:21), `usda_domain` (:37), `usda_statistic_category` (:42) |
| external_data/usda_survey.py:8 | `usda_market_report`, `usda_market_record` (:25), `usda_survey_program` (:56), `usda_survey_record` (:61), `usda_term_map` (:83) |
| external_data/billion_ton.py:11 | `billion_ton2023_record`: dataset_id, subclass_id, resource_id, geoid, county_square_miles, model_name, scenario_name, price_offered_usd, production, production_unit_id, btu_ton, production_energy_content, energy_content_unit_id, product_density_dtpersqmi, land_source |
| external_data/county_ag_report_record.py:6 | `county_ag_report_record`: record_id (unique), geoid, primary_ag_product_id, data_year, data_source_id, produced_nsjv, processed_nsjv |
| external_data/resource_usda_commodity_map.py:7 | `resource_usda_commodity_map`: resource_id, primary_ag_product_id, usda_commodity_id, match_tier |

Tables: landiq_record, landiq_resource_mapping, polygon, usda_commodity, usda_census_record, usda_domain, usda_statistic_category, usda_market_report, usda_market_record, usda_survey_program, usda_survey_record, usda_term_map, billion_ton2023_record, county_ag_report_record, resource_usda_commodity_map (15 tables).

## How it works
Each external record table FKs to `dataset` (the import batch, see general_analysis) and to `place.geoid` for county-level data. Crop and commodity names are resolved through mapping tables (resource_usda_commodity_map with match_tier, usda_term_map with is_verified). Census and survey counts are also expanded into observation rows keyed by record_type ’usda_census_record’ or similar (inferred from mv_biomass_volume_estimate.py filters).

## Interfaces
- Writers: USDA, LandIQ, Billion Ton and county ETL flows in the pipeline (pipeline slice).
- Readers: mv_biomass_county_production, mv_biomass_volume_estimate, mv_usda_county_production, mv_billion_ton_county_production (views.py / data_portal_views/).

## Gotchas
- Views that surface raw government data deliberately apply no QC or blacklist filters (documented in datamodels README, Data-Quality Filters section).
- landiq_resource_mapping.landiq_crop_name is an int FK to primary_ag_product despite the ’name’ in its column name.
- usda_market_record.class_ uses a trailing underscore to avoid the Python keyword.
- usda_market_record.market_type_id and market_category_id have no FKs.
- usda_term_map.is_verified is nullable, so ’unverified’ and ’unknown’ look the same.

## History
- Billion Ton 2023 ETL: 447162c (PR #121). USDA manual fix: 3918d29 (PR #124).
- Polygon: introduced in a9a86eb (PR #84, verified with git log -S). Moved to native PostGIS geometry and GIST index in 7a41e0e; see docs/datamodels/SCHEMA_DRIFT.md section 4.
- county_ag_report_record: introduced in bd0ec5e (PR #260, verified with git log -S).

## Open questions
- Whether usda_market_record and usda_survey_program should FK to dataset/geoid consistently (inferred drift; confirm with the USDA ETL owners).

# Related Concepts
- [Data source and file metadata: provenance for datasets, files and locations](datamodels-data-sources-metadata.md): Every external import points to a data_source and file_object_metadata row for provenance
- [General analysis: observation (long-format measurements), dataset, analysis type, dimension type](datamodels-general-analysis.md): Dataset grouping and observation rows for census and county records
- [Resource information: biomass resource, residue factors, availability, prices, end uses](datamodels-resource-information.md): Resource-to-commodity and LandIQ crop mappings tie external crops to resources
- [Places tables: place (GEOID natural key), location_address, multilinestring](datamodels-places.md): geoid FKs point into place (county FIPS)
- [System overview (start here)](system-overview.md): Hub for the ETL-to-database-to-API flow
