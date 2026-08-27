# Step 4 & 5 Findings — Method × Parameter Summary and Review Heatmap

Scripts: [`04_build_method_parameter_summary.py`](../04_build_method_parameter_summary.py),
[`05_build_review_heatmap.py`](../05_build_review_heatmap.py)
Outputs: [`outputs/method_parameter_summary.csv`](method_parameter_summary.csv) (74 rows),
[`outputs/precision_review_heatmap.png`](precision_review_heatmap.png)

## 1. Overview

This document interprets `method_parameter_summary.csv` — 74 distinct
`analysis_type × parameter` combinations, each pooled from
`replicate_group_summary.csv`'s 2712 technical replicate groups (Step 1,
enriched in Step 3) — and its companion visual,
`precision_review_heatmap.png`. Both artifacts summarize replicate-level
precision (SD, RSD) and candidate flag rates (RSD benchmarks, Dixon Q) at
the `analysis_type × parameter` grain; neither recomputes anything from raw
observations.

**Interpretation boundary** (restated from the heatmap script's docstring,
and binding on this document too): this is a **descriptive comparison
tool** for data coverage, typical/high-tail relative precision (RSD-based),
and RSD/Dixon flagging rates across combinations. It must **not** be used
to choose final QC thresholds, decide absolute-SD-vs-relative-RSD precision
models, or rank parameters by absolute SD (units differ across parameters,
e.g., % for compositional analytes vs. ppm for ICP/XRF). Those remain
explicit human-review decisions per the handoff's "Scientific Decisions
After the MVP" section. Every observation below is framed as a candidate
for review, not a proposed cutoff — "statistical flag ≠ bad data."

## 2. Column definitions

| Column | Definition |
|---|---|
| `analysis_type`, `parameter` | Grouping key — one row per distinct combination. |
| `n_replicate_groups` | Count of replicate groups (rows in `replicate_group_summary.csv`) pooled into this combination. |
| `n_independent_samples` | Count of distinct `sample_id` values contributing to those groups. |
| `replicate_n_counts` | Distribution of `n_replicates` across the combination's groups, e.g. `"1:12, 2:5, 3:40"` (n_replicates value : count of groups with that value). |
| `median_replicate_n` | Median `n_replicates` across the combination's groups. |
| `min_sample_mean` / `max_sample_mean` / `sample_mean_span` | Min / max / range (`max − min`) of the per-group `mean` value across the combination — indicates the concentration range covered, not a precision metric. |
| `median_SD` / `Q1_SD` / `Q3_SD` | Median / Q1 / Q3 of `standard_deviation` across groups (NaN-skipping; singleton groups with undefined SD are excluded, never coerced to 0). **Absolute units — not comparable across parameters with different units.** |
| `median_RSD` / `Q1_RSD` / `Q3_RSD` / `P90_RSD` / `P95_RSD` | Median / Q1 / Q3 / 90th / 95th percentile of `RSD_percent` across groups (NaN-skipping). Unit-agnostic (%), comparable across parameters. |
| `n_RSD_defined` / `percent_RSD_defined` | Count / % of the combination's groups where RSD could be computed (requires `n_replicates ≥ 2` and a non-near-zero mean). |
| `percent_RSD_gt_10` / `percent_RSD_gt_20` | % of **RSD-defined** groups exceeding 10% / 20% RSD — comparison benchmarks from Step 3, not proposed BioCirV thresholds. |
| `n_Dixon_calculated` / `percent_Dixon_calculated` | Count / % of groups where Dixon's Q was applicable (`3 ≤ n_replicates ≤ 30`). |
| `percent_Dixon_flagged` | % of **Dixon-calculated** groups flagged at alpha = 0.05. |
| `percent_ROUT_flagged` | Always NaN — ROUT was never implemented in this MVP (handoff guardrail: never fabricate a percentage of an uncalculated quantity). |

## 3. Descriptive interpretation

### Coverage patterns

Coverage is highly uneven across the 74 combinations:

- **Best covered**: all four `proximate` parameters (`ash`, `moisture`,
  `total solids`, `volatile solids`) each have `n_replicate_groups=115`
  from 106 independent samples — the single best-covered analytical
  family. A large block of `xrf` matrix/major elements (`ba`, `ca`, `fe`,
  `k`, `p`, `s`, `th`, `u`, `zn`, and others) each have `n_replicate_groups=55`.
- **Thinnest coverage**: `ultimate/carbon` and `ultimate/oxygen` each have
  only **1 replicate group from 1 sample** — no precision information can
  be drawn from a single group. `ultimate/sulfur` has 2 groups,
  `compositional/lignin+` has 4, and `compositional/arabinan` /
  `arabinose` have 7 each.
- **RSD structurally undefined**: 12 `xrf` trace parameters — `ag`, `bi`,
  `cd`, `cr`, `hg`, `nb`, `ni`, `sb`, `se`, `sn`, `v`, `w` — show
  `percent_RSD_defined = 0.0%`. Their `replicate_n_counts` is uniformly
  `"1:10"` (or `"1:12"` for `w`), meaning every replicate group for these
  parameters has exactly one replicate — RSD/SD can never be computed
  regardless of how much data is added later without a change in
  replicate design.
- **Dixon structurally unavailable for an entire analysis type**: all 15
  `icp` parameters show `n_Dixon_calculated = 0` / `percent_Dixon_calculated
  = 0.0%`. ICP's `replicate_n_counts` tops out at `n_replicates = 2`
  (median_replicate_n = 1.0–2.0 across ICP parameters), and Dixon requires
  `3 ≤ n ≤ 30` — so Dixon is never applicable to ICP under the current
  replicate design, independent of sample count.
- **Ultimate analysis** broadly runs thin even where nominally "defined":
  `ultimate/dm` has `n_RSD_defined=1` of 13 groups (7.7%), `adf-r` and `cf`
  have 4 of 13 (30.8%), `nitrogen` has 5 of 14 (35.7%) — these combinations'
  RSD quantiles are effectively built from a handful of points and should
  be read as point estimates, not real distributions.

### Typical precision patterns

`median_RSD` across the 74 combinations spans from 0% (several
singleton/zero-SD parameters — not a meaningful "perfect precision" signal,
just structurally undefined or trivial) up to 24.51% (`xrf/nd`, but backed
by only 3 RSD-defined groups — see caveats below). Restricting attention to
combinations with a reasonably large RSD-defined sample:

- **Proximate runs tightest**: `total solids` median_RSD = 0.31% (lowest of
  any well-populated combination), `moisture` = 0.99%, `volatile solids` =
  1.05%, `ash` = 4.40% — consistent with these being core mass-balance
  measurements, all with 81.7–100% RSD coverage.
- **Compositional sugars are tight except the least-detected ones**:
  `glucan` (1.48%), `glucose` (1.53%), `lignin` (1.09%), `xylan` (2.12%),
  `xylose` (2.15%) all run low; `arabinan`/`arabinose` run notably higher
  (~6.5% median RSD) — these are also the two lowest-n, lowest-concentration
  sugars (spans of ~0.03–4 vs. tens for glucan/xylan), consistent with
  precision degrading near detection limits.
- **ICP looks fine at the median but has long high-RSD tails**: most ICP
  median RSDs sit in the 1.2–5.3% range, but `P90_RSD`/`P95_RSD` blow out
  for several elements (`ti`: P90=P95=141.4%; `nd`: P90=57.8%, P95=130.1%;
  `al`: P90=57.7%, P95=75.3%) — the median alone would hide these tails.
- **XRF is the most heterogeneous analysis type**: matrix elements (`ca`,
  `k`, `p`, `s`, `si`, `th`, `zn`) sit in a tight 2–6% median-RSD band,
  while several minor/trace elements (`ba` 16.4%, `mg` 16.2%, `mo` 15.7%,
  `pr` 15.2%, `ce` 12.3%, plus the small-n `nd`/`y` cases) run much higher
  — consistent with expected XRF behavior near detection limits for trace
  analytes.

### High-variability tails

The largest `P90_RSD` values with a reasonably solid RSD-defined base
(n≥14) are `icp/ti` (P90=P95=141.42%, n_RSD_defined=14, 58.3% defined) and
`icp/nd` (P90=57.77%, P95=130.11%, n_RSD_defined=24, **100%** defined).
Among `xrf`, `mo` (P90=36.66%, n=21) and `ce` (P90=24.49%, n=23) stand out.
By `percent_RSD_gt_20` with adequate n: `xrf/mo` (42.86%, n=21), `xrf/ce`
(39.13%, n=23), `icp/ti` (42.86%, n=14), `icp/al` (29.17%, n=24, 100%
defined), and `xrf/mg` (29.41%, n=17) are the clearest candidates for
concern.

### RSD/Dixon flagging patterns

Across combinations with adequate RSD coverage, `percent_RSD_gt_10` ranges
from 0% up to extremes such as `xrf/mg` (88.24%, n_RSD_defined=17),
`xrf/ba` (78.38%, n=37), `xrf/mn` (66.67%, n=45), `xrf/ce` (65.22%, n=23),
and `icp/al` (54.17%, n=24, fully RSD-defined). Dixon flag rates show a
largely **different** set of high-flag combinations: `xrf/rb` (75.68%,
n_Dixon_calculated=37), `xrf/sr` (56.41%, n=39), `xrf/u` (54.76%, n=42), and
`xrf/k` (33.33%, n=45) top the Dixon list, none of which are the top RSD
flaggers.

This mismatch previews the candidate-rule-comparison step (Step 8) and is
consistent with Step 3's replicate-group-level finding that RSD>20 and
Dixon flags overlap on only 19 of 2712 groups. At the combination level the
disagreement runs **both directions**:
- `xrf/mg`: RSD flags heavily (88.24% RSD>10, 29.41% RSD>20) while Dixon
  flags almost nothing (7.14% of 14 Dixon-calculated groups).
- `xrf/rb`/`xrf/sr`: the reverse — Dixon flags a majority of groups
  (75.68% / 56.41%) while RSD>10 is comparatively rare (14.29% / 9.30%).

Neither pattern indicates one method is "wrong" — RSD is sensitive to
overall spread while Dixon is sensitive to one point standing out from an
otherwise tight cluster, and these are genuinely different failure modes.

### Data-quality caveats visible in the numbers

- The two smallest combinations, `ultimate/carbon` and `ultimate/oxygen`
  (`n_replicate_groups=1` each), cannot support any distributional
  statistic — their SD=0/RSD=0 reflects a single group, not measured
  precision.
- `xrf/nd` (median_RSD=24.51%, the highest of all 74 rows) and `xrf/y`
  (median_RSD=19.43%, percent_RSD_gt_10=100%) are backed by only 3 and 2
  RSD-defined groups respectively (9.4% and 16.7% `percent_RSD_defined`)
  — their headline numbers are the most extreme in the table but rest on
  the least data, so they should be treated as flagged-for-investigation
  rather than established high-variability parameters.
- `icp/ti`'s P90=P95=141.42% is driven by only 14 RSD-defined groups
  (58.3% of 24) — a single unusual group can dominate a percentile at this
  sample size.
- The 12 `xrf` trace parameters with `percent_RSD_defined=0%` and the
  entire `icp` analysis type with `percent_Dixon_calculated=0%` are not
  data-quality failures per se, but structural consequences of the
  replicate design (n_replicates capped at 1 or 2) — worth flagging to the
  human team as a possible design question (e.g., would triplicate ICP
  runs be valuable for Dixon-style single-outlier detection?) rather than
  an analysis bug.

## 4. Recommended combinations for Step 6 diagnostic review

Per the handoff's Step 6 guidance, the following **8** combinations were
selected using varied, documented reasons (not a single top-N-by-one-metric
list), and were checked for adequate `n_RSD_defined`/`n_Dixon_calculated`
so the resulting scatter plots will have enough points to be visually
informative.

| # | `analysis_type` / `parameter` | Key metric value(s) | Reason |
|---|---|---|---|
| 1 | `icp / al` | median_RSD=12.22%, RSD>10%=54.17%, RSD>20%=29.17%, n_RSD_defined=24 (**100%** defined), n_Dixon_calculated=0 | Highest RSD flag rate among fully RSD-covered ICP parameters, and a clean illustration of an analysis type where Dixon is structurally never calculable. |
| 2 | `xrf / ba` | median_RSD=16.38%, P90_RSD=24.46%, RSD>10%=78.38%, n_RSD_defined=37 (67.3% defined) | Highest median RSD among combinations with a substantively large RSD-defined sample (n≥30) — a "highest RSD" pick that isn't a small-n artifact. |
| 3 | `xrf / mg` | RSD>10%=88.24% (highest of any combo with n_RSD_defined≥10), RSD>20%=29.41%, Dixon flagged=7.14% (n_Dixon_calculated=14) | Largest RSD-high / Dixon-quiet disagreement — RSD-based rules would flag most groups while Dixon flags almost none. |
| 4 | `xrf / rb` | Dixon flagged=75.68% (highest Dixon flag rate of all 74 combos, n_Dixon_calculated=37), median_RSD=2.75%, RSD>10%=14.29% | Highest Dixon flag rate overall, and the mirror-image disagreement case — Dixon flags most groups while RSD would flag almost none. |
| 5 | `xrf / si` | sample_mean_span=157,414.0 (min 252.67 → max 157,666.67), the widest concentration span of all 74 combinations; n_RSD_defined=45 (81.8% defined) | Widest concentration range in the dataset — best candidate to visually check for concentration-dependent precision. |
| 6 | `icp / nd` | n_RSD_defined=24 (**100%** defined), median_RSD=1.03% but P90_RSD=57.77%, P95_RSD=130.11% | Median looks unremarkable but the high-percentile tail is extreme despite full RSD coverage — shows why median alone can hide a real high-variability subgroup. |
| 7 | `compositional / glucan` | n_replicate_groups=68, n_independent_samples=67, 100% RSD-defined, 97.1% Dixon-calculated, median_RSD=1.48% | Strategically important analytical family (core structural-sugar composition feeding downstream bioconversion-yield calculations) with excellent data coverage — worth a baseline diagnostic even without a variability red flag. |
| 8 | `proximate / total solids` | median_RSD=0.31% (lowest of any well-populated combination), RSD>10%=0.87%, RSD>20%=0.0%, n_RSD_defined=115 (**100%** defined) | Intentional low-variability control — the tightest-running, best-covered combination in the dataset, included for contrast against the higher-variability picks above. |

**Deliberately avoided despite topping a metric ranking:** `xrf/nd`
(highest median_RSD in the table, 24.51%) and `xrf/y` (percent_RSD_gt_10 =
100%) were **not** selected even though they lead their respective metrics,
because they are backed by only 3 and 2 RSD-defined groups respectively —
too few points to produce a visually or statistically meaningful sample
mean vs. SD/RSD scatter plot in Step 6. `icp/ti`'s extreme P90/P95 RSD
(141.42%) was considered for the same reason as `icp/nd` but not selected
in favor of `icp/nd`, since `icp/nd` has full (100%) RSD coverage (24 of
24 groups) versus `icp/ti`'s partial coverage (14 of 24, 58.3%), giving a
more robust diagnostic plot for the same "hidden tail" story.
