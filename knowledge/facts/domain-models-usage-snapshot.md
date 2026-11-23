---
type: Fact
title: "Snapshot: datamodels tables with no ETL or view references (name-based grep at e41d00d)"
description: "About 29 model classes in this slice are not referenced by pipeline, views or webservice by class name, so they may be unused, loaded under other names, or dormant."
tags: [domain, snapshot, unused-tables, datamodels, current-state]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:20Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/", "src/ca_biositing/datamodels/ca_biositing/datamodels/views.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/"]
sources: ["commit e41d00d", "docs/datamodels/CONTRIBUTING.md", "docs/datamodels/README.md", "docs/pipeline/USDA/ANALYTICS_HANDOFF.md"]
governance: context
stale_after: "2026-12-31"
---

## Method
At HEAD e41d00d, each table=True class in the slice was searched by class name (grep -w) in src/ca_biositing/pipeline/ca_biositing, src/ca_biositing/webservice/ca_biositing, and the datamodels views.py and data_portal_views. Tests were excluded. Zero hits means no code reference by class name. This is approximate: tables may be used by lowercase table name, through relationships, or by SQL.

## Zero hits (by class name)
- aim1: RgbRecord
- aim2: AutoclaveRecord
- experiment_equipment: ExperimentAnalysis, ExperimentEquipment, ExperimentMethod, ExperimentPreparedSample
- external_data: UsdaDomain, UsdaStatisticCategory, UsdaSurveyProgram, UsdaTermMap
- field_sampling: FieldSampleCondition, PhysicalCharacteristic, AgTreatment, CollectionMethod, HarvestMethod, ProcessingMethod, LocationSoilType
- general_analysis: none beyond DimensionType (1 hit) and AnalysisType (1 hit)
- methods_parameters_units: MethodAbbrev, MethodCategory (2), MethodStandard, MethodAssumption, TechnicalAssumption, ParameterCategory, ParameterCategoryParameter, ParameterUnit
- resource_information: ResourceCounterfactual
- sample_preparation: PreparationMethodAbbreviation
- data_sources_metadata: DataSourceType, SourceType, LocationResolution

Low hits (1 to 2, usually the views or one loader): GasificationTimeseries (1), DimensionType (1), AnalysisType (1), ResourceMorphology (1), PreparationMethod (1), UsdaMarketReport (1), UsdaMarketRecord (1), UseCase (3).

## Consequences
- Before touching these tables, search the lowercase table name too (for example `physical_characteristic`) and check the webservice.
- Do not drop a table on the strength of this list. Dropping requires a migration and a check of downstream users.

## Doc drift found in the same pass
- README and docs/datamodels/README.md say 91 models. There are 112 table classes across all subdirectories at HEAD (grep for table=True).
- docs/datamodels/CONTRIBUTING.md lists `misc/` (no such directory), puts Strain under resource_information (it is in aim2_records), puts PhysicalCharacteristic under general_analysis (it is in field_sampling), and puts Dataset under data_sources_metadata (it is in general_analysis).
- docs/pipeline/USDA/ANALYTICS_HANDOFF.md refers to an aim1_record_base table; it is a mixin, not a table.

# Related Concepts
- [Experiment and equipment: experiment header, decon vessels, and link tables to methods, samples and analyses](../architecture/datamodels-experiment-equipment.md): Most zero-hit experiment link tables are here
- [Methods, parameters, units and technical assumptions: the measurement vocabulary](../architecture/datamodels-methods-parameters-units.md): Most zero-hit method and assumption tables are here
- [Sample chain: field samples, collection and storage, then prepared samples and preparation methods](../architecture/datamodels-sample-chain.md): Zero-hit sample lookup tables are here
- [Current state snapshot (2026-10-16)](current-state.md): Current-state hub for this snapshot
- [System overview (start here)](../architecture/system-overview.md): Hub for the overall system
