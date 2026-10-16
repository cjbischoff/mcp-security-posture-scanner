"""
MCP-008: Missing or malformed schema on required parameters.

Checks that required parameters have valid schema definitions (type + constraints).
"""
from app.mcp_client.models import MCPSnapshot
from app.rules import Rule, RuleMetadata, finding


class MCP008MissingSchemaRule(Rule):
    metadata = RuleMetadata(
        rule_id="MCP-008",
        severity="medium",
        title="Missing or malformed schema on required parameters",
        description="Required parameters lack proper schema validation (no type or missing constraints).",
        remediation="Ensure every required parameter has a type and appropriate constraints (pattern, enum, format, min/max).",
    )

    def check(self, snapshot: MCPSnapshot) -> list[dict]:
        results = []
        for tool in snapshot.tools:
            schema = tool.input_schema or {}
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            bad_params = []
            for param_name in required:
                param_schema = properties.get(param_name, {})
                # Missing type or type is "any" without constraints
                if "type" not in param_schema:
                    bad_params.append(f"{param_name} (no type)")
                elif param_schema.get("type") == "any" and not param_schema.get("enum"):
                    bad_params.append(f"{param_name} (unconstrained 'any')")

            if bad_params:
                results.append(finding(
                    rule_id="MCP-008",
                    severity="medium",
                    title=self.metadata.title,
                    description=f"Tool '{tool.name}' has malformed required params: {', '.join(bad_params)}.",
                    remediation=self.metadata.remediation,
                    subject=tool.name,
                ))
        return results
