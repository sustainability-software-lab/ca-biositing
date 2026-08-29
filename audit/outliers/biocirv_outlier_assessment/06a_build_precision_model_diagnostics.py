"""
06a_build_precision_model_diagnostics.py — comprehensive precision-model
screening step, added beyond the original handoff v4 Step 6.

WHY THIS SCRIPT EXISTS (design rationale):
The handoff's Step 6 only selects 5-10 `analysis_type x parameter`
combinations for detailed diagnostic plots. Inferring absolute-SD-vs-
relative-RSD precision behavior from only 8 examples is too narrow a base
for later human review. This script instead builds a COMPREHENSIVE,
DESCRIPTIVE screen across ALL 74 `analysis_type x parameter` combinations
using simple numerical diagnostics (Spearman rank correlations + a
log-log SD-vs-mean regression), before anyone selects detailed examples.
A later, separate task builds the 8-example detailed plots that visually
validate/explain what this screen finds.

*** EXPLORATORY LABELS ONLY — NOT PRODUCTION QC RULES ***
Every diagnostic and category produced here is a first-pass, descriptive,
human-review aid. Per the handoff's "Core Statistical Principle" and
"Standardization principle" ("calculate broadly first; classify and
narrow later" — do NOT create an early ABSOLUTE-vs-RELATIVE branch that
determines which downstream analysis runs), nothing here is a validated
statistical cutoff or an automatic model-assignment rule. Thresholds used
in `classify_precision_model()` below are simple, documented, exploratory
heuristics chosen for triage convenience only. They must NOT be copied
into `analysis_config.py` or treated as automatic model-assignment logic.
Human review determines whether any given category assignment is
scientifically meaningful for that specific parameter.

Purpose:
Load `outputs/replicate_group_summary.csv` (2712 rows, one row per
technical replicate group), group by `["analysis_type", "parameter"]`
(should yield the same 74 combinations as `method_parameter_summary.csv`),
and for each combination compute:
  - coverage counts (how many rows have usable mean/SD, usable mean/SD for
    log transform, usable mean/RSD)
  - Spearman rank correlations: mean vs SD, mean vs RSD_percent
  - a log-log linear regression of SD on mean (slope + R^2)
  - a descriptive `precision_model_category` label

This step does NOT re-read raw observations and does NOT modify
`replicate_group_summary.csv`, `method_parameter_summary.csv`,
`analysis_config.py`, or any earlier script.

Usage:
    pixi run python audit/outliers/biocirv_outlier_assessment/06a_build_precision_model_diagnostics.py
"""

from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy.stats import linregress, spearmanr

# Make analysis_config importable regardless of CWD.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis_config  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

INPUT_PATH = os.path.join(analysis_config.OUTPUT_DIR, "replicate_group_summary.csv")
METHOD_PARAM_SUMMARY_PATH = os.path.join(
    analysis_config.OUTPUT_DIR, "method_parameter_summary.csv"
)
OUTPUT_PATH = os.path.join(
    analysis_config.OUTPUT_DIR, "precision_model_diagnostics.csv"
)

GROUP_KEYS = ["analysis_type", "parameter"]

EXPECTED_N_COMBINATIONS = 74

# Minimum usable-n guard for Spearman correlations — a simple, conservative
# guard against spurious/unstable correlation coefficients computed on tiny
# samples. Not a statistically derived power calculation, just a documented
# floor: below this, the correlation is set to NaN rather than reported.
MIN_N_FOR_CORRELATION = 5

# Minimum usable-n guard for the log-log regression — same rationale as
# above, applied to the (typically smaller, mean>0 & SD>0 only) log-log
# subset.
MIN_N_FOR_LOGLOG = 5


# ---------------------------------------------------------------------------
# Per-combination diagnostic computation
# ---------------------------------------------------------------------------
def compute_group_diagnostics(group: pd.DataFrame) -> pd.Series:
    """Compute all Step 6a diagnostic fields for one analysis_type x
    parameter group of replicate-group rows.
    """
    n_replicate_groups = len(group)

    mean = group["mean"]
    sd = group["standard_deviation"]
    rsd = group["RSD_percent"]

    # --- Coverage counts ---
    # Usable for correlation: both mean and SD non-null (SD is undefined
    # for singleton replicate groups, n_replicates == 1).
    corr_mask = mean.notna() & sd.notna()
    n_points_usable_for_correlation = int(corr_mask.sum())

    # Usable for log-log: additionally requires strictly positive mean AND
    # SD, since log(0) / log(negative) is undefined. This is a stricter
    # subset than the correlation mask above.
    loglog_mask = mean.notna() & sd.notna() & (mean > 0) & (sd > 0)
    n_points_usable_for_loglog = int(loglog_mask.sum())

    # RSD correlation has its own, separately-tracked usable subset: RSD
    # can be undefined (NaN) even when SD is defined, e.g. near-zero mean
    # causes a divide-by-near-zero blowup/undefined RSD upstream. Use
    # whatever subset has both mean and RSD non-null.
    rsd_corr_mask = mean.notna() & rsd.notna()
    n_points_usable_for_RSD_correlation = int(rsd_corr_mask.sum())

    # --- Spearman correlations (guarded by MIN_N_FOR_CORRELATION) ---
    if n_points_usable_for_correlation >= MIN_N_FOR_CORRELATION:
        spearman_mean_vs_SD, spearman_mean_vs_SD_pvalue = spearmanr(
            mean[corr_mask], sd[corr_mask]
        )
    else:
        # Reason: fewer than MIN_N_FOR_CORRELATION usable points — a
        # correlation coefficient computed on such a tiny sample would be
        # unstable/spurious, so we deliberately report NaN rather than a
        # misleadingly precise-looking number.
        spearman_mean_vs_SD, spearman_mean_vs_SD_pvalue = np.nan, np.nan

    if n_points_usable_for_RSD_correlation >= MIN_N_FOR_CORRELATION:
        spearman_mean_vs_RSD, spearman_mean_vs_RSD_pvalue = spearmanr(
            mean[rsd_corr_mask], rsd[rsd_corr_mask]
        )
    else:
        spearman_mean_vs_RSD, spearman_mean_vs_RSD_pvalue = np.nan, np.nan

    # --- Log-log slope diagnostic (guarded by MIN_N_FOR_LOGLOG) ---
    # Standard log-log variance-function reasoning (not a novel statistical
    # claim): regress log(SD) on log(mean).
    #   slope ~= 0            -> SD roughly constant regardless of
    #                            concentration ("constant absolute SD" /
    #                            homoscedastic in absolute terms)
    #   slope ~= 1            -> SD scales proportionally with
    #                            concentration ("constant RSD")
    #   slope in between, or
    #   very low R^2          -> mixed / unclear behavior
    if n_points_usable_for_loglog >= MIN_N_FOR_LOGLOG:
        log_mean = np.log(mean[loglog_mask])
        log_sd = np.log(sd[loglog_mask])
        fit = linregress(log_mean, log_sd)
        loglog_slope = fit.slope
        loglog_r_squared = fit.rvalue**2
    else:
        # Reason: fewer than MIN_N_FOR_LOGLOG usable (mean>0 & SD>0)
        # points — not enough data for a meaningful log-log fit.
        loglog_slope, loglog_r_squared = np.nan, np.nan

    return pd.Series(
        {
            "n_replicate_groups": n_replicate_groups,
            "n_points_usable_for_correlation": n_points_usable_for_correlation,
            "n_points_usable_for_RSD_correlation": n_points_usable_for_RSD_correlation,
            "n_points_usable_for_loglog": n_points_usable_for_loglog,
            "spearman_mean_vs_SD": spearman_mean_vs_SD,
            "spearman_mean_vs_SD_pvalue": spearman_mean_vs_SD_pvalue,
            "spearman_mean_vs_RSD": spearman_mean_vs_RSD,
            "spearman_mean_vs_RSD_pvalue": spearman_mean_vs_RSD_pvalue,
            "loglog_slope": loglog_slope,
            "loglog_r_squared": loglog_r_squared,
        }
    )


# ---------------------------------------------------------------------------
# Descriptive categorization heuristic
# ---------------------------------------------------------------------------
# *** EXPLORATORY, NON-VALIDATED THRESHOLDS — TRIAGE ONLY ***
#
# The thresholds below (SLOPE_TOLERANCE / SPEARMAN_TOLERANCE = 0.3 as
# "close to 0/1" and "small correlation magnitude" tolerance bands, and
# CONCENTRATION_CLEAR_R_SQUARED_MIN = 0.15 as the "reasonably clear
# concentration relationship" cutoff used ONLY to split
# concentration_dependent_mixed from unclear) are SIMPLE, DOCUMENTED,
# EXPLORATORY HEURISTICS chosen only for descriptive first-pass triage
# across 74 combinations. They are:
#   - NOT validated statistical cutoffs (no power analysis, no calibration
#     against known-good/known-bad precision behavior),
#   - NOT production QC rules,
#   - NOT to be copied into `analysis_config.py`,
#   - NOT an automatic model-assignment mechanism.
# Human review determines whether any given category assignment is
# scientifically meaningful for that specific analysis_type x parameter
# combination. This function only produces a starting label for that
# review, per the handoff's "calculate broadly first; classify and narrow
# later" principle — it is explicitly NOT the "early ABSOLUTE vs RELATIVE
# branch" the handoff warns against building into automated downstream
# routing.
#
# DESIGN FIX (post-hoc, see git history / audit notes for full rationale):
# the two stability categories (approx_constant_absolute_SD,
# approx_constant_relative_RSD) previously required loglog_r_squared >= 0.3
# as a blanket gate BEFORE checking the slope at all. This was
# self-defeating: a genuinely flat/no-trend SD-vs-mean pattern naturally
# produces BOTH a near-zero slope AND a low R^2 (there is little real
# variance for a log-log line to explain when there's no real trend), so
# the old gate made approx_constant_absolute_SD nearly unreachable for real
# flat data (0 of 74 combinations qualified). The R^2 gate is now used
# ONLY to decide whether a non-stability relationship counts as
# "concentration_dependent_mixed" vs "unclear" — the stability categories
# are instead independently corroborated by the corresponding Spearman
# rank correlation magnitude (mean vs SD, or mean vs RSD) being small,
# which is a more direct "no concentration-dependence" check than R^2 of a
# potentially-noisy log-log line.
SLOPE_TOLERANCE = 0.3
SPEARMAN_TOLERANCE = 0.3
# "Reasonably clear concentration relationship" cutoff for
# concentration_dependent_mixed vs unclear (Candidate A: log-log R^2
# threshold). Chosen at 0.15 (rather than the prior 0.3) after reviewing
# the actual 74-row distribution: at 0.3, 17 of 30 contested combinations
# fall to "unclear"; at 0.15, only 10 do, better matching the intent that
# "not a stability pattern, but with a real correlation" should default to
# "mixed" rather than "unclear" for weak-but-nonzero R^2 cases. Candidates
# based on Spearman-magnitude or p-value thresholds were also considered
# (see audit notes) and would materially shift this split — this remains a
# human-adjustable value, not a statistically derived cutoff.
CONCENTRATION_CLEAR_R_SQUARED_MIN = 0.15


def classify_precision_model(
    n_points_usable_for_loglog: int,
    spearman_mean_vs_SD: float,
    spearman_mean_vs_SD_pvalue: float,
    spearman_mean_vs_RSD: float,
    spearman_mean_vs_RSD_pvalue: float,
    loglog_slope: float,
    loglog_r_squared: float,
) -> str:
    """Return one descriptive category label. See module-level comment
    block above for the explicit non-production-cutoff caveat and the
    design-fix rationale for why the stability categories no longer gate
    on loglog_r_squared.

    `spearman_mean_vs_SD_pvalue` / `spearman_mean_vs_RSD_pvalue` are
    accepted for interface completeness / future candidate definitions of
    "reasonably clear concentration relationship" (see audit notes) but are
    not used by the current (Candidate A, R^2-based) implementation.
    """
    if n_points_usable_for_loglog < MIN_N_FOR_LOGLOG:
        return "insufficient_data"

    # These should all be non-NaN whenever n_points_usable_for_loglog >=
    # MIN_N_FOR_LOGLOG (see compute_group_diagnostics), but guard
    # defensively — Spearman NaNs can still occur if that correlation's own
    # usable-n guard (MIN_N_FOR_CORRELATION) failed independently of the
    # log-log usable-n guard.
    required_values = (
        loglog_slope,
        loglog_r_squared,
        spearman_mean_vs_SD,
        spearman_mean_vs_RSD,
    )
    if any(pd.isna(v) for v in required_values):
        return "insufficient_data"

    is_approx_constant_absolute_SD = (
        abs(loglog_slope) <= SLOPE_TOLERANCE
        and abs(spearman_mean_vs_SD) <= SPEARMAN_TOLERANCE
    )
    is_approx_constant_relative_RSD = (
        abs(loglog_slope - 1.0) <= SLOPE_TOLERANCE
        and abs(spearman_mean_vs_RSD) <= SPEARMAN_TOLERANCE
    )

    if is_approx_constant_absolute_SD:
        return "approx_constant_absolute_SD"
    if is_approx_constant_relative_RSD:
        return "approx_constant_relative_RSD"

    # Neither stability pattern holds. If there is a reasonably clear
    # concentration relationship (Candidate A: log-log R^2 clears the
    # bar), call it "mixed"; otherwise it's genuinely unclear/noisy.
    if loglog_r_squared >= CONCENTRATION_CLEAR_R_SQUARED_MIN:
        return "concentration_dependent_mixed"

    return "unclear"


# ---------------------------------------------------------------------------
# Build / validate / summarize
# ---------------------------------------------------------------------------
def build_precision_model_diagnostics(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby(GROUP_KEYS, dropna=False, sort=True)
    diagnostics = grouped.apply(compute_group_diagnostics, include_groups=False)
    diagnostics = diagnostics.reset_index()

    diagnostics["precision_model_category"] = diagnostics.apply(
        lambda row: classify_precision_model(
            row["n_points_usable_for_loglog"],
            row["spearman_mean_vs_SD"],
            row["spearman_mean_vs_SD_pvalue"],
            row["spearman_mean_vs_RSD"],
            row["spearman_mean_vs_RSD_pvalue"],
            row["loglog_slope"],
            row["loglog_r_squared"],
        ),
        axis=1,
    )

    # Column order per task spec.
    column_order = [
        "analysis_type",
        "parameter",
        "n_replicate_groups",
        "n_points_usable_for_correlation",
        "n_points_usable_for_RSD_correlation",
        "n_points_usable_for_loglog",
        "spearman_mean_vs_SD",
        "spearman_mean_vs_SD_pvalue",
        "spearman_mean_vs_RSD",
        "spearman_mean_vs_RSD_pvalue",
        "loglog_slope",
        "loglog_r_squared",
        "precision_model_category",
    ]
    return diagnostics[column_order]


def run_validation(diagnostics_df: pd.DataFrame) -> bool:
    """Confirm 74 rows produced, matching method_parameter_summary.csv's 74
    analysis_type x parameter combinations exactly (set-equality on the
    combination tuples, not just a row-count match).
    """
    print("\n=== Step 6a Validation ===")
    all_pass = True

    n_rows = len(diagnostics_df)
    ok_count = n_rows == EXPECTED_N_COMBINATIONS
    all_pass &= ok_count
    print(
        f"[{'PASS' if ok_count else 'FAIL'}] row count == "
        f"{EXPECTED_N_COMBINATIONS}: got {n_rows}"
    )

    if not os.path.exists(METHOD_PARAM_SUMMARY_PATH):
        print(
            f"*** WARNING: {METHOD_PARAM_SUMMARY_PATH} not found — cannot "
            f"cross-check combination set-equality. ***"
        )
        return all_pass and ok_count

    method_param_df = pd.read_csv(METHOD_PARAM_SUMMARY_PATH)
    expected_combinations = set(
        zip(method_param_df["analysis_type"], method_param_df["parameter"])
    )
    actual_combinations = set(
        zip(diagnostics_df["analysis_type"], diagnostics_df["parameter"])
    )

    ok_set_equal = expected_combinations == actual_combinations
    all_pass &= ok_set_equal
    print(
        f"[{'PASS' if ok_set_equal else 'FAIL'}] combination set matches "
        f"method_parameter_summary.csv exactly"
    )
    if not ok_set_equal:
        missing_from_ours = expected_combinations - actual_combinations
        extra_in_ours = actual_combinations - expected_combinations
        print(f"    *** BUG: missing from our output: {missing_from_ours}")
        print(f"    *** BUG: extra in our output (not in method_parameter_summary.csv): {extra_in_ours}")

    return all_pass


def print_category_distribution(diagnostics_df: pd.DataFrame) -> None:
    print("\n=== precision_model_category distribution ===")
    counts = diagnostics_df["precision_model_category"].value_counts()
    for category, count in counts.items():
        print(f"  {category}: {count}")


def print_example_rows(diagnostics_df: pd.DataFrame) -> None:
    """Print 2-3 example rows showing clearly different categories, to
    demonstrate the categorization logic is working sensibly.
    """
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)

    categories_to_show = [
        "approx_constant_relative_RSD",
        "approx_constant_absolute_SD",
        "concentration_dependent_mixed",
        "unclear",
        "insufficient_data",
    ]

    print("\n=== Example rows across categories ===")
    shown = 0
    for category in categories_to_show:
        subset = diagnostics_df[diagnostics_df["precision_model_category"] == category]
        if len(subset) == 0:
            continue
        # Pick the row with the highest n_points_usable_for_loglog within
        # this category as the clearest example.
        row = subset.loc[subset["n_points_usable_for_loglog"].idxmax()]
        print(f"\n--- category: {category} ---")
        print(row.to_string())
        shown += 1
        if shown >= 3:
            break


def main() -> None:
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(
            f"{INPUT_PATH} not found — run 01_build_replicate_summary.py and "
            f"03_add_candidate_flags.py first."
        )

    # log(0) / log(negative) never reaches numpy.log here because
    # loglog_mask filters to strictly-positive mean/SD before the log
    # transform (see compute_group_diagnostics). This filterwarnings call
    # is a defensive no-op for any unexpected all-NaN slice warnings from
    # pandas aggregation, mirroring the pattern used in
    # 04_build_method_parameter_summary.py.
    warnings.filterwarnings(
        "ignore", message="Mean of empty slice", category=RuntimeWarning
    )

    df = pd.read_csv(INPUT_PATH)
    print(f"Loaded {len(df)} replicate-group rows from {INPUT_PATH}")

    diagnostics_df = build_precision_model_diagnostics(df)
    print(
        f"\nBuilt precision_model_diagnostics with {len(diagnostics_df)} rows "
        f"(distinct analysis_type x parameter combinations)"
    )

    diagnostics_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(diagnostics_df)} rows to: {OUTPUT_PATH}")

    all_pass = run_validation(diagnostics_df)
    if not all_pass:
        print(
            "\n*** VALIDATION FAILURE: one or more checks did not match "
            "expected values. Investigate before treating this output as "
            "final. ***"
        )
    else:
        print("\nAll validation checks passed.")

    print_category_distribution(diagnostics_df)
    print_example_rows(diagnostics_df)


if __name__ == "__main__":
    main()
