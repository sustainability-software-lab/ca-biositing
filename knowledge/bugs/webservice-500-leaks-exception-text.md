---
type: Bug
title: Catch-all 500 handler returns raw exception text
description: "main.py’s Exception handler puts str(exc) in the response body, exposing internal error details to any unauthenticated caller who triggers a failure."
tags: [webservice, security, errors, bug]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:46Z" }
status: stable
governance: context
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/main.py"]
stale_after: "2026-12-31"
sources: ["commit e41d00d", "src/ca_biositing/webservice/ca_biositing/webservice/main.py", "commit cd1b9bd", "src/ca_biositing/webservice/ca_biositing/webservice/main.py@a2c8de8"]
---

## Symptom
Any unhandled exception returns HTTP 500 with JSON `{"detail":"Internal server error","error":"<str(exc)>"}`. `str(exc)` can contain SQL fragments, DB host or user names, or file paths.

## Location
`src/ca_biositing/webservice/ca_biositing/webservice/main.py:96` (`general_exception_handler`, defined at line 82, registered by `@app.exception_handler(Exception)` at line 81).

## Root cause
The handler includes the exception message on purpose or by oversight. Nothing filters it. It also runs for unauthenticated routes such as `/v1/auth/token` and `/health`.

## Impact
Information disclosure. Medium severity for a public Cloud Run service (`allUsers` has `roles/run.invoker`, see `architecture/webservice-deployment-cloud-run`).

## Suggested fix (not applied)
Return a generic message; log the exception server-side with a request id. Keep the `detail` key so clients do not break.

## Status
Still present at HEAD a2c8de8: `main.py:96` returns `"error": str(exc)`. `git log -S` traces the line to cd1b9bd (2025-12-16), so it predates the 2026-10 portal work and was not changed by #524. Open. Read from code; no tracking issue checked in this slice.

# Related Concepts
- [Webservice error responses and exception classes](../architecture/webservice-error-handling.md): The handler this bug is in
- [Webservice deployment on GCP Cloud Run](../architecture/webservice-deployment-cloud-run.md): Public exposure makes the leak reachable from the internet
