---
type: Architecture
title: "Aim 1 analytical record tables (proximate, ultimate, XRF, ICP, etc.)"
description: "Nine Aim 1 lab-analysis record tables share Aim1RecordBase keys; measured values live in observation, not in these tables."
tags: [datamodels, aim1, analysis-records, feedstock-characterization]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:03Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/base.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/aim1_records/*.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/proximate_record.py"]
sources: ["commit a9a86eb", "commit 7a41e0e", "commit 5ebbe4f", "https://github.com/sustainability-software-lab/ca-biositing/pull/84", "https://github.com/sustainability-software-lab/ca-biositing/pull/112", "https://github.com/sustainability-software-lab/ca-biositing/pull/123", "docs/pipeline/USDA/ANALYTICS_HANDOFF.md", "docs/datamodels/CONTRIBUTING.md"]
governance: context
---

## Purpose
One table per Aim 1 lab technique (feedstock characterization). Each row is one analysis run on one prepared sample, identified by a unique `record_id`. The row carries provenance and QC context only; the measured numbers are written as `observation` rows keyed by `record_id`.

## Key files
| Path:line | Role |
|---|---|
| models/base.py:39 | `Aim1RecordBase` mixin: record_id (unique, non-null), dataset_id, experiment_id, resource_id, prepared_sample_id, technical_replicate_no/total, method_id, analyst_id, raw_data_id, qc_pass (str), note |
| models/base.py:14 | `BaseEntity`: id, created_at, updated_at, etl_run_id (FK etl_run), lineage_group_id |
| models/aim1_records/proximate_record.py:4 | `proximate_record` (no extra columns) |
| models/aim1_records/ultimate_record.py:4 | `ultimate_record` (no extra columns) |
| models/aim1_records/compositional_record.py:4 | `compositional_record` (no extra columns) |
| models/aim1_records/icp_record.py:4 | `icp_record` (no extra columns) |
| models/aim1_records/xrf_record.py:7 | `xrf_record`: wavelength_nm, intensity, energy_slope, energy_offset (Decimal) |
| models/aim1_records/xrd_record.py:7 | `xrd_record`: scan_low_nm, scan_high_nm (int) |
| models/aim1_records/calorimetry_record.py:4 | `calorimetry_record` (no extra columns) |
| models/aim1_records/ftnir_record.py:4 | `ftnir_record` (no extra columns) |
| models/aim1_records/rgb_record.py:4 | `rgb_record` (no extra columns) |

Tables: proximate_record, ultimate_record, compositional_record, icp_record, xrf_record, xrd_record, calorimetry_record, ftnir_record, rgb_record (9 tables).

## How it works
```
prepared_sample --prepared_sample_id--> Aim1 row (record_id) --observation.record_id--> many observation rows (parameter, unit, value)
                                         |-- method_id, analyst_id, dataset_id, experiment_id, resource_id, raw_data_id
```
The ETL transform for proximate (pipeline/.../etl/transform/analysis/proximate_record.py) renames only FK/meta columns (record_id, repl_no to technical_replicate_no, qc_result to qc_pass, normalized ids) and drops duplicate record_ids. It emits no measurement columns; those go through the observation transform.

## Interfaces
- Inputs: ETL transform/load under pipeline etl/transform/analysis and etl/load/analysis (pipeline slice).
- Outputs: read by materialized views in datamodels views.py / data_portal_views (observation joined on record_id and record_type).
- Callers: `from ca_biositing.datamodels.models import ProximateRecord, ...`.

## Gotchas
- Aim1RecordBase is a mixin, not a table. A name like `aim1_record_base` appears in docs/pipeline/USDA/ANALYTICS_HANDOFF.md but no such table exists; the real tables are the nine above.
- qc_pass and note are plain strings (varchar), not booleans or enums.
- Only xrd and xrf add columns; a reader looking for moisture or carbon values must look in observation.
- `record_id` is globally unique per table, but the same string is reused as a join key against observation, which also filters on record_type.

## History
- Introduced in a9a86eb (2026-02-05, PR #84 Berkeley Upstream integration) as Python classes, and in 7a41e0e (PR #112, LinkML to SQLModel migration).
- Analytical ETL for ICP, XRF, calorimetry and XRD: 5ebbe4f (PR #123).


## Open questions
- rgb_record has no ETL or view references by class name at e41d00d (see facts/domain-models-usage-snapshot); confirm whether it is still loaded (inferred; confirm by searching pipeline flows for RgbRecord).

# Related Concepts
- [General analysis: observation (long-format measurements), dataset, analysis type, dimension type](datamodels-general-analysis.md): Measurements for each Aim 1 record are stored as observation rows keyed by record_id
- [Aim 2 processing and conversion tables (pretreatment, fermentation, gasification)](datamodels-aim2-records.md): Sibling record family for Aim 2 processing experiments with the same base key set
- [Datamodels base mixins (BaseEntity, LookupBase, Aim1/Aim2RecordBase)](datamodels-base.md): Aim1RecordBase and BaseEntity mixins are defined in models/base.py (slice 02)
- [Sample chain: field samples, collection and storage, then prepared samples and preparation methods](datamodels-sample-chain.md): prepared_sample_id links each analysis record to the physical sample it measured
- [System overview (start here)](system-overview.md): Hub: where the datamodels package sits in the ETL to DB to API flow
