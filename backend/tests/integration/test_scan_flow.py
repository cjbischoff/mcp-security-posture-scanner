"""
End-to-end integration tests for the full scan → report → diff workflow.

Uses httpx.AsyncClient with the FastAPI ASGI app directly.
"""
import sys
import asyncio
import pytest
import httpx
from pathlib import Path

from tests.fixtures.stub_mcp_server import EXPECTED_FINDINGS as FIXTURE_FINDINGS

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "stub_mcp_server.py"
BASE_URL = "http://test"


async def _client():
    from app.main import app
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url=BASE_URL)


async def _wait_completed(ac: httpx.AsyncClient, scan_id: int, timeout: float = 9.0) -> dict:
    """Poll a scan until it is completed; fail the test with a clear message if not.

    Args:
        ac: Client bound to the app.
        scan_id: Scan to poll.
        timeout: Seconds to wait.

    Returns:
        The completed scan's JSON.
    """
    for _ in range(int(timeout / 0.3)):
        scan = (await ac.get(f"/api/scans/{scan_id}")).json()
        if scan["status"] == "completed":
            return scan
        if scan["status"] == "failed":
            pytest.fail(f"scan {scan_id} failed: {scan.get('error')}")
        await asyncio.sleep(0.3)
    pytest.fail(f"scan {scan_id} not completed after {timeout}s (status {scan['status']})")


@pytest.fixture(autouse=True)
def local_mode(monkeypatch):
    """These tests run the fixture via sys.executable, which needs local mode."""
    monkeypatch.setenv("ALLOW_ARBITRARY_STDIO", "true")


@pytest.mark.asyncio(loop_scope="module")
async def test_public_mode_rejects_arbitrary_command(monkeypatch):
    monkeypatch.delenv("ALLOW_ARBITRARY_STDIO")
    async with await _client() as ac:
        resp = await ac.post("/api/scans", json={
            "target": {"name": "rce", "transport": "stdio",
                       "command": "touch", "args": ["/tmp/x"]}
        })
        assert resp.status_code == 422


@pytest.mark.asyncio(loop_scope="module")
async def test_public_mode_accepts_fixture_name(monkeypatch):
    monkeypatch.delenv("ALLOW_ARBITRARY_STDIO")
    async with await _client() as ac:
        resp = await ac.post("/api/scans", json={
            "target": {"name": "demo", "transport": "stdio", "command": "vulnerable-demo"}
        })
        assert resp.status_code == 201


@pytest.mark.asyncio(loop_scope="module")
async def test_health():
    async with await _client() as ac:
        resp = await ac.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio(loop_scope="module")
async def test_submit_scan_returns_id():
    async with await _client() as ac:
        resp = await ac.post("/api/scans", json={
            "target": {
                "name": "async-int-test",
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(FIXTURE_PATH)],
            }
        })
        assert resp.status_code == 201
        assert "id" in resp.json()


@pytest.mark.asyncio(loop_scope="module")
async def test_submit_and_poll_scan():
    async with await _client() as ac:
        resp = await ac.post("/api/scans", json={
            "target": {
                "name": "async-poll-test",
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(FIXTURE_PATH)],
            }
        })
        assert resp.status_code == 201
        scan_id = resp.json()["id"]

        scan = await _wait_completed(ac, scan_id)
        assert scan["finding_count"] > 0


@pytest.mark.asyncio(loop_scope="module")
async def test_get_report():
    async with await _client() as ac:
        resp = await ac.post("/api/scans", json={
            "target": {
                "name": "async-report-test",
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(FIXTURE_PATH)],
            }
        })
        scan_id = resp.json()["id"]

        await _wait_completed(ac, scan_id)

        resp = await ac.get(f"/api/scans/{scan_id}/report")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["findings"]) > 0


@pytest.mark.asyncio(loop_scope="module")
async def test_diff_two_scans():
    async with await _client() as ac:
        # Scan 1
        resp = await ac.post("/api/scans", json={
            "target": {
                "name": "async-diff-target",
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(FIXTURE_PATH)],
            }
        })
        scan1_id = resp.json()["id"]
        await _wait_completed(ac, scan1_id)

        # Scan 2 (same target name)
        resp = await ac.post("/api/scans", json={
            "target": {
                "name": "async-diff-target",
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(FIXTURE_PATH)],
            }
        })
        scan2_id = resp.json()["id"]
        await _wait_completed(ac, scan2_id)

        # Diff
        resp = await ac.get(f"/api/scans/{scan1_id}/diff/{scan2_id}")
        assert resp.status_code == 200
        data = resp.json()
        # Same fixture twice: nothing added, removed, or drifted
        assert data["added"] == []
        assert data["removed"] == []
        assert data["drift"] == []
        assert {(f["rule_id"], f["subject"]) for f in data["unchanged"]} == FIXTURE_FINDINGS


@pytest.mark.asyncio(loop_scope="module")
async def test_external_rejected_without_consent():
    async with await _client() as ac:
        resp = await ac.post("/api/scans", json={
            "target": {
                "name": "ext-no-consent",
                "transport": "http",
                "url": "http://example.com/mcp",
            }
        })
        assert resp.status_code == 422


@pytest.mark.asyncio(loop_scope="module")
async def test_external_allowed_with_consent(monkeypatch):
    from app.mcp_client.client import MCPClient, MCPClientError

    async def no_network(self, url):
        raise MCPClientError("network disabled in tests")

    # The scan task would connect to the URL; keep the test off the network
    monkeypatch.setattr(MCPClient, "connect_http", no_network)
    async with await _client() as ac:
        resp = await ac.post("/api/scans", json={
            "target": {
                "name": "ext-with-consent",
                "transport": "http",
                "url": "http://example.com/mcp",
                "allow_external": True,
            }
        })
        assert resp.status_code == 201
