# ca-biositing

[![ssec](https://img.shields.io/badge/SSEC-Project-purple?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAOCAQAAABedl5ZAAAACXBIWXMAAAHKAAABygHMtnUxAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAMNJREFUGBltwcEqwwEcAOAfc1F2sNsOTqSlNUopSv5jW1YzHHYY/6YtLa1Jy4mbl3Bz8QIeyKM4fMaUxr4vZnEpjWnmLMSYCysxTcddhF25+EvJia5hhCudULAePyRalvUteXIfBgYxJufRuaKuprKsbDjVUrUj40FNQ11PTzEmrCmrevPhRcVQai8m1PRVvOPZgX2JttWYsGhD3atbHWcyUqX4oqDtJkJiJHUYv+R1JbaNHJmP/+Q1HLu2GbNoSm3Ft0+Y1YMdPSTSwQAAAABJRU5ErkJggg==&style=plastic)](https://escience.washington.edu/software-engineering/ssec/)
[![BSD License](https://badgen.net/badge/license/BSD-3-Clause/blue)](./LICENSE)
[![Pixi Badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/prefix-dev/pixi/main/assets/badge/v0.json)](https://pixi.sh)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![DOI](https://zenodo.org/badge/1036998116.svg)](https://zenodo.org/badge/latestdoi/1036998116)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/sustainability-software-lab/ca-biositing/main.svg)](https://results.pre-commit.ci/latest/github/sustainability-software-lab/ca-biositing/main)

CA-BioSiting is the backend data platform for
[Cal BioScape](https://calbioscape.org), a web-based tool supporting the
development of a circular bioeconomy in California's Northern San Joaquin Valley
(San Joaquin, Stanislaus, and Merced counties). The platform is a part of the
[BioCircular Valley](https://calbioscape.org/about) initiative, a
multi-institutional collaboration involving Lawrence Berkeley National
Laboratory, UC Berkeley, UC Merced, UC Agriculture and Natural Resources, USDA
Albany Agricultural Research Station, the Almond Board of California, and BEAM
Circular. The initiative is funded through Schmidt Sciences' Virtual Institute
on Feedstocks of the Future, with support from the Foundation for Food &
Agriculture Research.

Cal BioScape aims to transform the region's abundant but often underutilized
agricultural waste streams -- crop residues, almond shells, fruit peels, orchard
trimmings -- into valuable bioproducts, sustainable biofuels, and advanced
materials. The platform serves feedstock suppliers, biomanufacturing companies,
policymakers, and researchers by providing interactive mapping, comprehensive
data integration, spatial analysis, and programmatic API access.

## Motivation

Identifying optimal locations for bioconversion facilities requires integrating
heterogeneous datasets across multiple spatial and analytical domains. Biomass
composition data (proximate, ultimate, compositional, ICP, XRF, XRD, and
calorimetry analyses), field sampling records, parcel-level crop mapping
(LandIQ), federal agricultural production statistics (USDA Census and Survey),
and DOE Billion Ton Study projections all originate from different sources with
varying schemas and spatial resolutions. Meaningful siting analysis depends on
spatially joining these datasets to enable high-resolution visualization of
agricultural feedstocks, spatial buffer and summary queries for radius-based
resource aggregation, and temporal filtering across data sources.

CA-BioSiting provides the data infrastructure to automate ingestion of these
datasets, normalize them into a common relational schema with geospatial support
(PostgreSQL + PostGIS), and expose them through a REST API for downstream
analysis, visualization, and data export.

## Key Features

- **Automated ETL pipelines** for ingesting biomass characterization data,
  LandIQ crop mapping, USDA agricultural statistics, and DOE Billion Ton Study
  records
- **Spatially-enabled relational database** (PostgreSQL + PostGIS) with 15
  domain model groups covering field sampling, analytical records,
  fermentation/pretreatment experiments, and geographic information
- **Materialized views** that pre-compute spatial joins across datasets (e.g.,
  LandIQ records with crop mapping, USDA records with commodity lookups, Billion
  Ton records with spatial tile aggregation)
- **REST API** (FastAPI) for programmatic access to all ingested and derived
  data with interactive OpenAPI documentation
- **Cloud-native deployment** on Google Cloud Run with Cloud SQL (PostgreSQL),
  infrastructure managed as code via Pulumi, and automated CI/CD through GitHub
  Actions
- **Reproducible environments** using [Pixi](https://pixi.sh) for local
  development and Docker for containerized production deployment

## Data Domains

The database schema covers the following research domains:

| Domain                  | Description                                                                   |
| ----------------------- | ----------------------------------------------------------------------------- |
| Aim 1 Records           | Proximate, ultimate, compositional, ICP, XRF, XRD, and calorimetry analyses   |
| Aim 2 Records           | Fermentation and pretreatment experiment results                              |
| Field Sampling          | Sample collection metadata and location information                           |
| Sample Preparation      | Prepared sample tracking and provenance                                       |
| External Data           | LandIQ crop mapping, USDA Census/Survey records, Billion Ton 2023 projections |
| Resource Information    | Biomass resource types and characteristics                                    |
| Places & Infrastructure | Geographic locations, addresses, and facility information                     |
| People & Organizations  | Contacts and institutional affiliations                                       |

## Architecture

CA-BioSiting is organized as a
[PEP 420 namespace package](https://peps.python.org/pep-0420/) with three
independently installable components:

- **`ca_biositing.datamodels`** -- SQLModel database models, Alembic migrations,
  and materialized view definitions
- **`ca_biositing.pipeline`** -- Prefect-orchestrated ETL workflows for data
  extraction, transformation, and loading
- **`ca_biositing.webservice`** -- FastAPI REST API for data access

The ETL pipeline extracts data from Google Sheets, transforms and validates
records with pandas, and loads them into PostgreSQL via SQLAlchemy. Seven
materialized views provide pre-computed spatial joins for common query patterns.

## GitHub Actions

| Workflow                             | Status                                                                                                                                                                                                                                      |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CI                                   | [![CI](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/ci.yml/badge.svg)](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/ci.yml)                                               |
| CD                                   | [![CD](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/cd.yml/badge.svg)](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/cd.yml)                                               |
| Migrations                           | [![Migrations](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/migrations.yml/badge.svg)](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/migrations.yml)                       |
| Build and Push Docker Images         | [![Build and Push Docker Images](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/docker-build.yml/badge.svg)](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/docker-build.yml) |
| Deploy Staging                       | [![Deploy Staging](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/deploy-staging.yml/badge.svg)](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/deploy-staging.yml)           |
| Deploy Production                    | [![Deploy Production](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/deploy-production.yml/badge.svg)](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/deploy-production.yml)  |
| Trigger Staging ETL                  | [![Trigger Staging ETL](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/trigger-etl.yml/badge.svg)](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/trigger-etl.yml)            |
| Deploy Resource Info to GitHub Pages | [![Deploy Resource Info to GitHub Pages](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/gh-pages.yml/badge.svg)](https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/gh-pages.yml) |

## Docker Images

| Image                                                                                                                                                                 | Description                             |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| [`ghcr.io/sustainability-software-lab/ca-biositing/pipeline`](https://github.com/sustainability-software-lab/ca-biositing/pkgs/container/ca-biositing%2Fpipeline)     | ETL pipeline (Prefect flows and worker) |
| [`ghcr.io/sustainability-software-lab/ca-biositing/webservice`](https://github.com/sustainability-software-lab/ca-biositing/pkgs/container/ca-biositing%2Fwebservice) | FastAPI REST API                        |

## Technology Stack

| Component              | Technology                       |
| ---------------------- | -------------------------------- |
| Language               | Python 3                         |
| Database               | PostgreSQL 15 + PostGIS          |
| ORM / Models           | SQLModel (SQLAlchemy + Pydantic) |
| Migrations             | Alembic                          |
| Workflow Orchestration | Prefect                          |
| Web API                | FastAPI                          |
| Geospatial Analysis    | QGIS, GeoAlchemy2, Shapely       |
| Package Management     | Pixi (conda-forge + PyPI)        |
| Containerization       | Docker, Docker Compose           |
| Cloud Deployment       | Google Cloud Run, Pulumi         |
| CI/CD                  | GitHub Actions                   |

## Quick Start

### Prerequisites

- [Pixi](https://pixi.sh/latest/#installation) (v0.55.0+)
- [Docker](https://docs.docker.com/get-docker/)
- Google Cloud credentials (optional, for Google Sheets access)

### Installation

```bash
git clone https://github.com/sustainability-software-lab/ca-biositing.git
cd ca-biositing
pixi install
pixi run pre-commit-install
```

### Running the ETL Pipeline

```bash
# Create environment file from template
cp resources/docker/.env.example resources/docker/.env

# Start all services (PostgreSQL, Prefect server, worker)
pixi run start-services

# Deploy and run ETL flows
pixi run deploy
pixi run run-etl

# Monitor via Prefect UI at http://localhost:4200
```

### Running the Web Service

```bash
pixi run start-webservice
# API docs at http://localhost:8000/docs
```

## Documentation

Full documentation is available via
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/) and can be
previewed locally:

```bash
pixi install -e docs
pixi run -e docs docs-serve
# Open http://127.0.0.1:8000
```

## Contributing

See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for general contribution
guidelines (branching, PRs, commit style, pre-commit setup).

Each namespace package also has its own contributing guide with
component-specific details:

- [`docs/datamodels/CONTRIBUTING.md`](docs/datamodels/CONTRIBUTING.md) -- Data
  models and database schema
- [`docs/pipeline/CONTRIBUTING.md`](docs/pipeline/CONTRIBUTING.md) -- ETL
  pipeline and Prefect workflows
- [`docs/webservice/CONTRIBUTING.md`](docs/webservice/CONTRIBUTING.md) --
  FastAPI web service

## Acknowledgement

We'd like to acknowledge the software engineering efforts from the
[University of Washington Scientific Software Engineering Center (SSEC)](https://escience.washington.edu/software-engineering/ssec/),
as part of the
[Schmidt Sciences' Virtual Institute for Scientific Software (VISS)](https://www.schmidtsciences.org/viss/).

## License

This project is licensed under the BSD 3-Clause License. See [LICENSE](LICENSE)
for details.
