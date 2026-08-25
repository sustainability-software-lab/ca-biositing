# BioCirV Replicate Precision & Outlier Assessment

## Purpose

This is a small, auditable, exploratory pipeline to characterize BioCirV
technical-replicate precision and compare candidate rerun / outlier flags
(Level 1 technical-replicate variation only — the spread within one sample's
replicate cluster, as distinct from sample-to-sample or resource-to-resource
variation). It is not intended to choose or implement permanent production
filters or thresholds. See
[`biocirv_outlier_assessment_handoff_v4.md`](../biocirv_outlier_assessment_handoff_v4.md)
for the full task specification, statistical principles, and guardrails this
pipeline follows.

## Schema audit findings

Lightweight compatibility review (per the handoff's "Lightweight schema
audit" step) of whether each analysis type can be mapped to a shared
`sample × analysis × parameter × value` structure:

| Analysis type | Status        | Notes |
|---------------|----------------|-------|
| compositional | COMPATIBLE    | |
| proximate     | COMPATIBLE    | |
| xrf           | COMPATIBLE    | |
| icp           | COMPATIBLE    | |
| ultimate      | SMALL_MAPPING | Tiny n (≈78 rows). Includes non-elemental parameter names (e.g. `dm`, `adf-r`, `cf`) alongside nitrogen. Kept per the generic parameter/value principle rather than special-cased. |
| xrd           | COMPATIBLE    | Only 27 rows currently — low volume, watch for thin summaries downstream. |
| calorimetry   | COMPATIBLE    | 0 rows currently — schema-ready, will populate as the DB grows. |

None of the seven target analyses required `DEFER`.

## Data source rationale

This pipeline extracts directly from the raw, unfiltered database rather
than reusing the filtered audit-target views in `audit/targets/views/*.py`
(e.g. `compositional.py`, `proximate.py`, `icp.py`). Those views apply
business-rule filtering — `qc_pass != 'fail'` row drops, compositional/
proximate sum-range filters, an ICP max-ppm filter, and hard-coded resource
exclusion lists — before data reaches any downstream consumer. A replicate-
precision and outlier study needs to see exactly the rows those filters
would hide, since flagged/failed/edge-case rows are the population of
interest here. See
[`extract_raw_data.py`](extract_raw_data.py) for the extraction query and a
fuller explanation in its docstring.

## No separate normalization step

The handoff doc's "Shared Normalization Layer" section originally
envisioned a dedicated `normalize_inputs.py` script to rename the raw
SQL/DB-origin columns produced by extraction into a canonical long-form
schema. That extra stage turned out to be unnecessary indirection:
`observation`'s `(parameter, value, unit)` structure already provides the
structural harmonization the normalization layer was meant to achieve
across the seven characterization analysis tables. Instead,
[`extract_raw_data.py`](extract_raw_data.py) aliases its SQL `SELECT`
columns directly to the canonical names, so its output CSV already is the
canonical schema — no separate `normalize_inputs.py` exists or is planned.

The canonical long-form columns produced directly by `extract_raw_data.py` are:

```text
record_id
sample_id
resource_id
resource_type
analysis_type
parameter
value
unit
lab
method
protocol_version
existing_QC_status
```

plus a few extra columns kept for downstream convenience that are not part
of the strict canonical list: `experiment_id`, `technical_replicate_no`,
`technical_replicate_total`, `method_id`, `analyst_id`, `analyst_name`,
`analyst_email`, `note`, `created_at`.

Several of these are approximations given the current schema (documented
in the script's docstring/comments): `sample_id` is `prepared_sample_id`
(closest DB proxy to an independent sample), `lab` is `provider_codename`
(no dedicated "lab" field exists), `protocol_version` is
`exper_start_date` (no dedicated protocol_version column exists), and
`existing_QC_status` is `qc_pass` carried as metadata only — it is **not**
used as a filter anywhere in this pipeline.

## Pipeline stages

Mirrors the handoff's "Suggested Structure," minus the now-unnecessary
`normalize_inputs.py` stage (see "No separate normalization step" above).
Only extraction exists today; everything else is TBD and will be added as
separate, incremental scripts.

```text
biocirv_outlier_assessment/
│
├── README.md                          ✅ exists (this file)
├── analysis_config.py                 ✅ exists
├── extract_raw_data.py                ✅ exists (raw DB extraction, outputs canonical schema directly)
├── 01_build_replicate_summary.py      ⏳ TBD
├── 02_build_method_parameter_summary.py  ⏳ TBD
├── 03_build_review_heatmap.py         ⏳ TBD
├── 04_selected_diagnostics.py         ⏳ TBD
├── 05_compare_candidate_rules.py      ⏳ TBD
│
├── data/                              ✅ exists (raw_extract_*.csv snapshots, canonical schema)
│
└── outputs/                           ✅ exists (empty, scaffolded)
    ├── replicate_group_summary.csv    ⏳ TBD
    ├── sample_level_summary.csv       ⏳ TBD
    ├── method_parameter_summary.csv   ⏳ TBD
    ├── candidate_rule_comparison.csv  ⏳ TBD
    ├── flagged_cases_for_review.csv   ⏳ TBD
    ├── precision_review_heatmap.png   ⏳ TBD
    └── plots_selected/                ✅ exists (empty, scaffolded)
```

## Status

This is exploratory / MVP work per the handoff's guardrails. No production
thresholds, rerun policies, or database filters are being decided or
implemented here — outputs are intended to inform human review, not to
drive automated decisions.
