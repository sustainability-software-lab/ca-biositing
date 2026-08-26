"""
03_add_candidate_flags.py — Step 3 (handoff v4, "Add Candidate Replicate-Level
Flags").

Purpose:
Enrich `outputs/replicate_group_summary.csv` (built by
`01_build_replicate_summary.py`) IN PLACE with exploratory candidate
rerun/outlier flags:

1. RSD sensitivity benchmarks (`rsd_gt_{threshold}` for each threshold in
   `analysis_config.RSD_BENCHMARK_THRESHOLDS`) — comparison benchmarks only,
   NOT proposed BioCirV production thresholds (handoff Step 3).
2. Classical/simple Dixon's Q test (r10 statistic), applied per replicate
   group where `DIXON_Q_MIN_N <= n_replicates <= DIXON_Q_MAX_N`. Dixon is
   treated strictly as a FLAG, never as a removal mechanism, and is a
   single-pass calculation (no sequential remove-and-rerun), per the
   handoff's explicit guardrail.
3. A ROUT placeholder (`rout_status` / `rout_status_reason`), since ROUT is
   NOT implemented from scratch during this MVP (handoff Step 3 / "Do not
   implement ROUT from scratch during the MVP").

This script reads and overwrites
`audit/outliers/biocirv_outlier_assessment/outputs/replicate_group_summary.csv`
— this is an intentional in-place enrichment of the Step 1 output, not a new
output file. Row count must remain 2712 (no rows added or removed).

Dixon's Q critical-value table source:
    Rorabacher, D. B. (1991). "Statistical Treatment for Rejection of
    Deviant Values: Critical Values of Dixon's 'Q' Parameter and Related
    Subrange Ratios at the 95% Confidence Level." Analytical Chemistry,
    63(2), 139-146. This is the standard extended two-tailed alpha=0.05
    critical-value table for Dixon's Q test (n = 3 to 30), and is used here
    as-is (approximate/standard reference table) — appropriate for
    exploratory MVP use, NOT a from-scratch statistical derivation.

Guardrails honored (see handoff Step 3 + task spec):
- Dixon is a flag, not a removal mechanism — no `values`/rows are ever
  modified or excluded based on the Dixon result.
- No sequential remove-and-rerun of Dixon (single-pass only).
- ROUT is not implemented from scratch — placeholder columns only, sourced
  directly from `analysis_config.ROUT_STATUS` / `ROUT_STATUS_REASON`.
- Every "not calculated" case gets an explicit status/reason
  (`dixon_status`), never a silent unexplained NaN.

Usage:
    pixi run python audit/outliers/biocirv_outlier_assessment/03_add_candidate_flags.py
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

OUTPUT_PATH = os.path.join(analysis_config.OUTPUT_DIR, "replicate_group_summary.csv")

EXPECTED_TOTAL_ROWS = 2712

# ---------------------------------------------------------------------------
# Dixon's Q critical-value table (Rorabacher 1991, extended, two-tailed,
# alpha = 0.05). See module docstring for full citation. Keys are
# n_replicates (n = 3 to 30); values are the critical Q value above which
# the r10 statistic is considered significant at the 95% confidence level.
# ---------------------------------------------------------------------------
DIXON_Q_CRITICAL_VALUES_ALPHA_0_05 = {
    3: 0.970, 4: 0.829, 5: 0.710, 6: 0.625, 7: 0.568, 8: 0.526, 9: 0.493,
    10: 0.466, 11: 0.444, 12: 0.426, 13: 0.410, 14: 0.396, 15: 0.384,
    16: 0.374, 17: 0.365, 18: 0.356, 19: 0.349, 20: 0.342, 21: 0.337,
    22: 0.331, 23: 0.326, 24: 0.321, 25: 0.317, 26: 0.312, 27: 0.308,
    28: 0.305, 29: 0.301, 30: 0.290,
}

# Dixon status categories (tracked explicitly per handoff's "every omitted
# calculation needs a stated reason" principle).
DIXON_STATUS_CALCULATED = "calculated"
DIXON_STATUS_N_OUT_OF_RANGE = "not_applicable_n_out_of_range"
DIXON_STATUS_ZERO_RANGE = "not_applicable_zero_range"
DIXON_STATUS_DATA_MISMATCH = "skipped_data_mismatch"


def add_rsd_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Add `rsd_gt_{threshold}` columns for each threshold in
    analysis_config.RSD_BENCHMARK_THRESHOLDS, driven dynamically (no
    hardcoding of 10/20) per the handoff's "keep the target list
    configurable" spirit.

    Each column is a pandas nullable boolean ("boolean" dtype): True/False
    when RSD_percent is defined, and <NA> (not silently False) when
    RSD_percent is NaN — so "RSD undefined" stays visually and logically
    distinct from "RSD defined but below threshold".
    """
    rsd = df["RSD_percent"]
    for threshold in analysis_config.RSD_BENCHMARK_THRESHOLDS:
        col_name = f"rsd_gt_{threshold}"
        flag = pd.Series(np.where(rsd.isna(), pd.NA, rsd > threshold), index=df.index)
        df[col_name] = flag.astype("boolean")
    return df


def _parse_csv_floats(s: str) -> list[float]:
    return [float(x) for x in s.split(",")]


def _parse_csv_strs(s: str) -> list[str]:
    return s.split(",")


def compute_dixon_for_row(row: pd.Series) -> dict:
    """Compute the classical/simple Dixon's Q test (r10 statistic) for a
    single replicate-group row.

    Returns a dict with keys: dixon_q_statistic, dixon_candidate_record_id,
    dixon_flag_0_05, dixon_status.

    Single-pass only — never removes a point and reruns Dixon (handoff
    guardrail). Never mutates `values`/`source_record_ids`.
    """
    n = row["n_replicates"]

    result = {
        "dixon_q_statistic": np.nan,
        "dixon_candidate_record_id": None,
        "dixon_flag_0_05": pd.NA,
        "dixon_status": None,
    }

    if n < analysis_config.DIXON_Q_MIN_N or n > analysis_config.DIXON_Q_MAX_N:
        result["dixon_status"] = DIXON_STATUS_N_OUT_OF_RANGE
        return result

    values_str = row["values"]
    record_ids_str = row["source_record_ids"]

    try:
        values = _parse_csv_floats(values_str)
    except (ValueError, AttributeError):
        result["dixon_status"] = DIXON_STATUS_DATA_MISMATCH
        print(
            f"WARNING: replicate_group_id={row.get('replicate_group_id')} — "
            f"could not parse 'values' as floats: {values_str!r}. Skipping Dixon."
        )
        return result

    record_ids = _parse_csv_strs(record_ids_str) if isinstance(record_ids_str, str) else []

    if len(values) != len(record_ids):
        result["dixon_status"] = DIXON_STATUS_DATA_MISMATCH
        print(
            f"WARNING: replicate_group_id={row.get('replicate_group_id')} — "
            f"length mismatch between 'values' ({len(values)}) and "
            f"'source_record_ids' ({len(record_ids)}). Skipping Dixon for this group."
        )
        return result

    # Sort (value, record_id) pairs together by value, ascending.
    paired = sorted(zip(values, record_ids), key=lambda p: p[0])
    sorted_values = [p[0] for p in paired]
    sorted_record_ids = [p[1] for p in paired]

    range_val = sorted_values[-1] - sorted_values[0]

    if range_val == 0:
        result["dixon_status"] = DIXON_STATUS_ZERO_RANGE
        return result

    gap_low = sorted_values[1] - sorted_values[0]
    gap_high = sorted_values[-1] - sorted_values[-2]
    q_low = gap_low / range_val
    q_high = gap_high / range_val

    if q_low >= q_high:
        q_statistic = q_low
        candidate_record_id = sorted_record_ids[0]
    else:
        q_statistic = q_high
        candidate_record_id = sorted_record_ids[-1]

    critical_value = DIXON_Q_CRITICAL_VALUES_ALPHA_0_05[int(n)]
    flag = q_statistic > critical_value

    result["dixon_q_statistic"] = q_statistic
    result["dixon_candidate_record_id"] = candidate_record_id
    result["dixon_flag_0_05"] = bool(flag)
    result["dixon_status"] = DIXON_STATUS_CALCULATED
    return result


def add_dixon_flags(df: pd.DataFrame) -> pd.DataFrame:
    dixon_results = df.apply(compute_dixon_for_row, axis=1, result_type="expand")
    df["dixon_q_statistic"] = dixon_results["dixon_q_statistic"]
    df["dixon_candidate_record_id"] = dixon_results["dixon_candidate_record_id"]
    df["dixon_flag_0_05"] = dixon_results["dixon_flag_0_05"].astype("boolean")
    df["dixon_status"] = dixon_results["dixon_status"]
    return df


def add_rout_placeholder(df: pd.DataFrame) -> pd.DataFrame:
    """ROUT is NOT implemented from scratch during this MVP (handoff Step 3
    guardrail). Every row gets an explicit status/reason instead of a
    silent NaN/omitted column.
    """
    df["rout_status"] = analysis_config.ROUT_STATUS
    df["rout_status_reason"] = analysis_config.ROUT_STATUS_REASON
    return df


def print_validation_summary(df: pd.DataFrame) -> None:
    total = len(df)
    print("\n=== Step 3 Validation Summary ===")
    print(f"Total rows: {total} (expected {EXPECTED_TOTAL_ROWS})")

    # --- RSD flags ---
    n_rsd_undefined = int(df["RSD_percent"].isna().sum())
    print(f"\nRSD undefined (NaN RSD_percent): {n_rsd_undefined} ({100.0 * n_rsd_undefined / total:.1f}%)")
    for threshold in analysis_config.RSD_BENCHMARK_THRESHOLDS:
        col = f"rsd_gt_{threshold}"
        n_true = int((df[col] == True).sum())  # noqa: E712
        n_defined = int(df[col].notna().sum())
        pct_of_total = 100.0 * n_true / total
        pct_of_defined = 100.0 * n_true / n_defined if n_defined else 0.0
        print(
            f"{col}: {n_true} groups flagged "
            f"({pct_of_total:.1f}% of all groups, {pct_of_defined:.1f}% of RSD-defined groups)"
        )

    # --- Dixon status breakdown ---
    print("\nDixon status breakdown:")
    status_counts = df["dixon_status"].value_counts(dropna=False)
    for status, count in status_counts.items():
        print(f"  {status}: {count} ({100.0 * count / total:.1f}%)")

    n_calculated = int((df["dixon_status"] == DIXON_STATUS_CALCULATED).sum())
    n_dixon_flagged = int((df["dixon_flag_0_05"] == True).sum())  # noqa: E712
    pct_flagged_of_calc = 100.0 * n_dixon_flagged / n_calculated if n_calculated else 0.0
    print(
        f"\nDixon flagged (dixon_flag_0_05 == True): {n_dixon_flagged} "
        f"out of {n_calculated} calculated groups ({pct_flagged_of_calc:.1f}%)"
    )

    # --- RSD (gt_20) x Dixon 2x2 cross-tab ---
    rsd20 = df["rsd_gt_20"].fillna(False).astype(bool)
    dixon_flag = df["dixon_flag_0_05"].fillna(False).astype(bool)
    both = int((rsd20 & dixon_flag).sum())
    rsd_only = int((rsd20 & ~dixon_flag).sum())
    dixon_only = int((~rsd20 & dixon_flag).sum())
    neither = int((~rsd20 & ~dixon_flag).sum())
    print("\nRSD (>20%) x Dixon (0.05) 2x2 cross-tab:")
    print(f"  Both flagged:        {both}")
    print(f"  RSD only:            {rsd_only}")
    print(f"  Dixon only:          {dixon_only}")
    print(f"  Neither flagged:     {neither}")
    print(f"  Total:               {both + rsd_only + dixon_only + neither} (expected {total})")

    # --- ROUT confirmation ---
    n_rout_not_calculated = int((df["rout_status"] == analysis_config.ROUT_STATUS).sum())
    print(
        f"\nrout_status == '{analysis_config.ROUT_STATUS}' for all rows: "
        f"{n_rout_not_calculated}/{total} "
        f"[{'OK' if n_rout_not_calculated == total else 'MISMATCH'}]"
    )


def print_spot_checks(df: pd.DataFrame) -> None:
    print("\n=== Spot-check: one row with dixon_flag_0_05 == True ===")
    flagged = df[df["dixon_flag_0_05"] == True]  # noqa: E712
    if len(flagged) > 0:
        example = flagged.iloc[0]
        n = int(example["n_replicates"])
        critical_value = DIXON_Q_CRITICAL_VALUES_ALPHA_0_05[n]
        print(example[[
            "replicate_group_id", "sample_id", "analysis_type", "parameter",
            "n_replicates", "values", "source_record_ids",
            "dixon_q_statistic", "dixon_candidate_record_id", "dixon_flag_0_05", "dixon_status",
        ]].to_string())
        values = _parse_csv_floats(example["values"])
        record_ids = _parse_csv_strs(example["source_record_ids"])
        paired = sorted(zip(values, record_ids), key=lambda p: p[0])
        sorted_values = [p[0] for p in paired]
        sorted_record_ids = [p[1] for p in paired]
        range_val = sorted_values[-1] - sorted_values[0]
        gap_low = sorted_values[1] - sorted_values[0]
        gap_high = sorted_values[-1] - sorted_values[-2]
        q_low = gap_low / range_val
        q_high = gap_high / range_val
        print(f"\nManual arithmetic check:")
        print(f"  sorted_values = {sorted_values}")
        print(f"  sorted_record_ids = {sorted_record_ids}")
        print(f"  range_val = {sorted_values[-1]} - {sorted_values[0]} = {range_val}")
        print(f"  gap_low = {sorted_values[1]} - {sorted_values[0]} = {gap_low}; Q_low = {gap_low}/{range_val} = {q_low}")
        print(f"  gap_high = {sorted_values[-1]} - {sorted_values[-2]} = {gap_high}; Q_high = {gap_high}/{range_val} = {q_high}")
        print(f"  dixon_q_statistic = max(Q_low, Q_high) = {max(q_low, q_high)}")
        print(f"  n_replicates = {n} -> critical_value (alpha=0.05, Rorabacher 1991) = {critical_value}")
        print(f"  {max(q_low, q_high)} > {critical_value} => dixon_flag_0_05 = {max(q_low, q_high) > critical_value}")
    else:
        print("No rows with dixon_flag_0_05 == True found.")

    print("\n=== Spot-check: one row with n_replicates < 3 ===")
    small_n = df[df["n_replicates"] < analysis_config.DIXON_Q_MIN_N]
    if len(small_n) > 0:
        example = small_n.iloc[0]
        print(example[[
            "replicate_group_id", "sample_id", "analysis_type", "parameter",
            "n_replicates", "dixon_q_statistic", "dixon_candidate_record_id",
            "dixon_flag_0_05", "dixon_status",
        ]].to_string())
        print(f"\ndixon_status == '{DIXON_STATUS_N_OUT_OF_RANGE}': {example['dixon_status'] == DIXON_STATUS_N_OUT_OF_RANGE}")
        print(f"dixon_q_statistic is NaN: {pd.isna(example['dixon_q_statistic'])}")
        print(f"dixon_candidate_record_id is null: {example['dixon_candidate_record_id'] is None or pd.isna(example['dixon_candidate_record_id'])}")
        print(f"dixon_flag_0_05 is NA: {pd.isna(example['dixon_flag_0_05'])}")
    else:
        print("No rows with n_replicates < 3 found (unexpected).")


def main() -> None:
    if not os.path.exists(OUTPUT_PATH):
        raise FileNotFoundError(
            f"{OUTPUT_PATH} not found — run 01_build_replicate_summary.py first."
        )

    df = pd.read_csv(OUTPUT_PATH)
    print(f"Loaded {len(df)} rows from {OUTPUT_PATH}")
    if len(df) != EXPECTED_TOTAL_ROWS:
        print(
            f"*** WARNING: row count {len(df)} does not match expected "
            f"{EXPECTED_TOTAL_ROWS}. Proceeding anyway. ***"
        )

    df = add_rsd_flags(df)
    df = add_dixon_flags(df)
    df = add_rout_placeholder(df)

    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nWrote {len(df)} enriched rows back to: {OUTPUT_PATH}")

    print_validation_summary(df)
    print_spot_checks(df)


if __name__ == "__main__":
    main()
