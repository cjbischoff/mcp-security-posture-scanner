"""
Tests for MCP-005: Unauthenticated HTTP transport.

Note: This rule is a placeholder until Plan 1.4 provides transport context.
For now it always returns empty.
"""
from app.rules.mcp005_unauthenticated import MCP005UnauthenticatedRule
from app.mcp_client.models import MCPTool, MCPSnapshot


class TestMCP005Unauthenticated:
    rule = MCP005UnauthenticatedRule()

    def test_placeholder_returns_empty(self):
        """Snapshot-only check returns no findings (transport context comes from scan service)."""
        snapshot = MCPSnapshot()
        findings = self.rule.check(snapshot)
        assert len(findings) == 0

    def test_with_tools_still_empty(self):
        """Even with tools present, snapshot-only check returns empty."""
        tool = MCPTool(name="test", input_schema={"type": "object"})
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 0
