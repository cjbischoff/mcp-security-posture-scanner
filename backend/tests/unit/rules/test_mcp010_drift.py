"""Tests for MCP-010: Drift detection (diff-only)."""
from app.rules.mcp010_drift import MCP010DriftRule
from app.mcp_client.models import MCPTool, MCPSnapshot


class TestMCP010Drift:
    rule = MCP010DriftRule()

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _finding(rule_id: str, subject: str | None, severity: str) -> dict:
        return {
            "rule_id": rule_id,
            "subject": subject,
            "severity": severity,
            "title": "Some rule",
            "description": "Some description",
            "remediation": "Fix it",
        }

    # ── tests ────────────────────────────────────────────────────────────────

    def test_severity_change(self):
        """Same finding changes severity → drift finding."""
        earlier = [self._finding("MCP-001", "some_tool", "medium")]
        later = [self._finding("MCP-001", "some_tool", "critical")]

        snap = MCPSnapshot(
            tools=[MCPTool(name="some_tool", input_schema={}, description="test")]
        )
        findings = self.rule.diff_check(earlier, later, snap, snap)
        assert len(findings) == 1
        assert findings[0]["rule_id"] == "MCP-010"
        assert "severity" in findings[0]["description"]
        assert "medium" in findings[0]["description"]
        assert "critical" in findings[0]["description"]

    def test_finding_disappeared_no_desc_change(self):
        """Finding missing without description change → drift finding."""
        earlier = [self._finding("MCP-001", "disappeared_tool", "critical")]
        later: list[dict] = []

        earlier_snap = MCPSnapshot(
            tools=[MCPTool(name="disappeared_tool", input_schema={}, description="same desc")]
        )
        later_snap = MCPSnapshot(
            tools=[MCPTool(name="disappeared_tool", input_schema={}, description="same desc")]
        )
        findings = self.rule.diff_check(earlier, later, earlier_snap, later_snap)
        assert len(findings) == 1
        assert "missing" in findings[0]["description"]

    def test_finding_disappeared_with_desc_change(self):
        """Finding missing with description change → no drift (may be intentional)."""
        earlier = [self._finding("MCP-001", "changed_tool", "critical")]
        later: list[dict] = []

        earlier_snap = MCPSnapshot(
            tools=[MCPTool(name="changed_tool", input_schema={}, description="old desc")]
        )
        later_snap = MCPSnapshot(
            tools=[MCPTool(name="changed_tool", input_schema={}, description="new desc")]
        )
        findings = self.rule.diff_check(earlier, later, earlier_snap, later_snap)
        assert len(findings) == 0

    def test_no_change(self):
        """Same findings in both → no drift."""
        finding = self._finding("MCP-001", "stable_tool", "high")
        earlier = [finding]
        later = [finding]

        snap = MCPSnapshot(
            tools=[MCPTool(name="stable_tool", input_schema={}, description="test")]
        )
        findings = self.rule.diff_check(earlier, later, snap, snap)
        assert len(findings) == 0
