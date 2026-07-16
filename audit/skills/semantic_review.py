# audit/skills/semantic_review.py
import litellm
import json
import os
from pathlib import Path
from typing import List, Dict
from audit.skills.grouped_outlier_detection import FlaggedObservation
from audit.config import settings

# Reuse existing rubric
SYSTEM_PROMPT_PATH = Path("audit/REPORT_PROMPT.md")

import pandas as pd

def semantic_review(
    target_name: str,
    flagged_observations: List[FlaggedObservation],
    population_df: pd.DataFrame,
    model: str = settings.LLM_MODEL,
    max_tokens: int = settings.LLM_MAX_TOKENS,
) -> str:
    """
    Uses LLM to generate a holistic synthesis of the audit results.
    Returns a single Markdown string containing the analysis.
    """
    if not flagged_observations and population_df.empty:
        return "No data available for review."

    system_prompt = ""
    if SYSTEM_PROMPT_PATH.exists():
        system_prompt = SYSTEM_PROMPT_PATH.read_text()

    # 1. Population Distribution Summary (Layer 1 stats)
    # We'll create a simple summary of the numerical columns
    numeric_cols = population_df.select_dtypes(include='number').columns
    if not numeric_cols.empty:
        pop_summary = population_df[numeric_cols].describe().to_markdown()
    else:
        pop_summary = "No numerical data available for population summary."

    # 2. Flagged Observations Table
    if flagged_observations:
        obs_data = [
            {
                "record_id": o.record_id,
                "resource": o.resource_name,
                "parameter": o.parameter_name,
                "value": o.observed_value,
                "unit": o.unit,
                "z_score": o.z_score,
                "note": o.note
            }
            for o in flagged_observations
        ]
        obs_df = pd.DataFrame(obs_data)
        obs_table = obs_df.to_markdown(index=False)

        # 3. Aggregated Counts
        anomalies_per_param = obs_df['parameter'].value_counts().to_markdown()
        anomalies_per_resource = obs_df['resource'].value_counts().to_markdown()
    else:
        obs_table = "No flagged observations."
        anomalies_per_param = "N/A"
        anomalies_per_resource = "N/A"

    user_message = f"""
Audit Target: {target_name}

## Population Distribution Summary
{pop_summary}

## Flagged Observations
{obs_table}

## Aggregated Counts
### Anomalies per Parameter
{anomalies_per_param}

### Anomalies per Resource
{anomalies_per_resource}
"""

    response = litellm.completion(
        model=model,
        api_key=os.environ.get("CBORG_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        api_base=settings.LLM_BASE_URL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=max_tokens,
    )

    try:
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating semantic review: {str(e)}"
