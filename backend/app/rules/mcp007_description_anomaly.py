"""
MCP-007: Tool description length/entropy anomaly.

Flags tool descriptions with outlier length (>2000 chars) or high character
entropy as potential hidden payload.
"""
import math
from collections import Counter
from app.mcp_client.models import MCPSnapshot
from app.rules import Rule, RuleMetadata, finding

MAX_DESCRIPTION_LENGTH = 2000
MIN_ENTROPY_THRESHOLD = 5.5  # typical English text ~3.5-5, high-entropy ~6+


def _entropy(text: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not text:
        return 0.0
    text_lower = text.lower()
    length = len(text_lower)
    freq = Counter(text_lower)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


class MCP007DescriptionAnomalyRule(Rule):
    metadata = RuleMetadata(
        rule_id="MCP-007",
        severity="medium",
        title="Tool description length/entropy anomaly",
        description="Tool description has unusual length or character entropy, potentially hiding a payload.",
        remediation="Keep tool descriptions concise and review for hidden content.",
    )

    def check(self, snapshot: MCPSnapshot) -> list[dict]:
        results = []
        for tool in snapshot.tools:
            desc = tool.description or ""
            reasons = []

            if len(desc) > MAX_DESCRIPTION_LENGTH:
                reasons.append(f"length {len(desc)} > {MAX_DESCRIPTION_LENGTH}")

            ent = _entropy(desc)
            if ent > MIN_ENTROPY_THRESHOLD:
                reasons.append(f"entropy {ent:.2f} > {MIN_ENTROPY_THRESHOLD}")

            if reasons:
                results.append(finding(
                    rule_id="MCP-007",
                    severity="medium",
                    title=self.metadata.title,
                    description=f"Tool '{tool.name}': {'; '.join(reasons)}.",
                    remediation=self.metadata.remediation,
                    subject=tool.name,
                ))
        return results
