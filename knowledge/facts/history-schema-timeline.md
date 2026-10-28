---
type: Fact
title: "Alembic revision chain 0001-0024: what each revision changed and when"
description: "Linear list of the live alembic/versions chain (0001-0024) with commit dates, PR numbers, and the effect of each revision group."
tags: [alembic, migrations, history, schema, materialized-views]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:39Z" }
status: stable
code_refs: ["alembic/versions/0001_initial_infra.py", "alembic/versions/0002_permissions.py", "alembic/versions/0003_core_tables.py", "alembic/versions/0004_views_and_indexes.py", "alembic/versions/0006_add_petroleum_pipelines.py", "alembic/versions/0010_mv_fixes.py", "alembic/versions/0011_add_aim2_pretreatment_and_eh_models.py", "alembic/versions/0014_add_gasification_timeseries_table.py", "alembic/versions/0024_centralize_qc_constants_across_data_portal_views.py"]
sources: ["commit db578ad", "commit 0ccbb0f", "commit 2576d03", "commit 85373ad", "commit d4f6b33", "https://github.com/sustainability-software-lab/ca-biositing/pull/340", "https://github.com/sustainability-software-lab/ca-biositing/pull/387", "https://github.com/sustainability-software-lab/ca-biositing/pull/362", "https://github.com/sustainability-software-lab/ca-biositing/pull/492", "git log --follow --name-status -- alembic/versions"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Quick map of the live revision chain. The chain is linear (each `down_revision` is the previous number; verified by reading all 24 headers). Dates are commit dates from `git log -- alembic/versions` at HEAD `e41d00d`. Revision file `Create Date` headers are not reliable (for example `0001` says 2024-05-08, which is the squash-era copy).

## Key files
All files are in `alembic/versions/`. Revision IDs match the filename prefix, except as noted.

## Timeline
| Rev | Commit (date, PR) | What it does |
|---|---|---|
| 0001 | `db578ad` (2026-05-08, #340) | Extensions (postgis etc.) and schemas. Replaced old `97a23076c0d9` (pg_trgm, from `1189a05` 2026-02-23, #129). |
| 0002 | `db578ad`; edited `0ccbb0f` (2026-06-01, #387) | Role `biocirv_readonly`, schema usage grants, default privileges. The default-privilege block was rewritten to use `EXECUTE format(...)` and to tolerate `insufficient_privilege`. |
| 0003 | `db578ad` (2026-05-08, #340) | Consolidated core tables: 107 `create_table` calls, 4 indexes. Replaced `f5c8c031aef9` (`initial_migration_sqlmodel`, `7a41e0e`, 2026-02-12, #112). Header says `Revision ID: 87835166014d`, but the variable is `"0003"`. |
| 0004 | `db578ad` (2026-05-08, #340) | Views and indexes (82 `op.execute`): creates the legacy `ca_biositing` views and the 9 `data_portal` MVs as raw SQL. |
| 0005 | `4ce9559` (2026-05-12, #326) | Recreates all 9 MVs with fixes (mv_biomass_search, pricing, end_uses). |
| 0006 | `f66e296` (2026-05-13, #344) | Biodiesel plants and petroleum pipelines. Adds timestamps, and alters `infrastructure_biodiesel_plants.address` VARCHAR to INTEGER with `USING address::integer` (see bugs/biodiesel-address-type-change). |
| 0007 | `840f7f2` (2026-05-14, #358) | Empty placeholder (`pass` in both directions) titled ’adding exper tracking’. |
| 0008 | `840f7f2` (2026-05-14, #358) | MV recreate for experiment-id proximate filter (docstring copy-pasted from 0005). |
| 0009 | `9697eeb` (2026-05-19, #320) | Almond ETL MV edits. Revision ID is the string `0009_almond_etl_mv_edits`. |
| 0010 | `2576d03` (2026-05-19, #362) | ’mv_fixes’, the first revision from `compile-mv-fixes`. Was named `0009` before the rename in that PR. |
| 0011 | `543adde` (2026-05-21, #370) | New tables `pretreatment_setup`, `enz_hydr_method`, and FKs. |
| 0012 | `543adde` (2026-05-21, #370) | `mv_biomass_fermentation` uses the new setup tables. |
| 0013 | `bd0a35c` (2026-05-21, #371) | `resource_image` unique constraint (name, url, sort_order) becomes NULLS NOT DISTINCT. |
| 0014 | `b328b5f` (2026-06-01, #377) | New table `gasification_timeseries`. |
| 0015 | `5ab52b8` (2026-06-01, #382) | QC filters for analysis views (MV recreate). |
| 0016 | `45b98d1` (2026-06-09, #395) | Adds `gasification_timeseries.reactor_name`. |
| 0017 | `b646a9e` (2026-06-10, #399) | Geography standardization and volume-estimate changes (MV recreate). |
| 0018 | `c0f0b62` (2026-06-18, #422/#431) | ’fix view X’. The name is vague, so check the file before relying on it. MV recreate. |
| 0019 | `7bd24a2` (2026-06-22, #434) | Indexes on the USDA census view. |
| 0020 | `12ff1b8` (2026-06-23, #438) | Volume estimate filtered to San Joaquin, Stanislaus, Merced counties. |
| 0021 | `22507cc` (2026-06-23, #439) | Removes almond meats from volume estimate. |
| 0022 | `d4f6b33` (2026-09-02, #472) | Excludes the jaguar provider from MVs. |
| 0023 | `85373ad` (2026-10-08, #476/#480/#492) | Centralizes QC constants; fixes ICP ppm cap drift in `analysis_data_view`. |
| 0024 | `85373ad` (2026-10-08, #492) | Same QC centralization across all data_portal views. Head at HEAD. |

Groups: (a) squash baseline 0001-0004; (b) MV-only revisions 0005, 0008-0010, 0012, 0015, 0017-0024 (each embeds the full SQL set of the affected views); (c) table/column revisions 0006, 0011, 0013, 0014, 0016.

## How it works
Each MV revision drops and recreates every view it touches, then recreates indexes. Downgrades only drop views and indexes (see facts/mv-downgrade-drops-views). Table revisions use autogenerate-style `op.*` calls.

## Interfaces
- Head: `0024`. Single head, no merge revisions in the live chain.
- Pre-squash revision IDs (for example `f5c8c031aef9`, `9e8f7a6b5c54`, `63c0fedd3446`) exist only in `alembic/versions_old/`. A database stamped at one of those IDs cannot find its revision in the live chain.

## Gotchas
- Gap of about 10 weeks between 0021 (2026-06-23) and 0022 (2026-09-02) with no revisions in between.
- Revision 0008 was modified in place in `9697eeb` (2026-05-19, PR #320) after its creation in `840f7f2` (2026-05-14). Whether that was before any shared deploy is unknown.

## History
See the commit column. The squash that created 0001-0004 is `db578ad` (PR #340). The 0002 edit is in `0ccbb0f` (PR #387).

## Open questions
- Which environments are stamped at which revision now (inferred: staging and prod were reset during #340 and #387; confirm with `alembic current` against each DB).

# Related Concepts
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): The env and tooling that apply this chain.
- [Why alembic history was squashed to 0001-0004 and old revisions moved to versions_old/](../decisions/squash-migration-history.md): The squash that started the chain at 0001.
- [Downgrading an MV revision drops the views; it does not restore the previous definition](mv-downgrade-drops-views.md): Explains what downgrading the MV revisions does.
- [System overview (start here)](../architecture/system-overview.md): Hub entry for the overall system; the schema this chain builds feeds the ETL and API.
