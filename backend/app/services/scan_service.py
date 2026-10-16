"""
Scan service — creates and runs scans, produces reports.
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.mcp_client.client import MCPClient, MCPClientError
from app.rules.orchestrator import run_all_rules
from app.services.consent import validate_target, resolve_stdio

logger = logging.getLogger(__name__)

# In-memory store for Plan 1.4 (DB integration deferred to Plan 1.5 if needed)
# ponytail: replace with SQLAlchemy repository in Plan 1.5
_targets: dict[int, dict] = {}
_scans: dict[int, dict] = {}
_findings: dict[int, list[dict]] = {}
_next_id: int = 1


def _next_scan_id() -> int:
    global _next_id
    _next_id += 1
    return _next_id - 1


def _target_key(name: str) -> str:
    return name


async def create_scan(target_data: dict) -> dict:
    """Create a scan and start it as a background task.

    Returns the scan dict immediately.
    """
    # Validate consent; raises ConsentError for the router to map to 422
    validate_target(
        target_data.get("transport", "stdio"),
        target_data.get("url"),
        target_data.get("allow_external", False),
    )
    if target_data.get("transport", "stdio") == "stdio":
        resolve_stdio(target_data.get("command"), target_data.get("args"))

    # Resolve or create ScanTarget
    target_name = target_data["name"]
    target_key = _target_key(target_name)
    if target_key not in _targets:
        target_id = len(_targets) + 1
        _targets[target_key] = {
            "id": target_id,
            "name": target_name,
            "transport": target_data.get("transport", "stdio"),
            "command": target_data.get("command"),
            "args": target_data.get("args", []),
            "url": target_data.get("url"),
            "allow_external": target_data.get("allow_external", False),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        target_id = _targets[target_key]["id"]
    else:
        target_id = _targets[target_key]["id"]

    # Create Scan
    scan_id = _next_scan_id()
    now = datetime.now(timezone.utc).isoformat()
    scan = {
        "id": scan_id,
        "target_id": target_id,
        "status": "pending",
        "error": None,
        "created_at": now,
        "finished_at": None,
        "finding_count": 0,
        "target": _targets[target_key],
    }
    _scans[scan_id] = scan
    _findings[scan_id] = []

    # Run scan in background
    asyncio.create_task(_execute_scan(scan_id, target_data))

    return _scan_to_response(scan_id)


async def _execute_scan(scan_id: int, target_data: dict) -> None:
    """Execute a scan: connect, enumerate, run rules, store findings."""
    import time as time_module
    from app.metrics import record_scan_duration, record_finding_count

    scan = _scans[scan_id]
    start_time = time_module.time()
    try:
        scan["status"] = "running"

        client = MCPClient()
        transport = target_data.get("transport", "stdio")

        if transport == "http":
            await client.connect_http(target_data["url"])
        else:
            await client.connect_stdio(
                *resolve_stdio(target_data.get("command"), target_data.get("args"))
            )

        snapshot = await client.enumerate()
        await client.close()

        # Store raw snapshot for diffing
        scan["raw_snapshot"] = {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in snapshot.tools
            ],
            "resources": [
                {
                    "name": r.name,
                    "uri": r.uri,
                    "description": r.description,
                }
                for r in snapshot.resources
            ],
            "prompts": [
                {
                    "name": p.name,
                    "description": p.description,
                }
                for p in snapshot.prompts
            ],
        }

        # Run rule engine
        findings = run_all_rules(snapshot)
        _findings[scan_id] = findings

        scan["status"] = "completed"
        scan["finding_count"] = len(findings)
        scan["finished_at"] = datetime.now(timezone.utc).isoformat()

        duration = time_module.time() - start_time
        record_scan_duration(duration)
        record_finding_count(len(findings))

    except (MCPClientError, Exception) as e:
        logger.error(f"Scan {scan_id} failed: {e}")
        scan["status"] = "failed"
        scan["error"] = str(e)
        scan["finished_at"] = datetime.now(timezone.utc).isoformat()

        duration = time_module.time() - start_time
        record_scan_duration(duration)


def get_scan(scan_id: int) -> dict | None:
    """Get a scan by ID."""
    scan = _scans.get(scan_id)
    if scan is None:
        return None
    return _scan_to_response(scan_id)


def list_scans() -> list[dict]:
    """List all scans, newest first."""
    ids = sorted(_scans.keys(), reverse=True)
    return [_scan_to_response(sid) for sid in ids]


def get_report(scan_id: int) -> dict | None:
    """Get a findings report for a completed scan."""
    scan = _scans.get(scan_id)
    if scan is None:
        return None
    if scan["status"] != "completed":
        return None  # caller handles 409

    findings = _findings.get(scan_id, [])
    summary: dict[str, int] = {}
    for f in findings:
        sev = f["severity"]
        summary[sev] = summary.get(sev, 0) + 1

    return {
        "scan": _scan_to_response(scan_id),
        "findings": findings,
        "summary": summary,
    }


def diff_scans(scan_id: int, other_id: int) -> dict | None:
    """Diff findings between two scans of the same target."""
    scan1 = _scans.get(scan_id)
    scan2 = _scans.get(other_id)
    if scan1 is None or scan2 is None:
        return None

    if scan1["status"] != "completed" or scan2["status"] != "completed":
        return None  # caller handles 409

    if scan1["target_id"] != scan2["target_id"]:
        return None  # caller handles 409

    from app.services.diff_service import compute_diff
    from app.rules.registry import get_rule

    findings1 = _findings.get(scan_id, [])
    findings2 = _findings.get(other_id, [])

    diff = compute_diff(findings1, findings2)

    # Run drift detection (MCP-010)
    drift_rule = get_rule("MCP-010")
    drift: list[dict] = []
    if drift_rule is not None and hasattr(drift_rule, "diff_check"):
        from app.mcp_client.models import MCPSnapshot, MCPTool, MCPResource, MCPPrompt

        def _snapshot_from_raw(raw: dict | None) -> MCPSnapshot:
            if raw is None:
                return MCPSnapshot()
            return MCPSnapshot(
                tools=[MCPTool(**t) for t in raw.get("tools", [])],
                resources=[MCPResource(**r) for r in raw.get("resources", [])],
                prompts=[MCPPrompt(**p) for p in raw.get("prompts", [])],
            )

        drift = drift_rule.diff_check(
            findings1,
            findings2,
            _snapshot_from_raw(scan1.get("raw_snapshot")),
            _snapshot_from_raw(scan2.get("raw_snapshot")),
        )

    return {
        "scan_id": scan_id,
        "other_id": other_id,
        "added": diff["added"],
        "removed": diff["removed"],
        "unchanged": diff["unchanged"],
        "drift": drift,
    }


def _scan_to_response(scan_id: int) -> dict:
    """Build the Scan API response."""
    scan = _scans[scan_id]
    return {
        "id": scan["id"],
        "status": scan["status"],
        "error": scan.get("error"),
        "target": scan["target"],
        "created_at": scan["created_at"],
        "finished_at": scan.get("finished_at"),
        "finding_count": scan.get("finding_count", 0),
    }
