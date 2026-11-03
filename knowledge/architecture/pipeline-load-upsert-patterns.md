---
type: Architecture
title: "Load task upsert patterns (on_conflict, natural key, bulk)"
description: "Three load styles in etl/load: postgres on_conflict upsert, select-then-write by natural key, and bulk loads with lookup maps; each commits once per task call."
tags: [pipeline, load, upsert, postgres, sqlalchemy]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:51Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/**", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/templates/load_template.py"]
sources: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/templates/load_template.py", "commit b5887e4", "commit 2dcfa81", "https://github.com/sustainability-software-lab/ca-biositing/pull/456", "https://github.com/sustainability-software-lab/ca-biositing/pull/451"]
governance: context
---

## Purpose
Documents how loads write to PostgreSQL and which key each one uses for idempotency.

## Key files
| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/templates/load_template.py:9-80` | Template: `insert(...).on_conflict_do_update(index_elements=["record_id"], set_=...)`. Excludes `id`, `created_at`, `record_id` from updates. |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/prepared_sample.py:9-70` | Natural key `name`. Select, then update or add. Skips rows without `name`. |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/landiq.py:101-135` | `bulk_upsert_landiq_records`, `bulk_insert_polygons_ignore` (line 20), and `load_landiq_record` using `fetch_lookup_ids` (lines 154-186). |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/usda/usda_census_survey.py` | Raw `text`/`insert` style load (imports at lines 12-14). |

## How it works
Common steps across styles:
1. `df.replace({np.nan: None}).to_dict(orient="records")`.
2. Filter each record to real table columns (`__table__.columns`).
3. Stamp `updated_at`, and `created_at` if missing.
4. Open `engine.connect()` and `Session(bind=conn)`, then one `commit` at the end.

## Interfaces
- Input: transformed DataFrame. Output: none (`None`). Logs row counts.
- Idempotency key: `record_id` (template), `name` (prepared_sample), polygon geometry and dataset/crop lookups (landiq).

## Gotchas
- Per-call commit means a failed call rolls back that call only. Chunked loads (landiq) keep earlier chunks.
- The natural-key style runs one SELECT per row (inferred from code; N+1 queries).
- Template placeholders (`YourModel`, `Observation`) must be replaced. The template imports `Observation` as a stand-in (`load_template.py:34`).

## History
- `b5887e4` (PR #456): geocoding split out from ETL. Load modules were touched.
- `2dcfa81` (PR #451): cotton volumes fix touched USDA load.

## Open questions
- Whether natural-key loads should move to on_conflict for speed (inferred; no benchmark found).

# Related Concepts
- [How a pipeline flow wires extract, transform, and load](pipeline-flow-wiring.md): Load is the final step of a flow.
- [Database engines and DATABASE_URL host rewriting](pipeline-engine-and-db-url.md): Source of the engine these loads use.
- [Land IQ ETL flow (shapefile to landiq_record and polygon)](flow-landiq-etl.md): Chunked bulk load in practice.
