"""
Unit tests for MCP client — mock the SDK transport layer.
"""
import pytest
from app.mcp_client.models import MCPSnapshot, MCPTool, MCPResource, MCPPrompt, ToolAnnotations
from app.mcp_client.client import MCPClient, MCPClientError


class TestMCPSnapshot:
    def test_snapshot_creation(self):
        """MCPSnapshot can be created with typed fields."""
        tool = MCPTool(
            name="test-tool",
            description="a tool",
            input_schema={"type": "object"},
        )
        snapshot = MCPSnapshot(tools=[tool], resources=[], prompts=[])
        assert len(snapshot.tools) == 1
        assert snapshot.tools[0].name == "test-tool"

    def test_snapshot_empty(self):
        """All fields default to empty list."""
        snapshot = MCPSnapshot()
        assert snapshot.tools == []
        assert snapshot.resources == []
        assert snapshot.prompts == []


class TestMCPTool:
    def test_minimal(self):
        """Tool with only required fields."""
        tool = MCPTool(name="minimal", input_schema={"type": "object"})
        assert tool.name == "minimal"
        assert tool.input_schema == {"type": "object"}
        assert tool.description is None

    def test_full(self):
        """Tool with all optional fields."""
        tool = MCPTool(
            name="full",
            description="Full description here",
            input_schema={"type": "object", "properties": {"cmd": {"type": "string"}}},
            annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True),
        )
        assert tool.annotations is not None
        assert tool.annotations.destructive_hint is True

    def test_from_raw(self):
        """Converting from raw dict preserves fields."""
        raw = {
            "name": "raw_tool",
            "description": "Raw tool",
            "inputSchema": {"type": "object"},
            "annotations": {"readOnlyHint": True, "destructiveHint": False},
        }
        tool = MCPTool.from_raw(raw)
        assert tool.name == "raw_tool"
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True


class TestMCPResource:
    def test_minimal(self):
        """Resource with required fields only."""
        r = MCPResource(name="config", uri="file:///etc/config")
        assert r.name == "config"
        assert r.uri == "file:///etc/config"

    def test_wildcard_uri(self):
        """Resource with broad URI pattern."""
        r = MCPResource(name="wild", uri="file:///**", description="All files")
        assert "**" in r.uri


class TestMCPPrompt:
    def test_minimal(self):
        """Prompt with required fields only."""
        p = MCPPrompt(name="greet")
        assert p.name == "greet"
        assert p.description is None


class TestMCPClient:
    @pytest.mark.asyncio
    async def test_not_connected_raises(self):
        """Calling enumerate without connecting raises."""
        client = MCPClient()
        with pytest.raises(MCPClientError, match="Not connected"):
            await client.enumerate()

    @pytest.mark.asyncio
    async def test_connect_http_invalid_url(self):
        """HTTP connect with invalid URL raises."""
        client = MCPClient()
        with pytest.raises(MCPClientError, match="Invalid URL"):
            await client.connect_http("not-a-url")
