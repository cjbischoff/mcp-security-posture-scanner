"""
End-to-end integration tests for the full scan → report → diff workflow.

Uses httpx.AsyncClient with the FastAPI ASGI app directly.
"""
import sys
import asyncio
import pytest
import httpx
from pathlib import Path

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "stub_mcp_server.py"
BASE_URL = "http://test"


@pytest.fixture(scope="module")
def event_loop():
    """Single event loop for all tests in this module."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def _client():
    from app.main import app
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url=BASE_URL)


@pytest.fixture(autouse=True)
def local_mode(monkeypatch):
    """These tests run the fixture via sys.executable, which needs local mode."""
    monkeypatch.setenv("ALLOW_ARBITRARY_STDIO", "true")


@pytest.mark.asyncio(scope="module")
async def test_public_mode_rejects_arbitrary_command(monkeypatch):
    monkeypatch.delenv("ALLOW_ARBITRARY_STDIO")
    async with await _client() as ac:
        resp = await ac.post("/api/scans", json={
            "target": {"name": "rce", "transport": "stdio",
                       "command": "touch", "args": ["/tmp/x"]}
        })
        assert resp.status_code == 422


@pytest.mark.asyncio(scope="module")
async def test_public_mode_accepts_fixture_name(monkeypatch):
    monkeypatch.delenv("ALLOW_ARBITRARY_STDIO")
    async with await _client() as ac:
        resp = await ac.post("/api/scans", json={
            "target": {"name": "demo", "transport": "stdio", "command": "vulnerable-demo"}
        })
        assert resp.status_code == 201


@pytest.mark.asyncio(scope="module")
async def test_health():
    async with await _client() as ac:
        resp = await ac.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio(scope="module")
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


@pytest.mark.asyncio(scope="module")
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

        for _ in range(30):
            resp = await ac.get(f"/api/scans/{scan_id}")
            status = resp.json()["status"]
            if status == "completed":
                break
            await asyncio.sleep(0.3)
        else:
            pytest.fail("Scan did not complete in time")

        assert resp.json()["finding_count"] > 0


@pytest.mark.asyncio(scope="module")
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

        for _ in range(30):
            resp = await ac.get(f"/api/scans/{scan_id}")
            if resp.json()["status"] == "completed":
                break
            await asyncio.sleep(0.3)

        resp = await ac.get(f"/api/scans/{scan_id}/report")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["findings"]) > 0


@pytest.mark.asyncio(scope="module")
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
        for _ in range(30):
            r = await ac.get(f"/api/scans/{scan1_id}")
            if r.json()["status"] == "completed":
                break
            await asyncio.sleep(0.3)

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
        for _ in range(30):
            r = await ac.get(f"/api/scans/{scan2_id}")
            if r.json()["status"] == "completed":
                break
            await asyncio.sleep(0.3)

        # Diff
        resp = await ac.get(f"/api/scans/{scan1_id}/diff/{scan2_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "added" in data
        assert "removed" in data
        assert "unchanged" in data
        assert "drift" in data


@pytest.mark.asyncio(scope="module")
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


@pytest.mark.asyncio(scope="module")
async def test_external_allowed_with_consent():
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
