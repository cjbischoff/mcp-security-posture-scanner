"""
Enhanced metrics for the MCP scanner.

Tracks scan count, finding count, scan duration histogram,
and request counts by endpoint.
"""
import time
from collections import defaultdict
from typing import Any
from fastapi import Request, Response
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource


# In-memory counters for the /api/metrics endpoint
_request_counts: dict[str, int] = defaultdict(int)
_scan_durations: list[float] = []
_finding_counts: list[int] = []

# OTel instruments (set up lazily)
_meter: Any = None
_scan_duration_histogram: Any = None


def setup_metrics(settings) -> None:
    """Configure OTel metrics pipeline."""
    global _meter, _scan_duration_histogram

    resource = Resource.create({
        "service.name": "mcp-scanner-backend",
        "service.version": "0.1.0",
    })

    reader = PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=5000)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)

    _meter = metrics.get_meter(__name__)
    _scan_duration_histogram = _meter.create_histogram(
        name="scan.duration.seconds",
        description="Time to complete a scan",
        unit="s",
    )


async def metrics_middleware(request: Request, call_next):
    """Middleware that counts requests and records scan durations."""
    start = time.time()
    response: Response = await call_next(request)

    # Count by route
    route = request.url.path
    _request_counts[route] += 1

    # Record scan duration from response headers
    duration = time.time() - start
    if _scan_duration_histogram:
        _scan_duration_histogram.record(duration, {"route": route})

    return response


def record_scan_duration(seconds: float) -> None:
    """Record a completed scan's duration for metrics."""
    _scan_durations.append(seconds)
    if _scan_duration_histogram:
        _scan_duration_histogram.record(seconds, {"route": "scan_execution"})


def record_finding_count(count: int) -> None:
    """Record finding count from a completed scan."""
    _finding_counts.append(count)


def get_enhanced_metrics():
    """Return current metrics snapshot."""
    return {
        "request_count_total": dict(_request_counts),
        "scan_duration_seconds": {
            "count": len(_scan_durations),
            "average": round(sum(_scan_durations) / len(_scan_durations), 2) if _scan_durations else 0,
            "max": round(max(_scan_durations), 2) if _scan_durations else 0,
        },
        "finding_counts": {
            "count": len(_finding_counts),
            "average": round(sum(_finding_counts) / len(_finding_counts), 1) if _finding_counts else 0,
        },
    }
