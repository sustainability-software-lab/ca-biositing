---
type: Fact
title: "Issues: webservice / REST API, auth and API docs"
description: "GitHub issue inventory for the FastAPI webservice, endpoints and API auth, as of 2026-10-22; open issues first."
tags: [webservice, api, auth]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:28:35Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/", "src/ca_biositing/webservice/ca_biositing/webservice/v1/"]
stale_after: "2026-11-15"
sources: ["gh issue list --repo sustainability-software-lab/ca-biositing --state all (2026-10-16)", "https://github.com/sustainability-software-lab/ca-biositing/issues"]
---

**Purpose.** FastAPI REST API: endpoint families (USDA census/survey, analysis, resource availability, feedstock), discovery endpoints, auth (JWT, cookie, X-API-Key), and performance/observability work.

**Counts.** 41 issues: 15 open, 26 closed. Open issues are listed first. Snapshot as of 2026-10-22 (HEAD a2c8de8); lists come from `gh issue list --state all`.

**Key files.**

| Path | Role |
|---|---|
| `src/ca_biositing/webservice/ca_biositing/webservice/dependencies.py` | get_current_user auth chain: JWT/cookie -> X-API-Key with rate limit (L95-135) |
| `src/ca_biositing/webservice/ca_biositing/webservice/services/auth_service.py` | validate_api_key and auth helpers |
| `src/ca_biositing/webservice/ca_biositing/webservice/v1/ (endpoints, auth/, feedstocks/, router.py)` | Route handlers per endpoint family |

**How it works.** Issues are the work queue for this area. Each line below is one GitHub issue; bug-type open issues also have their own `bugs/` concept.

**Interfaces.** Inputs: GitHub issues on sustainability-software-lab/ca-biositing. Outputs: none in-repo; status changes are tracked on GitHub.

**Gotchas.** Per-client API keys with rate limiting landed in e289fd1 (#248). MCP server work (#494) is a follow-up to PR #484 and is not yet in the tree.

**History.** Issue numbers are the history index; see `facts/current-state` for the current-state snapshot. Commit refs where verified: 85373ad (#476, #480 centralization), e289fd1 (#248 per-client API keys), 203b787 (#139 JWT).

**Open questions.** Which open items are still wanted after the 2026 cleanup (for example #157 `name` to `api_name`, #147 lowercase validation) is not stated in the issues; confirm with the owners listed.

## Issues (41)

- #132 [OPEN] [Feature]: Vector Tile Pipeline (Tippecanoe) (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/132
- #133 [OPEN] [Feature]: Spatial Analytics Endpoints (buffer, hex aggregation) (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/133
- #134 [OPEN] [Feature]: Data Export Services (CSV, GeoJSON, Shapefile) (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/134
- #135 [OPEN] [Feature]: Performance, Caching & Observability (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/135
- #136 [OPEN] [Feature]: API Documentation & Workshop Demo Prep (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/136
- #146 [OPEN] [Feature]: Add integration smoke-test script for all API endpoints (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/146
- #147 [OPEN] [Feature]: lowercase validation for database (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/147
- #157 [OPEN] [Feature]: Complete USDA `name` -> `api_name` transition for crop-facing output (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/157
- #229 [OPEN] [Docs]: Fix API Reference rendering — add model docstrings and tune mkdocstrings config (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/229
- #230 [OPEN] [Feature]: Add HTTP caching headers to API responses (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/230
- #231 [OPEN] [Feature]: Add server-side in-memory cache for frequently accessed API queries (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/231
- #232 [OPEN] [Perf]: Establish baseline benchmarks and validate PRD latency targets (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/232
- #233 [OPEN] [Feature]: Integrate OpenTelemetry traces, metrics, and Prometheus endpoint into the webservice (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/233
- #234 [OPEN] [Feature]: Create SLA monitoring dashboard for API latency targets (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/234
- #494 [OPEN] Design and implement MCP server with proper auth (follow-up to PR #484) (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/494
- #21 [CLOSED] feat: FastAPI skeleton (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/21
- #86 [CLOSED] [Feature]: Feedstock API Implementation (@lsetiawan) https://github.com/sustainability-software-lab/ca-biositing/issues/86
- #87 [CLOSED] feat: API skeleton created (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/87
- #88 [CLOSED] feat: Static JSON in repo (@tylerhuntington,@petercarbsmith) https://github.com/sustainability-software-lab/ca-biositing/issues/88
- #89 [CLOSED] feat: Common API exception types created (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/89
- #90 [CLOSED] feat: APIs implemented with testing (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/90
- #91 [CLOSED] feat: GetUsdaCensusData implementation (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/91
- #92 [CLOSED] feat: GetUsdaCensusDataByResource implementation (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/92
- #93 [CLOSED] feat: ListUsdaCensusData implementation (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/93
- #94 [CLOSED] feat: ListUsdaCensusDataByResource implementation (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/94
- #95 [CLOSED] feat: GetUsdaSurveyData implementation (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/95
- #96 [CLOSED] feat: GetUsdaSurveyDataByResource implementation (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/96
- #97 [CLOSED] feat: ListUsdaSurveyData implementation (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/97
- #98 [CLOSED] feat: ListUsdaSurveyDataByResource implementation (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/98
- #99 [CLOSED] feat: GetResourceAvailability implementation (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/99
- #100 [CLOSED] feat: GetAnalysisData implementation (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/100
- #101 [CLOSED] feat: ListAnalysisData implementation (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/101
- #137 [CLOSED] Add JWT authentication with database-managed users to webservice (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/137
- #140 [CLOSED] [Bug]: USDA crop endpoints require exact casing and whitespace for crop lookups (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/140
- #153 [CLOSED] [Bug]: USDA census/survey endpoints return 404 due to observation key mismatch with ETL data (unassigned) https://github.com/sustainability-software-lab/ca-biositing/issues/153
- #158 [CLOSED] [Feature]: Webservice should query canonical datamodel views instead of rebuilding joins (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/158
- #165 [CLOSED] Fix misleading API documentation and example values (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/165
- #166 [CLOSED] Add per-endpoint-family discovery endpoints for queryable values (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/166
- #167 [CLOSED] Add integration smoke-test script for all API endpoints (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/167
- #168 [CLOSED] Normalize all string-based lookups (resource, parameter) for case-insensitive matching (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/168
- #169 [CLOSED] Return 200 + empty list instead of 404 for collection endpoints with no matching data (@Vraj1234) https://github.com/sustainability-software-lab/ca-biositing/issues/169

# Related Concepts
- [Current state snapshot (2026-10-16)](current-state.md): Current-state snapshot this issue inventory belongs to
- [Full webservice endpoint table (36 routes)](../architecture/webservice-endpoints.md): Webservice endpoints and auth
- [JWT login, cookie transport, and refresh in the webservice](../architecture/webservice-auth-jwt.md): Auth chain (inferred target)
