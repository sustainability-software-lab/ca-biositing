---
type: Requirement
title: Migrations must not import SQLAlchemy models or view definitions
description: "Hard rule: revision files contain frozen SQL and plain op calls, and never import ca_biositing modules, so replays stay deterministic."
tags: [alembic, migrations, materialized-views, requirement, constraint]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:42Z" }
status: stable
code_refs: ["alembic/versions/*.py", "alembic/AGENTS.md", "alembic/env.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/258", "commit d961724", "alembic/AGENTS.md"]
governance: constraint
---

## Rule
A revision file under `alembic/versions/` must not import `ca_biositing.*` (or any app module that reads models or views). Use SQL strings embedded in the file, plus `alembic.op` / `sqlalchemy` primitives.

## Why
- PR #258: importing `data_portal_views` at upgrade time made replays depend on today’s code. A view could fail to build if a table it needs was created after the migration ran, which broke teardown and rebuild.
- `alembic/AGENTS.md` lists the legacy import pattern as ’DON’T USE’.

## Current state
No file in `alembic/versions/` imports `ca_biositing` at HEAD `e41d00d` (checked with a grep for `from ca_biositing` and `import ca_biositing`). `alembic/versions_old/` may contain older imports, but those files are not loaded.

## How to check
`grep -l "ca_biositing" alembic/versions/*.py` should return nothing.

## Exceptions
None recorded. Use `env.py` helpers only for connection setup.

## Open questions
- Would a grep check in pre-commit be worth adding? (inferred: not present; confirm in `.pre-commit-config.yaml`.)

# Related Concepts
- [Decision: migrations embed frozen compiled SQL instead of importing view expressions](../decisions/views-compiled-sql-snapshots.md): The decision this rule enforces.
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): The env and chain the rule protects.
