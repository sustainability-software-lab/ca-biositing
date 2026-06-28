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

# # Biomass Composition Distribution
# This script visualizes the distribution of key biomass composition parameters
# (xylan, glucan, arabinan, lignin, moisture, ash solids, volatile solids)
# using data from the `ca_biositing.analysis_data_view`.
# It creates interactive violin plots to show variance and distribution across different resources.

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

    # Define the parameters we are interested in
    target_parameters = [
        'xylan', 'glucan', 'arabinan', 'lignin',
        'moisture', 'ash solids', 'volatile solids'
    ]

    # Querying the relevant composition data
    # Note: parameter names in the view are already lowercased or mapped (like "ash" -> "ash solids")
    query = text("""
        SELECT
            resource,
            parameter,
            value,
            unit,
            record_type
        FROM ca_biositing.analysis_data_view
        WHERE parameter IN :params
        AND value IS NOT NULL
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"params": tuple(target_parameters)})

    if df.empty:
        print("No matching composition data found in ca_biositing.analysis_data_view.")
        return

    # Clean up parameter names for display
    df['parameter'] = df['parameter'].str.title()

    # 2. Prepare Labels with Counts
    # Calculate counts per parameter
    counts = df.groupby('parameter')['resource'].nunique().reset_index()
    counts.columns = ['parameter', 'count']

    # Create a mapping for updated x-axis labels
    label_map = {row['parameter']: f"{row['parameter']}<br>(n={row['count']})" for _, row in counts.iterrows()}
    df['parameter_labeled'] = df['parameter'].map(label_map)

    # Order for the labeled parameters
    ordered_labels = [label_map[p.title()] for p in target_parameters if p.title() in label_map]

    # 3. Create Interactive Violin Plot
    # We'll create a plot where each parameter has its own violin
    fig = px.violin(
        df,
        y="value",
        x="parameter_labeled",
        color="parameter",
        hover_name="resource",
        box=True,           # Show box plot inside violin
        points="all",       # Show all data points
        hover_data=["unit", "record_type"],
        labels={
            "value": "Measured Value",
            "parameter_labeled": "Composition Parameter",
            "resource": "Biomass Resource",
            "unit": "Unit",
            "record_type": "Analysis Type"
        },
        title="Distribution of Biomass Composition Data",
        category_orders={"parameter_labeled": ordered_labels}
    )

    # 4. Update Traces for Styling
    fig.update_traces(
        marker=dict(
            size=24,
            opacity=0.5,
            line=dict(width=1, color='white')
        )
    )

    # 5. Update layout for better readability
    fig.update_layout(
        xaxis_title="Parameter",
        yaxis_title="Value (%)",
        showlegend=False,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False)
    )

    # 3. Save Export
    os.makedirs("exports/plots", exist_ok=True)
    export_path_html = "exports/plots/biomass_composition_distribution.html"
    fig.write_html(export_path_html)

    # Also save a static version for the gallery
    try:
        export_path_png = "exports/plots/biomass_composition_distribution.png"
        fig.write_image(export_path_png, scale=2)
        print(f"Static version saved to {export_path_png}")
    except Exception as e:
        print(f"Could not save static image: {e}")

    print(f"Visualization saved to {export_path_html}")

if __name__ == "__main__":
    main()
