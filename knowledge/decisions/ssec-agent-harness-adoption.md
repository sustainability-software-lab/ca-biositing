---
type: Decision
title: Agent harness adopted from UW SSEC template; agent_docs/ retired (Oct 2026)
description: "AGENTS.md became a short entry point, rules moved to .agents/rules, Claude imports AGENTS.md via CLAUDE.md, and a test asserts agent_docs/ stays deleted."
tags: [agents, harness, decision, claude-code]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:53Z" }
status: stable
code_refs: ["AGENTS.md", "CLAUDE.md", ".agents/rules", "tests/agent_harness/test_rules.py", ".agents/skills"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/497", "commit e41d00d", "AGENTS.md"]
governance: context
---

## Purpose
Record PR #497 and the structure it produced for AI assistant guidance.

## Key files
| Path | Role |
|---|---|
| `AGENTS.md:1-92` | Entry point with a table pointing to `.agents/rules/*.md` and package guides |
| `CLAUDE.md` | Imports `@AGENTS.md` |
| `.agents/rules/*.md` (12 files) | On-demand rules (working agreement, contribution discipline, pixi, testing, schema, Docker, etc.) |
| `tests/agent_harness/test_rules.py:32-34` | Asserts `agent_docs/` does not exist |
| `.agents/skills/` | Project skills: clean-branches, commit, create-issue, create-pr, docs, merge-pr, okf-memory, push |
| `AI_POLICY.md` | Adopted SSEC AI policy |

## How it works
Agents read the short AGENTS.md, then load a rule file whose "Load when" trigger matches the task. Package-level AGENTS.md and CLAUDE.md files (datamodels, pipeline, webservice, alembic, audit, resources) cover local detail.

## Interfaces
- Inputs: agent harness (Claude Code reads CLAUDE.md, others read AGENTS.md). Outputs: guided behavior, commit trailers, PR template.

## Gotchas
- The 2026-10-16 commit (e41d00d) touched 71 files. Docs that still say `agent_docs/` are stale (none found in-repo outside the test).
- AGENTS.md says `.agents/rules/` is the source for rules, so edits belong there.

## History
- Commit e41d00d (2026-10-16), PR #497 by Don Setiawan: "feat(agents): adopt the SSEC project-template agent harness". Upstream: uw-ssec/project-template at commit fc00b39.
- Behavioral rules adapted from obra/superpowers and multica-ai/andrej-karpathy-skills (AGENTS.md Provenance).

## Rejected alternatives
Keeping a single long `agent_docs/` tree (retired by the PR; reasons not written).

## Open questions
- Whether the project-template upstream will be the next source for updates (unknown).

# Related Concepts
- [AI-assisted contributions: disclose, own, and credit with Assisted-by (never Co-Authored-By)](ai-contribution-policy.md): The harness ships the AI policy it enforces
- [System overview (start here)](../architecture/system-overview.md): Harness is the entry point for agents working on any component
