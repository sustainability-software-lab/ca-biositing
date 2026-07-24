# Audit Platform Phase 2: Standard Dimensions & Sidecar Context

## Overview

This document outlines the plan for rolling out the "Standard Dimension" SQL
query pattern and enhanced LLM sidecar context across all audit targets in the
CA Biositing platform.

## 1. The "Standard Dimension" Query Pattern

The goal is to ensure all audit targets pull a consistent set of metadata
dimensions to allow the LLM to reason about anomalies across time, providers,
analysts, and experimental conditions.

### Required Columns for `observation_sql`

Every target's `observation_sql` should be updated to include these columns (or
`NULL AS column_name` if the concept doesn't exist for that record type):

```sql
SELECT
    r.record_id,
    r.experiment_id,
    exp.exper_start_date AS experiment_date,
    r.prepared_sample_id,
    fs.id AS field_sample_id,
    fs.collection_timestamp,
    prov.codename AS provider_codename,
    res.name AS resource_name,
    pap.name AS primary_product,
    p.name AS parameter_name,
    u.name AS unit,
    o.value AS observed_value,
    r.technical_replicate_no AS repl_no,
    r.qc_pass,
    o.note AS note,
    c.email AS analyst_email,
    -- Target-specific columns below (e.g., reactor_vessel, strain_name)
```

### Key Learnings from Pilot (`mv_biomass_fermentation`)

1. **Column Naming in `group_by_cols`**: Ensure the columns listed in
   `group_by_cols` exactly match the aliases used in `population_sql` and
   `observation_sql`. In the pilot, `product_name` was used in the view, but we
   aliased it to `parameter_name` in the observation query, causing a `KeyError`
   during the pandas merge.
2. **Evidently AI Legacy Bug**: The `TestColumnsType()` check in
   `evidently_engine.py` was temporarily disabled because adding new columns to
   the `observation_sql` that weren't in the golden reference CSV caused
   Evidently to crash. When updating targets, either re-freeze the golden
   reference (`pixi run audit-freeze <target>`) or leave this check disabled.
3. **Replicate Numbers**: Use `technical_replicate_no` from the `Aim1RecordBase`
   or `Aim2RecordBase` mixins for the `repl_no` dimension.

## 2. Sub-Tasks for Remaining Targets

The following targets need to be updated with the Standard Dimension query
pattern and a dedicated sidecar context markdown file in
`audit/targets/context/`.

### AIM 1 Targets (Compositional)

- [ ] `mv_biomass_composition` (Note: This is a UNION of many tables, so the
      query update will be large)
- [ ] `mv_biomass_composition_extended`

### AIM 2 Targets (Conversion)

- [ ] `mv_biomass_gasification`
  - **Specific Case**: Add `reactor_id` (or `reactor_type`) to the query.
- [ ] `pretreatment` (if separate from composition)

### Other Targets

- [ ] `mv_biomass_availability`
- [ ] `mv_biomass_pricing`
- [ ] `mv_biomass_end_uses`
- [ ] `mv_biomass_sample_stats`

## 3. Sidecar Context Guidelines

When creating the `.md` files in `audit/targets/context/`, include:

1. **Target Overview**: What does this data represent?
2. **Audit Dimensions & Reasoning**: How should the LLM interpret the standard
   dimensions (e.g., how does `provider_codename` affect expected variance?).
3. **Known Anomalies & Expected Patterns**: What are common "false positive"
   anomalies (e.g., BDL zeros in ICP, expected high variance in certain
   parameters)?

## 4. LLM Prompt Update

The prompt in `audit/skills/llm_synthesis.py` has been updated to explicitly ask
the LLM to summarize the issue groups in the executive summary, rather than just
listing them in the table.
