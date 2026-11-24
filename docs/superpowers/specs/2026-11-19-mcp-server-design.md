# MCP Server Design (follow-up to PR #484)

- **Issue:** sustainability-software-lab/ca-biositing#494
- **Status:** Revised after security review on #565 (2026-11-24); pending
  re-review
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
    ratelimit.py   per-IP (pre-auth) and per-principal (post-auth) limiters
```

### Mounts

| Path          | Tiers served                             | Auth                                   |
| ------------- | ---------------------------------------- | -------------------------------------- |
| `/mcp`        | `public`, `authenticated` (+ `kb` later) | OAuth 2.1, API JWT, or `ApiKey` bearer |
| `/mcp/public` | `public` only                            | None; per-IP rate limit (§3 Client IP) |

Both servers are built from the same `Registry` by filtering on tier. A tool
outside the requested tier set is never registered on that server — exclusion is
structural, not a call-time check. `/mcp/public` must be mounted before `/mcp`
so the prefix route does not capture it. Both use `stateless_http=True` (Cloud
Run has multiple instances and no session affinity). The OAuth endpoints are
listed in §5 Endpoints; note that protected-resource metadata for `/mcp` lives
at `/.well-known/oauth-protected-resource/mcp` (RFC 9728 path insertion), not at
the root path.

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

| Setting                                                                       | Purpose                                                                                                         |
| ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `deployment_env` (`local` \| `staging` \| `production`, default `production`) | Explicit environment. Anything other than `local` is "deployed" and fails closed                                |
| `dev_mode` (default `False`)                                                  | Disables MCP auth. Allowed only when `deployment_env=local`; the server must then bind to loopback              |
| `mcp_resource_url`                                                            | Canonical `/mcp` URL: OAuth audience and resource server URL (§5)                                               |
| `mcp_issuer_url`                                                              | OAuth issuer (same origin as `mcp_resource_url`)                                                                |
| `mcp_google_client_id` / `mcp_google_client_secret`                           | **Separate** Google OAuth client for MCP (not the portal's); secret from Secret Manager                         |
| `portal_jwt_secret_key`                                                       | Signing key for portal session tokens, split from `jwt_secret_key` (§5 API JWT changes)                         |
| `mcp_redirect_host_allowlist`                                                 | Optional allowlist of `https` redirect hosts for DCR (§5)                                                       |
| `mcp_public_rate_limit`                                                       | Per-IP limit for `/mcp/public`                                                                                  |
| `mcp_trusted_proxy_hops`                                                      | Number of trusted proxies in front of the app, used to pick the client IP from `X-Forwarded-For` (§3 Client IP) |
| `mcp_allowed_hosts`                                                           | DNS-rebinding allowlist. Always enforced; in `dev_mode` it defaults to `localhost`, `127.0.0.1`, `[::1]`        |
| `mcp_db_url`                                                                  | Connection for the read-only MCP database role (§4)                                                             |

**Boot guard.** When `deployment_env` is not `local`, the app raises at startup
if any of these hold:

- `dev_mode` is true;
- `jwt_secret_key` or `portal_jwt_secret_key` is empty or equals the known
  default `changeme-only-for-local-dev-do-not-use-in-prod!!`, or the two keys
  are equal;
- `google_client_id` (portal) or `mcp_google_client_id` is empty (an empty
  audience would accept ID tokens issued for any Google client);
- `mcp_google_client_secret`, `mcp_resource_url`, `mcp_issuer_url`, or
  `mcp_db_url` is missing, or `mcp_resource_url` is not `https`.

Detection uses the explicit `deployment_env` setting, not `K_SERVICE`, so
Compose, VM, or GKE deployments also fail closed. The default is `production`,
so forgetting to set it can only make the app stricter.

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

1. **Checks scopes.** Reads the principal from the SDK auth context
   (`get_access_token()`) and rejects the call with `isError=True`
   ("insufficient scope") unless the principal holds every scope in
   `ToolSpec.scopes`. The SDK only enforces `AuthSettings.required_scopes` for
   the whole endpoint, so this check is what makes per-tool scopes such as the
   future `kb:query` real. Public-tier tools on `/mcp/public` have no principal
   and declare no scopes.
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
  `api_user`, `api_key`, or any `mcp_oauth_*` table;
- `default_transaction_read_only = on` and `statement_timeout` (e.g. 10 s) set
  on the role itself, so a tool cannot exceed them even by mistake;
- provisioned with the same Pulumi pattern as the existing `READONLY_USERS`
  (`deployment/cloud/gcp/infrastructure/config.py`, `secret_manager.py`), with
  its password in Secret Manager.

The verifier, OAuth provider, and rate limiter continue to use the normal
read-write engine, because they must write tokens, consents, and counters.

In `deployment_env=local`, `mcp_db_url` may point at the local database with the
same role created by a dev setup script.

### Error mapping

| Raised                                                | Client receives                                                             |
| ----------------------------------------------------- | --------------------------------------------------------------------------- |
| `webservice.exceptions` not-found / validation errors | `isError=True`, actionable message (e.g. "unknown geoid; call list_geoids") |
| `SQLAlchemyError` or any unexpected exception         | `isError=True`, "Internal error (ref=<uuid>)"; full trace logged only       |
| Missing/invalid token                                 | Rejected by SDK auth at the HTTP layer before the tool runs                 |
| Principal lacks a scope in `ToolSpec.scopes`          | `isError=True`, "insufficient scope" (checked in `runtime.py`)              |
| Per-principal rate limit exceeded                     | `isError=True`, "rate limit exceeded; retry after N s"                      |

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

| Path                                           | Served by                                                  |
| ---------------------------------------------- | ---------------------------------------------------------- |
| `/.well-known/oauth-protected-resource/mcp`    | SDK (RFC 9728 path insertion for resource `/mcp`)          |
| `/.well-known/oauth-authorization-server`      | SDK                                                        |
| `/register`, `/authorize`, `/token`, `/revoke` | SDK handlers backed by our `provider.py`                   |
| `/mcp/oauth/consent`                           | Ours (`auth/routes.py`): consent page and its POST handler |
| `/mcp/oauth/google/callback`                   | Ours (`auth/routes.py`): Google redirect target            |

### Flow

1. Client calls `/mcp` without a token → `401` with `WWW-Authenticate` whose
   `resource_metadata` points to `/.well-known/oauth-protected-resource/mcp`.
2. Client registers via DCR.
   `ClientRegistrationOptions(enabled=True, valid_scopes=["data:read"], default_scopes=["data:read"], client_secret_expiry_seconds=<set>)`.
   Our `provider.register_client()` enforces the redirect URI policy below and
   rejects anything else with `invalid_redirect_uri`.
3. Client starts `/authorize`. `provider.authorize()`:
   - validates `client_id`, the exact `redirect_uri`, PKCE S256, scope, and
     `resource == mcp_resource_url`. **Errors before `client_id` and
     `redirect_uri` are validated are shown as an error page on our domain and
     never redirected**;
   - stores the authorization request server-side (single-use, 10 min TTL);
   - sets a short-lived (10 min), `HttpOnly`, `Secure`, `SameSite=Lax` browser
     cookie scoped to path `/mcp/oauth`, holding a random **binding nonce**, and
     stores only its hash on the request. `Lax` is required so the cookie is
     sent on the top-level redirect back from Google;
   - redirects to the consent page, which our server renders.
4. **Consent page (ours).** It shows the client's registered name, the redirect
   URI **host**, and the requested scopes, with Approve/Deny. The page is served
   with `Content-Security-Policy: frame-ancestors 'none'` and
   `X-Frame-Options: DENY`; its POST is CSRF-protected by the binding cookie.
   Deny ends the flow with `access_denied` to the validated redirect URI.
   **Remembered approvals:** the page is skipped only if the browser presents a
   valid signed consent cookie (`__Host-` prefixed, `HttpOnly`, `Secure`) naming
   an `api_user_id`, **and** `mcp_oauth_consent` holds an unrevoked approval for
   that `(api_user_id, client_id)` covering the requested scopes. After Google
   login (step 6) the logged-in user must equal that `api_user_id`; otherwise
   the flow fails with an error page, no redirect. Remembered consents are
   listed and revocable by admins (see Admin operations).
5. On Approve we redirect to Google OIDC (authorization-code flow with our
   **MCP-specific Google client**). The Google `state` is a random value bound
   to the stored request and to the binding-nonce hash; it is single-use.
6. `/mcp/oauth/google/callback`:
   - requires the binding cookie and checks that its hash matches the request
     referenced by `state`; consumes `state` and the stored request (reuse or
     expiry → error page, no redirect);
   - exchanges the Google code server-side with the MCP client secret and
     verifies the ID token with **`audience = mcp_google_client_id` (never
     empty)**, issuer, expiry, and `email_verified is True` (a missing claim is
     a rejection). This is a new helper; the portal's `verify_google_id_token`
     is not reused because it accepts a missing `email_verified` and an empty
     audience;
   - resolves the `ApiUser` (see Identity binding). No match, or `disabled` →
     `access_denied` to the validated redirect URI with a message to ask an
     admin for API access.
7. We store the approval in `mcp_oauth_consent` for `(api_user_id, client_id)`
   and set or refresh the consent cookie. We mint an authorization code bound to
   `client_id`, `redirect_uri`, `resource`, the PKCE challenge, and
   `api_user_id`, and redirect to the client.
8. `/token` exchanges the code (PKCE verified) for an access token and a
   rotating refresh token (see Token lifecycle).

### DCR redirect URI policy

A registration is rejected unless **every** `redirect_uri`:

- is `https://` with a host, **or** `http://127.0.0.1[:port]/…`,
  `http://[::1][:port]/…`, or `http://localhost[:port]/…` (loopback, for desktop
  and CLI clients);
- has no fragment and no userinfo;
- if `mcp_redirect_host_allowlist` is set (non-empty), has an `https` host in
  that allowlist (e.g. the claude.ai and ChatGPT connector callback hosts).
  Loopback URIs remain allowed.

`/register` is per-IP rate limited, and clients that never complete a flow are
deleted after 24 h, so the client table cannot be flooded.

### Identity binding

`ApiUser` gains `google_sub` (nullable, unique) alongside the existing `email`.

- **Lookup by `sub` first.** If an `ApiUser` has `google_sub` equal to the ID
  token's `sub`, that is the user.
- **First link.** Otherwise, match the verified Google email to
  `lower(ApiUser.email)` among users whose `google_sub` is **null**. Exactly one
  match → store the Google `sub` in `google_sub`. More than one match → refuse
  (ask an admin).
- **Already linked to another account.** If the email matches an `ApiUser` whose
  `google_sub` is set to a different value, refuse. The email in the ID token
  never overrides an existing link, so a Google account whose email later
  changes, or a new account reusing an old address, cannot take over an
  `ApiUser`.
- The `hd` (Workspace domain) claim is **not** required, so researchers with
  personal Google accounts can log in. Binding to `sub` is the protection.

Because `ApiUser.email` and `google_sub` now act as login identifiers, changing
either is a privileged operation:

- only admins (JWT-only `AdminUserDep`, which already excludes ApiKeys) can
  change them, through the new admin endpoint below;
- every change is written to an audit table;
- changing `email` clears `google_sub` (forcing a fresh link) and **revokes all
  of the user's MCP grants** (tokens, refresh families, remembered consents).

### Admin operations (new endpoints, PR 1)

`v1/auth/router.py` has no user-update endpoint today, so PR 1 adds, all behind
`AdminUserDep`:

| Endpoint                                     | Purpose                                                                        |
| -------------------------------------------- | ------------------------------------------------------------------------------ |
| `PATCH /v1/auth/users/{user_id}`             | Update `email`, `full_name`, `disabled`, or clear `google_sub`. Audit-logged.  |
| `GET /v1/auth/users/{user_id}/mcp-grants`    | List the user's active MCP clients, consents, and token families (no secrets). |
| `DELETE /v1/auth/users/{user_id}/mcp-grants` | Revoke all MCP grants for the user. Audit-logged.                              |

Setting `disabled=true` also revokes all MCP grants, so re-enabling a user does
not silently restore old tokens.

### Storage

New SQLModel tables in `datamodels`, created through one PR 1 Alembic migration:

| Table                          | Notes                                                                                 |
| ------------------------------ | ------------------------------------------------------------------------------------- |
| `mcp_oauth_client`             | DCR clients; `last_completed_at` for the 24 h expiry of never-used clients            |
| `mcp_oauth_pending_request`    | Stored `/authorize` requests and binding-nonce hash; single-use, 10 min TTL           |
| `mcp_oauth_consent`            | Remembered `(api_user_id, client_id, scopes)` approvals                               |
| `mcp_oauth_authorization_code` | Single-use codes, bound as in step 7                                                  |
| `mcp_oauth_token`              | Access and refresh tokens with `family_id`, `kind`, expiry, `revoked_at`              |
| `mcp_rate_window`              | Per-`api_user_id` fixed-window counters (see Rate limiting)                           |
| `api_user_audit`               | `actor_id`, `target_id`, `field`, `old_value`, `new_value`, `at` for identity changes |

The same migration adds `api_user.google_sub` (nullable, unique).

All codes and tokens are high-entropy random values stored as **SHA-256 hashes**
(not Argon2, which would add per-request CPU cost for no benefit at this
entropy). Codes and tokens carry a foreign key to `api_user.id`.

**Email uniqueness and backfill.** `api_user.email` is optional and not unique
today. PR 1 does not add a unique email index, because the deploy would run the
migration before admins can use the new `PATCH /v1/auth/users/{user_id}`
endpoint to fix existing rows. Instead:

- at first link, if more than one `ApiUser` matches the verified email
  (case-insensitive), the login is refused with an error asking the user to
  contact an admin; nothing is linked;
- after PR 1 deploys, an admin lists users with a null or duplicate email and
  fixes them through the new endpoint;
- PR 6 adds the case-insensitive unique index on `lower(email)` (where not
  null); that migration fails fast with a clear message if duplicates remain.

Users with a null `email` keep ApiKey/JWT access on `/mcp`; they only cannot
complete the Google OAuth flow until an email is set.

### Token lifecycle

| Item               | Rule                                                                                                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Token format       | Typed prefixes: access `bcv_mcp_at_…`, refresh `bcv_mcp_rt_…` (lets the verifier route by prefix, and makes leaked tokens matchable by a custom secret-scanning pattern) |
| Authorization code | Single-use, 60 s TTL, bound to `client_id`, `redirect_uri`, `resource`, PKCE challenge. A reused code revokes every token issued from it.                                |
| Access token       | 1 h, `resource = mcp_resource_url`, scope `data:read`                                                                                                                    |
| Refresh token      | Rotated on every use; 30-day absolute lifetime per family; reuse of a rotated refresh token revokes the whole family                                                     |
| Revocation         | SDK `/revoke` enabled; admin grant revocation; automatic on `disabled=true` and on `email` change                                                                        |

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

**Audience for JWT and ApiKey principals.** With `validate_token_resource=True`
the SDK's `BearerAuthBackend` rejects any `AccessToken` whose `resource` is not
`mcp_resource_url`, including those from the JWT and ApiKey paths. The verifier
therefore sets `resource = mcp_resource_url` on those principals. In practice
this means their audience is **asserted by us** (they are our own credentials,
accepted only by this service), not checked from a token claim.

The verifier yields
`Principal(api_user_id, username, kind="oauth"|"jwt"|"apikey", scopes)`. Tools
and logs use `principal.api_user_id`; emails are never logged.

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

- PKCE S256 mandatory; `plain` rejected.
- Exact-match redirect URIs; DCR redirect URI policy enforced.
- Consent page served by us before Google; `frame-ancestors 'none'` and
  `X-Frame-Options: DENY` on consent and authorize pages.
- Google `state` bound to the browser binding cookie; `state` and stored
  requests single-use with TTL.
- No redirect to `redirect_uri` for errors before client and redirect URI are
  validated.
- Separate MCP Google client; ID token audience always set;
  `email_verified is True`.
- Identity bound to Google `sub` after first link; identity changes admin-only,
  audit-logged, and revoke grants.
- `validate_token_resource=True`; JWT/ApiKey principals stamped with
  `mcp_resource_url`.
- API JWTs require `token_use="api"`; portal tokens use a separate key.
- ApiKey and API JWT principals get `data:read` only; DCR `valid_scopes` is
  `["data:read"]`.
- Per-tool scopes checked in `runtime.py`.
- `ApiUser.disabled` and `ApiKey.is_active` checked on every request.
- Google login without a matching active `ApiUser` is denied, never
  auto-provisioned.
- Codes single-use; refresh-token reuse revokes the family.
- No tokens, codes, ApiKeys, or emails logged.

## 6. Delivery plan (PR sequence)

| PR  | Scope                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Depends on      |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------- |
| 0   | `datamodels/config.py` Docker/local DB host auto-detect (standalone)                                                                                                                                                                                                                                                                                                                                                                                                                                                     | —               |
| 1   | `mcp>=2.3,<3`; registry, runtime (scope check, per-principal limit, read-only engine), error mapping; `/mcp` with OAuth 2.1 (consent page, cookie-bound `state`, DCR redirect policy, `sub` binding, token lifecycle) + API JWT + ApiKey verifier; `token_use` claim and split portal signing key; admin user-update and MCP-grant endpoints with audit log; OAuth/audit/rate tables and `google_sub` migration; `biocirv_mcp_ro` role for local dev; `list_geoids` smoke tool; boot guard, `deployment_env`, `dev_mode` | —               |
| 2   | Feedstock availability + analysis tools (worked example referenced by docs)                                                                                                                                                                                                                                                                                                                                                                                                                                              | 1               |
| 3   | USDA census + survey tools                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 1               |
| 4   | `/mcp/public` mount + per-IP limit + `tools/public.py` over `PublicDatasetService`                                                                                                                                                                                                                                                                                                                                                                                                                                       | 1, #545         |
| 5   | Docs: "Adding MCP tools" guide, AGENTS.md pointer, `tools/_template.py`, client connection how-to                                                                                                                                                                                                                                                                                                                                                                                                                        | 1 (parallel OK) |
| 6   | Cloud deployment: Secret Manager entries for the MCP Google client, `portal_jwt_secret_key`, and `biocirv_mcp_ro` password; Pulumi role provisioning; `deployment_env`, issuer/resource URLs, custom domain; case-insensitive unique index on `lower(api_user.email)` after the admin backfill                                                                                                                                                                                                                           | 1               |

Each PR targets the 200–400 line sizing guideline. PR 1 is kept as one PR by
decision: the OAuth flow, its hardening, and the identity and admin changes it
relies on are one security boundary and are reviewed together. PR 1 is expected
to be well over the size target, and its description must explain this and point
reviewers to the §5 hardening checklist as the review map.

**PR 1 deploy notes.** Introducing `token_use` and the separate portal signing
key logs out every API JWT holder and every portal session at deploy. Announce
the deploy window to users.

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
    only, including for `is_admin` users.
- Provider and routes (Google mocked), one test per §5 hardening item:
  - DCR: non-`https`, non-loopback, fragment, userinfo, and (when the allowlist
    is set) non-allowlisted redirect URIs rejected; `admin` and `kb:query` scope
    requests rejected;
  - `/authorize`: unknown client or unregistered redirect URI → error page, no
    redirect; `plain` PKCE rejected; wrong `resource` rejected;
  - consent page sends `frame-ancestors 'none'` and `X-Frame-Options: DENY`;
    consent POST without the binding cookie rejected;
  - callback: missing or mismatched binding cookie, reused `state`, expired
    request → error page, no redirect;
  - ID token: wrong audience, `email_verified` false, `email_verified` missing →
    rejected;
  - identity: first login links `google_sub`; later login with the same `sub`
    but a different email still maps to the same user; a different `sub` with
    the linked email is refused; email matching more than one `ApiUser` is
    refused; no match or `disabled` → `access_denied`;
  - remembered consent: skipped only with cookie + DB row for the same user;
    mismatch after login → error page;
  - tokens: code reuse revokes issued tokens; refresh-token reuse revokes the
    family; refresh family expires at 30 days.
- Admin endpoints: non-admin and ApiKey callers rejected; email change clears
  `google_sub`, revokes grants, and writes an audit row; `disabled=true` revokes
  grants.
- Boot guard: with `deployment_env` unset or `staging`/`production`, each
  condition in §3 raises; `dev_mode` with `deployment_env=local` boots.
- Client IP: spoofed left-most `X-Forwarded-For` entries are ignored.

### Integration (shared dev DB)

- Drive the ASGI app with the SDK streamable-HTTP client: unauthenticated `/mcp`
  → 401 with `resource_metadata` pointing to
  `/.well-known/oauth-protected-resource/mcp`; ApiKey → tool call succeeds; API
  JWT from `/v1/auth/token` → tool call succeeds; `/mcp/public` lists only
  public tools.
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
  the `SELECT` it needs) on `api_user`, `api_key`, and the `mcp_oauth_*` tables.
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

| Artifact                                           | Audience       | Content                                                                                                      |
| -------------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------ |
| `docs/webservice/mcp/adding-tools.md` (MkDocs nav) | Humans, agents | Step-by-step checklist: pick tier/scopes, write handler over service, reuse schema, register, test, document |
| `src/ca_biositing/webservice/AGENTS.md` pointer    | Agents         | "Adding or changing an API? Also update MCP tools" with a link to the guide                                  |
| `mcp/tools/_template.py`                           | Both           | Annotated copy-me module                                                                                     |
| Registry guard test                                | Both           | Fails CI with a message linking the guide when the checklist is not followed                                 |
| `docs/webservice/mcp/connecting-clients.md`        | Humans         | Connecting Claude Code, Claude Desktop, claude.ai, MCP Inspector                                             |

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

| Risk                                                                     | Mitigation                                                                                                                                                          |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mcp` 2.x API churn within the major version                             | Bounded pin `<3`; SDK usage isolated to `registry.py`, `runtime.py`, and `auth/`                                                                                    |
| Google OIDC proxy complexity (callback state, PKCE)                      | Dedicated PR 1 review; a unit test per hardening item                                                                                                               |
| Confused-deputy attack through open DCR and a shared upstream client     | Our own consent page naming the redirect host, cookie-bound `state`, DCR redirect URI policy (§5); manual attack walkthrough in PR 1                                |
| PR 1 is large and security-critical                                      | Kept as one boundary by decision; §5 hardening checklist is the review map; one test per item                                                                       |
| PR 1 logs out all API JWT and portal sessions                            | Announce the deploy window; JWT lifetime is short (`jwt_expire_minutes`)                                                                                            |
| Read-only DB role adds provisioning work                                 | Reuse the existing `READONLY_USERS` Pulumi pattern; local dev script creates the role                                                                               |
| Ingested data or KB text carries prompt-injection payloads to the agent  | Tools are read-only at the DB level; outputs are structured; risk documented in the client guide                                                                    |
| Shared dev DB flakiness / cross-run interference                         | Per-run namespacing, cleanup job, quarantine marker for reference-data tests                                                                                        |
| `ApiUser` emails missing, duplicated, or not the person's Google account | Ambiguous emails refuse first link; admin backfill via the new endpoint; PR 6 unique index fails fast on duplicates; binding moves to Google `sub` after first link |
| #545 schemas change before merge                                         | PR 4 starts only after #545 merges                                                                                                                                  |
| Hosted connector differences (claude.ai vs. ChatGPT)                     | Manual verification with each connector before closing PR 1; document quirks in the guide                                                                           |
