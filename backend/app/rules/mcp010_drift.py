"""
MCP-010: Drift detection (diff-only).

Compares two snapshots' findings, flagging findings that changed severity
or disappeared without a corresponding description change.
"""
from app.mcp_client.models import MCPSnapshot
from app.rules import Rule, RuleMetadata, finding


class MCP010DriftRule(Rule):
    metadata = RuleMetadata(
        rule_id="MCP-010",
        severity="high",
        title="Finding drift — severity change or silent removal",
        description="A finding changed severity or disappeared between scans without a description change in the corresponding subject.",
        remediation="Review the drift: verify whether the change was intentional or a 'rug pull' by the server operator.",
    )

    def check(self, snapshot: MCPSnapshot) -> list[dict]:
        # MCP-010 is a diff-only rule; it requires two snapshots and prior findings.
        # The diff_service calls this rule specifically during diff computation.
        # Return empty for single-snapshot check.
        return []

    def diff_check(
        self,
        earlier_findings: list[dict],
        later_findings: list[dict],
        earlier_snapshot: MCPSnapshot,
        later_snapshot: MCPSnapshot,
    ) -> list[dict]:
        """Run drift detection comparing two scan results.

        Flags findings in earlier_findings that:
        - Changed severity in later_findings
        - Disappeared from later_findings without a description change
        """
        results = []

        # Index later findings by (rule_id, subject)
        later_index: dict[tuple[str, str | None], dict] = {}
        for f in later_findings:
            later_index[(f["rule_id"], f.get("subject"))] = f

        # Index subjects' descriptions for cross-checking
        earlier_descriptions = _build_description_map(earlier_snapshot)
        later_descriptions = _build_description_map(later_snapshot)

        for f in earlier_findings:
            key = (f["rule_id"], f.get("subject"))
            later = later_index.get(key)

            if later is None:
                # Finding disappeared — check if description changed
                subject = f.get("subject")
                old_desc = earlier_descriptions.get(subject)
                new_desc = later_descriptions.get(subject)

                if old_desc != new_desc:
                    # Description changed — might be intentional
                    continue

                # Finding disappeared without description change → drift
                results.append(finding(
                    rule_id="MCP-010",
                    severity="high",
                    title=self.metadata.title,
                    description=(
                        f"Finding {f['rule_id']} on '{subject}' was present in earlier scan "
                        f"but is missing in later scan (no description change)."
                    ),
                    remediation=self.metadata.remediation,
                    subject=subject,
                ))
            elif later.get("severity") != f.get("severity"):
                # Severity changed
                results.append(finding(
                    rule_id="MCP-010",
                    severity="high",
                    title=self.metadata.title,
                    description=(
                        f"Finding {f['rule_id']} on '{f.get('subject')}' changed severity "
                        f"from '{f['severity']}' to '{later['severity']}'."
                    ),
                    remediation=self.metadata.remediation,
                    subject=f.get("subject"),
                ))

        return results


def _build_description_map(snapshot: MCPSnapshot) -> dict[str | None, str]:
    """Build a map of subject name → description for cross-referencing."""
    desc_map: dict[str | None, str] = {}
    for t in snapshot.tools:
        desc_map[t.name] = t.description or ""
    for r in snapshot.resources:
        desc_map[r.name] = r.description or ""
    for p in snapshot.prompts:
        desc_map[p.name] = p.description or ""
    return desc_map
