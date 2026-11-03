---
type: Architecture
title: Residue Factors ETL flow (Residue Factors sheet to residue_factor)
description: "Upserts residue yield factors keyed by (resource_id, factor_type); rows whose resource is not yet loaded are dropped, so it must run after resource_information."
tags: [pipeline, etl, flow, residue, google-sheets, ordering]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:07Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/residue_factors_flow.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/residue_factors.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource_information/residue_factor.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/resource_information/residue_factor.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lineage.py", "resources/prefect/run_prefect_flow.py"]
sources: ["commit 99cbfcd", "commit 543adde", "https://github.com/sustainability-software-lab/ca-biositing/pull/288", "https://github.com/sustainability-software-lab/ca-biositing/pull/370", "plans/phase3_materialized_views_assessment.md"]
governance: constraint
stale_after: "2026-12-31"
---

**Purpose**
Loads residue factors (min, mid, max and prune/trim yield per resource and factor type) into `residue_factor`. These feed residue volume estimates in the planned materialized views (see plans/phase3_materialized_views_assessment.md).

**Key files**

| Path:line | Role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/residue_factors_flow.py:18-19 | `@flow(name="Residue Factors ETL")` `residue_factors_etl_flow()` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/residue_factors.py:15-16 | Sheet ID `13rwxml9JEC2BJOrZ7m5tRDj2zf-6tNRHEY0KvIauNOA`, worksheet `Data Views` |
| etl/extract/residue_factors.py:19 | `extract_residue_factors` (gspread open_by_key) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource_information/residue_factor.py:28 | `transform_residue_factor`: FK resolution for resource, data_source (by source URL), unit |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/resource_information/residue_factor.py:19 | `load_residue_factors` returns {inserted, updated, failed} |
| src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lineage.py:9,42 | lineage helpers, called with `.fn()` |

**How it works**
1. Lineage record and group (note: "Residue factor data from Google Sheets").
2. Extract (`extract_residue_factors.fn()`); empty or None returns early.
3. Transform: resolve `resource` to `resource_id` through the Resource table (by name), denormalize `resource_name`, resolve `data_source_id` and `prune_trim_yield_unit_id`.
4. Load: drop rows with NULL resource_id (warning), then upsert on (resource_id, factor_type).

**Interfaces**
- Input: the Google Sheet above, columns `resource, factor_type, primary_product, factor_min, factor_max, factor_mid, prune_trim_yield, prune_trim_yield_unit, source, notes`.
- Output: `residue_factor` rows with `etl_run_id` and `lineage_group_id`.
- Callers: master registry (run_prefect_flow.py:13). It runs before resource_information in the list.

**Gotchas**
- ORDERING: master registry order runs residue_factors (line 13) before resource_information (line 14). Resource names come from the Resource table, so on a fresh DB every residue row lacks resource_id and is dropped (inferred from transform lines 103-125 and load lines 150-160; confirm by a clean run).
- Docstring says sheet "Residue Factors" and worksheet "Data_Views", but code uses the sheet ID and worksheet `Data Views` (space, not underscore).
- Load path: a transform that produces an empty frame returns early without an error.

**History**
- 99cbfcd (2026-04-28, PR #288 Residue Factor ETL): flow added.
- 543adde (2026-05-21, PR #370 Bioconversion ETL and view improvements): later changes.
- https://github.com/sustainability-software-lab/ca-biositing/pull/288 and https://github.com/sustainability-software-lab/ca-biositing/pull/370

**Open questions**
- Should the flow be moved after resource_information in the master registry? (inferred; the comment at run_prefect_flow.py:7 says order matters.)
- Is `factor_type` a closed enum? Not verified.

# Related Concepts
- [System overview (start here)](system-overview.md): Residue factors are an input to residue volume estimates downstream
- [Resource Information ETL flow (resources, then resource images)](flow-resource-information.md): Must run after resource_information so Resource names resolve to resource_id
- [Primary Ag Product ETL flow (basic sample info to primary_ag_product)](flow-primary-ag-product.md): Resources reference primary_ag_product names
