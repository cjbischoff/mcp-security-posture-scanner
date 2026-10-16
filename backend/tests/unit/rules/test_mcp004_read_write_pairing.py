"""
Tests for MCP-004: Read + write capability pairing.
"""
from app.rules.mcp004_read_write_pairing import MCP004ReadWritePairingRule
from app.mcp_client.models import MCPTool, MCPSnapshot


class TestMCP004ReadWritePairing:
    rule = MCP004ReadWritePairingRule()

    def test_both_present(self):
        """One tool with read param, another with write param → finding."""
        read_tool = MCPTool(name="reader", input_schema={
            "type": "object",
            "properties": {"source_path": {"type": "string"}},
        })
        write_tool = MCPTool(name="writer", input_schema={
            "type": "object",
            "properties": {"target_url": {"type": "string"}},
        })
        snapshot = MCPSnapshot(tools=[read_tool, write_tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 1
        assert findings[0]["rule_id"] == "MCP-004"

    def test_read_only(self):
        """Only read params → no finding."""
        tools = [
            MCPTool(name="reader", input_schema={
                "type": "object",
                "properties": {"source_path": {"type": "string"}},
            }),
        ]
        findings = self.rule.check(MCPSnapshot(tools=tools))
        assert len(findings) == 0

    def test_write_only(self):
        """Only write params → no finding."""
        tools = [
            MCPTool(name="sender", input_schema={
                "type": "object",
                "properties": {"target_url": {"type": "string"}},
            }),
        ]
        findings = self.rule.check(MCPSnapshot(tools=tools))
        assert len(findings) == 0

    def test_neither(self):
        """No read or write params → no finding."""
        tools = [
            MCPTool(name="echo", input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
            }),
        ]
        findings = self.rule.check(MCPSnapshot(tools=tools))
        assert len(findings) == 0
