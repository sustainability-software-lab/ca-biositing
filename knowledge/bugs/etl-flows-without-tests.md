---
type: Bug
title: 14 of 20 Prefect flow modules are not imported by any test
description: "Only 5-6 flow modules are referenced by tests; flows such as landiq_etl, usda_etl, samples_etl and thermochem_etl have no direct test."
tags: [testing, etl, prefect, flows, coverage]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:49Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/*.py", "src/ca_biositing/pipeline/tests/test_flows.py", "src/ca_biositing/pipeline/tests/test_residue_factors_flow.py"]
sources: ["grep of tests for flow module names at HEAD e41d00d", "src/ca_biositing/pipeline/tests/test_flows.py"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Lists flow entry points with no test import, so a regression in orchestration (task order, parameters, deployment names) is not caught.

## Evidence
Flow modules in src/ca_biositing/pipeline/ca_biositing/pipeline/flows/: 20 files.
- Directly imported by tests: almond_nsjv_etl, analysis_type, primary_ag_product (src/.../pipeline/tests/test_flows.py), residue_factors_flow (src/.../pipeline/tests/test_residue_factors_flow.py), county_ag_report_etl (tests/pipeline/test_county_ag_report_etl.py), resource_information (tests/pipeline/test_resource_images_etl.py via `flows import`).
- No test import found: aim2_bioconversion, analysis_records, billion_ton_etl, biodiesel_plants, field_sample_etl, gasification_archive_pipeline, geography, landiq_etl, prepared_sample_etl, qualitative, samples_etl, static_resource_info, thermochem_etl, usda_etl.
- test_flows.py only checks import and callable; it does not run the flow.

## Impact
ETL orchestration errors surface only in production Prefect runs. Underlying ETL modules are often tested (see facts/testing-suite-inventory) so the gap is the flow wiring, not every transform.

## Open questions
- Whether a flow-level dry-run test is feasible without Docker: (inferred; confirm).
- Flow names vs module names differ for some (e.g. `landiq_etl`); the grep was by module name (text match).

# Related Concepts
- [Test suite layout, how to run each suite, and fixture map](../architecture/testing.md): test-layout parent
- [System overview (start here)](../architecture/system-overview.md): flows are the ETL entry points
- [About 40 ETL, utils and template modules have no test reference](etl-modules-without-tests.md): the same gap at module level
