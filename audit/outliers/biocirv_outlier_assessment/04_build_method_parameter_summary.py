"""
04_build_method_parameter_summary.py — Step 4 (handoff v4, "Summarize by
Analysis Type x Parameter").

Purpose:
Aggregate the existing replicate-group table
(`outputs/replicate_group_summary.csv`, built by `01_build_replicate_summary.py`
and enriched in place by `03_add_candidate_flags.py`) UP ONE LEVEL, grouping
by `["analysis_type", "parameter"]`.

IMPORTANT — this step does NOT re-read raw observations and does NOT
recompute anything from scratch. It pools the already-computed per-group
`mean`, `standard_deviation`, `RSD_percent`, and flag columns from
`replicate_group_summary.csv` (2712 rows, one row per technical replicate
group) into one summary row per `analysis_type x parameter` combination.

Stratification decision (handoff Step 4: "Stratify by lab / method /
protocol only when known differences make pooling inappropriate"):
This MVP pass does NOT stratify by lab/method/protocol_version — everything
is pooled within `analysis_type x parameter`. No known systematic
differences between labs/methods/protocols in this dataset have been
identified that would make pooling inappropriate at this stage; that
judgment is left to human review of this summary table (and later steps),
per the handoff's default behavior.

Guardrails honored:
- Groups over replicate_group_summary.csv rows only — never touches raw
  observations.
- NaN-skipping quantiles for SD/RSD — pandas' default `.median()` /
  `.quantile()` already skip NaN, so singleton-group NaN SDs are correctly
  excluded from SD quantiles (not coerced to 0). This is NOT overridden.
- Explicit division-by-zero guards for `percent_RSD_gt_10`,
  `percent_RSD_gt_20`, and `percent_Dixon_flagged`, whose denominators are
  conditional (n_RSD_defined / n_Dixon_calculated) and can be zero for a
  given analysis_type x parameter combination.
- `percent_ROUT_flagged` is always NaN — ROUT was never calculated (handoff
  Step 3 guardrail: never fabricate a percentage of an uncalculated
  quantity).

Usage:
    pixi run python audit/outliers/biocirv_outlier_assessment/04_build_method_parameter_summary.py
"""

from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pandas as pd

# Some analysis_type x parameter groups consist entirely of singleton
# replicate groups (n_replicates == 1), whose standard_deviation / RSD_percent
# are legitimately NaN (SD is undefined for n=1, per Step 1's design). Taking
# .median()/.quantile() of an all-NaN column is well-defined (NaN result) but
# numpy internally emits a benign "Mean of empty slice" RuntimeWarning during
# that computation. This is expected, harmless, and does NOT indicate a bug —
# suppressing it here keeps script output focused on real issues.
warnings.filterwarnings(
    "ignore", message="Mean of empty slice", category=RuntimeWarning
)

# Make analysis_config importable regardless of CWD.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis_config  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

INPUT_PATH = os.path.join(analysis_config.OUTPUT_DIR, "replicate_group_summary.csv")
OUTPUT_PATH = os.path.join(analysis_config.OUTPUT_DIR, "method_parameter_summary.csv")

GROUP_KEYS = ["analysis_type", "parameter"]

# Expected aggregate validation numbers (from Step 3 findings /
# STEP3_FINDINGS.md) — sanity checks that this step's pooling is faithful
# to the Step 1/3 per-group data, not a recomputation.
EXPECTED_TOTAL_REPLICATE_GROUPS = 2712
EXPECTED_TOTAL_RSD_DEFINED = 1955  # 2712 - 757 RSD-undefined groups
EXPECTED_TOTAL_DIXON_CALCULATED = 1447


def format_replicate_n_counts(n_replicates: pd.Series) -> str:
    """Render the distribution of n_replicates within a group as a compact,
    human-scannable string, e.g. "1:12, 2:5, 3:40" (sorted by n_replicates
    value ascending).
    """
    counts = n_replicates.value_counts().sort_index()
    return ", ".join(f"{int(n)}:{int(c)}" for n, c in counts.items())


def summarize_group(group: pd.DataFrame) -> pd.Series:
    """Compute all Step 4 summary fields for one analysis_type x parameter
    group of replicate-group rows. See module docstring / handoff Step 4
    table for exact field definitions.
    """
    n_replicate_groups = len(group)

    # --- Sample / replicate count fields ---
    n_independent_samples = group["sample_id"].nunique()
    replicate_n_counts = format_replicate_n_counts(group["n_replicates"])
    median_replicate_n = group["n_replicates"].median()

    # --- Sample mean span ---
    min_sample_mean = group["mean"].min()
    max_sample_mean = group["mean"].max()
    sample_mean_span = max_sample_mean - min_sample_mean

    # --- SD quantiles (NaN-skipping is pandas' default; singleton-group
    # NaN SDs are correctly excluded, never coerced to 0) ---
    median_SD = group["standard_deviation"].median()
    Q1_SD = group["standard_deviation"].quantile(0.25)
    Q3_SD = group["standard_deviation"].quantile(0.75)

    # --- RSD quantiles (same NaN-skipping approach) ---
    rsd = group["RSD_percent"]
    median_RSD = rsd.median()
    Q1_RSD = rsd.quantile(0.25)
    Q3_RSD = rsd.quantile(0.75)
    P90_RSD = rsd.quantile(0.90)
    P95_RSD = rsd.quantile(0.95)

    # --- RSD-defined counts ---
    n_RSD_defined = int(rsd.notna().sum())
    percent_RSD_defined = n_RSD_defined / n_replicate_groups * 100

    # --- RSD benchmark flag rates, denominator = n_RSD_defined (NOT
    # n_replicate_groups) — guard against division by zero. ---
    if n_RSD_defined == 0:
        percent_RSD_gt_10 = np.nan
        percent_RSD_gt_20 = np.nan
    else:
        n_rsd_gt_10 = int((group["rsd_gt_10"] == True).sum())  # noqa: E712
        n_rsd_gt_20 = int((group["rsd_gt_20"] == True).sum())  # noqa: E712
        percent_RSD_gt_10 = n_rsd_gt_10 / n_RSD_defined * 100
        percent_RSD_gt_20 = n_rsd_gt_20 / n_RSD_defined * 100

    # --- Dixon calculated / flagged counts ---
    dixon_calculated_mask = group["dixon_status"] == "calculated"
    n_Dixon_calculated = int(dixon_calculated_mask.sum())
    percent_Dixon_calculated = n_Dixon_calculated / n_replicate_groups * 100

    if n_Dixon_calculated == 0:
        percent_Dixon_flagged = np.nan
    else:
        n_dixon_flagged = int(
            (group.loc[dixon_calculated_mask, "dixon_flag_0_05"] == True).sum()  # noqa: E712
        )
        percent_Dixon_flagged = n_dixon_flagged / n_Dixon_calculated * 100

    # --- ROUT — never calculated; never fabricate a percentage of an
    # uncalculated quantity (handoff Step 3 guardrail). ---
    percent_ROUT_flagged = np.nan

    return pd.Series(
        {
            "n_replicate_groups": n_replicate_groups,
            "n_independent_samples": n_independent_samples,
            "replicate_n_counts": replicate_n_counts,
            "median_replicate_n": median_replicate_n,
            "min_sample_mean": min_sample_mean,
            "max_sample_mean": max_sample_mean,
            "sample_mean_span": sample_mean_span,
            "median_SD": median_SD,
            "Q1_SD": Q1_SD,
            "Q3_SD": Q3_SD,
            "median_RSD": median_RSD,
            "Q1_RSD": Q1_RSD,
            "Q3_RSD": Q3_RSD,
            "P90_RSD": P90_RSD,
            "P95_RSD": P95_RSD,
            "n_RSD_defined": n_RSD_defined,
            "percent_RSD_defined": percent_RSD_defined,
            "percent_RSD_gt_10": percent_RSD_gt_10,
            "percent_RSD_gt_20": percent_RSD_gt_20,
            "n_Dixon_calculated": n_Dixon_calculated,
            "percent_Dixon_calculated": percent_Dixon_calculated,
            "percent_Dixon_flagged": percent_Dixon_flagged,
            "percent_ROUT_flagged": percent_ROUT_flagged,
        }
    )


def build_method_parameter_summary(df: pd.DataFrame) -> pd.DataFrame:
    # groupby(..., dropna=False) is not strictly required here since
    # analysis_type/parameter should always be populated, but we pass it
    # for consistency with the same defensive pattern used in Step 1 (see
    # analysis_config.py's REPLICATE_GROUP_KEYS comment).
    grouped = df.groupby(GROUP_KEYS, dropna=False, sort=True)
    summary = grouped.apply(summarize_group, include_groups=False)
    summary = summary.reset_index()
    return summary


def run_validation(replicate_df: pd.DataFrame, summary_df: pd.DataFrame) -> bool:
    """Run the three required validation checks. Returns True iff all pass."""
    print("\n=== Step 4 Validation ===")
    all_pass = True

    sum_n_replicate_groups = int(summary_df["n_replicate_groups"].sum())
    ok1 = sum_n_replicate_groups == EXPECTED_TOTAL_REPLICATE_GROUPS
    all_pass &= ok1
    print(
        f"[{'PASS' if ok1 else 'FAIL'}] sum(n_replicate_groups) == "
        f"{EXPECTED_TOTAL_REPLICATE_GROUPS}: got {sum_n_replicate_groups}"
    )

    sum_n_rsd_defined = int(summary_df["n_RSD_defined"].sum())
    ok2 = sum_n_rsd_defined == EXPECTED_TOTAL_RSD_DEFINED
    all_pass &= ok2
    print(
        f"[{'PASS' if ok2 else 'FAIL'}] sum(n_RSD_defined) == "
        f"{EXPECTED_TOTAL_RSD_DEFINED}: got {sum_n_rsd_defined}"
    )

    sum_n_dixon_calculated = int(summary_df["n_Dixon_calculated"].sum())
    ok3 = sum_n_dixon_calculated == EXPECTED_TOTAL_DIXON_CALCULATED
    all_pass &= ok3
    print(
        f"[{'PASS' if ok3 else 'FAIL'}] sum(n_Dixon_calculated) == "
        f"{EXPECTED_TOTAL_DIXON_CALCULATED}: got {sum_n_dixon_calculated}"
    )

    return all_pass


def print_representative_rows(summary_df: pd.DataFrame) -> None:
    """Print 2-3 representative full rows for manual sanity review: one
    high-median_RSD combination, one low-median_RSD combination, and the
    combination with the highest n_replicate_groups.
    """
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)

    defined_rsd = summary_df[summary_df["median_RSD"].notna()]

    print("\n=== Representative row: HIGHEST median_RSD ===")
    if len(defined_rsd) > 0:
        row = defined_rsd.loc[defined_rsd["median_RSD"].idxmax()]
        print(row.to_string())

    print("\n=== Representative row: LOWEST median_RSD ===")
    if len(defined_rsd) > 0:
        row = defined_rsd.loc[defined_rsd["median_RSD"].idxmin()]
        print(row.to_string())

    print("\n=== Representative row: HIGHEST n_replicate_groups ===")
    row = summary_df.loc[summary_df["n_replicate_groups"].idxmax()]
    print(row.to_string())


def main() -> None:
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(
            f"{INPUT_PATH} not found — run 01_build_replicate_summary.py and "
            f"03_add_candidate_flags.py first."
        )

    df = pd.read_csv(INPUT_PATH)
    print(f"Loaded {len(df)} replicate-group rows from {INPUT_PATH}")
    if len(df) != EXPECTED_TOTAL_REPLICATE_GROUPS:
        print(
            f"*** WARNING: row count {len(df)} does not match expected "
            f"{EXPECTED_TOTAL_REPLICATE_GROUPS}. Proceeding anyway. ***"
        )

    summary_df = build_method_parameter_summary(df)
    print(
        f"\nBuilt method_parameter_summary with {len(summary_df)} rows "
        f"(distinct analysis_type x parameter combinations)"
    )

    summary_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(summary_df)} rows to: {OUTPUT_PATH}")

    all_pass = run_validation(df, summary_df)
    if not all_pass:
        print(
            "\n*** VALIDATION FAILURE: one or more checks did not match "
            "expected values. Investigate before treating this output as "
            "final. ***"
        )
    else:
        print("\nAll validation checks passed.")

    print_representative_rows(summary_df)


if __name__ == "__main__":
    main()
