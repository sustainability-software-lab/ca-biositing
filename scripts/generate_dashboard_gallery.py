import os
import glob
from datetime import datetime

def generate_gallery():
    # Configuration
    target_dir = "exports/plots"
    output_file = os.path.join(target_dir, "index.html")

    # Get all HTML files in the directory
    html_files = glob.glob(os.path.join(target_dir, "*.html"))

    # Filter out index.html if it already exists
    html_files = [f for f in html_files if os.path.basename(f) != "index.html"]

    # Sort files by name
    html_files.sort()

    # Build the dashboard items
    dashboard_items = []
    for file_path in html_files:
        file_name = os.path.basename(file_path)
        # Create a readable title from the filename
        # e.g., aim_record_distribution_proximate.html -> Aim Record Distribution Proximate
        title = file_name.replace(".html", "").replace("_", " ").title()

        dashboard_items.append(f"""
            <div class="col">
                <div class="card h-100 shadow-sm">
                    <div class="card-body">
                        <h5 class="card-title">{title}</h5>
                        <p class="card-text text-muted small">Analysis type visualization.</p>
                        <a href="{file_name}" class="btn btn-primary w-100" target="_blank">View Dashboard</a>
                    </div>
                    <div class="card-footer text-muted small">
                        Filename: {file_name}
                    </div>
                </div>
            </div>
        """)

    items_html = "\n".join(dashboard_items)

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
    <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
        {items_html}
    </div>
</div>

<footer class="py-4 bg-white border-top mt-auto">
    <div class="container text-center text-muted">
        <p class="mb-0">CA Bioscape Analysis Hub</p>
    </div>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

    with open(output_file, "w") as f:
        f.write(html_content)

    print(f"Gallery generated successfully at {output_file}")

if __name__ == "__main__":
    generate_gallery()
