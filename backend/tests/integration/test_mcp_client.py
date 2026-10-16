"""
Integration tests for MCP client — runs against the stub fixture MCP server.
"""
import sys
import pytest
from pathlib import Path

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "stub_mcp_server.py"


@pytest.mark.asyncio
async def test_enumerate_stub_server():
    """Spawn stub server, connect via stdio, enumerate all 3 types."""
    from app.mcp_client.client import MCPClient

    client = MCPClient()
    try:
        await client.connect_stdio(sys.executable, [str(FIXTURE_PATH)])
        snapshot = await client.enumerate()

        assert len(snapshot.tools) >= 2, "Expected at least 2 tools"
        assert len(snapshot.resources) >= 1, "Expected at least 1 resource"
        assert len(snapshot.prompts) >= 1, "Expected at least 1 prompt"

        tool_names = [t.name for t in snapshot.tools]
        assert "injected_tool" in tool_names
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_enumerate_returns_typed_snapshot():
    """Snapshot contains typed MCPTool, MCPResource, MCPPrompt objects."""
    from app.mcp_client.client import MCPClient
    from app.mcp_client.models import MCPTool, MCPResource, MCPPrompt

    client = MCPClient()
    try:
        await client.connect_stdio(sys.executable, [str(FIXTURE_PATH)])
        snapshot = await client.enumerate()

        assert all(isinstance(t, MCPTool) for t in snapshot.tools)
        assert all(isinstance(r, MCPResource) for r in snapshot.resources)
        assert all(isinstance(p, MCPPrompt) for p in snapshot.prompts)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_snapshot_contains_vulnerable_patterns():
    """Snapshot from stub server contains known vulnerable patterns."""
    from app.mcp_client.client import MCPClient

    client = MCPClient()
    try:
        await client.connect_stdio(sys.executable, [str(FIXTURE_PATH)])
        snapshot = await client.enumerate()

        # Find the injected_tool
        injected = next(t for t in snapshot.tools if t.name == "injected_tool")
        assert injected.description is not None

        # Must contain injection pattern markers
        assert "IMPORTANT" in injected.description
        assert "Ignore all previous instructions" in injected.description

        # Unconstrained schema — no pattern/format/enum on "command" param
        schema = injected.input_schema
        props = schema.get("properties", {})
        assert "command" in props
        cmd_schema = props["command"]
        # No pattern/format constraint
        assert "pattern" not in cmd_schema
        assert "enum" not in cmd_schema
    finally:
        await client.close()
