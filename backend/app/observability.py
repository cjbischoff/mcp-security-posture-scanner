"""
OpenTelemetry observability setup.

Instruments FastAPI with auto-traces, configures structured logging
with trace IDs, and sets up a metrics pipeline.
"""
import logging
import os

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.config import Settings


def setup_observability(app, settings: Settings) -> None:
    """Configure OpenTelemetry for the FastAPI application.

    Uses OTLP exporter if OTEL_EXPORTER_OTLP_ENDPOINT is set,
    otherwise falls back to console export for local development.
    """
    resource = Resource.create({
        "service.name": "mcp-scanner-backend",
        "service.version": "0.1.0",
        "deployment.environment": "development" if settings.debug else "production",
    })

    tracer_provider = TracerProvider(resource=resource)

    # Export traces via OTLP if configured, otherwise console
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    else:
        span_exporter = ConsoleSpanExporter()

    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Configure structured logging with trace ID injection
    _setup_logging()

    app.state.tracer_provider = tracer_provider


def _setup_logging() -> None:
    """Configure logging to include trace_id and span_id."""
    handler = logging.StreamHandler()
    handler.setFormatter(_TraceLogFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


class _TraceLogFormatter(logging.Formatter):
    """Log formatter that injects current trace/span IDs."""

    def format(self, record: logging.LogRecord) -> str:
        span = trace.get_current_span()
        span_context = span.get_span_context() if span else None

        trace_id = ""
        span_id = ""
        if span_context and span_context.is_valid:
            trace_id = hex(span_context.trace_id)[2:16]
            span_id = hex(span_context.span_id)[2:8]

        record.trace_id = trace_id
        record.span_id = span_id

        return (
            f"[{self.formatTime(record)}] "
            f"trace={trace_id} span={span_id} "
            f"{record.levelname} {record.name}: {record.getMessage()}"
        )
