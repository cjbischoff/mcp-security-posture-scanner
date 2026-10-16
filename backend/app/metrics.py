"""Scan metrics: OTel instruments plus an in-memory snapshot for /api/metrics.

OTel names (Prometheus names in LGTM, see ops/alerts.md):

- ``scanner.scans`` counter, attribute ``status`` = completed|failed
  (``scanner_scans_total``)
- ``scanner.scan.duration`` histogram in seconds, one point per scan
  (``scanner_scan_duration_seconds``)

HTTP server metrics come from the FastAPI instrumentation.
"""
from collections import defaultdict

from fastapi import Request, Response
from opentelemetry import metrics

_meter = metrics.get_meter("scanner")
SCANS = _meter.create_counter("scanner.scans", description="Finished scans by status")
SCAN_DURATION = _meter.create_histogram(
    "scanner.scan.duration",
    unit="s",
    description="Time from scan start to finish",
    explicit_bucket_boundaries_advisory=[0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60],
)

# In-memory values for the /api/metrics JSON endpoint
_request_counts: dict[str, int] = defaultdict(int)
_scan_durations: list[float] = []
_finding_counts: list[int] = []


async def metrics_middleware(request: Request, call_next) -> Response:
    """Count requests by path for the /api/metrics JSON endpoint.

    Args:
        request: The incoming request.
        call_next: The next ASGI handler.

    Returns:
        The response from ``call_next``.
    """
    response: Response = await call_next(request)
    _request_counts[request.url.path] += 1
    return response


def init_scan_series() -> None:
    """Export both ``status`` series at 0 from startup.

    Prometheus ``increase()`` ignores a series' first sample, so a failed
    series that first appears mid-incident would hide its first failures.
    Call after the meter provider is installed; earlier values are dropped.
    """
    for status in ("completed", "failed"):
        SCANS.add(0, {"status": status})


def record_scan(status: str, seconds: float, finding_count: int | None = None) -> None:
    """Record one finished scan.

    Args:
        status: ``completed`` or ``failed``.
        seconds: Scan duration.
        finding_count: Findings produced, for completed scans.
    """
    SCANS.add(1, {"status": status})
    SCAN_DURATION.record(seconds, {"status": status})
    _scan_durations.append(seconds)
    if finding_count is not None:
        _finding_counts.append(finding_count)


def get_enhanced_metrics() -> dict:
    """Return the in-memory metrics snapshot.

    Returns:
        Request counts by path, scan duration stats, and finding stats.
    """
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
