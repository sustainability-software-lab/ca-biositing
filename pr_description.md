## 🔬 CA Biositing Audit Platform — Complete System Overview

This PR implements the complete Skill-Based Data Auditor (Phase 1 & 2) as
specified in `plans/skill_based_data_auditor_plan.md`. It serves as an automated
"Bad Data Hunter" — a modular data quality observability pipeline that runs
against the `ca-biositing` PostgreSQL database.

### 🏗️ Architecture

The platform combines three methodologies:

| Layer                 | Tool                                                | Purpose                                                          |
| --------------------- | --------------------------------------------------- | ---------------------------------------------------------------- |
| **Statistical Drift** | [Evidently AI](https://www.evidentlyai.com/)        | Detects distribution shifts, missing values, schema changes      |
| **Hard Assertions**   | [Great Expectations](https://greatexpectations.io/) | Enforces non-null, range, and type rules                         |
| **Semantic Review**   | LLM (Gemini/Claude via `litellm`)                   | Groups anomalies into root-cause hypotheses with priority triage |

The output is a **Data Quality Portal** (Quarto website) and a **Google Sheet
Anomaly Tracker** that a data steward can act on.

### 📁 Key Components

- **Modular Architecture**: Created the `audit` package with a modular Skills
  and Targets architecture.
- **Core Skills**:
  - Statistical Profiling (`ydata-profiling`)
  - Grouped Outlier Detection (Z-score)
  - DQ Assertions (Great Expectations)
  - Semantic Review (`litellm`)
  - Analyst Reporting
  - Anomaly Tracker (Google Sheets integration)
- **Granular Sub-Targets**: Split the monolithic `mv_biomass_composition` view
  into focused sub-targets (`compositional`, `proximate`, `icp`, etc.) that map
  to specific analytical domains.
- **Schema Guard & Golden References**: Added support for frozen CSV snapshots
  of a known-good population state to enable longitudinal drift detection and
  schema validation.
- **AI Sidecar Context System**: Injects domain knowledge into LLM prompts to
  ground the synthesis.
- **Deep Dives & Investigator Skill**: Added tools for targeted investigation of
  specific dimensions (provider, resource, analysis type, temporal drift) and
  interactive DuckDB query helpers.
- **Data Quality Portal**: A Quarto website that visualizes the latest audit
  run, including LLM executive summaries, embedded Evidently AI reports, and
  discovered analysis plots.
- **Environment Integration**: Updated `pixi.toml` with an `auditor`
  environment, dependencies, and tasks.
- **Workflow Orchestration**: Added Prefect flows for scheduled execution.

### 🚀 How to Run

**Prerequisites:**

- Pixi ≥ 0.55 installed
- Docker running (for local database)
- `.env` file with `CBORG_API_KEY`, `AUDITOR_STAGING_DATABASE_URL`, and
  `AUDITOR_ANOMALY_TRACKER_SHEET_KEY`
- `credentials.json` Google Service Account file

**Commands:**

```bash
# Start Local Services
pixi run start-services

# Standard run (all registered targets)
pixi run -e auditor run-auditor

# With per-target Markdown reports
pixi run -e auditor run-auditor-verbose

# With full ydata-profiling HTML reports (slow — run weekly)
pixi run -e auditor run-auditor-profile

# Freeze a new reference
pixi run -e auditor run-auditor --freeze-reference

# Deep Dives
pixi run -e auditor audit-deep-dive --deep-dive provider --value uc_davis
pixi run -e auditor audit-deep-dive --deep-dive resource --value "Almond Hulls"
pixi run -e auditor audit-deep-dive --deep-dive analysis-type --value proximate
pixi run -e auditor audit-deep-dive --deep-dive temporal --target compositional

# Investigator Skill
pixi run -e auditor audit-investigate

# Data Quality Portal
pixi run -e portal generate-portal
pixi run -e portal serve-portal
pixi run -e portal build-portal
```

### ⚙️ Updating Great Expectations Suites

GX suites are JSON files in `audit/expectations/`. To add a new check:

1. Edit the relevant JSON file (e.g.,
   `audit/expectations/mv_biomass_composition.json`)
2. Add an expectation object following the GX expectation gallery
3. Link the suite to a target via `gx_suite_path` in the target definition

### 🌿 Environment Variables Summary

| Variable                            | Required    | Purpose                                                 |
| ----------------------------------- | ----------- | ------------------------------------------------------- |
| `CBORG_API_KEY`                     | ✅ Yes      | LLM synthesis (Gemini/Claude via CBORG proxy)           |
| `AUDITOR_STAGING_DATABASE_URL`      | For staging | PostgreSQL connection string for staging DB             |
| `AUDITOR_ANOMALY_TRACKER_SHEET_KEY` | For Sheets  | Google Sheet ID for anomaly logging                     |
| `POSTGRES_HOST`                     | For local   | Set to `localhost` when running against local Docker DB |
