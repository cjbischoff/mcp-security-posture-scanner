#!/usr/bin/env python3
"""
Functional smoke test for the MCP scanner backend.

Starts the stub fixture server, runs a full scan, and verifies
findings are returned. Exits 0 on success, 1 with details on failure.

Usage:
    python scripts/smoke_test.py
"""
import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

async def smoke_test() -> bool:
    """Run one scan against the bundled fixture in a throwaway SQLite DB.

    Returns:
        True if the scan completed with findings.
    """
    import tempfile
    from app import database, models  # noqa: F401 -- registers models
    from app.services.scan_service import create_scan, get_scan, get_report

    db_dir = tempfile.mkdtemp()
    database.Base.metadata.create_all(database.configure(f"sqlite:///{db_dir}/smoke.db"))

    # Create and run a scan
    result = await create_scan({
        "name": "smoke-test",
        "transport": "stdio",
        "command": "vulnerable-demo",
    })
    scan_id = result["id"]
    print(f"Scan {scan_id} created (status: {result['status']})")

    # Wait for completion
    for _ in range(30):
        await asyncio.sleep(0.3)
        scan = get_scan(scan_id)
        if scan is None:
            print("ERROR: Scan not found")
            return False
        if scan["status"] in ("completed", "failed"):
            break

    if scan["status"] == "failed":
        print(f"ERROR: Scan failed: {scan.get('error', 'unknown')}")
        return False

    if scan["status"] != "completed":
        print("ERROR: Scan did not complete")
        return False

    print(f"Scan completed with {scan['finding_count']} findings")

    # Get report
    report = get_report(scan_id)
    if report is None:
        print("ERROR: Report not available")
        return False

    print(f"Report summary: {json.dumps(report['summary'], indent=2)}")

    severity_groups = report["summary"]
    total = sum(severity_groups.values())
    print(f"Total findings: {total}")
    print(f"Severity breakdown: {severity_groups}")

    if total == 0:
        print("ERROR: No findings detected — stub fixture should produce findings")
        return False

    # List rule IDs found
    rule_ids = sorted({f["rule_id"] for f in report["findings"]})
    print(f"Rules triggered: {', '.join(rule_ids)}")

    print("\n✓ Smoke test passed")
    return True


def main():
    success = asyncio.run(smoke_test())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
