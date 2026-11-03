---
type: Decision
title: "History: docs consolidation, CalVer, and CHANGELOG policy (2025-11 to 2026-04)"
description: "How docs moved to MkDocs/ReadTheDocs, adopted CalVer with an empty CHANGELOG, added CITATION.cff and a Zenodo-ready README, and what those imply for release notes."
tags: [docs, release, calver, changelog, history]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:04Z" }
status: stable
code_refs: ["CHANGELOG.md", "CITATION.cff", "mkdocs.yml", "readthedocs.yaml", "README.md"]
sources: ["commit c6a15a6", "commit 7a27ee8", "commit 4ff6700", "commit 2b516af", "https://github.com/sustainability-software-lab/ca-biositing/pull/253"]
governance: context
---

## Purpose
Explains why CHANGELOG.md has no released entries and where docs live.

## Key files
| Path | Role |
|---|---|
| CHANGELOG.md | Keep-a-Changelog stub with CalVer YYYY.M.D and an [Unreleased] section only |
| CITATION.cff | Citation metadata with DOI (added 7d6591d, 2b516af) |
| mkdocs.yml | MkDocs config for ReadTheDocs (c6a15a6, 2025-11-17) |
| readthedocs.yaml | RTD build config |
| docs/ | Consolidated docs (8 by Vraj Rajpura, 7 by petercarbsmith in history) |

## How it works
- c6a15a6 (PR #67, 2025-11-17): consolidated docs, MkDocs on ReadTheDocs.
- 66cb070 (PR #204, 2026-04-13): changelog and static API reference.
- 7a27ee8 (PR #253, 2026-04-06): SECURITY.md, CHANGELOG.md, and CalVer adopted.
- 4ff6700 (PR #237, 2026-04-01): README overhaul for Zenodo publication; e3ed4de (PR #252) badges and acknowledgments.
- 7d6591d (PR #251) and 2b516af (PR #255): CITATION.cff and DOI.

## Interfaces
Inputs: docs/ and README. Outputs: ReadTheDocs site. Callers: maintainers and external citers.

## Gotchas
- The CHANGELOG has no release entries even though CalVer was adopted (7a27ee8); release notes are not being written there.
- README and docs changed heavily (27 README commits); check the dates before quoting setup steps.

## History
Listed above with SHAs and PRs.

## Open questions
- Whether CalVer releases are published (no tags checked in this slice; confirm with `git tag`).

# Related Concepts
- [System overview (start here)](../architecture/system-overview.md): hub for repo-level docs
- [Project history eras (2025-08 to 2026-10)](history-eras.md): docs changes sit in E3, E7 and E8
