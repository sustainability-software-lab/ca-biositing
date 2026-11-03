---
type: Architecture
title: "analysis_data_view and analysis_average_view: observation-level analysis layer"
description: "How analysis_data_view flattens Observations into one row per measurement with normalized analysis types and QC flags, and how analysis_average_view builds on it."
tags: [views, analysis, observation, qc, webservice]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:25Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/views.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/analysis_service.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/feedstocks/analysis.py"]
sources: ["commit 85373ad", "commit 5ab52b8", "commit 9d1e16f", "commit 83d42dc", "alembic/versions/0023_centralize_qc_constants_and_fix_icp_ppm_cap_drift_in_analysis_data_view.py", "https://github.com/sustainability-software-lab/ca-biositing/pull/382", "https://github.com/sustainability-software-lab/ca-biositing/pull/492"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
`analysis_data_view` is the single flattened view of lab-analysis observations. It is the main read path for the webservice analysis endpoints and the source for `analysis_average_view`.

## Key files
| Path:line | Symbol | Role |
|---|---|---|
| `views.py:107` | `AnalysisDimensionUnit`, `_analysis_base` | Base select: Observation joined to Parameter, Unit, DimensionType, and an outer join to each of the 9 analytical record tables |
| `views.py:275` | `ANALYSIS_DATA_VIEW` | Final projection with `analysis_type_norm`, `qc_pass`, geoid |
| `views.py:300-310` | filter calls | `get_resource_filter`, `get_qc_status_filter`, `get_ultimate_filter`, `get_icp_filter`, `get_provider_filter` |
| `views.py:497` | `ANALYSIS_AVERAGE_VIEW` | Aggregates from analysis_data_view |

## How it works
1. Each observation is matched to its record table with `lower(record_id) = lower(record_id)` AND a `record_type` predicate.
2. `analysis_type_norm` maps record_type spellings to a canonical name (for example `icp-oes` to `icp`).
3. `qc_pass` is a `COALESCE` across record tables with default `"pass"` when no record matches.
4. `geoid` comes from `LocationAddress.geography_id`.
5. Filters from `common.py` remove excluded resources and providers, failed QC, ultimate values above 100 and non-ppm ICP values above the cap.

## Interfaces
- Reader: `analysis_service.py` `get_analysis_data_view` and related functions (lines 74-95, 210-238), which filter by `resource_id`, `geoid`, `parameter`.
- `feedstocks/analysis.py:40` returns an empty list while the geoid bug is open.
- Writer: migrations only (latest DDL in 0023 and 0024).

## Gotchas
- Filtering on `geoid` returns nothing useful today because geoids are NULL for many rows (see bugs/views-analysis-data-view-null-geoid).
- The ICP ppm cap was documented in `common.py` but absent from this view until migration 0023 (issue #476).
- The base join is case-insensitive on `record_id` and keyed on `record_type`. A new record type needs edits in three places: the join, the `analysis_type_norm` CASE, and the `analysis_metrics` list in `common.py`.

## History
- 9d1e16f (PR #154) and 83d42dc (PR #155): refinement and USDA normalization.
- 5ab52b8 (PR #382): QC filters added.
- 85373ad (PR #492): filters centralized and ICP cap wired in.

## Open questions
- Root cause of the NULL geoid issue (not investigated in this slice).

# Related Concepts
- [ca_biositing schema views in views.py: definitions, order, and consumers](views-ca-biositing-schema.md): Parent list of ca_biositing views this one belongs to.
- [common.py: the single gatekeeper for view data-quality filters](views-data-quality-filters.md): Filter helpers applied in this view.
- [Open bug: analysis_data_view geoid is NULL, so geoid-based analysis returns nothing](../bugs/views-analysis-data-view-null-geoid.md): Open bug that makes the geoid filter unusable here.
- [Materialized view system: two schemas, one compile-and-refresh loop](views-overview.md): Compile and refresh path for this view.
