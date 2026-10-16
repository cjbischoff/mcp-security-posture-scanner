# ROADMAP — MCP Security Posture Scanner

**Granularity:** Standard (4–6 phases)
**Phase ID convention:** Sequential
**Active milestone:** 1

---

## Phase Overview

- [ ] **Phase 1: Backend Core + MCP Client + Rule Engine**
- [ ] **Phase 2: Frontend + Integration**
- [ ] **Phase 3: Testing + Containerization + CI**
- [ ] **Phase 4: Security/Audit/DevOps Hardening**
- [ ] **Phase 5: Decision Model (operator-requested, not graded)**

---

### Phase 1: Backend Core + MCP Client + Rule Engine

**Goal:** A user can submit a scan target, enumerate its MCP metadata, run deterministic rules, and view a findings report — all via the API.

**Dependencies:** Phase 0 scaffold (openapi.yaml, Docker Compose skeleton, docs). None upstream.

**Requirements:** FR-1, FR-2, FR-3, FR-4, FR-5, FR-7, MCP-001..MCP-010, NFR-1, NFR-2, NFR-3, NFR-4, NFR-5, R-01, R-02, R-03, R-06, R-07, R-14

**Success Criteria:**
1. User can POST a scan target (stdio command or HTTP URL) and receive a scan ID immediately. API returns `202 Accepted`.
2. User can poll scan status and, upon completion, retrieve a scored findings report with findings grouped by severity.
3. User can diff two completed scans of the same target and see added/removed/unchanged findings, plus drift flags from MCP-010.
4. User can attempt a scan on a non-localhost target **without** `allow_external: true` and receive a consent error. Setting the flag permits the scan.
5. User can run all 10 rules against a fixture MCP server and get detections for known-vulnerable descriptions and schemas.

**Plans:** 5 (1.1 scaffold+DB, 1.2 MCP client, 1.3 rules, 1.4 API, 1.5 docs+smoke)

**Phase overview:**
| Plan | Deliverable | Test level |
|---|---|---|
| 1.1 | pyproject.toml, models, Alembic, health endpoint | Unit (models, config) |
| 1.2 | MCP enumeration client + stub fixture server | Unit + Integration (stub server) |
| 1.3 | 10 deterministic rules + orchestrator | Unit (per rule) + Integration (fixture snapshot) |
| 1.4 | Scan/report/diff API + services + consent | Unit (consent, diff) + Integration (end-to-end TestClient) |
| 1.5 | README, docs/architecture.md, AGENTS.md, smoke script | Smoke (standalone script) |

**Test strategy:** Tests expand monotonically per plan. After 1.4: `uv run pytest -v` covers all unit + integration tests. After 1.5: smoke test proves end-to-end outside pytest.

---

### Phase 2: Frontend + Integration

**Goal:** A user can run scans, browse reports, and diff scans through a browser UI.

**Dependencies:** Phase 1 (API must be functionally complete).

**Requirements:** R-04 (Frontend), R-12 (Agent Extension Pack — conditional on Module 3)

**Success Criteria:**
1. User can navigate to the web app, paste a scan target, and initiate a scan. The UI shows a loading state while the scan runs.
2. Scan completion redirects to a report page showing findings grouped by severity, with severity-colored badges and remediation text.
3. User can select two completed scans and view a diff page showing added, removed, and unchanged findings, with drift indicators.
4. User can toggle the `allow_external` consent flag in the UI when creating a scan target.

**Plans:** 3 (2.1 Vite+API client, 2.2 scan form+list, 2.3 report+diff+navigation)

**Phase overview:**
| Plan | Deliverable | Tests |
|---|---|---|
| 2.1 | Vite scaffold, centralized API client, MSW mock handlers, Vitest+RTL config | Unit: API client (6 endpoints), TypeScript compile |
| 2.2 | New Scan form, scan list with polling, status badges | RTL: form validation, submit, consent toggle, list rendering, polling |
| 2.3 | Findings report (severity groups), scan diff (added/removed/drift), navigation | RTL: report page, diff page, app navigation |

**Test maintenance:** Backend 86-test suite must remain green (`cd backend && uv run pytest -v`). Smoke test also verified (`uv run python scripts/smoke_test.py`).

**UI hint:** `frontend/src/api/` — centralized API client using `openapi.yaml` as contract. React Router for scan/report/diff pages. Vitest + React Testing Library for component tests.

**Phase 2(b) — Agent Extension Pack (conditional):**
If Module 3 is confirmed, this sub-phase adds: agent capabilities documentation, agent hooks, a custom MCP server, agent workflow instructions, and permissions. Delivered under `agent-capabilities/`, `agent-hooks/`, `mcp-server/`, `custom-agent/`.

---

### Phase 3: Testing + Containerization + CI

**Goal:** The full application runs via Docker Compose with no manual steps, integration tests pass against fixture MCP servers, and CI ensures regressions are caught.

**Dependencies:** Phase 1 (application code).

**Requirements:** R-08 (Containerization), R-09 (Integration Testing), R-13 (Security/Audit/DevOps — artifact type: Semgrep + ops output)

**Success Criteria:**
1. User runs `docker compose up --build` and the full stack (frontend, backend, Postgres) starts with no manual steps. A health endpoint at `/api/health` returns 200.
2. Integration tests run against a stub MCP fixture server (dockerized) and cover the scan → report → diff workflow, all passing via `docker compose run --rm backend pytest tests/integration/`.
3. CI pipeline (GitHub Actions) runs unit tests, integration tests, frontend type check, and linters on every push.
4. A custom Semgrep rule (`no-llm-on-untrusted-mcp-data`) is written and passes on the codebase, preventing accidental LLM calls on target data.

**Plans:** 4 (3.1 backend Dockerfile, 3.2 frontend Dockerfile+nginx, 3.3 CI update, 3.4 Semgrep rule+ops)

**Phase overview:**
| Plan | Deliverable | Critical tests |
|---|---|---|
| 3.1 | Backend Dockerfile (uv + uvicorn) | Docker build; container runs 86 tests |
| 3.2 | Frontend Dockerfile (multi-stage) + nginx proxy | Full compose up; /api/health proxied |
| 3.3 | CI pipeline (frontend job, compose build check) | All jobs defined; deploy gates on CI |
| 3.4 | Semgrep `no-llm-on-untrusted-mcp-data` rule + /metrics | Semgrep passes; rule flags target-to-LLM patterns |

**Test maintenance:** Backend 86 + frontend 26 suites must remain green after each plan. `cd backend && uv run pytest -v && cd ../frontend && npx vitest run`.

---

### Phase 4: Security/Audit/DevOps Hardening

**Goal:** All security and audit artifacts are produced, the application is deployed to cloud, and CI/CD deploys on every green push.

**Dependencies:** Phase 1, Phase 3 (integration tests passing, containerization working).

**Requirements:** R-10 (Deployment), R-11 (CI/CD), R-13 (Security/Audit/DevOps — full: PR audit, Semgrep, agent/extension notes, ops output, AI data policy), R-15 (Peer Review)

**Success Criteria:**
1. Application is deployed to a cloud provider (Render, Fly.io, or Railway) and accessible at a working public URL.
2. GitHub Actions deploy workflow runs tests and, on pass, deploys to the cloud provider.
3. All 5 Security/Audit/DevOps artifact types are present in the `security/` and `ops/` directories:
   - PR audit log (`.code-review-graph/` or `security/pr-audit/`)
   - Custom Semgrep rule results
   - Agent/extension notes
   - Ops output (deployment logs, monitoring)
   - AI tool data policy (`security/ai-tool-data-policy.md`)
4. Student has completed minimum 3 peer evaluations on the course platform.
5. README provides complete end-to-end instructions: setup, run, test, deploy.

**Plans:** 3 (4.1 Semgrep full scan + SBOM, 4.2 PR audit + AI policy, 4.3 agent notes + README + full smoke)

**Phase overview:**
| Plan | Deliverable | Critical test |
|---|---|---|
| 4.1 | Semgrep p/security-audit + p/owasp-top-ten SARIF, Syft SBOM | SARIF valid JSON; SBOM generates |
| 4.2 | PR audit log + ai-tool-data-policy.md | Policy accurately describes runtime data flows |
| 4.3 | Agent/extension security notes, final README, AGENTS.md, full smoke | pytest 86 + npm test 26 + smoke + compose build + semgrep all green |

**Local-first:** No cloud deployment. Clone → `docker compose up --build` → works.
**Peer reviews:** To be completed on course platform (not a code deliverable).

---

### Phase 5: Decision Model (operator-requested, not graded)

**Goal:** A scan returns a machine-readable verdict (allow/review/block) optionally refined by a hosted decision model, with deterministic fallback.

**Dependencies:** Phase 1 (scan and report API must exist).

**Requirements:** FR-6 (Verdict), ADR-001 (typed input, policy floor, opt-in config)

**Success Criteria:**
1. User calls `GET /api/scans/{id}/verdict` and receives `allow`, `review`, or `block` with a score (0–100), reasons list, and `source` field (`model` or `policy`).
2. With `DECISION_MODEL_URL` and `DECISION_MODEL_API_KEY` unset, the verdict uses the deterministic policy only.
3. User submits a scan with a Critical finding: verdict is always `block` regardless of model output (policy floor enforced).
4. The model input (serialized request) contains only typed fields: counts, rule IDs (enum), transport type (enum), `allow_external` flag. Unit test asserts no target-derived string leaks into the model payload.

**Plans:** TBD — blocks on operator providing endpoint, request/response format, auth, and data retention details.

**UI hint:** None — verdict is API-only in this phase. No UI required for graded work.
