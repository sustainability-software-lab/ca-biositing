---
type: Architecture
title: Webservice error responses and exception classes
description: "Custom HTTPException subclasses, the 422 and 500 global handlers in main.py, and the error body shape clients get."
tags: [webservice, errors, exceptions]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:45Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/exceptions.py", "src/ca_biositing/webservice/ca_biositing/webservice/main.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/portal_auth.py"]
sources: ["commit 815d5ee", "commit 1880284", "https://github.com/sustainability-software-lab/ca-biositing/pull/105", "https://github.com/sustainability-software-lab/ca-biositing/pull/106", "commit 00a7146"]
---

## Purpose
Consistent error bodies for clients. Services raise domain exceptions; FastAPI turns them into HTTP responses.

## Key files
| Path | Role |
|---|---|
| `.../webservice/exceptions.py:1` | `CropNotFoundException` (404), `ResourceNotFoundException` (404), `ParameterNotFoundException` (404), `ParameterErrorException` (422, unused), `ServiceException` (500, unused) |
| `.../webservice/main.py:59` | `@app.exception_handler(RequestValidationError)` returns 422 `{detail:"Validation error", errors:[...]}` |
| `.../webservice/main.py:81` | `@app.exception_handler(Exception)` returns 500 `{detail:"Internal server error", error: str(exc)}` |

## How it works
- Services raise, e.g., `ResourceNotFoundException(resource_name)` with detail `Resource not found: <name>`.
- `ParameterNotFoundException` detail: `Parameter "<p>" not found for <context>`.
- Auth errors are plain `HTTPException` with `WWW-Authenticate: Bearer`.
- Validation errors (bad path or query types, extra body fields) use the custom 422 shape above, not FastAPI’s default `detail` list.

## Interfaces
- Error body: `{"detail": string}` for domain and auth errors; `{"detail", "errors"}` for 422; `{"detail", "error"}` for 500.
- Status codes seen: 401, 403, 404, 409 (register, duplicate username), 422, 429, 500, 503 (`/health`).

## Gotchas
- Portal login echoes the verifier exception text in its 401 detail: `Invalid Google ID token: {exc}` (`portal_auth.py:172-176`). Same class of leak as the 500 handler.
- The `/v1/qc` and `/v1/dashboards` routes return the portal 401/403 detail strings shown in `portal_auth.py` (for example `BioCirV portal authentication required`). Dashboard browser requests get a 302 instead of a 401.
- The catch-all 500  handler returns `str(exc)` to the client, which can leak internal messages (SQL errors, hostnames). See `bugs/webservice-500-leaks-exception-text`.
- `ParameterErrorException` and `ServiceException` are dead code. Nothing raises them. Do not assume a 422 or 500 path exists for business-rule errors.
- The docstring of `ParameterErrorException` describes a "both usda_crop and resource" mutual-exclusion check. That check is not in the current endpoints (route paths already make the choice).
- Missing-resource and missing-crop checks run inside the service, after the DB session is opened.

## History
- Exception classes and handlers appear with the early API work (`815d5ee`, `1880284`, PR #105/#106, Feb 2026) (inferred from commit titles). Git log for the exceptions and main files was not traced per-line (inferred; confirm with `git log -p` on exceptions.py and main.py).

# Related Concepts
- [Full webservice endpoint table (36 routes)](webservice-endpoints.md): Endpoints that raise these 404s and 422s
- [Catch-all 500 handler returns raw exception text](../bugs/webservice-500-leaks-exception-text.md): Known issue with the catch-all handler
- [Service layer behind feedstock queries and canonical view selection](webservice-usda-query-services.md): Services that raise the domain exceptions
