"""Input validation for POST /api/scans: bad targets return 422, never 500."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _post(**target):
    """POST a scan with a demo stdio target, overridden by ``target``."""
    body = {"name": "demo", "transport": "stdio", "command": "vulnerable-demo", **target}
    return client.post("/api/scans", json={"target": body})


@pytest.mark.parametrize("target", [
    {"transport": "http", "command": None},  # http without url
    {"command": None},  # stdio without command
    {"name": ""},
    {"name": "   "},
    {"name": "x" * 201},
    {"name": "a\x00b"},
    {"name": "a\nb"},
    {"command": "vulnerable\x00-demo"},
    {"args": ["ok", "a\x1bb"]},
    {"transport": "http", "url": "http://localhost:1/\x00"},
    {"args": ["a"] * 51},
    {"args": ["x" * 1001]},
], ids=lambda t: repr(t)[:40])
def test_bad_target_returns_422(target):
    """Each malformed target is rejected by validation."""
    assert _post(**target).status_code == 422


def test_name_is_stripped(monkeypatch):
    """Surrounding whitespace is removed from the stored name."""
    resp = _post(name="  demo-strip  ")
    assert resp.status_code == 201
    assert resp.json()["target"]["name"] == "demo-strip"


def test_name_of_200_chars_accepted():
    """200 characters is the upper bound, inclusive."""
    assert _post(name="n" * 200).status_code == 201
