# Troubleshooting Guide

**Load when:** a documented command fails or behaves unexpectedly: environment,
namespace import, Docker, database, Prefect, or Google credential problems.

This document consolidates common issues and solutions from all ca-biositing
packages and components.

## Common Pitfalls

- **Import Errors**: Ensure you are running inside the Pixi environment
  (`pixi run ...`) or using the Pixi kernel in Jupyter.
- **macOS Geospatial Library Conflicts**: On macOS (especially Apple Silicon),
  you may encounter `PROJ` database version mismatch errors when using
  `geopandas` or `pyogrio`.
  - **Fix**: Ensure `PROJ_LIB` environment variable is set to the Pixi
    environment's data directory _before_ importing geospatial libraries.
  - **Example**:
    ```python
    import os, pyproj
    os.environ['PROJ_LIB'] = pyproj.datadir.get_data_dir()
    import geopandas as gpd
    ```
- **Docker Hangs & Deadlocks**:
  - **CRITICAL**: Never import heavy SQLAlchemy models or Pydantic settings at
    the module level. Always import them inside the `@task` or `@flow` function.
  - **CRITICAL**: Avoid any network I/O or database connectivity tests at the
    module level (import time).
  - **Docker Networking**: Inside containers, use the `db` hostname for
    PostgreSQL. Outside, use `localhost`.
- **GCP Auth**: `credentials.json` must be in the root for ETL tasks. See
  [`docs/pipeline/GCP_SETUP.md`](../../docs/pipeline/GCP_SETUP.md).

## Environment Issues

### Issue: "pre-commit not found" or command fails

**Solution:** Run `pixi install` first. Pixi manages pre-commit installation.

```bash
pixi install
pixi run pre-commit
```

### Issue: Modifying pixi.toml breaks the environment

**Solution:**

```bash
# Validate syntax, reinstall environment
pixi install

# If still broken, remove and reinstall
rm -rf .pixi
pixi install
```

### Issue: Platform-specific problems (non-supported platforms)

**Current platforms:** `osx-arm64`, `osx-64`, `linux-64`

**Solution:** Edit `pixi.toml` and add platforms:

```toml
platforms = ["osx-arm64", "osx-64", "linux-64", "linux-aarch64"]
```

Then run `pixi install`.

## Namespace Package Issues

For detailed namespace package troubleshooting, see
[namespace-packages.md](namespace-packages.md).

### Issue: "ModuleNotFoundError: No module named 'ca_biositing.<package>'"

**Causes:**

1. Package not installed
2. `__init__.py` exists in `ca_biositing/` directory (breaks namespace)
3. Incorrect working directory

**Quick fix:**

```bash
# Verify no __init__.py in ca_biositing/
ls -la src/ca_biositing/
# Should show: datamodels/ pipeline/ webservice/ (no __init__.py)

# Reinstall
pixi install
```

### Issue: Import works in one package but not another

**Cause:** Only some packages are installed.

**Solution:** Install all packages:

```bash
pixi install  # Installs all packages via Pixi
```

## Docker Issues

### Issue: Docker container won't start

```bash
# Check container logs
pixi run service-logs

# Rebuild from scratch
pixi run teardown-services
pixi run rebuild-services
pixi run start-services

# Check if ports are already in use
lsof -i :5432  # PostgreSQL default port
lsof -i :4200  # Prefect UI port
```

### Issue: Database connection refused

**Check:** `DATABASE_URL` uses correct host (`db`, not `localhost` in
containers)

**Solution:** Update `resources/docker/.env` to use `POSTGRES_HOST=db`

### Issue: "Module not found" errors in containers

```bash
# Add dependency to appropriate feature
pixi add --feature pipeline --pypi <package-name>

# Rebuild and restart
pixi run rebuild-services
pixi run start-services
```

### Issue: Services not starting in correct order

**Cause:** Health checks not passing or dependencies not ready.

**Solution:**

```bash
# Check individual service health
pixi run check-db-health

# View detailed logs
pixi run service-logs

# Restart all services
pixi run restart-services
```

## Database Issues

### Issue: Database migration errors

```bash
# Check migration history
pixi run exec-prefect-worker alembic history

# Downgrade and reapply
pixi run exec-prefect-worker alembic downgrade -1
pixi run exec-prefect-worker alembic upgrade head

# For development, clear and restart (CAUTION: deletes data)
pixi run teardown-services-volumes
pixi run start-services
```

### Issue: SQLModel field defaults

**Problem:** Field validation errors or unexpected None values

**Solution:**

- Use `default=None` for optional fields
- Use `Optional[T]` type hint for nullable fields
- Use `default_factory=callable` for mutable defaults (lists, dicts, datetime)

```python
# Correct patterns
name: Optional[str] = Field(default=None, description="Name")
created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
tags: List[str] = Field(default_factory=list, description="Tags")
```

### Issue: Foreign key constraints

Foreign keys are normally declared directly in the SQLModel classes and enforced
through Alembic migrations.

If a table must be loaded before its parent rows exist, keep the field nullable
for that bootstrap period and add the constraint in a migration once the data
flow is ready.

```python
parent_id: Optional[int] = Field(
    default=None,
    description="Reference to parent"
    # foreign_key="parent_table.id"  # Uncomment when ready
)
```

In practice, "when ready" means the schema and load order are stable enough that
the database can enforce referential integrity without blocking the ETL or
initial backfill.

### Issue: Decimal vs Float precision

**Problem:** Precision issues with financial/scientific data

**Solution:** Always use `Decimal` for currency, percentages, precise
measurements.

```python
# Good - use Decimal for precision
price: Optional[Decimal] = Field(default=None)
percentage: Optional[Decimal] = Field(default=None)

# Bad - float loses precision
price: Optional[float] = Field(default=None)  # Don't use for currency
```

### Issue: DateTime deprecation warning

**Problem:** `datetime.utcnow()` deprecation warning

**Current:**

```python
from datetime import datetime, UTC
from sqlmodel import Field

created_at: datetime = Field(
    default_factory=lambda: datetime.now(tz=UTC)
)
```

**Recommended migration:**

```python
from datetime import datetime, UTC

created_at: datetime = Field(
    default_factory=lambda: datetime.now(UTC)
)
```

### Issue: SQLModel deprecation warnings

**Problem:** Warning about `session.query()` vs `session.exec()`

**Solution:** Prefer `session.exec()` for SQLModel queries:

```python
# Old pattern
records = session.query(Model).all()

# New pattern (recommended)
from sqlmodel import select
records = session.exec(select(Model)).all()
```

## Prefect Issues

### Issue: Prefect worker not picking up flow runs

```bash
# Check worker logs
pixi run service-logs

# Restart worker
pixi run restart-prefect-worker

# Verify work pool exists in Prefect UI
# Navigate to: http://0.0.0.0:4200/work-pools
```

### Issue: Prefect server not responding

```bash
# Check server health endpoint
curl -f http://0.0.0.0:4200/api/health

# Expected output: HTTP 200 OK

# Restart services if needed
pixi run restart-services
```

### Issue: Prefect logger context errors in tests

**Problem:** `MissingContextError: There is no active flow or task run context`

**Solution:** See [testing-patterns.md](testing-patterns.md) for the `.fn()`
pattern.

Quick fix:

```python
from unittest.mock import patch

@patch("module.get_run_logger")
def test_task(mock_logger):
    mock_logger.return_value.info = lambda msg: None
    result = my_task.fn()  # Use .fn() instead of my_task()
```

### Issue: Flow deployment fails

```bash
# Check Prefect server is running
pixi run service-status

# Redeploy flows
pixi run deploy

# Check deployment in UI
# Navigate to: http://0.0.0.0:4200/deployments
```

## Google Sheets Issues

### Issue: Google Sheets authentication fails

1. Ensure `credentials.json` is in the correct location (project root)
2. Follow the complete setup: `docs/pipeline/GCP_SETUP.md`
3. Check `resources/docker/.env` file has correct configuration
4. Verify service account has access to the Google Sheets

### Issue: "File not found: credentials.json"

**Solution:**

```bash
# Verify credentials file exists
ls -la credentials.json

# For Docker, check mount in docker-compose.yml
# credentials.json should be mounted into container
```

### Issue: "Permission denied" accessing Google Sheet

**Cause:** Service account doesn't have access to the sheet.

**Solution:**

1. Open the Google Sheet in browser
2. Click "Share" button
3. Add the service account email (from credentials.json)
4. Give at least "Viewer" permission

## QGIS Issues

### Issue: QGIS fails to launch on macOS

Python faulthandler error is expected and can be ignored. See:
<https://github.com/qgis/QGIS/issues/52987>

If QGIS doesn't launch at all:

```bash
rm -rf .pixi
pixi install
pixi run qgis
```

### Issue: QGIS plugins not loading

**Solution:**

```bash
# Ensure gis environment is active
pixi run -e gis qgis

# Or launch QGIS directly in gis environment
pixi shell -e gis
qgis
```

## API Issues

### Issue: 422 Unprocessable Entity errors

**Cause:** Request body doesn't match Pydantic model

**Solution:**

- Check Pydantic model field types
- Use `Field()` for validation rules
- Test with correct JSON structure
- Check FastAPI `/docs` for expected schema

```python
# Example: field requires min_length
class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1)  # Empty string will cause 422
```

### Issue: CORS errors in browser

**Cause:** Missing CORS middleware

**Solution:** Add CORS middleware to FastAPI app:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue: TestClient import fails

**Cause:** Missing httpx dependency

**Solution:** Add to `pyproject.toml`:

```toml
dependencies = ["httpx>=0.27.0"]
```

### Issue: Database session errors in endpoints

**Cause:** Incorrect dependency injection or session management

**Solution:**

```python
# Correct pattern
from fastapi import Depends
from sqlmodel import Session
from ca_biositing.datamodels.database import get_session

@app.get("/items")
async def list_items(session: Session = Depends(get_session)):
    # Use session
    pass
```

### Issue: Async vs sync confusion

**Problem:** Blocking calls in async endpoints

**Solution:**

```python
# Good - async all the way
@app.get("/items")
async def list_items():
    return await get_items_async()

# Good - use sync for blocking calls
@app.get("/items")
def list_items():  # Note: def, not async def
    return blocking_database_call()

# Bad - blocking in async (blocks event loop)
@app.get("/items")
async def list_items():
    return blocking_call()  # Don't do this
```

## Pandas Issues

### Issue: SettingWithCopyWarning

**Problem:** Warning when modifying DataFrame slice

**Solution:** Always use `.copy()` when modifying DataFrames:

```python
# Bad - may cause warning
df = source_df[source_df["col"] > 0]
df["new_col"] = "value"

# Good - explicit copy
df = source_df[source_df["col"] > 0].copy()
df["new_col"] = "value"

# Good - method chaining with pyjanitor
df = (
    source_df.copy()
    .filter_on("col > 0")
    .add_column("new_col", "value")
)
```

### Issue: Empty DataFrame handling

**Solution:** Always check for empty DataFrames:

```python
if df is None or df.empty:
    logger.warning("No data to process")
    return None
```

## General Tips

### When to restart services

```bash
# After changing Python dependencies
pixi run rebuild-services
pixi run start-services

# After changing .env file
pixi run restart-services

# After changing flow code (with volume mounts)
# No restart needed - changes are picked up automatically

# After changing Docker configuration
pixi run teardown-services
pixi run start-services
```

### Checking service health

```bash
# All services status
pixi run service-status

# Database health
pixi run check-db-health

# Prefect server health
curl http://0.0.0.0:4200/api/health

# View all logs
pixi run service-logs
```

### Getting help

- Check the specific package AGENTS.md for package-specific guidance
- Check the main [/AGENTS.md](../../AGENTS.md) for project-wide guidance
- Search existing issues on GitHub
- Check Prefect documentation: <https://docs.prefect.io/>
- Check FastAPI documentation: <https://fastapi.tiangolo.com/>
- Check SQLModel documentation: <https://sqlmodel.tiangolo.com/>
