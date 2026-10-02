"""Client for calling biocirv-kb MCP tools via streamable HTTP.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def call_kb_tool(
    tool_name: str,
    arguments: dict[str, Any],
    kb_url: str,
    kb_api_key: str | None = None,
) -> dict[str, Any]:
    """Call a tool on the biocirv-kb MCP server.

    Args:
        tool_name: Name of the tool to call (e.g., "search_corpus")
        arguments: Arguments for the tool
        kb_url: Base URL of the KB MCP endpoint (e.g., "https://.../mcp")
        kb_api_key: Optional API key for authentication

    Returns:
        The tool result as a dictionary

    Raises:
        httpx.HTTPStatusError: If the request fails
    """
    headers = {}
    if kb_api_key:
        headers["Authorization"] = f"Bearer {kb_api_key}"

    json_rpc_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
        "id": 1,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(kb_url, json=json_rpc_request, headers=headers)
        response.raise_for_status()
        result = response.json()

    if "error" in result:
        logger.error(f"Error calling KB tool {tool_name}: {result['error']}")
        return {"error": result["error"]}

    # The result field in the JSON-RPC response contains the actual tool output
    # For MCP tools, this is usually a dict with a "content" list.
    return result.get("result", {})
