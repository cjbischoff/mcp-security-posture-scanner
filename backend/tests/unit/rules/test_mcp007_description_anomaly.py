"""Tests for MCP-007: Tool description length/entropy anomaly."""
from app.rules.mcp007_description_anomaly import MCP007DescriptionAnomalyRule
from app.mcp_client.models import MCPTool, MCPSnapshot


class TestMCP007DescriptionAnomaly:
    rule = MCP007DescriptionAnomalyRule()

    def test_long_description(self):
        """Description > 2000 chars → finding."""
        tool = MCPTool(
            name="verbose_tool",
            description="x" * 2001,
            input_schema={},
        )
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 1
        assert "length 2001" in findings[0]["description"]

    def test_high_entropy(self):
        """Random-looking high-entropy description → finding."""
        # Mix of lowercase, digits, and symbols yields Shannon entropy > 5.5
        tool = MCPTool(
            name="random_tool",
            description="xj9k!q2m@4p#r7t%v8w&y1z*a3b5c6d8e0f/h?g:i;j<l>n,o.s_u~x" * 4,
            input_schema={},
        )
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 1
        assert "entropy" in findings[0]["description"]

    def test_normal_description(self):
        """Short English description → no finding."""
        tool = MCPTool(
            name="normal_tool",
            description="Lists all files in the current directory.",
            input_schema={},
        )
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 0

    def test_empty_description(self):
        """None description → no finding (entropy 0, length 0)."""
        tool = MCPTool(name="null_desc_tool", description=None, input_schema={})
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 0
