"""Persistence for scan targets, scans, and findings.

Plain functions over a caller-owned SQLAlchemy session. Functions that
write commit before returning.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.finding import Finding, FindingSeverity
from app.models.scan import Scan
from app.models.scan_target import ScanTarget, TransportType


def get_or_create_target(session: Session, data: dict) -> ScanTarget:
    """Return the target with this exact connection info, creating it if new.

    Identity is (name, transport, command, args, url): a second scan with the
    same name but a different command gets its own target, so it never reuses
    an old command and diff treats the two as different servers.

    Args:
        session: Open database session.
        data: Target fields: ``name``, ``transport``, ``command``, ``args``,
            ``url``, ``allow_external``.

    Returns:
        The persisted ScanTarget.
    """
    transport = TransportType(data.get("transport", "stdio"))
    args = data.get("args") or []
    candidates = session.scalars(
        select(ScanTarget).where(
            ScanTarget.name == data["name"],
            ScanTarget.transport == transport,
            ScanTarget.command.is_(None) if data.get("command") is None
            else ScanTarget.command == data["command"],
            ScanTarget.url.is_(None) if data.get("url") is None
            else ScanTarget.url == data["url"],
        )
    )
    # args is JSON; compare in Python rather than per-dialect JSON equality
    for target in candidates:
        if (target.args or []) == args:
            return target
    target = ScanTarget(
        name=data["name"],
        transport=transport,
        command=data.get("command"),
        args=args,
        url=data.get("url"),
        allow_external=data.get("allow_external", False),
    )
    session.add(target)
    session.commit()
    return target


def create_scan(session: Session, target: ScanTarget) -> Scan:
    """Create a pending scan for ``target``.

    Args:
        session: Open database session.
        target: Persisted target to scan.

    Returns:
        The new Scan with its id assigned.
    """
    scan = Scan(target=target)
    session.add(scan)
    session.commit()
    return scan


def get_scan(session: Session, scan_id: int) -> Scan | None:
    """Load a scan with its target and findings.

    Args:
        session: Open database session.
        scan_id: Scan primary key.

    Returns:
        The Scan, or None if it does not exist.
    """
    return session.scalars(
        select(Scan)
        .where(Scan.id == scan_id)
        .options(selectinload(Scan.target), selectinload(Scan.findings))
    ).first()


def list_scans(session: Session) -> list[Scan]:
    """Load all scans, newest first, with targets and findings.

    Args:
        session: Open database session.

    Returns:
        Scans ordered by id descending.
    """
    return list(session.scalars(
        select(Scan)
        .order_by(Scan.id.desc())
        .options(selectinload(Scan.target), selectinload(Scan.findings))
    ))


def add_findings(session: Session, scan: Scan, findings: list[dict]) -> None:
    """Persist rule-engine finding dicts for ``scan``.

    Args:
        session: Open database session.
        scan: Scan the findings belong to.
        findings: Dicts from the rule engine (rule_id, severity, title,
            description, remediation, subject).
    """
    for f in findings:
        session.add(Finding(
            scan_id=scan.id,
            rule_id=f["rule_id"],
            severity=FindingSeverity(f["severity"]),
            title=f["title"],
            description=f["description"],
            remediation=f["remediation"],
            subject=f.get("subject"),
        ))
    session.commit()
