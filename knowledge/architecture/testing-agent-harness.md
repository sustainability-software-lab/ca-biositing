---
type: Architecture
title: "Agent-harness tests: repo-structure invariants for AI rules, skills, and pins"
description: "tests/agent_harness checks instruction files, rules, skills, links and pixi pins with git and YAML parsing; no DB or network."
tags: [testing, agent-harness, skills, ci]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:47Z" }
status: stable
code_refs: ["tests/agent_harness/**", ".github/workflows/ci.yml", ".agents/rules/*.md", "skills.json"]
sources: ["commit e41d00d", "https://github.com/sustainability-software-lab/ca-biositing/pull/497", ".github/workflows/ci.yml"]
governance: context
---

## Purpose
43 pytest tests (10 files) that enforce invariants of the agent harness added in e41d00d: AGENTS.md/CLAUDE.md imports, `.agents/rules/` naming and frontmatter, skill frontmatter, ignore rules, pixi pin consistency, and CI wiring. They inspect the repository; they do not import application code.

## Key files
| Path:line | Role |
|---|---|
| tests/agent_harness/conftest.py:28 | `repo_files(*pathspecs)`: `git ls-files --cached --others --exclude-standard`, so only committable files count |
| tests/agent_harness/conftest.py:51, :57 | session fixtures `agents_md_files`, `rule_files` |
| tests/agent_harness/test_lockfile.py:25-48 | `lock_format` reads the pixi.lock header; `pixi_pins` collects pinned pixi versions; `pins_that_cannot_read` |
| tests/agent_harness/test_lockfile.py:99 | asserts CI harness job does not install from pixi.lock |
| tests/agent_harness/test_rules.py | kebab-case rule names, rule index completeness, "load when" line |
| tests/agent_harness/test_skills.py | skill frontmatter spec, `.claude/skills` symlink, skills.json declares project skills |
| tests/agent_harness/test_pixi_references.py | every `pixi run <task>` mentioned in docs names a real pixi task |
| tests/agent_harness/test_links.py | broken-link checker over harness markdown |
| tests/agent_harness/test_okf.py | OKF knowledge bundle initialised; prettier skips it |

## How it works
Tests read files through git (so ignored synced skills are excluded), parse TOML/YAML, and assert text patterns. The harness CI job runs them in a Python 3.12 pixi exec env with pytest and pyyaml only.

## Interfaces
- Input: repository working tree and git index.
- Output: pass/fail; failure messages name the file and recovery step (per commit message wording).
- Callers: CI `harness` job (ci.yml:21-40); developers via `pixi run pytest tests/agent_harness -v`.

## Gotchas
- Tests depend on git: outside a git checkout `repo_files` returns an error (RuntimeError on non-zero git exit).
- `test_pixi_references` and `test_lockfile` couple docs and pins; changing a pixi task name or pinned pixi version needs matching doc edits.

## History
- e41d00d (2026-10-16, PR #497): introduced. Commit message notes the harness runs in its own job so a lock-format failure is not hidden by a failing install.

## Open questions
- Whether these tests should move to a tests/ subfolder run by `pixi run test` (currently they are not in CI’s checks job). (inferred; confirm.)

# Related Concepts
- [Test suite layout, how to run each suite, and fixture map](testing.md): parent test layout
- [What the CI test jobs run, and what they skip](../facts/testing-ci-scope.md): the harness job is the only CI test job that runs tests/
- [System overview (start here)](system-overview.md): agent harness is developer tooling around the system
