---
type: Bug
title: Pipeline QC writeback utility maps records to the wrong sheet names and tabs
description: "pipeline utils/gsheet_qc_writeback.py uses sheet names and tab numbers that do not match the ETL extractors. It is dormant today, but would write to the wrong tabs if wired in."
tags: [qc, gsheet, pipeline, bug]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:09Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gsheet_qc_writeback.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/", "src/ca_biositing/webservice/ca_biositing/webservice/services/gsheet_sync_service.py"]
sources: ["commit ca71a99"]
governance: context
stale_after: "2026-12-31"
---

## Symptom
If `writeback_qc_decision_to_gsheet` were called, it would look up the wrong tab for several record types, and could fail (record not found) or update the wrong analysis. The webservice mapping (`gsheet_sync_service.py:37-60`) matches the extractors.

## Location
`src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gsheet_qc_writeback.py`:
- lines 22-24: `AIM1_GSHEET_NAME = "Aim 1 - Feedstock CharacterizationData"`, `AIM2_BIOCHEM_GSHEET_NAME = "Aim 2 - BioChem Conversion Data"`, `AIM2_THERMO_GSHEET_NAME = "Aim 2 - ThermoChem Conversion Data"`. Extractors use `Aim 1-Feedstock Collection and Processing Data-BioCirV`, `Aim 2-Biomass Biochem Conversion Data-BioCirV`, `Aim 2-Thermochem Conversion Data-BioCirV` (e.g. `etl/extract/xrd.py:7`, `thermochem_data.py:7`).
- lines 26-37 tab mapping against the extractors’ `WORKSHEET_NAME`:
  - ultimate: writeback `03.2-Ultimate`, extractor `03.7-Ultimate` (`extract/ultimate.py:25`)
  - icp: writeback `03.4-ICP`, extractor `03.5-ICP` (`extract/icp.py:8`)
  - xrf: writeback `03.5-XRF`, extractor `03.2-XRF` (`extract/xrf.py:8`)
  - xrd: writeback `03.6-XRD`, extractor `03.4-XRD` (`extract/xrd.py:8`)
  - calorimetry: writeback `03.7-Calorimetry`, extractor `03.6-Caloric` (`extract/calorimetry.py:8`)

## Reach
Only `tests/pipeline/test_qc_writeback_and_seed.py` (which uses a fake gspread with `03.1-Proximate` only, so it does not catch this) and `docs/pipeline/ETL_WORKFLOW.md` reference it. No flow or endpoint imports it.

## Status
Open at HEAD a2c8de8. Low severity while dormant. Read from code.

# Related Concepts
- [Stage 2 Google Sheets writeback: webservice path and dormant pipeline copy](../architecture/gsheet-qc-writeback.md): the live implementation
- [Google Sheets extraction: factory, gsheet_to_df, and retries](../architecture/pipeline-gsheet-extraction.md): the extractor names that are correct
