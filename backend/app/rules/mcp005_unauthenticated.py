"""
MCP-005: Unauthenticated HTTP transport.

Flags HTTP transport with no auth scheme in server info.
"""
from app.mcp_client.models import MCPSnapshot
from app.rules import Rule, RuleMetadata


class MCP005UnauthenticatedRule(Rule):
    metadata = RuleMetadata(
        rule_id="MCP-005",
        severity="high",
        title="Unauthenticated HTTP transport",
        description="Server uses HTTP transport without authentication.",
        remediation="Add authentication (bearer token, OAuth, or API key) to HTTP transport.",
    )

    def check(self, snapshot: MCPSnapshot) -> list[dict]:
        # ponytail: HTTP transport isn't in the snapshot right now (it's a target-level property).
        # This rule fires based on target transport, not snapshot.
        # Return empty for snapshot-only check — the scan service will call this
        # rule with transport context in Plan 1.4.
        return []
