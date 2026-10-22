---
type: Fact
title: "Domain terms as used in the datamodels: resource, field sample, prepared sample, analysis record, observation, parameter, unit, method, dataset"
description: "Defines the data-model meaning of resource, field sample, prepared sample, analysis record, observation, parameter, unit, method, dataset, experiment and provider."
tags: [domain, glossary, resource, sample, observation, parameter, unit, method]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:19Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/resource.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/field_sampling/field_sample.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/sample_preparation/prepared_sample.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/general_analysis/observation.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/methods_parameters_units/parameter.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/methods_parameters_units/unit.py", "docs/database_conventions.md"]
sources: ["docs/database_conventions.md", "docs/data_dictionary.md", "docs/architecture.md", "commit 7a41e0e"]
governance: context
---

## Terms (as the code uses them)
- **Resource** (`resource`): a biomass feedstock type, for example a crop residue or orchard waste stream. Carries a primary_ag_product, a resource_class and resource_subclass, and a resource_code. It is the hub that samples, records and supply tables reference. Not the same as a ’resource’ in the generic webservice sense.
- **Primary ag product** (`primary_ag_product`): an agricultural commodity such as almond, used by LandIQ crops, USDA mappings and resources.
- **Field sample** (`field_sample`): one physical sample collected in the field, with location, collector, provider, collection method, harvest date and storage details.
- **Prepared sample** (`prepared_sample`): a processed derivative of a field sample (dried, ground, sieved), created with a preparation_method. Analysis records point to this.
- **Analysis record** (Aim 1 or Aim 2 record table): one analytical run or one processing run. Identified by `record_id`. Holds provenance (method, analyst, dataset, experiment, raw file) and QC (`qc_pass`), not measured numbers.
- **Observation** (`observation`): one measured value. Keys: record_id, record_type, parameter, unit. Also an optional dimension (for example time or temperature) through dimension_type and dimension_value.
- **Record_type**: which kind of record an observation belongs to. Either an analysis-type label (’xrf analysis’) or a table name (’usda_census_record’). Two conventions coexist.
- **Parameter** (`parameter`): the quantity being measured (for example a percent or a yield). `calculated=true` means derived.
- **Unit** (`unit`): how a value is scaled (lookup). parameter.standard_unit_id gives the canonical unit; parameter_unit lists alternates.
- **Method** (`method`): the procedure or protocol used (analysis, preparation or pretreatment). Has a category, standard, abbreviation and detection limits.
- **Technical assumption** (`technical_assumption`): a named numeric input (for example a conversion factor) used in calculations.
- **Dataset** (`dataset`): a grouping of records from one import or source. Points to a data_source.
- **Data source** (`data_source`): citation and provenance for a dataset or method.
- **Experiment** (`experiment`): a named lab run with analyst, dates, duration and location. Aim 1 and Aim 2 records point to it.
- **Decon vessel** (`decon_vessel`): the reactor or multi-well plate used in pretreatment or conversion.
- **Provider** (`provider`): the organization that supplied a sample. Defined in the people slice.
- **Place / geoid** (`place`): county-level geography keyed by FIPS geoid. Defined in the places slice.
- **Residue factor**: yield-per-acre factors (min, mid, max) used to convert production into residue volume.
- **Availability**: the months and year-round flag when a resource can be harvested in a place.

## Conventions
- Lookup names are lowercase. Parameter names use spaces, not snake_case (docs/database_conventions.md).
- `record_id` is the join key from analysis records to observation.
- Measured values are never on the record table (except the xrd and xrf instrument fields).

# Related Concepts
- [Research aims: Aim 1 feedstock characterization vs Aim 2 conversion experiments](domain-aims-aim1-aim2.md): The aims these terms serve
- [Measurements as a long observation table instead of one column per analysis](../decisions/datamodels-observation-long-table.md): Explains why observation is the measurement term
- [Glossary](glossary.md): Project-wide glossary hub
- [Sample chain: field samples, collection and storage, then prepared samples and preparation methods](../architecture/datamodels-sample-chain.md): Detailed model for field and prepared sample
- [System overview (start here)](../architecture/system-overview.md): Hub for the overall system
