---
type: Decision
title: Why alembic history was squashed to 0001-0004 and old revisions moved to versions_old/
description: "Records the May 2026 squash (PR #340): what was replaced, why the old revisions were parked in versions_old/, and what the trade-off is."
tags: [alembic, migrations, squash, versions_old, decision]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:39Z" }
status: stable
code_refs: ["alembic/versions_old", "alembic/versions/0001_initial_infra.py", "alembic/versions/0003_core_tables.py", "alembic/versions/0004_views_and_indexes.py", "alembic.ini"]
sources: ["commit db578ad", "https://github.com/sustainability-software-lab/ca-biositing/pull/340", "https://github.com/sustainability-software-lab/ca-biositing/pull/112", "commit 7a41e0e"]
governance: context
---

## Purpose
Record the decision behind `alembic/versions_old/` (41 files) and the 0001-0004 baseline.

## Key files
| path:line | role |
|---|---|
| `alembic/versions_old/` | 41 pre-squash revisions, not loaded by Alembic (no `version_locations` in `alembic.ini`) |
| `alembic/versions/0001_initial_infra.py` .. `0004_views_and_indexes.py` | the squashed baseline |
| `alembic/versions/0003_core_tables.py:1` | consolidated snapshot of the 107 tables |

## What happened
- Commit `db578ad` ("Database Maintenance Staging Reset", PR #340, merged 2026-05-09 UTC): "squashing and reorganizing alembic migrations". The PR body says the squash replaced about 42 multi-branch migrations with a linear 0001-0004. It also says old migrations were moved to `alembic/versions_old/` "(to be removed after verification)".
- Verification in the PR: fresh `alembic upgrade head`, `alembic check` showing zero drift, and a successful staging Cloud deploy.
- `versions_old/` is still present at HEAD `e41d00d`, so the removal did not happen.

## Why (from the PR body and commit)
- PR #340 describes the old chain as about 42 complex, multi-branch migrations. It paired the squash with a full staging database refresh, so (inferred; confirm) no existing staging DB needed the old revision IDs.
- A single baseline makes a fresh DB build simpler (the CI job in `.github/workflows/migrations.yml` depends on this).

## Alternatives and trade-offs
- Keep the full chain: preserves audit history, but multi-branch merges and broken early revisions remained.
- Squash and delete: simpler, but loses audit trail (partly mitigated by parking the files in `versions_old/`).
- Chosen: squash to baseline and park the old files. Cost: any DB still stamped at a pre-squash revision cannot run `alembic upgrade` without a manual `alembic stamp`.

## Interfaces
- Anything that refers to old revision IDs (for example `f5c8c031aef9`, `9e8f7a6b5c54`, `63c0fedd3446`) must now use the 0001-0004 baseline or the rebuilt chain.

## Gotchas
- `versions_old/` is inert. Do not add it to `version_locations`; that would create duplicate heads.
- Old files are kept for reference only; they are not part of the migration graph.

## History
- `7a41e0e` (2026-02-12, PR #112): the LinkML to SQLModel switch created `f5c8c031aef9` as a fresh initial revision and the 12+ LinkML-era revisions were the predecessors.
- `db578ad` (2026-05-08, PR #340): the squash.
- `d961724` (PR #258) and `2576d03` (PR #362): views refactor; this chain was not squashed again.

## Open questions
- Was `versions_old/` ever scheduled for deletion? (inferred: the PR text says yes, but it has not happened; confirm with the maintainers, or check the audit trail in PR #340 review comments.)
- Which DBs were stamped at pre-squash revisions before #340? (inferred: none, because staging was refreshed; confirm with `alembic current` on production.)

# Related Concepts
- [Alembic revision chain 0001-0024: what each revision changed and when](../facts/history-schema-timeline.md): The live chain that this squash created the baseline for.
- [Why datamodels moved from LinkML codegen to hand-written SQLModel + Alembic (PR #112)](linkml-to-sqlmodel-alembic.md): The earlier switch that made the pre-squash chain obsolete.
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): Describes how the live chain is loaded (only alembic/versions/).
