"""OpenTelemetry setup: traces, metrics, and logs over OTLP/HTTP.

Every app log is a JSON line on stderr with the full 32-hex ``trace_id``
and 16-hex ``span_id``. When ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set (for
example ``http://lgtm:4318``), traces, metrics, and logs are also exported
to that collector. When it is unset (tests, a deploy without a collector),
spans and metrics are still created in process but nothing is exported and
nothing extra is printed.

Redaction contract: spans, metrics, and log records carry only scan_id,
transport, status, counts, durations, and an error category. Never put a
target's command, args, URL, name, tool data, or raw error text in them.
"""
import json
import logging
import os
from datetime import datetime, timezone

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Extra LogRecord fields copied into the JSON line when present
LOG_FIELDS = ("scan_id", "status", "transport", "finding_count", "duration_s", "error_category")


class JsonFormatter(logging.Formatter):
    """Format a log record as one JSON object with the current trace context."""

    def format(self, record: logging.LogRecord) -> str:
        """Render ``record`` as JSON.

        Args:
            record: The log record.

        Returns:
            A JSON string with timestamp, level, logger, message, trace_id,
            span_id, and any of ``LOG_FIELDS`` set via ``extra=``.

        Example:
            >>> r = logging.LogRecord("app", logging.INFO, "", 1, "hi", None, None)
            >>> json.loads(JsonFormatter().format(r))["message"]
            'hi'
        """
        ctx = trace.get_current_span().get_span_context()
        line = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": format(ctx.trace_id, "032x") if ctx.is_valid else None,
            "span_id": format(ctx.span_id, "016x") if ctx.is_valid else None,
        }
        for field in LOG_FIELDS:
            if hasattr(record, field):
                line[field] = getattr(record, field)
        return json.dumps(line, default=str)


def setup_telemetry(app: FastAPI) -> None:
    """Install tracer, meter, and logger providers and instrument ``app``.

    Call once at import time, before the app serves a request. Exporters
    read ``OTEL_EXPORTER_OTLP_ENDPOINT`` and ``OTEL_METRIC_EXPORT_INTERVAL``
    from the environment.

    Args:
        app: The FastAPI application to instrument.
    """
    resource = Resource.create({
        "service.name": os.environ.get("OTEL_SERVICE_NAME", "scanner-backend"),
        "service.version": os.environ.get("APP_VERSION", "dev"),
    })
    export = bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"))

    tracer_provider = TracerProvider(resource=resource)
    readers = []
    if export:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        readers.append(PeriodicExportingMetricReader(OTLPMetricExporter()))
    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=readers))

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    if export:
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
        set_logger_provider(logger_provider)
        root.addHandler(LoggingHandler(logger_provider=logger_provider))

    FastAPIInstrumentor.instrument_app(app)
