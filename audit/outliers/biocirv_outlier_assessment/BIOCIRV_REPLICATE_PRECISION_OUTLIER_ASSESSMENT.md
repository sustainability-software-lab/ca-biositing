# BioCirV Exploratory Outlier & Variance Analysis Report

**Status:** Synthesis of a completed Exploratory Outlier & Variance Analysis (Steps 0–10). This analysis summarizes and cross-references the existing, frozen Step 0–10 outputs.

This document is a colleague-facing synthesis of the BioCirV **Exploratory Outlier & Variance Analysis**, which investigated technical-replicate precision and compared candidate outlier/high-variance screens across BioCirV's characterization data. It is exploratory work intended to inform human review and does not implement, recommend, or finalize any production QC threshold, rerun policy, or database filter.

---

## 1. Executive Summary

The analysis examined **2,712 technical-replicate groups** spanning six characterization analysis families (`xrf`, `icp`, `proximate`, `compositional`, `ultimate`, `xrd`) extracted from BioCirV's raw, unfiltered data. Its purpose was to characterize how consistently repeated measurements of the same sample agree with one another, and to compare several candidate statistical screens for flagging replicate groups that show unusually large or unusual disagreement.

**Broad picture of replicate precision.** Typical (median) replicate precision is good to excellent for most well-populated analysis families. See the analysis-type precision table in Section 3 for the full quantitative breakdown. Precision is not uniform: several `xrf` trace elements, several `icp` elements' upper tails, and a handful of low-concentration/near-detection-limit `compositional` sugars show materially higher typical or tail variability, and a few analysis families (`ultimate`, `xrd`) have too little replicate data to draw firm precision conclusions at all. Sparse data should not be read as "high precision."

**Analysis families / parameters needing attention.** No single analysis family is uniformly "poor." Specific `xrf` trace elements (rubidium, copper, strontium, uranium, molybdenum, potassium, manganese, zinc, barium, cerium, praseodymium, thorium) show flag rates several times the dataset-wide baseline. `icp` shows reasonable median precision but extreme upper-tail RSD for elements including titanium, neodymium, aluminum, and sodium. `proximate` ash shows a modestly elevated flag rate; volatile solids and total solids contribute meaningful review-queue counts despite flag rates *below* the dataset-wide baseline (their large denominators, not disproportionate unreliability, drive their raw counts). `compositional` xylan and xylose are modestly elevated; arabinan/arabinose show high enrichment but rest on very small samples (n=7).

**Review backlog.** Combining three candidate screens (RSD > 20%, Dixon's Q at α = 0.05, and an exploratory pooled 3×SD comparator), **427 of 2,712 replicate groups (15.7%) were flagged by at least one screen.** The three screens answer different statistical questions and largely do not agree with one another — this is expected, not evidence that any one screen is "wrong."

**Concentration of the review burden.** The 427-group backlog is highly concentrated: a single `experiment_id` (47) accounts for 59.5% of all flags at an elevated flag rate (27.5%, 1.74× the overall 15.7% baseline); a second (`experiment_id` 43) adds another 14.3%. Five additional `analysis_type × parameter` combinations bring cumulative, non-overlapping coverage to **90.6%** of the entire 427-group backlog using only seven review targets.

**A statistical flag is not proof of bad data.** Throughout this analysis, a flag from RSD, Dixon, or the exploratory 3×SD comparator identifies a replicate group **worth reviewing**. It does not, on its own, establish that any individual measurement is erroneous, and it does not justify excluding or deleting an observation.

---

## 2. Methods and Scope

### Scope of the Exploratory Outlier & Variance Analysis

This analysis focused exclusively on **characterization measurements** — `xrf`, `icp`, `proximate`, `compositional`, `ultimate`, and `xrd` analyses of physical samples/resources. It did **not** evaluate bioconversion or process-performance data (e.g., biogas yield, digestion performance), which follows a fundamentally different data shape and was out of scope from the outset.

A seventh characterization analysis, `calorimetry`, was scoped for potential inclusion but currently has **0 rows** in the extracted dataset and therefore contributes no findings here — it is schema-compatible and will be evaluated once data exists.

The analysis used a **point-in-time extracted snapshot** of BioCirV's raw, unfiltered database (`extract_raw_data.py` → `data/raw_extract_20260825.csv`, 6,155 rows), deliberately bypassing the pre-filtered audit-target views (which drop `qc_pass == 'fail'` rows, apply compositional/proximate sum-range filters, an ICP max-ppm filter, and hard-coded resource exclusions) because a replicate-precision and outlier study needs to see exactly the rows those filters would otherwise hide. This means the analysis reflects a snapshot, not a live query — it is **not** wired into the production BioCirV database, and no repeatable/automated pipeline against the staging or production database currently exists. Building such a repeatable workflow (rerun on a schedule or on demand against the staging database) is identified as future work, not something already implemented.

### How the analysis activities built on each other

Steps 0–10 progressively built one shared, auditable pipeline. Script and output filenames retain their original Step numbering for traceability; this table is the one place in this report where Step numbers are used prominently.

| Step | Script(s) | Activity | Goal / question answered |
|---|---|---|---|
| 0 | `00_validate_replicate_grouping.py` | Validate the replicate-grouping key | Does grouping raw rows by `sample_id + analysis_type + parameter + unit + method + experiment_id` produce a sound, non-broken definition of a "technical replicate group"? (2,712 groups confirmed) |
| 1 | `01_build_replicate_summary.py` | Build the replicate-group summary | For every replicate group, compute n, mean, standard deviation (SD), and relative standard deviation (RSD). Produces `replicate_group_summary.csv` (2,712 rows), the base table for everything downstream. |
| 2 | `02_build_sample_level_summary.py` | Build the sample-level summary | One level up from Step 1 (collapsing across `experiment_id`): separates *pooled* (within + between experiment) variability from *between-experiment* variability for the same sample, so that inter-experiment disagreement is not silently mixed into "technical replicate" precision. |
| 3 | `03_add_candidate_flags.py` | Add candidate replicate-level flags | Enrich the Step 1 table in place with RSD-benchmark flags (>10%, >20%), a classical Dixon's Q test (single-pass, flag-only, α = 0.05), and an explicit ROUT placeholder status (ROUT was never implemented). |
| 4 | `04_build_method_parameter_summary.py` | Build the analysis × parameter summary | Pool the 2,712 replicate groups into 74 `analysis_type × parameter` combinations, characterizing typical and tail precision (median/Q1/Q3/P90/P95 RSD, median SD) and flag rates per combination. |
| 5 | `05_build_review_heatmap.py` | Build the review heatmap | Render a descriptive, non-recomputing heatmap of the Step 4 table. |
| 6 | `06a_build_precision_model_diagnostics.py`, `06b_build_precision_model_heatmap.py`, `07_selected_diagnostics.py` | Characterize relative-vs-absolute error behavior | For each of the 74 combinations, classify whether replicate error behaves more like 1) constant absolute error, 2) constant relative error, 3) mixed concentration-dependent behavior, or 4) is unclear/insufficiently supported using log-log slope and R² with Spearman-correlation corroboration. Render one annotated diagnostic figure per non-trivial category. |
| 8 | `08_compare_candidate_rules.py` | Compare candidate screens | Quantify applicability, overlap, and disagreement among RSD > 20%, Dixon's Q, and an exploratory pooled 3×SD comparator across all 2,712 groups. |
| 9 | `09_build_review_queue.py`, `09b_analyze_backlog_concentration.py` | Characterize the review backlog and consolidate into investigations | Assemble the union of all three screens' flags into a single 427-group review queue; characterize where flags concentrate (analysis × parameter, analysis type, experiment, resource, provider, sample preparation method, existing QC status); consolidate into 114 investigation packets; estimate hypothetical review workload. |
| 10 | `10_build_review_priorities.py` | Build human-review priorities | Rank a small number of non-overlapping, high-coverage review targets so that a limited set of investigations addresses most of the 427-group backlog. |

*(Step 7 refers to the same selected-diagnostics work folded into Step 6's findings above — `07_selected_diagnostics.py` produces the diagnostic figures referenced in the Step 6 row.)*

---

## 3. Precision Findings

### What variability at different grains tells us

Replicate precision can be examined at several nested grains, and each answers a different question:

- **Replicate group** — within-sample technical repeatability. Asks how consistently the *same physical sample* is measured under the *same* analysis/parameter/preparation/experiment conditions. This is the finest grain and the primary unit of this analysis.
- **Independent sample** — distinguishes within-sample analytical variability from differences among separate physical samples. Between-sample variation can reflect genuine material heterogeneity (a real biological/physical property of the resource) and should not automatically be read as analytical error.
- **Analysis × parameter** — pools many replicate groups for one specific measurement (e.g., `xrf/rb`), characterizing what precision typically looks like for that measurement across the whole dataset.
- **Analysis type** — a higher-level view of whether precision concerns are broadly distributed across an entire analytical family (e.g., all of `xrf`) or concentrated in a handful of its parameters.

This matters because a bare statement like "SD = 3" is not inherently meaningful in isolation — its significance depends on the parameter's units, its concentration/value range, what precision is normally expected for that kind of measurement, and whether replicate error for that parameter behaves more like *constant absolute error* or *constant relative error* (addressed in Section 4). It is equally important to keep the limits of this analysis in view: between-sample or between-resource variability is not automatically measurement error; a precision distribution describes a population of replicate groups, not any single observation; and sparse replicate evidence (e.g., `n=1` groups, or combinations with very few RSD-defined groups) cannot support strong precision conclusions no matter how the summary statistic looks.

### Metrics used to characterize precision

The table below preserves the column definitions used throughout the Step 4 analysis × parameter summary (`outputs/method_parameter_summary.csv`). Not all metrics are discussed in downstream tables. See the .csv for full findings. 

| Metric | Definition / denominator | How to interpret it |
|---|---|---|
| `n_replicate_groups` | Count of replicate groups pooled into this `analysis_type × parameter` combination. | Larger n supports more reliable summary statistics; small n (e.g., <10) should be treated cautiously. |
| `n_independent_samples` | Count of distinct `sample_id` values contributing. | Indicates how many separate physical samples underlie the combination, distinct from replicate count. |
| `replicate_n_counts` | Distribution of `n_replicates` per group, e.g. `"1:12, 2:5, 3:40"`. | Shows how much of the combination's data is singleton (SD/RSD undefined) vs. multi-replicate. |
| `median_replicate_n` | Median `n_replicates` across the combination's groups. | A quick summary of typical replicate depth. |
| `min_sample_mean` / `max_sample_mean` / `sample_mean_span` | Range of the per-group mean across the combination. | Indicates concentration range covered — **not** a precision metric. |
| `median_SD` / `Q1_SD` / `Q3_SD` | Median/Q1/Q3 of absolute standard deviation across groups (NaN-skipping; singleton groups excluded, never coerced to 0). | Absolute-unit dispersion. **Not comparable across parameters with different units** (e.g., % vs. ppm). |
| `median_RSD` / `Q1_RSD` / `Q3_RSD` / `P90_RSD` / `P95_RSD` | Median/Q1/Q3/90th/95th percentile of relative (%) dispersion across groups (NaN-skipping). | Unit-agnostic — comparable across parameters. `P90`/`P95` reveal upper-tail behavior a median can hide. |
| `n_RSD_defined` / `percent_RSD_defined` | Count/% of groups where RSD is computable (requires `n_replicates ≥ 2` and a non-near-zero mean). | Low `percent_RSD_defined` means the RSD statistics for that combination rest on limited evidence. |
| `percent_RSD_gt_10` / `percent_RSD_gt_20` | % of **RSD-defined** groups exceeding 10%/20% RSD. | Exploratory comparison benchmarks only — not adopted BioCirV production thresholds. |
| `n_Dixon_calculated` / `percent_Dixon_calculated` | Count/% of groups where Dixon's Q was applicable (`3 ≤ n_replicates ≤ 30`). | Low applicability (e.g., 0% for all of `icp`) means Dixon simply cannot evaluate that combination under the current replicate design. |
| `percent_Dixon_flagged` | % of **Dixon-calculated** groups flagged at α = 0.05. | A within-group, single-extreme-value screen — see Section 5. |
| `percent_ROUT_flagged` | Always `NaN`. | ROUT was never implemented in this analysis; this column is retained only so its absence is explicit, never fabricated. |

Two qualifications carry through every table in this section: absolute SD retains each parameter's own units and must not be compared across unrelated parameters, and singleton (`n_replicates == 1`) groups have undefined SD/RSD by construction. They were never coerced to zero.

### Precision by analysis type

| Analysis | Overall precision | Typical precision across parameters | Main issue | Parameters needing attention | Frontend implication |
|---|---|---|---|---|---|
| Proximate | Generally strong | Total solids, moisture, and volatile solids all run at very low median RSD (0.31–1.05%); ash is somewhat higher (4.40%). All four parameters are close to fully RSD-defined (81.7–100%). | Ash's flag rate (18.3%, 1.16×) is modestly elevated; volatile solids and total solids contribute meaningful *counts* to the review queue (14 and 13 groups) despite flag *rates below* the 15.7% baseline (12.2%/0.77×, 11.3%/0.72×) — their large denominator (115 groups each), not disproportionate unreliability, drives their raw contribution. | ash (mild); note that VS/TS queue presence ≠ poor overall precision | Present proximate parameters as generally reliable; an ash-specific caveat is reasonable, but VS/TS should not inherit a caveat merely from queue-count presence. |
| XRF | Highly heterogeneous | Matrix/major elements (ca, k, p, s, si, th, zn) sit in a tight 2–6% median-RSD band; several trace elements (ba 16.4%, mg 16.2%, mo 15.7%, pr 15.2%, ce 12.3%) run much higher, consistent with expected behavior near detection limits. | XRF's analysis-type-level flag rate (19.3%, 1.23×) is only modestly above baseline — its 59.5% share of the raw 427-group queue is driven mainly by it being the largest analysis family (48.5% of all 2,712 groups), not by uniquely poor per-group precision. Specific parameters are, however, substantially more enriched (rb 3.66×, cu 3.00×, sr 2.82×, u 2.65×, mo 1.91×, k 1.73×, mn/zn 1.62×). | rb, cu, sr, u, mo, k, mn, zn, ba, ce, pr, th | Do not issue a blanket XRF caveat; reserve parameter-specific caveats for the enriched trace elements above. |
| ICP | Reasonable at the median, long tails for specific elements | Most element median RSDs sit at 1.2–5.3%. | P90/P95 RSD "blow out" for several elements despite adequate coverage: `ti` (P90=P95=141.4%, 58.3% RSD-defined), `nd` (P90=57.8%, P95=130.1%, 100% RSD-defined). ICP also has **0% Dixon applicability dataset-wide** (n_replicates never reaches 3 under the current replicate design), so Dixon provides no signal for any ICP parameter. | ti, nd, al, na | Avoid a single universal ICP precision statement; median-only framing would hide the real upper-tail risk for these elements. |
| Compositional | Strong for major sugars, weaker for trace sugars | glucan, glucose, lignin, xylan, xylose all run tight (median RSD ~1–2%). | arabinan/arabinose run notably higher (~6.5% median RSD) and are the two lowest-concentration, lowest-n sugars (spans of ~0.03–4 vs. tens for glucan/xylan) — precision appears to degrade near detection limits, but n=7 for each is thin evidence. xylan/xylose show modestly elevated flag rates (1.21×, 1.06×). | arabinan, arabinose (sparse-evidence caveat), xylan/xylose (mild) | Summarize typical strong precision for major sugars; flag arabinan/arabinose as sparse-evidence rather than firmly "imprecise." |
| Ultimate | Insufficient evidence, not "high precision" | 57 total groups across the analysis type; several parameters (`carbon`, `oxygen`) have only 1 replicate group each; `dm` has only 1 of 13 groups RSD-defined (7.7%); `adf-r`/`cf` have 4 of 13 (30.8%); `nitrogen` has 5 of 14 (35.7%). Zero flags were raised across all of `ultimate`. | Zero flags reflects near-total structural inapplicability (too few multi-replicate groups), not demonstrated precision. | All ultimate parameters — sparse-evidence caveat | Present as "limited replicate evidence," never as "high precision," per the guardrail below. |
| XRD | Insufficient evidence | Only 10 replicate groups total (`crystallinity`); the smallest analysis-type population in the dataset. Zero flags. | Same sparse-evidence caveat as ultimate. | crystallinity | Present as "limited replicate evidence." |

🚩 **Flagged for further discussion:** Twelve `xrf` trace parameters (`ag`, `bi`, `cd`, `cr`, `hg`, `nb`, `ni`, `sb`, `se`, `sn`, `v`, `w`) have `percent_RSD_defined = 0%` because every replicate group for these parameters currently has exactly one replicate. RSD/SD can never be computed for these parameters without a change to the replicate design, independent of how much additional sample volume is collected. Whether triplicate runs for these (and for `icp`, where Dixon is entirely inapplicable) would be worth the added cost is a design question for the team, not something this analysis can resolve.


### Precision by analysis × parameter

The characterization dataset spans **74 distinct `analysis_type × parameter` combinations**. The table below is a representative subset, ordered by contribution to the combined review backlog (the same 427-group union of RSD>20/Dixon/3×SD flags used throughout this report), together with each combination's flag rate and its enrichment relative to the dataset-wide 15.7% baseline flag rate. The complete 74-row table appears in the Appendix (Section 10, Table A1).

| analysis_type | parameter | n_replicate_groups | n_flagged_groups | flag_rate % | enrichment vs 15.7% baseline |
|---|---|---:|---:|---:|---:|
| xrf | rb | 52 | 30 | 57.7 | 3.66x |
| xrf | cu | 55 | 26 | 47.3 | 3.00x |
| xrf | sr | 54 | 24 | 44.4 | 2.82x |
| xrf | u | 55 | 23 | 41.8 | 2.65x |
| proximate | ash | 115 | 21 | 18.3 | 1.16x |
| xrf | k | 55 | 15 | 27.3 | 1.73x |
| proximate | volatile solids | 115 | 14 | 12.2 | 0.77x |
| xrf | mn | 55 | 14 | 25.5 | 1.62x |
| xrf | zn | 55 | 14 | 25.5 | 1.62x |
| compositional | xylan | 68 | 13 | 19.1 | 1.21x |
| proximate | total solids | 115 | 13 | 11.3 | 0.72x |
| xrf | ba | 55 | 12 | 21.8 | 1.38x |
| xrf | mo | 40 | 12 | 30.0 | 1.91x |
| compositional | xylose | 66 | 11 | 16.7 | 1.06x |
| icp | al | 24 | 7 | 29.2 | 1.85x |
| icp | na | 24 | 7 | 29.2 | 1.85x |
| icp | ti | 24 | 6 | 25.0 | 1.59x |
| compositional | arabinose | 7 | 3 | 42.9 | 2.72x |

*(This is a subset selected for narrative usefulness — largest raw contributors, most-enriched parameters, and parameters called out elsewhere in this report. The full 74-row table with all combinations, including the 51 combinations that contributed zero flags, is in Appendix Table A1.)*

🚩 **Flagged for further discussion:** The `xrf` trace elements with the highest Dixon flag rates (rb, sr, u, cu) and the `icp` elements with the most extreme upper-tail RSD (ti, nd, al, na) are strong candidates for additional replicate collection and/or analyst review. Their signal is robust (adequate n, in most cases fully RSD-defined), not a small-sample artifact, so it warrants attention rather than dismissal as noise.

🚩 **Flagged for further discussion:** `compositional/arabinose` and `arabinan` show the highest enrichment values in the entire 74-row table (2.72x and 1.82x) but rest on only 7 replicate groups each. Before treating these as a genuine precision concern, additional replicate data for these two low-concentration sugars would materially strengthen (or weaken) the finding.


---

## 4. Relative vs. Absolute Error Behavior

### Why distinguish relative and absolute variability?

Two different questions can be asked about a replicate group's spread:

- **RSD / relative variability** — how large is replicate disagreement *relative to* the magnitude of the measurement?
- **SD / absolute variability** — how large is replicate disagreement on the measurement's *absolute* scale (its own units)?

The distinction matters because values near zero can produce very high RSD despite modest absolute differences (a classic low-concentration artifact); some measurements may have roughly constant absolute error across their whole concentration range; others may have error that scales with concentration (roughly constant relative error); and some show mixed or ambiguous behavior. There is no reason to expect one universal error model (all-relative or all-absolute) to fit every `analysis_type × parameter` combination in this dataset — and the evidence below confirms it does not.

| What you see | Best interpretation |
|---|---|
| SD flat; RSD decreases with mean | Absolute-SD-like |
| SD rises with mean; RSD flat | Relative/RSD-like |
| Both strongly depend on mean | Neither simple model fits |
| Neither clearly depends on mean | Could be either; possibly too little range/data |
| High RSD mostly near zero | Possible low-concentration artifact; inspect as absolute SD |

### Observed precision-model behavior

Each of the 74 `analysis_type × parameter` combinations was classified into one of five categories using a log-log slope/R² heuristic on mean vs. SD, corroborated by Spearman correlation (mean vs. SD, mean vs. RSD) rather than a blanket R² gate:

| Category | Count | Named example(s) |
|---|---:|---|
| Insufficient data | 26 | `compositional/lignin+` (n=4 replicate groups, n_points_usable_for_loglog=4 — just below the MIN_N_FOR_LOGLOG=5 fitting threshold; no slope/R² could be computed, but this is the combination closest to being fittable in this category) |
| Unclear | 10 | `proximate/total solids` (largest n in category, R²=0.085, slope=−0.696) |
| Concentration-dependent mixed | 20 | `xrf/zn` (slope=0.529, R²=0.438, n=41 — representative) |
| Approximately constant relative RSD | 13 | `icp/ca` (best of 13, R²=0.886, slope=1.056, n=30) |
| Approximately constant absolute SD | 5 | `compositional/xylan`, `compositional/xylose`, `icp/si`, `xrf/k`, `proximate/volatile solids` (best: `proximate/volatile solids`, n=115, slope=−0.091, R²=0.006, Spearman=−0.289) |

**Only a minority (5 of 74) of combinations clearly support a constant-absolute-SD model.** The majority behave more like relative error (13), mixed concentration-dependence (20), unclear behavior (10), or lack sufficient replicate evidence to classify at all (26). This is a direct empirical caution against assuming one universal absolute-SD or relative-RSD error model applies dataset-wide. Review of absolute-SD graphs may reveal their flagging was due to outliers or other graphical features that disproportionately impacted the categorization defining parameters. Removal of outlier/erroneous data could also change the slope and R² values enough to change classifications.

Four existing diagnostic figures (one representative example per non-trivial category) are available for visual review. See the Appendix (Section 10) for embedded images and captions. Each figure contains two side-by-side subplots (mean vs. SD, mean vs. RSD), labels high-leverage points with their `replicate_group_id`, and displays a title reading "PROPOSED precision_model_category: {category}" together with the underlying log-log slope/R² diagnostics and an explicit "not a validated statistical cutoff" caveat.

🚩 **Flagged for further analysis:** Manually review of mixed and unclear diagnostic plots before assigning an analysis × parameter to a relative- or absolute-error model.

🚩 **Flagged for further analysis:** During visual diagnostic review, consider noting unusually extreme RSD>20 / 3×SD points replicate-group IDs (labeled) so conspicuous cases can be traced directly back to source records.

---

## 5. Candidate Outlier & High-Variance Screens

### What question does each screen ask?

- **RSD > 10% / RSD > 20%** — *Does this replicate group have unusually large overall disagreement relative to its own mean?* RSD is a relative, within-group statistic; it only uses that one group's own values and mean.
- **Dixon's Q** — *Does one individual measurement appear unusually extreme relative to the other measurements in this same replicate group?* Dixon is also within-group, but focuses on a single extreme value rather than the group's total spread. This is a genuinely different question from RSD.
- **3× pooled within-replicate SD (exploratory only)** — *Does an individual value deviate unusually far, on an absolute scale, relative to the historical within-replicate precision observed for this `analysis_type × parameter`?* This is the only *cross-group, absolute-scale* comparator among the three; it borrows a pooled SD from every SD-defined replicate group sharing that combination. It is explicitly **exploratory only, not a proposed production threshold** given that most parameter x analysis combinations do not support absolute standard deviation constancy.

### Screen applicability and review burden

Not every screen can evaluate every replicate group; raw flag counts are misleading without knowing each screen's own applicable denominator. **Note on the shared RSD denominator:** RSD > 10% and RSD > 20% intentionally share the same 1,955-group "applicable population" — both thresholds are two different cutoffs applied to the *same* underlying RSD-defined population (any group with a computable RSD is applicable to both).

| Screen | Flagged (count) | % of all 2,712 groups | Applicable population | % of 2,712 for which screen is applicable | % of applicable population flagged |
|---|---:|---:|---:|---:|---:|
| RSD > 10% | 407 | 15.0% | 1,955 (RSD-defined) | 72.1% | 20.8% |
| RSD > 20% | 177 | 6.5% | 1,955 (RSD-defined, same population as RSD > 10%) | 72.1% | 9.1% |
| Dixon (α=0.05) | 246 | 9.1% | 1,447 (Dixon-applicable) | 53.4% | 17.0% |
| 3×SD (pooled, exploratory) | 51 | 1.9% | 1,966 (3×SD-applicable) | 72.5% | 2.6% |

Dixon has **0% applicability across the entire `icp` analysis type** (518 groups) — `n_replicates` never reaches 3 for ICP under the current replicate design, so Dixon cannot be evaluated for a single ICP replicate group, independent of how much ICP data exists.

### Agreement and disagreement among screens

| Category | Count | % of 427 | % of 2,712 |
|---|---:|---:|---:|
| Dixon only | 224 | 52.5% | 8.3% |
| RSD20 only | 140 | 32.8% | 5.2% |
| 3×SD only | 23 | 5.4% | 0.8% |
| RSD20 + 3×SD (not Dixon) | 18 | 4.2% | 0.7% |
| RSD20 + Dixon (not 3×SD) | 12 | 2.8% | 0.4% |
| All three | 7 | 1.6% | 0.3% |
| Dixon + 3×SD (not RSD20) | 3 | 0.7% | 0.1% |
| Flagged by any | 427 | 100% | 15.7% |
| Flagged by none | 2,285 | — | 84.3% |

Only 7 groups (0.3% of 2,712) were flagged by all three methods simultaneously. Genuine three-way agreement is rare. **Low overlap is expected because the screens answer different statistical questions; it is not evidence that one method is "wrong."** 

Dixon-only is the single largest category, consistent with Dixon most often firing on an isolated extreme value in an otherwise low-spread group, a pattern RSD (overall group spread) and 3×SD (an absolute, cross-group threshold) do not necessarily also catch.

**Connecting 3×SD back to Section 4:** the 3×SD comparator's implicit assumption, that replicate error is well described by a constant absolute SD for a given `analysis_type × parameter` , is only clearly supported for 5 of 74 combinations (Section 4). This gives limited empirical justification for treating 3×SD as a broadly appropriate absolute-scale screening model; it remains useful here purely as an exploratory point of comparison against RSD and Dixon, not as a candidate production rule.

🚩 **Flagged for further discussion:** Which signal or combination of signals should eventually trigger routine analyst review?

---

## 6. Review Backlog and Investigation Prioritization

### Size and composition of the review backlog

**427 of 2,712 replicate groups (15.7%) were flagged by at least one of RSD>20, Dixon, or the exploratory 3×SD screen.** The flag-category breakdown (Section 5) shows Dixon-only as the largest single category (52.5% of the queue), RSD-only second (32.8%), and all pairwise/triple combinations together making up the remaining ~15%.

### Where flags are concentrated

See [Precision by analysis × parameter](#precision-by-analysis--parameter) above for the full per-combination and per-analysis-type breakdown (flagged counts, flag rates, and enrichment vs. the 15.7% baseline); this section focuses on cross-cutting concentration patterns not already covered there — experiment_id, provider, sample preparation method, and existing QC status.

**Other review dimensions** The table below merges the Step 10 priority-order targets (rows 1–7, which achieve 90.6% true set-union cumulative coverage of the 427-group backlog) with additional Step 9 supporting-context dimension cuts (rows 8–11, not promoted to standalone Step 10 targets because they are redundant with or subsumed by an already-selected target).

| analysis | parameter | experiment_id | provider | sample_preparation_method | all groups | flagged groups | % of 427 | flag rate | enrichment vs baseline | cumulative % | source |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| — | — | 47 | — | — | 925 | 254 | 59.5% | 27.5% | 1.74x | 59.5% (Priority 1) | Step 9 + Step 10 |
| — | — | 43 | — | — | 336 | 61 | 14.3% | 18.2% | 1.15x | 73.8% (Priority 2) | Step 9 + Step 10 |
| proximate | ash | — | — | — | 115 | 21 | 4.9% | 18.3% | 1.16x | 78.7% (Priority 3) | Step 10 |
| proximate | volatile solids | — | — | — | 115 | 14 | 3.3% | 12.2% | 0.77x | 82.0% (Priority 4) | Step 10 |
| compositional | xylan | — | — | — | 68 | 13 | 3.0% | 19.1% | 1.21x | 85.0% (Priority 5) | Step 10 |
| proximate | total solids | — | — | — | 115 | 13 | 3.0% | 11.3% | 0.72x | 88.1% (Priority 6) | Step 10 |
| compositional | xylose | — | — | — | 66 | 11 | 2.6% | 16.7% | 1.06x | 90.6% (Priority 7) | Step 10 |
| xrf (all params) | — | — | — | — | 1,315 | 254 | 59.5% | 19.3% | 1.23x |  | Step 9 only |
| — | — | — | rigging | — | 178 | 55 | 12.9% | 30.9% | 1.96x | subsumed in experiment_id=47 (41/254) | Step 9 only |
| — | — | — | — | knife mill (2mm) | 952 | 197 | 46.1% | 20.7% | 1.31x |  | Step 9 only |
| — | — | — | — | oven dry + knife mill (2mm) | 590 | 144 | 33.7% | 24.4% | 1.55x |  | Step 9 only |

Rows 1–7 use true set-union cumulative coverage (verified zero overlap between the five analysis × parameter rows and the two experiment_id rows) so the final 90.6% is not double-counted. Rows 8–11 are non unique: `xrf` overlaps heavily with experiment 47's own sub-focus list; the `rigging` provider is already 41-of-254 inside the experiment 47 target and so was not made a separate row; `provider` and `sample_preparation_method` were considered but rejected as standalone Step 10 targets for being redundant with, or too small relative to, the selected targets.

**Experiment 47 sub-focus** (254 groups): `xrf/rb`=30, `cu`=26, `sr`=24, `u`=23, `k`=15, `mn`=14, `zn`=14, `mo`=12, `ba`=12, `ca`=11 — these 10 parameters make up 181/254 (71%) of experiment 47's flags, each 100% contained within experiment 47, with a Dixon_only-dominant flag-category mix.

**Experiment 43 sub-focus** (61 groups): `icp/p`=8, `al`=7, `na`=7, `ti`=6, `cu`=6, `fe`=5, `si`=5, `nd`=5, `s`=4, `zn`=3 — all 61 flagged groups are `icp`, with an RSD_only-dominant mix (87%), a notably different signature from experiment 47's Dixon-dominant pattern.

**`existing_QC_status` overlap** (descriptive only):

| existing_QC_status | n_flagged | % of 427 | n_total | flag_rate |
|---|---:|---:|---:|---:|
| pass | 390 | 91.3% | 1,994 | 19.6% |
| (missing) | 14 | 3.3% | 83 | 16.9% |
| fail | 12 | 2.8% | 233 | 5.2% |
| fail,pass | 7 | 1.6% | 8 | 87.5% |
| pass,provisional | 4 | 0.9% | 4 | 100.0% |

Values such as `fail,pass` and `pass,provisional` are **mixed within replicate group QC statuses**, comma-joined distinct statuses observed across the underlying records of that one replicate group, not standalone QC categories. Their apparently striking 87.5%/100.0% flag rates rest on tiny denominators (8 and 4 groups) and are better read as a small number of interesting candidates for direct human review than as strong statistical evidence. Groups already marked `fail` are actually flagged at a *lower* rate (5.2%) than the dataset average (15.7%). This may be due to other reasons than variance being cause of QC fail statu, showing statistical screening and existing QC do not simply reproduce one another. 

### Consolidating cases into investigations

The provisional grouping key `analysis_type + parameter + experiment_id` was chosen after comparing several alternatives:

| grouping_key | n_packets | median_group_size | max_group_size | n_singleton_packets | % singleton |
|---|---:|---:|---:|---:|---:|
| base (analysis_type+parameter+experiment_id) | 114 | 2.0 | 30 | 53 | 46.5% |
| +resource_id | 340 | 1.0 | 5 | 273 | 80.3% |
| +provider | 297 | 1.0 | 6 | 211 | 71.0% |
| +sample_preparation_method | 144 | 2.0 | 18 | 69 | 47.9% |
| all metadata dims combined | 379 | 1.0 | 4 | 338 | 89.2% |

Adding more metadata dimensions rapidly fragments the backlog into mostly singleton packets, defeating the purpose of consolidation.

**Documented limitation, preserved as-is:** `experiment_id` is a convenient review-grouping key. The available data do **not** establish that it corresponds to a specific common day/run/batch or a validated shared root cause. It is a provisional simplification for organizing review, not a proven investigation unit.

### Human-review priorities

The merged priority table above ("Other review dimensions") key practical finding is that **seven non-overlapping review targets (2 `experiment_id`s and 5 `analysis_type × parameter` combinations) collectively address 90.6% of the entire 427-group backlog** (387 of 427 unique replicate groups), calculated such that any group belonging to more than one target would be counted only once. This means a small number of coherent investigations can, in principle, address most of the backlog.

🚩 **Flagged for further discussion:** Is `analysis_type + parameter + experiment_id` actually a useful investigation grain for the analysts who will conduct review?

🚩 **Flagged for further discussion:** What is a reasonable analyst review load? The answer depends not only on case count but on how much friction the review interface and documentation workflow create.

---

## 7. Report Summary for Analysts

**Different flags imply different review questions.** A high RSD flag calls for investigating large *overall* replicate disagreement within a group. A Dixon flag calls for investigating whether a single, potentially isolated extreme replicate is responsible for that group's spread. A 3×SD flag calls for investigating an unusual *absolute* deviation relative to the historical within-replicate precision for that analysis × parameter, but remember 3xSD comparator's exploratory status and its limited empirical support (only 5 of 74 combinations behave like constant-absolute-SD; Section 4).

**Flags need contextual review.** A statistical flag alone is not enough information to disposition a case. An analyst reviewing a flagged replicate group will typically need the individual replicate values, source record IDs, existing QC status/notes, experiment context, resource/sample context, and relevant preparation/method metadata together in one place. This report does not prescribe a specific interface to do this, only that the flag by itself is insufficient.

**Existing QC and statistical screening are complementary, not redundant.** The large majority of statistically flagged groups (91.3%) already carry an `existing_QC_status` of `pass`. This does not mean existing QC was wrong; it means statistical screening surfaces forms of replicate disagreement that the existing QC field does not currently represent.

**Investigation grain remains provisional.** The `analysis_type + parameter + experiment_id` packet structure used to consolidate 427 flagged groups into 114 investigation packets  may be useful, but remains an unruly workload. Some experimentation may be required to determine the most efficient way to select, evaluate and mark-as-analysis-ready swaths of data.  

🚩 **Flagged for further discussion:** Is the proposed investigation-packet grain useful to analysts?

🚩 **Flagged for further discussion:** What information must be visible together in an analyst-review interface to make disposition fast and credible?

🚩 **Flagged for further discussion:** What recurring review workload is operationally acceptable?

---

## 8. Report Summary for Frontend Data Visualization

Frontend communication of precision/variability findings should remain clearly distinct from backend statistical QC screening. **A statistical flag should not be displayed to end users as "bad data."** Instead, these findings can inform how BioCirV communicates expected precision, parameter-specific variability, evidence sufficiency, and relevant methodological context.

| Finding in analysis | Possible frontend treatment |
|---|---|
| Typical precision well characterized | Ordinary presentation; precision context/metadata if useful |
| Parameter shows elevated or long-tailed variability | Parameter-specific variability caveat |
| Sparse replicate evidence | Indicate limited precision evidence rather than implying high precision |
| Relevant methodological/preparation differences | Provide methodological context where useful |
| Individual statistical flag | Backend review signal; do not automatically label as bad data |

**XRF.** XRF warrants substantial parameter-specific consideration, but not a blanket warning — its overall flag rate (19.3%) is only modestly above baseline. Emphasis should fall on specific elevated-enrichment parameters (rb, cu, sr, u, mo, k, mn, zn, and others identified in Section 3), not on XRF as a whole.

**ICP.** Typical median precision is reasonable for most ICP elements, but several show important upper-tail variability (ti, nd, al, na) that a single, universal ICP precision statement would obscure. Frontend messaging should avoid collapsing ICP into one precision claim.

**Proximate.** Several major parameters (total solids, moisture, volatile solids) show strong typical repeatability while still contributing flagged cases driven substantially by dataset size rather than poor reliability. Presence in the human-review queue should not be equated with poor user-facing reliability for these parameters; ash carries a more warranted, though still modest, caveat.

**Compositional.** Major structural sugars (glucan, glucose, lignin, xylan, xylose) show strong typical precision; arabinan and arabinose are the exception, showing higher variability that likely reflects proximity to detection limits, but on only 7 replicate groups each. A sparse-evidence caveat is more appropriate than a firm "high variability" claim.

**Sparse evidence.** For `ultimate`, `xrd`, and other sparsely replicated measurements, the frontend (and any internal messaging) should distinguish "limited evidence about precision" from "high precision". The current zero-flag result for these analyses reflects insufficient multi-replicate data to evaluate, not demonstrated reliability.

🚩 **Flagged for further discussion:** Which precision/variability information is useful to BioCirV users versus appropriate only for internal QC?

🚩 **Flagged for further discussion:** Should frontend caveats be defined at the analysis level, analysis × parameter level, or only after analyst disposition of individual cases?

🚩 **Flagged for further discussion:** How should insufficient replicate evidence be represented so absence of evidence is not mistaken for evidence of high precision?

---

## 9. Data Quality Due Diligence Questions for Further Discussion

This Exploratory Outlier & Variance Analysis demonstrates that BioCirV can quantify replicate precision at measurement-specific grains; that different statistical signals identify complementary, largely non-redundant review candidates; that the resulting review burden is measurable (427 of 2,712 groups, 15.7%); that this burden is concentrated enough to prioritize a small number of coherent investigations (90.6% coverage from seven targets); and that none of these statistical signals, independently, proves that any observation is erroneous.

**Proposed Data Quality Due Diligence principle** (proposed only — not a claim that production infrastructure already implements it): *BioCirV preserves raw observations, screens analysis-ready data for predefined quality signals, and uses flagged cases to prioritize documented human review. Statistical flags initiate due diligence; they do not independently establish that a measurement is erroneous or justify deletion.*

Relevant unresolved decisions intentionally not settled in this report include: which signals should trigger review; what evidence analysts should inspect for disposition; what constitutes sufficient disposition/documentation; what review burden is operationally acceptable; and which findings should remain backend-only versus become frontend-facing context.

🚩 **Flagged for further discussion:** What exactly should a BioCirV "Data Quality Due Diligence Guarantee" promise?

---

## 10. Appendix: Supporting Tables and Figures

### Table A1 — Complete analysis × parameter flag/enrichment table (all 74 combinations)

Source: `outputs/candidate_rule_comparison.csv` joined with `outputs/review_queue_by_analysis_parameter.csv`. Sum of `n_flagged_groups` = 427 (verified). Sorted by `n_flagged_groups` descending.

| analysis_type | parameter | n_replicate_groups | n_flagged_groups | flag_rate % | enrichment vs 15.7% baseline |
|---|---|---:|---:|---:|---:|
| xrf | rb | 52 | 30 | 57.7 | 3.66x |
| xrf | cu | 55 | 26 | 47.3 | 3.00x |
| xrf | sr | 54 | 24 | 44.4 | 2.82x |
| xrf | u | 55 | 23 | 41.8 | 2.65x |
| proximate | ash | 115 | 21 | 18.3 | 1.16x |
| xrf | k | 55 | 15 | 27.3 | 1.73x |
| proximate | volatile solids | 115 | 14 | 12.2 | 0.77x |
| xrf | mn | 55 | 14 | 25.5 | 1.62x |
| xrf | zn | 55 | 14 | 25.5 | 1.62x |
| compositional | xylan | 68 | 13 | 19.1 | 1.21x |
| proximate | total solids | 115 | 13 | 11.3 | 0.72x |
| xrf | ba | 55 | 12 | 21.8 | 1.38x |
| xrf | mo | 40 | 12 | 30.0 | 1.91x |
| compositional | xylose | 66 | 11 | 16.7 | 1.06x |
| proximate | moisture | 115 | 11 | 9.6 | 0.61x |
| xrf | ca | 55 | 11 | 20.0 | 1.27x |
| xrf | ce | 45 | 10 | 22.2 | 1.41x |
| xrf | th | 55 | 10 | 18.2 | 1.16x |
| compositional | glucan | 68 | 8 | 11.8 | 0.75x |
| compositional | glucose | 66 | 8 | 12.1 | 0.77x |
| icp | p | 50 | 8 | 16.0 | 1.02x |
| xrf | pr | 49 | 8 | 16.3 | 1.04x |
| compositional | lignin | 66 | 7 | 10.6 | 0.67x |
| icp | al | 24 | 7 | 29.2 | 1.85x |
| icp | na | 24 | 7 | 29.2 | 1.85x |
| xrf | p | 55 | 7 | 12.7 | 0.81x |
| xrf | si | 55 | 7 | 12.7 | 0.81x |
| icp | cu | 37 | 6 | 16.2 | 1.03x |
| icp | fe | 37 | 6 | 16.2 | 1.03x |
| icp | ti | 24 | 6 | 25.0 | 1.59x |
| xrf | mg | 37 | 6 | 16.2 | 1.03x |
| icp | nd | 24 | 5 | 20.8 | 1.32x |
| icp | si | 24 | 5 | 20.8 | 1.32x |
| xrf | fe | 55 | 5 | 9.1 | 0.58x |
| icp | s | 37 | 4 | 10.8 | 0.69x |
| xrf | la | 48 | 4 | 8.3 | 0.53x |
| xrf | pb | 35 | 4 | 11.4 | 0.72x |
| compositional | arabinose | 7 | 3 | 42.9 | 2.72x |
| icp | zn | 37 | 3 | 8.1 | 0.51x |
| xrf | s | 55 | 3 | 5.5 | 0.35x |
| compositional | arabinan | 7 | 2 | 28.6 | 1.82x |
| icp | mn | 37 | 2 | 5.4 | 0.34x |
| xrf | al | 36 | 2 | 5.6 | 0.36x |
| xrf | nd | 32 | 2 | 6.2 | 0.39x |
| xrf | ti | 44 | 2 | 4.5 | 0.29x |
| xrf | y | 12 | 2 | 16.7 | 1.06x |
| icp | ca | 50 | 1 | 2.0 | 0.13x |
| icp | k | 50 | 1 | 2.0 | 0.13x |
| icp | mg | 50 | 1 | 2.0 | 0.13x |
| xrf | as | 11 | 1 | 9.1 | 0.58x |
| compositional | lignin+ | 4 | 0 | 0.0 | 0.00x |
| icp | b | 13 | 0 | 0.0 | 0.00x |
| ultimate | adf-r | 13 | 0 | 0.0 | 0.00x |
| ultimate | carbon | 1 | 0 | 0.0 | 0.00x |
| ultimate | cf | 13 | 0 | 0.0 | 0.00x |
| ultimate | dm | 13 | 0 | 0.0 | 0.00x |
| ultimate | nitrogen | 14 | 0 | 0.0 | 0.00x |
| ultimate | oxygen | 1 | 0 | 0.0 | 0.00x |
| ultimate | sulfur | 2 | 0 | 0.0 | 0.00x |
| xrd | crystallinity | 10 | 0 | 0.0 | 0.00x |
| xrf | ag | 10 | 0 | 0.0 | 0.00x |
| xrf | bi | 10 | 0 | 0.0 | 0.00x |
| xrf | cd | 10 | 0 | 0.0 | 0.00x |
| xrf | co | 26 | 0 | 0.0 | 0.00x |
| xrf | cr | 10 | 0 | 0.0 | 0.00x |
| xrf | hg | 10 | 0 | 0.0 | 0.00x |
| xrf | nb | 10 | 0 | 0.0 | 0.00x |
| xrf | ni | 10 | 0 | 0.0 | 0.00x |
| xrf | sb | 10 | 0 | 0.0 | 0.00x |
| xrf | se | 10 | 0 | 0.0 | 0.00x |
| xrf | sn | 10 | 0 | 0.0 | 0.00x |
| xrf | v | 10 | 0 | 0.0 | 0.00x |
| xrf | w | 12 | 0 | 0.0 | 0.00x |
| xrf | zr | 12 | 0 | 0.0 | 0.00x |

Key cross-checks: volatile solids and total solids are both below baseline (0.77×, 0.72×) despite meaningful absolute counts (14, 13), driven by their shared large denominator (115 groups). The highest single enrichment values in the table are `compositional/arabinose` (2.72×, n=7 — small-denominator caveat applies) and `xrf/rb` (3.66×, n=52 — a robust denominator).

### Table A2 — Top parameters by individual screen (extended)

| Screen | Rank 1 | Rank 2 | Rank 3 | Rank 4 | Rank 5 |
|---|---|---|---|---|---|
| RSD > 20 rate (≥5 RSD-defined) | xrf/pr 44.4% (n=18) | icp/ti 42.9% (n=14) | xrf/mo 42.9% (n=21) | xrf/ce 39.1% (n=23) | icp/na 33.3% (n=21) |
| Dixon rate (≥5 Dixon-applicable) | xrf/rb 75.7% (n=37) | xrf/sr 56.4% (n=39) | xrf/u 54.8% (n=42) | xrf/cu 43.2% (n=44) | compositional/arabinose 42.9% (n=7) |
| 3×SD rate (≥10 3×SD-applicable) | xrf/ca 6.7% (n=45) | xrf/la 5.6% (n=18) | xrf/sr 4.7% (n=43) | compositional/glucose 4.5% (n=66) | xrf/si 4.4% (n=45) |

### Table A4 — Precision-model diagnostics: supplementary detail

- ICP median RSDs mostly sit at 1.2–5.3%, but P90/P95 blow out for specific elements: `icp/ti` P90=P95=141.4% (n=14, 58.3% RSD-defined); `icp/nd` P90=57.8%, P95=130.1% (n=24, 100% RSD-defined) — the median alone hides these tails.
- `icp/na` special case: the RSD sign fix corrected 13 negative-mean replicate groups; corrected figures are median RSD=8.32%, %RSD>10=42.9%, %RSD>20=33.3%, P90/P95 RSD=103.1%/147.2%.
- Ash/moisture/total solids/volatile solids precision detail: ash median SD=0.1888, median RSD=4.40%, %RSD>10=22.6%, %RSD>20=4.3%, n_RSD_defined=115 (100%); moisture median SD=0.1145, median RSD=0.99%, %RSD>10=1.06%, %RSD>20=1.06%, n_RSD_defined=94 (81.7%); total solids median SD=0.1823, median RSD=0.31%, %RSD>10=0.87%, %RSD>20=0.0%, n_RSD_defined=115 (100%); volatile solids median SD=0.3522, median RSD=1.05%, %RSD>10=6.96%, %RSD>20=3.48%, n_RSD_defined=115 (100%).

### Figure catalog

All paths are relative to `audit/outliers/biocirv_outlier_assessment/` (this report's own directory).

**Descriptive coverage/precision heatmap** — one row per `analysis_type × parameter`, showing data coverage and RSD/Dixon flagging rates. Not for choosing QC thresholds or ranking parameters by absolute SD; the `median_SD` column is deliberately non-color-ranked since absolute SD units differ by parameter.

![Precision review heatmap](outputs/precision_review_heatmap.png)

**Precision-model category heatmap** — one row per `analysis_type × parameter`, showing the discrete `precision_model_category` label. `insufficient_data` rows show blank/gray cells. These are exploratory triage categories, not validated statistical models or production QC rules.

![Precision model heatmap](outputs/precision_model_heatmap.png)

**Selected diagnostic plots** (one representative example per non-trivial `precision_model_category`; each contains two side-by-side subplots — mean vs. SD, mean vs. RSD — with high-leverage points labeled by `replicate_group_id`, a "PROPOSED precision_model_category" title, and log-log slope/R² diagnostics with a "not a validated statistical cutoff" caveat):

![proximate / volatile solids — approx_constant_absolute_SD (best of 5, n=115)](outputs/plots_selected/proximate_volatile_solids_approx_constant_absolute_SD.png)

![icp / ca — approx_constant_relative_RSD (best of 13, R²=0.886, n=30)](outputs/plots_selected/icp_ca_approx_constant_relative_RSD.png)

![xrf / zn — concentration_dependent_mixed (representative, slope=0.529, R²=0.438, n=41)](outputs/plots_selected/xrf_zn_concentration_dependent_mixed.png)

![proximate / total solids — unclear (representative, n=115, R²=0.085)](outputs/plots_selected/proximate_total_solids_unclear.png)

---

*End of report.*
