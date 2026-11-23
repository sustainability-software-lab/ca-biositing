---
type: Fact
title: "What the CI test jobs run, and what they skip"
description: CI runs tests/agent_harness and three src package paths; root tests/ and the integration smoke tests are not run in CI.
tags: [ci, github-actions, testing]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:46Z" }
status: stable
code_refs: [".github/workflows/ci.yml"]
sources: [".github/workflows/ci.yml", "commit e41d00d", "https://github.com/sustainability-software-lab/ca-biositing/pull/497", "commit ce9cc92"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Defines which tests gate a PR. Verified from .github/workflows/ci.yml at HEAD e41d00d.

## Key files
| Path:line | Role |
|---|---|
| .github/workflows/ci.yml:21-40 | `harness` job (ubuntu-latest): installs pixi only (`run-install: false`), then `pixi exec --spec python=3.12 --spec pytest --spec pyyaml -- python -m pytest tests/agent_harness -v` |
| .github/workflows/ci.yml:42-49 | `checks` job matrix: python-version py312, py313 x runs-on ubuntu-latest, macos-14 |
| .github/workflows/ci.yml:65-67 | `pixi run pytest src/ca_biositing/datamodels --cov ...` |
| .github/workflows/ci.yml:69-71 | `pixi run pytest src/ca_biositing/pipeline --cov ...` |
| .github/workflows/ci.yml:73-75 | `pixi run pytest src/ca_biositing/webservice -m "not integration" --cov ...` |
| .github/workflows/ci.yml:77-80 | codecov upload |

## How it works
- Pixi version is pinned to v0.63.2 in both jobs; the harness job deliberately does not install from pixi.lock so `tests/agent_harness/test_lockfile.py` can report pin problems.
- `pixi run test` (tests/) is not invoked by any workflow. Grep of .github/workflows for `pytest` returns only the lines above.
- Pre-commit hooks (.pre-commit-config.yaml) contain no pytest hook.

## Gotchas
- A PR can merge with failing root tests under tests/webservice or tests/pipeline; CI will not report them (see bugs/testing-root-tests-outside-ci).
- The `integration` marker is deselected in CI, so test_smoke.py never runs there.

## History
- e41d00d (2026-10-16, PR #497): created the separate `harness` job.
- ce9cc92 (2026-09-24), 3a8e1ff (2026-09-02), 6c34737 (2026-08-17): dependency bumps of setup-pixi/codecov action (commit subjects only; diffs not read).

## Open questions
- Whether the checks matrix should add `pixi run test` (tests/) is a policy decision; not decided in repo. (inferred; confirm with maintainers.)

# Related Concepts
- [Test suite layout, how to run each suite, and fixture map](../architecture/testing.md): the test layout these jobs run
- [Root tests/ (275 non-harness tests) are not gated by CI; analysis view tests broke unnoticed](../bugs/testing-root-tests-outside-ci.md): consequence of this scope
- [System overview (start here)](../architecture/system-overview.md): CI sits outside the runtime system; see hub for components
