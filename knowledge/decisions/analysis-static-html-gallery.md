---
type: Decision
title: Publish analysis as committed static HTML instead of a live dashboard
description: "Charts are rendered to self-contained HTML/PNG and committed to exports/plots, then published via GitHub Pages; rejected live-serving alternatives are not documented (inferred)."
tags: [decision, analysis, gallery, static-site, trade-off]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:07Z" }
status: stable
governance: context
code_refs: ["scripts/regenerate_all_plots.py", "scripts/generate_dashboard_gallery.py", ".github/workflows/gh-pages.yml"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/442", "commit 707afa8", "https://github.com/sustainability-software-lab/ca-biositing/issues/519", "commit ae147f6", "commit 1fcadb4"]
---

## Status
Superseded for dashboards by decisions/dashboards-gcs-over-committed-exports (issue #519, commits 752a80d, 1fcadb4, ae147f6, bd72222). The original decision is kept below as history. Chart scripts that still write local HTML and PNG under exports/plots/ remain valid for local work.

## Decision (original, 707afa8 / PR #442)
Render each chart to a standalone file (Altair/Plotly HTML, PNG) under exports/plots/ and commit it. Deploy the tree to GitHub Pages on push to main.

## What changed
- ae147f6 (2026-10-19, PR #522): exports/plots tracked files removed (34 files changed in the commit), .gitignore:142 ignores exports/plots/, and the pre-commit guard refuses it.
- 1fcadb4 (2026-10-19, PR #521): gh-pages.yml copies the public allowlist from GCS latest/, not from exports/plots/.
- scripts/generate_dashboard_gallery.py still writes index.html and login.html, now into exports/plots/ during CI only (line 434-435).

## Trade-offs (original, inferred from the code)
- Pro: no runtime server for charts; static hosting; reviewable output in PRs. Those PR-review benefits are gone for dashboards.
- Con (resolved): binary PNGs and multi-MB HTML in git. Now in GCS.
- Con (still true): charts go stale until someone reruns the generator.

## Rejected alternatives
Not recorded in the repo. Inferred: serving charts from FastAPI was not chosen for the first set (confirm with PR #442).

## Open questions
- Should the chart scripts also publish to GCS, or stay local-only? (inferred: local-only is the intent of the .gitignore rule)

# Related Concepts
- [Plot regeneration, HTML gallery index, and GitHub Pages deploy](../architecture/analysis-regeneration-and-gallery.md): Implementation of the decision
- [frontend/ git submodule (cal-bioscape-frontend), pin, and API consumption](../architecture/frontend.md): The alternative live UI path the static gallery sits beside
- [System overview (start here)](../architecture/system-overview.md): Places the analysis outputs in the overall delivery picture
- [Decision: store generated dashboards in a GCS bucket instead of committing them to git (#519)](dashboards-gcs-over-committed-exports.md): the decision that superseded this one for dashboards
