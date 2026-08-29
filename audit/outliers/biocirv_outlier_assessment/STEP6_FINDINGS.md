## Addendum — RSD sign-bug fix + `classify_precision_model()` redesign

**Two fixes were applied after this document's original analysis below (see
git history for `01_build_replicate_summary.py` and
`06a_build_precision_model_diagnostics.py`):**

1. **`RSD_percent` sign bug fix (Step 1).** `01_build_replicate_summary.py`
   previously computed `RSD_percent = (sd / mean) * 100.0`, using the
   *signed* mean. For the 13 `icp/na` replicate groups with a negative
   `mean` (a legitimate outcome of background/blank subtraction upstream),
   this produced **negative** RSD% values — contrary to the standard
   convention that RSD is a non-negative dispersion measure — which
   corrupted every downstream RSD-based comparison for `icp/na`
   specifically (RSD benchmark flags, `spearman_mean_vs_RSD` correlation,
   and any RSD quantile/percentile touching those 13 rows). The fix uses
   `abs(mean)` in the denominator instead. Only `icp/na` rows were
   affected (13 of 2712 replicate groups, 0.48%); all other combinations'
   RSD values were computed from positive means and are numerically
   unchanged by this fix.
2. **`classify_precision_model()` redesign (Step 6a).** The prior
   categorization function gated the stability categories
   (`approx_constant_absolute_SD`, `approx_constant_relative_RSD`) behind
   a blanket `loglog_r_squared >= 0.3` check. This was self-defeating: a
   genuinely flat/no-trend SD-vs-mean pattern naturally produces *both* a
   near-zero slope *and* a low R² (there's little real variance for a
   log-log fit to explain when there's no real trend), so the old gate
   made `approx_constant_absolute_SD` nearly unreachable for real flat
   data — **0 of 74 combinations** qualified under the old logic (see
   original §2 below). The redesigned function drops the R² gate for the
   stability categories entirely and instead corroborates each stability
   pattern independently via the corresponding Spearman correlation
   magnitude (`spearman_mean_vs_SD` for absolute-SD, `spearman_mean_vs_RSD`
   for relative-RSD) being small (`<= 0.3`). The R² threshold is retained,
   but repurposed and lowered (`0.3` → `0.15`, per audit review of the
   actual 74-row R² distribution) to distinguish
   `concentration_dependent_mixed` from `unclear` only.

### Category distribution: before vs after

| Category | Before (RSD bug + old classifier) | After (both fixes applied) |
|---|---:|---:|
| `insufficient_data` | 26 | 26 |
| `unclear` | 25 | 10 |
| `concentration_dependent_mixed` | 13 | 20 |
| `approx_constant_relative_RSD` | 10 | 13 |
| `approx_constant_absolute_SD` | **0** | **5** |

**`approx_constant_absolute_SD` now has 5 real members** —
`compositional/xylan`, `compositional/xylose`, `icp/si`, `xrf/k`, and
`proximate/volatile solids` — directly resolving the design flaw this
document's original §5/§6 flagged (zero qualifying examples, forcing
`07_selected_diagnostics.py` to pick a non-qualifying `xrf/sr` placeholder;
see original text below, left unmodified as the historical record of that
finding). A large share of the old `unclear` bucket (15 of 25 combinations)
reclassified into either a stability category or
`concentration_dependent_mixed` — consistent with §5's observation below
that "the `unclear` / `concentration_dependent_mixed` categories are
genuine grab-bags" and that the simple log-log heuristic was likely missing
real structure.

Combination directly affected by the RSD-sign fix: `icp/na` (the only
combination with any negative-mean replicate groups) stays classified as
`concentration_dependent_mixed` both before and after the fix (its
`loglog_slope=0.680`/`loglog_r_squared=0.887` never qualified it for a
stability category or for `unclear` either way), but its
`spearman_mean_vs_RSD` value itself changed substantially: **+0.556**
(p=0.0089, nominally significant) before the fix vs **-0.145** (p=0.529,
not significant) after — a sign flip and a swing from "significant
positive correlation" to "no significant correlation," entirely an
artifact of the RSD-sign bug (13 of `icp/na`'s replicate groups have
negative means, which previously produced negative `RSD_percent` values
that distorted the rank correlation) rather than a real change in the
underlying data. This also materially changed `icp/na`'s `median_RSD` /
`percent_RSD_gt_10` / `percent_RSD_gt_20` in `method_parameter_summary.csv`
and `candidate_rule_comparison.csv` (see `STEP8_FINDINGS.md` addendum for
the exact before/after numbers: `median_RSD` was negative/misleading
before the fix and is now a proper non-negative **8.32%**, with
`percent_RSD_gt_20` rising from a smaller pre-fix count to **33.3%**
post-fix as several previously-negative RSD values flipped sign and
crossed the 20% magnitude threshold).

**This addendum reflects a real pipeline rerun** (Steps 1, 3, 4, 5, 6a, 6b,
8 were all regenerated from the corrected scripts) — it is not a
simulation/preview. `07_selected_diagnostics.py` (the 8-PNG selected-plot
script) was intentionally **not** rerun in this pass and its
`SELECTED_COMBINATIONS` list (including the `xrf/sr` non-qualifying
placeholder discussion in the original §2 below) still reflects the
pre-fix categorization; whether to refresh that script's selections
(e.g., swapping the `xrf/sr` non-qualifying placeholder for one of the 5
newly-qualifying `approx_constant_absolute_SD` combinations) remains an
open follow-up, not addressed here.

Everything below this line is the **original, unmodified** Step 6 findings
document, preserved as the historical record of the pre-fix analysis.

---

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
