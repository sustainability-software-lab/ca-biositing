---
type: Architecture
title: "Test suite layout, how to run each suite, and fixture map"
description: "Where the test trees live, which of them CI runs, the pixi commands for each, and which fixture file backs which suite, including the dashboard and drift tests added in 2026-10."
tags: [testing, pytest, ci, fixtures]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:02Z" }
status: stable
governance: context
code_refs: ["pixi.toml", "tests/**", "src/ca_biositing/*/tests/**", "src/ca_biositing/webservice/pyproject.toml", ".github/workflows/ci.yml", ".agents/rules/testing-patterns.md", "tests/fixtures/minimal_dashboard_snapshot.json", "tests/fixtures/minimal_env_fingerprint.json"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/490", "commit bd42ca2", "https://github.com/sustainability-software-lab/ca-biositing/pull/497", "commit e41d00d", "commit 7a41e0e", "commit 203b787", ".agents/rules/testing-patterns.md", "https://github.com/sustainability-software-lab/ca-biositing/pull/535", "commit a2c8de8", "commit f954bd3", "commit 4f3e0be"]
---

## Purpose
Hub for the test slice. Explains the test trees, which commands run them, and which conftest supplies the DB/session/client fixtures. Read this before writing or running tests.

## Key files
| Path:line | Role |
|---|---|
| pixi.toml:271-273 | `pixi run test` = `python -m pytest tests/ --verbose` (root suite only) |
| pixi.toml:275-277 | `pixi run test-cov` = same path with `--cov=src/ca_biositing` and HTML report |
| src/ca_biositing/webservice/pyproject.toml:63-66 | Only pytest ini block in the repo; registers the `integration` marker. No `testpaths`, no root `pytest.ini`/`pyproject.toml` |
| tests/webservice/v1/conftest.py:50 | `engine_fixture`: SQLite in-memory, creates ~27 selected tables only |
| tests/webservice/v1/conftest.py:96 | `session_fixture`: connection-level transaction, rolled back after each test |
| tests/webservice/v1/conftest.py:118 | `client_fixture`: overrides `get_session` and `get_current_user` (always admin) |
| tests/webservice/conftest.py:21, :53 | `auth_engine_fixture` (api_user table only, StaticPool) and `auth_client_fixture` (override of get_session) |
| tests/webservice/test_qc_review.py | `/v1/qc` Audit Workbench API, Stage 1 persistence, Stage 2 sync (4 test functions; added in a2c8de8) |
| tests/pipeline/conftest.py, src/ca_biositing/pipeline/tests/conftest.py | Two near-duplicate pipeline conftests (fixtures: sample_ids/desc/qty/producers DataFrames, mock_prefect_logger, session) |
| src/ca_biositing/pipeline/tests/conftest.py:12, :52-64, :96-108 | SQLite shims: md5 function registered on connect; GeoAlchemy2 `after_create` patched so Spatial columns create without SpatiaLite |
| src/ca_biositing/datamodels/tests/conftest.py:8, :16 | `engine` and `session` (plain SQLite in-memory) |
| src/ca_biositing/webservice/tests/conftest.py | Live-server client (httpx) for `integration` tests; skips when env vars absent |
| tests/agent_harness/conftest.py:28, :51, :57 | `repo_files` (git ls-files), `agents_md_files`, `rule_files`; no DB |
| tests/analysis/, tests/audit/, tests/test_resource_slice_export.py | Dashboard, workbench, drift and slice tests; several run Node to execute inline JS (tests/analysis/test_resource_audit_workbench.py, tests/analysis/test_live_qc_overlay_and_tray.py, tests/test_resource_slice_export.py) |
| tests/fixtures/minimal_dashboard_snapshot.json | Offline snapshot used by the workbench fallback (`load_snapshot`) and by the dashboard workflow when no snapshot exists |
| tests/fixtures/minimal_env_fingerprint.json | Fixture fingerprint used by tests/audit/test_db_environment_drift.py when no live fingerprints are on disk |
| .github/workflows/ci.yml:37-40 | `harness` job: pixi installed only, runs `pytest tests/agent_harness` |
| .github/workflows/ci.yml:42-80 | `checks` job: py312/py313 x ubuntu-latest/macos-14, runs three package paths (ci.yml:67, 71, 75) |
| .agents/rules/testing-patterns.md | Pattern doc; partly stale (see bugs/doc-drift-testing) |

## How it works
```mermaid
flowchart LR
  L[pixi run test] --> R[pytest tests/ - root suite, 318 collected at e41d00d]
  CI1[CI checks job] --> P1[pytest src/ca_biositing/datamodels]
  CI1 --> P2[pytest src/ca_biositing/pipeline]
  CI1 --> P3[pytest src/ca_biositing/webservice -m "not integration"]
  CI2[CI harness job] --> H[pytest tests/agent_harness - 43 collected at e41d00d]
```
- DB-backed suites use SQLite in-memory, not Postgres (see decisions/testing-sqlite-in-memory-fixtures). testcontainers is pinned in pixi.toml:38 but no test imports it.
- Prefect tasks are tested by calling `.fn(...)` with `get_run_logger` patched (see facts/testing-prefect-fn-pattern).
- Dashboard JS tests write a small Node script to a temp directory and run it with a 15-second timeout (test_resource_slice_export.py, #531). `node` must be on PATH or the test fails by design.

## Commands
- All root tests: `pixi run test`
- Coverage: `pixi run test-cov`
- One package (CI form): `pixi run pytest src/ca_biositing/pipeline -v`
- Webservice without live server: `pixi run pytest src/ca_biositing/webservice -m "not integration"`
- Harness: `pixi run pytest tests/agent_harness -v` (CI uses `pixi exec --spec python=3.12 --spec pytest --spec pyyaml`)
- Dashboards and drift: `pixi run pytest tests/analysis tests/audit tests/test_resource_slice_export.py -v` (not run by CI)
- Collection only (no run): `pixi run pytest --collect-only -q <path>`

## Interfaces
- Inputs: fixtures above; env vars `CA_BIOSITING_BASE_URL`, `CA_BIOSITING_TEST_USERNAME`, `CA_BIOSITING_TEST_PASSWORD` for integration tests.
- Outputs: pytest report; coverage XML uploaded to Codecov in CI (ci.yml, codecov-action v7.1.1).
- Callers: developers via pixi; CI workflow `ci.yml` only.

## Gotchas
- `pixi run test` covers tests/ but CI does not; the root suite (incl. webservice v1 endpoint tests and the dashboard tests) is not gated (see bugs/testing-root-tests-outside-ci).
- No test-file basename appears in both root tests/ and a src package tests/ (checked with find at e41d00d); keep it that way or pytest module names may collide.
- Pipeline DataFrame fixtures state expected row counts in docstrings (137/104/142/64); they are mock data, not a DB snapshot.

## History
- bd42ca2 (2026-10-02, PR #490): added `Provider` table creation to `tests/webservice/v1/conftest.py` after PR #472 made the analysis view join `provider`; before the fix analysis view tests failed with "no such table: provider".
- e41d00d (2026-10-16, PR #497): adopted SSEC agent harness; added `tests/agent_harness/` and split it into its own CI job; moved AGENTS guidance to `.agents/rules/`.
- 4f3e0be (PR #517), d290906 (PR #518), c4cbf2d (PR #525), 587c1cb (PR #526), f4e9f5a (PR #530), f954bd3 (PR #531), a2c8de8 (PR #535), 2026-10-19 to 2026-10-22: added the dashboard, workbench, drift and QC API tests outside CI.
- 7a41e0e (2026-02-12, PR #112): SQLModel/Alembic migration, origin of the current models the fixtures import.
- 203b787 (2026-02-26, PR #139): JWT auth added; origin of `tests/webservice/conftest.py` and auth endpoint tests.

## Open questions
- Root `tests/` pass/fail status at HEAD was not verified (no test run in this review). (inferred; confirm by running `pixi run test`.)
- Whether the dashboard tests should join the CI checks matrix; they need Node on the runner.

# Related Concepts
- [System overview (start here)](system-overview.md): hub; test trees cover the datamodels, pipeline and webservice packages
- [Test counts per suite and what each file covers (HEAD e41d00d)](../facts/testing-suite-inventory.md): per-suite counts and file-to-module map
- [What the CI test jobs run, and what they skip](../facts/testing-ci-scope.md): which of these trees CI actually runs
- [DB tests use SQLite in-memory with selected tables, not Postgres or testcontainers](../decisions/testing-sqlite-in-memory-fixtures.md): why fixtures use SQLite rather than Postgres
- [Root tests/ (275 non-harness tests) are not gated by CI; analysis view tests broke unnoticed](../bugs/testing-root-tests-outside-ci.md): risk created by pixi run test vs CI scope split
- [Product 4 QC Audit Workbench: Stage 1 decisions, Stage 2 Sheets sync, tray handoff](analysis-qc-audit-workbench.md): the workbench tests cover this page
