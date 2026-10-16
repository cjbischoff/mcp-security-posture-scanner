"""Tests for MCP-003: Missing readOnlyHint/destructiveHint annotations."""
from app.rules.mcp003_missing_annotations import MCP003MissingAnnotationsRule
from app.mcp_client.models import MCPTool, MCPSnapshot, ToolAnnotations


class TestMCP003MissingAnnotations:
    rule = MCP003MissingAnnotationsRule()

    def test_no_annotations(self):
        """Tool with annotations=None → finding for both hints."""
        tool = MCPTool(
            name="unannotated_tool",
            input_schema={},
            annotations=None,
        )
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 1
        assert "readOnlyHint" in findings[0]["description"]
        assert "destructiveHint" in findings[0]["description"]

    def test_missing_read_only(self):
        """Only destructive_hint set → finding mentions missing readOnlyHint."""
        tool = MCPTool(
            name="partial_tool",
            input_schema={},
            annotations=ToolAnnotations(read_only_hint=None, destructive_hint=False),
        )
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 1
        assert "readOnlyHint" in findings[0]["description"]
        assert "destructiveHint" not in findings[0]["description"]

    def test_partial_annotations(self):
        """Only read_only_hint set → finding mentions missing destructiveHint."""
        tool = MCPTool(
            name="partial_tool",
            input_schema={},
            annotations=ToolAnnotations(read_only_hint=True, destructive_hint=None),
        )
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 1
        assert "destructiveHint" in findings[0]["description"]
        assert "readOnlyHint" not in findings[0]["description"]

    def test_all_annotations_present(self):
        """Both hints set → no finding."""
        tool = MCPTool(
            name="fully_annotated_tool",
            input_schema={},
            annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False),
        )
        snapshot = MCPSnapshot(tools=[tool])
        findings = self.rule.check(snapshot)
        assert len(findings) == 0
