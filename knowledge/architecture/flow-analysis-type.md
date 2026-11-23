---
type: Architecture
title: Analysis Type ETL flow
description: "Inserts unique Analysis_type names from the Aim 1 Experiments tab into AnalysisType, insert-only; nested inside the Aim 2 and analysis-records flows."
tags: [pipeline, etl, prefect, flow, analysis-type, gsheet]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:58Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/analysis_type.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/experiments.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/analysis_type.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/analysis_type.py", "src/ca_biositing/pipeline/tests/test_flows.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/154", "https://github.com/sustainability-software-lab/ca-biositing/pull/66", "https://github.com/sustainability-software-lab/ca-biositing/pull/53", "commit 9d1e16f", "resources/prefect/run_prefect_flow.py"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Loads the distinct analysis type names (for example, ’proximate analysis’, ’xrd analysis’) that the experiments sheet uses, into AnalysisType. Entry point analysis_type_flow. It is also called as a nested subflow by the aim2_bioconversion and analysis_records flows, so it is effectively a shared dependency.

## Source
Google Sheet ’Aim 1-Feedstock Collection and Processing Data-BioCirV’, tab 03.0-Experiments, via etl/extract/experiments.py (task name extract_experiments). The transform reads the raw column ’Analysis_type’.

## Key files
| path:line | role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/analysis_type.py:3 | @flow analysis_type_flow (uses print, not the run logger) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/experiments.py | extractor for tab 03.0 |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/analysis_type.py:8 | transform_analysis_analysis_type, returns DataFrame with analysis_name |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/analysis_type.py:8 | load_analysis_analysis_type, insert-only |
| src/ca_biositing/pipeline/tests/test_flows.py | import smoke test for analysis_type_flow |

## How it works
1. Extract the experiments tab.
2. Transform: if ’Analysis_type’ is missing, log and return None. Otherwise take unique values into a single analysis_name column.
3. Load: read existing AnalysisType.name values, insert only new names, commit once.

## Interfaces
- Input: GSheet tab 03.0-Experiments, CREDENTIALS_PATH.
- Output: AnalysisType rows (name column).
- Callers: aim2_bioconversion, analysis_records (nested), master flow (AVAILABLE_FLOWS ’analysis_type’ in resources/prefect/run_prefect_flow.py).

## Gotchas
- Insert-only. Renamed or removed analysis types in the sheet are never removed from the table.
- The raw header must be exactly ’Analysis_type’. The extract does not clean headers first.
- If the extract returns None, the transform indexes data_sources[’experiments’] and fails on .columns (inferred from code; not run).
- The transform and load compare names as-is, so whitespace or case differences create new rows.
- The nested calls mean the same extract and load run again inside each parent flow. The insert-only load makes this safe but adds work.

## History
- 43f3147 (2025-10-29, PR #53) Prefect implementation and directory reorganisation.
- ab8fa6c (2025-11-05, PR #66) PEP 420 namespace-package reorganisation.
- 9d1e16f (2026-03-18, PR #154) Aim 2 fermentation ETL (latest flow-file change).

## Open questions
- Whether the analysis_type strings hard-coded in analysis_records match these names (see the analysis-records concept).

# Related Concepts
- [Aim 2 Bioconversion ETL flow](flow-aim2-bioconversion.md): Nested subflow that must run first so AnalysisType rows exist.
- [Analysis Records ETL flow (proximate, ultimate, compositional, ICP, XRF, calorimetry, XRD)](flow-analysis-records.md): Nested subflow whose analysis_type names come from the same convention.
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Standard extract, transform, load layout and the flow registry live here.
- [System overview (start here)](system-overview.md): Provides the lookup table for analysis types in the analytical data model.
