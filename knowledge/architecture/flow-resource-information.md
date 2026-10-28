---
type: Architecture
title: "Resource Information ETL flow (resources, then resource images)"
description: "Two-phase load of the resource table from the 07.2-Resources tab, then resource_image from 08.0_Resource_images; images depend on resources being loaded first."
tags: [pipeline, etl, flow, resource, google-sheets, ordering]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:08Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/resource_information.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/resources.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/resource_images.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource_information/resource_image.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/resource.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/resource_information/resource_image.py"]
sources: ["commit bd0ec5e", "commit dc98b30", "commit a9a86eb", "https://github.com/sustainability-software-lab/ca-biositing/pull/260", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource.py"]
governance: constraint
stale_after: "2026-12-31"
---

**Purpose**
Creates the canonical `resource` rows (feedstock resources such as crops and residues) and their `resource_image` rows, both from the Aim 1 Google Sheet.

**Key files**

| Path:line | Role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/resource_information.py:4-5 | `@flow(name="Resource Information ETL")` `resource_information_flow()` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/resources.py:7-8 | GSheet `Aim 1-Feedstock Collection and Processing Data-BioCirV`, tab `07.2-Resources` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/resource_images.py:7-8 | Same sheet, tab `08.0_Resource_images` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource.py:22 | `transform`: swaps names for IDs via `normalize_dataframes` (primary_ag_product), renames `resource` to `name`, lowercases |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/resource.py:9 | `load_resource` upserts Resource |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource_information/resource_image.py:18 | `transform_resource_images` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/resource_information/resource_image.py:17 | `load_resource_images`, upsert on (resource_name, image_url, sort_order) |

**How it works**
1. Lineage record and group.
2. Phase 1: extract resources, transform, load `resource`.
3. Phase 2: extract images, transform, load `resource_image` (resolves resource by name, so phase 1 must be committed first).

**Interfaces**
- Input: two GSheet tabs above.
- Output: `resource`, `resource_image`.
- Callers: master registry (run_prefect_flow.py:14). Downstream: residue_factors, static_resource_info, qualitative.

**Gotchas**
- transform/resource.py:104 still has a template TODO for the column mapping (only `resource -> name` is mapped). Adding columns requires editing that dict.
- Calls `resources.extract.fn()` etc. directly, so retries of the factory task are bypassed in this flow (inferred from `.fn()` usage; confirm).
- Requires primary_ag_product rows to exist for name-to-ID swaps (see flow-primary-ag-product).

**History**
- a9a86eb (2026-02-05, PR #84): initial.
- dc98b30 (2026-02-11, PR #108): SQL-first refactor.
- bd0ec5e (2026-04-14, PR #260): multiple ETL refinements.
- https://github.com/sustainability-software-lab/ca-biositing/pull/260

**Open questions**
- None beyond the TODO above.

# Related Concepts
- [System overview (start here)](system-overview.md): Creates the resource backbone that many analysis tables reference
- [Residue Factors ETL flow (Residue Factors sheet to residue_factor)](flow-residue-factors-flow.md): Residue factors resolve resource names created here
- [Primary Ag Product ETL flow (basic sample info to primary_ag_product)](flow-primary-ag-product.md): Name-to-ID swap for primary_ag_product must succeed before this runs
