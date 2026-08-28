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
reviewing the actual 74-row table, and renders 2 plots per example (mean vs
SD, mean vs RSD) = 8 PNGs total. See the completion report for the full
selection reasoning; short version reproduced here for anyone reading only
this file:

  1. approx_constant_absolute_SD -> xrf / sr
     ZERO of the 74 combinations were actually classified into this
     category by 06a's heuristic (R^2 >= 0.3 AND |slope| <= 0.3). Per this
     task's instructions, we relax the R^2 threshold to >= 0.2 for
     BROWSING PURPOSES ONLY (not to relabel anything) and pick the
     candidate with the smallest |loglog_slope| among those. That is
     xrf/sr: loglog_slope=0.294, loglog_r_squared=0.258, n=39 usable
     log-log points. Its ACTUAL precision_model_category in the CSV is
     "unclear" (R^2 of 0.258 is just under the 0.3 clear-fit bar). This
     pick is explicitly NON-QUALIFYING and is labeled as such in its plot
     titles and in the printed validation summary below — it is presented
     as "closest available candidate", never as a clean positive example.

  2. approx_constant_relative_RSD -> icp / ca
     Highest loglog_r_squared (0.886) among the 10 rows actually
     classified as approx_constant_relative_RSD, with a decent n=30
     usable log-log points (not the smallest-n option in the category).

  3. concentration_dependent_mixed -> xrf / zn
     Among the 13 rows in this category, slope=0.529 sits cleanly in the
     0.4-0.6 "real relationship but not close to 0 or 1" band requested by
     this task, with decent R^2=0.438 and the largest n (41) of any
     candidate in that slope band.

  4. unclear -> proximate / volatile solids
     Largest n_points_usable_for_loglog (115) of any row in the ENTIRE
     74-row table, with essentially no log-log fit (R^2=0.006, slope close
     to 0 by coincidence but not a good fit) -- a genuinely "many points,
     no clean relationship" control case, not "unclear due to low n".

This step does NOT recompute or re-derive any precision-model statistics.
Every category/slope/R^2 value shown comes as-is from
`precision_model_diagnostics.csv`; this script only visualizes the
underlying `replicate_group_summary.csv` rows for the 4 selected
combinations and annotates each plot with that pre-computed classification
for visual sanity-checking.

Guardrails honored:
- Does NOT modify replicate_group_summary.csv, precision_model_diagnostics.csv,
  method_parameter_summary.csv, or any earlier script.
- Does NOT introduce new statistical claims -- titles only restate values
  already present in precision_model_diagnostics.csv.
- NaN standard_deviation / RSD_percent points (singleton replicate groups)
  are never silently dropped -- their count is explicitly reported in each
  plot's caption and in the printed validation summary.
- resource_type color-coding uses a legend only when there are <=15
  distinct values present in the plotted subset; above that cutoff we
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
# given plot's plotted (non-NaN) subset, per-category coloring becomes
# visually unreadable (too many legend entries / indistinguishable colors),
# so we fall back to a single, uncolored marker style and note this in the
# subtitle instead of forcing an unreadable 16+-color legend.
MAX_DISTINCT_RESOURCE_TYPES_FOR_LEGEND = 15

# ---------------------------------------------------------------------------
# The 4 selected combinations (see module docstring for full reasoning).
# ---------------------------------------------------------------------------
SELECTED_COMBINATIONS = [
    {
        "analysis_type": "xrf",
        "parameter": "sr",
        "role_label": "approx_constant_absolute_SD -- CLOSEST AVAILABLE, NON-QUALIFYING",
        "non_qualifying_note": (
            "NON-QUALIFYING PICK: this combination's actual precision_model_category "
            "is 'unclear', not 'approx_constant_absolute_SD'. Zero of the 74 "
            "combinations met the real categorization bar (R2>=0.3 & |slope|<=0.3) "
            "for approx_constant_absolute_SD. This is the closest available "
            "candidate (smallest |slope| among rows with R2>=0.2, threshold relaxed "
            "for browsing only) -- it does NOT meet the R2>=0.3 & |slope|<=0.3 "
            "threshold for that category."
        ),
    },
    {
        "analysis_type": "icp",
        "parameter": "ca",
        "role_label": "approx_constant_relative_RSD -- best of 10 (highest R2)",
        "non_qualifying_note": None,
    },
    {
        "analysis_type": "xrf",
        "parameter": "zn",
        "role_label": "concentration_dependent_mixed -- representative (slope in 0.4-0.6 band)",
        "non_qualifying_note": None,
    },
    {
        "analysis_type": "proximate",
        "parameter": "volatile solids",
        "role_label": "unclear -- representative (largest n in table, genuinely no fit)",
        "non_qualifying_note": None,
    },
]


def sanitize_for_filename(value: str) -> str:
    """Replace filesystem-unsafe characters (spaces, slashes, etc.) with
    underscores so parameter names like "volatile solids" or "lignin+"
    become safe path components.
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


def build_title_lines(
    analysis_type: str,
    parameter: str,
    metric_label: str,
    diag_row: pd.Series,
    non_qualifying_note: str | None,
    n_plotted: int,
    n_excluded_nan: int,
    n_distinct_resource_types: int,
    color_coded: bool,
) -> str:
    """Build the full multi-line title/caption text for one plot, per task
    Step 2/3/4/5 requirements: states category/slope/R^2, flags
    non-qualifying picks, notes NaN-excluded count, and notes
    resource_type cardinality / color-coding decision.
    """
    category = diag_row["precision_model_category"]
    slope_str = format_stat(diag_row["loglog_slope"])
    r2_str = format_stat(diag_row["loglog_r_squared"])

    lines = [
        f"{analysis_type} / {parameter} -- mean vs {metric_label}",
        (
            f"Comprehensive screen classified this as {category} "
            f"(slope={slope_str}, R\u00b2={r2_str}) -- visual check."
        ),
    ]

    if non_qualifying_note:
        lines.append(non_qualifying_note)

    lines.append(
        f"{n_plotted} points plotted; {n_excluded_nan} singleton/NaN-{metric_label} "
        "group(s) excluded from this view."
    )

    if color_coded:
        lines.append(
            f"Points colored by resource_type ({n_distinct_resource_types} distinct values, legend shown)."
        )
    else:
        lines.append(
            f"resource_type NOT color-coded: {n_distinct_resource_types} distinct values "
            f"exceeds the {MAX_DISTINCT_RESOURCE_TYPES_FOR_LEGEND}-category legend cutoff "
            "-- single-color fallback used."
        )

    return "\n".join(lines)


def make_scatter_plot(
    combo_df: pd.DataFrame,
    metric_col: str,
    metric_label: str,
    analysis_type: str,
    parameter: str,
    diag_row: pd.Series,
    non_qualifying_note: str | None,
    output_path: str,
) -> dict:
    """Build one scatter plot (mean on x-axis, `metric_col` on y-axis) for
    one selected combination, color-coded by resource_type (with legend
    fallback per MAX_DISTINCT_RESOURCE_TYPES_FOR_LEGEND), and save it to
    `output_path`. Returns a small dict of validation-summary stats.
    """
    # --- Explicit NaN handling (Step 5 / guardrail: never silently drop) ---
    # mean is essentially always defined per replicate group; the metric
    # column (SD or RSD_percent) is undefined for singleton replicate
    # groups (n_replicates == 1) or, for RSD, near-zero-mean groups.
    is_metric_nan = combo_df[metric_col].isna()
    n_excluded_nan = int(is_metric_nan.sum())
    plot_df = combo_df.loc[~is_metric_nan].copy()
    n_plotted = len(plot_df)

    # --- resource_type color-coding decision ---
    resource_types = plot_df["resource_type"].fillna("(missing resource_type)")
    distinct_resource_types = sorted(resource_types.unique().tolist())
    n_distinct = len(distinct_resource_types)
    color_coded = n_distinct <= MAX_DISTINCT_RESOURCE_TYPES_FOR_LEGEND

    fig, ax = plt.subplots(figsize=(9, 7))

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
            fontsize=7,
            title_fontsize=8,
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

    ax.set_xlabel("sample mean")
    ax.set_ylabel(metric_label)

    title_text = build_title_lines(
        analysis_type=analysis_type,
        parameter=parameter,
        metric_label=metric_label,
        diag_row=diag_row,
        non_qualifying_note=non_qualifying_note,
        n_plotted=n_plotted,
        n_excluded_nan=n_excluded_nan,
        n_distinct_resource_types=n_distinct,
        color_coded=color_coded,
    )
    ax.set_title(title_text, fontsize=9, loc="left", wrap=True)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    return {
        "output_path": output_path,
        "n_plotted": n_plotted,
        "n_excluded_nan": n_excluded_nan,
        "n_distinct_resource_types": n_distinct,
        "color_coded": color_coded,
    }


def main() -> None:
    os.makedirs(PLOTS_DIR, exist_ok=True)

    replicate_df, diagnostics_df = load_inputs()

    validation_summary = []

    for combo in SELECTED_COMBINATIONS:
        analysis_type = combo["analysis_type"]
        parameter = combo["parameter"]
        role_label = combo["role_label"]
        non_qualifying_note = combo["non_qualifying_note"]

        diag_row = get_diagnostics_row(diagnostics_df, analysis_type, parameter)

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

        sd_path = os.path.join(
            PLOTS_DIR, f"{safe_analysis_type}_{safe_parameter}_mean_vs_SD.png"
        )
        rsd_path = os.path.join(
            PLOTS_DIR, f"{safe_analysis_type}_{safe_parameter}_mean_vs_RSD.png"
        )

        sd_stats = make_scatter_plot(
            combo_df=combo_df,
            metric_col="standard_deviation",
            metric_label="replicate SD",
            analysis_type=analysis_type,
            parameter=parameter,
            diag_row=diag_row,
            non_qualifying_note=non_qualifying_note,
            output_path=sd_path,
        )
        rsd_stats = make_scatter_plot(
            combo_df=combo_df,
            metric_col="RSD_percent",
            metric_label="replicate RSD (%)",
            analysis_type=analysis_type,
            parameter=parameter,
            diag_row=diag_row,
            non_qualifying_note=non_qualifying_note,
            output_path=rsd_path,
        )

        validation_summary.append(
            {
                "analysis_type": analysis_type,
                "parameter": parameter,
                "role_label": role_label,
                "n_replicate_groups_total": len(combo_df),
                "sd_plot": sd_stats,
                "rsd_plot": rsd_stats,
            }
        )

    # --- Validation summary printout ---
    print("\n" + "=" * 78)
    print("VALIDATION SUMMARY -- 07_selected_diagnostics.py")
    print("=" * 78)
    n_pngs = 0
    for entry in validation_summary:
        print(f"\n{entry['analysis_type']} / {entry['parameter']}  ({entry['role_label']})")
        print(f"  total replicate groups: {entry['n_replicate_groups_total']}")
        for plot_key, human_label in (("sd_plot", "mean vs SD"), ("rsd_plot", "mean vs RSD")):
            stats = entry[plot_key]
            n_pngs += 1
            print(
                f"  [{human_label}] plotted={stats['n_plotted']}, "
                f"NaN-excluded={stats['n_excluded_nan']}, "
                f"distinct resource_type={stats['n_distinct_resource_types']}, "
                f"color-coded={stats['color_coded']} -> {stats['output_path']}"
            )
    print(f"\nTotal PNG files written: {n_pngs} (expected 8 = 4 combinations x 2 plot types)")
    print("=" * 78)


if __name__ == "__main__":
    main()
