"""
Detects anomalous individual observations within each (resource_name x parameter_name)
group using within-group Z-scores. A moisture reading of 87% for almond hull is
compared only against other almond hull moisture readings.
"""
from dataclasses import dataclass
from typing import Optional, List
import pandas as pd
import numpy as np

@dataclass
class FlaggedObservation:
    """A single anomalous observation, ready for analyst reporting."""
    record_id: str
    resource_name: str
    parameter_name: str
    unit: Optional[str]
    observed_value: float
    group_mean: float
    group_std: float
    group_n: int
    z_score: float
    severity: str           # "HIGH" |z|>4, "MEDIUM" |z|>3, "LOW" |z|>2.5
    analyst_name: Optional[str]
    analyst_email: Optional[str]
    qc_pass: Optional[str]
    note: Optional[str]
    created_at: Optional[str]

def detect_grouped_outliers(
    population_df: pd.DataFrame,   # Layer 1: group-level stats from view
    observation_df: pd.DataFrame,  # Layer 2: individual records from tables
    group_cols: List[str],          # ["resource_name", "parameter_name", "unit"]
    value_col: str = "observed_value",
    id_col: str = "record_id",
    zscore_threshold: float = 3.0,
    min_group_size: int = 3,
) -> List[FlaggedObservation]:
    """
    Merge population stats into individual observations, compute within-group
    Z-scores, and return all records exceeding the threshold.
    """
    merged = observation_df.merge(
        population_df[group_cols + ["avg_value", "std_dev", "observation_count"]],
        on=group_cols,
        how="left",
    )
    merged = merged[merged["observation_count"] >= min_group_size]

    # Avoid division by zero
    std = merged["std_dev"].replace(0, np.nan)
    merged["z_score"] = ((merged[value_col] - merged["avg_value"]) / std).abs()

    flagged = merged[merged["z_score"] > zscore_threshold].copy()

    def get_severity(z: float) -> str:
        if z > 4.0: return "HIGH"
        if z > 3.0: return "MEDIUM"
        return "LOW"

    results = [
        FlaggedObservation(
            record_id=row[id_col],
            resource_name=row["resource_name"],
            parameter_name=row["parameter_name"],
            unit=row.get("unit"),
            observed_value=float(row[value_col]),
            group_mean=float(row["avg_value"]),
            group_std=float(row["std_dev"]),
            group_n=int(row["observation_count"]),
            z_score=float(row["z_score"]),
            severity=get_severity(row["z_score"]),
            analyst_name=row.get("analyst_name"),
            analyst_email=row.get("analyst_email"),
            qc_pass=row.get("qc_pass"),
            note=row.get("note"),
            created_at=str(row.get("created_at", "")),
        )
        for _, row in flagged.iterrows()
    ]
    results.sort(key=lambda x: x.z_score, reverse=True)
    return results
