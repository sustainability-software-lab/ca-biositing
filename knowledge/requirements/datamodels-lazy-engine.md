---
type: Requirement
title: Do not create the DB engine or open connections at import time
description: Import-time DB connection or engine creation hangs Docker and Prefect workers. Keep engine creation behind get_engine() and imports of settings inside functions.
tags: [datamodels, requirement, import-time, docker, prefect]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:01Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/database.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/config.py"]
sources: ["AGENTS.md", "src/ca_biositing/datamodels/ca_biositing/datamodels/database.py"]
governance: constraint
---

## Rule
No module-level code in `ca_biositing.datamodels` (or code importing it) may create an engine, open a connection, or run a query. Heavy imports such as `settings` should happen inside functions.

## Why
- `database.py:17` comment: "Lazy initialization of engine to avoid import-time hangs".
- `database.py:13` imports `settings` inside `_get_engine`.
- Root `AGENTS.md` "Docker Hangs & Deadlocks" lists this as CRITICAL.

## Where it is enforced
- `database.py:18-26` (`_engine` singleton) and `database.py:45-47` (`__getattr__` for `engine`).
- Not enforced by a test in this slice (inferred; no import-time test found).

## Caveat
`config.py:75` (`settings = Settings()`) does run at import time. It only reads env vars and a `.env` file, no network. The rule above is about connections, not env reads.

# Related Concepts
- [Datamodels DB engine and session management (database.py)](../architecture/datamodels-database-session.md): the implementation of this rule
- [Datamodels settings and DB environment variables (config.py)](../architecture/datamodels-settings-env.md): the one import-time side effect that is allowed (env read)
