"""
MCP-005: Unauthenticated HTTP transport. INACTIVE, not in the registry.

It needs the HTTP transport, which is not built (``MCPClient.connect_http``
always raises), so no HTTP target ever reaches the rules. Register it and
give it the target's transport and auth state when the transport exists.
"""
from app.rules import Rule, RuleMetadata


class MCP005UnauthenticatedRule(Rule):
    metadata = RuleMetadata(
        rule_id="MCP-005",
        severity="high",
        title="Unauthenticated HTTP transport",
        description="Server uses HTTP transport without authentication.",
        remediation="Add authentication (bearer token, OAuth, or API key) to HTTP transport.",
    )

    # No check(): the base Rule.check raises NotImplementedError until then
