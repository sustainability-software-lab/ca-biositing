# ETL Pipeline Workflow

This guide explains the structure of the ETL (Extract, Transform, Load) pipeline
and how to use Prefect to execute it.

---

### Core Concepts

The ETL pipeline extracts data from Google Sheets, transforms it using pandas,
and loads it into the PostgreSQL database.

- **Structure:** The core logic is organized into three main packages within
  `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/`:
  - `extract`: Functions to pull raw data from sources (e.g., Google Sheets).
  - `transform`: Functions to clean, process, and structure the raw data.
  - `load`: Functions to insert the transformed data into the database using
    SQLAlchemy.

- **Hierarchical Pipelines:** Individual pipelines are nested within
  subdirectories reflecting the data they handle (e.g., `products`, `biomass`).

---

### Running the ETL Pipelines

The ETL system runs in a containerized Prefect environment.

**Step 1: Start Services**

```bash
pixi run start-services
```

**Step 2: Deploy Flows**

```bash
pixi run deploy
```

**Step 3: Run the Master Pipeline**

```bash
pixi run run-etl
```

**Step 4: Monitor** Access the Prefect UI at
[http://localhost:4200](http://localhost:4200).

---

### How to Add a New ETL Flow

**Step 1: Create the Task Files** Create the three Python files for your
extract, transform, and load logic in the appropriate subdirectories under
`src/ca_biositing/pipeline/ca_biositing/pipeline/etl/`. Decorate each function
with `@task`.

**Step 2: Create the Pipeline Flow** Create a new file in
`src/ca_biositing/pipeline/ca_biositing/pipeline/flows/` to define the flow.

```python
from prefect import flow
from ca_biositing.pipeline.etl.extract.samples.new_type import extract
from ca_biositing.pipeline.etl.transform.samples.new_type import transform
from ca_biositing.pipeline.etl.load.samples.new_type import load

@flow
def new_type_flow():
    raw_data = extract()
    transformed_data = transform(raw_data)
    load(transformed_data)
```

**Step 3: Register the New Flow** Add your flow to the `AVAILABLE_FLOWS`
dictionary in `resources/prefect/run_prefect_flow.py`.

**Step 4: Deploy and Run**

```bash
pixi run deploy
pixi run run-etl
```

---

### Using Templates

Template files are available in
`src/ca_biositing/pipeline/ca_biositing/pipeline/etl/templates/` to help you get
started with new tasks.

---

### Two-Stage QC Protection & Google Sheets Writeback

When analysts record Stage 1 Quality Control (QC) decisions in the **QC Audit
Workbench** (`/v1/qc/decisions`), the webservice immediately updates `qc_pass`
on the target PostgreSQL record table (`proximate_record`, `ultimate_record`,
`compositional_record`, `icp_record`, `xrf_record`, `xrd_record`,
`calorimetry_record`, `fermentation_record`, `pretreatment_record`, or
`gasification_record`) and inserts a ledger entry in `qc_review_decision` with
`synced_to_gsheet = False`.

Because routine Prefect ETL runs extract raw rows from Google Sheets and execute
PostgreSQL `INSERT ... ON CONFLICT (record_id) DO UPDATE` statements, unguarded
ETL runs would overwrite Stage 1 `qc_pass` overrides before an admin promotes
them to Google Sheets in Stage 2.

#### 1. ETL Upsert Protection (`qc_protected_records.py`)

All 10 Aim 1 and Aim 2 analytical record loaders in
`src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/` use
`ca_biositing.pipeline.utils.qc_protected_records`:

- **`get_unsynced_qc_protected_record_ids(session, record_table)`**: Queries
  `qc_review_decision` for all `record_id` values targeting `record_table` where
  `synced_to_gsheet IS FALSE` (including sibling IDs in `record_ids_json`).
  Performs a `sqlalchemy.inspect` table check first so ETL loads degrade
  gracefully if migration `0025` has not yet been applied.
- **`build_qc_aware_update_dict(insert_stmt, update_columns, protected_record_ids, model_table)`**:
  Wraps the `qc_pass` assignment in a SQL
  `CASE WHEN table.record_id IN (<protected_ids>) THEN table.qc_pass ELSE EXCLUDED.qc_pass END`
  expression during `on_conflict_do_update`, preserving the analyst's Stage 1
  `qc_pass` state in PostgreSQL while still updating all other columns from
  Google Sheets.

#### 2. Deterministic Seed CSV Round-Trip (`qc_ledger_seed.py`)

To preserve Stage 1 and Stage 2 QC decisions across local Docker database resets
(`pixi run reset-db`), `ca_biositing.pipeline.utils.qc_ledger_seed` provides
deterministic CSV export and import utilities:

```bash
# Export current qc_review_decision rows to data/seeds/qc_review_decisions_seed.csv
pixi run python -m ca_biositing.pipeline.utils.qc_ledger_seed export \
  --output data/seeds/qc_review_decisions_seed.csv

# Re-import decisions and re-apply qc_pass overrides after a DB reset
pixi run python -m ca_biositing.pipeline.utils.qc_ledger_seed import \
  --input data/seeds/qc_review_decisions_seed.csv
```

#### 3. Idempotent Stage 2 Google Sheets Writeback (`gsheet_qc_writeback.py`)

When a Portal Admin triggers Stage 2 writeback (`POST /v1/qc/sync-gsheet`),
`ca_biositing.pipeline.utils.gsheet_qc_writeback.sync_qc_decisions_to_gsheet`
performs two idempotent operations via `gspread`:

1. **Audit Ledger Worksheet (`qc_Waiting_Decisions`)**: Creates the worksheet
   with canonical headers if missing, keys existing rows by `decision_id`,
   updates existing entries in place, and batch-appends new decisions in a
   single API call.
2. **Source Worksheet `qc_pass` Update**: Locates each target `record_id` in the
   corresponding analytical worksheet tab and updates its `qc_pass` cell (plus
   optional `qc_audit_note` column if present) via `worksheet.batch_update`.
3. **Completion & View Refresh**: Marks synced rows `synced_to_gsheet = True`
   with `synced_at = UTC now()` in PostgreSQL (releasing the temporary ETL
   upsert lock now that the upstream Google Sheet matches PostgreSQL) and
   optionally refreshes materialized views.
