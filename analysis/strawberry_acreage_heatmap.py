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
# # California Strawberry Acreage Heatmap (2022)
#
# This notebook generates a choropleth heatmap of strawberry acreage (bearing and non-bearing)
# for California counties using data from the USDA Census (2022).
# It utilizes the LBNL branding theme for consistency.

# %%
import os
import pandas as pd
import plotly.express as px
import plotly.io as pio
from pathlib import Path
from sqlalchemy import text

from ca_biositing.datamodels.database import get_engine
from ca_biositing.visualization.theme import get_lbnl_template_plotly, LBNL_COLORS

# %% [markdown]
# ## 1. Query Data
#
# We query the `ca_biositing.usda_census_view` materialized view to get strawberry acreage.
# We include both "area bearing" and "area non-bearing" for the 2022 census year.

# %%
# Ensure POSTGRES_HOST is set for local execution if not in environment
if "POSTGRES_HOST" not in os.environ:
    os.environ["POSTGRES_HOST"] = "localhost"

engine = get_engine()

query = """
SELECT
    geoid,
    SUM(value) as total_strawberry_acres
FROM
    ca_biositing.usda_census_view
WHERE
    usda_crop = 'strawberries'
    AND parameter IN ('area bearing', 'area non-bearing')
    AND record_year = 2022
GROUP BY
    geoid
"""

with engine.connect() as conn:
    df_strawberry = pd.read_sql(text(query), conn)

# %% [markdown]
# ## 2. Load County Names
#
# Load the static California counties mapping to get county names for display.

# %%
df_counties = pd.read_csv('data/static/ca_counties.csv')
df_counties['fips'] = df_counties['state_fips'].astype(str).str.zfill(2) + df_counties['county_fips'].astype(str).str.zfill(3)

# Merge with strawberry data
df_merged = pd.merge(df_strawberry, df_counties[['fips', 'county_name']], left_on='geoid', right_on='fips', how='right')
df_merged['total_strawberry_acres'] = df_merged['total_strawberry_acres'].fillna(0)

# %% [markdown]
# ## 3. Apply LBNL Branding and Generate Plot
#
# Create the choropleth map using Plotly Express and the LBNL template.

# %%
# Set LBNL template
pio.templates["lbnl"] = get_lbnl_template_plotly()
pio.templates.default = "lbnl"

# Create choropleth map
fig = px.choropleth(
    df_merged,
    geojson="https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json",
    locations='geoid',
    color='total_strawberry_acres',
    color_continuous_scale=[
        [0, LBNL_COLORS["secondary"]["light_gray"]],
        [1, LBNL_COLORS["primary"]["teal"]]
    ],
    scope="usa",
    hover_name="county_name",
    hover_data={"geoid": False, "total_strawberry_acres": ":,.2f"},
    labels={'total_strawberry_acres': 'Total Acres (Bearing + Non-Bearing)'},
    title="Strawberry Acreage by California County (USDA Census 2022)"
)

fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(
    margin={"r":0,"t":60,"l":0,"b":0},
    title_x=0.5,
    title_font_size=20
)

# %% [markdown]
# ## 4. Save Plot
#
# Save the interactive plot as an HTML file in the `exports/plots/` directory.

# %%
output_dir = Path("exports/plots")
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / "strawberry_acreage_heatmap.html"

fig.write_html(output_path)
print(f"Plot saved to {output_path}")
