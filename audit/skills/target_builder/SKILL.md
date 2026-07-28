# Target Building Skill

This skill allows agents to generate ephemeral audits for off-the-cuff data
exploration by creating dynamic ad-hoc target files.

## Overview

The audit system supports dynamic discovery of targets placed in the
`audit/targets/adhoc/` directory. This allows for rapid prototyping and
investigation of specific data quality concerns without modifying the core
registry.

## How to use

1.  **Identify the need**: Determine what specific data or relationship you want
    to audit (e.g., "variance in forest residue moisture").
2.  **Generate a target file**: Create a new Python file in
    `audit/targets/adhoc/` (e.g., `audit/targets/adhoc/forest_moisture.py`).
3.  **Define the `AuditTarget`**:
    - Use `from audit.targets.registry import AuditTarget, register`.
    - Define an `AuditTarget` instance with unique `name`, `population_sql` (for
      reference/baseline), `observation_sql` (for current data), and relevant
      columns.
    - Call `register(target)`.
4.  **Run the audit**: Use the auditor agent with the specific target name.
    ```bash
    pixi run -e auditor python audit/agent.py --targets adhoc_forest_residue_moisture
    ```

## Example Blueprint

```python
from audit.targets.registry import AuditTarget, register

target = AuditTarget(
    name="adhoc_custom_check",
    source_type="view",
    description="My custom investigation",
    population_sql="SELECT ...",
    observation_sql="SELECT ...",
    group_by_cols=["col1", "col2"],
    numeric_cols=["val"],
    id_cols=["record_id"]
)

register(target)
```

## Maintenance

Ad-hoc targets are intended to be ephemeral. Delete them once the investigation
is complete or promote them to the main registry if they provide long-term
value.
