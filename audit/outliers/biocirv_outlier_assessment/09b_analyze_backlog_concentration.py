"""
09b_analyze_backlog_concentration.py - Step 9 Parts B, C, D (handoff v4
follow-on).

Reads `outputs/flagged_review_queue.csv` (427 rows, built by
`09_build_review_queue.py`) plus `outputs/replicate_group_summary.csv`
(2712 rows, all replicate groups - used ONLY as denominators for rate
calculations) and `outputs/candidate_rule_comparison.csv` (74 rows, one per
analysis_type x parameter - used ONLY as the denominator for Part B.1).

*** CRITICAL FRAMING (repeated throughout Step 9): a statistical flag is
NOT a determination that the underlying data is invalid, bad, or should be
excluded. This script mea I think it's a good idea to have a Oh, just so you know, if you're making brown rice, there's a bunch in the Fridge already. Oh, word. Well, I was, I literally was like, if I'm making the brown rice, I might as well Because I did Well, I'll tell you if I talk on the phone, Now I did not hear my phone, but I think that's rare. It doesn't happen to me so often.review WORKLOAD and organizes investigation
only - it does not filter, exclude, or judge any replicate group's
underlying data. ***

Part B - Concentration of the backlog:
    B.1: outputs/review_queue_by_analysis_parameter.csv - one row per
         analysis_type x parameter present in the queue, with counts AND
         rates (n_flagged_groups / n_replicate_groups_for_that_combo).
    B.2: outputs/review_queue_by_dimension_summary.csv - one combined table
         (dimension, value, n_flagged_groups, percent_of_total_flags,
         n_replicate_groups_total, flag_rate_percent) covering
         analysis_type, resource_type, experiment_id, lab, method,
         protocol_version, existing_QC_status. EVERY groupby here uses
         dropna=False so that groups with a null dimension value form
         their own explicit "(missing)" row rather than vanishing.

Part C - Provisional investigation-packet consolidation:
    Tests the grouping key `analysis_type + parameter + experiment_id`
    (dropna=False) against a handful of alternatives that add resource_id /
    lab / method / protocol_version, reports a small comparison table, then
    builds outputs/investigation_packets.csv using the CHOSEN key.

    LIMITATION (documented per Step 9 spec, repeated in STEP9_FINDINGS.md):
    `experiment_id` is used here as a convenience batching key. The data
    does NOT establish that `experiment_id` corresponds to a specific
    day/run/batch in a way that guarantees an analyst can investigate all
    flagged groups within one experiment as a single coherent root-cause
    investigation. This is a provisional MVP simplification, not a
    validated investigation unit.

Part D - Approximate analyst workload:
    A planning-scenario-only table (5 / 10 / 15 minutes-per-review) applied
    to both the raw 427-group queue and the packet-consolidated queue, plus
    an "X minutes per 100 replicate groups reviewed" rate. Explicitly
    labeled as PLANNING SCENARIOS ONLY, NOT measured analyst-time
    estimates.

Guardrails honored:
- Does not modify Steps 0-8 or their outputs.
- Does not change RSD/Dixon/3xSD calculation logic.
- Does not implement ROUT.
- Does not create new statistical thresholds.
- Does not classify or imply flagged data is bad/invalid.
- Every dimension/packet groupby explicitly uses dropna=False.

Usage:
    pixi run python audit/outliers/biocirv_outlier_assessment/09b_analyze_backlog_concentration.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis_config  # noqa: E402

QUEUE_PATH = os.path.join(analysis_config.OUTPUT_DIR, "flagged_review_queue.csv")
SUMMARY_PATH = os.path.join(analysis_config.OUTPUT_DIR, "replicate_group_summary.csv")
COMPARISON_PATH = os.path.join(analysis_config.OUTPUT_DIR, "candidate_rule_comparison.csv")

OUTPUT_BY_ANALYSIS_PARAMETER_PATH = os.path.join(
    analysis_config.OUTPUT_DIR, "review_queue_by_analysis_parameter.csv"
)
OUTPUT_DIMENSION_SUMMARY_PATH = os.path.join(analysis_config.OUTPUT_DIR, "review_queue_by_dimension_summary.csv")
OUTPUT_PACKETS_PATH = os.path.join(analysis_config.OUTPUT_DIR, "investigation_packets.csv")

EXPECTED_QUEUE_ROWS = 427
EXPECTED_TOTAL_ROWS = 2712

MISSING_LABEL = "(missing)"

# Dimensions summarized individually in Part B.2. Every groupby against
# these columns MUST use dropna=False.
DIMENSION_COLUMNS = [
    "analysis_type",
    "resource_type",
    "experiment_id",
    "lab",
    "method",
    "protocol_version",
    "existing_QC_status",
]

# Chosen MVP investigation-packet grouping key (Part C).
PACKET_GROUP_KEY = ["analysis_type", "parameter", "experiment_id"]

# Alternative grouping keys tested for comparison (Part C.2), all built on
# top of PACKET_GROUP_KEY, all evaluated with dropna=False.
ALTERNATIVE_GROUP_KEYS = {
    "base (analysis_type+parameter+experiment_id)": PACKET_GROUP_KEY,
    "+resource_id": PACKET_GROUP_KEY + ["resource_id"],
    "+lab": PACKET_GROUP_KEY + ["lab"],
    "+method": PACKET_GROUP_KEY + ["method"],
    "+protocol_version": PACKET_GROUP_KEY + ["protocol_version"],
    "+resource_id+lab+method+protocol_version (all)": PACKET_GROUP_KEY
    + ["resource_id", "lab", "method", "protocol_version"],
}

# Part D workload planning scenarios (minutes per review). PLANNING
# SCENARIOS ONLY - not measured analyst-time estimates.
WORKLOAD_SCENARIOS = [
    ("Fast", 5),
    ("Moderate", 10),
    ("Thorough", 15),
]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_inputs():
    for path in (QUEUE_PATH, SUMMARY_PATH, COMPARISON_PATH):
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} not found - run the prerequisite script first.")

    queue = pd.read_csv(QUEUE_PATH)
    print(f"Loaded {len(queue)} rows from {QUEUE_PATH}")
    if len(queue) != EXPECTED_QUEUE_ROWS:
        raise AssertionError(
            f"flagged_review_queue.csv has {len(queue)} rows, expected exactly {EXPECTED_QUEUE_ROWS}. "
            "Re-run 09_build_review_queue.py and confirm it passes validation before running this script."
        )

    summary = pd.read_csv(SUMMARY_PATH)
    print(f"Loaded {len(summary)} rows from {SUMMARY_PATH}")
    if len(summary) != EXPECTED_TOTAL_ROWS:
        print(f"*** WARNING: row count {len(summary)} != expected {EXPECTED_TOTAL_ROWS}. Proceeding anyway. ***")

    comparison = pd.read_csv(COMPARISON_PATH)
    print(f"Loaded {len(comparison)} rows from {COMPARISON_PATH}")

    return queue, summary, comparison


# ---------------------------------------------------------------------------
# Part B.1 - review_queue_by_analysis_parameter.csv
# ---------------------------------------------------------------------------


def build_by_analysis_parameter(queue: pd.DataFrame, comparison: pd.DataFrame) -> pd.DataFrame:
    flagged_counts = (
        queue.groupby(["analysis_type", "parameter"], dropna=False)
        .size()
        .reset_index(name="n_flagged_groups")
    )

    comp_slim = comparison[["analysis_type", "parameter", "n_replicate_groups"]].copy()
    comp_slim["n_replicate_groups"] = comp_slim["n_replicate_groups"].astype(int)

    merged = flagged_counts.merge(comp_slim, on=["analysis_type", "parameter"], how="left")

    if merged["n_replicate_groups"].isna().any():
        missing = merged[merged["n_replicate_groups"].isna()]
        raise AssertionError(
            "Some analysis_type x parameter combos in the flagged queue have no matching row in "
            f"candidate_rule_comparison.csv:\n{missing}"
        )

    merged["percent_of_total_flags"] = merged["n_flagged_groups"] / EXPECTED_QUEUE_ROWS * 100
    merged["flag_rate_percent"] = merged["n_flagged_groups"] / merged["n_replicate_groups"] * 100

    merged = merged.sort_values("n_flagged_groups", ascending=False).reset_index(drop=True)
    merged = merged[
        [
            "analysis_type",
            "parameter",
            "n_flagged_groups",
            "percent_of_total_flags",
            "n_replicate_groups",
            "flag_rate_percent",
        ]
    ]
    return merged


# ---------------------------------------------------------------------------
# Part B.2 - review_queue_by_dimension_summary.csv (one combined table)
# ---------------------------------------------------------------------------


def _label_value(v):
    """Render a groupby key value for display/CSV, mapping NaN -> '(missing)'."""
    if pd.isna(v):
        return MISSING_LABEL
    return v


def build_dimension_summary(queue: pd.DataFrame, summary: pd.DataFrame, dim: str) -> pd.DataFrame:
    """Build counts + rates for a single dimension. CRITICAL: dropna=False
    on BOTH groupby calls so null values form their own explicit
    '(missing)' row rather than being silently dropped.
    """
    flagged_counts = queue.groupby(dim, dropna=False).size().rename("n_flagged_groups")
    total_counts = summary.groupby(dim, dropna=False).size().rename("n_replicate_groups_total")

    merged = pd.concat([flagged_counts, total_counts], axis=1)
    # Groups present in summary but not in the flagged queue have n_flagged_groups == NaN -> 0.
    merged["n_flagged_groups"] = merged["n_flagged_groups"].fillna(0).astype(int)
    # Groups present in the flagged queue but (should never happen) absent from summary -> NaN denominator.
    merged = merged.reset_index().rename(columns={dim: "value"})

    merged["dimension"] = dim
    merged["value"] = merged["value"].apply(_label_value)
    merged["percent_of_total_flags"] = merged["n_flagged_groups"] / EXPECTED_QUEUE_ROWS * 100
    merged["flag_rate_percent"] = merged["n_flagged_groups"] / merged["n_replicate_groups_total"] * 100

    # Only keep rows that actually appear in the flagged queue (n_flagged_groups > 0) for
    # readability, EXCEPT we always want to see rows even with 0 flags is not required by spec;
    # spec wants counts/rates for the queue's dimensions, so restrict to flagged-queue values,
    # but denominator remains the FULL dataset's group count for that value (not just flagged).
    merged = merged[merged["n_flagged_groups"] > 0].copy()

    merged = merged.sort_values("n_flagged_groups", ascending=False).reset_index(drop=True)
    merged = merged[
        ["dimension", "value", "n_flagged_groups", "percent_of_total_flags", "n_replicate_groups_total", "flag_rate_percent"]
    ]
    return merged


def build_all_dimension_summaries(queue: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    frames = [build_dimension_summary(queue, summary, dim) for dim in DIMENSION_COLUMNS]
    combined = pd.concat(frames, ignore_index=True)
    return combined


# ---------------------------------------------------------------------------
# Part B - printed reporting (top contributors, top-5/top-10 concentration, QC overlap)
# ---------------------------------------------------------------------------


def print_top_contributors(by_ap: pd.DataFrame) -> tuple[float, float]:
    print("\n=== Part B: Top analysis_type x parameter contributors to the 427-group backlog ===")
    top10 = by_ap.head(10)
    print(
        top10[
            ["analysis_type", "parameter", "n_flagged_groups", "percent_of_total_flags", "n_replicate_groups", "flag_rate_percent"]
        ].to_string(index=False)
    )

    top5_pct = float(by_ap.head(5)["n_flagged_groups"].sum() / EXPECTED_QUEUE_ROWS * 100)
    top10_pct = float(by_ap.head(10)["n_flagged_groups"].sum() / EXPECTED_QUEUE_ROWS * 100)
    print(f"\nTop-5 analysis_type x parameter combinations account for {top5_pct:.1f}% of all {EXPECTED_QUEUE_ROWS} flags.")
    print(f"Top-10 analysis_type x parameter combinations account for {top10_pct:.1f}% of all {EXPECTED_QUEUE_ROWS} flags.")
    return top5_pct, top10_pct


def print_dimension_summaries(dim_summary: pd.DataFrame) -> None:
    print("\n=== Part B: By-dimension backlog concentration (counts AND rates; dropna=False throughout) ===")
    for dim in DIMENSION_COLUMNS:
        sub = dim_summary[dim_summary["dimension"] == dim].head(10)
        n_distinct_values_with_flags = len(dim_summary[dim_summary["dimension"] == dim])
        print(f"\n--- {dim} (top up to 10 of {n_distinct_values_with_flags} values with >=1 flag) ---")
        print(sub[["value", "n_flagged_groups", "percent_of_total_flags", "n_replicate_groups_total", "flag_rate_percent"]].to_string(index=False))


def print_experiment_resource_clustering(queue: pd.DataFrame, summary: pd.DataFrame) -> None:
    print("\n=== Part B: Clustering concentration summary (counts AND rates) ===")
    for dim in ["experiment_id", "resource_id", "lab", "method", "protocol_version"]:
        flagged_by_dim = queue.groupby(dim, dropna=False).size().sort_values(ascending=False)
        n_distinct_flagged = len(flagged_by_dim)
        n_distinct_total = summary[dim].nunique(dropna=False)
        # top-N values needed to reach >=50% of flags
        cumsum_pct = flagged_by_dim.cumsum() / EXPECTED_QUEUE_ROWS * 100
        n_to_half = int((cumsum_pct < 50).sum()) + 1 if len(cumsum_pct) else 0
        top_val = flagged_by_dim.index[0] if len(flagged_by_dim) else None
        top_val_label = _label_value(top_val)
        top_val_count = int(flagged_by_dim.iloc[0]) if len(flagged_by_dim) else 0
        top_val_total = int(summary.groupby(dim, dropna=False).size().get(top_val, np.nan)) if len(flagged_by_dim) else 0
        top_val_rate = (top_val_count / top_val_total * 100) if top_val_total else float("nan")
        print(
            f"  {dim}: {n_distinct_flagged} distinct value(s) among the {n_distinct_total} total appear in the "
            f"flagged queue; {n_to_half} value(s) account for >=50% of the {EXPECTED_QUEUE_ROWS} flags. "
            f"Single largest contributor: '{top_val_label}' with {top_val_count} flags "
            f"({top_val_count}/{top_val_total} = {top_val_rate:.1f}% of its own replicate groups flagged)."
        )


def print_qc_status_overlap(queue: pd.DataFrame) -> None:
    print("\n=== Part B: existing_QC_status overlap with statistical flags (descriptive only, no causal claim) ===")
    counts = queue["existing_QC_status"].value_counts(dropna=False)
    for status, count in counts.items():
        label = _label_value(status)
        pct = count / EXPECTED_QUEUE_ROWS * 100
        print(f"  existing_QC_status = {label!r}: {count} flagged groups ({pct:.1f}% of the {EXPECTED_QUEUE_ROWS}-group queue)")
    print(
        "\nNote: most flagged groups carry an existing_QC_status of 'pass' (the dominant status across the "
        "whole dataset), so the presence of 'pass' among flagged groups is expected and NOT evidence that "
        "statistical flags contradict analyst QC. The relevant descriptive question is whether NON-'pass' "
        "statuses ('fail', 'provisional', and compound values) are over- or under-represented among flagged "
        "groups relative to the full dataset - reported purely descriptively above, no causal claim made."
    )


# ---------------------------------------------------------------------------
# Part C - investigation packet grouping comparison + build
# ---------------------------------------------------------------------------


def compare_grouping_keys(queue: pd.DataFrame) -> pd.DataFrame:
    records = []
    for label, keys in ALTERNATIVE_GROUP_KEYS.items():
        sizes = queue.groupby(keys, dropna=False).size()
        n_packets = len(sizes)
        median_size = float(sizes.median())
        max_size = int(sizes.max())
        n_singleton = int((sizes == 1).sum())
        records.append(
            {
                "grouping_key": label,
                "n_packets": n_packets,
                "median_group_size": median_size,
                "max_group_size": max_size,
                "n_singleton_packets": n_singleton,
                "percent_singleton_packets": n_singleton / n_packets * 100 if n_packets else np.nan,
            }
        )
    return pd.DataFrame.from_records(records)


def print_grouping_comparison(comparison_table: pd.DataFrame) -> None:
    print("\n=== Part C.2: Investigation-packet grouping-key comparison (all dropna=False) ===")
    print(comparison_table.to_string(index=False))
    print(
        "\nInterpretation: adding resource_id, lab, method, or protocol_version to the base "
        "(analysis_type+parameter+experiment_id) key increases the packet count toward the raw "
        "427-group count (i.e., most added splits produce singleton packets), which defeats the "
        "purpose of consolidation. protocol_version is 100% null in this dataset, so splitting on "
        "it changes nothing on its own. The base key is retained as the MVP grouping definition "
        "because it provides the most consolidation while remaining a plausible (if unproven) "
        "review-batching unit - see the documented limitation below."
    )


def _packet_id_component(v) -> str:
    if pd.isna(v):
        return MISSING_LABEL
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def build_investigation_packets(queue: pd.DataFrame) -> pd.DataFrame:
    """Build investigation_packets.csv using PACKET_GROUP_KEY
    (analysis_type + parameter + experiment_id), dropna=False so that
    groups with a null experiment_id form their own explicit packet(s)
    rather than being dropped.

    LIMITATION (see module docstring / STEP9_FINDINGS.md): experiment_id is
    used here as a convenience batching key. The data does not establish
    that experiment_id corresponds to a specific day/run/batch in a way
    that guarantees an analyst can investigate all flagged groups within
    one experiment as a single coherent root-cause investigation. This is
    a provisional MVP simplification, not a validated investigation unit.
    """
    records = []
    grouped = queue.groupby(PACKET_GROUP_KEY, dropna=False, sort=True)
    for key_values, group in grouped:
        if not isinstance(key_values, tuple):
            key_values = (key_values,)
        packet_id = "|".join(_packet_id_component(v) for v in key_values)
        replicate_group_ids = ",".join(str(x) for x in sorted(group["replicate_group_id"].tolist()))
        record = dict(zip(PACKET_GROUP_KEY, key_values))
        record["packet_id"] = packet_id
        record["n_flagged_groups_in_packet"] = len(group)
        record["replicate_group_ids"] = replicate_group_ids
        records.append(record)

    packets = pd.DataFrame.from_records(records)
    packets = packets.sort_values("n_flagged_groups_in_packet", ascending=False).reset_index(drop=True)

    ordered_cols = ["packet_id"] + PACKET_GROUP_KEY + ["n_flagged_groups_in_packet", "replicate_group_ids"]
    packets = packets[ordered_cols]
    return packets


def validate_packets(packets: pd.DataFrame, queue: pd.DataFrame) -> None:
    total = int(packets["n_flagged_groups_in_packet"].sum())
    ok_total = total == EXPECTED_QUEUE_ROWS
    print(
        f"\n[VALIDATION] sum(n_flagged_groups_in_packet) == {EXPECTED_QUEUE_ROWS}: got {total} "
        f"[{'PASS' if ok_total else 'FAIL'}]"
    )
    if not ok_total:
        raise AssertionError("Packet group-size sum does not equal 427 - some groups were lost or duplicated.")

    all_ids_in_packets = []
    for ids_str in packets["replicate_group_ids"]:
        all_ids_in_packets.extend(int(x) for x in ids_str.split(","))

    ok_no_dupes = len(all_ids_in_packets) == len(set(all_ids_in_packets))
    print(f"[VALIDATION] no replicate_group_id appears in more than one packet: [{'PASS' if ok_no_dupes else 'FAIL'}]")
    if not ok_no_dupes:
        raise AssertionError("Some replicate_group_id appears in more than one packet.")

    expected_ids = set(queue["replicate_group_id"].tolist())
    actual_ids = set(all_ids_in_packets)
    ok_complete = expected_ids == actual_ids
    print(
        f"[VALIDATION] every one of the {EXPECTED_QUEUE_ROWS} flagged replicate groups appears in exactly one "
        f"packet: [{'PASS' if ok_complete else 'FAIL'}]"
    )
    if not ok_complete:
        missing = expected_ids - actual_ids
        extra = actual_ids - expected_ids
        raise AssertionError(f"Packet membership mismatch. Missing: {missing}. Unexpected extra: {extra}.")


def print_packet_stats(packets: pd.DataFrame) -> None:
    n_packets = len(packets)
    sizes = packets["n_flagged_groups_in_packet"]
    median_size = float(sizes.median())
    max_size = int(sizes.max())
    n_multi = int((sizes > 1).sum())
    pct_multi = n_multi / n_packets * 100 if n_packets else np.nan

    print("\n=== Part C: Investigation packet statistics (chosen key: analysis_type+parameter+experiment_id) ===")
    print(f"Total raw flagged groups: {EXPECTED_QUEUE_ROWS} (confirmed)")
    print(f"Number of resulting packets: {n_packets}")
    print(f"Median flagged-groups-per-packet: {median_size}")
    print(f"Max flagged-groups-in-one-packet: {max_size}")
    print(f"Packets containing >1 flagged group: {n_multi} ({pct_multi:.1f}% of {n_packets} packets)")

    print("\nExamples of the largest packets (for sanity-checking):")
    for _, row in packets.head(3).iterrows():
        key_desc = ", ".join(f"{k}={row[k]}" for k in PACKET_GROUP_KEY)
        print(f"  packet_id={row['packet_id']!r} ({key_desc}): {row['n_flagged_groups_in_packet']} flagged groups")


# ---------------------------------------------------------------------------
# Part D - workload planning table
# ---------------------------------------------------------------------------


def print_workload_table(n_raw: int, n_packets: int) -> pd.DataFrame:
    print("\n=== Part D: Approximate analyst workload - PLANNING SCENARIOS ONLY, NOT measured analyst-time estimates ===")
    records = []
    for scenario, minutes_per_review in WORKLOAD_SCENARIOS:
        total_min_raw = minutes_per_review * n_raw
        total_hr_raw = total_min_raw / 60
        total_min_packets = minutes_per_review * n_packets
        total_hr_packets = total_min_packets / 60
        records.append(
            {
                "Scenario": scenario,
                "Minutes/review": minutes_per_review,
                f"Total minutes ({n_raw} raw groups)": total_min_raw,
                f"Total hours ({n_raw} raw groups)": round(total_hr_raw, 1),
                f"Total minutes ({n_packets} packets)": total_min_packets,
                f"Total hours ({n_packets} packets)": round(total_hr_packets, 1),
            }
        )
    table = pd.DataFrame.from_records(records)
    print(table.to_string(index=False))

    print("\nApproximate review rate (minutes per 100 replicate groups reviewed):")
    for scenario, minutes_per_review in WORKLOAD_SCENARIOS:
        rate_raw = minutes_per_review * 100
        rate_packets = minutes_per_review * 100 * (n_packets / n_raw)
        print(
            f"  {scenario} ({minutes_per_review} min/review): {rate_raw} min per 100 raw groups reviewed; "
            f"~{rate_packets:.0f} min per 100-raw-group-equivalent if reviewed via packets "
            f"(packet consolidation ratio {n_packets}/{n_raw} = {n_packets / n_raw:.3f})"
        )
    print(
        "\nLabel: these are PLANNING SCENARIOS ONLY, not measured analyst-time estimates. Actual "
        "review time will vary by analysis_type, data complexity, and analyst familiarity."
    )
    return table


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    queue, summary, comparison = load_inputs()

    # --- Part B.1 ---
    by_ap = build_by_analysis_parameter(queue, comparison)
    by_ap.to_csv(OUTPUT_BY_ANALYSIS_PARAMETER_PATH, index=False)
    print(f"\nWrote {len(by_ap)} rows to: {OUTPUT_BY_ANALYSIS_PARAMETER_PATH}")
    top5_pct, top10_pct = print_top_contributors(by_ap)

    # --- Part B.2 ---
    dim_summary = build_all_dimension_summaries(queue, summary)
    dim_summary.to_csv(OUTPUT_DIMENSION_SUMMARY_PATH, index=False)
    print(f"\nWrote {len(dim_summary)} rows to: {OUTPUT_DIMENSION_SUMMARY_PATH}")
    print_dimension_summaries(dim_summary)
    print_experiment_resource_clustering(queue, summary)
    print_qc_status_overlap(queue)

    # --- Part C ---
    comparison_table = compare_grouping_keys(queue)
    print_grouping_comparison(comparison_table)

    packets = build_investigation_packets(queue)
    validate_packets(packets, queue)
    packets.to_csv(OUTPUT_PACKETS_PATH, index=False)
    print(f"\nWrote {len(packets)} rows to: {OUTPUT_PACKETS_PATH}")
    print_packet_stats(packets)

    # --- Part D ---
    print_workload_table(n_raw=EXPECTED_QUEUE_ROWS, n_packets=len(packets))

    print(
        "\nReminder: a statistical flag is NOT a determination that the underlying data is invalid "
        "or should be excluded. This analysis measures review workload and organizes investigation "
        "only; no data has been altered, excluded, or judged bad."
    )


if __name__ == "__main__":
    main()
