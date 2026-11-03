---
type: Architecture
title: Samples ETL wrapper flow (field samples then prepared samples)
description: Thin wrapper that runs field_sample_etl_flow then prepared_sample_etl_flow in order; run-single-flow resolves the wrong flow in this module (inferred).
tags: [pipeline, etl, flow, samples, orchestration]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:08Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/samples_etl.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/field_sample_etl.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/prepared_sample_etl.py", "scripts/run_flow.py"]
sources: ["commit dc98b30", "https://github.com/sustainability-software-lab/ca-biositing/pull/108", "resources/prefect/run_prefect_flow.py"]
governance: constraint
stale_after: "2026-12-31"
---

**Purpose**
Orchestrates the two sample-tracking flows in dependency order: field samples first, then preparations, which reference field samples.

**Key files**

| Path:line | Role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/samples_etl.py:5-6 | `@flow(name="Samples ETL")` `samples_etl_flow()` |
| flows/samples_etl.py:2-3 | Imports `field_sample_etl_flow` and `prepared_sample_etl_flow` at module level |
| flows/samples_etl.py:15, 18 | Calls the two sub-flows directly (no separate deployment) |

**How it works**
Sequential calls: `field_sample_etl_flow()` then `prepared_sample_etl_flow()`. Each sub-flow creates its own lineage record. No shared lineage group is passed.

**Interfaces**
- Callers: master registry key `samples` (run_prefect_flow.py:17), and `pixi run run-single-flow samples_etl`.
- Depends on: flow-field-sample-etl and flow-prepared-sample-etl.

**Gotchas**
- `resources/docker` run_flow.py picks the first `Flow` object in the module namespace (scripts/run_flow.py, python one-liner). Because the two sub-flow imports come first, `run-single-flow samples_etl` will likely run field_sample_etl_flow only (inferred from dict order; confirm by running `pixi run run-single-flow samples_etl` and checking the Prefect run name).
- Sub-flow failures propagate, so prepared samples do not run if field samples raise.

**History**
- dc98b30 (2026-02-11, PR #108 SQL-first): wrapper introduced.
- https://github.com/sustainability-software-lab/ca-biositing/pull/108

**Open questions**
- Fix option: move the wrapper flow to the top of the module or rename imports to `_`-prefixed names so run_flow selects the right flow (not implemented).

# Related Concepts
- [System overview (start here)](system-overview.md): Sample tracking is one of the pipeline’s core ingest paths
- [Prepared Sample ETL flow (Google Sheet 02-Preparation to prepared_sample)](flow-prepared-sample-etl.md): Runs prepared_sample after field samples
- [Field Sample ETL flow (four-worksheet join)](flow-field-sample-etl.md): Runs first; preparations depend on its FieldSample rows
