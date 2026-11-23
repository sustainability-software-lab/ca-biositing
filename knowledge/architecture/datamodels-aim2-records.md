---
type: Architecture
title: "Aim 2 processing and conversion tables (pretreatment, fermentation, gasification)"
description: "Aim 2 tables hold thermochemical and bioconversion experiment setups, methods, strains and runs; outcome numbers are in observation."
tags: [datamodels, aim2, bioconversion, thermochem, pretreatment, fermentation, gasification]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:04Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/aim2_records/*.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/aim2_bioconversion.py"]
sources: ["commit 9d1e16f", "commit a4e6fc9", "commit 543adde", "commit b328b5f", "commit e6ee628", "https://github.com/sustainability-software-lab/ca-biositing/pull/154", "https://github.com/sustainability-software-lab/ca-biositing/pull/217", "https://github.com/sustainability-software-lab/ca-biositing/pull/370", "https://github.com/sustainability-software-lab/ca-biositing/pull/377", "docs/architecture.md"]
governance: context
---

## Purpose
Records for Aim 2 experiments that convert feedstock: pretreatment and enzymatic hydrolysis, fermentation (bioconversion), gasification (thermochemical), and autoclave runs. Setup entities (methods, strains, vessels) sit beside per-run record tables.

## Key files
| Path:line | Role |
|---|---|
| models/aim2_records/autoclave_record.py:7 | `autoclave_record`: no extra columns (Aim2RecordBase only). No ETL references found at e41d00d |
| models/aim2_records/fermentation_record.py:8 | `fermentation_record`: strain_id, bioconversion_method_id, pretreatment_method_id, pretreatment_setup_id, eh_method_id (to method), eh_method_id_new (to enz_hydr_method), well_position, vessel_id (to decon_vessel), analyte_detection_equipment_id (no FK) |
| models/aim2_records/gasification_record.py:8 | `gasification_record`: reactor_type_id (to decon_vessel). Comment says feedstock mass, bed temperature and gas flow were moved to observation |
| models/aim2_records/gasification_timeseries.py:8 | `gasification_timeseries`: metadata for archived per-run CSV timeseries in GCS. Unique (resource_id, experiment_id). Stores bucket_path, file_size, checksum_md5, gsheet_url |
| models/aim2_records/pretreatment_record.py:8 | `pretreatment_record`: pretreatment_method_id and eh_method_id as plain ints (no FK), reaction_block_id, vessel_id, block_position, temperature, replicate_no |
| models/aim2_records/pretreatment_setup.py:9 | `pretreatment_setup`: experiment-level setup. JSON/JSONB lists `resources` and `prepared_samples` (string ids), decon_method_id, decon_vessel_id, eh_method_id, experiment_date, analyst_email |
| models/aim2_records/bioconversion_method.py:5 | `bioconversion_method`: unique name, strain_id, inoculum_volume_L, reaction_volume_L, temperature_C, time_h, protocol_url |
| models/aim2_records/enz_hydr_method.py:6 | `enz_hydr_method`: enzymatic hydrolysis protocol; eh_uuid, eh_id (unique), method_id (string), enzyme_formulation, temperature_c, time_h |
| models/aim2_records/strain.py:6 | `strain` (LookupBase): name (unique), parent_strain_id, genus, species, strain |

Tables: autoclave_record, fermentation_record, gasification_record, gasification_timeseries, pretreatment_record, pretreatment_setup, bioconversion_method, enz_hydr_method, strain (9 tables).

## How it works
The Aim 2 bioconversion Prefect flow (pipeline flows/aim2_bioconversion.py) runs in order: pretreatment setup and records, then methods and strains, then fermentation records. Observations for run measurements are loaded through the shared observation transform/load. Gasification archives its timeseries to GCS and records only metadata here.

## Interfaces
- Writers: pipeline etl transform and load under analysis/ (pipeline slice).
- Readers: materialized views such as mv_biomass_fermentation and mv_biomass_gasification (data_portal_views, per docs/data_dictionary.md).
- Method references are split: some columns FK to `method.id`, others to `enz_hydr_method.id`, and some are unconstrained integers. See decisions/datamodels-unconstrained-fk-convention.

## Gotchas
- fermentation_record.py ends with a `# ... other fields if they exist` placeholder comment; treat the column list as possibly incomplete.
- `eh_method_id` (to method) and `eh_method_id_new` (to enz_hydr_method) coexist on fermentation_record; the `_new` suffix signals a migration in progress (inferred; confirm with the view code).
- pretreatment_record.pretreatment_method_id has no FK, unlike fermentation_record.pretreatment_method_id which FKs to method.id.
- gasification_timeseries.file_format defaults to csv; checksum is md5 only here (FileObjectMetadata also has sha256).

## History
- 9d1e16f (PR #154, Aim 2 fermentation ETL) is the commit that introduced decon_vessel (verified with git log -S); fermentation ETL work landed here.
- a4e6fc9 (PR #217, gasification ETL) introduced the note that feedstock mass, bed temperature and gas flow are now observations (verified with git log -S).
- 543adde (PR #370, bioconversion ETL) introduced pretreatment_setup and enz_hydr_method (verified with git log -S).
- e6ee628 (PR #268, mv_biomass_fermentation fixes) introduced bioconversion_method (verified with git log -S).
- b328b5f (PR #377, gasification ETL) introduced gasification_timeseries. 45b98d1 (PR #395) added reactor_name.

## Open questions
- Autoclave: is autoclave_record loaded anywhere (inferred from zero references by class name; confirm by grepping the pipeline for autoclave loads)?
- Confirm the intended meaning of analyte_detection_equipment_id, which has no FK.

# Related Concepts
- [Aim 1 analytical record tables (proximate, ultimate, XRF, ICP, etc.)](datamodels-aim1-records.md): Parallel record family; both use Aim2RecordBase/Aim1RecordBase key columns
- [General analysis: observation (long-format measurements), dataset, analysis type, dimension type](datamodels-general-analysis.md): Run outcomes are stored as observation rows keyed by record_id
- [Experiment and equipment: experiment header, decon vessels, and link tables to methods, samples and analyses](datamodels-experiment-equipment.md): Experiment, decon_vessel and equipment tables are the setup context for Aim 2 runs
- [Resource information: biomass resource, residue factors, availability, prices, end uses](datamodels-resource-information.md): Aim 2 records and pretreatment_setup reference feedstock resources by id or name
- [Research aims: Aim 1 feedstock characterization vs Aim 2 conversion experiments](../facts/domain-aims-aim1-aim2.md): Explains what Aim 2 covers in the research program
- [System overview (start here)](system-overview.md): Hub for the ETL-to-database-to-API flow
