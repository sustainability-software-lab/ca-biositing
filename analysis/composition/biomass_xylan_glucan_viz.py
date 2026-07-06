# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# # Biomass Composition: Xylan vs Glucan
# This script visualizes the relationship between Xylan and Glucan content across various biomass resources
# using data from the `data_portal.mv_biomass_composition` view.
# Almond-based resources are highlighted in gold with explicit labels.

import os
import pandas as pd
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
from sqlalchemy import text

# Force localhost for local database access
os.environ["POSTGRES_HOST"] = "localhost"

from ca_biositing.datamodels.database import get_engine
from ca_biositing.visualization.theme import get_lbnl_template_plotly, LBNL_COLORS

# Set LBNL Plotly Theme
pio.templates["lbnl"] = get_lbnl_template_plotly()
pio.templates.default = "lbnl"

def main():
    # 1. Query Data
    engine = get_engine()
    query = text("""
        SELECT resource_name, parameter_name, avg_value
        FROM data_portal.mv_biomass_composition
        WHERE parameter_name IN ('glucan', 'xylan')
    """)

    with engine.connect() as conn:
        df_raw = pd.read_sql(query, conn)

    if df_raw.empty:
        print("No data found in mv_biomass_composition for glucan and xylan.")
        return

    # 2. Process Data
    # Pivot to have one row per resource with glucan and xylan columns
    df = df_raw.pivot_table(
        index='resource_name',
        columns='parameter_name',
        values='avg_value',
        aggfunc='mean'
    ).reset_index()

    # Drop rows missing either parameter
    df = df.dropna(subset=['glucan', 'xylan'])

    # Identify almond-based resources
    df['is_almond'] = df['resource_name'].str.contains('almond', case=False)

    # Define colors and sizes
    # Almond resources: Gold, Other: Teal
    df['color'] = df['is_almond'].map({True: LBNL_COLORS["primary"]["gold"], False: LBNL_COLORS["primary"]["teal"]})
    df['size'] = df['is_almond'].map({True: 15, False: 8})

    # 3. Create Interactive Plot
    fig = px.scatter(
        df,
        x='glucan',
        y='xylan',
        color='is_almond',
        color_discrete_map={True: LBNL_COLORS["primary"]["gold"], False: LBNL_COLORS["primary"]["teal"]},
        size='size',
        hover_name='resource_name',
        labels={
            'glucan': 'Glucan Content (avg_value)',
            'xylan': 'Xylan Content (avg_value)',
            'is_almond': 'Almond Resource'
        },
        title='Biomass Composition: Xylan vs Glucan'
    )

    # Add explicit labels for almond resources
    almond_df = df[df['is_almond']]
    for _, row in almond_df.iterrows():
        fig.add_annotation(
            x=row['glucan'],
            y=row['xylan'],
            text=row['resource_name'],
            showarrow=True,
            arrowhead=1,
            ax=0,
            ay=-30,
            font=dict(color=LBNL_COLORS["primary"]["deep_blue"], size=10)
        )

    # 4. Save Export
    os.makedirs("exports/plots/composition", exist_ok=True)
    export_path = "exports/plots/composition/biomass_xylan_glucan.html"
    fig.write_html(export_path)

    # Also save a static version for the gallery
    try:
        fig.write_image("exports/plots/biomass_xylan_glucan.png", scale=2)
        print("Static version saved to exports/plots/biomass_xylan_glucan.png")
    except Exception as e:
        print(f"Could not save static image: {e}")

    print(f"Visualization saved to {export_path}")

if __name__ == "__main__":
    main()
