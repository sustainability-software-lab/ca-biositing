"""
08_compare_candidate_rules.py — Step 8 (handoff v4, "Produce the
Candidate-Rule Comparison").

Purpose:
Build a compact, report-ready comparison of the candidate replicate-quality
screening methods already computed earlier in the pipeline
(`RSD_percent` benchmarks, Dixon's Q) plus one NEW exploratory comparator
computed here for the first time: a pooled, cross-group, absolute-scale
"3xSD" flag.

This script READS `outputs/replicate_group_summary.csv` (built by
`01_build_replicate_summary.py`, enriched by `03_add_candidate_flags.py`)
but never writes back to it — all 3xSD enrichment is done on an in-memory
copy of the data, per this step's explicit guardrail ("Do NOT overwrite
`replicate_group_summary.csv` itself").

Part A — Pooled within-replicate SD per analysis_type x parameter:
    pooled_SD = sqrt( sum((n_i - 1) * SD_i^2) / sum(n_i - 1) )
    computed ONLY over replicate groups within that combination where
    `standard_deviation` is defined (not NaN). This is the classical
    pooled-variance estimator, used here purely as an ABSOLUTE-scale,
    cross-group reference for comparison against Dixon's WITHIN-group
    relative test and RSD's WITHIN-group relative-to-own-mean test.

Part B — Per-replicate-group 3xSD flag:
    For each replicate group whose analysis_type x parameter has a defined
    pooled_SD, parse the `values` column back into individual floats and
    flag the group (`flag_3xSD = True`) if ANY individual value deviates
    from that group's own `mean` by more than 3 x the analysis_type x
    parameter's POOLED SD (never the group's own SD — explicit handoff
    instruction).

Part C — outputs/candidate_rule_comparison.csv (74 rows, one per
    analysis_type x parameter): applicability and flag-rate comparison
    across RSD>10, RSD>20, Dixon, and 3xSD.

Part D — Overall 3-way overlap cross-tab (RSD>20 x Dixon x 3xSD) across all
    2712 replicate groups, treating NaN/not-applicable as "not flagged" for
    this overlap tally ONLY (explicit stated simplification).
    Saved as outputs/candidate_rule_overlap_summary.csv.

Part E — By-analysis_type roll-up of Part C, saved as
    outputs/candidate_rule_by_analysis_type.csv.

Guardrails honored (see handoff + task spec):
- Never overwrites replicate_group_summary.csv.
- Never implements ROUT.
- Never implements a 2xSD variant.
- Never revisits Step 6/6A's precision_model_category classifications.
- Never performs review-queue clustering / rerun-burden analysis (Step 9,
  explicitly out of scope for this script).
- NaN/not-applicable handling follows the same pandas nullable-boolean and
  explicit-status conventions used in 03_add_candidate_flags.py.

Usage:
    pixi run python audit/outliers/biocirv_outlier_assessment/08_compare_candidate_rules.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

# Make analysis_config importable regardless of CWD.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis_config  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

INPUT_PATH = os.path.join(analysis_config.OUTPUT_DIR, "replicate_group_summary.csv")

OUTPUT_COMPARISON_PATH = os.path.join(analysis_config.OUTPUT_DIR, "candidate_rule_comparison.csv")
OUTPUT_OVERLAP_PATH = os.path.join(analysis_config.OUTPUT_DIR, "candidate_rule_overlap_summary.csv")
OUTPUT_BY_ANALYSIS_TYPE_PATH = os.path.join(analysis_config.OUTPUT_DIR, "candidate_rule_by_analysis_type.csv")
OUTPUT_3XSD_FLAGS_PATH = os.path.join(analysis_config.OUTPUT_DIR, "replicate_group_3xSD_flags.csv")

EXPECTED_TOTAL_ROWS = 2712
EXPECTED_TOTAL_COMBOS = 74

GROUP_KEYS = ["analysis_type", "parameter"]

STATUS_3XSD_CALCULATED = "calculated"
STATUS_3XSD_NOT_APPLICABLE = "not_applicable_pooled_SD_undefined"
STATUS_3XSD_NOT_APPLICABLE_N_LT_2 = "not_applicable_n_lt_2"


# ---------------------------------------------------------------------------
# Part A — pooled within-replicate SD per analysis_type x parameter
# ---------------------------------------------------------------------------


def compute_pooled_sd_table(df: pd.DataFrame) -> pd.DataFrame:
    """Compute pooled_SD per analysis_type x parameter using only
    SD-defined replicate groups (standard_deviation not NaN).

    pooled_SD = sqrt( sum((n_i - 1) * SD_i^2) / sum(n_i - 1) )

    Returns a DataFrame indexed by [analysis_type, parameter] with columns:
        pooled_SD, n_SD_defined_groups_used, pooled_SD_status
    """
    sd_defined = df[df["standard_deviation"].notna()].copy()

    records = []
    for keys, group in df.groupby(GROUP_KEYS, dropna=False, sort=True):
        analysis_type, parameter = keys
        sub = sd_defined[
            (sd_defined["analysis_type"] == analysis_type) & (sd_defined["parameter"] == parameter)
        ]
        n_sd_defined = len(sub)

        if n_sd_defined == 0:
            pooled_sd = np.nan
            status = "insufficient data for pooled SD (no SD-defined replicate groups)"
        else:
            numerator = ((sub["n_replicates"] - 1) * sub["standard_deviation"] ** 2).sum()
            denominator = (sub["n_replicates"] - 1).sum()
            if denominator == 0:
                pooled_sd = np.nan
                status = "insufficient data for pooled SD (sum(n_i - 1) == 0)"
            else:
                pooled_sd = np.sqrt(numerator / denominator)
                status = "calculated"

        records.append(
            {
                "analysis_type": analysis_type,
                "parameter": parameter,
                "pooled_SD": pooled_sd,
                "n_SD_defined_groups_used": n_sd_defined,
                "pooled_SD_status": status,
            }
        )

    result = pd.DataFrame.from_records(records)
    return result


# ---------------------------------------------------------------------------
# Part B — per-replicate-group 3xSD flag
# ---------------------------------------------------------------------------


def _parse_csv_floats(s: str) -> list[float]:
    return [float(x) for x in s.split(",")]


def compute_3xsd_flag_for_row(row: pd.Series, pooled_sd_lookup: dict) -> dict:
    """Compute the 3xSD flag for a single replicate-group row, using the
    POOLED SD for that row's analysis_type x parameter (never the row's own
    standard_deviation) as the threshold multiplier base.

    A replicate group is only 3xSD-applicable when BOTH:
      1. the analysis_type x parameter's pooled_SD is defined, AND
      2. the group itself has n_replicates >= 2.
    Singleton groups (n_replicates == 1) are excluded from applicability
    even when pooled_SD is defined: with only one observation, that value
    IS the group mean, so "deviation from the group mean" is trivially
    zero and the check cannot meaningfully evaluate anything about that
    group. Counting singletons as evaluated would artificially inflate
    3xSD coverage without adding real information.
    """
    key = (row["analysis_type"], row["parameter"])
    pooled_sd = pooled_sd_lookup.get(key, np.nan)

    result = {
        "pooled_SD_used": pooled_sd,
        "flag_3xSD": pd.NA,
        "3xSD_status": None,
    }

    if pd.isna(pooled_sd):
        result["3xSD_status"] = STATUS_3XSD_NOT_APPLICABLE
        return result

    if row["n_replicates"] < 2:
        result["3xSD_status"] = STATUS_3XSD_NOT_APPLICABLE_N_LT_2
        return result

    values_str = row["values"]
    try:
        values = _parse_csv_floats(values_str)
    except (ValueError, AttributeError):
        result["3xSD_status"] = STATUS_3XSD_NOT_APPLICABLE
        print(
            f"WARNING: replicate_group_id={row.get('replicate_group_id')} — "
            f"could not parse 'values' as floats: {values_str!r}. Skipping 3xSD."
        )
        return result

    group_mean = row["mean"]
    threshold = 3.0 * pooled_sd
    any_exceeds = any(abs(v - group_mean) > threshold for v in values)

    result["flag_3xSD"] = bool(any_exceeds)
    result["3xSD_status"] = STATUS_3XSD_CALCULATED
    return result


def add_3xsd_flags(df: pd.DataFrame, pooled_sd_table: pd.DataFrame) -> pd.DataFrame:
    """Return a COPY of df enriched with pooled_SD_used, flag_3xSD,
    3xSD_status columns. Does not mutate the input df in place beyond the
    copy returned.
    """
    df = df.copy()
    pooled_sd_lookup = {
        (row["analysis_type"], row["parameter"]): row["pooled_SD"]
        for _, row in pooled_sd_table.iterrows()
    }

    results = df.apply(compute_3xsd_flag_for_row, axis=1, result_type="expand", pooled_sd_lookup=pooled_sd_lookup)
    df["pooled_SD_used"] = results["pooled_SD_used"]
    df["flag_3xSD"] = results["flag_3xSD"].astype("boolean")
    df["3xSD_status"] = results["3xSD_status"]
    return df


# ---------------------------------------------------------------------------
# Part C — candidate_rule_comparison.csv
# ---------------------------------------------------------------------------


def summarize_combo(group: pd.DataFrame) -> pd.Series:
    n_replicate_groups = len(group)

    # --- RSD applicability ---
    n_RSD_defined = int(group["RSD_percent"].notna().sum())
    percent_RSD_defined = n_RSD_defined / n_replicate_groups * 100 if n_replicate_groups else np.nan

    # --- Dixon applicability ---
    n_Dixon_applicable = int((group["dixon_status"] == "calculated").sum())
    percent_Dixon_applicable = n_Dixon_applicable / n_replicate_groups * 100 if n_replicate_groups else np.nan

    # --- 3xSD applicability ---
    n_3xSD_applicable = int((group["3xSD_status"] == STATUS_3XSD_CALCULATED).sum())
    percent_3xSD_applicable = n_3xSD_applicable / n_replicate_groups * 100 if n_replicate_groups else np.nan

    # --- RSD flag rates (denominator = n_RSD_defined) ---
    if n_RSD_defined == 0:
        n_RSD_gt_10 = 0
        n_RSD_gt_20 = 0
        percent_RSD_gt_10 = np.nan
        percent_RSD_gt_20 = np.nan
    else:
        n_RSD_gt_10 = int((group["rsd_gt_10"] == True).sum())  # noqa: E712
        n_RSD_gt_20 = int((group["rsd_gt_20"] == True).sum())  # noqa: E712
        percent_RSD_gt_10 = n_RSD_gt_10 / n_RSD_defined * 100
        percent_RSD_gt_20 = n_RSD_gt_20 / n_RSD_defined * 100

    # --- Dixon flag rate (denominator = n_Dixon_applicable) ---
    if n_Dixon_applicable == 0:
        n_Dixon_flagged = 0
        percent_Dixon_flagged = np.nan
    else:
        dixon_applicable_mask = group["dixon_status"] == "calculated"
        n_Dixon_flagged = int((group.loc[dixon_applicable_mask, "dixon_flag_0_05"] == True).sum())  # noqa: E712
        percent_Dixon_flagged = n_Dixon_flagged / n_Dixon_applicable * 100

    # --- 3xSD flag rate (denominator = n_3xSD_applicable) ---
    if n_3xSD_applicable == 0:
        n_3xSD_flagged = 0
        percent_3xSD_flagged = np.nan
    else:
        applicable_mask = group["3xSD_status"] == STATUS_3XSD_CALCULATED
        n_3xSD_flagged = int((group.loc[applicable_mask, "flag_3xSD"] == True).sum())  # noqa: E712
        percent_3xSD_flagged = n_3xSD_flagged / n_3xSD_applicable * 100

    # --- pooled_SD for this combo (constant across the group's rows via pooled_SD_used) ---
    pooled_sd_values = group["pooled_SD_used"].dropna().unique()
    pooled_sd = pooled_sd_values[0] if len(pooled_sd_values) > 0 else np.nan

    return pd.Series(
        {
            "n_replicate_groups": n_replicate_groups,
            "n_RSD_defined": n_RSD_defined,
            "percent_RSD_defined": percent_RSD_defined,
            "n_Dixon_applicable": n_Dixon_applicable,
            "percent_Dixon_applicable": percent_Dixon_applicable,
            "n_3xSD_applicable": n_3xSD_applicable,
            "percent_3xSD_applicable": percent_3xSD_applicable,
            "n_RSD_gt_10": n_RSD_gt_10,
            "percent_RSD_gt_10": percent_RSD_gt_10,
            "n_RSD_gt_20": n_RSD_gt_20,
            "percent_RSD_gt_20": percent_RSD_gt_20,
            "n_Dixon_flagged": n_Dixon_flagged,
            "percent_Dixon_flagged": percent_Dixon_flagged,
            "n_3xSD_flagged": n_3xSD_flagged,
            "percent_3xSD_flagged": percent_3xSD_flagged,
            "pooled_SD": pooled_sd,
        }
    )


def build_candidate_rule_comparison(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby(GROUP_KEYS, dropna=False, sort=True)
    summary = grouped.apply(summarize_combo, include_groups=False)
    summary = summary.reset_index()
    return summary


# ---------------------------------------------------------------------------
# Part D — overall 3-way overlap
# ---------------------------------------------------------------------------


def build_overlap_summary(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)

    # Simplification (explicit): NaN/not-applicable treated as "not flagged"
    # for this overlap tally only.
    rsd20 = (df["rsd_gt_20"] == True).fillna(False).astype(bool)  # noqa: E712
    dixon = (df["dixon_flag_0_05"] == True).fillna(False).astype(bool)  # noqa: E712
    sd3x = (df["flag_3xSD"] == True).fillna(False).astype(bool)  # noqa: E712

    categories = {
        "RSD20_only": (rsd20 & ~dixon & ~sd3x),
        "Dixon_only": (~rsd20 & dixon & ~sd3x),
        "3xSD_only": (~rsd20 & ~dixon & sd3x),
        "RSD20_and_Dixon": (rsd20 & dixon & ~sd3x),
        "RSD20_and_3xSD": (rsd20 & ~dixon & sd3x),
        "Dixon_and_3xSD": (~rsd20 & dixon & sd3x),
        "all_three": (rsd20 & dixon & sd3x),
        "flagged_by_any": (rsd20 | dixon | sd3x),
        "flagged_by_none": (~rsd20 & ~dixon & ~sd3x),
    }

    records = []
    for cat, mask in categories.items():
        count = int(mask.sum())
        pct = count / total * 100 if total else np.nan
        records.append({"category": cat, "count": count, "percent_of_total": pct})

    result = pd.DataFrame.from_records(records)
    return result, categories, total


# ---------------------------------------------------------------------------
# Part E — by-analysis_type roll-up
# ---------------------------------------------------------------------------


def build_by_analysis_type_summary(comparison_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for analysis_type, group in comparison_df.groupby("analysis_type", dropna=False, sort=True):
        n_replicate_groups = int(group["n_replicate_groups"].sum())
        n_RSD_gt_20 = int(group["n_RSD_gt_20"].sum())
        n_RSD_defined = int(group["n_RSD_defined"].sum())
        n_Dixon_flagged = int(group["n_Dixon_flagged"].sum())
        n_Dixon_applicable = int(group["n_Dixon_applicable"].sum())
        n_3xSD_flagged = int(group["n_3xSD_flagged"].sum())
        n_3xSD_applicable = int(group["n_3xSD_applicable"].sum())

        percent_RSD_gt_20 = n_RSD_gt_20 / n_RSD_defined * 100 if n_RSD_defined else np.nan
        percent_Dixon_flagged = n_Dixon_flagged / n_Dixon_applicable * 100 if n_Dixon_applicable else np.nan
        percent_3xSD_flagged = n_3xSD_flagged / n_3xSD_applicable * 100 if n_3xSD_applicable else np.nan

        records.append(
            {
                "analysis_type": analysis_type,
                "n_replicate_groups": n_replicate_groups,
                "n_RSD_gt_20": n_RSD_gt_20,
                "percent_RSD_gt_20": percent_RSD_gt_20,
                "n_Dixon_flagged": n_Dixon_flagged,
                "percent_Dixon_flagged": percent_Dixon_flagged,
                "n_3xSD_flagged": n_3xSD_flagged,
                "percent_3xSD_flagged": percent_3xSD_flagged,
            }
        )

    result = pd.DataFrame.from_records(records)
    result = result.sort_values("n_replicate_groups", ascending=False).reset_index(drop=True)
    return result


# ---------------------------------------------------------------------------
# Validation / printing
# ---------------------------------------------------------------------------


def print_part_a_summary(pooled_sd_table: pd.DataFrame) -> None:
    print("\n=== Part A: Pooled SD per analysis_type x parameter ===")
    n_combos = len(pooled_sd_table)
    n_defined = int(pooled_sd_table["pooled_SD"].notna().sum())
    n_undefined = n_combos - n_defined
    print(f"Total analysis_type x parameter combinations: {n_combos}")
    print(f"pooled_SD defined: {n_defined}")
    print(f"pooled_SD undefined (insufficient data): {n_undefined}")
    if n_undefined:
        print("\nCombinations with undefined pooled_SD:")
        undefined = pooled_sd_table[pooled_sd_table["pooled_SD"].isna()]
        for _, row in undefined.iterrows():
            print(
                f"  {row['analysis_type']} / {row['parameter']}: "
                f"{row['pooled_SD_status']} (n_SD_defined_groups_used={row['n_SD_defined_groups_used']})"
            )


def print_part_b_summary(df: pd.DataFrame) -> None:
    print("\n=== Part B: 3xSD flag status breakdown (all 2712 replicate groups) ===")
    total = len(df)
    status_counts = df["3xSD_status"].value_counts(dropna=False)
    for status, count in status_counts.items():
        print(f"  {status}: {count} ({100.0 * count / total:.1f}%)")

    n_calculated = int((df["3xSD_status"] == STATUS_3XSD_CALCULATED).sum())
    n_flagged = int((df["flag_3xSD"] == True).sum())  # noqa: E712
    pct = 100.0 * n_flagged / n_calculated if n_calculated else 0.0
    print(f"\n3xSD flagged (flag_3xSD == True): {n_flagged} out of {n_calculated} applicable groups ({pct:.1f}%)")


def print_part_d_summary(overlap_df: pd.DataFrame, total: int) -> None:
    print(f"\n=== Part D: 3-way overlap (RSD>20 x Dixon x 3xSD), N={total} ===")
    print(
        "Simplification note: NaN/not-applicable values for any of the three "
        "methods are treated as 'not flagged' for this overlap tally ONLY. "
        "A group that is Dixon-not-applicable (e.g., n_replicates out of "
        "Dixon's 3-30 range) is NOT equivalent to Dixon having evaluated it "
        "and said 'no' -- it simply cannot contribute to Dixon's flag count here."
    )
    for _, row in overlap_df.iterrows():
        print(f"  {row['category']:20s}: {row['count']:5d} ({row['percent_of_total']:.1f}%)")


def print_part_e_summary(by_type_df: pd.DataFrame) -> None:
    print("\n=== Part E: By-analysis_type flag summary ===")
    print(by_type_df.to_string(index=False))


def print_top_flag_rate_combos(comparison_df: pd.DataFrame, n: int = 5) -> None:
    print(f"\n=== Top {n} highest RSD>20 flag-rate combinations (RSD-defined n>=5) ===")
    eligible = comparison_df[comparison_df["n_RSD_defined"] >= 5].copy()
    top = eligible.sort_values("percent_RSD_gt_20", ascending=False).head(n)
    print(
        top[["analysis_type", "parameter", "n_replicate_groups", "n_RSD_defined", "percent_RSD_gt_20"]].to_string(
            index=False
        )
    )


def main() -> None:
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(f"{INPUT_PATH} not found — run 01_build_replicate_summary.py first.")

    df = pd.read_csv(INPUT_PATH)
    print(f"Loaded {len(df)} rows from {INPUT_PATH}")
    if len(df) != EXPECTED_TOTAL_ROWS:
        print(f"*** WARNING: row count {len(df)} does not match expected {EXPECTED_TOTAL_ROWS}. Proceeding anyway. ***")

    # --- Part A ---
    pooled_sd_table = compute_pooled_sd_table(df)
    print_part_a_summary(pooled_sd_table)

    # --- Part B (in-memory enrichment of a COPY only) ---
    enriched_df = add_3xsd_flags(df, pooled_sd_table)
    print_part_b_summary(enriched_df)

    # Optional traceability CSV
    trace_cols = ["replicate_group_id", "analysis_type", "parameter", "pooled_SD_used", "flag_3xSD", "3xSD_status"]
    enriched_df[trace_cols].to_csv(OUTPUT_3XSD_FLAGS_PATH, index=False)
    print(f"\nWrote {len(enriched_df)} rows to: {OUTPUT_3XSD_FLAGS_PATH}")

    # Confirm original file untouched
    original_check = pd.read_csv(INPUT_PATH)
    assert "flag_3xSD" not in original_check.columns, "replicate_group_summary.csv was unexpectedly modified!"
    print(f"\nConfirmed: {INPUT_PATH} does NOT contain 3xSD columns (untouched).")

    # --- Part C ---
    comparison_df = build_candidate_rule_comparison(enriched_df)
    print(f"\n=== Part C: candidate_rule_comparison.csv ===")
    print(f"Rows: {len(comparison_df)} (expected {EXPECTED_TOTAL_COMBOS})")
    if len(comparison_df) != EXPECTED_TOTAL_COMBOS:
        print(f"*** WARNING: row count {len(comparison_df)} does not match expected {EXPECTED_TOTAL_COMBOS}. ***")
    comparison_df.to_csv(OUTPUT_COMPARISON_PATH, index=False)
    print(f"Wrote: {OUTPUT_COMPARISON_PATH}")

    # Validation: sums should match totals
    sum_n_replicate_groups = int(comparison_df["n_replicate_groups"].sum())
    print(f"\n[VALIDATION] sum(n_replicate_groups) == {EXPECTED_TOTAL_ROWS}: got {sum_n_replicate_groups} "
          f"[{'PASS' if sum_n_replicate_groups == EXPECTED_TOTAL_ROWS else 'FAIL'}]")

    print_top_flag_rate_combos(comparison_df, n=5)

    # --- Part D ---
    overlap_df, overlap_masks, total = build_overlap_summary(enriched_df)
    print_part_d_summary(overlap_df, total)
    overlap_df.to_csv(OUTPUT_OVERLAP_PATH, index=False)
    print(f"\nWrote: {OUTPUT_OVERLAP_PATH}")

    # Validation: mutually-exclusive categories should sum to total
    exclusive_cats = ["RSD20_only", "Dixon_only", "3xSD_only", "RSD20_and_Dixon", "RSD20_and_3xSD", "Dixon_and_3xSD", "all_three"]
    sum_exclusive = int(overlap_df[overlap_df["category"].isin(exclusive_cats)]["count"].sum())
    flagged_by_none = int(overlap_df.loc[overlap_df["category"] == "flagged_by_none", "count"].iloc[0])
    print(f"[VALIDATION] sum(7 exclusive categories) + flagged_by_none == {total}: "
          f"got {sum_exclusive + flagged_by_none} [{'PASS' if sum_exclusive + flagged_by_none == total else 'FAIL'}]")

    # --- Part E ---
    by_type_df = build_by_analysis_type_summary(comparison_df)
    print_part_e_summary(by_type_df)
    by_type_df.to_csv(OUTPUT_BY_ANALYSIS_TYPE_PATH, index=False)
    print(f"\nWrote: {OUTPUT_BY_ANALYSIS_TYPE_PATH}")

    sum_by_type = int(by_type_df["n_replicate_groups"].sum())
    print(f"[VALIDATION] sum(by_analysis_type n_replicate_groups) == {EXPECTED_TOTAL_ROWS}: "
          f"got {sum_by_type} [{'PASS' if sum_by_type == EXPECTED_TOTAL_ROWS else 'FAIL'}]")


if __name__ == "__main__":
    main()
