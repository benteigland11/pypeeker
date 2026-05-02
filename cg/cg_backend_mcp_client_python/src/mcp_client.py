from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import itertools
import json
import queue
import subprocess
import threading
import time
from typing import Any
from typing import Callable
from typing import Sequence
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen


JsonObject = dict[str, Any]
TransportHandler = Callable[["McpServerConfig", JsonObject], JsonObject]
PopenFactory = Callable[..., subprocess.Popen]


class McpClientError(Exception):
    """Base exception for generic MCP client failures."""


class McpTransportError(McpClientError):
    """Raised when the transport layer cannot reach or parse a response."""


class McpProtocolError(McpClientError):
    """Raised when an MCP server returns malformed JSON-RPC data."""


class McpMethodNotFoundError(McpProtocolError):
    """Raised when an MCP server does not implement a requested method."""

    def __init__(self, method: str, message: str, *, code: int = -32601) -> None:
        super().__init__(f"MCP method '{method}' failed: {code} {message}")
        self.method = method
        self.code = code
        self.rpc_message = message


@dataclass(frozen=True)
class McpServerConfig:
    """Connection details for an MCP server transport."""

    name: str
    url: str
    transport: str = "streamable_http"
    headers: dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class McpJsonRpcRequest:
    """A JSON-RPC request payload used by the MCP client."""

    request_id: str
    method: str
    params: JsonObject | None = None
    jsonrpc: str = "2.0"

    def as_dict(self) -> JsonObject:
        payload: JsonObject = {
            "jsonrpc": self.jsonrpc,
            "id": self.request_id,
            "method": self.method,
        }
        if self.params is not None:
            payload["params"] = self.params
        return payload


@dataclass(frozen=True)
class McpJsonRpcError:
    """Structured JSON-RPC error payload."""

    code: int
    message: str
    data: Any = None


@dataclass(frozen=True)
class McpJsonRpcResponse:
    """Validated JSON-RPC response payload."""

    request_id: str | int | None
    result: Any = None
    error: McpJsonRpcError | None = None
    jsonrpc: str = "2.0"

    @property
    def is_error(self) -> bool:
        return self.error is not None


@dataclass(frozen=True)
class McpToolDefinition:
    """Canonical MCP tool description."""

    name: str
    description: str = ""
    input_schema: JsonObject = field(default_factory=dict)
    annotations: JsonObject = field(default_factory=dict)


@dataclass(frozen=True)
class McpResourceDefinition:
    """Canonical MCP resource description."""

    uri: str
    name: str = ""
    description: str = ""
    mime_type: str | None = None
    annotations: JsonObject = field(default_factory=dict)


@dataclass(frozen=True)
class McpPromptArgument:
    """Argument metadata for an MCP prompt."""

    name: str
    description: str = ""
    required: bool = False


@dataclass(frozen=True)
class McpPromptDefinition:
    """Canonical MCP prompt description."""

    name: str
    description: str = ""
    arguments: tuple[McpPromptArgument, ...] = ()


def build_initialize_request(
    *,
    request_id: str = "initialize-1",
    client_name: str,
    client_version: str,
    protocol_version: str = "2025-03-26",
    capabilities: JsonObject | None = None,
) -> McpJsonRpcRequest:
    return McpJsonRpcRequest(
        request_id=request_id,
        method="initialize",
        params={
            "protocolVersion": protocol_version,
            "capabilities": capabilities or {},
            "clientInfo": {
                "name": client_name,
                "version": client_version,
            },
        },
    )


def build_initialized_notification() -> JsonObject:
    return {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
    }


def build_tools_list_request(*, request_id: str = "tools-list-1", cursor: str | None = None) -> McpJsonRpcRequest:
    params = {"cursor": cursor} if cursor else None
    return McpJsonRpcRequest(request_id=request_id, method="tools/list", params=params)


def build_resources_list_request(
    *,
    request_id: str = "resources-list-1",
    cursor: str | None = None,
) -> McpJsonRpcRequest:
    params = {"cursor": cursor} if cursor else None
    return McpJsonRpcRequest(request_id=request_id, method="resources/list", params=params)


def build_prompts_list_request(*, request_id: str = "prompts-list-1", cursor: str | None = None) -> McpJsonRpcRequest:
    params = {"cursor": cursor} if cursor else None
    return McpJsonRpcRequest(request_id=request_id, method="prompts/list", params=params)


def build_tool_call_request(
    *,
    request_id: str = "tool-call-1",
    name: str,
    arguments: JsonObject | None = None,
) -> McpJsonRpcRequest:
    return McpJsonRpcRequest(
        request_id=request_id,
        method="tools/call",
        params={
            "name": name,
            "arguments": arguments or {},
        },
    )


def build_resource_read_request(*, request_id: str = "resource-read-1", uri: str) -> McpJsonRpcRequest:
    return McpJsonRpcRequest(
        request_id=request_id,
        method="resources/read",
        params={"uri": uri},
    )


def build_prompt_get_request(
    *,
    request_id: str = "prompt-get-1",
    name: str,
    arguments: JsonObject | None = None,
) -> McpJsonRpcRequest:
    return McpJsonRpcRequest(
        request_id=request_id,
        method="prompts/get",
        params={
            "name": name,
            "arguments": arguments or {},
        },
    )


def parse_jsonrpc_response(payload: JsonObject) -> McpJsonRpcResponse:
    if not isinstance(payload, dict):
        raise McpProtocolError("JSON-RPC response must be an object.")
    if payload.get("jsonrpc") != "2.0":
        raise McpProtocolError("JSON-RPC response must declare jsonrpc='2.0'.")
    if "id" not in payload:
        raise McpProtocolError("JSON-RPC response is missing an id.")

    error_payload = payload.get("error")
    error = None
    if error_payload is not None:
        if not isinstance(error_payload, dict):
            raise McpProtocolError("JSON-RPC error payload must be an object.")
        error = McpJsonRpcError(
            code=int(error_payload.get("code", -32000)),
            message=str(error_payload.get("message", "Unknown JSON-RPC error")),
            data=error_payload.get("data"),
        )

    return McpJsonRpcResponse(
        request_id=payload.get("id"),
        result=payload.get("result"),
        error=error,
    )


def parse_tool_list(result: JsonObject | None) -> tuple[McpToolDefinition, ...]:
    tools = (result or {}).get("tools", [])
    if not isinstance(tools, list):
        raise McpProtocolError("tools/list result must contain a list under 'tools'.")
    return tuple(
        McpToolDefinition(
            name=str(item.get("name", "")),
            description=str(item.get("description", "")),
            input_schema=dict(item.get("inputSchema", {}) or {}),
            annotations=dict(item.get("annotations", {}) or {}),
        )
        for item in tools
        if isinstance(item, dict)
    )


def parse_resource_list(result: JsonObject | None) -> tuple[McpResourceDefinition, ...]:
    resources = (result or {}).get("resources", [])
    if not isinstance(resources, list):
        raise McpProtocolError("resources/list result must contain a list under 'resources'.")
    return tuple(
        McpResourceDefinition(
            uri=str(item.get("uri", "")),
            name=str(item.get("name", "")),
            description=str(item.get("description", "")),
            mime_type=str(item["mimeType"]) if item.get("mimeType") is not None else None,
            annotations=dict(item.get("annotations", {}) or {}),
        )
        for item in resources
        if isinstance(item, dict)
    )


def parse_prompt_list(result: JsonObject | None) -> tuple[McpPromptDefinition, ...]:
    prompts = (result or {}).get("prompts", [])
    if not isinstance(prompts, list):
        raise McpProtocolError("prompts/list result must contain a list under 'prompts'.")
    parsed_prompts: list[McpPromptDefinition] = []
    for item in prompts:
        if not isinstance(item, dict):
            continue
        arguments = tuple(
            McpPromptArgument(
                name=str(argument.get("name", "")),
                description=str(argument.get("description", "")),
                required=bool(argument.get("required", False)),
            )
            for argument in item.get("arguments", []) or []
            if isinstance(argument, dict)
        )
        parsed_prompts.append(
            McpPromptDefinition(
                name=str(item.get("name", "")),
                description=str(item.get("description", "")),
                arguments=arguments,
            )
        )
    return tuple(parsed_prompts)


class McpClient:
    """Generic JSON-RPC MCP client with injectable transport."""

    def __init__(
        self,
        server: McpServerConfig,
        *,
        transport: TransportHandler | None = None,
    ) -> None:
        self._server = server
        self._transport = transport or _default_http_transport
        self._request_counter = itertools.count(1)

    @property
    def server(self) -> McpServerConfig:
        return self._server

    def call(self, request: McpJsonRpcRequest) -> McpJsonRpcResponse:
        raw_response = self._transport(self._server, request.as_dict())
        response = parse_jsonrpc_response(raw_response)
        if response.is_error:
            assert response.error is not None
            if response.error.code == -32601:
                raise McpMethodNotFoundError(request.method, response.error.message, code=response.error.code)
            raise McpProtocolError(
                f"MCP method '{request.method}' failed: {response.error.code} {response.error.message}"
            )
        return response

    def initialize(
        self,
        *,
        client_name: str,
        client_version: str,
        protocol_version: str = "2025-03-26",
        capabilities: JsonObject | None = None,
    ) -> JsonObject:
        request = build_initialize_request(
            request_id=self._next_request_id("initialize"),
            client_name=client_name,
            client_version=client_version,
            protocol_version=protocol_version,
            capabilities=capabilities,
        )
        return dict(self.call(request).result or {})

    def list_tools(self, *, cursor: str | None = None) -> tuple[McpToolDefinition, ...]:
        request = build_tools_list_request(
            request_id=self._next_request_id("tools-list"),
            cursor=cursor,
        )
        return parse_tool_list(self.call(request).result)

    def list_resources(self, *, cursor: str | None = None) -> tuple[McpResourceDefinition, ...]:
        request = build_resources_list_request(
            request_id=self._next_request_id("resources-list"),
            cursor=cursor,
        )
        return parse_resource_list(self.call(request).result)

    def list_prompts(self, *, cursor: str | None = None) -> tuple[McpPromptDefinition, ...]:
        request = build_prompts_list_request(
            request_id=self._next_request_id("prompts-list"),
            cursor=cursor,
        )
        return parse_prompt_list(self.call(request).result)

    def call_tool(self, *, name: str, arguments: JsonObject | None = None) -> JsonObject:
        request = build_tool_call_request(
            request_id=self._next_request_id("tool-call"),
            name=name,
            arguments=arguments,
        )
        return dict(self.call(request).result or {})

    def read_resource(self, *, uri: str) -> JsonObject:
        request = build_resource_read_request(
            request_id=self._next_request_id("resource-read"),
            uri=uri,
        )
        return dict(self.call(request).result or {})

    def get_prompt(self, *, name: str, arguments: JsonObject | None = None) -> JsonObject:
        request = build_prompt_get_request(
            request_id=self._next_request_id("prompt-get"),
            name=name,
            arguments=arguments,
        )
        return dict(self.call(request).result or {})

    def _next_request_id(self, prefix: str) -> str:
        return f"{prefix}-{next(self._request_counter)}"


class McpStdioSession:
    """Stateful JSON-RPC transport for MCP servers launched over stdio."""

    def __init__(
        self,
        command: str | Sequence[str],
        *,
        args: Sequence[str] = (),
        name: str = "stdio-mcp-server",
        timeout_seconds: float = 30.0,
        popen_factory: PopenFactory = subprocess.Popen,
    ) -> None:
        self._command = (command,) if isinstance(command, str) else tuple(command)
        self._args = tuple(args)
        self._name = name
        self._timeout_seconds = timeout_seconds
        self._popen_factory = popen_factory
        self._process: subprocess.Popen | None = None
        self._responses: queue.Queue[JsonObject | Exception] = queue.Queue()
        self._reader_thread: threading.Thread | None = None
        self._client: McpClient | None = None
        self._closed = False

    def __enter__(self) -> "McpStdioSession":
        return self.start()

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    @property
    def client(self) -> McpClient:
        if self._client is None:
            raise McpTransportError("MCP stdio session has not been started.")
        return self._client

    def start(self) -> "McpStdioSession":
        if self._process is not None:
            return self
        argv = [*self._command, *self._args]
        if not argv:
            raise McpTransportError("MCP stdio command must not be empty.")
        try:
            self._process = self._popen_factory(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise McpTransportError(f"Unable to launch MCP stdio server: {exc}") from exc
        self._reader_thread = threading.Thread(target=self._read_stdout_loop, daemon=True)
        self._reader_thread.start()
        server = McpServerConfig(
            name=self._name,
            url="",
            transport="stdio",
            timeout_seconds=self._timeout_seconds,
        )
        self._client = McpClient(server, transport=self.request)
        return self

    def initialize(
        self,
        *,
        client_name: str,
        client_version: str,
        protocol_version: str = "2025-03-26",
        capabilities: JsonObject | None = None,
    ) -> JsonObject:
        result = self.client.initialize(
            client_name=client_name,
            client_version=client_version,
            protocol_version=protocol_version,
            capabilities=capabilities,
        )
        self.notify(build_initialized_notification())
        return result

    def request(self, server: McpServerConfig, payload: JsonObject) -> JsonObject:
        if self._process is None:
            raise McpTransportError("MCP stdio session has not been started.")
        request_id = payload.get("id")
        if request_id is None:
            raise McpProtocolError("MCP stdio requests must include an id.")
        self._write_payload(payload)
        deadline = time.monotonic() + server.timeout_seconds
        unmatched: list[JsonObject] = []
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise McpTransportError(f"Timed out waiting for MCP stdio response to {request_id}.")
                try:
                    response = self._responses.get(timeout=remaining)
                except queue.Empty as exc:
                    raise McpTransportError(f"Timed out waiting for MCP stdio response to {request_id}.") from exc
                if isinstance(response, Exception):
                    raise response
                if response.get("id") == request_id:
                    return response
                if "id" in response:
                    unmatched.append(response)
        finally:
            for response in unmatched:
                self._responses.put(response)

    def notify(self, payload: JsonObject) -> None:
        self._write_payload(payload)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        process = self._process
        if process is None:
            return
        try:
            if process.stdin is not None:
                process.stdin.close()
        except OSError:
            pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)

    def _write_payload(self, payload: JsonObject) -> None:
        if self._process is None or self._process.stdin is None:
            raise McpTransportError("MCP stdio process is not writable.")
        try:
            self._process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
            self._process.stdin.flush()
        except OSError as exc:
            raise McpTransportError(f"Failed to write MCP stdio request: {exc}") from exc

    def _read_stdout_loop(self) -> None:
        assert self._process is not None
        stdout = self._process.stdout
        if stdout is None:
            self._responses.put(McpTransportError("MCP stdio process has no stdout."))
            return
        try:
            for line in stdout:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    self._responses.put(McpTransportError("MCP stdio server returned invalid JSON."))
                    continue
                if not isinstance(parsed, dict):
                    self._responses.put(McpTransportError("MCP stdio server returned a non-object JSON payload."))
                    continue
                self._responses.put(parsed)
        finally:
            process = self._process
            if process is not None and process.poll() not in (None, 0):
                self._responses.put(McpTransportError(f"MCP stdio server exited with code {process.poll()}."))


@dataclass(frozen=True)
class McpStdioServerSpec:
    """Launch and lifecycle settings for a stdio MCP server."""

    server_id: str
    command: str
    args: tuple[str, ...] = ()
    name: str = "stdio-mcp-server"
    timeout_seconds: float = 30.0
    session_mode: str = "per_call"


class McpStdioSessionManager:
    """Manage per-call or persistent stdio MCP sessions."""

    def __init__(
        self,
        *,
        session_factory: Callable[[McpStdioServerSpec], object] | None = None,
        client_name: str = "mcp-client",
        client_version: str = "0.1.0",
    ) -> None:
        self._session_factory = session_factory or self._default_session_factory
        self._client_name = client_name
        self._client_version = client_version
        self._persistent_sessions: dict[str, object] = {}

    def call_tool(self, server: McpStdioServerSpec, tool_name: str, arguments: JsonObject | None = None) -> JsonObject:
        mode = server.session_mode.strip().lower()
        if mode == "persistent":
            session = self._persistent_session(server)
            return dict(session.client.call_tool(name=tool_name, arguments=dict(arguments or {})))
        if mode in {"per_call", "fresh", ""}:
            with self._session_factory(server) as session:
                self._initialize(session)
                return dict(session.client.call_tool(name=tool_name, arguments=dict(arguments or {})))
        raise McpTransportError(f"Unsupported MCP stdio session mode: {server.session_mode}")

    def close_server(self, server_id: str) -> None:
        session = self._persistent_sessions.pop(server_id, None)
        if session is None:
            return
        close = getattr(session, "close", None)
        if callable(close):
            close()

    def close_all(self) -> None:
        for server_id in tuple(self._persistent_sessions):
            self.close_server(server_id)

    def _persistent_session(self, server: McpStdioServerSpec):
        session = self._persistent_sessions.get(server.server_id)
        if session is not None:
            return session
        session = self._session_factory(server)
        enter = getattr(session, "__enter__", None)
        if callable(enter):
            session = enter()
        self._initialize(session)
        self._persistent_sessions[server.server_id] = session
        return session

    def _initialize(self, session: object) -> None:
        initialize = getattr(session, "initialize", None)
        if not callable(initialize):
            raise McpTransportError("MCP stdio session does not expose initialize().")
        initialize(client_name=self._client_name, client_version=self._client_version)

    @staticmethod
    def _default_session_factory(server: McpStdioServerSpec) -> McpStdioSession:
        return McpStdioSession(
            server.command,
            args=server.args,
            name=server.name,
            timeout_seconds=server.timeout_seconds,
        )


def _default_http_transport(server: McpServerConfig, payload: JsonObject) -> JsonObject:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        **server.headers,
    }
    request = Request(server.url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=server.timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise McpTransportError(f"HTTP error from MCP server: {exc.code}") from exc
    except URLError as exc:
        raise McpTransportError(f"Unable to reach MCP server: {exc.reason}") from exc

    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise McpTransportError("MCP server returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise McpTransportError("MCP server returned a non-object JSON payload.")
    return parsed
