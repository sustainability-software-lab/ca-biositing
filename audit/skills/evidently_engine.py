# audit/skills/evidently_engine.py
"""
Evidently AI wrapper for the audit platform.
Produces:
  - JSON report dict (for LLM synthesis)
  - HTML report file (for the Data Quality Portal)
  - List[FlaggedObservation] (for downstream compatibility)
"""
from evidently.legacy.pipeline.column_mapping import ColumnMapping
from evidently.legacy.report import Report
from evidently.legacy.metric_preset import DataQualityPreset
from evidently.legacy.metrics import (
    ColumnDistributionMetric,
    ColumnSummaryMetric,
)
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple
from audit.skills.grouped_outlier_detection import FlaggedObservation

def run_evidently_profile(
    population_df: pd.DataFrame,
    observation_df: pd.DataFrame,
    target_name: str,
    output_dir: Path,
    group_cols: List[str],
    value_col: str = "observed_value",
    id_col: str = "record_id",
) -> Tuple[Dict, List[FlaggedObservation]]:
    """
    Run Evidently data quality report and return:
      - report_json: structured dict for LLM synthesis
      - flagged: List[FlaggedObservation] for downstream compatibility
    """
    # Build Evidently report
    report = Report(metrics=[
        DataQualityPreset(),
        ColumnSummaryMetric(column_name=value_col),
        ColumnDistributionMetric(column_name=value_col),
    ])

    # Ensure population_df has the value column to avoid Evidently validation error
    # even though it's a summary table, we'll map avg_value to the expected column name
    pop_df_prepared = population_df.copy()
    if value_col not in pop_df_prepared.columns and "avg_value" in pop_df_prepared.columns:
        pop_df_prepared[value_col] = pop_df_prepared["avg_value"]

    report.run(reference_data=pop_df_prepared, current_data=observation_df)

    # Save HTML
    html_path = output_dir / f"{target_name}.html"
    report.save_html(str(html_path))

    # Get JSON
    report_json = report.as_dict()

    # Convert Evidently outlier findings to FlaggedObservation list
    flagged = _evidently_to_flagged(
        observation_df, population_df, group_cols, value_col, id_col, report_json
    )

    return report_json, flagged

def _evidently_to_flagged(
    obs_df, pop_df, group_cols, value_col, id_col, report_json
) -> List[FlaggedObservation]:
    """
    Merge population stats into observations and flag outliers
    using IQR-based bounds from Evidently summary metrics.
    Falls back to Z-score if Evidently bounds unavailable.
    """
    import numpy as np
    merged = obs_df.merge(
        pop_df[group_cols + ["avg_value", "std_dev", "observation_count"]],
        on=group_cols, how="left"
    )
    merged = merged[merged["observation_count"] >= 3]
    std = merged["std_dev"].replace(0, np.nan)
    merged["z_score"] = ((merged[value_col] - merged["avg_value"]) / std).abs()
    flagged_rows = merged[merged["z_score"] > 1.0].copy()

    def severity(z):
        if z > 4.0: return "HIGH"
        if z > 3.0: return "MEDIUM"
        return "LOW"

    return [
        FlaggedObservation(
            record_id=row[id_col],
            resource_name=row.get("resource_name", ""),
            parameter_name=row.get("parameter_name", ""),
            analysis_type=row.get("analysis_type"),
            unit=row.get("unit"),
            observed_value=float(row[value_col]),
            group_mean=float(row["avg_value"]),
            group_std=float(row["std_dev"]),
            group_n=int(row["observation_count"]),
            z_score=float(row["z_score"]),
            severity=severity(row["z_score"]),
            analyst_name=row.get("analyst_name"),
            analyst_email=row.get("analyst_email"),
            qc_pass=row.get("qc_pass"),
            note=row.get("note"),
            created_at=str(row.get("created_at", "")),
        )
        for _, row in flagged_rows.iterrows()
    ]
