"""
MCP-002: Unconstrained input schema on sensitive parameters.

Scans tool input schemas for parameters named `command`, `path`, `url`,
`shell`, `exec` that lack pattern/format/enum constraints.
"""
from app.mcp_client.models import MCPSnapshot
from app.rules import Rule, RuleMetadata, finding

SENSITIVE_PARAMS = {"command", "path", "url", "shell", "exec", "program", "binary", "cmd"}


class MCP002UnconstrainedSchemaRule(Rule):
    metadata = RuleMetadata(
        rule_id="MCP-002",
        severity="high",
        title="Unconstrained input schema on sensitive parameters",
        description="Tool has sensitive parameters (command/path/url/shell) without pattern/format/enum constraints.",
        remediation="Add pattern, format, or enum constraints to sensitive parameters in input schemas.",
    )

    def check(self, snapshot: MCPSnapshot) -> list[dict]:
        results = []
        for tool in snapshot.tools:
            schema = tool.input_schema or {}
            props = schema.get("properties", {})
            unconstrained = []
            for param_name, param_schema in props.items():
                if param_name.lower() in SENSITIVE_PARAMS:
                    # Check if it has constraints
                    has_constraint = bool(
                        param_schema.get("pattern")
                        or param_schema.get("enum")
                        or param_schema.get("format")
                        or param_schema.get("maxLength")
                    )
                    if not has_constraint:
                        unconstrained.append(param_name)

            if unconstrained:
                results.append(finding(
                    rule_id="MCP-002",
                    severity="high",
                    title=self.metadata.title,
                    description=f"Tool '{tool.name}' has unconstrained params: {', '.join(unconstrained)}.",
                    remediation=self.metadata.remediation,
                    subject=tool.name,
                ))
        return results
