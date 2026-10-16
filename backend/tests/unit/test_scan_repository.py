"""Unit tests for the scan repository against in-memory SQLite."""
from app.models.finding import FindingSeverity
from app.models.scan import ScanStatus
from app.repositories import scans as repo

DEMO = {"name": "demo", "transport": "stdio", "command": "vulnerable-demo", "args": [], "url": None}


def test_same_connection_info_reuses_target(db_session):
    t1 = repo.get_or_create_target(db_session, DEMO)
    t2 = repo.get_or_create_target(db_session, dict(DEMO))
    assert t1.id == t2.id


def test_same_name_different_command_creates_new_target(db_session):
    t1 = repo.get_or_create_target(db_session, DEMO)
    t2 = repo.get_or_create_target(db_session, {**DEMO, "command": "other"})
    t3 = repo.get_or_create_target(db_session, {**DEMO, "args": ["x"]})
    assert len({t1.id, t2.id, t3.id}) == 3
    assert t2.command == "other"


def test_create_get_and_list_scans(db_session):
    target = repo.get_or_create_target(db_session, DEMO)
    s1 = repo.create_scan(db_session, target)
    s2 = repo.create_scan(db_session, target)
    assert s1.status == ScanStatus.PENDING
    assert repo.get_scan(db_session, s1.id).target.name == "demo"
    assert repo.get_scan(db_session, 9999) is None
    assert [s.id for s in repo.list_scans(db_session)] == [s2.id, s1.id]


def test_add_findings(db_session):
    scan = repo.create_scan(db_session, repo.get_or_create_target(db_session, DEMO))
    repo.add_findings(db_session, scan, [{
        "rule_id": "MCP-001", "severity": "critical", "title": "t",
        "description": "d", "remediation": "r", "subject": "tool",
    }])
    saved = repo.get_scan(db_session, scan.id)
    assert len(saved.findings) == 1
    assert saved.findings[0].severity == FindingSeverity.CRITICAL
