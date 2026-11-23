---
type: Decision
title: Measurements as a long observation table instead of one column per analysis
description: "Analysis record tables hold provenance only; every measured value is an observation row, which lets one schema cover many techniques but moves value meaning into lookups."
tags: [datamodels, observation, decision, eav, trade-off]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:16Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/general_analysis/observation.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/aim1_records/proximate_record.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/aim2_records/gasification_record.py"]
sources: ["commit a9a86eb", "commit a4e6fc9", "https://github.com/sustainability-software-lab/ca-biositing/pull/84", "https://github.com/sustainability-software-lab/ca-biositing/pull/217", "docs/datamodels/ALEMBIC_VIEW_WORKFLOW.md"]
governance: context
---

## Decision
Aim 1 record tables have almost no measurement columns (only xrd scan range and xrf energy/intensity fields). Measured values go into the shared `observation` table, keyed by record_id and record_type, with parameter_id and unit_id. Gasification run values were moved there as well (comment in gasification_record.py).

## Alternatives and trade-offs
- Wide per-technique tables (one column per parameter): precise types and easy SQL, but every new parameter needs a migration and the views need hand-written column lists.
- Long/EAV observation table (current): new parameters need only lookup rows, and one view can union many techniques. Costs are weaker typing (value is one Decimal), no FK on record_id, and joins that must filter by record_type.
- Mixed: keep provenance in typed record tables and measurements in observation (current).

## Evidence
- proximate_record, ultimate_record, compositional_record, icp_record and others have no measurement columns (verified in models/aim1_records/).
- The proximate transform emits only record_id, FKs and QC fields (verified in pipeline etl/transform/analysis/proximate_record.py).
- a4e6fc9 (PR #217) changed gasification to observations. a9a86eb (PR #84) introduced the table.

## Inferred rationale
Inferred from the code shape, not from a written decision record: the project mixes many analytical techniques with different parameter sets (proximate, ultimate, ICP, XRF, calorimetry, fermentation, gasification), which a long table absorbs without schema churn. Confirm with the datamodels maintainers.

## Consequences for readers
- To find a number, join observation to the record table on record_id and to parameter by parameter_id.
- Filter record_type, because the same record_id can appear under different types.

# Related Concepts
- [General analysis: observation (long-format measurements), dataset, analysis type, dimension type](../architecture/datamodels-general-analysis.md): The observation table this decision describes
- [Observation upserts depend on the (record_id, record_type, parameter_id, unit_id) unique key](../requirements/datamodels-observation-upsert-key.md): The unique key is part of the cost of this design
- [Aim 1 analytical record tables (proximate, ultimate, XRF, ICP, etc.)](../architecture/datamodels-aim1-records.md): Aim 1 tables hold provenance only
- [Domain terms as used in the datamodels: resource, field sample, prepared sample, analysis record, observation, parameter, unit, method, dataset](../facts/domain-core-terms.md): Defines observation, parameter and record_id
- [System overview (start here)](../architecture/system-overview.md): Hub for the datamodels picture
