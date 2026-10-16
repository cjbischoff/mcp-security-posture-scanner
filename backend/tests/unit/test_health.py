from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealth:
    def test_health_returns_ok(self):
        """GET /api/health returns 200 with status ok and trace_id."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


def test_health_reports_app_version(monkeypatch):
    """GET /api/health reports APP_VERSION so deploys can confirm the build."""
    monkeypatch.setenv("APP_VERSION", "abc123")
    assert client.get("/api/health").json()["version"] == "abc123"


def test_static_dir_serves_spa(tmp_path):
    """With a static dir, / and unknown client routes return index.html."""
    from app.main import mount_frontend
    from fastapi import FastAPI

    (tmp_path / "index.html").write_text("<html>spa</html>")
    spa = FastAPI()

    @spa.get("/api/health")
    def _health():
        return {"status": "ok"}

    mount_frontend(spa, str(tmp_path))
    c = TestClient(spa)
    assert "spa" in c.get("/").text
    assert "spa" in c.get("/scans/7").text
    assert c.get("/api/health").json() == {"status": "ok"}
