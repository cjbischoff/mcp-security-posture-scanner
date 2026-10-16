"""
Tests for the diff service.
"""
import pytest
from app.services.diff_service import compute_diff


class TestDiffService:
    def test_added_finding(self):
        """Finding in later but not earlier → added."""
        earlier = []
        later = [
            {"rule_id": "MCP-001", "severity": "critical", "subject": "tool1"},
        ]
        result = compute_diff(earlier, later)
        assert len(result["added"]) == 1
        assert len(result["removed"]) == 0
        assert len(result["unchanged"]) == 0

    def test_removed_finding(self):
        """Finding in earlier but not later → removed."""
        earlier = [
            {"rule_id": "MCP-001", "severity": "critical", "subject": "tool1"},
        ]
        later = []
        result = compute_diff(earlier, later)
        assert len(result["removed"]) == 1
        assert len(result["added"]) == 0

    def test_unchanged_finding(self):
        """Same finding in both → unchanged."""
        earlier = [
            {"rule_id": "MCP-001", "severity": "critical", "subject": "tool1"},
        ]
        later = [
            {"rule_id": "MCP-001", "severity": "critical", "subject": "tool1"},
        ]
        result = compute_diff(earlier, later)
        assert len(result["unchanged"]) == 1
        assert len(result["added"]) == 0
        assert len(result["removed"]) == 0

    def test_keyed_by_rule_id_and_subject(self):
        """Findings keyed by (rule_id, subject) tuple."""
        earlier = [
            {"rule_id": "MCP-001", "severity": "critical", "subject": "t1"},
            {"rule_id": "MCP-001", "severity": "critical", "subject": "t2"},
        ]
        later = [
            {"rule_id": "MCP-001", "severity": "critical", "subject": "t1"},
        ]
        result = compute_diff(earlier, later)
        assert len(result["unchanged"]) == 1
        assert len(result["removed"]) == 1
        assert result["removed"][0]["subject"] == "t2"

    def test_multiple_changes(self):
        """Mix of added, removed, unchanged."""
        earlier = [
            {"rule_id": "MCP-001", "severity": "critical", "subject": "a"},
            {"rule_id": "MCP-002", "severity": "high", "subject": "b"},
        ]
        later = [
            {"rule_id": "MCP-001", "severity": "critical", "subject": "a"},
            {"rule_id": "MCP-003", "severity": "medium", "subject": "c"},
        ]
        result = compute_diff(earlier, later)
        assert len(result["unchanged"]) == 1  # MCP-001/a
        assert len(result["removed"]) == 1  # MCP-002/b
        assert len(result["added"]) == 1  # MCP-003/c
