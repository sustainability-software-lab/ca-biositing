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

# # Sample Lineage Flow Visualization
# This script visualizes the flow of samples from Resource -> Field Sample -> Prepared Sample -> Analysis.
# Flows are color-coded by Primary Ag Product.

import os
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import text

# Force localhost for local database access
os.environ["POSTGRES_HOST"] = "localhost"

from ca_biositing.datamodels.database import get_engine
from ca_biositing.visualization.theme import LBNL_PALETTE

def main():
    # 1. Query Data
    engine = get_engine()

    # Define the record types and their human-readable names
    record_types = {
        'compositional_record': 'Compositional',
        'proximate_record': 'Proximate',
        'ultimate_record': 'Ultimate',
        'icp_record': 'ICP',
        'xrf_record': 'XRF',
        'xrd_record': 'XRD',
        'calorimetry_record': 'Calorimetry',
        'pretreatment_record': 'Pretreatment',
        'fermentation_record': 'Fermentation',
        'gasification_record': 'Gasification'
    }

    union_queries = []
    for table, label in record_types.items():
        union_queries.append(f"""
        SELECT
            pap.name as primary_ag_product,
            res.name as resource_name,
            fs.name as field_sample_name,
            ps.name as prepared_sample_name,
            '{label}' as analysis_type
        FROM {table} rec
        JOIN prepared_sample ps ON rec.prepared_sample_id = ps.id
        JOIN field_sample fs ON ps.field_sample_id = fs.id
        JOIN resource res ON fs.resource_id = res.id
        JOIN primary_ag_product pap ON res.primary_ag_product_id = pap.id
        """)

    query = text(" UNION ALL ".join(union_queries))

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    if df.empty:
        print("No sample lineage data found.")
        return

    # 2. Prepare Data for Sankey
    # Levels: Resource -> Field Sample -> Prepared Sample -> Analysis
    levels = ['resource_name', 'field_sample_name', 'prepared_sample_name', 'analysis_type']

    # Prefix nodes with level name to avoid collisions
    nodes = []
    for i, level in enumerate(levels):
        unique_vals = df[level].unique()
        for val in unique_vals:
            nodes.append(f"{level}_{val}")

    node_map = {node: i for i, node in enumerate(nodes)}

    sources = []
    targets = []
    values = []
    link_colors = []
    link_custom_data = [] # For link tooltips: [pap, source, target]

    # Color mapping for primary_ag_products
    unique_paps = df['primary_ag_product'].unique()

    # Manual color mapping for common Ag Products
    # Colors: purple, gold, brown, red, green, etc.
    MANUAL_MAP = {
        'grape': '#6f2da8',     # Purple
        'grapes': '#6f2da8',
        'almond': '#FFD700',    # Gold
        'almonds': '#FFD700',
        'tomato': '#FF6347',    # Tomato Red
        'tomatoes': '#FF6347',
        'pistachio': '#93C572', # Pistachio Green
        'pistachios': '#93C572',
        'walnut': '#A0522D',    # Sienna (Woody Brown)
        'walnuts': '#A0522D',
        'wood': '#8B4513',      # Saddle Brown
        'citrus': '#FFA500',    # Orange
        'lemon': '#FFF700',     # Lemon Yellow
        'orange': '#FF8C00',    # Dark Orange
        'strawberry': '#FC5A8D',# Strawberry Red
        'strawberries': '#FC5A8D',
        'wheat': '#F5DEB3',     # Wheat
        'corn': '#FBEC5D',      # Corn Yellow
        'rice': '#FFFFFF',      # Rice White
        'olive': '#808000',     # Olive Green
        'olives': '#808000'
    }

    pap_colors = {}
    palette_idx = 0
    for pap in unique_paps:
        found = False
        pap_lower = pap.lower()
        for key, color in MANUAL_MAP.items():
            if key in pap_lower:
                pap_colors[pap] = color
                found = True
                break
        if not found:
            pap_colors[pap] = LBNL_PALETTE[palette_idx % len(LBNL_PALETTE)]
            palette_idx += 1

    # Links for each transition
    for i in range(len(levels) - 1):
        source_level = levels[i]
        target_level = levels[i+1]

        groupby_cols = list(dict.fromkeys([source_level, target_level, 'primary_ag_product']))
        counts = df.groupby(groupby_cols).size().reset_index(name='count')

        for _, row in counts.iterrows():
            sources.append(node_map[f"{source_level}_{row[source_level]}"])
            targets.append(node_map[f"{target_level}_{row[target_level]}"])
            values.append(row['count'])
            # Opacity for links
            color = pap_colors[row['primary_ag_product']]
            # Convert hex to rgba for transparency if needed, or just use hex
            link_colors.append(color)
            link_custom_data.append([row['primary_ag_product'], row[source_level], row[target_level]])

    # Node labels: The user wants no individual labels on nodes, but category labels at the top.
    # We will set node labels to empty strings and use annotations for headers.
    node_labels = [""] * len(nodes)

    # For tooltips, we want the actual name
    node_custom_data = [node.split('_', 1)[1] for node in nodes]

    # 3. Create Sankey Diagram
    fig = go.Figure(data=[go.Sankey(
        node = dict(
          pad = 15,
          thickness = 20,
          line = dict(color = "black", width = 0.5),
          label = node_labels,
          customdata = node_custom_data,
          hovertemplate = '%{customdata}<extra></extra>',
          color = "lightgray"
        ),
        link = dict(
          source = sources,
          target = targets,
          value = values,
          color = link_colors,
          customdata = link_custom_data,
          hovertemplate = (
              '<b>Flow: %{value}</b><br>' +
              'From: %{customdata[1]}<br>' +
              'To: %{customdata[2]}<br>' +
              'Primary Product: %{customdata[0]}<extra></extra>'
          )
        ))])

    # Category Headers
    headers = ["Resource", "Field Sample", "Prepared Sample", "Analysis Type"]
    annotations = []
    for i, header in enumerate(headers):
        annotations.append(dict(
            x = i / (len(headers) - 1),
            y = 1.05,
            xref = "paper",
            yref = "paper",
            text = f"<b>{header}</b>",
            showarrow = False,
            font = dict(size=14)
        ))

    fig.update_layout(
        title_text="Biomass Sample Lineage Flow",
        font_size=12,
        width=1400,
        height=900,
        annotations=annotations,
        margin=dict(t=80, l=50, r=50, b=50)
    )

    # 4. Save
    os.makedirs("exports/plots/lineage", exist_ok=True)
    export_path = "exports/plots/lineage/sample_lineage_flow.html"
    fig.write_html(export_path)

    print(f"Sankey diagram saved to {export_path}")

if __name__ == "__main__":
    main()
