---
type: Fact
title: Current state snapshot (2026-10-16)
description: "Snapshot at a2c8de8 on 2026-10-22: in-flight PRs, open bugs to know first, tech debt, and doc/code contradictions. Regenerate after 2026-11-21."
tags: [status, snapshot, bugs, tech-debt, prs]
generated: { by: "claude-code:claude-opus-5-5", at: "2026-10-22T21:29:34Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing", "alembic/versions", "deployment", ".github/workflows"]
stale_after: "2026-11-21"
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pulls", "https://github.com/sustainability-software-lab/ca-biositing/issues", "commit e41d00d", "commit a2c8de8"]
---

## Snapshot

Taken 2026-10-22 at `a2c8de8` (`main`). Stale after 2026-11-21; regenerate from `gh` and `git log` rather than trusting it later. The previous snapshot was 2026-10-16 at `e41d00d`.

## What changed since 2026-10-16
- 17 commits landed. Infrastructure ETL: 18 flows, 19 table models, migration 0026 (#514, `architecture/pipeline-infrastructure-etl-family`, `facts/pr-514`).
- QC review system: the `qc_review_decision` ledger and ETL upsert guard (#523), portal OIDC auth and `/v1/qc` (#524), live overlay and tray export (#526), docs (#527) (`architecture/qc-review-decision-ledger`, `architecture/qc-review-api-v1-qc`, `architecture/portal-oidc-auth-and-rbac`).
- Dashboards: drift assessment (#517), 3-page resource analytics (#518), QC Audit Workbench and 5-product gallery (#525), fixes (#530, #535) (`architecture/analysis-resource-dashboard-suite`, `architecture/analysis-db-drift-assessment`, `architecture/analysis-qc-audit-workbench`).
- Publishing: GCS dashboards bucket and WIF service accounts (#520), publisher and Pages consumer workflows (#521, #533), generated artifacts untracked with a pre-commit guard (#522) (`decisions/dashboards-gcs-over-committed-exports`, `requirements/generated-artifacts-never-committed`).
- Six PRs closed unmerged, among them the audit platform (#455, #458), the drift monitor (#499, split into #517/#518) and the Sargassum dashboards (#500). Their `facts/pr-*` concepts are deprecated.

## Active work
- 7 open PRs (3 draft); see `facts/prs-open-overview`. Ready and green: volume view name joins (#513, `facts/pr-513`) and an Actions bump (#528, `facts/pr-528`). Conflicting with main: infrastructure ETL first attempt (#482, superseded by #514, inferred), county-map skills (#498). Drafts: docs review (#177), pip-audit (#254), food-processing ETL (#401).
- 100 of 285 issues are open; themes in `facts/issues-*`. New since the last snapshot: EPA load OOM (#534), dedupe the Report a Bug modal (#536, `facts/issue-536-dedupe-report-a-bug`). The residue-factor and volume epic (#505-#512, `facts/issues-residue-factors-volumes`) still carries most data-correctness bugs.

## Open bugs worth knowing first
- Volume estimates: `bugs/corn-stover-grain-routing`, `bugs/wet-pomace-vegetable-cull-dry-basis`, `bugs/tree-nut-residue-factor-dry-basis`, `bugs/volume-view-hardcoded-ids` (fix in #513), `bugs/almond-nsjv-production-discrepancy-2024`.
- Infrastructure ETL: `bugs/infra-load-unbatched-session-oom` (#534), `bugs/infra-epa-upsert-conflict-key-unset`, `bugs/infra-migration-0026-drops-populated-columns`.
- QC review: `bugs/qc-stage2-marks-synced-without-sheet-write`, `bugs/dashboard-client-calls-missing-qc-routes`, `bugs/pipeline-gsheet-qc-writeback-wrong-targets`.
- Dashboards: `bugs/dashboards-production-latest-unpublished`, `bugs/dashboard-seed-fingerprints-cached-in-live-db`, `bugs/dashboards-report-bug-github-repo-mismatch`.
- API: `bugs/views-analysis-data-view-null-geoid`, `bugs/webservice-500-leaks-exception-text` (still open at `main.py:96`).
- Pipeline: `bugs/pipeline-normalization-silent-null-ids`, `bugs/field-samples-without-resource`.
- Infra and CI: `bugs/infra-deployer-trust-scope`, `bugs/deploy-image-tag-latest-drift`, `bugs/ci-fakeredis-prefect-ephemeral-server`.
- Views: `bugs/mv-billion-ton-county-production-unmigrated`.

## Tech debt
- Test gaps: root `tests/` coverage in CI (`bugs/testing-root-tests-outside-ci`); flows and ETL modules without tests (`bugs/etl-flows-without-tests`, `bugs/etl-modules-without-tests`); MVs never run against Postgres in tests (`bugs/datamodels-materialized-views-partially-tested`).
- Duplicate lookup helpers (`decisions/pipeline-lookup-helper-duplication`); stale legacy runner and templates (`bugs/pipeline-stale-legacy-runner-and-templates`).
- FK columns kept as plain ints in several tables (`decisions/datamodels-unconstrained-fk-convention`).
- Pixi lockfile v6 pin blocks dependency updates until a coordinated pixi upgrade (`requirements/tooling-pixi-lockfile-format-pin`; upgrade tracked in #501).
- Root `config.py` appears unused (inferred; see `architecture/system-overview`).

## Doc and code contradictions
- Model count: docs say 91; code has 118 table models at `a2c8de8` (`bugs/doc-drift-model-count`).
- View count and location (`bugs/doc-drift-materialized-view-count`, `bugs/doc-drift-view-location`, `facts/views-sql-artifacts-status`).
- QC and portal docs name routes and settings that do not exist (`facts/docs-qc-portal-readme-drift`); the deployment README describes a dashboard privacy gate the code does not implement (`bugs/doc-drift-dashboard-privacy-gate`).
- Dead references to removed files (`bugs/doc-drift-missing-referenced-artifacts`), infra docs (`bugs/doc-drift-infra`), testing docs (`bugs/doc-drift-testing`).
- `src/ca_biositing/webservice/AGENTS.md:406` says FastAPI `>=0.115.0, <1`, but `pixi.toml:369` pins `>=0.111.0,<0.115.0` (verified 2026-10-22).
- Resolved since the last snapshot: `skills.json` no longer declares missing local skills (#531, `bugs/tooling-skills-json-declares-missing-local-skills`).

# Related Concepts
- [System overview (start here)](../architecture/system-overview.md): cited under ’Tech debt’
- [Issues: datamodels, schema, SQL and materialized views](issues-datamodels-views.md): GitHub issue inventory for SQLModel schema, SQL-as-source-of-truth, FK/constraint work and data_portal materialized view fixes.
- [Open PRs: overview (7)](prs-open-overview.md): cited under ’Active work’
- [Agent harness adopted from UW SSEC template; agent_docs/ retired (Oct 2026)](../decisions/ssec-agent-harness-adoption.md): cited under ’Active work’
- [Decision: centralize data-quality exclusions in common.py (not per-view literals)](../decisions/views-centralized-qc-filters.md): cited under ’Active work’
- [Issues: residue factors, volume estimates and new MV products](issues-residue-factors-volumes.md): cited under ’Active work’
- [#507: Corn stover silage vs grain overestimate (43.5x) and substream double counting](../bugs/corn-stover-grain-routing.md): cited under ’Open bugs worth knowing first’
- [#510: Wet-basis pomace and vegetable cull factors overstate dry tonnage 3.3x to 7.4x](../bugs/wet-pomace-vegetable-cull-dry-basis.md): cited under ’Open bugs worth knowing first’
- [#509: Tree nut and orchard residue factors are not on a dry basis](../bugs/tree-nut-residue-factor-dry-basis.md): cited under ’Open bugs worth knowing first’
- [#506: Volume view uses hard-coded integer IDs instead of name joins](../bugs/volume-view-hardcoded-ids.md): cited under ’Open bugs worth knowing first’
- [#496: 2024 NSJV almond hull and shell volumes disagree in resource_production_record](../bugs/almond-nsjv-production-discrepancy-2024.md): cited under ’Open bugs worth knowing first’
- [Open bug: analysis_data_view geoid is NULL, so geoid-based analysis returns nothing](../bugs/views-analysis-data-view-null-geoid.md): cited under ’Open bugs worth knowing first’
- [Catch-all 500 handler returns raw exception text](../bugs/webservice-500-leaks-exception-text.md): cited under ’Open bugs worth knowing first’
- [Name-to-ID normalization can emit NULL foreign keys without failing](../bugs/pipeline-normalization-silent-null-ids.md): cited under ’Open bugs worth knowing first’
- [#174: 38 of 96 field samples have no resource (stub rows from prepared_sample normalization)](../bugs/field-samples-without-resource.md): cited under ’Open bugs worth knowing first’
- [Open risk: deployer SA trusts any workflow in the repo; PR runs authenticate to GCP](../bugs/infra-deployer-trust-scope.md): cited under ’Open bugs worth knowing first’
- [#491: IMAGE_TAG defaults to ’latest’ and Pulumi GCP provider drift causes spurious cloud diffs](../bugs/deploy-image-tag-latest-drift.md): cited under ’Open bugs worth knowing first’
- [#261: CI fails: Prefect ephemeral server cannot import fakeredis FakeConnection](../bugs/ci-fakeredis-prefect-ephemeral-server.md): cited under ’Open bugs worth knowing first’
- [mv_billion_ton_county_production has no migration and is missing from the package export; mv_biomass_county_production is not exported](../bugs/mv-billion-ton-county-production-unmigrated.md): cited under ’Open bugs worth knowing first’
- [Root tests/ (275 non-harness tests) are not gated by CI; analysis view tests broke unnoticed](../bugs/testing-root-tests-outside-ci.md): cited under ’Tech debt’
- [14 of 20 Prefect flow modules are not imported by any test](../bugs/etl-flows-without-tests.md): cited under ’Tech debt’
- [About 40 ETL, utils and template modules have no test reference](../bugs/etl-modules-without-tests.md): cited under ’Tech debt’
- [5 of 12 materialized views have only SQL-text tests; 7 have none](../bugs/datamodels-materialized-views-partially-tested.md): cited under ’Tech debt’
- [Two competing name-to-id helpers (lookup_utils vs name_id_swap)](../decisions/pipeline-lookup-helper-duplication.md): cited under ’Tech debt’
- [Legacy run_pipeline.py and extract template reference removed paths](../bugs/pipeline-stale-legacy-runner-and-templates.md): cited under ’Tech debt’
- [Unconstrained foreign keys: many FK columns are commented out as ’per repo convention’](../decisions/datamodels-unconstrained-fk-convention.md): cited under ’Tech debt’
- [Do not run pixi commands that rewrite pixi.lock while any pinned pixi is older than 0.68](../requirements/tooling-pixi-lockfile-format-pin.md): cited under ’Tech debt’
- [Docs say 91 models; the code has 112 table models (15 subdirectories is correct)](../bugs/doc-drift-model-count.md): cited under ’Doc and code contradictions’
- [Docs disagree on materialized view count: 7, 9, 10 and ’nine’ vs 12 data_portal modules plus 7 ca_biositing views](../bugs/doc-drift-materialized-view-count.md): cited under ’Doc and code contradictions’
- [Docs say materialized views live in views.py; the data_portal views are in data_portal_views/](../bugs/doc-drift-view-location.md): cited under ’Doc and code contradictions’
- [Status of view SQL reference files and docs: what is stale or orphaned](views-sql-artifacts-status.md): cited under ’Doc and code contradictions’
- [Docs reference files that do not exist: plans/sql_first_workflow.md, scripts/extract_view_sql.py, resources/linkml, migration 9e8f7a6b5c4e](../bugs/doc-drift-missing-referenced-artifacts.md): cited under ’Doc and code contradictions’
- [Known infra documentation drift and dead config (snapshot at e41d00d)](../bugs/doc-drift-infra.md): cited under ’Doc and code contradictions’
- [Test docs and layout drift: missing test files named in READMEs, duplicate conftests, misplaced diagnostics](../bugs/doc-drift-testing.md): cited under ’Doc and code contradictions’
- [skills.json declares two local skills that do not exist in .agents/skills](../bugs/tooling-skills-json-declares-missing-local-skills.md): cited under ’Doc and code contradictions’
- [Revision 0006 changes infrastructure_biodiesel_plants.address from VARCHAR to INTEGER](../bugs/biodiesel-address-type-change.md): Open question: revision 0006 alters the address column type with a USING cast, which looks like a data-loss risk and may be a generation artifact.
- [Analysis MVs filter parameters by underscore names in 0009 but space names in 0015 and 0017](../bugs/analysis-view-parameter-name-spacing.md): Open question: the resource end-use parameter filter changed from underscore names to space names between revisions 0009 and 0015, which may silently drop rows.
- [Issues: webservice / REST API, auth and API docs](issues-webservice-api.md): GitHub issue inventory for the FastAPI webservice: endpoints, JWT/API-key auth, case-insensitive lookups, discovery and performance work.
- [Issues: project planning, milestones and documentation](issues-project-management-docs.md): GitHub issue inventory for PRD, roadmap, milestones, repo restructuring phases, community files and docs-site issues.
- [#152: Pixi tasks hard-code port 5432 for DB access (refresh-views fails on other ports)](../bugs/pixi-refresh-views-hardcoded-port.md): Pixi tasks hard-code local Postgres port 5432 for schema tasks; refresh-views fails on non-5432 machines.
- [#176: QGIS install/open fails after `pixi run qgis`](../bugs/qgis-install-open-error.md): pixi run qgis opens a window with an error on the reporter’s machine; cause not in the issue text.
- [#178: Tracked docs symlinks become unreadable on Windows after checkout](../bugs/windows-docs-symlinks-break.md): Docs files stored as git symlinks break on Windows checkouts.
- [#263: CountyAgRecord: data_source (6 entries) vs dataset ambiguity](../bugs/county-ag-data-source-dataset-ambiguity.md): county ag report writes data_source and dataset rows that overlap; modeling decision still open.
- [#316: County ag report dataset names not standardized (snake_case vs lowercase)](../bugs/county-ag-dataset-name-casing.md): County ag report dataset names need to be lowercase, not snake_case.
- [#264: Recently added resources lack primary ag product linkages](../bugs/resource-missing-primary-ag-product.md): Resources added by some ETL have no primary_ag_product mapping; mapping approach undecided.
- [#324: UC Davis forage analysis shows up as ultimate analysis](../bugs/ultimate-analysis-forage-split.md): UC Davis forage parameters are classified as ultimate analysis in the portal views.
- [#356: Experiment metadata not fully included in the ETL](../bugs/experiment-metadata-missing-etl.md): Experiment metadata beyond what #341 added is still not loaded into the experiment field.
- [#361: State and county name inconsistencies in mv_biomass_volume_estimate](../bugs/state-county-name-inconsistency.md): State/county names differ in form across rows of mv_biomass_volume_estimate; the mapping is split across utils and the view.
- [#368: Resources table missing primary_ag_product, class_id and other fields for many resources](../bugs/resource-attribute-completeness-qc.md): Resource rows are missing primary_ag_product and class_id; resources table needs a QC pass.
- [#375: ICP/XRF value of exactly 0 should mean not detected, not zero](../bugs/icp-xrf-zero-vs-not-detected.md): ICP/XRF zero values are ambiguous (not detected vs real zero); a NULL plus flag design is proposed but undecided.
- [#400: Review data currently filtered out by QC](../bugs/qc-filtered-data-review.md): No process exists yet to review rows dropped by QC filters; log_filter_summary gives counts only.
- [#405: Almond hulls show only N for ultimate analysis (no C, O, H)](../bugs/almond-hull-ultimate-nitrogen-only.md): Almond hull ultimate analysis shows nitrogen only; C and O rows are missing from the view.
- [#428: Prod frontend X-API-Key is not auto-seeded, so a DB reset silently breaks the frontend](../bugs/infra-frontend-api-key-not-seeded.md): Production frontend breaks silently if auth rows are wiped; the frontend API key is not seeded by the deploy pipeline.
- [#446: Pie chart palette has low contrast on some displays](../bugs/pie-chart-low-contrast.md): Pie chart colors have low contrast on some displays.
- [#453: Olive pomace 3HP yields in the portal are unclear and implausible](../bugs/olive-pomace-3hp-yield-view.md): Olive pomace 3HP yields are implausible and have undefined units in the portal; proposed removal from the MV.
- [#454: Bioconversion compare figure overlaps on mobile (iPhone Safari)](../bugs/bioconversion-compare-mobile-layout.md): Bioconversion compare chart text overlaps on mobile Safari.
- [#470: Explore filter min/max defaults should be 0.1 when unset](../bugs/explore-filter-minmax-defaults.md): Explore filters with no min/max should default min to 0.1.
- [#471: Chart axes and filters lack units (% dry weight, dry tons/year, $/ton)](../bugs/chart-axes-units.md): Portal charts and filters lack units; labels need to be added.
- [#477: Filters in the ETL transform are broken or too aggressive](../bugs/transform-broken-filters.md): Some ETL transform filters may drop rows too aggressively; no specific case is identified yet.
- [#487: Shortened ’Structural Carb.’ label should be spelled out](../bugs/structural-carb-abbreviation.md): Portal shows the abbreviation ’Structural Carb.’ in several places.
- [#488: Unready data is shown; bioconversion should be greyed out and gasification tagged beta](../bugs/unready-data-and-beta-tags.md): Unready tabs are visible in the portal and need [beta] or [coming soon] tags.
- [#508: Almond shell copy and walnut basis errors in ag reports](../bugs/almond-shell-copy-walnut-basis.md): Almond shell copy and Merced walnut basis are wrong in county ag report records; Path C lacks dry-matter conversion.
- [Merged PRs: ETL pipelines and source loads](prs-etl-pipelines.md): Index of merged PRs that built or changed ETL extract/transform/load code (pipeline package, flows, source data), grouped by merge month.
- [Merged PRs: webservice (FastAPI), API keys, and auth](prs-webservice-api-auth.md): Index of merged PRs touching the FastAPI webservice: endpoints, JWT and per-client API keys, MCP server, and tests, grouped by merge month.
- [Merged PRs: infrastructure, GCP deployment, and GitHub workflows](prs-infra-deploy-cloud.md): Index of merged PRs for Pulumi/GCP deployment, Cloud Run, Docker images, DB security and reset, and CI/CD workflow wiring, grouped by merge month.
- [Merged PRs: analysis, visualizations, and exports](prs-analysis-visualization-exports.md): Index of merged PRs that changed analysis/ and exports/ visualizations, reports, and gallery, grouped by merge month.
- [Merged PRs: docs, governance, and agent tooling](prs-docs-governance-agents.md): Index of merged PRs for README/CITATION/SECURITY/CHANGELOG, MkDocs and agent docs, AGENTS.md, and agent-skills and task tooling, grouped by merge month.
- [Closed-unmerged PRs (28)](prs-closed-unmerged.md): The 22 PRs closed without merging, with the superseding PR where the titles show one; use before re-proposing similar work.
- [PR #500 (closed unmerged 2026-10-19): Sargassum analysis dashboards, Excel workbook, and reports](pr-500.md): Open PR (created 2026-10-16) packaging Sargassum analysis scripts, dashboards, XLSX, and PNG reports on feat/sargassum-analysis; mergeable with all real checks passing.
- [PR #499 (closed unmerged 2026-10-18): BioCirV DB environment drift monitor and resource explorer dashboards](pr-499.md): Open draft-style feature PR (created 2026-10-16) adding DB drift monitor, resource explorer dashboards, and a dashboard-artifacts CI workflow; blocked by a failing pre-commit.ci check.
- [PR #498 (open, conflicting): ca-county-map and generative_ui agent skills plus CA county boundary assets](pr-498.md): Open PR (created 2026-10-15) adding ca-county-map and generative_ui skills, canonical CA county geojson/SVG, and CRS standards docs; merge conflicts with main must be resolved.
- [PR #495 (closed unmerged 2026-10-19): dependabot bump of prefix-dev/setup-pixi 0.10.2 to 0.11.0](pr-495.md): Open dependabot PR (created 2026-10-14) bumping the setup-pixi GitHub Action across workflows; all checks pass and it is mergeable.
- [PR #473 (closed unmerged 2026-10-19): cotton and sweet potato biomass report](pr-473.md): Open PR (created 2026-08-26) adding a cotton and sweet potato residue report, plots, and generator script for San Joaquin, Stanislaus, and Merced counties; checks pass.
- [PR #455 (closed unmerged 2026-10-19): Skill-Based Data Auditor, Phase 1](pr-455.md): Open PR (created 2026-07-13) for Phase 1 of the skill-based data auditor; 4 deployment-related checks fail (Pulumi Preview and TestPyPI publish jobs), and the thread is a long author status log.
- [PR #401 (open, draft, conflicting): food processing facilities ETL and geocoding](pr-401.md): Draft PR (created 2026-06-05, 41 files) for the food processing facilities ETL with geocoding safety controls and a seed-from-CSV system; checks failing and no review.
- [PR #254 (open, draft, conflicting): pip-audit CI job and dependency CVE fixes](pr-254.md): Draft PR (created 2026-04-06) adding pip-audit to pixi and CI and bumping fastapi, aiohttp, requests, pygments, pip, and starlette; the new audit job fails.
- [PR #177 (open, draft, conflicting): thorough docs review (superseded)](pr-177.md): Draft docs-review PR (created 2026-03-13) that the author says is largely superseded by #225; pre-commit.ci ERROR and a committed binary DB file are open concerns.
- [#534: EPA food manufacturers load is OOM-killed; all 18 infrastructure loads use one unbatched session](../bugs/infra-load-unbatched-session-oom.md): Open infrastructure ETL bug (#534)
- [EPA food manufacturers loader: ON CONFLICT key processing_facility_id is never set by the transform](../bugs/infra-epa-upsert-conflict-key-unset.md): Open infrastructure ETL bug
- [Migration 0026 drops source address and city columns from 7 infrastructure tables without copying data](../bugs/infra-migration-0026-drops-populated-columns.md): Migration risk
- [Stage 2 sync marks a QC decision synced even when no sheet cell was written](../bugs/qc-stage2-marks-synced-without-sheet-write.md): Open QC bug
- [Dashboard client calls /v1/qc routes that do not exist; failures fall back to local-only state](../bugs/dashboard-client-calls-missing-qc-routes.md): Open QC bug
- [Production webservice reads dashboards/production/latest, which no workflow writes](../bugs/dashboards-production-latest-unpublished.md): Open dashboard publishing bug
- [live_db runs can copy seeded minimal fingerprints into the GCS snapshot cache](../bugs/dashboard-seed-fingerprints-cached-in-live-db.md): Open dashboard publishing bug
- [Report a Bug links and the bug-issue API default point at uw-ssec/ca-biositing, not the origin repo](../bugs/dashboards-report-bug-github-repo-mismatch.md): Open dashboard bug
- [deployment/README.md describes a dashboard privacy gate and bucket settings the code does not implement](../bugs/doc-drift-dashboard-privacy-gate.md): Doc and code contradiction
- [Docs for the portal and QC API disagree with the code (webservice README, ETL workflow)](docs-qc-portal-readme-drift.md): Doc and code contradiction
- [PR #513 (open): replace hardcoded IDs with name joins in the volume view and ETL transforms](pr-513.md): Open PR
- [PR #528 (open): dependabot GitHub Actions group bump (setup-pixi 0.11.2, setup-node 7, upload-artifact 7)](pr-528.md): Open PR
- [PR #514 (merged 2026-10-22): infrastructure ETL second attempt, commit f8c9353](pr-514.md): Latest large merge
- [Open issue #536: deduplicate the Report a Bug modal across the dashboard suite](issue-536-dedupe-report-a-bug.md): Open issue
