# CA Biositing Database Audit System

This directory contains a standardized, reproducible audit system for the CA
Biositing project. It is designed to provide a holistic overview of the
database's data quality, coverage, and integrity across AIM1 (analytical) and
AIM2 (processing) domains.

## Directory Structure

- `main.py`: The Python orchestrator that runs the audit using
  `ca_biositing.datamodels` utilities.
- `sql/`: Granular SQL modules for each record type, including lineage and
  quality checks.
- `AGENTS.md`: Specific instructions for AI agents to interpret the audit
  results.
- `REPORT_PROMPT.md`: A template and prompt for generating a comprehensive audit
  report.
- `output/`: (Gitignored) Contains the generated audit artifacts.
  - `audit_data.json`: Structured data for programmatic use.
  - `audit_summary.md`: Compiled raw output for LLM ingestion.

## Usage

### Local Environment

Run the audit against your local Docker-hosted database:

```bash
pixi run audit
```

_Note: This command automatically sets `POSTGRES_HOST=localhost` to connect to
your local services._

### Staging Environment

Run the audit against the Staging database (requires the Cloud SQL Auth Proxy
tunnel to be active):

```bash
pixi run audit-staging
```

## Adding New Audits

To add a new audit check:

1. Create a new `.sql` file in the `sql/` directory.
2. The script will automatically pick it up and include it in the next run.
3. If specific interpretation logic is needed, update `AGENTS.md` and
   `REPORT_PROMPT.md`.
