# MCP Security Posture Scanner

Final project for the [AI Dev Tools Zoomcamp](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp) (DataTalksClub, 2026 cohort).

A security scanner that connects to an MCP server as a client, enumerates tools/resources/prompts, runs a deterministic rule set against them, and produces a scored findings report with diff/drift detection.

## Problem

Teams wire third-party MCP (Model Context Protocol) servers into AI agents
with little security review. A tool description can carry a prompt
injection, an input schema can accept any shell command or path, and a
server can change its descriptions after a client trusted it. There is no
lightweight, self-hostable way to check a server before connecting an agent
to it.

## What it does

- You submit a target (a bundled fixture server, or a local stdio/HTTP
  server) in the web UI or with `POST /api/scans`.
- The scanner connects as an MCP client, lists tools, resources, and prompts,
  and runs 9 active deterministic rules on the metadata (MCP-005 waits for
  the HTTP transport).
- You get a findings report with severity, evidence, and remediation, and
  you can diff two scans of the same target to catch description drift.
- Expected behavior: a scan of the bundled `vulnerable-demo` fixture
  completes and returns findings from several rules; an external URL without
  `allow_external: true` is rejected with 422; a scan never calls a target
  tool.

**Safety boundary:** enumerate only — never invokes a target server's tools. Rule engine is deterministic — target metadata is never fed to an LLM. See `docs/permissions.md`.

## Quick start

```bash
# Full stack
docker compose up --build

# All tests, one command (backend 131 + oncall 46 + frontend 32 = 209)
make test

# Backend only
cd backend && uv sync && uv run pytest -v

# Frontend tests (32)
cd frontend && npm install && npm test

# Smoke test (proves the scanner works)
cd backend && uv run python scripts/smoke_test.py
```

Local ports (all bound to 127.0.0.1 by `docker-compose.yml`):

| Service | URL |
|---|---|
| Frontend (nginx, proxies `/api` to the backend) | http://127.0.0.1:3000 |
| Backend API | http://127.0.0.1:8000/api/health |
| Grafana (LGTM) | http://127.0.0.1:3001 |
| On-call agent | http://127.0.0.1:8080 |

The local stack sets `ALLOW_ARBITRARY_STDIO=true`, so the backend runs any
stdio command you submit, as the container user; that is why every port is
bound to 127.0.0.1.

## Key documents

| File | Purpose |
|---|---|
| [GitHub Issues](https://github.com/cjbischoff/mcp-security-posture-scanner/issues) | Public task tracker; each issue has acceptance criteria |
| `docs/task-tracker.md` | Tracker pointer, labels, issue to evidence-commit map |
| `docs/agent-team.md` | Agent team: roles, handoff process, rules, evidence |
| `.claude/agents/` | Reusable subagent definitions (builder, auditor, researcher) |
| `docs/agent-extension-pack.md` | Deterministic engine design rationale and security boundary enforcement |
| `docs/architecture.md` | System architecture with Mermaid flow diagrams |
| `docs/permissions.md` | Enumerate-only safety boundary |
| `docs/oncall-agent.md` | On-call responder agent: flow, tools, data boundary, demo |
| `ops/observability.md`, `ops/alerts.md`, `ops/runbooks/` | Observability stack, alert rule, runbook |
| `docs/decisions/` | Decision records (ADR-001: Phase 5 decision model) |
| `.planning/` | Planning artifacts (PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md) |
| `AGENTS.md` | Entry point for agents: context, modular doc index, session log |
| `security/ai-tool-data-policy.md` | What data flows to AI services (dev-time and runtime) |
| `security/pr-audit/review-log.md` | Code review methodology and session history |

## API endpoints

Every endpoint gets an HTTP server span from the FastAPI OpenTelemetry instrumentation (see [Observability](#observability)).

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness check and build version; not traced, so `trace_id` is `null` |
| GET | `/api/metrics` | In-process JSON snapshot: scan/finding totals, request counts, scan durations |
| POST | `/api/scans` | Submit a scan target (stdio or HTTP), returns scan ID |
| GET | `/api/scans` | List scans, newest first |
| GET | `/api/scans/{id}` | Scan status and metadata |
| GET | `/api/scans/{id}/report` | Findings report; for a failed scan, the error and no findings (409 while pending or running) |
| GET | `/api/scans/{id}/diff/{other_id}` | Diff findings between two scans of the same target |
| GET/POST/DELETE | `/api/admin/faults[/scan-failure]` | Fault injection to trigger the alert. Needs `Authorization: Bearer $ADMIN_TOKEN`; 404 when `ADMIN_TOKEN` is unset |

`openapi.yaml` also defines `GET /api/scans/{id}/verdict` (Phase 5 decision
model). It is not implemented yet; see issue #12.

Example request (the bundled fixture; works locally and on the deployed
services):

```bash
curl -s -X POST http://127.0.0.1:8000/api/scans \
  -H 'Content-Type: application/json' \
  -d '{"target": {"name": "demo", "transport": "stdio", "command": "vulnerable-demo"}}'
```

The response is the new scan with its `id` and `status: "pending"`; poll
`GET /api/scans/{id}` until `completed`, then read `/api/scans/{id}/report`.

**Target types:**
- **stdio:** in public mode, `command` must be a bundled fixture name (`vulnerable-demo`) with no `args`. Any command runs only when `ALLOW_ARBITRARY_STDIO=true` (set in `docker-compose.yml` for local use; never set it in a deployed environment).
- **HTTP:** provide `url`. Non-localhost URLs require `allow_external: true`. The API accepts HTTP targets, but the MCP client supports only stdio today, so an HTTP scan ends as `failed` (see Future work).

## v1 rule set (9 active deterministic rules)

MCP-005 is written down but not registered: it needs the HTTP transport,
which is not built, so it would never fire (#21).

| ID | Check | Severity |
|---|---|---|
| MCP-001 | Injection patterns in tool descriptions (hidden unicode, "ignore previous instructions") | Critical |
| MCP-002 | Unconstrained input schema on sensitive params (command/path/url/shell, no pattern/format/enum) | High |
| MCP-003 | Missing `readOnlyHint`/`destructiveHint` annotations | Medium |
| MCP-004 | Read + write capability pairing (confused-deputy signal) | High |
| MCP-005 | Unauthenticated HTTP transport (inactive until the HTTP transport exists) | High |
| MCP-006 | Overly broad resource URI patterns (wildcards, root paths) | Medium |
| MCP-007 | Tool description length/entropy anomaly (>2000 chars or entropy >5.5) | Medium |
| MCP-008 | Missing or malformed schema on required parameters | Medium |
| MCP-009 | Injection patterns in resource/prompt descriptions | Critical |
| MCP-010 | (Diff-only) Finding drift detection (severity change or silent removal) | High |

## Observability

The scan journey (POST `/api/scans`, background scan, report) is instrumented
with OpenTelemetry and exported over OTLP/HTTP to a local Grafana LGTM
container (`lgtm` in `docker-compose.yml`). The deployed Render services send
the same signals to Grafana Cloud instead; only env vars differ. Details:
`ops/observability.md`.

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

Without `OTEL_EXPORTER_OTLP_ENDPOINT` (unit tests, local runs outside
Docker) nothing is exported and only the JSON logs are written. The Render
services set it and send to Grafana Cloud; see "Two destinations" in
`ops/observability.md`.

## On-call agent

The `oncall` service (`oncall/`) is the responder for the `ScanFailureRateHigh`
alert. Grafana posts the alert to `http://oncall:8080/alert` with a shared
secret (`ONCALL_WEBHOOK_TOKEN`; any other request gets 401). The agent reads
the fault flags, health, and failure ratio. It clears the injected fault only
if one is active; otherwise it changes nothing and reports `needs_human` with
the diagnosis. After a fix it verifies with one real fixture scan through
`POST /api/scans`: `resolved` only if that scan completes, health is ok, and
no fault is active, else `fix_failed`. Reports go to `ops/incidents/<id>.md`
and `.json`.

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
cd oncall && uv run pytest    # 46 tests
```

Details: `docs/oncall-agent.md`. Runbook: `ops/runbooks/scan-failure-rate.md`.

## Test coverage

**209 tests, all passing** (`make test`, 2026-10-17).

| Layer | Count | What |
|---|---|---|
| Backend unit tests | 114 | Models, config, DB URL and engine pool, scan repository, health, MCP client, 9 active rules, consent, scan input validation, diff service, telemetry (trace IDs, redaction, query-string stripping, health not traced, metrics), admin fault API |
| Backend integration tests | 17 | MCP client enumerate (3), rule engine (2), scan flow (9), persistence across restart and failed-scan report (3) |
| On-call agent tests | 46 | Webhook app and token auth, agent loop and runbook fallback, verification scan, LLM client, tool allowlist (`oncall/tests/`) |
| Frontend unit tests | 32 | API client (8), NewScanPage (6), ScansPage (3), ScanReportPage (10), ScanDiffPage (5) |
| Smoke test | 1 | Standalone: full scan → report → findings against stub fixture server |

```bash
# Run all backend tests
cd backend && uv run pytest -v

# Run on-call agent tests
cd oncall && uv run pytest

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

- **CI** (`.github/workflows/ci.yml`): on every pull request and every push
  to `main`: backend ruff + unit + integration tests, oncall ruff + tests,
  frontend type check + tests + build, and `docker compose build`.
- **CD** (`.github/workflows/deploy.yml`): see Deployment.

## Deployment

One image (root `Dockerfile`): FastAPI serves the API and the built React
app. Images are tagged with the commit SHA in `ghcr.io`, and
`.github/scripts/render-deploy.sh` deploys a tag through a Render deploy
hook, then waits until `/api/health` reports that SHA as `version`.

- **Dev:** every green CI run on `main` builds the image and deploys it to
  dev automatically.
- **Prod:** Actions -> [Deploy](https://github.com/cjbischoff/mcp-security-posture-scanner/actions/workflows/deploy.yml)
  -> Run workflow, environment `prod`. The GitHub environment `prod` needs
  a reviewer to approve the run. Because prod is deployed by hand, it can
  lag `main`; `/api/health` reports the deployed commit as `version`.
- **Rollback:** run the same workflow by hand with an earlier commit SHA as
  the tag. Tested on dev (runs 38979968207, 38980090745).
  Drilled on prod 2026-10-17 (runs 39047623170 and 39063223640). A rollback
  is safe only to a SHA with the same Alembic migrations; across a migration,
  downgrade the schema first.
- **URLs:**
  - Prod: https://scanner-prod.onrender.com
  - Dev: https://scanner-dev-4o95.onrender.com

  Both run on Render's free plan with Neon Postgres (one branch per
  environment). A free instance sleeps after 15 minutes idle, so the first
  request after that can take about a minute.
- **Public mode:** deployed services do not set `ALLOW_ARBITRARY_STDIO`, so
  scans accept only the bundled `vulnerable-demo` fixture. Try it: open the
  UI, choose stdio, and enter `vulnerable-demo` as the command.

## Agent team

The project was built by a Claude Code orchestrator session that writes
contracts and prompts, builder subagents (one per issue, test-first, with
fixed file ownership), read-only auditor subagents, a researcher subagent,
and a human operator who decides scope and merges PRs. Earlier planning used
GSD roles (`.planning/`).

See `docs/agent-team.md` for roles, the handoff process, and evidence, and
`AGENTS.md` for the session log.

## Grading criteria map

| Criterion | Where it lives |
|---|---|
| Problem Description | This README (Problem, What it does) |
| Product Specification | `product-spec.md`, `openapi.yaml`, [GitHub Issues](https://github.com/cjbischoff/mcp-security-posture-scanner/issues), `docs/task-tracker.md` |
| Agent Team Specification | `docs/agent-team.md`, `.claude/agents/` |
| Context Management | `AGENTS.md`, `CLAUDE.md`, `docs/`, `.planning/` |
| Application | `backend/`, `frontend/`, `oncall/` |
| Testing | `backend/tests/unit/`, `backend/tests/integration/`, `oncall/tests/`, `frontend/src/**/__tests__/`, `make test` |
| Containerization | `docker-compose.yml`, `Dockerfile`, `backend/Dockerfile`, `frontend/Dockerfile`, `oncall/Dockerfile` |
| Deployment | Deployment section above, `.github/workflows/deploy.yml` |
| CI/CD | `.github/workflows/ci.yml`, `.github/workflows/deploy.yml` |
| Observability | `ops/observability.md`, `ops/grafana/`, `backend/app/observability.py` |
| Alerting on User Impact | `ops/alerts.md`, `ops/grafana/alerting.yaml`, `scripts/trigger-alert.sh` |
| On-Call Agent | `docs/oncall-agent.md`, `oncall/`, `ops/runbooks/`, `ops/incidents/` |

Full rubric mapping: `mcp-scanner-project-brief.md` Section 9.

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
- Scheduled re-scans with alerts on posture changes
- Tool-inventory SBOM export
- HTTP transport support in the MCP client (currently stdio only)
- Phase 5 decision model (requires operator-provided endpoint + auth)
