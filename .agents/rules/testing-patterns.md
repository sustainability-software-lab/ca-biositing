# Testing Patterns

**Load when:** writing, fixing, or running tests: pytest fixtures, Prefect task
tests, and FastAPI TestClient tests.

This document consolidates testing patterns used across all ca-biositing
packages.

## Running Tests with Pixi

### Project-Wide Commands

```bash
# Run all tests
pixi run test
# Runs pytest on tests/ directory with verbose output

# Run tests with coverage report
pixi run test-cov
# Generates HTML coverage report in htmlcov/
# Shows coverage for src/ca_biositing module
# Displays term-missing report in terminal
```

### Package-Specific Commands

```bash
# Datamodels tests
pixi run pytest src/ca_biositing/datamodels -v
pixi run pytest src/ca_biositing/datamodels --cov=ca_biositing.datamodels --cov-report=html

# Pipeline tests
pixi run pytest src/ca_biositing/pipeline -v
pixi run pytest src/ca_biositing/pipeline --cov=ca_biositing.pipeline --cov-report=html

# Webservice tests
pixi run pytest src/ca_biositing/webservice -v
pixi run pytest src/ca_biositing/webservice --cov=ca_biositing.webservice --cov-report=html --cov-report=term-missing

# Run specific test file
pixi run pytest src/ca_biositing/<package>/tests/test_<module>.py -v

# Run specific test function
pixi run pytest src/ca_biositing/<package>/tests/test_<module>.py::test_function_name -v
```

### Standalone Development

```bash
# From the package directory
pip install -e .
pytest -v
```

## Test Fixtures (conftest.py)

All packages use similar fixture patterns defined in their `tests/conftest.py`.

### Database Session Fixture

Used by **datamodels** and **pipeline** packages:

```python
import pytest
from sqlmodel import Session, create_engine, SQLModel

@pytest.fixture
def engine():
    """Create an in-memory SQLite database engine."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine

@pytest.fixture
def session(engine):
    """Create a database session for tests."""
    with Session(engine) as session:
        yield session
```

**Usage:**

```python
def test_my_function(session):
    """Test using database session."""
    # session is an in-memory SQLite database
    model = MyModel(name="test")
    session.add(model)
    session.commit()
    assert model.id is not None
```

**Available fixtures:**

- `engine`: SQLite in-memory database engine
- `session`: SQLModel session for database operations

### FastAPI TestClient Fixture

Used by **webservice** package:

```python
import pytest
from fastapi.testclient import TestClient
from ca_biositing.webservice.main import app

@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)
```

**Usage:**

```python
def test_endpoint(client):
    """Test an API endpoint."""
    response = client.get("/some-endpoint")
    assert response.status_code == 200
    data = response.json()
    assert "key" in data
```

## Test Patterns by Type

### Model Instantiation Test

Test creating model instances without database:

```python
from decimal import Decimal

def test_model_creation():
    """Test creating a Model instance."""
    model = MyModel(name="Test", value=Decimal("100.50"))
    assert model.name == "Test"
    assert model.value == Decimal("100.50")
    assert model.id is None  # Not yet persisted
```

### Database Persistence Test

Test saving and retrieving from database:

```python
def test_model_persistence(session):
    """Test saving and retrieving a Model."""
    model = MyModel(name="Test")
    session.add(model)
    session.commit()
    session.refresh(model)

    assert model.id is not None

    retrieved = session.get(MyModel, model.id)
    assert retrieved is not None
    assert retrieved.name == "Test"
```

### API Endpoint Test (GET)

Test reading data via API:

```python
from fastapi import status

def test_read_item(client):
    """Test reading a single item."""
    response = client.get("/items/1")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "id" in data
    assert "name" in data
    assert data["id"] == 1
```

### API Endpoint Test (POST)

Test creating data via API:

```python
def test_create_item(client):
    """Test creating a new item."""
    item_data = {
        "name": "Test Item",
        "description": "A test item",
    }
    response = client.post("/items", json=item_data)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == item_data["name"]
    assert "id" in data
```

### Utility Function Test

Test utility functions with database:

```python
def test_lookup_utility(session):
    """Test lookup utility function."""
    from ca_biositing.pipeline.utils.lookup_utils import replace_name_with_id_df
    from ca_biositing.datamodels.biomass import BiomassType

    # Create test data
    biomass_type = BiomassType(biomass_type="Test Type")
    session.add(biomass_type)
    session.commit()

    # Test the function
    df = pd.DataFrame({"biomass_type": ["Test Type"]})
    result = replace_name_with_id_df(
        db=session,
        df=df,
        ref_model=BiomassType,
        name_column_name="biomass_type",
        id_column_name="biomass_type_id"
    )

    assert "biomass_type_id" in result.columns
    assert result.loc[0, "biomass_type_id"] == biomass_type.biomass_type_id
```

## Testing Prefect Tasks

Prefect tasks require special handling to avoid runtime context errors.

### The Problem

```python
# This will fail with MissingContextError
def test_my_task():
    result = my_task()  # Error: no active flow/task context
```

The error message:

```
prefect.exceptions.MissingContextError: There is no active flow or task run context
```

### The Solution: Use .fn() and Mock Logger

```python
from unittest.mock import patch
import pandas as pd

@patch("ca_biositing.pipeline.etl.extract.basic_sample_info.get_run_logger")
@patch("ca_biositing.pipeline.etl.extract.basic_sample_info.gsheet_to_df")
def test_extract_task(mock_gsheet, mock_logger):
    """Test extract task with mocked dependencies."""
    from ca_biositing.pipeline.etl.extract.basic_sample_info import extract_basic_sample_info

    # Mock logger to avoid Prefect context issues
    mock_logger.return_value.info = lambda msg: None
    mock_logger.return_value.error = lambda msg: None
    mock_logger.return_value.warning = lambda msg: None

    # Mock external data source
    mock_gsheet.return_value = pd.DataFrame({"col": ["val"]})

    # Call the task function directly using .fn()
    result = extract_basic_sample_info.fn()

    # Verify results
    assert result is not None
    assert len(result) == 1
```

### Key Points

1. **Use `.fn()`** - Call the underlying function without Prefect runtime:
   `my_task.fn()` instead of `my_task()`

2. **Mock `get_run_logger()`** - Avoid context errors by mocking the logger

3. **Mock external dependencies** - Google Sheets, APIs, databases, etc.

4. **Patch at the correct location** - Patch where the function is imported, not
   where it's defined

### Complete Prefect Task Test Example

```python
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest

@patch("ca_biositing.pipeline.etl.extract.my_module.get_run_logger")
@patch("ca_biositing.pipeline.etl.extract.my_module.gsheet_to_df")
def test_extract_my_data(mock_gsheet, mock_logger):
    """Test extract task with mocked dependencies."""
    from ca_biositing.pipeline.etl.extract.my_module import extract_my_data

    # Setup mock logger
    logger_mock = MagicMock()
    mock_logger.return_value = logger_mock

    # Setup mock data
    mock_gsheet.return_value = pd.DataFrame({
        "column1": ["value1", "value2"],
        "column2": [1, 2]
    })

    # Call the task function directly
    result = extract_my_data.fn()

    # Assertions
    assert result is not None
    assert len(result) == 2
    assert "column1" in result.columns

    # Verify logging was called
    logger_mock.info.assert_called()
```

### Testing Transform Tasks

```python
@patch("ca_biositing.pipeline.etl.transform.my_module.get_run_logger")
def test_transform_my_data(mock_logger):
    """Test transform task."""
    from ca_biositing.pipeline.etl.transform.my_module import transform_my_data

    mock_logger.return_value.info = lambda msg: None

    # Prepare input data
    input_data = {
        "source": pd.DataFrame({"raw_col": ["value1", "value2"]})
    }

    # Call transform
    result = transform_my_data.fn(input_data)

    # Verify transformation
    assert result is not None
    assert "transformed_col" in result.columns
```

### Testing Load Tasks

```python
@patch("ca_biositing.pipeline.etl.load.my_module.get_run_logger")
@patch("ca_biositing.pipeline.etl.load.my_module.get_engine")
def test_load_my_data(mock_engine, mock_logger, session):
    """Test load task with database session."""
    from ca_biositing.pipeline.etl.load.my_module import load_my_data

    mock_logger.return_value.info = lambda msg: None
    mock_engine.return_value = session.get_bind()

    # Prepare data to load
    df = pd.DataFrame({"name": ["Test1", "Test2"]})

    # Call load
    load_my_data.fn(df)

    # Verify data was loaded
    from ca_biositing.datamodels.my_model import MyModel
    records = session.query(MyModel).all()
    assert len(records) == 2
```

## Test Structure

Each package has a similar test directory structure:

```text
tests/
├── __init__.py
├── conftest.py           # Shared fixtures
├── README.md             # Test documentation
├── test_package.py       # Package metadata tests
├── test_<module>.py      # Module-specific tests
└── ...
```

### Package Metadata Test

Every package should have a test verifying package metadata:

```python
def test_package_version():
    """Test that package version is defined."""
    from ca_biositing.<package> import __version__
    assert __version__ is not None
    assert isinstance(__version__, str)
```

### Flow Import Test

For pipeline package, test that flows can be imported:

```python
def test_flow_imports():
    """Test that all flows can be imported."""
    from ca_biositing.pipeline.flows.primary_product import primary_product_flow
    from ca_biositing.pipeline.flows.analysis_type import analysis_type_flow

    assert primary_product_flow is not None
    assert analysis_type_flow is not None
```
