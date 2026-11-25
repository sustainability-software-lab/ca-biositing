# MCP Server Design (follow-up to PR #484)

- **Issue:** sustainability-software-lab/ca-biositing#494
- **Status:** Revised after two rounds of security review on #565 (2026-11-24);
  pending re-review
- **Date:** 2026-11-19
- **Reference PoC:** PR #484 / branch `mcp` (design input only — not merged, not
  a starting diff)

## 1. Intent

### Outcome

AI agents can discover and query ca-biositing feedstock, analysis, USDA, and
(once #545 merges) public-dataset data through a Model Context Protocol (MCP)
server embedded in `ca_biositing.webservice`. The server is secure by default in
Cloud Run, and adding MCP tools for a newly merged API is a small,
self-contained PR guided by discoverable documentation.

### Clients that must be supported

| Client                                                 | Access path                                         |
| ------------------------------------------------------ | --------------------------------------------------- |
| Internal agents / scripts (Claude Code, CI)            | `/mcp` with `Bearer <ApiKey>` or `Bearer <API JWT>` |
| Researchers via Claude Desktop / IDE clients           | `/mcp` with OAuth 2.1 (or ApiKey / API JWT)         |
| Hosted connectors (claude.ai, ChatGPT)                 | `/mcp` with OAuth 2.1 (DCR + PKCE)                  |
| Anonymous public users (open data, mirrors /v1/public) | `/mcp/public`, no auth, rate-limited                |

### Access model

**API access implies MCP access.** The single source of truth for who may use
the authenticated `/mcp` endpoint is the existing `ApiUser` table, which already
governs `/v1/feedstocks/*` and is managed by admins via `/v1/auth/register`.
Every credential `/mcp` accepts resolves to an active (not `disabled`)
`ApiUser`:

- an existing `ApiKey` (same keys as the REST `X-API-Key` header);
- an existing API JWT from `/v1/auth/token`;
- an MCP OAuth 2.1 access token, whose Google login is linked to an `ApiUser` by
  verified email on first login and by Google `sub` after that (§5).

No separate MCP user list exists, and the portal email allowlist does not grant
MCP access. Disabling an `ApiUser` revokes REST and MCP access together.

### Success criteria

1. All four client types above can connect and call tools appropriate to them.
   Any active `ApiUser` can use `/mcp` without extra provisioning; anyone who is
   not an active `ApiUser` cannot.
2. In any deployed environment the app refuses to boot if auth configuration is
   missing or insecure (fail closed; §3 Boot guard). Auth is disabled only when
   `dev_mode` is explicitly set, and then only on loopback.
3. An authenticated-tier tool can never be reachable from `/mcp/public`.
4. Adding tools for a new API requires one new module plus one registry
   registration, following a documented checklist enforced by tests.
5. Tool handlers never block the event loop; tool outputs are uniformly typed;
   DB/internal errors never leak to clients.

### Out of scope

- **Knowledge-base (`biocirv-kb`) proxy tools.** Moved to a separate issue (see
  §9). This design only reserves the `kb` tier name and the `kb:query` scope so
  that follow-up is purely additive.
- Write/mutating tools. All tools are read-only, and this is enforced by a
  read-only database role (§4), not only by convention.
- `datamodels/config.py` Docker/local host auto-detection from the PoC — lands
  as its own standalone PR (PR 0), not bundled with MCP work.

## 2. Key decisions

| Decision          | Choice                                                                                                                                                | Rationale                                                                                                                                                                                                                        |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDK               | `mcp>=2.3,<3`, `mcp.server.mcpserver.MCPServer`                                                                                                       | `mcp.server.fastmcp` raises `ModuleNotFoundError` in 2.x; a bounded pin prevents a relock from breaking the webservice at import time (PoC flaw).                                                                                |
| Auth              | Native OAuth 2.1 via SDK `auth_server_provider` + `token_verifier`, embedded Google-OIDC proxy with our own consent page; ApiKey and API JWT accepted | Hosted connectors need OAuth discovery + DCR, which Google does not provide directly; a separate MCP Google client (not the portal's) keeps ID tokens from being replayed between them; no new vendor; we host no password form. |
| Who gets access   | Any active `ApiUser` (Google login linked by verified email once, then by Google `sub`)                                                               | API access implies MCP access; one user list, one place to grant and revoke (§1 Access model).                                                                                                                                   |
| Tool registration | Per-domain modules + tier-filtered registry over the service layer                                                                                    | Absorbs new APIs with one module each; service layer stays the single source of truth; deliberate, agent-quality tool descriptions.                                                                                              |
| Anonymous access  | Separate mount `/mcp/public`                                                                                                                          | SDK auth gates a whole streamable-HTTP endpoint, so public and authenticated tools cannot safely share one mount.                                                                                                                |
| Test DB           | Shared non-prod (dev) DB with per-run namespacing + cleanup job                                                                                       | Team choice; risks mitigated in §7.                                                                                                                                                                                              |
| Delivery          | OAuth first (PR 1), then small follow-up PRs                                                                                                          | The riskiest, most security-sensitive piece gets focused review; everything after is additive.                                                                                                                                   |

## 3. Architecture

```
src/ca_biositing/webservice/ca_biositing/webservice/mcp/
  __init__.py
  registry.py      ToolSpec + Registry; build_server(tiers) -> MCPServer
  runtime.py       handler wrapper: threadpool, session scope, output model, error mapping, logging
  principal.py     Principal(api_user_id, username, kind, scopes)
  tools/
    _template.py   copy-me scaffold for new API modules
    feedstocks.py  availability + analysis tools        tier=authenticated
    usda.py        census + survey tools                tier=authenticated
    public.py      PublicDatasetService (#545) tools    tier=public       (PR 4)
    # kb.py        reserved for KB follow-up issue      tier=kb
  auth/
    provider.py    OAuthAuthorizationServerProvider (DCR + Google OIDC proxy)
    verifier.py    TokenVerifier: MCP OAuth token, existing API JWT, or existing ApiKey
    routes.py      consent page + Google OIDC callback routes
    app.py         exact-path ASGI dispatcher, child lifespans, host check (§3 Wiring)
    ratelimit.py   per-IP (pre-auth) and per-principal (post-auth) limiters
```

### Mounts

| Path          | Tiers served                             | Auth                                   |
| ------------- | ---------------------------------------- | -------------------------------------- |
| `/mcp`        | `public`, `authenticated` (+ `kb` later) | OAuth 2.1, API JWT, or `ApiKey` bearer |
| `/mcp/public` | `public` only                            | None; per-IP rate limit (§3 Client IP) |

Both servers are built from the same `Registry` by filtering on tier. A tool
outside the requested tier set is never registered on that server — exclusion is
structural, not a call-time check. Both use `stateless_http=True` (Cloud Run has
multiple instances and no session affinity). The OAuth endpoints are listed in
§5 Endpoints; protected-resource metadata for `/mcp` lives at
`/.well-known/oauth-protected-resource/mcp` (RFC 9728 path insertion), not at
the root path.

### Wiring into the FastAPI app

`MCPServer` raises `ValueError` if given both `auth_server_provider` and
`token_verifier`, and with only a provider it wraps it in
`ProviderTokenVerifier`, which would never run our JWT and ApiKey paths. So:

- The authenticated server is built with **only our `token_verifier`** plus
  `auth=AuthSettings(issuer_url=mcp_issuer_url, resource_server_url=mcp_resource_url, validate_token_resource=True, required_scopes=["data:read"])`.
  Its `streamable_http_app()` then serves `/mcp` behind `RequireAuthMiddleware`
  and serves `/.well-known/oauth-protected-resource/mcp`.
- The SDK's authorization-server routes come from
  `create_auth_routes(provider, issuer_url, client_registration_options, revocation_options)`
  (`/.well-known/oauth-authorization-server`, `/register`, `/authorize`,
  `/token`, `/revoke`), added to the **parent** FastAPI app together with our
  consent and callback routes (§5 Endpoints).
- The public server has no auth settings at all.

**Paths.** `streamable_http_app()` registers its own route at
`streamable_http_path` (default `/mcp`), so mounting it under a `/mcp` prefix
would serve `/mcp/mcp`. Instead each child app is built with its full external
path (`streamable_http_path="/mcp"` and `"/mcp/public"`), and the parent
dispatches **exact** paths to it, not by prefix:

| External path                                       | Dispatched to           |
| --------------------------------------------------- | ----------------------- |
| `/mcp`, `/.well-known/oauth-protected-resource/mcp` | authenticated child app |
| `/mcp/public`                                       | public child app        |
| everything else                                     | FastAPI as today        |

A small ASGI dispatcher in front of FastAPI does this. It also keeps each
child's own middleware (`AuthenticationMiddleware`, transport security) from
running on REST routes, and a token sent to `/mcp/public` is never even read.

**Lifespans.** Starlette does not run a mounted or dispatched child app's
lifespan, and without it the session manager fails with "Task group is not
initialized". The parent FastAPI lifespan therefore enters both child apps'
lifespan contexts (which run `session_manager.run()`) in an `AsyncExitStack`.

A prototype of exactly this wiring (exact-path dispatch, both child lifespans
entered from the parent, REST routes untouched) was run against Starlette in the
webservice environment while revising this spec. A startup test in PR 1 calls
both mounts through the real app (§7).

### Feature flag

`mcp_enabled` (default `False`) controls everything in this spec that can stop
the service from starting or change its routes:

- when `False`, no MCP routes are registered (no `/mcp`, `/mcp/public`,
  `/.well-known/oauth-*`, `/register`, `/authorize`, `/token`, `/revoke`,
  consent, or callback), and the MCP-specific boot-guard checks are skipped;
- the REST-side security changes in PR 1 (`token_use`, split portal key, admin
  endpoints, and their boot-guard checks) are **not** behind the flag.

Infrastructure is provisioned before PR 1 (PR 0.5, §6), so in the normal order
the flag is not what keeps the service up. It is the second safety: if PR 1
reaches an environment before PR 0.5 has been applied there, the REST service
still starts and MCP simply stays off. It is removed in a final cleanup PR (§6)
once MCP is live in production.

### Registry contract

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str                 # snake_case, globally unique
    description: str          # agent-facing; >= 40 chars; names the discovery tool to call first
    tier: Literal["public", "authenticated", "kb"]
    scopes: tuple[str, ...]   # required OAuth scopes, e.g. ("data:read",)
    handler: Callable[..., BaseModel]   # sync fn(session, **args) -> Pydantic model
    output_model: type[BaseModel]
```

Each `tools/<domain>.py` exposes `def register(registry: Registry) -> None`.
`registry.py` imports and calls each domain module explicitly (no import-time
magic). `tier` has no default — omitting it is a type error — and the guard test
in §7 fails on any spec missing a tier, output model, or adequate description.

### Configuration

| Setting                                                                       | Purpose                                                                                                             |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `deployment_env` (`local` \| `staging` \| `production`, default `production`) | Explicit environment. Anything other than `local` is "deployed" and fails closed                                    |
| `mcp_enabled` (default `False`)                                               | Turns MCP routes and MCP boot-guard checks on (§3 Feature flag). Removed in the final cleanup PR                    |
| `dev_mode` (default `False`)                                                  | Disables MCP auth. Allowed only when `deployment_env=local` **and** the bound host is loopback (checked at startup) |
| `server_bind_host`                                                            | The host Uvicorn binds to, passed through from the start command so the boot guard can check it                     |
| `mcp_resource_url`                                                            | Canonical `/mcp` URL: OAuth audience and resource server URL (§5)                                                   |
| `mcp_issuer_url`                                                              | OAuth issuer (same origin as `mcp_resource_url`)                                                                    |
| `mcp_google_client_id` / `mcp_google_client_secret`                           | **Separate** Google OAuth client for MCP (not the portal's); secret from Secret Manager                             |
| `mcp_consent_signing_key` (+ optional previous key)                           | Signs remembered-consent cookies; rotatable (§5 Flow)                                                               |
| `portal_jwt_secret_key`                                                       | Signing key for portal session tokens, split from `jwt_secret_key` (§5 API JWT changes)                             |
| `mcp_redirect_host_allowlist`                                                 | Optional allowlist of `https` redirect hosts for DCR (§5)                                                           |
| `mcp_public_rate_limit`                                                       | Per-IP limit for `/mcp/public`                                                                                      |
| `mcp_trusted_proxy_hops`                                                      | Number of trusted proxies in front of the app, used to pick the client IP from `X-Forwarded-For` (§3 Client IP)     |
| `mcp_allowed_hosts`                                                           | Host allowlist (§3 Host and origin checks). In `local` it defaults to `localhost`, `127.0.0.1`, `[::1]`             |
| `mcp_allowed_origins`                                                         | `Origin` allowlist for browser-based MCP clients. In `local` it defaults to the loopback origins                    |
| `mcp_db_url`                                                                  | Connection for the read-only MCP database role (§4)                                                                 |

**Boot guard.** When `deployment_env` is not `local`, the app raises at startup
if any of these hold.

Always (REST and MCP; settings provisioned in PR 0.5, §6):

- `dev_mode` is true;
- `jwt_secret_key` or `portal_jwt_secret_key` is empty or equals the known
  default `changeme-only-for-local-dev-do-not-use-in-prod!!`, or the two keys
  are equal;
- `google_client_id` (portal) is empty (an empty audience would accept ID tokens
  issued for any Google client).

Only when `mcp_enabled` is true:

- `mcp_google_client_id` or `mcp_google_client_secret` is empty;
- `mcp_resource_url`, `mcp_issuer_url`, or `mcp_db_url` is missing, or
  `mcp_resource_url` is not `https`;
- `mcp_allowed_hosts` is empty, or does not contain the host of
  `mcp_resource_url`.

In every environment, `dev_mode` true with a non-loopback `server_bind_host`
raises. This matters because the Cloud Run start command binds `--host 0.0.0.0`;
a convention alone would not stop `dev_mode` there.

Detection uses the explicit `deployment_env` setting, not `K_SERVICE`, so
Compose, VM, or GKE deployments also fail closed. The default is `production`,
so forgetting to set it can only make the app stricter.

### Host and origin checks

The SDK's DNS-rebinding protection (`TransportSecuritySettings`) has separate
host and origin allowlists, and it only covers the streamable-HTTP transport.
So:

- Both MCP child apps get explicit
  `TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=mcp_allowed_hosts, allowed_origins=mcp_allowed_origins)`;
  we never rely on the SDK's localhost-only defaults, and protection is never
  turned off, including in `dev_mode`.
- The parent app checks `Host` against `mcp_allowed_hosts` for **every** MCP and
  OAuth route (`/register`, `/authorize`, `/token`, `/revoke`, metadata,
  consent, callback) before they run. A request on the raw `*.run.app` host is
  rejected on these routes exactly as on `/mcp`. REST routes are unaffected.
- `mcp_allowed_origins` is empty outside `local` unless a browser-based client
  needs it; adding an origin is the supported way to enable one, so there is no
  reason to turn protection off.

### Client IP

Per-IP limits (on `/mcp/public` and pre-auth on `/mcp`) take the client IP from
`X-Forwarded-For` by counting `mcp_trusted_proxy_hops` entries from the
**right** (the entry appended by the last trusted proxy, i.e. Google's front end
on Cloud Run). Left-most entries can be set by the client and are ignored. With
zero trusted hops the socket peer address is used.

The #545 limiter keeps counts in memory per instance, so the effective limit is
`limit × instances`. That is acceptable for abuse damping on `/mcp/public` (max
instances is bounded by Cloud Run config); the documented limit says "per
instance". Public-tier database sessions also run under the read-only role's
statement timeout (§4), which bounds the cost of any single anonymous query.

## 4. Tool contract and runtime

### Contract (every tool)

- Returns a Pydantic model, so the SDK emits `structuredContent` and
  `outputSchema`. Reuse existing `v1/**/schemas.py` response models where
  possible so REST and MCP shapes cannot drift.
- Description is written for an LLM and names the discovery tool to call first
  (e.g. "Call `list_geoids` to find valid `geoid` values").
- Annotated `readOnlyHint=True`.
- List results are bounded: a `limit` argument with a default and maximum, plus
  a `truncated: bool` field in the output.

### Runtime wrapper (`runtime.py`)

Handlers are plain synchronous functions `fn(session, **args)`. The wrapper:

1. **Checks scopes.** Reads the verifier's `AccessToken` from the SDK auth
   context (`get_access_token()`), builds a `Principal` from it (§5 Verifier
   contract), and rejects the call with `isError=True` ("insufficient scope")
   unless the principal holds every scope in `ToolSpec.scopes`. The SDK only
   enforces `AuthSettings.required_scopes` for the whole endpoint, so this check
   is what makes per-tool scopes such as the future `kb:query` real. Public-tier
   tools on `/mcp/public` have no principal and declare no scopes.
2. **Applies the per-principal rate limit** (§5 Rate limiting) on authenticated
   mounts.
3. Runs the handler via `anyio.to_thread.run_sync` (fixes the PoC's event-loop
   blocking).
4. Opens a session per call on the **read-only MCP engine** and closes it in
   `finally` (see Database access below).
5. Validates that the return value is an instance of `output_model`.
6. Maps exceptions (below).
7. Logs `tool`, `principal.api_user_id`, `principal.kind`, `tier`, duration,
   outcome. Emails, tokens, and tool argument values are never logged. Logs
   follow the existing Cloud Logging retention for the service.

### Database access

Tool sessions never use the webservice's read-write connection. They use a
separate engine built from `mcp_db_url`, which connects as a dedicated
**read-only Postgres role** (`biocirv_mcp_ro`):

- `GRANT SELECT` only, on the schemas and views that tools read; no access to
  `api_user`, `api_key`, or the `mcp_auth` schema (§5 Storage);
- `default_transaction_read_only = on` and `statement_timeout` (e.g. 10 s) set
  on the role itself, so a tool cannot exceed them even by mistake;
- provisioned in PR 0.5 with the same Pulumi pattern as the existing
  `READONLY_USERS` (`deployment/cloud/gcp/infrastructure/config.py`,
  `secret_manager.py`), with its password in Secret Manager.

The verifier, OAuth provider, and rate limiter continue to use the normal
read-write engine, because they must write tokens, consents, and counters.

In `deployment_env=local`, `mcp_db_url` may point at the local database with the
same role created by a dev setup script.

### Error mapping

| Raised                                                 | Client receives                                                                |
| ------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `webservice.exceptions` not-found / validation errors  | `isError=True`, actionable message (e.g. "unknown geoid; call list_geoids")    |
| `SQLAlchemyError` or any unexpected exception          | `isError=True`, "Internal error (ref=<uuid>)"; full trace logged only          |
| Missing/invalid token                                  | Rejected by SDK auth at the HTTP layer (401) before the tool runs              |
| Database or other infrastructure error in the verifier | HTTP 503 with a stable error code and opaque reference (§5 Errors and logging) |
| Principal lacks a scope in `ToolSpec.scopes`           | `isError=True`, "insufficient scope" (checked in `runtime.py`)                 |
| Per-principal rate limit exceeded                      | `isError=True`, "rate limit exceeded; retry after N s"                         |

## 5. Authentication (OAuth 2.1, PR 1)

### Canonical resource URL

One canonical, externally visible URL identifies the MCP resource:
`mcp_resource_url` (e.g. `https://<custom-domain>/mcp`). It is the OAuth
audience for every token, the `resource_server_url` passed to the SDK, and the
base for the protected-resource metadata. Requests that arrive on any other host
(such as the raw `*.run.app` URL) are rejected by the host check, so a `run.app`
URL and a custom domain can never produce mismatched audiences. The issuer
(`mcp_issuer_url`) is the same origin.

### Endpoints

| Path                                           | Served by                                                                  |
| ---------------------------------------------- | -------------------------------------------------------------------------- |
| `/.well-known/oauth-protected-resource/mcp`    | SDK, from the authenticated child app (§3 Wiring)                          |
| `/.well-known/oauth-authorization-server`      | SDK `create_auth_routes()`, on the parent app                              |
| `/register`, `/authorize`, `/token`, `/revoke` | SDK `create_auth_routes()` handlers backed by our `provider.py`, on parent |
| `/mcp/oauth/consent`                           | Ours (`auth/routes.py`): consent page (GET) and decision (POST)            |
| `/mcp/oauth/google/callback`                   | Ours (`auth/routes.py`): Google redirect target                            |

All of these are registered only when `mcp_enabled` is true, and all are behind
the parent-app host check (§3).

### Clients: public PKCE only

Open DCR accepts **public clients only**: `provider.register_client()` rejects
any registration whose `token_endpoint_auth_method` is not `"none"` with
`invalid_client_metadata`. No client secret is ever issued, so there is nothing
to store, hash, expire, or rotate, and the SDK's plaintext `hmac.compare_digest`
secret check never runs. PKCE (S256) is the only proof of possession, which is
what OAuth 2.1 expects for public clients.

The SDK fills in `client_secret_post` when a client omits the method, so a
client must send `token_endpoint_auth_method="none"` explicitly. PR 1 verifies
that each client in §1 (Claude Code, Claude Desktop, claude.ai, ChatGPT, MCP
Inspector) registers this way. If a hosted connector turns out to require a
confidential client, that is a spec change, not an implementation detail.

### Flow

1. Client calls `/mcp` without a token → `401` with `WWW-Authenticate` whose
   `resource_metadata` points to `/.well-known/oauth-protected-resource/mcp`.
2. Client registers via DCR with
   `ClientRegistrationOptions(enabled=True, valid_scopes=["data:read"], default_scopes=["data:read"])`.
   Our `provider.register_client()` enforces the public-client rule above and
   the redirect URI policy below, and rejects anything else.
3. Client starts `/authorize`. `provider.authorize()`:
   - validates `client_id`, the exact `redirect_uri`, PKCE S256, and
     `resource == mcp_resource_url`. **Errors before `client_id` and
     `redirect_uri` are validated are shown as an error page on our domain and
     never redirected**;
   - **resolves scopes:** the SDK's `validate_scope()` returns `None` when the
     client omits `scope`, so the provider replaces `None` with the client's
     registered scopes. That resolved list is what is stored, shown on the
     consent page, and bound to the code and tokens;
   - stores the authorization request server-side (single-use, 10 min TTL),
     **including the client's own `state` exactly as received** (it may be
     absent);
   - sets a short-lived (10 min), `HttpOnly`, `Secure`, `SameSite=Lax` browser
     **binding cookie** scoped to path `/mcp/oauth`, holding a random nonce, and
     stores only its hash on the request. It intentionally does not use the
     `__Host-` prefix, which requires `Path=/`. `Lax` is required so the cookie
     is sent on the top-level redirect back from Google;
   - redirects (GET) to the consent page.
4. **Consent page (ours).**
   - GET renders the client's registered name, the redirect URI **host**, and
     the resolved scopes, with Approve/Deny. **GET never approves anything.**
   - The form carries a per-request token derived from the binding nonce (HMAC
     of the nonce with `mcp_consent_signing_key`). The POST is accepted only if
     that token matches the binding cookie's hash for this request.
   - Approve and Deny are POST only. Deny ends the flow with `access_denied` to
     the validated redirect URI.
   - **Remembered approvals:** the page is skipped only if the browser presents
     a valid **consent cookie** **and** `mcp_oauth_consent` holds an unrevoked,
     unexpired approval for that `(api_user_id, client_id)` covering the
     resolved scopes. The consent cookie is `__Host-mcp_consent`, `Path=/`, no
     `Domain`, `HttpOnly`, `Secure`, `SameSite=Lax`. Its value names the
     `api_user_id` and `client_id`, carries an expiry, and is signed with
     `mcp_consent_signing_key` (with a key id so the key can be rotated; see
     below). Both the cookie and the DB row expire after 30 days. After Google
     login (step 6) the logged-in user must equal the cookie's `api_user_id`;
     otherwise the flow fails with an error page, no redirect.
5. On Approve we redirect to Google OIDC (authorization-code flow with our
   **MCP-specific Google client** and Google's own PKCE). We send:
   - `state`: a random value bound to the stored request and the binding-nonce
     hash, single-use;
   - `nonce`: a random value stored with the request, which must come back in
     the ID token.
6. `/mcp/oauth/google/callback`:
   - requires the binding cookie and checks that its hash matches the request
     referenced by Google's `state`; consumes that `state` and the stored
     request atomically (reuse or expiry → error page, no redirect);
   - exchanges the Google code server-side with the MCP client secret and
     verifies the ID token with **`audience = mcp_google_client_id` (never
     empty)**, issuer, expiry, `nonce` equal to the stored value, and
     `email_verified is True` (a missing claim is a rejection). This is a new
     helper; the portal's `verify_google_id_token` is not reused because it
     accepts a missing `email_verified` and an empty audience;
   - resolves the `ApiUser` (see Identity binding). No match, ambiguity, or
     `disabled` → `access_denied` to the validated redirect URI with a message
     to ask an admin for API access.
7. We store the approval in `mcp_oauth_consent` for `(api_user_id, client_id)`
   and set or refresh the consent cookie. We mint an authorization code bound to
   `client_id`, `redirect_uri`, `resource`, the PKCE challenge, the resolved
   scopes, and `api_user_id`, and redirect to the client.
8. `/token` exchanges the code (PKCE verified) for an access token and a
   rotating refresh token (see Token lifecycle).

**The client's `state` is returned unchanged on every redirect to the client:**
the success redirect in step 7 and every redirect-based error (`access_denied`
from Deny or from identity resolution, and any later error once the redirect URI
is validated). If the client sent no `state`, none is added. MCP clients,
including the SDK's own, reject a callback whose `state` is missing or
different, so PR 1 has end-to-end tests for success and for denial that check
`state` round-trips.

**Consent signing key.** `mcp_consent_signing_key` is its own secret (not the
JWT keys). Consent cookies carry a key id; the verifier accepts the current key
and, during a rotation window, the previous key. Rotation: add the new key as
current, keep the old one as previous for 30 days (the cookie lifetime), then
remove it. Rotating early simply forces users back through the consent page.

### DCR redirect URI policy

A registration is rejected unless **every** `redirect_uri`:

- is `https://` with a host, **or** `http://127.0.0.1[:port]/…`,
  `http://[::1][:port]/…`, or `http://localhost[:port]/…` (loopback, for desktop
  and CLI clients);
- has no fragment and no userinfo;
- if `mcp_redirect_host_allowlist` is set (non-empty), has an `https` host in
  that allowlist (e.g. the claude.ai and ChatGPT connector callback hosts).
  Loopback URIs remain allowed.

`/register` is per-IP rate limited. Clients that never complete a flow are
deleted 24 h after `created_at` by the cleanup job (see Storage), so the client
table cannot be flooded.

### Identity binding

`ApiUser` gains `google_sub` (nullable, unique) alongside the existing `email`.
Emails are **normalized on every write** (`strip()` then lowercase) in
`/v1/auth/register`, the new `PATCH` endpoint, and `scripts/create_admin.py`,
and the backfill normalizes existing rows; comparisons also use `lower(email)`.

After the ID token is verified, the callback resolves the user in one
transaction, in this order:

1. **Look up by `sub`.** If an `ApiUser` has `google_sub` equal to the ID
   token's `sub`, that is the user (then check `disabled`). Stop.
2. **Find all email matches.** Select **every** `ApiUser` whose `lower(email)`
   equals the normalized verified email, regardless of `google_sub`.
   - If **any** of them has a non-null `google_sub`, refuse. The email is
     already claimed by another Google account, and an unlinked duplicate row
     must not let a different account in.
   - If there are zero matches, refuse.
   - If there is more than one match, refuse (ambiguous; ask an admin).
3. **Link atomically.** With exactly one match whose `google_sub` is null:
   `UPDATE api_user SET google_sub = :sub WHERE id = :id AND google_sub IS NULL`.
   If zero rows are updated (a concurrent login won) or the unique constraint on
   `google_sub` fires, refuse; nothing is retried.

Every refusal ends the flow with `access_denied` to the validated redirect URI
and the client's `state`, with a message to ask an admin. The email in the ID
token never overrides an existing link, so a Google account whose email later
changes, or a new account reusing an old address, cannot take over an `ApiUser`.

The `hd` (Workspace domain) claim is **not** required, so researchers with
personal Google accounts can log in. Binding to `sub` is the protection.

Because `ApiUser.email` and `google_sub` now act as login identifiers, changing
either is a privileged operation:

- only admins (JWT-only `AdminUserDep`, which already excludes ApiKeys) can
  change them, through the new admin endpoints below;
- every change is written to an audit table;
- changing `email` clears `google_sub` (forcing a fresh link) and **revokes all
  of the user's MCP grants** (tokens, refresh families, remembered consents).

### Admin operations (new endpoints, PR 1)

`v1/auth/router.py` has no user-list or user-update endpoint today, so PR 1
adds, all behind `AdminUserDep` (JWT-only, so ApiKeys can never call them):

| Endpoint                                     | Purpose                                                                                                                                                                                      |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /v1/auth/users`                         | Paginated user list with filters `email_missing=true` and `email_duplicate=true` (case-insensitive). Returns no password hashes, key hashes, or `google_sub` values (only whether it is set) |
| `PATCH /v1/auth/users/{user_id}`             | Update `email`, `full_name`, `disabled`, or clear `google_sub`. Audit-logged                                                                                                                 |
| `GET /v1/auth/users/{user_id}/mcp-grants`    | List the user's active MCP clients, consents, and token families (no secrets)                                                                                                                |
| `DELETE /v1/auth/users/{user_id}/mcp-grants` | Revoke all MCP grants for the user. Audit-logged                                                                                                                                             |

Setting `disabled=true` also revokes all MCP grants, so re-enabling a user does
not silently restore old tokens.

The bootstrap admin created by `scripts/create_admin.py` from the Cloud Run job
currently runs without `--email`. PR 0.5 (§6) passes the admin's email to that
job so the bootstrap admin can complete the Google flow.

### Storage

All new tables live in a **dedicated `mcp_auth` schema**, created by one PR 1
Alembic migration:

| Table                          | Notes                                                                                                                                 |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| `mcp_oauth_client`             | DCR public clients; `created_at` and `last_completed_at` for the 24 h expiry of clients that never complete a flow                    |
| `mcp_oauth_pending_request`    | Stored `/authorize` requests: client `state`, resolved scopes, binding-nonce hash, Google `state` and `nonce`; single-use, 10 min TTL |
| `mcp_oauth_consent`            | Remembered `(api_user_id, client_id, scopes)` approvals, with `expires_at` (30 days) and `revoked_at`                                 |
| `mcp_oauth_authorization_code` | Codes, bound as in Flow step 7, with `consumed_at` and a tombstone (see Token lifecycle)                                              |
| `mcp_oauth_token`              | Access and refresh tokens with `family_id`, `kind`, `generation`, expiry, `rotated_at`, `revoked_at`                                  |
| `mcp_rate_window`              | Per-`api_user_id` fixed-window counters (see Rate limiting)                                                                           |
| `api_user_audit`               | `actor_id`, `target_id`, `field`, `old_value`, `new_value`, `at` for identity and grant changes                                       |

The same migration adds `api_user.google_sub` (nullable, unique) in the existing
schema.

> **Coordination note (#580):** `api_user` and `api_key` now live in a dedicated
> `auth` schema (migration `0029`) that already has the isolation described
> below: no `USAGE` or default privileges for `biocirv_readonly`, and
> `scripts/check_readonly_auth_grants.py` checks every table registered under
> `ca_biositing.datamodels.models.auth`. Before PR 1, decide whether the MCP
> tables go into `auth` (a model under `models/auth/` is then checked
> automatically) or stay in a separate `mcp_auth` schema (which then needs its
> own grants, a `private_schemas` entry in `resources/config/db_reset.yaml`, and
> an entry in `MANAGED_SCHEMAS` in `alembic/env.py`). Foreign keys use
> `auth.api_user.id`.

**No inherited grants.** Migration `0002_permissions` sets
`ALTER DEFAULT PRIVILEGES` on `public`, `ca_biositing`, and `data_portal`, so a
new table in those schemas would automatically be readable by
`biocirv_readonly`. The `mcp_auth` schema has no default privileges for any
role. The migration grants `USAGE` on the schema and table privileges only to
the webservice's own role, and explicitly revokes `ALL` from `PUBLIC`. A
migration test asserts that `has_table_privilege(role, table, 'SELECT')` is
false for every role other than the webservice's own, including
`biocirv_readonly`, `biocirv_mcp_ro`, and the test-cleanup role, for every table
in `mcp_auth`.

All codes and tokens are high-entropy random values stored as **SHA-256 hashes**
(not Argon2, which would add per-request CPU cost for no benefit at this
entropy). There are no client secrets to store (public clients only). Codes and
tokens carry a foreign key to `api_user.id`.

**Cleanup job (PR 1).** A scheduled job, shipped in PR 1 rather than left as a
column, deletes:

- `mcp_oauth_client` rows with `last_completed_at IS NULL` and `created_at`
  older than 24 h;
- expired `mcp_oauth_pending_request` rows;
- code and refresh-token tombstones past their retention (see Token lifecycle);
- expired `mcp_oauth_consent` rows.

**Email uniqueness and backfill.** `api_user.email` is optional and not unique
today. PR 1 does not add a unique email index, because the deploy would run the
migration before admins can use the new endpoints to fix existing rows. Instead:

- the identity-binding rules above refuse ambiguous emails, so nothing is linked
  by guesswork;
- after PR 1 deploys, an admin uses `GET /v1/auth/users?email_missing=true` and
  `?email_duplicate=true` to find rows and fixes them with
  `PATCH /v1/auth/users/{user_id}`, with no direct database edits;
- PR 6 adds the case-insensitive unique index on `lower(email)` (where not
  null); that migration fails fast with a clear message if duplicates remain.

Users with a null `email` keep ApiKey/JWT access on `/mcp`; they only cannot
complete the Google OAuth flow until an email is set.

### Token lifecycle

| Item               | Rule                                                                                                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Token format       | Typed prefixes: access `bcv_mcp_at_…`, refresh `bcv_mcp_rt_…` (lets the verifier route by prefix, and makes leaked tokens matchable by a custom secret-scanning pattern) |
| Authorization code | Single-use, 60 s TTL, bound to `client_id`, `redirect_uri`, `resource`, PKCE challenge, resolved scopes. Reuse revokes the whole family issued from it                   |
| Access token       | 1 h, `resource = mcp_resource_url`, the resolved scopes                                                                                                                  |
| Refresh token      | Rotated on every use; 30-day absolute lifetime per family; reuse of a rotated refresh token revokes the whole family                                                     |
| Revocation         | SDK `/revoke` revokes the **whole family** of the presented token; admin grant revocation; automatic on `disabled=true` and on `email` change                            |

**Atomic single-use and rotation.** The SDK's `/token` handler calls
`load_authorization_code()`, then checks expiry and PKCE itself, and only then
calls `exchange_authorization_code()`; refresh tokens follow the same load →
check → exchange pattern. A plain read-then-update would let two concurrent
requests both succeed, so:

- **`load_*` never consumes anything.** It runs before PKCE is checked, so
  consuming there would let anyone holding only the code burn it. It returns the
  row for the SDK's checks, **and** it performs reuse detection: if the
  presented code or refresh token is already consumed or rotated (a tombstone
  exists), it revokes the family in its own transaction and returns `None`. This
  has to happen in `load_*` because the SDK rejects an expired code before our
  exchange hook would ever run.
- **`exchange_*` consumes and issues in one transaction.** It runs
  `UPDATE … SET consumed_at = now() WHERE id = :id AND consumed_at IS NULL` (for
  refresh tokens, `rotated_at` on the current generation), and only if exactly
  one row changed does it insert the new access and refresh tokens in the same
  transaction. Zero rows changed means a concurrent request won: the family is
  revoked and the request fails with `invalid_grant`.
- **Tombstones.** Consumed codes and rotated refresh tokens are kept, by hash,
  until the end of their family's absolute lifetime (30 days), so a replay
  arriving later is still recognized and revokes the family.
- **Refresh re-checks.** `exchange_refresh_token()` also re-checks, inside the
  same transaction, that the `ApiUser` is active, the client still exists, the
  consent is unrevoked and unexpired, and the family is within its 30-day
  lifetime; any failure revokes the family.
- **Tests.** PR 1 includes tests that fire real concurrent `/token` requests
  against Postgres (same code twice, same refresh token twice) and assert that
  exactly one succeeds and the family is revoked.

### Scopes

| Scope       | Granted to                                                                                                                                                                                            |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `data:read` | Every principal: MCP OAuth, API JWT, ApiKey                                                                                                                                                           |
| `kb:query`  | Reserved — not in DCR `valid_scopes`, not grantable until the KB issue lands                                                                                                                          |
| `admin`     | Reserved — not in DCR `valid_scopes`. **Never** granted to ApiKey or API JWT principals, even when the user `is_admin`, which keeps the existing rule that an ApiKey can never reach admin operations |

The SDK only enforces `AuthSettings.required_scopes` for the whole endpoint, so
per-tool scopes are enforced in `runtime.py` (§4).

### API JWT changes

Today `create_portal_token` signs portal session tokens with the same
`jwt_secret_key` as API JWTs and sets `sub=email`, and `decode_access_token`
accepts any JWT signed with that key. A portal token could therefore pass as an
API JWT for an `ApiUser` whose `username` equals the email. PR 1 fixes this for
REST and MCP together:

- API JWTs from `/v1/auth/token` and `/v1/auth/refresh` gain `token_use="api"`;
  `decode_access_token` rejects any token without it. Existing API JWTs (no
  claim) stop working at deploy and users log in again; their lifetime is
  `jwt_expire_minutes`, so the impact is short.
- Portal tokens move to a separate signing key, `portal_jwt_secret_key`, and
  keep `token_use="biocirv_portal"`. Active portal sessions end at deploy.
- The MCP verifier accepts a JWT only if `token_use == "api"`.

These changes are not behind `mcp_enabled`; `portal_jwt_secret_key` is
provisioned in PR 0.5 so PR 1 can deploy.

### Verifier

`verifier.py` implements the SDK `TokenVerifier`. The SDK calls it on every
JSON-RPC message (we run `stateless_http=True`), so it routes on the token's
shape instead of trying each path in turn, and runs all synchronous work
(database, Argon2) through `anyio.to_thread.run_sync`:

| Bearer value shape                  | Path                                                                                                                                             |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| starts with `bcv_mcp_at_`           | SHA-256 lookup in `mcp_oauth_token`; not expired, not revoked, `resource == mcp_resource_url`                                                    |
| three dot-separated base64url parts | API JWT: `decode_access_token()`; require `token_use == "api"`; resolve `sub` to an `ApiUser`                                                    |
| anything else, 8–128 chars          | ApiKey: `validate_api_key()`. Results are cached by SHA-256 of the raw key for 60 s, so Argon2 runs at most once per key per minute per instance |
| otherwise                           | `None`                                                                                                                                           |

After any path, the verifier loads the `ApiKey` (if any) and `ApiUser` **by id**
on every request — a cheap indexed query that is never cached — and rejects
inactive keys and `disabled` users. Disabling a user or key therefore takes
effect immediately even for cached ApiKeys and unexpired tokens.

**Verifier contract.** `BearerAuthBackend` reads `client_id`, `scopes`,
`expires_at`, and `resource` from whatever the verifier returns, and
`get_access_token()` hands the same object to `runtime.py`. So the verifier
returns a fully populated `McpAccessToken`, a subclass of the SDK's
`AccessToken`:

| Field        | MCP OAuth                   | API JWT                    | ApiKey                     |
| ------------ | --------------------------- | -------------------------- | -------------------------- |
| `token`      | the presented bearer value  | the presented bearer value | the presented bearer value |
| `client_id`  | the real DCR `client_id`    | `jwt:<api_user_id>`        | `apikey:<api_key_id>`      |
| `subject`    | `str(api_user_id)`          | `str(api_user_id)`         | `str(api_user_id)`         |
| `scopes`     | the token's resolved scopes | `["data:read"]`            | `["data:read"]`            |
| `resource`   | the token's stored resource | `mcp_resource_url`         | `mcp_resource_url`         |
| `expires_at` | the token's expiry          | the JWT's `exp`            | `None` (keys don't expire) |
| `kind`       | `"oauth"`                   | `"jwt"`                    | `"apikey"`                 |

`kind` is a field on the subclass; `claims` is not used for it. `runtime.py`
builds `Principal(api_user_id=int(subject), kind, scopes, client_id)` from this
object and never re-reads the bearer value. Tools and logs use
`principal.api_user_id`; emails are never logged.

**Audience for JWT and ApiKey principals.** With `validate_token_resource=True`
the SDK's `BearerAuthBackend` rejects any `AccessToken` whose `resource` is not
`mcp_resource_url`, including those from the JWT and ApiKey paths. The verifier
therefore sets `resource = mcp_resource_url` on those principals. In practice
this means their audience is **asserted by us** (they are our own credentials,
accepted only by this service), not checked from a token claim.

**Failure modes.** `BearerAuthBackend` does not catch exceptions from the
verifier. So the verifier:

- returns `None` for any bad, unknown, expired, or revoked credential (→ 401);
- catches infrastructure errors (database unavailable, timeouts) and raises a
  dedicated `McpAuthUnavailable`, which the parent app turns into an HTTP 503
  with `{"error": "temporarily_unavailable", "ref": "<uuid>"}` and no exception
  text. The full error is logged server-side with the same `ref`.

### Errors and logging

- **No internal details in responses.** `main.py`'s global exception handler
  returns `str(exc)` to the client today. PR 1 changes it to return
  `{"detail": "Internal server error", "ref": "<uuid>"}` and log the exception
  with that `ref`. This applies to REST routes as well.
- **Stable OAuth errors.** Our own routes (consent, callback) and provider hooks
  return standard OAuth error codes (`invalid_request`, `access_denied`,
  `invalid_grant`, `temporarily_unavailable`, …) with an opaque `ref`, never an
  exception message.
- **Request-log redaction.** The callback URL carries Google's `code` and our
  Google `state`, and `/authorize` and `/token` carry codes, verifiers, and
  tokens. A logging filter on Uvicorn's access logger replaces the query strings
  of `/mcp/oauth/*`, `/authorize`, and `/token` with `?<redacted>`. `/token` is
  a POST with form-encoded secrets, so its body is never logged.
- **Cloud Run's platform request log is not redactable by the app** and records
  the full callback URL, including Google's `code` and our Google `state`. We do
  not switch Google to `response_mode=form_post` to avoid this, because a
  cross-site POST would not carry the `SameSite=Lax` binding cookie that step 6
  depends on. The residual exposure is accepted and documented: Google's `code`
  is single-use, short-lived, and cannot be exchanged without our MCP client
  secret and our Google PKCE verifier, and our Google `state` is consumed on
  first use. `/authorize` query strings carry only the client's public PKCE
  challenge and `state`. Read access to the Cloud Run request logs stays limited
  to project maintainers.
- **Headers.** Consent and callback responses send `Cache-Control: no-store`,
  `Referrer-Policy: no-referrer`,
  `Content-Security-Policy: frame-ancestors 'none'`, and
  `X-Frame-Options: DENY`.
- Emails, tokens, codes, ApiKeys, and tool arguments are never logged.

### Rate limiting

| Layer                         | Where                                                 | Limit                                                                                                                                                                 |
| ----------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Per-IP, before authentication | `/mcp`, `/register`, `/authorize`, `/token`, callback | In-memory per instance; bounds unauthenticated CPU cost such as dummy Argon2 verifies                                                                                 |
| Per-principal, after auth     | `runtime.py`, `tools/call` only                       | Postgres fixed window keyed by `api_user_id` (`mcp_rate_window`), same technique as `ApiKey`. `initialize` and `tools/list` do not consume quota and take no row lock |

The ApiKey path no longer calls `check_and_increment_rate_limit` from the
verifier; ApiKey principals are counted by the per-principal limiter like
everyone else, so `initialize`/`tools/list` traffic does not use up the key's
quota. REST `X-API-Key` behaviour is unchanged.

### Hardening checklist

Each item has a unit test (§7).

- `MCPServer` built with only our `token_verifier`; SDK auth routes mounted on
  the parent app; exact-path dispatch; both child lifespans run.
- `mcp_enabled` off → no MCP or OAuth routes exist and MCP boot checks are
  skipped; REST security changes and their boot checks apply regardless.
- Host checked on every MCP and OAuth route; explicit
  `TransportSecuritySettings` with host and origin allowlists; never disabled.
- `dev_mode` refused unless `deployment_env=local` and the bind host is
  loopback.
- Public PKCE clients only; no client secrets issued.
- PKCE S256 mandatory; `plain` rejected.
- Exact-match redirect URIs; DCR redirect URI policy enforced.
- Omitted `scope` at `/authorize` resolved to the client's registered scopes.
- Consent page served by us before Google; approval only by POST with a
  per-request token tied to the binding cookie; `frame-ancestors 'none'`,
  `X-Frame-Options: DENY`, `Cache-Control: no-store`, and
  `Referrer-Policy: no-referrer` on consent and callback.
- Remembered consent: `__Host-` cookie (`Path=/`, no `Domain`), signed with its
  own rotatable key, 30-day expiry, matched to an unexpired DB row.
- Google `state` bound to the browser binding cookie; `state` and stored
  requests single-use with TTL; Google `nonce` verified.
- Client's own `state` returned unchanged on success and on every redirect-based
  error.
- No redirect to `redirect_uri` for errors before client and redirect URI are
  validated.
- Separate MCP Google client; ID token audience always set;
  `email_verified is True`.
- Identity: lookup by `sub`; refuse if any email match is already linked or the
  match is ambiguous; atomic conditional link; emails normalized on write.
- Identity changes admin-only, audit-logged, and revoke grants.
- Auth tables in `mcp_auth` schema with no inherited grants; migration test
  proves no other role can read them.
- Code consumption and refresh rotation are atomic conditional updates in the
  same transaction as token issue; replay detected in `load_*` via tombstones
  and revokes the family; `/revoke` revokes the family.
- Verifier returns a fully populated `McpAccessToken`; `None` for bad
  credentials, 503 with opaque `ref` for infrastructure errors.
- No `str(exc)` in any response; app request logs redact OAuth query strings.
- `validate_token_resource=True`; JWT/ApiKey principals stamped with
  `mcp_resource_url`.
- API JWTs require `token_use="api"`; portal tokens use a separate key.
- ApiKey and API JWT principals get `data:read` only; DCR `valid_scopes` is
  `["data:read"]`.
- Per-tool scopes checked in `runtime.py`.
- `ApiUser.disabled` and `ApiKey.is_active` checked on every request.
- Google login without a matching active `ApiUser` is denied, never
  auto-provisioned.
- No tokens, codes, ApiKeys, or emails logged.

## 6. Delivery plan (PR sequence)

| PR  | Scope                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Depends on       |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------- |
| 0   | `datamodels/config.py` Docker/local DB host auto-detect (standalone)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | —                |
| 0.5 | **Infrastructure first.** Pulumi and Secret Manager: `portal_jwt_secret_key`, `mcp_consent_signing_key`, MCP Google OAuth client ID and secret, `biocirv_mcp_ro` role and password, test-cleanup role. Cloud Run start command exports them plus `DEPLOYMENT_ENV`, `MCP_RESOURCE_URL`, `MCP_ISSUER_URL`, `MCP_ALLOWED_HOSTS`, `SERVER_BIND_HOST`, `MCP_DB_URL`, with `MCP_ENABLED=false`. `create_admin` job passes `--email`. Custom domain mapping. No application code reads the new settings yet                                                                                                                                                               | 0                |
| 1   | `mcp>=2.3,<3`; `mcp_enabled` flag; exact-path dispatcher and lifespans; registry, runtime (scope check, per-principal limit, read-only engine), error mapping; `/mcp` with OAuth 2.1 (public clients, consent page, cookie-bound `state`, client `state` passthrough, DCR redirect policy, `sub` binding, atomic token lifecycle) + API JWT + ApiKey verifier; host/origin checks; `token_use` claim and split portal signing key; global error handler without `str(exc)`; admin user-list, user-update, and MCP-grant endpoints with audit log; `mcp_auth` schema and migration; cleanup job; `list_geoids` smoke tool; boot guard, `deployment_env`, `dev_mode` | 0.5              |
| 2   | Feedstock availability + analysis tools (worked example referenced by docs)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 1                |
| 3   | USDA census + survey tools                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | 1                |
| 4   | `/mcp/public` mount + per-IP limit + `tools/public.py` over `PublicDatasetService`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | 1, #545          |
| 5   | Docs: "Adding MCP tools" guide, AGENTS.md pointer, `tools/_template.py`, client connection how-to                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | 1 (parallel OK)  |
| 6   | Case-insensitive unique index on `lower(api_user.email)` after the admin backfill; turn `MCP_ENABLED=true` in staging, then production                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 1, backfill done |
| 7   | **Cleanup.** Once MCP is live in production and stable, remove the `mcp_enabled` flag and its branches: MCP routes and MCP boot checks become unconditional                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 6                |

Each PR targets the 200–400 line sizing guideline. PR 1 is kept as one PR by
decision: the OAuth flow, its hardening, and the identity and admin changes it
relies on are one security boundary and are reviewed together. PR 1 is expected
to be well over the size target, and its description must explain this and point
reviewers to the §5 hardening checklist as the review map.

### Deploy order

For each environment (staging first, then production):

1. **Secrets and roles** (PR 0.5): apply Pulumi, confirm every new secret exists
   and the Cloud Run revision starts with `MCP_ENABLED=false`.
2. **Migration** (PR 1): run Alembic, which creates `mcp_auth` and adds
   `google_sub`. The migration test for grants runs in CI before this.
3. **Service** (PR 1): deploy the new revision. With `MCP_ENABLED=false`, only
   the REST-side changes are live, and the always-on boot checks already have
   their settings from step 1.
4. **Backfill**: admins fix null and duplicate emails through the new endpoints.
5. **Enable** (PR 6): add the unique email index, then set `MCP_ENABLED=true`.
   The MCP boot checks now run, and the revision refuses to start if anything
   from step 1 is missing, before it takes traffic.

Because PR 1's REST-side changes (`token_use`, the split portal key) are not
behind the flag, step 3 logs out every API JWT holder and every portal session.
Announce the deploy window to users.

## 7. Testing strategy

### Unit (no DB)

- Registry: `build_server({"public"})` contains no non-public tools.
- Guard: every registered `ToolSpec` has a tier, an output model, and a
  description of at least 40 characters; names are unique.
- Error mapping: each row of the §4 table.
- Runtime: a tool whose `ToolSpec.scopes` the principal lacks returns
  "insufficient scope" without running the handler; `initialize`/`tools/list` do
  not consume the per-principal quota.
- Verifier:
  - each token shape routes to exactly one path;
  - MCP OAuth, API JWT, and ApiKey paths each resolve to the right `ApiUser`;
  - expired, revoked, and wrong-resource OAuth tokens rejected;
  - a portal token (`token_use="biocirv_portal"`) and a legacy API JWT with no
    `token_use` are both rejected;
  - a `disabled` user and an inactive ApiKey are rejected even when the ApiKey
    is in the verification cache or the token is unexpired;
  - JWT and ApiKey principals get `resource = mcp_resource_url` and `data:read`
    only, including for `is_admin` users;
  - each kind returns a fully populated `McpAccessToken` (table in §5 Verifier
    contract), and `runtime.py` builds the right `Principal` from it;
  - a database error inside the verifier yields HTTP 503 with an opaque `ref`
    and no exception text, not a 500 traceback.
- Provider and routes (Google mocked), one test per §5 hardening item:
  - DCR: non-`https`, non-loopback, fragment, userinfo, and (when the allowlist
    is set) non-allowlisted redirect URIs rejected; `admin` and `kb:query` scope
    requests rejected; any `token_endpoint_auth_method` other than `none`
    (including an omitted one) rejected, and no `client_secret` is ever
    returned;
  - `/authorize`: unknown client or unregistered redirect URI → error page, no
    redirect; `plain` PKCE rejected; wrong `resource` rejected; omitted `scope`
    resolves to the client's registered scopes, which then appear on the consent
    page, the code, and the token;
  - consent page sends `frame-ancestors 'none'`, `X-Frame-Options: DENY`,
    `Cache-Control: no-store`, and `Referrer-Policy: no-referrer`; GET never
    approves; POST without the binding cookie, or with a form token that does
    not match it, is rejected;
  - consent cookie has the `__Host-` prefix, `Path=/`, and no `Domain`; a cookie
    signed with an unknown key id, or past its expiry, is ignored; a cookie
    signed with the previous key is accepted during rotation;
  - callback: missing or mismatched binding cookie, reused `state`, expired
    request → error page, no redirect;
  - ID token: wrong audience, `email_verified` false, `email_verified` missing,
    missing or wrong `nonce` → rejected;
  - identity: first login links `google_sub`; later login with the same `sub`
    but a different email still maps to the same user; a different `sub` with
    the linked email is refused; **user A linked plus an unlinked duplicate row
    B with the same email → a different `sub` is refused, not linked to B**;
    email matching more than one unlinked `ApiUser` is refused; no match or
    `disabled` → `access_denied`; emails with different case or surrounding
    whitespace are normalized on write;
  - client `state`: round-trips unchanged on success, on Deny, and on an
    identity refusal; when the client sent none, none is added;
  - remembered consent: skipped only with cookie + DB row for the same user;
    mismatch after login → error page;
  - tokens: code reuse revokes the family; refresh-token reuse revokes the
    family, including a replay that arrives after the code or token has expired;
    `load_*` never consumes; refresh fails and revokes the family when the user
    is disabled, the client deleted, or the consent revoked or expired; refresh
    family expires at 30 days; `/revoke` revokes the family.
- Admin endpoints: non-admin and ApiKey callers rejected; email change clears
  `google_sub`, revokes grants, and writes an audit row; `disabled=true` revokes
  grants; `GET /v1/auth/users` filters for missing and duplicate emails and
  returns no hashes.
- Boot guard: with `deployment_env` unset or `staging`/`production`, each
  always-on condition in §3 raises; MCP conditions raise only when `mcp_enabled`
  is true; `dev_mode` with `deployment_env=local` and a loopback bind host
  boots; `dev_mode` with `server_bind_host=0.0.0.0` raises in every environment.
- Feature flag: with `mcp_enabled=false`, `/mcp`, `/mcp/public`,
  `/.well-known/oauth-*`, `/register`, `/authorize`, `/token`, `/revoke`,
  consent, and callback all return 404, and the app boots without any MCP
  settings.
- Host and origin: a request with a non-allowlisted `Host` is rejected on `/mcp`
  and on every OAuth route; a request with an allowlisted `Host` but a
  non-allowlisted `Origin` is rejected on `/mcp`.
- Errors: the global exception handler returns no exception text; access-log
  lines for `/mcp/oauth/*`, `/authorize`, and `/token` contain no query string.
- Client IP: spoofed left-most `X-Forwarded-For` entries are ignored.

### Integration (shared dev DB)

- **Startup through the real app.** Start the full FastAPI app (with its
  lifespan) and drive it with the SDK streamable-HTTP client, so the dispatcher,
  both mounts, and both session-manager lifespans are exercised: unauthenticated
  `/mcp` → 401 with `resource_metadata` pointing to
  `/.well-known/oauth-protected-resource/mcp`; ApiKey → tool call succeeds; API
  JWT from `/v1/auth/token` → tool call succeeds; `/mcp/public` lists only
  public tools, **and still lists only public tools when a valid ApiKey or OAuth
  token is sent to it**; `/mcp/mcp` and `/mcp/public/mcp` return 404.
- **End-to-end OAuth (Google mocked at the HTTP boundary).** Run the SDK's own
  OAuth client (`mcp/client/auth/oauth2.py`) against the app through DCR,
  `/authorize`, consent, callback, and `/token`, for both an approval and a
  denial, asserting that the SDK client accepts the callback (its `state` check
  passes) and that the resulting token can call a tool.
- **Concurrency.** Fire two concurrent `/token` requests with the same
  authorization code, and separately with the same refresh token, against
  Postgres; exactly one succeeds and the family is revoked. Fire two concurrent
  first-link callbacks for the same unlinked user with different `sub` values;
  exactly one links.
- **Grants.** For every table in `mcp_auth`,
  `has_table_privilege(role, table, 'SELECT')` is false for every role other
  than the webservice's own.
- A tool session attempting `INSERT`/`UPDATE` fails (read-only role), and a long
  query is cancelled by the role's `statement_timeout`.
- **Namespacing:** every row a test creates (OAuth clients/tokens, ApiUsers)
  carries a per-run `test_run_id` prefix. Session-scoped teardown deletes rows
  for the current run only.
- **Test credentials are never long-lived:** every test `ApiUser`, ApiKey, and
  OAuth client uses random secrets generated per run (nothing fixed in the
  repo). Teardown first sets the test users `disabled` and keys inactive, then
  deletes them; even if deletion fails, the credentials are dead.
- **Cleanup job:** a scheduled job deletes `test_run_id`-prefixed rows older
  than 24 h (orphans from crashed runs). It never touches unprefixed rows. It
  runs as a dedicated database role whose grants are limited to `DELETE` (and
  the `SELECT` it needs) on `api_user`, `api_key`, and the `mcp_auth` tables.
  This is separate from the production OAuth cleanup job in §5 Storage.
- **CI exposure:** jobs that hold dev DB credentials run only on `push` and on
  `pull_request` from branches in this repository, never on fork PRs, and never
  via `pull_request_target`.
- **Reference data:** tool-output assertions are taken from fixed reference rows
  in the dev DB, with expected values human-reviewed. Tests never mutate
  non-test rows or the config singleton (use dependency overrides instead).
- **Concurrency risk:** parallel CI runs share the DB; namespacing prevents row
  collisions, but reference-data changes (e.g. ETL reloads) can cause flakes.
  Integration tests that depend on reference values carry a marker so they can
  be quarantined without blocking unit tests.

### Manual

MCP Inspector against staging (`/mcp` OAuth flow and `/mcp/public`), documented
in each PR's "How to test" section. PR 1 also includes a manual run of the
confused-deputy scenario: register a client with an attacker-controlled redirect
host and confirm that the user sees our consent page, naming that host, before
any code is issued.

## 8. Documentation for adding new APIs

Must be discoverable and easy to follow for both humans and agents:

| Artifact                                           | Audience       | Content                                                                                                                                    |
| -------------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `docs/webservice/mcp/adding-tools.md` (MkDocs nav) | Humans, agents | Step-by-step checklist: pick tier/scopes, write handler over service, reuse schema, register, test, document                               |
| `src/ca_biositing/webservice/AGENTS.md` pointer    | Agents         | "Adding or changing an API? Also update MCP tools" with a link to the guide                                                                |
| `mcp/tools/_template.py`                           | Both           | Annotated copy-me module                                                                                                                   |
| Registry guard test                                | Both           | Fails CI with a message linking the guide when the checklist is not followed                                                               |
| `docs/webservice/mcp/connecting-clients.md`        | Humans         | Connecting Claude Code, Claude Desktop, claude.ai, MCP Inspector; that tool output is untrusted data and can contain prompt-injection text |

Checklist (canonical text lives in the guide):

1. A service method exists in `services/` (no SQL in tool modules).
2. Choose the tier explicitly (`public` only if the data is already exposed on
   `/v1/public`) and the scopes.
3. Reuse or define a Pydantic output model, with `truncated` for lists.
4. Write an agent-oriented description naming the discovery tool.
5. Add the module's `register()` call in `registry.py`.
6. Add tests: registered on the correct mount(s), output shape, one error case.
7. Update the tool table in the guide.

## 9. Follow-up issue: knowledge-base proxy (draft)

> **Title:** Add biocirv-kb proxy tools to MCP server
>
> Add `tools/kb.py` (tier `kb`, scope `kb:query`) exposing search, question
> answering, and entity-relationship lookups from `biocirv-kb`. Use the `mcp`
> SDK streamable-HTTP client (handles SSE/JSON framing) with a lifespan-managed
> session, 30 s timeout, and one retry on connect errors. Enforce a
> per-principal quota (calls proxy to a paid third-party API). Never expose on
> `/mcp/public`. Add a `kb_live` contract test against the staging KB, run
> nightly. Extend the boot guard to require the KB URL/key in deployed
> environments. Depends on MCP PR 1 (#494).
>
> **No token passthrough.** The proxy calls `biocirv-kb` with its own service
> credential and never forwards the MCP client's bearer token (the MCP spec
> forbids token passthrough). Add a test that the outbound request carries the
> service credential and none of the inbound `Authorization` header.
>
> **Prompt-injection surface.** Text returned from the KB goes straight into an
> LLM's context. Return it as clearly delimited data (structured fields, not
> free text merged into instructions), document the risk in the tool description
> and the client guide, and never let KB output trigger further tool calls
> server-side.

## 10. Risks

| Risk                                                                     | Mitigation                                                                                                                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mcp` 2.x API churn within the major version                             | Bounded pin `<3`; SDK usage isolated to `registry.py`, `runtime.py`, and `auth/`                                                                                                                                                                                                                                             |
| Google OIDC proxy complexity (callback state, PKCE)                      | Dedicated PR 1 review; a unit test per hardening item                                                                                                                                                                                                                                                                        |
| Confused-deputy attack through open DCR and a shared upstream client     | Our own consent page naming the redirect host, cookie-bound `state`, DCR redirect URI policy (§5); manual attack walkthrough in PR 1                                                                                                                                                                                         |
| PR 1 is large and security-critical                                      | Kept as one boundary by decision; §5 hardening checklist is the review map; one test per item                                                                                                                                                                                                                                |
| First PR 1 deploy stops the whole webservice from starting               | Infrastructure ships first in PR 0.5; MCP boot checks only run with `mcp_enabled`; documented deploy order (§6)                                                                                                                                                                                                              |
| PR 1 logs out all API JWT and portal sessions                            | Announce the deploy window; JWT lifetime is short (`jwt_expire_minutes`)                                                                                                                                                                                                                                                     |
| Read-only DB role adds provisioning work                                 | Provisioned in PR 0.5 with the existing `READONLY_USERS` Pulumi pattern; local dev script creates the role                                                                                                                                                                                                                   |
| Ingested data or KB text carries prompt-injection payloads to the agent  | Not prevented by read-only DB access or structured output: a string in a JSON field still reaches the model. All retrieved content is treated as untrusted data, and it never drives server-side tool chaining (no tool calls another tool based on returned content). User-facing guidance lives in `connecting-clients.md` |
| Shared dev DB flakiness / cross-run interference                         | Per-run namespacing, cleanup job, quarantine marker for reference-data tests                                                                                                                                                                                                                                                 |
| `ApiUser` emails missing, duplicated, or not the person's Google account | Ambiguous or already-linked emails refuse first link; admin backfill via `GET`/`PATCH /v1/auth/users`; PR 6 unique index fails fast on duplicates; binding moves to Google `sub` after first link                                                                                                                            |
| #545 schemas change before merge                                         | PR 4 starts only after #545 merges                                                                                                                                                                                                                                                                                           |
| A target client cannot register as a public PKCE client                  | Verified per client in PR 1 (§5 Clients); if one needs a confidential client, the spec changes before PR 1 merges                                                                                                                                                                                                            |
| `mcp_enabled` flag outlives its purpose                                  | PR 7 removes it once MCP is live and stable in production                                                                                                                                                                                                                                                                    |
| Hosted connector differences (claude.ai vs. ChatGPT)                     | Manual verification with each connector before closing PR 1; document quirks in the guide                                                                                                                                                                                                                                    |
