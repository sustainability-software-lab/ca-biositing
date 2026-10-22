---
type: Architecture
title: "Devcontainer and Copilot setup: how a fresh agent or contributor gets the pixi toolchain"
description: "What .devcontainer (Dockerfile pinned to pixi v0.63.2, onCreate pixi install, agent CLI installer) and the Copilot setup workflow provide, and their differences."
tags: [tooling, devcontainer, copilot, onboarding]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:21Z" }
status: stable
governance: context
code_refs: [".devcontainer/devcontainer.json", ".devcontainer/devcontainer-lock.json", ".devcontainer/Dockerfile", ".devcontainer/onCreate.sh", ".devcontainer/install-agents.sh", ".github/workflows/copilot-setup-steps.yml"]
stale_after: "2026-12-31"
sources: [".devcontainer", ".github/workflows/copilot-setup-steps.yml", "commit a647afb", "https://github.com/sustainability-software-lab/ca-biositing/pull/51", "commit e41d00d", "https://github.com/sustainability-software-lab/ca-biositing/pull/497", "commit f8c9353", "https://github.com/sustainability-software-lab/ca-biositing/pull/514"]
---

## Purpose
Reproducible starting environments for humans (Codespaces, VS Code devcontainer) and for coding agents (Copilot cloud agent) that already have pixi installed.

## Key files
| Path | Role |
| --- | --- |
| .devcontainer/devcontainer.json | builds Dockerfile (context ..); features docker-in-docker, sshd, github-cli; named volume for .pixi; onCreateCommand .devcontainer/onCreate.sh; 4 CPU, 16 GB RAM, 32 GB disk; extension recommendations now include anthropic.claude-code and Google.google-antigravity (added by f8c9353) |
| .devcontainer/devcontainer-lock.json | new in f8c9353 (#514): pins docker-in-docker 2.17.0, github-cli 1.1.3 and sshd 1.1.0 by sha256 digest |
| .devcontainer/Dockerfile | mcr.microsoft.com/devcontainers/base:jammy; installs pixi v0.63.2 with SHA-256 verification (x86_64 and aarch64); runs install-agents.sh |
| .devcontainer/onCreate.sh | sudo chown vscode .pixi, then pixi install -e default |
| .devcontainer/install-agents.sh | installs Claude Code, Codex, Copilot CLI and OpenCode via their curl installers |
| .github/workflows/copilot-setup-steps.yml | sets up pixi (activate-environment) and runs pre-commit install-hooks |

## How it works
- Container build pulls pixi with checksums, then CLIs; onCreate installs the default environment on first create.
- The lock file makes the feature versions reproducible; the devcontainer.json itself still names feature tags.
- Copilot setup installs the environment from pixi.lock (its own job, pinned action SHAs).

## Interfaces
- Inputs: devcontainer features; network for pixi, npm and CLI installers.
- Outputs: a shell with pixi, the agent CLIs and the default environment.
- Callers: VS Code and Codespaces; Copilot coding agent.

## Gotchas
- onCreate.sh comment says GIS is intentionally excluded from the default install, but the default environment includes the light gis feature; QGIS is still excluded (see pixi-manifest gotchas).
- The Dockerfile pixi version must match the CI pins; tests/agent_harness/test_lockfile.py checks it.
- install-agents.sh pipes remote installers into bash; unpinned.
- The lock file covers only the three features. The Dockerfile pixi version and the agent CLIs are not locked.

## History
- Devcontainer added in a647afb (#51, 2025-10-27); agent-ready devcontainer, Copilot setup and the agent CLIs in e41d00d (#497, 2026-10-16); pixi pin bump 102afdf (#150).
- f8c9353 (2026-10-22, PR #514): lock file added and two extension recommendations.

## Open questions
- Whether the devcontainer should pin the agent CLI versions instead of using the latest installers.

# Related Concepts
- [pixi.toml: workspace, features and environment composition](tooling-pixi-manifest.md): The environment these images install
- [Do not run pixi commands that rewrite pixi.lock while any pinned pixi is older than 0.68](../requirements/tooling-pixi-lockfile-format-pin.md): Why the Dockerfile pixi pin must match CI
- [System overview (start here)](system-overview.md): Hub
