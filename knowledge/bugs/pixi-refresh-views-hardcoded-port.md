---
type: Bug
title: "#152: Pixi tasks hard-code port 5432 for DB access (refresh-views fails on other ports)"
description: Pixi tasks hard-code local Postgres port 5432 for schema tasks; refresh-views fails on non-5432 machines.
tags: [bug, tooling-devex-ci]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:11Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/database.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/152"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #152 (https://github.com/sustainability-software-lab/ca-biositing/issues/152). Symptom: On a machine whose Postgres is not on 5432, `pixi run refresh-views` fails; start-services, migrate, deploy and run-etl work.

**Status.** Open on GitHub (created 2026-02-26; assignee unassigned). Part of theme `facts/issues-tooling-devex-ci`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `pixi.toml:234` | schema-dump, :237 schema-plan, :240 schema-analytics-plan (all `--port 5432`) |
| `pixi.toml:244` | refresh-views (uses SQLAlchemy get_engine, not a port flag) |
| `src/ca_biositing/datamodels/ca_biositing/datamodels/database.py` | (connection config, not read in this pass) |

**How it works.** Verified that pixi.toml hard-codes 5432 in the schema-* tasks. The refresh-views task itself passes no port, so the failing path is inferred to come from the engine config in database.py (inferred; confirm by reading database.py and running refresh-views with a non-5432 DATABASE URL).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-02-26 as #152. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: developer environment, CI and agent tooling](../facts/issues-tooling-devex-ci.md): Theme inventory that lists #152
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
