---
type: Fact
title: "Open issue #536: deduplicate the Report a Bug modal across the dashboard suite"
description: "Open issue #536 (filed from review of PR #535) asks to replace four copies of the Report a Bug modal and JS with one shared helper and to verify the slice test across all five products."
tags: [issue, dashboards, refactor, snapshot]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:18Z" }
status: stable
code_refs: ["analysis/metadata/resource_analysis_dashboard.py", "analysis/metadata/resource_audit_workbench.py", "analysis/audit/db_environment_drift.py", "scripts/generate_dashboard_gallery.py", "tests/test_resource_slice_export.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/536", "https://github.com/sustainability-software-lab/ca-biositing/pull/535", "commit a2c8de8"]
governance: context
stale_after: "2026-11-21"
---

## Snapshot
Open as of 2026-10-22 (sustainability-software-lab/ca-biositing#536, state OPEN). Opened as a follow-up to PR #535. Snapshot of the issue, not of the code.

## What the issue asks for
- One shared Report a Bug modal HTML and JS helper that takes per-page configuration (page label and diagnostics callback).
- Replace the copies in resource_analysis_dashboard.py (Products 1-3, via `SHARED_SLICE_AND_BUG_MODALS_HTML` and `_JS`), resource_audit_workbench.py (Product 4), db_environment_drift.py (Product 5) and generate_dashboard_gallery.py (gallery).
- One `escapeHtml` and one `??` convention for status and toast messages.
- Make `test_report_a_bug_modal_executes_and_opens_across_dashboard_suite` (tests/test_resource_slice_export.py:706) pass for all five products and the gallery.

## Where the copies are at HEAD a2c8de8
| Copy | Location |
| --- | --- |
| Products 1-3 (shared source) | analysis/metadata/resource_analysis_dashboard.py:605 (HTML) and :986 (JS) |
| Product 4 | analysis/metadata/resource_audit_workbench.py:3348 (URL) and the modal in render_workbench_html |
| Product 5 | analysis/audit/db_environment_drift.py:3805 (URL) and the modal in build_drift_dashboard_html |
| Gallery | scripts/generate_dashboard_gallery.py:886 and :974 |

## Notes
- The issue does not mention the repo-name mismatch (bugs/dashboards-report-bug-github-repo-mismatch). A consolidated helper should take the repo from one constant.
- The consolidated helper would have to be shared by a package or a file that all four generators import; the gallery and drift scripts currently inline their JS.

## Status
Open. No commit in e41d00d..a2c8de8 addresses it.

# Related Concepts
- [Report a Bug links and the bug-issue API default point at uw-ssec/ca-biositing, not the origin repo](../bugs/dashboards-report-bug-github-repo-mismatch.md): repo-name divergence the issue does not cover
- [Five-product BioCirV resource dashboard suite and how each is generated](../architecture/analysis-resource-dashboard-suite.md): the suite whose four copies the issue consolidates
- [Plot regeneration, HTML gallery index, and GitHub Pages deploy](../architecture/analysis-regeneration-and-gallery.md): gallery and dashboard generation that the modal copies live in
