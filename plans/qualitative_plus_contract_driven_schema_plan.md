# Plan: Qualitative Plus Contract-Driven Schema + Materialized Views

## Objective

Implement the new DBML-backed schema changes and materialized views in a single
contract-driven pass so BEAM Portal can query stable view outputs immediately.

## End-of-Day Handoff (April 2, 2026)

### What Was Completed Today

- Completed Step 1A scope lock with naming and linkage corrections
  (`place.geoid`, `source_id`, dual-ID pricing linkage).
- Aligned schema table naming to `resource_production_record`.
- Implemented SQLModel classes for the new record/assumption tables and wired
  exports in model `__init__.py` files for Alembic discovery.
- Chose current FK strategy for this phase: typed linkage columns only,
  defer strict DB-level FK constraints until ETL validation.
- Locked default numeric precision guidance: `NUMERIC(18, 8)` for technical
  assumptions and ratio-like values.
- Expanded frontend scope to four contract views:
  `mv_biomass_search`, `mv_biomass_county_production`,
  `mv_biomass_pricing`, `mv_biomass_end_uses`.
- Applied the schema migration for the new resource/pricing/assumption tables.
- Updated `data_portal_views.py` for the active frontend contract, including
  observation-backed pricing/end-use pivots and the all-years USDA county
  production view.
- Applied the data-portal MV migration and verified the target views exist in
  `data_portal`.
- Ran focused datamodel tests and targeted pre-commit checks successfully.
- Confirmed migration sequencing decision: separate schema migration first,
  separate view migration later after frontend specs are provided.

### Current Position in Plan

- Step 1A: complete
- Step 2: complete (models implemented)
- Step 3: complete (precision/linkage review completed for current scope)
- Step 4: complete (schema migration generated, reviewed, and applied)
- Step 5: complete enough for current contract scope (spec intake resolved)
- Step 6: complete (view definitions updated)
- Step 7: complete (MV migration with UNIQUE indexes applied)
- Step 8: in progress (final wrap-up, reviewer summary, and PR prep)

### Tomorrow Kickoff Plan

1. Review final MV contracts against the frontend checklist.
2. If any new source data appears, rerun refresh/spot-check queries.
3. Share the PR summary and reviewer checklist with colleagues.
4. If needed, run `pixi run pre-commit-all` before merge.
5. Close out remaining comments from review.

### Draft MV Deliverable to Web App Team (Tomorrow)

Provide a draft contract doc containing, for each of the 4 views:

- View name
- Grain definition
- Expected columns (draft)
- Unique key/index strategy
- Status label: **Draft — pending ETL and data cleaning validation**

### Current Verification Notes

- `mv_biomass_search` and `mv_biomass_county_production` are kept as active
  contract views.
- `mv_usda_county_production` remains in the codebase and database as the
  historical/all-years county production view.
- The new pricing and end-use views are structurally valid; local data currently
  yields zero rows because their source record tables are empty in the test DB.

### Notes for Next Contributor

- Do not create materialized views until expected columns/specs are provided.
- Keep schema and view migrations separate.
- If ETL validation reveals key nullability or grain issues, update the draft
  MV contract before finalizing view DDL.

## Context Cross-Checked Against Repo Conventions

- **Base class usage**: New entity tables should inherit from `BaseEntity`
  (`id`, `created_at`, `updated_at`, `etl_run_id`, `lineage_group_id` already
  included).
- **Explicit table names**: Every SQLModel class should define `__tablename__`
  (snake_case).
- **Precision-first numerics**: Use `Decimal` for high-precision values.
- **Alembic autogenerate visibility**: New models must be imported in
  `src/ca_biositing/datamodels/ca_biositing/datamodels/models/__init__.py`.
- **Materialized views are manual**: View DDL is handled via manual Alembic
  migrations and definitions in `views.py`.
- **Local migration workflow**: Use Pixi local commands only:
  `pixi run migrate-autogenerate ...` and `pixi run migrate`.

## Frontend Contract Requirements (Locked)

1. Materialized views are built now (not deferred).
2. Each frontend-facing materialized view includes a **UNIQUE index**.
3. Views must support `REFRESH MATERIALIZED VIEW CONCURRENTLY`.
4. Column names and types are stable for frontend integration.

## Scope Lock: Target New Tables from DBML

Planned SQLModel tables:

1. `resource_price_record`
2. `resource_transport_record`
3. `resource_storage_record`
4. `resource_end_use_record`
5. `resource_production_record`
6. `technical_assumption`
7. `method_assumption`

## Scope Lock: Planned View Outputs (Frontend Contract)

Planned materialized views:

1. `mv_biomass_search`
2. `mv_biomass_county_production`
3. `mv_biomass_pricing`
4. `mv_biomass_end_uses`

> Note: Final SELECT definitions and unique-key strategy will be locked during
> implementation Step 1A below.

## Step 1A Scope Lock (Resolved)

### A) Naming + FK Target Corrections from DBML

- Use `place.geoid` (not `geography.geoid`) for geographic linkage.
- Use `source_id` (not `source_id_id`) for data source linkage.
- Use existing `data_source.id`, `dataset.id`, `method.id`, `resource.id`,
  `primary_ag_product.id`, `unit.id` targets.
- `parameter.calculated` already exists in current model; no new column needed
  unless we decide to alter nullability/default behavior.

### B) Table-by-Table Schema Lock

1. `resource_price_record`
   - Base: inherit `BaseEntity`
   - Required fields: `dataset_id`, `source_id`, `report_start_date`,
     `report_end_date`
   - Optional fields: `method_id`, `geoid`, `resource_id`,
     `primary_ag_product_id`, `freight_terms`, `transport_mode`, `note`
   - FK plan: linkage columns only in this phase; DB-level FK enforcement is
     deferred for ETL compatibility

2. `resource_transport_record`
   - Base: inherit `BaseEntity`
   - Required fields: `dataset_id`, `method_id`, `transport_description`
   - Optional fields: `geoid`, `resource_id`, `note`
   - FK plan: linkage columns only in this phase; DB-level FK enforcement is
     deferred for ETL compatibility

3. `resource_storage_record`
   - Base: inherit `BaseEntity`
   - Required fields: `dataset_id`, `method_id`, `storage_description`
   - Optional fields: `geoid`, `resource_id`, `note`
   - FK plan: linkage columns only in this phase; DB-level FK enforcement is
     deferred for ETL compatibility

4. `resource_end_use_record`
   - Base: inherit `BaseEntity`
   - Required fields: `dataset_id`, `method_id`
   - Optional fields: `geoid`, `resource_id`, `note`
   - FK plan: linkage columns only in this phase; DB-level FK enforcement is
     deferred for ETL compatibility

5. `resource_production_record`
   - Base: inherit `BaseEntity`
   - Required fields: `dataset_id`, `report_date`
   - Optional fields: `method_id`, `geoid`, `primary_ag_product_id`,
     `resource_id`, `scenario`, `note`
   - FK plan: linkage columns only in this phase; DB-level FK enforcement is
     deferred for ETL compatibility

6. `technical_assumption`
   - Base: inherit `BaseEntity`
   - Required fields: `assumption_name`, `assumption_value`
   - Optional fields: `unit_id`, `source_id`, `note`
   - FK plan: linkage columns only in this phase; DB-level FK enforcement is
     deferred for ETL compatibility
   - Numeric plan: `Decimal` with explicit DB numeric precision/scale
     (proposed default: `NUMERIC(18, 8)`)

## Numeric Precision Guidance

- **Default precision target**: use `NUMERIC(18, 8)` for technical
  assumptions and other ratio-like values.
- **Why**: enough room for fractional factors and percent-derived values while
  keeping storage and rounding behavior predictable.
- **If a field is truly monetary**: prefer a separate review and use a money
  scale such as `NUMERIC(18, 4)` only if the source data is currency-like.
- **If a field is a count or identifier**: keep it as `int`; do not use
  `Decimal`.
- **If a field is a percentage**: `NUMERIC(12, 6)` is often sufficient, but we
  should only apply that when the source field is explicitly a percent.

7. `method_assumption`
   - Pattern lock: use association-table style consistent with existing bridge
     models (`SQLModel, table=True` + explicit PK), not `BaseEntity`
   - Fields: `id` (auto PK), `method_id` (required linkage),
     `technical_assumption_id` (required linkage)
   - Optional enhancement: add unique constraint on
     (`method_id`, `technical_assumption_id`) to prevent duplicate mappings

### C) Materialized View Contract + Unique Index Keys

1. `mv_biomass_search`
   - Contract intent: one row per `resource.id`
   - Unique key: `id` (resource primary key)
   - Migration requirement: create UNIQUE index on `id` immediately after view
     creation

2. `mv_biomass_county_production`
   - Contract intent: one row per resource × county
   - Unique key: synthesized `id` or (`resource_id`, `county`)
   - Migration requirement: create UNIQUE index on chosen key immediately after
     view creation

3. `mv_biomass_pricing`
   - Contract intent: one row per commodity × county × report date
   - Unique key candidate: (`commodity`, `county`, `report_date`)
   - Migration requirement: create UNIQUE index on the chosen contract grain
     immediately after view creation

4. `mv_biomass_end_uses`
   - Contract intent: one row per resource × use case
   - Unique key candidate: (`resource_id`, `use_case`) or synthesized `id`
   - Migration requirement: create UNIQUE index on the chosen contract grain
     immediately after view creation

### D) Concurrent Refresh Operational Lock

- Frontend requirement is accepted: all MVs must support
  `REFRESH MATERIALIZED VIEW CONCURRENTLY`.
- Precondition is locked: each MV gets at least one valid UNIQUE index that
  covers full-row uniqueness at its contract grain.
- Implementation note: concurrent refresh is operational/runtime behavior;
  migrations will focus on create/drop + indexes, while runtime refresh logic
  is updated to issue concurrent refresh for these views.

## Foreign Key Strategy Adjustment (Risk-Controlled)

Per project convention and ETL compatibility requirements, new linkage columns
in this phase are modeled without DB-level FK constraints.

- Use typed linkage fields (`*_id`, `geoid`) in SQLModel classes.
- Defer strict FK DDL to a later hardening migration after ETL validation.

## Execution Steps (2.5-Hour Time Box)

### Step 1A — Scope Lock (15-20 min)

- Confirm each new column’s type/nullability.
- Confirm FK targets and strict-vs-deferred decisions per linkage.
- Confirm frontend view output columns and unique row key(s) for indexes.

### Step 2 — SQLModel Implementation (30-40 min)

- Add model classes in
  `src/ca_biositing/datamodels/ca_biositing/datamodels/models/...`.
- Inherit from `BaseEntity` or `LookupBase` as appropriate.
- Use explicit `__tablename__`, field descriptions, and `Decimal` where needed.
- Register imports in domain `__init__.py` and top-level `models/__init__.py`.

### Step 3 — Precision/Linkage Review (15-20 min)

- Fine-tooth review of numeric precision (`Decimal` scale), nullable behavior,
  and relational integrity.
- Verify column naming consistency for ETL and API consumption.

### Step 4 — Alembic for Schema Changes (20-30 min)

- Generate migration with local Pixi command.
- Manually review revision script for FK/index/type correctness.
- Apply migration locally and confirm expected objects.

> Scope note: this migration covers the database tables/bridge tables only.
> View creation is intentionally separated into a later migration once the
> frontend view specifications and expected columns are provided.

### Step 5 — Materialized View Spec Intake (blocked on frontend specs)

- Wait for the expected columns and grain definitions for each frontend view.
- Draft the `views.py` select logic only after specs are received and reviewed.
- Confirm unique key strategy for each view before writing DDL.

### Step 6 — Materialized View Definitions + DDL (25-35 min)

- Add view definitions in `views.py` for lifecycle-managed refresh.
- Ensure dependency ordering is valid.
- Add/confirm `alembic/env.py` materialized view filter names as needed.

### Step 7 — MV DDL + UNIQUE Indexes (20-30 min)

- Create manual Alembic migration for MV create/drop.
- Add required **UNIQUE indexes** for each frontend-facing MV.
- Use concurrent-safe refresh pattern (`REFRESH MATERIALIZED VIEW CONCURRENTLY`)
  in operational guidance and refresh utility updates (if required).

### Step 8 — Validation & Handoff (15-20 min)

- Run migrations and refresh views.
- Verify frontend contract columns and refresh behavior.
- Run `pixi run pre-commit-all`.
- Document outputs and any deferred constraints.

## Command Checklist (Exact)

### Environment

```bash
pixi install
```

### Migration generation + apply (local, not Docker)

```bash
pixi run migrate-autogenerate -m "Add qualitative-plus schema tables"
pixi run migrate
```

### Materialized view refresh + validation

```bash
pixi run refresh-views
pixi run schema-analytics-list
pixi run pre-commit-all
```

## File Touch Plan

Expected primary files:

- `src/ca_biositing/datamodels/ca_biositing/datamodels/models/...` (new models)
- `src/ca_biositing/datamodels/ca_biositing/datamodels/models/__init__.py`
- `src/ca_biositing/datamodels/ca_biositing/datamodels/views.py`
- `alembic/env.py` (if adding MV names)
- `alembic/versions/<new_schema_migration>.py`
- `alembic/versions/<new_mv_migration>.py`

## Definition of Done

- New SQLModel classes compile and are imported correctly.
- Schema migration applies cleanly.
- MVs exist with required UNIQUE index per view.
- Concurrent refresh is executable without blocking frontend reads.
- Frontend contract columns are stable and documented.
- Pre-commit checks pass.

## Residual Decisions (Narrow)

1. Final numeric precision/scale values for `Decimal` fields in
  `technical_assumption` and any price/ratio columns added during model coding.
2. Whether to add explicit DB unique constraints for natural keys in record
  tables (beyond PK + MV unique indexes).
