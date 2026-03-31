# ca-biositing

A geospatial bioeconomy project for biositing analysis in California. This
repository provides tools for ETL pipelines to process data from Google Sheets
into PostgreSQL databases, geospatial analysis using QGIS, and a REST API for
data access.

## Project Structure

This project uses a **PEP 420 namespace package** structure with three main
components:

- **`ca_biositing.datamodels`**: Hand-written SQLModel database models,
  materialized views, and database configuration
- **`ca_biositing.pipeline`**: ETL pipelines orchestrated with Prefect, deployed
  via Docker
- **`ca_biositing.webservice`**: FastAPI REST API for data access

### Directory Layout

```text
ca-biositing/
├── src/ca_biositing/           # Namespace package root
│   ├── datamodels/             # Database models (SQLModel) and Alembic migrations
│   ├── pipeline/               # ETL pipelines (Prefect)
│   └── webservice/             # REST API (FastAPI)
├── resources/                  # Deployment resources
│   ├── docker/                 # Docker Compose configuration
│   └── prefect/                # Prefect deployment files
├── tests/                      # Integration tests
├── pixi.toml                   # Pixi dependencies and tasks
│   └── pixi.lock               # Dependency lock file
```

## Quick Start

### Prerequisites

- **Pixi** (v0.55.0+):
  [Installation Guide](https://pixi.sh/latest/#installation)
- **Docker**: For running the ETL pipeline
- **Google Cloud credentials**: For Google Sheets access (optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/sustainability-software-lab/ca-biositing.git
cd ca-biositing

# Install dependencies with Pixi
pixi install

# Install pre-commit hooks
pixi run pre-commit-install
```

### Running Components

#### ETL Pipeline (Prefect + Docker)

**Note**: Before starting the services for the first time, create the required
environment file from the template:

```bash
cp resources/docker/.env.example resources/docker/.env
```

**CRITICAL (PostgreSQL 15 Upgrade)**: If you are upgrading from a version prior
to Feb 2026, you must wipe your local volumes to support the PostgreSQL 15
image:

```bash
pixi run teardown-services-volumes
```

Then start and use the services:

```bash
# 1. Start all services (PostgreSQL, Prefect server, worker)
pixi run start-services

# 2. Deploy flows to Prefect
pixi run deploy

# 3. Apply any pending database migrations
# Note: start-services automatically applies migrations at startup via the
# setup-db container. Run this step manually when you pull new migration
# files without restarting services.
pixi run migrate

# 4. Run the ETL pipeline
pixi run run-etl

# Monitor via Prefect UI: http://localhost:4200

# Stop services
pixi run teardown-services
```

See [`resources/README.md`](resources/README.md) for detailed pipeline
documentation.

#### Web Service (FastAPI)

```bash
# Start the web service
pixi run start-webservice

# Access API docs: http://localhost:8000/docs
```

#### QGIS (Geospatial Analysis)

```bash
pixi run qgis
```

**Note**: On macOS, you may see a Python faulthandler error - this is expected
and can be ignored. See
[QGIS Issue #52987](https://github.com/qgis/QGIS/issues/52987).

## Development

### Running Tests

```bash
# Run all tests
pixi run test

# Run tests with coverage
pixi run test-cov
```

### Code Quality

```bash
# Run pre-commit checks on staged files
pixi run pre-commit

# Run pre-commit on all files (before PR)
pixi run pre-commit-all
```

### Available Pixi Tasks

View all available tasks:

```bash
pixi task list
```

Key tasks:

- **Service Management**: `start-services`, `teardown-services`,
  `service-status`
- **ETL Operations**: `deploy`, `run-etl`
- **Development**: `test`, `test-cov`, `pre-commit`, `pre-commit-all`
- **Applications**: `start-webservice`, `qgis`
- **Database**: `access-db`, `check-db-health`
- **Schema Management**: `migrate`, `migrate-autogenerate`, `refresh-views`
- **Validation (pgschema)**: `schema-plan`, `schema-analytics-plan`,
  `schema-dump`, `schema-analytics-list`

## Architecture

### Namespace Packages

This project uses **PEP 420 namespace packages** to organize code into
independently installable components that share a common namespace:

- Each component has its own `pyproject.toml` and can be installed separately
- Shared models in `datamodels` are used by both `pipeline` and `webservice`
- Clear separation of concerns while maintaining type consistency

### ETL Pipeline

The ETL pipeline uses:

- **Prefect**: Workflow orchestration and monitoring
- **Docker**: Containerized execution environment
- **PostgreSQL**: Data persistence
- **Google Sheets API**: Primary data source

Pipeline architecture:

1. **Extract**: Pull data from Google Sheets
2. **Transform**: Clean and normalize data with pandas
3. **Load**: Insert/update records in PostgreSQL via SQLAlchemy

### Database Models

Database models are **hand-written SQLModel classes** organized into 15 domain
subdirectories under
`src/ca_biositing/datamodels/ca_biositing/datamodels/models/`. All schema
changes are managed through Alembic migrations.

**Development workflow:**

1.  Edit SQLModel classes in `models/`
2.  Auto-generate a migration: `pixi run migrate-autogenerate -m "Description"`
3.  Apply the migration: `pixi run migrate`

SQLModel-based models provide:

- Type-safe database operations (SQLAlchemy + Pydantic in one class)
- Versioned schema migrations (via Alembic)
- Shared models across ETL and API components
- Built-in Pydantic validation

Seven materialized views are defined in `views.py` and managed through Alembic
migrations. Refresh them after loading data with `pixi run refresh-views`.

## Project Components

### 1. Data Models (`ca_biositing.datamodels`)

Database models for:

- Biomass data (field samples, measurements)
- Geographic locations
- Experiments and analysis
- Metadata and samples
- Organizations and contacts

**Documentation**: [`datamodels/README.md`](datamodels/README.md)

### 2. ETL Pipeline (`ca_biositing.pipeline`)

Prefect-orchestrated workflows for:

- Data extraction from Google Sheets
- Data transformation and validation
- Database loading and updates
- Lookup table management

**Documentation**: [`pipeline/README.md`](pipeline/README.md)

**Guides**:

- [Docker Workflow](pipeline/DOCKER_WORKFLOW.md)
- [Prefect Workflow](pipeline/PREFECT_WORKFLOW.md)
- [ETL Development](pipeline/ETL_WORKFLOW.md)
- [Database Migrations](pipeline/ALEMBIC_WORKFLOW.md)

### 3. Web Service (`ca_biositing.webservice`)

FastAPI REST API providing:

- Read access to database records
- Interactive API documentation (Swagger/OpenAPI)
- Type-safe endpoints using Pydantic

**Documentation**: [`webservice/README.md`](webservice/README.md)

### 4. Deployment Resources (`resources/`)

Docker and Prefect configuration for:

- Service orchestration (Docker Compose)
- Prefect deployments
- Database initialization

**Documentation**: [`resources/README.md`](resources/README.md)

## Adding Dependencies

### For Local Development (Pixi)

```bash
# Add conda package to default environment
pixi add <package-name>

# Add PyPI package to default environment
pixi add --pypi <package-name>

# Add to specific feature (e.g., pipeline)
pixi add --feature pipeline --pypi <package-name>
```

### For ETL Pipeline (Docker)

The pipeline dependencies are managed by Pixi's `etl` environment feature in
`pixi.toml`. When you add dependencies and rebuild Docker images, they are
automatically included:

```bash
# Add dependency to pipeline feature
pixi add --feature pipeline --pypi <package-name>

# Rebuild Docker images
pixi run rebuild-services

# Restart services
pixi run start-services
```

## Environment Management

This project uses **Pixi environments** for different workflows:

- **`default`**: General development, testing, pre-commit hooks
- **`gis`**: QGIS and geospatial analysis tools
- **`etl`**: ETL pipeline (used in Docker containers)
- **`webservice`**: FastAPI web service
- **`frontend`**: Node.js/npm for frontend development

## Frontend Integration

This repository now includes the **Cal Bioscape Frontend** as a Git submodule
located in the `frontend/` directory.

### Initializing the Submodule

When you first clone this repository, you can initialize and pull only the
`frontend` submodule with:

```bash
pixi run submodule-frontend-init
```

## 📘 Documentation

This project uses
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/) for
documentation.

### Local Preview

You can preview the documentation locally using [Pixi](https://pixi.sh/):

```bash
pixi install -e docs
pixi run -e docs docs-serve
```

Then open your browser and go to:

```
http://127.0.0.1:8000
```

### Contributing Documentation

Most documentation should live in the relevant directories within the `docs`
folder.

When adding new pages to the documentation, make sure you update the
[`mkdocs.yml` file](https://github.com/sustainability-software-lab/ca-biositing/blob/main/mkdocs.yml)
so they can be rendered on the website.

If you need to add documentation referencing a file that lives elsewhere in the
repository, you'll need to do the following (this is an example, run from the
package root directory)

```bash
# symlink the file to its destination
# Be sure to use relative paths here, otherwise it won't work!
ln -s ../../deployment/README.md docs/deployment/README.md

# stage your new file
git add docs/deployment/README.md
```

Be sure to preview the documentation to make sure it's accurate before
submitting a PR.
