---
type: Requirement
title: Do not run pixi commands that rewrite pixi.lock while any pinned pixi is older than 0.68
description: "pixi.lock is format v6; pixi 0.68+ writes v7 and CI, Docker and devcontainer pin v0.63.2, so dependency changes must wait for a coordinated upgrade."
tags: [pixi, lockfile, ci, constraint]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:26:51Z" }
status: stable
code_refs: ["pixi.lock", "pixi.toml", "tests/agent_harness/test_lockfile.py", ".agents/rules/pixi-environments.md"]
sources: [".agents/rules/pixi-environments.md", "tests/agent_harness/test_lockfile.py", "commit 102afdf", "https://github.com/sustainability-software-lab/ca-biositing/pull/150", "commit e41d00d"]
governance: constraint
stale_after: "2026-11-30"
---

## The rule
Do not run `pixi add`, `pixi remove`, `pixi update` or `pixi lock` with pixi 0.68.0 or newer until every pinned pixi (CI workflows, deploy workflows, `.devcontainer/Dockerfile`, `copilot-setup-steps.yml`) is upgraded to the same release and the lock is migrated to v7 in its own PR. `pixi install` and `pixi run` leave an up-to-date lock alone, and editing a task does not change it.

## Why
- `pixi.lock` line 1 is `version: 6` (verified).
- Pinned pixi in CI and devcontainer is `v0.63.2` (verified in `.github/workflows/*.yml` and `.devcontainer/Dockerfile`), which cannot read v7.
- A v7 lock makes CI fail at setup, or silently re-solve.

## Enforcement
- `tests/agent_harness/test_lockfile.py` (names: `test_every_pinned_pixi_can_read_pixi_lock`, `test_every_pixi_pin_is_the_same_release`, `test_ci_runs_the_harness_without_installing_from_pixi_lock`).
- `ci.yml` harness job installs pixi only, so the failure is reported by the test instead of by setup-pixi.

## Scope
Applies to all agents and humans working in this repo. Source: `.agents/rules/pixi-environments.md` (Lock File Compatibility). Constraint for editing `pixi.toml` dependency sections and `pixi.lock`; does not restrict task edits.

## History
- Pixi pin moved from v0.59.0 to v0.63.2 in `102afdf` (#150, 2026-02-26). The harness adoption `e41d00d` (#497) documented the 0.68 rule and added the lockfile tests.

## Open questions
- Exact date for the v7 migration PR (not in the repo).

# Related Concepts
- [pixi.toml: workspace, features and environment composition](../architecture/tooling-pixi-manifest.md): Manifest whose dependency edits this rule limits
- [Devcontainer and Copilot setup: how a fresh agent or contributor gets the pixi toolchain](../architecture/tooling-devcontainer-and-copilot.md): Devcontainer pin that must match
- [GitHub Actions workflows: what runs on PRs, main, releases and deploys](../architecture/tooling-ci-workflows.md): CI pins that must match
