# Plan: Almond NSJV ETL Remaining Issues

**Status:** Partially complete **Date:** May 7, 2026 **Scope:** Fix remaining
issues only

---

## Current State

The almond_nsjv ETL price pipeline is now working end to end for the biomass
pricing materialized view. One issue has been resolved in this pass, while the
other items remain as separate follow-up work:

1. Observation table rejects inserts associated with
   `resource_production_record`.
2. `mv_biomass_pricing` county price rows were missing before this fix, but the
   ETL now loads them successfully and the view is returning the expected
   county-level results.
3. `mv_biomass_county_production` does not include new years from the
   almond_nsjv ETL.

This plan now records the price-side resolution and keeps the remaining
follow-up items visible without changing the overall ETL design.

---

## Goals

- Ensure observations for production records load successfully.
- Populate `price received` observations and their associated price records for
  San Joaquin, Stanislaus, and Merced so `mv_biomass_pricing` can aggregate
  county-specific rows. This is now complete.
- Ensure `mv_biomass_county_production` reflects the new years of production
  data.

---

## Issue 1: Observation inserts rejected (production records)

### Likely Causes

- Foreign key mismatch (e.g., `resource_production_record_id` missing or not
  linked correctly).
- Wrong record type or missing required fields
  (year/resource/parameter/geoid/unit).
- Dataset/method mismatches or missing IDs for production dataset.
- Unique constraint conflict due to natural key usage or duplicated rows.
- Incorrect column set in the production observation payload (e.g., missing
  `record_id` or using the wrong record id column).

### Diagnostics

- Confirm production records are inserted before observation load.
- Verify that each production observation row has valid IDs:
  - `parameter_id`, `unit_id`, `geoid`, `dataset_id`, `method_id`
  - `resource_id` (if used), `year` (if required)
  - record reference field used by the observation schema
- Compare price vs production observation payloads to identify schema drift.
- Inspect the exact database error message for the rejected inserts and map it
  to the constraint.

### Fix Checklist

- Verify load order: parameters -> production records -> production
  observations.
- Align observation payload columns with schema expectations for production
  records.
- Ensure dataset/method IDs for production are present and correct.
- Deduplicate on the natural key used by observation upserts.

### Acceptance Criteria

- Production observations insert cleanly with no rejected rows.
- Sample query confirms production observations exist for expected years.

---

## Issue 2: `mv_biomass_pricing` missing county price rows

### Resolution

The fix was implemented in the almond NSJV load path so the canonical
`price received` parameter is created and resolved before observation insertion.
That lets the county-specific price records from the cleaned almond sheet load
through the polymorphic hourglass design and feed the materialized view.

### What Changed

- Added explicit creation of the `price received` parameter during almond load.
- Preserved the existing `price production weighted average` parameter path.
- Added a defensive alias so legacy misspellings still resolve to
  `price received`.
- Updated the regression test to confirm a county price observation is linked to
  the inserted `resource_price_record`.

### Validation

- `pixi run pytest tests/pipeline/test_almond_nsjv_load.py`
- Manual ETL rerun confirmed `mv_biomass_pricing` now shows the county-level
  price rows.

### Likely Causes

- The almond ETL is only populating the weighted-average price parameter and not
  the county-specific `price received` observations from the cleaned almond
  sheet.
- `resource_price_record` rows exist, but their associated observations are not
  being loaded for San Joaquin, Stanislaus, and Merced.
- The view is aggregating correctly, but there is no county-level price signal
  for it to roll up.
- The materialized view may also be stale and need a refresh after ETL fixes.

### Diagnostics

- Confirm the cleaned almond source still contains county price columns for San
  Joaquin, Stanislaus, and Merced.
- Verify the transform emits `resource_price_record` payload rows for those
  counties and the load step creates matching observations with parameter
  `price received`.
- Confirm the record/observation hourglass linkage resolves to the expected
  `record_id` values.
- Refresh the materialized view only after the base data is fixed.

### Fix Checklist

- Keep the canonical parameter name as `price received` in both transform and
  load paths.
- Ensure county price columns from the original cleaned almond sheet are
  normalized into `resource_price_record` rows for the three NSJV counties.
- Ensure observations for those rows are written with the existing
  `price received` parameter so the polymorphic hourglass design is populated
  end to end.
- Refresh the materialized view after a successful ETL run.

### Acceptance Criteria

- `mv_biomass_pricing` returns price_min, price_max, and price_avg for each of
  San Joaquin, Stanislaus, and Merced, plus the NSJV weighted-average row.

### Status

Completed for the price MV path.

---

## Issue 3: `mv_biomass_county_production` missing new years

### Likely Causes

- New years not present in observations (upsert did not insert or they are
  filtered out).
- View filters limit years or datasets.
- View has not been refreshed after a successful ETL run.

### Diagnostics

- Query observation table for production values for the new years.
- Compare years in base observation data vs materialized view output.
- Check view definition for year filters or dataset constraints.

### Fix Checklist

- Ensure production observations for the new years exist and are valid.
- Update view definition only if required filters are incorrect.
- Refresh the materialized view after ETL load.

### Acceptance Criteria

- `mv_biomass_county_production` includes the new almond years.

---

## Suggested Debug Order

1. Fix production observation load rejects (Issue 1).
2. Confirm the price MV remains correct on future ETL runs.
3. Re-run ETL and confirm base observations contain the county price records.
4. Refresh materialized views.
5. Validate `mv_biomass_pricing` and `mv_biomass_county_production`.

---

## Done When

- All three issues are resolved.
- `price received` observations exist for the county price rows and the NSJV
  weighted-average row.
- Both materialized views return rows for the updated almond data.
- The load-path regression test passes and the price MV shows the county-level
  almond rows after an ETL rerun.
