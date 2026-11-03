---
type: Decision
title: "History: AI agent tooling, skills manager, and SSEC harness (Oct 2025 to Oct 2026)"
description: "How AGENTS.md, skills.py replacing skills.sh, .agents/ rules and skills, and the Oct 2026 SSEC harness adoption evolved, with the files each change touched."
tags: [agents, skills, tooling, history]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:02Z" }
status: stable
code_refs: ["AGENTS.md", "skills.py", "skills.json", ".agents/rules", ".agents/skills"]
sources: ["commit bc3f4d8", "commit 522d108", "commit be75727", "commit e41d00d", "https://github.com/sustainability-software-lab/ca-biositing/pull/497", "https://github.com/sustainability-software-lab/ca-biositing/pull/398"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Explains the agent-facing files and why they changed, so agents do not rely on stale guidance.

## Key files
| Path | Role |
|---|---|
| AGENTS.md | Agent guide; first added in bc3f4d8 (PR #31, 2025-10-14); rewritten to ~360 lines in e41d00d |
| skills.json, skills.py, skills-lock.json | Skills manifest and sync script (522d108, PR #398) |
| skills.sh | Original shell sync script, reduced by 522d108 |
| .agents/rules/ and .agents/skills/ | SSEC harness rules and skills (e41d00d, PR #497) |
| .claude/skills/ | Symlinks into .agents/skills (e41d00d) |
| CLAUDE.md | Claude-specific guidance (check current content before relying on it) |

## How it works
- bc3f4d8 (PR #31, 2025-10-14): AGENTS.md and copilot env setup.
- 522d108 (PR #398, Peter Smith, 2026-06-12): integrated declarative skills management (skills.py); pixi skills-sync task.
- be75727 (PR #440, 2026-06-23): unified update-static-resource-info task, also documented in AGENTS.md.
- e41d00d (PR #497, Don Setiawan, 2026-10-16): adopted the SSEC project-template harness: rules, skills (commit, create-pr, merge-pr, okf-memory, docs), .devcontainer install-agents.sh, and a CI workflow addition.

## Interfaces
Inputs: AGENTS.md, .agents/rules/*.md, skills.json. Callers: AI coding agents and the pixi skills-sync task.

## Gotchas
- The harness commit is one day old relative to HEAD (2026-10-16); it may be incomplete. Treat new rules as provisional.
- Two sources (AGENTS.md and .agents/rules) can drift; e41d00d moved troubleshooting from agent_docs/ into .agents/rules/.

## History
Listed above with SHAs and PRs.

## Open questions
- Whether the harness rules fully replace the older agent_docs/ directory (inferred from the move; confirm).

# Related Concepts
- [Agent harness layout: AGENTS.md entry point, .agents/rules, .claude links, and its invariant tests](../architecture/tooling-agent-harness.md): current agent tooling (id prefix architecture/tooling-*)
- [Project history eras (2025-08 to 2026-10)](history-eras.md): E9 era
- [Contributors by commit count and area (snapshot at e41d00d)](history-contributors.md): who maintains these files
