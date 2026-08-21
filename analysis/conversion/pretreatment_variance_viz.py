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

# # Aim Record Variance Visualization - Pretreatment
# This script visualizes the variance of individual data points for Pretreatment, grouped by prepared sample and pretreatment method.

import os
import pandas as pd
import altair as alt
from sqlalchemy import text

# Force localhost for local database access
os.environ["POSTGRES_HOST"] = "localhost"

from ca_biositing.datamodels.database import get_engine
from ca_biositing.visualization.theme import LBNL_PALETTE

def main():
    # 1. Query Data
    engine = get_engine()

    EXCLUDED_RESOURCES = [
        "sargassum", "#n/a", "lab media", "alfalfa",
        "almond hulls and shells mix", "almond shells and hulls mix", "almond woodchips"
    ]

    query = text("""
    WITH all_records AS (
        SELECT record_id, resource_id, experiment_id, prepared_sample_id, qc_pass, note, pretreatment_method_id FROM pretreatment_record
    )
    SELECT
        obs.record_id,
        res.name as resource_name,
        pap.name as primary_ag_product,
        psam.name as prepared_sample_name,
        prov.codename as provider_code,
        meth.name as raw_pretreatment_method,
        param.name as analysis_param,
        obs.value,
        u.name as unit,
        rec.qc_pass,
        CASE
            WHEN LOWER(res.name) IN :excluded THEN 'Raw'
            WHEN rec.qc_pass = 'fail' THEN 'Raw'
            ELSE 'Portal Compliant'
        END as data_status
    FROM observation obs
    JOIN all_records rec ON obs.record_id = rec.record_id
    LEFT JOIN resource res ON rec.resource_id = res.id
    LEFT JOIN primary_ag_product pap ON res.primary_ag_product_id = pap.id
    LEFT JOIN prepared_sample psam ON rec.prepared_sample_id = psam.id
    LEFT JOIN field_sample fs ON psam.field_sample_id = fs.id
    LEFT JOIN provider prov ON fs.provider_id = prov.id
    LEFT JOIN parameter param ON obs.parameter_id = param.id
    LEFT JOIN unit u ON obs.unit_id = u.id
    LEFT JOIN method meth ON rec.pretreatment_method_id = meth.id
    WHERE obs.record_type = 'pretreatment'
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"excluded": tuple(EXCLUDED_RESOURCES)})

    if df.empty:
        print("No Pretreatment data found.")
        return

    # Data Cleaning
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['value']).copy()
    df['qc_pass'] = df['qc_pass'].fillna('unknown')
    df['provider_code'] = df['provider_code'].fillna('unknown')
    df['primary_ag_product'] = df['primary_ag_product'].fillna('unknown')
    df['unit'] = df['unit'].fillna('unknown')
    df['prepared_sample_name'] = df['prepared_sample_name'].fillna('unknown')

    # Collapse Pretreatment Methods into categories consistent with data portal
    def collapse_method(name):
        if not name or pd.isna(name):
            return 'unknown'
        name_lower = name.lower()
        if 'cholinium' in name_lower and 'lysinate' in name_lower:
            return 'Cholinium Lysinate 140°C'
        if 'butylamine' in name_lower:
            return 'Butylamine 140°C'
        if 'hot water' in name_lower or 'water pretreatment' in name_lower:
            return 'Water 140°C'
        if 'no pretreatment' in name_lower or 'no pretreat' in name_lower:
            return 'No Pretreatment'
        return name

    df['pretreatment_method'] = df['raw_pretreatment_method'].apply(collapse_method)

    # 2. Build Altair Dashboard

    # Selections
    status_sel = alt.selection_point(name='status_selector', fields=['data_status'], toggle=True)
    res_sel = alt.selection_point(name='res_selector', fields=['resource_name'], toggle=True)
    param_sel = alt.selection_point(name='param_selector', fields=['analysis_param'], toggle=True)
    method_sel = alt.selection_point(name='method_selector', fields=['pretreatment_method'], toggle=True)
    sample_sel = alt.selection_point(name='sample_selector', fields=['prepared_sample_name'], toggle=True)

    # Combined filters
    all_filters = status_sel & res_sel & param_sel & method_sel & sample_sel

    # Base Chart
    base = alt.Chart(df)

    # Main Chart 1: Scatter plot with shape for method and color for sample
    main_base = base.transform_filter(all_filters)

    points = main_base.mark_point(size=100, opacity=0.8, filled=True).encode(
        x=alt.X('analysis_param:N', title='Pretreatment Parameter'),
        y=alt.Y('value:Q', title='Measured Value (%)'),
        xOffset='jitter:Q',
        color=alt.Color('prepared_sample_name:N', scale=alt.Scale(scheme='category20'), legend=alt.Legend(title="Prepared Sample", columns=2, symbolLimit=50)),
        shape=alt.Shape('pretreatment_method:N', legend=alt.Legend(title="Pretreatment Method")),
        tooltip=['record_id', 'prepared_sample_name', 'resource_name', 'provider_code', 'pretreatment_method', 'raw_pretreatment_method', 'data_status', 'qc_pass', 'value', 'unit']
    ).transform_calculate(
        jitter='sqrt(-2*log(random()))*cos(2*PI*random())'
    )

    main_chart = points.properties(
        width=600,
        height=500,
        title='Pretreatment Variance by Sample and Method'
    )

    # Chart 2: Strip plot grouped by sample and method to see variance clearly
    strip_plot = main_base.mark_circle(size=60, opacity=0.7).encode(
        x=alt.X('value:Q', title='Measured Value (%)'),
        y=alt.Y('prepared_sample_name:N', title='Prepared Sample', sort='-x'),
        color=alt.Color('prepared_sample_name:N', legend=None),
        row=alt.Row('pretreatment_method:N', title='Pretreatment Method'),
        column=alt.Column('analysis_param:N', title='Parameter'),
        tooltip=['record_id', 'prepared_sample_name', 'pretreatment_method', 'value']
    ).properties(
        width=300,
        height=alt.Step(20),
        title='Variance within Sample/Method Replicates'
    )

    # Sidebar Filter Factory
    def make_filter_bar(field, title, selection):
        return base.mark_bar().encode(
            y=alt.Y(f'{field}:N', sort='-x', title=None),
            x=alt.X('count():Q', title=None, axis=alt.Axis(labels=False, ticks=False)),
            color=alt.condition(selection, alt.value('#00B5E2'), alt.value('lightgray')),
            tooltip=[alt.Tooltip(field, title=title), alt.Tooltip('count()', title='Count')]
        ).add_params(selection).properties(
            width=180,
            height=alt.Step(20),
            title=alt.TitleParams(text=title, fontSize=13, anchor='start')
        )

    # Sidebars
    sidebar = alt.vconcat(
        make_filter_bar('data_status', 'Data Status', status_sel),
        make_filter_bar('analysis_param', 'Parameter', param_sel),
        make_filter_bar('pretreatment_method', 'Pretreatment Method', method_sel),
        make_filter_bar('resource_name', 'Resource Name', res_sel),
        make_filter_bar('prepared_sample_name', 'Prepared Sample', sample_sel)
    ).resolve_scale(y='independent')

    # Final Assembly
    dashboard = alt.vconcat(
        alt.hconcat(sidebar, main_chart).resolve_scale(color='independent', shape='independent'),
        strip_plot
    ).configure_view(
        stroke=None
    ).configure_title(
        anchor='start',
        fontSize=18
    )

    # 4. Save
    os.makedirs("exports/plots/conversion", exist_ok=True)
    export_path = "exports/plots/conversion/pretreatment_variance.html"
    dashboard.save(export_path)

    print(f"Dashboard saved to {export_path}")

if __name__ == "__main__":
    main()
