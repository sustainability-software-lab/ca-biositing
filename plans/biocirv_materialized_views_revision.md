# Handoff: Materialized Views Revision

**Context:** The core join logic for the `data_portal` materialized views has
been updated to align with the BIOCIRV Specification. Migrations have been
applied and views are populated.

**Current Status:**

- `Resource` table has a new `uri` column.
- `mv_biomass_search` includes aggregated moisture, sugar (glucose+xylose), and
  analytical flags.
- `mv_biomass_fermentation` is functional (33 rows) after fixing the `Strain`
  join.
- **Pretreatment Integration Complete**: `PretreatmentRecord` data is now
  integrated into `mv_biomass_search`, `mv_biomass_composition`, and
  `mv_biomass_sample_stats`.
- Documentation in
  [`src/ca_biositing/datamodels/AGENTS.md`](../src/ca_biositing/datamodels/AGENTS.md)
  has been updated with critical migration and view update workflows.

**Immediate Next Steps for the Agent:**

1. **Phase 2 Tags:** Implement the logic to derive descriptive tags (e.g., "high
   moisture") based on whether a resource is in the top/bottom 10% for its
   category in `mv_biomass_search`.
2. **Pricing View:** Finalize `mv_biomass_pricing` once the source columns in
   `UsdaMarketRecord` are ready.

---

# Plan: BIOCIRV Materialized Views Revision

This plan outlines the revisions required for the `data_portal` materialized
views to align with the [BIOCIRV-Materialized Views
Specification-160326-153133.pdf](BIOCIRV-Materialized Views
Specification-160326-153133.pdf).

## 1. Overview of Gaps

The current implementation in
[`data_portal_views.py`](../src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views.py)
lacks several pre-aggregated metrics and experimental metadata fields required
by the frontend prototype.

## 2. Revision Details

### 2.1 `mv_biomass_search`

- **Grain:** One row per `Resource`.
- **Pretreatment Flag:** `has_pretreatment` flag indicating existence of records
  in `pretreatment_record`.
- **Tags (PHASE 2):** Derivation of descriptors based on summary statistics
  (e.g., "high sugar" for top 10% glucose+xylose). _This is the primary
  remaining task._

### 2.2 `mv_biomass_composition`

- **Revisions:** Expanded the `union_all` to include `PretreatmentRecord`
  measurements.

### 2.3 `mv_biomass_fermentation`

- **Revisions:** Changed `Strain` join to `outerjoin` to ensure records without
  specific strains are preserved. Verified 33 rows present.

### 2.4 `mv_biomass_sample_stats`

- **Revisions:** Included `PretreatmentRecord` in distinct counts for samples
  and datasets.

## 3. Performance & Workflow

- **Crucial:** See
  [`src/ca_biositing/datamodels/AGENTS.md`](../src/ca_biositing/datamodels/AGENTS.md)
  for instructions on how to update materialized views and handle macOS
  migration connectivity (`POSTGRES_HOST=localhost`).

## 4. Execution Summary (Updated 2026-03-16)

### 4.1 Completed

- Added `uri` field to `Resource` model.
- Fixed `mv_biomass_fermentation` row count issue.
- Integrated `PretreatmentRecord` into the characterization and stats views.
- Updated developer documentation for migrations.
- Applied migration `3a9adc1f9228`.
- **Phase 2 Tags**: Implemented percentile-based array column for resource
  descriptors in `mv_biomass_search` (moisture, sugar, lignin, ash). Applied
  migration `7d1e5a1f0c38`.

### 4.2 Pending (Handoff Target)

- **Pricing View**: Final implementation once `UsdaMarketRecord` schema is
  validated.
