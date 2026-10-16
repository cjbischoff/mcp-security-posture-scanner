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

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "stub_mcp_server.py"


async def smoke_test() -> bool:
    from app.services.scan_service import create_scan, get_scan, get_report

    # Create and run a scan
    result = await create_scan({
        "name": "smoke-test",
        "transport": "stdio",
        "command": sys.executable,
        "args": [str(FIXTURE_PATH)],
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
