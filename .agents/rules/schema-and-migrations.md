# Schema & Migrations

**Load when:** changing SQLModel models, writing or reviewing Alembic
migrations, editing materialized views in `data_portal_views/`, or validating
the schema with pgschema.

## Schema Management & Migrations (CRITICAL)

All schema changes are managed through **SQLModel classes** and **Alembic
migrations**. There is no code generation step.

### Making Schema Changes

1.  **Edit Models**: Modify SQLModel classes in
    `src/ca_biositing/datamodels/ca_biositing/datamodels/models/`. If adding a
    new model, also add its import to `models/__init__.py`.
2.  **Auto-Generate Migration**:
    ```bash
    pixi run migrate-autogenerate -m "Description of changes"
    ```
3.  **Review**: Check the generated script in `alembic/versions/`.
4.  **Apply Migration**:
    ```bash
    pixi run migrate
    ```

_Note: `migrate` runs `alembic upgrade head` locally against the Docker-hosted
PostgreSQL._

### Materialized Views

Nine materialized views are defined in
`src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/`. They
are managed through manual Alembic migrations using a compilation script.

**To update view definitions:**

1.  Edit the SQLAlchemy expression in `data_portal_views/`.
2.  Compile the changes into a new or existing migration:
    ```bash
    pixi run compile-mv-fixes -m "Fix view X"
    ```

Refresh after data loads:

```bash
pixi run refresh-views
```

### Validation with pgschema (Optional)

The `pgschema` tool can still be used for validation (diffing live DB against
reference SQL), but it does **not** modify the database:

- `pixi run schema-plan`: Diff public schema.
- `pixi run schema-analytics-plan`: Diff analytics schema.
- `pixi run schema-analytics-list`: List materialized views.
- `pixi run schema-dump`: Dump DB state to SQL files.

## Related Guides

- [`alembic/AGENTS.md`](../../alembic/AGENTS.md) — migration templates and the
  raw-SQL snapshot pattern for materialized views
- [`src/ca_biositing/datamodels/AGENTS.md`](../../src/ca_biositing/datamodels/AGENTS.md)
  — SQLModel model and view patterns
- [`docs/datamodels/SQL_FIRST_WORKFLOW.md`](../../docs/datamodels/SQL_FIRST_WORKFLOW.md)
  — the SQL-first path for rapid schema iteration
