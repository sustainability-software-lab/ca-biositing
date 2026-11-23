---
type: Bug
title: Revision 0006 changes infrastructure_biodiesel_plants.address from VARCHAR to INTEGER
description: "Resolved in 0026: infrastructure_biodiesel_plants.address (VARCHAR cast to INTEGER in revision 0006) was dropped and replaced by an address_id foreign key."
tags: [alembic, migrations, schema, bug, open-question]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:32Z" }
status: stable
governance: context
code_refs: ["alembic/versions/0006_add_petroleum_pipelines.py", "alembic/versions/0026_add_food_processing_infrastructure_datasets.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/biodiesel_plants.py"]
stale_after: "2026-12-31"
sources: ["commit f66e296", "https://github.com/sustainability-software-lab/ca-biositing/pull/344", "commit db578ad", "commit f8c9353", "alembic/versions/0026_add_food_processing_infrastructure_datasets.py"]
---

## Symptom (historical)
`alembic/versions/0006_add_petroleum_pipelines.py:27-31` runs `op.alter_column("infrastructure_biodiesel_plants", "address", existing_type=sa.VARCHAR(), type_=sa.Integer(), postgresql_using="address::integer")`. A text street address fails that cast, and the downgrade (around line 76) reverses it. Commit `f66e296` (PR #344, 2026-05-13) added it, probably from autogenerate.

## Current state (HEAD a2c8de8)
- `alembic/versions/0026_add_food_processing_infrastructure_datasets.py:26-34` (f8c9353, PR #514): adds `address_id` (FK `location_address.id`), `etl_run_id` (FK `etl_run.id`), `lineage_group_id`, then `op.drop_column("infrastructure_biodiesel_plants", "address")`.
- `datamodels/.../models/infrastructure/biodiesel_plants.py:19` has `address_id: Optional[int]` with the FK, and no integer `address` field. The model and the chain now agree.
- Revision 0006 is still in the live chain (`down_revision "0005"`, `0005_mv_view_fixes.py` exists). A fresh database runs the cast on an empty table and then drops the column in 0026.

## Why it still matters
- A database that ran 0006 with text in `address` would fail the cast before 0026 runs. Whether any such database exists is not recorded here (inferred: staging was reset).
- The drop in 0026 discards the integer `address` values (see bugs/infra-migration-0026-drops-populated-columns).

## Status
Resolved for the model and for fresh databases. Remaining risk: any environment that holds data in the old column is not migrated safely; check before running 0026 there.

## Gotchas
- Do not edit revision 0006 (requirements/never-edit-applied-migrations). Any further change is a new revision.

## Open questions
- Was 0006 applied to a database with text in `address`? Confirm with the DB owner.

# Related Concepts
- [Alembic revision chain 0001-0024: what each revision changed and when](../facts/history-schema-timeline.md): Where this revision sits in the chain.
- [Do not edit a revision that has been applied to a shared database; add a new revision](../requirements/never-edit-applied-migrations.md): Why the fix must be a new revision, not an edit.
- [Migration 0026 drops source address and city columns from 7 infrastructure tables without copying data](infra-migration-0026-drops-populated-columns.md): the data-loss risk of the 0026 drop
- [Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern](../architecture/pipeline-infrastructure-etl-family.md): the family whose 0026 resolved this
