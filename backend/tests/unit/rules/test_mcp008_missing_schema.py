"""Tests for MCP-008: Missing or malformed schema on required parameters."""
from app.rules.mcp008_missing_schema import MCP008MissingSchemaRule
from app.mcp_client.models import MCPTool, MCPSnapshot


class TestMCP008MissingSchema:
    rule = MCP008MissingSchemaRule()

    def test_required_param_no_type(self):
        """Required parameter lacks 'type' → finding."""
        tool = MCPTool(
            name="sloppy_tool",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"description": "The search query"},
                },
                "required": ["query"],
            },
        )
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 1
        assert findings[0]["rule_id"] == "MCP-008"
        assert "query" in findings[0]["description"]

    def test_all_params_typed(self):
        """All required params have types → no finding."""
        tool = MCPTool(
            name="typed_tool",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query", "limit"],
            },
        )
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 0

    def test_no_required(self):
        """Schema has no 'required' list → no finding (nothing to check)."""
        tool = MCPTool(
            name="no_required_tool",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"description": "The search query"},
                },
            },
        )
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 0
