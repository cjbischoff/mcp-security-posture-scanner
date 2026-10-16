"""
MCP-003: Missing readOnlyHint/destructiveHint annotations.

Flags tools that are missing safety annotations.
"""
from app.mcp_client.models import MCPSnapshot
from app.rules import Rule, RuleMetadata, finding


class MCP003MissingAnnotationsRule(Rule):
    metadata = RuleMetadata(
        rule_id="MCP-003",
        severity="medium",
        title="Missing readOnlyHint/destructiveHint annotations",
        description="Tool is missing readOnlyHint and/or destructiveHint safety annotations.",
        remediation="Add readOnlyHint and destructiveHint annotations to every tool definition.",
    )

    def check(self, snapshot: MCPSnapshot) -> list[dict]:
        results = []
        for tool in snapshot.tools:
            ann = tool.annotations
            missing = []
            if ann is None:
                missing = ["readOnlyHint", "destructiveHint"]
            else:
                if ann.read_only_hint is None:
                    missing.append("readOnlyHint")
                if ann.destructive_hint is None:
                    missing.append("destructiveHint")

            if missing:
                results.append(finding(
                    rule_id="MCP-003",
                    severity="medium",
                    title=self.metadata.title,
                    description=f"Tool '{tool.name}' missing annotations: {', '.join(missing)}.",
                    remediation=self.metadata.remediation,
                    subject=tool.name,
                ))
        return results
