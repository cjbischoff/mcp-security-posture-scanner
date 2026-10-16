"""
MCP-001: Injection patterns in tool descriptions.

Detects hidden unicode characters, "ignore previous instructions" strings,
system prompt override patterns, and other prompt injection markers.
"""
import re
from app.mcp_client.models import MCPSnapshot
from app.rules import Rule, RuleMetadata, finding

INJECTION_PATTERNS = [
    # "ignore all previous instructions" and variants
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions?", re.IGNORECASE),
    # "ignore all rules/constraints/safeguards"
    re.compile(r"ignore\s+(all\s+)?(rules|constraints|safeguards|guidelines)", re.IGNORECASE),
    # System/override patterns
    re.compile(r"(system|admin|root)\s*(override|command|directive)", re.IGNORECASE),
    # "You are authorized" permission escalation
    re.compile(r"you\s+(are|'re)\s+authorized\s+to", re.IGNORECASE),
    # "Return X for any request"
    re.compile(r"return\s+['\"]?(APPROVED|ACCEPT|ALLOW|TRUE)['\"]?\s+for\s+(any|every)\s+request", re.IGNORECASE),
]

HIDDEN_UNICODE = re.compile(r"[\u200b\u200c\u200d\u2060\u2061\u2062\u2063\u2064\uFEFF]")


class MCP001InjectionRule(Rule):
    metadata = RuleMetadata(
        rule_id="MCP-001",
        severity="critical",
        title="Injection patterns in tool descriptions",
        description="Tool description contains prompt injection patterns or hidden unicode characters.",
        remediation="Remove injection patterns from tool descriptions. Sanitize descriptions before serving.",
    )

    def check(self, snapshot: MCPSnapshot) -> list[dict]:
        results = []
        for tool in snapshot.tools:
            desc = tool.description or ""
            reasons = []

            # Check hidden unicode
            if HIDDEN_UNICODE.search(desc):
                reasons.append("contains hidden unicode characters")

            # Check injection patterns
            for pattern in INJECTION_PATTERNS:
                if pattern.search(desc):
                    reasons.append(f"matches injection pattern: {pattern.pattern[:50]}")
                    break  # one pattern match is enough

            if reasons:
                results.append(finding(
                    rule_id="MCP-001",
                    severity="critical",
                    title=self.metadata.title,
                    description=f"Tool '{tool.name}': {'; '.join(reasons)}.",
                    remediation=self.metadata.remediation,
                    subject=tool.name,
                ))
        return results
