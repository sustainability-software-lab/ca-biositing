---
type: Fact
title: "Issues: developer environment, CI and agent tooling"
description: "GitHub issue inventory for developer tooling, pixi, skills and CI, as of 2026-10-22; open issues first."
tags: [tooling, pixi, ci, devex]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:32Z" }
status: stable
governance: context
code_refs: ["pixi.toml", "pixi.lock", ".github/workflows/", "skills.json", "skills.py", "src/ca_biositing/pipeline/pyproject.toml"]
stale_after: "2026-11-15"
sources: ["gh issue list --repo sustainability-software-lab/ca-biositing --state all (2026-10-16)", "https://github.com/sustainability-software-lab/ca-biositing/issues", "https://github.com/sustainability-software-lab/ca-biositing/issues/516"]
---

**Purpose.** Developer-environment, CI and agent-harness issues: Pixi environments and tasks, CI workflows, Docker image publishing, Windows/dev-tool breakage.

**Counts.** 20 issues: 9 open, 11 closed. Open issues are listed first. Snapshot as of 2026-10-22 (HEAD a2c8de8); lists come from `gh issue list --state all`.

**Key files.**

| Path | Role |
|---|---|
| `pixi.toml` | Pixi features, environments and tasks (qgis task at ~L251, schema-* tasks hard-code port 5432 at ~L234-240) |
| `pixi.lock` | Locked pins; pydocket 0.21.0 is pulled in via Prefect (relevant to #261) |
| `src/ca_biositing/pipeline/pyproject.toml` | Pipeline deps incl. prefect>=3,<4 |
| `skills.json / skills.py` | Agent skill manifest and sync script (#503, #504) |

**How it works.** Issues are the work queue for this area. Each line below is one GitHub issue; bug-type open issues also have their own `bugs/` concept.

**Interfaces.** Inputs: GitHub issues on sustainability-software-lab/ca-biositing. Outputs: none in-repo; status changes are tracked on GitHub.

**Gotchas.** Several open items are environment-specific (Windows symlinks, custom local DB port, QGIS install on macOS). Verify on the reporter’s platform before fixing.

**History.** Issue numbers are the history index; see `facts/current-state` for the current-state snapshot. Commit refs where verified: 85373ad (#476, #480 centralization), e289fd1 (#248 per-client API keys), 203b787 (#139 JWT).

**Open questions.** Which open items are still wanted after the 2026 cleanup (for example #157 `name` to `api_name`, #147 lowercase validation) is not stated in the issues; confirm with the owners listed.

**Update 2026-10-22.** Added #516 (closed 2026-10-18; a test issue titled "test").

## Issues (20)

- #152 [OPEN] [Bug]: pixi run refresh-views and others hard-coding local port in the pixi commands (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/152
- #176 [OPEN] [Bug]: Error installing and opening qgis (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/176
- #178 [OPEN] [Bug]: symlinks broken on windows (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/178
- #179 [OPEN] feat: Update docker image to use published pypi package (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/179
- #261 [OPEN] [Bug]: CI pipelines failing on fakeredis (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/261
- #501 [OPEN] build(deps): upgrade pixi pins and migrate pixi.lock to format v7 (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/501
- #502 [OPEN] build(deps): move okf-agent-memory and gh into Pixi features (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/502
- #503 [OPEN] chore(agents): resolve database-query and data-visualization in skills.json (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/503
- #504 [OPEN] chore(github): create the ai-assisted label once the AI policy is agreed (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/504
- #18 [CLOSED] ci: CI/CD setup (@nikiburggraf) https://github.com/sustainability-software-lab/ca-biositing/issues/18
- #20 [CLOSED] feat: Environment Reproducibility (@nikiburggraf) https://github.com/sustainability-software-lab/ca-biositing/issues/20
- #23 [CLOSED] Setup Pixi (@nikiburggraf) https://github.com/sustainability-software-lab/ca-biositing/issues/23
- #30 [CLOSED] [Feature]: ETL Pixi Environment (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/30
- #35 [CLOSED] [Bug]: Pixi codespell issue with Jupyter notebooks (@nikiburggraf) https://github.com/sustainability-software-lab/ca-biositing/issues/35
- #50 [CLOSED] [Feature]: Add GitHub codespaces (@Copilot) https://github.com/sustainability-software-lab/ca-biositing/issues/50
- #131 [CLOSED] fix: Fix failing CI (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/131
- #143 [CLOSED] ci: Activate PyPi releases for 3 namespace packages (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/143
- #145 [CLOSED] ci: Update pixi version to 0.63 (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/145
- #162 [CLOSED] ci: Create alembic migrations test (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/162
- #516 [CLOSED] test (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/516

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state snapshot this issue inventory belongs to
- [pixi.toml: workspace, features and environment composition](../architecture/tooling-pixi-manifest.md): Pixi environments and tasks these issues touch
- [Test suite layout, how to run each suite, and fixture map](../architecture/testing.md): CI test failures (#261) live here
