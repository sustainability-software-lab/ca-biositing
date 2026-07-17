import json
import os
from pathlib import Path
import pandas as pd
from audit.config import settings

def generate_portal():
    output_root = Path(settings.OUTPUT_ROOT)
    # Find latest run
    runs = sorted([d for d in output_root.iterdir() if d.is_dir()], reverse=True)
    if not runs:
        print(f"No audit runs found in {settings.OUTPUT_ROOT}")
        return

    latest_run = runs[0]
    print(f"Generating portal from latest run: {latest_run}")

    portal_dir = Path("audit/portal")
    targets_dir = portal_dir / "targets"
    targets_dir.mkdir(parents=True, exist_ok=True)

    # 1. Read executive_audit_summary.md
    summary_md_path = latest_run / "executive_audit_summary.md"
    summary_md = ""
    if summary_md_path.exists():
        summary_md = summary_md_path.read_text()
        # Replace markdown horizontal rules to avoid confusing Quarto's YAML parser
        summary_md = summary_md.replace("\n---\n", "\n***\n")

    # 2. Find all llm_synthesis_*.json files
    synthesis_files = list(latest_run.glob("llm_synthesis_*.json"))

    target_summaries = []

    for synth_file in synthesis_files:
        target_name = synth_file.stem.replace("llm_synthesis_", "")
        with open(synth_file, "r") as f:
            synth_data = json.load(f)

        # Generate .qmd for this target
        qmd_path = targets_dir / f"{target_name}.qmd"

        # Evidently HTML path (relative to portal/targets for iframe)
        # The build-portal task renders to audit/portal/_site
        # If we put evidently in _site/evidently, we can link it.
        # But the audit output has it in latest_run/evidently.
        # We should probably copy the evidently files to the portal dir or reference them.
        # The instructions say: "<iframe> embedding the Evidently HTML"
        # Let's assume we copy them to audit/portal/evidently/

        evidently_src = latest_run / "evidently" / f"{target_name}.html"
        evidently_dest_dir = portal_dir / "evidently"
        evidently_dest_dir.mkdir(exist_ok=True)
        evidently_dest = evidently_dest_dir / f"{target_name}.html"

        if evidently_src.exists():
            import shutil
            shutil.copy2(evidently_src, evidently_dest)
            evidently_rel_path = f"../evidently/{target_name}.html"
        else:
            evidently_rel_path = ""

        # Check for plots in analysis/ (though they aren't per-run usually)
        # Instructions say: "Custom Visuals — links to analysis/ directory plots"
        # We'll just list some generic ones or if they exist.

        qmd_content = f"""---
title: "Audit Target: {target_name}"
format:
  html:
    page-layout: full
---

::: {{.panel-tabset}}

## Executive Summary

{synth_data.get('executive_summary', 'No summary available.')}

## Evidently Profile

"""
        if evidently_rel_path:
            qmd_content += f'<iframe src="{evidently_rel_path}" width="100%" height="800px" frameborder="0"></iframe>\n'
        else:
            qmd_content += "Evidently report not found.\n"

        qmd_content += """
## Custom Visuals

Links to specific analysis plots:

- [Biomass Composition Plots](../../../analysis/composition/)
- [Conversion Distribution Plots](../../../analysis/conversion/)

:::
"""
        qmd_path.write_text(qmd_content)

        target_summaries.append({
            "Target": f"[{target_name}](targets/{target_name}.qmd)",
            "Flagged": synth_data.get("flagged_count", "N/A"), # Note: AuditorAgent output results has flagged_count, synthesis json might not.
            "Status": "✅ Pass" if not synth_data.get("grouped_issues") else "⚠️ Issues"
        })

    # 3. Generate index.qmd
    # We need to extract the summary table if possible or build one.

    # Try to find target results from the summary md if possible,
    # but generate_portal.py should probably reconstruct it from JSONs.

    # The summary_md might contain markdown that breaks Quarto's YAML parser
    # if it's not properly separated. Ensure there's a blank line.
    index_qmd = f"""---
title: "Data Quality Portal"
---

# Executive Summary

{summary_md}

# Target Audit Status

| Target | Status |
|--------|--------|
"""
    for ts in target_summaries:
        index_qmd += f"| {ts['Target']} | {ts['Status']} |\n"

    (portal_dir / "index.qmd").write_text(index_qmd)
    print("Portal generation complete.")

if __name__ == "__main__":
    generate_portal()
