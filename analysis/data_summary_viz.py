# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
# ---

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from ca_biositing.datamodels.database import get_engine
from ca_biositing.visualization.theme import set_lbnl_theme_mpl

# Set LBNL Theme
set_lbnl_theme_mpl()

def generate_visualizations():
    engine = get_engine()
    os.makedirs("exports/plots", exist_ok=True)

    # 1. Aim 1 Record Counts
    aim1_data = {
        "Type": ["Compositional", "Calorimetry", "FTNIR", "ICP", "Proximate"],
        "Count": [1043, 6, 0, 1066, 1339]
    }
    df_aim1 = pd.DataFrame(aim1_data)

    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_aim1, x="Type", y="Count")
    plt.title("Aim 1: Analytical Record Counts")
    plt.ylabel("Number of Records")
    plt.xlabel("Analysis Type")
    plt.tight_layout()
    plt.savefig("exports/plots/aim1_record_counts.png", dpi=300)
    plt.close()

    # 2. Aim 2 Record Counts
    aim2_data = {
        "Type": ["Fermentation", "Gasification"],
        "Count": [4021, 801]
    }
    df_aim2 = pd.DataFrame(aim2_data)

    plt.figure(figsize=(8, 6))
    sns.barplot(data=df_aim2, x="Type", y="Count")
    plt.title("Aim 2: Processing Record Counts")
    plt.ylabel("Number of Records")
    plt.xlabel("Analysis Type")
    plt.tight_layout()
    plt.savefig("exports/plots/aim2_record_counts.png", dpi=300)
    plt.close()

    # 3. Filter Quality Assessment
    qc_data = [
        {"Domain": "Fermentation", "Type": "Raw", "Count": 4021},
        {"Domain": "Fermentation", "Type": "QC Pass", "Count": 410},
        {"Domain": "Gasification", "Type": "Raw", "Count": 801},
        {"Domain": "Gasification", "Type": "QC Pass", "Count": 269},
    ]
    df_qc = pd.DataFrame(qc_data)

    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_qc, x="Domain", y="Count", hue="Type")
    plt.title("Filter Quality Assessment: Raw vs QC Pass")
    plt.ylabel("Number of Records")
    plt.tight_layout()
    plt.savefig("exports/plots/filter_quality_assessment.png", dpi=300)
    plt.close()

    print("Visualizations generated successfully in exports/plots/")

if __name__ == "__main__":
    generate_visualizations()
