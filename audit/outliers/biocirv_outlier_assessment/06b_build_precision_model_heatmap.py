"""
06b_build_precision_model_heatmap.py — companion heatmap for the
comprehensive precision-model screen built by
`06a_build_precision_model_diagnostics.py`.

INTERPRETATION BOUNDARY (read before using this figure):
This heatmap visualizes the comprehensive precision-model screen
(`precision_model_diagnostics.csv`) across all `analysis_type x parameter`
combinations. `precision_model_category` labels are exploratory,
descriptive triage categories based on simple log-log slope/R^2
heuristics — they are NOT validated statistical models, NOT production QC
rules, and must NOT be used to automatically assign an
absolute-SD-vs-relative-RSD precision model to any parameter without human
review. Categories and correlation values are for identifying candidates
worth closer visual inspection (see the 8 detailed diagnostic plots in
`outputs/plots_selected/`), not for making final scientific determinations.

Purpose:
Load the already-computed `outputs/precision_model_diagnostics.csv` (built
by `06a_build_precision_model_diagnostics.py`, 74 rows = 74 distinct
`analysis_type x parameter` combinations) and render it as ONE compact,
whole-dataset heatmap image. This script performs NO statistical
recomputation whatsoever — every number/label shown is read as-is from the
CSV; this script only visualizes it.

Column treatment (see task spec):
- 6 numeric columns (n_replicate_groups, n_points_usable_for_loglog,
  spearman_mean_vs_SD, spearman_mean_vs_RSD, loglog_slope,
  loglog_r_squared) are each independently min-max normalized (NaN-safe,
  and correctly handling negative values since spearman/loglog_slope are
  NOT 0-based) PURELY to drive per-cell background color for
  relative-magnitude comparison WITHIN that column. The raw, non-normalized
  value is always what's printed in the cell.
- `precision_model_category` is a LABEL, not a magnitude, and is therefore
  rendered as a separate column with DISCRETE categorical coloring (one
  fixed, distinct color per category value) rather than a continuous
  gradient. Cells are annotated with a short abbreviation; a legend maps
  abbreviation -> full category name.
- NaN handling is explicit everywhere: NaN is excluded from each numeric
  column's min/max during normalization (never coerced to 0), and any NaN
  cell is rendered with a distinct gray background and a "—" placeholder
  instead of a number (never silently becomes 0 and never crashes
  normalization). Rows with `precision_model_category ==
  "insufficient_data"` naturally have NaN in the correlation/slope columns
  (too few usable replicate groups to compute them) — these render as
  blank/gray cells in this heatmap, consistent with
  `05_build_review_heatmap.py`'s pattern.

Guardrails honored:
- No recomputation of statistics — reads precision_model_diagnostics.csv
  as-is.
- `precision_model_category` uses discrete/categorical coloring, never a
  continuous gradient.
- No thresholds/cutoffs derived from this visualization are written back to
  analysis_config.py.
- Exactly ONE heatmap image.

Usage:
    pixi run python audit/outliers/biocirv_outlier_assessment/06b_build_precision_model_heatmap.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis_config  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(analysis_config.OUTPUT_DIR, "precision_model_diagnostics.csv")
OUTPUT_PATH = os.path.join(analysis_config.OUTPUT_DIR, "precision_model_heatmap.png")

EXPECTED_N_ROWS = 74

# ---------------------------------------------------------------------------
# Plotting backend selection — try seaborn first (see pixi.toml
# [feature.visualization] — matplotlib + seaborn are only installed in the
# `viz` pixi environment), fall back to plain matplotlib if unavailable.
# ---------------------------------------------------------------------------
try:
    import seaborn as sns  # noqa: F401

    HAVE_SEABORN = True
except ImportError:
    HAVE_SEABORN = False

import matplotlib

matplotlib.use("Agg")  # headless-safe backend for script execution
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Column configuration
# ---------------------------------------------------------------------------

# Numeric columns, each independently min-max normalized (NaN-safe) purely
# to drive relative-magnitude cell BACKGROUND COLOR. The raw value is always
# what's annotated in the cell — normalization NEVER touches the displayed
# number, only the color. Several of these (spearman_*, loglog_slope) are
# NOT 0-based (they range roughly -1..1 or can be negative), so min/max is
# computed directly from the data rather than assuming a 0-based range.
NUMERIC_COLUMNS = [
    "n_replicate_groups",
    "n_points_usable_for_loglog",
    "spearman_mean_vs_SD",
    "spearman_mean_vs_RSD",
    "loglog_slope",
    "loglog_r_squared",
]

# The categorical label column — rendered as its own column with discrete,
# fixed-per-category coloring (never a continuous gradient).
CATEGORY_COLUMN = "precision_model_category"

ALL_EXPECTED_COLUMNS = ["analysis_type", "parameter"] + NUMERIC_COLUMNS + [CATEGORY_COLUMN]

NAN_PLACEHOLDER = "\u2014"  # em dash — used for any missing/NaN numeric cell, never "0"

# Fixed category order, colors (visually distinct, tab10-derived), and
# short abbreviations for in-cell annotation (legend maps abbrev -> full
# name). Order and colors are fixed regardless of which categories are
# actually present in a given run's data (defensive against future data
# changes), per task spec's 5 named categories.
CATEGORY_ORDER = [
    "approx_constant_absolute_SD",
    "approx_constant_relative_RSD",
    "concentration_dependent_mixed",
    "unclear",
    "insufficient_data",
]

CATEGORY_COLORS = {
    "approx_constant_absolute_SD": "#1f77b4",  # tab10 blue
    "approx_constant_relative_RSD": "#2ca02c",  # tab10 green
    "concentration_dependent_mixed": "#ff7f0e",  # tab10 orange
    "unclear": "#9467bd",  # tab10 purple
    "insufficient_data": "#d62728",  # tab10 red
}

# Text color chosen per category background for contrast (all categorical
# cells use a fixed background, so a single legible text color per category
# can be hardcoded rather than computed dynamically).
CATEGORY_TEXT_COLORS = {
    "approx_constant_absolute_SD": "white",
    "approx_constant_relative_RSD": "white",
    "concentration_dependent_mixed": "black",
    "unclear": "white",
    "insufficient_data": "white",
}

CATEGORY_ABBREV = {
    "approx_constant_absolute_SD": "constSD",
    "approx_constant_relative_RSD": "constRSD",
    "concentration_dependent_mixed": "concMix",
    "unclear": "unclear",
    "insufficient_data": "insuff",
}

NAN_CATEGORY_COLOR = "#d9d9d9"  # distinct light gray, same convention as numeric NaN cells


def load_diagnostics() -> pd.DataFrame:
    """Load precision_model_diagnostics.csv as-is. No recomputation."""
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(
            f"{INPUT_PATH} not found — run 06a_build_precision_model_diagnostics.py first."
        )
    df = pd.read_csv(INPUT_PATH)
    print(f"Loaded {len(df)} rows x {len(df.columns)} columns from {INPUT_PATH}")
    missing_cols = [c for c in ALL_EXPECTED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Expected columns missing from input CSV: {missing_cols}")
    if len(df) != EXPECTED_N_ROWS:
        print(
            f"[WARN] Expected {EXPECTED_N_ROWS} rows (74 analysis_type x "
            f"parameter combinations), found {len(df)}. Proceeding anyway "
            "since this script must render whatever the diagnostics CSV "
            "actually contains."
        )
    unknown_categories = set(df[CATEGORY_COLUMN].dropna().unique()) - set(CATEGORY_ORDER)
    if unknown_categories:
        raise ValueError(
            f"Unrecognized precision_model_category value(s) found: "
            f"{unknown_categories}. Expected one of {CATEGORY_ORDER}. "
            "Update CATEGORY_ORDER/CATEGORY_COLORS/CATEGORY_ABBREV in this "
            "script if new categories are intentionally introduced upstream."
        )
    return df


def sort_and_label(df: pd.DataFrame) -> pd.DataFrame:
    """Sort rows by analysis_type, then parameter (stable), and build the
    human-readable row label used on the y-axis. Same convention as
    05_build_review_heatmap.py.
    """
    sorted_df = df.sort_values(
        by=["analysis_type", "parameter"], kind="stable"
    ).reset_index(drop=True)
    sorted_df["row_label"] = (
        sorted_df["analysis_type"] + " / " + sorted_df["parameter"]
    )
    return sorted_df


def minmax_normalize_ignoring_nan(series: pd.Series) -> pd.Series:
    """Per-column min-max scale to [0, 1], EXCLUDING NaNs from the min/max
    calculation. NaN inputs remain NaN in the output — never coerced to 0,
    and never allowed to distort another cell's normalization.

    Handles negative values correctly: min/max are taken directly from the
    data (no assumption of a 0-based range), so columns like
    spearman_mean_vs_SD/spearman_mean_vs_RSD (~-1..1) and loglog_slope
    (can be negative) normalize correctly.
    """
    valid = series.dropna()
    if valid.empty:
        # Entire column is NaN — nothing to rank (not expected given the
        # data, but handled defensively).
        return pd.Series(np.nan, index=series.index)
    col_min, col_max = valid.min(), valid.max()
    if col_max == col_min:
        # Degenerate column (all defined values equal) — avoid a divide by
        # zero; render all defined cells at mid-scale rather than crashing
        # or arbitrarily picking 0/1.
        return series.apply(lambda v: np.nan if pd.isna(v) else 0.5)
    return (series - col_min) / (col_max - col_min)


def format_numeric_value(col: str, value: float) -> str:
    """Per-column raw-value text formatting for numeric cell annotations.
    NaN always renders as the placeholder, never as 0 or a blank number.
    """
    if pd.isna(value):
        return NAN_PLACEHOLDER
    if col in ("n_replicate_groups", "n_points_usable_for_loglog"):
        return f"{value:.0f}"
    # spearman_mean_vs_SD, spearman_mean_vs_RSD, loglog_slope, loglog_r_squared
    return f"{value:.2f}"


def build_heatmap(df: pd.DataFrame) -> plt.Figure:
    n_rows = len(df)
    n_numeric_cols = len(NUMERIC_COLUMNS)
    n_total_cols = n_numeric_cols + 1  # + categorical column

    if HAVE_SEABORN:
        sns.set_theme(style="white")
        print(
            "seaborn is installed — using seaborn's theme for figure "
            "aesthetics, but the heatmap grid itself is drawn with plain "
            "matplotlib imshow() calls (not seaborn.heatmap()), because "
            "seaborn.heatmap() cannot express independently-normalized "
            "per-column numeric color scales combined with a discrete "
            "categorical column in a single call."
        )
    else:
        print(
            "seaborn is NOT installed in this environment — falling back "
            "to plain matplotlib (pyplot) with manual imshow() + text "
            "annotation."
        )

    # --- Per-column, NaN-safe min-max normalization (numeric columns only, color only) ---
    color_matrix = np.full((n_rows, n_numeric_cols), np.nan)
    for j, col in enumerate(NUMERIC_COLUMNS):
        color_matrix[:, j] = minmax_normalize_ignoring_nan(df[col]).to_numpy()

    numeric_masked = np.ma.masked_invalid(color_matrix)

    cmap = matplotlib.colormaps["viridis"].copy()
    cmap.set_bad(color=NAN_CATEGORY_COLOR)  # NaN cells -> distinct gray, no numeric color meaning

    # --- Categorical column: discrete color per fixed category, never a gradient ---
    category_values = df[CATEGORY_COLUMN]
    category_codes = np.full(n_rows, np.nan)
    for i, cat in enumerate(category_values):
        if pd.isna(cat):
            continue  # left as NaN -> rendered as the NaN gray, same as numeric NaN cells
        category_codes[i] = CATEGORY_ORDER.index(cat)
    category_display = np.ma.masked_invalid(category_codes.reshape(-1, 1))

    category_cmap = mcolors.ListedColormap([CATEGORY_COLORS[c] for c in CATEGORY_ORDER])
    category_cmap.set_bad(color=NAN_CATEGORY_COLOR)

    # --- Figure sizing (dynamic per row/column count; 74 rows x 7 columns) ---
    fig, ax = plt.subplots(figsize=(13, max(11, 0.22 * n_rows)))

    # Numeric block occupies x in [-0.5, n_numeric_cols - 0.5]
    im = ax.imshow(
        numeric_masked,
        cmap=cmap,
        vmin=0,
        vmax=1,
        aspect="auto",
        extent=(-0.5, n_numeric_cols - 0.5, n_rows - 0.5, -0.5),
    )

    # Categorical column occupies the next x slot, visually separated with
    # a vertical divider line, discretely colored (boundaries at
    # -0.5, 0.5, ..., len(CATEGORY_ORDER)-0.5 so each integer code maps to
    # exactly one solid color, no interpolation/gradient between categories).
    ax.imshow(
        category_display,
        cmap=category_cmap,
        vmin=-0.5,
        vmax=len(CATEGORY_ORDER) - 0.5,
        aspect="auto",
        extent=(n_numeric_cols - 0.5, n_numeric_cols + 0.5, n_rows - 0.5, -0.5),
    )
    ax.axvline(x=n_numeric_cols - 0.5, color="black", linewidth=1.5)

    ax.set_xlim(-0.5, n_total_cols - 0.5)
    ax.set_ylim(n_rows - 0.5, -0.5)

    # --- Cell annotations: always the RAW value/label, never the normalized code ---
    for i in range(n_rows):
        for j, col in enumerate(NUMERIC_COLUMNS):
            raw_val = df.iloc[i][col]
            text = format_numeric_value(col, raw_val)
            norm_val = color_matrix[i, j]
            if pd.isna(norm_val):
                text_color = "#555555"  # NaN placeholder — neutral gray text
            else:
                # Light text on dark backgrounds, dark text on light ones.
                text_color = "white" if norm_val > 0.55 else "black"
            ax.text(
                j,
                i,
                text,
                ha="center",
                va="center",
                fontsize=7,
                color=text_color,
            )
        # Categorical column — abbreviation annotated with a per-category
        # fixed, legible text color; NaN gets the neutral placeholder.
        raw_cat = df.iloc[i][CATEGORY_COLUMN]
        if pd.isna(raw_cat):
            cat_text = NAN_PLACEHOLDER
            cat_text_color = "#555555"
        else:
            cat_text = CATEGORY_ABBREV[raw_cat]
            cat_text_color = CATEGORY_TEXT_COLORS[raw_cat]
        ax.text(
            n_numeric_cols,
            i,
            cat_text,
            ha="center",
            va="center",
            fontsize=7,
            color=cat_text_color,
        )

    # --- Axis labels / ticks ---
    ax.set_xticks(range(n_total_cols))
    ax.set_xticklabels(
        NUMERIC_COLUMNS + [CATEGORY_COLUMN],
        rotation=45,
        ha="right",
        fontsize=9,
    )
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(df["row_label"], fontsize=6.5)
    ax.set_xlabel("")
    ax.set_ylabel("analysis_type / parameter")

    ax.set_title(
        "BioCirV Precision-Model Screen Heatmap — one row per "
        "analysis_type x parameter (n=%d)\n"
        "Numeric columns: per-column min-max relative rank (0=lowest, "
        "1=highest within that column only) — NOT an absolute/pass-fail "
        "scale.\n"
        "precision_model_category: discrete, exploratory triage label "
        "(NOT a validated model) — see script docstring." % n_rows,
        fontsize=10,
        loc="left",
    )

    cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cbar.set_label(
        "Per-column relative rank (0=lowest, 1=highest within that column)",
        fontsize=8,
    )

    # --- Categorical color legend (abbreviation -> full category name) ---
    legend_handles = [
        mpatches.Patch(
            facecolor=CATEGORY_COLORS[cat],
            edgecolor="black",
            label=f"{CATEGORY_ABBREV[cat]} = {cat}",
        )
        for cat in CATEGORY_ORDER
    ]
    legend_handles.append(
        mpatches.Patch(
            facecolor=NAN_CATEGORY_COLOR,
            edgecolor="black",
            label=f"{NAN_PLACEHOLDER} = missing / NaN",
        )
    )
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=3,
        fontsize=7.5,
        frameon=True,
        bbox_to_anchor=(0.5, 0.045),
        title="precision_model_category (discrete color key)",
        title_fontsize=8,
    )

    # Footer note reinforcing the interpretation boundary directly on the figure.
    fig.text(
        0.5,
        0.005,
        "Exploratory triage screen only — NOT validated statistical models, "
        "NOT production QC rules. Do not auto-assign an absolute-SD-vs-"
        "relative-RSD precision model without human review. Gray cells = "
        "NaN / not applicable, never coerced to 0.",
        ha="center",
        fontsize=8,
        style="italic",
    )

    fig.tight_layout(rect=(0, 0.09, 1, 1))
    return fig


def validate_output(path: str) -> bool:
    """Confirm the PNG exists, is non-empty, and can be re-opened as a
    valid image — do not just assume success because savefig() didn't
    raise.
    """
    print("\n=== Output validation ===")
    if not os.path.exists(path):
        print(f"[FAIL] Output file does not exist: {path}")
        return False

    size_bytes = os.path.getsize(path)
    print(f"File: {path}")
    print(f"Size: {size_bytes} bytes")
    if size_bytes == 0:
        print("[FAIL] Output file is zero bytes.")
        return False

    ok = True

    # Check 1: PIL can open and verify the file structure.
    try:
        from PIL import Image

        with Image.open(path) as img:
            img.verify()
        print("[PASS] PIL.Image.open(...).verify() succeeded.")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] PIL verification failed: {exc}")
        ok = False

    # Check 2: matplotlib can re-read the pixel array with non-zero dimensions.
    try:
        arr = plt.imread(path)
        h, w = arr.shape[0], arr.shape[1]
        print(f"[PASS] matplotlib.pyplot.imread(...) succeeded, shape={arr.shape}")
        if h == 0 or w == 0:
            print("[FAIL] Re-read image has a zero dimension.")
            ok = False
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] matplotlib re-read failed: {exc}")
        ok = False

    return ok


def main() -> None:
    df = load_diagnostics()
    df = sort_and_label(df)
    n_total_cols = len(NUMERIC_COLUMNS) + 1
    print(f"Rows to plot: {len(df)} | Columns to plot: {n_total_cols}")

    fig = build_heatmap(df)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=150)
    plt.close(fig)
    print(f"\nSaved heatmap to: {OUTPUT_PATH}")

    ok = validate_output(OUTPUT_PATH)
    if ok:
        print("\nAll output validation checks passed.")
    else:
        print(
            "\n*** VALIDATION FAILURE: one or more output checks did not "
            "pass. Investigate before treating this figure as final. ***"
        )


if __name__ == "__main__":
    main()
