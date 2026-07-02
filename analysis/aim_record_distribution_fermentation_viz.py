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

# # Aim Record Distribution Visualization - Fermentation
# This script visualizes the distribution of individual data points for Fermentation.

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
        SELECT record_id, resource_id, experiment_id, prepared_sample_id, qc_pass,
               strain_id, pretreatment_method_id, eh_method_id_new, bioconversion_method_id
        FROM fermentation_record
    ),
    fermentation_qc_stats AS (
        SELECT
            r.record_id,
            AVG(CASE WHEN LOWER(p.name) = 'sugar_cons' THEN o.value END) as avg_sugar_cons,
            AVG(CASE WHEN LOWER(p.name) = 'sugart0' THEN o.value END) as avg_sugart0,
            AVG(CASE WHEN LOWER(p.name) = 'sugarteof' THEN o.value END) as avg_sugarteof
        FROM observation o
        JOIN all_records r ON o.record_id = r.record_id
        JOIN parameter p ON o.parameter_id = p.id
        WHERE o.record_type = 'fermentation'
        GROUP BY r.record_id
    )
    SELECT
        obs.record_id,
        res.name as resource_name,
        pap.name as primary_ag_product,
        psam.name as prepared_sample_name,
        prov.codename as provider_code,
        param.name as analysis_param,
        obs.value,
        u.name as unit,
        rec.qc_pass,
        st.name as strain_name,
        pm.name as pretreatment_method,
        ehm.enzyme_formulation as enzyme_name,
        bcm.name as bioconversion_method,
        fqc.avg_sugar_cons,
        fqc.avg_sugart0,
        fqc.avg_sugarteof,
        CASE
            WHEN LOWER(res.name) IN :excluded THEN 'Raw'
            WHEN rec.qc_pass = 'fail' THEN 'Raw'
            WHEN (fqc.avg_sugart0 IS NOT NULL AND fqc.avg_sugart0 != 0 AND fqc.avg_sugar_cons IS NOT NULL)
                 AND ABS(fqc.avg_sugar_cons - ((fqc.avg_sugart0 - COALESCE(fqc.avg_sugarteof, 0)) / fqc.avg_sugart0) * 100) > 100 THEN 'Raw'
            WHEN LOWER(param.name) LIKE '%%yield%%' AND (obs.value < 0 OR obs.value > 105) THEN 'Raw'
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
    LEFT JOIN strain st ON rec.strain_id = st.id
    LEFT JOIN method pm ON rec.pretreatment_method_id = pm.id
    LEFT JOIN enz_hydr_method ehm ON rec.eh_method_id_new = ehm.id
    LEFT JOIN bioconversion_method bcm ON rec.bioconversion_method_id = bcm.id
    LEFT JOIN fermentation_qc_stats fqc ON rec.record_id = fqc.record_id
    WHERE obs.record_type = 'fermentation'
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"excluded": tuple(EXCLUDED_RESOURCES)})

    if df.empty:
        print("No Fermentation data found.")
        return

    # Data Cleaning
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['value']).copy()
    df['qc_pass'] = df['qc_pass'].fillna('unknown')
    df['provider_code'] = df['provider_code'].fillna('unknown')
    df['primary_ag_product'] = df['primary_ag_product'].fillna('unknown')
    df['unit'] = df['unit'].fillna('unknown')
    df['strain_name'] = df['strain_name'].fillna('unknown')
    df['pretreatment_method'] = df['pretreatment_method'].fillna('unknown')
    df['enzyme_name'] = df['enzyme_name'].fillna('unknown')
    df['bioconversion_method'] = df['bioconversion_method'].fillna('unknown')

    # 2. Build Altair Dashboard

    # Selections
    status_sel = alt.selection_point(name='status_selector', fields=['data_status'], toggle=True)
    res_sel = alt.selection_point(name='res_selector', fields=['resource_name'], toggle=True)
    prod_sel = alt.selection_point(name='prod_selector', fields=['primary_ag_product'], toggle=True)
    prov_sel = alt.selection_point(name='prov_selector', fields=['provider_code'], toggle=True)
    unit_sel = alt.selection_point(name='unit_selector', fields=['unit'], toggle=True)
    strain_sel = alt.selection_point(name='strain_selector', fields=['strain_name'], toggle=True)
    method_sel = alt.selection_point(name='method_selector', fields=['bioconversion_method'], toggle=True)

    # Combined filters
    all_filters = status_sel & res_sel & prod_sel & prov_sel & unit_sel & strain_sel & method_sel

    # Base Chart
    base = alt.Chart(df)

    # Main Chart
    main_base = base.transform_filter(all_filters)

    boxplot = main_base.mark_boxplot(extent='min-max', size=30, color='#00313C', opacity=0.3).encode(
        x=alt.X('analysis_param:N', title='Product / Parameter', axis=alt.Axis(labelAngle=45)),
        y=alt.Y('value:Q', title='Measured Value')
    )

    points = main_base.mark_circle(size=60, opacity=0.7).encode(
        x=alt.X('analysis_param:N'),
        y=alt.Y('value:Q'),
        xOffset='jitter:Q',
        color=alt.Color('resource_name:N', scale=alt.Scale(range=LBNL_PALETTE), legend=None),
        tooltip=['record_id', 'prepared_sample_name', 'resource_name', 'primary_ag_product', 'provider_code', 'data_status', 'qc_pass', 'strain_name', 'pretreatment_method', 'enzyme_name', 'bioconversion_method', 'value', 'unit']
    ).transform_calculate(
        jitter='sqrt(-2*log(random()))*cos(2*PI*random())'
    )

    main_chart = (boxplot + points).properties(
        width=1000,
        height=600,
        title='Fermentation Distribution'
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
        make_filter_bar('data_status', 'Data Status', status_sel),
        make_filter_bar('resource_name', 'Resource Name', res_sel),
        make_filter_bar('primary_ag_product', 'Ag Product', prod_sel),
        make_filter_bar('provider_code', 'Provider Code', prov_sel),
        make_filter_bar('unit', 'Unit', unit_sel),
        make_filter_bar('strain_name', 'Strain', strain_sel),
        make_filter_bar('bioconversion_method', 'Method', method_sel)
    ).resolve_scale(y='independent')

    # Final Assembly
    dashboard = alt.hconcat(
        sidebar,
        main_chart
    ).resolve_scale(
        color='independent'
    ).configure_view(
        stroke=None
    ).configure_title(
        anchor='start',
        fontSize=18
    )

    # 4. Save
    os.makedirs("exports/plots", exist_ok=True)
    export_path = "exports/plots/aim_record_distribution_fermentation.html"
    dashboard.save(export_path)

    print(f"Dashboard saved to {export_path}")

if __name__ == "__main__":
    main()
