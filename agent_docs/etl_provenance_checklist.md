# ETL Provenance Checklist — CA Biositing

> **Purpose:** Field-level reference for every provenance table an ETL may need
> to populate. Use this during **Phase 2 (Column Population Plan)** to ensure
> no required field is missed.
>
> **How to use:**
> 1. Identify which tables your ETL touches (see §1 for the standard chain).
> 2. For each table, copy the column list into your Column Population Plan.
> 3. Mark each column ✅ YES (will populate), ⬜ SKIP (intentionally null), or
>    ❓ UNKNOWN (needs human decision).
> 4. Every SKIP and UNKNOWN must have a reason or question.

---

## 1. Standard Provenance Chain

Most ETLs follow this dependency order. Load in this sequence:

```
DataSource
  └─ MethodCategory
       └─ Method  ──────────────────────────────────────────┐
  └─ Dataset  ──────────────────────────────────────────────┤
Place (geographic)                                          │
Resource (biomass resource)                                 │
Parameter + Unit (for observations)                         │
  └─ <Record Table>  (FK → Dataset, Method, Place, Resource)│
       └─ Observation  (FK → Record, Parameter, Unit) ──────┘
```

Experimental ETLs (Aim 2) add:

```
Experiment → ExperimentSetup → PretreatmentSetup → BioconversionSetup
  └─ <Aim2RecordBase subclass>  (FK → Experiment, Method, Strain, ...)
```

---

## 2. Universal Fields (every table that has them)

These fields apply to **every** table that defines them. Never omit them.

| Column | Rule | Code pattern |
|---|---|---|
| `id` | Auto-assigned by DB sequence. Never set manually. | — |
| `created_at` | Set to `datetime.now(UTC)` **only on first insert**. Never overwrite. | `if record.get('created_at') is None: record['created_at'] = now` |
| `updated_at` | Set to `datetime.now(UTC)` **on every upsert**. Always overwrite. | `record['updated_at'] = now` |
| `etl_run_id` | FK to the ETL run record. Pass from flow. | `record['etl_run_id'] = etl_run_id` |
| `lineage_group_id` | FK to the lineage group. Pass from flow. | `record['lineage_group_id'] = lineage_group_id` |

> ⚠️ If a table has `etl_run_id` or `lineage_group_id` columns and your ETL
> does not populate them, that is a **bug**, not a design choice.

---

## 3. Table-by-Table Field Reference

### 3.1 `data_source`

The root of the provenance chain. Every ETL must ensure exactly one
`DataSource` row exists for its source publication/dataset.

| Column | Required? | Typical value | Notes |
|---|---|---|---|
| `name` | ✅ REQUIRED | Short identifier string | Lowercase. Used for lookup deduplication. |
| `full_title` | ✅ REQUIRED | Full publication/report title | |
| `description` | ✅ REQUIRED | 1–2 sentence description of the source | |
| `uri` | ⬜ OPTIONAL | URL to source document | Populate if available; null otherwise. |
| `source_type` | ⬜ OPTIONAL | e.g. `"report"`, `"survey"`, `"interview"` | Populate if model supports it. |
| `created_at` | ✅ REQUIRED | See §2 | |
| `updated_at` | ✅ REQUIRED | See §2 | |
| `etl_run_id` | ✅ REQUIRED | See §2 | |
| `lineage_group_id` | ✅ REQUIRED | See §2 | |

**Idempotency key:** `name` (case-insensitive lookup via `func.lower()`).

---

### 3.2 `method_category`

Groups methods by type. Usually reuses an existing row; rarely creates a new one.

| Column | Required? | Typical value | Notes |
|---|---|---|---|
| `name` | ✅ REQUIRED | `"research method"` (most common) | Lowercase. Check existing rows first. |
| `description` | ✅ REQUIRED | Description of the category | |
| `uri` | ⬜ OPTIONAL | | |
| `created_at` | ✅ REQUIRED | See §2 | |
| `updated_at` | ✅ REQUIRED | See §2 | |

**Idempotency key:** `name` (case-insensitive).

> ⚠️ **Common mistake:** Creating a new `method_category` when `"research method"`
> already exists. Always check before inserting.

---

### 3.3 `method`

Describes how data was collected or derived. One per ETL (usually).

| Column | Required? | Typical value | Notes |
|---|---|---|---|
| `name` | ✅ REQUIRED | Descriptive method name | Lowercase. |
| `description` | ✅ REQUIRED | What the method entails | |
| `method_abbrev` | ⬜ OPTIONAL | Short abbreviation | |
| `method_category_id` | ✅ REQUIRED | FK → `method_category.id` | Must be resolved before insert. |
| `source_id` | ✅ REQUIRED | FK → `data_source.id` | Must be resolved before insert. |
| `duration` | ⬜ OPTIONAL | Numeric duration (hours, etc.) | Required for fermentation/bioconversion ETLs. |
| `uri` | ⬜ OPTIONAL | | |
| `created_at` | ✅ REQUIRED | See §2 | |
| `updated_at` | ✅ REQUIRED | See §2 | |
| `etl_run_id` | ✅ REQUIRED | See §2 | |
| `lineage_group_id` | ✅ REQUIRED | See §2 | |

**Idempotency key:** `name` (case-insensitive).

---

### 3.4 `dataset`

Groups records from the same source into a named collection.

| Column | Required? | Typical value | Notes |
|---|---|---|---|
| `name` | ✅ REQUIRED | Descriptive dataset name | Lowercase. |
| `record_type` | ✅ REQUIRED | e.g. `"resource_price_record"` | The SQLModel table name of the record type. |
| `source_id` | ✅ REQUIRED | FK → `data_source.id` | |
| `description` | ✅ REQUIRED | What this dataset contains | |
| `start_date` | ✅ REQUIRED | First date of data coverage | Use `date(YYYY, 1, 1)` if only year known. |
| `end_date` | ✅ REQUIRED | Last date of data coverage | Use `date(YYYY, 12, 31)` if only year known. |
| `created_at` | ✅ REQUIRED | See §2 | |
| `updated_at` | ✅ REQUIRED | See §2 | |
| `etl_run_id` | ✅ REQUIRED | See §2 | |
| `lineage_group_id` | ✅ REQUIRED | See §2 | |

**Idempotency key:** `name` (case-insensitive).

---

### 3.5 `place`

Geographic context for records. Often reuses existing rows (e.g. California counties).

| Column | Required? | Typical value | Notes |
|---|---|---|---|
| `geoid` | ✅ REQUIRED | e.g. `"06001"`, `"NSJV"` | Primary key / idempotency key. |
| `state_name` | ✅ REQUIRED | `"california"` | Lowercase. |
| `state_fips` | ✅ REQUIRED | `"06"` | |
| `county_name` | ⬜ OPTIONAL | e.g. `"alameda"` | Null for region-level records. |
| `county_fips` | ⬜ OPTIONAL | e.g. `"001"` | Null for region-level records. |
| `agg_level_desc` | ⬜ OPTIONAL | `"COUNTY"`, `"IN-STATE REGION"` | |

**Idempotency key:** `geoid`.

---

### 3.6 `resource`

The biomass resource being described. Check for existing rows before creating.

| Column | Required? | Typical value | Notes |
|---|---|---|---|
| `name` | ✅ REQUIRED | e.g. `"almond hulls"` | Lowercase. Always check existing before insert. |
| `created_at` | ✅ REQUIRED | See §2 | |
| `updated_at` | ✅ REQUIRED | See §2 | |

**Idempotency key:** `name` (case-insensitive).

> ⚠️ **Common mistake:** Silently creating a new Resource when one already
> exists under a slightly different name. Always log when a new Resource is
> created and flag it for human review.

---

### 3.7 `parameter`

Defines what is being measured in an observation.

| Column | Required? | Typical value | Notes |
|---|---|---|---|
| `name` | ✅ REQUIRED | e.g. `"price received"` | **Lowercase words with spaces** — NOT snake_case. |
| `description` | ✅ REQUIRED | Human-readable description | |
| `standard_unit_id` | ⬜ OPTIONAL | FK → `unit.id` | Populate if a canonical unit exists. |
| `calculated` | ⬜ OPTIONAL | `True` / `False` | Whether this is a derived value. |
| `created_at` | ✅ REQUIRED | See §2 | |
| `updated_at` | ✅ REQUIRED | See §2 | |
| `etl_run_id` | ✅ REQUIRED | See §2 | |
| `lineage_group_id` | ✅ REQUIRED | See §2 | |

**Idempotency key:** `name` (case-insensitive, normalised with `_normalize_parameter_name()`).

> ⚠️ **Common mistake:** Inserting parameter names in snake_case
> (e.g. `"price_received"`) instead of lowercase-with-spaces
> (`"price received"`). This breaks lookup matching.

---

### 3.8 `unit`

Unit of measurement for observations.

| Column | Required? | Typical value | Notes |
|---|---|---|---|
| `name` | ✅ REQUIRED | e.g. `"$/ton"`, `"percent"` | Lowercase. |
| `description` | ⬜ OPTIONAL | | |
| `abbreviation` | ⬜ OPTIONAL | | |

**Idempotency key:** `name` (case-insensitive).

---

### 3.9 Record tables (general pattern)

Applies to: `resource_price_record`, `resource_production_record`,
`county_ag_report_record`, `resource_storage_record`,
`resource_transport_record`, `resource_end_use_record`, and all Aim2 record
types.

| Column | Required? | Notes |
|---|---|---|
| `record_id` | ✅ REQUIRED | Unique hash/identifier for upsert. Never null. |
| `dataset_id` | ✅ REQUIRED | FK → `dataset.id`. Must be resolved before insert. |
| `method_id` | ✅ REQUIRED | FK → `method.id`. Must be resolved before insert. |
| `geoid` | ✅ if geographic | FK → `place.geoid`. |
| `resource_id` | ✅ if resource-linked | FK → `resource.id`. |
| `year` / `date` | ✅ if temporal | Populate from source data. |
| `value` / measurement columns | ✅ REQUIRED | The actual data being stored. |
| `created_at` | ✅ REQUIRED | See §2 |
| `updated_at` | ✅ REQUIRED | See §2 |
| `etl_run_id` | ✅ REQUIRED | See §2 |
| `lineage_group_id` | ✅ REQUIRED | See §2 |

**Idempotency key:** `record_id` (unique constraint).

> ⚠️ **Common mistake:** Leaving `record_id` null. Always validate
> `df['record_id'].isna().any()` before the load loop and skip/warn on nulls.

---

### 3.10 `observation`

Links a numeric measurement to a record, parameter, and unit.

| Column | Required? | Notes |
|---|---|---|
| `record_id` | ✅ REQUIRED | FK to the parent record table row's `id` (not `record_id`). |
| `record_type` | ✅ REQUIRED | String name of the parent table, e.g. `"resource_end_use_record"`. |
| `parameter_id` | ✅ REQUIRED | FK → `parameter.id`. |
| `unit_id` | ✅ REQUIRED | FK → `unit.id`. |
| `value` | ✅ REQUIRED | Numeric value. Use `Decimal` for `NUMERIC(18,8)` columns. |
| `created_at` | ✅ REQUIRED | See §2 |
| `updated_at` | ✅ REQUIRED | See §2 |
| `etl_run_id` | ✅ REQUIRED | See §2 |
| `lineage_group_id` | ✅ REQUIRED | See §2 |

**Idempotency key:** composite `(record_id, record_type, parameter_id, unit_id)`.

---

## 4. Aim 2 Experimental Data — Additional Tables

For bioconversion / fermentation / enzyme hydrolysis ETLs, the provenance chain
extends. Consult the existing Aim 2 ETLs (`bioconversion_method.py`,
`fermentation_record.py`) for the exact pattern. Key additional tables:

| Table | Key FKs | Notes |
|---|---|---|
| `experiment` | `source_id`, `dataset_id` | Top-level experiment container |
| `strain` | — | Microbe strain; use microbe-only name (not product code) |
| `pretreatment_setup` | `experiment_id`, `method_id` | |
| `bioconversion_setup` | `experiment_id`, `method_id`, `strain_id` | |
| `fermentation_record` | `method_id`, `strain_id`, `dataset_id` | `method_id` must be the bioconversion method, not pretreatment |

---

## 5. Quick Verification SQL

After running the ETL, use these queries to spot-check provenance completeness.
Run them manually in psql or a DB client.

```sql
-- Check for NULL etl_run_id or lineage_group_id in any table
SELECT 'data_source' AS tbl, COUNT(*) AS null_lineage
FROM data_source WHERE etl_run_id IS NULL OR lineage_group_id IS NULL
UNION ALL
SELECT 'dataset', COUNT(*) FROM dataset WHERE etl_run_id IS NULL OR lineage_group_id IS NULL
UNION ALL
SELECT 'method', COUNT(*) FROM method WHERE etl_run_id IS NULL OR lineage_group_id IS NULL;

-- Check for NULL created_at
SELECT 'data_source' AS tbl, COUNT(*) AS null_created
FROM data_source WHERE created_at IS NULL
UNION ALL
SELECT 'dataset', COUNT(*) FROM dataset WHERE created_at IS NULL;

-- Check record table for NULL record_id
SELECT COUNT(*) AS null_record_id FROM <your_record_table> WHERE record_id IS NULL;

-- Check observation FK completeness
SELECT COUNT(*) AS orphan_obs FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
WHERE p.id IS NULL;
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
