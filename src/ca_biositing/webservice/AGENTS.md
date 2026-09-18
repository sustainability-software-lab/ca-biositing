# AGENTS.md - CA Biositing Web Service

This file provides guidance to AI assistants when working with the
ca-biositing-webservice namespace package.

## Package Overview

The **ca-biositing-webservice** package is a FastAPI-based REST API for the CA
Biositing project. It provides HTTP endpoints for accessing bioeconomy site
selection data and analysis results.

**Package Stats:**

- **Type:** REST API / Web Service
- **Size:** Small (~10-20 files expected)
- **Language:** Python 3.12+
- **Build System:** Hatchling (PEP 517)
- **Framework:** FastAPI (>=0.115.0, <1)
- **Server:** Uvicorn (>=0.30.0, <1)
- **Testing:** Pytest with TestClient
- **Namespace:** PEP 420 namespace package under `ca_biositing.webservice`

## Cross-Cutting Documentation

This package follows project-wide patterns documented in:

| Topic              | Document                                                           | When to Reference                          |
| ------------------ | ------------------------------------------------------------------ | ------------------------------------------ |
| Namespace Packages | [namespace_packages.md](../../../agent_docs/namespace_packages.md) | Import errors, package structure questions |
| Testing Patterns   | [testing_patterns.md](../../../agent_docs/testing_patterns.md)     | Writing tests, TestClient fixtures         |
| Code Quality       | [code_quality.md](../../../agent_docs/code_quality.md)             | Pre-commit, style, imports                 |
| Troubleshooting    | [troubleshooting.md](../../../agent_docs/troubleshooting.md)       | Common errors and solutions                |

## Package Structure

```text
src/ca_biositing/webservice/
├── LICENSE                     # BSD License
├── README.md                   # Package documentation
├── pyproject.toml              # Package metadata and dependencies
├── AGENTS.md                   # This file
├── ca_biositing/
│   └── webservice/
│       ├── __init__.py         # Package initialization with version
│       └── main.py             # FastAPI application
└── tests/
    ├── __init__.py
    ├── conftest.py             # Shared pytest fixtures (TestClient)
    ├── test_package.py         # Package-level tests
    ├── test_main.py            # API endpoint tests
    └── README.md               # Test documentation
```

## FastAPI Application Pattern

### Main Application (`ca_biositing/webservice/main.py`)

```python
"""Main FastAPI application for CA Biositing API."""

from fastapi import FastAPI

# Import version from package
from . import __version__

# Create FastAPI app with metadata
app = FastAPI(
    title="CA Biositing API",
    description="REST API for CA Biositing bioeconomy site selection",
    version=__version__,
)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "message": "Welcome to CA Biositing API",
        "version": __version__,
    }
```

**Key Patterns:**

- Always import `__version__` from package `__init__.py`
- Set app title, description, and version in FastAPI constructor
- Use async def for all endpoints (FastAPI best practice)
- Return dict objects (FastAPI automatically converts to JSON)
- Use type hints for request/response models

### Running the API

**Development server:**

```bash
# From project root
pixi run start-webservice

# Or manually with uvicorn
uvicorn ca_biositing.webservice.main:app --reload

# With custom host/port
uvicorn ca_biositing.webservice.main:app --host 0.0.0.0 --port 8000 --reload
```

**Access endpoints:**

- API: <http://localhost:8000>
- MCP Server (SSE): <http://localhost:8000/mcp>
- Interactive docs (Swagger): <http://localhost:8000/docs>
- Alternative docs (ReDoc): <http://localhost:8000/redoc>
- OpenAPI JSON: <http://localhost:8000/openapi.json>

## FastAPI Development Best Practices

### 1. Use Pydantic Models for Request/Response

```python
from pydantic import BaseModel, Field

class ItemCreate(BaseModel):
    """Model for creating a new item."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None

class ItemResponse(BaseModel):
    """Model for item responses."""
    id: int
    name: str
    description: str | None

@app.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate):
    """Create a new item."""
    # Implementation
    pass
```

### 2. Use Path/Query Parameters

```python
from fastapi import Path, Query

@app.get("/items/{item_id}")
async def read_item(
    item_id: int = Path(..., gt=0),
    include_details: bool = Query(False),
):
    """Get item by ID with optional details."""
    pass
```

### 3. Use Dependency Injection

```python
from fastapi import Depends
from sqlmodel import Session
from ca_biositing.datamodels.database import get_session

@app.get("/biomass/{biomass_id}")
async def read_biomass(
    biomass_id: int,
    session: Session = Depends(get_session),
):
    """Get biomass record from database."""
    biomass = session.get(Biomass, biomass_id)
    if not biomass:
        raise HTTPException(status_code=404, detail="Biomass not found")
    return biomass
```

### 4. Use HTTP Exception for Errors

```python
from fastapi import HTTPException, status

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    """Get item by ID."""
    item = get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )
    return item
```

### 5. Use Router for Organization

```python
from fastapi import APIRouter

router = APIRouter(prefix="/biomass", tags=["biomass"])

@router.get("/")
async def list_biomass():
    """List all biomass records."""
    pass

@router.get("/{biomass_id}")
async def read_biomass(biomass_id: int):
    """Get specific biomass record."""
    pass

# In main.py
app.include_router(router)
```

### 6. Model Context Protocol (MCP) Integration

The webservice includes an embedded MCP server powered by `mcp` SDK and
`FastMCP`.

```python
# In main.py
from ca_biositing.webservice.mcp_server import build_mcp_server

mcp = build_mcp_server(session_factory, config)

# Lifespan drives the session manager
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    _ = mcp.streamable_http_app()
    async with mcp.session_manager.run():
        yield

# Mounted as streamable HTTP
app.mount("/mcp", mcp.streamable_http_app())
```

**Testing MCP:** Use `TestClient` with a special `parse_mcp_sse` helper as
demonstrated in `tests/test_mcp.py`.

## Integration with Datamodels

The API depends on `ca-biositing-datamodels` for database models:

```python
from ca_biositing.datamodels.models import Resource
from ca_biositing.datamodels.database import get_session
from sqlmodel import Session, select
from fastapi import Depends

@app.get("/resources", response_model=list[Resource])
async def list_resources(
    session: Session = Depends(get_session),
):
    """List all resource records."""
    statement = select(Resource)
    resource_list = session.exec(statement).all()
    return resource_list
```

## API Design Guidelines

### RESTful URL Patterns

```text
GET    /items          # List all items
POST   /items          # Create new item
GET    /items/{id}     # Get specific item
PUT    /items/{id}     # Update item
DELETE /items/{id}     # Delete item
GET    /items/{id}/details  # Get item details (sub-resource)
```

### HTTP Status Codes

- **200 OK**: Successful GET, PUT, PATCH
- **201 Created**: Successful POST
- **204 No Content**: Successful DELETE
- **400 Bad Request**: Invalid request body
- **401 Unauthorized**: Missing/invalid authentication
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource doesn't exist
- **422 Unprocessable Entity**: Validation errors
- **500 Internal Server Error**: Server error

### Response Format

```json
// Successful response
{
  "id": 1,
  "name": "Item Name",
  "created_at": "2024-01-15T10:30:00Z"
}

// Error response
{
  "detail": "Error description"
}

// List response
[
  { "id": 1, "name": "Item 1" },
  { "id": 2, "name": "Item 2" }
]
```

## Common Tasks

### Adding a New Endpoint

1. **Define Pydantic models** (if needed):

   ```python
   class ItemCreate(BaseModel):
       name: str

   class ItemResponse(BaseModel):
       id: int
       name: str
   ```

2. **Add endpoint to `main.py`**:

   ```python
   @app.post("/items", response_model=ItemResponse, status_code=201)
   async def create_item(item: ItemCreate):
       # Implementation
       return {"id": 1, "name": item.name}
   ```

3. **Write tests in `tests/test_main.py`**:

   ```python
   def test_create_item(client):
       response = client.post("/items", json={"name": "Test"})
       assert response.status_code == 201
       data = response.json()
       assert data["name"] == "Test"
   ```

4. **Run tests**:

   ```bash
   pixi run pytest src/ca_biositing/webservice -v
   ```

### Adding Database Queries

1. **Import datamodels**:

   ```python
   from ca_biositing.datamodels.models import Resource
   from ca_biositing.datamodels.database import get_session
   from sqlmodel import Session, select
   from fastapi import Depends
   ```

2. **Use dependency injection**:

   ```python
   @app.get("/resources/{resource_id}")
   async def read_resource(
       resource_id: int,
       session: Session = Depends(get_session),
   ):
       resource = session.get(Resource, resource_id)
       if not resource:
           raise HTTPException(status_code=404, detail="Not found")
       return resource
   ```

### Adding CORS Support

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

## Performance Considerations

### Use Async Properly

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

### Database Connection Pooling

```python
# In database.py
engine = create_engine(
    database_url,
    pool_size=20,
    max_overflow=0,
)
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_expensive_data(param: str):
    # Expensive operation
    return data

@app.get("/data/{param}")
async def read_data(param: str):
    return get_expensive_data(param)
```

## Dependencies

### Core Dependencies

- **fastapi** (>=0.115.0, <1): Web framework
- **uvicorn** (>=0.30.0, <1): ASGI server
- **httpx** (>=0.27.0): HTTP client for TestClient
- **ca-biositing-datamodels** (>=0.1.0): Database models

### Testing Dependencies

- **pytest** (>=8.4.2): Testing framework
- **pytest-cov** (>=7.0.0): Coverage reporting

## Development Workflow

1. **Start development server:**

   ```bash
   pixi run start-webservice
   ```

2. **Make changes** to `main.py` or add new modules

3. **Test endpoints** in browser or with curl:

   ```bash
   curl http://localhost:8000/
   curl -X POST http://localhost:8000/items -H "Content-Type: application/json" -d '{"name":"Test"}'
   ```

4. **Write/update tests** in `tests/`

5. **Run tests:**

   ```bash
   pixi run pytest src/ca_biositing/webservice -v
   ```

6. **Check coverage:**

   ```bash
   pixi run pytest src/ca_biositing/webservice --cov=ca_biositing.webservice --cov-report=html
   ```

## Related Documentation

- **Main Project AGENTS.md:** [/AGENTS.md](../../../AGENTS.md)
- **Datamodels AGENTS.md:** [../datamodels/AGENTS.md](../datamodels/AGENTS.md)
- **Package README:** `README.md` (in this directory)
- **FastAPI Docs:** <https://fastapi.tiangolo.com/>
- **Pydantic Docs:** <https://docs.pydantic.dev/>

For more information on SSEC best practices:
<https://rse-guidelines.readthedocs.io/en/latest/llms-full.txt>
