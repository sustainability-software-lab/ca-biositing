---
type: Bug
title: "#508: Almond shell copy and walnut basis errors in ag reports"
description: Almond shell copy and Merced walnut basis are wrong in county ag report records; Path C lacks dry-matter conversion.
tags: [bug, etl-ingestion]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:23Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_report_record.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/almond_nsjv.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/508"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #508 (https://github.com/sustainability-software-lab/ca-biositing/issues/508). Symptom: Upstream ingestion bugs in county_ag_report_record and resource_production_record for NSJV almond shells, almond hulls and Merced walnuts; Path C needs dry-matter conversion. Resolves #496.

**Status.** Open on GitHub (created 2026-10-16; assignee unassigned). Part of theme `facts/issues-etl-ingestion`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/county_ag_report_record.py` | see path |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/almond_nsjv.py` | see path |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py` | (Path C commodity_direct) |

**How it works.** Files verified to exist; the ’shell copy’ defect itself is from the issue text and not reproduced here.

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-10-16 as #508. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: ETL and data ingestion (pipeline)](../facts/issues-etl-ingestion.md): Theme inventory that lists #508
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
