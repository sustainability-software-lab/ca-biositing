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

# # Moisture vs Ash Content for All Resources
# This script compares moisture and ash content across all resources, highlighting almond residues.

import os
import pandas as pd
import altair as alt

# Force localhost for local database access
os.environ["POSTGRES_HOST"] = "localhost"

from ca_biositing.datamodels.database import get_engine
from ca_biositing.visualization.theme import LBNL_PALETTE

def main():
    # 1. Query Data
    engine = get_engine()

    query = """
    SELECT
        name as resource_name,
        moisture_percent,
        ash_percent
    FROM data_portal.mv_biomass_search
    WHERE moisture_percent IS NOT NULL OR ash_percent IS NOT NULL
    """

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    if df.empty:
        print("No data found for moisture or ash content.")
        return

    # Data Cleaning
    df['moisture_percent'] = pd.to_numeric(df['moisture_percent'], errors='coerce')
    df['ash_percent'] = pd.to_numeric(df['ash_percent'], errors='coerce')
    df = df.fillna(0) # Fill NAs with 0 for plotting if one is present

    # Define color logic: yellow for almond residues, blue for others
    df['color_group'] = df['resource_name'].apply(
        lambda x: 'Almond Residues' if 'almond' in x.lower() else 'Other Resources'
    )

    # 2. Build Chart
    chart = alt.Chart(df).mark_circle(size=100, opacity=0.7).encode(
        x=alt.X('moisture_percent:Q', title='Moisture Content (%)'),
        y=alt.Y('ash_percent:Q', title='Ash Content (%)'),
        color=alt.Color('color_group:N',
                        scale=alt.Scale(domain=['Almond Residues', 'Other Resources'],
                                       range=['#FFD700', '#00B5E2']),
                        legend=alt.Legend(title="Resource Category")),
        tooltip=['resource_name', 'moisture_percent', 'ash_percent']
    ).properties(
        width=600,
        height=400,
        title='Moisture vs Ash Content by Resource'
    ).interactive()

    # 3. Save
    os.makedirs("exports/plots/composition", exist_ok=True)

    # Save as Interactive HTML
    html_path = "exports/plots/composition/moisture_vs_ash.html"
    chart.save(html_path)
    print(f"Interactive plot saved to {html_path}")

    # Save as Static PNG
    png_path = "exports/plots/composition/moisture_vs_ash.png"
    chart.save(png_path)
    print(f"Static plot saved to {png_path}")

if __name__ == "__main__":
    main()
