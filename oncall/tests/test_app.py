"""Integration test: real FastAPI app, fake backend + Prometheus behind httpx."""

from pathlib import Path

from fastapi.testclient import TestClient

from conftest import grafana_payload
from oncall.app import create_app


def test_firing_webhook_clears_fault_and_writes_report(config, client, world):
    api = TestClient(create_app(config, client))
    assert api.get("/health").json() == {"status": "ok"}

    resp = api.post("/alert", json=grafana_payload())
    assert resp.status_code == 202
    # TestClient runs background tasks before returning.
    assert ("DELETE", "http://backend/api/admin/faults/scan-failure") in world.requests
    assert world.faults["scan-failure"] is False
    reports = list(Path(config.incidents_dir).glob("*.md"))
    assert len(reports) == 1
    assert "resolved" in reports[0].read_text()


def test_malformed_webhook_is_rejected(config, client, world):
    api = TestClient(create_app(config, client))
    assert api.post("/alert", json={"nope": 1}).status_code == 400
    assert world.requests == []
