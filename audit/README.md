# Skill-Based Data Auditor

The Skill-Based Data Auditor is a modular, extensible system for performing data
quality analysis and observability on the `ca-biositing` dataset. It utilizes a
"Two-Layer Audit Model" to compare individual observations against population
statistics.

## Overview

- **Layer 1: Population Statistics**: Group-level stats (mean, std dev, count)
  typically sourced from materialized views.
- **Layer 2: Individual Observation Audit**: Raw records queried from public
  schema tables to identify specific anomalies.

The system is organized into **Skills** (modular analysis logic) and **Targets**
(declarative data definitions).

---

## The 5 Core Skills

1.  **📊 Statistical Profiling**: Generates comprehensive dataset summaries and
    HTML reports using `ydata-profiling`.
2.  **📍 Grouped Outlier Detection**: Identifies anomalous individual
    observations using within-group Z-scores (e.g., comparing almond hull
    moisture only against other almond hull samples).
3.  **✅ Data Quality Assertions**: Executes hard validation rules (non-null,
    value ranges) using Great Expectations (GX).
4.  **🧠 Semantic Review**: Leverages LLMs (Gemini/Claude) via `litellm` to
    provide natural language assessments and possible causes for detected
    anomalies.
5.  **📝 Analyst Reporting**: Consolidates all findings into a structured,
    human-readable Markdown narrative.

---

## How-to Guides

### Run the Auditor

**Prerequisites:**

- Local Docker database services must be running (`pixi run start-services`).
- `GOOGLE_API_KEY` (for Gemini) or `ANTHROPIC_AUTH_TOKEN` (for CBORG/Claude)
  must be set in your environment.

**Via Pixi:**

```bash
# Run all registered audit targets
POSTGRES_HOST=localhost pixi run -e auditor run-auditor
```

**Via Prefect:** The auditor is available as a Prefect flow for automated
scheduling:

```python
from ca_biositing.pipeline.flows.data_audit_flow import data_quality_audit_flow
data_quality_audit_flow()
```

### Expand with New Targets

To audit a new view or table, create a new registration file in
`audit/targets/views/` (or `tables/`):

1.  **Define the AuditTarget**:

    ```python
    from audit.targets.registry import AuditTarget, register

    register(AuditTarget(
        name="my_new_view",
        source_type="view",
        description="Description of the target",
        population_sql="SELECT ...", # Layer 1 stats
        observation_sql="SELECT ...", # Layer 2 records
        group_by_cols=["resource_name", "parameter_name"],
        numeric_cols=["observed_value"],
        id_cols=["record_id"]
    ))
    ```

2.  **Register the Module**: Add `from . import my_new_view` to
    [`audit/targets/views/__init__.py`](audit/targets/views/__init__.py).

### Expand with New Skills

1.  Create a new Python module in `audit/skills/`.
2.  Implement your analysis logic (taking a DataFrame and returning a result
    object).
3.  Integrate the skill into the `run()` loop in
    [`audit/agent.py`](audit/agent.py).

---

## Reference

### Key Audit Targets

- **`mv_biomass_composition`**: The standard baseline audit for all AIM1
  compositional data.
- **`mv_biomass_composition_extended`**: An extended audit that groups data by
  `provider_codename` and includes `collection_timestamp` and `harvest_date`.
  Use this to find provider-specific drift or temporal anomalies.

### Outputs

Every run creates a timestamped directory in
`audit/output/YYYY-MM-DD_HH-MM-SS/`:

| File                     | Description                                        |
| :----------------------- | :------------------------------------------------- |
| `full_audit_report.md`   | The primary human-readable narrative.              |
| `flagged_<target>.csv`   | Machine-readable list of all outlier observations. |
| `profiles/<target>.html` | Detailed interactive profiling report.             |
| `report_<target>.md`     | Individual target summary.                         |
