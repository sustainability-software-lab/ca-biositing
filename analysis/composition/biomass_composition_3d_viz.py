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

# # Biomass Composition 3D Representation
# This script creates a 3D scatter plot of Glucan vs Xylan vs Lignin content for various biomass resources.
# Data is sourced from `data_portal.mv_biomass_composition`.
# Sweet potato culls are highlighted in orange.

import os
import pandas as pd
import plotly.express as px
import plotly.io as pio
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
        WHERE parameter_name IN ('glucan', 'xylan', 'lignin')
    """)

    with engine.connect() as conn:
        df_raw = pd.read_sql(query, conn)

    if df_raw.empty:
        print("No data found in mv_biomass_composition for glucan, xylan, and lignin.")
        return

    # 2. Process Data
    # Pivot to have one row per resource with glucan, xylan, and lignin columns
    df = df_raw.pivot_table(
        index='resource_name',
        columns='parameter_name',
        values='avg_value',
        aggfunc='mean'
    ).reset_index()

    # Drop rows missing any of the three parameters
    df = df.dropna(subset=['glucan', 'xylan', 'lignin'])

    # Highlight Sweet Potato Culls
    df['is_sweet_potato'] = df['resource_name'].str.contains('sweet potato', case=False)

    # Map colors: Orange for sweet potato, Teal (LBNL primary) for others
    # LBNL orange is 'burnt_orange' or similar in the theme, but user specifically asked for 'orange'
    # We will use LBNL's orange if available, or standard orange.
    orange_color = LBNL_COLORS["secondary"]["orange"] if "orange" in LBNL_COLORS["secondary"] else "orange"
    teal_color = LBNL_COLORS["primary"]["teal"]

    df['color_group'] = df['is_sweet_potato'].map({True: 'Sweet Potato Culls', False: 'Other Resources'})

    # 3. Create Interactive 3D Plot
    fig = px.scatter_3d(
        df,
        x='glucan',
        y='xylan',
        z='lignin',
        color='color_group',
        color_discrete_map={
            'Sweet Potato Culls': orange_color,
            'Other Resources': teal_color
        },
        hover_name='resource_name',
        hover_data={
            'glucan': ':.2f',
            'xylan': ':.2f',
            'lignin': ':.2f',
            'color_group': False # Hide the color group from tooltip
        },
        labels={
            'glucan': 'Glucan (%)',
            'xylan': 'Xylan (%)',
            'lignin': 'Lignin (%)',
            'color_group': 'Category'
        },
        title='Biomass Composition: Glucan vs Xylan vs Lignin (3D)'
    )

    # Improve 3D scene aesthetics
    fig.update_layout(
        scene=dict(
            xaxis_title='Glucan (%)',
            yaxis_title='Xylan (%)',
            zaxis_title='Lignin (%)'
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )

    # 4. Save Export
    os.makedirs("exports/plots/composition", exist_ok=True)
    export_path_html = "exports/plots/composition/biomass_composition_3d.html"
    fig.write_html(export_path_html)
    print(f"Interactive visualization saved to {export_path_html}")

    # Also save a static version for the gallery if possible
    try:
        # For 3D plots, we might need a specific view angle to be informative
        fig.update_layout(scene_camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)))
        export_path_png = "exports/plots/biomass_composition_3d.png"
        fig.write_image(export_path_png, scale=2)
        print(f"Static version saved to {export_path_png}")
    except Exception as e:
        print(f"Could not save static image: {e}")

if __name__ == "__main__":
    main()
