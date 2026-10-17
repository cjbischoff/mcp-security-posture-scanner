# Incident 20261017T160850Z-ScanFailureRateHigh-bc7a2c

- **Alert:** ScanFailureRateHigh (page, service scanner-backend)
- **Started:** 2026-10-17T16:08:40Z
- **Handled:** 2026-10-17T16:08:50.066203+00:00 -> 2026-10-17T16:09:07.132387+00:00
- **Mode:** runbook
- **Outcome:** resolved

## Steps

1. `get_alert` {} by runbook -> `{"status": "firing", "alertname": "ScanFailureRateHigh", "service": "scanner-backend", "severity": "page", "starts_at": "2026-10-17T16:08:40Z", "values": {"A": 1.0, "B": 1.0}, "summary": "More than half of scans failed in the last 5 minutes"}`
2. `query_metrics` {"name": "scan_failure_ratio"} by runbook -> `{"name": "scan_failure_ratio", "values": [1.0]}`
3. `get_faults` {} by runbook -> `{"active": ["scan-failure"]}`
4. `check_health` {} by runbook -> `{"ok": true, "http_status": 200, "status": "ok", "version": "dev"}`
5. `clear_fault` {"name": "scan-failure"} by runbook -> `{"cleared": "scan-failure", "http_status": 200}`

## Verification

```json
{
  "health": {
    "ok": true,
    "http_status": 200,
    "status": "ok",
    "version": "dev"
  },
  "active_faults": [],
  "failure_ratio": [
    1.0
  ],
  "scan": {
    "id": 13,
    "status": "completed"
  },
  "ok": true
}
```
