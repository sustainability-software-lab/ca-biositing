import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import select, and_, func

# Ensure we connect to localhost when running outside docker
os.environ['POSTGRES_HOST'] = 'localhost'

from ca_biositing.datamodels.database import get_engine
from ca_biositing.datamodels.data_portal_views import (
    mv_biomass_volume_estimate,
    mv_biomass_composition,
    mv_biomass_fermentation,
    mv_biomass_gasification
)

# Configuration
TARGET_RESOURCES = ['cotton stem mix', 'sweet potato culls']
TARGET_COUNTIES = ['san joaquin', 'stanislaus', 'merced']
EXPORT_DIR = 'exports/plots/cotton_sweet_potato'
REPORT_PATH = 'exports/cotton_sweet_potato_report.md'

# Ensure export directory exists
os.makedirs(EXPORT_DIR, exist_ok=True)

def get_volume_data(engine):
    """Query volume estimates for target resources and counties."""
    with engine.connect() as conn:
        # Create subquery to access columns properly
        sq = mv_biomass_volume_estimate.subquery()

        query = select(
            sq.c.resource_name,
            sq.c.county,
            sq.c.dataset_year,
            sq.c.estimated_residue_volume_mid,
            sq.c.biomass_unit
        ).where(
            and_(
                func.lower(sq.c.resource_name).in_(TARGET_RESOURCES),
                func.lower(sq.c.county).in_(TARGET_COUNTIES)
            )
        )
        df = pd.read_sql(query, conn)
        return df

def get_composition_data(engine):
    """Query composition data for target resources."""
    with engine.connect() as conn:
        sq = mv_biomass_composition.subquery()

        query = select(
            sq.c.resource_name,
            sq.c.analysis_type,
            sq.c.parameter_name,
            sq.c.avg_value,
            sq.c.unit
        ).where(
            func.lower(sq.c.resource_name).in_(TARGET_RESOURCES)
        )
        df = pd.read_sql(query, conn)
        return df

def get_fermentation_data(engine):
    """Query fermentation data for target resources."""
    with engine.connect() as conn:
        sq = mv_biomass_fermentation.subquery()

        query = select(
            sq.c.resource_name,
            sq.c.strain_name,
            sq.c.pretreatment_method,
            sq.c.enzyme_name,
            sq.c.product_name,
            sq.c.avg_value,
            sq.c.unit
        ).where(
            func.lower(sq.c.resource_name).in_(TARGET_RESOURCES)
        )
        df = pd.read_sql(query, conn)
        return df

def get_gasification_data(engine):
    """Query gasification data for target resources."""
    with engine.connect() as conn:
        sq = mv_biomass_gasification.subquery()

        query = select(
            sq.c.resource_name,
            sq.c.reactor_type,
            sq.c.parameter_name,
            sq.c.avg_value,
            sq.c.unit
        ).where(
            func.lower(sq.c.resource_name).in_(TARGET_RESOURCES)
        )
        df = pd.read_sql(query, conn)
        return df

def plot_volume_distribution(df):
    """Plot volume distribution by county and resource."""
    if df.empty:
        return None

    # Aggregate by resource and county (taking the most recent year or average)
    # Here we'll take the average across years for a general estimate
    agg_df = df.groupby(['resource_name', 'county'])['estimated_residue_volume_mid'].mean().reset_index()

    # Capitalize county names for the plot
    agg_df['county'] = agg_df['county'].str.title()

    plt.figure(figsize=(10, 6))
    sns.barplot(data=agg_df, x='county', y='estimated_residue_volume_mid', hue='resource_name')
    plt.title('Average Estimated Residue Volume by County')
    plt.ylabel('Volume (Dry Tons)')
    plt.xlabel('County')
    plt.tight_layout()

    plot_path = os.path.join(EXPORT_DIR, 'volume_distribution.png')
    plt.savefig(plot_path)
    plt.close()
    return plot_path

def plot_composition_summary(df):
    """Plot key composition parameters."""
    if df.empty:
        return None

    # Filter for some key parameters to avoid cluttered plots
    key_params = ['Moisture', 'Ash', 'Carbon', 'Glucan', 'Xylan', 'Lignin']
    # We might need to adjust these based on what's actually in the DB
    # Let's just take the top 10 most frequent parameters for now
    top_params = df['parameter_name'].value_counts().head(10).index
    plot_df = df[df['parameter_name'].isin(top_params)]

    plt.figure(figsize=(12, 8))
    sns.boxplot(data=plot_df, x='parameter_name', y='avg_value', hue='resource_name')
    plt.title('Composition Analysis Summary')
    plt.ylabel('Average Value')
    plt.xlabel('Parameter')
    plt.xticks(rotation=45)
    plt.tight_layout()

    plot_path = os.path.join(EXPORT_DIR, 'composition_summary.png')
    plt.savefig(plot_path)
    plt.close()
    return plot_path

def generate_markdown_report(vol_df, comp_df, ferm_df, gas_df, vol_plot, comp_plot):
    """Generate the final markdown report."""

    md_content = [
        "# Cotton and Sweet Potato Biomass Report",
        "\nThis report summarizes the availability, composition, and conversion potential of cotton and sweet potato residues in San Joaquin, Stanislaus, and Merced counties.",
        "\n## 1. Biomass Availability",
        "The following table and chart show the estimated volume of these resources across the target counties.",
        f"\n![Volume Distribution]({os.path.relpath(vol_plot, os.path.dirname(REPORT_PATH))} 'Volume Distribution')" if vol_plot else "\n*No volume plot available.*",
        "\n### Volume Data Summary",
    ]

    if not vol_df.empty:
        # Create a summary table
        vol_summary = vol_df.groupby(['resource_name', 'county', 'dataset_year'])['estimated_residue_volume_mid'].sum().reset_index()
        vol_summary['county'] = vol_summary['county'].str.title()
        vol_summary.columns = ['Resource', 'County', 'Year', 'Estimated Volume (Dry Tons)']
        md_content.append(vol_summary.to_markdown(index=False))
    else:
        md_content.append("*No volume data found for these resources in the target counties.*")

    md_content.extend([
        "\n## 2. Composition Analysis",
        "Composition data provides insights into the chemical makeup of the biomass, which is critical for determining suitable conversion pathways.",
        f"\n![Composition Summary]({os.path.relpath(comp_plot, os.path.dirname(REPORT_PATH))} 'Composition Summary')" if comp_plot else "\n*No composition plot available.*",
        "\n### Composition Data Summary (Averages)",
    ])

    if not comp_df.empty:
        comp_summary = comp_df.groupby(['resource_name', 'parameter_name', 'unit'])['avg_value'].mean().reset_index()
        comp_summary.columns = ['Resource', 'Parameter', 'Unit', 'Average Value']
        md_content.append(comp_summary.to_markdown(index=False))
    else:
        md_content.append("*No composition data found for these resources.*")

    md_content.extend([
        "\n## 3. Fermentation Potential",
        "Data on fermentation yields and parameters.",
    ])

    if not ferm_df.empty:
        ferm_summary = ferm_df.groupby(['resource_name', 'product_name', 'unit'])['avg_value'].mean().reset_index()
        ferm_summary.columns = ['Resource', 'Product', 'Unit', 'Average Value']
        md_content.append(ferm_summary.to_markdown(index=False))
    else:
        md_content.append("*No fermentation data found for these resources.*")

    md_content.extend([
        "\n## 4. Gasification Potential",
        "Data on gasification outputs and parameters.",
    ])

    if not gas_df.empty:
        gas_summary = gas_df.groupby(['resource_name', 'parameter_name', 'unit'])['avg_value'].mean().reset_index()
        gas_summary.columns = ['Resource', 'Parameter', 'Unit', 'Average Value']
        md_content.append(gas_summary.to_markdown(index=False))
    else:
        md_content.append("*No gasification data found for these resources.*")

    with open(REPORT_PATH, 'w') as f:
        f.write('\n'.join(md_content))

    print(f"Report generated successfully at: {REPORT_PATH}")

def main():
    print("Connecting to database...")
    engine = get_engine()

    print("Extracting data...")
    vol_df = get_volume_data(engine)
    comp_df = get_composition_data(engine)
    ferm_df = get_fermentation_data(engine)
    gas_df = get_gasification_data(engine)

    print(f"Found {len(vol_df)} volume records, {len(comp_df)} composition records, {len(ferm_df)} fermentation records, {len(gas_df)} gasification records.")

    print("Generating visualizations...")
    vol_plot = plot_volume_distribution(vol_df)
    comp_plot = plot_composition_summary(comp_df)

    print("Compiling report...")
    generate_markdown_report(vol_df, comp_df, ferm_df, gas_df, vol_plot, comp_plot)

if __name__ == "__main__":
    main()
