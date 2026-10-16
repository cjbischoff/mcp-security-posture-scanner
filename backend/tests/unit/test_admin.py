"""Admin fault-injection API: token auth and toggling."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import scan_service

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-token"}


@pytest.fixture(autouse=True)
def reset_fault():
    yield
    scan_service.FAULTS["scan_failure"] = False


def test_admin_routes_404_when_token_unset(monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    assert client.get("/api/admin/faults", headers=AUTH).status_code == 404
    assert client.post("/api/admin/faults/scan-failure", headers=AUTH).status_code == 404
    assert client.delete("/api/admin/faults/scan-failure", headers=AUTH).status_code == 404


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": "test-token"}])
def test_admin_routes_401_on_bad_token(monkeypatch, headers):
    monkeypatch.setenv("ADMIN_TOKEN", "test-token")
    assert client.get("/api/admin/faults", headers=headers).status_code == 401
    assert client.post("/api/admin/faults/scan-failure", headers=headers).status_code == 401
    assert scan_service.FAULTS["scan_failure"] is False


def test_admin_toggles_scan_failure_fault(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "test-token")
    assert client.get("/api/admin/faults", headers=AUTH).json() == {"scan_failure": False}
    assert client.post("/api/admin/faults/scan-failure", headers=AUTH).json() == {"scan_failure": True}
    assert scan_service.FAULTS["scan_failure"] is True
    assert client.delete("/api/admin/faults/scan-failure", headers=AUTH).json() == {"scan_failure": False}
    assert scan_service.FAULTS["scan_failure"] is False
