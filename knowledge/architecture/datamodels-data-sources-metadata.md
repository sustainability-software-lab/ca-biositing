---
type: Architecture
title: "Data source and file metadata: provenance for datasets, files and locations"
description: data_source describes where a dataset came from (Dublin Core style fields); file_object_metadata tracks individual files with checksums; location_resolution is a lookup.
tags: [datamodels, provenance, metadata, data-source]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:09Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/data_sources_metadata/*.py"]
sources: ["commit 7a41e0e", "commit a9a86eb", "https://github.com/sustainability-software-lab/ca-biositing/pull/84", "https://github.com/sustainability-software-lab/ca-biositing/pull/112", "docs/datamodels/CONTRIBUTING.md"]
governance: context
---

## Purpose
Provenance layer. A data source (a report, a sheet, a dataset publisher) is described once, and individual files (raw data, uploads, archives) are tracked with URI, bucket path, format, size and checksums. Other tables point here rather than repeating citation info.

## Key files
| Path:line | Role |
|---|---|
| data_sources_metadata/data_source.py:7 | `data_source`: name, description, data_source_type_id, full_title, creator, subject, publisher, contributor, date, type, biocirv (bool), format, language, relation, temporal_coverage, location_coverage_id, rights, license, uri, note |
| data_sources_metadata/data_source.py:36 | `data_source_type` (BaseEntity): source_type_id FK to source_type |
| data_sources_metadata/data_source.py:45 | `source_type` (LookupBase) |
| data_sources_metadata/file_object_metadata.py:7 | `file_object_metadata`: uri (unique), data_source_id, bucket_path, file_format, file_size, checksum_md5, checksum_sha256 |
| data_sources_metadata/location_resolution.py:5 | `location_resolution` (LookupBase): the spatial resolution of a source (for example county) |

Tables: data_source, data_source_type, source_type, file_object_metadata, location_resolution (5 tables).

## How it works
`data_source` is referenced by method.source_id, technical_assumption.source_id (unconstrained), county_ag_report_record.data_source_id, usda_market_report.source_id, residue_factor.data_source_id, and resource_price_record.source_id (unconstrained). `file_object_metadata` is referenced by Aim 1 and Aim 2 records as raw_data_id, so each analysis can point at its raw file.

## Interfaces
- Writers: ETL flows create data_source and file rows (pipeline slice).
- Readers: Aim records (raw_data_id) and the views that surface source citations.

## Gotchas
- data_source.date is a datetime while other date fields are date. Keep this in mind when comparing.
- data_source.biocirv is a flag that marks records owned by the BioCirV project.
- file_object_metadata.uri is unique; the same file cannot be registered twice even under different sources.
- Because the Aim1/Aim2 raw_data_id FKs to file_object_metadata, deleting a file row can fail on any analysis that references it.

## History
- data_source and data_source_type were already present in the LinkML-era history; the earliest commit that defines the DataSource class in this tree is 608530b (import of my_etl_postgres under etl_merge/), per git log -S. The SQLModel rewrite is 7a41e0e (PR #112).
- data_source_type and source_type are the lookup pair; their naming follows the LinkML origin.

## Open questions
- Whether data_source_type is used by any ETL (no pipeline reference found by class name; inferred; confirm).

# Related Concepts
- [External data: LandIQ crop map, USDA census and survey and market, Billion Ton, county ag reports](datamodels-external-data.md): External datasets cite a data_source for provenance
- [General analysis: observation (long-format measurements), dataset, analysis type, dimension type](datamodels-general-analysis.md): dataset.source_id FKs to data_source
- [Aim 1 analytical record tables (proximate, ultimate, XRF, ICP, etc.)](datamodels-aim1-records.md): Aim records keep raw_data_id to file_object_metadata
- [Core ETL run and lineage tables (etl_run, lineage_group, entity_lineage)](datamodels-core.md): etl_run and lineage track which load produced each row (slice 02)
- [System overview (start here)](system-overview.md): Hub for the ETL-to-database-to-API flow
