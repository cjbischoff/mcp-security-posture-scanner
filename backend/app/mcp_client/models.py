from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolAnnotations:
    """Annotations on an MCP tool."""
    read_only_hint: bool | None = None
    destructive_hint: bool | None = None


@dataclass
class MCPTool:
    """Typed representation of an MCP tool."""
    name: str
    input_schema: dict[str, Any]
    description: str | None = None
    annotations: ToolAnnotations | None = None

    @classmethod
    def from_raw(cls, raw: dict) -> "MCPTool":
        ann_raw = raw.get("annotations")
        ann = None
        if ann_raw:
            ann = ToolAnnotations(
                read_only_hint=ann_raw.get("readOnlyHint"),
                destructive_hint=ann_raw.get("destructiveHint"),
            )
        return cls(
            name=raw.get("name", ""),
            description=raw.get("description"),
            input_schema=raw.get("inputSchema", raw.get("input_schema", {})),
            annotations=ann,
        )


@dataclass
class MCPResource:
    """Typed representation of an MCP resource."""
    name: str
    uri: str
    description: str | None = None
    mime_type: str | None = None

    @classmethod
    def from_raw(cls, raw: dict) -> "MCPResource":
        return cls(
            name=raw.get("name", ""),
            uri=raw.get("uri", ""),
            description=raw.get("description"),
            mime_type=raw.get("mimeType"),
        )


@dataclass
class MCPPrompt:
    """Typed representation of an MCP prompt."""
    name: str
    description: str | None = None

    @classmethod
    def from_raw(cls, raw: dict) -> "MCPPrompt":
        return cls(
            name=raw.get("name", ""),
            description=raw.get("description"),
        )


@dataclass
class MCPSnapshot:
    """Result of enumerating an MCP server's capabilities."""
    tools: list[MCPTool] = field(default_factory=list)
    resources: list[MCPResource] = field(default_factory=list)
    prompts: list[MCPPrompt] = field(default_factory=list)
