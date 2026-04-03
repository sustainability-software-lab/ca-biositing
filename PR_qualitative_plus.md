# Qualitative Plus PR Summary

## Summary

This branch implements the qualitative-plus schema and materialized-view work for the BEAM Portal contract.

### Schema changes
- Added the new record/assumption tables:
  - resource_price_record
  - resource_transport_record
  - resource_storage_record
  - resource_end_use_record
  - resource_production_record
  - technical_assumption
  - method_assumption
- Preserved explicit numeric precision for technical assumptions.

### Materialized views
- Updated mv_biomass_search with:
  - storage and transport snippets
  - carbon_percent, hydrogen_percent, cn_ratio
  - Sargassum exclusion
- Updated mv_biomass_county_production for the current contract grain.
- Updated mv_usda_county_production to include all years.
- Added mv_biomass_pricing and mv_biomass_end_uses using observation-backed pivots.
- Added UNIQUE indexes required for concurrent refresh.

### Validation performed
- Applied pending Alembic migrations successfully.
- Verified materialized views exist in data_portal.
- Ran focused datamodel tests: passed.
- Ran targeted pre-commit checks on changed files: passed.

### Reviewer notes
- Current local data contains rows for mv_usda_county_production.
- mv_biomass_search contains rows in the local test DB.
- mv_biomass_pricing and mv_biomass_end_uses currently return zero rows in the local DB because their source record tables are empty there; this is expected and not a SQL error.
- Validated after a service restart, but not after tearing down service volumes and rebuilding from scratch.

### Quick inspection queries
- SELECT version_num FROM alembic_version;
- SELECT matviewname FROM pg_matviews WHERE schemaname = 'data_portal';
- SELECT * FROM data_portal.mv_biomass_search LIMIT 5;
- SELECT * FROM data_portal.mv_biomass_county_production LIMIT 5;
- SELECT * FROM data_portal.mv_biomass_pricing LIMIT 5;
- SELECT * FROM data_portal.mv_biomass_end_uses LIMIT 5;
- SELECT DISTINCT dataset_year FROM data_portal.mv_usda_county_production ORDER BY 1 DESC;
