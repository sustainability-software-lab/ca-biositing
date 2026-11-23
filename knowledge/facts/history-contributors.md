---
type: Fact
title: Contributors by commit count and area (snapshot at e41d00d)
description: "Who committed what: author counts overall and per directory, with name variants that refer to the same people, as of 2026-10-16."
tags: [contributors, ownership, history]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:03Z" }
status: stable
code_refs: ["AGENTS.md"]
sources: ["git shortlog and git log --no-merges, HEAD e41d00d"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Tells a reader whom to ask about an area. Counts are non-merge commits from `git log --no-merges` at HEAD e41d00d (201 commits).

## Key files
Not applicable; this concept summarizes authorship. Per-area counts come from `git log --no-merges --format="%an" -- <dir>`.

## How it works (counts)
| Author (as in git) | Commits | Main areas (per-directory count) |
|---|---|---|
| Don Setiawan | 54 | deployment (19), .github (16), alembic (7), webservice (7), datamodels (8) |
| Peter Smith | 50 | pipeline (23), datamodels (19), alembic (20), analysis (10), audit (2) |
| Vraj Rajpura | 23 | webservice (13), docs (8), pipeline (5), datamodels (5) |
| petercarbsmith | 21 | pipeline (10), datamodels (9), alembic (11), docs (7) |
| dependabot[bot] | 13 | GitHub Actions bumps |
| pre-commit-ci[bot] | 12 | pre-commit hook updates |
| Landung ’Don’ Setiawan | 11 | deployment and CI fixes (Mar 2026) |
| Niki Burggraf | 5 | LICENSE, community files, CI/CD, GCP staging DB (2025) |
| mglbleta | 5 | pipeline (5), datamodels (4), alembic (4); USDA/almond/qualitative ETL |
| Tyler Huntington | 3 | webservice API keys and IAM hardening (2026-04) |
| Copilot | 3 | PEP 420 reorg (#66), CRUD endpoints (#68), devcontainer (#51) |
| Avi | 1 | geocoding split (#456) |

Peter Smith and petercarbsmith are very likely the same person (inferred from matching ETL work; confirm). Don Setiawan and Landung ’Don’ Setiawan are very likely the same person (inferred from the same deploy work; confirm).

## Interfaces
Not applicable.

## Gotchas
- Name variants split the counts; combine them before concluding ownership.
- Counts reflect commits, not review or design authority.

## History
Snapshot only. Counts change as work lands; regenerate with the commands in Purpose.

## Open questions
- Who the external (pre-repo) ETL authors were (not in this clone).

# Related Concepts
- [Project history eras (2025-08 to 2026-10)](history-eras.md): each era has a dominant author
- [Most-churned files and what the churn implies (snapshot at e41d00d)](history-churn.md): churn hot spots map to these owners
- [System overview (start here)](../architecture/system-overview.md): hub for area ownership questions
