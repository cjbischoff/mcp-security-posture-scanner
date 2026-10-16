"""Scans survive an app restart (new engine on the same SQLite file)."""
import asyncio
import sys
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport

from app import database

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "stub_mcp_server.py"


def _client():
    from app.main import app
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _wait_completed(ac, scan_id):
    for _ in range(50):
        resp = await ac.get(f"/api/scans/{scan_id}")
        if resp.json()["status"] in ("completed", "failed"):
            return resp.json()
        await asyncio.sleep(0.2)
    pytest.fail("Scan did not finish in time")


@pytest.mark.asyncio
async def test_scan_survives_restart(app_db):
    async with _client() as ac:
        resp = await ac.post("/api/scans", json={
            "target": {"name": "demo", "transport": "stdio", "command": "vulnerable-demo"}
        })
        assert resp.status_code == 201
        scan_id = resp.json()["id"]
        before = await _wait_completed(ac, scan_id)
        assert before["status"] == "completed"
        report_before = (await ac.get(f"/api/scans/{scan_id}/report")).json()

    database.configure(app_db)  # simulate restart: fresh engine, same file

    async with _client() as ac:
        resp = await ac.get(f"/api/scans/{scan_id}")
        assert resp.status_code == 200
        assert resp.json() == before
        resp = await ac.get(f"/api/scans/{scan_id}/report")
        assert resp.status_code == 200
        assert resp.json() == report_before
        assert len(resp.json()["findings"]) > 0
        assert all("id" in f for f in resp.json()["findings"])

    from app.repositories import scans as repo
    with database.SessionLocal() as s:
        assert repo.get_scan(s, scan_id).raw_snapshot["tools"]


@pytest.mark.asyncio
async def test_same_name_different_command_is_a_different_target(app_db, monkeypatch):
    monkeypatch.setenv("ALLOW_ARBITRARY_STDIO", "true")
    async with _client() as ac:
        a = (await ac.post("/api/scans", json={"target": {
            "name": "same", "transport": "stdio", "command": "vulnerable-demo"}})).json()
        b = (await ac.post("/api/scans", json={"target": {
            "name": "same", "transport": "stdio", "command": sys.executable,
            "args": [str(FIXTURE_PATH)]}})).json()
        assert a["target"]["id"] != b["target"]["id"]
        assert b["target"]["command"] == sys.executable
        await _wait_completed(ac, a["id"])
        await _wait_completed(ac, b["id"])
        resp = await ac.get(f"/api/scans/{a['id']}/diff/{b['id']}")
        assert resp.status_code == 409
