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

from opentelemetry import trace
from opentelemetry.trace import StatusCode

from app import database
from app.metrics import record_scan
from app.mcp_client.client import MCPClient
from app.models.scan import Scan, ScanStatus
from app.models.scan_target import ScanTarget
from app.repositories import scans as repo
from app.rules.orchestrator import run_all_rules
from app.services.consent import ConsentError, validate_target, resolve_stdio

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# In-memory fault flags, toggled by the admin router to trigger alerts
FAULTS: dict[str, bool] = {"scan_failure": False}

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
    logger.info("scan submitted", extra={"scan_id": scan.id, "transport": transport})

    task = asyncio.create_task(_execute_scan(scan.id, target_data))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return response


def _span(name: str, attributes: dict):
    """Start a span that never copies exception text into events or status.

    Args:
        name: Span name.
        attributes: Safe attributes (scan_id, transport).

    Returns:
        A context manager yielding the span.
    """
    return tracer.start_as_current_span(
        name, attributes=attributes, record_exception=False, set_status_on_exception=False
    )


class FaultInjected(Exception):
    """Raised by a scan while the admin ``scan_failure`` fault is on."""


def user_error(exc: BaseException) -> str:
    """Return the error text shown to the user for a failed scan.

    Some exceptions carry no message (``str(TimeoutError())`` is empty), so
    the API would show an empty error. Those get the exception type and a
    short explanation instead.

    Args:
        exc: The exception that failed the scan.

    Returns:
        A non-empty, human-readable error message.

    Example:
        >>> user_error(TimeoutError())
        'TimeoutError: the target did not respond in time'
    """
    if str(exc):
        return str(exc)
    if isinstance(exc, TimeoutError):
        return "TimeoutError: the target did not respond in time"
    return f"{type(exc).__name__}: no error message"


def error_category(exc: BaseException, phase: str) -> str:
    """Map a scan failure to a fixed category that is safe for telemetry.

    Exception text can hold the target's command, URL, or server output, so
    only this category goes to logs and spans; the text stays in ``scan.error``.

    Args:
        exc: The exception that ended the scan.
        phase: Where it happened: ``connect``, ``enumerate``, or ``finish``.

    Returns:
        One of fault_injected, consent_rejected, timeout, connect_failed,
        protocol_error, internal_error.

    Example:
        >>> error_category(TimeoutError(), "connect")
        'timeout'
    """
    chain = [exc, exc.__cause__]
    if isinstance(exc, FaultInjected):
        return "fault_injected"
    if isinstance(exc, ConsentError):
        return "consent_rejected"
    if any(isinstance(e, TimeoutError) for e in chain):
        return "timeout"
    return {"connect": "connect_failed", "enumerate": "protocol_error"}.get(phase, "internal_error")


async def _execute_scan(scan_id: int, target_data: dict) -> None:
    """Connect, enumerate, run rules, and store the snapshot and findings.

    Runs as an asyncio task. ``create_task`` copies the caller's contextvars,
    so the ``scan.execute`` span is a child of the POST /api/scans span and
    the whole journey shares one trace_id.

    Uses its own session, held for the whole task so it stays bound to the
    engine that existed when the scan started.

    Args:
        scan_id: The pending scan to run.
        target_data: Target fields from the API.
    """
    transport = target_data.get("transport", "stdio")
    log = {"scan_id": scan_id, "transport": transport}
    start_time = time.monotonic()
    phase = "connect"
    with (
        _span("scan.execute", log) as span,
        database.SessionLocal() as session,
    ):
        scan = session.get(Scan, scan_id)
        try:
            logger.info("scan started", extra=log)
            scan.status = ScanStatus.RUNNING
            session.commit()
            if FAULTS["scan_failure"]:
                raise FaultInjected("Injected fault: scan failure (admin fault injection)")

            client = MCPClient()
            with _span("mcp.connect", log):
                if transport == "http":
                    await client.connect_http(target_data["url"])
                else:
                    await client.connect_stdio(
                        *resolve_stdio(target_data.get("command"), target_data.get("args"))
                    )
            phase = "enumerate"
            with _span("mcp.enumerate", log) as sp:
                snapshot = await client.enumerate()
                sp.set_attributes({
                    "tool_count": len(snapshot.tools),
                    "resource_count": len(snapshot.resources),
                    "prompt_count": len(snapshot.prompts),
                })
            await client.close()
            phase = "finish"

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
            with _span("rules.run", log) as sp:
                findings = run_all_rules(snapshot)
                sp.set_attribute("finding_count", len(findings))
            repo.add_findings(session, scan, findings)
            scan.status = ScanStatus.COMPLETED
            scan.finished_at = datetime.now(timezone.utc)
            session.commit()

            duration = time.monotonic() - start_time
            span.set_attributes({"status": "completed", "finding_count": len(findings)})
            record_scan("completed", duration, len(findings))
            logger.info("scan completed", extra={
                **log, "status": "completed", "finding_count": len(findings),
                "duration_s": round(duration, 3),
            })
        except Exception as e:
            category = error_category(e, phase)
            session.rollback()
            scan.status = ScanStatus.FAILED
            scan.error = user_error(e)  # user-facing only; never sent to telemetry
            scan.finished_at = datetime.now(timezone.utc)
            session.commit()

            duration = time.monotonic() - start_time
            span.set_attributes({"status": "failed", "error_category": category})
            span.set_status(StatusCode.ERROR, category)
            record_scan("failed", duration)
            logger.error("scan failed", extra={
                **log, "status": "failed", "error_category": category,
                "duration_s": round(duration, 3),
            })


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
    """Build the findings report for a finished (completed or failed) scan.

    A failed scan yields a report with no findings; its ``scan.status`` and
    ``scan.error`` tell the UI why.

    Args:
        scan_id: Scan primary key.

    Returns:
        ``{"scan", "findings", "summary"}``, or None if the scan is missing
        or still pending/running (the router tells 404 from 409).
    """
    with database.SessionLocal() as session:
        scan = repo.get_scan(session, scan_id)
        if scan is None or scan.status not in (ScanStatus.COMPLETED, ScanStatus.FAILED):
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
