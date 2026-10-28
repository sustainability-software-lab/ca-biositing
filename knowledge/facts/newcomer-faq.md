---
type: Fact
title: Newcomer FAQ
description: "About 20 common questions (add a flow, column, view or endpoint; where the API gets data; why flows hang; how deploys work) answered with links to concepts."
tags: [faq, onboarding, how-to]
generated: { by: "claude-code:claude-opus-5-5", at: "2026-10-22T21:29:10Z" }
status: stable
governance: context
code_refs: ["pixi.toml", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows", "src/ca_biositing/webservice/ca_biositing/webservice/v1"]
sources: ["AGENTS.md", ".agents/rules/schema-and-migrations.md", "pixi.toml", "commit a2c8de8"]
---

## Questions and where the answer lives

1. **Where do I start?** `architecture/system-overview`, then `facts/glossary`.
2. **How do I set up and start the local stack?** `pixi install`, then `pixi run start-services` (`architecture/infra-local-topology`, `architecture/tooling-task-services-and-etl`).
3. **How do I add a new ETL flow?** Write extract/transform/load tasks under `pipeline/etl/`, wire them in `flows/<name>.py` as in `architecture/pipeline-flow-wiring`, register it in the master runner (`architecture/pipeline-flow-registry-and-run`), and keep model imports inside functions (`requirements/pipeline-lazy-model-and-settings-imports`).
4. **How do I run one flow?** `pixi run run-single-flow <module>`; see `architecture/pipeline-flow-registry-and-run` for modules that resolve the wrong flow.
5. **Which flows must run before others?** Geography first, resources before residue factors and images; see `architecture/pipeline-flow-registry-and-run` and each `architecture/flow-*` concept.
6. **How do I add a column or table?** Edit the SQLModel class, import new models in `models/__init__.py`, `pixi run migrate-autogenerate -m "..."`, review, `pixi run migrate` (`requirements/datamodels-register-new-models`, `requirements/autogenerate-then-review`).
7. **How do I change a materialized view?** Edit the `select()` expression, `pixi run compile-mv-fixes -m "..."`, migrate, refresh (`architecture/views-compile-workflow`, `requirements/mv-migrations-embed-raw-sql`).
8. **Why did my view change not show up?** Autogenerate ignores MVs and views need a refresh (`architecture/views-overview`, `architecture/views-refresh`).
9. **How do I exclude bad data from the portal?** Add it to the filter lists in `data_portal_views/common.py` (`architecture/views-data-quality-filters`, `decisions/views-centralized-qc-filters`) and mirror it in analysis scripts (`requirements/analysis-qc-filter-parity`).
10. **How do I add an API endpoint?** Add a router under `v1/feedstocks/`, a static-method service querying a `ca_biositing` view, and a response model (`architecture/webservice-overview`, `architecture/webservice-usda-query-services`); admin routes must be JWT-only (`requirements/webservice-admin-endpoints-jwt-only`). Portal routes under `/v1/qc` and `/v1/dashboards` use portal auth instead (`architecture/portal-oidc-auth-and-rbac`).
11. **Where does the API get its data?** Mostly `ca_biositing` schema views via `_canonical_views.py`, plus `resource` and `resource_availability` tables (`architecture/webservice-endpoints`).
12. **How does API auth work?** JWT for people and admins, hashed API keys with rate limits for clients (`architecture/webservice-auth-jwt`, `architecture/webservice-api-keys`, `decisions/webservice-jwt-and-api-key-split`).
13. **What does the frontend use?** Separate repo pinned as `frontend/`; usage is inferred (`architecture/frontend`).
14. **How do I run tests, and what runs in CI?** `pixi run test` locally; CI runs a subset (`architecture/testing`, `facts/testing-ci-scope`).
15. **Why is my flow hanging in Docker?** Module-level model, settings or DB imports (`requirements/pipeline-lazy-model-and-settings-imports`, `requirements/datamodels-lazy-engine`) or wrong DB host (`requirements/pipeline-db-host-in-containers`).
16. **Google Sheets extraction fails. Why?** Missing or wrong `credentials.json` (`requirements/pipeline-gsheet-credentials-file`).
17. **How is it deployed?** Pulumi stacks per environment on GCP Cloud Run and Cloud SQL, rolled by GitHub Actions (`architecture/infra-cloud-topology`, `architecture/infra-ci-cd-pipelines`, `requirements/infra-deploy-invariants`).
18. **Two people added migrations at once. What now?** Keep a single linear head (`requirements/single-linear-head`); never edit applied revisions (`requirements/never-edit-applied-migrations`).
19. **Why is `alembic/versions_old/` there?** The May 2026 squash (`decisions/squash-migration-history`).
20. **Why hand-written SQLModel instead of LinkML?** `decisions/linkml-to-sqlmodel-alembic`.
21. **Who works on what?** `facts/history-contributors`; what changes most: `facts/history-churn`.
22. **What must I do before opening a PR?** `pixi run pre-commit-all`, the PR template and AI disclosure (`requirements/tooling-pr-ai-disclosure-and-preflight`, `decisions/ai-contribution-policy`).
23. **How does QC review work?** Analysts flag and decide records in the dashboards; decisions land in `qc_review_decision`, ETL reloads leave them alone, and an admin syncs them to the sheets (`architecture/qc-review-decision-ledger`, `architecture/qc-review-api-v1-qc`, `decisions/qc-decisions-protected-from-etl-overwrite`).
24. **Where do the dashboards come from, and can I commit them?** CI builds them and publishes to GCS; never commit `exports/plots/` (`requirements/generated-artifacts-never-committed`, `architecture/ci-dashboard-artifacts-publisher`).
25. **How do I check that staging and production databases match?** The drift assessment (`architecture/analysis-db-drift-assessment`, skill `db-drift-assessment`).
26. **How do I add an infrastructure dataset?** Follow the shared pattern in `architecture/pipeline-infrastructure-etl-family` and keep reloads idempotent (`requirements/infra-loader-idempotent-rerun`).
27. **What is broken or in flight right now?** `facts/current-state`.

# Related Concepts
- [System overview (start here)](../architecture/system-overview.md): first answer
- [How a pipeline flow wires extract, transform, and load](../architecture/pipeline-flow-wiring.md): how to add a flow
- [New table models must be re-exported and migrated; views are not autogenerated](../requirements/datamodels-register-new-models.md): how to add a table
- [Table changes: edit SQLModel, run migrate-autogenerate, then review the generated revision](../requirements/autogenerate-then-review.md): migration workflow
- [compile_mv_fixes.py: turning view expressions into an Alembic migration](../architecture/views-compile-workflow.md): how to change a view
- [Admin and key-management routes must stay JWT-only](../requirements/webservice-admin-endpoints-jwt-only.md): rule for new admin endpoints
- [Service layer behind feedstock queries and canonical view selection](../architecture/webservice-usda-query-services.md): service pattern for new endpoints
- [Import models and settings inside task or flow bodies](../requirements/pipeline-lazy-model-and-settings-imports.md): why flows hang
- [DATABASE_URL uses host db inside containers; localhost on host](../requirements/pipeline-db-host-in-containers.md): DB host inside containers
- [Google Sheets extracts need a service-account credentials.json](../requirements/pipeline-gsheet-credentials-file.md): Sheets credentials
- [Do not edit a revision that has been applied to a shared database; add a new revision](../requirements/never-edit-applied-migrations.md): fix forward
- [Why alembic history was squashed to 0001-0004 and old revisions moved to versions_old/](../decisions/squash-migration-history.md): versions_old explained
- [Why datamodels moved from LinkML codegen to hand-written SQLModel + Alembic (PR #112)](../decisions/linkml-to-sqlmodel-alembic.md): why SQLModel
- [PRs need pre-commit passing, the full PR template, AI disclosure and human diff review](../requirements/tooling-pr-ai-disclosure-and-preflight.md): PR checklist
- [Contributors by commit count and area (snapshot at e41d00d)](history-contributors.md): who to ask
- [GitHub Actions deploy chain: docker-build, staging/production deploy, migrations, ETL trigger](../architecture/infra-ci-cd-pipelines.md): deploy path
- [Glossary](glossary.md): cited under ’Questions and where the answer lives’
- [Local Docker Compose topology (db, setup-db, Prefect server/worker, oauth2-proxy)](../architecture/infra-local-topology.md): cited under ’Questions and where the answer lives’
- [Pixi tasks for Docker services, psql access and ETL triggering](../architecture/tooling-task-services-and-etl.md): cited under ’Questions and where the answer lives’
- [How flows are registered and run (master flow, run-single-flow, list-flows)](../architecture/pipeline-flow-registry-and-run.md): cited under ’Questions and where the answer lives’
- [Migrations must not import SQLAlchemy models or view definitions](../requirements/mv-migrations-embed-raw-sql.md): cited under ’Questions and where the answer lives’
- [Materialized view system: two schemas, one compile-and-refresh loop](../architecture/views-overview.md): cited under ’Questions and where the answer lives’
- [refresh_all_views: refresh order, concurrency, and callers](../architecture/views-refresh.md): cited under ’Questions and where the answer lives’
- [common.py: the single gatekeeper for view data-quality filters](../architecture/views-data-quality-filters.md): cited under ’Questions and where the answer lives’
- [Decision: centralize data-quality exclusions in common.py (not per-view literals)](../decisions/views-centralized-qc-filters.md): cited under ’Questions and where the answer lives’
- [Analysis chart exclusions must match the portal QC definitions](../requirements/analysis-qc-filter-parity.md): cited under ’Questions and where the answer lives’
- [Webservice package layout and app factory](../architecture/webservice-overview.md): cited under ’Questions and where the answer lives’
- [Full webservice endpoint table (36 routes)](../architecture/webservice-endpoints.md): cited under ’Questions and where the answer lives’
- [JWT login, cookie transport, and refresh in the webservice](../architecture/webservice-auth-jwt.md): cited under ’Questions and where the answer lives’
- [Per-client X-API-Key auth with rate limiting](../architecture/webservice-api-keys.md): cited under ’Questions and where the answer lives’
- [Why the webservice has both JWT users and per-client API keys](../decisions/webservice-jwt-and-api-key-split.md): cited under ’Questions and where the answer lives’
- [frontend/ git submodule (cal-bioscape-frontend), pin, and API consumption](../architecture/frontend.md): cited under ’Questions and where the answer lives’
- [Test suite layout, how to run each suite, and fixture map](../architecture/testing.md): cited under ’Questions and where the answer lives’
- [What the CI test jobs run, and what they skip](testing-ci-scope.md): cited under ’Questions and where the answer lives’
- [Do not create the DB engine or open connections at import time](../requirements/datamodels-lazy-engine.md): cited under ’Questions and where the answer lives’
- [GCP cloud topology per environment (Cloud Run, Cloud SQL, AR proxies, GCS, WIF)](../architecture/infra-cloud-topology.md): cited under ’Questions and where the answer lives’
- [Deploy and infra invariants a change must keep](../requirements/infra-deploy-invariants.md): cited under ’Questions and where the answer lives’
- [Keep one Alembic head: linear chain, merge revisions for conflicts](../requirements/single-linear-head.md): cited under ’Questions and where the answer lives’
- [Most-churned files and what the churn implies (snapshot at e41d00d)](history-churn.md): cited under ’Questions and where the answer lives’
- [AI-assisted contributions: disclose, own, and credit with Assisted-by (never Co-Authored-By)](../decisions/ai-contribution-policy.md): cited under ’Questions and where the answer lives’
- [Current state snapshot (2026-10-16)](current-state.md): cited under ’Questions and where the answer lives’
- [QC review decision ledger (qc_review_decision table, lifecycle, seed CSV)](../architecture/qc-review-decision-ledger.md): Answers how QC review works
- [Generated dashboards, fingerprints, drift reports and insights are never committed to git](../requirements/generated-artifacts-never-committed.md): Answers whether dashboards can be committed
- [Multi-environment DB drift assessment (4 layers, local/staging/production)](../architecture/analysis-db-drift-assessment.md): Answers how to compare environments
- [Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern](../architecture/pipeline-infrastructure-etl-family.md): Answers how to add an infrastructure dataset
- [Infrastructure loaders must be idempotent: a re-run updates rows and never duplicates them](../requirements/infra-loader-idempotent-rerun.md): Rule for infrastructure reloads
