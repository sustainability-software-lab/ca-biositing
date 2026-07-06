import os
import glob
from datetime import datetime

def generate_gallery():
    # Configuration
    target_dir = "exports/plots"
    output_file = os.path.join(target_dir, "index.html")

    # Categories based on subdirectories
    categories = ["composition", "conversion", "geospatial", "metadata", "lineage"]

    # Build the dashboard sections
    sections_html = []

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
            # Create a relative path for the link
            rel_path = os.path.join(category, file_name)

            # Create a readable title from the filename
            title = file_name.replace(".html", "").replace("_", " ").title()

            dashboard_items.append(f"""
                <div class="col">
                    <div class="card h-100 shadow-sm">
                        <div class="card-body">
                            <h5 class="card-title">{title}</h5>
                            <p class="card-text text-muted small">Analysis type visualization.</p>
                            <a href="{rel_path}" class="btn btn-primary w-100" target="_blank">View Dashboard</a>
                        </div>
                        <div class="card-footer text-muted small">
                            Filename: {file_name}
                        </div>
                    </div>
                </div>
            """)

        items_html = "\n".join(dashboard_items)

        sections_html.append(f"""
            <div class="category-section mb-5">
                <h2 class="border-bottom pb-2 mb-4 text-dark fw-bold">{category_title}</h2>
                <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
                    {items_html}
                </div>
            </div>
        """)

    all_sections_html = "\n".join(sections_html)

    # HTML Template
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CA Biositing - Analysis Gallery</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background-color: #f8f9fa;
            font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }}
        .hero {{
            background: linear-gradient(135deg, #00313C 0%, #00B5E2 100%);
            color: white;
            padding: 4rem 2rem;
            margin-bottom: 3rem;
        }}
        .category-section h2 {{
            color: #00313C;
            letter-spacing: -0.025em;
        }}
        .card {{
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
            border: none;
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15) !important;
        }}
        .btn-primary {{
            background-color: #00B5E2;
            border-color: #00B5E2;
        }}
        .btn-primary:hover {{
            background-color: #0094b8;
            border-color: #0094b8;
        }}
    </style>
</head>
<body>

<div class="hero text-center">
    <h1 class="display-4 fw-bold">Analysis Visualization Gallery</h1>
    <p class="lead">CA Biositing Geospatial Bioeconomy Project</p>
    <div class="mt-4">
        <span class="badge bg-light text-dark px-3 py-2">Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
    </div>
</div>

<div class="container mb-5">
    {all_sections_html}
</div>

<footer class="py-4 bg-white border-top mt-auto">
    <div class="container text-center text-muted">
        <p class="mb-0">CA Bioscape Analysis Hub</p>
    </div>
</footer>

</body>
</html>
"""

    with open(output_file, "w") as f:
        f.write(html_content)

    print(f"Gallery generated at {output_file}")

if __name__ == "__main__":
    generate_gallery()
