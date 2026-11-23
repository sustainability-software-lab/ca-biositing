---
type: Fact
title: "Issues: ETL and data ingestion (pipeline)"
description: "GitHub issue inventory for ETL, ingestion and loader bugs and features, as of 2026-10-22; open issues first."
tags: [pipeline, etl, ingestion]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:40Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/"]
stale_after: "2026-11-15"
sources: ["gh issue list --repo sustainability-software-lab/ca-biositing --state all (2026-10-16)", "https://github.com/sustainability-software-lab/ca-biositing/issues", "https://github.com/sustainability-software-lab/ca-biositing/issues/534"]
---

**Purpose.** Prefect ETL flows and extract/transform/load code for USDA, county ag reports, almond NSJV, LandIQ, gasification, field/prepared samples and resources.

**Counts.** 40 issues: 22 open, 18 closed. Open issues are listed first. Snapshot as of 2026-10-22 (HEAD a2c8de8); lists come from `gh issue list --state all`.

**Key files.**

| Path | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/flows/` | Prefect flow entrypoints (e.g. county_ag_report_etl.py, almond_nsjv_etl.py, usda_etl.py) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/` | Transform layer (analysis/, prepared_sample.py, resource.py, usda/, landiq/) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/almond_nsjv.py` | Almond NSJV loader; normalization helpers |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/` | Mapping helpers (reviewed_api_mappings.py, seed_commodity_mappings.py, us_state_abbrev.py, name_id_swap.py) |

**How it works.** Issues are the work queue for this area. Each line below is one GitHub issue; bug-type open issues also have their own `bugs/` concept.

**Interfaces.** Inputs: GitHub issues on sustainability-software-lab/ca-biositing. Outputs: none in-repo; status changes are tracked on GitHub.

**Gotchas.** Many ingestion bugs are upstream data (Google Sheets) problems; fixing the sheet is often the real fix (e.g. #174).

**History.** Issue numbers are the history index; see `facts/current-state` for the current-state snapshot. Commit refs where verified: 85373ad (#476, #480 centralization), e289fd1 (#248 per-client API keys), 203b787 (#139 JWT).

**Open questions.** Which open items are still wanted after the 2026 cleanup (for example #157 `name` to `api_name`, #147 lowercase validation) is not stated in the issues; confirm with the owners listed.

**Update 2026-10-22.** Added #534 (open, batch the EPA Food Manufacturers ETL load to avoid OOM; created 2026-10-22).

## Issues (40)

- #156 [OPEN] # [Feature]: Enforce lowercase normalization for commodity mapping and seeding inputs (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/156
- #174 [OPEN] Bug: Field_samples without a Resource (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/174
- #263 [OPEN] [Bug]: CountyAgRecord data_source and dataset ambiguity/issues (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/263
- #264 [OPEN] [Bug]: missing primary ag product linkages for resources (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/264
- #316 [OPEN] [Bug]: fix county ag report flow dataset and methods (@mglbleta) https://github.com/sustainability-software-lab/ca-biositing/issues/316
- #318 [OPEN] [Feature]: Split out white grape pomace samples from grape data (@mglbleta) https://github.com/sustainability-software-lab/ca-biositing/issues/318
- #324 [OPEN] [Bug]: Ultimate Analysis - separate out the UC Davis analysis into “forage_analysis” (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/324
- #339 [OPEN] [Enhancement] ETL templates (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/339
- #356 [OPEN] [Bug]: Include experiment metadata in the ETL (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/356
- #361 [OPEN] [Bug]: State and County Name Inconsistencies (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/361
- #368 [OPEN] [Bug]: Almond hash & other resources need additional fields completed (@mglbleta) https://github.com/sustainability-software-lab/ca-biositing/issues/368
- #375 [OPEN] [Bug]: discuss ICP/XRF longer term solution (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/375
- #378 [OPEN] [Feature]: Data versioning and citing instructions (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/378
- #379 [OPEN] [Feature]: Add column check to ETL (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/379
- #400 [OPEN] [Bug]: Review data filtered out through QC (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/400
- #403 [OPEN] [Feature]: Geocode improvements: write-back & address deduplication by lat/long (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/403
- #405 [OPEN] [Bug] Almond hulls only shows N content for ultimate analysis (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/405
- #477 [OPEN] Fix broken filters in the transform (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/477
- #478 [OPEN] Improve error logging for silent data drops and investigate USDA log discrepancies (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/478
- #479 [OPEN] Standardize DB table constraints across staging and production tables (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/479
- #496 [OPEN] 2024 NSJV almond hull & shell production discrepancies in resource_production_record (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/496
- #534 [OPEN] perf(pipeline): batch EPA Food Manufacturers ETL load to avoid OOM (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/534
- #319 [CLOSED] [Bug]: Pre-treatment and enzyme names are keys (@petercarbsmith,@mglbleta) https://github.com/sustainability-software-lab/ca-biositing/issues/319
- #330 [CLOSED] [Feature]: Review existing data with Beau for accuracy (@bexodim) https://github.com/sustainability-software-lab/ca-biositing/issues/330
- #331 [CLOSED] [Feature]: Check on lignin+ for tomato and grape pomace (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/331
- #338 [CLOSED] [Bug]: Longer names in qualitative data than expected (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/338
- #342 [CLOSED] [Feature]: Gasification timeseries data in google cloud bucket (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/342
- #365 [CLOSED] [Bug]: Descriptions lose sentence case capitalization in the ETL (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/365
- #367 [CLOSED] [Bug]: Image table has multiple null rows for some resource types (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/367
- #369 [CLOSED] [Bug]: LandIQ ETL Not Functioning (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/369
- #383 [CLOSED] [Bug]: look into 0% 3HP yields (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/383
- #384 [CLOSED] [Bug]: update almond woodchips volumes to match almond branches (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/384
- #389 [CLOSED] [Bug]: Change “unc-bio” to its longer name of “unconverted biomass” (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/389
- #390 [CLOSED] [Bug]: add reactor_name to gasification_timeseries table (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/390
- #391 [CLOSED] Crystallinity (XRD) data should be filtered out (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/391
- #407 [CLOSED] [Bug]: Almond Shells Duplicate End Use Case (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/407
- #459 [CLOSED] [Bug]: Walnut shells missing some parts of qualitative data (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/459
- #475 [CLOSED] Move gasification pipeline filter out of Prefect flow file (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/475
- #476 [CLOSED] Move physically impossible data filters and cross-view quality checks into common.py (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/476
- #480 [CLOSED] White list centralization evaluation (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/480

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state snapshot this issue inventory belongs to
- [System overview (start here)](../architecture/system-overview.md): Where pipeline sits in the system
- [How a pipeline flow wires extract, transform, and load](../architecture/pipeline-flow-wiring.md): ETL layers these issues touch
- [#534: EPA food manufacturers load is OOM-killed; all 18 infrastructure loads use one unbatched session](../bugs/infra-load-unbatched-session-oom.md): issue #534 detail
