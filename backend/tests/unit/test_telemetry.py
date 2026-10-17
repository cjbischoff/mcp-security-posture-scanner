"""Telemetry contract tests: trace IDs, JSON logs, redaction, scan metrics."""
import asyncio
import json
import logging

import httpx
import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from app import metrics as app_metrics
from app.main import app
from app.observability import JsonFormatter
from app.services import scan_service

SECRET_CMD = "/nonexistent/bin/run-sk-live-SECRETCMD123"
SECRET_ARG = "--token=hunter2SECRETARG"


async def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _drain() -> None:
    """Wait for every background scan task to finish."""
    await asyncio.gather(*list(scan_service._tasks))


@pytest.fixture
def local_mode(monkeypatch):
    monkeypatch.setenv("ALLOW_ARBITRARY_STDIO", "true")


@pytest.fixture
def meter(monkeypatch):
    """Swap the scan instruments for ones backed by an in-memory reader."""
    reader = InMemoryMetricReader()
    m = MeterProvider(metric_readers=[reader]).get_meter("test")
    monkeypatch.setattr(app_metrics, "SCANS", m.create_counter("scanner.scans"))
    monkeypatch.setattr(
        app_metrics, "SCAN_DURATION", m.create_histogram("scanner.scan.duration", unit="s")
    )
    return reader


def _points(reader: InMemoryMetricReader) -> dict:
    data = reader.get_metrics_data()
    out: dict = {}
    for rm in data.resource_metrics if data else []:
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                out[metric.name] = list(metric.data.data_points)
    return out


def test_health_creates_no_trace(spans):
    """Health checks are excluded, so they do not flood Tempo search."""
    from fastapi.testclient import TestClient

    assert TestClient(app).get("/api/health").json()["trace_id"] is None
    assert spans.get_finished_spans() == ()


def test_span_urls_drop_query_string(spans):
    """Query strings can hold user data; spans keep only the path."""
    from fastapi.testclient import TestClient

    TestClient(app).get("/api/scans?q=LEAKQUERY")
    finished = spans.get_finished_spans()
    assert finished
    assert "LEAKQUERY" not in repr([dict(s.attributes) for s in finished])
    server = next(s for s in finished if s.name == "GET /api/scans")
    assert server.attributes["http.route"] == "/api/scans"
    assert server.attributes["http.target"] == "/api/scans"


def test_json_formatter_emits_full_ids_and_scan_id():
    from opentelemetry import trace

    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("t") as span:
        record = logging.LogRecord("app.x", logging.INFO, __file__, 1, "hello", None, None)
        record.scan_id = 42
        line = json.loads(JsonFormatter().format(record))
        ctx = span.get_span_context()
    assert line["trace_id"] == format(ctx.trace_id, "032x")
    assert line["span_id"] == format(ctx.span_id, "016x")
    assert line["level"] == "INFO"
    assert line["logger"] == "app.x"
    assert line["message"] == "hello"
    assert line["scan_id"] == 42


@pytest.mark.asyncio
async def test_failed_scan_keeps_target_data_out_of_telemetry(local_mode, spans, caplog, meter):
    caplog.set_level(logging.INFO)
    async with await _client() as ac:
        resp = await ac.post("/api/scans", json={"target": {
            "name": "secret-target", "transport": "stdio",
            "command": SECRET_CMD, "args": [SECRET_ARG],
        }})
        assert resp.status_code == 201
        await _drain()
        scan = (await ac.get(f"/api/scans/{resp.json()['id']}")).json()

    assert scan["status"] == "failed"
    assert "SECRETCMD" in scan["error"]  # user-facing error is kept in the API

    fmt = JsonFormatter()
    log_text = "\n".join(fmt.format(r) for r in caplog.records)
    assert '"error_category": "connect_failed"' in log_text
    finished = spans.get_finished_spans()
    span_text = repr([(s.name, dict(s.attributes), s.status.description, s.events) for s in finished])
    for secret in ("SECRETCMD", "SECRETARG", "secret-target"):
        assert secret not in log_text
        assert secret not in span_text
    assert {"scan.execute", "mcp.connect"} <= {s.name for s in finished}
    assert _points(meter)["scanner.scans"][0].attributes == {"status": "failed"}


@pytest.mark.asyncio
async def test_scan_journey_is_one_trace(spans, meter):
    async with await _client() as ac:
        resp = await ac.post("/api/scans", json={"target": {
            "name": "demo", "transport": "stdio", "command": "vulnerable-demo"}})
        await _drain()
        scan_id = resp.json()["id"]
        assert (await ac.get(f"/api/scans/{scan_id}/report")).status_code == 200

    by_name = {s.name: s for s in spans.get_finished_spans()}
    post = by_name["POST /api/scans"]
    for name in ("scan.execute", "mcp.connect", "mcp.enumerate", "rules.run"):
        assert by_name[name].context.trace_id == post.context.trace_id, name
    execute = by_name["scan.execute"]
    assert execute.attributes["scan_id"] == scan_id
    assert execute.attributes["status"] == "completed"
    assert execute.attributes["transport"] == "stdio"
    assert execute.attributes["finding_count"] > 0

    points = _points(meter)
    assert points["scanner.scans"][0].attributes == {"status": "completed"}
    # Only the scan is recorded, not the HTTP requests around it
    assert points["scanner.scan.duration"][0].count == 1


@pytest.mark.asyncio
async def test_fault_injection_fails_scan_fast(spans, caplog, meter, monkeypatch):
    caplog.set_level(logging.INFO)
    monkeypatch.setitem(scan_service.FAULTS, "scan_failure", True)
    async with await _client() as ac:
        resp = await ac.post("/api/scans", json={"target": {
            "name": "demo", "transport": "stdio", "command": "vulnerable-demo"}})
        await _drain()
        scan = (await ac.get(f"/api/scans/{resp.json()['id']}")).json()

    assert scan["status"] == "failed"
    assert any(getattr(r, "error_category", None) == "fault_injected" for r in caplog.records)
    assert "mcp.connect" not in {s.name for s in spans.get_finished_spans()}
    assert _points(meter)["scanner.scans"][0].attributes == {"status": "failed"}
