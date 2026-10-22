---
type: Architecture
title: "How flows are registered and run (master flow, run-single-flow, list-flows)"
description: "Three flow entry points: a hand-kept AVAILABLE_FLOWS dict (32 entries since #514) for the master deployment, scripts/run_flow.py for single flows in the worker, and a legacy runner that no longer works."
tags: [pipeline, prefect, flows, pixi, deploy, orchestration, ordering, registry]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:34Z" }
status: stable
governance: constraint
code_refs: ["resources/prefect/run_prefect_flow.py", "resources/prefect/prefect.yaml", "resources/prefect/deploy.py", "scripts/run_flow.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/*.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/run_pipeline.py", "pixi.toml"]
stale_after: "2026-12-31"
sources: ["pixi.toml", "scripts/run_flow.py", "resources/prefect/run_prefect_flow.py", "docs/pipeline/PREFECT_WORKFLOW.md", "commit 43f3147", "commit fa8583a", "https://github.com/sustainability-software-lab/ca-biositing/pull/380", "commit 5f995e5", "commit f8c9353", "https://github.com/sustainability-software-lab/ca-biositing/pull/514"]
---

## Purpose
Explains how a flow module becomes runnable. There are three mechanisms. Only two work today.

## Key files
| Path:line | Role |
|---|---|
| `resources/prefect/run_prefect_flow.py:8-46` | `AVAILABLE_FLOWS` dict. Hand-maintained. Landiq, billion_ton, field_sample and prepared_sample are commented out (`:22-25`). Infrastructure entries are at `:27-45`. |
| `resources/prefect/run_prefect_flow.py:48-61` | `refresh_materialized_views_task` |
| `resources/prefect/run_prefect_flow.py:63-92` | `master_flow`. Imports each entry, calls it, logs and continues on failure, then refreshes views. |
| `resources/prefect/prefect.yaml` | Deployment `master-etl-deployment`, entrypoint `run_prefect_flow.py:master_flow`, work pool from `$PREFECT_WORK_POOL_NAME`. |
| `resources/prefect/deploy.py` | Runs `prefect deploy` (pixi task `deploy`, `pixi.toml:327-334`). |
| `pixi.toml:135-146` | `run-etl`: `prefect deployment run "Master ETL Flow/master-etl-deployment"` inside `prefect-worker`. |
| `scripts/run_flow.py:15-34` | `list` globs `src/ca_biositing/pipeline/ca_biositing/pipeline/flows/*.py` and prints stems. |
| `scripts/run_flow.py:36-100` | `run <module>`: `docker-compose exec prefect-worker` runs `import ca_biositing.pipeline.flows.<module>`, takes the first `prefect.Flow` in the module `__dict__`, and calls it with no arguments. |
| `pixi.toml:147-150` | Tasks `run-single-flow` and `list-flows`. |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/run_pipeline.py` | Legacy discovery runner. Points at `src/etl/...`, which does not exist. See `bugs/pipeline-stale-legacy-runner-and-templates`. |

## How it works
- Master path: `pixi run deploy` registers the deployment. `pixi run run-etl` starts a run. The worker runs `master_flow`, which imports each `AVAILABLE_FLOWS` entry in order and calls it.
- Single-flow path: `pixi run run-single-flow <module>` does not need registration. It execs in the worker and runs the first `Flow` object found in the module.

## Interfaces
- Flow module naming: module stem = argument to `run-single-flow`, e.g. `landiq_etl`, `railways`.
- Master registry keys are display names, not module names, except for the infrastructure entries, which use the module name.

## Gotchas
- `run-single-flow` picks the first `Flow` in module `__dict__`. Imported flows count. `flows/samples_etl.py:2-3` imports `field_sample_etl_flow` and `prepared_sample_etl_flow`, so `run-single-flow samples_etl` probably runs only the field-sample flow (inferred; confirm by running it).
- `list-flows` lists every `.py` in `flows/`, not only modules that define a flow.
- Adding a flow to the master run means editing `AVAILABLE_FLOWS`. Docs say the same (`docs/pipeline/ETL_WORKFLOW.md`, "Step 3").
- Flow arguments are not passed by `run_flow.py`. Only zero-argument calls work.
- Infrastructure flows run late in the master order (after `thermochem`), so one failing infrastructure flow is logged and the run continues.

## History
- `43f3147` (PR #53): Prefect implementation and flow directory.
- `c46fa7a` (PR #126): "fix prefect flows" after merging branches.
- `fa8583a` (PR #380): biodiesel ETL commented out of the registry.
- `9697eeb` (PR #320): almond ETL module added (`almond_nsjv` is present in the registry today).
- `5f995e5` (2026-05-26): registry changes around biodiesel.
- f8c9353 (PR #514, 2026-10-22): 18 infrastructure entries added; biodiesel re-enabled.

## Open questions
- Whether `run_pipeline.py` should be deleted. No pixi task or doc references it (inferred from grep).

## Merged detail: Master ETL registry: which flows run and in what order

**Purpose**
The Master ETL Flow (`master_flow`) runs every enabled sub-flow in the order of the `AVAILABLE_FLOWS` dict, catches and logs each failure, then refreshes materialized views.

**Key files**

| Path:line | Role |
|---|---|
| resources/prefect/run_prefect_flow.py:8-46 | `AVAILABLE_FLOWS`, with the comment "THE ORDER MATTERS" |
| resources/prefect/run_prefect_flow.py (master_flow) | Imports each module, calls `flow_func()`, catches exceptions per flow |
| resources/prefect/run_prefect_flow.py (refresh_materialized_views_task) | Runs `refresh_all_views` after all flows |
| scripts/run_flow.py | Runs one flow by module name inside the worker container |

**Enabled order (current, a2c8de8)**
geography, primary_ag_product, analysis_type, residue_factors, resource_information, county_ag_report, static_resource_info, samples, usda_etl, almond_nsjv, qualitative, analysis_records, aim2_bioconversion, thermochem; then the 18 infrastructure flows: biodiesel_plants, tomato_processors, food_manufacturers_carb, food_manufacturers_epa, crude_oil_pipelines, railways, petroleum_pipelines, biosolids_facilities, cafo_manure_locations, combustion_plants, district_energy_systems, ethanol_biorefineries, food_processing_facilities, landfills, livestock_anaerobic_digesters, msw_to_energy_anaerobic_digesters, saf_and_renewable_diesel_plants, wastewater_treatment_plants.

Commented out: landiq, billion_ton, field_sample, prepared_sample. Field and prepared samples still run through `samples`.

**Gotchas**
- residue_factors runs before resource_information. Residue rows need Resource rows (see flow-residue-factors-flow), so a fresh DB loses them (inferred; confirm).
- Errors are caught per sub-flow, so a broken sub-flow shows as a logged exception, not a failed master run.
- `scripts/run_flow.py` (python one-liner in run_flow) takes the first Prefect `Flow` in a module, which can pick the wrong flow for modules that import other flows (samples_etl).

**History**
- Dates: registry changes in 5f995e5 (2026-05-26, biodiesel disabled), fa8583a (PR #380), and f8c9353 (PR #514, 2026-10-22, 18 infrastructure entries).

**Open questions**
- Why are landiq and billion_ton disabled? Not recorded in code.

# Related Concepts
- [System overview (start here)](system-overview.md): Where orchestration sits in the overall system.
- [How a pipeline flow wires extract, transform, and load](pipeline-flow-wiring.md): What the registered flows contain.
- [Legacy run_pipeline.py and extract template reference removed paths](../bugs/pipeline-stale-legacy-runner-and-templates.md): The legacy runner described here is broken.
- [Pipeline package layout and ETL layers](pipeline-package-layout.md): Master flow is the scheduler-level counterpart of the per-flow concepts
- [Residue Factors ETL flow (Residue Factors sheet to residue_factor)](flow-residue-factors-flow.md): Order constraint: residue factors must run after resource information
- [Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern](pipeline-infrastructure-etl-family.md): the 18 infrastructure registry entries
