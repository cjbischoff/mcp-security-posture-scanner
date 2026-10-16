# Runbook: ScanFailureRateHigh

**Alert:** `ScanFailureRateHigh` (labels `service=scanner-backend`,
`severity=page`). More than half of scans failed over 5 minutes, with at
least 3 scans.

**Impact:** users get failed reports instead of findings.

The on-call agent (`oncall/`, see `docs/oncall-agent.md`) runs these steps
automatically. A human can run the same steps with the commands below.

## 1. Confirm

```bash
# Failure ratio (Prometheus inside lgtm; from the host use Grafana Explore)
sum(rate(scanner_scans_total{status="failed"}[5m])) / sum(rate(scanner_scans_total[5m]))

curl http://127.0.0.1:8000/api/health
```

## 2. Find the cause

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" http://127.0.0.1:8000/api/admin/faults
```

`{"scan_failure": true}` means the failures are injected.

## 3. Fix

| Cause | Action |
|---|---|
| `scan_failure` fault is on | `curl -XDELETE -H "Authorization: Bearer $ADMIN_TOKEN" http://127.0.0.1:8000/api/admin/faults/scan-failure` |
| no fault, health fails | Restart: Render deploy hook, or `docker compose restart backend` locally |
| restart did not help, bad release suspected | Roll back: run the Deploy workflow by hand with an earlier SHA as `tag` |

## 4. Verify

Wait about 15 seconds, then:

- `/api/health` returns `{"status": "ok", ...}`
- `GET /api/admin/faults` shows `scan_failure: false`
- run one scan; it completes

The failure ratio is a 5-minute rate, so it drops a few minutes after the
fix. Grafana then sends a `resolved` notification.

## 5. Record

Write an incident report: what fired, what you checked, what you changed,
and the verification result. The agent writes one to `ops/incidents/<id>.md`
and `<id>.json`, and opens a GitHub issue if `ONCALL_GITHUB_TOKEN` is set.
