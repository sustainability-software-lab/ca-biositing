---
type: Decision
title: "History: ETL buildout by data source (Oct 2025 to Oct 2026)"
description: "Which ETL sources were added when (Prefect, BT2023, analytical suite, gasification, USDA counties, almond, biodiesel, infrastructure) and by whom, to date a pipeline module."
tags: [pipeline, etl, history, prefect]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:39Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py"]
sources: ["commit 43f3147", "commit 447162c", "commit 5ebbe4f", "commit a4e6fc9", "commit 4d2f128", "commit fa8583a", "commit b5887e4", "https://github.com/sustainability-software-lab/ca-biositing/pull/53", "commit f8c9353", "https://github.com/sustainability-software-lab/ca-biositing/pull/514", "https://github.com/sustainability-software-lab/ca-biositing/pull/482", "https://github.com/sustainability-software-lab/ca-biositing/pull/344"]
---

## Purpose
Maps data sources to the commits that introduced them, so a reader can find the origin of a flow or transform.

## Key files
| Path | Role |
|---|---|
| src/ca_biositing/pipeline/ca_biositing/pipeline/flows/ | Prefect flows (now includes 18 infrastructure flows) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/resource.py | Shared resource transform (7 changes) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/landiq.py | LandIQ loader (7 changes) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py | Name/id swap helper (9 changes) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/ | Infrastructure transforms (18 files, from f8c9353) |

## How it works
- 608530b (2025-09-29): my_etl_postgres imported under etl_merge/ from the earlier repo.
- 43f3147 (PR #53, 2025-10-29): Prefect implementation and directory reorganization.
- 447162c (PR #121, 2026-02-19): Billion Ton 2023 agricultural ETL.
- 7187692 (PR #122): LandIQ normalization; 5ebbe4f (PR #123): ICP, XRF, calorimetry, XRD analytical suite.
- a4e6fc9 (PR #217, 2026-04-01): gasification ETL; 9d1e16f (PR #154): Aim 2 fermentation.
- 35423d1 (PR #265): qualitative data ETL; 99cbfcd (PR #288): residue factor ETL.
- 4d2f128 (PR #432, 2026-06-20): USDA expanded to all California counties; 6b575b1 (PR #436): dynamic top commodity discovery.
- 9697eeb (PR #320): almond ETL; b5887e4 (PR #456, Avi, 2026-09-09): geocoding separated from ETL.
- 85373ad (PR #492) and c5a592e (PR #493): later refactors.
- f66e296 (PR #344, 2026-05-13, Avi): biodiesel ETL first added; fa8583a (PR #380, 2026-05-26): biodiesel commented out of the registry.
- PR #482 (open, created 2026-09-13, Avi): infrastructure ETL first attempt.
- f8c9353 (PR #514, merged 2026-10-22, Avi): infrastructure ETL second attempt, 18 datasets (15 geocoded, 3 lines), biodiesel re-enabled, `temp_external_datasets/` removed. See architecture/pipeline-infrastructure-etl-family.

## Interfaces
Inputs: Google Sheets and Google Drive files (`gsheet_to_pandas.py`, `gdrive_to_pandas.py`). Outputs: Postgres tables and views. Callers: run-single-flow and list-flows pixi tasks.

## Gotchas
- Biodiesel ETL was commented out in fa8583a (PR #380) and re-enabled in f8c9353 (PR #514), so the module runs again in the master runner.
- Static data must be shipped in the production image (73ffbf2, PR #406), a recurring issue. The infrastructure family removed its committed staging files instead (f8c9353).

## History
Dates and PRs listed above.

## Open questions
- Which flows are scheduled in production (not verified in this slice).
- Whether the infrastructure flows have run in staging or production since f8c9353 (not verified).

# Related Concepts
- [System overview (start here)](../architecture/system-overview.md): hub for the pipeline layer
- [Pipeline package layout and ETL layers](../architecture/pipeline-package-layout.md): current pipeline design (id prefix architecture/pipeline-*)
- [Contributors by commit count and area (snapshot at e41d00d)](history-contributors.md): who owns each ETL area
- [Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern](../architecture/pipeline-infrastructure-etl-family.md): the infrastructure buildout
- [PR #514 (merged 2026-10-22): infrastructure ETL second attempt, commit f8c9353](pr-514.md): the merged PR that completed it
