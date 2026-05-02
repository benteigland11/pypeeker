from __future__ import annotations

from pathlib import Path
import sys
import textwrap
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.mcp_client import McpClient
from src.mcp_client import McpMethodNotFoundError
from src.mcp_client import McpProtocolError
from src.mcp_client import McpServerConfig
from src.mcp_client import McpStdioServerSpec
from src.mcp_client import McpStdioSession
from src.mcp_client import McpStdioSessionManager
from src.mcp_client import McpTransportError
from src.mcp_client import build_initialize_request
from src.mcp_client import build_tool_call_request
from src.mcp_client import parse_jsonrpc_response
from src.mcp_client import parse_prompt_list
from src.mcp_client import parse_resource_list


def test_build_initialize_request_contains_client_info() -> None:
    request = build_initialize_request(
        client_name="example-client",
        client_version="1.2.3",
        capabilities={"roots": {"listChanged": True}},
    )

    assert request.method == "initialize"
    assert request.params == {
        "protocolVersion": "2025-03-26",
        "capabilities": {"roots": {"listChanged": True}},
        "clientInfo": {
            "name": "example-client",
            "version": "1.2.3",
        },
    }


def test_build_tool_call_request_contains_arguments() -> None:
    request = build_tool_call_request(name="search_documents", arguments={"query": "widgets"})

    assert request.as_dict()["params"] == {
        "name": "search_documents",
        "arguments": {"query": "widgets"},
    }


def test_parse_jsonrpc_response_handles_error_payload() -> None:
    response = parse_jsonrpc_response(
        {
            "jsonrpc": "2.0",
            "id": "request-1",
            "error": {"code": -32001, "message": "not allowed"},
        }
    )

    assert response.is_error is True
    assert response.error is not None
    assert response.error.code == -32001
    assert response.error.message == "not allowed"


def test_client_lists_tools_from_fake_transport() -> None:
    seen_payloads: list[dict[str, object]] = []

    def fake_transport(server: McpServerConfig, payload: dict[str, object]) -> dict[str, object]:
        seen_payloads.append(payload)
        assert server.name == "example-server"
        return {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "result": {
                "tools": [
                    {
                        "name": "search_documents",
                        "description": "Search documents by query",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                        },
                    }
                ]
            },
        }

    client = McpClient(
        McpServerConfig(name="example-server", url="https://example.com/mcp"),
        transport=fake_transport,
    )

    tools = client.list_tools()

    assert len(tools) == 1
    assert tools[0].name == "search_documents"
    assert tools[0].description == "Search documents by query"
    assert seen_payloads[0]["method"] == "tools/list"


def test_client_passes_arguments_when_calling_tool() -> None:
    def fake_transport(server: McpServerConfig, payload: dict[str, object]) -> dict[str, object]:
        assert server.headers == {"Authorization": "Bearer token"}
        assert payload["method"] == "tools/call"
        assert payload["params"] == {
            "name": "search_documents",
            "arguments": {"query": "mcp"},
        }
        return {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "result": {
                "content": [{"type": "text", "text": "match"}],
            },
        }

    client = McpClient(
        McpServerConfig(
            name="example-server",
            url="https://example.com/mcp",
            headers={"Authorization": "Bearer token"},
        ),
        transport=fake_transport,
    )

    result = client.call_tool(name="search_documents", arguments={"query": "mcp"})

    assert result == {"content": [{"type": "text", "text": "match"}]}


def test_client_raises_on_jsonrpc_error() -> None:
    def fake_transport(server: McpServerConfig, payload: dict[str, object]) -> dict[str, object]:
        return {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "error": {"code": -32002, "message": "Tool execution failed"},
        }

    client = McpClient(
        McpServerConfig(name="example-server", url="https://example.com/mcp"),
        transport=fake_transport,
    )

    try:
        client.call_tool(name="search_documents")
    except McpProtocolError as exc:
        assert "Tool execution failed" in str(exc)
    else:
        raise AssertionError("Expected McpProtocolError")


def test_client_raises_method_not_found_error_for_unsupported_method() -> None:
    def fake_transport(server: McpServerConfig, payload: dict[str, object]) -> dict[str, object]:
        return {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "error": {"code": -32601, "message": "Method not found: resources/list"},
        }

    client = McpClient(
        McpServerConfig(name="example-server", url="https://example.com/mcp"),
        transport=fake_transport,
    )

    try:
        client.list_resources()
    except McpMethodNotFoundError as exc:
        assert exc.method == "resources/list"
        assert exc.code == -32601
    else:
        raise AssertionError("Expected McpMethodNotFoundError")


def test_client_initializes_lists_resources_and_gets_prompts() -> None:
    def fake_transport(server: McpServerConfig, payload: dict[str, object]) -> dict[str, object]:
        method = payload["method"]
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {"serverInfo": {"name": server.name, "version": "1.0.0"}},
            }
        if method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "resources": [
                        {
                            "uri": "file:///example.txt",
                            "name": "example.txt",
                            "description": "Example file",
                            "mimeType": "text/plain",
                        }
                    ]
                },
            }
        if method == "resources/read":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {"contents": [{"uri": "file:///example.txt", "text": "hello"}]},
            }
        if method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "prompts": [
                        {
                            "name": "summarize",
                            "description": "Summarize content",
                            "arguments": [{"name": "text", "required": True}],
                        }
                    ]
                },
            }
        if method == "prompts/get":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {"messages": [{"role": "user", "content": "Summarize this"}]},
            }
        raise AssertionError(f"Unexpected method: {method}")

    client = McpClient(
        McpServerConfig(name="example-server", url="https://example.com/mcp"),
        transport=fake_transport,
    )

    initialized = client.initialize(client_name="example-client", client_version="1.0.0")
    resources = client.list_resources()
    read_result = client.read_resource(uri="file:///example.txt")
    prompts = client.list_prompts()
    prompt_result = client.get_prompt(name="summarize", arguments={"text": "hello"})

    assert initialized["serverInfo"]["name"] == "example-server"
    assert resources[0].uri == "file:///example.txt"
    assert resources[0].mime_type == "text/plain"
    assert read_result["contents"][0]["text"] == "hello"
    assert prompts[0].arguments[0].name == "text"
    assert prompts[0].arguments[0].required is True
    assert prompt_result["messages"][0]["role"] == "user"


def test_stdio_session_initializes_and_lists_tools() -> None:
    server_script = textwrap.dedent(
        """
        import json
        import sys

        initialized = False
        for line in sys.stdin:
            payload = json.loads(line)
            method = payload.get("method")
            if method == "initialize":
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {"serverInfo": {"name": "example-stdio", "version": "1.0.0"}},
                }), flush=True)
            elif method == "notifications/initialized":
                initialized = True
            elif method == "tools/list" and initialized:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {"tools": [{"name": "search", "description": "Search items"}]},
                }), flush=True)
            else:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }), flush=True)
        """
    )

    with McpStdioSession(
        (sys.executable, "-u", "-c", server_script),
        name="example-stdio",
        timeout_seconds=2,
    ) as session:
        initialized = session.initialize(client_name="example-client", client_version="1.0.0")
        tools = session.client.list_tools()

    assert initialized["serverInfo"]["name"] == "example-stdio"
    assert len(tools) == 1
    assert tools[0].name == "search"
    assert tools[0].description == "Search items"


class _FakeManagedSession:
    instances: list["_FakeManagedSession"] = []

    def __init__(self, server: McpStdioServerSpec) -> None:
        self.server = server
        self.initialized = 0
        self.closed = False
        self.client = self
        self.calls: list[dict[str, object]] = []
        _FakeManagedSession.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def initialize(self, *, client_name: str, client_version: str) -> None:
        self.initialized += 1

    def call_tool(self, *, name: str, arguments: dict[str, object] | None = None) -> dict[str, object]:
        self.calls.append({"name": name, "arguments": dict(arguments or {})})
        return {"name": name, "arguments": dict(arguments or {})}

    def close(self) -> None:
        self.closed = True


def test_stdio_session_manager_uses_fresh_session_for_per_call_mode() -> None:
    _FakeManagedSession.instances = []
    server = McpStdioServerSpec(
        server_id="example",
        command="example-mcp",
        session_mode="per_call",
    )
    manager = McpStdioSessionManager(session_factory=lambda spec: _FakeManagedSession(spec))

    manager.call_tool(server, "search", {"query": "a"})
    manager.call_tool(server, "search", {"query": "b"})

    assert len(_FakeManagedSession.instances) == 2
    assert [session.initialized for session in _FakeManagedSession.instances] == [1, 1]


def test_stdio_session_manager_reuses_persistent_session() -> None:
    _FakeManagedSession.instances = []
    server = McpStdioServerSpec(
        server_id="stateful",
        command="stateful-mcp",
        session_mode="persistent",
    )
    manager = McpStdioSessionManager(session_factory=lambda spec: _FakeManagedSession(spec))

    manager.call_tool(server, "remember", {"value": "a"})
    manager.call_tool(server, "remember", {"value": "b"})

    assert len(_FakeManagedSession.instances) == 1
    assert _FakeManagedSession.instances[0].initialized == 1
    assert _FakeManagedSession.instances[0].calls == [
        {"name": "remember", "arguments": {"value": "a"}},
        {"name": "remember", "arguments": {"value": "b"}},
    ]

    manager.close_all()

    assert _FakeManagedSession.instances[0].closed is True


def test_parse_resource_and_prompt_lists_validate_shapes() -> None:
    resources = parse_resource_list(
        {
            "resources": [
                {
                    "uri": "file:///notes.md",
                    "name": "notes.md",
                    "description": "Notes",
                    "mimeType": "text/markdown",
                    "annotations": {"source": "workspace"},
                }
            ]
        }
    )
    prompts = parse_prompt_list(
        {
            "prompts": [
                {
                    "name": "plan",
                    "description": "Build a plan",
                    "arguments": [{"name": "goal", "description": "User goal", "required": False}],
                }
            ]
        }
    )

    assert resources[0].annotations["source"] == "workspace"
    assert prompts[0].description == "Build a plan"
    assert prompts[0].arguments[0].description == "User goal"


def test_parse_jsonrpc_response_rejects_invalid_shape() -> None:
    try:
        parse_jsonrpc_response({"jsonrpc": "2.0", "result": {}})
    except McpProtocolError as exc:
        assert "missing an id" in str(exc)
    else:
        raise AssertionError("Expected McpProtocolError")


def test_default_transport_wraps_url_errors(monkeypatch) -> None:
    def raising_urlopen(request, timeout):
        raise URLError("offline")

    monkeypatch.setattr("src.mcp_client.urlopen", raising_urlopen)
    client = McpClient(McpServerConfig(name="example-server", url="https://example.com/mcp"))

    try:
        client.list_tools()
    except McpTransportError as exc:
        assert "Unable to reach MCP server" in str(exc)
    else:
        raise AssertionError("Expected McpTransportError")
