---
type: Bug
title: exports/gallery.md and analysis outputs reference scripts that do not exist
description: "exports/gallery.md links to analysis scripts that were removed or renamed, and the Aim-2 audit log is a failed run; the untracked gallery index can no longer go stale in git."
tags: [bug, gallery, stale, analysis]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:07Z" }
status: stable
governance: context
code_refs: ["exports/gallery.md", "analysis/metadata/audit_profiling_output.txt", "scripts/generate_dashboard_gallery.py"]
stale_after: "2026-12-31"
sources: ["commit e41d00d", "https://github.com/sustainability-software-lab/ca-biositing/pull/442", "commit ae147f6", "commit a2c8de8"]
---

## Symptom
- exports/gallery.md still cites analysis/composition/biomass_xylan_glucan_viz.py and analysis/composition/xrf_si_k_distribution_viz.py (exports/gallery.md:62, 83), and links plots/composition/biomass_xylan_glucan.html and plots/composition/xrf_si_k_distribution_viz.html (lines 57, 77). Both scripts are missing at a2c8de8 (verified).
- analysis/metadata/audit_profiling_output.txt is a failed run: psql error for scripts/audit_profiling.sql, which is absent (the file still exists, verified).
- The plots themselves are no longer in git. Every plot link in exports/gallery.md is dead in the repo, not only the stale ones.

## Root cause
exports/gallery.md is hand-maintained. Its entries were never regenerated from the scripts that produce plots.

## What changed since e41d00d
- exports/plots/index.html was removed from git by ae147f6 (2026-10-19). It is now generated into exports/plots/ in CI by scripts/generate_dashboard_gallery.py:434-435 and never committed, so orphan HTML can no longer sit in git.
- The orphan-HTML symptom in the earlier version is resolved. The stale markdown is not.

## Impact
A reader of exports/gallery.md finds links to scripts and plots that do not exist in the repo.

## Fix direction
Delete exports/gallery.md, or generate it from the same source as the gallery index.

## Status
Open at a2c8de8.

# Related Concepts
- [Plot regeneration, HTML gallery index, and GitHub Pages deploy](../architecture/analysis-regeneration-and-gallery.md): Generator that does not clean up orphan outputs
- [exports/ directory: committed SQL, reports, and plot outputs](../architecture/analysis-exports-artifacts.md): The stale files live in exports/
