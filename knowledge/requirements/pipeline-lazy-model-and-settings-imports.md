---
type: Requirement
title: Import models and settings inside task or flow bodies
description: "Pipeline tasks and flows must import SQLAlchemy models, datamodels settings, and engines inside function bodies to avoid Docker import hangs; several modules violate this today."
tags: [pipeline, requirement, imports, docker, prefect]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:52Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/**", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/**", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/engine.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lineage.py"]
sources: ["src/ca_biositing/pipeline/AGENTS.md", "AGENTS.md", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/templates/load_template.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/templates/transform_template.py"]
governance: constraint
---

## Requirement
Inside `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/**` and `src/ca_biositing/pipeline/ca_biositing/pipeline/flows/**`, import `ca_biositing.datamodels.models`, `ca_biositing.datamodels.config`, and engine objects inside the `@task` or `@flow` body, not at module level.

## Source
- `src/ca_biositing/pipeline/AGENTS.md` ("Docker Hangs & Deadlocks"; "Lazy Loading").
- Root `AGENTS.md` (Common Pitfalls, CRITICAL).
- Templates: `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/templates/transform_template.py:42` and `load_template.py:32` ("CRITICAL: Lazy import models ... Docker import hangs").
- Compliant examples: `etl/load/prepared_sample.py:33`, `etl/transform/prepared_sample.py:38-43`, `utils/lineage.py:13,47`.

## Verified violations (module-level)
- `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lineage.py:6` imports `engine`. Eight flows import lineage at top level (`usda_etl`, `biodiesel_plants`, `field_sample_etl`, `prepared_sample_etl`, `residue_factors_flow`, `resource_information`, `static_resource_info`, `county_ag_report_etl`).
- `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/{xrd,xrf,icp,calorimetry}_record.py` import `engine` from `utils/engine` at top level.
- `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/analysis_type.py:3-5` and `products/primary_ag_product.py:3-5` import models at top level.
- `src/ca_biositing/pipeline/ca_biositing/pipeline/flows/field_sample_etl.py:13` imports `engine` at top level.

## Why it matters
Top-level engine construction loads `datamodels.config.settings` (reads `.env`) on import. The repo docs say this caused hangs in Docker. The git history does not contain a commit that documents the hang itself (grep for hang/deadlock found none). Governance is set to constraint because the repo treats this as a hard rule, but the root cause is not recorded here.

## How to comply
Use `get_engine()` inside the task, or import the module inside the function body.

## Open questions
- Whether the listed violations are benign in practice (inferred: `create_engine` does not connect until used, so no network I/O at import). Confirm by timing `python -c "import ca_biositing.pipeline.flows.usda_etl"` in the worker.

# Related Concepts
- [Database engines and DATABASE_URL host rewriting](../architecture/pipeline-engine-and-db-url.md): Where the module-level engine lives.
- [ETL run and lineage group tracking](../architecture/pipeline-lineage-tracking.md): Module-level engine import in lineage.py.
- [Test suite layout, how to run each suite, and fixture map](../architecture/testing.md): Tests import these modules and would reveal import-time issues.
