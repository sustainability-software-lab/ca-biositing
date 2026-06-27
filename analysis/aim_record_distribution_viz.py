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

# # Aim Record Distribution Visualization (Altair Dashboard)
# This script visualizes the distribution of individual data points for Proximate Analysis.
# It supports multi-dimensional cross-filtering for:
# - Resource Name
# - Primary Ag Product
# - Provider Code
# - Unit
# - QC Status
#
# **Instructions:**
# - **Filter**: Click bars in the sidebar to filter the main chart.
# - **Multi-Select**: Hold **Shift** while clicking to select multiple items in a sidebar.
# - **Toggle**: Clicking an item again removes it from the selection.
# - **Clear**: Click in the empty area of a sidebar chart to clear that specific filter.

import os
import pandas as pd
import altair as alt
from sqlalchemy import text

# Force localhost for local database access
os.environ["POSTGRES_HOST"] = "localhost"

from ca_biositing.datamodels.database import get_engine
from ca_biositing.visualization.theme import LBNL_PALETTE, LBNL_COLORS

def main():
    # 1. Query Data
    engine = get_engine()

    query = text("""
    WITH all_records AS (
        SELECT record_id, resource_id, prepared_sample_id, qc_pass, note FROM proximate_record
        UNION ALL SELECT record_id, resource_id, prepared_sample_id, qc_pass, note FROM compositional_record
        UNION ALL SELECT record_id, resource_id, prepared_sample_id, qc_pass, note FROM ultimate_record
        UNION ALL SELECT record_id, resource_id, prepared_sample_id, qc_pass, note FROM icp_record
        UNION ALL SELECT record_id, resource_id, prepared_sample_id, qc_pass, note FROM xrf_record
        UNION ALL SELECT record_id, resource_id, prepared_sample_id, qc_pass, note FROM calorimetry_record
        UNION ALL SELECT record_id, resource_id, prepared_sample_id, qc_pass, note FROM xrd_record
        UNION ALL SELECT record_id, resource_id, prepared_sample_id, qc_pass, note FROM ftnir_record
        UNION ALL SELECT record_id, resource_id, prepared_sample_id, qc_pass, note FROM rgb_record
        UNION ALL SELECT record_id, resource_id, prepared_sample_id, qc_pass, note FROM fermentation_record
        UNION ALL SELECT record_id, resource_id, prepared_sample_id, qc_pass, note FROM pretreatment_record
        UNION ALL SELECT record_id, resource_id, prepared_sample_id, qc_pass, note FROM gasification_record
    )
    SELECT
        obs.record_id,
        res.name as resource_name,
        pap.name as primary_ag_product,
        rec.prepared_sample_id,
        prov.codename as provider_code,
        obs.record_type as analysis_type,
        param.name as meas_parameter,
        u.name as meas_unit,
        obs.value,
        rec.qc_pass,
        rec.note
    FROM observation obs
    JOIN all_records rec ON obs.record_id = rec.record_id
    LEFT JOIN resource res ON rec.resource_id = res.id
    LEFT JOIN primary_ag_product pap ON res.primary_ag_product_id = pap.id
    LEFT JOIN prepared_sample ps ON rec.prepared_sample_id = ps.id
    LEFT JOIN field_sample fs ON ps.field_sample_id = fs.id
    LEFT JOIN provider prov ON fs.provider_id = prov.id
    LEFT JOIN parameter param ON obs.parameter_id = param.id
    LEFT JOIN unit u ON obs.unit_id = u.id
    WHERE obs.record_type = 'proximate analysis'
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    if df.empty:
        print("No Proximate Analysis data found.")
        return

    # Data Cleaning
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['value'])
    df['qc_pass'] = df['qc_pass'].fillna('unknown')
    df['provider_code'] = df['provider_code'].fillna('unknown')
    df['primary_ag_product'] = df['primary_ag_product'].fillna('unknown')
    df['meas_unit'] = df['meas_unit'].fillna('unknown')

    # 2. Build Altair Dashboard

    # Selection definitions with explicit names to avoid collisions
    res_sel = alt.selection_point(name='resSelection', fields=['resource_name'], toggle='true')
    prod_sel = alt.selection_point(name='prodSelection', fields=['primary_ag_product'], toggle='true')
    prov_sel = alt.selection_point(name='provSelection', fields=['provider_code'], toggle='true')
    unit_sel = alt.selection_point(name='unitSelection', fields=['meas_unit'], toggle='true')
    qc_sel = alt.selection_point(name='qcSelection', fields=['qc_pass'], toggle='true')

    # Combined selection predicate for filtering the main chart
    filters = res_sel & prod_sel & prov_sel & unit_sel & qc_sel

    color_scale = alt.Scale(range=LBNL_PALETTE)

    # Main Chart Base
    main_base = alt.Chart(df).encode(
        y=alt.Y('value:Q', title='Measured Value'),
        x=alt.X('meas_parameter:N', title='Parameter', axis=alt.Axis(labelAngle=0)),
        color=alt.condition(
            filters,
            alt.Color('resource_name:N', scale=color_scale, legend=None),
            alt.value('lightgray')
        ),
        tooltip=[
            alt.Tooltip('record_id:N', title='Record ID'),
            alt.Tooltip('resource_name:N', title='Resource'),
            alt.Tooltip('primary_ag_product:N', title='Ag Product'),
            alt.Tooltip('provider_code:N', title='Provider'),
            alt.Tooltip('meas_unit:N', title='Unit'),
            alt.Tooltip('qc_pass:N', title='QC Status'),
            alt.Tooltip('value:Q', title='Value', format='.2f'),
            alt.Tooltip('note:N', title='Note')
        ]
    ).transform_filter(
        filters
    )

    # Main Plot: Boxplot + Jittered Points
    boxplot = main_base.mark_boxplot(extent='min-max', size=30, color='#00313C', opacity=0.3)
    points = main_base.mark_circle(size=70, opacity=0.7).encode(
        xOffset='jitter:Q'
    ).transform_calculate(
        jitter='sqrt(-2*log(random()))*cos(2*PI*random())'
    )

    main_chart = (boxplot + points).properties(
        width=700,
        height=600,
        title=alt.TitleParams(
            text='Proximate Analysis: Multi-Dimensional Distribution',
            subtitle=['Click/Shift-Click sidebar categories to filter. Combinations are supported across all filters.'],
            anchor='start',
            fontSize=20,
            subtitleFontSize=12
        )
    )

    # Sidebar Chart Factory
    def make_sidebar(field, title, selection, other_filters):
        return alt.Chart(df).mark_bar().encode(
            y=alt.Y(f'{field}:N', title=None, sort='-x'),
            x=alt.X('count():Q', title='Records', axis=alt.Axis(labels=False, ticks=False)),
            color=alt.condition(selection, alt.value('#00B5E2'), alt.value('lightgray')),
            opacity=alt.condition(other_filters, alt.value(1.0), alt.value(0.2)),
            tooltip=[alt.Tooltip(field, title=title), alt.Tooltip('count()', title='Count')]
        ).properties(
            width=180,
            height=alt.Step(18),
            title=alt.TitleParams(text=title, fontSize=14, anchor='start')
        ).add_params(selection)

    # Create Sidebars
    res_sidebar = make_sidebar('resource_name', 'Resources', res_sel, prod_sel & prov_sel & unit_sel & qc_sel)
    prod_sidebar = make_sidebar('primary_ag_product', 'Ag Products', prod_sel, res_sel & prov_sel & unit_sel & qc_sel)
    prov_sidebar = make_sidebar('provider_code', 'Providers', prov_sel, res_sel & prod_sel & unit_sel & qc_sel)
    qc_sidebar = make_sidebar('qc_pass', 'QC Status', qc_sel, res_sel & prod_sel & prov_sel & unit_sel)
    unit_sidebar = make_sidebar('meas_unit', 'Units', unit_sel, res_sel & prod_sel & prov_sel & qc_sel)

    # Final Dashboard Construction
    sidebars = alt.vconcat(
        res_sidebar, prod_sidebar, prov_sidebar, qc_sidebar, unit_sidebar
    ).resolve_scale(
        color='independent',
        y='independent'
    )

    dashboard = alt.hconcat(
        sidebars,
        main_chart
    ).resolve_scale(
        color='independent'
    ).configure_axis(
        grid=False,
        labelColor='#00313C',
        titleColor='#00313C'
    ).configure_view(
        stroke=None
    )

    # 4. Save Export
    os.makedirs("exports/plots", exist_ok=True)
    export_path_html = "exports/plots/aim_record_distribution_proximate.html"
    dashboard.save(export_path_html)

    print(f"Interactive dashboard updated at {export_path_html}")

if __name__ == "__main__":
    main()
