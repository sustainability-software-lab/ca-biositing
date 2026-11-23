---
type: Fact
title: Test counts per suite and what each file covers (HEAD e41d00d)
description: "Test counts per suite at e41d00d, the file-to-module map, and a def-count table of the dashboard, workbench, drift and QC API tests added in #517-#535."
tags: [testing, inventory, coverage]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:03Z" }
status: stable
governance: context
code_refs: ["tests/**", "src/ca_biositing/datamodels/tests/**", "src/ca_biositing/pipeline/tests/**", "src/ca_biositing/webservice/tests/**"]
stale_after: "2026-12-31"
sources: ["commit e41d00d", "pytest --collect-only at HEAD e41d00d (this slice)", "commit a2c8de8", "commit f954bd3", "commit 4f3e0be", "commit 587c1cb", "commit c4cbf2d", "commit d290906"]
---

## Purpose
Snapshot of how many tests each suite collects and which modules each test file exercises. Counts at e41d00d were collected via `pixi run --frozen python -m pytest --collect-only -q <path>`; nothing was executed. The dashboard tests added after e41d00d are counted by `def test_` lines only, not by collection (no collection run in this review).

## Counts (collected at e41d00d)
| Suite path | Collected | Test files | In CI |
|---|---|---|---|
| tests/ (whole root tree) | 318 | 33 | only tests/agent_harness is in CI |
| tests/agent_harness/ | 43 | 10 | yes (harness job) |
| tests/ minus agent_harness | 275 | 23 | no |
| src/ca_biositing/datamodels/ | 17 | 2 | yes |
| src/ca_biositing/pipeline/ | 123 | 28 | yes |
| src/ca_biositing/webservice/ | 26 | 3 | yes, `-m "not integration"` |

## Added after e41d00d (def count, not collected)
| Test file | `def test_` count | Exercises | In CI |
|---|---|---|---|
| tests/analysis/test_resource_audit_workbench.py | 6 | Product 4 build, snapshot loader branches, gallery and login HTML | no |
| tests/analysis/test_live_qc_overlay_and_tray.py | 6 | live QC overlay, BroadcastChannel, tray-to-workbench, Node execution | no |
| tests/audit/test_db_environment_drift.py | 3 | no hard-coded personal paths; committed or fixture fingerprints; unreachable-DB fallback | no |
| tests/test_resource_slice_export.py | 11 | Page 1-3 QC defaults, slice isolation, multi-resource filters, bug-URL builder, issue #515 date filtering, Report a Bug across the suite | no |
| tests/webservice/test_qc_review.py | 4 | `/v1/qc` API (see the webservice QC concept) | no |

Total added: 30 test functions in 5 files (1 directory `__init__.py` excluded). Parametrized cases are not counted.

## Map: test file to module (root tests/)
| Test file | Exercises |
|---|---|
| tests/datamodels/test_config.py | ca_biositing.datamodels.config (DB URL resolution) |
| tests/test_namespace_imports.py | top-level imports of datamodels, pipeline flows |
| tests/pipeline/test_resource_images_etl.py | extract/transform/load resource_information + flows package |
| tests/pipeline/test_residue_factor_etl.py | residue_factors extract/transform/load |
| tests/pipeline/test_county_ag_report_etl.py | county_ag_report extract/transform/load + flow |
| tests/pipeline/test_field_sample_integration.py | producers, qty_field_storage, sample_desc, sample_ids -> field_sample transform |
| tests/pipeline/test_qualitative_*.py | qualitative extract/transform/load |
| tests/pipeline/test_bioconversion_method_etl.py, test_almond_nsjv_load.py, test_name_id_swap.py | respective transform/load and name-id swap |
| tests/pipeline/etl/transform/analysis/*.py | enz_hydr_method, pretreatment_setup transforms |
| tests/webservice/v1/test_analysis.py | /v1/feedstocks/analysis routes |
| tests/webservice/v1/test_availability.py | /v1/feedstocks/availability routes |
| tests/webservice/v1/test_usda_census.py, test_usda_survey.py | /v1/feedstocks/usda/{census,survey} routes |
| tests/webservice/v1/test_auth.py, test_api_keys.py, test_exceptions.py | auth router, API key routes, webservice exceptions |
| tests/webservice/test_auth_endpoints.py, test_auth_service.py | auth endpoints and auth_service |
| tests/webservice/test_qc_review.py | `/v1/qc` routes (added a2c8de8) |
| tests/analysis/*, tests/audit/*, tests/test_resource_slice_export.py | dashboard, workbench, drift and slice modules (see the added table) |

## Map: test file to module (src package tests)
| Test file | Exercises |
|---|---|
| datamodels/tests/test_view_filters.py | 5 materialized view definitions via compiled SQL (see bugs/datamodels-materialized-views-partially-tested) |
| pipeline/tests/test_flows.py | import-only checks for almond_nsjv_etl, analysis_type, primary_ag_product flows |
| pipeline/tests/test_residue_factors_flow.py | residue_factors flow structure and error handling, mocked |
| pipeline/tests/test_landiq_load.py, test_landiq_transform.py | landiq load and transform |
| pipeline/tests/test_static_resource_info_{extract,transform,load}.py | static_resource_info ETL triple |
| pipeline/tests/test_fermentation_etl.py, test_fermentation_record_etl.py, test_pretreatment_etl.py | fermentation/pretreatment records and observations |
| pipeline/tests/test_thermochem_{extract,transform}.py, test_gasification_archive_transform.py | gasification/thermochem partial coverage (flow not tested) |
| pipeline/tests/test_billion_ton_etl.py, test_seeding.py, USDA/*.py | billion_ton ETL, seed_commodity_mappings, USDA discovery/survey/api names |
| pipeline/tests/test_usda_comprehensive.py | NOT a pytest suite; CLI diagnostic (see bugs/doc-drift-testing) |
| webservice/tests/test_health.py | /v1/health with DB available and unavailable |
| webservice/tests/test_smoke.py | 23 integration tests against a live server (see facts/testing-integration-smoke-tests) |

## Gotchas
- Counts are collection-only; a collected test may skip or fail at run time (e.g. USDA survey tests call pytest.skip when helpers are absent).
- The dashboard tests need `node` on PATH (tests/test_resource_slice_export.py:422-423 asserts it) and generate HTML from the current generators, so a failing generator fails the test even when the page is unchanged.

# Related Concepts
- [Test suite layout, how to run each suite, and fixture map](../architecture/testing.md): layout and commands this inventory belongs to
- [Current state snapshot (2026-10-16)](current-state.md): current-state snapshot of repo at HEAD e41d00d
- [Product 4 QC Audit Workbench: Stage 1 decisions, Stage 2 Sheets sync, tray handoff](../architecture/analysis-qc-audit-workbench.md): workbench and overlay tests
- [Multi-environment DB drift assessment (4 layers, local/staging/production)](../architecture/analysis-db-drift-assessment.md): drift test file
