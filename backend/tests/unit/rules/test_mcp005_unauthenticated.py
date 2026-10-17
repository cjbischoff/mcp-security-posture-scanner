"""MCP-005 is inactive until the HTTP transport exists (#21).

``MCPClient.connect_http`` always raises, so an HTTP target never reaches
the rules. The rule is kept out of the registry and the rule count.
"""
from fastapi.testclient import TestClient

from app.main import app
from app.rules.registry import RULES, get_rule


def test_mcp005_not_registered():
    """The registry holds the 9 active rules and no MCP-005."""
    assert get_rule("MCP-005") is None
    assert len(RULES) == 9


def test_metrics_rule_count_matches_registry():
    """/api/metrics reports the active rule count, not a hard-coded 10."""
    assert TestClient(app).get("/api/metrics").json()["rule_count_total"] == len(RULES)
