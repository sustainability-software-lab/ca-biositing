---
type: Architecture
title: "Thermochemical Conversion ETL flow (Aim 2 sheet to experiment, observation, gasification)"
description: "Loads experiments, observations and gasification records from the Aim 2 thermochem sheet, then triggers the gasification archive subflow for unique GSheet URLs."
tags: [pipeline, etl, flow, thermochem, gasification, google-sheets]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:51Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/thermochem_etl.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/gasification_archive_pipeline.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/thermochem_data.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/experiment.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/observation.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/gasification_record.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/gasification_archive.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/experiment.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/observation.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/gasification_record.py"]
stale_after: "2026-12-31"
sources: ["commit a4e6fc9", "commit b328b5f", "commit 45b98d1", "commit c5a592e", "https://github.com/sustainability-software-lab/ca-biositing/pull/217", "https://github.com/sustainability-software-lab/ca-biositing/pull/493", "commit ca71a99"]
---

**Purpose**
Loads thermochemical conversion (gasification) experiments and their time-series observations from the Aim 2 Google Sheet, then archives referenced sheet URLs through a subflow.

**Key files**

| Path:line | Role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/thermochem_etl.py:4-5 | `@flow(name="Thermochemical Conversion ETL")` `thermochem_etl_flow(force_refresh=False, *args, **kwargs)` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/thermochem_data.py:7-11 | GSheet `Aim 2-Thermochem Conversion Data-BioCirV`, tabs `01-ThermoExperiment` and `02-ThermoData` (plus setup tabs at lines 14-21) |
| etl/transform/analysis/experiment.py | `transform_experiment` |
| etl/transform/analysis/observation.py | `transform_observation` (dataset set to `biocirv`, analysis_type from sheet or default gasification) |
| etl/transform/analysis/gasification_record.py | `transform_gasification_record` (uses experiment DataFrame) |
| etl/transform/analysis/gasification_archive.py | `build_gasification_archive_records` |
| etl/load/analysis/experiment.py, observation.py, gasification_record.py | Load functions for each table. `gasification_record` is QC-protected (ca71a99): unsynced QC decisions keep `qc_pass` and `note` on reload |
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/gasification_archive_pipeline.py:152 | `gasification_archive_subflow` (archives to GCS, records metadata) |

**How it works**
1. Lineage record and group.
2. Extract experiment and data tabs. If data is empty, the flow logs and stops.
3. Load experiments, then observations (record_id from Record_id, Rx_UUID or RxID), then gasification records.
4. If gasification records exist, build archive records and call the archive subflow with `force_refresh`, `etl_run_id` and `lineage_group_id` cast to int.

**Interfaces**
- Input: GSheet above.
- Output: `experiment`, `observation`, `gasification_record`, and archive metadata via the subflow.
- Callers: master registry (run_prefect_flow.py:27).

**Gotchas**
- `*args, **kwargs` are accepted and ignored.
- Calls `create_etl_run_record` and `create_lineage_group` directly (not `.fn`), unlike most other flows; behavior is the same inside a flow run.
- Archive step only runs when gasification records were produced, so a run with no new records does not archive.
- `int(etl_run_id)` and `int(lineage_group)` assume numeric IDs.

**History**
- ca71a99 (2026-10-19, PR #523): gasification_record load uses the QC-aware upsert.
- a4e6fc9 (2026-04-01, PR #217 Gasification ETL pipeline): flow introduced.
- b328b5f (2026-06-01, PR #377) and 45b98d1 (2026-06-09, PR #395, reactor name in gasification_timeseries): later changes.
- c5a592e (2026-10-08, PR #493): archival prep moved into a transform task.
- https://github.com/sustainability-software-lab/ca-biositing/pull/217 and https://github.com/sustainability-software-lab/ca-biositing/pull/493

**Open questions**
- The archive subflow’s own gotchas belong to the gasification archive concept (owned elsewhere).

# Related Concepts
- [System overview (start here)](system-overview.md): Thermochem analysis data is one of the analysis domains loaded by the pipeline
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Uses shared lineage helpers and the subflow pattern
- [Field Sample ETL flow (four-worksheet join)](flow-field-sample-etl.md): Experiments and observations reference resources and feedstock records (inferred; confirm in load code)
- [QC review decision ledger (qc_review_decision table, lifecycle, seed CSV)](qc-review-decision-ledger.md): source of the protection rows
