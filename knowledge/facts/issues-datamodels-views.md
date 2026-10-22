---
type: Fact
title: "Issues: datamodels, schema, SQL and materialized views"
description: "GitHub issue inventory for SQLModel datamodels and data_portal views, as of 2026-10-22; open issues first."
tags: [datamodels, schema, views, materialized-views]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:33Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/"]
stale_after: "2026-11-15"
sources: ["gh issue list --repo sustainability-software-lab/ca-biositing --state all (2026-10-16)", "https://github.com/sustainability-software-lab/ca-biositing/issues"]
---

**Purpose.** SQLModel schema, SQL-as-source-of-truth decisions, constraints and the data_portal materialized views that feed the portal.

**Counts.** 26 issues: 2 open, 24 closed. Open issues are listed first. Snapshot as of 2026-10-22 (HEAD a2c8de8); lists come from `gh issue list --state all`.

**Key files.**

| Path | Role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/models/` | Hand-written SQLModel classes (91 models, 15 domains) |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/` | Materialized view definitions (mv_biomass_search, mv_biomass_composition, mv_biomass_volume_estimate, ...) |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/views.py` | View refresh helpers (refresh_all_views) |

**How it works.** Issues are the work queue for this area. Each line below is one GitHub issue; bug-type open issues also have their own `bugs/` concept.

**Interfaces.** Inputs: GitHub issues on sustainability-software-lab/ca-biositing. Outputs: none in-repo; status changes are tracked on GitHub.

**Gotchas.** Schema changes go through SQLModel + Alembic; view changes go through the compile-mv-fixes flow (see AGENTS.md).

**History.** Issue numbers are the history index; see `facts/current-state` for the current-state snapshot. Commit refs where verified: 85373ad (#476, #480 centralization), e289fd1 (#248 per-client API keys), 203b787 (#139 JWT).

**Open questions.** Which open items are still wanted after the 2026 cleanup (for example #157 `name` to `api_name`, #147 lowercase validation) is not stated in the issues; confirm with the owners listed.

## Issues (26)

- #115 [OPEN] feat: Add FK declarations for `fermentation_record` columns (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/115
- #461 [OPEN] Investigate and unify redundant columns in fermentation_record (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/461
- #107 [CLOSED] feat: SQL as source of truth (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/107
- #113 [CLOSED] refactor: LinkML Removal & SQLModel Migration (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/113
- #266 [CLOSED] [Bug]: Resource images upsetting based on resource_id not resource_name (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/266
- #269 [CLOSED] [BUG] add elapsed_time field to mv_biomass_fermentation (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/269
- #270 [CLOSED] [BUG] fix enzyme_name = NULL entries (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/270
- #271 [CLOSED] [BUG] has_gasification needs updating for 3 resources (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/271
- #272 [CLOSED] [BUG] Microbe value should be just the microbe (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/272
- #273 [CLOSED] [BUG] Resource images not flowing through accurately (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/273
- #275 [CLOSED] [BUG] has_volume boolean needs updating to match new approach (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/275
- #279 [CLOSED] [BUG] add min and max fields for calculated_estimate_volume metric (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/279
- #280 [CLOSED] [BUG] the ’high sugar’ tag should instead be ’high xylan’, ’high glucan’ (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/280
- #281 [CLOSED] [BUG] 18 resources have invalid compositional sums (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/281
- #282 [CLOSED] [BUG] “volatile solids” in ICP analysis (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/282
- #286 [CLOSED] [BUG] remove sargassum and lab media from materialized view (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/286
- #287 [CLOSED] [FEATURE] use metadata to recategorize grape pomace into red, white, or mixed (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/287
- #294 [CLOSED] [Bug]: mv_biomass_volume_estimate is missing indexes (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/294
- #321 [CLOSED] [Feature]: Create volume indices (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/321
- #322 [CLOSED] [Bug]: mv_biomass_search has discrepancy in sugars definition (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/322
- #323 [CLOSED] [Bug]: Rename ’Ash’ to ’Ash solids’ for consistency (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/323
- #337 [CLOSED] [Bug]: Remove ultimate analysis from the mv_biomass_composition view (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/337
- #343 [CLOSED] [Feature]: populate total_annual_volume_year in MV (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/343
- #357 [CLOSED] [Bug]: has_fermentation and has_gasification not working in mv_biomass_search (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/357
- #359 [CLOSED] [Bug]: sample_count should reflect field samples (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/359
- #374 [CLOSED] [Bug]: add county name to mv_volume_estimates and mv_biomass_pricing (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/374

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state snapshot this issue inventory belongs to
- [Materialized view system: two schemas, one compile-and-refresh loop](../architecture/views-overview.md): Model and view layer
- [data_portal materialized views: modules, grain, and consumers](../architecture/views-data-portal-matviews.md): Materialized view definitions
