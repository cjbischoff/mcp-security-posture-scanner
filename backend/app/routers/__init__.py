import os

from fastapi import APIRouter, Request
from app.routers.admin import router as admin_router
from app.routers.scans import router as scans_router

router = APIRouter()


@router.get("/health")
def health(request: Request):
    """Liveness check.

    Args:
        request: The incoming request (unused).

    Returns:
        status, build version, and the full 32-hex trace_id of this request,
        so a caller can look the request up in Tempo.
    """
    from opentelemetry import trace

    ctx = trace.get_current_span().get_span_context()
    return {
        "status": "ok",
        "version": os.environ.get("APP_VERSION", "dev"),
        "trace_id": format(ctx.trace_id, "032x") if ctx.is_valid else None,
    }


@router.get("/metrics")
def metrics():
    """Application metrics with traces, histograms, and request counts.

    In-process JSON snapshot. The OTel metrics (scanner_scans_total etc.)
    export to the collector when OTEL_EXPORTER_OTLP_ENDPOINT is set.

    Returns:
        Scan, finding, and rule totals plus request counts and scan durations.
    """
    from app.services.scan_service import list_scans as get_scans
    from app.metrics import get_enhanced_metrics

    scans = get_scans()
    finding_count = sum(s.get("finding_count", 0) for s in scans)
    rule_count = 10

    result = {
        "scan_count_total": len(scans),
        "finding_count_total": finding_count,
        "rule_count_total": rule_count,
    }

    # Include enhanced metrics
    enhanced = get_enhanced_metrics()
    result["request_counts"] = enhanced["request_count_total"]
    result["scan_duration"] = enhanced["scan_duration_seconds"]
    result["finding_avg_per_scan"] = enhanced["finding_counts"]["average"]

    return result


# Include sub-routers
router.include_router(scans_router)
router.include_router(admin_router)
