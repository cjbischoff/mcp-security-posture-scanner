"""Integration test: real FastAPI app, fake backend + Prometheus behind httpx."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import grafana_payload
from oncall.app import create_app

AUTH = {"Authorization": "Bearer hook-secret"}


def test_firing_webhook_clears_fault_and_writes_report(config, client, world):
    api = TestClient(create_app(config, client))
    assert api.get("/health").json() == {"status": "ok"}

    resp = api.post("/alert", json=grafana_payload(), headers=AUTH)
    assert resp.status_code == 202
    # TestClient runs background tasks before returning.
    assert ("DELETE", "http://backend/api/admin/faults/scan-failure") in world.requests
    assert world.faults["scan-failure"] is False
    reports = list(Path(config.incidents_dir).glob("*.md"))
    assert len(reports) == 1
    assert "resolved" in reports[0].read_text()


def test_malformed_webhook_is_rejected(config, client, world):
    api = TestClient(create_app(config, client))
    assert api.post("/alert", json={"nope": 1}, headers=AUTH).status_code == 400
    assert world.requests == []


@pytest.mark.parametrize("headers", [
    {}, {"Authorization": "Bearer wrong"}, {"Authorization": "hook-secret"},
])
def test_alert_without_valid_token_is_401_and_creates_no_incident(
        config, client, world, headers):
    api = TestClient(create_app(config, client))
    assert api.post("/alert", json=grafana_payload(), headers=headers).status_code == 401
    assert world.requests == []
    assert not Path(config.incidents_dir).exists()


def test_alert_is_401_when_server_token_unset(config, client, world):
    config.oncall_webhook_token = ""
    api = TestClient(create_app(config, client))
    assert api.post("/alert", json=grafana_payload(),
                    headers={"Authorization": "Bearer "}).status_code == 401
    assert world.requests == []
