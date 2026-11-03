---
type: Architecture
title: Name-to-ID normalization (get-or-create reference rows)
description: "normalize_dataframes swaps name columns for foreign-key IDs, case-insensitively, inserting missing reference rows in one session; used by about 38 modules."
tags: [pipeline, transform, foreign-key, lookup]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:49Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/prepared_sample.py"]
sources: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py", "commit ed3a3f7", "commit 930d868", "https://github.com/sustainability-software-lab/ca-biositing/pull/376", "https://github.com/sustainability-software-lab/ca-biositing/pull/220"]
governance: context
---

## Purpose
Lets transforms work with human names (e.g. `dataset`, `resource`) while loading integer foreign keys. Missing reference rows are created on the fly.

## Key files
| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py:148` | `normalize_dataframes(dataframes, normalize_columns)`. `normalize_columns` maps column name to `(Model, name_attr)`. |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py:35` | `replace_name_with_id_df`: builds lowercased, stripped map (`normalize_name`, line 86). Strips `#gid=` fragments for `FileObjectMetadata`. Adds missing names with `db.add` and one `flush`, then re-queries. |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py:71` | Inner `except` in the helper returns an all-NA column for models without the expected attributes. |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/transform/*` (about 38 modules) | Call sites. Example: `etl/transform/prepared_sample.py:13,94`. |

## How it works
1. `normalize_dataframes` opens one `Session(engine)` (engine imported at call time, `name_id_swap.py:~225`).
2. For each frame and each `col: (Model, attr)`: primary key of Model is the id column. Calls `replace_name_with_id_df`.
3. Missing normalized names are added to the session as the model (new rows store the lowercased name, since the normalized value is inserted, `name_id_swap.py:~110-120`).
4. Result column is `<col>_id`. The original name column is dropped (unless the name and final column match).
5. One `commit` at the end for all frames.

## Interfaces
- Input: DataFrame(s) plus column map. Output: list of DataFrames, always a list.
- Side effects: inserts reference rows into the DB. This is the only place transforms write.

## Gotchas
- Errors are swallowed per column and turned into NA ids. See `bugs/pipeline-normalization-silent-null-ids`.
- Case-insensitive matching means `Corn` and `corn` resolve to the same row.
- Two replacement helpers exist. `utils/lookup_utils.py` has its own version with a different signature. See `decisions/pipeline-lookup-helper-duplication`.

## History
- `930d868` (PR #220) and `bd0ec5e` (PR #260): normalization refined during data-portal schema work.
- `e6ee628` (PR #268): mv_biomass_fermentation fixes.
- `ed3a3f7` (PR #376): `FileObjectMetadata` URL-fragment handling added.

## Open questions
- Whether the all-NA fallback should raise instead (inferred; confirm with the owners of the affected loads).

# Related Concepts
- [Two competing name-to-id helpers (lookup_utils vs name_id_swap)](../decisions/pipeline-lookup-helper-duplication.md): Competing helper with a different contract.
- [Name-to-ID normalization can emit NULL foreign keys without failing](../bugs/pipeline-normalization-silent-null-ids.md): Failure mode of this function.
- [How a pipeline flow wires extract, transform, and load](pipeline-flow-wiring.md): Where this step sits in transform.
