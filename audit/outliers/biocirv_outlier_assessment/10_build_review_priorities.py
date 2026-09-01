"""
10_build_review_priorities.py - Step 10 (final step, handoff v4 follow-on):
"Turn the Step 9 review queue / packets into a small, human-review priority
list."

Purpose:
Build a short (5-10 row) human-review priority table identifying which
`experiment_id` and `analysis_type x parameter` targets would be most
efficient for a human reviewer to look at first, given the existing 427-row
statistical-flag backlog from Step 9. This script does NOT recompute RSD,
Dixon, or 3xSD, does NOT implement ROUT, and does NOT create any new
statistical thresholds or QC flags. It reads Step 9's own output CSVs
(`flagged_review_queue.csv`, `review_queue_by_analysis_parameter.csv`,
`review_queue_by_dimension_summary.csv`, `investigation_packets.csv`) and
Steps 1-8's `replicate_group_summary.csv` exactly as-is, and does not modify
any of them.

*** CRITICAL FRAMING (repeated from Step 9): a statistical flag is NOT a
determination that the underlying data is invalid, bad, or should be
excluded. This step only organizes review priority - it does not filter,
exclude, or alter any replicate group's underlying values. ***

Review-target grain: primarily `experiment_id` and `analysis_type x
parameter`. `provider`, `resource_type`, `sample_preparation_method`,
`flag_category`, and `existing_QC_status` are used only as supporting
context in the "why review" narrative, not as top-level grains (per the
task's explicit instruction), unless a dimension is promoted with explicit
justification (none was promoted in this run - see STEP10_FINDINGS.md).

Cumulative coverage rule: "Cumulative % of 427 flagged groups addressed" is
computed as the size of the actual set UNION of `replicate_group_id`s
covered by all selected priorities up through that row (not a naive running
sum), because a replicate group could in principle belong to more than one
selected target (e.g. an experiment-level target and an
analysis_type x parameter target can share member groups). This script
computes that union explicitly, row by row, in code.

Outputs:
    outputs/human_review_priorities.csv - one row per selected priority
    (5-10 rows), with the 8 required human-readable columns, a machine
    readable `grain` column, and 2 traceability columns
    (`replicate_group_id_list`, `source_record_ids_list`).

Guardrails honored:
- Does not modify any Steps 1-9 script or output CSV.
- Does not recompute RSD, Dixon, or 3xSD.
- Does not implement ROUT.
- Does not create any new statistical thresholds/flags.
- Does not state or imply any observation is invalid/wrong/should be
  excluded.
- Creates ONLY outputs/human_review_priorities.csv (this script) and
  STEP10_FINDINGS.md (written separately, by hand, from this script's
  printed output) - no other new CSVs.

Usage:
    pixi run python audit/outliers/biocirv_outlier_assessment/10_build_review_priorities.py
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis_config  # noqa: E402

FLAGGED_PATH = os.path.join(analysis_config.OUTPUT_DIR, "flagged_review_queue.csv")
RG_SUMMARY_PATH = os.path.join(analysis_config.OUTPUT_DIR, "replicate_group_summary.csv")
AP_QUEUE_PATH = os.path.join(analysis_config.OUTPUT_DIR, "review_queue_by_analysis_parameter.csv")
DIM_QUEUE_PATH = os.path.join(analysis_config.OUTPUT_DIR, "review_queue_by_dimension_summary.csv")
PACKETS_PATH = os.path.join(analysis_config.OUTPUT_DIR, "investigation_packets.csv")

OUTPUT_PATH = os.path.join(analysis_config.OUTPUT_DIR, "human_review_priorities.csv")

EXPECTED_FLAGGED_ROWS = 427
EXPECTED_TOTAL_ROWS = 2712
EXPECTED_PACKET_ROWS = 114

BASELINE_RATE_PERCENT = EXPECTED_FLAGGED_ROWS / EXPECTED_TOTAL_ROWS * 100.0


def verify_inputs(flagged: pd.DataFrame, rg: pd.DataFrame, ap_queue: pd.DataFrame,
                   dim_queue: pd.DataFrame, packets: pd.DataFrame) -> None:
    """Verify input file shapes/consistency per task instructions. Reports
    but does not attempt to fix any inconsistency found (out of scope)."""
    print("=== INPUT VERIFICATION ===")

    ok_427 = len(flagged) == EXPECTED_FLAGGED_ROWS
    print(f"flagged_review_queue.csv rows: {len(flagged)} (expected {EXPECTED_FLAGGED_ROWS}) -> "
          f"{'PASS' if ok_427 else 'FAIL'}")

    has_new_names = "provider" in flagged.columns and "sample_preparation_method" in flagged.columns
    has_legacy_names = "lab" in flagged.columns and "method" in flagged.columns
    print(f"flagged_review_queue.csv column naming: "
          f"provider/sample_preparation_method present = {has_new_names}; "
          f"legacy lab/method present = {has_legacy_names}")

    print(f"review_queue_by_analysis_parameter.csv loaded OK, shape={ap_queue.shape}, "
          f"columns={list(ap_queue.columns)}")
    print(f"review_queue_by_dimension_summary.csv loaded OK, shape={dim_queue.shape}, "
          f"columns={list(dim_queue.columns)}")

    ok_114 = len(packets) == EXPECTED_PACKET_ROWS
    packet_sum = packets["n_flagged_groups_in_packet"].sum()
    ok_sum = packet_sum == EXPECTED_FLAGGED_ROWS
    print(f"investigation_packets.csv rows: {len(packets)} (expected {EXPECTED_PACKET_ROWS}) -> "
          f"{'PASS' if ok_114 else 'FAIL'}")
    print(f"investigation_packets.csv sum(n_flagged_groups_in_packet): {packet_sum} "
          f"(expected {EXPECTED_FLAGGED_ROWS}) -> {'PASS' if ok_sum else 'FAIL'}")

    ok_rg = len(rg) == EXPECTED_TOTAL_ROWS
    print(f"replicate_group_summary.csv rows: {len(rg)} (expected {EXPECTED_TOTAL_ROWS}) -> "
          f"{'PASS' if ok_rg else 'FAIL'}")

    if not (ok_427 and ok_114 and ok_sum and ok_rg):
        print("*** WARNING: one or more input verification checks FAILED. "
              "Proceeding with best-effort use of the data that IS consistent, "
              "per task instructions. Not attempting to fix Step 9 outputs. ***")
    print()


def build_experiment_target(flagged: pd.DataFrame, rg: pd.DataFrame, experiment_id: float) -> dict:
    exp_flagged_mask = flagged["experiment_id"] == experiment_id
    exp_total_mask = rg["experiment_id"] == experiment_id
    group_ids = set(flagged.loc[exp_flagged_mask, "replicate_group_id"])
    n_flagged = len(group_ids)
    n_total = int(exp_total_mask.sum())
    flag_rate = n_flagged / n_total * 100.0 if n_total else 0.0
    enrichment = flag_rate / BASELINE_RATE_PERCENT if BASELINE_RATE_PERCENT else 0.0
    return {
        "review_target": f"experiment_id = {experiment_id:g}",
        "grain": "experiment_id",
        "group_ids": group_ids,
        "n_flagged": n_flagged,
        "n_total": n_total,
        "flag_rate": flag_rate,
        "enrichment": enrichment,
    }


def build_analysis_parameter_target(flagged: pd.DataFrame, rg: pd.DataFrame,
                                     analysis_type: str, parameter: str) -> dict:
    mask_flagged = (flagged["analysis_type"] == analysis_type) & (flagged["parameter"] == parameter)
    mask_total = (rg["analysis_type"] == analysis_type) & (rg["parameter"] == parameter)
    group_ids = set(flagged.loc[mask_flagged, "replicate_group_id"])
    n_flagged = len(group_ids)
    n_total = int(mask_total.sum())
    flag_rate = n_flagged / n_total * 100.0 if n_total else 0.0
    enrichment = flag_rate / BASELINE_RATE_PERCENT if BASELINE_RATE_PERCENT else 0.0
    return {
        "review_target": f"{analysis_type} x {parameter}",
        "grain": "analysis_type_x_parameter",
        "group_ids": group_ids,
        "n_flagged": n_flagged,
        "n_total": n_total,
        "flag_rate": flag_rate,
        "enrichment": enrichment,
    }


def top_subgroups_within_experiment(flagged: pd.DataFrame, experiment_id: float, top_n: int = 10) -> pd.DataFrame:
    sub = flagged[flagged["experiment_id"] == experiment_id]
    counts = (
        sub.groupby(["analysis_type", "parameter"])
        .size()
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index(name="n_flagged_groups")
    )
    return counts


def flag_category_breakdown(flagged: pd.DataFrame, mask: pd.Series) -> pd.Series:
    return flagged.loc[mask, "flag_category"].value_counts()


def existing_qc_status_breakdown(flagged: pd.DataFrame, mask: pd.Series) -> pd.Series:
    return flagged.loc[mask, "existing_QC_status"].value_counts(dropna=False)


def source_record_ids_for_groups(rg: pd.DataFrame, group_ids: set) -> str:
    """Concatenate the (already comma-joined) source_record_ids strings for
    every replicate_group_id in group_ids, flattened into a single
    comma-joined list. Approach: pull each group's source_record_ids string
    from replicate_group_summary.csv (itself comma-joined per group),
    split on comma, then join every individual record id across all
    selected groups with commas (deduplication is not applied since the
    same source record should not legitimately appear in more than one
    replicate group, but no assumption is made either way - flattening is
    a simple concatenation)."""
    sub = rg[rg["replicate_group_id"].isin(group_ids)]
    all_ids: list[str] = []
    for val in sub["source_record_ids"].fillna(""):
        if val:
            all_ids.extend([x.strip() for x in val.split(",") if x.strip()])
    return ",".join(all_ids)


def main() -> None:
    flagged = pd.read_csv(FLAGGED_PATH)
    rg = pd.read_csv(RG_SUMMARY_PATH)
    ap_queue = pd.read_csv(AP_QUEUE_PATH)
    dim_queue = pd.read_csv(DIM_QUEUE_PATH)
    packets = pd.read_csv(PACKETS_PATH)

    verify_inputs(flagged, rg, ap_queue, dim_queue, packets)

    print(f"Overall baseline flag rate: {EXPECTED_FLAGGED_ROWS}/{EXPECTED_TOTAL_ROWS} = "
          f"{BASELINE_RATE_PERCENT:.4f}%\n")

    # -------------------------------------------------------------------
    # Candidate targets, chosen per the task's stated criteria:
    #  - number of flagged groups represented
    #  - flag rate / enrichment vs baseline
    #  - flag category concentration
    #  - mixed / non-pass existing_QC_status presence
    #  - known high-interest analysis/parameter per STEP9_FINDINGS.md
    #  - avoiding redundant top-level targets (an analysis_type x parameter
    #    target already ~100% contained within an already-selected
    #    experiment-level target is treated as a sub-focus, not a separate
    #    top-level row)
    #
    # Exploration performed prior to finalizing this list (not re-shown
    # here) confirmed:
    #  - All of xrf/rb, xrf/cu, xrf/sr, xrf/u, xrf/k, xrf/mn, xrf/zn,
    #    xrf/mo, xrf/ba, xrf/ca's flagged groups are 100% contained within
    #    experiment_id=47 -> these are treated as sub-focuses of the
    #    experiment_id=47 priority, not separate top-level rows.
    #  - proximate/ash, proximate/volatile solids, proximate/total solids,
    #    compositional/xylan, and compositional/xylose have ZERO overlap
    #    with experiment_id=47 or 43's flagged groups (and, being distinct
    #    parameters, have zero overlap with each other by construction,
    #    since one replicate_group_id belongs to exactly one
    #    analysis_type x parameter combination) -> each is a
    #    non-redundant, distinct top-level target.
    #  - mixed existing_QC_status groups (fail,pass / pass,provisional,
    #    11 groups total) are mostly already contained within the
    #    experiment_id and analysis_type x parameter targets below; they
    #    are too few (11 of 427) to justify a standalone top-level target
    #    per the task's instruction to use existing_QC_status as
    #    supporting context only, and are instead called out in the "why
    #    review" text of the targets that already contain them.
    # -------------------------------------------------------------------

    candidates_spec = [
        ("experiment", 47.0),
        ("experiment", 43.0),
        ("ap", ("proximate", "ash")),
        ("ap", ("proximate", "volatile solids")),
        ("ap", ("compositional", "xylan")),
        ("ap", ("proximate", "total solids")),
        ("ap", ("compositional", "xylose")),
    ]

    targets = []
    for kind, spec in candidates_spec:
        if kind == "experiment":
            targets.append(build_experiment_target(flagged, rg, spec))
        else:
            at, param = spec
            targets.append(build_analysis_parameter_target(flagged, rg, at, param))

    # -------------------------------------------------------------------
    # Why-review narrative construction (supporting context only: provider,
    # resource_type, sample_preparation_method, flag_category,
    # existing_QC_status).
    # -------------------------------------------------------------------

    exp47_subgroups = top_subgroups_within_experiment(flagged, 47.0, top_n=10)
    exp43_subgroups = top_subgroups_within_experiment(flagged, 43.0, top_n=10)

    exp47_mask = flagged["experiment_id"] == 47.0
    exp43_mask = flagged["experiment_id"] == 43.0
    ash_mask = (flagged["analysis_type"] == "proximate") & (flagged["parameter"] == "ash")
    vs_mask = (flagged["analysis_type"] == "proximate") & (flagged["parameter"] == "volatile solids")
    ts_mask = (flagged["analysis_type"] == "proximate") & (flagged["parameter"] == "total solids")
    xylan_mask = (flagged["analysis_type"] == "compositional") & (flagged["parameter"] == "xylan")
    xylose_mask = (flagged["analysis_type"] == "compositional") & (flagged["parameter"] == "xylose")

    exp47_fc = flag_category_breakdown(flagged, exp47_mask)
    exp43_fc = flag_category_breakdown(flagged, exp43_mask)
    ash_fc = flag_category_breakdown(flagged, ash_mask)
    vs_fc = flag_category_breakdown(flagged, vs_mask)
    ts_fc = flag_category_breakdown(flagged, ts_mask)
    xylan_fc = flag_category_breakdown(flagged, xylan_mask)
    xylose_fc = flag_category_breakdown(flagged, xylose_mask)

    exp47_qc = existing_qc_status_breakdown(flagged, exp47_mask)
    exp43_qc = existing_qc_status_breakdown(flagged, exp43_mask)
    ash_qc = existing_qc_status_breakdown(flagged, ash_mask)

    exp47_sub_str = ", ".join(
        f"{row.analysis_type}/{row.parameter} (N={row.n_flagged_groups})"
        for row in exp47_subgroups.itertuples()
    )
    exp43_sub_str = ", ".join(
        f"{row.analysis_type}/{row.parameter} (N={row.n_flagged_groups})"
        for row in exp43_subgroups.itertuples()
    )

    why_review = {
        "experiment_id = 47": (
            f"Largest single review target: 254 of 427 flagged groups (59.5%), "
            f"flag rate 27.5% vs 15.7% baseline (1.74x enrichment) - the most elevated "
            f"large-denominator target in the dataset (per STEP9_FINDINGS.md Sec 2). "
            f"Almost entirely `xrf` trace-element parameters: {exp47_sub_str}. "
            f"Flag-category mix: {exp47_fc.to_dict()} (Dixon_only dominant, consistent with "
            f"isolated-extreme-value behavior). Provider `rigging` contributes 41 of the "
            f"254 groups here (supporting context, not a separate top-level target - see "
            f"STEP9_FINDINGS.md's rigging enrichment note). existing_QC_status is 252 "
            f"pass / 2 fail,pass (mixed-status) within this target. Per Step 9's documented "
            f"limitation, experiment_id is a convenience review-batching key here, not a "
            f"validated common-root-cause unit."
        ),
        "experiment_id = 43": (
            f"Second-largest experiment-level target: 61 of 427 flagged groups (14.3%), "
            f"flag rate 18.2% vs 15.7% baseline (1.15x enrichment). Entirely `icp` "
            f"trace-element parameters: {exp43_sub_str}. Flag-category mix: "
            f"{exp43_fc.to_dict()} (RSD_only dominant, 53/61=87%, unlike experiment 47's "
            f"Dixon-dominant pattern - a distinct flag-category signature worth noting "
            f"for reviewers). existing_QC_status includes 3 mixed-status (`fail,pass`) "
            f"groups, all `icp/na`, within this target (supporting context per Step 9's "
            f"guardrail against over-interpreting small mixed-status denominators). Same "
            f"experiment_id-is-a-convenience-key limitation applies as for experiment 47."
        ),
        "proximate x ash": (
            f"Largest analysis_type x parameter target with zero overlap with the "
            f"experiment-level targets above (spread across many small experiments, "
            f"12/44 flagged from experiment_id=6 alone per exploratory review). Flag rate "
            f"18.3% vs 15.7% baseline (1.16x enrichment). Flag-category mix: "
            f"{ash_fc.to_dict()} (Dixon_only dominant, 14/21). Includes 1 `fail` and 2 "
            f"mixed-status (`fail,pass`, `pass,provisional`) existing_QC_status groups - "
            f"a useful cross-check candidate per STEP9_FINDINGS.md Sec 2's note on "
            f"mixed-status overlap. `ash` is one of the four `proximate` mass-balance "
            f"parameters (with volatile solids, total solids, moisture) that together "
            f"appear across many small experiments rather than concentrating in one."
        ),
        "proximate x volatile solids": (
            f"Second-largest `proximate` parameter target, zero overlap with "
            f"experiment_id=47/43 or with `proximate x ash`. Flag rate 12.2% vs 15.7% "
            f"baseline (0.77x enrichment - below baseline; included here for its "
            f"absolute count and its shared-family relationship to `ash`, not because "
            f"its own rate is unusually elevated). Flag-category mix: {vs_fc.to_dict()}."
        ),
        "compositional x xylan": (
            f"Largest `compositional` parameter target, zero overlap with "
            f"experiment_id=47/43. Flag rate 19.1% vs 15.7% baseline (1.21x enrichment). "
            f"Flag-category mix: {xylan_fc.to_dict()}. Spread across 9 distinct "
            f"experiment_ids (27, 30, 31, 32, 35, 36, 37, 38, 40) - a genuinely different "
            f"concentration pattern than the two experiment-level targets above."
        ),
        "proximate x total solids": (
            f"Third `proximate` parameter target, zero overlap with experiment_id=47/43 "
            f"or with `ash`/`volatile solids`. Flag rate 11.3% vs 15.7% baseline (0.72x "
            f"enrichment - below baseline; included for absolute count and shared-family "
            f"relationship to `ash`). Flag-category mix: {ts_fc.to_dict()}."
        ),
        "compositional x xylose": (
            f"Second `compositional` parameter target, zero overlap with "
            f"experiment_id=47/43 or with `xylan` (distinct parameter, so distinct "
            f"replicate groups by construction). Flag rate 16.7% vs 15.7% baseline "
            f"(1.06x enrichment, close to baseline). Flag-category mix: "
            f"{xylose_fc.to_dict()}. Often measured alongside `xylan` in the same "
            f"compositional analysis batch, so grouped adjacently in this priority list "
            f"for reviewer convenience even though it is a separate top-level target."
        ),
    }

    # -------------------------------------------------------------------
    # Build the priority rows in order, computing TRUE set-union cumulative
    # coverage row by row (not a naive running sum).
    # -------------------------------------------------------------------

    rows = []
    union_so_far: set = set()
    for i, t in enumerate(targets, start=1):
        union_so_far = union_so_far | t["group_ids"]
        cumulative_pct = len(union_so_far) / EXPECTED_FLAGGED_ROWS * 100.0

        group_ids_sorted = sorted(t["group_ids"])
        source_record_ids_list = source_record_ids_for_groups(rg, t["group_ids"])

        rows.append({
            "Priority": i,
            "Review target": t["review_target"],
            "Grain": "experiment_id" if t["grain"] == "experiment_id" else "analysis_type x parameter",
            "grain": t["grain"],
            "Flagged groups in target": t["n_flagged"],
            "Flag rate": f"{t['flag_rate']:.1f}%",
            "Enrichment vs baseline": f"{t['enrichment']:.2f}x",
            "Cumulative % of 427 flagged groups addressed": f"{cumulative_pct:.1f}%",
            "Why review / suggested focus": why_review[t["review_target"]],
            "replicate_group_id_list": ",".join(str(x) for x in group_ids_sorted),
            "source_record_ids_list": source_record_ids_list,
        })

    out_df = pd.DataFrame(rows)

    print("=== FINAL PRIORITY TABLE ===")
    print_cols = [
        "Priority", "Review target", "Grain", "Flagged groups in target",
        "Flag rate", "Enrichment vs baseline",
        "Cumulative % of 427 flagged groups addressed",
    ]
    print(out_df[print_cols].to_string(index=False))
    print()

    final_union_pct = out_df["Cumulative % of 427 flagged groups addressed"].iloc[-1]
    print(f"Final cumulative unique coverage: {final_union_pct}")

    # Reorder / finalize output columns per spec.
    output_columns = [
        "Priority", "Review target", "Grain", "Flagged groups in target",
        "Flag rate", "Enrichment vs baseline",
        "Cumulative % of 427 flagged groups addressed",
        "Why review / suggested focus",
        "grain",
        "replicate_group_id_list",
        "source_record_ids_list",
    ]
    out_df = out_df[output_columns]
    out_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nWrote {OUTPUT_PATH} ({len(out_df)} rows)")

    # Print sub-focus tables for STEP10_FINDINGS.md authoring.
    print("\n=== Experiment 47 top sub-focus analysis_type x parameter ===")
    print(exp47_subgroups.to_string(index=False))
    print("\n=== Experiment 43 top sub-focus analysis_type x parameter ===")
    print(exp43_subgroups.to_string(index=False))


if __name__ == "__main__":
    main()
