---
type: Decision
title: "AI-assisted contributions: disclose, own, and credit with Assisted-by (never Co-Authored-By)"
description: "Policy requiring disclosure, human review, no autonomous PRs, and an Assisted-by trailer. Conflicts with Co-Authored-By attribution used by some harnesses."
tags: [policy, ai, commits, decision, governance]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:53Z" }
status: stable
code_refs: ["AI_POLICY.md", "docs/AI_POLICY.md", ".agents/skills/commit/SKILL.md", ".agents/skills/create-pr/SKILL.md"]
sources: ["AI_POLICY.md", "https://github.com/sustainability-software-lab/ca-biositing/pull/497", "commit e41d00d"]
governance: constraint
---

## Purpose
Record the contribution policy for AI-assisted work in this repo.

## Key files
| Path | Role |
|---|---|
| `AI_POLICY.md:1-43` (copy at `docs/AI_POLICY.md:19`) | Rules: disclose, review, no fully autonomous agents, humans respond to reviewers |
| `AI_POLICY.md:27` | `Assisted-by: <harness>:<model>` trailer format |
| `.agents/skills/commit/SKILL.md:55-72,104-105` | Commit skill: Assisted-by trailer; "never Co-Authored-By" |
| `.agents/skills/create-pr/SKILL.md:72` | PR skill mirrors the trailer rule |
| `.agents/rules/contribution-discipline.md` | Agent rules before opening a PR |

## How it works
AI-assisted commits end with `Assisted-by: claude-code:<model>`. Humans are the only named co-authors. AI never signs off. The PR template holds a disclosure section.

## Interfaces
- Inputs: commit message, PR body. Outputs: trailer that machine tools can parse.

## Gotchas
- Commit trailers written under other harness instructions may use `Co-Authored-By: Claude ...`. AI_POLICY.md:19 and the commit skill forbid that form. This repo’s policy is the one to follow in committed work; confirm with the maintainer when in doubt.
- Policy says non-human agents may not open issues or PRs autonomously.

## History
- Policy adopted in commit e41d00d (2026-10-16), PR #497.

## Open questions
- Whether the Co-Authored-By form used in commit 85373ad (2026-10-08, before the policy) is an accepted precedent (unknown).

# Related Concepts
- [Agent harness adopted from UW SSEC template; agent_docs/ retired (Oct 2026)](ssec-agent-harness-adoption.md): Adopted in the same PR as the harness
- [System overview (start here)](../architecture/system-overview.md): Governs how AI-assisted changes reach any component
