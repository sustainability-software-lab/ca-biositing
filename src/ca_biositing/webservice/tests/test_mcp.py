import pytest
import json
from fastapi.testclient import TestClient
from ca_biositing.webservice.main import app

def parse_mcp_sse(text: str) -> dict:
    """Parse JSON-RPC response from MCP SSE stream."""
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    raise ValueError(f"No data found in SSE response: {text}")

def test_mcp_unified_smoke_test():
    """Verify MCP /mcp endpoint tool discovery and calling in a single session.

    We use a single TestClient context to avoid re-initializing the MCP session manager,
    which in mcp 1.30.0 cannot be restarted within the same process if it's a global instance.
    """
    with TestClient(app, base_url="http://localhost") as client:
        # Step 1: List tools
        # Note: In mcp 1.30.0 streamable_http_app mounted at /mcp usually exposes its handler at /mcp/mcp

        json_rpc_list = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        }

        headers = {"Accept": "application/json, text/event-stream"}

        response = client.post("/mcp/mcp", json=json_rpc_list, headers=headers)

        if response.status_code == 400 and "Missing session ID" in response.text:
            # Initialize session by GET-ing the endpoint first
            init_resp = client.get("/mcp/mcp", headers=headers)
            session_id = init_resp.headers.get("mcp-session-id")
            if session_id:
                headers["mcp-session-id"] = session_id
                response = client.post("/mcp/mcp", json=json_rpc_list, headers=headers)

        assert response.status_code == 200
        # MCP 1.x streamable HTTP responses are SSE-wrapped even for POSTs
        result_envelope = parse_mcp_sse(response.text)
        assert "result" in result_envelope
        tools = result_envelope["result"]["tools"]
        tool_names = [t["name"] for t in tools]

        assert "list_feedstock_resources" in tool_names
        assert "search_biositing_knowledge" in tool_names

        # Step 2: Call a tool
        json_rpc_call = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_feedstock_resources",
                "arguments": {},
            },
            "id": 2,
        }

        response = client.post("/mcp/mcp", json=json_rpc_call, headers=headers)
        assert response.status_code == 200
        result_envelope = parse_mcp_sse(response.text)
        assert "result" in result_envelope
        assert "content" in result_envelope["result"]
