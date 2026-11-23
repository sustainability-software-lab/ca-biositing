---
type: Decision
title: "Decision: views split across ca_biositing and data_portal schemas"
description: "Why views sit in two schemas (ca_biositing vs data_portal); rationale is undocumented, so this records the known facts and labeled inferences."
tags: [decision, views, schemas, data-portal, permissions]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:33Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/views.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/__init__.py", "resources/config/db_reset.yaml", "docs/operations/DB_RESET.md"]
sources: ["commit 930d868", "https://github.com/sustainability-software-lab/ca-biositing/pull/220", "resources/assets/data_portal_spec_docs/20260420", "docs/operations/DB_RESET.md"]
governance: context
---

## Decision
Two Postgres schemas hold materialized views:
- `ca_biositing`: `views.py` views (analysis, USDA, LandIQ, Billion Ton). Read by the webservice.
- `data_portal`: `data_portal_views/` views (search, composition, volume, pricing, end uses, and so on). Read by analysis scripts and the portal.

## What is documented
- `data_portal` was introduced in 930d868 (PR #220, 2026-04-01): "Feat: Data-portal-schema With Views".
- Every compiled migration grants `SELECT` on both schemas to `biocirv_readonly` (see the 0024 template), and `resources/config/db_reset.yaml` / `docs/operations/DB_RESET.md` define the read-only role.
- `refresh_all_views` refreshes `ca_biositing` non-concurrently and `data_portal` discovered-and-concurrent.

## Rationale (inferred; confirm with maintainers)
- The `data_portal` schema looks like the public-facing surface: a separate schema makes it easy to grant or refresh independently and to see which views the portal uses. The `resources/assets/data_portal_spec_docs/20260420` folder suggests a spec drove the set (not read in this slice).
- `ca_biositing` holds views that mirror the internal analysis tables and are used by the API.

## Alternatives
Not recorded in the repo. A single schema was evidently not chosen, but no comparison was found.

## Governance
Context.

# Related Concepts
- [ca_biositing schema views in views.py: definitions, order, and consumers](../architecture/views-ca-biositing-schema.md): Views that live in the ca_biositing side of the split.
- [data_portal materialized views: modules, grain, and consumers](../architecture/views-data-portal-matviews.md): Views that live in the data_portal side of the split.
- [Materialized view system: two schemas, one compile-and-refresh loop](../architecture/views-overview.md): Parent overview.
