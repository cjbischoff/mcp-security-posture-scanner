# MCP Security Posture Scanner

Final project for the [AI Dev Tools Zoomcamp](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp) (DataTalksClub, 2026 cohort).

A security scanner that connects to an MCP server as a client, enumerates tools/resources/prompts, runs a deterministic rule set against them, and produces a scored findings report with diff/drift detection.

**Safety boundary:** enumerate only — never invokes a target server's tools. Rule engine is deterministic — target metadata is never fed to an LLM. See `docs/permissions.md`.

## Quick start

```bash
# Full stack
docker compose up --build

# All tests, one command (backend 114 + frontend 26)
make test

# Backend only
cd backend && uv sync && uv run pytest -v

# Frontend tests (26)
cd frontend && npm install && npm test

# Smoke test (proves the scanner works)
cd backend && uv run python scripts/smoke_test.py
```

## Key documents

| File | Purpose |
|---|---|
| `docs/task-tracker.md` | Public task tracker with acceptance criteria and agent execution evidence |
| `docs/agent-team.md` | Agent team specification with roles, responsibilities, collaboration process |
| `docs/agent-extension-pack.md` | Deterministic engine design rationale and security boundary enforcement |
| `docs/architecture.md` | System architecture with Mermaid flow diagrams |
| `docs/permissions.md` | Enumerate-only safety boundary |
| `docs/oncall-agent.md` | On-call responder agent: flow, tools, data boundary, demo |
| `docs/decisions/` | Decision records (ADR-001: Phase 5 decision model) |
| `.planning/` | Planning artifacts (PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md) |
| `AGENTS.md` | AI-assisted development workflow log |
| `security/ai-tool-data-policy.md` | What data flows to AI services (dev-time and runtime) |
| `security/pr-audit/review-log.md` | Code review methodology and session history |

## API endpoints

Every endpoint gets an HTTP server span from the FastAPI OpenTelemetry instrumentation (see [Observability](#observability)).

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness check; returns the request's full 32-hex `trace_id` |
| GET | `/api/metrics` | In-process JSON snapshot: scan/finding totals, request counts, scan durations |
| POST | `/api/scans` | Submit a scan target (stdio or HTTP), returns scan ID |
| GET | `/api/scans` | List scans, newest first |
| GET | `/api/scans/{id}` | Scan status and metadata |
| GET | `/api/scans/{id}/report` | Findings report (409 if not yet completed) |
| GET | `/api/scans/{id}/diff/{other_id}` | Diff findings between two scans of the same target |
| GET/POST/DELETE | `/api/admin/faults[/scan-failure]` | Fault injection to trigger the alert. Needs `Authorization: Bearer $ADMIN_TOKEN`; 404 when `ADMIN_TOKEN` is unset |

**Target types:**
- **stdio:** in public mode, `command` must be a bundled fixture name (`vulnerable-demo`) with no `args`. Any command runs only when `ALLOW_ARBITRARY_STDIO=true` (set in `docker-compose.yml` for local use; never set it in a deployed environment).
- **HTTP:** provide `url`. Non-localhost URLs require `allow_external: true`

## v1 rule set (10 deterministic rules)

| ID | Check | Severity |
|---|---|---|
| MCP-001 | Injection patterns in tool descriptions (hidden unicode, "ignore previous instructions") | Critical |
| MCP-002 | Unconstrained input schema on sensitive params (command/path/url/shell, no pattern/format/enum) | High |
| MCP-003 | Missing `readOnlyHint`/`destructiveHint` annotations | Medium |
| MCP-004 | Read + write capability pairing (confused-deputy signal) | High |
| MCP-005 | Unauthenticated HTTP transport | High |
| MCP-006 | Overly broad resource URI patterns (wildcards, root paths) | Medium |
| MCP-007 | Tool description length/entropy anomaly (>2000 chars or entropy >5.5) | Medium |
| MCP-008 | Missing or malformed schema on required parameters | Medium |
| MCP-009 | Injection patterns in resource/prompt descriptions | Critical |
| MCP-010 | (Diff-only) Finding drift detection (severity change or silent removal) | High |

## Observability

The scan journey (POST `/api/scans`, background scan, report) is instrumented
with OpenTelemetry and exported over OTLP/HTTP to a local Grafana LGTM
container (`lgtm` in `docker-compose.yml`). Details: `ops/observability.md`.

- **Traces (Tempo):** HTTP spans from the FastAPI instrumentation, plus
  `scan.execute` > `mcp.connect`, `mcp.enumerate`, `rules.run`. The background
  scan stays in the POST request's trace.
- **Logs (Loki and stderr):** one JSON object per line with the full 32-hex
  `trace_id`, 16-hex `span_id`, level, logger, message, and `scan_id`.
- **Metrics (Prometheus):** `scanner_scans_total{status="completed"|"failed"}`,
  `scanner_scan_duration_seconds_*`, and the HTTP server metrics.
- **Redaction:** no target command, args, URL, name, tool data, or raw error
  text goes to telemetry. Failed scans report an `error_category` (for example
  `connect_failed`, `timeout`); the full error stays in the API response. A
  unit test checks this.
- **Alert:** `ScanFailureRateHigh` pages when more than half of the scans in
  5 minutes fail (at least 3 scans). It posts to the on-call webhook. Rule,
  rationale, and trigger: `ops/alerts.md`.

```bash
docker compose up --build -d
open http://127.0.0.1:3001             # Grafana: dashboard "Scanner — scan journey"
scripts/trigger-alert.sh               # inject scan failures; alert fires in about 1-2 min
scripts/trigger-alert.sh --off
```

Without `OTEL_EXPORTER_OTLP_ENDPOINT` (tests, the Render deploy) nothing is
exported and only the JSON logs are written.

## On-call agent

The `oncall` service (`oncall/`) is the responder for the `ScanFailureRateHigh`
alert. Grafana posts the alert to `http://oncall:8080/alert`; the agent reads
the fault flags, health, and failure ratio, clears the injected fault, waits,
verifies, and writes an incident report to `ops/incidents/<id>.md` and `.json`.

- **LLM optional:** any OpenAI-compatible provider via `LLM_BASE_URL`,
  `LLM_API_KEY`, `LLM_MODEL`. With no key, or on any invalid tool call or
  provider error, a deterministic runbook does the same fix.
- **Fixed tool allowlist:** the model picks from 7 server-side tools with
  enumerated arguments; it cannot write PromQL, URLs, or new tools.
- **Data boundary:** the agent sees only alert fields, metric numbers, fault
  flag names, and health. It has no access to scan targets or findings; a test
  and a Semgrep rule enforce this.

```bash
docker compose up --build -d backend db lgtm oncall
scripts/trigger-alert.sh      # or see docs/oncall-agent.md for a manual payload
ls ops/incidents/
cd oncall && uv run pytest    # 38 tests
```

Details: `docs/oncall-agent.md`. Runbook: `ops/runbooks/scan-failure-rate.md`.

## Test coverage

**140 tests — all passing.**

| Layer | Count | What |
|---|---|---|
| Backend unit tests | 98 | Models, config, DB URL, scan repository, health, MCP client, 10 rules, consent, diff service, telemetry (trace IDs, redaction, metrics), admin fault API |
| Backend integration tests | 16 | MCP client enumerate (3), rule engine (2), scan flow (9), persistence across restart (2) |
| Frontend unit tests | 26 | API client (8), NewScanPage (5), ScansPage (3), ScanReportPage (5), ScanDiffPage (5) |
| Smoke test | 1 | Standalone: full scan → report → findings against stub fixture server |

```bash
# Run all backend tests
cd backend && uv run pytest -v

# Run all frontend tests
cd frontend && npm test

# Run smoke test
cd backend && uv run python scripts/smoke_test.py
```

## Persistence

Targets, scans, findings, and the raw enumeration snapshot (used by diff and MCP-010) are stored in the database selected by `DATABASE_URL`: Postgres in Docker Compose, SQLite (`backend/scanner.db`) by default. Bare `postgresql://` / `postgres://` URLs (e.g. Neon, with `?sslmode=require`) are mapped to the psycopg2 driver. The schema is managed by Alembic; the backend container runs `alembic upgrade head` before starting uvicorn. For local runs outside Docker: `cd backend && uv run alembic upgrade head`.

A Postgres volume created before migrations existed (tables but no `alembic_version`) needs a one-time `docker compose run --rm --no-deps backend uv run --no-sync alembic stamp 1689000e03f7`.

## Containerization

```bash
# Full stack (db, backend, frontend, lgtm, oncall)
docker compose up --build

# Individual images
docker compose build backend
docker compose build frontend

# Security scanning tools (semgrep, syft, grype) in a container
docker build -t mcp-scanner-security security/
docker run --rm -v $(pwd):/repo mcp-scanner-security semgrep --config p/security-audit /repo/backend/
```

## CI/CD

- **CI:** GitHub Actions runs backend tests (pytest), frontend tests (vitest), TypeScript check, build, and Docker compose build on every push/PR.
- **CD:** Triggered on merge to main after CI passes. Requires `DEPLOY_HOOK_URL` secret (no-op until configured).

## Agent team

The project uses a defined agent team with separation of concerns:

- **Orchestrator** — decomposes phases, delegates work, runs verification gates
- **Classifier / Synthesizer / Roadmapper** — document analysis and planning
- **Planner / Checker** — plan decomposition and quality review
- **Builder** — implements TDD (RED → GREEN → REFACTOR)

See `docs/agent-team.md` for full role definitions, process flow, and communication patterns.

## Security artifacts

All 5 artifact types from the rubric are present:

| # | Artifact | Location |
|---|---|---|
| 1 | PR audit log | `security/pr-audit/review-log.md` |
| 2 | Semgrep scan results (standard + custom rule) | `security/semgrep/` |
| 3 | Agent/extension security notes | `docs/agent-extension-pack.md` |
| 4 | Ops diagnosis output | `ops/health-sample-output.md` |
| 5 | AI tool data policy | `security/ai-tool-data-policy.md` |

Additional: SBOM (`security/sbom/backend-sbom.cdx.json`) and Grype vulnerability scan (`security/grype/backend-vulns.json`, 0 findings).

## Future work

- Rules beyond the capped set (rug-pull hash pinning, OAuth scope analysis)
- Scheduled re-scans and alerting
- Tool-inventory SBOM export
- HTTP transport support in the MCP client (currently stdio only)
- Phase 5 decision model (requires operator-provided endpoint + auth)
