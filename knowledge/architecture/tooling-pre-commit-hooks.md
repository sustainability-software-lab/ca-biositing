---
type: Architecture
title: "Pre-commit configuration: hooks, exclusions and the mandatory pre-PR check"
description: "What .pre-commit-config.yaml runs (pre-commit-hooks, prettier, codespell, a GitHub capitalization check, check-jsonschema), its exclusions, and how it is run."
tags: [tooling, pre-commit, quality, lint]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:15Z" }
status: stable
governance: context
code_refs: [".pre-commit-config.yaml", ".codespellrc", "scripts/check_no_generated_artifacts.py"]
sources: [".pre-commit-config.yaml", "commit e41d00d", "commit dc4423b", "https://github.com/sustainability-software-lab/ca-biositing/pull/489", "https://github.com/sustainability-software-lab/ca-biositing/pull/497", "commit ae147f6", "https://github.com/sustainability-software-lab/ca-biositing/pull/522"]
---

## Purpose
Single quality gate: pixi run pre-commit-all (pre-commit run --all-files) must pass before a PR, per .agents/rules/contribution-discipline.md and the PR template. pre-commit.ci auto-updates hooks.

## Key files
| Path | Role |
| --- | --- |
| .pre-commit-config.yaml | all hook definitions and exclusions |
| .codespellrc | codespell settings |
| pixi.toml:64-65 | pre-commit-all and pre-commit-install tasks |
| scripts/check_no_generated_artifacts.py | the forbid-generated-artifacts hook implementation |

## Hooks (as configured at a2c8de8)
- pre-commit/pre-commit-hooks v6.0.0 (.pre-commit-config.yaml:6-19): check-added-large-files with --maxkb=500 (line 10, no exclusion since ae147f6), check-case-conflict, check-merge-conflict, check-symlinks, check-yaml (excludes mkdocs.yml), debug-statements, end-of-file-fixer, mixed-line-ending, trailing-whitespace.
- mirrors-prettier v4.0.0-alpha.8 on yaml, markdown, html, css, scss, javascript, json with --prose-wrap=always; excludes docs/api/, readthedocs.yaml, exports/plots/ and knowledge/ (line 27).
- codespell v2.4.3; excludes notebooks, pixi.lock, temp_external_datasets/, exports/plots/ (line 33).
- Local hooks (lines 35-46): disallow-caps (pygrep, lines 37-41) and forbid-generated-artifacts (lines 42-46), which runs python3 scripts/check_no_generated_artifacts.py with pass_filenames.
- check-jsonschema 0.38.2: check-dependabot and check-github-workflows (lines 48-52).

## How it works
- CI autofix commits use the messages style: pre-commit fixes and chore: update pre-commit hooks (ci block, lines 1-3).
- Hook versions are bumped by the autoupdate job.

## Interfaces
- Inputs: staged or all tracked files.
- Outputs: fixed files (whitespace, EOF, prettier) or a non-zero exit.
- Callers: developers, copilot-setup-steps.yml (pre-commit install-hooks), pre-commit.ci.

## Gotchas
- The prettier hook rewrites markdown and YAML, so edits to .agents/rules/*.md and AGENTS.md are reflowed to 80 columns when pre-commit runs.
- knowledge/ is excluded from prettier but not from codespell or the trailing-whitespace hook (inferred from the config).
- disallow-caps also matches the misspelling inside URLs or identifiers.
- The forbid-generated-artifacts hook is not in the GitHub Actions workflows. It runs locally or through pre-commit.ci. See requirements/generated-artifacts-never-committed.
- check-added-large-files checks added files only. An already tracked large file is not caught by it.

## History
- Hook bumps: f4606d4 (#421), 8b124c1 (#460), 7266bad (#466), dc4423b (#489).
- e41d00d (#497): prettier exclude for knowledge/.
- ae147f6 (2026-10-19, PR #522): forbid-generated-artifacts hook added; large-file limit lowered from 10,000 KB to 500 KB; exports/plots exclusion removed.

## Open questions
- Whether codespell should skip .agents/ and .claude/ (not excluded today).

# Related Concepts
- [System overview (start here)](system-overview.md): Hub
- [PRs need pre-commit passing, the full PR template, AI disclosure and human diff review](../requirements/tooling-pr-ai-disclosure-and-preflight.md): Requires this gate to pass before a PR
- [Agent harness layout: AGENTS.md entry point, .agents/rules, .claude links, and its invariant tests](tooling-agent-harness.md): Files the prettier exclude protects
- [Generated dashboards, fingerprints, drift reports and insights are never committed to git](../requirements/generated-artifacts-never-committed.md): the rule enforced by the forbid-generated-artifacts hook
