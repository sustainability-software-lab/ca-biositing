---
type: Bug
title: "#496: 2024 NSJV almond hull and shell volumes disagree in resource_production_record"
description: "2024 NSJV almond hull/shell production rows disagree and inflate mv_biomass_search totals; overlaps #508."
tags: [bug, etl-ingestion]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:22Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/flows/almond_nsjv_etl.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/almond_nsjv.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_search.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/496"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #496 (https://github.com/sustainability-software-lab/ca-biositing/issues/496). Symptom: For report_date 2024-01-01 in NSJV counties, almond hull and shell rows in public.resource_production_record disagree with the view totals, propagating into mv_biomass_search.total_annual_volume.

**Status.** Open on GitHub (created 2026-10-15; assignee unassigned). Part of theme `facts/issues-etl-ingestion`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/flows/almond_nsjv_etl.py` | see path |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/almond_nsjv.py` | see path |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_search.py` | see path |

**How it works.** Verified the almond NSJV flow and loader exist. Discrepancy numbers are from the issue body (2026-10-15); not re-queried (inferred cause; overlaps #508).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-10-15 as #496. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: ETL and data ingestion (pipeline)](../facts/issues-etl-ingestion.md): Theme inventory that lists #496
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
