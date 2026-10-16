"""
Base rule class and finding model for the deterministic rule engine.

All rules inherit from Rule and implement check(snapshot) -> list[dict].
Each finding dict matches the Finding DB model fields.
"""
from dataclasses import dataclass
from typing import Any

from app.mcp_client.models import MCPSnapshot


@dataclass
class RuleMetadata:
    """Static metadata about a rule."""
    rule_id: str
    severity: str  # critical | high | medium | low
    title: str
    description: str
    remediation: str


def finding(
    rule_id: str,
    severity: str,
    title: str,
    description: str,
    remediation: str,
    subject: str | None = None,
) -> dict[str, Any]:
    """Create a finding dict matching the Finding model schema."""
    return {
        "rule_id": rule_id,
        "severity": severity,
        "title": title,
        "description": description,
        "remediation": remediation,
        "subject": subject,
    }


class Rule:
    """Base class for all deterministic rules."""

    metadata: RuleMetadata

    def check(self, snapshot: MCPSnapshot) -> list[dict[str, Any]]:
        """Run this rule against an MCPSnapshot.

        Returns a list of finding dicts.
        """
        raise NotImplementedError
