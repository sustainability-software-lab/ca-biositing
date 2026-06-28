# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # California County Biomass Production
#
# This notebook generates a choropleth map of total biomass production by county in California, using the LBNL branding theme.

# %%
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.io as pio
from sqlalchemy import text
from pathlib import Path

from ca_biositing.datamodels.database import get_engine
from ca_biositing.visualization.theme import get_lbnl_template_plotly, LBNL_COLORS

# %% [markdown]
# ## 1. Query Data
#
# We query the `mv_biomass_county_production` materialized view to get the total biomass production per county.

# %%
engine = get_engine()

query = """
SELECT
    county,
    SUM(production) as total_production
FROM
    data_portal.mv_biomass_county_production
WHERE
    state = 'California'
GROUP BY
    county
"""

with engine.connect() as conn:
    df_biomass = pd.read_sql(query, conn)

# Clean up county names to match the shapefile (e.g., "Alameda County" -> "Alameda")
df_biomass['county'] = df_biomass['county'].str.replace(' County', '', regex=False).str.lower()

# %% [markdown]
# ## 2. Load Geospatial Data
#
# We load the California counties shapefile/GeoJSON. We'll use the provided `ca_counties.csv` which has FIPS codes, and fetch the actual geometry using `geopandas` or a known URL if needed. Actually, `plotly.express` has built-in US county geometries if we use FIPS codes. Let's get the FIPS codes.

# %%
# Load county FIPS mapping
df_counties = pd.read_csv('data/static/ca_counties.csv')
df_counties['county_name'] = df_counties['county_name'].str.lower()

# Merge biomass data with FIPS codes
df_merged = pd.merge(df_biomass, df_counties, left_on='county', right_on='county_name', how='inner')

# Ensure FIPS is a 5-digit string (State FIPS + County FIPS)
df_merged['fips'] = df_merged['state_fips'].astype(str).str.zfill(2) + df_merged['county_fips'].astype(str).str.zfill(3)

# %% [markdown]
# ## 3. Apply LBNL Branding and Generate Plot
#
# We use Plotly Express to create the choropleth map and apply the LBNL template.

# %%
# Set LBNL template
pio.templates["lbnl"] = get_lbnl_template_plotly()
pio.templates.default = "lbnl"

# Create choropleth map
fig = px.choropleth(
    df_merged,
    geojson="https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json",
    locations='fips',
    color='total_production',
    color_continuous_scale=[
        [0, LBNL_COLORS["secondary"]["light_gray"]],
        [1, LBNL_COLORS["primary"]["teal"]]
    ],
    scope="usa",
    hover_name="county_name",
    hover_data={"fips": False, "total_production": ":,.0f"},
    labels={'total_production': 'Total Production (dt)'},
    title="Total Biomass Production by County in California"
)

fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})

# %% [markdown]
# ## 4. Save Plot
#
# Save the interactive plot as an HTML file in the `exports/plots/` directory.

# %%
output_dir = Path("exports/plots")
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / "ca_county_biomass.html"

fig.write_html(output_path)
print(f"Plot saved to {output_path}")
