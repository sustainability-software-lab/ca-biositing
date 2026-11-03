---
type: Decision
title: "Lookup names and qualitative values are stored lowercase, with lineage fields"
description: "ETL convention: lookup names lowercase, parameter names space-separated, use_case_name canonical, and etl_run_id / lineage_group_id populated where supported."
tags: [etl, lookups, conventions, decision]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:54Z" }
status: stable
code_refs: ["docs/database_conventions.md", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/base.py"]
sources: ["docs/database_conventions.md"]
governance: context
---

## Purpose
Record the convention that keeps lookup matching stable across ETL runs.

## Key files
| Path | Role |
|---|---|
| `docs/database_conventions.md:1-19` | The full convention |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/lookup_utils.py` | Lookup matching helpers (see pipeline slice) |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/models/base.py` | Base columns including `etl_run_id` and `lineage_group_id` |

## How it works
Source labels are lowercased and mapped to the canonical `use_case_name`. Parameter names use spaces (`resource use perc low`), not snake case. Lineage fields are set when the model supports them.

## Interfaces
- Input: Google Sheets labels. Output: lowercase lookup rows used in joins.

## Gotchas
- Purpose is inferred: the doc says the convention keeps lookup matching stable and aligned with lowercase queries (inferred from docs/database_conventions.md:1-19).

## History
- Doc present in the repo with no dated change in this slice (dates not verified; check `git log -- docs/database_conventions.md`).

## Open questions
- Whether every lookup in `models/` follows the convention is not verified.

# Related Concepts
- [Decision: centralize data-quality exclusions in common.py (not per-view literals)](views-centralized-qc-filters.md): Filters compare lowercase names, so both conventions interact
- [Glossary](../facts/glossary.md): Defines lookup and lineage terms
