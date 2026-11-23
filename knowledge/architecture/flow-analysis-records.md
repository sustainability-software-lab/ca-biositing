---
type: Architecture
title: "Analysis Records ETL flow (proximate, ultimate, compositional, ICP, XRF, calorimetry, XRD)"
description: Loads seven analytical-lab record types from Aim 1 GSheet tabs into per-analysis record tables plus shared Observation rows; runs analysis_type first.
tags: [pipeline, etl, prefect, flow, analysis, lab-data, gsheet]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:53Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/analysis_records.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/proximate.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/ultimate.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/cmpana.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/icp.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/xrf.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/calorimetry.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/xrd.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/*_record.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/observation.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/*_record.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/observation.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/analysis_type.py"]
stale_after: "2026-12-31"
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/123", "https://github.com/sustainability-software-lab/ca-biositing/pull/220", "https://github.com/sustainability-software-lab/ca-biositing/pull/154", "https://github.com/sustainability-software-lab/ca-biositing/pull/84", "commit 5ebbe4f", "commit 930d868", "commit 85373ad", "resources/prefect/run_prefect_flow.py", "commit ca71a99", "https://github.com/sustainability-software-lab/ca-biositing/pull/523"]
---

## Purpose
Orchestrates analytical lab data: Proximate, Ultimate, Compositional (CmpAna), ICP, XRF, Calorimetry and XRD. Each produces a record table row and shared Observation rows. Flow name ’Analysis Records ETL’, entry point analysis_records_flow.

## Source
Google Sheet ’Aim 1-Feedstock Collection and Processing Data-BioCirV’, tabs: 03.1-Proximate, 03.7-Ultimate, 03.3-CmpAna, 03.5-ICP, 03.2-XRF, 03.6-Caloric, 03.4-XRD. The proximate.py and ultimate.py extract modules still carry TODO template comments, but their GSHEET_NAME and WORKSHEET_NAME values are real.

## Key files
| path:line | role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/analysis_records.py:4 | @flow and orchestration |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/proximate.py, ultimate.py, cmpana.py, icp.py, xrf.py, calorimetry.py, xrd.py | one extractor each |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/observation.py | shared Observation transform (takes the list of raw frames) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/proximate_record.py, ultimate_record.py, compositional_record.py, icp_record.py, xrf_record.py, calorimetry_record.py, xrd_record.py | per-analysis record transforms |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/observation.py:10 | load_observation |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/proximate_record.py, ultimate_record.py, compositional_record.py, icp_record.py, xrf_record.py, calorimetry_record.py, xrd_record.py | upserts on record_id; `qc_pass` and `note` protected while a QC decision is unsynced (ca71a99) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/analysis_type.py | nested subflow at step 0 |

## How it works
1. analysis_type_flow() as a subflow. Then create_etl_run_record and one lineage group.
2. safe_extract for each of the seven extractors. It sets analysis_type to a fixed string per analysis (’proximate analysis’, ’ultimate analysis’, ’compositional analysis’, ’icp analysis’, ’xrf analysis’, ’calorimetry analysis’, ’xrd analysis’), drops any incoming analysis_type column, and defaults dataset to ’biocirv’.
3. Transform: observations from all non-None frames in one call, then each record transform.
4. Load: observation first, then each record table, in fixed order.

## Interfaces
- Input: seven tabs above, CREDENTIALS_PATH.
- Output: Observation, ProximateRecord, UltimateRecord, CompositionalRecord, IcpRecord, XrfRecord, CalorimetryRecord, XrdRecord, plus EtlRun and LineageGroup.
- Downstream: materialized views that read these tables (see the views slice).

## Gotchas
- All seven record loads use the QC-aware upsert from `ca_biositing.pipeline.utils.qc_protected_records`. Protection applies only to rows with `synced_to_gsheet = False`. Observation rows are not protected.
- safe_extract returns None on ValueError or IOError (logged, the analysis is skipped). Any other exception is re-raised.
- Record transforms receive None when an extract failed. Each transform’s handling of None is not verified here (inferred; confirm per transform).
- Unlike aim2_bioconversion, the loads here are not gated on non-empty frames. It is unverified whether each record load handles empty frames (load_observation does).
- The analysis_type strings are hard-coded here and must match the AnalysisType names produced by analysis_type_flow from the experiments sheet. This match is unverified (inferred; confirm against the AnalysisType table).
- XRF and ICP observations are treated as 0 when value is null and record_id is present (observation transform), which is a deliberate business rule.

## History
- ca71a99 (2026-10-19, PR #523): QC upsert guard on the seven record loads.
- 5ebbe4f (2026-02-19, PR #123) comprehensive analytical suite (ICP, XRF, Calorimetry, XRD).
- a9a86eb (2026-02-05, PR #84) Berkeley Upstream integration.
- 9d1e16f (2026-03-18, PR #154) Aim 2 fermentation and analytical view refinement.
- 930d868 (2026-04-01, PR #220) data-portal schema with views (latest flow-file change).

## Open questions
- Whether empty per-analysis frames are safe through the record loads (see Gotchas).

# Related Concepts
- [Analysis Type ETL flow](flow-analysis-type.md): Nested subflow run first to create the AnalysisType names this flow’s analysis_type strings refer to.
- [Aim 2 Bioconversion ETL flow](flow-aim2-bioconversion.md): Shares the observation transform and load and the analysis_type convention.
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Uses the extract factory, shared observation transform and lineage helpers described there.
- [System overview (start here)](system-overview.md): Primary source of lab composition data for the analysis views.
- [QC review decision ledger (qc_review_decision table, lifecycle, seed CSV)](qc-review-decision-ledger.md): source of the protection rows
- [QC decisions are protected from ETL overwrite until they reach the Google Sheet](../decisions/qc-decisions-protected-from-etl-overwrite.md): why these loads skip QC columns
