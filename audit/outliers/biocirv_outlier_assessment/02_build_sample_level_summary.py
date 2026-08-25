"""
02_build_sample_level_summary.py — Step 2 (handoff v4, "Build the Sample-Level
Summary").

Purpose:
Collapse `outputs/replicate_group_summary.csv` (Step 1, one row per
`sample_id x analysis_type x parameter x unit x method x experiment_id`)
one level further, to one row per
`sample_id x analysis_type x parameter x unit x method` (no `experiment_id`
in the grain — that is the level above experiment). Per Step 0's findings
(`STEP0_FINDINGS.md`), 151 of these combinations span more than one
`experiment_id`; the rest are trivial 1-experiment pass-throughs.

Design (finalized after review, see handoff Step 2 + task spec):

1. `sample_mean` / `n_replicates` are computed by re-grouping the RAW extract
   directly by `["sample_id", "analysis_type", "parameter", "unit", "method"]`
   (dropna=False) rather than by re-parsing the comma-joined `values` string
   in `replicate_group_summary.csv`. This is simpler, more robust, and
   automatically gives the correct n_replicates-weighted pooled mean (NOT an
   unweighted mean-of-per-experiment-means, which would let a 1-replicate
   experiment count equally with a 5-replicate experiment).

2. TWO distinct variability statistics are reported side by side — do not
   collapse them into one:
   - `pooled_SD` / `pooled_RSD_percent`: computed from ALL pooled raw values
     for the sample-level group. This mixes within-experiment technical-
     replicate variation and between-experiment variation together — "total
     variability" for the sample.
   - `between_experiment_SD` / `between_experiment_RSD_percent`: computed
     from the spread of the PER-EXPERIMENT GROUP MEANS ONLY (pulled from
     `replicate_group_summary.csv`'s `mean` column, one value per
     contributing experiment). This isolates between-experiment
     agreement/disagreement as a distinct signal and is fundamentally
     different from `pooled_SD` — it measures inter-experiment consistency,
     not raw replicate precision (raw replicate precision stays in
     `replicate_group_summary.csv`'s `standard_deviation` / `RSD_percent`
     columns, one row per experiment).

Critical guardrails (mirrors 01_build_replicate_summary.py's conventions):
- `groupby(..., dropna=False)` is MANDATORY wherever `unit` or `method` (both
  of which can be null) are part of the grouping key, to avoid pandas
  silently excluding rows with NaN key values.
- Sample SD uses `ddof=1`; NaN (not 0) when undefined (n==1, or only 1
  contributing experiment for between_experiment_SD).
- RSD_percent is NaN (never inf) when the relevant mean is (near-)zero,
  reusing Step 1's `RSD_MEAN_EPSILON = 1e-9` convention (see
  01_build_replicate_summary.py).
- Never silently drop rows; report null `sample_id` rows and any metadata
  (`resource_id`/`resource_type`/`lab`/`protocol_version`) inconsistency
  warnings explicitly.

Usage:
    pixi run python audit/outliers/biocirv_outlier_assessment/02_build_sample_level_summary.py
"""

from __future__ import annotations

import glob
import os
import sys

import numpy as np
import pandas as pd

# Make analysis_config importable regardless of CWD.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis_config  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# Sample-level grouping key: same as REPLICATE_GROUP_KEYS but WITHOUT
# experiment_id — this is exactly the "collapse across experiment_id" step
# that distinguishes sample_level_summary.csv (Step 2) from
# replicate_group_summary.csv (Step 1). See STEP0_FINDINGS.md for the
# design rationale and the confirmed 151-combination overlap count.
SAMPLE_LEVEL_KEYS = ["sample_id", "analysis_type", "parameter", "unit", "method"]

# Metadata columns that are NOT part of the grouping key but should logically
# be constant within a sample-level group (they could legitimately differ
# across experiments — e.g. a resample analyzed under a different protocol
# version). We check for within-group consistency and warn if more than one
# distinct non-null value is found, per the task spec (item 6).
METADATA_CONSISTENCY_COLS = ["resource_id", "resource_type", "lab", "protocol_version"]

# Same epsilon as Step 1 (01_build_replicate_summary.py's RSD_MEAN_EPSILON):
# "If mean is zero or nearly zero, mark RSD undefined rather than infinite"
# (handoff Step 1). Reused here for both pooled_RSD_percent and
# between_experiment_RSD_percent so the two statistics stay comparable.
RSD_MEAN_EPSILON = 1e-9

# Sentinel used only internally to make NaN-safe groupby/get_group lookups
# work correctly. `unit` and `method` can legitimately be null; using a
# literal sentinel string (instead of relying on NaN as a dict/group key,
# which is unreliable across separately-loaded DataFrames because
# `float('nan') != float('nan')`) sidesteps that pitfall entirely while
# still preserving the *original* null values in the output rows.
_NULL_SENTINEL = "\x00__NULL_KEY__\x00"

# From STEP0_FINDINGS.md: 151 `sample_id x analysis_type x parameter x unit x
# method` combinations span more than one `experiment_id`. Used here purely
# as a cross-check / regression guard for this script.
EXPECTED_MULTI_EXPERIMENT_COUNT = 151

# Total raw rows in raw_extract_20260825.csv (per STEP0_FINDINGS.md / Step 1).
EXPECTED_TOTAL_RAW_ROWS = 6155


def load_latest_raw_extract() -> pd.DataFrame:
    """Load the most recent raw_extract_*.csv from analysis_config.RAW_DATA_DIR
    (simple glob + lexicographic sort, which is date-sort for YYYYMMDD
    filenames). Returns the raw dataframe with `value` coerced to numeric.

    Mirrors 01_build_replicate_summary.py's loader exactly, for consistency.
    """
    pattern = os.path.join(analysis_config.RAW_DATA_DIR, analysis_config.RAW_DATA_GLOB)
    candidates = sorted(glob.glob(pattern))
    if not candidates:
        # Fallback: resolve relative to this script's directory.
        alt_dir = os.path.join(HERE, "data")
        pattern = os.path.join(alt_dir, analysis_config.RAW_DATA_GLOB)
        candidates = sorted(glob.glob(pattern))
    if not candidates:
        raise FileNotFoundError(
            f"No files matching {analysis_config.RAW_DATA_GLOB} found under "
            f"{analysis_config.RAW_DATA_DIR} (or fallback {os.path.join(HERE, 'data')})"
        )
    raw_path = candidates[-1]  # lexicographic sort == date sort for YYYYMMDD naming
    print(f"Loading raw extract: {raw_path}")

    df = pd.read_csv(raw_path, dtype=str, keep_default_na=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def load_replicate_group_summary() -> pd.DataFrame:
    """Load outputs/replicate_group_summary.csv (Step 1's output).

    Loaded entirely as strings (dtype=str) first — matching how the raw
    extract is loaded — so that key columns (sample_id, unit, method, etc.)
    compare equal across the two dataframes without int/str or NaN-type
    mismatches. Numeric columns needed downstream (`mean`, `experiment_id`
    for nunique counting) are then coerced back explicitly.
    """
    path = os.path.join(analysis_config.OUTPUT_DIR, "replicate_group_summary.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found — run 01_build_replicate_summary.py first (Step 1 must "
            f"precede Step 2)."
        )
    print(f"Loading replicate group summary: {path}")
    df = pd.read_csv(path, dtype=str, keep_default_na=True)
    df["mean"] = pd.to_numeric(df["mean"], errors="coerce")
    return df


def _first_non_null(series: pd.Series):
    """Return the first non-null value in a series, or None if all null."""
    non_null = series.dropna()
    return non_null.iloc[0] if len(non_null) > 0 else None


def _add_sentinel_key_cols(df: pd.DataFrame, key_cols: list[str]) -> pd.DataFrame:
    """Add `_gkey_<col>` columns for each key column, substituting a literal
    sentinel string for NaN. Grouping/lookup on these sentinel columns avoids
    the classic `float('nan') != float('nan')` pitfall that makes NaN
    unreliable as a groupby/dict/get_group key across separately-loaded
    DataFrames, while the ORIGINAL columns (with real NaNs preserved) remain
    available for output.
    """
    df = df.copy()
    for col in key_cols:
        df[f"_gkey_{col}"] = df[col].fillna(_NULL_SENTINEL)
    return df


def build_sample_level_summary(
    raw_df: pd.DataFrame, replicate_df: pd.DataFrame
) -> tuple[pd.DataFrame, dict]:
    """Build the sample-level summary described in the module docstring.

    Returns (summary_df, stats) where `stats` is a dict of counters used by
    `print_validation_summary()` (n_null_sample_id, n_metadata_warnings,
    n_experiment_count_mismatches, total_raw_rows).
    """
    total_raw_rows = len(raw_df)

    # --- Never silently drop rows: report + exclude null sample_id --------
    null_sample_mask = raw_df["sample_id"].isna()
    n_null_sample_id = int(null_sample_mask.sum())
    if n_null_sample_id:
        print(
            f"WARNING: excluding {n_null_sample_id} raw rows with null sample_id from "
            f"sample-level aggregation (cannot be grouped by this key)."
        )
    working_df = raw_df.loc[~null_sample_mask].copy()

    # --- Sentinel-key both frames for NaN-safe grouping/lookup -------------
    working_df = _add_sentinel_key_cols(working_df, SAMPLE_LEVEL_KEYS)
    replicate_keyed = _add_sentinel_key_cols(replicate_df, SAMPLE_LEVEL_KEYS)
    gkey_cols = [f"_gkey_{c}" for c in SAMPLE_LEVEL_KEYS]

    # Pre-group replicate_group_summary.csv by the SAME sample-level key
    # (collapsing across experiment_id, i.e. NOT re-using
    # REPLICATE_GROUP_KEYS which includes experiment_id) so we can look up,
    # for each sample-level group: (a) its contributing replicate_group_id's
    # for traceability, and (b) its per-experiment `mean` values for
    # between_experiment_SD/RSD.
    rep_grouped = replicate_keyed.groupby(gkey_cols, dropna=False, sort=False)

    rows = []
    n_metadata_warnings = 0
    n_experiment_count_mismatches = 0

    for _gkey_vals, sub in working_df.groupby(gkey_cols, dropna=False, sort=False):
        # Recover the actual (possibly-null) key values from the first row —
        # all rows in this group share equivalent keys post-sentinel
        # substitution, but we want the TRUE (possibly-NaN) value for output.
        first_row = sub.iloc[0]
        key_dict = {c: first_row[c] for c in SAMPLE_LEVEL_KEYS}

        # --- (1) & (2): pooled sample_mean, n_replicates, pooled_SD/RSD ----
        # n_replicates is the literal raw row count for this sample-level
        # group (sum across all contributing experiments' raw rows) — this
        # falls naturally out of grouping the raw data directly.
        n_replicates = len(sub)
        # pandas .mean()/.std() skip NaN `value`s automatically (consistent
        # with 01_build_replicate_summary.py's approach on grouped values).
        sample_mean = sub["value"].mean()

        if n_replicates == 1:
            pooled_sd = np.nan
        else:
            pooled_sd = sub["value"].std(ddof=1)

        if n_replicates == 1 or pd.isna(sample_mean) or abs(sample_mean) < RSD_MEAN_EPSILON:
            pooled_rsd_percent = np.nan
        else:
            pooled_rsd_percent = (pooled_sd / sample_mean) * 100.0

        # --- (4): n_contributing_experiments -------------------------------
        # nunique(dropna=False) counts a null experiment_id as its own
        # "pseudo-experiment" category, matching Step 1's dropna=False
        # groupby convention (a null experiment_id forms its own
        # replicate_group_summary.csv row rather than being silently
        # dropped or merged with real experiment_ids).
        n_contributing_experiments = int(sub["experiment_id"].nunique(dropna=False))

        # --- (6): resource_id/resource_type/lab/protocol_version ----------
        # Check within-sample-level-group consistency (could legitimately
        # differ across contributing experiments); warn + log if so, then
        # take the first non-null value for output.
        metadata_values = {}
        for col in METADATA_CONSISTENCY_COLS:
            distinct_non_null = sub[col].dropna().unique().tolist()
            if len(distinct_non_null) > 1:
                n_metadata_warnings += 1
                print(
                    f"WARNING: metadata inconsistency in column '{col}' for sample-level "
                    f"group {key_dict}: found distinct values {distinct_non_null}. Using "
                    f"first non-null value for output."
                )
            metadata_values[col] = _first_non_null(sub[col])

        # --- (5): replicate_group_id traceability + (3) between_experiment_* -
        rep_key = tuple(first_row[f"_gkey_{c}"] for c in SAMPLE_LEVEL_KEYS)
        try:
            rep_sub = rep_grouped.get_group(rep_key)
        except KeyError:
            # Should not happen — every sample-level combo present in the raw
            # data must also appear in replicate_group_summary.csv (Step 1
            # groups by a superset of these keys). Report loudly rather than
            # silently dropping traceability/between-experiment stats.
            print(
                f"WARNING: no matching replicate_group_summary.csv rows found for "
                f"sample-level group {key_dict} — replicate_group_id and "
                f"between_experiment_* will be blank/NaN for this row."
            )
            rep_sub = replicate_keyed.iloc[0:0]

        replicate_group_id_str = ",".join(str(x) for x in rep_sub["replicate_group_id"].tolist())

        # Cross-check: number of rows in rep_sub should equal
        # n_contributing_experiments (each Step-1 row = one experiment_id,
        # since Step 1 groups WITH experiment_id + dropna=False).
        if len(rep_sub) != n_contributing_experiments:
            n_experiment_count_mismatches += 1
            print(
                f"WARNING: experiment-count mismatch for sample-level group {key_dict}: "
                f"raw data shows {n_contributing_experiments} distinct experiment_id(s) but "
                f"replicate_group_summary.csv has {len(rep_sub)} matching row(s)."
            )

        # between_experiment_SD/RSD: computed from the SPREAD OF PER-EXPERIMENT
        # GROUP MEANS ONLY (replicate_group_summary.csv's `mean` column, one
        # value per contributing experiment) — NOT from pooled raw values.
        # This is fundamentally different from pooled_SD above: pooled_SD
        # mixes within-experiment (technical-replicate) variation together
        # with between-experiment variation, while between_experiment_SD
        # isolates ONLY the inter-experiment agreement/disagreement signal
        # (raw within-experiment replicate precision is preserved separately
        # in replicate_group_summary.csv's own standard_deviation/RSD_percent
        # columns, one row per experiment — this script does not touch it).
        per_experiment_means = rep_sub["mean"].tolist()
        if len(per_experiment_means) <= 1 or pd.isna(sample_mean) or abs(sample_mean) < RSD_MEAN_EPSILON:
            between_experiment_sd = np.nan
            between_experiment_rsd_percent = np.nan
        else:
            between_experiment_sd = float(np.std(per_experiment_means, ddof=1))
            between_experiment_rsd_percent = (between_experiment_sd / sample_mean) * 100.0

        rows.append(
            {
                "sample_id": key_dict["sample_id"],
                "resource_id": metadata_values["resource_id"],
                "resource_type": metadata_values["resource_type"],
                "analysis_type": key_dict["analysis_type"],
                "parameter": key_dict["parameter"],
                "lab": metadata_values["lab"],
                "method": key_dict["method"],
                "protocol_version": metadata_values["protocol_version"],
                "unit": key_dict["unit"],
                "sample_mean": sample_mean,
                "n_replicates": n_replicates,
                "n_contributing_experiments": n_contributing_experiments,
                "pooled_SD": pooled_sd,
                "pooled_RSD_percent": pooled_rsd_percent,
                "between_experiment_SD": between_experiment_sd,
                "between_experiment_RSD_percent": between_experiment_rsd_percent,
                "replicate_group_id": replicate_group_id_str,
            }
        )

    summary_df = pd.DataFrame(
        rows,
        columns=[
            "sample_id",
            "resource_id",
            "resource_type",
            "analysis_type",
            "parameter",
            "lab",
            "method",
            "protocol_version",
            "unit",
            "sample_mean",
            "n_replicates",
            "n_contributing_experiments",
            "pooled_SD",
            "pooled_RSD_percent",
            "between_experiment_SD",
            "between_experiment_RSD_percent",
            "replicate_group_id",
        ],
    )

    stats = {
        "n_null_sample_id": n_null_sample_id,
        "n_metadata_warnings": n_metadata_warnings,
        "n_experiment_count_mismatches": n_experiment_count_mismatches,
        "total_raw_rows": total_raw_rows,
    }
    return summary_df, stats


def print_validation_summary(summary_df: pd.DataFrame, stats: dict) -> None:
    total_rows = len(summary_df)
    n_multi_experiment = int((summary_df["n_contributing_experiments"] > 1).sum())
    n_singleton_passthrough = int((summary_df["n_contributing_experiments"] == 1).sum())

    print("\n=== Validation Summary (Step 2 — sample_level_summary.csv) ===")
    print(f"Total sample-level rows: {total_rows}")

    multi_status = "OK" if n_multi_experiment == EXPECTED_MULTI_EXPERIMENT_COUNT else "MISMATCH"
    print(
        f"Rows with n_contributing_experiments > 1: {n_multi_experiment} "
        f"(expected ~{EXPECTED_MULTI_EXPERIMENT_COUNT} per STEP0_FINDINGS.md) [{multi_status}]"
    )
    print(f"Singleton pass-through rows (n_contributing_experiments == 1): {n_singleton_passthrough}")
    print(f"Metadata (resource_id/resource_type/lab/protocol_version) consistency warnings: {stats['n_metadata_warnings']}")
    print(f"Experiment-count mismatch warnings (raw vs replicate_group_summary.csv): {stats['n_experiment_count_mismatches']}")
    print(f"Rows excluded for null sample_id: {stats['n_null_sample_id']}")

    # Cross-check: sum(n_replicates) across all sample-level rows should equal
    # total raw-data row count minus any rows excluded for null sample_id.
    sum_n_replicates = int(summary_df["n_replicates"].sum())
    expected_sum = stats["total_raw_rows"] - stats["n_null_sample_id"]
    recon_status = "OK" if sum_n_replicates == expected_sum else "MISMATCH"
    print(
        f"\nsum(n_replicates) across sample-level rows: {sum_n_replicates}"
        f"\nexpected (total raw rows {stats['total_raw_rows']} - excluded null sample_id "
        f"{stats['n_null_sample_id']}): {expected_sum}"
        f"\n[{recon_status}]"
    )
    if sum_n_replicates != expected_sum:
        print(
            "*** FLAG: n_replicates reconciliation does NOT match. This is a likely bug — "
            "check for double-counting or a missed exclusion. ***"
        )
    if total_rows != EXPECTED_TOTAL_RAW_ROWS and False:
        pass  # (total_rows is # of distinct combos, not raw rows — no direct check here)

    if stats["total_raw_rows"] != EXPECTED_TOTAL_RAW_ROWS:
        print(
            f"\nNOTE: loaded raw extract has {stats['total_raw_rows']} rows, which differs from "
            f"the documented {EXPECTED_TOTAL_RAW_ROWS} (raw_extract_20260825.csv) — likely a "
            f"newer raw_extract_*.csv snapshot was picked up by the glob. Cross-checks above "
            f"still self-consistently validate against the ACTUAL loaded row count."
        )


def main() -> None:
    raw_df = load_latest_raw_extract()
    print(f"Total raw rows loaded: {len(raw_df)}")

    replicate_df = load_replicate_group_summary()
    print(f"Total replicate-group rows loaded: {len(replicate_df)}")

    summary_df, stats = build_sample_level_summary(raw_df, replicate_df)

    output_dir = analysis_config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "sample_level_summary.csv")
    summary_df.to_csv(output_path, index=False)
    print(f"\nWrote {len(summary_df)} sample-level rows to: {output_path}")

    print_validation_summary(summary_df, stats)

    # --- head() ------------------------------------------------------------
    print("\n=== head() ===")
    print(summary_df.head().to_string())

    # --- Spot-check: one multi-experiment row (n_contributing_experiments > 1)
    print("\n" + "=" * 80)
    print("=== Spot-check: one multi-experiment row (n_contributing_experiments > 1) ===")
    print("=" * 80)
    multi = summary_df[summary_df["n_contributing_experiments"] > 1]
    if len(multi) > 0:
        example = multi.iloc[0]
        print("\n--- sample_level_summary.csv row ---")
        print(example.to_string())

        key = {
            "sample_id": example["sample_id"],
            "analysis_type": example["analysis_type"],
            "parameter": example["parameter"],
            "unit": example["unit"],
            "method": example["method"],
        }
        print(f"\n--- Underlying raw extract rows for {key} ---")
        raw_mask = (
            (raw_df["sample_id"] == key["sample_id"])
            & (raw_df["analysis_type"] == key["analysis_type"])
            & (raw_df["parameter"] == key["parameter"])
            & (raw_df["unit"].fillna(_NULL_SENTINEL) == (key["unit"] if pd.notna(key["unit"]) else _NULL_SENTINEL))
            & (raw_df["method"].fillna(_NULL_SENTINEL) == (key["method"] if pd.notna(key["method"]) else _NULL_SENTINEL))
        )
        raw_rows = raw_df.loc[raw_mask, ["record_id", "experiment_id", "value", "technical_replicate_no"]]
        print(raw_rows.to_string(index=False))

        print(f"\n--- Corresponding replicate_group_summary.csv rows for {key} ---")
        rep_mask = (
            (replicate_df["sample_id"] == key["sample_id"])
            & (replicate_df["analysis_type"] == key["analysis_type"])
            & (replicate_df["parameter"] == key["parameter"])
            & (replicate_df["unit"].fillna(_NULL_SENTINEL) == (key["unit"] if pd.notna(key["unit"]) else _NULL_SENTINEL))
            & (replicate_df["method"].fillna(_NULL_SENTINEL) == (key["method"] if pd.notna(key["method"]) else _NULL_SENTINEL))
        )
        rep_rows = replicate_df.loc[
            rep_mask,
            ["replicate_group_id", "experiment_id", "n_replicates", "mean", "standard_deviation", "RSD_percent"],
        ]
        print(rep_rows.to_string(index=False))

        print(
            "\nManual check: sample_mean should equal the mean of ALL raw values above; "
            "pooled_SD/pooled_RSD_percent should reflect the spread of ALL raw values "
            "pooled together; between_experiment_SD/between_experiment_RSD_percent should "
            "reflect only the spread of the per-experiment `mean` values shown above "
            "(should differ meaningfully from pooled_SD in general)."
        )
    else:
        print("No multi-experiment rows found (unexpected).")

    # --- Spot-check: one trivial singleton pass-through row -----------------
    print("\n" + "=" * 80)
    print("=== Spot-check: one singleton pass-through row (n_contributing_experiments == 1) ===")
    print("=" * 80)
    singletons = summary_df[summary_df["n_contributing_experiments"] == 1]
    if len(singletons) > 0:
        example = singletons.iloc[0]
        print("\n--- sample_level_summary.csv row ---")
        print(example.to_string())

        rep_group_ids = [x for x in str(example["replicate_group_id"]).split(",") if x]
        rep_rows = replicate_df[replicate_df["replicate_group_id"].isin(rep_group_ids)]
        print("\n--- Corresponding replicate_group_summary.csv row(s) ---")
        print(
            rep_rows[
                ["replicate_group_id", "experiment_id", "n_replicates", "mean", "standard_deviation", "RSD_percent"]
            ].to_string(index=False)
        )

        pooled_sd = example["pooled_SD"]
        rep_sd = pd.to_numeric(rep_rows["standard_deviation"], errors="coerce").iloc[0] if len(rep_rows) else np.nan
        sd_match = (
            (pd.isna(pooled_sd) and pd.isna(rep_sd))
            or (pd.notna(pooled_sd) and pd.notna(rep_sd) and abs(pooled_sd - rep_sd) < 1e-9)
        )
        between_is_nan = pd.isna(example["between_experiment_SD"])
        print(f"\npooled_SD ({pooled_sd}) ~= replicate_group_summary standard_deviation ({rep_sd}): {sd_match}")
        print(f"between_experiment_SD is NaN (expected, since only 1 contributing experiment): {between_is_nan}")
    else:
        print("No singleton pass-through rows found (unexpected).")


if __name__ == "__main__":
    main()
