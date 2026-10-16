"""
Rule orchestrator — iterates all registered rules and collects findings.
"""
from app.mcp_client.models import MCPSnapshot
from app.rules import Rule, finding


def run_all_rules(snapshot: MCPSnapshot) -> list[dict]:
    """Run all registered rules against an MCPSnapshot.

    Returns a deduplicated list of finding dicts.
    """
    from app.rules.registry import RULES

    all_findings: list[dict] = []
    for rule in RULES:
        try:
            all_findings.extend(rule.check(snapshot))
        except Exception:
            # ponytail: log rule failure, don't crash the scan
            pass

    # Deduplicate by (rule_id, subject)
    seen: set[tuple[str, str | None]] = set()
    deduped: list[dict] = []
    for f in all_findings:
        key = (f["rule_id"], f.get("subject"))
        if key not in seen:
            seen.add(key)
            deduped.append(f)

    return deduped
