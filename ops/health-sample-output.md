# Ops: Health and Metrics Sample Output

Captured from a local instance of the MCP Security Posture Scanner.
Generated: 2026-10-16

---

## /api/health

```json
{
  "status": "ok"
}
```

---

## /api/metrics

```json
{
  "scan_count_total": 0,
  "finding_count_total": 0,
  "rule_count_total": 10
}
```

After running smoke tests:
```json
{
  "scan_count_total": 1,
  "finding_count_total": 6,
  "rule_count_total": 10
}
```

---

## Application Status

All three Docker Compose services running and healthy:
- `db` — Postgres 16 (healthy)
- `backend` — FastAPI (healthy)
- `frontend` — nginx serving React SPA (running)

---

## Operational Notes

- Backend runs on `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Postgres runs on port 5432 with user/pass/db: scanner/scanner/scanner
- Frontend nginx proxies `/api/` to `backend:8000`
- All 86 backend tests and 26 frontend tests pass
- Semgrep custom rule `no-llm-on-untrusted-mcp-data` passes with 0 findings on clean codebase
- Deployment: requires `DEPLOY_HOOK_URL` secret to be configured (no-op until then)
