---
type: Decision
title: "Phase 3 plan: align data_portal views to spec and fix has_* QC gating"
description: "April 2026 plan for the residue-factor volume path and QC-gated boolean flags; partly implemented, status text is stale."
tags: [materialized-views, data-portal, plan, residue-factors]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:52Z" }
status: stable
code_refs: ["plans/phase3_materialized_views_assessment.md", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_search.py"]
sources: ["plans/phase3_materialized_views_assessment.md", "https://github.com/sustainability-software-lab/ca-biositing/pull/288", "commit 99cbfcd"]
governance: context
stale_after: "2026-11-16"
---

## Purpose
Capture the April 2026 assessment and what it says about the data-portal views, with its current status.

## Key files
| Path | Role |
|---|---|
| `plans/phase3_materialized_views_assessment.md:1-120` | Issues 1 (has_* gating), 2 (volume strategy), 3 (view alignment table) |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_search.py:148` | Comment says tag thresholds use QC-filtered metrics |
| `mv_biomass_search.py:289-300` | `has_moisture_data`, `has_volume_data` use `resource_metrics_v2` and `volume_agg` |

## How it works
The plan proposes: exclude `qc_pass = "fail"` before computing `has_*` flags; compute residue volume as production volume times residue factor, with census bearing-acre fallback; apply a view-by-view alignment table.

## Interfaces
- Affects `mv_biomass_search`, `mv_usda_county_production`, `mv_biomass_composition`, and others.

## Gotchas
- The plan marks `mv_biomass_search` as "Needs Fix", but current code uses QC-filtered metric CTEs (inferred from the comment at line 148; confirm by querying `data_portal.mv_biomass_search` against failed-QC data).
- The plan says "9 views"; the code now has 12 data_portal view modules (see bugs/doc-drift-materialized-view-count).

## History
- Plan dated 2026-04-20, status "Assessment Complete - Ready for Implementation Planning".
- Related work: commit 99cbfcd (2026-04-28), PR #288, residue-factor ETL and mv_biomass_search refinement.

## Open questions
- Whether the dual-path volume strategy (production vs census) shipped is unverified.

# Related Concepts
- [Decision: centralize data-quality exclusions in common.py (not per-view literals)](views-centralized-qc-filters.md): QC gating in the plan is implemented through common.py
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Plan status is a point-in-time snapshot
