# BioCirV Replicate Precision & Outlier Assessment — Coding Agent Handoff v4

## Purpose

Build a **small, auditable exploratory pipeline** to characterize BioCirV replicate precision and compare candidate rerun / outlier flags.

The goal is **not** to choose or implement permanent production filters.

The analysis should answer:

1. What does replicate precision look like for each `analysis_type × parameter`?
2. Which combinations appear most problematic?
3. How often do candidate rules flag replicate groups?
4. Where do candidate methods agree or disagree?
5. What rerun burden would each candidate policy create?
6. Are there signs that precision depends on concentration or resource / matrix?
7. Which combinations deserve deeper human review?

The first pass should prioritize broad descriptive comparison and human review, while staying easy to narrow if data-structure issues appear.

## Scope Boundary

Focus first on characterization / composition-style data:

- proximate
- XRF
- compositional analysis
- XRD
- ICP
- caloric
- ultimate analysis

Conversion / process-performance data should be handled later because it may have a different structure.

Keep the target list configurable:

```python
CHARACTERIZATION_ANALYSES = [
    "proximate",
    "xrf",
    "compositional",
    "xrd",
    "icp",
    "caloric",
    "ultimate",
]

TARGET_ANALYSES = CHARACTERIZATION_ANALYSES
```

If needed:

```python
TARGET_ANALYSES = [
    "proximate",
    "compositional",
    "icp",
    "ultimate",
]
```

The downstream pipeline should not need to change.

# Recommended Execution Strategy

## 1. Lightweight schema audit — reasoning step, not coding project

Before writing analysis code, inspect the characterization datasets and answer only:

> Can each analysis be mapped reasonably easily to a shared structure of `sample × analysis × parameter × value`?

This is intended to be **LLM / human reasoning**, not a separate script to build and debug.

For each analysis, identify only:

```text
analysis_type
source / sheet
sample identifier
resource identifier
candidate parameter columns
value representation
unit representation
replicate information
obvious special structure
```

Then assign one status:

```text
COMPATIBLE
SMALL_MAPPING
DEFER
```

### COMPATIBLE
Can be normalized through ordinary reshaping / renaming.

### SMALL_MAPPING
Needs a small explicit mapping, such as:
- different sample ID column name
- wide parameter columns
- units encoded in headers
- extra metadata columns

### DEFER
Would require substantial analysis-specific logic or has fundamentally different data, such as:
- raw spectra
- peak arrays
- time series
- ambiguous replicate structure
- unclear parameter/value semantics

Do not solve `DEFER` analyses during the MVP.

# Agile Fallback: Skip the Audit if It Starts Expanding

The schema audit is **optional supporting work**.

If it starts taking too long:

1. Stop the audit.
2. Manually choose a smaller `TARGET_ANALYSES` list containing analyses whose structure is already understandable.
3. Normalize only those analyses.
4. Run the MVP replicate analysis.
5. Add additional analyses later only when they can be mapped with a small adapter.

Record only:

```text
included_analyses = [...]
deferred_analyses = [...]
deferred_reason = [...]
```

That is sufficient.

## Stop rule

Do not spend substantial time trying to make every characterization analysis compatible before producing useful results.

The schema review should answer:

> "Can we include this easily?"

not:

> "How do we fully harmonize every BioCirV analysis table?"

# Shared Normalization Layer

For included analyses, normalize data into one canonical long-form structure:

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

Different parameter names are expected.

Examples:

```text
proximate     ash           12.4
proximate     moisture       8.1
ICP           Fe           135
ICP           Ca           820
ultimate      carbon        46.2
caloric       HHV           18.7
```

The downstream replicate-QC pipeline should operate on generic `analysis_type`, `parameter`, and `value` fields rather than hard-coded analyte names.

Prefer:
- a small config dictionary
- a few adapter functions
- `melt()` / reshape operations
- column renaming

Do **not** build a generalized schema-conversion framework.

# Core Statistical Principle

BioCirV has several levels of variation. Keep them separate.

## Level 1 — Technical replicate variation

The spread within one sample's replicate cluster represents analytical / measurement repeatability.

Use this level for:
- replicate SD
- replicate RSD
- Dixon Q
- candidate outlier flags
- rerun triggers
- method-precision characterization

## Level 2 — Sample-to-sample variation within a resource

The spread among independent sample means reflects resource / sample heterogeneity plus residual analytical error.

It is **not analytical precision**.

## Level 3 — Differences among resources

Differences among resources primarily represent real material differences.

Do not use them to estimate method precision.

## Standardization principle

1. Calculate variation within each technical replicate cluster.
2. Calculate **both SD and RSD for every eligible cluster**.
3. Carry both forward through the first-pass analysis.
4. Summarize cluster-level precision by `analysis_type × parameter`.
5. Review evidence before deciding whether absolute SD, RSD, concentration dependence, or matrix effects should guide later policy.

**Standardize the decision process, not necessarily one numeric cutoff.**

# Scope Reduction for This First Pass

The first pass should:

> **calculate broadly first; classify and narrow later.**

Do **not** create an early `ABSOLUTE` vs `RELATIVE` branch that determines which downstream analysis runs.

For every sufficiently populated `analysis_type × parameter`:
- summarize SD
- summarize RSD
- calculate candidate flag rates
- retain concentration-range information
- retain resource / matrix information
- select only a few combinations for deeper visual review

The absolute-vs-relative distinction is an observation for human discussion, not an automated routing rule in the MVP.

# Step 0 — Determine the Technical Replicate Grouping Key

Likely grouping key:

```text
sample_id
+ analysis_type
+ parameter
+ method / protocol_version, if available
+ lab, if available
```

`resource` is normally metadata, not part of the replicate grouping key.

Do not combine:
- different independent samples of the same resource
- different labs
- different protocols
- distinct experimental runs

unless the data explicitly show they are true technical replicates.

## Stop condition

If true technical replicates cannot be identified reliably:

**Do not guess. Stop and report the grouping problem.**

# Step 1 — Build the Replicate-Group Summary

For every technical replicate group calculate:

```text
replicate_group_id
sample_id
resource_id
resource_type
analysis_type
parameter
lab
method
protocol_version
unit

n_replicates
mean
median
standard_deviation
RSD_percent
min
max
range

values
source_record_ids
existing_QC_status
```

Use sample SD (`ddof = 1`).

If mean is zero or nearly zero, mark RSD undefined rather than infinite.

Do not silently drop undefined groups.

## Output

```text
outputs/replicate_group_summary.csv
```

# Step 2 — Build the Sample-Level Summary

Create one row per independent sample using the technical replicate-group mean.

Include:

```text
sample_id
resource_id
resource_type
analysis_type
parameter
lab
method
protocol_version

sample_mean
n_replicates
replicate_SD
replicate_RSD
replicate_group_id
```

Do not use raw replicate values pooled across samples to measure resource spread.

## Output

```text
outputs/sample_level_summary.csv
```

# Step 3 — Add Candidate Replicate-Level Flags

These are exploratory only.

## RSD sensitivity

Add:

```text
rsd_gt_10
rsd_gt_20
```

These are comparison benchmarks, not proposed BioCirV thresholds.

## Dixon Q

Where applicable, calculate:

```text
dixon_q_statistic
dixon_candidate_record_id
dixon_flag_0_05
```

Treat Dixon as a flag, not removal.

Do not sequentially remove a point and rerun Dixon.

## ROUT — optional

If a trusted implementation is readily available:

```text
rout_flag
rout_q
```

Prefer `Q = 1%`.

If not, record:

```text
rout_status = "not_calculated"
```

and continue.

Do not implement ROUT from scratch during the MVP.

# Step 4 — Summarize by Analysis Type × Parameter

Group **replicate summaries**, not raw observations.

For each `analysis_type × parameter` calculate:

```text
n_replicate_groups
n_independent_samples
replicate_n_counts
median_replicate_n

min_sample_mean
max_sample_mean
sample_mean_span

median_SD
Q1_SD
Q3_SD

median_RSD
Q1_RSD
Q3_RSD
P90_RSD
P95_RSD

percent_RSD_gt_10
percent_RSD_gt_20
percent_Dixon_flagged
percent_ROUT_flagged
```

Stratify by lab / method / protocol only when known differences make pooling inappropriate.

Do **not** automatically classify combinations as `ABSOLUTE`, `RELATIVE`, or `CONCENTRATION_DEPENDENT`.

## Output

```text
outputs/method_parameter_summary.csv
```

# Step 5 — Build One Compact Review Heatmap

Do **not** create two plots for every method × parameter combination.

Create one whole-dataset heatmap or similarly scannable summary with one row per `analysis_type × parameter`.

Preferred comparable metrics:

```text
n_replicate_groups
median_RSD
P90_RSD
percent_RSD_gt_10
percent_RSD_gt_20
percent_Dixon_flagged
percent_ROUT_flagged
```

Do not use raw median SD as the main heatmap comparison across unrelated parameters with different units.

Keep SD in the underlying table.

## Output

```text
outputs/precision_review_heatmap.png
```

# Step 6 — Select Only 5–10 Combinations for Diagnostic Plots

Select combinations using documented reasons such as:
- highest median RSD
- highest P90 RSD
- highest `% RSD >20`
- highest Dixon flag rate
- largest RSD/Dixon disagreement
- widest concentration range
- known QC concern
- strategically important analytical family
- one low-variability example

For selected combinations create:

```text
sample mean vs replicate SD
sample mean vs replicate RSD
```

Each point represents one technical replicate group / independent sample.

If easy, encode resource / matrix.

## Output

```text
outputs/plots_selected/
```

# Step 7 — Add Human-Review Interpretation

For selected combinations, add:

```text
sd_behavior_note
rsd_behavior_note
concentration_effect_possible
matrix_effect_possible
low_concentration_issue_possible
review_notes
```

These are observations, not algorithm-routing categories.

# Step 8 — Produce the Candidate-Rule Comparison

Create approximately:

| Analysis type | Parameter | Replicate groups | Median RSD | P90 RSD | RSD >10% | RSD >20% | Dixon | ROUT |
|---|---|---:|---:|---:|---:|---:|---:|---:|

Also calculate overlap:

```text
RSD-only
Dixon-only
ROUT-only
RSD + Dixon
RSD + ROUT
Dixon + ROUT
all available methods
```

## Output

```text
outputs/candidate_rule_comparison.csv
```

# Step 9 — Calculate Operational Rerun Burden

For each candidate policy estimate:

```text
number_of_groups_triggering_rerun
percent_of_groups_triggering_rerun
```

At minimum compare:

```text
RSD > 10%
RSD > 20%
Dixon Q
ROUT   # if available
```

Do **not** implement 2s / 3s precision-envelope rules in the MVP.

# Step 10 — Create a Small Human-Review Sample

Create approximately 20–40 representative replicate groups:

```text
flagged by all available methods
RSD-only
Dixon-only
ROUT-only
very high RSD but no individual outlier flag
known QC / analyst flags
possible matrix-effect cases
```

Include source record IDs.

## Output

```text
outputs/flagged_cases_for_review.csv
```

# Decision Dependency

```text
OPTIONAL QUICK LLM/HUMAN SCHEMA REVIEW
        │
        ├── easy → include analysis
        ├── small mapping → add simple adapter
        └── getting complicated → defer it
        │
        ▼
CONFIGURE TARGET_ANALYSES
        │
        ▼
NORMALIZE INCLUDED ANALYSES
        │
        ▼
IDENTIFY TECHNICAL REPLICATE GROUPS
        │
        ▼
CALCULATE BOTH SD + RSD + CANDIDATE FLAGS
        │
        ▼
SUMMARIZE BY ANALYSIS × PARAMETER
        │
        ▼
ONE COMPACT HEATMAP
        │
        ▼
SELECT ONLY 5–10 COMBINATIONS
        │
        ▼
PLOT BOTH SD AND RSD BEHAVIOR
        │
        ▼
HUMAN REVIEW
        │
        ▼
COMPARE FLAG BURDEN + OVERLAP
        │
        ▼
DECIDE WHAT DESERVES A SECOND PHASE

IMPORTANT:

THE SCHEMA AUDIT IS OPTIONAL.

IF IT BECOMES A PROJECT,
SKIP IT AND NARROW TARGET_ANALYSES.

DO NOT CHOOSE AN ABSOLUTE VS RELATIVE
MODEL BEFORE HUMAN REVIEW.
```

# Minimum Viable Analysis

1. Choose `TARGET_ANALYSES`.
2. Normalize included analyses.
3. Identify technical replicate groups.
4. Build replicate-group summary.
5. Build sample-level summary.
6. Calculate mean / SD / RSD.
7. Calculate RSD benchmark flags.
8. Calculate Dixon Q.
9. Build method × parameter summary.
10. Build one compact heatmap.
11. Select only 5–10 diagnostic combinations.
12. Plot SD and RSD for those combinations.
13. Compare flag burden and overlap.
14. Calculate rerun burden.
15. Build a small flagged-case review table.

The optional schema review should not become an additional software subproject.

# Optional After Human Review

Only add if the MVP shows they are worth pursuing:

- ROUT, if not already easy
- 2s / 3s precision-envelope analysis
- pooled absolute SD
- pooled / weighted CV
- concentration-specific precision rules
- matrix-specific stratification
- reference-material / control-chart analysis
- resource-level variability summaries

# Later, Not Today

Do not implement during the MVP:

- formal variance-function modeling
- hierarchical variance decomposition
- production thresholds
- production database filters
- automatic exclusion logic
- ML anomaly detection
- generalized schema-harmonization infrastructure
- complex interactive dashboards

# Coding Agent Guardrails

## Agility / schema-review guardrails

- Treat the compatibility audit as **LLM / human reasoning**, not a script deliverable.
- Do not write a schema-audit framework unless explicitly requested.
- Do not require every characterization analysis to be compatible before proceeding.
- If one analysis requires significant special handling, mark it `DEFER` and continue.
- Keep `TARGET_ANALYSES` configurable.
- Prefer a small explicit adapter over generalized harmonization code.

## Data safety

- Never mutate source data.
- Never delete observations.
- Never overwrite QC flags.
- Never silently exclude rows.
- Every omitted row / group must have an explicit reason.

## Statistical transparency

- Every flag must record method, threshold, and applicability.
- Statistical flag ≠ bad data.
- High RSD ≠ proof that one replicate is wrong.
- Never use between-sample or between-resource spread as analytical precision.
- Never calculate raw SD across independent samples and call it method precision.
- Do not invent final cutoffs from observed distributions.

## No premature absolute-vs-relative branching

- Calculate both SD and RSD for all eligible replicate clusters.
- Carry both into summaries.
- Do not automatically assign a production error model.
- Do not suppress analyses based on an early SD-vs-RSD judgment.
- Treat SD / RSD behavior as information for human review.

## Replicate integrity

- `sample_id` is essential.
- Do not pool independent samples of one resource into a technical replicate group.
- Do not combine labs / methods / protocols without explicit justification.
- Preserve source record IDs.

## Resource / matrix handling

- Keep resource / matrix as metadata in the first pass.
- Do not default to `analysis × parameter × resource` thresholds.
- Do not interpret large resource heterogeneity as poor method precision.
- Recommend matrix stratification only if selected diagnostics show a plausible pattern and enough data exist.

## Plotting control

- No plots for every method × parameter by default.
- Build the whole-dataset heatmap first.
- Limit detailed plots to approximately 5–10 combinations.
- Record why each was selected.

## Complexity control

- Build one generic downstream analysis pipeline.
- Keep normalization adapters simple.
- ROUT must not block completion.
- Do not implement ROUT from scratch during MVP.
- Do not implement 2s / 3s modeling before human review.
- No ML.
- No elaborate variance or hierarchical models.
- No generalized schema engine.

## Debugging / time-risk control

If a step causes a time-consuming bug:

1. Decide whether it is required for the MVP.
2. If optional, skip it and record:
   ```text
   status = not_calculated
   reason = ...
   ```
3. Continue downstream.
4. Prefer simple, transparent calculations.
5. Never block the pipeline on schema harmonization, ROUT, plotting cosmetics, matrix stratification, or advanced statistics.

## Reproducibility

- Keep code modular.
- Use clear function names.
- Use deterministic outputs.
- Record new dependency versions.
- Prefer common scientific Python packages.
- Comment statistical assumptions.
- Save derived outputs under `outputs/`.
- Make analysis scope configurable rather than rewriting code.

# Suggested Structure

```text
biocirv_outlier_assessment/
│
├── README.md
├── analysis_config.py
├── normalize_inputs.py
├── 01_build_replicate_summary.py
├── 02_build_method_parameter_summary.py
├── 03_build_review_heatmap.py
├── 04_selected_diagnostics.py
├── 05_compare_candidate_rules.py
│
└── outputs/
    ├── replicate_group_summary.csv
    ├── sample_level_summary.csv
    ├── method_parameter_summary.csv
    ├── candidate_rule_comparison.csv
    ├── flagged_cases_for_review.csv
    ├── precision_review_heatmap.png
    └── plots_selected/
```

`normalize_inputs.py` should remain simple. It is not intended to become a generalized ETL framework.

# Scientific Decisions After the MVP

The coding agent should **not** choose these.

The human team will decide:

1. whether triplicates remain the default
2. what should trigger rerun
3. where an RSD criterion is appropriate
4. whether absolute SD, relative precision, or concentration dependence matters for particular methods
5. whether matrix modifies analytical precision
6. whether Dixon / ROUT adds value beyond RSD
7. whether 2s / 3s analysis is worth a second phase
8. how statistical flags interact with analyst QC
9. what evidence is sufficient for exclusion from analysis-ready views
