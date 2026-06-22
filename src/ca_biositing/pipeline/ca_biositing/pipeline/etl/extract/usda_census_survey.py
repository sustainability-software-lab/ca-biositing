"""
USDA Census and Survey Data Extraction.

This module extracts agricultural census and survey data from the USDA NASS
Quick Stats API for all 58 California counties.
The county list is driven by `data/static/ca_counties.csv`.

Data includes:
- Census data (every 5 years): Complete agricultural census
- Survey data (annual): Preliminary and final agricultural estimates
The USDA API provides access to decades of historical data across many
commodities and regions.
For more information: https://quickstats.nass.usda.gov/api
"""

from typing import Optional
import os
from pathlib import Path
import pandas as pd
from prefect import task, get_run_logger

# Use absolute imports that work both locally and in Docker
try:
    # Try absolute import first (works in Docker)
    from ca_biositing.pipeline.utils.usda_nass_to_pandas import usda_nass_to_df
    from ca_biositing.pipeline.utils.fetch_mapped_commodities import get_mapped_commodity_ids
    from ca_biositing.pipeline.utils.usda_discovery import discover_top_commodities
    from ca_biositing.pipeline.utils.seed_commodity_mappings import ensure_commodities_exist
    from ca_biositing.pipeline.utils.engine import get_engine
except ImportError:
    # Fallback for local testing
    from src.ca_biositing.pipeline.ca_biositing.pipeline.utils.usda_nass_to_pandas import usda_nass_to_df
    from src.ca_biositing.pipeline.ca_biositing.pipeline.utils.fetch_mapped_commodities import get_mapped_commodity_ids
    from src.ca_biositing.pipeline.ca_biositing.pipeline.utils.usda_discovery import discover_top_commodities
    from src.ca_biositing.pipeline.ca_biositing.pipeline.utils.seed_commodity_mappings import ensure_commodities_exist
    from src.ca_biositing.pipeline.ca_biositing.pipeline.utils.engine import get_engine

# --- CONFIGURATION ---
# USDA API Key - loaded from environment variable
# To set this, add to resources/docker/.env:
#   USDA_NASS_API_KEY=your_api_key_here
# Get your free API key at: https://quickstats.nass.usda.gov/api
USDA_API_KEY = os.getenv("USDA_NASS_API_KEY", "")

# State code to query (using USDA state abbreviation)
# CA = California
STATE = "CA"

# Optional: Filter by specific year. Set to None for all available years.
YEAR = None

# Optional: Filter by commodity (e.g., "CORN", "ALMONDS", "WHEAT")
# Leave as None to get all commodities
COMMODITY = None

def _load_ca_counties() -> list:
    """
    Load all California counties from the static CSV file.
    Returns a sorted list of (county_fips, county_name) tuples.
    County FIPS codes are 3-digit zero-padded strings matching the USDA API county_code param.
    """
    # Try cwd-relative first (works in Docker where WORKDIR=/app)
    cwd_path = Path.cwd() / "data" / "static" / "ca_counties.csv"
    # Fallback: relative to this file (works in local dev)
    # The file is at src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/usda_census_survey.py
    # So parents are: 0:extract, 1:etl, 2:pipeline, 3:ca_biositing, 4:pipeline, 5:ca_biositing, 6:src, 7:root
    try:
        file_path = Path(__file__).resolve().parents[7] / "data" / "static" / "ca_counties.csv"
    except IndexError:
        # If path is shorter than expected, just use cwd as last resort
        file_path = cwd_path

    csv_path = cwd_path if cwd_path.exists() else file_path
    if not csv_path.exists():
        raise FileNotFoundError(
            f"ca_counties.csv not found. Tried:\n  {cwd_path}\n  {file_path}"
        )

    df = pd.read_csv(csv_path, dtype=str)
    counties = sorted(zip(df["county_fips"], df["county_name"]))
    return counties


@task
def extract() -> Optional[pd.DataFrame]:
    """
    Extracts USDA data ONLY for commodities mapped in resource_usda_commodity_map
    for all California counties.
    This allows adding new crops by updating the database, no code changes needed.
    """
    logger = get_run_logger()
    logger.info("🔵 [USDA Extract] Starting...")

    # 1. Discover top commodities dynamically
    logger.info("🔵 [USDA Extract] Discovering top commodities...")
    top_commodities = discover_top_commodities(api_key=USDA_API_KEY, state=STATE, year=YEAR, top_n=5)

    # 2. Ensure discovered commodities exist in the database
    if top_commodities:
        logger.info(f"🔵 [USDA Extract] Ensuring {len(top_commodities)} discovered commodities exist in DB...")
        engine = get_engine()
        ensure_commodities_exist(engine, top_commodities)

    # 3. Get user-defined commodity names from database
    mapped_commodity_ids = get_mapped_commodity_ids()

    # 4. Combine lists
    commodity_ids = list(set((mapped_commodity_ids or []) + top_commodities))

    logger.info(f"🔵 [USDA Extract] Got {len(commodity_ids) if commodity_ids else 0} total commodities to extract: {commodity_ids}")

    if not commodity_ids:
        logger.error(
            "No commodity mappings found. This could mean:\n"
            "1. Resource and primary_ag_product tables are empty (run full ETL pipeline first)\n"
            "2. The CSV mapping file is missing or corrupted\n"
            "3. Auto-seeding failed (check logs above for details)"
        )
        return None

    ca_counties = _load_ca_counties()
    logger.info(f"Loaded {len(ca_counties)} CA counties from ca_counties.csv")
    logger.info(f"Extracting USDA data for {len(commodity_ids)} commodities for all counties in a single query per commodity...")
    logger.info("Note: Optimized to 1 query per commodity instead of 1 per county/commodity")

    # Call utility with commodity names, without county_code to get all counties at once
    # This is much faster and stays well within rate limits
    raw_df = usda_nass_to_df(
        api_key=USDA_API_KEY,
        state=STATE,
        year=YEAR,
        commodity_ids=commodity_ids,  # Database-driven commodity names
        county_code=None  # Get all counties at once
    )

    if raw_df is None or raw_df.empty:
        logger.error("No data retrieved from USDA NASS API. Aborting.")
        return None

    # Filter for the 58 California counties we care about (in case API returns others)
    # The API 'county_code' is 3-digits.
    valid_county_fips = {fips for fips, name in ca_counties}
    initial_count = len(raw_df)
    raw_df = raw_df[raw_df["county_code"].isin(valid_county_fips)]
    filtered_count = len(raw_df)

    logger.info(f"Filtered {initial_count} records down to {filtered_count} records for valid CA counties")

    # Calculate how many counties actually returned data
    counties_with_data = raw_df["county_code"].nunique()

    logger.info(f"Successfully extracted {len(raw_df)} total records from USDA NASS API across {counties_with_data} of {len(ca_counties)} counties.")

    # 🔍 DIAGNOSTIC: Save raw extracted data for inspection (OPTIONAL - uncomment to enable)
    # Uncomment the following block to generate debug CSV files for troubleshooting
    """
    try:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_csv_path = f"/app/data/usda_raw_extracted_debug_{timestamp}.csv"
        raw_df.to_csv(debug_csv_path, index=False)
        logger.info(f"💾 Debug: Raw extracted data saved to {debug_csv_path}")
    """
    logger.info(f"📊 Raw data shape: {raw_df.shape}")
    logger.info(f"📊 Columns: {list(raw_df.columns)}")

    # Show what commodities and statistics are in the raw data
    if 'commodity_desc' in raw_df.columns:
        commodities = raw_df['commodity_desc'].unique()
        logger.info(f"🌾 Commodities in raw data: {len(commodities)}")
        for comm in sorted(commodities):
            count = len(raw_df[raw_df['commodity_desc'] == comm])
            logger.info(f"  {comm}: {count} records")

        if 'short_desc' in raw_df.columns:
            statistics = raw_df['short_desc'].str.extract(r'- (\w+(?:\s+\w+)?)\s*$')[0].unique()
            logger.info(f"📈 Statistics types in raw data: {len([s for s in statistics if s])}")

    return raw_df
