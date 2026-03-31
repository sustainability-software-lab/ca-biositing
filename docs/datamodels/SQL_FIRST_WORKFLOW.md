# Schema Validation with pgschema

This document describes how `pgschema` is used for **validation only** in the CA
Biositing project. All operational schema management (creating tables, adding
columns, modifying constraints) is handled by **Alembic migrations** generated
from SQLModel class definitions.

## Overview

The project previously used `pgschema` as the primary tool for applying schema
changes during development. That workflow has been replaced by a standard
SQLModel + Alembic migration pipeline. The `pgschema` tool is retained solely
for **diffing** the live database against reference SQL files, which is useful
for verifying that migrations have been applied correctly.

## Prerequisites

### Install pgschema (optional)

`pgschema` is a Go-based binary. It is only needed if you want to run validation
diffs against the reference SQL file.

#### macOS (Homebrew)

```bash
brew tap pgplex/pgschema
brew install pgschema
```

#### Linux

Download the pre-built binary for your architecture from the
[pgschema releases page](https://github.com/pgplex/pgschema/releases), then:

```bash
chmod +x pgschema
sudo mv pgschema /usr/local/bin/
```

#### Windows

Download the `.exe` binary from the
[pgschema releases page](https://github.com/pgplex/pgschema/releases) and add it
to a directory on your `PATH`. Note: this workflow is primarily developed and
tested on macOS and Linux — Windows support is best-effort.

#### Cross-platform (pixi)

The `install-pgschema` task installs the binary directly into your pixi
environment on macOS and Linux:

```bash
pixi run install-pgschema
```

## The Current Workflow

### Primary: SQLModel + Alembic (All Schema Changes)

1.  **Edit Models**: Modify SQLModel classes in
    `src/ca_biositing/datamodels/ca_biositing/datamodels/models/`.
2.  **Auto-Generate Migration**:
    ```bash
    pixi run migrate-autogenerate -m "Description of changes"
    ```
3.  **Review**: Check the generated script in `alembic/versions/`.
4.  **Apply Migration**:
    ```bash
    pixi run migrate
    ```

### Optional: pgschema Validation (Diff Only)

These tasks compare the live database state against reference SQL files. They do
**not** modify the database.

#### Diff the public schema:

```bash
pixi run schema-plan
```

#### Diff the analytics schema (materialized views):

```bash
pixi run schema-analytics-plan
```

#### List materialized views:

```bash
pixi run schema-analytics-list
```

#### Dump current DB state to SQL files:

```bash
pixi run schema-dump
```

**Note:** `schema-dump` will overwrite the local SQL files in `sql_schemas/`
with the current state of the database.

### Materialized Views

Materialized views are defined in
`src/ca_biositing/datamodels/ca_biositing/datamodels/views.py` as SQLAlchemy
Core `select()` expressions. They are created via Alembic migrations and
refreshed after data loads:

```bash
pixi run refresh-views
```

## Removed Tasks

The following pixi tasks have been removed as part of the migration to
Alembic-managed schemas:

| Removed Task               | Replacement                        |
| -------------------------- | ---------------------------------- |
| `generate-models`          | Models are now hand-written        |
| `update-schema`            | `migrate-autogenerate` + `migrate` |
| `schema-apply`             | `migrate`                          |
| `schema-analytics-apply`   | `migrate`                          |
| `schema-analytics-refresh` | `refresh-views`                    |

## Reference SQL Files

The SQL files in `sql_schemas/` are retained as a reference for pgschema
validation. They are **not** the source of truth for the database schema. The
source of truth is the SQLModel classes in `models/` combined with the Alembic
migration chain in `alembic/versions/`.
