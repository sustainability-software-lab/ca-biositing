---
type: Requirement
title: "Keep one Alembic head: linear chain, merge revisions for conflicts"
description: "Invariant: the live alembic/versions chain has exactly one head, and parallel branches are resolved with a merge revision, not a DB reset."
tags: [alembic, migrations, requirement, constraint, decision]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:43Z" }
status: stable
code_refs: ["alembic/versions/*.py", "alembic/README", "docs/pipeline/ALEMBIC_WORKFLOW.md", "scripts/compile_mv_fixes.py", "src/ca_biositing/datamodels/AGENTS.md", "alembic/versions", "alembic/versions_old"]
sources: ["docs/pipeline/ALEMBIC_WORKFLOW.md", "commit db578ad", "commit 2576d03", "src/ca_biositing/datamodels/AGENTS.md", "https://github.com/sustainability-software-lab/ca-biositing/pull/258"]
governance: constraint
---

## Rule
`alembic heads` must return exactly one revision on `main`. If two branches add revisions after the same parent, merge them with `pixi run alembic merge -m "Merge heads" <head1> <head2>` and commit the merge.

## Why
- `alembic/README` (’Linear Migration Chain’) requires a single sequence that follows the head of `upstream/main`, because staging and prod already have upstream revisions applied.
- History has precedent: `2605c6e2b9da`, `64de60aff03d`, and `6f9bf0b22fc4` were merge revisions in the pre-squash chain. The squash `db578ad` removed them from the live chain.

## Current state
Live chain 0001 to 0024 is linear; each `down_revision` is the previous number (checked by reading all 24 headers).

## Gotchas
- `compile-mv-fixes` takes the highest numeric prefix as the parent. Two branches each running it will produce two `0025` files, which then conflict. Resolve before merge.
- `pixi run alembic upgrade heads` is for local troubleshooting only (`alembic/README` / ALEMBIC_WORKFLOW.md).

## Open questions
- Is there an automated check for multiple heads in CI? (inferred: none; `migrations.yml` runs `upgrade head`, which would fail on multiple heads, so a head conflict surfaces as a CI failure.)

## Merged detail: Alembic history must stay a single linear chain

### Purpose
State the invariant that the Alembic revision graph is one line, matching staging and production.

### Key files
| Path | Role |
|---|---|
| `src/ca_biositing/datamodels/AGENTS.md:209-222` | "Linear Alembic Chain" section |
| `alembic/versions/` | 24 active revisions (verified by `ls`) |
| `alembic/versions_old/` | 41 retired revisions kept for reference |
| `alembic/AGENTS.md` | Migration template and workflow |

### How it works
Developers run `pixi run migrate-autogenerate` and `pixi run migrate`, rebase onto `upstream/main`, and keep one head. Staging and production are assumed to match the head.

### Interfaces
- Input: new revisions. Output: a single head.

### Gotchas
- Two heads break `alembic upgrade head`. Rebase, do not merge migrations.
- The `versions_old/` directory is not in the active chain, so a revision there is never applied.

### History
- Rule introduced with the migration cleanup in commit d961724 (PR #258) (inferred from file history).

### Open questions
- No CI check enforces linearity (unverified; confirm in `.github/workflows`).

# Related Concepts
- [Alembic migrations: env.py, URL resolution, autogenerate filters, MV handling](../architecture/migrations.md): The tooling that creates and merges revisions.
- [Alembic revision chain 0001-0024: what each revision changed and when](../facts/history-schema-timeline.md): The chain whose single-head property this rule protects.
- [Decision: migrations embed frozen compiled SQL instead of importing view expressions](../decisions/views-compiled-sql-snapshots.md): View revisions also live in this chain
