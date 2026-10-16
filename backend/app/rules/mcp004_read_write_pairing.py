"""
MCP-004: Read capability + network/write capability pairing (confused-deputy).

Signals if any tool has read-like characteristics and another has write-like
characteristics, indicating confused-deputy risk when both are present.
"""
from app.mcp_client.models import MCPSnapshot, MCPTool
from app.rules import Rule, RuleMetadata, finding

# Heuristics: patterns commonly associated with read vs write capabilities
READ_PARAMS = {"path", "source", "file", "read", "get", "fetch", "query"}
WRITE_PARAMS = {"url", "target", "dest", "write", "create", "upload", "post", "send", "delete"}


def _has_read_param(schema: dict) -> bool:
    """Check if schema has any read-associated parameter names."""
    props = schema.get("properties", {})
    for name in props:
        parts = set(name.lower().replace("-", "_").split("_"))
        if parts & READ_PARAMS:
            return True
    return False


def _has_write_param(schema: dict) -> bool:
    """Check if schema has any write-associated parameter names."""
    props = schema.get("properties", {})
    for name in props:
        parts = set(name.lower().replace("-", "_").split("_"))
        if parts & WRITE_PARAMS:
            return True
    return False


class MCP004ReadWritePairingRule(Rule):
    metadata = RuleMetadata(
        rule_id="MCP-004",
        severity="high",
        title="Read capability + network/write capability pairing (confused-deputy)",
        description="Server exposes both read and write capabilities across its tools — potential confused-deputy / exfiltration risk.",
        remediation="Separate read-only and write-capable tools onto different servers, or add strict access controls.",
    )

    def check(self, snapshot: MCPSnapshot) -> list[dict]:
        has_read = False
        has_write = False
        read_tools: list[str] = []
        write_tools: list[str] = []

        for tool in snapshot.tools:
            schema = tool.input_schema or {}
            if _has_read_param(schema):
                has_read = True
                read_tools.append(tool.name)
            if _has_write_param(schema):
                has_write = True
                write_tools.append(tool.name)

        if has_read and has_write:
            return [finding(
                rule_id="MCP-004",
                severity="high",
                title=self.metadata.title,
                description=(
                    f"Read-capable tools: {', '.join(read_tools)}; "
                    f"write-capable tools: {', '.join(write_tools)}."
                ),
                remediation=self.metadata.remediation,
                subject=None,
            )]
        return []
