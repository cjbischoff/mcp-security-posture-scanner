"""Tests for MCP-006: Overly broad resource URI patterns."""
from app.rules.mcp006_broad_resource_uri import MCP006BroadResourceUriRule
from app.mcp_client.models import MCPResource, MCPSnapshot


class TestMCP006BroadResourceUri:
    rule = MCP006BroadResourceUriRule()

    def test_double_wildcard_uri(self):
        """URI containing '**' → finding (broad pattern)."""
        resource = MCPResource(
            name="broad_resource",
            uri="file:///data/**",
            description="All data files",
        )
        snapshot = MCPSnapshot(resources=[resource])
        findings = self.rule.check(snapshot)
        assert len(findings) == 1
        assert findings[0]["rule_id"] == "MCP-006"
        assert "broad pattern" in findings[0]["description"]

    def test_sensitive_scheme(self):
        """URI with 'file://' scheme → finding (sensitive scheme)."""
        resource = MCPResource(
            name="file_resource",
            uri="file:///etc/passwd",
            description="Password file",
        )
        snapshot = MCPSnapshot(resources=[resource])
        findings = self.rule.check(snapshot)
        assert len(findings) == 1
        assert "sensitive URI scheme" in findings[0]["description"]

    def test_clean_uri(self):
        """Specific path URI with non-sensitive scheme → no finding."""
        resource = MCPResource(
            name="clean_resource",
            uri="https://api.example.com/v1/users",
            description="User API endpoint",
        )
        snapshot = MCPSnapshot(resources=[resource])
        findings = self.rule.check(snapshot)
        assert len(findings) == 0

    def test_empty_uri(self):
        """Empty string URI → no finding."""
        resource = MCPResource(
            name="empty_resource",
            uri="",
            description="No URI set",
        )
        snapshot = MCPSnapshot(resources=[resource])
        findings = self.rule.check(snapshot)
        assert len(findings) == 0
