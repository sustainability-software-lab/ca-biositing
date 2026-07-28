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

---

## Session Notes: 2026-07-24

### Query Improvements Needed for `mv_biomass_fermentation`

The following columns should be added to the `observation_sql` for
`mv_biomass_fermentation` but are **not yet in the query**:

1. **`pretreatment_method`**: The fermentation experiment has a pretreatment
   stage before bioconversion. The pretreatment method (e.g., cholinium lysinate
   concentration, steam explosion) is a critical grouping variable because
   yields are highly dependent on how the biomass was pretreated. This should be
   joined from the `method` table via `fr.pretreatment_method_id`.
2. **`strain_name`**: Already in the query — confirmed present.
3. **`bioconversion_method`**: The bioconversion method (e.g., SSF, SHF) is
   another key grouping variable. Should be joined from `bioconversion_method`
   table via `fr.bioconversion_method_id`.

### Experimental Structure Context (for Sidecar)

The fermentation assay is a **high-throughput, low-volume** experiment with the
following structure:

- **T0 (Start of Fermentation)**: Initial sugar concentrations are measured
  (`SugarT0`, `GluConcT0`, `XylConcT0`). These are the "input" values.
- **TEOF (End of Fermentation)**: Final product concentrations and residual
  sugars are measured (`EtOHtiter`, `EtOHyield`, `SugarTEOF`, `GluConcTEOF`,
  `XylConcTEOF`, `OD600TEOF`). These are the "output" values.
- **Elapsed Fermentation Time (EFT)**: The duration in hours between T0 and
  TEOF.

**Key Implication for Audit**: T0 and TEOF values for the same `record_id` are
linked. The audit should ideally correlate T0 sugar concentrations with TEOF
product yields to detect implausible mass balances (e.g., high ethanol yield
from very low initial glucose). This is a future enhancement — for now, the
sidecar context should instruct the LLM to be aware of this T0/TEOF pairing when
reasoning about anomalies.

### Parameter Categories (for Sidecar)

Parameters fall into distinct categories that have different expected ranges and
anomaly patterns:

| Category                           | Parameters                                                                                                                                                                                                         | Notes                                                         |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------- |
| **Product (Bioconversion Output)** | `EtOHtiter`, `EtOHrate`, `EtOHyield`, `3HPtiter`, `3HPrate`, `3HPyield`                                                                                                                                            | Yields are bounded by theoretical maxima                      |
| **Fermentable Carbon (Sugars)**    | `Fructose_gL`, `Glucose_yld`, `Xylose_yld`, `Mannose_gL`, `Galactose_pc`, `Glucose_cons`, `Xylose_cons`, `Sugar_yld`, `Sugar_cons`, `SugarT0`, `SugarTEOF`, `GluConcT0`, `XylConcT0`, `GluConcTEOF`, `XylConcTEOF` | T0 vs TEOF pairs; consumption % should be 0-100               |
| **Lignin (Pretreatment Output)**   | `Lignin`, `G-Lignin_pc`, `H-Lignin_pc`, `S-Lignin_pc`                                                                                                                                                              | Percentages; should sum to ~100% for G+H+S                    |
| **Fermentation Growth**            | `OD600TEOF`, `Rel_growth`                                                                                                                                                                                          | OD600 is unitless; Rel_growth is % of synthetic media control |
| **Pretreatment Conditions**        | `TotSug`, `ChoLys_pc`                                                                                                                                                                                              | Cholinium lysinate is the ionic liquid pretreatment agent     |
| **Fermentation Timing**            | `EFT`                                                                                                                                                                                                              | Elapsed time in hours; typical range 24-120h                  |

### Theoretical Maxima for Anomaly Detection

| Parameter                                       | Theoretical Max   | Notes                                                        |
| ----------------------------------------------- | ----------------- | ------------------------------------------------------------ |
| `EtOHyield` (mol%)                              | ~100 mol%         | Values >100 are physically impossible                        |
| `EtOHtiter` (g/L)                               | ~100 g/L          | Values >100 g/L are extremely unusual                        |
| `EtOHrate` (g/Lh)                               | ~5 g/Lh           | Very high rates suggest unit error                           |
| `3HPyield` (g/g)                                | ~1.0 g/g          | Yield per gram carbon consumed                               |
| `Glucose_cons`, `Xylose_cons`, `Sugar_cons` (%) | 100%              | Cannot consume more than 100%                                |
| `Rel_growth` (%)                                | Typically 0-200%  | >200% is unusual; negative values indicate growth inhibition |
| `OD600TEOF`                                     | Typically 0.1-5.0 | Unitless; values >10 are unusual for this assay              |

---

## SQL Join Investigations

### 1. Analyst Attribution (analyst_email)

**Issue**: High number of null values for `analyst_email` in
`mv_biomass_fermentation`. **Root Cause**: The query was joining `contact`
through the `experiment` table:

```sql
LEFT JOIN public.experiment exp ON fr.experiment_id = exp.id
LEFT JOIN public.contact c ON exp.analyst_id = c.id
```

However, `experiment_id` is often null (sparse) in the records table.
**Resolution**: Join `contact` directly from the record table's `analyst_id`
column (provided by the `Aim2RecordBase` mixin).

```sql
LEFT JOIN public.contact c ON fr.analyst_id = c.id
```

**Verification**: Verified on 2026-07-24. `analyst_email` null counts dropped
from 2,873 to 0. **Action Taken**: Updated
`audit/targets/views/mv_biomass_fermentation.py`. Other targets (composition,
gasification) were verified to already be using the correct direct join pattern.
