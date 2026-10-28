---
type: Bug
title: Legacy run_pipeline.py and extract template reference removed paths
description: "utils/run_pipeline.py scans src/etl/ which no longer exists, the gsheet extract template imports a stale module path, and root AGENTS.md links to a deleted agent_docs/ folder."
tags: [pipeline, bug, stale-docs, templates, legacy]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:54Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/run_pipeline.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/templates/extract_gsheet_template.py", "AGENTS.md"]
sources: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/run_pipeline.py", "commit ab8fa6c", "commit e41d00d", "https://github.com/sustainability-software-lab/ca-biositing/pull/497", "https://github.com/sustainability-software-lab/ca-biositing/pull/66"]
governance: context
stale_after: "2026-12-31"
---

## Symptom
- `python src/ca_biositing/pipeline/ca_biositing/pipeline/utils/run_pipeline.py <name>` prints "Pipeline not found" or fails to import. Discovery uses `src/etl/transform` (`run_pipeline.py:55`), which is absent.
- Copying `etl/templates/extract_gsheet_template.py` gives `ModuleNotFoundError`. Line 17 imports `pipeline.utils.gsheet_to_pandas` instead of `ca_biositing.pipeline.utils.gsheet_to_pandas`.
- Following the root `AGENTS.md` table opens dead links to `agent_docs/*.md`. The content moved to `.agents/rules/` in `e41d00d` (PR #497).

## Root cause
- Namespace reorg `ab8fa6c` (PR #66) moved code under `ca_biositing/pipeline/` without updating the legacy runner.
- Agent-harness change `e41d00d` (PR #497) moved docs without updating links.

## Evidence
- `ls src/etl` returns no such directory.
- `run_pipeline.py:92-93,102,123-127` use `src/etl/...` paths in messages and imports.
- Also: `run_pipeline.py` expects `extract_<source>` names, while landiq and most extracts use `extract`.
- The docs for running flows (`docs/pipeline/PREFECT_WORKFLOW.md`) use the registry and `run-etl`, not this runner.

## Status
Open. Nothing in pixi or CI calls `run_pipeline.py`.

## Open questions
- Delete the legacy runner, or update it? Owner decision.

# Related Concepts
- [How flows are registered and run (master flow, run-single-flow, list-flows)](../architecture/pipeline-flow-registry-and-run.md): The working runners that replace this one.
- [Google Sheets extraction: factory, gsheet_to_df, and retries](../architecture/pipeline-gsheet-extraction.md): Template is a copy-start for this layer.
