---
type: Fact
title: "Snapshot: datamodels table and subpackage counts disagree across docs"
description: "Snapshot at HEAD a2c8de8: 118 table models in 94 files and 16 domain subpackages; docs still say 91 models. Use code counts, not doc numbers."
tags: [datamodels, inventory, snapshot, counts]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:36Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/__init__.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/base.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/infrastructure/", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/__init__.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views.py"]
stale_after: "2026-11-16"
sources: ["src/ca_biositing/datamodels/README.md", "src/ca_biositing/datamodels/AGENTS.md", "AGENTS.md", "commit ca71a99", "commit f8c9353"]
---

## Snapshot (HEAD a2c8de8, 2026-10-22)
- AST count over `src/ca_biositing/datamodels/ca_biositing/datamodels/models/**/*.py`: 122 class definitions; 118 with `table=True`, in 94 files; the 4 non-table classes are `BaseEntity`, `LookupBase`, `Aim1RecordBase`, `Aim2RecordBase` in `models/base.py`. Earlier snapshot at e41d00d: 112 table classes in 88 files.
- Infrastructure contributed 19 of the 118 (18 dataset tables from #514 plus `facility_record`).
- Domain subpackages under `models/`: 16 (aim1_records, aim2_records, auth, core, data_sources_metadata, experiment_equipment, external_data, field_sampling, general_analysis, infrastructure, methods_parameters_units, people, places, qc, resource_information, sample_preparation). `qc` is new since e41d00d (ca71a99, PR #523).
- Docs: `src/ca_biositing/datamodels/README.md`, `src/ca_biositing/datamodels/AGENTS.md`, and `docs/` still say 91 models (see bugs/doc-drift-model-count). Root `AGENTS.md` says nine materialized views; `src/ca_biositing/datamodels/AGENTS.md` says 7.
- `data_portal_views/` has `mv_*.py` modules (count only; not checked one-to-one against registered views).
- Package root has both `data_portal_views.py` and a `data_portal_views/` directory. Python resolves the package directory first (inferred); potential confusion for readers.

## Why it matters
Doc counts are stale. Do not quote them without re-counting. A re-count with `grep -rE "^class .*table=True"` misses multi-line class headers; use an AST count.

# Related Concepts
- [How models are registered: models/__init__.py re-exports and Alembic metadata](../architecture/datamodels-model-registry.md): how these counts are produced
- [Current state snapshot (2026-10-16)](current-state.md): hub for point-in-time facts
- [Infrastructure tables (infrastructure_* facility datasets, facility_record)](../architecture/datamodels-infrastructure.md): the 19 infrastructure tables in the count
