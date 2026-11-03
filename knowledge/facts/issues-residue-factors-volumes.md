---
type: Fact
title: "Issues: residue factors, volume estimates and new MV products"
description: "GitHub issue inventory for residue factor data, volume/pricing estimate views and the biocirv P0/P1 remediation epic (#505), with open fix PR #513; as of 2026-10-22."
tags: [residue-factors, volume-estimates, biocirv]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:36Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/residue_factor.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py"]
stale_after: "2026-11-15"
sources: ["gh issue list --repo sustainability-software-lab/ca-biositing --state all (2026-10-16)", "https://github.com/sustainability-software-lab/ca-biositing/issues"]
---

**Purpose.** Residue factor reference data, volume/pricing estimate logic (Paths A-E in mv_biomass_volume_estimate) and the biocirv P0/P1 remediation epic #505.

**Counts.** 18 issues: 10 open, 8 closed. Open issues are listed first. Snapshot as of 2026-10-22 (HEAD a2c8de8); lists come from `gh issue list --state all`.

**Key files.**

| Path | Role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/residue_factor.py` | residue_factor model |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/models/resource_information/resource_availability.py` | resource_availability model |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py` | Volume estimate view; path logic and COALESCE fallbacks |

**How it works.** Issues are the work queue for this area. Each line below is one GitHub issue; bug-type open issues also have their own `bugs/` concept.

**Interfaces.** Inputs: GitHub issues on sustainability-software-lab/ca-biositing. Outputs: none in-repo; status changes are tracked on GitHub.

**Gotchas.** Epic #505 (open, P0) groups residue-factor basis (wet vs dry), name-based joins and corn-stover routing fixes. As of 2026-10-22 the child issues 506-512 are still open; #506 has an open fix PR (#513).

**History.** Issue numbers are the history index; see `facts/current-state` for the current-state snapshot. Commit refs where verified: 85373ad (#476, #480 centralization), e289fd1 (#248 per-client API keys), 203b787 (#139 JWT).

**Open questions.** Which open items are still wanted after the 2026 cleanup (for example #157 `name` to `api_name`, #147 lowercase validation) is not stated in the issues; confirm with the owners listed.

**Update 2026-10-22.** #513 (open PR, created 2026-10-17, all checks passing, mergeable) is the fix for #506 and says "Resolves #506" and "Part of #505". Epic #505 and children #507 to #512 have no PR as of 2026-10-22 (#513 defers #507 to #510 explicitly).

## Issues (18)

- #283 [OPEN] [FEATURE] ETL and materialized view for Grape pricing and volume data (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/283
- #423 [OPEN] [Feature] g/g yotal syngas yields in gasification data (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/423
- #505 [OPEN] feat(data): remediate residue factors and biomass volume estimates (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/505
- #506 [OPEN] fix(views): replace hardcoded IDs with name joins in volume view (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/506
- #507 [OPEN] fix(views): route corn stover to grain corn and flag substreams (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/507
- #508 [OPEN] fix(pipeline): fix almond shell copy and walnut basis in ag reports (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/508
- #509 [OPEN] fix(data): correct tree nut and orchard residue factors to dry basis (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/509
- #510 [OPEN] fix(data): convert wet pomace and vegetable cull factors to dry basis (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/510
- #511 [OPEN] feat(datamodels): add provenance and basis columns to residue_factor (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/511
- #512 [OPEN] docs(audit): publish academic SI residue factor reference table (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/512
- #274 [CLOSED] [FEATURE] ETL and materialized view for primary product and estimated volumes from weight based residue factors (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/274
- #276 [CLOSED] [FEATURE] ETL and materialized view for end uses (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/276
- #277 [CLOSED] [FEATURE] ETL and materialized view for storage and transportation data (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/277
- #278 [CLOSED] [FEATURE] ETL and materialized view for Almond pricing and volume data (@mglbleta) https://github.com/sustainability-software-lab/ca-biositing/issues/278
- #296 [CLOSED] [Feature]: ETL and materialized view for primary product and estimated volumes from commodity based residue factors (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/296
- #297 [CLOSED] [Feature]: ETL and materialized view for primary product and estimated volumes from acreage based residue factors (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/297
- #414 [CLOSED] [Bug]: Pistachio shell residue factors seem extremely low (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/414
- #419 [CLOSED] [Bug]: Corn stover is missing volume data (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/419

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state snapshot this issue inventory belongs to
- [Resource information: biomass resource, residue factors, availability, prices, end uses](../architecture/datamodels-resource-information.md): Domain meaning of residue factors (inferred target)
- [data_portal materialized views: modules, grain, and consumers](../architecture/views-data-portal-matviews.md): Volume view lives here
- [PR #513 (open): replace hardcoded IDs with name joins in the volume view and ETL transforms](pr-513.md): open PR that resolves #506 (sub-issue of #505)
