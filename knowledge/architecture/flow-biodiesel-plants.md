---
type: Architecture
title: Biodiesel Plants ETL flow (Drive CSV with geocoding)
description: "Biodiesel plants ETL flow: Drive CSV read in memory, geocoded via the address-to-geocoded sheet, loaded to infrastructure_biodiesel_plants; registered in the master runner again since #514."
tags: [pipeline, etl, prefect, flow, biodiesel, infrastructure, geocoding, google-drive]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:30Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/biodiesel_plants.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/biodiesel_plants.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/biodiesel_plants.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/infrastructure/biodiesel_plants.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/geo_utils.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gdrive_to_pandas.py", "resources/prefect/run_prefect_flow.py"]
stale_after: "2026-12-31"
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/344", "https://github.com/sustainability-software-lab/ca-biositing/pull/380", "commit f66e296", "commit fa8583a", "resources/prefect/run_prefect_flow.py", "commit f8c9353", "https://github.com/sustainability-software-lab/ca-biositing/pull/514"]
---

## Purpose
Loads biodiesel plant records into `InfrastructureBiodieselPlants`, linking each plant to a `LocationAddress` and `Place` (county) through the geocoded merge. Entry point `biodiesel_plants_flow` (`flows/biodiesel_plants.py:8`) returns True on success and False on failure, and does not raise.

## Source
Google Drive file `Biodiesel_Plants.csv` (MIME `text/csv`), found by exact title. `gdrive_to_df` parses it in memory (`utils/gdrive_to_pandas.py`). Nothing is written to disk any more. The old copy in `temp_external_datasets/` was removed in f8c9353.

## Key files
| path:line | role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/flows/biodiesel_plants.py:8` | `@flow` "Biodiesel Plants ETL", step logging, returns bool; calls `extract()` then `geocoded_extractor()` (`:29-33`) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/biodiesel_plants.py:28` | `FILE_NAME = "Biodiesel_Plants.csv"`; also `create_extractor("address-to-geocoded", "Biodiesel Plants")` |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/biodiesel_plants.py:105`, `:151-153` | Geocoded merge; lat/lon `and_` lookup for `LocationAddress` |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/biodiesel_plants.py:212-234` | Final column select; `except KeyError` returns `normalized_df` unfiltered (`:234`) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/infrastructure/biodiesel_plants.py:79` | Load; upsert on `biodiesel_plant_id` |
| `resources/prefect/run_prefect_flow.py:30` | Registry entry `biodiesel_plants` (re-enabled in f8c9353) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/geo_utils.py:64` | `parse_addresses` is imported at `transform/infrastructure/biodiesel_plants.py:10` but not called |

## How it works
1. Lineage: `create_etl_run_record.fn` and `create_lineage_group.fn` with note `Infrastructure/Biodiesel Plant Data` (`flows/biodiesel_plants.py:20-22`).
2. Extract: raw frame and a geocoded-sheet reader. Empty raw data returns False.
3. Transform: standard clean, merge with the geocoded sheet, bridge to `Place` and `LocationAddress`, select final columns.
4. Load: upsert by `biodiesel_plant_id`; `address_id` links to `location_address`.

## Interfaces
- Input: Drive file above; `CREDENTIALS_PATH`; the `address-to-geocoded` Google Sheet (worksheet "Biodiesel Plants").
- Output: `infrastructure_biodiesel_plants`, `location_address`, `place`, `etl_run`, `lineage_group`.
- Callers: `master_flow` (registry entry, runs in dict order after `thermochem`), and `pixi run run-single-flow biodiesel_plants`.

## Gotchas
- The GOOGLE_MAPS_API_KEY and GoogleV3 notes from earlier versions no longer apply to this flow: geocoding happens in the separate sheet, not in the transform.
- The `TODO` comments on the rename and final select from earlier versions are gone; `rename_columns` is not used here, and the final select lists 14 columns.
- The `KeyError` fallback at `transform/infrastructure/biodiesel_plants.py:234` returns the unselected frame (see bugs/transform-broken-filters).
- The transform writes `Place` and `LocationAddress` rows before load (`session.commit()` at `:188`).
- Migration 0026 replaced the integer `address` column with `address_id` (see bugs/biodiesel-address-type-change).

## History
- f66e296 (2026-05-13, PR #344): flow added.
- fa8583a (2026-05-26, PR #380): flow commented out in the master runner.
- f8c9353 (2026-10-22, PR #514): load moved to `etl/load/infrastructure/`, geocoded sheet added, flow re-enabled in the master runner, and the Drive file read in memory.

## Open questions
- Whether the address-to-geocoded "Biodiesel Plants" worksheet is current (not checked).

# Related Concepts
- [Geography ETL flow (CA counties to Place)](flow-geography.md): Uses Place rows and county GEOIDs that the geography flow maintains.
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Shares the geocoding utilities and lineage pattern described there.
- [System overview (start here)](system-overview.md): Infrastructure layer of the data model (biodiesel plants as facilities).
- [Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern](pipeline-infrastructure-etl-family.md): the family this flow is one member of
- [Infrastructure geocoded datasets: Google Sheet merge and Place/LocationAddress bridging](pipeline-infrastructure-geocoded-datasets.md): the geocoded merge and bridging this flow uses
