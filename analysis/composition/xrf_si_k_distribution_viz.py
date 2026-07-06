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

# # XRF Si and K Elemental Distribution
# This script visualizes the distribution of Si (Silicon) and K (Potassium) concentrations
# from XRF analysis using data from the `ca_biositing.analysis_data_view`.
# It creates interactive violin plots for these two elements to show variance and distribution.

import os
import pandas as pd
import plotly.express as px
import plotly.io as pio
from sqlalchemy import text
import plotly.graph_objects as go

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
    # Querying XRF data specifically for Si and K
    query = text("""
        SELECT
            resource,
            parameter as element,
            value,
            unit
        FROM ca_biositing.analysis_data_view
        WHERE record_type ILIKE '%xrf%'
        AND parameter IN ('si', 'k')
        AND value IS NOT NULL
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    if df.empty:
        print("No XRF data for Si or K found in ca_biositing.analysis_data_view.")
        return

    # Identify unique unit (assuming consistent for the plot)
    unit = df['unit'].iloc[0] if not df.empty else "ppm"

    # 2. Create Interactive Violin Plot using Graph Objects for finer control over point colors
    df['element'] = df['element'].str.upper()

    # Define highlight logic
    highlight_resources = ['rice hulls', 'wheat straw']
    NEON_GREEN = "#39FF14"

    fig = go.Figure()

    for element, color in [("SI", LBNL_COLORS["primary"]["teal"]), ("K", LBNL_COLORS["primary"]["gold"])]:
        el_df = df[df['element'] == element]

        # Add the violin background and box
        fig.add_trace(go.Violin(
            x=el_df['element'],
            y=el_df['value'],
            name=element,
            box_visible=True,
            meanline_visible=True,
            line_color=color,
            fillcolor=color,
            opacity=0.4,
            points=False, # Points added separately for control
            showlegend=True
        ))

        # Add normal points
        normal_df = el_df[~el_df['resource'].isin(highlight_resources)]
        fig.add_trace(go.Box(
            x=normal_df['element'],
            y=normal_df['value'],
            name=element,
            boxpoints='all',
            jitter=0.5,
            pointpos=0,
            fillcolor='rgba(0,0,0,0)',
            line=dict(color='rgba(0,0,0,0)'), # Hide the box, just show points
            marker=dict(
                color=color,
                opacity=0.5,
                size=5
            ),
            showlegend=False,
            hoverinfo='none'
        ))

        # Add highlight points
        highlight_df = el_df[el_df['resource'].isin(highlight_resources)]
        fig.add_trace(go.Box(
            x=highlight_df['element'],
            y=highlight_df['value'],
            name=element,
            boxpoints='all',
            jitter=0.5,
            pointpos=0,
            fillcolor='rgba(0,0,0,0)',
            line=dict(color='rgba(0,0,0,0)'),
            marker=dict(
                color=NEON_GREEN,
                opacity=1.0,
                size=10,
                line=dict(width=1.5, color="black")
            ),
            text=highlight_df['resource'],
            showlegend=False,
            hovertemplate="<b>%{text}</b><br>Value: %{y} " + unit + "<extra></extra>"
        ))

    # Update layout for better readability and remove grid lines
    fig.update_layout(
        title="Distribution of XRF Si and K Elemental Analysis",
        xaxis_title="Element (Silicon vs Potassium)",
        yaxis_title=f"Measured Value ({unit})",
        legend_title="Element",
        showlegend=True,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
        template="lbnl"
    )

    # Add a single legend entry for the highlight
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode='markers',
        marker=dict(
            size=10,
            color=NEON_GREEN,
            line=dict(width=1, color="black")
        ),
        showlegend=True,
        name='Rice Hulls / Wheat Straw'
    ))

    # 3. Save Export
    os.makedirs("exports/plots/composition", exist_ok=True)
    export_path_html = "exports/plots/composition/xrf_si_k_distribution_viz.html"
    fig.write_html(export_path_html)

    # Also save a static version for the gallery
    try:
        export_path_png = "exports/plots/xrf_si_k_distribution_viz.png"
        fig.write_image(export_path_png, scale=2)
        print(f"Static version saved to {export_path_png}")
    except Exception as e:
        print(f"Could not save static image: {e}")

    print(f"Visualization saved to {export_path_html}")

if __name__ == "__main__":
    main()
