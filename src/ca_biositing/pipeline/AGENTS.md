# AGENTS.md - CA Biositing Pipeline

This file provides guidance to AI assistants when working with the
`ca-biositing-pipeline` namespace package.

## Package Overview

This is the **ca-biositing-pipeline** package, a PEP 420 namespace package
containing ETL (Extract, Transform, Load) pipelines and workflows for the CA
Biositing project. It depends on the shared `ca-biositing-datamodels` package
and uses Prefect for workflow orchestration.

**Package Stats:**

- **Type:** Python namespace package (PEP 420)
- **Package Name:** `ca-biositing-pipeline`
- **Import Name:** `ca_biositing.pipeline`
- **Version:** 0.1.0
- **Python:** >= 3.12
- **Build System:** Hatchling
- **License:** BSD License
- **Domain:** ETL pipelines, data workflows, Prefect orchestration, Google
  Sheets integration

## Cross-Cutting Documentation

This package follows project-wide patterns documented in:

| Topic              | Document                                                              | When to Reference                          |
| ------------------ | --------------------------------------------------------------------- | ------------------------------------------ |
| Namespace Packages | [namespace-packages.md](../../../.agents/rules/namespace-packages.md) | Import errors, package structure questions |
| Testing Patterns   | [testing-patterns.md](../../../.agents/rules/testing-patterns.md)     | Writing tests, Prefect task tests          |
| Code Quality       | [code-quality.md](../../../.agents/rules/code-quality.md)             | Pre-commit, style, imports                 |
| Docker Workflow    | [docker-workflow.md](../../../.agents/rules/docker-workflow.md)       | Running flows in the Docker services       |
| Troubleshooting    | [troubleshooting.md](../../../.agents/rules/troubleshooting.md)       | Common errors and solutions                |

```text
src/ca_biositing/pipeline/
├── ca_biositing/              # No __init__.py at this level (namespace)
│   └── pipeline/              # Package implementation
│       ├── __init__.py        # Package initialization
│       ├── etl/               # Extract, Transform, Load tasks
│       ├── flows/             # Prefect flow definitions
│       └── utils/             # Utility functions and helpers
├── tests/                     # Test suite
├── docs/                      # Workflow documentation
├── pyproject.toml            # Package metadata
└── README.md                 # Documentation
```

## Key Concepts

### ETL Architecture

The pipeline follows a modular ETL pattern:

- **Extract**: Prefect tasks that pull data from sources (Google Sheets, APIs,
  files).
- **Transform**: Prefect tasks that clean, validate, and reshape data using
  pandas.
- **Load**: Prefect tasks that insert data into PostgreSQL using SQLAlchemy.
- **Flows**: Prefect flows that orchestrate Extract → Transform → Load
  sequences.

## Dependencies

From `pyproject.toml`:

- **ca-biositing-datamodels** (>=0.1.0): Shared database models
- **pandas** (>=2.2.0, <3): Data manipulation
- **Prefect**: Workflow orchestration
- **gspread** & **gspread-dataframe**: Google Sheets integration
- **pyjanitor**: Data cleaning utilities
- **google-auth-oauthlib**: Google authentication
- **python-dotenv** (>=1.0.1, <2): Environment variables

### Development Environment

This package is typically developed as part of the main ca-biositing project
using Pixi.

**For testing this package:**

```bash
# From the main project root
pixi run pytest src/ca_biositing/pipeline -v
```

## Working with ETL Pipelines

### Prefect Task Pattern

```python
from prefect import task, get_run_logger
import pandas as pd

@task
def my_task(df: pd.DataFrame) -> pd.DataFrame:
    logger = get_run_logger()
    logger.info("Processing data...")
    # ... transformation logic ...
    return df
```

### Prefect Flow Pattern

```python
from prefect import flow
from ca_biositing.pipeline.etl.extract.my_extract import extract_data
from ca_biositing.pipeline.etl.transform.my_transform import transform_data
from ca_biositing.pipeline.etl.load.my_load import load_data

@flow(name="My ETL Flow")
def my_etl_flow():
    raw_df = extract_data()
    clean_df = transform_data(raw_df)
    load_data(clean_df)
```

## Common Tasks

### Adding a New ETL Pipeline

1. **Create tasks** in `etl/extract/`, `etl/transform/`, or `etl/load/`.
2. **Create flow** in `flows/` orchestrating the tasks.
3. **Register flow** in the master flow if applicable.
4. **Write tests** in `tests/`.

## Common Pitfalls & Solutions

### Issue: Import errors with namespace package

**Solution:** Ensure `ca_biositing/` does **NOT** have `__init__.py`. Ensure you
are running inside the Pixi environment (`pixi run ...`) where all namespace
packages are installed. See root `AGENTS.md` for details.

### Issue: Prefect flows or tasks hanging indefinitely

**Solution:** This is often caused by module-level import deadlocks or blocking
I/O.

1.  **Lazy Loading**: Move all heavy imports (SQLAlchemy models, Pydantic
    settings, ETL components) inside the `@flow` or `@task` function.
2.  **Bypass Orchestration**: Use `sub_flow.fn()` when calling flows from within
    a master flow to avoid scheduling deadlocks in local environments.
3.  **Docker Networking**: Ensure database engines use the `db` host inside
    containers.

### Issue: Prefect flows or tasks hanging indefinitely

**Solution:** This is often caused by module-level import deadlocks or blocking
I/O.

1.  **Lazy Loading**: Move all heavy imports (SQLAlchemy models, Pydantic
    settings, ETL components) inside the `@flow` or `@task` function.
2.  **Bypass Orchestration**: Use `sub_flow.fn()` when calling flows from within
    a master flow to avoid scheduling deadlocks in local environments.
3.  **Docker Networking**: Ensure database engines use the `db` host inside
    containers.

### Issue: Prefect logger context errors in tests

**Solution:** Use `.fn()` to call the underlying function of a task directly in
tests to bypass the Prefect runtime context.

### Issue: Google Sheets authentication failures

**Solution:** Ensure `credentials.json` exists in the project root and the
service account has access to the target sheet.

## Related Documentation

- **Main Project AGENTS.md**: `AGENTS.md` (root)
- **Datamodels AGENTS.md**: `src/ca_biositing/datamodels/AGENTS.md`
- **ETL Workflow**: `docs/pipeline/ETL_WORKFLOW.md`
- **GCP Setup**: `docs/pipeline/GCP_SETUP.md`
