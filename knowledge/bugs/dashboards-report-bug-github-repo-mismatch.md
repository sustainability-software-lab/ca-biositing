---
type: Bug
title: "Report a Bug links and the bug-issue API default point at uw-ssec/ca-biositing, not the origin repo"
description: "Report a Bug in Products 4-5 and the gallery targets uw-ssec/ca-biositing, Products 1-3 target sustainability-software-lab/ca-biositing, and the API defaults to uw-ssec."
tags: [bug, dashboards, github-issues, qc]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:17Z" }
status: stable
code_refs: ["analysis/metadata/resource_analysis_dashboard.py", "analysis/metadata/resource_audit_workbench.py", "analysis/audit/db_environment_drift.py", "scripts/generate_dashboard_gallery.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/endpoints/qc_review.py", "tests/test_resource_slice_export.py"]
sources: ["commit a2c8de8", "https://github.com/sustainability-software-lab/ca-biositing/pull/535", "https://github.com/sustainability-software-lab/ca-biositing/issues/536", "gh repo view uw-ssec/ca-biositing (2026-10-22)"]
governance: context
stale_after: "2026-11-30"
---

## Symptom
The Report a Bug modal produces a pre-filled issue URL, or calls the API, against two different GitHub repositories depending on which dashboard the user is on. Products 4 and 5 and the gallery use `uw-ssec/ca-biositing`; Products 1-3 use `sustainability-software-lab/ca-biositing`.

## Evidence
- analysis/metadata/resource_analysis_dashboard.py:50 and :987: `https://github.com/sustainability-software-lab/ca-biositing/issues/new` (Products 1-3, shared modal).
- analysis/metadata/resource_audit_workbench.py:3348: `https://github.com/uw-ssec/ca-biositing/issues/new` (Product 4).
- analysis/audit/db_environment_drift.py:3805: same uw-ssec URL (Product 5).
- scripts/generate_dashboard_gallery.py:886: same uw-ssec URL (gallery).
- src/ca_biositing/webservice/ca_biositing/webservice/v1/endpoints/qc_review.py:737: `os.getenv("GITHUB_REPO", "uw-ssec/ca-biositing")` is used for both the pre-filled URL and the REST API call (`api.github.com/repos/{repo}/issues`).
- `git remote -v` for this worktree points at sustainability-software-lab/ca-biositing. `gh repo view uw-ssec/ca-biositing` returns the sustainability-software-lab URL, so the old name appears to be a rename redirect (checked 2026-10-22).
- The four uw-ssec strings were added in a2c8de8 (`git log -S` on analysis/ and scripts/).

## Impact
- Browser pre-filled links work through the rename redirect (inferred from the `gh` result).
- The REST path is less certain. The endpoint uses `urllib.request` for a POST; a 301 on POST is typically re-issued as GET, which would not create an issue. The endpoint then returns the fallback URL with `api_error` set (inferred from the urllib behaviour; not exercised).
- No existing test asserts the repo name, so nothing catches this. tests/test_resource_slice_export.py:345 only checks the Product 1-3 URL prefix.

## Suspected root cause
The uw-ssec name was copied from the template or an earlier remote when a2c8de8 added the modal to the other three generators (inferred; the commit message says the copies were made across generators, not which source was used).

## Fix direction (not applied)
Use one constant (repo name, or `GITHUB_REPO` for the endpoint) across the four generators and the endpoint, as tracked in issue #536 (facts/issue-536-dedupe-report-a-bug). Set the endpoint default to the origin repo and add a test that all copies agree.

## History
- a2c8de8 (PR #535, 2026-10-22): introduced the modal copies and the endpoint with the uw-ssec default.
- Related open issue: #536 (dedupe the modal), which does not mention the repo name.

# Related Concepts
- [Product 4 QC Audit Workbench: Stage 1 decisions, Stage 2 Sheets sync, tray handoff](../architecture/analysis-qc-audit-workbench.md): Product 4 modal and API call
- [Multi-environment DB drift assessment (4 layers, local/staging/production)](../architecture/analysis-db-drift-assessment.md): Product 5 modal
- [Five-product BioCirV resource dashboard suite and how each is generated](../architecture/analysis-resource-dashboard-suite.md): Products 1-3 use the other repo name
- [Open issue #536: deduplicate the Report a Bug modal across the dashboard suite](../facts/issue-536-dedupe-report-a-bug.md): open issue that would consolidate the copies
- [/v1/qc API: routes, auth, request and response shapes](../architecture/qc-review-api-v1-qc.md): owns the /v1/qc/github-issue default GITHUB_REPO
- [Plot regeneration, HTML gallery index, and GitHub Pages deploy](../architecture/analysis-regeneration-and-gallery.md): publish path that carries the gallery links and the Pages subset
