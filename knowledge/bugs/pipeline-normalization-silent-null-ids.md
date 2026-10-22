---
type: Bug
title: Name-to-ID normalization can emit NULL foreign keys without failing
description: "normalize_dataframes turns per-column errors, missing columns and all-null columns into NA <col>_id values with only a log line, so loads can silently write NULL foreign keys."
tags: [pipeline, bug, normalization, data-quality]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:54Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/landiq_etl.py"]
sources: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/landiq_etl.py"]
governance: context
stale_after: "2026-12-31"
---

## Symptom
A transform finishes and a load runs, but the foreign-key column is empty for some or all rows. Nothing raises.

## Root cause (code)
- Missing column: `src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py:~186-196` logs a warning and sets `<col>_id` to NA.
- All-null column: `name_id_swap.py:~198-205` does the same and drops the name column.
- Per-column exception: `name_id_swap.py:~226-236` logs with `exc_info` and sets NA.
- Model without the expected attributes: `replace_name_with_id_df` returns NA (`name_id_swap.py:71-78`).
- Downstream: `etl/transform/prepared_sample.py` and others keep going. The load writes whatever is there.
- Landiq flow has the same pattern: `src/ca_biositing/pipeline/ca_biositing/pipeline/flows/landiq_etl.py:109-110` catches all exceptions and returns normally.

## Status
Open. No issue or PR found in git history for this specific behavior.

## Reproduction
Pass a DataFrame whose name column is entirely null to `normalize_dataframes` and inspect the output (inferred from code; not run).

## Open questions
- Whether a strict mode (raise when more than N rows get NA) is wanted. Owner decision.

# Related Concepts
- [Name-to-ID normalization (get-or-create reference rows)](../architecture/pipeline-name-id-normalization.md): Function where the silent fallback lives.
- [How a pipeline flow wires extract, transform, and load](../architecture/pipeline-flow-wiring.md): Flows that pass the NA ids on.
