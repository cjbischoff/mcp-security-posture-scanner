"""
Diff computation service — compares findings from two scans.
"""
from typing import Any


def compute_diff(
    earlier_findings: list[dict[str, Any]],
    later_findings: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Compare two lists of findings and return added/removed/unchanged sets.

    Findings are keyed by (rule_id, subject).
    """
    earlier_map: dict[tuple[str, str | None], dict] = {}
    for f in earlier_findings:
        earlier_map[(f["rule_id"], f.get("subject"))] = f

    later_map: dict[tuple[str, str | None], dict] = {}
    for f in later_findings:
        later_map[(f["rule_id"], f.get("subject"))] = f

    earlier_keys = set(earlier_map)
    later_keys = set(later_map)

    added_keys = later_keys - earlier_keys
    removed_keys = earlier_keys - later_keys
    unchanged_keys = earlier_keys & later_keys

    return {
        "added": [later_map[k] for k in added_keys],
        "removed": [earlier_map[k] for k in removed_keys],
        "unchanged": [earlier_map[k] for k in unchanged_keys],
    }
