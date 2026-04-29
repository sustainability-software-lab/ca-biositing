# Phase 3: Materialized Views Assessment & Implementation Plan

**Date**: 2026-04-20
**Status**: Assessment Complete - Ready for Implementation Planning
**Objective**: Update data_portal materialized views to align with spec, fix has_blank detection issue, and implement volume calculation strategy

---

## Executive Summary

Phase 3 involves three major areas of work to complete the Residue Factors ETL integration and update the data_portal schema materialized views:

1. **Fix Boolean Indicator Detection Bug** - The `has_*` boolean columns in `mv_biomass_search` currently detect resource presence BEFORE QC filtering, but should only return TRUE if data exists AFTER `qc_pass != "fail"` filtering
2. **Volume Estimation Strategy** - Implement dual-path volume calculation: (a) county_ag_report_record × residue_factors for production-based volumes, (b) USDA census bearing acres for orchard crops
3. **Materialized View Alignment** - Ensure all views align with the data_portal specification (9 views, specific column sets, proper aggregation logic)

---

## Issue 1: Boolean Indicator Detection (has_moisture, has_sugar, has_volume, has_image, etc.)

### Current Problem

In `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_search.py`, the boolean flags are computed from the `resource_analysis_map` and `analysis_metrics` queries without filtering for `qc_pass != "fail"`.

**Current logic (lines 184-187)**:
```python
case((resource_metrics.c.moisture_percent != None, True), else_=False).label("has_moisture_data"),
case((resource_metrics.c.sugar_content_percent > 0, True), else_=False).label("has_sugar_data"),
case((ResourceMorphology.morphology_uri != None, True), else_=False).label("has_image"),
case((agg_vol.c.total_annual_volume != None, True), else_=False).label("has_volume_data"),
```

These aggregate all observations INCLUDING those marked as `qc_pass = "fail"`, but the specification and UI require that these booleans reflect only VALID data (i.e., observations with `qc_pass != "fail"`).

### Impact
- Frontend assumes `has_moisture_data = true` means "this resource has valid moisture data to display"
- Currently shows TRUE even if all moisture data is failed QC
- Leads to broken UI displays when users filter to a resource with supposedly available data but all data is invalid

### Solution Approach

1. **Filter resource_analysis_map & analysis_metrics at source** - Add WHERE clause to exclude `qc_pass = "fail"` observations
   - Modify the base subquery that builds `resource_analysis_map`
   - Apply `AND qc_pass != "fail"` to the join between Observation and analytical records

2. **Propagate filter through aggregations** - Ensure the has_proximate, has_compositional, etc. flags only count valid records

3. **Test with edge cases**:
   - Resource with only failed QC data (should show all has_* = FALSE)
   - Resource with mixed valid/failed data (should show has_* = TRUE)
   - Resource with no data at all (should show has_* = FALSE)

---

## Issue 2: Volume Estimation Strategy

### Current State

Currently, volumes come from `BillionTon2023Record` via the `agg_vol` subquery. However, the specification and new Residue Factors data enable more sophisticated volume estimation:

**Spec Reference** (MV 3: mv_usda_county_production):
- `calculated_estimate_volume` = dry_tons/acre × production_acres
- This implies that residue volume = primary_product_volume × residue_factor

### Two Volume Calculation Paths

#### Path A: Production-Based Residue Volumes (Most Resources)

For resources with primary agricultural products (e.g., corn stover, wheat straw):

```
residue_volume = county_ag_report_record.primary_product_volume
                 × residue_factors.factor_mid (or factor_min/max for ranges)
```

**Data sources**:
- `county_ag_report_record` - USDA/state agricultural production volumes by county
- `residue_factors` - Residue factor data loaded in Phase 1/2
- `resource` → `primary_ag_product` join to match crops

**Implementation steps**:
1. Join `county_ag_report_record` to `Resource` via `primary_ag_product_id`
2. Join `Resource` to `ResidueFactor` on `resource_id`
3. Filter `ResidueFactor` by `factor_type` (likely "commodity" for standard residue yield)
4. Calculate: `estimated_residue_volume = production_volume × factor_mid`
5. Aggregate by county to support monthly/quarterly breakdowns

**SQL Pattern**:
```sql
SELECT
    car.geoid,
    car.county,
    car.dataset_year,
    r.id as resource_id,
    r.name as resource_name,
    car.primary_product_volume,
    car.production_unit,
    rf.factor_mid,
    rf.factor_min,
    rf.factor_max,
    (car.primary_product_volume * rf.factor_mid)::numeric AS estimated_residue_volume,
    'dry_tons' AS biomass_unit
FROM county_ag_report_record car
JOIN resource r ON car.resource_id = r.id
JOIN residue_factor rf ON r.id = rf.resource_id
    AND rf.factor_type = 'commodity'
WHERE rf.resource_id IS NOT NULL
```

#### Path B: Census-Based Orchard Volumes (Perennial Crops)

For orchard/perennial crops (almonds, walnuts, etc.), bearing acres are tracked separately:

```
residue_volume = USDA_census.bearing_acres_county
                 × residue_factors.prune_trim_yield
                 × (years_in_production_cycle / 1)
```

**Data sources**:
- `usda_census_record` - Bearing acres, inventory data for perennial crops
- `residue_factors.prune_trim_yield` - Yield from pruning/trimming operations (Phase 1 field)
- `residue_factors.prune_trim_yield_unit_id` - Unit for yield (e.g., "DT/acre year")

**Implementation steps**:
1. Identify orchard crops: those with `ResourceClass.name LIKE '%orchard%'` or similar
2. Join `usda_census_record` to `Resource`
3. Join `Resource` to `ResidueFactor` on resource_id
4. Filter for records where `prune_trim_yield IS NOT NULL`
5. Calculate: `estimated_residue_volume = bearing_acres × prune_trim_yield`
6. Annotate source as "census_bearing_acres" vs "production_based"

**SQL Pattern**:
```sql
SELECT
    ucr.geoid,
    ucr.county,
    ucr.year,
    r.id as resource_id,
    r.name as resource_name,
    ucr.bearing_acres,
    rf.prune_trim_yield,
    u.name as yield_unit,
    (ucr.bearing_acres * rf.prune_trim_yield)::numeric AS estimated_residue_volume,
    'dry_tons' AS biomass_unit,
    'census_bearing_acres' AS volume_source
FROM usda_census_record ucr
JOIN resource r ON ucr.resource_id = r.id
JOIN residue_factor rf ON r.id = rf.resource_id
JOIN unit u ON rf.prune_trim_yield_unit_id = u.id
WHERE rf.prune_trim_yield IS NOT NULL
    AND ucr.bearing_acres > 0
```

### Integration into mv_biomass_search & mv_usda_county_production

1. **mv_usda_county_production** should include a new `volume_source` column:
   - "production_based" - from county_ag_report_record × residue_factors
   - "census_bearing_acres" - from usda_census_record × residue_factors
   - "billion_ton_2023" - legacy (keep for backward compatibility)

2. **mv_biomass_search** aggregates across all sources:
   - `calculated_estimate_volume_min` = MIN across all (resource, county) combinations
   - `calculated_estimate_volume_max` = MAX across all (resource, county) combinations
   - `calculated_estimate_volume_mid` = (MIN + MAX) / 2

3. **Priority/Precedence**:
   - If production_based volume exists → use it (primary path)
   - Else if census_bearing_acres volume exists → use it (fallback for orchards)
   - Else if billion_ton_2023 exists → use it (legacy)

---

## Issue 3: Materialized View Alignment with Specification

### Views to Update/Verify

| View | Grain | Status | Action |
|------|-------|--------|--------|
| **mv_biomass_search** | 1 row per resource | 🔴 Needs Fix | Fix has_* boolean filtering + volume calculation |
| **mv_biomass_composition** | 1 row per resource × county × parameter × analysis_type | 🟡 Check | Verify qc_pass filtering, std_dev calculation |
| **mv_usda_county_production** | 1 row per resource × county × year | 🔴 Needs Major Update | Add residue factor-based volume calculation |
| **mv_biomass_availability** | 1 row per resource | ✅ Check | Verify includes residue_factors.prune_trim_yield |
| **mv_biomass_sample_stats** | 1 row per resource | ✅ Check | Verify sample counts, unique suppliers |
| **mv_biomass_fermentation** | 1 row per resource × county × strain × pretreatment+enzyme × product | ✅ Check | Verify grain and columns |
| **mv_biomass_gasification** | 1 row per resource × reactor type × parameter | ✅ Check | Verify grain and columns |
| **mv_biomass_pricing** | 1 row per resource × county × report source × report date | ✅ Check | Verify resource_price_record joins |
| **mv_biomass_end_uses** | 1 row per resource × use case | ✅ Check | Verify resource_end_use_record joins |

### Key QC Filtering Requirements

All views should apply the following filters consistently:

```sql
WHERE observation.qc_pass != 'fail'  -- Exclude failed QC observations
```

This applies to:
- Compositional analysis (CompositionalRecord)
- Proximate analysis (ProximateRecord)
- Ultimate analysis (UltimateRecord)
- XRF analysis (XrfRecord)
- ICP analysis (IcpRecord)
- Calorimetry analysis (CalorimetryRecord)
- XRD analysis (XrdRecord)
- FT-NIR analysis (FtnirRecord)

---

## Implementation Roadmap

### Phase 3.1: Boolean Indicator Fix (High Priority)
**Impact**: Medium (fixes UI display correctness)
**Complexity**: Medium (requires careful QC filtering propagation)
**Timeline**: ~1-2 sprints

**Tasks**:
1. Review and document current qc_pass filtering in codebase
2. Trace data flow: Observation → analytical_records → resource_analysis_map
3. Identify where qc_pass filter should be applied (likely in resource_analysis_map subquery)
4. Modify mv_biomass_search resource_metrics subquery to exclude failed QC
5. Add unit tests for edge cases (all failed, mixed, no data)
6. Update view, refresh materialized view, verify UI behavior

### Phase 3.2: Volume Calculation Strategy (High Priority)
**Impact**: High (enables residue volume estimation)
**Complexity**: High (multi-source joins, business logic)
**Timeline**: ~2-3 sprints

**Tasks**:
1. Validate county_ag_report_record schema and data availability
2. Map resource → primary_ag_product relationships
3. Implement Path A: production-based volume calculation
   - Create test query with sample data
   - Verify factor_mid values align with spec
   - Test aggregation logic
4. Validate usda_census_record schema and bearing_acres availability
5. Identify orchard crops (manual list or heuristic)
6. Implement Path B: census-based volume calculation
   - Create test query with sample data
   - Verify prune_trim_yield values exist and are reasonable
7. Create unified volume view that combines both paths with precedence logic
8. Integrate into mv_usda_county_production
9. Update mv_biomass_search to use new volume aggregates
10. Add volume_source annotation for transparency

### Phase 3.3: View Alignment & Verification (Medium Priority)
**Impact**: Medium (ensures frontend contract compliance)
**Complexity**: Medium (systematic review and fixes)
**Timeline**: ~1-2 sprints

**Tasks**:
1. Systematic review of each of 9 views against specification
2. Verify column names, types, nullable constraints
3. Verify aggregation logic (SUM, AVG, MIN, MAX, DISTINCT, etc.)
4. Verify join logic and grain (one row per...)
5. Create test cases with sample data to validate each view
6. Document any deviations from spec with justification
7. Update view definitions and refresh

---

## Data Model Context

### Key Tables for Volume Calculation

**county_ag_report_record** (expected schema):
- `id` - PK
- `geoid` - County FIPS code
- `county` - County name
- `dataset_year` - Year of report
- `resource_id` - FK to Resource
- `primary_product_volume` - Production volume
- `production_unit` - Unit (tons, DT, etc.)
- `production_acres` - Harvested acres

**residue_factor** (Phase 1 created):
- `id` - PK
- `resource_id` - FK to Resource (required)
- `resource_name` - Denormalized Resource.name
- `factor_type` - "commodity", "area", "weight"
- `factor_min`, `factor_max`, `factor_mid` - Numeric factor values
- `prune_trim_yield` - Yield from pruning/trimming
- `prune_trim_yield_unit_id` - FK to Unit
- `qc_pass` - Via observation lineage

**usda_census_record** (expected schema):
- `id` - PK
- `geoid` - County FIPS code
- `county` - County name
- `year` - Year of census
- `resource_id` - FK to Resource
- `bearing_acres` - Acres in production
- `inventory_count` - Number of trees/vines

### Observation QC Filter

**Observation** table has:
- `qc_pass` - "pass", "fail", NULL
- Must filter where `qc_pass != 'fail'` for all analytical views

---

## Success Criteria

### Phase 3.1 Completion
- [ ] has_* boolean columns return TRUE only when valid (qc_pass != 'fail') data exists
- [ ] Unit test coverage: all-fail, mixed, no-data scenarios
- [ ] No regression in existing UI pages

### Phase 3.2 Completion
- [ ] mv_usda_county_production includes calculated_estimate_volume from residue factors
- [ ] Path A (production-based) volumes validate against manual spot checks
- [ ] Path B (census-based) volumes validate against manual spot checks
- [ ] Volume precedence logic documented and tested
- [ ] volume_source column tracks calculation method
- [ ] mv_biomass_search volume aggregates (min/max/mid) are correct

### Phase 3.3 Completion
- [ ] All 9 views align with specification column sets
- [ ] All 9 views implement correct grain (one row per...)
- [ ] All aggregation logic verified with test data
- [ ] QC filtering consistently applied across all views
- [ ] Recommended indexes created

---

## Risk Assessment & Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| county_ag_report_record data unavailable/incorrect | High | Validate schema & data early; coordinate with data team |
| Residue factor values unrealistic or sparse | High | QA on residue_factors Phase 2 output; sample manually |
| QC filter propagation breaks existing functionality | Medium | Comprehensive test coverage before deployment |
| Bearing acres accuracy for orchard crops | Medium | Compare against USDA official reports |
| Volume unit inconsistencies (tons vs dry tons) | Medium | Document unit assumptions; apply conversion factors as needed |

---

## Next Steps

1. **Stakeholder Alignment** - Review this assessment with data team and frontend team
2. **Data Validation** - Confirm availability and quality of county_ag_report_record and usda_census_record
3. **Detailed Design** - Create SQL DDL for new/updated views
4. **Sprint Planning** - Sequence the three phases with engineering capacity
5. **Handoff to Code Mode** - Once approved, delegate implementation to code agents
