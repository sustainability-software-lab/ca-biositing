---
type: Bug
title: skills.json declares two local skills that do not exist in .agents/skills
description: "Fixed in #531 (f954bd3): skills.json had listed data-visualization and database-query under the local registry with no directory or allowlist entry; both were removed."
tags: [skills, bug, tooling]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:00Z" }
status: stable
governance: context
code_refs: ["skills.json", ".gitignore", ".agents/skills", ".claude/skills", "tests/agent_harness/test_skills.py"]
stale_after: "2026-11-30"
sources: ["skills.json", ".gitignore", "commit 707afa8", "commit c676d8a", "https://github.com/sustainability-software-lab/ca-biositing/pull/442", "commit e41d00d", "commit f954bd3", "https://github.com/sustainability-software-lab/ca-biositing/pull/531"]
---

## Status
Fixed in `f954bd3` (PR #531, 2026-10-21). The two names were removed from the `"local"` registry in `skills.json`. At `a2c8de8` `git grep` finds no remaining reference to `data-visualization` or `database-query` outside `knowledge/`. The fix took the second option below (remove the names); the allowlist was not extended.

## Symptom at e41d00d (historical)
`skills.json` listed `data-visualization` and `database-query` under the `"local"` registry. `.agents/skills/` had only 8 directories (clean-branches, commit, create-issue, create-pr, docs, merge-pr, okf-memory, push), and `.claude/skills/` had the same 8 links.

## Evidence at e41d00d (historical)
- skills.json lines for the local registry (verified).
- `git ls-files` finds neither directory; `git log --all -- .agents/skills/<name>` returns nothing for either name.
- `.gitignore:85` ignored `.agents/skills/*` except the allowlist, which omitted both names.
- Both names were added in `707afa8` (#442); `c676d8a` says "implementng the database-query and data visualization skills". The skill files were apparently never committed (inferred from history).

## Current state at a2c8de8
- The local registry lists the 10 committed project skills, and `.agents/skills/` has 10 directories, all allowlisted in `.gitignore:87-110`.
- `tests/agent_harness/test_skills.py::test_skills_json_declares_every_project_skill` and `test_declared_local_skills_on_disk_are_not_ignored` are the tests that guard this. They were not run in this review (confirm with `pixi run pytest tests/agent_harness -v`).

## History
- `707afa8` (PR #442): names added to skills.json.
- `c676d8a`: commit message says the skills were being implemented.
- `f954bd3` (PR #531, 2026-10-21): names removed.

# Related Concepts
- [skills.json / skills.py: how third-party and project agent skills are declared and synced](../architecture/tooling-skills-sync.md): The manifest described here
- [Agent harness layout: AGENTS.md entry point, .agents/rules, .claude links, and its invariant tests](../architecture/tooling-agent-harness.md): Allowlist and link rules this bug breaks
- [System overview (start here)](../architecture/system-overview.md): Hub
