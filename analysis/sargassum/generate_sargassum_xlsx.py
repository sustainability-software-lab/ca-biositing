#!/usr/bin/env python3
"""
Generate a formatted, multi-tab OpenXML Excel workbook (.xlsx) for Sargassum
analytical & bioconversion data — INCLUDING embedded Resource-Explorer-style
visual charts on a dedicated 'Visual Dashboard' tab and on each analysis tab.
"""

from __future__ import annotations

import io
import json
import math
import random
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


PAYLOAD_PATH = Path(
    "/Users/pjsmitty301/.gemini/antigravity/brain/42a5010b-7235-40e6-8c99-569580ebe1ec/scratch/dashboard_payload.json"
)
OUTPUT_XLSX = Path("/Users/pjsmitty301/ca-biositing/exports/sargassum_analytical_report.xlsx")
ARTIFACT_XLSX = Path(
    "/Users/pjsmitty301/.gemini/antigravity/brain/42a5010b-7235-40e6-8c99-569580ebe1ec/sargassum_analytical_report.xlsx"
)

# Carbon flow ordering for Fermentation parameters
FERM_CARBON_FLOW_ORDER = [
    "sugar_cons",
    "sugart0",
    "gluconct0",
    "xylconct0",
    "sugarteof",
    "gluconcteof",
    "xylconcteof",
    "od600teof",
    "rel_growth",
    "3hptiter",
    "3hpyield",
    "etohtiter",
    "etohyield",
]

FERM_STAGE_LABELS = {
    "sugar_cons": "1. Overall Sugar Consumption",
    "sugart0": "2. Initial Sugars (t = 0 h)",
    "gluconct0": "2. Initial Sugars (t = 0 h)",
    "xylconct0": "2. Initial Sugars (t = 0 h)",
    "sugarteof": "3. Residual Sugars (t = EOF)",
    "gluconcteof": "3. Residual Sugars (t = EOF)",
    "xylconcteof": "3. Residual Sugars (t = EOF)",
    "od600teof": "4. Biomass / Cell Growth",
    "rel_growth": "4. Biomass / Cell Growth",
    "3hptiter": "5. Product: 3-Hydroxypropionic Acid (3-HP)",
    "3hpyield": "5. Product: 3-Hydroxypropionic Acid (3-HP)",
    "etohtiter": "6. Product: Ethanol (EtOH)",
    "etohyield": "6. Product: Ethanol (EtOH)",
}

PALETTE = ["#00B5E2", "#10B981", "#F59E0B", "#6366F1", "#EC4899", "#8B5CF6", "#14B8A6"]


def style_ax(ax: plt.Axes, title: str, ylabel: str = "") -> None:
    ax.set_facecolor("#F8FAFC")
    ax.set_title(title, fontsize=10.5, fontweight="bold", color="#0F172A", loc="left", pad=8)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8.5, fontweight="bold", color="#334155")
    ax.grid(True, axis="y", linestyle="--", linewidth=0.6, color="#CBD5E1", alpha=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#94A3B8")
    ax.tick_params(colors="#334155", labelsize=8)


def _draw_proximate_panel(ax: plt.Axes, records: list[dict]) -> None:
    style_ax(ax, "Proximate Analysis — Sample Profile (Scatter + Mean ± SD)", "% Total Weight")
    params = ["moisture", "total solids", "volatile solids", "ash", "fixed carbon"]
    sub = [r for r in records if r["analysis_type"] == "Proximate Analysis" and r.get("parameter") in params]
    samples = sorted({r.get("prepared_sample") or "" for r in sub if r.get("prepared_sample")})
    sample_colors = {s: PALETTE[i % len(PALETTE)] for i, s in enumerate(samples)}
    markers = ["o", "s", "D", "^", "v", "P"]

    x_positions = np.arange(len(params))
    rng = random.Random(42)

    for p_idx, p in enumerate(params):
        p_vals = [float(r["value"]) for r in sub if r.get("parameter") == p and isinstance(r.get("value"), (int, float))]
        if p_vals:
            m = statistics.mean(p_vals)
            sd = statistics.stdev(p_vals) if len(p_vals) > 1 else 0.0
            ax.hlines(m, p_idx - 0.28, p_idx + 0.28, color="#0F172A", linewidth=2.0, zorder=4)
            if sd > 0:
                ax.vlines(p_idx, max(0, m - sd), m + sd, color="#475569", linewidth=1.2, zorder=3)

        for s_idx, s in enumerate(samples):
            s_vals = [
                float(r["value"])
                for r in sub
                if r.get("parameter") == p and r.get("prepared_sample") == s and isinstance(r.get("value"), (int, float))
            ]
            if not s_vals:
                continue
            offset = (s_idx - (len(samples) - 1) / 2.0) * 0.09
            xs = [p_idx + offset + rng.uniform(-0.02, 0.02) for _ in s_vals]
            ax.scatter(
                xs,
                s_vals,
                color=sample_colors[s],
                marker=markers[s_idx % len(markers)],
                s=38,
                alpha=0.88,
                edgecolors="#0F172A",
                linewidths=0.5,
                label=s if p_idx == 0 else None,
                zorder=5,
            )

    ax.set_xticks(x_positions)
    ax.set_xticklabels([p.title() for p in params], rotation=28, ha="right", fontsize=8.5, fontweight="bold")
    ax.set_xlabel("Proximate Parameter", fontsize=8.5, fontweight="bold", color="#334155", labelpad=4)
    ax.legend(loc="upper right", fontsize=7, frameon=True, facecolor="#FFFFFF", edgecolor="#CBD5E1", ncol=2, title="Prepared Sample", title_fontsize=7.5)


def _draw_compositional_panel(ax: plt.Axes, records: list[dict]) -> None:
    style_ax(ax, "Compositional Analysis — Structural Sugars & Acid-Insol. Lignin", "% Dry Weight")
    params = ["lignin", "glucan", "galactan", "xylan", "mannan", "arabinan"]
    sub = [r for r in records if r["analysis_type"] == "Compositional Analysis" and r.get("parameter") in params]
    samples = sorted({r.get("prepared_sample") or "" for r in sub if r.get("prepared_sample")})
    sample_colors = {s: PALETTE[i % len(PALETTE)] for i, s in enumerate(samples)}
    markers = ["o", "s", "D"]
    rng = random.Random(99)

    for p_idx, p in enumerate(params):
        p_vals = [float(r["value"]) for r in sub if r.get("parameter") == p and isinstance(r.get("value"), (int, float))]
        if p_vals:
            m = statistics.mean(p_vals)
            mn, mx = min(p_vals), max(p_vals)
            ax.fill_between([p_idx - 0.24, p_idx + 0.24], mn, mx, color="#00B5E2", alpha=0.14, zorder=2)
            ax.hlines(m, p_idx - 0.24, p_idx + 0.24, color="#0F172A", linewidth=2.0, zorder=4)

        for s_idx, s in enumerate(samples):
            s_vals = [
                float(r["value"])
                for r in sub
                if r.get("parameter") == p and r.get("prepared_sample") == s and isinstance(r.get("value"), (int, float))
            ]
            if not s_vals:
                continue
            offset = (s_idx - (len(samples) - 1) / 2.0) * 0.11
            xs = [p_idx + offset + rng.uniform(-0.02, 0.02) for _ in s_vals]
            ax.scatter(
                xs,
                s_vals,
                color=sample_colors[s],
                marker=markers[s_idx % len(markers)],
                s=44,
                alpha=0.9,
                edgecolors="#0F172A",
                linewidths=0.5,
                label=s if p_idx == 0 else None,
                zorder=5,
            )

    ax.set_xticks(range(len(params)))
    ax.set_xticklabels([p.title() for p in params], rotation=28, ha="right", fontsize=8.5, fontweight="bold")
    ax.set_xlabel("Compositional Parameter", fontsize=8.5, fontweight="bold", color="#334155", labelpad=4)
    ax.legend(loc="upper right", fontsize=7.5, frameon=True, facecolor="#FFFFFF", edgecolor="#CBD5E1", title="Prepared Sample", title_fontsize=7.5)


def _draw_icp_panel(ax: plt.Axes, records: list[dict]) -> None:
    style_ax(ax, "ICP Elemental Profile — Log10 Concentration & QC Status", "Log10(Concentration in ppm)")
    sub = [r for r in records if r["analysis_type"] == "ICP Elemental Analysis"]
    by_el: dict[str, list[dict]] = defaultdict(list)
    for r in sub:
        if r.get("parameter"):
            by_el[str(r["parameter"])].append(r)

    ordered_els = [
        el
        for el, _ in sorted(
            by_el.items(),
            key=lambda kv: -statistics.mean([float(x["value"]) for x in kv[1] if isinstance(x.get("value"), (int, float))] or [0.0]),
        )
    ]

    for idx, el in enumerate(ordered_els):
        grp = by_el[el]
        ys = []
        for r in grp:
            v = float(r.get("value") or 0.0)
            y_log = math.log10(max(v, 0.01))
            ys.append(y_log)
            is_pass = str(r.get("qc_status")).lower() == "pass"
            samp = r.get("prepared_sample") or ""
            offset = -0.12 if "031" in samp else 0.12
            ax.scatter(
                [idx + offset],
                [y_log],
                color="#10B981" if is_pass else "#EF4444",
                marker="o" if "031" in samp else "s",
                s=46,
                edgecolors="#0F172A",
                linewidths=0.6,
                zorder=5,
            )
        if ys:
            ax.vlines(idx, min(ys), max(ys), color="#64748B", linewidth=1.5, zorder=3)
            ax.hlines(statistics.mean(ys), idx - 0.2, idx + 0.2, color="#0F172A", linewidth=1.8, zorder=4)

    ax.set_xticks(range(len(ordered_els)))
    ax.set_xticklabels([el.upper() for el in ordered_els], fontsize=8.5, fontweight="bold")
    ax.set_xlabel("ICP Element (Ordered by Mean Concentration)", fontsize=8.5, fontweight="bold", color="#334155", labelpad=5)
    # Custom legend for QC Pass / Fail + Sample shape
    ax.scatter([], [], color="#10B981", marker="o", s=42, edgecolors="#0F172A", label="QC Pass (hai-sarg031okm2)")
    ax.scatter([], [], color="#10B981", marker="s", s=42, edgecolors="#0F172A", label="QC Pass (hai-sarg032okm2)")
    ax.scatter([], [], color="#EF4444", marker="o", s=42, edgecolors="#0F172A", label="QC Fail (Trace Cd/Co/Pb)")
    ax.legend(loc="upper right", fontsize=7.5, frameon=True, facecolor="#FFFFFF", edgecolor="#CBD5E1")


def _draw_pretreatment_panel(ax: plt.Axes, records: list[dict]) -> None:
    style_ax(ax, "Pretreatment & Hydrolysis — Method Variance (Replicate Strip/Scatter)", "Sugar Yield (mg/g biomass)")
    sub = [r for r in records if r["analysis_type"] == "Pretreatment & Hydrolysis"]
    methods = sorted({r.get("pt_method") or "" for r in sub if r.get("pt_method")})
    samples = sorted({r.get("prepared_sample") or "" for r in sub if r.get("prepared_sample")})
    sample_markers = {s: m for s, m in zip(samples, ["o", "s", "D"])}
    param_colors = {"glucose_yld": "#00B5E2", "xylose_yld": "#F59E0B"}
    rng = random.Random(77)

    for m_idx, m in enumerate(methods):
        for p_idx, p in enumerate(["glucose_yld", "xylose_yld"]):
            lane_x = m_idx + (-0.18 if p_idx == 0 else 0.18)
            grp = [r for r in sub if r.get("pt_method") == m and r.get("parameter") == p]
            vals = [float(r["value"]) for r in grp if isinstance(r.get("value"), (int, float))]
            if vals:
                mean_v = statistics.mean(vals)
                ax.vlines(lane_x, min(vals), max(vals), color=param_colors[p], linewidth=3.5, alpha=0.32, zorder=2)
                ax.hlines(mean_v, lane_x - 0.11, lane_x + 0.11, color="#0F172A", linewidth=2.0, zorder=4)
            for r in grp:
                v = float(r["value"])
                s = r.get("prepared_sample") or ""
                ax.scatter(
                    [lane_x + rng.uniform(-0.04, 0.04)],
                    [v],
                    color=param_colors[p],
                    marker=sample_markers.get(s, "o"),
                    s=44,
                    alpha=0.92,
                    edgecolors="#0F172A",
                    linewidths=0.6,
                    zorder=5,
                )

    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels(methods, rotation=25, ha="right", fontsize=8.5, fontweight="bold")
    ax.set_xlabel("Pretreatment Method", fontsize=8.5, fontweight="bold", color="#334155", labelpad=4)
    ax.scatter([], [], color="#00B5E2", marker="o", s=44, edgecolors="#0F172A", label="glucose_yld (mg/g)")
    ax.scatter([], [], color="#F59E0B", marker="s", s=44, edgecolors="#0F172A", label="xylose_yld (mg/g)")
    ax.legend(loc="upper left", fontsize=7.5, frameon=True, facecolor="#FFFFFF", edgecolor="#CBD5E1")


def _draw_fermentation_panel(ax: plt.Axes, records: list[dict]) -> None:
    style_ax(
        ax,
        "Fermentation (R. toruloides MCR-ALD6-g2945) — Carbon Flow: Sugar Consumption -> T0 -> TEOF -> Growth -> 3-HP & EtOH",
        "Measured Value (g/L, %, or OD)",
    )
    sub = [r for r in records if r["analysis_type"] == "Fermentation (Bioconversion)"]
    params = [p for p in FERM_CARBON_FLOW_ORDER if any(r.get("parameter") == p for r in sub)]
    samples = sorted({r.get("prepared_sample") or "" for r in sub if r.get("prepared_sample")})
    sample_colors = {s: PALETTE[i % len(PALETTE)] for i, s in enumerate(samples)}
    sample_markers = ["o", "s", "D", "^"]
    rng = random.Random(123)

    # Shaded stage bands
    stage_spans = [
        (0, 0, "Consumption", "#E0F2FE"),
        (1, 3, "Initial Sugars (t0)", "#F1F5F9"),
        (4, 6, "Residual Sugars (tEOF)", "#FEF3C7"),
        (7, 8, "Growth", "#DCFCE7"),
        (9, 10, "3-HP Product", "#EDE9FE"),
        (11, 12, "Ethanol Product", "#FCE7F3"),
    ]
    for s_start, s_end, s_label, s_col in stage_spans:
        if s_start < len(params):
            ax.axvspan(s_start - 0.45, min(s_end, len(params) - 1) + 0.45, color=s_col, alpha=0.38, zorder=1)

    for p_idx, p in enumerate(params):
        p_vals = [float(r["value"]) for r in sub if r.get("parameter") == p and isinstance(r.get("value"), (int, float))]
        if p_vals:
            m = statistics.mean(p_vals)
            sd = statistics.stdev(p_vals) if len(p_vals) > 1 else 0.0
            ax.hlines(m, p_idx - 0.28, p_idx + 0.28, color="#0F172A", linewidth=2.0, zorder=4)
            if sd > 0:
                ax.vlines(p_idx, max(0, m - sd), m + sd, color="#475569", linewidth=1.2, zorder=3)

        for s_idx, s in enumerate(samples):
            s_vals = [
                float(r["value"])
                for r in sub
                if r.get("parameter") == p and r.get("prepared_sample") == s and isinstance(r.get("value"), (int, float))
            ]
            if not s_vals:
                continue
            offset = (s_idx - (len(samples) - 1) / 2.0) * 0.14
            xs = [p_idx + offset + rng.uniform(-0.025, 0.025) for _ in s_vals]
            ax.scatter(
                xs,
                s_vals,
                color=sample_colors[s],
                marker=sample_markers[s_idx % len(sample_markers)],
                s=38,
                alpha=0.9,
                edgecolors="#0F172A",
                linewidths=0.45,
                label=s if p_idx == 0 else None,
                zorder=5,
            )

    ax.set_xticks(range(len(params)))
    ax.set_xticklabels(params, rotation=35, ha="right", fontsize=8.5, fontweight="bold")
    ax.set_xlabel("Fermentation Parameter (Ordered by Carbon Flow Stage)", fontsize=8.5, fontweight="bold", color="#334155", labelpad=5)
    ax.legend(
        loc="upper right",
        fontsize=8,
        frameon=True,
        facecolor="#FFFFFF",
        edgecolor="#CBD5E1",
        ncol=3,
        title="Prepared Sample (Strain: R. toruloides MCR-ALD6-g2945 · PT: cho10pc)",
        title_fontsize=8,
    )


def render_fig_bytes(fig: plt.Figure, dpi: int = 180) -> tuple[bytes, int, int]:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0.14, facecolor="#FFFFFF")
    png_bytes = buf.getvalue()
    w_px = int.from_bytes(png_bytes[16:20], "big")
    h_px = int.from_bytes(png_bytes[20:24], "big")
    plt.close(fig)
    return png_bytes, w_px, h_px


def build_all_chart_images(records: list[dict]) -> dict[str, tuple[bytes, int, int]]:
    images: dict[str, tuple[bytes, int, int]] = {}

    # 1. Master 5-panel overview dashboard
    fig = plt.figure(figsize=(13.5, 10.6), facecolor="#FFFFFF")
    gs = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.0, 1.2], hspace=0.52, wspace=0.18)
    fig.suptitle(
        "CA-BIOSITING SARGASSUM VISUAL EXPLORER — MULTI-DOMAIN ANALYTICAL & BIOCONVERSION DASHBOARD",
        fontsize=13,
        fontweight="bold",
        color="#0F172A",
        y=0.985,
    )
    _draw_proximate_panel(fig.add_subplot(gs[0, 0]), records)
    _draw_compositional_panel(fig.add_subplot(gs[0, 1]), records)
    _draw_icp_panel(fig.add_subplot(gs[1, 0]), records)
    _draw_pretreatment_panel(fig.add_subplot(gs[1, 1]), records)
    _draw_fermentation_panel(fig.add_subplot(gs[2, :]), records)
    images["overview"] = render_fig_bytes(fig, dpi=150)

    # 2. Proximate + Compositional dual chart
    fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(12.5, 4.0), facecolor="#FFFFFF")
    fig2.subplots_adjust(wspace=0.2)
    _draw_proximate_panel(ax2a, records)
    _draw_compositional_panel(ax2b, records)
    images["prox_comp"] = render_fig_bytes(fig2, dpi=150)

    # 3. ICP Elemental chart
    fig3, ax3 = plt.subplots(figsize=(11.5, 3.8), facecolor="#FFFFFF")
    _draw_icp_panel(ax3, records)
    images["icp"] = render_fig_bytes(fig3, dpi=150)

    # 4. Pretreatment & Hydrolysis chart
    fig4, ax4 = plt.subplots(figsize=(11.5, 3.8), facecolor="#FFFFFF")
    _draw_pretreatment_panel(ax4, records)
    images["pretreatment"] = render_fig_bytes(fig4, dpi=150)

    # 5. Fermentation (Carbon Flow) chart
    fig5, ax5 = plt.subplots(figsize=(12.5, 4.2), facecolor="#FFFFFF")
    _draw_fermentation_panel(ax5, records)
    images["fermentation"] = render_fig_bytes(fig5, dpi=150)

    return images


def col_letter(idx_1based: int) -> str:
    result = []
    n = idx_1based
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result.append(chr(65 + rem))
    return "".join(reversed(result))


STYLE_DEFAULT = 0
STYLE_TITLE = 1
STYLE_SUBTITLE = 2
STYLE_SECTION = 3
STYLE_HEADER = 4
STYLE_TEXT = 5
STYLE_NUM2 = 6
STYLE_INT = 7
STYLE_KEY = 8
STYLE_QC_PASS = 9
STYLE_QC_FAIL = 10
STYLE_SUM_TEXT = 11
STYLE_SUM_NUM2 = 12


def build_styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <numFmts count="2">
    <numFmt numFmtId="164" formatCode="0.00"/>
    <numFmt numFmtId="165" formatCode="#,##0"/>
  </numFmts>
  <fonts count="8">
    <font><sz val="10"/><color rgb="FF0F172A"/><name val="Calibri"/></font>
    <font><b/><sz val="14"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
    <font><i/><sz val="10"/><color rgb="FFE2E8F0"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
    <font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
    <font><b/><sz val="10"/><color rgb="FF0F172A"/><name val="Calibri"/></font>
    <font><b/><sz val="10"/><color rgb="FF166534"/><name val="Calibri"/></font>
    <font><b/><sz val="10"/><color rgb="FF991B1B"/><name val="Calibri"/></font>
  </fonts>
  <fills count="9">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF0F172A"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1E293B"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF0F766E"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF8FAFC"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFDCFCE7"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFEE2E2"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFEFF6FF"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border>
      <left style="thin"><color rgb="FFCBD5E1"/></left>
      <right style="thin"><color rgb="FFCBD5E1"/></right>
      <top style="thin"><color rgb="FFCBD5E1"/></top>
      <bottom style="thin"><color rgb="FFCBD5E1"/></bottom>
      <diagonal/>
    </border>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="13">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">
      <alignment vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="2" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">
      <alignment vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="3" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="4" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment vertical="center" wrapText="1"/>
    </xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment vertical="center"/>
    </xf>
    <xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="right" vertical="center"/>
    </xf>
    <xf numFmtId="165" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="right" vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="5" fillId="5" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="6" fillId="6" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="7" fillId="7" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="5" fillId="8" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment vertical="center"/>
    </xf>
    <xf numFmtId="164" fontId="5" fillId="8" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="right" vertical="center"/>
    </xf>
  </cellXfs>
  <cellStyles count="1">
    <cellStyle name="Normal" xfId="0" builtinId="0"/>
  </cellStyles>
  <dxfs count="0"/>
  <tableStyles count="0" defaultTableStyle="TableStyleMedium2" defaultPivotStyle="PivotStyleLight16"/>
</styleSheet>
"""


class SheetDrawing:
    def __init__(self, png_bytes: bytes, width_px: int, height_px: int, anchor_col: int = 0, anchor_row: int = 3):
        self.png_bytes = png_bytes
        self.width_px = width_px
        self.height_px = height_px
        self.anchor_col = anchor_col
        self.anchor_row = anchor_row


class SheetSpec:
    def __init__(
        self,
        title: str,
        rows: list[list[tuple[object, int]]],
        col_widths: list[int] | None = None,
        freeze_row: int | None = None,
        autofilter_ref: str | None = None,
        merges: list[str] | None = None,
        drawing: SheetDrawing | None = None,
    ):
        self.title = title
        self.rows = rows
        self.col_widths = col_widths or []
        self.freeze_row = freeze_row
        self.autofilter_ref = autofilter_ref
        self.merges = merges or []
        self.drawing = drawing


def render_sheet_xml(spec: SheetSpec, has_drawing: bool = False) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
    ]

    if spec.freeze_row and spec.freeze_row > 0:
        top_left = f"A{spec.freeze_row + 1}"
        lines.append("  <sheetViews>")
        lines.append('    <sheetView workbookViewId="0">')
        lines.append(
            f'      <pane ySplit="{spec.freeze_row}" topLeftCell="{top_left}" '
            'activePane="bottomLeft" state="frozen"/>'
        )
        lines.append("    </sheetView>")
        lines.append("  </sheetViews>")
    else:
        lines.append('  <sheetViews><sheetView workbookViewId="0"/></sheetViews>')

    lines.append('  <sheetFormatPr defaultRowHeight="18"/>')

    max_cols = max((len(r) for r in spec.rows), default=1)
    widths = list(spec.col_widths)
    if len(widths) < max_cols:
        for c_idx in range(len(widths), max_cols):
            max_len = 10
            for r in spec.rows:
                if c_idx < len(r) and r[c_idx][0] is not None:
                    cell_style = r[c_idx][1]
                    if cell_style in (STYLE_TITLE, STYLE_SUBTITLE, STYLE_SECTION):
                        continue
                    s_val = str(r[c_idx][0])
                    max_len = max(max_len, min(len(s_val) + 4, 42))
            widths.append(max_len)

    if widths:
        lines.append("  <cols>")
        for i, w in enumerate(widths, start=1):
            lines.append(f'    <col min="{i}" max="{i}" width="{w}" customWidth="1"/>')
        lines.append("  </cols>")

    lines.append("  <sheetData>")
    for r_idx, row in enumerate(spec.rows, start=1):
        row_h = 19
        if row and row[0][1] == STYLE_TITLE:
            row_h = 28
        elif row and row[0][1] == STYLE_SUBTITLE:
            row_h = 20
        elif row and row[0][1] == STYLE_SECTION:
            row_h = 24
        elif row and row[0][1] == STYLE_HEADER:
            row_h = 25

        lines.append(f'    <row r="{r_idx}" ht="{row_h}" customHeight="1">')
        for c_idx, (val, style_id) in enumerate(row, start=1):
            ref = f"{col_letter(c_idx)}{r_idx}"
            if val is None or val == "":
                lines.append(f'      <c r="{ref}" s="{style_id}"/>')
            elif isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val):
                lines.append(f'      <c r="{ref}" s="{style_id}"><v>{val}</v></c>')
            else:
                text = escape(str(val))
                lines.append(
                    f'      <c r="{ref}" s="{style_id}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'
                )
        lines.append("    </row>")
    lines.append("  </sheetData>")

    if spec.autofilter_ref:
        lines.append(f'  <autoFilter ref="{spec.autofilter_ref}"/>')

    if spec.merges:
        lines.append(f'  <mergeCells count="{len(spec.merges)}">')
        for m in spec.merges:
            lines.append(f'    <mergeCell ref="{m}"/>')
        lines.append("  </mergeCells>")

    if has_drawing:
        lines.append('  <drawing r:id="rId1"/>')

    lines.append("</worksheet>")
    return "\n".join(lines)


def build_drawing_xml(drawing: SheetDrawing, pic_id: int) -> str:
    # Convert pixel dimensions at 150 DPI to display size in EMUs (9525 EMU per 96-DPI pixel)
    scale = 96.0 / 150.0
    cx = int(drawing.width_px * scale * 9525)
    cy = int(drawing.height_px * scale * 9525)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
          xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <xdr:oneCellAnchor>
    <xdr:from>
      <xdr:col>{drawing.anchor_col}</xdr:col>
      <xdr:colOff>0</xdr:colOff>
      <xdr:row>{drawing.anchor_row}</xdr:row>
      <xdr:rowOff>0</xdr:rowOff>
    </xdr:from>
    <xdr:ext cx="{cx}" cy="{cy}"/>
    <xdr:pic>
      <xdr:nvPicPr>
        <xdr:cNvPr id="{pic_id}" name="Chart {pic_id}" descr="Sargassum Visual Chart"/>
        <xdr:cNvPicPr>
          <a:picLocks noChangeAspect="1"/>
        </xdr:cNvPicPr>
      </xdr:nvPicPr>
      <xdr:blipFill>
        <a:blip r:embed="rId1"/>
        <a:stretch><a:fillRect/></a:stretch>
      </xdr:blipFill>
      <xdr:spPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="{cx}" cy="{cy}"/>
        </a:xfrm>
        <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
      </xdr:spPr>
    </xdr:pic>
    <xdr:clientData/>
  </xdr:oneCellAnchor>
</xdr:wsDr>
"""


def fmt_mean_sd(vals: list[float]) -> str:
    if not vals:
        return "—"
    if len(vals) == 1:
        return f"{vals[0]:.2f} (n=1)"
    m = statistics.mean(vals)
    sd = statistics.stdev(vals)
    return f"{m:.2f} ± {sd:.2f} (n={len(vals)})"


def qc_cell(qc_val: object) -> tuple[str, int]:
    s = str(qc_val or "").strip().lower()
    if s == "pass":
        return ("PASS", STYLE_QC_PASS)
    if s == "fail":
        return ("FAIL", STYLE_QC_FAIL)
    return (s.upper() if s else "N/A", STYLE_TEXT)


def num_or_text(val: object, style_num: int = STYLE_NUM2) -> tuple[object, int]:
    if isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val):
        return (float(val), style_num)
    return ("" if val is None else str(val), STYLE_TEXT)


def banner_rows(title: str, subtitle: str, num_cols: int) -> tuple[list[list[tuple[object, int]]], list[str]]:
    row1 = [(title if i == 0 else "", STYLE_TITLE) for i in range(num_cols)]
    row2 = [(subtitle if i == 0 else "", STYLE_SUBTITLE) for i in range(num_cols)]
    end_col = col_letter(num_cols)
    merges = [f"A1:{end_col}1", f"A2:{end_col}2"]
    return [row1, row2, [("", STYLE_DEFAULT)]], merges


def section_row(label: str, num_cols: int, row_num: int) -> tuple[list[tuple[object, int]], str]:
    row = [(label if i == 0 else "", STYLE_SECTION) for i in range(num_cols)]
    end_col = col_letter(num_cols)
    return row, f"A{row_num}:{end_col}{row_num}"


def build_sheets(payload: dict, chart_images: dict[str, tuple[bytes, int, int]]) -> list[SheetSpec]:
    resource = payload["resource"]
    field_samples = payload["field_samples"]
    prepared_samples = payload["prepared_samples"]
    records = payload["records"]

    # -------------------------------------------------------------------------
    # SHEET 0: Visual Dashboard (Multi-Panel Overview Chart)
    # -------------------------------------------------------------------------
    s0_cols = 10
    s0_rows, s0_merges = banner_rows(
        "CA-BIOSITING SARGASSUM VISUAL EXPLORER — ANALYTICAL & BIOCONVERSION DASHBOARD",
        "Visual Overview of All 252 Observations Across Proximate, Compositional, ICP Elemental, Pretreatment, and Carbon-Flow Fermentation",
        s0_cols,
    )
    # Add spacer rows behind the multi-panel visual figure
    for _ in range(52):
        s0_rows.append([("", STYLE_DEFAULT)])

    ov_bytes, ov_w, ov_h = chart_images["overview"]
    sheet0 = SheetSpec(
        title="Visual Dashboard",
        rows=s0_rows,
        col_widths=[18] * s0_cols,
        freeze_row=2,
        merges=s0_merges,
        drawing=SheetDrawing(ov_bytes, ov_w, ov_h, anchor_col=0, anchor_row=3),
    )

    # -------------------------------------------------------------------------
    # SHEET 1: Executive Summary
    # -------------------------------------------------------------------------
    s1_cols = 9
    s1_rows, s1_merges = banner_rows(
        "CA-BIOSITING ANALYTICAL & BIOCONVERSION REPORT — SARGASSUM (MACROALGAE)",
        "Self-Contained Collaborator Workbook · Prepared Samples, Compositional, Elemental, Pretreatment & Bioconversion Data",
        s1_cols,
    )

    sec_r, sec_m = section_row("1. RESOURCE OVERVIEW & DATASET SCOPE", s1_cols, len(s1_rows) + 1)
    s1_rows.append(sec_r)
    s1_merges.append(sec_m)

    total_pass = sum(1 for r in records if str(r.get("qc_status")).lower() == "pass")
    total_fail = sum(1 for r in records if str(r.get("qc_status")).lower() == "fail")

    meta_pairs = [
        ("Resource Name", resource.get("name", "sargassum"), "Resource Class", resource.get("resource_class", "macroalgae")),
        ("Resource Code", resource.get("resource_code", "sarg"), "Sampling Provider", "hairpin (California, GEOID 06000)"),
        ("Field Samples", f"{len(field_samples)} (hai-sarg025, hai-sarg031, hai-sarg032)", "Prepared Samples", f"{len(prepared_samples)} (as-is, knife-milled 2mm, oven-dried + knife-milled 2mm)"),
        ("Total Observations", f"{len(records)} analytical & bioconversion measurements", "QC Breakdown", f"{total_pass} QC Pass ({total_pass / len(records) * 100:.1f}%) · {total_fail} QC Fail"),
        ("Resource Description", resource.get("description", ""), "How to Use This File", "Click 'Visual Dashboard' for charts or any analysis tab below to filter rows."),
    ]
    for k1, v1, k2, v2 in meta_pairs:
        s1_rows.append([
            (k1, STYLE_KEY),
            (v1, STYLE_TEXT),
            ("", STYLE_TEXT),
            ("", STYLE_TEXT),
            (k2, STYLE_KEY),
            (v2, STYLE_TEXT),
            ("", STYLE_TEXT),
            ("", STYLE_TEXT),
            ("", STYLE_TEXT),
        ])
        r_idx = len(s1_rows)
        s1_merges.extend([f"B{r_idx}:D{r_idx}", f"F{r_idx}:I{r_idx}"])

    s1_rows.append([("", STYLE_DEFAULT)])

    sec_r, sec_m = section_row("2. OBSERVATION BREAKDOWN BY ANALYSIS TYPE", s1_cols, len(s1_rows) + 1)
    s1_rows.append(sec_r)
    s1_merges.append(sec_m)

    s1_rows.append([
        ("Analysis Type", STYLE_HEADER),
        ("Total Obs", STYLE_HEADER),
        ("QC Pass", STYLE_HEADER),
        ("QC Fail", STYLE_HEADER),
        ("Prepared Samples", STYLE_HEADER),
        ("Distinct Parameters", STYLE_HEADER),
        ("Primary Experimental Methods / Strains", STYLE_HEADER),
        ("Workbook Tab", STYLE_HEADER),
        ("Key Takeaway", STYLE_HEADER),
    ])

    analysis_order = [
        ("Proximate Analysis", "Proximate & Compositional", "Wet as-is sample (hai-sarg032a) is ~81% moisture; dried samples have ~31–44% ash."),
        ("Compositional Analysis", "Proximate & Compositional", "Structural carbohydrates dominated by glucan (6.2–8.3%) & acid-insoluble residue (13.6–17.3%)."),
        ("Calorimetry", "Proximate & Compositional", "Higher heating value (HHV) measured at 9.75 MJ/kg on hai-sarg025a(0d)."),
        ("ICP Elemental Analysis", "ICP Elemental Analysis", "High Ca (12,535–13,343 ppm) and Mg (9,561–9,927 ppm); trace Cd/Co/Pb flagged in QC."),
        ("Pretreatment & Hydrolysis", "Pretreatment & Hydrolysis", "4 pretreatment regimes tested (butknt140c, cho10pc, h2o140c, none20c) for glucose & xylose yield."),
        ("Fermentation (Bioconversion)", "Fermentation (Carbon Flow)", "4 microbial strains evaluated across carbon flow (sugar consumption -> growth -> 3-HP & ethanol)."),
    ]

    for atype, tab_ref, takeaway in analysis_order:
        sub = [r for r in records if r["analysis_type"] == atype]
        n_tot = len(sub)
        n_pass = sum(1 for r in sub if str(r.get("qc_status")).lower() == "pass")
        n_fail = n_tot - n_pass
        n_samps = len({r["prepared_sample"] for r in sub if r.get("prepared_sample")})
        n_params = len({r["parameter"] for r in sub if r.get("parameter")})
        methods = sorted({
            str(r.get("strain") or r.get("pt_method") or r.get("method") or "")
            for r in sub
            if (r.get("strain") or r.get("pt_method") or r.get("method"))
        })
        s1_rows.append([
            (atype, STYLE_KEY),
            (n_tot, STYLE_INT),
            (n_pass, STYLE_INT),
            (n_fail, STYLE_INT),
            (n_samps, STYLE_INT),
            (n_params, STYLE_INT),
            (", ".join(methods), STYLE_TEXT),
            (tab_ref, STYLE_TEXT),
            (takeaway, STYLE_TEXT),
        ])

    s1_rows.append([
        ("TOTAL DATASET", STYLE_SUM_TEXT),
        (len(records), STYLE_INT),
        (total_pass, STYLE_INT),
        (total_fail, STYLE_INT),
        (len(prepared_samples), STYLE_INT),
        (len({r["parameter"] for r in records if r.get("parameter")}), STYLE_INT),
        ("All 6 workflows included", STYLE_SUM_TEXT),
        ("All Observations (Master)", STYLE_SUM_TEXT),
        ("Complete 252-observation dataset with full sample lineage", STYLE_SUM_TEXT),
    ])

    s1_rows.append([("", STYLE_DEFAULT)])

    sec_r, sec_m = section_row(
        "3. COMPLETE PARAMETER SUMMARY TABLE (QC-PASSED OBSERVATIONS, FERMENTATION ORDERED BY CARBON FLOW)",
        s1_cols,
        len(s1_rows) + 1,
    )
    s1_rows.append(sec_r)
    s1_merges.append(sec_m)

    param_header_row = len(s1_rows) + 1
    s1_rows.append([
        ("Analysis Type", STYLE_HEADER),
        ("Parameter", STYLE_HEADER),
        ("Parameter Description / Carbon Flow Stage", STYLE_HEADER),
        ("Unit", STYLE_HEADER),
        ("N (QC Pass)", STYLE_HEADER),
        ("Mean", STYLE_HEADER),
        ("Std Dev (SD)", STYLE_HEADER),
        ("Min", STYLE_HEADER),
        ("Max", STYLE_HEADER),
    ])

    by_atype_param: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in records:
        pname = str(r.get("parameter") or "").strip()
        if not pname:
            continue
        by_atype_param[(r["analysis_type"], pname)].append(r)

    def param_sort_key(item: tuple[tuple[str, str], list[dict]]) -> tuple[int, int, str]:
        (atype, param), _ = item
        param_s = str(param or "")
        atype_idx = next((i for i, (a, _, _) in enumerate(analysis_order) if a == atype), 99)
        if atype == "Fermentation (Bioconversion)":
            c_idx = FERM_CARBON_FLOW_ORDER.index(param_s) if param_s in FERM_CARBON_FLOW_ORDER else 99
            return (atype_idx, c_idx, param_s)
        return (atype_idx, 0, param_s)

    for (atype, param), grp in sorted(by_atype_param.items(), key=param_sort_key):
        pass_vals = [
            float(r["value"])
            for r in grp
            if str(r.get("qc_status")).lower() == "pass" and isinstance(r.get("value"), (int, float))
        ]
        all_vals = [float(r["value"]) for r in grp if isinstance(r.get("value"), (int, float))]
        use_vals = pass_vals if pass_vals else all_vals
        unit = next((r.get("unit") for r in grp if r.get("unit")), "") or "—"
        desc = next((r.get("parameter_desc") for r in grp if r.get("parameter_desc")), "") or ""
        if atype == "Fermentation (Bioconversion)" and param in FERM_STAGE_LABELS:
            desc = f"{FERM_STAGE_LABELS[param]}" + (f" — {desc}" if desc else "")
        if not pass_vals and all_vals:
            desc = (desc + " [QC Fail only]").strip()

        mean_v = statistics.mean(use_vals) if use_vals else None
        sd_v = statistics.stdev(use_vals) if len(use_vals) > 1 else 0.0
        min_v = min(use_vals) if use_vals else None
        max_v = max(use_vals) if use_vals else None

        s1_rows.append([
            (atype, STYLE_TEXT),
            (param, STYLE_KEY),
            (desc, STYLE_TEXT),
            (unit, STYLE_TEXT),
            (len(pass_vals), STYLE_INT),
            num_or_text(mean_v),
            num_or_text(sd_v),
            num_or_text(min_v),
            num_or_text(max_v),
        ])

    sheet1 = SheetSpec(
        title="Executive Summary",
        rows=s1_rows,
        col_widths=[28, 18, 42, 16, 13, 13, 14, 13, 13],
        freeze_row=2,
        autofilter_ref=f"A{param_header_row}:I{len(s1_rows)}",
        merges=s1_merges,
    )

    # -------------------------------------------------------------------------
    # SHEET 2: Sample Lineage
    # -------------------------------------------------------------------------
    s2_cols = 10
    s2_rows, s2_merges = banner_rows(
        "SARGASSUM SAMPLE LINEAGE — FIELD COLLECTION & LABORATORY PREPARATION",
        "Complete traceability from 3 coastal field collections (Hairpin) to 6 laboratory-prepared analytical samples",
        s2_cols,
    )

    sec_r, sec_m = section_row("1. FIELD COLLECTION SAMPLES (3 SAMPLES)", s2_cols, len(s2_rows) + 1)
    s2_rows.append(sec_r)
    s2_merges.append(sec_m)

    s2_rows.append([
        ("Field Sample Name", STYLE_HEADER),
        ("Resource", STYLE_HEADER),
        ("Provider", STYLE_HEADER),
        ("Collection Timestamp", STYLE_HEADER),
        ("Collection Method", STYLE_HEADER),
        ("Sample Source", STYLE_HEADER),
        ("Field Storage", STYLE_HEADER),
        ("Location GEOID", STYLE_HEADER),
        ("Derived Prepared Samples", STYLE_HEADER),
        ("Total Observations", STYLE_HEADER),
    ])

    for fs in field_samples:
        fname = fs["name"]
        derived = sorted({ps["name"] for ps in prepared_samples if ps.get("field_sample") == fname})
        n_obs = sum(1 for r in records if r.get("field_sample") == fname)
        s2_rows.append([
            (fname, STYLE_KEY),
            (fs.get("resource") or "sargassum", STYLE_TEXT),
            (fs.get("provider") or "hairpin", STYLE_TEXT),
            (fs.get("collection_timestamp") or "—", STYLE_TEXT),
            (fs.get("collection_method") or "—", STYLE_TEXT),
            (fs.get("sample_source") or "—", STYLE_TEXT),
            (fs.get("field_storage") or "—", STYLE_TEXT),
            (fs.get("geoid") or "06000", STYLE_TEXT),
            (", ".join(derived), STYLE_TEXT),
            (n_obs, STYLE_INT),
        ])

    s2_rows.append([("", STYLE_DEFAULT)])

    sec_r, sec_m = section_row("2. LABORATORY PREPARED SAMPLES (6 SAMPLES)", s2_cols, len(s2_rows) + 1)
    s2_rows.append(sec_r)
    s2_merges.append(sec_m)

    ps_header_row = len(s2_rows) + 1
    s2_rows.append([
        ("Prepared Sample Name", STYLE_HEADER),
        ("Parent Field Sample", STYLE_HEADER),
        ("Preparation Method", STYLE_HEADER),
        ("Prep Date", STYLE_HEADER),
        ("Total Obs", STYLE_HEADER),
        ("QC Pass", STYLE_HEADER),
        ("QC Fail", STYLE_HEADER),
        ("Analyses Performed on Sample", STYLE_HEADER),
        ("Notes", STYLE_HEADER),
    ])

    for ps in prepared_samples:
        pname = ps["name"]
        sub = [r for r in records if r.get("prepared_sample") == pname]
        n_tot = len(sub)
        n_pass = sum(1 for r in sub if str(r.get("qc_status")).lower() == "pass")
        n_fail = n_tot - n_pass
        analyses = sorted({r["analysis_type"] for r in sub})
        s2_rows.append([
            (pname, STYLE_KEY),
            (ps.get("field_sample") or "—", STYLE_TEXT),
            (ps.get("prep_method") or "—", STYLE_TEXT),
            (ps.get("prep_date") or "—", STYLE_TEXT),
            (n_tot, STYLE_INT),
            (n_pass, STYLE_INT),
            (n_fail, STYLE_INT),
            (", ".join(analyses), STYLE_TEXT),
            (ps.get("note") or "", STYLE_TEXT),
        ])

    sheet2 = SheetSpec(
        title="Sample Lineage",
        rows=s2_rows,
        col_widths=[24, 18, 28, 20, 14, 14, 14, 44, 24, 16],
        freeze_row=2,
        autofilter_ref=f"A{ps_header_row}:I{len(s2_rows)}",
        merges=s2_merges,
    )

    # -------------------------------------------------------------------------
    # SHEET 3: Proximate & Compositional (Includes embedded visual chart at top)
    # -------------------------------------------------------------------------
    s3_cols = 13
    s3_rows, s3_merges = banner_rows(
        "PROXIMATE, COMPOSITIONAL & CALORIMETRY ANALYSIS (62 OBSERVATIONS)",
        "Moisture, Ash, Volatile/Total Solids, Fixed Carbon, Structural Carbohydrates (Glucan, Xylan, etc.), Lignin & HHV",
        s3_cols,
    )
    for _ in range(21):
        s3_rows.append([("", STYLE_DEFAULT)])

    sec_r, sec_m = section_row(
        "1. PREPARED SAMPLE SUMMARY MATRIX (MEAN ± SD ACROSS REPLICATES)", s3_cols, len(s3_rows) + 1
    )
    s3_rows.append(sec_r)
    s3_merges.append(sec_m)

    prox_comp_records = [
        r
        for r in records
        if r["analysis_type"] in ("Proximate Analysis", "Compositional Analysis", "Calorimetry")
    ]

    summary_params = [
        ("moisture", "Moisture (%)"),
        ("total solids", "Total Solids (%)"),
        ("volatile solids", "Volatile Solids (%)"),
        ("ash", "Ash (%)"),
        ("fixed carbon", "Fixed Carbon (%)"),
        ("glucan", "Glucan (%)"),
        ("xylan", "Xylan (%)"),
        ("arabinan", "Arabinan (%)"),
        ("galactan", "Galactan (%)"),
        ("mannan", "Mannan (%)"),
        ("lignin", "Acid-Insol. Lignin (%)"),
        ("higher_heating_value", "HHV (MJ/kg)"),
    ]

    s3_rows.append(
        [("Prepared Sample (Prep Method)", STYLE_HEADER)]
        + [(label, STYLE_HEADER) for _, label in summary_params]
    )

    for ps in prepared_samples:
        pname = ps["name"]
        pmeth = ps.get("prep_method") or ""
        row_cells: list[tuple[object, int]] = [(f"{pname} [{pmeth}]", STYLE_KEY)]
        for pkey, _ in summary_params:
            vals = [
                float(r["value"])
                for r in prox_comp_records
                if r.get("prepared_sample") == pname
                and r.get("parameter") == pkey
                and isinstance(r.get("value"), (int, float))
            ]
            row_cells.append((fmt_mean_sd(vals), STYLE_TEXT))
        s3_rows.append(row_cells)

    s3_rows.append([("", STYLE_DEFAULT)])

    sec_r, sec_m = section_row(
        "2. INDIVIDUAL REPLICATE OBSERVATIONS (USE HEADER DROPDOWNS TO FILTER)", s3_cols, len(s3_rows) + 1
    )
    s3_rows.append(sec_r)
    s3_merges.append(sec_m)

    s3_filter_start = len(s3_rows) + 1
    s3_rows.append([
        ("Analysis Type", STYLE_HEADER),
        ("Field Sample", STYLE_HEADER),
        ("Prepared Sample", STYLE_HEADER),
        ("Prep Method", STYLE_HEADER),
        ("Parameter", STYLE_HEADER),
        ("Value", STYLE_HEADER),
        ("Unit", STYLE_HEADER),
        ("QC Status", STYLE_HEADER),
        ("Replicate", STYLE_HEADER),
        ("Record ID", STYLE_HEADER),
        ("Experiment", STYLE_HEADER),
        ("Method", STYLE_HEADER),
    ])

    for r in sorted(
        prox_comp_records,
        key=lambda x: (x["analysis_type"], x.get("prepared_sample") or "", x.get("parameter") or "", str(x.get("replicate") or "")),
    ):
        s3_rows.append([
            (r["analysis_type"], STYLE_TEXT),
            (r.get("field_sample") or "", STYLE_TEXT),
            (r.get("prepared_sample") or "", STYLE_KEY),
            (r.get("prep_method") or "", STYLE_TEXT),
            (r.get("parameter") or "", STYLE_KEY),
            num_or_text(r.get("value")),
            (r.get("unit") or "", STYLE_TEXT),
            qc_cell(r.get("qc_status")),
            (r.get("replicate") or "", STYLE_TEXT),
            (r.get("record_id") or "", STYLE_TEXT),
            (r.get("experiment") or "", STYLE_TEXT),
            (r.get("method") or "", STYLE_TEXT),
        ])

    pc_bytes, pc_w, pc_h = chart_images["prox_comp"]
    sheet3 = SheetSpec(
        title="Proximate & Compositional",
        rows=s3_rows,
        col_widths=[26, 16, 20, 24, 18, 16, 16, 14, 14, 24, 22, 18, 16],
        freeze_row=2,
        autofilter_ref=f"A{s3_filter_start}:L{len(s3_rows)}",
        merges=s3_merges,
        drawing=SheetDrawing(pc_bytes, pc_w, pc_h, anchor_col=0, anchor_row=3),
    )

    # -------------------------------------------------------------------------
    # SHEET 4: ICP Elemental Analysis (Includes embedded visual chart at top)
    # -------------------------------------------------------------------------
    s4_cols = 11
    s4_rows, s4_merges = banner_rows(
        "ICP-OES ELEMENTAL ANALYSIS (26 OBSERVATIONS)",
        "Macro-Minerals (Ca, Mg, P, Fe, Al) & Trace Metals (Mn, Zn, Cu, Ni, Cr, Co, Cd, Pb) in ppm (mg/kg)",
        s4_cols,
    )
    for _ in range(20):
        s4_rows.append([("", STYLE_DEFAULT)])

    icp_records = [r for r in records if r["analysis_type"] == "ICP Elemental Analysis"]

    sec_r, sec_m = section_row(
        "1. ELEMENT SUMMARY BY PREPARED SAMPLE (ORDERED BY CONCENTRATION)", s4_cols, len(s4_rows) + 1
    )
    s4_rows.append(sec_r)
    s4_merges.append(sec_m)

    s4_rows.append([
        ("Element", STYLE_HEADER),
        ("Unit", STYLE_HEADER),
        ("Overall Mean (ppm)", STYLE_HEADER),
        ("Min (ppm)", STYLE_HEADER),
        ("Max (ppm)", STYLE_HEADER),
        ("hai-sarg031okm2(42) (ppm)", STYLE_HEADER),
        ("hai-sarg032okm2(96) (ppm)", STYLE_HEADER),
        ("QC Pass Count", STYLE_HEADER),
        ("QC Fail Count", STYLE_HEADER),
        ("QC Status Summary", STYLE_HEADER),
        ("Method", STYLE_HEADER),
    ])

    by_elem: dict[str, list[dict]] = defaultdict(list)
    for r in icp_records:
        by_elem[str(r.get("parameter") or "")].append(r)

    for elem, grp in sorted(
        by_elem.items(),
        key=lambda item: -statistics.mean([float(x["value"]) for x in item[1] if isinstance(x.get("value"), (int, float))] or [0.0]),
    ):
        vals = [float(x["value"]) for x in grp if isinstance(x.get("value"), (int, float))]
        v31 = next((float(x["value"]) for x in grp if x.get("prepared_sample") == "hai-sarg031okm2(42)"), None)
        v32 = next((float(x["value"]) for x in grp if x.get("prepared_sample") == "hai-sarg032okm2(96)"), None)
        n_p = sum(1 for x in grp if str(x.get("qc_status")).lower() == "pass")
        n_f = len(grp) - n_p
        qc_label = "PASS" if n_f == 0 else "FAIL"
        s4_rows.append([
            (elem, STYLE_KEY),
            (grp[0].get("unit") or "ppm", STYLE_TEXT),
            num_or_text(statistics.mean(vals) if vals else None),
            num_or_text(min(vals) if vals else None),
            num_or_text(max(vals) if vals else None),
            num_or_text(v31),
            num_or_text(v32),
            (n_p, STYLE_INT),
            (n_f, STYLE_INT),
            qc_cell(qc_label),
            (grp[0].get("method") or "", STYLE_TEXT),
        ])

    s4_rows.append([("", STYLE_DEFAULT)])

    sec_r, sec_m = section_row(
        "2. INDIVIDUAL ICP OBSERVATIONS (AUTO-FILTERED)", s4_cols, len(s4_rows) + 1
    )
    s4_rows.append(sec_r)
    s4_merges.append(sec_m)

    s4_filter_start = len(s4_rows) + 1
    s4_rows.append([
        ("Element", STYLE_HEADER),
        ("Value", STYLE_HEADER),
        ("Unit", STYLE_HEADER),
        ("QC Status", STYLE_HEADER),
        ("Field Sample", STYLE_HEADER),
        ("Prepared Sample", STYLE_HEADER),
        ("Prep Method", STYLE_HEADER),
        ("Well / Position", STYLE_HEADER),
        ("Record ID", STYLE_HEADER),
        ("Experiment", STYLE_HEADER),
        ("Method", STYLE_HEADER),
    ])

    for r in sorted(icp_records, key=lambda x: (x.get("prepared_sample") or "", -float(x.get("value") or 0))):
        s4_rows.append([
            (r.get("parameter") or "", STYLE_KEY),
            num_or_text(r.get("value")),
            (r.get("unit") or "ppm", STYLE_TEXT),
            qc_cell(r.get("qc_status")),
            (r.get("field_sample") or "", STYLE_TEXT),
            (r.get("prepared_sample") or "", STYLE_KEY),
            (r.get("prep_method") or "", STYLE_TEXT),
            (r.get("well_or_block") or "", STYLE_TEXT),
            (r.get("record_id") or "", STYLE_TEXT),
            (r.get("experiment") or "", STYLE_TEXT),
            (r.get("method") or "", STYLE_TEXT),
        ])

    icp_bytes, icp_w, icp_h = chart_images["icp"]
    sheet4 = SheetSpec(
        title="ICP Elemental Analysis",
        rows=s4_rows,
        col_widths=[16, 14, 18, 14, 16, 22, 26, 16, 24, 22, 18],
        freeze_row=2,
        autofilter_ref=f"A{s4_filter_start}:K{len(s4_rows)}",
        merges=s4_merges,
        drawing=SheetDrawing(icp_bytes, icp_w, icp_h, anchor_col=0, anchor_row=3),
    )

    # -------------------------------------------------------------------------
    # SHEET 5: Pretreatment & Hydrolysis (Includes embedded visual chart at top)
    # -------------------------------------------------------------------------
    s5_cols = 13
    s5_rows, s5_merges = banner_rows(
        "PRETREATMENT & ENZYMATIC HYDROLYSIS (32 OBSERVATIONS)",
        "Comparison of 4 Pretreatment Methods (butknt140c, cho10pc, h2o140c, none20c) on Monomeric Glucose & Xylose Yields",
        s5_cols,
    )
    for _ in range(20):
        s5_rows.append([("", STYLE_DEFAULT)])

    pt_records = [r for r in records if r["analysis_type"] == "Pretreatment & Hydrolysis"]

    sec_r, sec_m = section_row(
        "1. PRETREATMENT METHOD × PREPARED SAMPLE SUMMARY (MEAN ± SD)", s5_cols, len(s5_rows) + 1
    )
    s5_rows.append(sec_r)
    s5_merges.append(sec_m)

    s5_rows.append([
        ("Pretreatment Method", STYLE_HEADER),
        ("EH Method", STYLE_HEADER),
        ("Prepared Sample", STYLE_HEADER),
        ("Field Sample", STYLE_HEADER),
        ("Prep Method", STYLE_HEADER),
        ("glucose_yld Mean", STYLE_HEADER),
        ("glucose_yld SD", STYLE_HEADER),
        ("glucose_yld (Mean ± SD)", STYLE_HEADER),
        ("xylose_yld Mean", STYLE_HEADER),
        ("xylose_yld SD", STYLE_HEADER),
        ("xylose_yld (Mean ± SD)", STYLE_HEADER),
        ("Unit", STYLE_HEADER),
        ("Total Obs", STYLE_HEADER),
    ])

    pt_combos = sorted({(r.get("pt_method") or "", r.get("eh_method") or "", r.get("prepared_sample") or "") for r in pt_records})
    for ptm, ehm, psamp in pt_combos:
        sub = [r for r in pt_records if (r.get("pt_method") or "") == ptm and (r.get("prepared_sample") or "") == psamp]
        g_vals = [float(r["value"]) for r in sub if r.get("parameter") == "glucose_yld" and isinstance(r.get("value"), (int, float))]
        x_vals = [float(r["value"]) for r in sub if r.get("parameter") == "xylose_yld" and isinstance(r.get("value"), (int, float))]
        fsamp = sub[0].get("field_sample") or ""
        pmeth = sub[0].get("prep_method") or ""
        unit = sub[0].get("unit") or "mg/g_biomass"
        s5_rows.append([
            (ptm, STYLE_KEY),
            (ehm, STYLE_TEXT),
            (psamp, STYLE_KEY),
            (fsamp, STYLE_TEXT),
            (pmeth, STYLE_TEXT),
            num_or_text(statistics.mean(g_vals) if g_vals else None),
            num_or_text(statistics.stdev(g_vals) if len(g_vals) > 1 else 0.0),
            (fmt_mean_sd(g_vals), STYLE_TEXT),
            num_or_text(statistics.mean(x_vals) if x_vals else None),
            num_or_text(statistics.stdev(x_vals) if len(x_vals) > 1 else 0.0),
            (fmt_mean_sd(x_vals), STYLE_TEXT),
            (unit, STYLE_TEXT),
            (len(sub), STYLE_INT),
        ])

    s5_rows.append([("", STYLE_DEFAULT)])

    sec_r, sec_m = section_row(
        "2. INDIVIDUAL PRETREATMENT & HYDROLYSIS OBSERVATIONS (AUTO-FILTERED)", s5_cols, len(s5_rows) + 1
    )
    s5_rows.append(sec_r)
    s5_merges.append(sec_m)

    s5_filter_start = len(s5_rows) + 1
    s5_rows.append([
        ("Pretreatment Method", STYLE_HEADER),
        ("EH Method", STYLE_HEADER),
        ("Parameter", STYLE_HEADER),
        ("Value", STYLE_HEADER),
        ("Unit", STYLE_HEADER),
        ("QC Status", STYLE_HEADER),
        ("Prepared Sample", STYLE_HEADER),
        ("Field Sample", STYLE_HEADER),
        ("Prep Method", STYLE_HEADER),
        ("Reaction Block", STYLE_HEADER),
        ("Record ID", STYLE_HEADER),
        ("Experiment", STYLE_HEADER),
    ])

    for r in sorted(
        pt_records,
        key=lambda x: (x.get("pt_method") or "", x.get("prepared_sample") or "", x.get("parameter") or "", x.get("record_id") or ""),
    ):
        s5_rows.append([
            (r.get("pt_method") or "", STYLE_KEY),
            (r.get("eh_method") or "", STYLE_TEXT),
            (r.get("parameter") or "", STYLE_KEY),
            num_or_text(r.get("value")),
            (r.get("unit") or "", STYLE_TEXT),
            qc_cell(r.get("qc_status")),
            (r.get("prepared_sample") or "", STYLE_KEY),
            (r.get("field_sample") or "", STYLE_TEXT),
            (r.get("prep_method") or "", STYLE_TEXT),
            (r.get("well_or_block") or "", STYLE_TEXT),
            (r.get("record_id") or "", STYLE_TEXT),
            (r.get("experiment") or "", STYLE_TEXT),
        ])

    pt_bytes, pt_w, pt_h = chart_images["pretreatment"]
    sheet5 = SheetSpec(
        title="Pretreatment & Hydrolysis",
        rows=s5_rows,
        col_widths=[20, 16, 20, 16, 24, 16, 20, 22, 24, 16, 22, 22, 16],
        freeze_row=2,
        autofilter_ref=f"A{s5_filter_start}:L{len(s5_rows)}",
        merges=s5_merges,
        drawing=SheetDrawing(pt_bytes, pt_w, pt_h, anchor_col=0, anchor_row=3),
    )

    # -------------------------------------------------------------------------
    # SHEET 6: Fermentation (Carbon Flow) (Includes embedded visual chart at top)
    # -------------------------------------------------------------------------
    s6_cols = 14
    s6_rows, s6_merges = banner_rows(
        "FERMENTATION & BIOCONVERSION ANALYSIS — CARBON FLOW ORDER (132 OBSERVATIONS)",
        "Ordered by Carbon Flow: Sugar Consumption -> Initial Sugars (t0) -> Final Residual Sugars (teof) -> Cell Growth -> 3-HP & Ethanol Products",
        s6_cols,
    )
    for _ in range(22):
        s6_rows.append([("", STYLE_DEFAULT)])

    ferm_records = [r for r in records if r["analysis_type"] == "Fermentation (Bioconversion)"]

    sec_r, sec_m = section_row(
        "1. CARBON-FLOW PARAMETER SUMMARY BY PREPARED SAMPLE (STRAIN: Rhodosporidium toruloides MCR-ALD6-g2945)",
        s6_cols,
        len(s6_rows) + 1,
    )
    s6_rows.append(sec_r)
    s6_merges.append(sec_m)

    s6_rows.append([
        ("Carbon Flow Stage", STYLE_HEADER),
        ("Parameter", STYLE_HEADER),
        ("Description", STYLE_HEADER),
        ("Unit", STYLE_HEADER),
        ("Microbial Strain", STYLE_HEADER),
        ("hai-sarg025a(0d) (Mean ± SD)", STYLE_HEADER),
        ("hai-sarg031okm2(42) (Mean ± SD)", STYLE_HEADER),
        ("hai-sarg032okm2(96) (Mean ± SD)", STYLE_HEADER),
        ("Overall Mean", STYLE_HEADER),
        ("Overall SD", STYLE_HEADER),
        ("Min", STYLE_HEADER),
        ("Max", STYLE_HEADER),
        ("N (Pass)", STYLE_HEADER),
        ("Pretreatment / EH", STYLE_HEADER),
    ])

    for pkey in FERM_CARBON_FLOW_ORDER:
        grp = [r for r in ferm_records if r.get("parameter") == pkey]
        if not grp:
            continue
        stage = FERM_STAGE_LABELS.get(pkey, "Other")
        desc = next((r.get("parameter_desc") for r in grp if r.get("parameter_desc")), "") or ""
        unit = next((r.get("unit") for r in grp if r.get("unit")), "") or "—"
        all_vals = [float(r["value"]) for r in grp if isinstance(r.get("value"), (int, float))]

        samp_cells = []
        for sp in ["hai-sarg025a(0d)", "hai-sarg031okm2(42)", "hai-sarg032okm2(96)"]:
            sp_vals = [
                float(r["value"])
                for r in grp
                if r.get("prepared_sample") == sp and isinstance(r.get("value"), (int, float))
            ]
            samp_cells.append((fmt_mean_sd(sp_vals), STYLE_TEXT))

        s6_rows.append([
            (stage, STYLE_TEXT),
            (pkey, STYLE_KEY),
            (desc, STYLE_TEXT),
            (unit, STYLE_TEXT),
            ("R. toruloides MCR-ALD6-g2945", STYLE_TEXT),
            *samp_cells,
            num_or_text(statistics.mean(all_vals) if all_vals else None),
            num_or_text(statistics.stdev(all_vals) if len(all_vals) > 1 else 0.0),
            num_or_text(min(all_vals) if all_vals else None),
            num_or_text(max(all_vals) if all_vals else None),
            (len(all_vals), STYLE_INT),
            ("cho10pc + EH1 (2rho-3hp)", STYLE_TEXT),
        ])

    s6_rows.append([("", STYLE_DEFAULT)])

    sec_r, sec_m = section_row(
        "2. INDIVIDUAL FERMENTATION OBSERVATIONS (ORDERED BY CARBON FLOW STAGE, AUTO-FILTERED)",
        s6_cols,
        len(s6_rows) + 1,
    )
    s6_rows.append(sec_r)
    s6_merges.append(sec_m)

    s6_filter_start = len(s6_rows) + 1
    s6_rows.append([
        ("Carbon Flow Stage", STYLE_HEADER),
        ("Parameter", STYLE_HEADER),
        ("Microbial Strain", STYLE_HEADER),
        ("Value", STYLE_HEADER),
        ("Unit", STYLE_HEADER),
        ("QC Status", STYLE_HEADER),
        ("Prepared Sample", STYLE_HEADER),
        ("Field Sample", STYLE_HEADER),
        ("Pretreatment Method", STYLE_HEADER),
        ("EH Method", STYLE_HEADER),
        ("Bioconversion Method", STYLE_HEADER),
        ("Vessel / Well", STYLE_HEADER),
        ("Record ID", STYLE_HEADER),
    ])

    def ferm_row_sort_key(r: dict) -> tuple[int, str, str, str]:
        p = r.get("parameter") or ""
        c_idx = FERM_CARBON_FLOW_ORDER.index(p) if p in FERM_CARBON_FLOW_ORDER else 99
        return (c_idx, r.get("strain") or "", r.get("prepared_sample") or "", r.get("record_id") or "")

    for r in sorted(ferm_records, key=ferm_row_sort_key):
        p = r.get("parameter") or ""
        stage = FERM_STAGE_LABELS.get(p, "Other")
        vessel_well = " / ".join(filter(None, [str(r.get("vessel") or ""), str(r.get("well_or_block") or "")]))
        s6_rows.append([
            (stage, STYLE_TEXT),
            (p, STYLE_KEY),
            (r.get("strain") or "", STYLE_KEY),
            num_or_text(r.get("value")),
            (r.get("unit") or "", STYLE_TEXT),
            qc_cell(r.get("qc_status")),
            (r.get("prepared_sample") or "", STYLE_KEY),
            (r.get("field_sample") or "", STYLE_TEXT),
            (r.get("pt_method") or "", STYLE_TEXT),
            (r.get("eh_method") or "", STYLE_TEXT),
            (r.get("bioconv") or "", STYLE_TEXT),
            (vessel_well, STYLE_TEXT),
            (r.get("record_id") or "", STYLE_TEXT),
        ])

    ferm_bytes, ferm_w, ferm_h = chart_images["fermentation"]
    sheet6 = SheetSpec(
        title="Fermentation (Carbon Flow)",
        rows=s6_rows,
        col_widths=[34, 16, 20, 14, 14, 14, 22, 22, 18, 16, 20, 18, 28, 18],
        freeze_row=2,
        autofilter_ref=f"A{s6_filter_start}:M{len(s6_rows)}",
        merges=s6_merges,
        drawing=SheetDrawing(ferm_bytes, ferm_w, ferm_h, anchor_col=0, anchor_row=3),
    )

    # -------------------------------------------------------------------------
    # SHEET 7: All Observations (Master Flat Table)
    # -------------------------------------------------------------------------
    s7_rows: list[list[tuple[object, int]]] = [
        [
            ("Analysis Type", STYLE_HEADER),
            ("Record ID", STYLE_HEADER),
            ("Field Sample", STYLE_HEADER),
            ("Prepared Sample", STYLE_HEADER),
            ("Prep Method", STYLE_HEADER),
            ("Parameter", STYLE_HEADER),
            ("Parameter Description", STYLE_HEADER),
            ("Value", STYLE_HEADER),
            ("Unit", STYLE_HEADER),
            ("QC Status", STYLE_HEADER),
            ("Pretreatment Method", STYLE_HEADER),
            ("EH Method", STYLE_HEADER),
            ("Microbial Strain", STYLE_HEADER),
            ("Vessel / Block / Well", STYLE_HEADER),
            ("Replicate", STYLE_HEADER),
            ("Experiment", STYLE_HEADER),
            ("Analytical Method", STYLE_HEADER),
        ]
    ]

    for r in records:
        vessel_well = " / ".join(filter(None, [str(r.get("vessel") or ""), str(r.get("well_or_block") or "")]))
        s7_rows.append([
            (r.get("analysis_type") or "", STYLE_TEXT),
            (r.get("record_id") or "", STYLE_TEXT),
            (r.get("field_sample") or "", STYLE_TEXT),
            (r.get("prepared_sample") or "", STYLE_KEY),
            (r.get("prep_method") or "", STYLE_TEXT),
            (r.get("parameter") or "", STYLE_KEY),
            (r.get("parameter_desc") or "", STYLE_TEXT),
            num_or_text(r.get("value")),
            (r.get("unit") or "", STYLE_TEXT),
            qc_cell(r.get("qc_status")),
            (r.get("pt_method") or "", STYLE_TEXT),
            (r.get("eh_method") or "", STYLE_TEXT),
            (r.get("strain") or "", STYLE_TEXT),
            (vessel_well, STYLE_TEXT),
            (r.get("replicate") or "", STYLE_TEXT),
            (r.get("experiment") or "", STYLE_TEXT),
            (r.get("method") or "", STYLE_TEXT),
        ])

    sheet7 = SheetSpec(
        title="All Observations (Master)",
        rows=s7_rows,
        col_widths=[26, 28, 16, 22, 24, 18, 36, 14, 16, 12, 18, 14, 18, 18, 12, 24, 20],
        freeze_row=1,
        autofilter_ref=f"A1:Q{len(s7_rows)}",
        merges=[],
    )

    return [sheet0, sheet1, sheet2, sheet3, sheet4, sheet5, sheet6, sheet7]


def write_xlsx_package(sheets: list[SheetSpec], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Track drawings
    sheet_drawing_idx: dict[int, int] = {}
    drawings: list[SheetDrawing] = []
    for i, s in enumerate(sheets, start=1):
        if s.drawing is not None:
            drawings.append(s.drawing)
            sheet_drawing_idx[i] = len(drawings)

    # 1. [Content_Types].xml
    ct_lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '  <Default Extension="xml" ContentType="application/xml"/>',
        '  <Default Extension="png" ContentType="image/png"/>',
        '  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    for i in range(1, len(sheets) + 1):
        ct_lines.append(
            f'  <Override PartName="/xl/worksheets/sheet{i}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    for d_idx in range(1, len(drawings) + 1):
        ct_lines.append(
            f'  <Override PartName="/xl/drawings/drawing{d_idx}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>'
        )
    ct_lines.append("</Types>")
    content_types_xml = "\n".join(ct_lines)

    # 2. _rels/.rels
    root_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""

    # 3. xl/workbook.xml
    wb_lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        "  <sheets>",
    ]
    for i, s in enumerate(sheets, start=1):
        wb_lines.append(f'    <sheet name="{escape(s.title)}" sheetId="{i}" r:id="rId{i}"/>')
    wb_lines.append("  </sheets>")
    wb_lines.append("</workbook>")
    workbook_xml = "\n".join(wb_lines)

    # 4. xl/_rels/workbook.xml.rels
    wb_rels_lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    for i in range(1, len(sheets) + 1):
        wb_rels_lines.append(
            f'  <Relationship Id="rId{i}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{i}.xml"/>'
        )
    wb_rels_lines.append(
        f'  <Relationship Id="rId{len(sheets) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    wb_rels_lines.append("</Relationships>")
    workbook_rels_xml = "\n".join(wb_rels_lines)

    # 5. Write ZIP package
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        zf.writestr("xl/styles.xml", build_styles_xml())

        for i, s in enumerate(sheets, start=1):
            has_d = i in sheet_drawing_idx
            zf.writestr(f"xl/worksheets/sheet{i}.xml", render_sheet_xml(s, has_drawing=has_d))
            if has_d:
                d_idx = sheet_drawing_idx[i]
                sheet_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing{d_idx}.xml"/>
</Relationships>
"""
                zf.writestr(f"xl/worksheets/_rels/sheet{i}.xml.rels", sheet_rels)

        for d_idx, d in enumerate(drawings, start=1):
            zf.writestr(f"xl/drawings/drawing{d_idx}.xml", build_drawing_xml(d, pic_id=d_idx))
            drawing_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image{d_idx}.png"/>
</Relationships>
"""
            zf.writestr(f"xl/drawings/_rels/drawing{d_idx}.xml.rels", drawing_rels)
            zf.writestr(f"xl/media/image{d_idx}.png", d.png_bytes)


def main() -> None:
    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    chart_images = build_all_chart_images(payload["records"])
    sheets = build_sheets(payload, chart_images)
    write_xlsx_package(sheets, OUTPUT_XLSX)
    write_xlsx_package(sheets, ARTIFACT_XLSX)
    print(f"Generated {OUTPUT_XLSX} ({OUTPUT_XLSX.stat().st_size:,} bytes) with {len(sheets)} tabs and {len(chart_images)} embedded visual charts:")
    for i, s in enumerate(sheets, start=1):
        chart_tag = " [+Embedded Visual Chart]" if s.drawing else ""
        print(f"  {i}. {s.title} ({len(s.rows)} rows){chart_tag}")


if __name__ == "__main__":
    main()
