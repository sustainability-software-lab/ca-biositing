---
type: Fact
title: Downgrading an MV revision drops the views; it does not restore the previous definition
description: "Behavior fact: every MV revision’s downgrade() only drops views and indexes, so downgrade -1 leaves the data portal without the views until upgrade runs again."
tags: [alembic, materialized-views, downgrade, fact]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:43Z" }
status: stable
code_refs: ["alembic/versions/0024_centralize_qc_constants_across_data_portal_views.py", "alembic/versions/0005_mv_view_fixes.py", "alembic/README"]
sources: ["commit 85373ad", "commit 2576d03", "alembic/README"]
governance: context
---

## What is true
For revisions 0005, 0010, 0015, 0017 to 0024, `downgrade()` runs `DROP_INDEX_STATEMENTS` then `DROP_VIEW_STATEMENTS` (for example `0024_...py:648`). It contains no `CREATE MATERIALIZED VIEW`. Checked by counting `CREATE MATERIALIZED` in each downgrade body: 0.

## Consequences
- `pixi run alembic downgrade -1` on an MV revision removes the views. It does not return to the previous SQL.
- The documented ’downgrade then upgrade’ refresh cycle (`alembic/README`) works only because upgrade recreates the views from the frozen SQL. It is not a rollback.
- `migrations.yml` runs `alembic downgrade base` in CI; that succeeds because each MV downgrade drops views and the table downgrades drop tables.

## Where it matters
- Rolling back a bad MV change in shared environments needs a new fix-forward revision that embeds the old SQL. Simply downgrading removes the views for users of the data portal.

## Source
- `alembic/versions/0024_centralize_qc_constants_across_data_portal_views.py:648` and the same function in 0005, 0010, 0015, 0017 to 0023.

## Open questions
- Should `downgrade()` restore the previous revision’s SQL? (inferred: not done, to keep revisions independent; confirm with maintainers.)

# Related Concepts
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): The MV handling that this downgrade behavior belongs to.
- [Do not edit a revision that has been applied to a shared database; add a new revision](../requirements/never-edit-applied-migrations.md): Fix-forward is the safe rollback path for MV changes.
