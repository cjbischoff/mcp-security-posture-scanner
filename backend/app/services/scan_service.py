"""
Scan service — creates and runs scans, produces reports.

State lives in the database via ``app.repositories.scans``. Each public
function opens its own short-lived session; the background scan task opens
a separate one.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone

from app import database
from app.mcp_client.client import MCPClient
from app.models.scan import Scan, ScanStatus
from app.models.scan_target import ScanTarget
from app.repositories import scans as repo
from app.rules.orchestrator import run_all_rules
from app.services.consent import validate_target, resolve_stdio

logger = logging.getLogger(__name__)

# Strong refs so running tasks are not garbage-collected mid-scan
_tasks: set[asyncio.Task] = set()


async def create_scan(target_data: dict) -> dict:
    """Validate consent, persist a pending scan, and start it in the background.

    Args:
        target_data: Target fields from the API (name, transport, command,
            args, url, allow_external).

    Returns:
        The Scan API response dict (status ``pending``).

    Raises:
        ConsentError: If the target is not allowed (router maps it to 422).
    """
    transport = target_data.get("transport", "stdio")
    validate_target(transport, target_data.get("url"), target_data.get("allow_external", False))
    if transport == "stdio":
        resolve_stdio(target_data.get("command"), target_data.get("args"))

    with database.SessionLocal() as session:
        target = repo.get_or_create_target(session, target_data)
        scan = repo.create_scan(session, target)
        response = _scan_to_response(scan)

    task = asyncio.create_task(_execute_scan(scan.id, target_data))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return response


async def _execute_scan(scan_id: int, target_data: dict) -> None:
    """Connect, enumerate, run rules, and store the snapshot and findings.

    Uses its own session, held for the whole task so it stays bound to the
    engine that existed when the scan started.
    """
    from app.metrics import record_scan_duration, record_finding_count

    start_time = time.time()
    with database.SessionLocal() as session:
        scan = session.get(Scan, scan_id)
        try:
            scan.status = ScanStatus.RUNNING
            session.commit()

            client = MCPClient()
            if target_data.get("transport", "stdio") == "http":
                await client.connect_http(target_data["url"])
            else:
                await client.connect_stdio(
                    *resolve_stdio(target_data.get("command"), target_data.get("args"))
                )
            snapshot = await client.enumerate()
            await client.close()

            # Raw snapshot is needed later for diff / MCP-010 drift
            scan.raw_snapshot = {
                "tools": [
                    {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                    for t in snapshot.tools
                ],
                "resources": [
                    {"name": r.name, "uri": r.uri, "description": r.description}
                    for r in snapshot.resources
                ],
                "prompts": [
                    {"name": p.name, "description": p.description} for p in snapshot.prompts
                ],
            }
            findings = run_all_rules(snapshot)
            repo.add_findings(session, scan, findings)
            scan.status = ScanStatus.COMPLETED
            scan.finished_at = datetime.now(timezone.utc)
            session.commit()

            record_scan_duration(time.time() - start_time)
            record_finding_count(len(findings))
        except Exception as e:
            logger.error(f"Scan {scan_id} failed: {e}")
            session.rollback()
            scan.status = ScanStatus.FAILED
            scan.error = str(e)
            scan.finished_at = datetime.now(timezone.utc)
            session.commit()
            record_scan_duration(time.time() - start_time)


def get_scan(scan_id: int) -> dict | None:
    """Get a scan by id.

    Args:
        scan_id: Scan primary key.

    Returns:
        The Scan API response dict, or None if not found.
    """
    with database.SessionLocal() as session:
        scan = repo.get_scan(session, scan_id)
        return _scan_to_response(scan) if scan else None


def list_scans() -> list[dict]:
    """List all scans, newest first.

    Returns:
        Scan API response dicts.
    """
    with database.SessionLocal() as session:
        return [_scan_to_response(s) for s in repo.list_scans(session)]


def get_report(scan_id: int) -> dict | None:
    """Build the findings report for a completed scan.

    Args:
        scan_id: Scan primary key.

    Returns:
        ``{"scan", "findings", "summary"}``, or None if the scan is missing
        or not completed (the router tells 404 from 409).
    """
    with database.SessionLocal() as session:
        scan = repo.get_scan(session, scan_id)
        if scan is None or scan.status != ScanStatus.COMPLETED:
            return None
        findings = _findings(scan)
        summary: dict[str, int] = {}
        for f in findings:
            summary[f["severity"]] = summary.get(f["severity"], 0) + 1
        return {"scan": _scan_to_response(scan), "findings": findings, "summary": summary}


def diff_scans(scan_id: int, other_id: int) -> dict | None:
    """Diff findings and run drift detection between two scans of one target.

    Args:
        scan_id: Earlier scan id.
        other_id: Later scan id.

    Returns:
        The ScanDiff response dict, or None if either scan is missing, not
        completed, or belongs to a different target (router maps to 404/409).
    """
    from app.services.diff_service import compute_diff
    from app.rules.registry import get_rule
    from app.mcp_client.models import MCPSnapshot, MCPTool, MCPResource, MCPPrompt

    with database.SessionLocal() as session:
        scan1 = repo.get_scan(session, scan_id)
        scan2 = repo.get_scan(session, other_id)
        if scan1 is None or scan2 is None:
            return None
        if scan1.status != ScanStatus.COMPLETED or scan2.status != ScanStatus.COMPLETED:
            return None
        if scan1.target_id != scan2.target_id:
            return None

        findings1, findings2 = _findings(scan1), _findings(scan2)
        diff = compute_diff(findings1, findings2)

        def _snapshot_from_raw(raw: dict | None) -> MCPSnapshot:
            if raw is None:
                return MCPSnapshot()
            return MCPSnapshot(
                tools=[MCPTool(**t) for t in raw.get("tools", [])],
                resources=[MCPResource(**r) for r in raw.get("resources", [])],
                prompts=[MCPPrompt(**p) for p in raw.get("prompts", [])],
            )

        drift_rule = get_rule("MCP-010")
        drift: list[dict] = []
        if drift_rule is not None and hasattr(drift_rule, "diff_check"):
            drift = drift_rule.diff_check(
                findings1,
                findings2,
                _snapshot_from_raw(scan1.raw_snapshot),
                _snapshot_from_raw(scan2.raw_snapshot),
            )

    return {
        "scan_id": scan_id,
        "other_id": other_id,
        "added": diff["added"],
        "removed": diff["removed"],
        "unchanged": diff["unchanged"],
        "drift": drift,
    }


def _iso(dt: datetime | None) -> str | None:
    """Format a stored datetime as ISO 8601; naive values are UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _target_to_response(target: ScanTarget) -> dict:
    """Build the ScanTarget API response."""
    return {
        "id": target.id,
        "name": target.name,
        "transport": target.transport.value,
        "command": target.command,
        "args": target.args or [],
        "url": target.url,
        "allow_external": target.allow_external,
        "created_at": _iso(target.created_at),
    }


def _findings(scan: Scan) -> list[dict]:
    """Build Finding API dicts for a scan, in insertion order."""
    return [
        {
            "id": f.id,
            "rule_id": f.rule_id,
            "severity": f.severity.value,
            "title": f.title,
            "description": f.description,
            "remediation": f.remediation,
            "subject": f.subject,
        }
        for f in sorted(scan.findings, key=lambda f: f.id)
    ]


def _scan_to_response(scan: Scan) -> dict:
    """Build the Scan API response."""
    return {
        "id": scan.id,
        "status": scan.status.value,
        "error": scan.error,
        "target": _target_to_response(scan.target),
        "created_at": _iso(scan.created_at),
        "finished_at": _iso(scan.finished_at),
        "finding_count": len(scan.findings),
    }
