---
type: Architecture
title: "frontend/ git submodule (cal-bioscape-frontend), pin, and API consumption"
description: "frontend/ is an uninitialized submodule pinned to 386e37a; its code is not in this checkout, so API usage is inferred from the backend CORS config and analysis routes."
tags: [frontend, submodule, react, cors, api-consumer]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:42Z" }
status: stable
code_refs: [".gitmodules", "frontend", "pixi.toml", "src/ca_biositing/webservice/ca_biositing/webservice/config.py", "src/ca_biositing/webservice/ca_biositing/webservice/main.py", "src/ca_biositing/webservice/ca_biositing/webservice/v1/feedstocks/analysis.py"]
sources: ["https://github.com/sustainability-software-lab/cal-bioscape-frontend", "https://github.com/sustainability-software-lab/ca-biositing/pull/49", "https://github.com/sustainability-software-lab/ca-biositing/pull/183", "https://github.com/sustainability-software-lab/ca-biositing/pull/217", "commit a4e6fc9", "commit e4420fe", "docs/architecture.md"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
The web UI lives in a separate repository and is mounted at `frontend/`. It consumes the FastAPI backend.

## Submodule facts (verified)
- `.gitmodules`: `path = frontend`, `url = https://github.com/sustainability-software-lab/cal-bioscape-frontend.git`.
- Pinned SHA in HEAD tree: `386e37afd74fe1458208128a575c8f04c44776c7` (gitlink, mode 160000).
- `git submodule status` shows `-386e37a…` (leading dash = not initialized). `frontend/` is an empty directory here.
- Pin history: added `0c06f60` (PR #49, 2025-10-30); moved to `2fe642c` in `e4420fe` (PR #183, 2026-03-19); moved to `386e37a` in `a4e6fc9` (PR #217, 2026-04-01).

## Local tooling (verified in pixi.toml)
- Pixi env `frontend` (`pixi.toml:22-25`), node `>=18,<21`.
- Tasks: `submodule-frontend-init` (`git submodule update --init frontend`, pixi.toml:266), `frontend-install`, `frontend-dev`, `frontend-build` (npm in `frontend/`).

## What it consumes from the backend
- **Verified on backend side:** CORS allows `http://localhost:3000`, `:5173`, `:8080` with credentials (`src/ca_biositing/webservice/ca_biositing/webservice/config.py:42-49`, applied in `main.py:40-46`).
- **Verified routes the UI could use:** `/v1/health`; `/v1/feedstocks/analysis/resources`, `/geoids`, `/parameters`; `/v1/feedstocks/analysis/resources/{r}/geoid/{g}/parameters[/{p}]` (`v1/feedstocks/analysis.py`).
- **Inferred, not verified:** that the frontend calls these routes. Confirm after `pixi run submodule-frontend-init` by grepping the submodule for `fetch(`, `axios`, and base URL config.
- `docs/architecture.md:113-126, 464-480` says React/Next.js with TypeScript; this is unverified because the code is not checked out.

## Gotchas
- The static gallery at `exports/plots` (GitHub Pages) is a separate front end and does not use the API.
- Because the submodule is not initialized, a plain `git clone` or `pixi install` does not give you the UI.
- `geoids` discovery returns an empty list (see `bugs/views-analysis-data-view-null-geoid`), so any UI picker built on it will be empty.

## Open questions
- Framework and exact endpoints of the UI (inferred from docs; confirm in the submodule at 386e37a).
- Whether the pin should be bumped to the submodule’s main branch (inferred; no bump since PR #217).

# Related Concepts
- [Full webservice endpoint table (36 routes)](webservice-endpoints.md): Backend routes and CORS settings the frontend depends on
- [System overview (start here)](system-overview.md): Frontend is the user-facing tier of the overall system
- [Open bug: analysis_data_view geoid is NULL, so geoid-based analysis returns nothing](../bugs/views-analysis-data-view-null-geoid.md): Empty geoid discovery would break any frontend geography picker
- [Plot regeneration, HTML gallery index, and GitHub Pages deploy](analysis-regeneration-and-gallery.md): Static gallery is a separate publish path from the frontend
