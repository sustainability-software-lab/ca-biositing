# audit/skills/statistical_profiling.py
import pandas as pd
from pathlib import Path
from typing import Dict
from ydata_profiling import ProfileReport

def run_statistical_profiling(
    df: pd.DataFrame,
    target_name: str,
    output_dir: Path,
) -> Dict:
    """
    Runs ydata-profiling on the target dataframe and saves the HTML report.
    Returns the summary dictionary.
    """
    profile = ProfileReport(df, title=f"Data Profile: {target_name}", minimal=True)

    output_path = output_dir / f"{target_name}.html"
    profile.to_file(output_path)

    return profile.get_description()
