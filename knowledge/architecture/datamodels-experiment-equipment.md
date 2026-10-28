---
type: Architecture
title: "Experiment and equipment: experiment header, decon vessels, and link tables to methods, samples and analyses"
description: "experiment is the named run header; four link tables attach it to analysis types, equipment, methods and prepared samples; decon_vessel is the reactor or well plate."
tags: [datamodels, experiment, equipment, decon-vessel, link-tables]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:10Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/experiment_equipment/*.py"]
sources: ["commit a9a86eb", "commit 7a41e0e", "commit 543adde", "https://github.com/sustainability-software-lab/ca-biositing/pull/84", "https://github.com/sustainability-software-lab/ca-biositing/pull/370"]
governance: context
---

## Purpose
An experiment is a named laboratory run (analyst, start date, duration, location). Link tables record which analysis types, equipment, methods and prepared samples belong to it. Decon vessels are the physical reactors or multi-well plates used for pretreatment and conversion.

## Key files
| Path:line | Role |
|---|---|
| experiment_equipment/experiment.py:9 | `experiment`: name (unique), analyst_id (contact), exper_start_date, exper_duration (+ unit FK), exper_location_id (location_address), description |
| experiment_equipment/equipment.py | `equipment` (LookupBase): equipment_location_id to location_address |
| experiment_equipment/decon_vessel.py | `decon_vessel` (LookupBase): vessel_uuid (unique), serial_number, volume_numeric_per_well, volume_unit |
| experiment_equipment/experiment_links.py | `experiment_analysis` (experiment_id, analysis_type_id), `experiment_equipment` (experiment_id, equipment_id), `experiment_method` (experiment_id, method_id), `experiment_prepared_sample` (experiment_id, prepared_sample_id). All use a plain integer id primary key |

Tables: experiment, equipment, decon_vessel, experiment_analysis, experiment_equipment, experiment_method, experiment_prepared_sample (7 tables).

## How it works
Aim 1 and Aim 2 records carry experiment_id. Experiment is the join point between a run and its context. Decon vessels are referenced by pretreatment_record.vessel_id, fermentation_record.vessel_id, gasification_record.reactor_type_id, pretreatment_setup.decon_vessel_id and gasification_timeseries.reactor_type_id.

## Interfaces
- Writers: Aim 2 and analytical ETL flows (experiments.py extract, pipeline slice).
- Readers: Aim record views and webservice analysis endpoints.

## Gotchas
- The four link tables have no BaseEntity fields (no created_at or lineage). Their rows cannot be traced to an ETL run.
- experiment_analysis, experiment_equipment, experiment_method and experiment_prepared_sample have no ETL or view references by class name at e41d00d (see facts/domain-models-usage-snapshot). Their role is as much metadata as runtime data.
- experiment.name is unique, so experiment names must be stable across ETL runs.

## History
- experiment_analysis: introduced in a9a86eb (PR #84, verified with git log -S). decon_vessel: introduced in 9d1e16f (PR #154, verified). The experiment class traces to the 608530b import commit (git log -S).

## Open questions
- Whether the experiment_* link tables are populated by any flow (inferred zero references; confirm).

# Related Concepts
- [Aim 2 processing and conversion tables (pretreatment, fermentation, gasification)](datamodels-aim2-records.md): Aim 2 run records reference experiment, decon_vessel and strain
- [Aim 1 analytical record tables (proximate, ultimate, XRF, ICP, etc.)](datamodels-aim1-records.md): Aim 1 records reference experiment_id
- [Methods, parameters, units and technical assumptions: the measurement vocabulary](datamodels-methods-parameters-units.md): experiment_method links an experiment to method rows
- [Sample chain: field samples, collection and storage, then prepared samples and preparation methods](datamodels-sample-chain.md): experiment_prepared_sample links an experiment to prepared samples
- [System overview (start here)](system-overview.md): Hub for the ETL-to-database-to-API flow
