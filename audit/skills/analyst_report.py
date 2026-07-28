# audit/skills/analyst_report.py
import pandas as pd
import json
from typing import List, Dict, Optional
from datetime import datetime
from audit.skills.grouped_outlier_detection import FlaggedObservation
from audit.config import settings

def generate_analyst_report(
    target_name: str,
    flagged_observations: List[FlaggedObservation],
    llm_synthesis: str,
    sheet_url: Optional[str] = None,
    zscore_threshold: float = settings.ZSCORE_THRESHOLD,
    min_group_size: int = settings.MIN_GROUP_SIZE,
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

    md = f"# 🔍 Detailed Target Audit: `{target_name}` — {date_str}\n\n"
    md += f"**Flagged Observations:** {len(flagged_observations)} ({severity_counts['HIGH']} HIGH, {severity_counts['MEDIUM']} MEDIUM, {severity_counts['LOW']} LOW)\n\n"
    md += f"**Z-Score Threshold:** {zscore_threshold} | **Min Group Size:** {min_group_size}\n\n"

    if sheet_url:
        md += f"**[🔗 View and Manage Anomalies in Google Sheets]({sheet_url})**\n\n"

    md += "---\n\n"
    md += "## 🧠 LLM Synthesis\n\n"
    md += llm_synthesis + "\n\n"

    if flagged_observations:
        md += "## 🚩 Flagged Observations (Top 100)\n\n"
        md += "| Record ID | Resource | Provider | Sample Date | Parameter | Value | Z-Score | Severity |\n"
        md += "|-----------|----------|----------|-------------|-----------|-------|---------|----------|\n"
        for obs in flagged_observations[:100]:
            provider = obs.provider_codename or "—"
            sample_date = obs.sample_date or "—"
            md += f"| {obs.record_id} | {obs.resource_name} | {provider} | {sample_date} | {obs.parameter_name} | {obs.observed_value:.4f} | {obs.z_score:.2f} | {obs.severity} |\n"

        if len(flagged_observations) > 100:
            md += f"\n*...and {len(flagged_observations) - 100} more observations. See `flagged_{target_name}.csv` for full data.*\n"

    return md
