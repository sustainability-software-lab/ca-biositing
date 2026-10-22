---
type: Decision
title: Two competing name-to-id helpers (lookup_utils vs name_id_swap)
description: lookup_utils.py and name_id_swap.py each implement replace_name_with_id_df with different signatures and commit rules; name_id_swap is the one most code uses.
tags: [pipeline, lookup, tech-debt, decision]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:51Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lookup_utils.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/landiq.py"]
sources: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lookup_utils.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py", "commit a9a86eb", "commit ed3a3f7"]
governance: context
---

## Purpose
Records the split between two helpers that solve the same problem and why both still exist.

## Key files
| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lookup_utils.py` (`replace_name_with_id_df`, about lines 73-126) | Signature `(db, df, ref_model, name_column_name, id_column_name)`. Exact-match names. Commits once per new name (`db.commit()` inside the loop, about line 117). |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lookup_utils.py` (`fetch_lookup_ids`, end of file) | Bulk id lookup. Used only by `etl/load/landiq.py:154,170,186` and `tests/test_landiq_load.py`. |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py:35` | Signature `(db, df, ref_model, df_name_column, model_name_attr, id_column_name, final_column_name)`. Case-insensitive. Flushes once. Returns `(df, num_created)`. Used through `normalize_dataframes` by about 38 modules. |

## How it works
Both build a name-to-id map from the reference table and insert missing names. Differences are in normalization and commit granularity.

## Interfaces
- Callers of `name_id_swap` go through `normalize_dataframes`. Callers of `lookup_utils` call the helper directly.

## Gotchas
- A change to one does not change the other. Tests that cover one path may miss the other.
- `lookup_utils` docstrings describe the interface, but the `tests/README.md` and a notebook (`docs/dev-references/test_lookup_utils.ipynb`) still reference it.

## History
- `43f3147` (PR #53) created `lookup_utils`; `a9a86eb` (PR #84) last changed it.
- `name_id_swap` was reworked in `930d868` (PR #220), `bd0ec5e` (PR #260), `ed3a3f7` (PR #376).

## Open questions
- Whether `lookup_utils.replace_name_with_id_df` can be removed after `landiq` is migrated (inferred; confirm with the landiq owner).

# Related Concepts
- [Name-to-ID normalization (get-or-create reference rows)](../architecture/pipeline-name-id-normalization.md): The preferred helper and its contract.
- [Load task upsert patterns (on_conflict, natural key, bulk)](../architecture/pipeline-load-upsert-patterns.md): Landiq load uses the older helper.
