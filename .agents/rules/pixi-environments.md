# Pixi Environments & Dependencies

**Load when:** setting up the repository, running any command, adding or
changing a dependency, editing `pixi.toml`, or touching `pixi.lock`.

## Pixi Overview

This project uses **Pixi** for local development environment and dependency
management. Pixi handles both Conda and PyPI dependencies. See
<https://pixi.sh/latest/llms-full.txt> for details.

**ALWAYS use Pixi commands — never use conda, pip, or venv directly for local
development.**

The ETL pipeline runs in Docker containers orchestrated by Pixi tasks. Pixi is
used for:

- Managing Docker services (start, stop, logs, status)
- Running code quality tools (pre-commit)
- Running tests (pytest)
- Running QGIS for geospatial analysis
- Deploying and running Prefect workflows
- Starting the FastAPI web service
- Managing agent skills (installing, syncing, updating)

## Environment Setup (ALWAYS RUN FIRST)

```bash
# Install the default environment (required before any other commands)
pixi install
```

**CRITICAL:** Always run `pixi install` before any other Pixi commands. It is
idempotent and safe to repeat.

## Available Environments

| Environment      | Features                                                | Use for                                                       |
| ---------------- | ------------------------------------------------------- | ------------------------------------------------------------- |
| `default`        | `datamodels`, `pipeline`, `webservice`, `kernel`, `gis` | Main development: the three packages, notebooks, tests        |
| `py312`, `py313` | The three packages on Python 3.12 or 3.13               | The CI test matrix                                            |
| `gis`            | `qgis`, `raster`, `vector`, `kernel`                    | Geospatial analysis (QGIS, rasterio, xarray, shapely, pyproj) |
| `etl`            | `datamodels`, `pipeline`                                | The ETL pipeline; the pipeline Docker image installs it       |
| `webservice`     | `datamodels`, `webservice`                              | The FastAPI service; the web service Docker image installs it |
| `frontend`       | `frontend`                                              | Frontend development (Node.js, npm)                           |
| `docs`           | `datamodels`, `pipeline`, `docs`                        | The MkDocs site                                               |
| `deployment`     | `cloud`                                                 | Cloud infrastructure (Pulumi, gcloud)                         |
| `viz`            | `datamodels`, `visualization`, `kernel`                 | The visualization gallery and plots                           |

## Channels

Conda packages resolve from the `conda-forge` channel only. Do not add channels.
The SSEC project template has moved to the `https://prefix.dev/conda-forge`
mirror; switching here would re-solve the whole lock file, so it is a separate
change.

## Lock File Compatibility (CRITICAL)

`pixi.lock` uses lock-file format **v6**. CI, the deploy workflows, both Docker
images (`resources/docker/*.dockerfile`), the devcontainer, and the Copilot
setup workflow pin pixi releases older than 0.68.0, which cannot read the v7
format that pixi 0.68.0 and later write. A newer pixi rewrites `pixi.lock` as v7
whenever it re-solves — `pixi add`, `pixi remove`, `pixi update`, or `pixi lock`
— and CI and the Docker builds then fail or silently re-solve.

- Check `pixi --version` before any command that changes dependencies.
- With pixi 0.68.0 or later, do not run `pixi add`, `pixi remove`,
  `pixi update`, or `pixi lock`. A dependency change first needs every pinned
  pixi upgraded to the same release and the lock migrated to v7, in its own pull
  request.
- `pixi install` and `pixi run` leave an up-to-date `pixi.lock` alone, and
  adding or editing a task in `pixi.toml` does not change it.
- `tests/agent_harness/test_lockfile.py` fails when the lock-file format
  outgrows a pinned pixi.

## Adding Dependencies

Only with a pixi that every pin can follow (see above):

```bash
pixi add <package-name>                         # conda package
pixi add --pypi <package-name>                  # PyPI package
pixi add --feature <feature-name> <package-name>  # into one feature
pixi install                                    # after manual pixi.toml edits
```

Every new dependency needs a justification — see
[contribution-discipline.md](contribution-discipline.md).

## GitHub CLI

The GitHub CLI (`gh`) is not a Pixi dependency in this repository. Install it
from <https://cli.github.com> and run `gh auth login` once.

## OKF Agent Memory

Project memory lives in the OKF bundle at `knowledge/`; the `okf-memory` skill
says how to read and write it. The `okf` CLI is not a Pixi dependency here: the
`okf` task runs it through `pixi exec`, which fetches
`okf-agent-memory>=0.5.0,<0.6` into a cached temporary environment, so
`pixi.lock` stays unchanged. Once every pinned pixi is upgraded (see Lock File
Compatibility), move it into a Pixi feature, as the SSEC template does.

```bash
pixi run okf version   # okf version 0.5.x (OKF v0.2 specification)
pixi run okf --help
```

## Jupyter Notebooks

This project uses [pixi-kernel](https://github.com/renan-r-santos/pixi-kernel)
for Jupyter integration. The kernel runs code inside the Pixi environment, so
all installed packages are available without any path configuration.

1. Run `pixi install` to set up the environment (includes `pixi-kernel`).
2. In VS Code or JupyterLab, select the **Pixi** kernel for your notebook.
3. All `ca_biositing` namespace packages are importable directly.

## Validated Commands

### Docker Operations

- `pixi run start-services`: Start DB and Prefect.
- `pixi run service-status`: Check container health.
- `pixi run service-logs`: View logs.
- `pixi run rebuild-services`: Rebuild images after dependency changes.

### Development & Quality

- `pixi run pre-commit-all`: Run all checks (MANDATORY before PR).
- `pixi run test`: Run pytest suite.
- `pixi run start-webservice`: Launch API locally.
- `pixi run skills-sync`: Synchronize agent skills from `skills.json`.

### ETL Flow Management

- `pixi run list-flows`: List all available Prefect flows in the project.
- `pixi run run-single-flow <module_name>`: Run a specific flow by its module
  name (e.g., `pixi run run-single-flow landiq_etl`).
- `pixi run update-static-resource-info`: Trigger the `static_resource_info` ETL
  flow, update local JSON assets, and validate headers. Use this to propagate
  changes from Google Sheets to the local application assets.
