---
type: Fact
title: Glossary
description: "Domain terms (resource, observation, residue factor, Aim 1/Aim 2, geoid...) and project jargon (MV, compile-mv-fixes, lineage, WIF), each with where it appears in code."
tags: [glossary, domain, terms, onboarding]
generated: { by: "claude-code:claude-opus-5-5", at: "2026-10-22T21:28:59Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows"]
sources: ["README.md", "docs/database_conventions.md", "commit e41d00d", "commit a2c8de8"]
---

## Domain terms

| Term | Meaning | Where in code |
|---|---|---|
| BioCirV / Cal BioScape | The research project and its public data portal | README.md, `frontend/` submodule |
| Aim 1 | Feedstock collection and lab characterization | `models/aim1_records/`, Aim 1 Google Sheet (`etl/extract/basic_sample_info.py`) |
| Aim 2 | Conversion experiments: pretreatment, fermentation, gasification, autoclave | `models/aim2_records/`, `flows/aim2_bioconversion.py`, `flows/thermochem_etl.py` |
| Resource | A biomass feedstock type (for example almond hulls); hub of most FKs | `models/resource_information/`, table `resource` |
| Primary ag product | The crop or commodity a resource comes from | table `primary_ag_product`, `flows/primary_ag_product.py` |
| Field sample / prepared sample | Physical sample collected, then processed for analysis | `models/field_sampling/`, `models/sample_preparation/` |
| Analysis record | One lab or experiment run (provenance and `qc_pass`, no values) | `*_record` tables in aim1/aim2 records |
| Observation | One measured value keyed by record_id, record_type, parameter, unit | `models/general_analysis/`, table `observation` |
| Parameter / unit / method | What is measured, its scale, and the procedure | `models/methods_parameters_units/` |
| Residue factor | Residue yield per unit of crop (min/mid/max, wet or dry basis) | table `residue_factor`, `flows/residue_factors_flow.py` |
| Availability | Months a resource can be harvested in a place | table `resource_availability` |
| Geoid / place | County FIPS code; PK of `place` | `models/places/`, `data/static/ca_counties.csv` |
| Provider | Organization that supplied a sample (codename only) | `models/people/` |
| QC pass / QC filters | Per-record quality flag and the exclusion lists applied in views | `data_portal_views/common.py` |
| Billion Ton (BT2023) | DOE 2023 biomass supply dataset | `flows/billion_ton_etl.py` |
| LandIQ | Statewide crop-mapping polygons (2024) | `flows/landiq_etl.py` |
| USDA NASS census / survey | Federal ag statistics via Quick Stats API | `flows/usda_etl.py`, `usda_census_view` |
| County ag report | County agricultural commissioner annual reports | `flows/county_ag_report_etl.py` |
| NSJV | North San Joaquin Valley (almond data scope) | `flows/almond_nsjv_etl.py` |
| Volume paths A-D | Four ways `mv_biomass_volume_estimate` derives residue tonnage | `data_portal_views/mv_biomass_volume_estimate.py` |
| Infrastructure datasets | 18 facility and line datasets (landfills, biorefineries, pipelines, railways, ...) loaded by `flows/<dataset>.py` | `models/infrastructure/`, `architecture/pipeline-infrastructure-etl-family` |
| Decon vessel | Reactor or plate used in Aim 2 runs | `models/experiment_equipment/` |

## Project jargon

| Term | Meaning | Where |
|---|---|---|
| MV | PostgreSQL materialized view | `views.py`, `data_portal_views/` |
| `ca_biositing` vs `data_portal` schema | API-facing views vs portal/analysis views | `decisions/views-two-schemas` |
| compile-mv-fixes | Pixi task compiling view expressions into a migration | `scripts/compile_mv_fixes.py` |
| refresh-views | Pixi task running `refresh_all_views` | `views.py` |
| etl_run / lineage group | Provenance rows stamped onto each loaded record | `models/core/`, `utils/lineage.py` (see `architecture/pipeline-lineage-tracking`) |
| name-id swap / normalization | Replacing name columns with FK ids, inserting missing lookups | `utils/name_id_swap.py` |
| Master runner / AVAILABLE_FLOWS | Ordered dict of flows the deployment runs | `resources/prefect/run_prefect_flow.py` |
| run-single-flow | Pixi task running one flow module in the worker | `pixi.toml` |
| SQL-first workflow | Earlier pgschema-based schema path, now validation only | `docs/datamodels/SQL_FIRST_WORKFLOW.md` |
| versions_old | Pre-squash Alembic revisions kept for reference | `alembic/versions_old/` |
| Agent harness / rules / skills | Instructions for AI agents | `AGENTS.md`, `.agents/rules/`, `.agents/skills/` |
| OKF bundle | This knowledge base | `knowledge/`, `pixi run okf` |
| DEPLOY_ENV / stack | Pulumi stack selector (staging, production) | `deployment/cloud/gcp/infrastructure/config.py` |
| WIF | Workload Identity Federation for keyless CI deploys | `deployment/cloud/gcp/infrastructure/wif.py` |
| QC review decision | An analyst or admin verdict on one analysis record, kept in `qc_review_decision` | `models/qc/`, `architecture/qc-review-decision-ledger` |
| Stage 1 / Stage 2 | Stage 1 records a decision in the DB; Stage 2 (admin sync) writes it back to the source Google Sheet | `services/qc_ledger_service.py`, `architecture/gsheet-qc-writeback` |
| Protected record | A record with an unsynced QC decision; ETL reloads keep its `qc_pass` and note | `utils/qc_protected_records.py`, `decisions/qc-decisions-protected-from-etl-overwrite` |
| Portal / analyst / admin | BioCirV dashboard sign-in (Google ID token, allowlist) and its two roles | `services/portal_auth.py`, `architecture/portal-oidc-auth-and-rbac` |
| Products 1-5 / gallery | The generated BioCirV dashboards and their index page | `analysis/metadata/`, `architecture/analysis-resource-dashboard-suite` |
| Tray / QC Audit Workbench | Dashboard selection of flagged records and the Product 4 page that reviews them | `analysis/metadata/resource_audit_workbench.py`, `architecture/analysis-qc-audit-workbench` |
| Drift assessment / fingerprint | 4-layer comparison of local, staging and production databases; per-env JSON snapshot | `analysis/audit/db_environment_drift.py`, `architecture/analysis-db-drift-assessment` |
| Dashboards bucket | Pulumi-managed GCS bucket holding published dashboards under `dashboards/<env>/` | `deployment/cloud/gcp/infrastructure/storage.py`, `architecture/infra-dashboards-gcs-bucket` |
| `db` host | Postgres hostname inside Docker; `localhost` outside | `resources/docker/docker-compose.yml` |

# Related Concepts
- [System overview (start here)](../architecture/system-overview.md): where the terms fit in the system
- [Domain terms as used in the datamodels: resource, field sample, prepared sample, analysis record, observation, parameter, unit, method, dataset](domain-core-terms.md): full definitions of data-model terms
- [Research aims: Aim 1 feedstock characterization vs Aim 2 conversion experiments](domain-aims-aim1-aim2.md): Aim 1 and Aim 2 in detail
- [common.py: the single gatekeeper for view data-quality filters](../architecture/views-data-quality-filters.md): QC filter terms
- [ETL run and lineage group tracking](../architecture/pipeline-lineage-tracking.md): etl_run and lineage terms
- [Name-to-ID normalization (get-or-create reference rows)](../architecture/pipeline-name-id-normalization.md): name-id swap
- [Decision: views split across ca_biositing and data_portal schemas](../decisions/views-two-schemas.md): ca_biositing vs data_portal
- [Lookup names and qualitative values are stored lowercase, with lineage fields](../decisions/lowercase-lookup-conventions.md): naming conventions for lookup values
- [Snapshot: datamodels tables with no ETL or view references (name-based grep at e41d00d)](domain-models-usage-snapshot.md): About 29 model classes in this slice are not referenced by pipeline, views or webservice by class name, so they may be unused, loaded under other names, or dormant.
- [QC review decision ledger (qc_review_decision table, lifecycle, seed CSV)](../architecture/qc-review-decision-ledger.md): Defines QC review decision, Stage 1 and Stage 2
- [BioCirV portal auth: Google OIDC, 2-role RBAC, isolated cookie](../architecture/portal-oidc-auth-and-rbac.md): Defines portal roles
- [Product 4 QC Audit Workbench: Stage 1 decisions, Stage 2 Sheets sync, tray handoff](../architecture/analysis-qc-audit-workbench.md): Defines tray and workbench
- [GCS dashboards bucket, its service accounts, WIF bindings, and runtime reads](../architecture/infra-dashboards-gcs-bucket.md): Defines the dashboards bucket
