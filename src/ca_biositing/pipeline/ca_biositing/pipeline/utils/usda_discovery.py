import pandas as pd
from typing import List, Optional
from ca_biositing.pipeline.utils.usda_nass_to_pandas import usda_nass_to_df

def discover_top_commodities(
    api_key: str,
    state: str = "CA",
    year: int = 2022,
    top_n: int = 5
) -> List[str]:
    """
    Discover the top commodities by acreage and production for a given state and year.

    This function queries the USDA NASS API for all commodities in a state for a specific year,
    looking at both AREA HARVESTED (ACRES) and PRODUCTION (TONS). It then identifies the top N
    commodities per county for each metric and returns a deduplicated list of these commodity names.

    Args:
        api_key: USDA NASS API key
        state: State abbreviation (default: "CA")
        year: Census year to query (default: 2022)
        top_n: Number of top commodities to keep per county per metric (default: 5)

    Returns:
        List of unique commodity names (api_name format)
    """
    if not api_key:
        print("Warning: No API key provided for commodity discovery.")
        return []

    print(f"Discovering top {top_n} commodities per county for {state} in {year}...")

    discovered_commodities = set()

    # 1. Query for Area Harvested (Acres)
    print("  Querying AREA HARVESTED (ACRES)...")
    df_acres = usda_nass_to_df(
        api_key=api_key,
        state=state,
        year=year,
        source_desc="CENSUS",
        statisticcat_desc="AREA HARVESTED",
        unit_desc="ACRES",
        agg_level_desc="COUNTY"
    )

    if df_acres is not None and not df_acres.empty:
        # Filter out aggregate summary categories (ending in TOTALS)
        df_acres = df_acres[~df_acres['commodity_desc'].str.endswith('TOTALS')]
        # Clean up the Value column (remove commas, handle (D) for undisclosed)
        df_acres['Value_num'] = pd.to_numeric(
            df_acres['Value'].astype(str).str.replace(',', '').str.replace('(D)', '0', regex=False),
            errors='coerce'
        )
        df_acres['Value_num'] = df_acres['Value_num'].fillna(0)

        # Group by county and get top N commodities
        for county, group in df_acres.groupby('county_code'):
            top_acres = group.nlargest(top_n, 'Value_num')
            discovered_commodities.update(top_acres['commodity_desc'].unique())

    # 2. Query for Production (Tons)
    print("  Querying PRODUCTION (TONS)...")
    df_tons = usda_nass_to_df(
        api_key=api_key,
        state=state,
        year=year,
        source_desc="CENSUS",
        statisticcat_desc="PRODUCTION",
        unit_desc="TONS",
        agg_level_desc="COUNTY"
    )

    if df_tons is not None and not df_tons.empty:
        # Filter out aggregate summary categories (ending in TOTALS)
        df_tons = df_tons[~df_tons['commodity_desc'].str.endswith('TOTALS')]
        # Clean up the Value column
        df_tons['Value_num'] = pd.to_numeric(
            df_tons['Value'].astype(str).str.replace(',', '').str.replace('(D)', '0', regex=False),
            errors='coerce'
        )
        df_tons['Value_num'] = df_tons['Value_num'].fillna(0)

        # Group by county and get top N commodities
        for county, group in df_tons.groupby('county_code'):
            top_tons = group.nlargest(top_n, 'Value_num')
            discovered_commodities.update(top_tons['commodity_desc'].unique())

    result = sorted(list(discovered_commodities))
    print(f"Discovered {len(result)} unique top commodities across all counties.")
    return result
