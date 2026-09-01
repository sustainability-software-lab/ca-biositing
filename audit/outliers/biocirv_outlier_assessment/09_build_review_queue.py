"""
09_build_review_queue.py - Step 9 Part A (handoff v4 follow-on, "Turn the
Step 8 statistical-flag backlog into an operationally useful review
queue").

Purpose:
Build a single, de-duplicated review queue of every replicate group
flagged by AT LEAST ONE of the three candidate screens already computed in
Steps 3/8 (`rsd_gt_20`, `dixon_flag_0_05`, `flag_3xSD`). This script does
NOT recompute RSD, Dixon, or the 3xSD flag from scratch - it reuses the
already-computed flag columns from `replicate_group_summary.csv` (Step 1/3)
and `replicate_group_3xSD_flags.csv` (Step 8) exactly as-is, joined on
`replicate_group_id`, using the identical "NaN/not-applicable == not
flagged" simplification that `08_compare_candidate_rules.py` used for its
overlap tally (see that script's `build_overlap_summary()`). This is a
deliberate, explicitly-labeled simplification carried forward for
consistency, not a new statistical choice.

TERMINOLOGY_NOTE_LAB_METHOD: the upstream lab and method columns
(unchanged, persisted verbatim in Steps 1-8's own CSVs) are semantically
mislabeled -- lab actually holds provider / source codename values (e.g.
"rigging"), not a laboratory identifier, and method actually holds sample
preparation method values (e.g. "knife mill (2mm)"), not the analytical
method. This script does NOT rename the upstream CSV columns it reads, but
DOES alias them to human-readable names (provider,
sample_preparation_method) in its OWN output (flagged_review_queue.csv) so
downstream consumers see accurate labels.

*** CRITICAL FRAMING (repeated throughout Step 9): a statistical flag is
NOT a determination that the underlying data is invalid, bad, or should be
excluded. This script only organizes review workload - it does not filter,
exclude, or alter any replicate group's underlying values. ***

Outputs:
    outputs/flagged_review_queue.csv - 427 rows (one per flagged replicate
    group), with a `flag_category` column classifying which of the 7
    mutually-exclusive flag combinations applies.

Validation performed (must pass before this script reports success):
    1. len(flagged_review_queue) == 427
    2. flag_category value_counts exactly match
       outputs/candidate_rule_overlap_summary.csv's per-category counts.

Guardrails honored:
- Does not modify replicate_group_summary.csv or replicate_group_3xSD_flags.csv.
- Does not recompute RSD, Dixon, or 3xSD.
- Does not implement ROUT.
- Does not create any new statistical thresholds.
- Does not classify or imply flagged data is bad/invalid.

Usage:
    pixi run python audit/outliers/biocirv_outlier_assessment/09_build_review_queue.py
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis_config  # noqa: E402

SUMMARY_PATH = os.path.join(analysis_config.OUTPUT_DIR, "replicate_group_summary.csv")
FLAGS_3XSD_PATH = os.path.join(analysis_config.OUTPUT_DIR, "replicate_group_3xSD_flags.csv")
OVERLAP_SUMMARY_PATH = os.path.join(analysis_config.OUTPUT_DIR, "candidate_rule_overlap_summary.csv")

OUTPUT_QUEUE_PATH = os.path.join(analysis_config.OUTPUT_DIR, "flagged_review_queue.csv")

EXPECTED_TOTAL_ROWS = 2712
EXPECTED_QUEUE_ROWS = 427

QUEUE_COLUMNS = [
    "replicate_group_id",
    "sample_id",
    "resource_id",
    "resource_type",
    "analysis_type",
    "parameter",
    "provider",
    "sample_preparation_method",
    "protocol_version",
    "experiment_id",
    "n_replicates",
    "mean",
    "standard_deviation",
    "RSD_percent",
    "existing_QC_status",
    "rsd_gt_20",
    "dixon_flag_0_05",
    "flag_3xSD",
    "dixon_candidate_record_id",
    "flag_category",
]

EXPECTED_CATEGORY_COUNTS = {
    "RSD_only": 140,
    "Dixon_only": 224,
    "3xSD_only": 23,
    "RSD_and_Dixon": 12,
    "RSD_and_3xSD": 18,
    "Dixon_and_3xSD": 3,
    "all_three": 7,
}

QUEUE_TO_OVERLAP_CATEGORY_NAME = {
    "RSD_only": "RSD20_only",
    "Dixon_only": "Dixon_only",
    "3xSD_only": "3xSD_only",
    "RSD_and_Dixon": "RSD20_and_Dixon",
    "RSD_and_3xSD": "RSD20_and_3xSD",
    "Dixon_and_3xSD": "Dixon_and_3xSD",
    "all_three": "all_three",
}


def load_joined_summary():
    if not os.path.exists(SUMMARY_PATH):
        raise FileNotFoundError(SUMMARY_PATH + " not found - run 01_build_replicate_summary.py first.")
    if not os.path.exists(FLAGS_3XSD_PATH):
        raise FileNotFoundError(FLAGS_3XSD_PATH + " not found - run 08_compare_candidate_rules.py first.")

    summary = pd.read_csv(SUMMARY_PATH)
    print("Loaded " + str(len(summary)) + " rows from " + SUMMARY_PATH)
    if len(summary) != EXPECTED_TOTAL_ROWS:
        print("*** WARNING: row count mismatch. Proceeding anyway. ***")

    flags3 = pd.read_csv(FLAGS_3XSD_PATH)
    print("Loaded " + str(len(flags3)) + " rows from " + FLAGS_3XSD_PATH)

    flags3_slim = flags3[["replicate_group_id", "pooled_SD_used", "flag_3xSD", "3xSD_status"]]

    joined = summary.merge(flags3_slim, on="replicate_group_id", how="left", validate="one_to_one")
    if len(joined) != len(summary):
        raise AssertionError("Join changed row count unexpectedly.")
    print("Joined on replicate_group_id -> " + str(len(joined)) + " rows.")

    # Alias the upstream lab/method columns (unchanged, persisted as-is from
    # Steps 1-8) to human-readable names for THIS script's own output only.
    # See module docstring's TERMINOLOGY_NOTE_LAB_METHOD above: lab actually
    # holds provider/source codename values, method actually holds sample
    # preparation method values.
    joined = joined.rename(columns={"lab": "provider", "method": "sample_preparation_method"})
    return joined


def compute_flag_masks(df):
    rsd20 = (df["rsd_gt_20"] == True).fillna(False).astype(bool)  # noqa: E712
    dixon = (df["dixon_flag_0_05"] == True).fillna(False).astype(bool)  # noqa: E712
    sd3x = (df["flag_3xSD"] == True).fillna(False).astype(bool)  # noqa: E712
    return rsd20, dixon, sd3x


def assign_flag_category(rsd20, dixon, sd3x):
    category = pd.Series(index=rsd20.index, dtype=object)

    category[rsd20 & ~dixon & ~sd3x] = "RSD_only"
    category[~rsd20 & dixon & ~sd3x] = "Dixon_only"
    category[~rsd20 & ~dixon & sd3x] = "3xSD_only"
    category[rsd20 & dixon & ~sd3x] = "RSD_and_Dixon"
    category[rsd20 & ~dixon & sd3x] = "RSD_and_3xSD"
    category[~rsd20 & dixon & sd3x] = "Dixon_and_3xSD"
    category[rsd20 & dixon & sd3x] = "all_three"

    if category.isna().any():
        raise AssertionError("Some rows could not be assigned a flag_category.")
    return category


def build_review_queue(joined):
    rsd20, dixon, sd3x = compute_flag_masks(joined)
    flagged_mask = rsd20 | dixon | sd3x

    queue = joined.loc[flagged_mask].copy()
    queue["flag_category"] = assign_flag_category(rsd20[flagged_mask], dixon[flagged_mask], sd3x[flagged_mask])

    queue = queue[QUEUE_COLUMNS]
    return queue


def validate_against_overlap_summary(queue):
    ok_len = len(queue) == EXPECTED_QUEUE_ROWS
    print("\n[VALIDATION] flagged_review_queue.csv row count == 427: got " + str(len(queue)) + " [" + ("PASS" if ok_len else "FAIL") + "]")
    if not ok_len:
        raise AssertionError("flagged_review_queue.csv row count mismatch.")

    if not os.path.exists(OVERLAP_SUMMARY_PATH):
        raise FileNotFoundError(OVERLAP_SUMMARY_PATH + " not found.")
    overlap_df = pd.read_csv(OVERLAP_SUMMARY_PATH).set_index("category")["count"].to_dict()

    actual_counts = queue["flag_category"].value_counts().to_dict()

    print("\n[VALIDATION] flag_category cross-tab vs candidate_rule_overlap_summary.csv:")
    all_pass = True
    for queue_cat, overlap_cat in QUEUE_TO_OVERLAP_CATEGORY_NAME.items():
        expected = int(overlap_df.get(overlap_cat, -1))
        actual = int(actual_counts.get(queue_cat, 0))
        ok = expected == actual
        all_pass = all_pass and ok
        print("  " + queue_cat + " (== " + overlap_cat + "): expected=" + str(expected) + " actual=" + str(actual) + " [" + ("PASS" if ok else "FAIL") + "]")

    if not all_pass:
        raise AssertionError("flag_category breakdown does not match candidate_rule_overlap_summary.csv.")
    print("\n[VALIDATION] All 7 flag_category counts match candidate_rule_overlap_summary.csv exactly. PASS.")


def main():
    joined = load_joined_summary()
    queue = build_review_queue(joined)

    validate_against_overlap_summary(queue)

    queue.to_csv(OUTPUT_QUEUE_PATH, index=False)
    print("\nWrote " + str(len(queue)) + " rows to: " + OUTPUT_QUEUE_PATH)

    print("\n=== flag_category breakdown (flagged_review_queue.csv) ===")
    counts = queue["flag_category"].value_counts()
    for cat in EXPECTED_CATEGORY_COUNTS:
        print("  " + cat + ": " + str(int(counts.get(cat, 0))))
    print("  TOTAL: " + str(len(queue)))

    print(
        "\nReminder: a statistical flag is NOT a determination that the underlying "
        "data is invalid or should be excluded. This queue organizes review "
        "workload only; no data has been altered, excluded, or judged bad."
    )


if __name__ == "__main__":
    main()
