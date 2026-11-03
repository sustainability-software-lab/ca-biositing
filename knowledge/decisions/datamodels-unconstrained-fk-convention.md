---
type: Decision
title: "Unconstrained foreign keys: many FK columns are commented out as ’per repo convention’"
description: About ten supply and assumption tables keep FK columns as plain ints with a ’commented out per repo convention’ note; the convention is not written down anywhere in the repo.
tags: [datamodels, foreign-keys, decision, etl-ordering, referential-integrity]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:15Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/methods_parameters_units/technical_assumption.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/methods_parameters_units/method_assumption.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/resource_price_record.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/resource_production_record.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/resource_storage_record.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/resource_transport_record.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/resource_end_use_record.py", "alembic/versions/0003_core_tables.py"]
sources: ["commit d961724", "alembic/versions/0003_core_tables.py", "docs/datamodels/CONTRIBUTING.md", "commit db578ad", "https://github.com/sustainability-software-lab/ca-biositing/pull/258", "https://github.com/sustainability-software-lab/ca-biositing/pull/340", "docs/database_conventions.md"]
governance: context
---

## Decision
Some model columns that look like references are plain integers, with the `foreign_key=` argument commented out and the comment `(commented out per repo convention)`. Affected tables and columns (verified in code):
- method_assumption: method_id, technical_assumption_id
- technical_assumption: unit_id, source_id
- resource_end_use_record: dataset_id, method_id, resource_id
- resource_price_record: method_id, resource_id, primary_ag_product_id, source_id
- resource_production_record: dataset_id, primary_ag_product_id, resource_id (method_id also plain)
- resource_storage_record: dataset_id, method_id, resource_id
- resource_transport_record: dataset_id, method_id, resource_id

Checked in alembic/versions/0003_core_tables.py for resource_production_record only: its create_table has only the etl_run_id FK, so the DB matches the commented-out ORM FKs there. The other listed tables were not individually checked.

## Alternatives and trade-offs
- Keep the FK: referential integrity, but the ETL must load parents first. Supply rows often arrive before their resource or method exists in sheets, and a failed FK would abort a whole batch.
- Drop the FK (current): loads are order-independent and faster. The cost is that dangling ids are possible and joins may silently lose rows.
- The rationale is not recorded in a commit body or doc. The only commit that first introduced the comments is d961724 (PR #258, ’View Creation and Iteration Alembic Workflow’), which does not explain it.

## Inferred rationale
Inferred, not verified: the comments are placed on exactly the ETL-loaded supply and assumption tables, which suggests load-order decoupling. Confirm with the author of d961724 (petercarbsmith) or the pipeline maintainers.

## Practical guidance
- Do not add a foreign_key to these columns without checking the loaders for order dependence.
- When joining these tables in views, use LEFT JOINs and check for orphans.
- Note that ’repo convention’ is only as strong as this comment. There is no CONTRIBUTING rule backing it up.

## Merged detail: Decision: many cross-domain FKs left as plain int columns with commented-out foreign_key

### Decision (as found in code)
Some tables store references as bare integers and leave the `foreign_key=` argument commented out, with the comment "commented out per repo convention". Examples: `models/resource_information/resource_end_use_record.py:12-13` (dataset, method), `resource_transport_record.py:13`, `resource_production_record.py:13` (dataset), `resource_storage_record.py:13`, and `resource_end_use_record.py:16` (resource). About 17 such comments exist under `models/`.

### Consequence
The database does not enforce these references. Orphan ids can be inserted.

### Trade-offs (inferred; not documented)
- Likely reason: ETL load order and missing parent rows would fail inserts (similar to the Place issue in PR #340). Confirm with the author of the convention.
- Cost: no referential integrity; joins rely on ETL correctness.

### Where the convention is written
Not found. `docs/database_conventions.md` covers lookup naming and lineage fields only. The comment first appears in `d961724` (PR #258) per `git log -S` (inferred; that commit’s title concerns the view workflow).

### Open questions
- Where is the convention documented, and does it still apply after the squash in `db578ad`?

# Related Concepts
- [Resource information: biomass resource, residue factors, availability, prices, end uses](../architecture/datamodels-resource-information.md): Most affected tables are supply records in this slice
- [Methods, parameters, units and technical assumptions: the measurement vocabulary](../architecture/datamodels-methods-parameters-units.md): method_assumption and technical_assumption are affected
- [Datamodels base mixins (BaseEntity, LookupBase, Aim1/Aim2RecordBase)](../architecture/datamodels-base.md): Contrast with BaseEntity FKs such as etl_run_id, which are constrained (slice 02)
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): The DB state is set by Alembic migrations, not by these comments
- [System overview (start here)](../architecture/system-overview.md): Hub for the datamodels picture
- [Places tables: place (GEOID natural key), location_address, multilinestring](../architecture/datamodels-places.md): the place.geoid FK that some of these tables omit
- [ER diagram: core, places, people, auth and infrastructure tables with verified FKs](../architecture/datamodels-er-diagram.md): missing edges in the diagram are these
