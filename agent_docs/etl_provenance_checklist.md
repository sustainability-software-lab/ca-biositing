# ETL Provenance Checklist — CA Biositing

> **Purpose:** A dynamic, FK-driven reference for building the Column Population
> Plan (Phase 2 of [`etl_creation_guide.md`](etl_creation_guide.md)).
>
> **How to use:**
>
> 1. Start from the **record table** named in the kickoff form.
> 2. Read its SQLModel definition and list every FK column.
> 3. For each FK, look up the parent table in this document to find its required
>    fields.
> 4. Repeat up the chain until you reach root tables.
> 5. Copy the relevant column tables into your Column Population Plan, marking
>    each column ✅ YES, ⬜ SKIP, or ❓ UNKNOWN.
>
> **This checklist is a reference, not a fixed recipe.** Not every ETL uses
> every table. Derive the chain from the actual model FKs.

---

## 1. How to Derive the Provenance Chain

### Step 1 — Read the record table model

Find the SQLModel class in:

```
src/ca_biositing/datamodels/ca_biositing/datamodels/models/
```

List every column that ends in `_id` or is a FK. Example for a hypothetical
`resource_price_record`:

```
dataset_id      → dataset
method_id       → method
geoid           → place
resource_id     → resource
```

### Step 2 — Trace each FK one level up

For each parent table, list its own FK columns:

```
dataset.source_id          → data_source
method.method_category_id  → method_category
method.source_id           → data_source
```

### Step 3 — Continue until you reach root tables

Root tables have no FK dependencies on other provenance tables: `data_source`,
`method_category`, `place`, `resource`, `parameter`, `unit`.

### Step 4 — Build the load order

Load parents before children. A typical resolved order:

```
1. data_source          (root)
2. method_category      (root)
3. place                (root, if geographic)
4. resource             (root, if resource-linked)
5. parameter            (root, if observation-linked)
6. unit                 (root, if observation-linked)
7. method               (FK → data_source, method_category)
8. dataset              (FK → data_source)
9. <record_table>       (FK → dataset, method, place, resource)
10. observation         (FK → record_table, parameter, unit)
```

> Some ETLs skip steps. Some add tables (e.g. `experiment`, `strain` for Aim 2
> bioconversion data). Always derive from the actual model, not this example.

---

## 2. Universal Fields (every table that has them)

These apply to **every** table that defines them. Never omit them.

| Column             | Rule                                                                            | Code pattern                                                      |
| ------------------ | ------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `id`               | Auto-assigned by DB. Never set manually.                                        | —                                                                 |
| `created_at`       | Set to `datetime.now(UTC)` **only on first insert**. Never overwrite on update. | `if record.get('created_at') is None: record['created_at'] = now` |
| `updated_at`       | Set to `datetime.now(UTC)` **on every upsert**. Always overwrite.               | `record['updated_at'] = now`                                      |
| `etl_run_id`       | FK to the ETL run record. Pass from flow through transform into load.           | `record['etl_run_id'] = etl_run_id`                               |
| `lineage_group_id` | FK to the lineage group. Pass from flow through transform into load.            | `record['lineage_group_id'] = lineage_group_id`                   |

> ⚠️ If a table has `etl_run_id` or `lineage_group_id` and your ETL does not
> populate them, that is a **bug**, not a design choice.

---

## 3. Field Reference by Table

Use the section for each table that appears in your derived provenance chain.
Copy the column list into your Column Population Plan and mark each row.

---

### `data_source`

Root table. Every ETL must ensure exactly one row exists for its source.

**Idempotency key:** `name` (case-insensitive lookup via `func.lower()`).

| Column             | Required?   | Notes                                                       |
| ------------------ | ----------- | ----------------------------------------------------------- |
| `name`             | ✅ REQUIRED | Short identifier. Lowercase. Used for deduplication.        |
| `full_title`       | ✅ REQUIRED | Full publication/report title.                              |
| `description`      | ✅ REQUIRED | 1–2 sentence description of the source.                     |
| `uri`              | ⬜ OPTIONAL | URL/DOI. Populate if available; null otherwise.             |
| `source_type`      | ⬜ OPTIONAL | e.g. `"report"`, `"survey"`. Populate if model supports it. |
| `created_at`       | ✅ REQUIRED | See §2.                                                     |
| `updated_at`       | ✅ REQUIRED | See §2.                                                     |
| `etl_run_id`       | ✅ REQUIRED | See §2.                                                     |
| `lineage_group_id` | ✅ REQUIRED | See §2.                                                     |

> ⚠️ **Common mistake:** `created_at` left NULL. Always set it in the
> `_ensure_data_source()` helper on first insert.

---

### `method_category`

Groups methods by type. Usually reuses an existing row.

**Idempotency key:** `name` (case-insensitive).

| Column        | Required?   | Notes                                                                               |
| ------------- | ----------- | ----------------------------------------------------------------------------------- |
| `name`        | ✅ REQUIRED | Lowercase. Check existing rows before inserting. Common value: `"research method"`. |
| `description` | ✅ REQUIRED | Description of the category.                                                        |
| `uri`         | ⬜ OPTIONAL |                                                                                     |
| `created_at`  | ✅ REQUIRED | See §2.                                                                             |
| `updated_at`  | ✅ REQUIRED | See §2.                                                                             |

> ⚠️ **Common mistake:** Creating a new `method_category` when an existing one
> (e.g. `"research method"`) already covers this ETL. Always check first.

---

### `method`

Describes how data was collected or derived.

**Idempotency key:** `name` (case-insensitive).

| Column               | Required?   | Notes                                                           |
| -------------------- | ----------- | --------------------------------------------------------------- |
| `name`               | ✅ REQUIRED | Lowercase descriptive name.                                     |
| `description`        | ✅ REQUIRED | What the method entails.                                        |
| `method_abbrev`      | ⬜ OPTIONAL | Short abbreviation.                                             |
| `method_category_id` | ✅ REQUIRED | FK → `method_category.id`. Resolve before insert.               |
| `source_id`          | ✅ REQUIRED | FK → `data_source.id`. Resolve before insert.                   |
| `duration`           | ⬜ OPTIONAL | Numeric duration. Required for fermentation/bioconversion ETLs. |
| `uri`                | ⬜ OPTIONAL |                                                                 |
| `created_at`         | ✅ REQUIRED | See §2.                                                         |
| `updated_at`         | ✅ REQUIRED | See §2.                                                         |
| `etl_run_id`         | ✅ REQUIRED | See §2.                                                         |
| `lineage_group_id`   | ✅ REQUIRED | See §2.                                                         |

---

### `dataset`

Groups records from the same source into a named collection.

**Idempotency key:** `name` (case-insensitive).

| Column             | Required?   | Notes                                                                        |
| ------------------ | ----------- | ---------------------------------------------------------------------------- |
| `name`             | ✅ REQUIRED | Lowercase descriptive name.                                                  |
| `record_type`      | ✅ REQUIRED | The SQLModel table name of the record type (e.g. `"resource_price_record"`). |
| `source_id`        | ✅ REQUIRED | FK → `data_source.id`. Resolve before insert.                                |
| `description`      | ✅ REQUIRED | What this dataset contains.                                                  |
| `start_date`       | ✅ REQUIRED | First date of data coverage. Use `date(YYYY, 1, 1)` if only year known.      |
| `end_date`         | ✅ REQUIRED | Last date of data coverage. Use `date(YYYY, 12, 31)` if only year known.     |
| `created_at`       | ✅ REQUIRED | See §2.                                                                      |
| `updated_at`       | ✅ REQUIRED | See §2.                                                                      |
| `etl_run_id`       | ✅ REQUIRED | See §2.                                                                      |
| `lineage_group_id` | ✅ REQUIRED | See §2.                                                                      |

---

### `place`

Geographic context. Often reuses existing rows (e.g. California counties).

**Idempotency key:** `geoid`.

| Column           | Required?   | Notes                                                         |
| ---------------- | ----------- | ------------------------------------------------------------- |
| `geoid`          | ✅ REQUIRED | Primary key. e.g. `"06001"` (county FIPS), `"NSJV"` (region). |
| `state_name`     | ✅ REQUIRED | Lowercase. e.g. `"california"`.                               |
| `state_fips`     | ✅ REQUIRED | e.g. `"06"`.                                                  |
| `county_name`    | ⬜ OPTIONAL | Lowercase. Null for region-level records.                     |
| `county_fips`    | ⬜ OPTIONAL | Null for region-level records.                                |
| `agg_level_desc` | ⬜ OPTIONAL | e.g. `"COUNTY"`, `"IN-STATE REGION"`.                         |

---

### `resource`

The biomass resource being described. Always check for existing rows first.

**Idempotency key:** `name` (case-insensitive).

| Column       | Required?   | Notes                                                                  |
| ------------ | ----------- | ---------------------------------------------------------------------- |
| `name`       | ✅ REQUIRED | Lowercase. e.g. `"almond hulls"`. Always check existing before insert. |
| `created_at` | ✅ REQUIRED | See §2.                                                                |
| `updated_at` | ✅ REQUIRED | See §2.                                                                |

> ⚠️ **Common mistake:** Silently creating a new Resource when one already
> exists under a slightly different name. Always log when a new Resource row is
> created and flag it for human review.

---

### `parameter`

Defines what is being measured in an observation.

**Idempotency key:** `name` (case-insensitive, normalised with
`_normalize_parameter_name()`).

| Column             | Required?   | Notes                                                                                             |
| ------------------ | ----------- | ------------------------------------------------------------------------------------------------- |
| `name`             | ✅ REQUIRED | **Lowercase words with spaces** — NOT snake_case. e.g. `"price received"` not `"price_received"`. |
| `description`      | ✅ REQUIRED | Human-readable description.                                                                       |
| `standard_unit_id` | ⬜ OPTIONAL | FK → `unit.id`. Populate if a canonical unit exists.                                              |
| `calculated`       | ⬜ OPTIONAL | `True` / `False`. Whether this is a derived value.                                                |
| `created_at`       | ✅ REQUIRED | See §2.                                                                                           |
| `updated_at`       | ✅ REQUIRED | See §2.                                                                                           |
| `etl_run_id`       | ✅ REQUIRED | See §2.                                                                                           |
| `lineage_group_id` | ✅ REQUIRED | See §2.                                                                                           |

> ⚠️ **Common mistake:** Inserting parameter names in snake_case. This breaks
> lookup matching across ETLs. Always apply `_normalize_parameter_name()`.

---

### `unit`

Unit of measurement for observations.

**Idempotency key:** `name` (case-insensitive).

| Column         | Required?   | Notes                                   |
| -------------- | ----------- | --------------------------------------- |
| `name`         | ✅ REQUIRED | Lowercase. e.g. `"$/ton"`, `"percent"`. |
| `description`  | ⬜ OPTIONAL |                                         |
| `abbreviation` | ⬜ OPTIONAL |                                         |

---

### Record tables (general pattern)

Applies to any table that is the primary target of the ETL (e.g.
`resource_price_record`, `county_ag_report_record`, `resource_end_use_record`,
`fermentation_record`, etc.).

**Read the actual SQLModel class** to get the full column list for your specific
record table. The columns below are the universal ones present on most record
tables — supplement with the model-specific columns.

**Idempotency key:** `record_id` (unique constraint — confirm with `\d <table>`
in psql if unsure).

| Column              | Required?       | Notes                                                            |
| ------------------- | --------------- | ---------------------------------------------------------------- |
| `record_id`         | ✅ REQUIRED     | Unique hash/identifier. Never null. Validate before insert loop. |
| `dataset_id`        | ✅ if FK exists | FK → `dataset.id`. Resolve before insert.                        |
| `method_id`         | ✅ if FK exists | FK → `method.id`. Resolve before insert.                         |
| `geoid`             | ✅ if FK exists | FK → `place.geoid`.                                              |
| `resource_id`       | ✅ if FK exists | FK → `resource.id`.                                              |
| `year` / `date`     | ✅ if temporal  | Populate from source data.                                       |
| Measurement columns | ✅ REQUIRED     | The actual data values. List each one explicitly in the plan.    |
| `created_at`        | ✅ REQUIRED     | See §2.                                                          |
| `updated_at`        | ✅ REQUIRED     | See §2.                                                          |
| `etl_run_id`        | ✅ REQUIRED     | See §2.                                                          |
| `lineage_group_id`  | ✅ REQUIRED     | See §2.                                                          |

> ⚠️ **Common mistake:** Leaving `record_id` null. Always validate
> `df['record_id'].isna().any()` before the load loop and skip/warn on nulls.

---

### `observation`

Links a numeric measurement to a record, parameter, and unit. Only present when
the ETL loads quantitative data.

**Idempotency key:** composite
`(record_id, record_type, parameter_id, unit_id)`.

| Column             | Required?   | Notes                                                                    |
| ------------------ | ----------- | ------------------------------------------------------------------------ |
| `record_id`        | ✅ REQUIRED | FK to the parent record table row's `id` (the integer PK, not the hash). |
| `record_type`      | ✅ REQUIRED | String name of the parent table, e.g. `"resource_end_use_record"`.       |
| `parameter_id`     | ✅ REQUIRED | FK → `parameter.id`.                                                     |
| `unit_id`          | ✅ REQUIRED | FK → `unit.id`.                                                          |
| `value`            | ✅ REQUIRED | Numeric value. Use `Decimal` for `NUMERIC(18,8)` columns.                |
| `created_at`       | ✅ REQUIRED | See §2.                                                                  |
| `updated_at`       | ✅ REQUIRED | See §2.                                                                  |
| `etl_run_id`       | ✅ REQUIRED | See §2.                                                                  |
| `lineage_group_id` | ✅ REQUIRED | See §2.                                                                  |

---

## 4. Aim 2 Experimental Data — Additional Tables

For bioconversion / fermentation / enzyme hydrolysis ETLs, the provenance chain
extends beyond the standard tables. Derive the exact chain from the Aim 2 record
model FKs. Key additional tables to be aware of:

| Table                 | Key FKs                                   | Notes                                                                                           |
| --------------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `experiment`          | `source_id`, `dataset_id`                 | Top-level experiment container.                                                                 |
| `strain`              | —                                         | Microbe strain. Use microbe-only name — strip product suffix (e.g. `"1Sac"` not `"1Sac-EtOH"`). |
| `pretreatment_setup`  | `experiment_id`, `method_id`              |                                                                                                 |
| `bioconversion_setup` | `experiment_id`, `method_id`, `strain_id` |                                                                                                 |
| `fermentation_record` | `method_id`, `strain_id`, `dataset_id`    | `method_id` must be the **bioconversion** method, not pretreatment.                             |

Consult the existing Aim 2 ETLs (`bioconversion_method.py`,
`fermentation_record.py`) for the exact pattern.

---

## 5. Quick Verification SQL

Run these manually after the ETL to spot-check provenance completeness.
Substitute `<your_table>` with the actual table names from your Column
Population Plan.

```sql
-- Check for NULL etl_run_id or lineage_group_id
-- Run once per table in your provenance chain
SELECT '<table_name>' AS tbl, COUNT(*) AS null_lineage
FROM <table_name>
WHERE etl_run_id IS NULL OR lineage_group_id IS NULL;

-- Check for NULL created_at
SELECT '<table_name>' AS tbl, COUNT(*) AS null_created
FROM <table_name>
WHERE created_at IS NULL;

-- Check record table for NULL record_id
SELECT COUNT(*) AS null_record_id
FROM <your_record_table>
WHERE record_id IS NULL;

-- Check observation FK completeness
SELECT COUNT(*) AS orphan_obs
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
WHERE p.id IS NULL;

-- Check dataset → data_source FK
SELECT COUNT(*) AS orphan_datasets
FROM dataset d
LEFT JOIN data_source ds ON d.source_id = ds.id
WHERE ds.id IS NULL;
```

---

## 6. Materialized View Refresh

If this ETL feeds a materialized view, the view must be refreshed after the ETL
run. This is a **manual step** — remind the user:

```bash
pixi run refresh-views
```

Then verify the view is not empty:

```sql
SELECT COUNT(*) FROM data_portal.<mv_name>;
```

If the view is empty after refresh, the most common causes are:

1. A required FK in the record table is NULL (e.g. `method_id`, `dataset_id`).
2. The view JOIN condition does not match the data loaded (check column names).
3. The view definition in the DB is stale — check if a migration is needed.
