# Step 6 Findings — Selected Diagnostic Plots

Script: [`07_selected_diagnostics.py`](07_selected_diagnostics.py)
Inputs: [`outputs/replicate_group_summary.csv`](outputs/replicate_group_summary.csv) (2712 rows),
[`outputs/precision_model_diagnostics.csv`](outputs/precision_model_diagnostics.csv) (74 rows, built by
[`06a_build_precision_model_diagnostics.py`](06a_build_precision_model_diagnostics.py))
Outputs: [`outputs/plots_selected/`](outputs/plots_selected/) (8 PNGs)

## 1. Overview

This step selects a small number of representative `analysis_type ×
parameter` combinations **after** reviewing the comprehensive 74-row
precision-model screen (Step 6a), rather than reusing the original
handoff's pre-fixed 8-combination list. One combination was selected per
non-trivial `precision_model_category` (`approx_constant_absolute_SD`,
`approx_constant_relative_RSD`, `concentration_dependent_mixed`,
`unclear`), and two scatter plots — sample mean vs. replicate SD, and
sample mean vs. replicate RSD — were produced for each, for a total of 8
PNGs.

**Interpretation boundary** (consistent with the rest of this pipeline):
these plots visually validate/explain classifications that already exist
in `precision_model_diagnostics.csv`. They introduce no new statistical
claims and are not a basis for choosing production QC thresholds.

## 2. Selected combinations and reasoning

All 74 rows of `precision_model_diagnostics.csv` were reviewed directly.
Category distribution going in: `insufficient_data`=26, `unclear`=25,
`concentration_dependent_mixed`=13, `approx_constant_relative_RSD`=10,
`approx_constant_absolute_SD`=**0**.

### `xrf / sr` — `approx_constant_absolute_SD` (NON-QUALIFYING, closest available)

Zero of the 74 combinations actually met the automated categorization bar
(`loglog_r_squared >= 0.3` AND `abs(loglog_slope) <= 0.3`) for
`approx_constant_absolute_SD`. Per this task's browsing-only relaxation
(R² ≥ 0.2), candidates and their `abs(loglog_slope)`: `mg` (R²=0.207,
n=17); `sr` (R²=0.258, slope=0.294, n=39); `xrd/crystallinity` (R²=0.214,
slope=−6.47 — excluded, huge |slope|). `xrf/sr` has the smallest
`abs(loglog_slope)` (0.294) among rows with R² ≥ 0.2 and the best-populated
n (39 usable log-log points). Its true `precision_model_category` is
`unclear` (R²=0.258 falls just under the 0.3 clear-fit bar).

**This pick is explicitly non-qualifying** and is labeled as such in its
plot titles, the script's docstring, and here — it must never be read as a
genuine positive example of constant-absolute-SD behavior.

### `icp / ca` — `approx_constant_relative_RSD` (best of 10)

Highest `loglog_r_squared` (0.886, slope=1.056) among the 10 rows actually
classified as `approx_constant_relative_RSD` (next-best: `k` R²=0.876,
`mg` R²=0.791, `al` R²=0.408), with n=30 usable log-log points — a
well-populated sample, not a thin 5–6 point option.

### `xrf / zn` — `concentration_dependent_mixed` (representative)

Slope=0.529 sits cleanly inside the requested 0.4–0.6 "real relationship,
not close to 0 or 1" band, with R²=0.438 and n=41 usable log-log points —
the largest n of any candidate in that slope band (alternatives considered:
`al` slope=0.587/R²=0.321/n=21; `fe` slope=0.606/R²=0.359/n=45).

### `proximate / volatile solids` — `unclear` (large-n control case)

`n_points_usable_for_loglog`=115 — the single largest value in the entire
74-row table — paired with R²=0.006 (essentially no log-log fit) and
slope=−0.091. This is "unclear because the data is genuinely scattered,"
not "unclear because of low n," providing a clean contrast against the
other 3 picks.

## 3. Plot design

Each of the 8 PNGs (`{analysis_type}_{parameter}_mean_vs_SD.png` /
`..._mean_vs_RSD.png` in `outputs/plots_selected/`):

- Plots one point per replicate group (`mean` on x-axis; `standard_deviation`
  or `RSD_percent` on y-axis).
- States the combination's `precision_model_category`, `loglog_slope`, and
  `loglog_r_squared` (read as-is from `precision_model_diagnostics.csv`) in
  the title, framed as "Comprehensive screen classified this as {category}
  (slope=x, R²=y) — visual check." The `xrf/sr` plots additionally state
  the non-qualifying caveat.
- Color-codes points by `resource_type` with a legend when ≤15 distinct
  values are present; falls back to a single color and documents that
  fallback in the subtitle otherwise (all 4 selected combinations in
  practice exceeded 15 distinct `resource_type` values and used the
  fallback — see run results below).
- Explicitly counts and captions NaN-excluded points (singleton replicate
  groups with undefined SD/RSD) rather than silently dropping them.

## 4. Run results

| Combination | Category (role) | Plotted / NaN-excluded | Distinct `resource_type` | Color-coded? |
|---|---|---:|---:|---|
| `xrf / sr` | approx_constant_absolute_SD (non-qualifying) | 43 / 11 | 20 | No (fallback) |
| `icp / ca` | approx_constant_relative_RSD (best) | 30 / 20 | 16 | No (fallback) |
| `xrf / zn` | concentration_dependent_mixed | 45 / 10 | 22 | No (fallback) |
| `proximate / volatile solids` | unclear (large-n control) | 115 / 0 | 40 | No (fallback) |

(Counts are identical for a combination's SD and RSD plot since both share
the same NaN mask for the respective metric column.)

## 5. Observations from reviewing the rendered plots

Visual review of the 8 plots surfaced two useful patterns worth recording
even though they are outside this step's scope to act on:

- **Individual high-leverage outlier points are visible but not
  identified.** Several plots show one or a small handful of points
  sitting well above the bulk of the replicate-group cloud in SD or RSD.
  Because points are currently unlabeled, a reviewer cannot tell *which*
  replicate group (sample, resource, experiment) an outlying point
  corresponds to without cross-referencing `replicate_group_summary.csv`
  by eye — a real friction point for the manual outlier-triage workflow
  this whole pipeline exists to support.
- **The `unclear` / `concentration_dependent_mixed` categories are genuine
  grab-bags.** Both categories are defined only by what they are *not*
  (not a clean fit, or a fit whose slope isn't close to 0 or 1). Visual
  inspection suggests some `unclear`/mixed combinations likely have a
  legitimate absolute-SD or relative-RSD structure that the simple
  log-log heuristic's R²/slope thresholds are just missing (e.g., driven
  by a handful of high-leverage points, non-linear relationships, or
  matrix/resource-type subgroups with different behavior pooled together).
  The current 74-row categorization should not be treated as a finished
  answer for these two categories.

## 6. Future work (not implemented in this step — recorded here per scope boundary)

Both items below are also flagged as future to-dos in the handoff document
(`biocirv_outlier_assessment_handoff_v4.md`, "Future Enhancements Identified
During Step 6 Review" section). They are explicitly **out of scope** for
this step's script and were not implemented in `07_selected_diagnostics.py`.

1. **Label high-leverage points with `replicate_group_id`.** Extend the
   selected-diagnostics plotting (or any future revision of it) to annotate
   individual points with their `replicate_group_id` when either:
   - `RSD_percent > 20`, or
   - `standard_deviation > 2 × median(standard_deviation)` computed within
     that same `analysis_type × parameter` combination (i.e., a per-combination
     median, not a global one, since absolute SD units differ by parameter).

   This would let a reviewer go directly from "that point looks high" to
   "here is the exact replicate group / sample / resource / experiment to
   pull up," closing the gap noted in §5 above.

2. **Human review (or a programmatic threshold refinement) of the
   `unclear` and `concentration_dependent_mixed` categories to
   differentiate into SD-dominant, RSD-dominant, or genuinely-mixed
   behavior.** Either:
   - a human reviewer works through the SD and RSD scatter plots for all
     combinations currently labeled `unclear` (25) or
     `concentration_dependent_mixed` (13) and records a differentiated
     judgment per combination, or
   - the categorization heuristic in
     [`06a_build_precision_model_diagnostics.py`](06a_build_precision_model_diagnostics.py)
     (`classify_precision_model()`, `R_SQUARED_MIN_FOR_CLEAR_FIT=0.3`,
     `SLOPE_TOLERANCE=0.3`) is revisited to see whether adjusted or
     additional decision bounds (e.g., separate SD-only and RSD-only
     log-log fits, rather than a single combined slope/R² pair) can
     programmatically split today's `unclear`/mixed bucket into
     SD-dominant, RSD-dominant, and genuinely-mixed sub-categories.

   Per the handoff's "Scientific Decisions After the MVP" guardrails, any
   changed thresholds remain a human decision, not something a coding
   agent should choose unilaterally.
