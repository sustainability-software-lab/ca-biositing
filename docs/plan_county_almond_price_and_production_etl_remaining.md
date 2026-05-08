# Plan: Almond NSJV ETL Remaining Issues

**Status:** In progress  **Date:** May 7, 2026  **Scope:** Fix remaining issues only

---

## Current State

The almond_nsjv ETL is mostly working. Three issues remain:

1. Observation table rejects inserts associated with `resource_production_record`.
2. `mv_biomass_pricing` is failing or not updating as expected.
3. `mv_biomass_county_production` does not include new years from the almond_nsjv ETL.

This plan focuses on diagnosing and resolving these specific problems without changing the overall ETL design.

---

## Goals

- Ensure observations for production records load successfully.
- Restore/validate `mv_biomass_pricing` output.
- Ensure `mv_biomass_county_production` reflects the new years of production data.

---

## Issue 1: Observation inserts rejected (production records)

### Likely Causes

- Foreign key mismatch (e.g., `resource_production_record_id` missing or not linked correctly).
- Wrong record type or missing required fields (year/resource/parameter/geoid/unit).
- Dataset/method mismatches or missing IDs for production dataset.
- Unique constraint conflict due to natural key usage or duplicated rows.
- Incorrect column set in the production observation payload (e.g., missing `record_id` or using the wrong record id column).

### Diagnostics

- Confirm production records are inserted before observation load.
- Verify that each production observation row has valid IDs:
  - `parameter_id`, `unit_id`, `geoid`, `dataset_id`, `method_id`
  - `resource_id` (if used), `year` (if required)
  - record reference field used by the observation schema
- Compare price vs production observation payloads to identify schema drift.
- Inspect the exact database error message for the rejected inserts and map it to the constraint.

### Fix Checklist

- Verify load order: parameters -> production records -> production observations.
- Align observation payload columns with schema expectations for production records.
- Ensure dataset/method IDs for production are present and correct.
- Deduplicate on the natural key used by observation upserts.

### Acceptance Criteria

- Production observations insert cleanly with no rejected rows.
- Sample query confirms production observations exist for expected years.

---

## Issue 2: `mv_biomass_pricing` not working

### Likely Causes

- View definition assumes columns or values not present in new almond data.
- Missing price observations for required parameters or units.
- Join conditions exclude new dataset or method.
- View has not been refreshed after the ETL run.

### Diagnostics

- Confirm that price observations exist for the almond dataset with the expected parameter names and units.
- Check view definition for hard-coded filters (dataset, method category, parameter names).
- Run a manual refresh to confirm it is not simply stale.

### Fix Checklist

- Align almond price parameter naming with view filters.
- Ensure correct dataset and method IDs are used in price observations.
- Refresh the materialized view after a successful ETL run.

### Acceptance Criteria

- `mv_biomass_pricing` returns rows for almond counties and years expected.

---

## Issue 3: `mv_biomass_county_production` missing new years

### Likely Causes

- New years not present in observations (upsert did not insert or they are filtered out).
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
2. Re-run ETL and confirm base observations contain new years.
3. Refresh materialized views.
4. Validate `mv_biomass_pricing` and `mv_biomass_county_production`.

---

## Done When

- All three issues are resolved.
- A rerun of the almond_nsjv ETL completes without rejected observation inserts.
- Both materialized views return rows for the updated almond data.
