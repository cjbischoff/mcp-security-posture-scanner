"""
Integration tests for the rule engine.

Runs all 9 active rules against a snapshot from the stub fixture MCP server
and verifies known-vulnerable patterns are detected.
"""
import sys
import pytest
from pathlib import Path

from tests.fixtures.stub_mcp_server import EXPECTED_FINDINGS as FIXTURE_FINDINGS

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "stub_mcp_server.py"


@pytest.mark.asyncio
async def test_rule_engine_detects_fixture_vulnerabilities():
    """Run all rules against stub server snapshot — verify known vulns found."""
    from app.mcp_client.client import MCPClient
    from app.rules.orchestrator import run_all_rules

    client = MCPClient()
    try:
        await client.connect_stdio(sys.executable, [str(FIXTURE_PATH)])
        snapshot = await client.enumerate()

        findings = run_all_rules(snapshot)
        assert {(f["rule_id"], f["subject"]) for f in findings} == FIXTURE_FINDINGS
        assert len(findings) == len(FIXTURE_FINDINGS)

    finally:
        await client.close()


def test_orchestrator_deduplicates(monkeypatch):
    """Duplicate (rule_id, subject) pairs from rules collapse to one finding each."""
    from app.rules import finding, registry
    from app.rules.orchestrator import run_all_rules
    from app.mcp_client.models import MCPSnapshot

    class Dup:
        def check(self, snapshot):
            return [
                finding("X-1", "low", "t", "d", "r", subject="a"),
                finding("X-1", "low", "t", "d", "r", subject="a"),
                finding("X-1", "low", "t", "d", "r", subject="b"),
                finding("X-2", "low", "t", "d", "r", subject="a"),
            ]

    monkeypatch.setattr(registry, "RULES", [Dup(), Dup()])
    pairs = [(f["rule_id"], f["subject"]) for f in run_all_rules(MCPSnapshot())]
    assert sorted(pairs) == [("X-1", "a"), ("X-1", "b"), ("X-2", "a")]
