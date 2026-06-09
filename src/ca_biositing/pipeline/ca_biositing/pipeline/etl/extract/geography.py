"""
ETL Extract: Geography (CA Counties)
"""

import os
import pandas as pd
from prefect import task, get_run_logger
from pathlib import Path

@task(name="extract_ca_counties")
def extract_ca_counties() -> pd.DataFrame:
    """
    Reads the static CA counties CSV.
    """
    logger = get_run_logger()

    # Path is relative to the workspace root
    csv_path = Path("data/static/ca_counties.csv")

    if not csv_path.exists():
        msg = f"Geography CSV not found at {csv_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    logger.info(f"Reading geography data from {csv_path}")
    df = pd.read_csv(csv_path, dtype={"geoid": str, "state_fips": str, "county_fips": str})

    return df
