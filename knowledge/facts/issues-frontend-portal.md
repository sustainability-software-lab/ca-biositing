---
type: Fact
title: "Issues: frontend data portal (UI, charts, labels, content)"
description: "GitHub issue inventory for the frontend, portal and dashboard UX, as of 2026-10-22; open issues first."
tags: [frontend, portal, charts]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:31Z" }
status: stable
governance: context
code_refs: ["frontend/"]
stale_after: "2026-11-15"
sources: ["gh issue list --repo sustainability-software-lab/ca-biositing --state all (2026-10-16)", "https://github.com/sustainability-software-lab/ca-biositing/issues", "https://github.com/sustainability-software-lab/ca-biositing/issues/536"]
---

**Purpose.** Public data portal UI: charts, explore filters, labels and units, cite blurbs, gasification/volume tabs, and mobile layout. Frontend is a git submodule.

**Counts.** 53 issues: 16 open, 37 closed. Open issues are listed first. Snapshot as of 2026-10-22 (HEAD a2c8de8); lists come from `gh issue list --state all`.

**Key files.**

| Path | Role |
|---|---|
| `frontend/` | Git submodule (frontend application); not populated in this worktree, so UI issues could not be grepped locally |

**How it works.** Issues are the work queue for this area. Each line below is one GitHub issue; bug-type open issues also have their own `bugs/` concept.

**Interfaces.** Inputs: GitHub issues on sustainability-software-lab/ca-biositing. Outputs: none in-repo; status changes are tracked on GitHub.

**Gotchas.** Frontend code is not in this checkout; frontend issue locations are unverified. Filter defaults and ICP 0 handling are partly backend (common.py) and partly frontend.

**History.** Issue numbers are the history index; see `facts/current-state` for the current-state snapshot. Commit refs where verified: 85373ad (#476, #480 centralization), e289fd1 (#248 per-client API keys), 203b787 (#139 JWT).

**Open questions.** Which open items are still wanted after the 2026 cleanup (for example #157 `name` to `api_name`, #147 lowercase validation) is not stated in the issues; confirm with the owners listed.

**Update 2026-10-22.** Added #536 (open, deduplicate the Report a Bug modal across dashboards; created 2026-10-22). The modal regression itself was restored by merged #535 on 2026-10-22.

## Issues (53)

- #60 [OPEN] Phase 5: Frontend Integration (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/60
- #291 [OPEN] [Feature]: add processor locations and materials flow (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/291
- #292 [OPEN] [Feature]: add forest residue data (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/292
- #293 [OPEN] [Feature]: integrate transportation cost/COe tool information (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/293
- #295 [OPEN] [Feature]: Final QA (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/295
- #424 [OPEN] [Bug] Not sure what "current biomass" means in the bioconversion tab (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/424
- #427 [OPEN] [Feature] Presentation of characterization parameters (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/427
- #446 [OPEN] [Bug] Low contrast in pie charts due to color scheme (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/446
- #453 [OPEN] [Bug] Remove Olive Pomace 3HP Yields from Materialized View (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/453
- #454 [OPEN] [Bug] Bioconversion compare on mobile (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/454
- #457 [OPEN] [Feature] More context on data provenance and method (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/457
- #470 [OPEN] [Bug]: Update min/max defaults in explore page filters (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/470
- #471 [OPEN] [Bug]: Fix axes on charts across the portal (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/471
- #487 [OPEN] [Bug]: Removed instances of shortened ’Structural Carb.’ (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/487
- #488 [OPEN] [Bug]: Remove data that’s not ready + [beta]/[coming soon] tags (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/488
- #536 [OPEN] refactor(viz): deduplicate Report a Bug modal across dashboards (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/536
- #44 [CLOSED] [Feature]: Add Frontend Repository Integration with Git Submodule and Pixi Environment (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/44
- #289 [CLOSED] [Feature]: Images needed for all biomass types with characterization data (@bexodim) https://github.com/sustainability-software-lab/ca-biositing/issues/289
- #290 [CLOSED] [Feature]: Descriptions needed for the resources visible in the portal (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/290
- #345 [CLOSED] "how to cite this data" blurb (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/345
- #346 [CLOSED] "how to cite this data"  blurb 2 (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/346
- #347 [CLOSED] calbioscape issue test (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/347
- #348 [CLOSED] "how to cite this data" blurb (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/348
- #349 [CLOSED] "how to cite this data"  blurb 2 (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/349
- #350 [CLOSED] calbioscape issue test (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/350
- #351 [CLOSED] "how to cite this data" blurb 3 (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/351
- #352 [CLOSED] "how to cite this data" blurb 4 (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/352
- #353 [CLOSED] "how to cite this data" blurb 5 (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/353
- #354 [CLOSED] test (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/354
- #355 [CLOSED] test (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/355
- #364 [CLOSED] [Bug]: <short summary> bug (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/364
- #388 [CLOSED] test bug (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/388
- #394 [CLOSED] Program Manager (@bexodim) https://github.com/sustainability-software-lab/ca-biositing/issues/394
- #397 [CLOSED] how to cite (@bexodim) https://github.com/sustainability-software-lab/ca-biositing/issues/397
- #404 [CLOSED] [Bug] Check proximate values for oven dried preprocessing (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/404
- #408 [CLOSED] [Feature]: Replace "BioCirV" in this section with "BioCircular Valley" (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/408
- #409 [CLOSED] [Feature]: Curate slightly for testing purposes (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/409
- #410 [CLOSED] [Bug]: Ensure production by volume and pricing charts shows all years (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/410
- #411 [CLOSED] [Bug]: Only show apex and ferdinand gasification data (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/411
- #412 [CLOSED] [Feature]: Change default sort order in explore to high to low volume (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/412
- #413 [CLOSED] [Feature]: Add high volume to list of tags (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/413
- #415 [CLOSED] [Bug]: When ’unconverted biomass’ is added ensure it fits (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/415
- #420 [CLOSED] [Feature]: Show gasification and volume tabs on production (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/420
- #425 [CLOSED] Cobalt in the XRF chart displaying incorrectly (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/425
- #426 [CLOSED] [Bug] Value abbreviations in the Production by Location graph (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/426
- #429 [CLOSED] Gasification Pressure Chart axes (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/429
- #430 [CLOSED] [Bug] Do not change the syngas chart to log scale (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/430
- #435 [CLOSED] [Bug]: Update canonical URLs to use biomass names vs ids (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/435
- #437 [CLOSED] [Bug]: Only show the 3 in scope county volumes (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/437
- #447 [CLOSED] [Bug]: Yield comparison charts are no longer showing the current biomass (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/447
- #448 [CLOSED] [Bug]: Add axes names to double axes (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/448
- #449 [CLOSED] [Bug]: Correct footer link (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/449
- #450 [CLOSED] [Bug]: Dead links (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/450

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state snapshot this issue inventory belongs to
- [frontend/ git submodule (cal-bioscape-frontend), pin, and API consumption](../architecture/frontend.md): Portal UI (submodule)
