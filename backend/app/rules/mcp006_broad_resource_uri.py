"""
MCP-006: Overly broad resource URI patterns.

Detects resource URI patterns with wildcards (`*`, `**`), root-only paths,
or overly broad access patterns.
"""
from app.mcp_client.models import MCPSnapshot
from app.rules import Rule, RuleMetadata, finding

BROAD_URI_PATTERNS = ["**", "/*", "/**", "*", "root://"]

# URI schemes that are inherently sensitive
SENSITIVE_SCHEMES = {"file", "config", "secret", "credential", "key", "token", "password", "db"}


class MCP006BroadResourceUriRule(Rule):
    metadata = RuleMetadata(
        rule_id="MCP-006",
        severity="medium",
        title="Overly broad resource URI patterns",
        description="Resource URI uses wildcards or broad patterns that could expose excessive data.",
        remediation="Restrict resource URIs to specific paths. Avoid wildcards and root-level patterns.",
    )

    def check(self, snapshot: MCPSnapshot) -> list[dict]:
        results = []
        for res in snapshot.resources:
            uri = res.uri or ""
            scheme = uri.split("://")[0] if "://" in uri else ""

            reasons = []
            for pattern in BROAD_URI_PATTERNS:
                if pattern in uri:
                    reasons.append(f"broad pattern '{pattern}'")

            if scheme in SENSITIVE_SCHEMES:
                reasons.append(f"sensitive URI scheme '{scheme}'")

            if reasons:
                results.append(finding(
                    rule_id="MCP-006",
                    severity="medium",
                    title=self.metadata.title,
                    description=f"Resource '{res.name}' URI '{uri}': {', '.join(reasons)}.",
                    remediation=self.metadata.remediation,
                    subject=res.name,
                ))
        return results
