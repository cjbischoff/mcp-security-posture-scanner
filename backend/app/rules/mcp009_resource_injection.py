"""
MCP-009: Prompt-injection patterns in resource/prompt content descriptions.

Same injection patterns as MCP-001 but applied to resource descriptions
and prompt descriptions.
"""
from app.mcp_client.models import MCPSnapshot
from app.rules import Rule, RuleMetadata, finding, mcp001_injection

# Reuse the same patterns and unicode detector from MCP-001
INJECTION_PATTERNS = mcp001_injection.INJECTION_PATTERNS
HIDDEN_UNICODE = mcp001_injection.HIDDEN_UNICODE


class MCP009ResourceInjectionRule(Rule):
    metadata = RuleMetadata(
        rule_id="MCP-009",
        severity="critical",
        title="Prompt-injection patterns in resource/prompt content descriptions",
        description="Resource or prompt description contains prompt injection patterns or hidden unicode characters.",
        remediation="Remove injection patterns from resource and prompt descriptions.",
    )

    def check(self, snapshot: MCPSnapshot) -> list[dict]:
        results = []

        for res in snapshot.resources:
            desc = res.description or ""
            reasons = self._check_text(desc)
            if reasons:
                results.append(finding(
                    rule_id="MCP-009",
                    severity="critical",
                    title=self.metadata.title,
                    description=f"Resource '{res.name}': {'; '.join(reasons)}.",
                    remediation=self.metadata.remediation,
                    subject=res.name,
                ))

        for prompt in snapshot.prompts:
            desc = prompt.description or ""
            reasons = self._check_text(desc)
            if reasons:
                results.append(finding(
                    rule_id="MCP-009",
                    severity="critical",
                    title=self.metadata.title,
                    description=f"Prompt '{prompt.name}': {'; '.join(reasons)}.",
                    remediation=self.metadata.remediation,
                    subject=prompt.name,
                ))

        return results

    def _check_text(self, text: str) -> list[str]:
        reasons = []
        if HIDDEN_UNICODE.search(text):
            reasons.append("contains hidden unicode characters")
        for pattern in INJECTION_PATTERNS:
            if pattern.search(text):
                reasons.append("matches injection pattern")
                break
        return reasons
