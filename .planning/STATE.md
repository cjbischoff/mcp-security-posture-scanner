# STATE — MCP Security Posture Scanner

> **Status note (2026-10-17):** this file is the original GSD plan, written
> 2026-10-15 before the code. It is not kept up to date. The live tracker is
> [GitHub Issues](https://github.com/cjbischoff/mcp-security-posture-scanner/issues)
> (index: [`docs/task-tracker.md`](../docs/task-tracker.md)). Actual status:
> Phases 1-4 were built and committed on 2026-10-16 (`9b844f6`, `22fecd4`,
> `a9610a6`, `5dfab96`, then issues #4-#11); deployment to Render dev and
> prod is live (#10); Phase 5 (decision model) is not built (#12). Known gaps
> are open issues #18-#26.

**Generated:** 2026-10-15
**Source:** Intel synthesis from 7 ingested documents

---

## Project Reference

| Field | Value |
|---|---|
| Name | MCP Security Posture Scanner |
| Course | AI Dev Tools Zoomcamp (DataTalksClub), 2026 cohort |
| Type | Final project |
| Source brief | `mcp-scanner-project-brief.md` |
| Active milestone | 1 |

---

## Current Position

| Phase | Description | Status |
|---|---|---|
| Phase 0 | Scaffolding (dirs, compose skeleton, openapi.yaml, docs, CI ymls) | ✅ Complete (2026-07-23) |
| Phase 1 | Backend Core + MCP Client + Rule Engine | ✅ Done 2026-10-16 (`9b844f6`, #2); MCP-005 is a stub, #21 |
| Phase 2 | Frontend + Integration + Agent Extension Pack (conditional) | ✅ Done 2026-10-16 (`22fecd4`, #3) |
| Phase 3 | Testing + Containerization + CI + Semgrep | ✅ Done 2026-10-16 (`a9610a6`, #5); Semgrep runs by hand, not in CI |
| Phase 4 | Security/Audit/DevOps Hardening + Deploy | ✅ Done 2026-10-16 (`5dfab96`, #10) |
| Phase 5 | Decision Model (operator-requested, not graded) | Not started (#12) |

**Phase 1 plans:**
- Plan 1.1: Project scaffold + DB (not started)
- Plan 1.2: MCP enumeration client (not started)
- Plan 1.3: Deterministic rule engine (not started)
- Plan 1.4: Scan/report/diff API + services (not started)
- Plan 1.5: Docs, README, smoke test (not started)

**Test coverage per plan:** Unit tests on every rule/service/model. Integration tests on full scan flow against fixture MCP server. Smoke script for CI. Tests expand monotonically. |

**Blockers:** Phase 1 not started. Phase 2 conditional on Module 3 completion (unconfirmed). Phase 5 requires operator to provide endpoint/auth/retention details.

**Open items (require human operator):**
1. **Deadline / time budget** — determines whether Syft/Grype and diff-based drift detection fit, or get cut.
2. **Module 3 completion** — determines whether Phase 2 (Agent Extension Pack) is in scope.
3. **External scan target support** — default to restricted per PRD Section 2; explicit decision needed.
4. **Decision model details** — endpoint, request/response format, auth, data retention.

**Instruction:** Do not proceed past Phase 1 without resolving items 1 and 2.

---

## Metrics

| Metric | Value | Notes |
|---|---|---|
| Phases complete | 1 of 6 (Phase 0) | Phase 0 is scaffold only |
| Phase 1 plans written | 5 of 5 | All planned, none executed |
| Requirements total | 40 (7 FR + 8 NFR + 10 Rules + 15 Rubric) | All mapped to phases |
| Rules implemented | 0 of 10 | All in Plan 1.3 |
| Tests written | 0 planned across 5 plans | Unit: ~20, Integration: ~4, Smoke: 1 |
| Tests passing | — | No test suite yet |
| CI green | — | No CI triggers yet |
| Deployed | No | Phase 4 |
| Peer reviews | 0 | Phase 4 |
| Blocker count | 0 (technical) | 4 open items (operator) |

---

## Accumulated Context

### Decision Model State (ADR-001)

- LOCKED — operator-requested, Phase 5, typed input only, policy floor
- No endpoint/auth/retention details confirmed yet
- Does not count toward the 10-rule cap
- Not traceable to rubric — not graded
- Must record what is sent to the model in `security/ai-tool-data-policy.md`

### Architecture Decisions

| Area | Decision | Source |
|---|---|---|
| API prefix | `/api` prefix on all endpoints (SPEC > PRD) | C-SPEC-001 |
| Dev approach | Spec-first: openapi.yaml before backend | C-PRD-007 |
| Engine | Deterministic only — never LLM on target data | NFR-1 |
| MCP interaction | Enumerate-only — never call_tool/read_resource | NFR-2 |
| Target scope | Localhost/fixture default, consent for external | NFR-3 |
| Rule set | Exactly 10 rules v1, public sources only | NFR-4, NFR-5 |
| Database | SQLite dev, Postgres prod via DATABASE_URL | NFR-7 |
| Secrets detection | ADR input constraints enforced via typed model, Semgrep, unit test | C-ADR-001 |

### Repository Layout

```
.
├── backend/          # FastAPI + SQLAlchemy + Alembic
├── frontend/         # React + TypeScript (Vite)
├── docs/             # architecture.md, permissions.md, agent-extension-pack.md
├── security/         # Phase 3 artifacts
├── ops/              # Phase 3 artifacts
├── .github/workflows/  # CI, security-scan, deploy
├── openapi.yaml      # API contract
├── docker-compose.yml
├── README.md
└── AGENTS.md
```

Phase 2 conditional directories: `agent-capabilities/`, `agent-hooks/`, `mcp-server/`, `custom-agent/` (exist in repo root, empty, will be populated if Module 3 confirmed).

### Risk Register

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Time budget insufficient for full scope | High | Medium | Syft/Grype and drift detection are conditional; cut to future work if tight |
| Module 3 not completed (Phase 2 lost) | Medium | Unknown | Phase 2 is additive, not critical path; focus on Phases 1, 3, 4 |
| Decision model endpoint not provided | Low | Low | Phase 5 is operator-requested and not graded; deterministic policy ships without it |
| Rubric changes (draft → final) | Medium | Medium | Re-verify against `DataTalksClub/ai-dev-tools-zoomcamp` before final submission |
