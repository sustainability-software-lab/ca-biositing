---
type: Fact
title: "Integration smoke tests need a live API, seeded DB and credentials; CI deselects them"
description: src/ca_biositing/webservice/tests/test_smoke.py hits a running server (23 tests); skipped without env vars and never run in CI.
tags: [testing, integration, webservice]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:48Z" }
status: stable
code_refs: ["src/ca_biositing/webservice/tests/test_smoke.py", "src/ca_biositing/webservice/tests/conftest.py", "src/ca_biositing/webservice/pyproject.toml"]
sources: ["src/ca_biositing/webservice/tests/test_smoke.py", ".github/workflows/ci.yml"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Smoke tests for the deployed or local API with seeded data.

## Key files
| Path:line | Role |
|---|---|
| src/ca_biositing/webservice/tests/test_smoke.py:1-12 | usage docstring: `CA_BIOSITING_BASE_URL`, `CA_BIOSITING_TEST_USERNAME`, `CA_BIOSITING_TEST_PASSWORD`, `-m integration` |
| src/ca_biositing/webservice/tests/test_smoke.py:350 | `pytest.skip` when credentials unset |
| src/ca_biositing/webservice/tests/conftest.py:8-42 | `base_url`, `auth_headers` (POST /v1/auth/token), `client` (httpx) |
| src/ca_biositing/webservice/pyproject.toml:64-65 | `integration` marker definition |
| .github/workflows/ci.yml:73-75 | CI runs webservice with `-m "not integration"` |

## How it works
Module-scoped fixtures log in once, then each test calls the live API. Connection failure triggers skip with message "is the server running?".

## Gotchas
- Local run: `pixi run start-webservice` plus `pixi run start-services` (DB) and seeded data; not automated.
- Without credentials the tests skip, so a passing local run without env vars proves nothing.

## Open questions
- Whether a deployed-environment smoke job exists in cd.yml/deploy-*.yml: not checked in this slice. (inferred.)

# Related Concepts
- [Test suite layout, how to run each suite, and fixture map](../architecture/testing.md): parent layout
- [System overview (start here)](../architecture/system-overview.md): webservice API under test
