---
type: Architecture
title: "Methods, parameters, units and technical assumptions: the measurement vocabulary"
description: "method (procedure), parameter (what is measured), unit (how) and their link tables; technical_assumption holds numeric model inputs; FKs on the assumption tables are unconstrained."
tags: [datamodels, method, parameter, unit, vocabulary, assumptions]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:13Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/methods_parameters_units/*.py", "docs/database_conventions.md"]
sources: ["commit 7a41e0e", "commit a9a86eb", "commit d961724", "https://github.com/sustainability-software-lab/ca-biositing/pull/112", "https://github.com/sustainability-software-lab/ca-biositing/pull/258", "docs/database_conventions.md"]
governance: context
---

## Purpose
The controlled vocabulary used by observations and records. A method describes how a measurement was made, a parameter names what was measured, a unit gives the scale, and technical assumptions hold named numeric inputs used by calculations (for example conversion factors).

## Key files
| Path:line | Role |
|---|---|
| methods_parameters_units/method.py | `method` (BaseEntity): name, duration, method_abbrev_id, method_category_id, method_standard_id, description, detection_limits, source_id (data_source) |
| method.py | `method_abbrev`, `method_category`, `method_standard` (LookupBase) |
| methods_parameters_units/parameter.py:31 | `parameter` (BaseEntity): name, standard_unit_id (unit), calculated (bool: derived rather than measured), description |
| parameter.py:19 | `parameter_unit`: parameter_id, alternate_unit_id. Allows alternate units per parameter |
| parameter.py:7 | `parameter_category_parameter` (parameter_id, parameter_category_id) |
| parameter.py:43 | `parameter_category` (LookupBase) |
| methods_parameters_units/unit.py | `unit` (LookupBase) |
| methods_parameters_units/technical_assumption.py | `technical_assumption`: assumption_name, assumption_value (Numeric(18,8), NOT NULL), unit_id, source_id, note. FKs commented out |
| methods_parameters_units/method_assumption.py | `method_assumption`: method_id, technical_assumption_id (plain ints, FKs commented out). Link table |

Tables: method, method_abbrev, method_category, method_standard, parameter, parameter_unit, parameter_category, parameter_category_parameter, unit, technical_assumption, method_assumption (11 tables).

## How it works
observation.parameter_id to parameter, observation.unit_id to unit, parameter.standard_unit_id gives the canonical unit, and parameter_unit lists alternates. Records carry method_id to method. Method.source_id gives the citation.

## Interfaces
- Writers: pipeline load steps for method, parameter and unit lookups (load/analysis/method.py and related).
- Readers: observation-based views, and webservice parameter endpoints (the /parameters routes in docs/architecture.md).

## Gotchas
- Parameter names are lowercase words separated by spaces, not snake_case (docs/database_conventions.md). Example: resource use perc low.
- parameter.calculated=true means the value is derived, so do not treat it as a direct lab reading.
- method_assumption and technical_assumption have no DB-level FKs (commented ’per repo convention’). Dangling ids are possible.
- parameter_category_parameter, parameter_unit, method_abbrev, method_category, method_standard, parameter_category and method_assumption have no ETL or view references by class name at e41d00d (see the usage snapshot concept).
- technical_assumption.assumption_value is Numeric(18,8), so values beyond 8 decimal places are rounded.

## History
- 7a41e0e (PR #112) migrated these from LinkML to SQLModel.
- technical_assumption and method_assumption were introduced in d961724 (PR #258), the same commit that first added the commented-out FK comments (verified with git log -S for both classes).
- Dataset-era methods and preparation lookups (preparation_method) trace to a9a86eb (PR #84, verified for PreparationMethod).

## Open questions
- Whether technical_assumption is used by any calculation (no ETL reference found; inferred; confirm).

# Related Concepts
- [General analysis: observation (long-format measurements), dataset, analysis type, dimension type](datamodels-general-analysis.md): observation rows reference parameter and unit
- [Unconstrained foreign keys: many FK columns are commented out as ’per repo convention’](../decisions/datamodels-unconstrained-fk-convention.md): technical_assumption and method_assumption are examples of the unconstrained FK convention
- [Experiment and equipment: experiment header, decon vessels, and link tables to methods, samples and analyses](datamodels-experiment-equipment.md): experiment_method links experiments to methods
- [Domain terms as used in the datamodels: resource, field sample, prepared sample, analysis record, observation, parameter, unit, method, dataset](../facts/domain-core-terms.md): Defines method, parameter and unit as used here
- [System overview (start here)](system-overview.md): Hub for the ETL-to-database-to-API flow
