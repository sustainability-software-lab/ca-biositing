# Contributing to CA Biositing

Thank you for your interest in contributing to **CA Biositing**! This guide
provides step-by-step instructions to set up the project locally. Follow these
guidelines to get started.

Read our
[Code of Conduct](https://github.com/uw-ssec/code-of-conduct/blob/main/CODE_OF_CONDUCT.md)
to keep our community approachable and respectable.

## Pull Requests

We welcome contributions! Please follow these guidelines when submitting a Pull
Request:

- It may be helpful to review
  [this tutorial](https://www.dataschool.io/how-to-contribute-on-github/) on how
  to contribute to open source projects. A typical task workflow is:
  - [Fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo) the
    code repository specified in the task and
    [clone](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)
    it locally.
  - Review the repo's README.md and CONTRIBUTING.md files to understand what is
    required to run and modify this code.
  - Create a branch in your local repo to implement the task.
  - Commit your changes to the branch and push it to the remote repo.
  - Create a pull request, adding the task owner as the reviewer.

- Please follow the
  [Conventional Commits](https://github.com/uw-ssec/rse-guidelines/blob/main/conventional-commits.md)
  naming for pull request titles.

Your contributions make this project better—thank you for your support! 🚀

## Development

### General Workflow

1. Set up your development environment with `pixi install`.
2. Install pre-commit hooks with `pixi run pre-commit-install`.
3. Create a feature branch.
4. Make your changes and ensure tests and pre-commit checks pass. . Submit a
   pull request.

### Configuring Pre-commit

PRs will fail style and formatting checks as configured by
[pre-commit](https://pre-commit.com/), but you can set up your local repository
such that precommit runs every time you commit. This way, you can fix any errors
before you send out pull requests!!

To do this, install [Pixi](https://pixi.sh/latest/) using either the
[instructions on their website](https://pixi.sh/latest/#installation), or the
commands below:

**macOS/Linux:**

```bash
curl -fsSL https://pixi.sh/install.sh | sh
```

**Windows:**

```powershell
powershell -ExecutionPolicy ByPass -c "irm -useb https://pixi.sh/install.ps1 | iex"
```

#### Configure Pre-commit to run on every commit

Then, once Pixi is installed, run the following command to set up pre-commit
checks on every commit

```
pixi run pre-commit-install
```

#### Manually run pre-commit on non-committed files

```
pixi run pre-commit
```

#### Manually run pre-commit on all files

```
pixi run pre-commit-all
```

#### Available Pixi Environments

| Environment  | Purpose                                                   |
| ------------ | --------------------------------------------------------- |
| `default`    | General development, testing, and pre-commit hooks        |
| `py312`      | Pin to Python 3.12 for cross-version testing              |
| `py313`      | Pin to Python 3.13 for cross-version testing              |
| `gis`        | Adds QGIS, rasterio, shapely, and geospatial tools        |
| `etl`        | ETL pipeline dependencies (used inside Docker containers) |
| `webservice` | FastAPI service dependencies                              |
| `frontend`   | Node.js/npm for the React/Next.js frontend                |
| `docs`       | MkDocs and documentation-build tools                      |
| `deployment` | Google Cloud CLI, Pulumi, and infrastructure tools        |

Each environment is a distinct dependency set — same Python/conda base,
different packages installed on top. To activate an environment:

```bash
pixi shell -e <environment>
```

### Database and Model Development

This project uses **SQLModel** for database models and **Alembic** for
migrations. Models are hand-written classes organized in
`src/ca_biositing/datamodels/ca_biositing/datamodels/models/`.

#### Making Schema Changes

1. Edit or add SQLModel classes in the appropriate `models/` subdirectory.
2. If adding a new model, re-export it in `models/__init__.py`.
3. Ensure services are running: `pixi run start-services`.
4. Auto-generate a migration:
   ```bash
   pixi run migrate-autogenerate -m "Description of changes"
   ```
5. Review the generated migration in `alembic/versions/`.
6. Apply the migration:
   ```bash
   pixi run migrate
   ```

#### Refreshing Materialized Views

After loading new data into the database, refresh the analytical views:

```bash
pixi run refresh-views
```

#### Importing Models

All models are re-exported from `ca_biositing.datamodels.models`:

```python
from ca_biositing.datamodels.models import Resource, FieldSample, Place
```

### Running Tests

This project uses [pytest](https://pytest.org/) as its testing framework. You
can execute the following command to run the full test suite:

```bash
pixi run test
```

This command executes `python -m pytest tests/ --verbose`, which:

- Runs all tests in the `tests/` directory.
- Prints the name of each test as it runs (`--verbose`).

For a coverage report, use `pixi run test-cov` instead.

#### Running Tests with Coverage

To run tests with coverage, use the following command

```bash
pixi run test-cov
```

This will run tests with coverage and generate an html report of said coverage.
