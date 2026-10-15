# Code Quality Standards

**Load when:** writing or reviewing Python code (style, type hints, docstrings,
imports), committing, preparing a PR, or claiming that checks pass.

This document consolidates code quality requirements, pre-commit workflows, and
style guidelines used across all ca-biositing packages.

## Pre-commit Checks (MANDATORY BEFORE PRs)

**Always run pre-commit checks before creating a pull request.**

### Setup (Run Once Per Clone)

```bash
# Install pre-commit hooks
pixi run pre-commit-install
# ✓ Installs .git/hooks/pre-commit
# ✓ Hooks will automatically run on every commit
```

### Daily Workflow

```bash
# Run pre-commit on staged files only (fast)
pixi run pre-commit
# ✓ Fast, only checks staged changes
# ✓ Will auto-fix many issues (trailing whitespace, end-of-file, formatting)
# ⚠️ If fixes are made, files are modified; you must re-stage them

# Run pre-commit on ALL files (required before PR submission)
pixi run pre-commit-all
# ✓ Takes 1-3 minutes on first run (installs hook environments)
# ✓ Subsequent runs are fast (environments are cached)
# ✓ Auto-fixes issues where possible
```

### Auto-Fix Workflow

When pre-commit auto-fixes files:

1. The hook shows "Failed" with "files were modified by this hook"
2. Re-stage the fixed files: `git add <files>`
3. Re-run `pixi run pre-commit` to verify

**This is expected behavior, not an error.**

### Package-Specific Checks

```bash
# Check specific package files
pixi run pre-commit run --files src/ca_biositing/datamodels/**/*
pixi run pre-commit run --files src/ca_biositing/pipeline/**/*
pixi run pre-commit run --files src/ca_biositing/webservice/**/*

# Check specific file
pixi run pre-commit run --files src/ca_biositing/datamodels/ca_biositing/datamodels/biomass.py
```

## Code Style Requirements

### Type Hints

**Required for all fields and functions.**

```python
from typing import Optional, Dict, List
import pandas as pd

# Function with type hints
def process_data(data: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Process the input data."""
    if data.empty:
        return None
    return data

# Function with multiple return types
def get_value(key: str) -> Optional[str]:
    """Get value by key."""
    return values.get(key)

# Function with complex types
def transform_data(
    data_sources: Dict[str, pd.DataFrame],
    columns: List[str]
) -> pd.DataFrame:
    """Transform data from multiple sources."""
    pass
```

### Docstrings

Use triple-quoted strings for classes and functions:

```python
def extract_data() -> Optional[pd.DataFrame]:
    """
    Extract data from Google Sheets.

    Returns:
        DataFrame with raw data, or None if extraction fails.
    """
    pass

class MyModel(SQLModel, table=True):
    """
    Description of the model.

    Attributes:
        id: Unique identifier
        name: Name of the entity
    """
    pass
```

### Formatting

- Handled automatically by pre-commit hooks (prettier, autopep8, ruff, etc.)
- Follow PEP 8 guidelines for line length
- Use 4-space indentation for Python
- No trailing whitespace
- Files should end with a newline

## Import Conventions

Group imports in this order with blank lines between groups:

1. **Standard library** - Built-in Python modules
2. **Third-party packages** - External dependencies
3. **Local packages** - Project-specific imports

### General Pattern

```python
# Standard library
from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, List

# Third-party
import pandas as pd
from sqlmodel import SQLModel, Field, Session

# Local
from ca_biositing.datamodels.biomass import Biomass
```

### Datamodels Package Pattern

```python
# Standard library
from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

# Third-party
from sqlmodel import SQLModel, Field
from sqlalchemy import Index

# Local (if needed)
# from ca_biositing.datamodels.config import settings
```

### Pipeline Package Pattern

```python
# Standard library
from typing import Optional, Dict
from datetime import datetime

# Third-party
import pandas as pd
from prefect import task, flow, get_run_logger
from sqlmodel import Session

# Local - datamodels
from ca_biositing.datamodels.biomass import Biomass
from ca_biositing.datamodels.database import get_engine

# Local - pipeline
from ca_biositing.pipeline.utils.lookup_utils import replace_name_with_id_df
from ca_biositing.pipeline.utils.gsheet_to_pandas import gsheet_to_df
```

### Webservice Package Pattern

```python
# Standard library
from typing import Optional, List

# Third-party
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

# Local - datamodels
from ca_biositing.datamodels.biomass import Biomass
from ca_biositing.datamodels.database import get_session

# Local - webservice
from ca_biositing.webservice import __version__
```

## Package-Specific Standards

### Datamodels

- Always use proper type hints (`str`, `int`, `Optional[T]`)
- Use `Decimal` for financial or high-precision numeric fields
- Use `Optional[int] = Field(default=None, primary_key=True)` for auto-increment
  IDs
- Always provide field descriptions in `Field()`
- Use `__tablename__` to explicitly set table names (snake_case)
- Use `default_factory` for mutable defaults (lists, dicts, datetime)

```python
class MyModel(SQLModel, table=True):
    """Description of the model."""
    __tablename__ = "my_model"

    id: Optional[int] = Field(default=None, primary_key=True, description="Unique ID")
    name: str = Field(default=None, index=True, description="Name of entity")
    value: Optional[Decimal] = Field(default=None, description="Numeric value")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
```

### Pipeline

- Use `@task` decorator for ETL functions
- Use `@flow` decorator for orchestration
- Use `get_run_logger()` for logging in Prefect tasks
- Return `None` or empty DataFrame on errors (don't raise unless intended)
- Use `Optional[pd.DataFrame]` for nullable returns

```python
from prefect import task, get_run_logger

@task
def extract_data() -> Optional[pd.DataFrame]:
    """Extract data from source."""
    logger = get_run_logger()
    logger.info("Starting extraction...")

    try:
        df = fetch_data()
        logger.info(f"Extracted {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return None
```

### Webservice

- Use `async def` for all endpoints
- Use Pydantic models for request/response validation
- Use dependency injection for database sessions
- Use `HTTPException` for error responses
- Use `response_model` parameter for automatic validation

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

class ItemCreate(BaseModel):
    name: str

class ItemResponse(BaseModel):
    id: int
    name: str

router = APIRouter()

@router.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate, session: Session = Depends(get_session)):
    """Create a new item."""
    db_item = Item(**item.model_dump())
    session.add(db_item)
    session.commit()
    return db_item
```

## Common Issues

### Issue: Pre-commit check fails after making fixes

**Behavior:** Pre-commit hooks auto-fix files. When this happens:

1. The hook shows "Failed" with "files were modified by this hook"
2. You must re-stage the fixed files: `git add <files>`
3. Re-run `pixi run pre-commit` to verify

**This is expected behavior, not an error.**

### Issue: "pre-commit not found" or command fails

**Solution:** Run `pixi install` first. Pixi manages pre-commit installation.

### Issue: Import order warnings

**Solution:** Let pre-commit auto-fix, or manually organize:

1. Standard library
2. Third-party
3. Local

With blank lines between groups.
