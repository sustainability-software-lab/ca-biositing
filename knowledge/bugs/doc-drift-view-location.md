---
type: Bug
title: Docs say materialized views live in views.py; the data_portal views are in data_portal_views/
description: "SQL_FIRST_WORKFLOW says data-portal views are in views.py. The code splits them: views.py holds 7 ca_biositing views, data_portal_views/ holds 12 data_portal modules."
tags: [docs, drift, materialized-views]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:56Z" }
status: stable
code_refs: ["docs/datamodels/SQL_FIRST_WORKFLOW.md", "src/ca_biositing/datamodels/ca_biositing/datamodels/views.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/__init__.py"]
sources: ["docs/datamodels/SQL_FIRST_WORKFLOW.md:106", "src/ca_biositing/datamodels/AGENTS.md:112"]
governance: context
stale_after: "2026-11-16"
---

## Purpose
Point readers at the correct location for each class of view.

## Evidence
- `docs/datamodels/SQL_FIRST_WORKFLOW.md:106-108` says "Materialized views are defined in ... views.py".
- `src/ca_biositing/datamodels/AGENTS.md:112` says views live in `data_portal_views/`, which matches the code.
- `views.py:1-12` docstring covers only the 7 ca_biositing views; `views.py:523` `VIEW_DEFINITIONS`.
- `data_portal_views/__init__.py` re-exports the data_portal views for backward compatibility.

## Impact
A developer following SQL_FIRST_WORKFLOW looks in views.py for `mv_biomass_search` and does not find it.

## Fix
Edit SQL_FIRST_WORKFLOW to say: ca_biositing schema views in `views.py`, data_portal views in `data_portal_views/`.

# Related Concepts
- [Decision: migrations embed frozen compiled SQL instead of importing view expressions](../decisions/views-compiled-sql-snapshots.md): Same split between the two view modules
- [Docs disagree on materialized view count: 7, 9, 10 and ’nine’ vs 12 data_portal modules plus 7 ca_biositing views](doc-drift-materialized-view-count.md): Same drift, count side
