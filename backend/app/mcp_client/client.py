"""
MCP enumeration client.

Connects to a target MCP server over stdio and enumerates its
tools, resources, and prompts via JSON-RPC. Never calls call_tool.

Uses direct asyncio subprocess communication to avoid the buggy
mcp.client.stdio.stdio_client (cancel-scope issue on CPython 3.13 + anyio).
"""
from __future__ import annotations

import asyncio
import json
import logging
from urllib.parse import urlparse

from app.mcp_client.models import MCPSnapshot, MCPTool, MCPResource, MCPPrompt

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Wraps MCP client errors (connection, protocol, timeout)."""


_REQUEST_ID = 0


def _next_id() -> int:
    global _REQUEST_ID
    _REQUEST_ID += 1
    return _REQUEST_ID


class MCPClient:
    """Enumerate-only MCP client.

    Connects via stdio, enumerates capabilities, and returns a
    typed MCPSnapshot. Never calls a target's tools.
    """

    def __init__(self) -> None:
        self._proc: asyncio.subprocess.Process | None = None
        self._connected = False

    async def connect_stdio(self, command: str, args: list[str] | None = None) -> None:
        """Connect to a stdio-based MCP server."""
        try:
            self._proc = await asyncio.create_subprocess_exec(
                command,
                *(args or []),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as e:
            raise MCPClientError(f"Command not found: {command}") from e

        # Initialize handshake
        result = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "mcp-scanner", "version": "0.1.0"},
        })
        if result is None:
            raise MCPClientError("Server closed during initialize")
        self._connected = True

        # Send initialized notification
        await self._send_notification("notifications/initialized")

    async def connect_http(self, url: str) -> None:
        """Connect to an HTTP-based MCP server."""
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise MCPClientError(f"Invalid URL: {url}")
        raise MCPClientError("HTTP transport not yet implemented")

    async def _send_request(self, method: str, params: dict | None = None) -> dict | None:
        """Send a JSON-RPC request and return the response result."""
        if self._proc is None or self._proc.stdout is None or self._proc.stdin is None:
            raise MCPClientError("Not connected")

        req_id = _next_id()
        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params:
            request["params"] = params

        line = json.dumps(request, ensure_ascii=False) + "\n"
        self._proc.stdin.write(line.encode("utf-8"))
        await self._proc.stdin.drain()

        response_line = await asyncio.wait_for(self._proc.stdout.readline(), timeout=30)
        if not response_line:
            return None

        response = json.loads(response_line)
        if "error" in response:
            err = response["error"]
            raise MCPClientError(f"RPC error ({err.get('code', '?')}): {err.get('message', '?')}")

        return response.get("result")

    async def _send_notification(self, method: str, params: dict | None = None) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if self._proc is None or self._proc.stdin is None:
            return
        notification = {"jsonrpc": "2.0", "method": method}
        if params:
            notification["params"] = params
        line = json.dumps(notification, ensure_ascii=False) + "\n"
        self._proc.stdin.write(line.encode("utf-8"))
        await self._proc.stdin.drain()

    async def enumerate(self) -> MCPSnapshot:
        """Enumerate all capabilities from the connected server.

        Returns a typed MCPSnapshot with tools, resources, and prompts.
        """
        if not self._connected:
            raise MCPClientError("Not connected. Call connect_stdio first.")

        try:
            tools_result = await self._send_request("tools/list")
            resources_result = await self._send_request("resources/list")
            prompts_result = await self._send_request("prompts/list")
        except Exception as e:
            raise MCPClientError(f"Enumeration failed: {e}") from e

        tools_raw = (tools_result or {}).get("tools", [])
        resources_raw = (resources_result or {}).get("resources", [])
        prompts_raw = (prompts_result or {}).get("prompts", [])

        return MCPSnapshot(
            tools=[MCPTool.from_raw(t) for t in tools_raw],
            resources=[MCPResource.from_raw(r) for r in resources_raw],
            prompts=[MCPPrompt.from_raw(p) for p in prompts_raw],
        )

    async def close(self) -> None:
        """Close the connection."""
        self._connected = False
        if self._proc is not None:
            try:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), timeout=5)
            except Exception:
                self._proc.kill()
                await self._proc.wait()
            self._proc = None
