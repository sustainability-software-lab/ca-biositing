---
type: Architecture
title: "Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern"
description: "Eighteen infrastructure flows (merged in f8c9353, PR #514) share one extract/transform/load shape; 15 are geocoded via a Google Sheet and 3 are GeoJSON lines."
tags: [pipeline, etl, infrastructure, prefect, google-drive, geocoding, postgis]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:26:54Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/railways.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/food_processing_facilities.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/infrastructure/", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gdrive_to_pandas.py", "resources/prefect/run_prefect_flow.py", "alembic/versions/0026_add_food_processing_infrastructure_datasets.py", "src/ca_biositing/pipeline/tests/test_infrastructure_etl.py", "src/ca_biositing/pipeline/tests/test_infrastructure_duplicate_prevention.py"]
sources: ["commit f8c9353", "https://github.com/sustainability-software-lab/ca-biositing/pull/514", "https://github.com/sustainability-software-lab/ca-biositing/pull/482", "https://github.com/sustainability-software-lab/ca-biositing/issues/534", "commit fa8583a"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
The 18 infrastructure datasets (biodiesel plants, landfills, wastewater plants, food manufacturers, pipelines, railways and others) are one ETL family. Each dataset has its own flow, extract, transform, load and SQLModel table, built from the same template. Commit f8c9353 (PR #514, merged 2026-10-22) added the family and registered all 18 flows in the master runner. The first attempt, PR #482, is still open and is superseded (see facts/pr-482).

## Key files
| Path | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/flows/` | One `<dataset>.py` per dataset, each defining `<dataset>_flow` (e.g. `railways.py:8`) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/` | One extractor per dataset; each calls `gdrive_to_df` (e.g. `railways.py:25`) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/` | One transform per dataset, all with the same 6-step shape |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/infrastructure/` | One `load` task per dataset (`landfills.py:12`, `food_manufacturers_epa.py:29-80`) |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/` | 19 table models (18 dataset tables plus `facility_record`) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gdrive_to_pandas.py:15` | `gdrive_to_df`, the in-memory Drive reader used by every extractor |
| `resources/prefect/run_prefect_flow.py:27-45` | The 18 infrastructure entries in `AVAILABLE_FLOWS` |
| `alembic/versions/0026_add_food_processing_infrastructure_datasets.py` | Schema change for the family (see bugs/infra-migration-0026-drops-populated-columns) |
| `src/ca_biositing/pipeline/tests/test_infrastructure_etl.py` | Import, signature, empty-input tests for all 18 datasets |
| `src/ca_biositing/pipeline/tests/test_infrastructure_duplicate_prevention.py` | Re-run tests: a second load must leave one row (`:153`, `:231`, `:296`) |

## Dataset table
Geocoded means the flow also reads the `address-to-geocoded` Google Sheet (via `create_extractor`, e.g. `food_processing_facilities.py:52`). Lines have no geocoding.

| Flow module | Drive source file (extract) | Geocoded worksheet | Model class | Load upsert key |
|---|---|---|---|---|
| biodiesel_plants | Biodiesel_Plants.csv | Biodiesel Plants | InfrastructureBiodieselPlants | biodiesel_plant_id |
| biosolids_facilities | Biosolids_Facilities.csv | Biosolids Facilities | InfrastructureBiosolidsFacilities | biosolid_facility_id |
| cafo_manure_locations | CAFO_Locations_and_Manure_Production.csv | CAFO Locations | InfrastructureCafoManureLocations | cafo_manure_id |
| combustion_plants | CA_comb_points.zip | Combustion Plants | InfrastructureCombustionPlants | combustion_fid |
| crude_oil_pipelines | US_Crude_Oil_Pipelines.geojson | none (line) | InfrastructureCrudeOilPipelines | object_id |
| district_energy_systems | CA_des_points.zip | District Energy Systems | InfrastructureDistrictEnergySystems | des_fid |
| ethanol_biorefineries | Ethanol_Biorefineries.csv | Ethanol Biorefineries | InfrastructureEthanolBiorefineries | ethanol_biorefinery_id |
| food_manufacturers_carb | food_manufacturers_and_processor_facilities_carb.csv | Food Manufacturers - CARB | InfrastructureFoodManufacturersCARB (`food_manufacturing_carb.py`) | processing_facility_id |
| food_manufacturers_epa | food_manufacturers_and_processors_epa.csv | Food Manufacturers - EPA | InfrastructureFoodManufacturersEPA (`food_manufacturing_epa.py`) | processing_facility_id, never populated (see bugs/infra-epa-upsert-conflict-key-unset) |
| food_processing_facilities | CA_proc_points.zip | Food Processor Facilities | InfrastructureFoodProcessingFacilities | processing_facility_id |
| landfills | Landfills.csv | Landfills | InfrastructureLandfills | project_id |
| livestock_anaerobic_digesters | Livestock_Anaerobic_Digesters.csv | Livestock Anaerobic Digesters | InfrastructureLivestockAnaerobicDigesters | digester_id |
| msw_to_energy_anaerobic_digesters | CA_wte_points.zip | California Anaerobic Digestion Projects | InfrastructureMswToEnergyAnaerobicDigesters | wte_id |
| petroleum_pipelines | US_Petroleum_Pipelines.geojson | none (line) | InfrastructurePetroleumPipelines | object_id |
| railways | US_Railways.geojson | none (line) | InfrastructureRailways | object_id |
| saf_and_renewable_diesel_plants | saf_and_renewable_diesel_plants.csv | SAF and Renewable Diesel Plants | InfrastructureSafAndRenewableDieselPlants | ibcc_index |
| tomato_processors | tomato_processors_ca.csv | Tomato Processors | InfrastructureTomatoProcessors | processing_facility_id |
| wastewater_treatment_plants | Wastewater_Treatment_Plants.csv | Wastewater Treatment Plants | InfrastructureWastewaterTreatmentPlants | plant_id |

Each flow is named `<module>_flow` and the registry key equals the module name. The 15 geocoded flows are described in architecture/pipeline-infrastructure-geocoded-datasets; the 3 line flows in architecture/pipeline-infrastructure-line-datasets.

## How it works
1. Flow start: `create_etl_run_record.fn` and `create_lineage_group.fn` with note `Infrastructure/<name> Data` (e.g. `railways.py:17-19`).
2. Extract: `gdrive_to_df(FILE_NAME, MIME_TYPE, credentials_path, dataset_folder)` finds the file by exact title and MIME type and parses it in memory. ZIPs must hold one CSV with the same stem. Geocoded flows also return a callable that reads the geocoded worksheet.
3. Transform: `standard_clean`, `coerce_columns`, left-merge the geocoded sheet on `MERGE_COLUMNS` (e.g. `landfills.py:21`, `:111`), `normalize_dataframes`, rename, then bridge to `Place` and `LocationAddress` (see the geocoded concept), then select the final columns (`landfills.py:202-209`).
4. Load: one `Session` on one connection; per row, a select on a natural key, then either an ORM update or an `insert ... on_conflict_do_update`; one `session.commit()` at the end (`food_manufacturers_epa.py:38-74`).
5. Return: the flow returns True or False and never raises. Empty extract, transform or load returns False. `master_flow` catches exceptions per sub-flow (`run_prefect_flow.py:63-92`).

## Interfaces
- Input: Google Drive files named in the table, via the service account at `CREDENTIALS_PATH` (default `credentials.json`), plus the `address-to-geocoded` Google Sheet for geocoded datasets.
- Output: 19 tables under `infrastructure_*`, `location_address` and `place` rows, and `etl_run` and `lineage_group` rows.
- Callers: `master_flow` (`resources/prefect/run_prefect_flow.py`) and `pixi run run-single-flow <module>`.

## Gotchas
- The `temp_external_datasets/` folder is gone (see architecture/flow-temp-external-datasets). Every extractor still passes that folder path, but `gdrive_to_df` no longer writes files, so the argument is unused.
- The Drive file must be shared with the service account, or `gdrive_to_df` returns None and the flow stops at extract (`gdrive_to_pandas.py:15-100`, error text at `FileNotFoundError`).
- Several transforms return the unselected frame on `KeyError` instead of failing: 18 infrastructure transforms have `except KeyError` returning `normalized_df` or `combined_df` (see bugs/transform-broken-filters).
- The load step has no batching: 18 loaders each commit once at the end (see bugs/infra-load-unbatched-session-oom, issue #534).
- The transform writes to the database (`session.commit()` at `landfills.py:189`) before load runs, so a failed load leaves new `place` and `location_address` rows.
- Loader duplicate prevention relies on a natural-key select, not on the upsert; see requirements/infra-loader-idempotent-rerun.

## History
- f8c9353 (PR #514, merged 2026-10-22): second attempt; adds the family, 19 models, migration 0026, tests, and the registry entries. Biodiesel was re-enabled in the registry here (it had been commented out in fa8583a, PR #380).
- PR #482 (open, created 2026-09-13): first attempt on branch `avi_infrastructure_etl`, see facts/pr-482.
- Issue #534 (open, 2026-10-22): EPA food manufacturers load OOM.

## Open questions
- Whether the `address-to-geocoded` worksheets are refreshed by a separate process (not in this commit; inferred from the PR #482 description).
- Whether the lat/lon key merging co-located facilities is intended (inferred; no requirement recorded).

# Related Concepts
- [How a pipeline flow wires extract, transform, and load](pipeline-flow-wiring.md): the extract/transform/load/flow layering this family follows
- [How flows are registered and run (master flow, run-single-flow, list-flows)](pipeline-flow-registry-and-run.md): where the 18 infrastructure flows are registered
- [Load task upsert patterns (on_conflict, natural key, bulk)](pipeline-load-upsert-patterns.md): load style these loaders use (select then upsert, one commit)
- [Google Sheets extraction: factory, gsheet_to_df, and retries](pipeline-gsheet-extraction.md): create_extractor reads the address-to-geocoded sheet
- [ETL run and lineage group tracking](pipeline-lineage-tracking.md): each flow creates an EtlRun and LineageGroup first
- [Infrastructure tables (infrastructure_* facility datasets, facility_record)](datamodels-infrastructure.md): the 19 target tables
- [Places tables: place (GEOID natural key), location_address, multilinestring](datamodels-places.md): Place and LocationAddress rows created by the address bridging
- [Test suite layout, how to run each suite, and fixture map](testing.md): test suites that cover the family
- [Biodiesel Plants ETL flow (Drive CSV with geocoding)](flow-biodiesel-plants.md): one member of the family, with its own history
- [temp_external_datasets folder: staged external geospatial/CSV inputs](flow-temp-external-datasets.md): the removed staging folder that the family used to read from
- [Import models and settings inside task or flow bodies](../requirements/pipeline-lazy-model-and-settings-imports.md): loaders and transforms import models inside function bodies
- [DB tests use SQLite in-memory with selected tables, not Postgres or testcontainers](../decisions/testing-sqlite-in-memory-fixtures.md): duplicate-prevention tests run on the SQLite fixture
- [PR #482 (open, conflicting): Infrastructure ETL pipelines (18 datasets) with geocoding](../facts/pr-482.md): the superseded first attempt
