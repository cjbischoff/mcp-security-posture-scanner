"""Tests for MCP-002: Unconstrained input schema on sensitive parameters."""
from app.rules.mcp002_unconstrained_schema import MCP002UnconstrainedSchemaRule
from app.mcp_client.models import MCPTool, MCPSnapshot


class TestMCP002UnconstrainedSchema:
    rule = MCP002UnconstrainedSchemaRule()

    def test_unconstrained_command(self):
        """'command' param without pattern/enum/maxLength → finding."""
        tool = MCPTool(
            name="executor",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                },
            },
        )
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 1
        assert findings[0]["rule_id"] == "MCP-002"
        assert "command" in findings[0]["description"]

    def test_constrained_param(self):
        """'command' param with pattern constraint → no finding."""
        tool = MCPTool(
            name="safe_executor",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "pattern": "^[a-zA-Z0-9_]+$"},
                },
            },
        )
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 0

    def test_sensitive_params_list(self):
        """'path', 'url', 'shell', 'exec' each trigger a finding individually."""
        tool = MCPTool(
            name="sensitive_tool",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "url": {"type": "string"},
                    "shell": {"type": "string"},
                    "exec": {"type": "string"},
                },
            },
        )
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 1
        desc = findings[0]["description"]
        for p in ("path", "url", "shell", "exec"):
            assert p in desc

    def test_no_sensitive_params(self):
        """Only 'text' param → no finding."""
        tool = MCPTool(
            name="text_tool",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
            },
        )
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 0
