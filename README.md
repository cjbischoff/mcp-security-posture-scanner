# MCP Security Posture Scanner

Final project for the [AI Dev Tools Zoomcamp](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp) (DataTalksClub, 2026 cohort).

A security scanner that connects to an MCP server as a client, enumerates tools/resources/prompts, runs a deterministic rule set against them, and produces a scored findings report with diff/drift detection.

**Safety boundary:** enumerate only — never invokes a target server's tools. Rule engine is deterministic — target metadata is never fed to an LLM. See `docs/permissions.md`.

## Quick start

```bash
# Full stack
docker compose up --build

# All tests, one command (backend 92 + frontend 26)
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
| `docs/decisions/` | Decision records (ADR-001: Phase 5 decision model) |
| `.planning/` | Planning artifacts (PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md) |
| `AGENTS.md` | AI-assisted development workflow log |
| `security/ai-tool-data-policy.md` | What data flows to AI services (dev-time and runtime) |
| `security/pr-audit/review-log.md` | Code review methodology and session history |

## API endpoints

| Method | Path | Description | Traced |
|---|---|---|---|
| GET | `/api/health` | Liveness check — returns `trace_id` for request correlation | ✅ |
| GET | `/api/metrics` | Application metrics: scan count, request counts, scan duration histogram | ✅ |
| POST | `/api/scans` | Submit a scan target (stdio or HTTP), returns scan ID | ✅ |
| GET | `/api/scans` | List scans, newest first | ✅ |
| GET | `/api/scans/{id}` | Scan status and metadata | ✅ |
| GET | `/api/scans/{id}/report` | Findings report (409 if not yet completed) | ✅ |
| GET | `/api/scans/{id}/diff/{other_id}` | Diff findings between two scans of the same target | ✅ |

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

The application is instrumented with **OpenTelemetry**:

- **Traces:** Every HTTP request generates a trace. Traces export via OTLP (if `OTEL_EXPORTER_OTLP_ENDPOINT` is set) or fall back to console output for local development.
- **Trace IDs:** Every log line includes `trace_id` and `span_id` for correlating logs to a single request. The `/api/health` endpoint returns the current request's `trace_id`.
- **Metrics:** Scan duration histogram, per-endpoint request counters, finding counts. View at `/api/metrics`.
- **Structured logs:** All logs carry trace context. No customer data or credentials are sent to telemetry.

```bash
# View trace output (console exporter)
docker compose logs backend | grep 'trace='

# View metrics
curl http://localhost:8000/api/metrics
```

## Test coverage

**112 tests — all passing.**

| Layer | Count | What |
|---|---|---|
| Backend unit tests | 73 | Models, config, health, MCP client, 10 rules (37), consent (6), diff service (5) |
| Backend integration tests | 13 | MCP client enumerate (3), rule engine (2), scan flow (7) + health |
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

## Containerization

```bash
# Full stack (3 services)
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
