---
type: Bug
title: "About 40 ETL, utils and template modules have no test reference"
description: "Name-level grep finds extract/transform/load and utils modules (autoclave, compost, decon_*, provider_info, ...) with no test reference."
tags: [testing, etl, coverage]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:50Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/**", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/*.py"]
sources: ["grep at HEAD e41d00d (this slice)"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Concrete list of pipeline modules that no test file names, for prioritising new tests.

## Evidence
Word-match grep of module basenames under src/ca_biositing/pipeline/ca_biositing/pipeline/etl, utils and flows against all test files (HEAD e41d00d). Templates excluded. Text match only: a module may be exercised indirectly.

Untested by name (selection):
- extract: autoclave, ca_proc_points, cmpana, decon_methods, decon_vessels, experiments, enz_hydr_methods, bioconversion_parameters, bioconversion_setup, petroleum_pipelines, provider_info (also `geospatial`, `gsheet_sheets` in utils).
- transform: analysis_records, compositional_record, county_ag_datasets, field_sample_v03, location_address_v03, ultimate_record, proximate_record.
- utils: gcs_utils, geo_utils, us_state_abbrev, usda_nass_to_pandas, populate_api_names, reviewed_api_mappings, run_pipeline, clear_alembic, interactive_commodity_mapper, template_comprehensive_commodity_mapping.

## Impact
These modules feed the analysis tables. Changes can break loads without any failing test. Their upstream role in the pipeline was not traced in this slice.

## Open questions
- Which of these are dead code: not determined in this slice. (inferred; confirm against `git log --follow` for each file.)

# Related Concepts
- [Test suite layout, how to run each suite, and fixture map](../architecture/testing.md): test-layout parent
- [14 of 20 Prefect flow modules are not imported by any test](etl-flows-without-tests.md): flow-level companion gap
