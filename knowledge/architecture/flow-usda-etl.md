---
type: Architecture
title: USDA Census and Survey ETL flow (NASS Quick Stats to observations)
description: "Pulls USDA NASS Quick Stats for all CA counties for DB-mapped plus top-5 commodities, after syncing commodity mappings from CSV; needs USDA_NASS_API_KEY."
tags: [pipeline, etl, flow, usda, nass, api]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:11Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/usda_etl.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/usda_census_survey.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/usda/usda_census_survey.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/usda/usda_census_survey.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/seed_commodity_mappings.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/commodity_mappings.csv", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/usda_nass_to_pandas.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/usda_discovery.py", "data/static/ca_counties.csv"]
sources: ["commit 3918d29", "commit 4d2f128", "commit 2dcfa81", "https://github.com/sustainability-software-lab/ca-biositing/pull/124", "https://github.com/sustainability-software-lab/ca-biositing/pull/432", "https://github.com/sustainability-software-lab/ca-biositing/pull/451"]
governance: context
stale_after: "2026-12-31"
---

**Purpose**
Loads USDA Census and Survey agricultural statistics for California counties via the NASS Quick Stats API. It creates per-year CENSUS and SURVEY datasets and writes census, survey and observation rows.

**Key files**

| Path:line | Role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/usda_etl.py:37-38 | `@flow(name="USDA Census Survey ETL")` `usda_etl_flow()` |
| flows/usda_etl.py:9-34 | `sync_commodity_mappings` task: seeds mappings from `utils/commodity_mappings.csv` when prerequisites are met |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/usda_census_survey.py:85 | `extract()`: discovers top 5 commodities, ensures they exist, unions with `get_mapped_commodity_ids()`, one NASS query per commodity for all counties, filters to CA county FIPS |
| etl/extract/usda_census_survey.py:43 | `USDA_API_KEY = os.getenv("USDA_NASS_API_KEY", "")` read at import |
| etl/extract/usda_census_survey.py:56 | `_load_ca_counties` reads `data/static/ca_counties.csv` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/usda/usda_census_survey.py:15 | `transform(data_sources, etl_run_id, lineage_group_id)` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/usda/usda_census_survey.py:17 | `load(transformed_df, etl_run_id, lineage_group_id)`: create datasets, census, survey, observations |
| src/ca_biositing/pipeline/ca_biositing/pipeline/utils/seed_commodity_mappings.py:34 | `seed_commodity_mappings_from_csv` |
| src/ca_biositing/pipeline/ca_biositing/pipeline/utils/usda_nass_to_pandas.py, usda_discovery.py, fetch_mapped_commodities.py | NASS API client, top-N discovery, DB commodity lookup |

**How it works**
1. Lineage record and group.
2. `sync_commodity_mappings.fn()` (return value is not checked).
3. Extract, then transform, then load. The flow returns False at the first None result.

**Interfaces**
- Input: NASS Quick Stats API (key from `USDA_NASS_API_KEY`, set in resources/docker/.env), county list `data/static/ca_counties.csv`, commodity names from the DB.
- Output: `dataset`, `usda_census_record`, `usda_survey_record`, `observation`.
- Callers: master registry (run_prefect_flow.py:18); `pixi run run-single-flow usda_etl`.

**Gotchas**
- Mapping sync is skipped silently when resource or primary_ag_product tables are empty (usda_etl.py:24-27). The extract then only uses discovered commodities.
- Empty API key is not validated at import; failures surface at request time (inferred).
- The load builds SQL with f-strings for dataset names (load lines 122, 146); names are internal, but this is not parameterized.
- Extract returns None if no commodities resolve, which the flow turns into return False (logged as error).

**History**
- 3918d29 (2026-02-19, PR #124 USDA manual fix): earlier loader.
- 4d2f128 (2026-06-20, PR #432): expanded to all CA counties.
- 2dcfa81 (2026-07-07, PR #451): automated mapping sync and cotton volume fix.
- https://github.com/sustainability-software-lab/ca-biositing/pull/432 and https://github.com/sustainability-software-lab/ca-biositing/pull/451

**Open questions**
- Should `sync_commodity_mappings` failing be fatal? Currently it is not.

# Related Concepts
- [System overview (start here)](system-overview.md): USDA NASS is an external API source feeding observation tables
- [Primary Ag Product ETL flow (basic sample info to primary_ag_product)](flow-primary-ag-product.md): Commodity mapping sync requires primary_ag_product rows
- [Resource Information ETL flow (resources, then resource images)](flow-resource-information.md): Commodity mapping sync requires resource rows
- [Static Resource Info ETL flow and update-static-resource-info pixi task](flow-static-resource-info.md): Same pixi-driven mapping sync pattern (update-static-resource-info also seeds commodity mappings)
