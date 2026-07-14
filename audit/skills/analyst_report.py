# audit/skills/analyst_report.py
import pandas as pd
import json
from typing import List, Dict, Optional
from datetime import datetime
from audit.skills.grouped_outlier_detection import FlaggedObservation

def generate_analyst_report(
    target_name: str,
    flagged_observations: List[FlaggedObservation],
    llm_assessments: Optional[Dict[str, str]] = None,
    zscore_threshold: float = 3.0,
    min_group_size: int = 3,
) -> str:
    """
    Generates a Markdown report for analysts.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")

    severity_counts = {
        "HIGH": len([o for o in flagged_observations if o.severity == "HIGH"]),
        "MEDIUM": len([o for o in flagged_observations if o.severity == "MEDIUM"]),
        "LOW": len([o for o in flagged_observations if o.severity == "LOW"]),
    }

    md = f"# ⚠️ Anomaly Report — {date_str}\n\n"
    md += f"**Audit Target:** {target_name}\n\n"
    md += f"**Flagged Observations:** {len(flagged_observations)} ({severity_counts['HIGH']} HIGH, {severity_counts['MEDIUM']} MEDIUM, {severity_counts['LOW']} LOW)\n\n"
    md += f"**Z-Score Threshold:** {zscore_threshold} | **Min Group Size:** {min_group_size}\n\n"

    if not flagged_observations:
        md += "No anomalies detected.\n"
        return md

    # Group by resource name
    grouped = {}
    for obs in flagged_observations:
        if obs.resource_name not in grouped:
            grouped[obs.resource_name] = []
        grouped[obs.resource_name].append(obs)

    for resource, obs_list in grouped.items():
        md += f"## 🌿 Resource: {resource}\n\n"
        for obs in obs_list:
            emoji = "🔴" if obs.severity == "HIGH" else "🟠" if obs.severity == "MEDIUM" else "🟡"
            md += f"### {emoji} {obs.parameter_name} ({obs.severity})\n\n"

            md += "| Field | Value |\n"
            md += "|---|---|\n"
            md += f"| Record ID | `{obs.record_id}` |\n"
            md += f"| Analysis Type | {obs.analysis_type} |\n"
            md += f"| Observed Value | {obs.observed_value} {obs.unit or ''} |\n"
            md += f"| Group Mean ± Std | {obs.group_mean:.2f} ± {obs.group_std:.2f} (n={obs.group_n}) |\n"
            md += f"| Z-Score | **{obs.z_score:.2f}** |\n"
            md += f"| QC Status | {obs.qc_pass} |\n"
            md += f"| Analyst | {obs.analyst_name} ({obs.analyst_email}) |\n"
            md += f"| Recorded | {obs.created_at} |\n"
            md += f"| Note | {obs.note} |\n\n"

            if llm_assessments and obs.record_id in llm_assessments:
                md += f"> **LLM Assessment:** {llm_assessments[obs.record_id]}\n\n"

            md += "---\n\n"

    return md
