---
type: Requirement
title: "Infrastructure loaders must be idempotent: a re-run updates rows and never duplicates them"
description: "Each infrastructure load must keep its natural-key select and on_conflict index on a column the transform actually fills, and the re-run duplicate tests must stay green."
tags: [pipeline, infrastructure, upsert, idempotent, constraint]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:26:58Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/infrastructure/", "src/ca_biositing/pipeline/tests/test_infrastructure_duplicate_prevention.py", "src/ca_biositing/pipeline/tests/test_infrastructure_etl.py"]
sources: ["commit f8c9353", "https://github.com/sustainability-software-lab/ca-biositing/pull/514"]
governance: constraint
stale_after: "2027-04-22"
---

## Rule
For every infrastructure dataset, running the flow twice on the same source must leave the same number of rows. Each loader in `etl/load/infrastructure/` must:
- select an existing row by a natural key that the transform fills (for example `name` and `address_id`, `project_id`, `company` and `address_id`), and update it if found;
- use `on_conflict_do_update(index_elements=[...])` only on a column that the transform populates for every row. A conflict target that is always NULL never matches.

## Why
Infrastructure flows run on each master ETL run (`run_prefect_flow.py`). A loader that inserts duplicates changes every downstream count. The EPA food manufacturers loader breaks the second half of this rule: its conflict key `processing_facility_id` is never set by the transform, so only the select prevents duplicates (see bugs/infra-epa-upsert-conflict-key-unset).

## Source
- `src/ca_biositing/pipeline/tests/test_infrastructure_duplicate_prevention.py`: `test_load_prevents_duplicates_on_rerun` (`:153`) loads twice and asserts one row (`count1 == 1`, `count2 == 1`) and a non-decreasing `updated_at`. Parametrised over 18 datasets.
- Load examples: `etl/load/infrastructure/landfills.py:12-80` (select on `project_id`, else on `landfill_name` and `address_id`), `food_manufacturers_epa.py:50-72`.

## How to check
1. `pixi run pytest src/ca_biositing/pipeline/tests/test_infrastructure_duplicate_prevention.py` (uses the SQLite fixture; see decisions/testing-sqlite-in-memory-fixtures).
2. For a new dataset, add it to `INFRASTRUCTURE_DATASETS` in both test files and to `get_model_class_for_dataset`.
3. Confirm the conflict target is populated by the transform (grep the final column select).

## Exceptions
None recorded. Note that the test passes for EPA even though the conflict key is unused, because the select matches. The test does not check the conflict key.

# Related Concepts
- [Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern](../architecture/pipeline-infrastructure-etl-family.md): the loaders this rule governs
- [Load task upsert patterns (on_conflict, natural key, bulk)](../architecture/pipeline-load-upsert-patterns.md): the upsert styles the rule allows
- [EPA food manufacturers loader: ON CONFLICT key processing_facility_id is never set by the transform](../bugs/infra-epa-upsert-conflict-key-unset.md): the EPA loader is the current violation
- [Observation upserts depend on the (record_id, record_type, parameter_id, unit_id) unique key](datamodels-observation-upsert-key.md): the same keep-the-key-in-sync rule for observation
