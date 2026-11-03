---
type: Bug
title: "EPA food manufacturers loader: ON CONFLICT key processing_facility_id is never set by the transform"
description: "The EPA transform never emits processing_facility_id, so the on_conflict target is always NULL and duplicate prevention rests only on a (name, address_id) select."
tags: [bug, etl, infrastructure, upsert, duplicates]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:00Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/food_manufacturers_epa.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/infrastructure/food_manufacturers_epa.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/food_manufacturing_epa.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/food_manufacturers_carb.py"]
sources: ["commit f8c9353", "https://github.com/sustainability-software-lab/ca-biositing/pull/514"]
governance: context
stale_after: "2026-11-21"
---

## Symptom
`etl/load/infrastructure/food_manufacturers_epa.py:69` uses `on_conflict_do_update(index_elements=["processing_facility_id"])`. The EPA transform’s final column select does not include `processing_facility_id`, so that column is NULL for every row and the conflict branch never matches an existing row.

## Evidence in code (HEAD a2c8de8)
- Transform final select `etl/transform/infrastructure/food_manufacturers_epa.py:197-209`: `name`, `naics_code_description`, `naics_code`, `address_id`, `phone`, `website`, the two excess-food estimates, `unique_identifier`, `etl_run_id`, `lineage_group_id`. No `processing_facility_id`.
- Model `datamodels/.../models/infrastructure/food_manufacturing_epa.py:10` makes `processing_facility_id` the primary key, default None, so SQLModel and Postgres assign it on insert (inferred from integer PK behaviour).
- Load select `food_manufacturers_epa.py:50-54` matches on `name` and `address_id` and updates the first match. This is the only effective duplicate check.
- Contrast: `etl/transform/infrastructure/food_manufacturers_carb.py:79` and `:199` carry `processing_facility_id` from the source, so the CARB conflict key works.
- The EPA transform comment at `food_manufacturers_epa.py:190` says the select "matches InfrastructureEthanolBiorefineries fields", a copy-paste from another transform.

## Impact
- Two EPA rows with the same name at the same bridged address (the address key is lat/lon, see architecture/pipeline-infrastructure-geocoded-datasets) collapse into one, and `unique_identifier` from the source is never used as a key (inferred; not run against data).
- `tests/test_infrastructure_duplicate_prevention.py` passes for EPA because the select matches; it does not check the conflict key.

## Status
Open at HEAD. No GitHub issue was found for it in `gh issue list` at the time of writing (not searched exhaustively).

## Gotchas
- Fixing it means adding a stable source identifier to the transform (for example `unique_identifier` or the source ID) and choosing a matching conflict key, then running the duplicate tests. Requirements/infra-loader-idempotent-rerun applies.

## History
- Present since f8c9353 (PR #514, 2026-10-22).

## Open questions
- Whether the EPA source file has a stable ID column (not checked; inspect the Drive file).

# Related Concepts
- [Infrastructure loaders must be idempotent: a re-run updates rows and never duplicates them](../requirements/infra-loader-idempotent-rerun.md): the rule this bug breaks
- [Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern](../architecture/pipeline-infrastructure-etl-family.md): family context and dataset table
- [#534: EPA food manufacturers load is OOM-killed; all 18 infrastructure loads use one unbatched session](infra-load-unbatched-session-oom.md): the same EPA loader is the subject of issue #534
- [Load task upsert patterns (on_conflict, natural key, bulk)](../architecture/pipeline-load-upsert-patterns.md): the upsert styles involved
