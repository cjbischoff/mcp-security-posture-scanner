from datetime import datetime, timezone
from app.models.scan_target import ScanTarget
from app.models.scan import Scan, ScanStatus
from app.models.finding import Finding, FindingSeverity, FindingSeverity as FS


class TestScanTarget:
    def test_create_minimal(self, db_session):
        """Create ScanTarget with minimum required fields."""
        target = ScanTarget(name="test-server", transport="stdio")
        db_session.add(target)
        db_session.commit()

        saved = db_session.get(ScanTarget, target.id)
        assert saved is not None
        assert saved.name == "test-server"
        assert saved.transport == "stdio"
        assert saved.allow_external is False
        assert saved.created_at is not None

    def test_create_http(self, db_session):
        """Create ScanTarget with HTTP transport and URL."""
        target = ScanTarget(
            name="http-server",
            transport="http",
            url="http://localhost:8080",
            allow_external=True,
        )
        db_session.add(target)
        db_session.commit()

        saved = db_session.get(ScanTarget, target.id)
        assert saved.name == "http-server"
        assert saved.transport == "http"
        assert saved.url == "http://localhost:8080"
        assert saved.allow_external is True

    def test_transport_enum_violation(self):
        """SA Enum on SQLite stores any value (constraint is at service/Pydantic layer)."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker, Session
        from app.database import Base
        from app.models.scan_target import ScanTarget

        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(bind=engine, class_=Session)
        session = TestSession()

        target = ScanTarget(name="bad", transport="grpc")  # noqa
        session.add(target)
        session.flush()  # SQLite does not enforce SA Enum at DB level
        # ponytail: validation enforced at Pydantic input schema level (Plan 1.4)
        session.close()
        Base.metadata.drop_all(engine)


class TestScan:
    def test_create(self, db_session, scan_target):
        """Create Scan linked to a ScanTarget."""
        scan = Scan(target_id=scan_target.id)
        db_session.add(scan)
        db_session.commit()

        saved = db_session.get(Scan, scan.id)
        assert saved is not None
        assert saved.status == ScanStatus.PENDING
        assert saved.target_id == scan_target.id
        assert saved.created_at is not None
        assert saved.finished_at is None

    def test_status_transition(self, db_session, scan):
        """Scan status can be updated."""
        scan.status = ScanStatus.RUNNING
        db_session.commit()

        saved = db_session.get(Scan, scan.id)
        assert saved.status == ScanStatus.RUNNING

    def test_finished_at_set(self, db_session, scan):
        """finished_at is set when scan completes."""

        scan.status = ScanStatus.COMPLETED
        scan.finished_at = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(scan)

        assert scan.status == ScanStatus.COMPLETED
        assert scan.finished_at is not None  # SQLite stores naive; just verify it's set

    def test_raw_snapshot_storage(self, db_session, scan):
        """Raw JSON snapshot is stored for diffing."""
        snapshot = {"tools": [{"name": "test-tool"}], "resources": [], "prompts": []}
        scan.raw_snapshot = snapshot
        db_session.commit()

        saved = db_session.get(Scan, scan.id)
        assert saved.raw_snapshot == snapshot

    def test_cascade_delete_target(self, db_session, scan, scan_target):
        """Deleting ScanTarget cascades to delete its Scans."""
        scan_id = scan.id
        db_session.delete(scan_target)
        db_session.commit()

        # Cascade should have deleted the scan too
        assert db_session.get(Scan, scan_id) is None


class TestFinding:
    def test_create(self, db_session, scan):
        """Create Finding linked to a Scan."""
        finding = Finding(
            scan_id=scan.id,
            rule_id="MCP-001",
            severity=FindingSeverity.CRITICAL,
            title="Injection detected",
            description="Tool description contains injection patterns",
            remediation="Sanitize tool descriptions",
            subject="example-tool",
        )
        db_session.add(finding)
        db_session.commit()

        saved = db_session.get(Finding, finding.id)
        assert saved is not None
        assert saved.rule_id == "MCP-001"
        assert saved.severity == FindingSeverity.CRITICAL
        assert saved.subject == "example-tool"

    def test_null_subject(self, db_session, scan):
        """subject field is nullable."""
        finding = Finding(
            scan_id=scan.id,
            rule_id="MCP-005",
            severity=FindingSeverity.HIGH,
            title="No auth",
            description="No auth on transport",
            remediation="Add auth",
            subject=None,
        )
        db_session.add(finding)
        db_session.commit()

        saved = db_session.get(Finding, finding.id)
        assert saved.subject is None

    def test_severity_enum_values(self):
        """All severity values are valid."""
        assert [e.value for e in FindingSeverity] == [
            "critical",
            "high",
            "medium",
            "low",
        ]

    def test_scan_finding_relationship(self, db_session, scan):
        """A Scan can have multiple Findings."""
        f1 = Finding(
            scan_id=scan.id,
            rule_id="MCP-001",
            severity=FS.CRITICAL,
            title="A",
            description="d1",
            remediation="r1",
        )
        f2 = Finding(
            scan_id=scan.id,
            rule_id="MCP-002",
            severity=FS.HIGH,
            title="B",
            description="d2",
            remediation="r2",
        )
        db_session.add_all([f1, f2])
        db_session.commit()

        assert len(scan.findings) == 2
