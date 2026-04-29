# AGENTS.md - CA Biositing Data Models

This file provides guidance to AI assistants when working with the
`ca-biositing-datamodels` namespace package.

## Package Overview

This is the **ca-biositing-datamodels** package, a PEP 420 namespace package
containing SQLModel database models for the CA Biositing project. It is designed
to be shared across multiple components (ETL pipelines, API services, analysis
tools) of the parent ca-biositing project.

**Package Stats:**

- **Type:** Python namespace package (PEP 420)
- **Package Name:** `ca-biositing-datamodels`
- **Import Name:** `ca_biositing.datamodels`
- **Version:** 0.1.0
- **Python:** >= 3.12
- **Build System:** Hatchling
- **License:** BSD License
- **Domain:** Database models, SQLModel, PostgreSQL, Alembic

## Cross-Cutting Documentation

This package follows project-wide patterns documented in:

| Topic              | Document                                                           | When to Reference                          |
| ------------------ | ------------------------------------------------------------------ | ------------------------------------------ |
| Namespace Packages | [namespace_packages.md](../../../agent_docs/namespace_packages.md) | Import errors, package structure questions |
| Testing Patterns   | [testing_patterns.md](../../../agent_docs/testing_patterns.md)     | Writing tests, fixtures, pytest commands   |
| Code Quality       | [code_quality.md](../../../agent_docs/code_quality.md)             | Pre-commit, style, imports                 |
| Troubleshooting    | [troubleshooting.md](../../../agent_docs/troubleshooting.md)       | Common errors and solutions                |

```text
src/ca_biositing/datamodels/
├── ca_biositing/              # No __init__.py at this level (namespace)
│   └── datamodels/            # Package implementation
│       ├── __init__.py        # Package initialization
│       ├── database.py        # SQLModel engine and session management
│       ├── config.py          # Pydantic Settings configuration
│       ├── views.py           # Materialized view definitions (7 views)
│       ├── models/            # Hand-written SQLModel classes
│       │   ├── __init__.py    # Central re-export of all 91 models
│       │   ├── base.py        # Base classes (BaseEntity, LookupBase, etc.)
│       │   ├── aim1_records/  # Aim 1 analytical records
│       │   ├── aim2_records/  # Aim 2 processing records
│       │   ├── core/          # ETL lineage and run tracking
│       │   ├── external_data/ # LandIQ, USDA, Billion Ton records
│       │   └── ...            # (+ 10 more domain subdirectories)
│       └── sql_schemas/       # Reference SQL files (for pgschema validation)
├── tests/                     # Test suite
├── pyproject.toml            # Package metadata
└── README.md                 # Documentation
```

**CRITICAL:** The `ca_biositing/` directory does **NOT** have an `__init__.py`
file. This allows multiple packages to share the `ca_biositing` namespace.

### Model Architecture

Models are **hand-written SQLModel classes** organized into 15 domain
subdirectories under `models/`. All models are re-exported from
`models/__init__.py` for convenient imports.

**Import pattern:**

```python
# Preferred: import from the models package
from ca_biositing.datamodels.models import Resource, FieldSample, Place

# Also valid: import from specific domain submodule
from ca_biositing.datamodels.models.resource_information import Resource
```

**Database operations:**

```python
from sqlmodel import Session, select
from ca_biositing.datamodels.database import get_engine
from ca_biositing.datamodels.models import Resource

engine = get_engine()
with Session(engine) as session:
    resources = session.exec(select(Resource)).all()
```

## Schema Management Workflow (CRITICAL)

All schema changes are managed through **SQLModel classes** and **Alembic
migrations**. There is no code generation step.

### Making Schema Changes

1.  **Edit Models**: Modify or add SQLModel classes in the appropriate
    subdirectory under `models/`.
2.  **Re-Export**: If adding a new model, add the import to
    `models/__init__.py`.
3.  **Auto-Generate Migration**:
    ```bash
    pixi run migrate-autogenerate -m "Description of changes"
    ```
4.  **Review**: Check the generated script in `alembic/versions/`.
5.  **Apply Migration**:
    ```bash
    # Note: On macOS, you may need to set POSTGRES_HOST=localhost if running from host
    POSTGRES_HOST=localhost pixi run migrate
    ```

### Materialized Views

Views are defined in `views.py` as SQLAlchemy Core `select()` expressions. They
are created/modified through **manual** Alembic migrations.

**CRITICAL:** Alembic `autogenerate` does NOT detect changes to materialized
views. When updating a view:

1. Generate an empty migration:
   `pixi run migrate-autogenerate -m "Update view X"`
2. Manually edit the script to use `op.execute()` to `DROP` and `CREATE` the
   view.
3. Use `stmt.compile()` with `literal_binds=True` to generate the SQL from the
   SQLAlchemy expression.

Refresh after data loads:

```bash
pixi run refresh-views
```

### Validation with pgschema (Optional)

The `pgschema` tool can be used for diffing the live DB against reference SQL
files (validation only):

- `pixi run schema-plan`: Diff public schema.
- `pixi run schema-analytics-plan`: Diff analytics schema.

## Dependencies & Environment

### Core Dependencies

From `pyproject.toml`:

- **SQLModel**: Combines SQLAlchemy + Pydantic for typed ORM models
- **SQLAlchemy** (>=2.0.0): SQL database ORM
- **GeoAlchemy2**: PostGIS geometry column support
- **Alembic** (>=1.13.2, <2): Database migrations
- **psycopg2-binary** (>=2.9.6, <3): PostgreSQL adapter
- **Pydantic Settings** (>=2.0.0): Configuration management

### Development Environment

This package is typically developed as part of the main ca-biositing project
using Pixi.

**For testing this package:**

```bash
# From the main project root
pixi run pytest src/ca_biositing/datamodels -v
```

## Code Quality & Standards

### Pre-commit Checks

Always run pre-commit before committing:

```bash
# From main project root
pixi run pre-commit run --files src/ca_biositing/datamodels/**/*
```

### Import Conventions

```python
# Standard library
from __future__ import annotations
from datetime import datetime
from typing import Optional

# Third-party
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, UniqueConstraint

# Local (models package)
from ca_biositing.datamodels.models import Resource, FieldSample
```

## Common Pitfalls & Solutions

### Issue: Import errors with namespace package

**Solution:** Ensure `ca_biositing/` does **NOT** have `__init__.py`. Ensure you
are running inside the Pixi environment (`pixi run ...`) where all namespace
packages are installed. See root `AGENTS.md` for details.

### Issue: Alembic hangs or fails to connect in Docker

**Solution:** Ensure `POSTGRES_HOST=localhost` is set when running migrations
from the host on macOS.

## Linear Alembic Chain

This project requires a **linear migration chain**.

1. Always rebase your work onto the latest `upstream/main`.
2. Ensure your local migrations follow the head of `upstream/main` in a single
   sequence.
3. This matches the state of our staging and production environments.

**Solution:** Always use `pixi run migrate-autogenerate` and `pixi run migrate`.
These are configured to run locally. On macOS, ensure `POSTGRES_HOST=localhost`
is set in your environment or prefixed to the command if the connection fails
(since the host sees the DB container at `localhost:5432`, but internal configs
might point to `db`).

### Issue: New model not detected by Alembic autogenerate

**Solution:** Ensure the new model is imported in `models/__init__.py`. Alembic
reads `SQLModel.metadata`, which only includes models that have been imported.

## Related Documentation

- **Main Project AGENTS.md**: `AGENTS.md` (root)
- **Package README**: `src/ca_biositing/datamodels/README.md`
- **Notebook Setup**: `docs/notebook_setup.md`
