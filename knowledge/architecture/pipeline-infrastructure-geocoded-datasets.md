---
type: Architecture
title: "Infrastructure geocoded datasets: Google Sheet merge and Place/LocationAddress bridging"
description: "The 15 geocoded infrastructure flows left-merge a pre-geocoded Google Sheet, then get-or-create Place and LocationAddress rows keyed on geoid and lat/lon inside the transform."
tags: [pipeline, infrastructure, geocoding, location-address, place, google-sheets]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:26:55Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/factory.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/landfills.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/biodiesel_plants.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/food_manufacturers_epa.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/food_processing_facilities.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/geo_utils.py"]
sources: ["commit f8c9353", "https://github.com/sustainability-software-lab/ca-biositing/pull/482", "https://github.com/sustainability-software-lab/ca-biositing/pull/514"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Fifteen of the 18 infrastructure datasets carry street addresses, not coordinates. Their flows read the raw file from Drive and a geocoded copy from the `address-to-geocoded` Google Sheet. The transform merges the two and creates the normalised `place` and `location_address` rows that `address_id` points to. Geocoding itself is not done in this code path.

## Key files
| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/factory.py` | `create_extractor(GSHEET_NAME, WORKSHEET_NAME)`, used by each geocoded extractor (e.g. `food_processing_facilities.py:52`) |
| `etl/transform/infrastructure/landfills.py:21` | `MERGE_COLUMNS` for the geocoded join (dataset-specific list in each file) |
| `etl/transform/infrastructure/landfills.py:22` | `geocoded_columns`: `geocoded_status`, `closest_*` address, lat/lon, geoid, state and county fields |
| `etl/transform/infrastructure/landfills.py:111` | Left merge of the raw frame with the geocoded frame |
| `etl/transform/infrastructure/landfills.py:131-192` | Bridge: `Place` by geoid, `LocationAddress` by lat/lon, `session.commit()` at `:189` |
| `etl/transform/infrastructure/landfills.py:153-155` | Address lookup: `and_(LocationAddress.lat == lat, LocationAddress.lon == lon)` |
| `etl/transform/infrastructure/biodiesel_plants.py:151-153` | Same lookup in biodiesel; `and_` used in all 15 geocoded transforms |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/geo_utils.py:64` | `parse_addresses` (GoogleV3 path). Imported by the geocoded transforms but not called in `etl/transform/infrastructure/` |

## How it works
1. Extract: raw frame from Drive, and a callable that reads the geocoded worksheet. `flows/food_processing_facilities.py:25-29` calls the callable inside the flow.
2. Merge: `pd.merge(combined_df, geocoded_df[MERGE_COLUMNS + geocoded_columns], on=MERGE_COLUMNS, how="left")`.
3. Bridge, for each row with lat, lon, a geoid that is not empty and not `00000`:
   - get or create `Place` by `geoid`, with state and county names and FIPS from the `closest_*` columns;
   - get or create `LocationAddress` by `(lat, lon)`, with `geography_id = geoid`, the street and city fields, and `etl_run_id` and `lineage_group_id`;
   - record `(lat, lon) -> address.id`, then `session.commit()` (`landfills.py:189`).
4. `address_id` is attached to each row from that map; rows without a usable point get no address (inferred from the map lookup).
5. Load writes the dataset row with `address_id` set.

## Interfaces
- Input: the Drive file and the geocoded worksheet, which must have the same `MERGE_COLUMNS` (for example `name`, `address`, `city`, `county`, `state`, `zip_code` for EPA, `landfill_name`, `state`, `physical_address`, `city`, `county`, `zip_code` for landfills).
- Output: `place`, `location_address` and the dataset table, all with `etl_run_id` and `lineage_group_id`.

## Gotchas
- The transform writes to the database before load. If load fails, the `place` and `location_address` rows remain.
- The address key is lat/lon only. Facilities at the same coordinates share one `location_address` row, and the row keeps the first facility’s street and city (`landfills.py:161-170`). The PR #482 review found this bug in the first attempt; #514 changed the key from county to lat/lon. Whether co-located facilities should share one row is an open question.
- `geo_utils.parse_addresses` is imported (`landfills.py:16`) but never called in `etl/transform/infrastructure/`, so GoogleV3 geocoding and `GOOGLE_MAPS_API_KEY` are not needed for these flows at HEAD.
- The `KeyError` fallback at `landfills.py:248-250` returns the unselected frame (see bugs/transform-broken-filters).

## History
- f8c9353 (PR #514, 2026-10-22): family merged, geocoded merge and lat/lon bridging in all 15 transforms.
- PR #482 (open): first attempt; its 2026-10-07 comment reports the county-keyed lookup in 3 files and a Python `and` bug in 9 files. Both are absent at HEAD (`a2c8de8`): `and_` appears in all 15 and no `lat == ... and` pattern remains.

## Open questions
- Whether the `address-to-geocoded` sheets are refreshed by a separate process (not in this commit).

# Related Concepts
- [Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern](pipeline-infrastructure-etl-family.md): the family this geocoded pattern belongs to
- [Google Sheets extraction: factory, gsheet_to_df, and retries](pipeline-gsheet-extraction.md): how the geocoded worksheet is read
- [Places tables: place (GEOID natural key), location_address, multilinestring](datamodels-places.md): Place and LocationAddress models and the GEOID natural key
- [Name-to-ID normalization (get-or-create reference rows)](pipeline-name-id-normalization.md): name-to-id normalisation that runs after the merge
- [Geography ETL flow (CA counties to Place)](flow-geography.md): the geography flow that maintains the Place rows counties point at
- [PR #482 (open, conflicting): Infrastructure ETL pipelines (18 datasets) with geocoding](../facts/pr-482.md): where the lat/lon versus county bridging bug was first reported
