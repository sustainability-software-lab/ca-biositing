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

# # XRF Analysis Data Distribution
# This script visualizes the distribution of elemental concentrations from XRF analysis
# using data from the `ca_biositing.analysis_data_view`.
# It creates interactive violin plots for each element to show variance and distribution,
# with tooltips highlighting the specific biomass resource.

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
    # Querying all XRF analysis data
    query = text("""
        SELECT
            resource,
            parameter as element,
            value,
            unit
        FROM ca_biositing.analysis_data_view
        WHERE record_type ILIKE '%xrf%'
        AND value IS NOT NULL
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    if df.empty:
        print("No XRF data found in ca_biositing.analysis_data_view.")
        return

    # Clean up element names (capitalize only the first letter)
    df['element'] = df['element'].str.capitalize()

    # Identify unique unit (assuming consistent for the plot)
    unit = df['unit'].iloc[0] if not df.empty else "ppm"

    # 2. Create Interactive Violin Plot
    # We'll use a violin plot with points to see the individual distributions
    fig = px.violin(
        df,
        y="value",
        x="element",
        color="element",
        box=True, # Show box plot inside violin
        points="all", # Show all data points
        hover_data=["resource", "unit"],
        labels={
            "value": f"Concentration ({unit})",
            "element": "Element",
            "resource": "Biomass Resource",
            "unit": "Unit"
        },
        title="Distribution of XRF Elemental Analysis Data"
    )

    # Update layout for better readability and remove grid lines
    fig.update_layout(
        xaxis_title="Element",
        yaxis_title=f"Measured Value ({unit})",
        legend_title="Element",
        showlegend=False,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False)
    )

    # 3. Save Export
    os.makedirs("exports/plots/composition", exist_ok=True)
    export_path_html = "exports/plots/composition/xrf_distribution_viz.html"
    fig.write_html(export_path_html)

    # Also save a static version for the gallery
    try:
        export_path_png = "exports/plots/xrf_distribution_viz.png"
        fig.write_image(export_path_png, scale=2)
        print(f"Static version saved to {export_path_png}")
    except Exception as e:
        print(f"Could not save static image: {e}")

    print(f"Visualization saved to {export_path_html}")

if __name__ == "__main__":
    main()
