---
type: Decision
title: Cloud SQL uses a grant-based control model instead of strict ownership
description: "Cloud SQL cannot support strict ownership for postgres, so the reset scripts grant privileges and set default privileges rather than transferring ownership."
tags: [database, permissions, cloud-sql, decision]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:54Z" }
status: stable
code_refs: ["docs/operations/DB_RESET.md", "scripts/sql", "scripts/db_reset.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/387", "commit 0ccbb0f", "docs/operations/DB_RESET.md"]
governance: context
---

## Purpose
Record why DB reset and permission scripts use grants, not ownership transfer, on Cloud SQL.

## Key files
| Path | Role |
|---|---|
| `docs/operations/DB_RESET.md:37-50` | Three-phase reset and "Grant-based Control Model" |
| `scripts/sql/db_reset_wipe.sql` | Phase 1: drops and recreates schemas |
| `scripts/sql/db_reset_ownership.sql` | Phase 2: grants ALL to `biocirv_user`, sets default privileges |
| `scripts/sql/db_reset_readonly.sql` | Phase 3: grants SELECT to `biocirv_readonly` |
| `scripts/db_reset.py` | Driver (pixi `db-reset-*` tasks) |

## How it works
Phase 1 wipes and recreates schemas as the current user. Phase 2 grants privileges to the app user and sets `ALTER DEFAULT PRIVILEGES`. Phase 3 grants read-only access. `postgres` must be a member of `biocirv_user` so it can manage app objects without `SET ROLE` errors.

## Interfaces
- Inputs: DB credentials per environment. Outputs: schemas with the expected grants.

## Gotchas
- Cloud SQL’s circular membership restrictions are the stated reason; strict ownership fails there.

## History
- Commit 0ccbb0f (2026-06-01), PR #387: "Db reset".

## Rejected alternatives
Strict Ownership Model (named in the doc as the ideal, rejected for Cloud SQL).

## Open questions
- Whether the local compose DB should also use the grant model is not stated (unknown).

# Related Concepts
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): Migrations run under these grants
- [System overview (start here)](../architecture/system-overview.md): Database access model for all components
