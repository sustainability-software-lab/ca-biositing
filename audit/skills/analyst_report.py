# audit/skills/analyst_report.py
import pandas as pd
import json
from typing import List, Dict, Optional
from datetime import datetime
from audit.skills.grouped_outlier_detection import FlaggedObservation

def generate_analyst_report(
    target_name: str,
    flagged_observations: List[FlaggedObservation],
    llm_synthesis: str,
    sheet_url: Optional[str] = None,
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

    if sheet_url:
        md += f"**[🔗 View and Manage Anomalies in Google Sheets]({sheet_url})**\n\n"

    md += "---\n\n"
    md += "## 🧠 LLM Synthesis\n\n"
    md += llm_synthesis + "\n\n"

    return md
