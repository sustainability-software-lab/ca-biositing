---
type: Bug
title: "Test docs and layout drift: missing test files named in READMEs, duplicate conftests, misplaced diagnostics"
description: READMEs and testing-patterns.md name files that do not exist; two pipeline conftests are duplicated; one ’test_’ file is a CLI script.
tags: [testing, docs, layout]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:33Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/tests/README.md", "src/ca_biositing/pipeline/tests/README.md", ".agents/rules/testing-patterns.md", "tests/pipeline/conftest.py", "src/ca_biositing/pipeline/tests/conftest.py", "src/ca_biositing/pipeline/tests/test_usda_comprehensive.py", "scripts/test_db_queries.py"]
sources: [".agents/rules/testing-patterns.md", "src/ca_biositing/datamodels/tests/README.md", "src/ca_biositing/pipeline/tests/README.md"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Lists places where test documentation or layout will mislead a new contributor.

## Evidence
- src/ca_biositing/datamodels/tests/README.md names test_biomass.py and test_geographic_locations.py; neither exists (only test_package.py and test_view_filters.py are present).
- src/ca_biositing/pipeline/tests/README.md names test_lookup_utils.py, which does not exist (test_etl_extract.py does).
- .agents/rules/testing-patterns.md shows `client = TestClient(app)` with no auth override, and its flow-import example uses `primary_product_flow` / `analysis_type_flow`; no `primary_product.py` exists under flows/ (the module is primary_ag_product.py).
- tests/pipeline/conftest.py and src/ca_biositing/pipeline/tests/conftest.py both exist and differ (diff -q reports different content); pytest uses whichever is in the collected tree.
- src/ca_biositing/pipeline/tests/test_usda_comprehensive.py is a CLI diagnostic (`main()`, classes USDAAPITester, DatabaseAnalyzer, CommodityMapper at lines 65, 210, 400); its test_* methods are not collected by pytest because the classes do not start with Test.
- src/ca_biositing/pipeline/tests/database_diagnostics.py and scripts/test_db_queries.py are also non-pytest scripts.

## Open questions
- Whether the duplicate pipeline conftest is still needed: (inferred; confirm by checking which tests resolve each one).

# Related Concepts
- [Test suite layout, how to run each suite, and fixture map](../architecture/testing.md): layout these docs describe
- [Test counts per suite and what each file covers (HEAD e41d00d)](../facts/testing-suite-inventory.md): authoritative file list
