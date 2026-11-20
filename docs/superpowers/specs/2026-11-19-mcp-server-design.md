# MCP Server Design (follow-up to PR #484)

- **Issue:** sustainability-software-lab/ca-biositing#494
- **Status:** Design approved in brainstorming; pending written-spec review
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
- an MCP OAuth 2.1 access token, whose Google login is matched to an `ApiUser`
  by verified email (§5).

No separate MCP user list exists, and the portal email allowlist does not grant
MCP access. Disabling an `ApiUser` revokes REST and MCP access together.

### Success criteria

1. All four client types above can connect and call tools appropriate to them.
   Any active `ApiUser` can use `/mcp` without extra provisioning; anyone who is
   not an active `ApiUser` cannot.
2. In Cloud Run the app refuses to boot if OAuth configuration is missing (fail
   closed). Auth is disabled only when `dev_mode` is explicitly set.
3. An authenticated-tier tool can never be reachable from `/mcp/public`.
4. Adding tools for a new API requires one new module plus one registry
   registration, following a documented checklist enforced by tests.
5. Tool handlers never block the event loop; tool outputs are uniformly typed;
   DB/internal errors never leak to clients.

### Out of scope

- **Knowledge-base (`biocirv-kb`) proxy tools.** Moved to a separate issue (see
  §9). This design only reserves the `kb` tier name and the `kb:query` scope so
  that follow-up is purely additive.
- Write/mutating tools. All tools are read-only.
- `datamodels/config.py` Docker/local host auto-detection from the PoC — lands
  as its own standalone PR (PR 0), not bundled with MCP work.

## 2. Key decisions

| Decision          | Choice                                                                                                                      | Rationale                                                                                                                                                          |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| SDK               | `mcp>=2.3,<3`, `mcp.server.mcpserver.MCPServer`                                                                             | `mcp.server.fastmcp` raises `ModuleNotFoundError` in 2.x; a bounded pin prevents a relock from breaking the webservice at import time (PoC flaw).                  |
| Auth              | Native OAuth 2.1 via SDK `auth_server_provider` + `token_verifier`, embedded Google-OIDC proxy; ApiKey and API JWT accepted | Hosted connectors need OAuth discovery + DCR, which Google does not provide directly; reuses existing Google OIDC client; no new vendor; we host no password form. |
| Who gets access   | Any active `ApiUser` (Google login matched to `ApiUser` by verified email)                                                  | API access implies MCP access; one user list, one place to grant and revoke (§1 Access model).                                                                     |
| Tool registration | Per-domain modules + tier-filtered registry over the service layer                                                          | Absorbs new APIs with one module each; service layer stays the single source of truth; deliberate, agent-quality tool descriptions.                                |
| Anonymous access  | Separate mount `/mcp/public`                                                                                                | SDK auth gates a whole streamable-HTTP endpoint, so public and authenticated tools cannot safely share one mount.                                                  |
| Test DB           | Shared non-prod (dev) DB with per-run namespacing + cleanup job                                                             | Team choice; risks mitigated in §7.                                                                                                                                |
| Delivery          | OAuth first (PR 1), then small follow-up PRs                                                                                | The riskiest, most security-sensitive piece gets focused review; everything after is additive.                                                                     |

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
    routes.py      Google OIDC callback route
```

### Mounts

| Path          | Tiers served                             | Auth                                         |
| ------------- | ---------------------------------------- | -------------------------------------------- |
| `/mcp`        | `public`, `authenticated` (+ `kb` later) | OAuth 2.1, API JWT, or `ApiKey` bearer       |
| `/mcp/public` | `public` only                            | None; per-IP rate limit (reuse #545 limiter) |

Both servers are built from the same `Registry` by filtering on tier. A tool
outside the requested tier set is never registered on that server — exclusion is
structural, not a call-time check. `/mcp/public` must be mounted before `/mcp`
so the prefix route does not capture it. Both use `stateless_http=True` (Cloud
Run has multiple instances and no session affinity). The SDK OAuth endpoints
(`/.well-known/oauth-protected-resource`,
`/.well-known/oauth-authorization-server`, `/register`, `/authorize`, `/token`,
`/revoke`) are served by the authenticated server's app.

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

| Setting                      | Purpose                                                              |
| ---------------------------- | -------------------------------------------------------------------- |
| `dev_mode` (default `False`) | Disables auth and DNS-rebinding protection locally. Must be explicit |
| `mcp_issuer_url`             | OAuth issuer / resource server URL (public Cloud Run URL)            |
| `google_client_id` / secret  | Existing Google OIDC client (reused); secret from Secret Manager     |
| `mcp_public_rate_limit`      | Per-IP limit for `/mcp/public`                                       |
| `mcp_allowed_hosts`          | DNS-rebinding allowlist (protection enabled whenever not `dev_mode`) |

**Boot guard:** if `K_SERVICE` is set (Cloud Run) and either `dev_mode` is true
or any required OAuth setting is missing, the app raises at startup.

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

1. Runs the handler via `anyio.to_thread.run_sync` (fixes the PoC's event-loop
   blocking).
2. Opens a SQLModel session per call and closes it in `finally`.
3. Validates that the return value is an instance of `output_model`.
4. Maps exceptions (below).
5. Logs `tool`, `principal.sub`, `principal.kind`, `tier`, duration, outcome.

### Error mapping

| Raised                                                | Client receives                                                             |
| ----------------------------------------------------- | --------------------------------------------------------------------------- |
| `webservice.exceptions` not-found / validation errors | `isError=True`, actionable message (e.g. "unknown geoid; call list_geoids") |
| `SQLAlchemyError` or any unexpected exception         | `isError=True`, "Internal error (ref=<uuid>)"; full trace logged only       |
| Missing/invalid token or insufficient scope           | Rejected by SDK auth at the HTTP layer before the tool runs                 |

## 5. Authentication (OAuth 2.1, PR 1)

### Flow

1. Client calls `/mcp` without a token → `401` with `WWW-Authenticate`
   referencing protected-resource metadata.
2. Client discovers the authorization server and registers via DCR
   (`ClientRegistrationOptions(enabled=True, valid_scopes=[...], default_scopes=["data:read"])`).
3. `provider.authorize()` persists the authorization request (PKCE challenge,
   redirect URI, scopes, state) and redirects to Google OIDC.
4. Google redirects to our callback (`auth/routes.py`). We verify the ID token
   and require `email_verified`. We then look up the `ApiUser` whose `email`
   matches the Google email (case-insensitive). If there is no match, or the
   user is `disabled`, the flow ends with an `access_denied` error that tells
   the user to ask an admin for API access. On a match we mint an authorization
   code bound to that `ApiUser.id` and redirect to the client's registered
   redirect URI.
5. `/token` exchanges the code (PKCE S256 verified) for an opaque access token
   (1 h) and a rotating refresh token.

### Storage

New SQLModel tables in `datamodels`, created through an Alembic migration:
`mcp_oauth_client`, `mcp_oauth_authorization_code`, `mcp_oauth_token`. Codes and
tokens are stored as hashes only, and codes and tokens carry a foreign key to
`api_user.id`. Storage is Postgres-backed because Cloud Run runs multiple
instances.

**`ApiUser.email` change (same PR 1 migration).** Today `api_user.email` is
optional and not unique, so it cannot identify a user. The migration adds a
case-insensitive unique index on `lower(email)` where `email` is not null.
Before it runs, an admin must:

1. List `ApiUser`s with a null `email` or a duplicate email (case-insensitive).
2. Fill in or correct those emails (the Google account each person will log in
   with) via `PATCH`/admin tooling.

The migration fails fast with a clear message if duplicates remain, rather than
silently picking one. Users with a null `email` keep REST and ApiKey/JWT access
on `/mcp`; they only cannot complete the Google OAuth flow until an email is
set.

### Scopes

| Scope       | Granted to                                    |
| ----------- | --------------------------------------------- |
| `data:read` | Any active `ApiUser`, whichever credential    |
| `kb:query`  | Reserved — not grantable until KB issue lands |
| `admin`     | Reserved — `ApiUser.is_admin`                 |

### Verifier

`verifier.py` implements the SDK `TokenVerifier`. It tries each credential type
in order and stops at the first that resolves:

1. **MCP OAuth access token:** hash match, not expired, not revoked, audience =
   this resource.
2. **API JWT** (from `/v1/auth/token`): `decode_access_token()` with the
   existing `jwt_secret_key`; resolve `sub` to an `ApiUser`.
3. **ApiKey:** `auth_service.validate_api_key()`, then
   `check_and_increment_rate_limit()` (existing per-key rate limit applies).
4. Otherwise return `None`.

Every path then loads the `ApiUser` and rejects it if `disabled`. This check
runs on every request, so disabling a user takes effect immediately even for
unexpired tokens. All paths yield one
`Principal(api_user_id, username, kind="oauth"|"jwt"|"apikey", scopes)`.

**API JWT and audience binding.** API JWTs carry no `aud` claim, so they bypass
the audience check that applies to MCP OAuth tokens. This is accepted because we
issue them only for this service with our own secret. It should be revisited if
the API JWT secret is ever shared with another service. They keep their existing
lifetime (`jwt_expire_minutes`).

### Hardening checklist

- PKCE S256 mandatory; `plain` rejected.
- Exact-match redirect URIs.
- `validate_token_resource=True` (audience binding) for MCP OAuth tokens; see
  the API JWT exception above.
- `ApiUser.disabled` checked on every request for every credential type.
- Google login without a matching active `ApiUser` is denied, never
  auto-provisioned.
- Revocation enabled.
- DNS-rebinding protection on whenever not `dev_mode`.
- No tokens, codes, or ApiKeys logged.

## 6. Delivery plan (PR sequence)

| PR  | Scope                                                                                                                                                                                                        | Depends on      |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------- |
| 0   | `datamodels/config.py` Docker/local DB host auto-detect (standalone)                                                                                                                                         | —               |
| 1   | `mcp>=2.3,<3`; registry, runtime, error mapping; `/mcp` with OAuth 2.1 + API JWT + ApiKey verifier; OAuth tables + `api_user.email` unique index migration; `list_geoids` smoke tool; boot guard, `dev_mode` | —               |
| 2   | Feedstock availability + analysis tools (worked example referenced by docs)                                                                                                                                  | 1               |
| 3   | USDA census + survey tools                                                                                                                                                                                   | 1               |
| 4   | `/mcp/public` mount + per-IP limit + `tools/public.py` over `PublicDatasetService`                                                                                                                           | 1, #545         |
| 5   | Docs: "Adding MCP tools" guide, AGENTS.md pointer, `tools/_template.py`, client connection how-to                                                                                                            | 1 (parallel OK) |
| 6   | Cloud Run deployment: Secret Manager entries for the Google OAuth client, ingress/issuer config                                                                                                              | 1               |

Each PR targets the 200–400 line sizing guideline. PR 1 is expected to exceed it
because of the OAuth provider and migration; its description must explain why it
cannot be split further.

## 7. Testing strategy

### Unit (no DB)

- Registry: `build_server({"public"})` contains no non-public tools.
- Guard: every registered `ToolSpec` has a tier, an output model, and a
  description of at least 40 characters; names are unique.
- Error mapping: each row of the §4 table.
- Verifier: MCP OAuth token, API JWT, and ApiKey paths each resolve to the right
  `ApiUser`; expired, revoked, and wrong-audience OAuth tokens rejected; a
  `disabled` user is rejected on every path, including with an unexpired token.
- Provider: PKCE S256 enforcement, exact redirect URI match, Google ID token
  verification mocked (`email_verified` false → rejected; email with no
  `ApiUser` → `access_denied`; email matching a disabled `ApiUser` →
  `access_denied`; email match is case-insensitive).
- Migration: fails with a clear message when duplicate emails exist.
- Boot guard: simulated Cloud Run env without OAuth config → startup raises.

### Integration (shared dev DB)

- Drive the ASGI app with the SDK streamable-HTTP client: unauthenticated `/mcp`
  → 401 with metadata; ApiKey → tool call succeeds; API JWT from
  `/v1/auth/token` → tool call succeeds; `/mcp/public` lists only public tools.
- **Namespacing:** every row a test creates (OAuth clients/tokens, ApiUsers)
  carries a per-run `test_run_id` prefix. Session-scoped teardown deletes rows
  for the current run only.
- **Cleanup job:** a scheduled job deletes `test_run_id`-prefixed rows older
  than 24 h (orphans from crashed runs). It never touches unprefixed rows.
- **Reference data:** tool-output assertions are taken from fixed reference rows
  in the dev DB, with expected values human-reviewed. Tests never mutate
  non-test rows or the config singleton (use dependency overrides instead).
- **Concurrency risk:** parallel CI runs share the DB; namespacing prevents row
  collisions, but reference-data changes (e.g. ETL reloads) can cause flakes.
  Integration tests that depend on reference values carry a marker so they can
  be quarantined without blocking unit tests.

### Manual

MCP Inspector against staging (`/mcp` OAuth flow and `/mcp/public`), documented
in each PR's "How to test" section.

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
> nightly. Extend the boot guard to require the KB URL/key in Cloud Run. Depends
> on MCP PR 1 (#494).

## 10. Risks

| Risk                                                                     | Mitigation                                                                                                                        |
| ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| `mcp` 2.x API churn within the major version                             | Bounded pin `<3`; SDK usage isolated to `registry.py`, `runtime.py`, and `auth/`                                                  |
| Google OIDC proxy complexity (callback state, PKCE)                      | Dedicated PR 1 review; a unit test per hardening item                                                                             |
| Shared dev DB flakiness / cross-run interference                         | Per-run namespacing, cleanup job, quarantine marker for reference-data tests                                                      |
| `ApiUser` emails missing, duplicated, or not the person's Google account | Pre-migration admin backfill (§5 Storage); migration fails fast on duplicates; clear `access_denied` message pointing to an admin |
| #545 schemas change before merge                                         | PR 4 starts only after #545 merges                                                                                                |
| Hosted connector differences (claude.ai vs. ChatGPT)                     | Manual verification with each connector before closing PR 1; document quirks in the guide                                         |
