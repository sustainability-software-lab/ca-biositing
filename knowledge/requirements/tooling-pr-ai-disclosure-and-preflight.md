---
type: Requirement
title: "PRs need pre-commit passing, the full PR template, AI disclosure and human diff review"
description: "Hard gate before opening a PR: run pixi run pre-commit-all, fill every PR template section including AI disclosure and author verification, and get human approval of the diff."
tags: [contribution, pr, ai-policy, constraint]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:26:52Z" }
status: stable
code_refs: [".github/pull_request_template.md", ".agents/rules/contribution-discipline.md", "AI_POLICY.md", "tests/agent_harness/test_ai_policy.py"]
sources: [".github/pull_request_template.md", ".agents/rules/contribution-discipline.md", "AI_POLICY.md", "commit e41d00d", "https://github.com/sustainability-software-lab/ca-biositing/pull/497", "commit 8e6e997"]
governance: constraint
---

## The rule
Before a PR is opened (by a human or an agent):
1. `pixi run pre-commit-all` passes (it is the minimum check).
2. The full `.github/pull_request_template.md` is filled in with specific answers; the AI-assistance section is required for AI-assisted PRs and must not be left blank.
3. Search open and closed PRs and issues for the same problem (`gh pr list --state all --search`, `gh issue list --state all --search`).
4. The change solves a real, observed problem and belongs in this repo.
5. A human has reviewed the complete diff and approved submission.
6. Commit and PR titles follow Conventional Commits; open against `main`; one problem per PR.

Commit messages from agent tooling end with the `Assisted-by:` trailer style visible in `e41d00d` (`Assisted-by: claude-code:<model>`), matching the PR template’s harness/model token.

## Enforcement
- `tests/agent_harness/test_ai_policy.py` checks the AI policy trailer, the PR template disclosure section and the policy link.
- `tests/agent_harness/test_skills.py::test_commit_and_pr_skills_follow_the_ai_policy` checks the commit and create-pr skills.
- The PR template checklist (human-checked).

## Scope
Applies to every PR to this repository. Source: `.agents/rules/contribution-discipline.md`, `.github/pull_request_template.md`, `AI_POLICY.md`. The rule restricts behavior, not code.

## History
- PR template from `8e6e997` (#24, 2025-09-10); AI disclosure and author verification sections, and the contribution-discipline rule, from `e41d00d` (#497, 2026-10-16).

## Open questions
- Whether the sizing target (200-400 changed lines) should be enforced by a check; it is currently human review only.

# Related Concepts
- [Pre-commit configuration: hooks, exclusions and the mandatory pre-PR check](../architecture/tooling-pre-commit-hooks.md): The gate this rule requires
- [Agent harness layout: AGENTS.md entry point, .agents/rules, .claude links, and its invariant tests](../architecture/tooling-agent-harness.md): Harness that holds the rule file
- [System overview (start here)](../architecture/system-overview.md): Hub
