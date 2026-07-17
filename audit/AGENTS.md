# Instructions for AI Agents: CA Biositing Database Audit

You are a data quality and database integrity specialist. You will be provided
with raw data from the `audit` system of the `ca-biositing` repository.

## Phase 2 Architecture

The Audit Platform has been refined in Phase 2 to provide granular observability
and AI-assisted investigation.

### 1. Granular Sub-Targets

Audit targets are now split into specialized sub-targets to improve detection
precision:

- **Analysis Type**: Focuses on specific analysis types that determine the
  biomsas compositon or conversion potential
- **Provider-Specific**:

### 2. Schema Guard & Golden References

- **Schema Guard**: Automatically detects schema drift in incoming data sources.
- **Golden References**: Located in `audit/references/`, these are static
  population snapshots used for longitudinal drift analysis. Use
  `--freeze-reference` to update them.

### 3. AI Sidecar Context System

Found in `audit/targets/context/`, this system provides the LLM with
domain-specific metadata (e.g., "Expected moisture range for almond hulls is
10-15%") to ground the Semantic Review.

### 4. Ad-Hoc Target Factory

The `audit/targets/adhoc/` directory contains templates for generating temporary
audit targets. This allows for rapid investigation of suspected issues without
permanent registration.

## Running the Audit

1. Ensure the database is accessible (local or staging).
2. Ensure `.env` is configured (`CBORG_API_KEY`, `AUDITOR_STAGING_DATABASE_URL`,
   `AUDITOR_ANOMALY_TRACKER_SHEET_KEY`).
3. Run: `pixi run -e auditor run-auditor`.

## Extending the Auditor

- **New Targets**: Define in `audit/targets/views/` or `audit/targets/tables/`.
- **Updating GX Suites**: Edit the JSON files in `audit/expectations/`. Suites
  should align with the SQL view logic.
- **New Skills**: Implement in `audit/skills/` and register in `audit/agent.py`.
