# Alerts

Grafana unified alerting, file-provisioned from `ops/grafana/alerting.yaml`
into the `lgtm` container. View it in Grafana > Alerting > Alert rules
(folder **Scanner**).

## ScanFailureRateHigh

| Field | Value |
|---|---|
| Condition | Failed scans / all finished scans over the last 5m **> 0.5**, only when at least **3** scans finished in that window |
| Evaluation | every 30s, pending period (`for`) 1m |
| Labels | `service=scanner-backend`, `severity=page` |
| No data | `OK` (no scans is not an incident) |
| Contact point | `oncall-webhook`: Grafana webhook JSON, `POST http://oncall:8080/alert` |
| Notification policy | group by `alertname, service`, group_wait 10s, repeat 1h |
| Dashboard | `scanner-scan-journey`, panel 2 (failed ratio) |

Query (Prometheus datasource, instant):

```promql
(sum(increase(scanner_scans_total{status="failed"}[5m]))
 / sum(increase(scanner_scans_total[5m])))
and on() (sum(increase(scanner_scans_total[5m])) >= 3)
```

Both `status` series are exported at 0 from startup
(`init_scan_series()` in `app/metrics.py`). `increase()` ignores a series'
first sample, so without this the first failures of an incident would not be
counted.

### Why this is user impact

A failed scan is a user who submitted a target and got an error instead of a
findings report. The alert counts outcomes of the main user journey, not host
resources like CPU or memory. The minimum of 3 scans stops one failed scan on
a quiet system from paging.

## Metric names (verified in Prometheus)

Read from the running LGTM Prometheus on 2026-10-16
(`/api/v1/label/__name__/values`):

| OTel instrument | Prometheus series |
|---|---|
| `scanner.scans` (counter, attr `status` = `completed`/`failed`) | `scanner_scans_total{status="completed"\|"failed", job="scanner-backend", service_name="scanner-backend"}` |
| `scanner.scan.duration` (histogram, unit `s`, scans only) | `scanner_scan_duration_seconds_bucket`, `_count`, `_sum` |
| FastAPI instrumentation | `http_server_duration_milliseconds_bucket/_count/_sum`, `http_server_active_requests`, `http_server_request_size_bytes_*`, `http_server_response_size_bytes_*` |

## Trigger it (fault injection)

```bash
docker compose up --build -d
scripts/trigger-alert.sh        # fault on + 12 vulnerable-demo scans, 2s apart
scripts/trigger-alert.sh --off  # fault off
```

The script calls `POST /api/admin/faults/scan-failure` with
`Authorization: Bearer $ADMIN_TOKEN` (from `.env`, default
`local-admin-token`; see `.env.example`). While the fault is on, every new
scan fails at once with `error_category=fault_injected`. Admin routes return
404 when `ADMIN_TOKEN` is unset and 401 for a wrong or missing token.

Watch the state:

```bash
curl -s http://127.0.0.1:3001/api/prometheus/grafana/api/v1/alerts | jq '.data.alerts[] | {state, value}'
curl -s http://127.0.0.1:3001/api/alertmanager/grafana/api/v2/alerts | jq '.[] | {status: .status.state, receivers}'
```

Verified 2026-10-16: trigger at 22:19:09Z, rule `Pending` at 22:19:10Z,
`Alerting` at 22:20:10Z (value 1.0), active in Alertmanager with receiver
`oncall-webhook`, and the `oncall` service logged `POST /alert 202` at
22:20:20Z.

**Timing depends on recent traffic.** The rule fires only when failed scans
are more than half of all scans in the last 5 minutes. Good scans run just
before the trigger count too. On 2026-10-16 23:26Z, 6 good scans plus 6
failed scans gave a ratio of exactly 0.5, so the rule went `Pending` only
after the good scans left the window (+193 s) and `Firing` at +254 s. The
on-call agent then cleared the fault in 10 s (incident
`20261016T233020Z-ScanFailureRateHigh-704e0d`). The script now sends 12
scans by default so a demo does not wait for that.
