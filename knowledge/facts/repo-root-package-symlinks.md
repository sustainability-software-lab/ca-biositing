---
type: Fact
title: "Root datamodels/, pipeline/, webservice/ are symlinks into src/"
description: "Top-level datamodels, pipeline, and webservice are symlinks to src/ca_biositing/*; visualization has no root link and lives only under src/."
tags: [repo-layout, symlinks, namespace-packages]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:41Z" }
status: stable
code_refs: ["datamodels", "pipeline", "webservice", "src/ca_biositing/visualization"]
sources: ["commit e41d00d", "agent_docs/namespace_packages.md"]
governance: context
---

## Facts (verified with ls -l)
- `datamodels` → `src/ca_biositing/datamodels` (27 chars)
- `pipeline` → `src/ca_biositing/pipeline`
- `webservice` → `src/ca_biositing/webservice`
- `src/ca_biositing/visualization` has no root symlink.
- `frontend/` at the root is an empty directory: it is the git submodule path, not checked out.

## Why it matters
Files reached through the root path are the same files as under `src/`. Edit under `src/` and treat the root path as a convenience alias. Tools that glob or follow symlinks can show each file twice.

## History
- Layout is in place as of HEAD `e41d00d`; the namespace-package layout is documented in `agent_docs/namespace_packages.md`.

## Open questions
- Whether the root symlinks are needed for the Docker build context (inferred; confirm in `resources/docker` and `.dockerignore`).

# Related Concepts
- [System overview (start here)](../architecture/system-overview.md): Explains the repo layout that the hub document describes
- [Full webservice endpoint table (36 routes)](../architecture/webservice-endpoints.md): The webservice package is reached through the root webservice/ alias
