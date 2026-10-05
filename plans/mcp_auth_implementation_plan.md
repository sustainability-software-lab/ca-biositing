# MCP Authentication Implementation Plan

## Overview

This plan outlines the implementation of proper authentication for the `/mcp` endpoint in the ca-biositing FastAPI webservice. The endpoint is currently mounted with zero authentication (line 173 in `main.py`), creating a critical security gap: the staging Cloud Run service is fully public (`ingress="INGRESS_TRAFFIC_ALL"`, `roles/run.invoker` granted to `allUsers`), allowing anyone to call all 10 MCP tools—including the 3 KB-proxy tools that spend the app's own third-party `biocirv-kb` API budget with no rate limit or attribution.

**Objective:** Secure the `/mcp` endpoint by requiring valid API key credentials, reusing the existing `ApiKey` infrastructure, updating the hybrid-query skill to supply credentials for local dev, and provisioning secrets in staging/production.

**Key Decision:** Reuse the production-ready `ApiKey` / `validate_api_key` / rate-limiting system already deployed for the REST API (`/v1/`), rather than inventing a new static-key-list system as originally sketched in `plans/mcp-architecture.md`. This avoids maintaining two parallel credential systems.

---

## Problem Statement

### Current State

- `/mcp` is mounted at `src/ca_biositing/webservice/ca_biositing/webservice/main.py:173` with **zero auth checks**.
- Staging's Cloud Run service is publicly reachable: `ingress="INGRESS_TRAFFIC_ALL"` (line 63 in `cloud_run.py`); all users have `roles/run.invoker` (lines 194–195).
- The 3 KB-proxy MCP tools (`search_biositing_knowledge`, `ask_biositing_question`, `get_feedstock_entity_relationships`) forward requests to `biocirv-kb` using the app's own `kb_api_key` from config. An anonymous caller can exhaust this third-party API budget without rate limiting or attribution.
- The 7 relational tools read Postgres data directly. Unauthenticated public access to production data violates basic security principle: limit access to systems and data to authorized users only.

### Original Plan vs. Reality

`plans/mcp-architecture.md` §3 ("Auth Strategy") and §6 step 5 proposed a `_BearerAuthASGI` wrapper validating static, comma-separated `MCP_API_KEYS` from an env var — but this was never implemented. PR #484's description states "Authentication for the /mcp endpoint is intentionally omitted in this phase for local development and private network use," which was correct for local dev but false for staging: staging is public.

---

## Recommended Solution

### 1. Auth Mechanism Decision: Reuse Existing `ApiKey` System

**Why reuse `ApiKey` instead of static-key list:**
- **Existing infrastructure:** `validate_api_key()` (in `auth_service.py`) is production-ready: hashed storage, prefix-based lookup, constant-time comparison, revocation via `is_active` flag, per-key rate limiting via `rate_limit_per_minute` and fixed-window counter.
- **Avoid dual maintenance:** A new static-key system would require separate provisioning, rotation, and lifecycle management. One system reduces complexity.
- **Same treatment as REST API:** Both `/v1/` and `/mcp` callers are machine agents or service accounts, not human users. The existing API-key infrastructure is built exactly for this use case.
- **Rate limiting per caller:** Each MCP caller gets its own rate-limit budget. This prevents a single bad actor from exhausting the shared `kb_api_key` budget.
- **Revocation story:** Leaked keys can be deactivated immediately without app redeployment via the `is_active` flag.

**Scope:** The MCP endpoint will accept the same auth sources as `get_current_user()` in `dependencies.py` (JWT Bearer, HTTP-only cookie, or X-API-Key header), but in practice MCP clients will use X-API-Key because JWT expiry (30 min) is incompatible with long-lived agent sessions.

---

## 2. Access-Control Mechanism: Pure ASGI Middleware (Not BaseHTTPMiddleware)

**Challenge:** `/mcp` is mounted as a raw Starlette/ASGI sub-application via `app.mount(path, mcp_app)`, not a FastAPI `APIRouter`. You cannot attach `dependencies=[Depends(get_current_user)]` to it. Auth must be enforced via middleware that runs before the MCP handler.

**Additional concern — streaming responses:** The `/mcp` endpoint returns Server-Sent Events (SSE) with `data: ` lines containing JSON-RPC envelopes. FastAPI's built-in `BaseHTTPMiddleware` (the common pattern for ASGI middleware in FastAPI apps) buffers responses in certain Starlette versions, which would break streaming. This repo pins `fastapi>=0.111.0,<0.115.0` (as of Sept 2026), which is affected by this issue. The safe approach is a **pure ASGI middleware** that implements `__call__(scope, receive, send)` directly, without subclassing `BaseHTTPMiddleware`.

**Solution:** Create a pure ASGI middleware class that:
1. Intercepts the request at the ASGI level (before the MCP app sees it).
2. Extracts credentials from the request (Bearer token, X-API-Key header, or HTTP-only cookie).
3. Calls the existing `validate_api_key()` function (reusing all its safety properties).
4. On auth failure: return HTTP 401 with a JSON error and **stop** (never call the inner app).
5. On auth success (or dev mode): call the inner app via `await self.app(scope, receive, send)` and **never touch the response** (pure pass-through for streaming).

Pure ASGI middleware is the standard pattern for auth gates on mounted ASGI apps precisely because it only intercepts before the request reaches the inner app and otherwise does zero response-side interception.

**Credential check order** (mirrors `get_current_user()`):
1. Authorization Bearer header (JWT or raw key)
2. HTTP-only `access_token` cookie
3. X-API-Key header

For simplicity and to match the MCP machine-caller pattern, the implementation will **check X-API-Key first** (most common for service-to-service), then fall back to Bearer/cookie. This is a minor deviation from the REST API order but makes sense for MCP's intended use case.

**Auth-failure response:** Return HTTP 401 with a JSON body that mimics MCP's streamable HTTP error envelope so MCP clients degrade gracefully:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32001,
    "message": "Could not validate credentials"
  }
}
```

Status: 401 Unauthorized. MCP clients that check `response.status_code` before parsing the body will not crash.

**Implementation structure (pseudocode):**
```python
class MCPAuthMiddleware:
    def __init__(self, app, session_factory, config):
        self.app = app
        self.session_factory = session_factory
        self.config = config

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # Non-HTTP (e.g., WebSocket) — pass through unchanged
            await self.app(scope, receive, send)
            return

        # Extract and validate credentials
        headers = dict(scope.get("headers", []))
        is_authenticated = self._check_auth(headers)

        if not is_authenticated and not self.config.dev_mode:
            # Auth failed and dev mode is off — return 401 and stop
            error_response = self._build_error_response()
            await self._send_response(send, error_response)
            return

        # Auth passed (or dev mode) — pass request to MCP app unchanged
        # Do NOT intercept or buffer the response
        await self.app(scope, receive, send)

    def _check_auth(self, headers) -> bool:
        # Extract X-API-Key, Bearer, or cookie
        # Call validate_api_key() if a key is present
        # Return True if valid, False otherwise
        ...

    def _build_error_response(self) -> dict:
        # Return JSON-RPC error envelope + HTTP status 401
        ...

    async def _send_response(self, send, response):
        # Send the error response and close the connection
        ...
```

---

## 3. Scoping: KB-Proxy Tools vs. Relational Tools

**Question:** Should the 3 KB-proxy tools (which spend the app's own budget) receive stricter treatment?

**Decision:** No. All 10 tools are equally protected behind the same auth gateway. The mitigation for KB-proxy budget abuse is the `ApiKey.rate_limit_per_minute` budget enforced by `check_and_increment_rate_limit()`. Each API key has its own per-minute quota; the rate-limit enforcement runs on every tool call, regardless of whether it calls the KB or local Postgres. This is sufficient: a caller whose key has a 10-req/min limit will consume their own budget at the KB tier, not the app's aggregate budget.

If finer-grained control is needed later (e.g., KB tools require a higher permission level), that can be added as a new `ApiKey.scope` field. For now, the uniform approach is simpler.

---

## 4. Config & Secrets Plan

### Local Development

**Approach:** Derive dev mode from environment, like the datamodels config already does for Docker detection.

Default behavior: Local dev runs with auth disabled (`dev_mode=True`). This matches the repo's convention (see `ca_biositing/datamodels/config.py`: `_in_docker = os.path.exists("/.dockerenv")`), where development contexts are auto-detected and relaxed. For local iteration, `pixi run start-webservice` works immediately without friction. If testing auth locally, set `BIOSITING_MCP_API_KEY` env var and the middleware will validate it (still allows requests because dev mode is on, but exercises the auth code path).

Production/staging explicitly set `API_DEV_MODE=false` in Cloud Run environment variables (Phase 3 covers this). This provides defense in depth: even if someone forgets an env var, a mistake in the env config won't accidentally leave auth disabled on production — it defaults to enabled.

**Code changes to `config.py`:**
```python
import os

# Detect if running in a local development environment
_is_local_dev = not os.environ.get("INSTANCE_CONNECTION_NAME")  # Not in Cloud Run

class WebServiceConfig(BaseSettings):
    # ... existing fields ...

    dev_mode: bool = Field(
        default=_is_local_dev,
        description="Skip auth on /mcp for local development. Defaults to True locally, False in Cloud Run. Set API_DEV_MODE to override."
    )
```

**Why this default is safe:**
- Local development: Auth is off by default. Developers iterate fast. Setting `BIOSITING_MCP_API_KEY` enables auth testing on demand.
- Staging/production: `INSTANCE_CONNECTION_NAME` is set by Cloud Run, so `_is_local_dev=False`, meaning `dev_mode=False` by default. Auth is ON unless explicitly disabled (which Cloud Run ops would never do; the only way it happens is if someone removes the `API_DEV_MODE=false` env var in the Cloud Run deployment config — at which point the app logs a FATAL warning at startup and exits if `API_MCP_API_KEY` is missing).
- Fails safe: If a deploy accidentally omits `API_DEV_MODE=false`, the app won't start (missing key error) rather than silently leaving auth open.

### Staging & Production

Credentials are already managed via GCP Secret Manager (see `deployment/cloud/gcp/infrastructure/secret_manager.py`). We will add a new secret for the MCP API key **following the same pattern as the JWT secret:**

**New secret in `secret_manager.py`:**
```python
# In SecretResources dataclass:
mcp_api_key: random.RandomPassword = None
mcp_api_key_sm: gcp.secretmanager.Secret = None

# In create_secrets():
SECRET_MCP_API_KEY = f"biocirv-{STACK_NAME}-mcp-api-key"

mcp_api_key = random.RandomPassword("mcp-api-key", length=64, special=False)
mcp_api_key_sm = gcp.secretmanager.Secret(
    "mcp-api-key-secret",
    secret_id=SECRET_MCP_API_KEY,
    replication=gcp.secretmanager.SecretReplicationArgs(
        auto=gcp.secretmanager.SecretReplicationAutoArgs(),
    ),
    opts=secret_opts,
)
gcp.secretmanager.SecretVersion(
    "mcp-api-key-version",
    secret=mcp_api_key_sm.id,
    secret_data=mcp_api_key.result,
)
```

**Wire into Cloud Run** (in `cloud_run.py`, following the JWT secret pattern):
1. Add volume mount for the new secret.
2. Add shell command to export it as `API_MCP_API_KEY` env var.
3. Store in the database as an active `ApiKey` record during deployment (via a separate one-time init step, or by having the app create it on first boot if missing).

**Key provisioning flow:**
1. Pulumi generates a random 64-char key.
2. Pulumi stores it in GCP Secret Manager.
3. Cloud Run mounts the secret and exports it to `API_MCP_API_KEY`.
4. App startup code checks if an `ApiKey` with prefix matching the first 8 chars of the API key already exists; if not, creates it (see step 7 below), owned by a dedicated service `ApiUser` (see "Owning `ApiUser`" below).

### Owning `ApiUser`: Design Clarification (resolves FK gap)

**Problem:** `ApiKey.api_user_id` is a `NOT NULL` foreign key to `api_user.id` (`src/ca_biositing/datamodels/ca_biositing/datamodels/models/auth/api_key.py:28`). The only existing creation path for `ApiUser` records is the admin-only `/v1/auth/register` endpoint (`v1/auth/router.py:99`), which is a human-driven flow requiring a unique `username` and a `hashed_password` — both `NOT NULL`. There is currently no "service account" concept in this schema. Auto-creating an `ApiKey` at startup with no corresponding `ApiUser` would violate the FK constraint and crash on insert.

**Decision:** Auto-provision a dedicated service `ApiUser` (not a human account) the first time the MCP key is set up, and attach the auto-created `ApiKey` to it.

- `username`: fixed, reserved value `mcp-service` (not derived from any secret, so it's stable across key rotations).
- `hashed_password`: a random, never-surfaced value generated with `secrets.token_urlsafe(32)` and hashed via the existing `get_password_hash()` — this account is never used for password login, only as the FK anchor for the API key. It satisfies the `NOT NULL` constraint without introducing a usable credential.
- `is_admin`: `False` — the MCP key must carry the same (non-admin) privilege level as any other API-key caller; it should never be able to reach admin-only endpoints like `/v1/auth/register`.
- `disabled`: `False`.

**Startup logic (updated):**
1. Look up `ApiUser` by `username == "mcp-service"`. If missing, create it (random password hash as above).
2. Look up `ApiKey` by `key_prefix` matching the first 8 chars of `API_MCP_API_KEY`. If missing, create it with `api_user_id` set to the service user's `id` from step 1.
3. Both lookups happen in the same idempotent startup routine, so a fresh environment provisions both rows in one pass, and a subsequent boot with the same env var is a no-op on both.

This mirrors the existing admin-registration pattern (`ApiUser` + password hash) rather than inventing a new schema concept, so no model or migration changes are needed — only startup code.

### Auto-Provisioning DB Credential at Startup: Design Clarification

The app's startup code will check if an `ApiKey` record exists with the prefix of the current `API_MCP_API_KEY` env var. If not, it creates one (after ensuring the owning `mcp-service` `ApiUser` exists, per above) with:
- `api_user_id`: the `mcp-service` `ApiUser`'s `id`
- `key_prefix`: first 8 chars of the env var (after hashing the full key)
- `key_hash`: Argon2 hash of the full env var
- `is_active`: true
- `rate_limit_per_minute`: 60 (or a configured default)

**Frequency & idempotency:** This check runs on every app startup, but is idempotent — if the record already exists (by prefix), no new record is created. This is safe because the prefix check is exact: even if Secret Manager rotates the key, a new `API_MCP_API_KEY` value will have a different prefix and will create a new `ApiKey` record (the old one remains in the DB but will never match, since `validate_api_key()` does prefix-based lookup). No DB migration or manual cleanup is needed; old rotated keys just expire naturally when never matched. If a key is rotated while the app is running, the in-flight app instance continues using the old key; only new instances (via Cloud Run rolling deploy) see the new key. This is correct behavior. The `mcp-service` `ApiUser` itself is created once and reused across all rotations — only the `ApiKey` row changes on rotation.

**Concurrency:** If Cloud Run scales to multiple instances during a deploy, multiple instances may simultaneously check and insert the same `ApiUser` and/or `ApiKey` record. This is safe because:
- Postgres uniqueness constraints prevent duplicate rows (`ApiUser.username` is unique; `key_prefix` lookup combined with `is_active=true` prevents duplicate active keys for the same prefix).
- Each INSERT is wrapped in a transaction; if two instances race, one succeeds and the other fails the constraint check, which is caught and ignored (idempotent). This applies to both the `ApiUser` lookup/insert and the `ApiKey` lookup/insert — the `ApiUser` step must complete (or be caught as a duplicate and re-queried) before the `ApiKey` step, since the latter needs a valid `api_user_id`.
- Both instances proceed to use the same key successfully.

**Startup validation:** If `API_MCP_API_KEY` is empty/missing and `dev_mode=False` (i.e., running in production without auth disabled), the app logs a FATAL error and exits. This prevents accidentally starting a production instance with no key configured.

---

## 5. Hybrid-Query Skill Update Plan

The skill's `hybrid_query_client.py` currently sends **zero auth headers**. Once auth is enforced, local dev will break unless the skill is updated.

**Changes to `/Users/pjsmitty301/ca-biositing/.claude/skills/hybrid-query/scripts/hybrid_query_client.py`:**

**After line 37** (where `_HEADERS` is defined):
```python
_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

# Add MCP API key to headers if set (for remote/prod use, or local testing with explicit key)
_mcp_api_key = os.environ.get("BIOSITING_MCP_API_KEY")
if _mcp_api_key:
    _HEADERS["X-API-Key"] = _mcp_api_key
```

**Update `_post()` function** (around line 55) to use the global `_HEADERS`:
```python
def _post(url: str, payload: dict[str, Any], session_id: str | None) -> requests.Response:
    headers = dict(_HEADERS)  # Use the global headers which now includes X-API-Key if set
    if session_id:
        headers["mcp-session-id"] = session_id
    return requests.post(url, json=payload, headers=headers, timeout=30)
```

**Update `/Users/pjsmitty301/ca-biositing/.claude/skills/hybrid-query/SKILL.md`:**

Add new "Auth" subsection in the workflow section (after "The two servers" table, before "Workflow"):

```markdown
## Auth

**Local development:**
- `pixi run start-webservice` runs the ca-biositing server without auth by default.
- To test auth locally, set `BIOSITING_MCP_API_KEY` before running the client:
  ```bash
  export BIOSITING_MCP_API_KEY="sk_dev_..." # Your dev API key
  pixi run python .claude/skills/hybrid-query/scripts/hybrid_query_client.py test
  ```

**Staging / Production:**
- The ca-biositing server requires authentication on `/mcp` via X-API-Key header (or Bearer token).
- Obtain an API key from your administrator (via ca-biositing's key management API or the ops team).
- Set the env var before querying:
  ```bash
  export BIOSITING_MCP_API_KEY="<your-key>"
  pixi run python .claude/skills/hybrid-query/scripts/hybrid_query_client.py test
  ```
- The script automatically adds the key to all requests via the `X-API-Key` header.
```

Also update the "Gotchas" section to note:
```markdown
- **Local dev without `BIOSITING_MCP_API_KEY`:** Works out of the box; auth is disabled in dev mode.
- **Staging/production:** Must set `BIOSITING_MCP_API_KEY` env var or requests will fail with 401.
```

---

## 6. File-by-File Change List

| File | Change | Lines/Notes |
|------|--------|-------------|
| `src/ca_biositing/webservice/ca_biositing/webservice/main.py` | Add pure ASGI middleware class (implementing `__call__(scope, receive, send)` directly) before FastAPI app creation; modify mount to wrap with middleware. Middleware only intercepts auth before request reaches MCP app; passes through response untouched (no buffering). | ~25 new lines around line 173 |
| `src/ca_biositing/webservice/ca_biositing/webservice/config.py` | Add `dev_mode: bool` field with environment-aware default (`_is_local_dev` derived from presence of `INSTANCE_CONNECTION_NAME`). Default is True locally, False in Cloud Run. | ~6 lines after line 66 |
| `src/ca_biositing/webservice/ca_biositing/webservice/dependencies.py` | (Optional) Export `_resolve_jwt_user()` or create a new `get_mcp_user()` function for middleware to reuse (avoid code duplication). May keep as-is if middleware calls `validate_api_key()` directly. | 0 lines if validate_api_key is reused directly |
| `src/ca_biositing/webservice/ca_biositing/webservice/mcp_server.py` | No changes required (auth is enforced before reaching MCP handler). | — |
| `src/ca_biositing/webservice/ca_biositing/webservice/services/auth_service.py` | Add `ensure_mcp_service_key(session, raw_key)`: idempotently creates the `mcp-service` `ApiUser` (if missing) and the matching `ApiKey` (if missing), per "Owning `ApiUser`" design above. Called from `main.py` startup/lifespan when `API_MCP_API_KEY` is set. | ~30 new lines |
| `src/ca_biositing/webservice/tests/test_mcp.py` | Add two new test functions: (1) fast non-integration test that /mcp returns 401 with no auth, (2) integration test confirming a valid API key works end-to-end. | ~30 new lines |
| `deployment/cloud/gcp/infrastructure/config.py` | Add `SECRET_MCP_API_KEY` constant. | ~1 line after line 55 |
| `deployment/cloud/gcp/infrastructure/secret_manager.py` | Add `mcp_api_key` and `mcp_api_key_sm` fields to `SecretResources` dataclass; add creation logic in `create_secrets()`. | ~30 new lines |
| `deployment/cloud/gcp/infrastructure/cloud_run.py` | Add volume mount and secret for MCP key; wire into shell cmd to export `API_MCP_API_KEY`. | ~15 new lines (volume + env export) |
| `.claude/skills/hybrid-query/scripts/hybrid_query_client.py` | Add `_mcp_api_key` env var reading; inject into `_HEADERS` if set. | ~3 lines after line 37 |
| `.claude/skills/hybrid-query/SKILL.md` | Add "Auth" subsection describing local dev bypass and key setup. | ~20 new lines |
| `plans/mcp-architecture.md` | Update §3 ("Auth Strategy") to note that the static-key system was superseded by `ApiKey` infrastructure; add a note at the end reconciling the two plans. | ~5 lines |

---

## 7. Implementation Steps (Phased Rollout)

### Phase 1: Local Auth Infrastructure (No Public Impact)

**Goal:** Develop and test auth locally; ensure hybrid-query skill works.

**Steps:**
1. Create pure ASGI middleware class (`MCPAuthMiddleware`) in `main.py` (or new `ca_biositing/webservice/middleware.py`). Middleware implements `__call__(scope, receive, send)` directly (not `BaseHTTPMiddleware`) to avoid buffering SSE streaming responses. Auth validation reuses `validate_api_key()` from service layer.
2. Update `config.py`: add `dev_mode` field with environment-aware default (`_is_local_dev` derived from `INSTANCE_CONNECTION_NAME`).
3. Wrap `/mcp` mount with middleware: `app.mount("/mcp", MCPAuthMiddleware(mcp.streamable_http_app(), session_factory, config))`.
4. Update `hybrid_query_client.py` to read `BIOSITING_MCP_API_KEY` env var and inject into X-API-Key header.
5. Update `SKILL.md` with auth documentation (local dev without key works by default; staging/production requires key).
6. Local testing:
   - `pixi run start-webservice` → `/mcp` is open (dev mode auto-enabled by absence of `INSTANCE_CONNECTION_NAME`).
   - Set `BIOSITING_MCP_API_KEY=<value>`, test hybrid-query skill → middleware validates key (still allows requests because dev mode is on, but exercises auth code path).
   - Set `API_DEV_MODE=false` env var, restart webservice → `/mcp` returns 401 without valid key; only succeeds with valid X-API-Key header.

**Time estimate:** 4–6 hours.

### Phase 2: Testing (Before Staging Deploy)

**Goal:** Verify auth at the code level.

**Steps:**
7. Write non-integration test: POST to `/mcp` with no auth → expect 401 with valid JSON-RPC error envelope.
8. Write integration test: POST to `/mcp` with valid X-API-Key → expect 200 + valid MCP response.
9. CI/CD runs both tests locally (non-integration) and optionally in staging (integration).

**Time estimate:** 2–3 hours.

### Phase 3: Staging Secret & Deployment

**Goal:** Enable auth on staging. Auth is automatically enabled on Cloud Run (via auto-detection of `INSTANCE_CONNECTION_NAME`).

**Sequencing (critical):**
1. Deploy code changes from Phases 1–2. The auto-detected dev mode means:
   - Local: `dev_mode=True` (auth off)
   - Cloud Run: `dev_mode=False` (auth on) — **but only if `API_MCP_API_KEY` is provisioned**
2. Create GCP Secret Manager secret for MCP API key via Pulumi (update `secret_manager.py` and `cloud_run.py`).
3. Deploy Pulumi stack → triggers new Cloud Run revision with secret mounted and exported as `API_MCP_API_KEY` env var.
4. App starts, detects `INSTANCE_CONNECTION_NAME` (Cloud Run), sets `dev_mode=False`, checks for `API_MCP_API_KEY` (present), auto-creates `ApiKey` record if missing.
5. `/mcp` now requires auth. Verify: curl staging `/mcp` without auth → 401; with valid X-API-Key header → 200 + MCP response.

**Deployment safety:**
- Pre-deploy (code only, no secret): staging `/mcp` remains unauth'd (current state).
- Post-Pulumi (secret now mounted): if app starts, secret is available, `dev_mode=False`, auth is ON.
- If Pulumi deploy fails to mount secret: app starts, checks for `API_MCP_API_KEY`, finds it empty, logs FATAL, exits (fail-safe: doesn't silently leave auth off).

**Rollback:** If needed, revert Pulumi changes to remove the secret, then redeploy Cloud Run (old revision without secret mounted, `dev_mode` still False, app fails to start, roll back to prior revision that didn't have code changes). Or: keep the secret but restore a prior Cloud Run revision that didn't have the middleware code.

**Time estimate:** 2–3 hours (Pulumi stack + verification).

### Phase 4: Production

**Goal:** Secure production `/mcp` with same approach.

**Steps:**
1. Same as Phase 3 but for production stack.
2. Notify downstream consumers (e.g., Claude, other agents using the API) to update their MCP client config with the new API key.
3. Monitor logs for any 401 errors (indicate clients still using old/no-auth requests).

**Time estimate:** 2–3 hours (repeats Phase 3 process).

---

## 8. Test Plan

### Fast (Non-Integration) Tests

**File: `src/ca_biositing/webservice/tests/test_mcp_auth.py` (new file)**

```python
import pytest
from fastapi.testclient import TestClient
from ca_biositing.webservice.main import app

@pytest.mark.asyncio
async def test_mcp_returns_401_without_auth():
    """Verify /mcp returns 401 with valid MCP error envelope when no credentials supplied."""
    with TestClient(app) as client:
        response = client.post(
            "/mcp/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 1,
            },
            headers={"Accept": "application/json, text/event-stream"},
        )
        assert response.status_code == 401
        body = response.json()
        assert "error" in body or "jsonrpc" in body  # Valid MCP error envelope

@pytest.mark.asyncio
async def test_mcp_accepts_x_api_key_header(test_api_key):
    """Verify /mcp accepts X-API-Key header (requires valid key in test DB)."""
    with TestClient(app) as client:
        response = client.post(
            "/mcp/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 1,
            },
            headers={
                "Accept": "application/json, text/event-stream",
                "X-API-Key": test_api_key,
            },
        )
        # Should not be 401 (may be 200 if DB is available, or 500 if not — but not 401)
        assert response.status_code != 401
```

**Fixtures (in `conftest.py`):**
- `test_api_key`: Creates a test `ApiKey` record in the test DB before tests run, returns its raw key.

### Integration Tests

**In `src/ca_biositing/webservice/tests/test_mcp.py`** (existing file, modify):

Add a test that:
1. Supplies a valid API key via X-API-Key header.
2. Calls `tools/list` → should return 200 + tool list (no auth failure).
3. Calls a relational tool → should execute successfully.

This test already runs as `@pytest.mark.integration` and requires a live DB, so it's the right place.

---

## 9. Reconciliation with Prior Plan

**File: `plans/mcp-architecture.md`** needs an update at the end:

```markdown
---

## 10. Auth Implementation Update (2026-09-29)

**Status Change:** The original "static API key list via `_BearerAuthASGI`" plan (§3) has been superseded by a more robust approach detailed in `plans/mcp_auth_implementation_plan.md`.

**Why:**
- The static-key system would require separate provisioning and rotation logic.
- Reusing the existing `ApiKey` infrastructure (hashed storage, revocation, per-key rate limiting, prefix-based lookup) is lower-maintenance and consistent with the `/v1/` REST API.
- The `/mcp` endpoint uses the same auth sources as `get_current_user()`: Bearer token, HTTP-only cookie, or X-API-Key header.

**Key Changes:**
- Auth is enforced via pure ASGI middleware (implementing `__call__(scope, receive, send)` directly, avoiding `BaseHTTPMiddleware` which buffers streaming responses). Reuses `validate_api_key()` from service layer.
- Config: `dev_mode` field with environment-aware default (True locally via absence of `INSTANCE_CONNECTION_NAME`; False in Cloud Run). Eliminates need to explicitly set env vars for normal deployments; fails safe (auth ON by default in production).
- Staging/production: generate and store MCP API key in GCP Secret Manager, wire into Cloud Run, auto-create `ApiKey` DB record on first boot (idempotent, handles secret rotation and concurrent instances).

**Hybrid-Query Skill:** Updated to read `BIOSITING_MCP_API_KEY` env var and inject into X-API-Key header for auth'd requests.

Refer to `plans/mcp_auth_implementation_plan.md` for full implementation details.
```

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Auth middleware breaks existing MCP clients before they're updated | Dev mode defaults to True locally (auto-detected via absence of `INSTANCE_CONNECTION_NAME`), so local workflows are unaffected. Staging/production auto-detect Cloud Run and default to `dev_mode=False` (auth on). Skill is updated in Phase 1. No env var config needed for normal rollout. Rollback risk is minimal. |
| Staging's public `/mcp` endpoint is currently exploitable; delay in auth means prolonged exposure | Prioritize Phase 3. The gap exists today; auth stops the clock. Document the risk clearly to stakeholders. The new default prevents accidental re-opening of the gap (production defaults to `dev_mode=False`). |
| MCP clients don't understand 401 error response | Use a valid MCP JSON-RPC error envelope (with `jsonrpc`, `error.code`, `error.message`). Most clients check `status_code` before parsing body, so a clear 401 is sufficient. |
| Shared `kb_api_key` budget can still be exhausted by a single attacker with a valid API key | True, but this is an existing architectural limit (the `kb_api_key` is app-wide). Mitigation: `ApiKey.rate_limit_per_minute` per caller limits aggressive use; add logging/alerting on KB calls to detect abuse patterns. Future work: per-key scopes or KB-specific rate limits. |
| Someone accidentally sets `API_DEV_MODE=true` in production, disabling auth | All prod configs should use Infrastructure-as-Code (Pulumi). Manual env var edits are audited. Startup validation: if `dev_mode=False` (production detected) and `API_MCP_API_KEY` is empty, app logs FATAL and exits. Cannot silently disable auth. |
| Secret provisioning fails; app boots without MCP API key in staging/production | Startup validation: if `dev_mode=False` (Cloud Run detected) and `API_MCP_API_KEY` is empty/missing, app logs FATAL error and exits (fail-safe). Prevents accidentally starting a production instance with no key configured. Ops must fix the secret before app can start. |
| Forgot to update hybrid-query skill → local tests break | Phase 1 includes skill update. Tested locally before proceeding. Document in SKILL.md that the key must be set in prod/staging. Local dev works without key by default. |

---

## 11. Key Decisions Summary

1. **Auth system:** Reuse existing `ApiKey` infrastructure (hashed, revokable, rate-limited) instead of static-key list. ✅
2. **Dev mode default:** Auto-detect environment (local dev: `dev_mode=True` by default; Cloud Run: `dev_mode=False` by default). Derive from absence/presence of `INSTANCE_CONNECTION_NAME`, like `datamodels/config.py` does for Docker detection. Fails safe: production defaults to auth ON; local defaults to auth OFF (zero friction for iteration). ✅
3. **Middleware implementation:** Pure ASGI middleware (raw `__call__(scope, receive, send)`, not `BaseHTTPMiddleware`) to avoid buffering SSE streaming responses. Auth rejection happens before inner app sees request; success path is 100% pass-through. ✅
4. **Auto-provisioning:** App checks for `ApiKey` record with matching prefix on every startup; creates one if missing (idempotent), owned by a dedicated `mcp-service` `ApiUser` (auto-created once, reused across key rotations) to satisfy `ApiKey.api_user_id`'s `NOT NULL` FK. Handles secret rotation and concurrent instances safely. ✅
5. **Skill handling:** Hybrid-query skill updated to read `BIOSITING_MCP_API_KEY` env var and inject into X-API-Key header. Local dev works without key; staging/production requires key. ✅
6. **KB-proxy tools scoping:** Same auth gateway + per-key rate limit is sufficient; no stricter control needed. ✅
7. **Error response:** Valid MCP JSON-RPC error envelope at HTTP 401 for graceful client degradation. ✅
8. **Phased rollout:** Code (with auto-detected dev mode) → test → staging (auto-detects Cloud Run, auth ON) → production (same pattern). Dev mode doesn't need explicit env var flips for normal deploy. ✅

---

## 12. File Structure & Implementation Order

```
ca-biositing/
├── src/ca_biositing/webservice/
│   ├── ca_biositing/webservice/
│   │   ├── main.py                   # ADD: middleware class + mount wrapper
│   │   ├── config.py                 # ADD: dev_mode field
│   │   ├── dependencies.py           # (no change if validate_api_key reused directly)
│   │   └── mcp_server.py             # (no change)
│   ├── tests/
│   │   ├── test_mcp_auth.py          # ADD: fast non-integration tests
│   │   └── test_mcp.py               # MODIFY: add integration test with auth
│   └── pyproject.toml                # (no change)
├── deployment/cloud/gcp/infrastructure/
│   ├── config.py                     # ADD: SECRET_MCP_API_KEY constant
│   ├── secret_manager.py             # ADD: mcp_api_key fields + creation logic
│   └── cloud_run.py                  # ADD: volume mount + secret export
├── .claude/skills/hybrid-query/
│   ├── SKILL.md                      # ADD: Auth section
│   └── scripts/hybrid_query_client.py # ADD: read & inject BIOSITING_MCP_API_KEY
└── plans/
    ├── mcp-architecture.md           # UPDATE: reconciliation note at end
    └── mcp_auth_implementation_plan.md # THIS FILE

Implementation order:
  1. main.py + config.py
  2. test_mcp_auth.py + test_mcp.py updates
  3. hybrid_query_client.py + SKILL.md
  4. secret_manager.py + cloud_run.py + config.py (Pulumi)
  5. mcp-architecture.md update
```

---

## 13. Success Criteria

✅ **Local Development**
- [ ] `pixi run start-webservice` starts webservice; `/mcp` is open by default.
- [ ] Setting `BIOSITING_MCP_API_KEY=<key>` makes hybrid-query skill send credentials.
- [ ] Setting `API_DEV_MODE=false` requires valid credentials to call `/mcp`.
- [ ] Non-integration tests pass: `/mcp` returns 401 without auth.

✅ **Staging Deployment**
- [ ] GCP Secret Manager stores MCP API key.
- [ ] Cloud Run mounts secret and exports as `API_MCP_API_KEY` env var.
- [ ] App creates the `mcp-service` `ApiUser` and matching `ApiKey` record on first boot (or manual insert succeeds).
- [ ] With `API_DEV_MODE=false`, `/mcp` returns 401 without auth.
- [ ] With valid X-API-Key header, `/mcp` returns 200 + valid MCP response.
- [ ] Integration tests pass against live DB.

✅ **Production**
- [ ] Same as staging.
- [ ] Downstream clients (Claude, agents) receive new API key and updated MCP client config.
- [ ] Logs show no unexpected 401 errors (all clients successfully authenticating).

✅ **Skill & Documentation**
- [ ] Hybrid-query SKILL.md documents how to set `BIOSITING_MCP_API_KEY`.
- [ ] hybrid_query_client.py injects key into X-API-Key header when present.
- [ ] Local dev workflows still work without setting key (dev mode default).

---

## Summary

This plan secures the `/mcp` endpoint by:
1. **Reusing proven infrastructure:** `ApiKey` system + `validate_api_key()` + per-key rate limiting.
2. **Environment-aware dev mode:** Auto-detected from `INSTANCE_CONNECTION_NAME` (absent locally = dev mode on; present in Cloud Run = dev mode off). Eliminates config friction; fails safe (auth ON by default in production).
3. **Streaming-safe middleware:** Pure ASGI middleware (raw `__call__(scope, receive, send)`, not `BaseHTTPMiddleware`) to avoid buffering SSE responses. Auth rejection happens pre-request; success path is transparent pass-through.
4. **Safe auto-provisioning:** App auto-creates a dedicated `mcp-service` `ApiUser` and matching `ApiKey` DB record on first boot if missing (idempotent, handles secret rotation and concurrent instances, satisfies the FK constraint on `ApiKey.api_user_id`). Startup validation fails fast if secret is missing in production.
5. **Skill integration:** Hybrid-query client updated to read `BIOSITING_MCP_API_KEY` and inject via X-API-Key header. Local dev works without key; staging/production require it.
6. **Phased rollout:** Code (auto-detects environment) → test → staging (auto-enables auth) → production, minimizing manual config and risk of silent failures.
7. **Strong guarantees:** Each API key is rate-limited, revokable, and hashed securely. No two parallel credential systems.

The approach supersedes the static-key list plan in `mcp-architecture.md` and provides better long-term maintainability, simpler deployment, and lower operational friction.

---

**Plan Author:** Claude Haiku 4.5
**Date:** 2026-09-29
**Status:** Phase 1–3 code complete; staging deploy pending (`pixi run cloud-plan` still shows the MCP secret as 3 resources to create — `cloud-deploy` has not yet been run for this change).
**Next Step:** Run `cloud-deploy` for staging (Phase 3), verify, then Phase 4 — Production deployment.
