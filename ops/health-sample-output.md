# Ops: Health and Metrics Sample Output

Captured from the local Docker Compose stack on 2026-10-16, after a few
`vulnerable-demo` scans and one `scripts/trigger-alert.sh` run.

## /api/health

```json
{
  "status": "ok",
  "version": "dev",
  "trace_id": "de142565528004aebb4abc0beeedbacf"
}
```

`trace_id` is the full 32-hex W3C trace ID of the health request. Paste it
into Grafana > Explore > Tempo to see that request's trace.

## /api/metrics

In-process JSON snapshot (the OTel metrics in Prometheus are separate, see
`ops/alerts.md`):

```json
{
  "scan_count_total": 16,
  "finding_count_total": 30,
  "rule_count_total": 10,
  "request_counts": {
    "/api/health": 43,
    "/api/admin/faults/scan-failure": 5,
    "/api/admin/faults": 16,
    "/api/scans": 15,
    "/api/metrics": 1
  },
  "scan_duration": {
    "count": 14,
    "average": 0.12,
    "max": 0.56
  },
  "finding_avg_per_scan": 6.0
}
```

`scan_count_total` comes from the database; `request_counts` and
`scan_duration` are per process and reset when the backend restarts.

## Sample log line (failed scan)

```json
{"timestamp": "2026-10-16T22:19:19.844585+00:00", "level": "ERROR", "logger": "app.services.scan_service", "message": "scan failed", "trace_id": "3bdf83879ff2f78acd37ae9c6e00bb31", "span_id": "a1f58edaf9631293", "scan_id": 16, "status": "failed", "transport": "stdio", "duration_s": 0.004, "error_category": "fault_injected"}
```

## Application status

`docker compose ps`:

```text
backend   Up (healthy)
db        Up (healthy)
frontend  Up
lgtm      Up (healthy)
oncall    Up
```

## Operational notes

- Backend: `uvicorn app.main:app --host 0.0.0.0 --port 8000`, published on 127.0.0.1:8000
- Grafana (lgtm): 127.0.0.1:3001; OTLP 4317/4318 only on the compose network
- Frontend nginx proxies `/api/` to `backend:8000`, published on 127.0.0.1:3000
- `make test`: 114 backend tests, 26 frontend tests pass
