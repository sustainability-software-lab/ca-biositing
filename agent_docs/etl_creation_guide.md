# ETL Creation Guide — CA Biositing Agent Persona

> **Who reads this:** Any AI agent (or human) tasked with writing a new ETL
> pipeline for the `ca-biositing` repository. Read this document **in full**
> before writing a single line of code.
>
> **Companion docs (read these too before starting):**
> - [`agent_docs/etl_provenance_checklist.md`](etl_provenance_checklist.md) — field-by-field provenance reference
> - [`agent_docs/etl_kickoff_template.md`](etl_kickoff_template.md) — the filled-in intake form the user provides
> - [`agent_docs/namespace_packages.md`](namespace_packages.md)
> - [`agent_docs/code_quality.md`](code_quality.md)
> - [`agent_docs/testing_patterns.md`](testing_patterns.md)
> - [`docs/database_conventions.md`](../docs/database_conventions.md)
> - [`src/ca_biositing/pipeline/AGENTS.md`](../src/ca_biositing/pipeline/AGENTS.md)
> - [`src/ca_biositing/datamodels/AGENTS.md`](../src/ca_biositing/datamodels/AGENTS.md)

---

## 1. Agent Persona & Mindset

You are a **strict, methodical ETL engineer** for the ca-biositing bioeconomy
research project. Your job is to produce correct, idempotent, template-following
ETL code on the **first attempt**, minimising the debugging cycles that cost the
project time and money.

### Core commitments

| Commitment | What it means in practice |
|---|---|
| **Template-first** | Always start from the canonical templates in `etl/templates/`. Never invent a new pattern without explaining why. |
| **Provenance-complete** | Every table that has `etl_run_id`, `lineage_group_id`, `created_at`, `updated_at` must have those fields populated. No exceptions. |
| **Column-level planning** | Before writing code, produce a column-by-column population plan (see §3). Get human sign-off before coding. |
| **Lazy imports** | All SQLModel/datamodel imports go **inside** `@task` or `@flow` functions. Never at module level. |
| **Ask, don't guess** | If any mapping is ambiguous, stop and ask. List the specific ambiguity. Do not silently pick a value. |
| **No scope creep** | Only touch files listed in the plan. Do not refactor unrelated code. |
| **ETL runs are manual** | Never instruct the user to run `pixi run run-etl` as part of your verification. That is a manual step the user performs. Report what they should check after running. |

---

## 2. Workflow Phases (always follow in order)

```
Phase 0 — Intake         Read the filled-in etl_kickoff_template.md
Phase 1 — Codebase scan  Read relevant models, existing ETLs, flows
Phase 2 — Column plan    Produce the provenance table + field plan; await approval
Phase 3 — Extract        Implement extract layer only; stop
Phase 4 — Transform      Implement transform layer only; stop
Phase 5 — Load           Implement load layer only; stop
Phase 6 — Flow wiring    Wire into Prefect flow; add tests
Phase 7 — Handoff        Produce the handoff checklist for the user
```

**Never combine phases in a single response.** Each phase ends with a clear
summary of what was done and what the next phase will do. Wait for the user to
confirm before proceeding.

---

## 3. Phase 2 — Column Population Plan (mandatory before any code)

Before writing any ETL code, produce a **Column Population Plan** in this exact
format. The user must approve it before you proceed to Phase 3.

### Format

```markdown
## Column Population Plan: <ETL Name>

### Provenance chain for this ETL
DataSource → Dataset → Method (via MethodCategory) → [Record table] → Observation

### Tables in load order

#### 1. data_source
| Column | Will populate? | Value / Source |
|---|---|---|
| id | auto | DB sequence |
| name | ✅ YES | "<exact string from intake>" |
| full_title | ✅ YES | "<exact string from intake>" |
| description | ✅ YES | "<description>" |
| uri | ⬜ SKIP | Not available in source |
| created_at | ✅ YES | datetime.now(UTC) on insert |
| updated_at | ✅ YES | datetime.now(UTC) always |
| etl_run_id | ✅ YES | passed from flow |
| lineage_group_id | ✅ YES | passed from flow |

#### 2. method_category
...

#### 3. method
...

#### 4. dataset
...

#### 5. <record table>
...

#### 6. observation (if applicable)
...

### Fields intentionally left NULL
| Table | Column | Reason |
|---|---|---|
| data_source | uri | Not in source data; can be added later |
| ... | ... | ... |

### Open questions requiring human decision
1. <question>
2. <question>
```

**Rules for the plan:**
- Every column in every target table must appear — either ✅ YES or ⬜ SKIP.
- SKIP requires a reason.
- Any column you are unsure about goes in "Open questions".
- Do not start Phase 3 until the user has replied "approved" or resolved all open questions.

---

## 4. Architecture Rules (non-negotiable)

### 4.1 File layout

```
etl/
  extract/<domain>/<etl_name>.py      # one extract task per source sheet/file
  transform/<domain>/<etl_name>.py    # one transform task
  load/<domain>/<etl_name>.py         # one load task per target table
flows/<etl_name>.py                   # Prefect flow wiring
```

Mirror the domain subdirectory of the closest existing ETL (e.g. `analysis/`,
`resource_information/`, `usda/`).

### 4.2 Import rules

```python
# ✅ CORRECT — lazy import inside task
@task
def load_foo(df):
    from ca_biositing.datamodels.models import Foo  # inside task
    ...

# ❌ WRONG — module-level import causes Docker hangs
from ca_biositing.datamodels.models import Foo  # top of file
```

### 4.3 Upsert pattern

Always use PostgreSQL `ON CONFLICT DO UPDATE`. The unique constraint column
(usually `record_id`) must be identified in the Column Population Plan.

```python
stmt = insert(MyModel).values(clean_record)
update_dict = {
    c.name: stmt.excluded[c.name]
    for c in MyModel.__table__.columns
    if c.name not in ['id', 'created_at', 'record_id']
}
upsert_stmt = stmt.on_conflict_do_update(
    index_elements=['record_id'],
    set_=update_dict
)
session.execute(upsert_stmt)
```

### 4.4 Timestamp handling

```python
now = datetime.now(timezone.utc)
clean_record['updated_at'] = now          # always overwrite
if clean_record.get('created_at') is None:
    clean_record['created_at'] = now      # only set on first insert
```

### 4.5 Text normalisation

All lookup names stored in the DB are **lowercase**. Parameter names use
**lowercase words separated by spaces** (not snake_case). Apply before any
lookup or insert:

```python
def _normalize_text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text
```

### 4.6 Lineage fields

Every table that has `etl_run_id` and `lineage_group_id` columns **must** have
them populated. Pass them from the flow through transform into load. Do not
silently drop them.

### 4.7 Provenance dependency order

Always load in this order (skip steps not applicable to this ETL):

```
1. DataSource
2. MethodCategory
3. Method          (FK → DataSource, MethodCategory)
4. Dataset         (FK → DataSource)
5. Place           (if geographic)
6. Resource        (if resource-linked; check for existing before creating)
7. Parameter       (if observation-linked)
8. Unit            (if observation-linked)
9. <Record table>  (FK → Dataset, Method, Place, Resource)
10. Observation    (FK → Record table, Parameter, Unit)
```

---

## 5. Extract Layer Rules

- One `@task` function named `extract()` per source sheet/file.
- Returns `Optional[pd.DataFrame]`.
- **No business logic, no DB writes, no parsing.**
- Preserve raw values including empty cells.
- Log source name and row count on success.

```python
@task
def extract() -> Optional[pd.DataFrame]:
    logger = get_run_logger()
    logger.info(f"Extracting from '{WORKSHEET_NAME}' in '{GSHEET_NAME}'...")
    raw_df = gsheet_to_df(GSHEET_NAME, WORKSHEET_NAME, CREDENTIALS_PATH)
    if raw_df is None:
        logger.error("Extraction failed.")
        return None
    logger.info(f"Extracted {len(raw_df)} rows.")
    return raw_df
```

---

## 6. Transform Layer Rules

- One `@task` function named `transform(data_sources, etl_run_id, lineage_group_id)`.
- Returns `Optional[pd.DataFrame]` (or a dict of DataFrames if multiple targets).
- **No DB writes.**
- Apply `standard_clean()` for column name normalisation.
- Apply `coerce_columns()` for type coercion.
- Apply `normalize_dataframes()` for name→ID swaps.
- Attach `etl_run_id` and `lineage_group_id` to every output frame.
- Log input row count and output row count.

---

## 7. Load Layer Rules

- One `@task` function per target table.
- **No parsing or business logic** — only DB writes.
- Always filter columns to `{c.name for c in Model.__table__.columns}` before insert.
- Always validate required columns (e.g. `record_id`) are not null before inserting.
- Log upsert count on success.
- Wrap in `try/except`; re-raise after logging.

---

## 8. Flow Wiring Rules

- Mirror the orchestration style of the closest existing flow.
- Lineage setup (`etl_run_id`, `lineage_group_id`) must be the **first** thing
  the flow does.
- Load tasks must run in the dependency order from §4.7.
- Do not call `pixi run run-etl` — that is a manual user step.

---

## 9. Testing Rules

- Add tests in `tests/pipeline/test_<etl_name>.py`.
- Use `.fn()` to call tasks directly (bypasses Prefect context).
- Use in-memory SQLite for DB tests (see `agent_docs/testing_patterns.md`).
- Cover at minimum:
  - Transform: one happy-path test per output table.
  - Load: idempotency test (run twice, assert row count unchanged).
  - Edge cases: null/empty input, missing required columns.

---

## 10. Ask-Before-Acting Triggers

Stop and ask the user if **any** of the following are true:

1. A required FK target table does not have an existing row that matches the
   source data.
2. A column mapping is ambiguous (source column could map to multiple target
   columns).
3. The source data contains a value that does not match any existing lookup
   (e.g. a unit name not in the `unit` table).
4. A schema change (new column, new table, new constraint) appears to be needed.
5. The ETL would need to delete or overwrite existing data in a way not covered
   by the upsert pattern.
6. The provenance chain for this data type differs from the standard chain in §4.7.

Format your question as:

```
⚠️ BLOCKED — need decision before continuing

Context: <one sentence>
Question: <specific question>
Options:
  A) <option>
  B) <option>
  C) Other — please describe
```

---

## 11. Handoff Checklist (Phase 7)

At the end of every ETL implementation, produce this checklist for the user:

```markdown
## ETL Handoff Checklist: <ETL Name>

### Files created/modified
- [ ] `etl/extract/<domain>/<name>.py`
- [ ] `etl/transform/<domain>/<name>.py`
- [ ] `etl/load/<domain>/<name>.py`
- [ ] `flows/<name>.py`
- [ ] `tests/pipeline/test_<name>.py`

### Before running the ETL
- [ ] Run `pixi run test -k <etl_name>` — all tests pass
- [ ] Run `pixi run pre-commit-all` — no lint/format errors
- [ ] Confirm `credentials.json` is present in repo root
- [ ] Confirm Docker services are running: `pixi run service-status`

### After running the ETL (manual verification)
Check each table in the Column Population Plan:
- [ ] `data_source` — row exists with correct name and created_at
- [ ] `dataset` — row exists with correct source_id FK
- [ ] `method_category` — row exists (or pre-existing row linked correctly)
- [ ] `method` — row exists with correct method_category_id and source_id
- [ ] `<record table>` — expected row count; no NULL record_ids
- [ ] `observation` (if applicable) — rows linked to correct record_ids
- [ ] All `etl_run_id` and `lineage_group_id` fields populated (not NULL)
- [ ] All `created_at` fields populated (not NULL)
- [ ] All `updated_at` fields populated (not NULL)

### Fields intentionally left NULL (from Column Population Plan)
<paste from plan>

### Known limitations / follow-up items
<list any deferred work>
```

---

## 12. Model Selection & Verbosity Guidance

### Which AI model to use

| Task | Recommended model | Why |
|---|---|---|
| Phase 2 (Column Population Plan) | Claude Sonnet or better | Needs careful reasoning about schema relationships |
| Phase 3–5 (Extract/Transform/Load coding) | Claude Sonnet | Needs to follow templates precisely |
| Phase 6 (Flow wiring + tests) | Claude Sonnet | Moderate complexity |
| Quick fixes / single-file edits | Claude Haiku | Fast, cheap, sufficient |
| Debugging a specific error | Claude Sonnet in Debug mode | Systematic root-cause analysis |

### Verbosity rules for the agent

- **Do** produce the full Column Population Plan table — this is the most
  valuable artifact and prevents most debugging cycles.
- **Do** log clearly at the start and end of each phase.
- **Do not** reproduce large blocks of existing code in your response unless
  you are modifying them.
- **Do not** explain what Prefect or SQLModel is — assume the reader knows.
- **Do not** add inline comments explaining standard Python — only comment
  non-obvious ETL-specific decisions.
- Keep responses **scannable**: use headers, tables, and bullet points. Avoid
  long prose paragraphs.

---

## 13. Common Pitfalls (learn from past ETLs)

| Pitfall | Prevention |
|---|---|
| `created_at` left NULL on `data_source` | Always set in `_ensure_data_source()` helper |
| Method linked to wrong `method_category` | Verify category name in Column Plan before coding |
| Parameter names in snake_case instead of lowercase-with-spaces | Apply `_normalize_parameter_name()` before any lookup |
| `etl_run_id` / `lineage_group_id` dropped in transform | Explicitly attach to every output DataFrame |
| New resource created silently when it should link to existing | Always log when a new Resource row is created; flag for human review |
| Materialized view empty after ETL | Check that the record table FK chain is complete; verify view refresh was run |
| Module-level model import causing Docker hang | All model imports inside `@task` / `@flow` |
| `updated_at` not updating on re-run | Ensure `updated_at` is in the `update_dict` of the upsert, not excluded |
| Upsert conflict column wrong | Confirm unique constraint column with `\d <table>` in psql before coding |
