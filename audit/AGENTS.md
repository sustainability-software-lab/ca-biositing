# Instructions for AI Agents: CA Biositing Database Audit

You are a data quality and database integrity specialist. You will be provided
with raw data from the `audit` system of the `ca-biositing` repository.

## Running the Audit

If you are asked to "run the audit" yourself as an agent:

1. Ensure the database is accessible (either local Docker services or staging
   via Cloud SQL Auth Proxy).
2. Ensure the `.env` file is properly configured with `CBORG_API_KEY`,
   `AUDITOR_STAGING_DATABASE_URL`, and `AUDITOR_ANOMALY_TRACKER_SHEET_KEY`.
3. Run the audit using:
   `POSTGRES_HOST=localhost pixi run -e auditor run-auditor`.
4. After execution, read the results from the latest timestamped directory in
   `audit/output/` (e.g.,
   `audit/output/YYYY-MM-DD_HH-MM-SS/full_audit_report.md`).

## Goal

The Skill-Based Data Auditor is an automated pipeline. Your goal as an agent is
typically to **maintain, extend, or troubleshoot** this pipeline, rather than
manually interpreting raw SQL results. The pipeline itself handles outlier
detection, data quality assertions, and LLM-powered semantic review.

## Extending the Auditor

If asked to add new checks or targets:

1. **New Targets**: Define a new `AuditTarget` in `audit/targets/views/` or
   `audit/targets/tables/` and register it in the corresponding `__init__.py`.
2. **New Skills**: Create a new Python module in `audit/skills/` and integrate
   it into the `run()` loop in `audit/agent.py`.
3. **Great Expectations**: To add hard data quality rules, create a new JSON
   expectation suite in `audit/expectations/` and link it to the target via the
   `gx_suite_path` attribute. See `agent_docs/gx_alignment_strategy.md` for the
   strategy on aligning GX with SQL view filters.
