# audit/skills/semantic_review.py
import litellm
import json
from pathlib import Path
from typing import List, Dict
from typing import List, Dict
from audit.skills.grouped_outlier_detection import FlaggedObservation

# Reuse existing rubric
SYSTEM_PROMPT_PATH = Path("audit/REPORT_PROMPT.md")

def semantic_review(
    target_name: str,
    flagged_observations: List[FlaggedObservation],
    profile_summary: Dict,
    gx_result: Dict,
    model: str = "anthropic/claude-3-5-sonnet-20241022",
    max_tokens: int = 4096,
) -> Dict[str, str]:
    """
    Uses LLM to generate assessments for flagged observations.
    Returns a mapping of record_id -> assessment_text.
    """
    if not flagged_observations:
        return {}

    system_prompt = ""
    if SYSTEM_PROMPT_PATH.exists():
        system_prompt = SYSTEM_PROMPT_PATH.read_text()

    # Build a compact representation for the LLM
    obs_data = [
        {
            "record_id": o.record_id,
            "resource": o.resource_name,
            "parameter": o.parameter_name,
            "value": o.observed_value,
            "unit": o.unit,
            "group_mean": o.group_mean,
            "group_std": o.group_std,
            "z_score": o.z_score,
            "note": o.note
        }
        for o in flagged_observations
    ]

    user_message = f"""
Audit Target: {target_name}

Flagged Observations:
{json.dumps(obs_data, indent=2)}

Please provide a concise assessment (1-2 sentences) for each record_id,
suggesting possible causes for the anomaly (e.g. unit error, contamination, equipment drift).
Return the result as a JSON object: {{"record_id": "assessment"}}
"""

    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=max_tokens,
        response_format={ "type": "json_object" }
    )

    try:
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception:
        return {}
