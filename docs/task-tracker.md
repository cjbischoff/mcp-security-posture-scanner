# Task Tracker — MCP Security Posture Scanner

Tracked phases with acceptance criteria and evidence of agent execution.

---

## Phase 0: Setup (scaffold, specs, compose skeleton)

| Task | Acceptance criteria | Agent used | Evidence |
|---|---|---|---|
| Scaffold repo structure | Directories per brief Section 4 exist | Claude (orchestrator) | `frontend/`, `backend/`, `docs/`, `.github/workflows/` created |
| Write product-spec.md | Describes problem, 10 rules, data model, flows | Claude | `product-spec.md` written |
| Write openapi.yaml | Spec-first contract with all endpoints | Claude | `openapi.yaml` defines 6 endpoints + schemas |
| Docker Compose skeleton | Frontend, backend, Postgres defined | Claude | `docker-compose.yml` with 3 services |
| CI/CD skeletons | `.github/workflows/ci.yml` + `deploy.yml` exist | Claude | CI runs lint+tests, deploy gates on CI |

---

## Phase 1: Backend Core

| Task | Acceptance criteria | Agent used | Evidence |
|---|---|---|---|
| Plan decomposition | Phase 1 split into 5 sub-plans with test-at-every-level | Claude | `.planning/ROADMAP.md`, `phases/01-backend-core-mcp-client-rule-engine/` |
| Project scaffold + DB | FastAPI factory, SQLAlchemy models (ScanTarget, Scan, Finding), Alembic, /api/health | Claude | 16 tests on models+config+health pass |
| MCP enumeration client | Connect via stdio, enumerate tools/resources/prompts, typed MCPSnapshot | Claude | Direct JSON-RPC over subprocess (bypassed buggy SDK client) |
| Deterministic rule engine | 10 rule modules (MCP-001..010), orchestrator, registry | Claude | 37 rule unit tests + 2 integration tests pass |
| Scan/report/diff API | POST /scans, GET /scans/{id}/report, GET /scans/{id}/diff/{other_id}, consent enforcement | Claude | 5 API endpoints; 18 tests (11 unit + 7 integration) |
| Docs + smoke test | README, AGENTS.md, smoke_test.py | Claude | 86 backend tests green; smoke test passes |

---

## Phase 2: Frontend

| Task | Acceptance criteria | Agent used | Evidence |
|---|---|---|---|
| Vite scaffold + API client | Vite+React+TS, centralized API client (6 endpoint methods), MSW mocks | Claude | 8 API client tests pass |
| Scan form + list page | NewScanPage (name, transport, command/args/URL, consent toggle), ScansPage (list + auto-poll) | Claude | 8 RTL tests pass |
| Report + diff pages | ScanReportPage (severity badges), ScanDiffPage (added/removed/unchanged/drift) | Claude | 10 RTL tests pass |

---

## Phase 3: Containerization + CI

| Task | Acceptance criteria | Agent used | Evidence |
|---|---|---|---|
| Backend Dockerfile | uv-based image, uvicorn, non-root user | Claude | Builds; runs 86 tests in container |
| Frontend Dockerfile + nginx | Multi-stage build, nginx proxy /api/ to backend | Claude | Builds; all 3 compose services healthy |
| CI pipeline update | `npm test` script, compose-build job in CI yml | Claude | CI yml has 3 jobs (backend, frontend, compose-build) |
| Semgrep custom rule + /metrics | Custom rule passes on clean code, flags violations | Claude | 0 findings on codebase; 1 finding on test violation |

---

## Phase 4: Security + DevOps

| Task | Acceptance criteria | Agent used | Evidence |
|---|---|---|---|
| Containerized security scanner | Dockerfile with semgrep + syft + grype | Claude | `security/Dockerfile` built; all 3 tools work |
| SBOM + Grype scan | 218 components, 0 vulnerabilities | Claude | `security/sbom/backend-sbom.cdx.json`, `security/grype/backend-vulns.json` |
| PR audit log | Documents review methodology + session history | Claude | `security/pr-audit/review-log.md` |
| AI tool data policy | States dev-time + runtime data flows accurately | Claude | `security/ai-tool-data-policy.md` |
| Agent/extension notes | Explains deterministic engine rationale | Claude | `docs/agent-extension-pack.md` |
| Full smoke | 86 backend + 26 frontend tests, compose build, semgrep all green | Claude | All verified passing |

---

## Phase 5: Decision Model (not started)

Blocks on operator providing hosted model endpoint, auth, and data retention details.
