import pandas as pd
from pathlib import Path
import os

def audit_provider_deep_dive(provider_codename: str, run_dir: str):
    """
    Deep-dive into anomalies for a specific provider.
    """
    run_path = Path(run_dir)
    csv_path = run_path / "flagged_mv_biomass_composition_extended.csv"

    if not csv_path.exists():
        print(f"⚠️ Provider deep-dive failed: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)

    # Filter by provider
    if "provider_codename" not in df.columns:
        print(f"⚠️ Provider deep-dive failed: 'provider_codename' column not in {csv_path}")
        return

    provider_df = df[df["provider_codename"] == provider_codename]

    if provider_df.empty:
        print(f"ℹ️ No flagged records found for provider '{provider_codename}'.")
        # Still create a report saying no anomalies found
        report_content = f"# Provider Deep-Dive: {provider_codename}\n\nNo anomalies found for this provider in this audit run."
    else:
        # Parameter breakdown
        param_breakdown = provider_df["parameter_name"].value_counts().to_markdown()

        # Severity distribution
        severity_dist = provider_df["severity"].value_counts().to_markdown()

        # Top anomalies (by Z-score)
        top_anomalies = provider_df.sort_values(by="z_score", ascending=False).head(10)[
            ["record_id", "resource_name", "parameter_name", "observed_value", "z_score", "severity"]
        ].to_markdown(index=False)

        report_content = f"""# Provider Deep-Dive: {provider_codename}

## Summary
- **Total Flagged Observations:** {len(provider_df)}

## Parameter Breakdown
{param_breakdown}

## Severity Distribution
{severity_dist}

## Top 10 Anomalies (by Z-score)
{top_anomalies}
"""

    # Save report
    deep_dive_dir = run_path / "deep_dives"
    deep_dive_dir.mkdir(exist_ok=True)
    report_path = deep_dive_dir / f"provider_{provider_codename}.md"
    report_path.write_text(report_content)
    print(f"✅ Provider deep-dive report saved to {report_path}")
