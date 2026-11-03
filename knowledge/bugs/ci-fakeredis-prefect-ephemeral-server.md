---
type: Bug
title: "#261: CI fails: Prefect ephemeral server cannot import fakeredis FakeConnection"
description: CI test runs fail at Prefect ephemeral server start due to a fakeredis import error in docket.
tags: [bug, tooling-devex-ci]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:12Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/pyproject.toml"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/261"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #261 (https://github.com/sustainability-software-lab/ca-biositing/issues/261). Symptom: CI tests fail because Prefect’s ephemeral API server fails at startup: docket/_redis.py imports FakeConnection from fakeredis.aioredis.

**Status.** Open on GitHub (created 2026-04-13; assignee unassigned). Part of theme `facts/issues-tooling-devex-ci`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/pipeline/pyproject.toml` | (prefect>=3,<4; no direct fakeredis pin) |
| `pixi.lock` | (pydocket 0.21.0 pinned, lines ~379/779) |

**How it works.** Import chain is in the issue text. fakeredis is not a direct dependency in the pipeline pyproject, so it is transitive via pydocket/Prefect (inferred; confirm with `pixi list | grep -i redis` in the default env).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-04-13 as #261. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: developer environment, CI and agent tooling](../facts/issues-tooling-devex-ci.md): Theme inventory that lists #261
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
