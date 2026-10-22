---
type: Bug
title: Root tests/ (275 non-harness tests) are not gated by CI; analysis view tests broke unnoticed
description: "Root tests/ (about 275 non-harness tests at e41d00d, plus 30 dashboard, drift and QC API tests added in #517-#535) are not gated by CI; analysis view tests broke unnoticed once."
tags: [testing, ci, webservice, regression]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:04Z" }
status: stable
governance: context
code_refs: ["tests/**", "pixi.toml", ".github/workflows/ci.yml", "tests/webservice/v1/conftest.py", ".github/workflows/dashboard-artifacts.yml"]
stale_after: "2026-12-31"
sources: ["commit bd42ca2", "https://github.com/sustainability-software-lab/ca-biositing/pull/490", "https://github.com/sustainability-software-lab/ca-biositing/pull/472", ".github/workflows/ci.yml", "https://github.com/sustainability-software-lab/ca-biositing/pull/535", "commit a2c8de8", "commit f954bd3"]
---

## Purpose
Records the gap between the local test command and CI scope, with the one documented regression it allowed, and the new dashboard tests that the same gap now leaves ungated.

## Evidence
- pixi.toml:271-273 runs `pytest tests/`. CI runs only src/ca_biositing/{datamodels,pipeline,webservice} (ci.yml:67, 71, 75) and tests/agent_harness (ci.yml:40). The gap is confirmed by grep: no workflow references tests/analysis, tests/audit or tests/test_resource_slice_export.py.
- Commit bd42ca2 (2026-10-02, PR #490) says PR #472 added an outer join to Provider in ANALYSIS_DATA_VIEW and "all analysis view tests [failed] with ’no such table: provider’". The fix only touched tests/webservice/v1/conftest.py (+2 lines).
- Inference: the failure stayed until #490 because no CI job ran tests/webservice (inferred; confirm from PR #472 check history).
- Added after e41d00d: tests/analysis (12 test functions), tests/audit (3), tests/test_resource_slice_export.py (11), tests/webservice/test_qc_review.py (4). These need Node for the inline JavaScript checks. The dashboard-artifacts workflow (.github/workflows/dashboard-artifacts.yml) runs the generators and checks inline JS with node --check, but it does not run pytest.

## Impact
Regressions in the API (`/v1/feedstocks/*`, `/v1/qc/*`), in tests/pipeline ETL modules, and in the dashboards merge without a red check. Local runs are the only gate. For the dashboards, the Report a Bug repo mismatch (bugs/dashboards-report-bug-github-repo-mismatch) is one defect of the kind these tests would catch if they asserted the repo name.

## Open questions
- Whether the root suite passes at HEAD: not run in this review. (inferred; confirm with `pixi run test`.)
- Adding `pixi run test` or the dashboard tests to the checks matrix would make these gating; not decided.

# Related Concepts
- [What the CI test jobs run, and what they skip](../facts/testing-ci-scope.md): the CI scope this bug follows from
- [Webservice test suites: unit (root tests/webservice) and live smoke (src)](../architecture/webservice-tests.md): fixture that was broken
- [System overview (start here)](../architecture/system-overview.md): API and ETL layers affected
- [Test counts per suite and what each file covers (HEAD e41d00d)](../facts/testing-suite-inventory.md): per-file counts including the new dashboard tests
- [Report a Bug links and the bug-issue API default point at uw-ssec/ca-biositing, not the origin repo](dashboards-report-bug-github-repo-mismatch.md): a defect the ungated dashboard tests do not assert
