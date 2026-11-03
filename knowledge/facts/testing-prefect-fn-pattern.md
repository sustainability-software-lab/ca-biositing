---
type: Fact
title: Testing Prefect tasks by calling .fn() with a patched run logger
description: Prefect tasks are unit-tested via task.fn(...) with get_run_logger patched; used in about 100 call sites across the test tree.
tags: [testing, prefect, pipeline]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:47Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/tests/conftest.py", "src/ca_biositing/pipeline/tests/*.py", ".agents/rules/testing-patterns.md"]
sources: [".agents/rules/testing-patterns.md", "grep of tests for '.fn(' and 'get_run_logger' at HEAD e41d00d"]
governance: context
---

## Purpose
Documents the convention that lets pipeline task functions run without a Prefect flow/task context.

## Key files
| Path | Role |
|---|---|
| src/ca_biositing/pipeline/tests/conftest.py (`mock_prefect_logger` fixture) | monkeypatches `prefect.get_run_logger` |
| tests/ and src/ca_biositing/pipeline/tests/ | about 102 `.fn(` occurrences and about 50 `get_run_logger` mentions across the test tree (grep count) |
| .agents/rules/testing-patterns.md | documents `.fn()` + patch of `get_run_logger` at the module where it is imported |

## How it works
Calling a `@task` directly outside a run raises `MissingContextError`. Tests call `task.fn(...)` (the undecorated function) and patch `get_run_logger` in the module that imports it (about 50 mentions across tests). External calls (gsheet_to_df, get_engine) are patched at the import site.

## Gotchas
- `mock_prefect_logger` patches `prefect.get_run_logger` on the package; modules that already did `from prefect import get_run_logger` keep the original reference (inferred; confirm by reading a module that imports it directly).
- Flow-level behaviour (retries, task chaining) is not exercised by `.fn()` tests; only residue-factor flow tests use mocked flow structure.

## Open questions
- Whether Prefect’s test harness (prefect_test_harness) would replace this pattern: not in repo. (inferred.)

# Related Concepts
- [Test suite layout, how to run each suite, and fixture map](../architecture/testing.md): parent layout
- [System overview (start here)](../architecture/system-overview.md): Prefect orchestrates the ETL tasks under test
