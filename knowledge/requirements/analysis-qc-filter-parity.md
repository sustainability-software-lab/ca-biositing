---
type: Requirement
title: Analysis chart exclusions must match the portal QC definitions
description: "Chart scripts must apply the same resource, provider, and qc_pass exclusions as data_portal_views/common.py; today they copy the lists by hand, so change them together."
tags: [qc, filters, analysis, data-portal, invariant]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:43Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py", "analysis/composition/*.py", "analysis/conversion/*.py"]
sources: ["commit 85373ad", "https://github.com/sustainability-software-lab/ca-biositing/pull/472", "https://github.com/sustainability-software-lab/ca-biositing/pull/476", "https://github.com/sustainability-software-lab/ca-biositing/pull/480", "https://github.com/sustainability-software-lab/ca-biositing/pull/492"]
governance: constraint
---

## Rule
Any analysis script that labels or excludes records must use the same definitions as the portal views in `src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py`:
- `EXCLUDED_RESOURCES` (lines 42-55): sargassum, #n/a, lab media, alfalfa, almond hulls and shells mix, almond shells and hulls mix, almond woodchips.
- `EXCLUDED_PROVIDERS` (lines 78-81): jaguar.
- `EXCLUDED_QC_STATUSES = ["fail"]` (line 104).

## Why
The gallery and the portal would otherwise show different counts for the same data. The commits that centralized these filters (`85373ad`, PRs #476, #480, #492) and the jaguar exclusion (`d4f6b33`, PR #472) were made to keep them in one place.

## Current state (verified by reading the files)
- The analysis scripts do NOT import `common.py`. Each of the 12 composition/conversion scripts repeats literal `EXCLUDED_RESOURCES` and `EXCLUDED_PROVIDERS` lists inside `main()` (for example `analysis/composition/proximate_distribution_viz.py:38-43`).
- The current literal lists match `common.py` (same seven resources, `jaguar`).
- `datamodels/tests/test_view_filters.py` checks the SQL of the views, not these scripts (inferred from the test names; confirm by reading the file).

## How to comply
When you change an exclusion in `common.py`, change every `analysis/**` copy in the same PR, or import from `common.py` instead of copying.

## Open questions
- Whether to replace the literal copies with imports from `common.py` (inferred as the right fix; not yet done).

# Related Concepts
- [Analysis visualization scripts (analysis/) and how they query the DB](../architecture/analysis-visualization-scripts.md): The scripts that hold the duplicated lists
- [System overview (start here)](../architecture/system-overview.md): Portal views and analysis outputs must agree on what counts as valid data
