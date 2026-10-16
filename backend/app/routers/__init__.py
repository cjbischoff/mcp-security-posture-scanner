from fastapi import APIRouter, Request
from app.routers.scans import router as scans_router

router = APIRouter()


@router.get("/health")
def health(request: Request):
    """Liveness check. Returns trace_id for request correlation."""
    from opentelemetry import trace

    span = trace.get_current_span()
    span_context = span.get_span_context() if span else None
    trace_id = ""
    if span_context and span_context.is_valid:
        trace_id = hex(span_context.trace_id)[2:16]

    return {"status": "ok", "trace_id": trace_id or None}


@router.get("/metrics")
def metrics():
    """Application metrics with traces, histograms, and request counts.

    When OTEL_EXPORTER_OTLP_ENDPOINT is set, traces export to the
    configured collector. Otherwise they print to console.
    All logs carry trace_id and span_id for request correlation.
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
