# audit/skills/analyst_report.py
import pandas as pd
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
    Generates a structured Markdown report for analysts.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")

    severity_counts = {
        "HIGH": len([o for o in flagged_observations if o.severity == "HIGH"]),
        "MEDIUM": len([o for o in flagged_observations if o.severity == "MEDIUM"]),
        "LOW": len([o for o in flagged_observations if o.severity == "LOW"]),
    }

    summary_line = f"{len(flagged_observations)} ({severity_counts['HIGH']} HIGH, {severity_counts['MEDIUM']} MEDIUM, {severity_counts['LOW']} LOW)"

    md = f"""## ⚠️ Anomaly Report — {date_str}

**Audit Target:** {target_name}
**Flagged Observations:** {summary_line}
**Z-Score Threshold:** {zscore_threshold} | **Min Group Size:** {min_group_size}

---
"""

    for obs in flagged_observations:
        severity_emoji = "🔴" if obs.severity == "HIGH" else "🟠" if obs.severity == "MEDIUM" else "🟡"

        md += f"""
### {severity_emoji} {obs.severity} — {obs.resource_name} / {obs.parameter_name}
| Field | Value |
|---|---|
| Record ID | `{obs.record_id}` |
| Observed Value | {obs.observed_value} {obs.unit or ''} |
| Group Mean ± Std | {obs.group_mean:.2f} ± {obs.group_std:.2f} (n={obs.group_n}) |
| Z-Score | **{obs.z_score:.2f}** |
| QC Status | {obs.qc_pass or '—'} |
| Analyst | {obs.analyst_name or '—'} ({obs.analyst_email or '—'}) |
| Recorded | {obs.created_at or '—'} |
| Note | {obs.note or '—'} |
"""
        if llm_assessments and obs.record_id in llm_assessments:
            md += f"\n**LLM Assessment:** {llm_assessments[obs.record_id]}\n"

        md += "\n---\n"

    return md
