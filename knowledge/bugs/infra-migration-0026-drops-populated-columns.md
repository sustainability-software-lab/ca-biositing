---
type: Bug
title: Migration 0026 drops source address and city columns from 7 infrastructure tables without copying data
description: "Revision 0026 drops address, city, state, zip and county columns on seven infrastructure tables and drops five tables on downgrade; data is lost if any DB held values there."
tags: [bug, alembic, migrations, infrastructure, data-loss, open-question]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:01Z" }
status: stable
code_refs: ["alembic/versions/0026_add_food_processing_infrastructure_datasets.py", "alembic/versions/0006_add_petroleum_pipelines.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/"]
sources: ["commit f8c9353", "https://github.com/sustainability-software-lab/ca-biositing/pull/514", "alembic/versions/0026_add_food_processing_infrastructure_datasets.py"]
governance: context
stale_after: "2026-11-21"
---

## Symptom
`alembic/versions/0026_add_food_processing_infrastructure_datasets.py` (`down_revision "0025"`, line 18) changes existing tables with `op.drop_column` on source address columns and does not copy their values into `location_address`.

## Evidence in code (HEAD a2c8de8)
- `infrastructure_biodiesel_plants.address`: drop at line 34 (this is the integer column set by revision 0006; see bugs/biodiesel-address-type-change).
- `infrastructure_biosolids_facilities`: drops `facility_address`, `facility_city`, `state`, `facility_zip`, `facility_county`, `mailing_street_1`, `mailing_city`, `mailing_state`, `mailing_zip` (lines 51-59).
- `infrastructure_cafo_manure_locations`: `address`, `town`, `state`, `zip` (lines 74-77).
- `infrastructure_combustion_plants`: `city`, `county` (lines 92-93).
- `infrastructure_district_energy_systems`: `city`, `state` (lines 108-109).
- `infrastructure_ethanol_biorefineries`: `address`, `city`, `state` (lines 124-126).
- `infrastructure_food_processing_facilities`: `address`, `county`, `city`, `state`, `zip` (lines 141-145).
- Downgrade drops five tables created by the same revision: `infrastructure_tomato_processors`, `food_manufacturers_carb`, `food_manufacturers_epa`, `railways`, `crude_oil_pipelines` (lines 374-386).

## Impact
- On a database that loaded these tables under the old code, the upgrade discards the old text address columns. The new code fills `address_id` only when the ETL runs again.
- The downgrade removes whatever rows exist in the five new tables (inferred from `drop_table`).
- Whether any shared database held rows in these columns at the time is not recorded here. The repo’s history notes that staging was reset in other revisions (inferred; confirm with the DB owner).

## Status
Open question. The migration is in the live chain and may already be applied to staging. Per requirements/never-edit-applied-migrations, a fix is a new revision, not an edit.

## Gotchas
- Revision 0026 was described in PR #482 as `0023_normalize_infrastructure_address_columns`; the name and number changed on merge.

## History
- Added in f8c9353 (PR #514, 2026-10-22).

## Open questions
- Did any environment have rows in the dropped columns before 0026 ran? Check staging before the next migration.

# Related Concepts
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): the migration chain this revision extends
- [Do not edit a revision that has been applied to a shared database; add a new revision](../requirements/never-edit-applied-migrations.md): why a fix must be a new revision
- [Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern](../architecture/pipeline-infrastructure-etl-family.md): the tables this revision changes
- [Revision 0006 changes infrastructure_biodiesel_plants.address from VARCHAR to INTEGER](biodiesel-address-type-change.md): the biodiesel column this revision drops
