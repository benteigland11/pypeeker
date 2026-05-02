"""
Example usage of the generic MCP client with a fake transport.

This example intentionally avoids real network calls. It demonstrates how a
consumer can inject headers, initialize a server, inspect tools, and call one
tool through the same client surface.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.mcp_client import McpClient
from src.mcp_client import McpServerConfig


def fake_transport(server: McpServerConfig, payload: dict[str, object]) -> dict[str, object]:
    method = payload["method"]
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "result": {
                "protocolVersion": "2025-03-26",
                "serverInfo": {"name": server.name, "version": "2026.04"},
                "capabilities": {"tools": {}, "resources": {}},
            },
        }
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "result": {
                "tools": [
                    {
                        "name": "search_documents",
                        "description": "Search a document index",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    }
                ]
            },
        }
    if method == "tools/call":
        params = dict(payload["params"])  # type: ignore[arg-type]
        return {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"Results for {params['arguments']['query']!r}",
                    }
                ],
            },
        }
    raise AssertionError(f"Unexpected method: {method}")


client = McpClient(
    McpServerConfig(
        name="example-mcp",
        url="https://example.invalid/mcp",
        headers={"Authorization": "Bearer example-token"},
    ),
    transport=fake_transport,
)

initialized = client.initialize(client_name="example-client", client_version="1.0.0")
tools = client.list_tools()
result = client.call_tool(name="search_documents", arguments={"query": "widgets"})

print(initialized["serverInfo"]["name"])
print(tools[0].name)
print(result["content"][0]["text"])
