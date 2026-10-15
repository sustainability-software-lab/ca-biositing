# Repository Map

**Load when:** you need to know what this repository is, where a file lives, or
what CI runs against it.

## Repository Overview

This is the **ca-biositing** repository, a geospatial bioeconomy project for
biositing analysis in California. It provides tools for ETL (Extract, Transform,
Load) pipelines to process data from Google Sheets into PostgreSQL databases,
geospatial analysis using QGIS, a REST API for data access, and research
prototyping for bioeconomy site selection.

**Repository Stats:**

- **Type:** Research project / Data processing / Geospatial analysis
- **Architecture:** PEP 420 namespace packages
- **Build System:** Pixi (v0.55.0+) + Docker for ETL pipeline orchestration
- **Platform:** macOS (osx-arm64, osx-64), Linux (linux-64, linux-aarch64),
  Windows (win-64)
- **Languages:** Python (primary), SQL, TOML, Jupyter Notebooks
- **Domain:** Geospatial analysis, bioeconomy, ETL pipelines, database
  management

**Key Components:**

- **`ca_biositing.datamodels`**: Hand-written SQLModel database models with
  Alembic migrations. Models are in `models/` subdirectories, views in
  `data_portal_views/`.
- **`ca_biositing.pipeline`**: Prefect-orchestrated ETL workflows
  (Docker-based).
- **`ca_biositing.webservice`**: FastAPI REST API.
- **`resources/`**: Docker Compose and Prefect deployment configuration.
- **`frontend/`**: Git submodule for frontend application.

## Project Structure & Package Overviews

### `src/ca_biositing/datamodels`

The core data layer.

- `ca_biositing/datamodels/models/`: Hand-written SQLModel classes (91 models,
  15 domain subdirectories).
- `ca_biositing/datamodels/views.py`: Materialized view definitions.
- `ca_biositing/datamodels/database.py`: Connection and session management.
- See
  [`src/ca_biositing/datamodels/README.md`](../../src/ca_biositing/datamodels/README.md).

### `src/ca_biositing/pipeline`

The ETL orchestration layer.

- `ca_biositing/pipeline/etl/`: Extract, Transform, and Load tasks.
- `ca_biositing/pipeline/flows/`: Prefect flow definitions.
- `ca_biositing/pipeline/utils/`: Helpers like `gsheet_to_pandas.py` and
  `lookup_utils.py`.
- See
  [`src/ca_biositing/pipeline/README.md`](../../src/ca_biositing/pipeline/README.md).

### `src/ca_biositing/webservice`

The API layer.

- `ca_biositing/webservice/main.py`: FastAPI application entrypoint.
- `ca_biositing/webservice/v1/endpoints/`: API route handlers.
- See
  [`src/ca_biositing/webservice/README.md`](../../src/ca_biositing/webservice/README.md).

## Agent Harness

```text
.
├── AGENTS.md              # Agent entry point: non-negotiables and the rule index
├── CLAUDE.md              # `@AGENTS.md` import; every package AGENTS.md has one too
├── .agents/
│   ├── rules/             # On-demand rules indexed by AGENTS.md
│   └── skills/            # Project skills (committed) and synced third-party skills (ignored)
├── .claude/
│   └── skills -> ../.agents/skills   # Symlink so Claude Code discovers the skills
├── knowledge/             # OKF project memory, read and written with `pixi run okf` (okf-memory skill)
├── .devcontainer/         # Codespaces image: pixi (checksum-verified) + Claude Code, Codex, Copilot CLI, OpenCode, gh
├── .github/workflows/copilot-setup-steps.yml   # Copilot cloud agent setup: locked pixi env, warm pre-commit hooks
├── skills.json            # Third-party agent skills synced by `pixi run skills-sync`
├── skills.py              # The sync script behind `pixi run skills-sync`
└── tests/agent_harness/   # Invariant tests for the harness (run in CI)
```

## Continuous Integration & Validation

| Workflow                                        | Runs on                                                                                                          | What it does                                                                                                       |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `ci.yml`                                        | PRs, pushes to `main`                                                                                            | Tests datamodels, pipeline, and webservice (Python 3.12/3.13 on Ubuntu and macOS) and the agent-harness invariants |
| `cd.yml`                                        | PRs and pushes touching the three packages, releases                                                             | Builds the package distributions and publishes them to TestPyPI                                                    |
| `docker-build.yml`                              | Pushes to `main` touching `src/`, `deployment/`, `resources/docker/`, `pixi.toml`, or `pixi.lock`; releases; PRs | Builds and pushes the Docker images                                                                                |
| `deploy-staging.yml`                            | A successful image build on `main`; PRs (preview)                                                                | Deploys to GCP staging                                                                                             |
| `deploy-production.yml`                         | An image build triggered by a release; pushes touching infrastructure or `pixi.toml` (Pulumi preview only)       | Deploys to GCP production                                                                                          |
| `migrations.yml`                                | PRs touching `alembic/`, the datamodels package, or Pixi files                                                   | Tests the Alembic migrations                                                                                       |
| `trigger-etl.yml`, `trigger-etl-production.yml` | A completed deploy                                                                                               | Triggers the ETL pipeline when ETL code changed                                                                    |
| `gh-pages.yml`                                  | Changes to the resource-info assets                                                                              | Validates them and publishes to GitHub Pages                                                                       |
| `copilot-setup-steps.yml`                       | Changes to itself                                                                                                | Prepares the GitHub Copilot cloud agent's environment                                                              |

[pre-commit.ci](https://pre-commit.ci) runs the pre-commit hooks on pull
requests (see the badge in `README.md`), and Dependabot updates GitHub Actions
weekly.

## Further Reading

For more information on SSEC best practices, see:
<https://rse-guidelines.readthedocs.io/en/latest/llms-full.txt>
