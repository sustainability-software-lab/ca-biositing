# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: Pixi
#     language: python
#     name: pixi
# ---

# # Database Metadata Dashboard
# This dashboard provides an overview of the data distribution within the BioCirV database,
# focusing on analysis types, resource classifications, and sample statistics.
#
# **LBNL BioCirV Project**

import os

# Force localhost for local database access
os.environ["POSTGRES_HOST"] = "localhost"

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ca_biositing.datamodels.database import get_engine
from ca_biositing.visualization.theme import set_lbnl_theme_mpl # For consistency in branding if needed

# ## Data Acquisition

def get_dashboard_data():
    engine = get_engine()

    # 1. Analysis Types distribution from Composition view
    query_comp = """
    SELECT analysis_type, SUM(observation_count) as total_observations
    FROM data_portal.mv_biomass_composition
    GROUP BY analysis_type
    ORDER BY total_observations DESC
    """
    df_analysis = pd.read_sql(query_comp, engine)

    # 2. Sample Stats summary (filtered to resources with samples)
    query_stats = "SELECT * FROM data_portal.mv_biomass_sample_stats WHERE sample_count > 0"
    df_stats = pd.read_sql(query_stats, engine)

    # 3. Resource Class and Primary Product distribution with stats and providers
    # Filtered to resources with at least one physical sample
    query_search = """
    WITH resource_providers AS (
        SELECT
            fs.resource_id,
            STRING_AGG(DISTINCT p.codename, ', ') as provider_list
        FROM public.field_sample fs
        JOIN public.provider p ON fs.provider_id = p.id
        GROUP BY fs.resource_id
    )
    SELECT
        s.resource_class,
        s.primary_product,
        s.name as resource_name,
        COALESCE(st.sample_count, 0) as sample_count,
        COALESCE(st.total_record_count, 0) as total_record_count,
        COALESCE(rp.provider_list, 'N/A') as providers
    FROM data_portal.mv_biomass_search s
    JOIN data_portal.mv_biomass_sample_stats st ON s.id = st.resource_id
    LEFT JOIN resource_providers rp ON s.id = rp.resource_id
    WHERE st.sample_count > 0
    ORDER BY s.resource_class, s.primary_product, s.name
    """
    df_search = pd.read_sql(query_search, engine)

    # 4. Sample Collection Time Series
    query_time = """
    SELECT
        fs.collection_timestamp,
        s.name as resource_name,
        s.resource_class,
        s.primary_product
    FROM public.field_sample fs
    JOIN data_portal.mv_biomass_search s ON fs.resource_id = s.id
    WHERE fs.collection_timestamp IS NOT NULL
    """
    df_time = pd.read_sql(query_time, engine)
    df_time['collection_timestamp'] = pd.to_datetime(df_time['collection_timestamp'])

    return df_analysis, df_stats, df_search, df_time

df_analysis, df_stats, df_search, df_time = get_dashboard_data()

# ## Visualizations

# ### 1. Distribution of Analysis Types
# Showing the breadth of analytical data available.

fig_analysis = px.pie(
    df_analysis,
    values='total_observations',
    names='analysis_type',
    title='Distribution of Observations by Analysis Type',
    hole=0.4,
    color_discrete_sequence=px.colors.qualitative.Prism
)
fig_analysis.update_traces(
    textinfo='percent+label',
    hovertemplate="<b>%{label}</b><br>Observations: %{value}<br>Percentage: %{percent}<extra></extra>"
)
fig_analysis.update_layout(template="plotly_white")

# ### 2. Resource Statistics Overview
# Comparing sample, supplier, and record counts across resources.

# Top 15 resources by total record count for readability
df_stats_top = df_stats.nlargest(15, 'total_record_count')

fig_stats = px.bar(
    df_stats_top,
    x='resource_name',
    y=['sample_count', 'supplier_count', 'total_record_count'],
    title='Top 15 Resources: Sample, Supplier, and Record Counts',
    barmode='group',
    labels={'value': 'Count', 'variable': 'Metric', 'resource_name': 'Resource'},
    color_discrete_sequence=['#00313C', '#005F73', '#0A9396'] # LBNL-ish colors
)
fig_stats.update_layout(xaxis_tickangle=-45, template="plotly_white")

# ### 3. Resource Classification Breakdown
# Treemap showing hierarchy of Resource Class and Primary Product.

# Handle None values for visualization
df_search_viz = df_search.copy()
df_search_viz['resource_class'] = df_search_viz['resource_class'].fillna('Unclassified')
df_search_viz['primary_product'] = df_search_viz['primary_product'].fillna('Unknown Product')
df_search_viz['resource_name'] = df_search_viz['resource_name'].fillna('Unnamed Resource')

# Add a dummy count column for treemap sizing if needed, or just use count of occurrences
df_search_viz['count'] = 1

fig_tree = px.treemap(
    df_search_viz,
    path=['resource_class', 'primary_product', 'resource_name'],
    values='count',
    custom_data=['sample_count', 'total_record_count', 'providers'],
    title='Database Resource Hierarchy: Class, Product, and Resource Name',
    color_discrete_sequence=px.colors.qualitative.Safe
)

fig_tree.update_traces(
    hovertemplate="<b>%{label}</b><br>Samples: %{customdata[0]}<br>Total Records: %{customdata[1]}<br>Providers: %{customdata[2]}<extra></extra>"
)
fig_tree.update_layout(template="plotly_white")

# ### 4. Sample Collection Over Time
# Stacked bar chart showing monthly collection counts.

# Prepare cumulative time series data
df_time_agg = df_time.copy()
df_time_agg['month_dt'] = df_time_agg['collection_timestamp'].dt.to_period('M').dt.to_timestamp()

# 1. Aggregate counts per month/resource
df_time_plot = df_time_agg.groupby(['month_dt', 'resource_name']).size().reset_index(name='monthly_count')

# 2. Ensure every resource has a row for every month to make cumulative sum work across all time steps
all_months = pd.date_range(start=df_time_plot['month_dt'].min(), end=df_time_plot['month_dt'].max(), freq='MS')
all_resources = df_time_plot['resource_name'].unique()
full_index = pd.MultiIndex.from_product([all_months, all_resources], names=['month_dt', 'resource_name'])
df_full = pd.DataFrame(index=full_index).reset_index()

df_time_plot = pd.merge(df_full, df_time_plot, on=['month_dt', 'resource_name'], how='left').fillna(0)
df_time_plot = df_time_plot.sort_values(['resource_name', 'month_dt'])

# 3. Calculate cumulative sum per resource
df_time_plot['cumulative_count'] = df_time_plot.groupby('resource_name')['monthly_count'].cumsum()

# 4. Format for display
df_time_plot['month_year'] = df_time_plot['month_dt'].dt.strftime('%Y-%m')

fig_time = px.bar(
    df_time_plot,
    x='month_year',
    y='cumulative_count',
    color='resource_name',
    title='Cumulative Samples Collected Over Time',
    labels={'month_year': 'Month', 'cumulative_count': 'Total Samples (Cumulative)', 'resource_name': 'Resource'},
    template="plotly_white"
)

fig_time.update_layout(
    xaxis_tickangle=-45,
    legend_title_text='Resource',
    hovermode='x unified',
    barmode='stack'
)

# ### 5. Cumulative Samples Over Time (by Primary Product)

# 1. Aggregate counts per month/primary_product
df_time_ag_plot = df_time_agg.groupby(['month_dt', 'primary_product']).size().reset_index(name='monthly_count')

# 2. Ensure every product has a row for every month
all_products = df_time_ag_plot['primary_product'].unique()
full_ag_index = pd.MultiIndex.from_product([all_months, all_products], names=['month_dt', 'primary_product'])
df_ag_full = pd.DataFrame(index=full_ag_index).reset_index()

df_time_ag_plot = pd.merge(df_ag_full, df_time_ag_plot, on=['month_dt', 'primary_product'], how='left').fillna(0)
df_time_ag_plot = df_time_ag_plot.sort_values(['primary_product', 'month_dt'])

# 3. Calculate cumulative sum per product
df_time_ag_plot['cumulative_count'] = df_time_ag_plot.groupby('primary_product')['monthly_count'].cumsum()

# 4. Format for display
df_time_ag_plot['month_year'] = df_time_ag_plot['month_dt'].dt.strftime('%Y-%m')

fig_time_ag = px.bar(
    df_time_ag_plot,
    x='month_year',
    y='cumulative_count',
    color='primary_product',
    title='Cumulative Samples Collected Over Time (by Primary Product)',
    labels={'month_year': 'Month', 'cumulative_count': 'Total Samples (Cumulative)', 'primary_product': 'Primary Product'},
    template="plotly_white"
)

fig_time_ag.update_layout(
    xaxis_tickangle=-45,
    legend_title_text='Primary Product',
    hovermode='x unified',
    barmode='stack'
)

# ## Dashboard Assembly

# Create a combined dashboard view (HTML export)
os.makedirs("exports/plots/metadata", exist_ok=True)

# Export individual plots as interactive HTML
fig_analysis.write_html("exports/plots/metadata/database_analysis_type_dist.html")
fig_stats.write_html("exports/plots/metadata/database_resource_stats.html")
fig_tree.write_html("exports/plots/metadata/database_resource_hierarchy.html")
fig_time.write_html("exports/plots/metadata/database_samples_over_time.html")
fig_time_ag.write_html("exports/plots/metadata/database_samples_over_time_ag.html")

# Displaying in notebook
fig_analysis.show()
fig_stats.show()
fig_tree.show()
fig_time.show()
fig_time_ag.show()

print("Dashboard components generated in exports/plots/metadata/")
