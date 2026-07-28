import pandas as pd
from pathlib import Path

def audit_analysis_type_review(analysis_type: str, run_dir: str):
    """
    Review systemic issues for a specific analysis type.
    """
    run_path = Path(run_dir)
    csv_path = run_path / "flagged_mv_biomass_composition.csv"

    if not csv_path.exists():
        # Try extended if normal not found
        csv_path = run_path / "flagged_mv_biomass_composition_extended.csv"

    if not csv_path.exists():
        print(f"⚠️ Analysis type review failed: No composition flagged CSVs found in {run_dir}.")
        return

    df = pd.read_csv(csv_path)

    if "analysis_type" not in df.columns:
        print(f"⚠️ Analysis type review failed: 'analysis_type' column not found in {csv_path}.")
        return

    # Filter by analysis type (case insensitive)
    type_df = df[df["analysis_type"].str.lower() == analysis_type.lower()]

    if type_df.empty:
        report_content = f"# Analysis Type Review: {analysis_type}\n\nNo systemic issues found for this analysis type."
    else:
        # Resource breakdown
        resource_breakdown = type_df["resource_name"].value_counts().to_markdown()

        # Parameter breakdown
        param_breakdown = type_df["parameter_name"].value_counts().to_markdown()

        # Top anomalies
        top_anomalies = type_df.sort_values(by="z_score", ascending=False).head(10)[
            ["record_id", "resource_name", "parameter_name", "observed_value", "z_score", "severity"]
        ].to_markdown(index=False)

        report_content = f"""# Analysis Type Review: {analysis_type}

## Summary
- **Total Flagged Observations:** {len(type_df)}
- **Resources Impacted:** {type_df['resource_name'].nunique()}

## Resource Impact Breakdown
{resource_breakdown}

## Parameter Breakdown
{param_breakdown}

## Top 10 Anomalies
{top_anomalies}
"""

    # Save report
    deep_dive_dir = run_path / "deep_dives"
    deep_dive_dir.mkdir(exist_ok=True)
    report_path = deep_dive_dir / f"analysis_{analysis_type.lower()}.md"
    report_path.write_text(report_content)
    print(f"✅ Analysis type review report saved to {report_path}")
