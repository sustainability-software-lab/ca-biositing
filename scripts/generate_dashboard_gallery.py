import os
import glob
from datetime import datetime


def generate_gallery(base_dir: str = "."):
    # Configuration
    target_dir = os.path.join(base_dir, "exports/plots")
    output_file = os.path.join(target_dir, "index.html")

    # Categories based on subdirectories
    categories = ["metadata", "audit", "conversion", "composition", "geospatial", "lineage"]

    # Build the dashboard sections
    sections_html = []

    descriptions = {
        "resource_analysis_dashboard.html": (
            "Page 1 (Characterization & AI Brief): Streamlined single-resource analytical & bioconversion dashboard "
            "with compact 2-card Executive AI Brief, 4 KPI cards, and 5 focused domain tabs across all 45 active resources."
        ),
        "resource_qc_outlier_dashboard.html": (
            "Page 2 (Statistical QC & Lab Notes Audit): Dedicated replicate precision (RSD_within vs. RSD_between), "
            "3-test candidate outlier screening (Dixon's Q, RSD > 20%, >3×SD_pooled with <100 ppm / <0.5% trace cutoffs), "
            "mined bench notes audit trail, and anonymized CSV export."
        ),
        "resource_explorer_dashboard.html": (
            "Page 3 (Multi-Resource Side-by-Side Parameter Explorer): High-DPI HTML5 Canvas explorer with always-accessible "
            "Multi-Select Checklists (Resources, Parameters & Units, Samples, Methods/Preps) and a Compare By grouping "
            "selector for visual & numeric head-to-head comparison."
        ),
        "db_environment_drift_dashboard.html": (
            "Local vs. Staging vs. Production Database Drift Assessment Dashboard: 4-layer parity scorecard, "
            "data_portal & ca_biositing View Schema Guard, table & materialized view row deltas, Resource × Analysis-Type "
            "drift heatmap, lineage set-difference explorer, parameter value shift (>5%) detector, and filter funnel comparison."
        ),
    }

    for category in categories:
        cat_dir = os.path.join(target_dir, category)
        if not os.path.exists(cat_dir):
            continue

        html_files = glob.glob(os.path.join(cat_dir, "*.html"))
        if not html_files:
            continue

        html_files.sort()

        category_title = category.replace("_", " ").title()

        dashboard_items = []
        for file_path in html_files:
            file_name = os.path.basename(file_path)
            if (
                "monolith" in file_name
                or "pretreatment_variance" in file_name
                or "resource_quick_widget" in file_name
            ):
                continue
            rel_path = os.path.join(category, file_name)
            title = file_name.replace(".html", "").replace("_", " ").title()
            desc = descriptions.get(file_name, "Interactive BioCirV analysis visualization.")

            dashboard_items.append(f"""
                <div class="col">
                    <div class="card h-100 shadow-sm">
                        <div class="card-body d-flex flex-column">
                            <h5 class="card-title fw-bold">{title}</h5>
                            <p class="card-text text-muted small flex-grow-1">{desc}</p>
                            <a href="{rel_path}" class="btn btn-primary w-100 mt-2" target="_blank">View Dashboard</a>
                        </div>
                        <div class="card-footer text-muted small font-monospace">
                            {category}/{file_name}
                        </div>
                    </div>
                </div>
            """)

        if not dashboard_items:
            continue

        items_html = "\n".join(dashboard_items)

        sections_html.append(f"""
            <div class="category-section mb-5">
                <h2 class="border-bottom border-secondary pb-2 mb-4 fw-bold">{category_title}</h2>
                <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
                    {items_html}
                </div>
            </div>
        """)

    all_sections_html = "\n".join(sections_html)

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BioCirV — Modular Analytics &amp; Drift Suite</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background-color: #0b1120;
            color: #f8fafc;
            font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }}
        .hero {{
            background: linear-gradient(135deg, #00313C 0%, #00B5E2 100%);
            color: white;
            padding: 3.5rem 2rem;
            margin-bottom: 2.5rem;
        }}
        .category-section h2 {{
            color: #38bdf8;
            letter-spacing: -0.025em;
        }}
        .card {{
            background-color: #111827;
            border: 1px solid #1e293b;
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        }}
        .card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.35) !important;
        }}
        .btn-primary {{
            background-color: #00B5E2;
            border-color: #00B5E2;
            color: #0f172a;
            font-weight: 600;
        }}
        .btn-primary:hover {{
            background-color: #0094b8;
            border-color: #0094b8;
            color: #0f172a;
        }}
    </style>
</head>
<body>

<div class="hero text-center">
    <h1 class="display-5 fw-bold">BioCirV Modular Analytics &amp; Environment Drift Hub</h1>
    <p class="lead mb-0">BioCirV Bioeconomy Analytics · Reproducible Agent-Skill Suite</p>
    <div class="mt-3">
        <span class="badge bg-light text-dark px-3 py-2">Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
    </div>
</div>

<div class="container mb-4">
  <div class="card shadow-sm border-0" style="background: linear-gradient(135deg, #0f172a 0%, #0369a1 100%); color: white;">
    <div class="card-body p-4">
      <div class="row align-items-center g-3">
        <div class="col-lg-8">
          <span class="badge bg-info text-dark fw-bold mb-2">MODULAR 3-PAGE RESOURCE SUITE + DB ENVIRONMENT DRIFT AUDIT</span>
          <h3 class="fw-bold mb-1">BioCirV Feedstock Characterization, Statistical QC &amp; Multi-Resource Explorer</h3>
          <p class="mb-2 text-light opacity-90 small">
            Explore all <strong>127 cataloged resources</strong> (45 with active lab records), <strong>147 field samples</strong>,
            <strong>384 prepared samples</strong>, and <strong>11,974 observations</strong> across all 10 Aim 1 &amp; Aim 2 tables via our
            de-cluttered modular suite: <strong>Page 1 (Characterization &amp; AI Brief)</strong>,
            <strong>Page 2 (Statistical Replicate Precision, Outlier Screening &amp; Lab Notes Audit)</strong>,
            <strong>Page 3 (Multi-Select Checklist Side-by-Side Comparison Explorer)</strong>, and our
            <strong>Local vs. Staging vs. Production DB Environment Drift Dashboard</strong>.
          </p>
          <div class="d-flex flex-wrap gap-2 mt-3">
            <a href="metadata/resource_analysis_dashboard.html" class="btn btn-sm btn-info text-dark fw-bold" target="_blank">📊 1. Characterization &amp; AI Brief</a>
            <a href="metadata/resource_qc_outlier_dashboard.html" class="btn btn-sm btn-warning text-dark fw-bold" target="_blank">🔬 2. Statistical QC &amp; Outlier Audit</a>
            <a href="metadata/resource_explorer_dashboard.html" class="btn btn-sm btn-light text-dark fw-bold" target="_blank">⚖️ 3. Multi-Select Side-by-Side Explorer</a>
            <a href="audit/db_environment_drift_dashboard.html" class="btn btn-sm btn-outline-light fw-bold" target="_blank">🔄 4. Local / Staging / Prod Drift Audit</a>
          </div>
        </div>
        <div class="col-lg-4 text-lg-end d-flex flex-column gap-2">
          <a href="metadata/resource_analysis_dashboard.html" class="btn btn-primary fw-bold px-4 py-2 shadow" target="_blank">
            Open Page 1: Characterization &rarr;
          </a>
          <a href="metadata/resource_qc_outlier_dashboard.html" class="btn btn-outline-light fw-semibold px-3 py-2" target="_blank">
            Open Page 2: Statistical QC &amp; Notes &rarr;
          </a>
          <a href="metadata/resource_explorer_dashboard.html" class="btn btn-outline-info text-white fw-semibold px-3 py-2" target="_blank">
            Open Page 3: Multi-Select Comparison &rarr;
          </a>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="container mb-5">
    {all_sections_html}
</div>

<footer class="py-4 bg-dark border-top border-secondary mt-auto">
    <div class="container text-center text-secondary">
        <p class="mb-0">BioCirV Analysis Hub · Powered by Reproducible Agent Skills (<code>pixi run refresh-dashboards</code> &amp; <code>pixi run db-drift-compare</code>)</p>
    </div>
</footer>

</body>
</html>
"""

    os.makedirs(target_dir, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Gallery generated at {output_file}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default=".", help="Base repository directory")
    args = parser.parse_args()
    generate_gallery(args.base_dir)
