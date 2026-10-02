# Hybrid Query Skill

Query the **relational** feedstock database (ca-biositing) and the **semantic**
knowledge base (biocirv-kb) from the same place, so an agent can pull a hard
number and its supporting literature in one workflow.

## The two servers

|           | ca-biositing                                                                                  | biocirv-kb                                                                                                                                        |
| --------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Data      | Relational: resource/parameter analysis values, availability, USDA census/survey              | Semantic: RAG over scientific reports + knowledge graph                                                                                           |
| Local URL | `http://localhost:8000/mcp/mcp`                                                               | `http://localhost:8001/mcp/`                                                                                                                      |
| MCP style | `FastMCP(stateless_http=True)` — every `tools/call` is a standalone POST, no session required | Stateful streamable HTTP — requires `initialize` → `notifications/initialized` handshake, then the returned `mcp-session-id` header on every call |
| Start it  | `pixi run start-webservice` (this repo)                                                       | `cd /Users/pjsmitty301/sci-rag-test/biocirv-kb && .venv/bin/sci-rag serve --port 8001`                                                            |

**Why port 8001 for the KB server:** its default port is also 8000, which
collides with ca-biositing's webservice on this machine. Always start it with
`--port 8001` locally, or set `KB_MCP_URL` to wherever it actually ended up.

**Why the two servers need different handshake logic:** ca-biositing's server
never issues a session id and silently accepts calls without one. biocirv-kb's
server rejects `tools/call` with `"Session not found"` if you skip `initialize`.
The `scripts/hybrid_query_client.py` helper always does the full handshake and
caches whatever session id (if any) comes back, so you don't have to
special-case either server by hand.

## Auth

**Local development:**

- `pixi run start-webservice` runs ca-biositing's `/mcp` without auth by default
  (dev mode is auto-detected locally).
- To exercise the auth code path locally, set `BIOSITING_MCP_API_KEY` before
  running the client:
  ```bash
  export BIOSITING_MCP_API_KEY="sk_dev_..."
  pixi run python .agents/skills/hybrid-query/scripts/hybrid_query_client.py test
  ```

**Staging / Production:**

- ca-biositing's `/mcp` endpoint requires authentication via the `X-API-Key`
  header once deployed (see `plans/mcp_auth_implementation_plan.md`).
- Set `BIOSITING_MCP_API_KEY` before querying a remote server:
  ```bash
  export BIOSITING_MCP_API_KEY="<your-key>"
  pixi run python .agents/skills/hybrid-query/scripts/hybrid_query_client.py test
  ```
  The script automatically adds the key to every request to `biositing` via the
  `X-API-Key` header. biocirv-kb's `kb` server has its own separate auth (if
  any); this env var only affects the `biositing` server.

## Workflow

1. **Test first.** Before doing anything else, confirm both servers are up and
   speaking MCP:

   ```bash
   pixi run python .agents/skills/hybrid-query/scripts/hybrid_query_client.py test
   ```

   This runs the handshake against both servers and returns each one's tool
   list. If a server is down, fix that before querying — don't guess at results.
   - If `biositing` fails: `pixi run start-webservice` in this repo.
   - If `kb` fails: start it per the table above. Also check `docker ps` shows
     `pgvector/pgvector:pg16` running (biocirv-kb's DB) — without it, the app
     process won't come up.

2. **Validate names before querying.** Resource names, parameter names, and
   geoids in ca-biositing don't always match plain-English terms (e.g. "walnut
   shells" isn't a resource — it's "walnut shelling fines"). Call
   `list-tools biositing` then use `list_analysis_resources` /
   `list_analysis_parameters` to check spelling before calling
   `get_feedstock_analysis_parameter`.

3. **Query one server directly** when you only need one kind of data:

   ```bash
   # Relational
   pixi run python .agents/skills/hybrid-query/scripts/hybrid_query_client.py \
     call biositing get_feedstock_analysis_parameter \
     '{"resource": "walnut shelling fines", "geoid": "06000", "parameter": "ash solids"}'

   # Semantic
   pixi run python .agents/skills/hybrid-query/scripts/hybrid_query_client.py \
     call kb search_corpus '{"query": "walnut shell ash content", "top_k": 3}'
   ```

4. **Query both together** for "what's the number, and what does the literature
   say" questions, using the built-in combined helper:

   ```bash
   pixi run python .agents/skills/hybrid-query/scripts/hybrid_query_client.py \
     hybrid "walnut shelling fines" "06000" "ash solids" \
     --kb-query "walnut shell ash content"
   ```

   This returns `{"relational": ..., "semantic": ...}` — the exact metric value
   from the relational DB plus ranked, cited evidence chunks from the KB. Read
   both before answering; the KB's `search_corpus` results carry `license_class`
   — don't quote `restricted` chunks verbatim outside this conversation,
   summarize instead.

   For a narrative answer instead of raw evidence, call `kb`'s `answer_question`
   tool the same way — it returns a cited, synthesized answer rather than
   chunks.

## Tool reference

**biositing** (12 tools — see `list-tools biositing` for the live, current list;
notably it also proxies `search_biositing_knowledge`, `ask_biositing_question`,
and `get_feedstock_entity_relationships`, which forward to the KB server
directly from within ca-biositing's own API. Use those instead of this skill's
`kb` calls when working purely through the ca-biositing REST/MCP surface, e.g.
in production where the KB is only reachable via ca-biositing's proxy, not
directly.)

**kb** (8 tools): `search_corpus`, `answer_question`, `get_document`,
`get_citations`, `search_entities`, `get_entity_relationships`, `list_sources`,
`corpus_stats`.

## Gotchas

- **Don't reuse a stale session id across process runs.** The script caches
  sessions per-process; each new script invocation re-handshakes. This is
  intentional and cheap (one extra round trip) — don't try to persist session
  ids to disk.
- **`/mcp` redirects to `/mcp/`** on both servers (a 307). The client already
  points at the canonical trailing-slash / double-`mcp` paths above; if you
  hand-roll a curl call, follow the redirect or use the documented path
  directly.
- **`get_feedstock_analysis_parameter` and friends need exact resource names.**
  They come back empty or wrong rather than erroring loudly on a near-miss —
  always validate with `list_analysis_resources` first.
- **KB results can be `restricted` license.** Check `license_class` in
  `search_corpus` output before quoting text at length outside internal
  analysis.
- **Local dev without `BIOSITING_MCP_API_KEY`:** Works out of the box; auth is
  disabled in dev mode.
- **Staging/production:** Must set `BIOSITING_MCP_API_KEY` or requests to
  `biositing` fail with 401.
