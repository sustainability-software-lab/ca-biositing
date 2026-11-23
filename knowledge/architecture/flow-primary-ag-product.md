---
type: Architecture
title: Primary Ag Product ETL flow (basic sample info to primary_ag_product)
description: Derives unique primary agricultural product names from the 01-BasicSampleInfo sheet and inserts new lowercase names into primary_ag_product; early in the master order.
tags: [pipeline, etl, flow, reference-data, google-sheets]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:06Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/primary_ag_product.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/basic_sample_info.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/products/primary_ag_product.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/products/primary_ag_product.py"]
sources: ["commit a9a86eb", "https://github.com/sustainability-software-lab/ca-biositing/pull/84", "AGENTS.md"]
governance: context
stale_after: "2026-12-31"
---

**Purpose**
Builds the `primary_ag_product` lookup table, which many other flows use to resolve crop names to IDs (resource, static_resource_info, USDA commodity sync). Dedupe is case-insensitive.

**Key files**

| Path:line | Role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/primary_ag_product.py:6-7 | `@flow(name="Primary Ag Product ETL")` `primary_ag_product_flow()` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/basic_sample_info.py:7-8 | GSheet `Aim 1-Feedstock Collection and Processing Data-BioCirV`, worksheet `01-BasicSampleInfo` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/products/primary_ag_product.py:7 | `transform`: lowercases columns, requires `primary_ag_product` column, returns unique `name` DataFrame |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/products/primary_ag_product.py:8 | `load`: inserts names not already present (case-insensitive) |

**How it works**
extract -> transform (dict keyed `basic_sample_info`) -> load. No lineage record is created in this flow.

**Interfaces**
- Input: GSheet tab `01-BasicSampleInfo`.
- Output: `primary_ag_product.name` (lowercased, stripped).
- Callers: master registry (run_prefect_flow.py:10, enabled); `static_resource_info` and `usda_etl` assume these rows exist.

**Gotchas**
- The transform mutates the input DataFrame’s column names in place (transform line 17-18).
- Load uses `from ca_biositing.datamodels.database import engine` at module level (load/products/primary_ag_product.py:3). This conflicts with the repo rule to lazy-import DB objects in tasks to avoid Docker import hangs (root AGENTS.md). Importing the flow module therefore touches the DB engine (inferred; confirm whether create_engine connects eagerly).
- No lineage columns are written, unlike most flows.

**History**
- a9a86eb (2026-02-05, PR #84): flow added with Berkeley Upstream integration.
- https://github.com/sustainability-software-lab/ca-biositing/pull/84

**Open questions**
- Should lineage (etl_run_id, lineage_group_id) be recorded for this table? Not verified whether the table has those columns.

# Related Concepts
- [System overview (start here)](system-overview.md): Reference-data flow that other flows depend on for crop names
- [Resource Information ETL flow (resources, then resource images)](flow-resource-information.md): Resource transform normalizes primary_ag_product names to IDs, so this flow must load first
- [USDA Census and Survey ETL flow (NASS Quick Stats to observations)](flow-usda-etl.md): USDA commodity sync requires populated primary_ag_product and resource tables
