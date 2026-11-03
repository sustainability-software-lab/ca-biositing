---
type: Decision
title: "DB tests use SQLite in-memory with selected tables, not Postgres or testcontainers"
description: Fixtures use SQLite in-memory engines with only needed tables and shims for Postgres-only types; testcontainers is pinned but unused.
tags: [testing, sqlite, postgres, fixtures, decision]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:46Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/tests/conftest.py", "tests/webservice/v1/conftest.py", "tests/webservice/conftest.py", "src/ca_biositing/pipeline/tests/conftest.py", "pixi.toml"]
sources: ["commit bd42ca2", "https://github.com/sustainability-software-lab/ca-biositing/pull/490", "commit 7a41e0e", "https://github.com/sustainability-software-lab/ca-biositing/pull/112"]
governance: context
---

## Purpose
Records the chosen test-database strategy and its trade-off. Rationale is inferred from fixture comments; no decision record was found in plans/ or docs/.

## Key files
| Path:line | Role |
|---|---|
| src/ca_biositing/datamodels/tests/conftest.py:10 | `create_engine("sqlite:///:memory:")` + `SQLModel.metadata.create_all` |
| tests/webservice/v1/conftest.py:50-93 | Creates only a list of tables "avoiding Polygon with md5()" (comment at fixture) |
| tests/webservice/conftest.py:21-37 | Creates only `api_user` table "avoiding PostGIS-specific tables" |
| src/ca_biositing/pipeline/tests/conftest.py:52-108 | Registers sqlite `md5` function; patches GeoAlchemy2 `after_create` to skip SpatiaLite |
| pixi.toml:38 | `testcontainers` pinned, but no test imports it (grep of src/ and tests/: 0 matches) |
| src/ca_biositing/datamodels/tests/test_view_filters.py:1-10 | Compiles SQL with `postgresql.dialect()` instead of running it |

## How it works
Each test (or function-scoped fixture) builds an in-memory SQLite DB. Postgres-only constructs (PostGIS geometry, `md5()`) are either skipped or shimmed. Sessions in the v1 suite run inside a transaction rolled back after each test.

## Trade-offs
- Pro: no Docker or network; fast; runs on macOS and Linux CI runners unchanged.
- Con: SQL that only Postgres accepts is not exercised; the materialized views are never executed (see bugs/datamodels-materialized-views-partially-tested). Spatial behaviour is mocked.
- Con: the same table lists are duplicated across conftests, so a new model needs manual addition (see v1 conftest `engine_fixture` list). Missing a table surfaces only as "no such table" (the bd42ca2 failure).

## Alternatives not used (from repo evidence)
- testcontainers (pinned in pixi.toml:38, unused).
- Live Postgres via `pixi run start-services` (used only by integration smoke tests against a running API).

## Open questions
- Whether a Postgres-backed test tier was planned: (inferred; confirm with maintainers, none found in plans/ or audit/).

# Related Concepts
- [Test suite layout, how to run each suite, and fixture map](../architecture/testing.md): fixture map where this strategy is implemented
- [5 of 12 materialized views have only SQL-text tests; 7 have none](../bugs/datamodels-materialized-views-partially-tested.md): SQLite strategy means MV SQL is never executed
- [System overview (start here)](../architecture/system-overview.md): production database is PostgreSQL; tests diverge from it
