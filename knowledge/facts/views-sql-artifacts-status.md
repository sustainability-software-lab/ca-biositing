---
type: Fact
title: "Status of view SQL reference files and docs: what is stale or orphaned"
description: "Snapshot of which view SQL files, counts, and doc claims disagree with the code as of HEAD e41d00d; check here before trusting any reference SQL or view count."
tags: [views, docs, stale, sql-reference, snapshot]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:30Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/sql_schemas/main.sql", "resources/sql/create_analytical_views.sql", "alembic/VIEW_SQL_REFERENCE.md", "docs/datamodels/SQL_FIRST_WORKFLOW.md", "docs/datamodels/ALEMBIC_VIEW_WORKFLOW.md", "scripts/compile_mv_fixes.py", "scripts/view_diagnostics.py"]
sources: ["commit 85373ad", "commit 9d1e16f", "commit d961724", "commit 7a41e0e", "alembic/VIEW_SQL_REFERENCE.md", "docs/datamodels/ALEMBIC_VIEW_WORKFLOW.md", "src/ca_biositing/datamodels/AGENTS.md"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Snapshot of the mismatches found while documenting the views slice. Verify against the code before acting on any of these.

## Key files and findings (as of e41d00d, 2026-10-16)
| Artifact | Status |
|---|---|
| `src/.../sql_schemas/main.sql` | pgschema dump of `public` tables only (about 93 `CREATE TABLE`). No MVs, no `ca_biositing.` or `data_portal.` references. Last changed 7a41e0e. |
| `resources/sql/create_analytical_views.sql` | Header says "[GENERATED] ... DO NOT EDIT" and claims to match `views.py`. Contains 7 `CREATE MATERIALIZED VIEW` for ca_biositing. No file in the repo references it (grep). Last changed 9d1e16f (2026-03-18). Likely orphaned (inferred). |
| `alembic/VIEW_SQL_REFERENCE.md` | "Generated 2026-04-04". Covers 9 data_portal views. Several sections say "See `scripts/extract_view_sql.py`", which does not exist. Predates migrations 0010-0024. Stale. |
| `docs/datamodels/SQL_FIRST_WORKFLOW.md` | Says views are defined in `views.py`. The data_portal views are in `data_portal_views/`. Stale. |
| `src/ca_biositing/datamodels/AGENTS.md` | Says `views.py` has "7 views" (there are 8 plus one extra) and "Nine materialized views" (compile list has 13). Stale. |
| `docs/datamodels/ALEMBIC_VIEW_WORKFLOW.md` | Says "10 data portal MVs" with a table that omits `mv_biomass_volume_estimate` and lists `mv_biomass_county_production`. Stale. |
| `scripts/compile_mv_fixes.py` docstring | "9 views"; the list has 13. Stale. |
| `views.py` module docstring | "7 views"; `analysis_average_view` described as "raw SQL" (it is `select()`). Stale. |
| `audit/output/filter_baseline/` (commit 85373ad) | Baseline counts for "19 MVs". Not reconciled with the 13-view compile list (inferred: includes legacy and ca_biositing views). |
| `plans/jiggly-crafting-planet.md` | Referenced by commit 85373ad; file not present in `plans/` (only `phase3_materialized_views_assessment.md`). Dangling reference. |
| `scripts/view_diagnostics.py:19-22` | Queries `ca_biositing.mv_biomass_search`; the MV lives in `data_portal`. |

## Gotchas
- Use the migration chain (latest: `alembic/versions/0024_*.py`) and `compile_mv_fixes.VIEWS` as the authority for what exists, not these docs.

## History
- Each doc above was last touched before the 0010-0024 migrations or before the `data_portal_views` split (d961724, 2026-04-09).

## Open questions
- Whether to delete `resources/sql/create_analytical_views.sql` and `alembic/VIEW_SQL_REFERENCE.md` or regenerate them (decision for maintainers).

# Related Concepts
- [pgschema diff tasks: read-only validation of the live DB against reference SQL](../architecture/views-pgschema-validation.md): The reference SQL file the diff tasks use is the stale main.sql.
- [Materialized view system: two schemas, one compile-and-refresh loop](../architecture/views-overview.md): Authoritative description of the view system these docs misdescribe.
- [Current state snapshot (2026-10-16)](current-state.md): Current-state hub that should carry the corrected view counts.
