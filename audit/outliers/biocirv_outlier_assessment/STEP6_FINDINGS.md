# Step 6 Findings — Selected Diagnostic Plots

Script: [`07_selected_diagnostics.py`](07_selected_diagnostics.py)
Inputs: [`outputs/replicate_group_summary.csv`](outputs/replicate_group_summary.csv) (2712 rows),
[`outputs/precision_model_diagnostics.csv`](outputs/precision_model_diagnostics.csv) (74 rows, built by
[`06a_build_precision_model_diagnostics.py`](06a_build_precision_model_diagnostics.py))
Outputs: [`outputs/plots_selected/`](outputs/plots_selected/) (4 PNGs, one combined
figure per selected combination)

## 1. Overview

This step selects a small number of representative `analysis_type ×
parameter` combinations **after** reviewing the comprehensive 74-row
precision-model screen (Step 6a), rather than reusing the original
handoff's pre-fixed 8-combination list. One combination is selected per
non-trivial `precision_model_category` (`approx_constant_absolute_SD`,
`approx_constant_relative_RSD`, `concentration_dependent_mixed`,
`unclear`), and each is rendered as ONE combined figure containing two
side-by-side subplots — sample mean vs. replicate SD on the left, sample
mean vs. replicate RSD on the right — for a total of 4 PNGs. The proposed
`precision_model_category` is displayed as a prominent suptitle at the top
of each figure and is also embedded directly in the output filename (e.g.
`proximate_volatile_solids_approx_constant_absolute_SD.png`), so the
category is visible both when viewing an image and when browsing the
output directory.

**Interpretation boundary** (consistent with the rest of this pipeline):
these plots visually validate/explain classifications that already exist
in `precision_model_diagnostics.csv`. They introduce no new statistical
claims and are not a basis for choosing production QC thresholds.

## 2. Two corrections applied to the underlying pipeline

Two fixes were applied to upstream scripts before this step's current
selections and plots were generated (see git history for
`01_build_replicate_summary.py` and `06a_build_precision_model_diagnostics.py`
for the full commit-level detail):

1. **`RSD_percent` sign fix (Step 1).**
   [`01_build_replicate_summary.py`](01_build_replicate_summary.py:151)
   computes `RSD_percent = (sd / abs(mean)) * 100.0`, using the absolute
   value of the mean in the denominator. Previously the signed mean was
   used, which produced **negative** RSD% values for the 13 `icp/na`
   replicate groups with a negative `mean` (a legitimate outcome of
   background/blank subtraction upstream) — contrary to the standard
   convention that RSD is a non-negative dispersion measure. This
   corrupted every downstream RSD-based comparison for `icp/na`
   specifically (RSD benchmark flags, `spearman_mean_vs_RSD` correlation,
   and any RSD quantile/percentile touching those 13 rows). Only `icp/na`
   rows were affected (13 of 2712 replicate groups, 0.48%); all other
   combinations' RSD values were computed from positive means and are
   numerically unaffected.

2. **`classify_precision_model()` redesign (Step 6a).**
   [`06a_build_precision_model_diagnostics.py`](06a_build_precision_model_diagnostics.py:201)
   no longer gates the stability categories
   (`approx_constant_absolute_SD`, `approx_constant_relative_RSD`) behind
   a blanket `loglog_r_squared >= 0.3` check. That gate was self-defeating:
   a genuinely flat/no-trend SD-vs-mean pattern naturally produces *both*
   a near-zero slope *and* a low R² (there's little real variance for a
   log-log fit to explain when there's no real trend), so the old gate
   made `approx_constant_absolute_SD` nearly unreachable for real flat
   data — 0 of 74 combinations qualified under the old logic. The current
   function instead corroborates each stability pattern independently via
   the corresponding Spearman correlation magnitude
   (`spearman_mean_vs_SD` for absolute-SD, `spearman_mean_vs_RSD` for
   relative-RSD) being small (`<= 0.3`). The R² threshold is retained but
   repurposed and lowered (`0.3` → `0.15`) to distinguish
   `concentration_dependent_mixed` from `unclear` only.

**Current category distribution** (`precision_model_diagnostics.csv`,
regenerated with both fixes applied):

| Category | Count |
|---|---:|
| `insufficient_data` | 26 |
| `unclear` | 10 |
| `concentration_dependent_mixed` | 20 |
| `approx_constant_relative_RSD` | 13 |
| `approx_constant_absolute_SD` | 5 |

`approx_constant_absolute_SD` now has 5 real members —
`compositional/xylan`, `compositional/xylose`, `icp/si`, `xrf/k`, and
`proximate/volatile solids` — where previously zero combinations
qualified, which is why §4 below no longer needs a non-qualifying
placeholder pick for that category.

## 3. Selected combinations and reasoning

All 74 rows of `precision_model_diagnostics.csv` were reviewed directly.
Category counts going in: `insufficient_data`=26, `unclear`=10,
`concentration_dependent_mixed`=20, `approx_constant_relative_RSD`=13,
`approx_constant_absolute_SD`=5.

### `proximate / volatile solids` — `approx_constant_absolute_SD` (best of 5)

Largest `n_points_usable_for_loglog` (115) of any row in the entire 74-row
table, with `loglog_slope=-0.091` and `loglog_r_squared=0.006` (the log-log
fit itself is negligible, consistent with "no real trend to fit") and
`spearman_mean_vs_SD=-0.289` (small magnitude, corroborating "no
concentration-dependence" independent of the noisy log-log fit). A
well-populated, genuine positive example for this category.

### `icp / ca` — `approx_constant_relative_RSD` (best of 13)

Highest `loglog_r_squared` (0.886, slope=1.056) among the 13 rows
classified as `approx_constant_relative_RSD` (next-best: `k` R²=0.876,
`p` R²=0.856, `mg` R²=0.791), with n=30 usable log-log points — a
well-populated sample, not a thin 5–6 point option.

### `xrf / zn` — `concentration_dependent_mixed` (representative)

Slope=0.529 sits cleanly inside the 0.4–0.6 "real relationship, not close
to 0 or 1" band, with R²=0.438 and n=41 usable log-log points — the
largest n of any candidate in that slope band (alternatives considered:
`al` slope=0.587/R²=0.321/n=21; `fe` slope=0.606/R²=0.359/n=45).

### `proximate / total solids` — `unclear` (representative, largest n)

Largest `n_points_usable_for_loglog` (115) of any row remaining in the
`unclear` category, with `loglog_r_squared=0.085` (weak log-log fit) and
`loglog_slope=-0.696` (not close to 0 or 1) — a genuinely ambiguous case,
not a low-n artifact.

## 4. Plot design

Each of the 4 PNGs (`{analysis_type}_{parameter}_{precision_model_category}.png`
in `outputs/plots_selected/` — category is embedded in the filename):

- Contains two side-by-side subplots sharing one figure: mean vs.
  `standard_deviation` on the left, mean vs. `RSD_percent` on the right
  (one point per replicate group, `mean` on the x-axis in both).
- Displays a three-line figure-level title: the combination name (small),
  then **"PROPOSED precision_model_category: {category}"** as the most
  visually prominent line (large, bold — the "PROPOSED" prefix makes clear
  this is an exploratory triage label, not a finalized/validated
  categorization), then the underlying `loglog_slope` / `loglog_r_squared`
  diagnostics (small, italic) with the "not a validated statistical
  cutoff" caveat.
- **Labels high-leverage points with their `replicate_group_id`** directly
  on the plot, so a reviewer can go from "that point looks high" straight
  to the exact replicate group / sample / resource / experiment to pull up
  in `replicate_group_summary.csv`, without needing to cross-reference by
  eye. A point qualifies as high-leverage (evaluated independently per
  combination, using that combination's own `standard_deviation` values)
  when EITHER:
  - `RSD_percent > 20`, or
  - `standard_deviation > 2 × median(standard_deviation)` computed within
    that same `analysis_type × parameter` combination (a per-combination
    median, not a global one, since absolute SD units differ by
    parameter).
- Each subplot independently color-codes points by `resource_type` with a
  legend when ≤15 distinct values are present in that subplot's plotted
  subset; falls back to a single color and documents that fallback in the
  subplot's own caption otherwise (all 4 selected combinations in practice
  exceeded 15 distinct `resource_type` values on both subplots and used
  the fallback — see run results below).
- Explicitly counts and captions NaN-excluded points (singleton replicate
  groups with undefined SD/RSD) and the high-leverage-labeled point count,
  per subplot, rather than silently dropping/omitting them.

## 5. Run results

| Combination | Category (role) | Plotted / NaN-excluded | High-leverage labeled | Distinct `resource_type` | Color-coded? |
|---|---|---:|---:|---:|---|
| `proximate / volatile solids` | approx_constant_absolute_SD (best of 5) | 115 / 0 | 38 | 40 | No (fallback) |
| `icp / ca` | approx_constant_relative_RSD (best of 13) | 30 / 20 | 7 | 16 | No (fallback) |
| `xrf / zn` | concentration_dependent_mixed | 45 / 10 | 10 | 22 | No (fallback) |
| `proximate / total solids` | unclear (largest n in category) | 115 / 0 | 44 | 40 | No (fallback) |

(Counts differ between a combination's SD and RSD subplot only when
`standard_deviation` and `RSD_percent` have different NaN masks, e.g. a
non-near-zero-mean singleton group has both undefined, but a near-zero-mean
multi-replicate group can have a defined SD and an undefined RSD — for
the 4 selected combinations here the two subplots' counts happen to match.
High-leverage counts are also identical between a combination's two
subplots, since the high-leverage flag is computed once per replicate
group from that combination's full data, not independently per metric.)

## 6. Observations from reviewing the rendered plots

Visual review of the 4 combined figures (8 subplots total) surfaced two useful patterns worth recording
even though they are outside this step's scope to act on:

- **High-leverage points are now labeled, but dense low-mean/high-RSD
  clusters can still crowd labels together.** For `proximate/volatile
  solids` and `proximate/total solids` specifically, a large fraction of
  points qualify as high-leverage (38 and 44 of 115 respectively, driven
  mostly by the `RSD_percent > 20` criterion at low sample means where RSD
  is naturally noisier), which produces some visual crowding among
  overlapping `replicate_group_id` labels in that region. `icp/ca` and
  `xrf/zn` (7 and 10 high-leverage points respectively) render cleanly
  with no crowding. This is a consequence of the underlying data's RSD
  distribution at low concentrations, not a defect in the labeling logic
  itself — a future refinement could consider a stricter/tunable
  high-leverage threshold or `adjustText`-style label repulsion if this
  becomes a practical review obstacle.
- **The remaining `unclear` / `concentration_dependent_mixed` categories
  are still genuine grab-bags,** now smaller (10 and 20 combinations
  respectively) than before the classifier redesign but still defined
  largely by what they are *not* (not a stability pattern, and either weak
  or unclassifiable log-log fit). Visual inspection suggests some
  `unclear`/mixed combinations likely have a legitimate absolute-SD or
  relative-RSD structure that the simple log-log heuristic's R²/slope
  thresholds are still missing (e.g., driven by a handful of high-leverage
  points, non-linear relationships, or matrix/resource-type subgroups with
  different behavior pooled together). The current 74-row categorization
  should not be treated as a finished answer for these two categories.

## 7. Future work (not implemented in this step — recorded here per scope boundary)

This item is also flagged as a future to-do in the handoff document
(`biocirv_outlier_assessment_handoff_v4.md`, "Future Enhancements Identified
During Step 6 Review" section). It is explicitly **out of scope** for
this step's script and was not implemented in `07_selected_diagnostics.py`.
(The high-leverage-point-labeling item previously listed here has since
been implemented — see §4 above.)

1. **Human review (or a programmatic threshold refinement) of the
   `unclear` and `concentration_dependent_mixed` categories to
   differentiate into SD-dominant, RSD-dominant, or genuinely-mixed
   behavior.** Either:
   - a human reviewer works through the SD and RSD scatter plots for all
     combinations currently labeled `unclear` (10) or
     `concentration_dependent_mixed` (20) and records a differentiated
     judgment per combination, or
   - the categorization heuristic in
     [`06a_build_precision_model_diagnostics.py`](06a_build_precision_model_diagnostics.py)
     (`classify_precision_model()`, `SLOPE_TOLERANCE=0.3`,
     `SPEARMAN_TOLERANCE=0.3`, `CONCENTRATION_CLEAR_R_SQUARED_MIN=0.15`) is
     revisited to see whether adjusted or additional decision bounds (e.g.,
     separate SD-only and RSD-only log-log fits, rather than a single
     combined slope/R² pair) can programmatically split today's
     `unclear`/mixed bucket into SD-dominant, RSD-dominant, and
     genuinely-mixed sub-categories.

   Per the handoff's "Scientific Decisions After the MVP" guardrails, any
   changed thresholds remain a human decision, not something a coding
   agent should choose unilaterally.
