---
type: Bug
title: "#477: Filters in the ETL transform are broken or too aggressive"
description: "Issue #477 (open): ETL transform filters may drop rows too aggressively; separately, 18 infrastructure transforms return an unselected frame on KeyError, which hides a bad final filter."
tags: [bug, etl-ingestion]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:33Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/food_manufacturers_epa.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/crude_oil_pipelines.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py"]
stale_after: "2026-11-15"
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/477", "commit f8c9353", "https://github.com/sustainability-software-lab/ca-biositing/pull/514"]
---

**Purpose.** Open defect tracked as #477 (https://github.com/sustainability-software-lab/ca-biositing/issues/477). Symptom in the issue: transform filter logic drops rows due to missing values or mishandles record IDs and method mappings. Peter owns per the QC tasks table.

**Status.** Open on GitHub (created 2026-09-08; assignee @petercarbsmith). Part of theme `facts/issues-etl-ingestion`. No change to #477 itself was found in the commits reviewed here.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/` | (all transform modules) |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py` | (centralized filters since #476/#480) |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/food_manufacturers_epa.py:197-220` | Final column select with `except KeyError` returning `normalized_df` at `:216-218` |
| `src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/infrastructure/crude_oil_pipelines.py:136` | Same fallback, returning `combined_df` |

**New evidence (infrastructure, a2c8de8).** All 18 infrastructure transforms wrap the final column selection in `try` and, on `KeyError`, log an error and return the frame before selection (`normalized_df` or `combined_df`). Examples: `biodiesel_plants.py:234`, `landfills.py:248-250`, `food_manufacturers_epa.py:216-218`, `crude_oil_pipelines.py:136`. Effect: a missing column does not stop the flow here. The load then keeps only columns that exist in the model (`clean_record` filter in each loader) and inserts NULL for the rest. This is a silent-data-loss pattern in the same family as #477 (inferred; not reproduced).

**How it works.** Scope is the audit itself; no specific broken filter is named in #477 (inferred). Follows the centralization in commit 85373ad.

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction. The infrastructure fallback is the opposite of "too aggressive": it is too lenient.

**History.** Opened 2026-09-08 as #477. Related issues are listed in the theme concept. The infrastructure fallback was introduced with the family in f8c9353 (PR #514, 2026-10-22).

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing. Should the infrastructure transforms raise instead of returning the unselected frame?

# Related Concepts
- [Issues: ETL and data ingestion (pipeline)](../facts/issues-etl-ingestion.md): Theme inventory that lists #477
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
- [Infrastructure ETL family: 18 facility and line datasets, one shared extract/transform/load pattern](../architecture/pipeline-infrastructure-etl-family.md): the family containing the fallback pattern
