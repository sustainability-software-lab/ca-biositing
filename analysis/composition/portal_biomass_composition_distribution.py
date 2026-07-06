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

# # Portal Biomass Composition Distribution
# This script visualizes the distribution of key biomass composition parameters
# (xylan, glucan, arabinan, lignin, moisture, ash solids, volatile solids)
# specifically using data from the `data_portal.mv_biomass_composition` view.
# This view contains aggregated statistics (avg, min, max) per resource and location.

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
    # Note: These are expected to be in the 'parameter_name' column
    target_parameters = [
        'xylan', 'glucan', 'arabinan', 'lignin',
        'moisture', 'ash solids', 'volatile solids'
    ]

    # Querying the relevant composition data from the data_portal schema
    query = text("""
        SELECT
            resource_name,
            parameter_name,
            avg_value,
            unit,
            analysis_type,
            county
        FROM data_portal.mv_biomass_composition
        WHERE parameter_name IN :params
        AND avg_value IS NOT NULL
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"params": tuple(target_parameters)})

    if df.empty:
        print("No matching composition data found in data_portal.mv_biomass_composition.")
        return

    # Clean up parameter names for display
    df['parameter_name'] = df['parameter_name'].str.title()

    # 2. Prepare Labels with Counts
    # Calculate counts per parameter
    counts = df.groupby('parameter_name')['resource_name'].nunique().reset_index()
    counts.columns = ['parameter_name', 'count']

    # Create a mapping for updated x-axis labels
    label_map = {row['parameter_name']: f"{row['parameter_name']}<br>(n={row['count']})" for _, row in counts.iterrows()}
    df['parameter_labeled'] = df['parameter_name'].map(label_map)

    # Order for the labeled parameters
    ordered_labels = [label_map[p.title()] for p in target_parameters if p.title() in label_map]

    # 3. Create Interactive Violin Plot
    # We'll visualize the distribution of 'avg_value' from the materialized view
    fig = px.violin(
        df,
        y="avg_value",
        x="parameter_labeled",
        color="parameter_name",
        hover_name="resource_name",
        box=True,           # Show box plot inside violin
        points="all",       # Show all data points (each point is an aggregate from the MV)
        hover_data=["unit", "analysis_type", "county"],
        labels={
            "avg_value": "Average Value (%)",
            "parameter_labeled": "Composition Parameter",
            "resource_name": "Biomass Resource",
            "unit": "Unit",
            "analysis_type": "Analysis Type",
            "county": "County"
        },
        title="Distribution of Biomass Composition (Data Portal Aggregates)",
        category_orders={"parameter_labeled": ordered_labels}
    )

    # 4. Update Traces for Styling
    fig.update_traces(
        marker=dict(
            size=12,
            opacity=0.5,
            line=dict(width=1, color='white')
        )
    )

    # 5. Update layout for better readability
    fig.update_layout(
        xaxis_title="Parameter",
        yaxis_title="Average Value (%)",
        showlegend=False,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False)
    )

    # 3. Save Export
    os.makedirs("exports/plots/composition", exist_ok=True)
    export_path_html = "exports/plots/composition/portal_biomass_composition_distribution.html"
    fig.write_html(export_path_html)

    # Also save a static version for the gallery
    try:
        export_path_png = "exports/plots/portal_biomass_composition_distribution.png"
        fig.write_image(export_path_png, scale=2)
        print(f"Static version saved to {export_path_png}")
    except Exception as e:
        print(f"Could not save static image: {e}")

    print(f"Visualization saved to {export_path_html}")

if __name__ == "__main__":
    main()
