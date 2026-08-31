"""
07_selected_diagnostics.py — selected diagnostic plots, chosen AFTER
reviewing the comprehensive precision-model screen
(`06a_build_precision_model_diagnostics.py` -> `precision_model_diagnostics.csv`,
74 rows = 74 distinct `analysis_type x parameter` combinations).

WHY THIS SCRIPT EXISTS (design rationale):
The original handoff's Step 6 pre-selected a fixed list of 5-10 combinations
before the comprehensive 74-row screen existed. This script instead selects
a SMALL, DELIBERATE set of 4 representative examples (one per non-trivial
precision_model_category: approx_constant_absolute_SD,
approx_constant_relative_RSD, concentration_dependent_mixed, unclear) by
reviewing the actual 74-row table, and renders ONE combined figure per
example (mean vs SD on the left, mean vs RSD on the right, side by side) =
4 PNGs total. Selections below reflect the CURRENT `classify_precision_model()`
logic (Spearman-corroborated stability categories, no blanket R^2 gate) and
the corrected `RSD_percent` computation (abs(mean) denominator) — see
`STEP6_FINDINGS.md` for the full history of that redesign. Short version of
the current selection reasoning, reproduced here for anyone reading only
this file:

  1. approx_constant_absolute_SD -> proximate / volatile solids
     One of 5 combinations now genuinely classified into this category
     (previously 0, before the classifier redesign). Largest
     n_points_usable_for_loglog (115) of any row in the entire 74-row
     table, with loglog_slope=-0.091 and loglog_r_squared=0.006 (log-log
     fit itself is negligible, consistent with "no real trend to fit") and
     spearman_mean_vs_SD=-0.289 (small magnitude, corroborating "no
     concentration-dependence" independent of the noisy log-log fit) — a
     well-populated, genuine positive example, not a placeholder.

  2. approx_constant_relative_RSD -> icp / ca
     Highest loglog_r_squared (0.886) among the 13 rows classified as
     approx_constant_relative_RSD, with a decent n=30 usable log-log
     points (not the smallest-n option in the category). Unchanged by the
     classifier redesign.

  3. concentration_dependent_mixed -> xrf / zn
     Among the 20 rows in this category, slope=0.529 sits cleanly in the
     0.4-0.6 "real relationship but not close to 0 or 1" band, with decent
     R^2=0.438 and the largest n (41) of any candidate in that slope band.
     Unchanged by the classifier redesign.

  4. unclear -> proximate / total solids
     Largest n_points_usable_for_loglog (115) of any row remaining in the
     (now much smaller, 10-row) unclear category, with loglog_r_squared
     =0.085 (weak log-log fit) and loglog_slope=-0.696 (not close to 0 or
     1) — a genuinely ambiguous case, not a low-n artifact. (The prior
     pick, proximate/volatile solids, reclassified into
     approx_constant_absolute_SD under the redesigned classifier and now
     serves that category instead — see #1 above.)

This step does NOT recompute or re-derive any precision-model statistics.
Every category/slope/R^2 value shown comes as-is from
`precision_model_diagnostics.csv`; this script only visualizes the
underlying `replicate_group_summary.csv` rows for the 4 selected
combinations and annotates each figure with that pre-computed
classification for visual sanity-checking.

OUTPUT FORMAT: one PNG per selected combination (not one per metric). Each
PNG contains TWO side-by-side subplots (mean vs replicate SD on the left,
mean vs replicate RSD on the right) so both views can be visually compared
directly. The PROPOSED `precision_model_category` is displayed as the
most visually prominent line of the figure's top-level title (large,
bold) AND is embedded in the output filename (e.g.
`proximate_volatile_solids_approx_constant_absolute_SD.png`), so the
proposed categorization is immediately visible both when looking at the
image and when browsing the output directory. Every plotted point is also
checked against simple high-leverage thresholds (RSD_percent > 20, or
standard_deviation > 2x that combination's own median SD); qualifying
points are annotated directly on the plot with their `replicate_group_id`
so a reviewer can go straight from "that point looks high" to the exact
replicate group / sample / resource / experiment to pull up in
`replicate_group_summary.csv`.

Guardrails honored:
- Does NOT modify replicate_group_summary.csv, precision_model_diagnostics.csv,
  method_parameter_summary.csv, or any earlier script.
- Does NOT introduce new statistical claims -- titles only restate values
  already present in precision_model_diagnostics.csv; high-leverage-point
  labeling is a visual aid only (replicate_group_id), not a new flag/status
  column written anywhere.
- NaN standard_deviation / RSD_percent points (singleton replicate groups)
  are never silently dropped -- their count is explicitly reported in each
  subplot's caption and in the printed validation summary.
- resource_type color-coding uses a legend only when there are <=15
  distinct values present in the plotted subset (evaluated independently
  per subplot, since the SD-defined and RSD-defined subsets of a
  combination's replicate groups can differ); above that cutoff we
  document the fallback to a single, uncolored marker style.

Usage:
    pixi run python audit/outliers/biocirv_outlier_assessment/07_selected_diagnostics.py
"""

from __future__ import annotations

import os
import re
import sys

import numpy as np
import pandas as pd

# Make analysis_config importable regardless of CWD.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis_config  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

REPLICATE_SUMMARY_PATH = os.path.join(analysis_config.OUTPUT_DIR, "replicate_group_summary.csv")
DIAGNOSTICS_PATH = os.path.join(analysis_config.OUTPUT_DIR, "precision_model_diagnostics.csv")
PLOTS_DIR = analysis_config.PLOTS_SELECTED_DIR

# ---------------------------------------------------------------------------
# Plotting backend -- headless-safe.
# ---------------------------------------------------------------------------
import matplotlib

matplotlib.use("Agg")
import matplotlib.cm as cm
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Color-coding cutoff (documented per task Step 4 requirement).
# ---------------------------------------------------------------------------
# If more than this many distinct resource_type values are present in a
# given subplot's plotted (non-NaN) subset, per-category coloring becomes
# visually unreadable (too many legend entries / indistinguishable colors),
# so we fall back to a single, uncolored marker style and note this in the
# subplot's caption instead of forcing an unreadable 16+-color legend.
MAX_DISTINCT_RESOURCE_TYPES_FOR_LEGEND = 15

# ---------------------------------------------------------------------------
# The 4 selected combinations (see module docstring for full reasoning).
# ---------------------------------------------------------------------------
SELECTED_COMBINATIONS = [
    {
        "analysis_type": "proximate",
        "parameter": "volatile solids",
        "role_label": "approx_constant_absolute_SD -- best of 5 (largest n, genuinely qualifying)",
    },
    {
        "analysis_type": "icp",
        "parameter": "ca",
        "role_label": "approx_constant_relative_RSD -- best of 13 (highest R2)",
    },
    {
        "analysis_type": "xrf",
        "parameter": "zn",
        "role_label": "concentration_dependent_mixed -- representative (slope in 0.4-0.6 band)",
    },
    {
        "analysis_type": "proximate",
        "parameter": "total solids",
        "role_label": "unclear -- representative (largest n in category, genuinely no fit)",
    },
]


def sanitize_for_filename(value: str) -> str:
    """Replace filesystem-unsafe characters (spaces, slashes, etc.) with
    underscores so parameter names like "volatile solids" or category
    labels like "approx_constant_absolute_SD" become safe path components.
    """
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip())


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the two upstream CSVs as-is. No recomputation, no mutation."""
    if not os.path.exists(REPLICATE_SUMMARY_PATH):
        raise FileNotFoundError(f"{REPLICATE_SUMMARY_PATH} not found.")
    if not os.path.exists(DIAGNOSTICS_PATH):
        raise FileNotFoundError(
            f"{DIAGNOSTICS_PATH} not found -- run "
            "06a_build_precision_model_diagnostics.py first."
        )
    replicate_df = pd.read_csv(REPLICATE_SUMMARY_PATH)
    diagnostics_df = pd.read_csv(DIAGNOSTICS_PATH)
    print(f"Loaded {len(replicate_df)} rows from {REPLICATE_SUMMARY_PATH}")
    print(f"Loaded {len(diagnostics_df)} rows from {DIAGNOSTICS_PATH}")
    return replicate_df, diagnostics_df


def get_diagnostics_row(diagnostics_df: pd.DataFrame, analysis_type: str, parameter: str) -> pd.Series:
    """Look up the single precision_model_diagnostics.csv row for a given
    analysis_type x parameter combination. Raises if not exactly 1 match.
    """
    match = diagnostics_df[
        (diagnostics_df["analysis_type"] == analysis_type)
        & (diagnostics_df["parameter"] == parameter)
    ]
    if len(match) != 1:
        raise ValueError(
            f"Expected exactly 1 precision_model_diagnostics.csv row for "
            f"analysis_type={analysis_type!r}, parameter={parameter!r}; found {len(match)}."
        )
    return match.iloc[0]


def format_stat(value: float, decimals: int = 3) -> str:
    """Format a numeric diagnostic value for display, NaN-safe."""
    if pd.isna(value):
        return "n/a"
    return f"{value:.{decimals}f}"


def build_subplot_caption(
    metric_label: str,
    n_plotted: int,
    n_excluded_nan: int,
    n_distinct_resource_types: int,
    color_coded: bool,
    n_high_leverage: int,
) -> str:
    """Build the per-subplot caption text: NaN-excluded count,
    resource_type color-coding decision, and high-leverage-point label
    count. The category/slope/R^2 line lives in the figure-level suptitle
    instead (see build_suptitle), since it is shared by both subplots.
    """
    lines = [
        f"mean vs {metric_label}",
        (
            f"{n_plotted} points plotted; {n_excluded_nan} singleton/NaN-{metric_label} "
            "group(s) excluded."
        ),
    ]
    if color_coded:
        lines.append(
            f"Colored by resource_type ({n_distinct_resource_types} distinct values, legend shown)."
        )
    else:
        lines.append(
            f"resource_type NOT color-coded: {n_distinct_resource_types} distinct values "
            f"exceeds the {MAX_DISTINCT_RESOURCE_TYPES_FOR_LEGEND}-category legend cutoff "
            "-- single-color fallback used."
        )
    lines.append(
        f"{n_high_leverage} high-leverage point(s) labeled with replicate_group_id "
        f"(RSD>{HIGH_LEVERAGE_RSD_THRESHOLD}% or SD>{HIGH_LEVERAGE_SD_MEDIAN_MULTIPLIER}x median SD)."
    )
    return "\n".join(lines)


def build_suptitle_lines(analysis_type: str, parameter: str, diag_row: pd.Series) -> tuple[str, str, str]:
    """Build the three figure-level title lines, returned separately so
    each can be rendered with its own font size/weight:
      1. combination name (small)
      2. "PROPOSED precision_model_category: {category}" (large, bold --
         the primary, most prominent line per task requirement)
      3. underlying slope/R^2 diagnostics + non-validated-cutoff caveat (small)
    """
    category = diag_row["precision_model_category"]
    slope_str = format_stat(diag_row["loglog_slope"])
    r2_str = format_stat(diag_row["loglog_r_squared"])
    line1 = f"{analysis_type} / {parameter}"
    line2 = f"PROPOSED precision_model_category: {category}"
    line3 = (
        f"(loglog_slope={slope_str}, loglog_r\u00b2={r2_str}) -- visual check, "
        "not a validated statistical cutoff"
    )
    return line1, line2, line3


# High-leverage-point labeling thresholds (per STEP6_FINDINGS.md future-work
# item, now implemented here): a point is annotated with its
# `replicate_group_id` when EITHER of these holds, so a reviewer can go
# directly from "that point looks high" to the exact replicate group /
# sample / resource / experiment to pull up, without cross-referencing
# replicate_group_summary.csv by eye.
HIGH_LEVERAGE_RSD_THRESHOLD = 20  # RSD_percent > 20
HIGH_LEVERAGE_SD_MEDIAN_MULTIPLIER = 2  # standard_deviation > 2 x per-combination median SD


def plot_one_subplot(
    ax: plt.Axes,
    combo_df: pd.DataFrame,
    metric_col: str,
    metric_label: str,
) -> dict:
    """Draw one mean-vs-metric scatter into the given Axes, color-coded by
    resource_type (with legend fallback per
    MAX_DISTINCT_RESOURCE_TYPES_FOR_LEGEND). High-leverage points (per
    HIGH_LEVERAGE_* thresholds, evaluated over the FULL combo_df so the
    per-combination median SD is not biased by this subplot's own NaN
    filtering) are annotated with their `replicate_group_id`. Returns a
    small dict of validation-summary stats for this subplot.
    """
    # --- Explicit NaN handling (guardrail: never silently drop) ---
    # mean is essentially always defined per replicate group; the metric
    # column (SD or RSD_percent) is undefined for singleton replicate
    # groups (n_replicates == 1) or, for RSD, near-zero-mean groups.
    is_metric_nan = combo_df[metric_col].isna()
    n_excluded_nan = int(is_metric_nan.sum())
    plot_df = combo_df.loc[~is_metric_nan].copy()
    n_plotted = len(plot_df)

    # --- High-leverage point flags (computed on the full combo_df's
    # standard_deviation, i.e. this combination's own SD distribution
    # across ALL its replicate groups, not just this subplot's plotted
    # subset -- .median() skips NaN automatically). ---
    median_sd = combo_df["standard_deviation"].median()
    is_high_rsd = plot_df["RSD_percent"] > HIGH_LEVERAGE_RSD_THRESHOLD
    is_high_sd = (
        plot_df["standard_deviation"] > HIGH_LEVERAGE_SD_MEDIAN_MULTIPLIER * median_sd
        if pd.notna(median_sd)
        else pd.Series(False, index=plot_df.index)
    )
    is_high_leverage = (is_high_rsd.fillna(False)) | (is_high_sd.fillna(False))
    n_high_leverage = int(is_high_leverage.sum())

    # --- resource_type color-coding decision ---
    resource_types = plot_df["resource_type"].fillna("(missing resource_type)")
    distinct_resource_types = sorted(resource_types.unique().tolist())
    n_distinct = len(distinct_resource_types)
    color_coded = n_distinct <= MAX_DISTINCT_RESOURCE_TYPES_FOR_LEGEND

    if color_coded and n_distinct > 0:
        cmap = cm.get_cmap("tab20", max(n_distinct, 1))
        color_lookup = {rt: cmap(i) for i, rt in enumerate(distinct_resource_types)}
        for rt in distinct_resource_types:
            subset = plot_df[resource_types == rt]
            ax.scatter(
                subset["mean"],
                subset[metric_col],
                label=rt,
                color=color_lookup[rt],
                alpha=0.8,
                edgecolors="black",
                linewidths=0.3,
                s=45,
            )
        ax.legend(
            title="resource_type",
            fontsize=6.5,
            title_fontsize=7.5,
            loc="best",
            ncol=1 if n_distinct <= 8 else 2,
            framealpha=0.9,
        )
    else:
        ax.scatter(
            plot_df["mean"],
            plot_df[metric_col],
            color="#4c72b0",
            alpha=0.7,
            edgecolors="black",
            linewidths=0.3,
            s=45,
        )

    # --- Annotate high-leverage points with their replicate_group_id ---
    for _, row in plot_df.loc[is_high_leverage].iterrows():
        ax.annotate(
            str(int(row["replicate_group_id"])),
            (row["mean"], row[metric_col]),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=7,
            fontweight="bold",
            color="#c0392b",
        )

    ax.set_xlabel("sample mean")
    ax.set_ylabel(metric_label)

    caption = build_subplot_caption(
        metric_label=metric_label,
        n_plotted=n_plotted,
        n_excluded_nan=n_excluded_nan,
        n_distinct_resource_types=n_distinct,
        color_coded=color_coded,
        n_high_leverage=n_high_leverage,
    )
    ax.set_title(caption, fontsize=8, loc="left", wrap=True)

    return {
        "n_plotted": n_plotted,
        "n_excluded_nan": n_excluded_nan,
        "n_distinct_resource_types": n_distinct,
        "color_coded": color_coded,
        "n_high_leverage": n_high_leverage,
    }


def make_combined_plot(
    combo_df: pd.DataFrame,
    analysis_type: str,
    parameter: str,
    diag_row: pd.Series,
    output_path: str,
) -> dict:
    """Build ONE figure with two side-by-side subplots (mean vs SD on the
    left, mean vs RSD on the right) for one selected combination, and save
    it to `output_path`. Returns a dict of validation-summary stats for
    both subplots.
    """
    fig, (ax_sd, ax_rsd) = plt.subplots(1, 2, figsize=(16, 7.5))

    sd_stats = plot_one_subplot(ax_sd, combo_df, "standard_deviation", "replicate SD")
    rsd_stats = plot_one_subplot(ax_rsd, combo_df, "RSD_percent", "replicate RSD (%)")

    # Three-line figure title, each line rendered independently via
    # fig.text() so the "PROPOSED precision_model_category" line can be
    # made visually dominant (larger + bold) relative to the other two.
    line1, line2, line3 = build_suptitle_lines(analysis_type, parameter, diag_row)
    fig.text(0.5, 0.975, line1, ha="center", fontsize=11, fontweight="normal")
    fig.text(0.5, 0.945, line2, ha="center", fontsize=15, fontweight="bold")
    fig.text(0.5, 0.915, line3, ha="center", fontsize=9, fontweight="normal", style="italic")

    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    return {"output_path": output_path, "sd": sd_stats, "rsd": rsd_stats}


def main() -> None:
    os.makedirs(PLOTS_DIR, exist_ok=True)

    replicate_df, diagnostics_df = load_inputs()

    validation_summary = []

    for combo in SELECTED_COMBINATIONS:
        analysis_type = combo["analysis_type"]
        parameter = combo["parameter"]
        role_label = combo["role_label"]

        diag_row = get_diagnostics_row(diagnostics_df, analysis_type, parameter)
        category = diag_row["precision_model_category"]

        combo_df = replicate_df[
            (replicate_df["analysis_type"] == analysis_type)
            & (replicate_df["parameter"] == parameter)
        ].copy()

        if combo_df.empty:
            raise ValueError(
                f"No replicate_group_summary.csv rows found for "
                f"analysis_type={analysis_type!r}, parameter={parameter!r}."
            )

        safe_analysis_type = sanitize_for_filename(analysis_type)
        safe_parameter = sanitize_for_filename(parameter)
        safe_category = sanitize_for_filename(category)

        # Category is embedded directly in the filename (per task
        # requirement), so the proposed categorization is visible when
        # browsing the output directory without opening each image.
        output_path = os.path.join(
            PLOTS_DIR, f"{safe_analysis_type}_{safe_parameter}_{safe_category}.png"
        )

        combined_stats = make_combined_plot(
            combo_df=combo_df,
            analysis_type=analysis_type,
            parameter=parameter,
            diag_row=diag_row,
            output_path=output_path,
        )

        validation_summary.append(
            {
                "analysis_type": analysis_type,
                "parameter": parameter,
                "category": category,
                "role_label": role_label,
                "n_replicate_groups_total": len(combo_df),
                "combined_stats": combined_stats,
            }
        )

    # --- Validation summary printout ---
    print("\n" + "=" * 78)
    print("VALIDATION SUMMARY -- 07_selected_diagnostics.py")
    print("=" * 78)
    n_pngs = 0
    for entry in validation_summary:
        print(
            f"\n{entry['analysis_type']} / {entry['parameter']}  "
            f"({entry['role_label']})"
        )
        print(f"  total replicate groups: {entry['n_replicate_groups_total']}")
        stats = entry["combined_stats"]
        n_pngs += 1
        for side_key, human_label in (("sd", "mean vs SD"), ("rsd", "mean vs RSD")):
            side_stats = stats[side_key]
            print(
                f"  [{human_label}] plotted={side_stats['n_plotted']}, "
                f"NaN-excluded={side_stats['n_excluded_nan']}, "
                f"distinct resource_type={side_stats['n_distinct_resource_types']}, "
                f"color-coded={side_stats['color_coded']}, "
                f"high-leverage labeled={side_stats['n_high_leverage']}"
            )
        print(f"  -> {stats['output_path']}")
    print(f"\nTotal PNG files written: {n_pngs} (expected 4 = 4 combinations x 1 combined figure)")
    print("=" * 78)


if __name__ == "__main__":
    main()
