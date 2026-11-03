---
type: Bug
title: "#534: EPA food manufacturers load is OOM-killed; all 18 infrastructure loads use one unbatched session"
description: "Open issue #534: the EPA load ran out of memory at 43,738 rows; the same single-session, one-commit loop is in all 18 infrastructure loaders."
tags: [bug, etl, infrastructure, performance, memory, open]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:26:59Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/infrastructure/food_manufacturers_epa.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/infrastructure/food_manufacturers_carb.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/infrastructure/"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/534", "commit f8c9353"]
governance: context
stale_after: "2026-11-21"
---

## Symptom
Issue #534 (open, opened 2026-10-22, https://github.com/sustainability-software-lab/ca-biositing/issues/534): the EPA Food Manufacturers ETL `load` task was OOM-killed during a `married-fossa` run with 43,738 records. Extract and transform had finished. The CARB flow, with 6,047 records and the same pattern, completes. Reported `dmesg`: anon-rss about 692 MB for python3.13.

## Evidence in code (HEAD a2c8de8)
- `etl/load/infrastructure/food_manufacturers_epa.py:38` opens one `Session(bind=conn)` for the whole batch.
- `:39` loops over every record; `:40-41` logs every 500 rows but does not commit.
- `:50-54` runs a per-row `SELECT` on `name` and `address_id`.
- `:68-72` runs a per-row `insert ... on_conflict_do_update`.
- `:74` is the only `session.commit()`.
- The same shape is in all 18 loaders: one `session.commit()` each (grep), and the `i % 500` check is a log line, not a flush or commit.

## Mechanism
The issue attributes the OOM to the ORM identity map and pending state growing across all rows before any flush. This is the issue’s reading; it was not reproduced in this slice (inferred).

## Status
Open. The issue is a tracking issue; no fix is in progress. The issue lists three asks: commit per batch of 500 to 1000 rows, a bulk `insert ... on_conflict_do_update` per batch, and an audit of the other loaders.

## Gotchas
- architecture/pipeline-load-upsert-patterns says loads commit once per task call; that is the pattern this bug is about.
- Any batching fix must keep the natural-key select that requirements/infra-loader-idempotent-rerun relies on, or switch to a conflict key that is populated (see bugs/infra-epa-upsert-conflict-key-unset).

## History
- Opened 2026-10-22 against the code merged in f8c9353 (PR #514).

## Open questions
- Whether the largest source (EPA, 43,738 rows) is the only one at risk on the devcontainer, or whether the memory limit there is the only constraint (not measured).

# Related Concepts
- [Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern](../architecture/pipeline-infrastructure-etl-family.md): the family whose loaders share this pattern
- [Load task upsert patterns (on_conflict, natural key, bulk)](../architecture/pipeline-load-upsert-patterns.md): the load style that commits once per call
- [Infrastructure loaders must be idempotent: a re-run updates rows and never duplicates them](../requirements/infra-loader-idempotent-rerun.md): a fix must keep the re-run rule
- [Issues: ETL and data ingestion (pipeline)](../facts/issues-etl-ingestion.md): issue inventory this bug belongs to
