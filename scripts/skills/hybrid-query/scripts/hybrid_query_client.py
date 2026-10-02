"""Client for querying the ca-biositing (relational) and biocirv-kb (semantic)
MCP servers side by side, hiding the fact that they speak two different MCP
transport dialects.

ca-biositing's server is built with FastMCP(stateless_http=True): every
``tools/call`` is a single self-contained POST, no handshake, no session.

biocirv-kb's server (sci-rag-kit) is a stateful streamable-HTTP MCP server:
it requires ``initialize`` -> ``notifications/initialized`` -> ``tools/*``,
and every call after ``initialize`` must carry the ``mcp-session-id`` header
the server handed back.

Rather than special-case each server, ``call_tool`` always does the full
handshake and reuses the session for the lifetime of the process (cheap: one
extra round trip, and the ca-biositing server ignores the session id it
never issued). This keeps one code path working for both servers, and for
any future MCP server regardless of which dialect it speaks.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import requests

# Default local endpoints. Override with env vars if you run on different
# ports (see SKILL.md's "Connection Requirements" section).
SERVERS = {
    "biositing": os.environ.get("BIOSITING_MCP_URL", "http://localhost:8000/mcp/mcp"),
    "kb": os.environ.get("KB_MCP_URL", "http://localhost:8001/mcp/"),
}

_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

# Add MCP API key to headers if set (needed once ca-biositing's /mcp auth is
# enabled — local dev defaults to auth off, so this is a no-op there unless
# you're deliberately testing the auth path; staging/production require it).
_mcp_api_key = os.environ.get("BIOSITING_MCP_API_KEY")
if _mcp_api_key:
    _HEADERS["X-API-Key"] = _mcp_api_key

# One session id per base URL, cached for the life of the process.
_sessions: dict[str, str | None] = {}


def _parse_sse(response: requests.Response) -> dict[str, Any]:
    """Pull the JSON-RPC envelope out of an SSE or plain-JSON response."""
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response.json()
    for line in response.text.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            return json.loads(line[6:])
    raise RuntimeError(f"No JSON-RPC envelope in response: {response.text[:300]!r}")


def _post(url: str, payload: dict[str, Any], session_id: str | None) -> requests.Response:
    headers = dict(_HEADERS)
    if session_id:
        headers["mcp-session-id"] = session_id
    return requests.post(url, json=payload, headers=headers, timeout=30)


def _ensure_session(url: str) -> str | None:
    """Run the initialize handshake once per base URL.

    Returns the session id if the server issued one (stateful servers like
    biocirv-kb), or None if it didn't (stateless servers like ca-biositing,
    which simply ignore session ids on every call).
    """
    if url in _sessions:
        return _sessions[url]

    init_payload = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "hybrid-query-skill", "version": "1.0"},
        },
        "id": 0,
    }
    response = _post(url, init_payload, session_id=None)
    response.raise_for_status()
    envelope = _parse_sse(response)
    if "error" in envelope:
        raise RuntimeError(f"initialize failed for {url}: {envelope['error']}")

    session_id = response.headers.get("mcp-session-id")
    if session_id:
        # Stateful server: complete the handshake with the required
        # notification before any tools/* call will be accepted.
        _post(url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, session_id)

    _sessions[url] = session_id
    return session_id


def resolve_url(server: str) -> str:
    if server in SERVERS:
        return SERVERS[server]
    return server  # allow a raw URL for one-off servers


def list_tools(server: str) -> list[dict[str, Any]]:
    url = resolve_url(server)
    session_id = _ensure_session(url)
    response = _post(url, {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}, session_id)
    response.raise_for_status()
    envelope = _parse_sse(response)
    if "error" in envelope:
        raise RuntimeError(f"tools/list failed for {url}: {envelope['error']}")
    return envelope["result"]["tools"]


def call_tool(server: str, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
    """Call one tool on one server ('biositing', 'kb', or a raw MCP URL)."""
    url = resolve_url(server)
    session_id = _ensure_session(url)
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments or {}},
        "id": 2,
    }
    response = _post(url, payload, session_id)
    response.raise_for_status()
    envelope = _parse_sse(response)
    if "error" in envelope:
        return {"error": envelope["error"]}

    content = envelope["result"]["content"][0]["text"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return content


def smoke_test() -> dict[str, Any]:
    """Verify both servers are up and speaking MCP. Run before real queries."""
    results: dict[str, Any] = {}
    for name, url in SERVERS.items():
        try:
            tools = list_tools(name)
            results[name] = {"url": url, "ok": True, "tool_count": len(tools), "tools": [t["name"] for t in tools]}
        except Exception as exc:  # noqa: BLE001 - surfaced to the caller, not swallowed
            results[name] = {"url": url, "ok": False, "error": str(exc)}
    return results


def hybrid_feedstock_query(resource: str, geoid: str, parameter: str, kb_query: str | None = None) -> dict[str, Any]:
    """Combine a relational lookup with semantic evidence for the same feedstock.

    This is the pattern to follow for "what's the X of Y, and what does the
    literature say" questions: one relational number, one grounded quote.
    """
    relational = call_tool(
        "biositing",
        "get_feedstock_analysis_parameter",
        {"resource": resource, "geoid": geoid, "parameter": parameter},
    )
    semantic = call_tool(
        "kb",
        "search_corpus",
        {"query": kb_query or f"{resource} {parameter}", "top_k": 3},
    )
    return {"relational": relational, "semantic": semantic}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the ca-biositing and biocirv-kb MCP servers")
    sub = parser.add_subparsers(dest="command", required=True)

    p_test = sub.add_parser("test", help="Smoke-test both servers (handshake + tools/list)")

    p_list = sub.add_parser("list-tools", help="List tools on one server")
    p_list.add_argument("server", choices=["biositing", "kb"])

    p_call = sub.add_parser("call", help="Call one tool on one server")
    p_call.add_argument("server", choices=["biositing", "kb"])
    p_call.add_argument("tool")
    p_call.add_argument("args", nargs="?", default="{}", help="JSON arguments")

    p_hybrid = sub.add_parser("hybrid", help="Combined relational + semantic query for one feedstock")
    p_hybrid.add_argument("resource")
    p_hybrid.add_argument("geoid")
    p_hybrid.add_argument("parameter")
    p_hybrid.add_argument("--kb-query", default=None)

    args = parser.parse_args()

    if args.command == "test":
        print(json.dumps(smoke_test(), indent=2))
    elif args.command == "list-tools":
        print(json.dumps(list_tools(args.server), indent=2))
    elif args.command == "call":
        print(json.dumps(call_tool(args.server, args.tool, json.loads(args.args)), indent=2))
    elif args.command == "hybrid":
        result = hybrid_feedstock_query(args.resource, args.geoid, args.parameter, args.kb_query)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
        sys.exit(1)
