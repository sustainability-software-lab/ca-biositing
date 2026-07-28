import pandas as pd
from pathlib import Path
import glob

def audit_resource_deep_dive(resource_name: str, run_dir: str):
    """
    Cross-target deep-dive for a specific resource.
    """
    run_path = Path(run_dir)
    flagged_files = list(run_path.glob("flagged_*.csv"))

    if not flagged_files:
        print(f"⚠️ Resource deep-dive failed: No flagged CSV files found in {run_dir}.")
        return

    all_flagged = []
    for f in flagged_files:
        df = pd.read_csv(f)
        df["source_target"] = f.stem.replace("flagged_", "")
        if "resource_name" in df.columns:
            resource_df = df[df["resource_name"].str.lower() == resource_name.lower()]
            all_flagged.append(resource_df)

    if not all_flagged:
        print(f"ℹ️ No flagged records found for resource '{resource_name}'.")
        report_content = f"# Resource Deep-Dive: {resource_name}\n\nNo anomalies found for this resource in this audit run."
    else:
        full_df = pd.concat(all_flagged)

        if full_df.empty:
            report_content = f"# Resource Deep-Dive: {resource_name}\n\nNo anomalies found for this resource in this audit run."
        else:
            # Breakdown by source target
            target_breakdown = full_df["source_target"].value_counts().to_markdown()

            # Parameter breakdown
            param_breakdown = full_df["parameter_name"].value_counts().to_markdown()

            # Top anomalies
            top_anomalies = full_df.sort_values(by="z_score", ascending=False).head(15)[
                ["source_target", "record_id", "parameter_name", "observed_value", "z_score", "severity"]
            ].to_markdown(index=False)

            report_content = f"""# Resource Deep-Dive: {resource_name}

## Summary
- **Total Flagged Observations:** {len(full_df)}
- **Targets Impacted:** {full_df['source_target'].nunique()}

## Target Breakdown
{target_breakdown}

## Parameter Breakdown
{param_breakdown}

## Top 15 Cross-Target Anomalies
{top_anomalies}
"""

    # Save report
    deep_dive_dir = run_path / "deep_dives"
    deep_dive_dir.mkdir(exist_ok=True)
    # Sanitize resource name for filename
    safe_name = resource_name.replace(" ", "_").lower()
    report_path = deep_dive_dir / f"resource_{safe_name}.md"
    report_path.write_text(report_content)
    print(f"✅ Resource deep-dive report saved to {report_path}")
