# Incident 20261016T222020Z-ScanFailureRateHigh-ceb72b

- **Alert:** ScanFailureRateHigh (page, service scanner-backend)
- **Started:** 2026-10-16T22:20:10Z
- **Handled:** 2026-10-16T22:20:20.019974+00:00 -> 2026-10-16T22:20:35.046483+00:00
- **Mode:** runbook
- **Outcome:** resolved

## Steps

1. `get_alert` {} by runbook -> `{"status": "firing", "alertname": "ScanFailureRateHigh", "service": "scanner-backend", "severity": "page", "starts_at": "2026-10-16T22:20:10Z", "values": {"A": 0.7857142857142857, "B": 1.0}, "summary": "More than half of scans failed in the last 5 minutes"}`
2. `query_metrics` {"name": "scan_failure_ratio"} by runbook -> `{"name": "scan_failure_ratio", "values": [0.7857142857142857]}`
3. `get_faults` {} by runbook -> `{"active": ["scan-failure"]}`
4. `check_health` {} by runbook -> `{"ok": true, "http_status": 200, "status": "ok", "version": "dev"}`
5. `clear_fault` {"name": "scan-failure"} by runbook -> `{"cleared": "scan-failure", "http_status": 200}`

## Verification

```json
{
  "ok": true,
  "health": {
    "ok": true,
    "http_status": 200,
    "status": "ok",
    "version": "dev"
  },
  "active_faults": [],
  "failure_ratio": [
    0.7857142857142858
  ]
}
```
