---
type: Architecture
title: Aim 2 Bioconversion ETL flow
description: "Loads Aim 2 pretreatment, enzymatic hydrolysis, strain, bioconversion-method and fermentation data from the Aim 2 Biomass Biochem GSheet; runs analysis_type first."
tags: [pipeline, etl, prefect, flow, aim2, bioconversion, gsheet]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:50Z" }
status: stable
governance: constraint
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/aim2_bioconversion.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/pretreatment_setup.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/pretreatment_data.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/bioconversion_data.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/bioconversion_methods.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/enz_hydr_methods.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/pretreatment_*.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/enz_hydr_method.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/bioconversion_method.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/fermentation_record.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/observation.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/pretreatment_*.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/enz_hydr_method.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/strain.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/bioconversion_method.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/fermentation_record.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/observation.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/analysis_type.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/factory.py"]
stale_after: "2026-12-31"
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/370", "https://github.com/sustainability-software-lab/ca-biositing/pull/268", "https://github.com/sustainability-software-lab/ca-biositing/pull/260", "https://github.com/sustainability-software-lab/ca-biositing/pull/220", "https://github.com/sustainability-software-lab/ca-biositing/pull/154", "commit 543adde", "commit e6ee628", "commit 9d1e16f", "resources/prefect/run_prefect_flow.py", "commit ca71a99", "https://github.com/sustainability-software-lab/ca-biositing/pull/523"]
---

## Purpose
Orchestrates the Aim 2 bioconversion ETL: pretreatment setup and records, enzymatic hydrolysis methods, strains, bioconversion methods, and fermentation records, plus their Observation rows. Flow name ’Aim 2 Bioconversion ETL’. Entry point: aim2_bioconversion_flow.

## Source
Google Sheet ’Aim 2-Biomass Biochem Conversion Data-BioCirV’, worksheet tabs (via etl/extract/factory.py create_extractor, retries=3):
- 01.1-PretreatmentSetup (pretreatment_setup)
- 02.1-PretreatmentData (pretreatment_data)
- 02.2-BioConversionData (bioconversion_data, fermentation)
- 03.3-BioConversionMethods (bioconversion_methods)
- 03.2-EnzHydrMethods (enz_hydr_methods)
bioconversion_setup (01.2-BioConversionSetup) is imported by the flow but never used.

## Key files
| path:line | role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/aim2_bioconversion.py:5 | @flow definition, Parts 1-3 |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/pretreatment_setup.py | extract tab 01.1 |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/pretreatment_data.py | extract tab 02.1 |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/bioconversion_data.py | extract tab 02.2 |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/bioconversion_methods.py | extract tab 03.3 |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/enz_hydr_methods.py | extract tab 03.2 |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/factory.py | create_extractor task factory |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/pretreatment_setup.py | transform_pretreatment_setup |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/pretreatment_record.py | transform_pretreatment_record |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/enz_hydr_method.py | transform_enz_hydr_method |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/bioconversion_method.py | transform_bioconversion_method |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/fermentation_record.py | transform_fermentation_record |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/observation.py | transform_observation (shared) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/pretreatment_setup.py | upsert keyed on pretreatment_exper_id |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/pretreatment_record.py | upsert keyed on record_id; `qc_pass` and `note` protected while a QC decision is unsynced (ca71a99) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/enz_hydr_method.py | upsert keyed on eh_id |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/strain.py | upsert Strain plus stale-row delete |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/bioconversion_method.py | upsert BioconversionMethod |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/fermentation_record.py | upsert FermentationRecord; same QC protection as pretreatment (ca71a99) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/observation.py:10 | load_observation (shared upsert) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/analysis_type.py | analysis_type_flow, run as a nested subflow at step 0 |

## How it works
1. analysis_type_flow() runs first as a subflow.
2. create_etl_run_record once, then three lineage groups (pretreatment; methods and strains; fermentation).
3. Part 1: extract pretreatment_setup, transform and load it if non-empty. Then extract pretreatment_data, write observations with analysis_type=’pretreatment’ and dataset default ’biocirv’, then write pretreatment records.
4. Part 2: extract bioconversion_methods. If non-empty, load enz_hydr_methods, then build Strain rows from the methods sheet (columns strain_name, genus, species, strain, description, note after cleaning_mod.clean_names_df), drop_duplicates on name, and load_strain. Only then load BioconversionMethod rows (the code comment says strains must load first).
5. Part 3: extract bioconversion_data, write observations with analysis_type=’fermentation’, then FermentationRecord rows.

Each stage is skipped when its extract is None or empty. Each load task is a Prefect task with retries=3.

## Interfaces
- Input: Google Sheet tabs above, read with gsheet_to_df using CREDENTIALS_PATH (default credentials.json).
- Output: DB tables PretreatmentSetup, PretreatmentRecord, EnzymaticHydrolysisMethod, Strain, BioconversionMethod, FermentationRecord, Observation.
- Lineage: EtlRun and LineageGroup rows via utils/lineage.py.
- Callers: master flow in resources/prefect/run_prefect_flow.py (AVAILABLE_FLOWS ’aim2_bioconversion’), or run directly.

## Gotchas
- `pretreatment_record` and `fermentation_record` skip `qc_pass` and `note` on reload for record_ids with an unsynced `qc_review_decision` row. See `architecture/qc-review-decision-ledger` and `decisions/qc-decisions-protected-from-etl-overwrite`.
- Strain load (etl/load/analysis/strain.py, around lines 60-75) deletes Strain rows that have null genus, species and strain and are not in the loaded set. This is a destructive cleanup on every run.
- Observation analysis_type strings are hard-coded in the flow (’pretreatment’, ’fermentation’). The fermentation observation transform treats xrf and icp specially, but this flow does not.
- Stages gate on non-empty extracts, so an empty tab silently skips its tables.
- Column names come from cleaned sheet headers. A renamed header breaks the strain mapping silently (the code falls back to lowercasing headers if clean_names_df raises).

## History
- ca71a99 (2026-10-19, PR #523): QC upsert guard added to the pretreatment and fermentation record loads.
- 9d1e16f (2026-03-18, PR #154) Aim 2 Fermentation ETL added.
- 930d868 (2026-04-01, PR #220) data-portal schema with views.
- bd0ec5e (2026-04-14, PR #260) multiple ETL refinements.
- e6ee628 (2026-04-30, PR #268) mv_biomass_fermentation fixes.
- 543adde (2026-05-21, PR #370) Bioconversion ETL and view improvements (latest flow-file change).
See https://github.com/sustainability-software-lab/ca-biositing/pull/370 and the matching PR URLs for the rest.

## Open questions
- Whether bioconversion_setup should be loaded. It is imported but unused (inferred; confirm with the Aim 2 data owner).
- Whether the stale-strain delete is intended (confirm against the Strain model’s consumers).

# Related Concepts
- [Analysis Type ETL flow](flow-analysis-type.md): Runs analysis_type_flow as a nested subflow before any loads, so AnalysisType rows exist.
- [Analysis Records ETL flow (proximate, ultimate, compositional, ICP, XRF, calorimetry, XRD)](flow-analysis-records.md): Sibling analytical flow that also writes Observation rows and calls analysis_type_flow.
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Flow sits inside the extract/transform/load framework and factory pattern described there.
- [System overview (start here)](system-overview.md): Source-of-truth GSheet to Postgres path for Aim 2 data.
- [QC review decision ledger (qc_review_decision table, lifecycle, seed CSV)](qc-review-decision-ledger.md): source of the protection rows
- [QC decisions are protected from ETL overwrite until they reach the Google Sheet](../decisions/qc-decisions-protected-from-etl-overwrite.md): why these loads skip QC columns
