---
type: Requirement
title: Do not edit a revision that has been applied to a shared database; add a new revision
description: "Once a revision reaches staging or prod, fix forward in a new revision. Known in-place edits (0002 in #387, 0008 in #320) are exceptions, not precedent."
tags: [alembic, migrations, requirement, constraint]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:42Z" }
status: stable
code_refs: ["alembic/versions/0002_permissions.py", "alembic/README", "scripts/compile_mv_fixes.py"]
sources: ["commit 0ccbb0f", "commit db578ad", "https://github.com/sustainability-software-lab/ca-biositing/pull/387", "https://github.com/sustainability-software-lab/ca-biositing/pull/362"]
governance: constraint
---

## Rule
Once a revision has been applied to staging or production, do not edit it. Add a new revision that corrects the effect. This is the fix-forward rule; the MV fix tooling (PR #362) writes new revisions rather than rewriting old ones.

## Why
- The `alembic_version` table records IDs, not contents. An edit does not re-run on a DB already at that revision, so environments drift from the file.

## Known exception
`0ccbb0f` (2026-06-01, PR #387, ’Db reset’) edited `alembic/versions/0002_permissions.py` in place. The default-privilege block was rewritten. That revision was part of the 0001-0004 baseline from `db578ad` (2026-05-08), so the change only affects fresh replays, not databases already past 0002. Treat this as a one-off, not a precedent.

## Allowed in-place edits
- Revisions that exist only on an unmerged local branch (use `pixi run compile-mv-fixes --revision NNNN --force` for MV iteration, per `alembic/README`). That flag overwrites an existing MV revision, so run it only on revisions not yet deployed.

## How to check
Compare the file to the commit that introduced it: `git log --follow -- alembic/versions/<file>`. If the file has later commits and is past a deployed revision, it violates this rule.

## Open questions
- Was 0002’s in-place edit ever applied to a live DB? (inferred: no, since staging was reset in #340 and #387; confirm with the staging `alembic_version` row.)

# Related Concepts
- [Alembic revision chain 0001-0024: what each revision changed and when](../facts/history-schema-timeline.md): Lists the revisions and their order, which this rule protects.
- [Keep one Alembic head: linear chain, merge revisions for conflicts](single-linear-head.md): The other invariant about history shape.
