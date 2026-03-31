# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project does not yet use versioned releases — all changes appear under
**Unreleased**.

## [Unreleased]

### Added

- JWT authentication for the webservice REST API (#139)
- PyPI releases for `ca-biositing-datamodels`, `ca-biositing-pipeline`, and
  `ca-biositing-webservice` namespace packages (#151)
- Seed admin user via Pulumi and Cloud Run job (#175)
- GCP staging deployment automation via GitHub Actions (#189)
- API discovery endpoints for analysis, USDA Census, and USDA Survey families,
  returning available crops, resources, geoids, and parameters (#170)
- Full integration test coverage for webservice endpoints (#170)
- Aim 2 Fermentation ETL flows and analytical view refinements (#154)
- Extended USDA commodity mapping with more resources (#173)
- Alembic migrations validation CI workflow (#164)
- `pg_trgm`, `unaccent`, and `btree_gin` PostgreSQL extensions (#129)
- Static OpenAPI spec committed to docs for offline API browsing

### Changed

- Cloud Run images switched from GCR to GHCR (#192)
- GHCR images routed through Artifact Registry remote repository for reliability
  (#193)
- Removed pixi lock file from version control (#185)
- Streamlined namespace package READMEs for PyPI (#184)
- Updated all repository links after repo rename/move (#180)
- CI pixi tasks moved to shell scripts for cross-platform compatibility (#190)

### Fixed

- Analysis API blocked by empty `location_address` table (#149)
- USDA crop normalization and `api_name` transition (#155)
- Docker builds broken after pixi lock file removal (#187)
- Deployer service account missing storage access to Cloud Build bucket (#191)

[Unreleased]:
  https://github.com/sustainability-software-lab/ca-biositing/compare/HEAD...HEAD
