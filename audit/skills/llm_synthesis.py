"""
Structured LLM synthesis using instructor + litellm.
Converts Evidently JSON + FlaggedObservation list into
a list of GroupedIssue objects for the Anomaly Tracker.
"""
import instructor
import litellm
import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from audit.skills.grouped_outlier_detection import FlaggedObservation
from audit.config import settings

class GroupedIssue(BaseModel):
    """A single grouped anomaly issue for the Anomaly Tracker."""
    group_label: str = Field(description="Short label, e.g. 'Almond Hulls / Moisture'")
    hypothesis: str = Field(description="LLM-generated root cause hypothesis")
    priority: Literal["High", "Medium", "Low"]
    affected_record_ids: List[str] = Field(description="Up to 10 representative record IDs")
    affected_parameters: List[str]
    affected_resources: List[str]
    evidently_finding: Optional[str] = Field(description="Key Evidently metric that triggered this group")
    recommended_action: str

class SynthesisResult(BaseModel):
    executive_summary: str = Field(description="2-3 paragraph executive summary for the audit report")
    grouped_issues: List[GroupedIssue] = Field(description="Up to 50 grouped issues")

def run_llm_synthesis(
    target_name: str,
    flagged: List[FlaggedObservation],
    evidently_json: dict,
    model: str = settings.LLM_MODEL,
) -> SynthesisResult:
    """
    Uses instructor-patched litellm to produce structured synthesis.
    """
    client = instructor.from_litellm(litellm.completion)

    # Load Domain Context if available
    context_path = Path("audit/targets/context") / f"{target_name}.md"
    domain_context = ""
    if context_path.exists():
        domain_context = f"\n## Domain Context\n{context_path.read_text()}\n"

    # Summarize flagged observations for the prompt
    import pandas as pd
    if flagged:
        obs_df = pd.DataFrame([vars(f) for f in flagged])
        top_params = obs_df['parameter_name'].value_counts().head(10).to_dict()
        top_resources = obs_df['resource_name'].value_counts().head(10).to_dict()
        severity_counts = obs_df['severity'].value_counts().to_dict()
        sample_records = obs_df.head(20)[
            ['record_id','resource_name','parameter_name','observed_value','z_score','severity','note']
        ].to_markdown(index=False)
    else:
        top_params = {}
        top_resources = {}
        severity_counts = {}
        sample_records = "No flagged observations."

    prompt = f"""
You are a domain-aware data quality statistician for agricultural biomass research.

Audit Target: {target_name}
{domain_context}
## Evidently AI Summary
{str(evidently_json)[:3000]}

## Flagged Observation Summary
- Severity counts: {severity_counts}
- Top anomalous parameters: {top_params}
- Top anomalous resources: {top_resources}

## Sample Flagged Records
{sample_records}

Your task:
1. Write a 2-3 paragraph executive summary of the data quality findings.
2. Group the anomalies into up to 50 distinct issues. Each group should represent
   a coherent root cause (e.g., "Unit mismatch in ICP elemental data for grape pomace",
   "Below-detection-limit zeros in XRF analysis").
3. For each group, assign a priority (High/Medium/Low), list affected record IDs
   (up to 10), and recommend a specific action.
"""

    result = client.chat.completions.create(
        model=model,
        api_key=os.environ.get("CBORG_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        api_base=settings.LLM_BASE_URL,
        response_model=SynthesisResult,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=settings.LLM_MAX_TOKENS,
    )
    return result
