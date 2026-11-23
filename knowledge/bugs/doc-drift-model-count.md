---
type: Bug
title: Docs say 91 models; the code has 112 table models (15 subdirectories is correct)
description: Docs say 91 models; the code has 118 table models (122 classes including 4 abstract bases) at a2c8de8 across 16 subdirectories.
tags: [docs, drift, datamodels]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:36Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models", "src/ca_biositing/datamodels/AGENTS.md", "docs/architecture.md", "docs/datamodels/CONTRIBUTING.md", "docs/api/index.md", "src/ca_biositing/datamodels/README.md", ".agents/rules/repository-map.md"]
stale_after: "2026-11-16"
sources: ["src/ca_biositing/datamodels/AGENTS.md:44", "docs/architecture.md:147", "docs/datamodels/CONTRIBUTING.md:20", "docs/api/index.md:8", "src/ca_biositing/datamodels/README.md:7", ".agents/rules/repository-map.md:42", "commit f8c9353"]
---

## Purpose
Record a verified count mismatch so readers do not trust "91 models".

## Evidence
- Code at a2c8de8: AST count over `src/ca_biositing/datamodels/ca_biositing/datamodels/models/**/*.py` gives 122 classes; 118 have `table=True` (in 94 files); 4 are non-table bases (`BaseEntity`, `LookupBase`, `Aim1RecordBase`, `Aim2RecordBase`) in `models/base.py`. 16 domain subdirectories (verified with `find`; `qc` added since e41d00d).
- At e41d00d the same count was 112 table models in 88 files.
- Docs saying 91 (unchanged at a2c8de8; grep confirmed):
  - `src/ca_biositing/datamodels/AGENTS.md:44` ("all 91 models" at `:62` in the earlier count)
  - `docs/architecture.md:147` and `:315`
  - `docs/datamodels/CONTRIBUTING.md:20` and `:50`
  - `docs/api/index.md:8`
  - `src/ca_biositing/datamodels/README.md:7`
  - `.agents/rules/repository-map.md:42`

## Impact
Agents and developers may budget effort or search for models wrongly. The subdirectory count is near-correct (16, not 15); the model total is wrong by 27.

## Fix
Replace "91" with "118 table models (122 classes including 4 abstract bases)" or drop the number and point to a generated count.

# Related Concepts
- [System overview (start here)](../architecture/system-overview.md): Datamodel size is part of the system overview
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Counts are a current-state snapshot
- [Snapshot: datamodels table and subpackage counts disagree across docs](../facts/datamodels-model-inventory.md): the counts this bug quotes
