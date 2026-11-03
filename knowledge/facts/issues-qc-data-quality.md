---
type: Fact
title: "Issues: data-quality audits and QC filters"
description: "GitHub issue inventory for QC and data-quality checks and filters, as of 2026-10-22; open issues first."
tags: [data-quality, qc, audit]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:32Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/"]
stale_after: "2026-11-15"
sources: ["gh issue list --repo sustainability-software-lab/ca-biositing --state all (2026-10-16)", "https://github.com/sustainability-software-lab/ca-biositing/issues", "https://github.com/sustainability-software-lab/ca-biositing/issues/515"]
---

**Purpose.** Per-analysis-type QC audits (proximate, compositional, ultimate, ICP, XRF, bioconversion, gasification, qualitative) and the QC filters that drop rows from portal views.

**Counts.** 33 issues: 14 open, 19 closed. Open issues are listed first. Snapshot as of 2026-10-22 (HEAD a2c8de8); lists come from `gh issue list --state all`.

**Key files.**

| Path | Role |
|---|---|
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py` | Central QC filters and thresholds: COMPOSITIONAL_SUM_MIN/MAX (L118), ICP_MAX_PPM (L119), get_qc_status_filter (L107), get_icp_filter (L254), log_filter_summary (L340) |
| `src/ca_biositing/datamodels/tests/test_view_filters.py` | Structural regression tests for view filters |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/` | Transform-side filtering (see #477) |

**How it works.** Issues are the work queue for this area. Each line below is one GitHub issue; bug-type open issues also have their own `bugs/` concept.

**Interfaces.** Inputs: GitHub issues on sustainability-software-lab/ca-biositing. Outputs: none in-repo; status changes are tracked on GitHub.

**Gotchas.** Commit 85373ad (#476, #480) centralized the filters into common.py; older issues referring to per-view filters may be stale. Filters drop data silently (see #478).

**History.** Issue numbers are the history index; see `facts/current-state` for the current-state snapshot. Commit refs where verified: 85373ad (#476, #480 centralization), e289fd1 (#248 per-client API keys), 203b787 (#139 JWT).

**Open questions.** Which open items are still wanted after the 2026 cleanup (for example #157 `name` to `api_name`, #147 lowercase validation) is not stated in the issues; confirm with the owners listed.

**Update 2026-10-22.** Added #515 (closed 2026-10-19; date fields not filtering in data QC dashboards).

## Issues (33)

- #284 [OPEN] [FEATURE] do checks on data entry validation (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/284
- #285 [OPEN] [FEATURE] do summation checks on pie chart data (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/285
- #298 [OPEN] [Feature]: Poximate Analysis QC (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/298
- #300 [OPEN] [Feature]: Compositional Analysis QC (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/300
- #302 [OPEN] [Feature]: Ultimate Analysis QC (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/302
- #304 [OPEN] [Feature]: ICP Analysis QC (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/304
- #306 [OPEN] [Feature]: XRF Analysis QC (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/306
- #308 [OPEN] [Feature]: Bioconversion Data QC (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/308
- #314 [OPEN] [Feature]: Ongoing database validation (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/314
- #328 [OPEN] [Feature]: Gasification QC (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/328
- #329 [OPEN] [Feature]: Qualitative Data QC (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/329
- #416 [OPEN] [Feature]: Gasification Data QC (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/416
- #417 [OPEN] [Feature]: Volume Data QC (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/417
- #465 [OPEN] [Feature]: Centralize filters as much as possible to one part of the stack (@mglbleta) https://github.com/sustainability-software-lab/ca-biositing/issues/465
- #299 [CLOSED] [Feature]: Initial Proximate Analysis Data Audit (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/299
- #301 [CLOSED] [Feature]: Initial compositional analysis audit (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/301
- #303 [CLOSED] [Feature]: Initial ultimate analysis audit (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/303
- #305 [CLOSED] [Feature]: Initial ICP analysis audit (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/305
- #307 [CLOSED] [Feature]: Initial audit of XRF analysis data (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/307
- #309 [CLOSED] [Feature]: Initial bioconversion data audit (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/309
- #312 [CLOSED] [Feature]: Initial Sample Lineage Audit (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/312
- #313 [CLOSED] [Feature]: gasification initial audit (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/313
- #317 [CLOSED] [Bug]: add QC filter for ultimate analysis (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/317
- #325 [CLOSED] [Bug]: Almond hulls have ’Zn’ in proximate analysis list (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/325
- #327 [CLOSED] [Bug]: Proximate analysis doesn’t add up to 100% for some resources (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/327
- #332 [CLOSED] [Bug]: ICP & XRF - include values = 0 (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/332
- #333 [CLOSED] [Feature]: Add QC filters for proximate analysis data (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/333
- #334 [CLOSED] [Feature]: Add QC filter for compositional analysis (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/334
- #335 [CLOSED] [Feature]: Add QC filter on ICP (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/335
- #336 [CLOSED] [Feature]: Add bioconversion QC filter (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/336
- #341 [CLOSED] [Bug]: Update QC filters by experiment vs by avg summaries (@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/341
- #396 [CLOSED] [Bug]: Physically Impossible ICP values (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/396
- #515 [CLOSED] Date fields are not working for filtering in data qc dashboards (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/515

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state snapshot this issue inventory belongs to
- [Materialized view system: two schemas, one compile-and-refresh loop](../architecture/views-overview.md): QC filters live in the view layer
- [How a pipeline flow wires extract, transform, and load](../architecture/pipeline-flow-wiring.md): Transform-side filtering
