"""
LBNL Theme definitions for Matplotlib, Seaborn, and Plotly.
"""

import matplotlib.pyplot as plt
import plotly.graph_objects as go

# LBNL Brand Colors
LBNL_COLORS = {
    "primary": {
        "deep_blue": "#00313C",
        "teal": "#00B5E2",
        "gold": "#FDB515",
    },
    "secondary": {
        "orange": "#F26D04",
        "red": "#E31837",
        "green": "#8CC63F",
        "gray": "#58595B",
        "light_gray": "#D1D3D4",
    }
}

# A categorical palette based on LBNL colors
LBNL_PALETTE = [
    LBNL_COLORS["primary"]["deep_blue"],
    LBNL_COLORS["primary"]["teal"],
    LBNL_COLORS["primary"]["gold"],
    LBNL_COLORS["secondary"]["orange"],
    LBNL_COLORS["secondary"]["green"],
    LBNL_COLORS["secondary"]["red"],
    LBNL_COLORS["secondary"]["gray"],
]

def set_lbnl_theme_mpl():
    """
    Updates matplotlib rcParams to use LBNL styling.
    """
    plt.rcParams.update({
        # Colors
        "axes.prop_cycle": plt.cycler(color=LBNL_PALETTE),
        "axes.facecolor": "white",
        "axes.edgecolor": LBNL_COLORS["secondary"]["gray"],
        "axes.labelcolor": LBNL_COLORS["primary"]["deep_blue"],

        # Grid
        "axes.grid": True,
        "grid.color": LBNL_COLORS["secondary"]["light_gray"],
        "grid.linestyle": "--",
        "grid.alpha": 0.7,

        # Fonts
        "font.family": "sans-serif",
        "text.color": LBNL_COLORS["primary"]["deep_blue"],
        "xtick.color": LBNL_COLORS["secondary"]["gray"],
        "ytick.color": LBNL_COLORS["secondary"]["gray"],

        # Spines
        "axes.spines.top": False,
        "axes.spines.right": False,

        # Legend
        "legend.frameon": False,
        "legend.numpoints": 1,
        "legend.scatterpoints": 1,
    })

def get_lbnl_template_plotly() -> go.layout.Template:
    """
    Returns a Plotly layout template with LBNL styling.
    """
    template = go.layout.Template()

    template.layout = go.Layout(
        colorway=LBNL_PALETTE,
        font=dict(color=LBNL_COLORS["primary"]["deep_blue"]),
        title=dict(font=dict(color=LBNL_COLORS["primary"]["deep_blue"])),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(
            gridcolor=LBNL_COLORS["secondary"]["light_gray"],
            linecolor=LBNL_COLORS["secondary"]["gray"],
            tickcolor=LBNL_COLORS["secondary"]["gray"],
            zerolinecolor=LBNL_COLORS["secondary"]["light_gray"],
            showgrid=True,
        ),
        yaxis=dict(
            gridcolor=LBNL_COLORS["secondary"]["light_gray"],
            linecolor=LBNL_COLORS["secondary"]["gray"],
            tickcolor=LBNL_COLORS["secondary"]["gray"],
            zerolinecolor=LBNL_COLORS["secondary"]["light_gray"],
            showgrid=True,
        ),
        legend=dict(
            bgcolor="rgba(255, 255, 255, 0)",
            bordercolor="rgba(255, 255, 255, 0)"
        )
    )

    return template
