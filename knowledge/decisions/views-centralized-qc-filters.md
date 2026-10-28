---
type: Decision
title: "Decision: centralize data-quality exclusions in common.py (not per-view literals)"
description: "Why exclusions moved into one module, what each exclusion was added for (with PR and issue links), and the rejected per-view-literal approach."
tags: [decision, data-quality, filters, history, materialized-views]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:35Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py", "alembic/versions/0022_exclude_jaguar_provider.py", "alembic/versions/0023_centralize_qc_constants_and_fix_icp_ppm_cap_drift_in_analysis_data_view.py", "src/ca_biositing/datamodels/README.md", "scripts/filter_funnel_snapshot.py", "src/ca_biositing/datamodels/tests/test_view_filters.py"]
sources: ["commit 85373ad", "commit d4f6b33", "commit c0f0b62", "commit 5ab52b8", "commit 4ce9559", "https://github.com/sustainability-software-lab/ca-biositing/pull/492", "https://github.com/sustainability-software-lab/ca-biositing/pull/472", "https://github.com/sustainability-software-lab/ca-biositing/pull/431", "https://github.com/sustainability-software-lab/ca-biositing/pull/382", "https://github.com/sustainability-software-lab/ca-biositing/pull/326", "src/ca_biositing/datamodels/README.md"]
governance: context
---

## Decision
All record and resource exclusions live in `data_portal_views/common.py`, one labeled section per dimension, even when a dimension is empty. Views import helpers rather than writing literals. The module docstring makes this a rule.

## History of the exclusions
- 4ce9559 (PR #326, 2026-05-12): "Audits and View Fixes" (initial fixes).
- 5ab52b8 (PR #382, 2026-06-01): filters added to the ca_biositing analysis tables.
- c0f0b62 (PR #431, with #422): excluded `alfalfa`, `almond hulls and shells mix`, `almond shells and hulls mix` (naming variant), `almond woodchips` (issue #409). Also issues #396, #389, #413, #419.
- d4f6b33 (PR #472, 2026-09-02): excluded provider `jaguar` (issue #472), migration 0022.
- 85373ad (PR #492, closes #476 and #480, 2026-10-08): centralized everything; added a pre-refactor baseline snapshot and structural tests. Migration 0023 fixed the ICP ppm cap drift; 0024 applied the centralized constants across data_portal views.

## Alternatives considered
- Inline literals in each view module: the state before #476/#480. It caused drift (ICP cap present in one view and missing in another).
- Placeholder sections for empty dimensions were kept deliberately so a reviewer can scan one file.

## Trade-offs
- Gained: one audit point; a filter change is one edit.
- Cost: an exclusion’s reason is often undocumented (`# excluded 2026-05: original placeholder exclusion, rationale undocumented`). Filter changes need recompile, migrate, and refresh before they show up.

## Governance
Constraint, see architecture/views-data-quality-filters.

## Merged detail: All data-quality filters live in data_portal_views/common.py

### Purpose
Record the refactor that moved view-level exclusions into one module and why views that deliberately skip filters say so.

### Key files
| Path | Role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py:42` | `EXCLUDED_RESOURCES` |
| `common.py:78` | `EXCLUDED_PROVIDERS` |
| `common.py:88` | `MIN_PRODUCTION_DATA_YEAR = 2017` |
| `common.py:104` | `EXCLUDED_QC_STATUSES = ["fail"]` |
| `common.py:119` | `ICP_MAX_PPM = 500_000` |
| `src/ca_biositing/datamodels/README.md:47-66` | "Data-Quality Filters" section and how-to |
| `scripts/filter_funnel_snapshot.py` | Phase-0 baseline snapshot tool (`pixi run filter-baseline-snapshot`) |
| `src/ca_biositing/datamodels/tests/test_view_filters.py` | Structural tests on compiled WHERE clauses |

### How it works
Views import constants and helpers from `common.py` and apply them in their `where()` clauses. Views that surface raw government data (`usda_census_view`, `mv_usda_county_production`, `mv_billion_ton_county_production`) deliberately apply none and say so in their docstrings.

### Interfaces
- Input: constants in `common.py`. Output: filtered view rows, recompiled via `compile-mv-fixes`.

### Gotchas
- Changing a constant does not change a view until a migration is compiled and applied.
- `EXCLUDED_PRIMARY_AG_PRODUCTS`, `EXCLUDED_EXPERIMENTS`, `EXCLUDED_REPLICATES` are empty lists today (`common.py:57,64,72`).

### History
- Commit 85373ad (2026-10-08), PR #492 for issues #476 and #480. Phase 0 added the snapshot and tests; Phase 1 reorganized common.py with no behavior change.
- That commit’s Phase-0 message notes that the ICP ppm cap was absent from `ANALYSIS_DATA_VIEW` before the refactor (issue #476 drift).

### Rejected alternatives
Per-view inline filters (the state before the refactor), rejected because drift between views was the problem (inferred from the commit messages).

### Open questions
- The baseline JSON cites `plans/jiggly-crafting-planet.md`, which is not in the repo (see bugs/doc-drift-missing-referenced-artifacts).

# Related Concepts
- [common.py: the single gatekeeper for view data-quality filters](../architecture/views-data-quality-filters.md): The module and helpers this decision produced.
- [analysis_data_view and analysis_average_view: observation-level analysis layer](../architecture/views-analysis-data-view.md): View where the ICP cap drift was found and fixed.
- [Decision: migrations embed frozen compiled SQL instead of importing view expressions](views-compiled-sql-snapshots.md): Why filter edits need a compile step.
- [Phase 3 plan: align data_portal views to spec and fix has_* QC gating](data-portal-mv-alignment-plan.md): The Phase 3 plan depends on QC filtering in these views
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Current filter values are a snapshot
