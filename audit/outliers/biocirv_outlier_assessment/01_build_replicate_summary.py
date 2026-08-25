"""
01_build_replicate_summary.py — Step 1 (handoff v4, "Build the Replicate-Group
Summary").

Purpose:
Group the raw extract by `analysis_config.REPLICATE_GROUP_KEYS`
(`sample_id, analysis_type, parameter, unit, method, experiment_id`) and
compute one summary row per technical-replicate group: n, mean, median,
sample SD (ddof=1), RSD%, min/max/range, plus traceability fields
(`values`, `source_record_ids`, `existing_QC_status`).

This produces `outputs/replicate_group_summary.csv` — one row per actual
technical-replicate cluster measured within a single experimental run. It
does NOT aggregate across `experiment_id` (that is `sample_level_summary.csv`,
a separate later task, per README/handoff design note).

Critical guardrails (see handoff Step 1 + analysis_config.py comments):
- `groupby(REPLICATE_GROUP_KEYS, dropna=False)` is MANDATORY. ~0.44% of rows
  have a null `experiment_id`; pandas' default groupby behavior silently
  drops rows with NaN in any key column unless `dropna=False` is passed.
- Never drop groups, including singletons (n_replicates == 1).
- Sample SD uses `ddof=1`; NaN (not 0) when n_replicates == 1 (SD undefined
  for a single observation).
- RSD_percent is NaN (never inf, never silently 0) when the mean is
  (near-)zero or when n_replicates == 1.
- `existing_QC_status` is reported as the comma-joined set of *distinct*
  values seen in the group — never resolved/collapsed.
- `record_id` traceability is preserved via `source_record_ids`.

Usage:
    pixi run python audit/outliers/biocirv_outlier_assessment/01_build_replicate_summary.py
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

REPLICATE_GROUP_KEYS = analysis_config.REPLICATE_GROUP_KEYS

# Metadata columns that are NOT part of the grouping key but should logically
# be constant within a group. We check for within-group consistency and warn
# if more than one distinct non-null value is found.
METADATA_CONSISTENCY_COLS = ["resource_id", "resource_type", "lab", "protocol_version"]

# Epsilon for "near-zero mean" RSD-undefined check. Chosen to be well below
# any plausible real measurement value in this dataset (units range from
# ppm to %) while still catching true zero/near-zero means that would
# otherwise blow up RSD toward +/-inf. Documented per handoff Step 1
# ("If mean is zero or nearly zero, mark RSD undefined rather than infinite").
RSD_MEAN_EPSILON = 1e-9

# Step 0's confirmed per-analysis_type group counts (STEP0_FINDINGS.md), used
# here purely as a cross-check / regression guard for this script.
EXPECTED_GROUP_COUNTS = {
    "xrf": 1315,
    "proximate": 460,
    "compositional": 352,
    "icp": 518,
    "ultimate": 57,
    "xrd": 10,
}
EXPECTED_TOTAL_GROUPS = 2712


def load_latest_raw_extract() -> pd.DataFrame:
    """Load the most recent raw_extract_*.csv from analysis_config.RAW_DATA_DIR
    (simple glob + lexicographic sort, which is date-sort for YYYYMMDD
    filenames). Returns the raw dataframe with `value` coerced to numeric.
    """
    data_dir = os.path.join(HERE, os.path.basename(analysis_config.RAW_DATA_DIR)) \
        if not os.path.isabs(analysis_config.RAW_DATA_DIR) else analysis_config.RAW_DATA_DIR
    # RAW_DATA_DIR in analysis_config.py is given relative to the repo root
    # (e.g. "audit/outliers/biocirv_outlier_assessment/data"). Resolve it
    # relative to the current working directory first; fall back to a path
    # relative to this script's directory for robustness.
    candidates_dir = analysis_config.RAW_DATA_DIR
    pattern = os.path.join(candidates_dir, analysis_config.RAW_DATA_GLOB)
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


def _first_non_null(series: pd.Series):
    """Return the first non-null value in a series, or None if all null."""
    non_null = series.dropna()
    return non_null.iloc[0] if len(non_null) > 0 else None


def build_replicate_group_summary(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Group `df` by REPLICATE_GROUP_KEYS (dropna=False — mandatory, see
    module docstring) and compute one summary row per group.

    Returns (summary_df, n_metadata_warnings).
    """
    # dropna=False is CRITICAL: without it, pandas silently excludes the ~27
    # rows with a null experiment_id from every group instead of giving them
    # their own group. sort=False preserves encounter order (not required for
    # correctness, but keeps replicate_group_id assignment deterministic given
    # a fixed input file).
    grouped = df.groupby(REPLICATE_GROUP_KEYS, dropna=False, sort=False)

    rows = []
    n_metadata_warnings = 0

    for group_idx, (gkey, sub) in enumerate(grouped, start=1):
        key_dict = dict(zip(REPLICATE_GROUP_KEYS, gkey if isinstance(gkey, tuple) else (gkey,)))

        values = sub["value"].tolist()
        n_replicates = len(sub)
        mean = sub["value"].mean()
        median = sub["value"].median()
        min_v = sub["value"].min()
        max_v = sub["value"].max()
        range_v = max_v - min_v

        # Sample SD (ddof=1): undefined (NaN, not 0) for a single observation.
        if n_replicates == 1:
            sd = np.nan
        else:
            sd = sub["value"].std(ddof=1)

        # RSD%: NaN (never inf) when mean is (near-)zero or n_replicates == 1.
        if n_replicates == 1 or abs(mean) < RSD_MEAN_EPSILON:
            rsd_percent = np.nan
        else:
            rsd_percent = (sd / mean) * 100.0

        # Metadata consistency check for columns NOT part of the grouping key
        # but expected to be constant per group (resource_id, resource_type,
        # lab, protocol_version). Warn + log if >1 distinct non-null value.
        metadata_values = {}
        for col in METADATA_CONSISTENCY_COLS:
            distinct_non_null = sub[col].dropna().unique().tolist()
            if len(distinct_non_null) > 1:
                n_metadata_warnings += 1
                print(
                    f"WARNING: metadata inconsistency in column '{col}' for group "
                    f"{key_dict}: found distinct values {distinct_non_null}. "
                    f"Using first non-null value for output."
                )
            metadata_values[col] = _first_non_null(sub[col])

        # existing_QC_status: comma-joined string of DISTINCT values, as-is
        # (never resolved/collapsed per handoff guardrail).
        qc_status_distinct = sorted(
            {str(x) for x in sub["existing_QC_status"].dropna().tolist()}
        )
        qc_status_joined = ",".join(qc_status_distinct)

        rows.append(
            {
                "replicate_group_id": group_idx,
                "sample_id": key_dict["sample_id"],
                "resource_id": metadata_values["resource_id"],
                "resource_type": metadata_values["resource_type"],
                "analysis_type": key_dict["analysis_type"],
                "parameter": key_dict["parameter"],
                "lab": metadata_values["lab"],
                "method": key_dict["method"],
                "protocol_version": metadata_values["protocol_version"],
                "unit": key_dict["unit"],
                "experiment_id": key_dict["experiment_id"],
                "n_replicates": n_replicates,
                "mean": mean,
                "median": median,
                "standard_deviation": sd,
                "RSD_percent": rsd_percent,
                "min": min_v,
                "max": max_v,
                "range": range_v,
                "values": ",".join(str(v) for v in values),
                "source_record_ids": ",".join(sub["record_id"].astype(str).tolist()),
                "existing_QC_status": qc_status_joined,
            }
        )

    summary_df = pd.DataFrame(rows)
    return summary_df, n_metadata_warnings


def print_validation_summary(summary_df: pd.DataFrame, n_metadata_warnings: int) -> None:
    total_groups = len(summary_df)
    n_singleton = int((summary_df["n_replicates"] == 1).sum())
    singleton_rate = 100.0 * n_singleton / total_groups if total_groups else 0.0

    # QC-status heterogeneity: groups where the comma-joined distinct list
    # contains more than one value.
    n_qc_heterogeneous = int(
        summary_df["existing_QC_status"].apply(lambda s: len(s.split(",")) > 1 if s else False).sum()
    )

    print("\n=== Validation Summary ===")
    print(f"Total replicate groups: {total_groups}")
    print(f"Singleton groups (n_replicates == 1): {n_singleton} ({singleton_rate:.1f}%)")
    print(f"Groups with existing_QC_status heterogeneity (>1 distinct value): {n_qc_heterogeneous}")
    print(f"Metadata-inconsistency warnings triggered: {n_metadata_warnings}")

    print("\nPer-analysis_type group counts (cross-check vs Step 0 STEP0_FINDINGS.md):")
    actual_counts = summary_df.groupby("analysis_type", dropna=False).size().to_dict()
    any_mismatch = False
    for atype, expected in EXPECTED_GROUP_COUNTS.items():
        actual = actual_counts.get(atype, 0)
        status = "OK" if actual == expected else "MISMATCH"
        if actual != expected:
            any_mismatch = True
        print(f"  {atype:15s} expected={expected:5d}  actual={actual:5d}  [{status}]")

    # Report any analysis_type present in actual but not in expected (unexpected extra)
    for atype, actual in actual_counts.items():
        if atype not in EXPECTED_GROUP_COUNTS:
            any_mismatch = True
            print(f"  {str(atype):15s} expected=  n/a  actual={actual:5d}  [UNEXPECTED ANALYSIS_TYPE]")

    total_status = "OK" if total_groups == EXPECTED_TOTAL_GROUPS else "MISMATCH"
    if total_groups != EXPECTED_TOTAL_GROUPS:
        any_mismatch = True
    print(f"  {'TOTAL':15s} expected={EXPECTED_TOTAL_GROUPS:5d}  actual={total_groups:5d}  [{total_status}]")

    if any_mismatch:
        print(
            "\n*** FLAG: group counts do NOT match Step 0's confirmed numbers. ***\n"
            "This is a likely bug — e.g. check that groupby() used dropna=False, "
            "that no rows were filtered before grouping, and that REPLICATE_GROUP_KEYS "
            "matches analysis_config.py exactly."
        )
    else:
        print("\nAll per-analysis_type counts and total match Step 0's confirmed numbers. No mismatch detected.")


def main() -> None:
    df = load_latest_raw_extract()
    print(f"Total raw rows loaded: {len(df)}")

    summary_df, n_metadata_warnings = build_replicate_group_summary(df)

    output_dir = analysis_config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "replicate_group_summary.csv")
    summary_df.to_csv(output_path, index=False)
    print(f"\nWrote {len(summary_df)} replicate-group rows to: {output_path}")

    print_validation_summary(summary_df, n_metadata_warnings)

    # --- Spot checks -----------------------------------------------------
    print("\n=== head() ===")
    print(summary_df.head().to_string())

    print("\n=== Spot-check: one multi-replicate group ===")
    multi = summary_df[summary_df["n_replicates"] >= 2]
    if len(multi) > 0:
        example = multi.iloc[0]
        print(example.to_string())
        raw_values = [float(v) for v in example["values"].split(",")]
        manual_mean = sum(raw_values) / len(raw_values)
        manual_sd = float(np.std(raw_values, ddof=1))
        manual_rsd = (manual_sd / manual_mean) * 100.0 if abs(manual_mean) >= RSD_MEAN_EPSILON else np.nan
        print(f"Raw values: {raw_values}")
        print(f"Manually computed mean={manual_mean}, sd={manual_sd}, rsd%={manual_rsd}")
        print(
            f"Computed columns   mean={example['mean']}, sd={example['standard_deviation']}, "
            f"rsd%={example['RSD_percent']}"
        )
    else:
        print("No multi-replicate groups found (unexpected).")

    print("\n=== Spot-check: one singleton group (n_replicates == 1) ===")
    singletons = summary_df[summary_df["n_replicates"] == 1]
    if len(singletons) > 0:
        example = singletons.iloc[0]
        print(example.to_string())
        sd_is_nan = pd.isna(example["standard_deviation"])
        rsd_is_nan = pd.isna(example["RSD_percent"])
        print(f"standard_deviation is NaN: {sd_is_nan}")
        print(f"RSD_percent is NaN: {rsd_is_nan}")
    else:
        print("No singleton groups found (unexpected).")


if __name__ == "__main__":
    main()
