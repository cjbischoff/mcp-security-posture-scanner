# Observability

The scan journey (submit scan, background scan, report) is instrumented with
OpenTelemetry. Traces, metrics, and logs go over OTLP/HTTP to the `lgtm`
container (`grafana/otel-lgtm:0.36.0`: OTel collector, Tempo, Loki,
Prometheus, Grafana). All three signals carry the same `trace_id`.

## Open Grafana

```bash
docker compose up --build -d
open http://127.0.0.1:3001        # anonymous admin, local only
```

Dashboard: **Scanner > Scanner — scan journey** (uid `scanner-scan-journey`).
It shows scan rate by status, the failed-scan ratio (the alert input), p95
scan duration, a table of recent `scan.execute` traces, and the scan logs.
Click a trace ID in the table, or the `trace_id` field on a log line, to open
the trace in Tempo.

## Find one request in all three signals

1. Get a trace ID. Every JSON log line written inside a request or scan has
   one (`/api/health` is not traced, so its `trace_id` is `null`):

   ```bash
   docker compose logs backend | grep '"scan completed"' | tail -1
   # {"level": "INFO", "message": "scan completed", "trace_id": "e17d2ab0...", "scan_id": 5, ...}
   ```

2. **Trace (Tempo):** Grafana > Explore > Tempo > TraceQL, paste the ID.
   A scan trace has `POST /api/scans` > `scan.execute` > `mcp.connect`,
   `mcp.enumerate`, `rules.run`. The background task runs in an
   `asyncio.create_task`, which copies the request's context, so the scan
   stays in the POST request's trace.

3. **Logs (Loki):** Explore > Loki:
   `{service_name="scanner-backend"} | trace_id="<id>"`
   (`trace_id`, `span_id`, `scan_id` are structured metadata).

4. **Metrics (Prometheus):** Explore > Prometheus: `scanner_scans_total`,
   `scanner_scan_duration_seconds_bucket`. Prometheus listens on 9090 inside
   the container only: `docker compose exec lgtm curl -s 'localhost:9090/api/v1/query?query=scanner_scans_total'`.

Same checks from the shell, through the Grafana datasource proxy:

```bash
T=<trace_id>; G=http://127.0.0.1:3001/api/datasources/proxy/uid
curl -s "$G/tempo/api/traces/$T" | jq '[.. | .name? // empty] | unique'
curl -sG "$G/loki/loki/api/v1/query_range" \
  --data-urlencode "query={service_name=\"scanner-backend\"} | trace_id=\"$T\"" \
  --data-urlencode "start=$(( $(date +%s) - 3600 ))000000000" | jq '.data.result[].values[][1]'
```

Verified 2026-10-16: trace `e17d2ab050c445265b391fb7dccdf306` (scan 5) had
spans `POST /api/scans`, `scan.execute`, `mcp.connect`, `mcp.enumerate`,
`rules.run` in Tempo and the log lines `scan submitted`, `scan started`,
`scan completed` in Loki.

## Signals

| Signal | What | Where in code |
|---|---|---|
| Traces | FastAPI auto-instrumentation (one span per request) plus `scan.execute`, `mcp.connect`, `mcp.enumerate`, `rules.run` | `app/observability.py`, `app/services/scan_service.py` |
| Metrics | `scanner_scans_total{status}`, `scanner_scan_duration_seconds_*`, `http_server_duration_milliseconds_*` and other HTTP server metrics | `app/metrics.py` |
| Logs | stdlib `logging`, one JSON object per line on stderr, also exported to Loki | `JsonFormatter` in `app/observability.py` |

Log fields: `timestamp`, `level`, `logger`, `message`, `trace_id` (32 hex),
`span_id` (16 hex), and when relevant `scan_id`, `transport`, `status`,
`finding_count`, `duration_s`, `error_category`.

Span attributes: `scan_id`, `transport`, `status`, `finding_count`,
`error_category`, and on `mcp.enumerate` the tool/resource/prompt counts.

## What is redacted

Target data never goes to telemetry. That covers the stdio command and args,
the URL, the target name, tool/resource/prompt names, descriptions and
schemas, and raw error text (it can quote the command or server output).

- A failed scan logs and tags its span with an `error_category`:
  `connect_failed`, `protocol_error`, `timeout`, `consent_rejected`,
  `fault_injected`, or `internal_error`. The full error text is still stored
  in `scan.error` and returned by the API to the user who ran the scan.
- Spans are started with `record_exception=False` and
  `set_status_on_exception=False`, so exception messages do not become span
  events or status descriptions. The span status description is the category.
- HTTP spans hold method, route, status code, and peer address. Request
  bodies and headers (including `Authorization`) are not captured.
- `http.url` and `http.target` are rewritten without the query string (a
  `server_request_hook` in `app/observability.py`); `http.route` keeps the
  route template. Test: `test_span_urls_drop_query_string`.
- `/api/health` is not traced (`OTEL_PYTHON_FASTAPI_EXCLUDED_URLS`, default
  `api/health`), so Render health checks do not bury scan traces. Test:
  `test_health_creates_no_trace`.
- uvicorn runs with `--no-access-log`: its access log prints the raw path
  with the query string. The app's JSON logs are kept.
- Test: `tests/unit/test_telemetry.py::test_failed_scan_keeps_target_data_out_of_telemetry`
  submits a scan whose command and args hold secret-looking strings and
  asserts that no log record or span contains them.

Telemetry stays on the host: the collector and its storage run in the local
`lgtm` container (volume `lgtmdata`). Nothing is sent to a hosted service.

## Without a collector

If `OTEL_EXPORTER_OTLP_ENDPOINT` is unset (unit tests, or a Render service
without the Grafana Cloud settings),
spans and metrics are still created in process so trace IDs exist, but
nothing is exported and nothing extra is printed. Logs still go to stderr as
JSON.

## Config

| Env var | Compose value | Purpose |
|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://lgtm:4318` | OTLP/HTTP collector; unset = no export |
| `OTEL_SERVICE_NAME` | `scanner-backend` | `service.name`, becomes `service_name`/`job` labels |
| `OTEL_METRIC_EXPORT_INTERVAL` | `10000` | Metric export period in ms (SDK default 60000) |

## Two destinations: local and Grafana Cloud

The backend code is the same in both places. Only the environment decides
where telemetry goes. The OTel SDK reads `OTEL_EXPORTER_OTLP_ENDPOINT` and
`OTEL_EXPORTER_OTLP_HEADERS` itself.

| Where it runs | Telemetry goes to | Set by |
|---|---|---|
| `docker compose up` (local) | `lgtm` container, Grafana at http://127.0.0.1:3001 | `docker-compose.yml` |
| Render dev and prod | Grafana Cloud (one stack for both) | Render service env vars |
| Unit tests, any env without the endpoint | Nowhere (no export) | unset |

### Grafana Cloud setup (once)

1. In the Grafana Cloud stack: **Connections → OpenTelemetry (OTLP)**. Copy
   the OTLP endpoint, the instance ID, and create a token with write scopes.
2. On each Render service, set:

   | Env var | Value |
   |---|---|
   | `OTEL_EXPORTER_OTLP_ENDPOINT` | `https://otlp-gateway-prod-<region>.grafana.net/otlp` |
   | `OTEL_EXPORTER_OTLP_HEADERS` | `Authorization=Basic%20<base64 of instanceID:token>` |
   | `OTEL_SERVICE_NAME` | `scanner-backend` |
   | `OTEL_RESOURCE_ATTRIBUTES` | `deployment.environment=dev` or `=prod` |

   Make the header value with
   `printf 'Basic %s' "$(printf '%s:%s' "$ID" "$TOKEN" | base64)" | sed 's/ /%20/'`.
   Never commit it.
3. Create a service account (**Administration → Service accounts**, role
   Editor) with a token, then push the dashboard and the alert rule:

   ```bash
   GRAFANA_URL=https://<stack>.grafana.net GRAFANA_SA_TOKEN=<token> ops/grafana/push-to-cloud.sh
   ```

   The script finds the stack's own data source UIDs, so the same
   `ops/grafana/` files serve both destinations. Running it again updates
   them in place.

### Limits

- In Grafana Cloud the alert goes to the stack's default notification policy
  (email to the account owner). The on-call agent runs only in local
  Compose, so the alert → agent → fix loop is demonstrated locally.
- Dev and prod share one stack. The alert and dashboard sum both
  environments; filter by `deployment_environment` in Explore.
- Grafana Cloud free tier: 14-day retention, 10k active metric series,
  50 GB/month each of logs and traces (checked 2026-10-16,
  https://grafana.com/pricing/).

### Automated setup (used for this project)

`ops/cloud-setup.sh` does steps 1-3 through the Grafana Cloud and Render APIs.
It reads `GRAFANA_CLOUD_TOKEN` (Cloud access policy token, scopes
`stacks:read` + `accesspolicies:read/write/delete`), `GRAFANA_SA_TOKEN`,
`GRAFANA_STACK`, and `RENDER_API_KEY` from `.env`, and prints no secrets.
It creates a `scanner-otlp` policy (write-only telemetry scopes), makes a new
OTLP token, tests it with one span, merges the `OTEL_*` vars into each Render
service (other vars stay), redeploys the running SHA, and pushes the dashboard
and alert. Running it again rotates the OTLP token and deletes the old one.

`ops/cloud-verify.sh` sends one scan to dev and prod and queries Grafana Cloud.
Verified 2026-10-17: traces `97a8c6b7…` (dev) and `c0cfc3a7…` (prod) in Tempo,
`scanner_scans_total` per `deployment_environment` in Prometheus, and Loki
lines carrying the same trace IDs.
