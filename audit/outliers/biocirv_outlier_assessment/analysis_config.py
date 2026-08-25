"""
analysis_config.py — flat, explicit configuration for the BioCirV
replicate-precision / outlier-assessment pipeline.

Per the handoff doc's guardrails ("Prefer a small config dictionary... Do
not build a generalized schema-conversion framework"), this module is
intentionally simple: plain module-level constants, no classes, no
pydantic. See `biocirv_outlier_assessment_handoff_v4.md` for the full
rationale behind each setting.
"""

# ---------------------------------------------------------------------------
# Input data location
# ---------------------------------------------------------------------------

# Path to the raw extraction input (most recent snapshot)
RAW_DATA_DIR = "audit/outliers/biocirv_outlier_assessment/data"
RAW_DATA_GLOB = "raw_extract_*.csv"  # normalize_inputs.py will pick the most recent by filename/date

# ---------------------------------------------------------------------------
# Output locations
# ---------------------------------------------------------------------------

OUTPUT_DIR = "audit/outliers/biocirv_outlier_assessment/outputs"
PLOTS_SELECTED_DIR = "audit/outliers/biocirv_outlier_assessment/outputs/plots_selected"

# ---------------------------------------------------------------------------
# Target analyses (handoff "Scope Boundary" / "Keep the target list configurable")
# ---------------------------------------------------------------------------

CHARACTERIZATION_ANALYSES = [
    "proximate",
    "xrf",
    "compositional",
    "xrd",
    "icp",
    "calorimetry",  # note: handoff doc's example config calls this "caloric"; we use
                     # "calorimetry" to match the actual DB table name / analysis_type
                     # value produced by extract_raw_data.py
    "ultimate",
]

TARGET_ANALYSES = CHARACTERIZATION_ANALYSES

# ---------------------------------------------------------------------------
# Technical replicate grouping key (handoff Step 0)
# ---------------------------------------------------------------------------

# sample_id here = prepared_sample_id (closest DB proxy to "independent sample").
# method is included when available (method_id/method_name on every Aim1 record).
# lab is approximated by provider_codename (no dedicated "lab" field in current
# schema — documented limitation, see README.md).
REPLICATE_GROUP_KEYS = ["sample_id", "analysis_type", "parameter", "unit", "method"]

# ---------------------------------------------------------------------------
# Candidate flag settings (handoff Step 3) — comparison benchmarks only,
# NOT proposed production thresholds.
# ---------------------------------------------------------------------------

# RSD sensitivity benchmarks (comparison benchmarks only, NOT proposed thresholds — see handoff Step 3)
RSD_BENCHMARK_THRESHOLDS = [10, 20]  # percent

# Dixon Q test significance level
DIXON_Q_ALPHA = 0.05

# Minimum / maximum replicate count required for Dixon Q applicability
# (Dixon Q is typically defined for n=3-30)
DIXON_Q_MIN_N = 3
DIXON_Q_MAX_N = 30

# ROUT — not implemented from scratch per handoff guardrails; always reported as not_calculated
ROUT_STATUS = "not_calculated"
ROUT_STATUS_REASON = "ROUT not implemented from scratch during MVP per handoff guardrails; no trusted existing implementation wired up yet."

# ---------------------------------------------------------------------------
# Diagnostic plot selection (handoff Step 6)
# ---------------------------------------------------------------------------

# Number of diagnostic combinations to select for detailed plotting (handoff Step 6)
N_DIAGNOSTIC_COMBINATIONS = (5, 10)  # inclusive range, pick within this
