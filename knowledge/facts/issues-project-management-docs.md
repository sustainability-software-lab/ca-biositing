---
type: Fact
title: "Issues: project planning, milestones and documentation"
description: "GitHub issue inventory for project management, planning and documentation, as of 2026-10-22; open issues first."
tags: [docs, planning, milestones]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:34Z" }
status: stable
governance: context
code_refs: ["docs/", "AGENTS.md", "mkdocs.yml"]
stale_after: "2026-11-15"
sources: ["gh issue list --repo sustainability-software-lab/ca-biositing --state all (2026-10-16)", "https://github.com/sustainability-software-lab/ca-biositing/issues"]
---

**Purpose.** Planning and documentation issues: PRD, roadmap, milestones, the 2025-era repo restructuring phases, community health files and the docs site.

**Counts.** 33 issues: 4 open, 29 closed. Open issues are listed first. Snapshot as of 2026-10-22 (HEAD a2c8de8); lists come from `gh issue list --state all`.

**Key files.**

| Path | Role |
|---|---|
| `docs/` | Docs tree (symlinked AI_POLICY.md, CHANGELOG.md, CODE_OF_CONDUCT.md at HEAD) |
| `AGENTS.md` | Agent guidance; #83 split it up |
| `mkdocs.yml` | Docs site config (API reference rendering, #229) |

**How it works.** Issues are the work queue for this area. Each line below is one GitHub issue; bug-type open issues also have their own `bugs/` concept.

**Interfaces.** Inputs: GitHub issues on sustainability-software-lab/ca-biositing. Outputs: none in-repo; status changes are tracked on GitHub.

**Gotchas.** Many early planning issues (#2-#16) are closed and historical; docs-site URL issues (#198) predate the repo rename.

**History.** Issue numbers are the history index; see `facts/current-state` for the current-state snapshot. Commit refs where verified: 85373ad (#476, #480 centralization), e289fd1 (#248 per-client API keys), 203b787 (#139 JWT).

**Open questions.** Which open items are still wanted after the 2026 cleanup (for example #157 `name` to `api_name`, #147 lowercase validation) is not stated in the issues; confirm with the owners listed.

## Issues (33)

- #13 [OPEN] California BioSiting Tool (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/13
- #54 [OPEN] Repository Restructuring Proposal - Full Stack Architecture (@lsetiawan) https://github.com/sustainability-software-lab/ca-biositing/issues/54
- #163 [OPEN] Chore: Thoroughly double check Documentation (@petercarbsmith,@mglbleta) https://github.com/sustainability-software-lab/ca-biositing/issues/163
- #207 [OPEN] [Docs]: Docs Improvements/Questions for UW-SSEC team (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/207
- #2 [CLOSED] Create User Stories (@atambay37) https://github.com/sustainability-software-lab/ca-biositing/issues/2
- #3 [CLOSED] Create a fork or new repo for project codebase (@nikiburggraf) https://github.com/sustainability-software-lab/ca-biositing/issues/3
- #4 [CLOSED] Create a Product Requirement Document (@vanitech,@atambay37,@lsetiawan) https://github.com/sustainability-software-lab/ca-biositing/issues/4
- #8 [CLOSED] Add LICENSE file (@nikiburggraf) https://github.com/sustainability-software-lab/ca-biositing/issues/8
- #9 [CLOSED] Setup Project Roadmap and Milestones (@lsetiawan) https://github.com/sustainability-software-lab/ca-biositing/issues/9
- #12 [CLOSED] Setup community health files (@nikiburggraf) https://github.com/sustainability-software-lab/ca-biositing/issues/12
- #16 [CLOSED] Milestone 1: Foundations (Platform Scaffold) (@nikiburggraf) https://github.com/sustainability-software-lab/ca-biositing/issues/16
- #29 [CLOSED] [Docs]: Pixi context + GCP project guidance for LBL org users (@mglbleta) https://github.com/sustainability-software-lab/ca-biositing/issues/29
- #36 [CLOSED] [Docs]: Git Commit Template URL broken (@nikiburggraf) https://github.com/sustainability-software-lab/ca-biositing/issues/36
- #56 [CLOSED] Phase 1: Create Namespace Package Structure (@Copilot) https://github.com/sustainability-software-lab/ca-biositing/issues/56
- #57 [CLOSED] Phase 2: Documentation Reorganization (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/57
- #58 [CLOSED] Phase 3: Create Webservice Namespace Package (@Copilot) https://github.com/sustainability-software-lab/ca-biositing/issues/58
- #59 [CLOSED] Phase 4: Update Docker for Namespace Packages (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/59
- #61 [CLOSED] Phase 6: Scripts & Automation (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/61
- #62 [CLOSED] Phase 7: Testing & Validation (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/62
- #63 [CLOSED] Phase 8: Documentation Update & Final Polish (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/63
- #64 [CLOSED] Phase 9: Cleanup & Archival (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/64
- #82 [CLOSED] [Docs]: Update Contributing markdown (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/82
- #83 [CLOSED] [Docs]: Break up AGENTS.md file (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/83
- #186 [CLOSED] [Docs]: Add contributing docs for each namespace packages (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/186
- #198 [CLOSED] [Bug]: https://ca-biositing-uw.readthedocs.io/ needs updating to new repo name (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/198
- #208 [CLOSED] [Docs]: API Reference Docs (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/208
- #209 [CLOSED] [Docs]: Contributing.md (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/209
- #210 [CLOSED] [Docs]: docs/webservice/readme.md (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/210
- #211 [CLOSED] [Docs]: docs/datamodels/sql_first_workflow.md (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/211
- #212 [CLOSED] [Docs]: pipeline / alembic workflow (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/212
- #213 [CLOSED] [Docs]: pipeline / overview (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/213
- #214 [CLOSED] [Docs]: Home / Architecture (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/214
- #215 [CLOSED] [Docs]: Home / Overview (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/215

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state snapshot this issue inventory belongs to
- [System overview (start here)](../architecture/system-overview.md): Repo-level docs and structure
- [Glossary](glossary.md): Terms used in planning issues
