#!/usr/bin/env python3
"""Build a standalone, Sargassum-specific HTML5 <canvas> Resource Explorer dashboard."""
import json
import re
from pathlib import Path

SRC_HTML = Path("/Users/pjsmitty301/.gemini/antigravity/brain/42a5010b-7235-40e6-8c99-569580ebe1ec/resource_explorer_dashboard.html")
OUT_EXPORT = Path("/Users/pjsmitty301/ca-biositing/exports/sargassum_resource_explorer.html")
OUT_ARTIFACT = Path("/Users/pjsmitty301/.gemini/antigravity/brain/42a5010b-7235-40e6-8c99-569580ebe1ec/sargassum_resource_explorer.html")


def main():
    html = SRC_HTML.read_text(encoding="utf-8")

    # Extract RAW_DATA JSON from line 264
    m = re.search(r"const RAW_DATA = (\{.*?\});\n", html)
    if not m:
        raise RuntimeError("Could not find RAW_DATA in source HTML")

    raw_data = json.loads(m.group(1))
    res_dict = raw_data["dicts"]["resource_name"]
    sarg_idx = res_dict.index("sargassum")

    # Filter rows to only sargassum
    sarg_rows = [list(r) for r in raw_data["rows"] if r[1] == sarg_idx]

    # Compact dictionaries to only strings used by Sargassum rows (and scrub analyst emails)
    new_dicts = {}
    for col_idx, col_name in enumerate(raw_data["str_cols"]):
        old_list = raw_data["dicts"][col_name]
        if col_name == "analyst":
            new_dicts[col_name] = ["Lab Analyst"]
            for r in sarg_rows:
                r[col_idx + 1] = 0
            continue
        used_vals = sorted({old_list[r[col_idx + 1]] for r in sarg_rows})
        val_to_new_idx = {v: i for i, v in enumerate(used_vals)}
        new_dicts[col_name] = used_vals
        for r in sarg_rows:
            r[col_idx + 1] = val_to_new_idx[old_list[r[col_idx + 1]]]

    raw_data["dicts"] = new_dicts
    raw_data["rows"] = sarg_rows
    raw_data["resources"] = [
        {
            "name": "sargassum",
            "resource_class": "Macroalgae / Marine Biomass",
            "primary_ag_product": "Pelagic Sargassum spp.",
        }
    ]

    new_raw_json = json.dumps(raw_data, separators=(",", ":"))
    sarg_html = html[: m.start()] + f"const RAW_DATA = {new_raw_json};\n" + html[m.end() :]

    # Customize title and header badges for Sargassum Collaborator Report
    sarg_html = sarg_html.replace(
        "<title>CA Biositing — Multi-Resource Variance &amp; Analytical Explorer</title>",
        "<title>Sargassum — Interactive Analytical &amp; Bioconversion Explorer</title>",
    )
    sarg_html = sarg_html.replace(
        'id="dashboard-title" class="text-[var(--foreground)] font-semibold text-base tracking-tight">CA Biositing Analytical &amp; Variance Dashboard</h2>',
        'id="dashboard-title" class="text-[var(--foreground)] font-semibold text-base tracking-tight">Sargassum Analytical &amp; Bioconversion Visual Explorer</h2>',
    )
    sarg_html = sarg_html.replace(
        '<a href="../index.html" class="text-xs px-2 py-1 rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors">\n          &larr; Gallery\n        </a>',
        "",
    )

    # Filter DOMAINS to the 6 active Sargassum domains (Proximate, Compositional, ICP Elements, Pretreatment, Fermentation, Calorimetry & XRD)
    old_domains = """    const DOMAINS = [
      { id: 'proximate', label: 'Proximate', title: 'Proximate Analysis Variance by Sample & Prep Method', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'compositional', label: 'Compositional', title: 'Compositional Biopolymers by Sample & Prep Method', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'ultimate', label: 'Ultimate', title: 'Ultimate Elemental & Fiber Analysis by Sample', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'calorimetry_xrd', label: 'Calorimetry & XRD', title: 'XRD Crystallinity & Calorimetry Records by Sample', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'icp', label: 'ICP Elements', title: 'ICP-OES Elemental Concentration Profile (ppm)', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'xrf', label: 'XRF Elements', title: 'XRF Elemental Concentration Profile (ppm)', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'pretreatment', label: 'Pretreatment', title: 'Pretreatment Variance by Sample & Method', methodCol: 'pt_method', methodLabel: 'Method:' },
      { id: 'fermentation', label: 'Fermentation', title: 'Fermentation Bioconversion & Sugar Depletion Profile', methodCol: 'pt_method', methodLabel: 'Method:' },
      { id: 'gasification', label: 'Gasification', title: 'Gasification Syngas, Flammability & Mass Balance Profile', methodCol: 'prep_method', methodLabel: 'Prep:' }
    ];"""

    new_domains = """    const DOMAINS = [
      { id: 'proximate', label: 'Proximate', title: 'Sargassum Proximate Analysis by Sample & Milling Prep', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'compositional', label: 'Compositional', title: 'Sargassum Compositional Biopolymers (Glucan, Xylan, Lignin)', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'icp', label: 'ICP Elements', title: 'Sargassum ICP-OES Elemental Profile (ppm, Log10 / Linear)', methodCol: 'prep_method', methodLabel: 'Prep:' },
      { id: 'pretreatment', label: 'Pretreatment', title: 'Sargassum Pretreatment & Enzymatic Hydrolysis Sugar Yields', methodCol: 'pt_method', methodLabel: 'Method:' },
      { id: 'fermentation', label: 'Fermentation', title: 'Sargassum Carbon-Flow Fermentation (R. toruloides MCR-ALD6-g2945)', methodCol: 'prepared_sample_name', methodLabel: 'Sample:' },
      { id: 'calorimetry_xrd', label: 'Calorimetry & XRD', title: 'Sargassum Calorimetry & XRD Crystallinity Metadata', methodCol: 'prep_method', methodLabel: 'Prep:' }
    ];"""
    assert old_domains in sarg_html, "Could not match DOMAINS block"
    sarg_html = sarg_html.replace(old_domains, new_domains)

    # For Fermentation in Sargassum, color/group series by prepared_sample_name so the 3 prepared samples have distinct colors/shapes
    old_series_fn = """    function getSeriesValue(r, domainId) {
      if (domainId === 'pretreatment' || domainId === 'fermentation') {
        return r.pt_method && r.pt_method !== 'N/A' ? r.pt_method : (r.strain !== 'N/A' ? r.strain : 'Standard');
      }
      return r.prep_method && r.prep_method !== 'N/A' ? r.prep_method : 'Standard';
    }"""
    new_series_fn = """    function getSeriesValue(r, domainId) {
      if (domainId === 'fermentation') {
        return r.prepared_sample_name || 'Sample';
      }
      if (domainId === 'pretreatment') {
        return r.pt_method && r.pt_method !== 'N/A' ? r.pt_method : (r.strain !== 'N/A' ? r.strain : 'Standard');
      }
      return r.prep_method && r.prep_method !== 'N/A' ? r.prep_method : 'Standard';
    }"""
    assert old_series_fn in sarg_html, "Could not match getSeriesValue block"
    sarg_html = sarg_html.replace(old_series_fn, new_series_fn)

    # Default resource to 'sargassum' in initResourceDropdown and resetFilters
    sarg_html = sarg_html.replace(
        "const initialRes = urlParams.get('resource') || 'ALL';",
        "const initialRes = urlParams.get('resource') || 'sargassum';",
    )
    sarg_html = sarg_html.replace(
        "document.getElementById('filter-resource').value = 'ALL';",
        "document.getElementById('filter-resource').value = 'sargassum';",
    )

    OUT_ARTIFACT.write_text(sarg_html, encoding="utf-8")

    # For standalone exports in exports/, use standard Tailwind v3 CDN
    export_sarg_html = sarg_html.replace(
        "https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4",
        "https://cdn.tailwindcss.com",
    )
    OUT_EXPORT.write_text(export_sarg_html, encoding="utf-8")

    export_full_path = Path("/Users/pjsmitty301/ca-biositing/exports/resource_explorer_dashboard.html")
    export_full_html = html.replace(
        "https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4",
        "https://cdn.tailwindcss.com",
    )
    export_full_path.write_text(export_full_html, encoding="utf-8")

    import zipfile
    bundle_zip = Path("/Users/pjsmitty301/ca-biositing/exports/sargassum_collaborator_bundle.zip")
    with zipfile.ZipFile(bundle_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn in [
            "sargassum_analytical_report.xlsx",
            "sargassum_resource_explorer.html",
            "sargassum_analysis_dashboards.html",
        ]:
            fp = Path("/Users/pjsmitty301/ca-biositing/exports") / fn
            if fp.exists():
                zf.write(fp, arcname=fn)

    print(f"Wrote {OUT_EXPORT} ({OUT_EXPORT.stat().st_size:,} bytes) with {len(sarg_rows)} Sargassum observations.")
    print(f"Updated {export_full_path} and {bundle_zip} ({bundle_zip.stat().st_size:,} bytes).")


if __name__ == "__main__":
    main()
