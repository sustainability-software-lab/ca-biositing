import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def audit_temporal_drift(target_name: str, run_dir: str):
    """
    Analyze anomaly trends over time for a target.
    """
    run_path = Path(run_dir)
    csv_path = run_path / f"flagged_{target_name}.csv"

    if not csv_path.exists():
        print(f"⚠️ Temporal drift analysis failed: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)

    if "created_at" not in df.columns:
        print(f"⚠️ Temporal drift analysis failed: 'created_at' column not found in {csv_path}.")
        return

    # Convert to datetime and group by month
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["month"] = df["created_at"].dt.to_period("M")
    monthly_counts = df.groupby("month").size().reset_index(name="anomaly_count")
    monthly_counts["month_str"] = monthly_counts["month"].astype(str)

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(monthly_counts["month_str"], monthly_counts["anomaly_count"], marker='o', linestyle='-', color='#2c3e50')
    plt.title(f"Anomaly Count Over Time: {target_name}")
    plt.xlabel("Month")
    plt.ylabel("Count of Flagged Records")
    plt.xticks(rotation=45)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()

    deep_dive_dir = run_path / "deep_dives"
    deep_dive_dir.mkdir(exist_ok=True)
    plot_path = deep_dive_dir / f"temporal_{target_name}.png"
    plt.savefig(plot_path)
    plt.close()

    # Markdown summary
    summary_table = monthly_counts[["month_str", "anomaly_count"]].to_markdown(index=False)

    report_content = f"""# Temporal Drift Analysis: {target_name}

## Summary Table
{summary_table}

## Anomaly Trend Plot
![Anomaly Trend Plot](temporal_{target_name}.png)
"""

    report_path = deep_dive_dir / f"temporal_{target_name}.md"
    report_path.write_text(report_content)
    print(f"✅ Temporal drift analysis saved to {report_path} and {plot_path}")
