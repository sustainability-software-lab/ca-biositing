import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from ca_biositing.datamodels.database import get_engine

def generate_sample_visualizations():
    # Ensure we use localhost for host since we are running outside docker
    os.environ["POSTGRES_HOST"] = "localhost"
    engine = get_engine()

    # 1. Fetch data
    query = "SELECT * FROM data_portal.mv_biomass_composition LIMIT 1000"
    df = pd.read_sql(query, engine)

    # 2. Basic Setup
    sns.set_theme(style="whitegrid")
    plt.rcParams['figure.figsize'] = (10, 6)

    # Ensure exports directory exists
    os.makedirs("exports", exist_ok=True)

    # 3. Generate Visualizations

    # Plot 1: Distribution of Average Values (Seaborn)
    plt.figure()
    sns.histplot(data=df, x="avg_value", kde=True)
    plt.title("Distribution of Average Values")
    plt.xlabel("Average Value")
    plt.savefig("exports/sample_avg_value_distribution.png", dpi=300, bbox_inches='tight')
    plt.close()

    # Plot 2: Average Value by Parameter Name (Seaborn)
    plt.figure()
    sns.boxplot(data=df, x="parameter_name", y="avg_value")
    plt.xticks(rotation=45)
    plt.title("Average Value by Parameter Name")
    plt.savefig("exports/sample_avg_value_by_parameter.png", dpi=300, bbox_inches='tight')
    plt.close()

    # Plot 3: Interactive Scatter Plot (Plotly)
    # Let's create a scatter plot of avg_value vs parameter_name, colored by county
    fig = px.scatter(
        df,
        x="parameter_name",
        y="avg_value",
        color="county",
        hover_data=["resource_name", "analysis_type"],
        title="Interactive: Average Value by Parameter and County"
    )
    fig.write_html("exports/sample_interactive_scatter.html")

    print("Sample visualizations generated successfully in exports/ directory.")

if __name__ == "__main__":
    generate_sample_visualizations()
