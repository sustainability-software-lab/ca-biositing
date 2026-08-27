"""
05_build_review_heatmap.py — Step 5 (handoff v4, "Build One Compact Review
Heatmap").

INTERPRETATION BOUNDARY (read before using this figure):
This heatmap is a descriptive comparison tool for data coverage,
typical/high-tail relative replicate precision (RSD-based), and RSD/Dixon
flagging rates across `analysis_type x parameter` combinations. It must NOT
be used to choose final QC thresholds, decide absolute-SD-vs-relative-RSD
precision models, or rank parameters by absolute SD (units differ across
parameters) — those are explicit human-review decisions per the handoff's
"Scientific Decisions After the MVP" section.

Purpose:
Load the already-computed `outputs/method_parameter_summary.csv` (built by
`04_build_method_parameter_summary.py`, 74 rows = 74 distinct
`analysis_type x parameter` combinations) and render it as ONE compact,
whole-dataset heatmap image. This script performs NO statistical
recomputation whatsoever — every number shown is read as-is from the CSV;
this script only visualizes it.

Column treatment (see handoff Step 5 + task spec):
- 8 "color-ranked" columns (n_replicate_groups, percent_RSD_defined,
  percent_Dixon_calculated, median_RSD, P90_RSD, percent_RSD_gt_10,
  percent_RSD_gt_20, percent_Dixon_flagged) are each independently
  min-max normalized (0-1, NaN-safe) PURELY to drive per-cell background
  color for relative-magnitude comparison WITHIN that column. The raw,
  non-normalized value is always what's printed in the cell.
- `median_SD` is included as a 9th column in the same grid for
  at-a-glance reference, but is deliberately NOT color-ranked: it is
  reported in different physical units depending on analysis_type/parameter
  (e.g. % for compositional analytes vs ppm for ICP), so a single color
  scale across all rows for this column would misleadingly imply
  cross-parameter comparability that does not exist. It is rendered with a
  flat neutral background (no colormap) and the raw value is annotated as
  text only — "shown for reference, not ranked" (see its x-axis label
  suffix in the figure).
- NaN handling is explicit everywhere: NaN is excluded from each column's
  min/max during normalization (never coerced to 0), and any NaN cell is
  rendered with a distinct gray background and a "—" placeholder instead of
  a number (never silently becomes 0 and never crashes normalization).

Guardrails honored:
- No recomputation of statistics — reads method_parameter_summary.csv as-is.
- Exactly ONE heatmap image — no per-parameter plots (that is a separate,
  later Step 6 task).
- No thresholds/cutoffs derived from this visualization are written back to
  analysis_config.py.

Usage:
    pixi run python audit/outliers/biocirv_outlier_assessment/05_build_review_heatmap.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis_config  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(analysis_config.OUTPUT_DIR, "method_parameter_summary.csv")
OUTPUT_PATH = os.path.join(analysis_config.OUTPUT_DIR, "precision_review_heatmap.png")

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
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Column configuration
# ---------------------------------------------------------------------------

# Columns whose values are independently min-max normalized (0-1) purely to
# drive relative-magnitude cell BACKGROUND COLOR. The raw value is always
# what's annotated in the cell — normalization NEVER touches the displayed
# number, only the color. (Handoff Step 5 "Preferred comparable metrics",
# plus percent_RSD_defined / percent_Dixon_calculated for data-coverage
# context, per this task's explicit column list.)
COLOR_RANKED_COLUMNS = [
    "n_replicate_groups",
    "percent_RSD_defined",
    "percent_Dixon_calculated",
    "median_RSD",
    "P90_RSD",
    "percent_RSD_gt_10",
    "percent_RSD_gt_20",
    "percent_Dixon_flagged",
]

# median_SD is included in the SAME heatmap grid for at-a-glance reference,
# but is NOT color-ranked (see module docstring). Rendered with a flat
# neutral background, raw value annotated as text only.
MEDIAN_SD_COLUMN = "median_SD"
MEDIAN_SD_AXIS_LABEL = "median_SD (raw, not ranked)"

ALL_COLUMNS = COLOR_RANKED_COLUMNS + [MEDIAN_SD_COLUMN]

NAN_PLACEHOLDER = "\u2014"  # em dash — used for any missing/NaN cell, never "0"


def load_summary() -> pd.DataFrame:
    """Load method_parameter_summary.csv as-is. No recomputation."""
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(
            f"{INPUT_PATH} not found — run 04_build_method_parameter_summary.py first."
        )
    df = pd.read_csv(INPUT_PATH)
    print(f"Loaded {len(df)} rows x {len(df.columns)} columns from {INPUT_PATH}")
    missing_cols = [c for c in ALL_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Expected columns missing from input CSV: {missing_cols}")
    return df


def sort_and_label(df: pd.DataFrame) -> pd.DataFrame:
    """Sort rows by analysis_type, then parameter (stable), and build the
    human-readable row label used on the y-axis."""
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
    """
    valid = series.dropna()
    if valid.empty:
        # Entire column is NaN (not expected for our 8 color-ranked columns
        # given the data, but handled defensively) — nothing to rank.
        return pd.Series(np.nan, index=series.index)
    col_min, col_max = valid.min(), valid.max()
    if col_max == col_min:
        # Degenerate column (all defined values equal) — avoid a divide by
        # zero; render all defined cells at mid-scale rather than crashing
        # or arbitrarily picking 0/1.
        return series.apply(lambda v: np.nan if pd.isna(v) else 0.5)
    return (series - col_min) / (col_max - col_min)


def format_value(col: str, value: float) -> str:
    """Per-column raw-value text formatting for cell annotations. NaN always
    renders as the placeholder, never as 0 or a blank number.
    """
    if pd.isna(value):
        return NAN_PLACEHOLDER
    if col == "n_replicate_groups":
        return f"{value:.0f}"
    if col in (
        "percent_RSD_defined",
        "percent_Dixon_calculated",
        "percent_RSD_gt_10",
        "percent_RSD_gt_20",
        "percent_Dixon_flagged",
    ):
        return f"{value:.1f}"
    if col in ("median_RSD", "P90_RSD"):
        return f"{value:.2f}"
    if col == MEDIAN_SD_COLUMN:
        # Raw SD in original, per-parameter units (spans ~0 to >1000 across
        # analysis_type x parameter) — 3 significant figures keeps cells
        # compact without implying false precision.
        return f"{value:.3g}"
    return f"{value:.2f}"


def build_heatmap(df: pd.DataFrame) -> plt.Figure:
    n_rows = len(df)
    n_ranked_cols = len(COLOR_RANKED_COLUMNS)
    n_total_cols = len(ALL_COLUMNS)

    if HAVE_SEABORN:
        sns.set_theme(style="white")
        print(
            "seaborn is installed — using seaborn's theme for figure "
            "aesthetics, but the heatmap grid itself is drawn with plain "
            "matplotlib imshow() calls (not seaborn.heatmap()), because "
            "seaborn.heatmap() cannot express independently-normalized "
            "per-column color scales combined with a non-ranked reference "
            "column in a single call."
        )
    else:
        print(
            "seaborn is NOT installed in this environment — falling back "
            "to plain matplotlib (pyplot) with manual imshow() + text "
            "annotation."
        )

    # --- Per-column, NaN-safe min-max normalization (color only) ---
    color_matrix = np.full((n_rows, n_ranked_cols), np.nan)
    for j, col in enumerate(COLOR_RANKED_COLUMNS):
        color_matrix[:, j] = minmax_normalize_ignoring_nan(df[col]).to_numpy()

    ranked_masked = np.ma.masked_invalid(color_matrix)

    cmap = matplotlib.colormaps["viridis"].copy()
    cmap.set_bad(color="#d9d9d9")  # NaN cells -> distinct gray, no numeric color meaning

    # median_SD reference column: fixed, flat neutral background (no
    # colormap gradient / no cross-row comparison implied). NaN cells get a
    # slightly darker gray so they remain visually distinct from populated
    # reference cells.
    sd_values = df[MEDIAN_SD_COLUMN].to_numpy()
    sd_nan_mask = np.isnan(sd_values)
    sd_display = np.ma.array(np.zeros((n_rows, 1)), mask=sd_nan_mask.reshape(-1, 1))
    neutral_cmap = mcolors.ListedColormap(["#f2f2f2"])  # single light gray, no gradient
    neutral_cmap.set_bad(color="#c9c9c9")  # NaN in the reference column

    # --- Figure sizing (dynamic per row/column count) ---
    fig, ax = plt.subplots(figsize=(14, max(10, 0.22 * n_rows)))

    # Color-ranked block occupies x in [-0.5, n_ranked_cols - 0.5]
    im = ax.imshow(
        ranked_masked,
        cmap=cmap,
        vmin=0,
        vmax=1,
        aspect="auto",
        extent=(-0.5, n_ranked_cols - 0.5, n_rows - 0.5, -0.5),
    )

    # median_SD reference column occupies the next x slot, visually
    # separated with a vertical divider line below.
    ax.imshow(
        sd_display,
        cmap=neutral_cmap,
        aspect="auto",
        extent=(n_ranked_cols - 0.5, n_ranked_cols + 0.5, n_rows - 0.5, -0.5),
    )
    ax.axvline(x=n_ranked_cols - 0.5, color="black", linewidth=1.5)

    ax.set_xlim(-0.5, n_total_cols - 0.5)
    ax.set_ylim(n_rows - 0.5, -0.5)

    # --- Cell annotations: always the RAW value, never the normalized one ---
    for i in range(n_rows):
        for j, col in enumerate(COLOR_RANKED_COLUMNS):
            raw_val = df.iloc[i][col]
            text = format_value(col, raw_val)
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
        # median_SD reference column — always plain dark text on neutral bg.
        raw_sd = df.iloc[i][MEDIAN_SD_COLUMN]
        sd_text = format_value(MEDIAN_SD_COLUMN, raw_sd)
        sd_color = "#555555" if pd.isna(raw_sd) else "black"
        ax.text(
            n_ranked_cols,
            i,
            sd_text,
            ha="center",
            va="center",
            fontsize=7,
            color=sd_color,
        )

    # --- Axis labels / ticks ---
    ax.set_xticks(range(n_total_cols))
    ax.set_xticklabels(
        COLOR_RANKED_COLUMNS + [MEDIAN_SD_AXIS_LABEL],
        rotation=45,
        ha="right",
        fontsize=9,
    )
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(df["row_label"], fontsize=6.5)
    ax.set_xlabel("")
    ax.set_ylabel("analysis_type / parameter")

    ax.set_title(
        "BioCirV Replicate Precision Review Heatmap — one row per "
        "analysis_type x parameter (n=%d)\n"
        "Colored columns: per-column min-max relative rank (0=lowest, "
        "1=highest within that column only) — NOT an absolute/pass-fail "
        "scale.\n"
        "Gray-background column: median_SD, raw values only, deliberately "
        "NOT color-ranked (different units per parameter — see script "
        "docstring)." % n_rows,
        fontsize=10,
        loc="left",
    )

    cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cbar.set_label(
        "Per-column relative rank (0=lowest, 1=highest within that column)",
        fontsize=8,
    )

    # Footer note reinforcing the interpretation boundary directly on the figure.
    fig.text(
        0.5,
        0.005,
        "Descriptive comparison only — NOT for choosing QC thresholds, "
        "absolute-SD-vs-RSD model decisions, or absolute-SD ranking across "
        "parameters (units differ). Gray cells = NaN / not applicable, "
        "never coerced to 0.",
        ha="center",
        fontsize=8,
        style="italic",
    )

    fig.tight_layout(rect=(0, 0.02, 1, 1))
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
    df = load_summary()
    df = sort_and_label(df)
    print(f"Rows to plot: {len(df)} | Columns to plot: {len(ALL_COLUMNS)}")

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
