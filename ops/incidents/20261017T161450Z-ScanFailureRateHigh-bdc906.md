# Incident 20261017T161450Z-ScanFailureRateHigh-bdc906

- **Alert:** ScanFailureRateHigh (page, service scanner-backend)
- **Started:** 2026-10-17T16:14:40Z
- **Handled:** 2026-10-17T16:14:50.024801+00:00 -> 2026-10-17T16:14:50.038977+00:00
- **Mode:** runbook
- **Outcome:** needs_human
- **Why:** no active fault to clear, so nothing was changed; a human must find the cause

## Steps

1. `get_alert` {} by runbook -> `{"status": "firing", "alertname": "ScanFailureRateHigh", "service": "scanner-backend", "severity": "page", "starts_at": "2026-10-17T16:14:40Z", "values": {"A": 1.0, "B": 1.0}, "summary": "More than half of scans failed in the last 5 minutes"}`
2. `query_metrics` {"name": "scan_failure_ratio"} by runbook -> `{"name": "scan_failure_ratio", "values": [1.0]}`
3. `get_faults` {} by runbook -> `{"active": []}`
4. `check_health` {} by runbook -> `{"ok": true, "http_status": 200, "status": "ok", "version": "dev"}`

## Diagnosis

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
  ]
}
```
