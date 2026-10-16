# AGENTS.md — AI-Assisted Development Workflow

This file documents how AI tooling is used to build this project (rubric
category 2). It is a running log, updated per phase.

## Ground rules given to every agent

- `mcp-scanner-project-brief.md` is the single source of truth; Section 2
  constraints are non-negotiable (deterministic rules, enumerate-only,
  localhost defaults, clean-room, capped rule set).
- Spec-first: `openapi.yaml` is written before backend code and used as the
  contract by both frontend and backend work.
- No target-server data ever flows to an LLM in the application itself; the
  AI assistance documented here is development-time only.

## Agent team

Defined in [`docs/agent-team.md`](docs/agent-team.md): human operator,
orchestrator (Claude Code main session), builder, auditor, and researcher
subagents, plus the GSD planning roles used earlier. Reusable subagent
definitions: [`.claude/agents/`](.claude/agents/). Process: issue ->
contract and prompt -> builder (TDD) -> commit `Refs #N` -> orchestrator
verification -> PR + CI -> human merge -> CD.

## Task tracker

Public tracker: [GitHub Issues](https://github.com/cjbischoff/mcp-security-posture-scanner/issues).
Each issue has an acceptance-criteria checklist; commits reference issues.
Index with evidence commits: [`docs/task-tracker.md`](docs/task-tracker.md).

## Modular docs

- [`docs/agent-team.md`](docs/agent-team.md) — agent roles, handoff process, evidence
- [`.claude/agents/`](.claude/agents/) — builder, auditor, researcher subagent definitions
- [`docs/task-tracker.md`](docs/task-tracker.md) — tracker pointer, labels, issue to commit map
- [`docs/architecture.md`](docs/architecture.md) — system architecture
- [`docs/permissions.md`](docs/permissions.md) — safety boundary
- [`docs/oncall-agent.md`](docs/oncall-agent.md) — runtime on-call responder agent (the only
  place the application itself may call an LLM; operational data only)
- [`ops/observability.md`](ops/observability.md) — traces, logs, metrics in Grafana
- [`ops/alerts.md`](ops/alerts.md) — `ScanFailureRateHigh` alert
- [`ops/runbooks/`](ops/runbooks/) — runbooks (scan failure rate)
- [`docs/decisions/`](docs/decisions/) — decision records
- [`security/ai-tool-data-policy.md`](security/ai-tool-data-policy.md) — data flow documentation
- [`docs/agent-extension-pack.md`](docs/agent-extension-pack.md) — security notes
- [`security/pr-audit/review-log.md`](security/pr-audit/review-log.md) — code review log
- [`.planning/`](.planning/) — GSD roadmap, requirements, phase plans
- [`mcp-scanner-project-brief.md`](mcp-scanner-project-brief.md) — single source of truth, rubric map (Section 9)

## Workflow pattern

1. **Context files:** agents are pointed at `CLAUDE.md` (constraints +
   commands), `product-spec.md`, and `openapi.yaml` before any code task.
2. **Task delegation:** backend and frontend are built by separate agent
   sessions against the shared OpenAPI contract; root-level artifacts
   (compose, CI, docs) are handled in the orchestrating session.
3. **Manual review:** the orchestrator checks every subagent diff and reruns
   the tests before commit; the human operator reviews and merges every PR.
   Commits are conventional-format and GPG-signed.
4. **Verification:** work is accepted only when the real commands pass —
   `make test`, `make lint`, CI on the PR, and `docker compose up` demos.

## Session log

| Date | Phase | What AI did | Human review/verification |
|---|---|---|---|
| 2026-07-23 | 0 | Verified brief against live course rubric; scaffolded repo per brief Section 4; drafted `product-spec.md`, `openapi.yaml`, compose + CI skeletons, docs | Operator reviewed scope, corrected an over-eager start on Phase 1 implementation (reverted; Phase 1 not yet authorized) |
| 2026-10-16 | 1 | Ran `/gsd-ingest-docs` to synthesize 7 planning documents into `.planning/`; created PROJECT.md, REQUIREMENTS.md, ROADMAP.md (5 phases), STATE.md. Ran `/gsd-plan-phase 1` producing 5 sub-plans with test-at-every-level strategy. Executed sequentially: (1.1) pyproject.toml, SQLAlchemy models (ScanTarget, Scan, Finding), Alembic migration, health endpoint, 16 tests; (1.2) MCP enumeration client (direct JSON-RPC over subprocess to avoid mcp SDK bug), stub fixture MCP server (+3 tools with known vulnerabilities), 3 unit + 3 integration tests; (1.3) 10 deterministic rule modules (MCP-001..010) + orchestrator + registry, 37 rule unit tests + 2 integration tests; (1.4) 5 API endpoints (POST/GET scans, report, diff), consent enforcement, diff service, 11 unit + 7 integration (full ASGI end-to-end); (1.5) README update, smoke test script. | Operator approved plan breakdown with testing embedded in each plan. All 86 tests verified passing: `uv run pytest -v` (86/86). Smoke test verified: `uv run python scripts/smoke_test.py` (completed, 6 findings, 5 rules triggered). Key decision: bypassed buggy `mcp.client.stdio.stdio_client` (cancel-scope issue on CPython 3.13 + anyio) in favor of direct asyncio subprocess JSON-RPC — simpler and more maintainable. |
| 2026-10-16 | 2 | Planned and executed 3 sub-plans: (2.1) Vite+React+TS scaffold, centralized API client (6 endpoints), MSW mock handlers, Vitest+RTL config, 8 API client tests; (2.2) NewScanPage form (name, transport, command/args/URL, consent toggle), ScansPage list with auto-polling, 8 RTL tests; (2.3) ScanReportPage (severity badges, findings, remediation), ScanDiffPage (added/removed/unchanged/drift), 10 RTL tests. | Operator approved 3-plan decomposition. Full verification: `cd frontend && npm test` (26/26), `npx tsc --noEmit` clean, `cd backend && uv run pytest -v` (86/86). Key correction: test files excluded from build tsconfig to fix production build. |
| 2026-10-16 | 3 | Planned and executed 4 sub-plans: (3.1) Backend Dockerfile (uv + uvicorn); (3.2) Multi-stage frontend Dockerfile (node build → nginx serve) + nginx proxy config; (3.3) CI update: `npm test` script, compose-build job added; (3.4) Custom Semgrep rule `no-llm-on-untrusted-mcp-data`, `/api/metrics` endpoint, ops sample output. | Operator approved containerized security scanning approach. Full verification: `docker compose build backend` + `frontend`, `compose up -d` all 3 services healthy. Semgrep rule verified: 0 findings on clean code, 1 finding on test violation. Dockerfile USER fix applied (Semgrep finding). |
| 2026-10-16 | 4 | Planned and executed 3 sub-plans: (4.1) Semgrep `p/security-audit` + `p/owasp-top-ten` SARIF results, Syft SBOM (218 components), Grype vuln scan (0 findings) — all via containerized security scanner; (4.2) PR audit log, AI tool data policy; (4.3) Agent/extension security notes, updated README, AGENTS.md, full smoke verification. | Operator requested containerized security tools. Built `security/Dockerfile` with semgrep + syft + grype. Final verification: 112 tests all green (86 backend + 26 frontend), smoke test passes, compose builds, semgrep 0 findings. |
| 2026-10-16 | oncall | Built the on-call responder agent (`oncall/`): Grafana webhook -> OpenAI-compatible LLM tool loop with a fixed 7-tool allowlist -> deterministic runbook fallback -> verify -> incident report. TDD: tests written first against fakes (httpx MockTransport for backend, Prometheus, and LLM). Built in parallel with the observability agent against agreed contracts (webhook URL, metric names, admin fault API). | Operator fixed the design: provider-agnostic LLM over httpx (no SDK), runbook fallback so a clone with no key still fixes the incident, server-side allowlist, data boundary per brief Section 2 item 1. Verified: 38 oncall tests, ruff clean, and a real Grafana-fired `ScanFailureRateHigh` alert cleared the fault in compose (`ops/incidents/20261016T222020Z-ScanFailureRateHigh-ceb72b.md`). |
| 2026-10-16 | audit + build | Auditor subagents reviewed repo/spec consistency, CI/scaffold, and rubric scoring; findings became issues #2-#12. Orchestrator fixed public-mode stdio (#4) and CI/`make test` (#5). Builder subagents: persistence (#6, SQLAlchemy repository + Alembic), then observability + alerting (#7, #8) in parallel with the on-call agent (#9) against shared contracts. Orchestrator added SHA-tagged image build, auto dev deploy, and manual prod deploy (#10); researcher subagent compared free hosting. Docs and tracker (#11). | Operator chose hosting and the LLM approach and merges PRs. Orchestrator reran `make test` after each stream: 114 backend + 38 oncall + 26 frontend = 178 passing; CI on PR #13. Hosting URLs pending Render setup. |

## Prompts and delegation records

### Phase 1 — Doc ingestion and planning

Documents ingested: `mcp-scanner-project-brief.md` (PRD), `product-spec.md` (SPEC), `docs/architecture.md` (DOC), `docs/permissions.md` (DOC), `docs/decisions/2026-10-15-decision-model.md` (ADR, LOCKED), `AGENTS.md` (DOC), `CLAUDE.md` (DOC). Synthesized into `.planning/intel/` and routed through `gsd-roadmapper` to produce PROJECT.md, REQUIREMENTS.md (40 reqs, 100% mapped to phases), ROADMAP.md (5 phases), STATE.md.

Phase 1 decomposed into 5 sub-plans:
- **1.1** — Project scaffold + DB (pyproject.toml, SQLAlchemy models, Alembic, /api/health)
- **1.2** — MCP enumeration client + stub fixture MCP server
- **1.3** — 10 deterministic rules + orchestrator + registry
- **1.4** — Scan/report/diff API + services + consent enforcement
- **1.5** — Docs, README, smoke test

### Phase 1 — Technical decisions

1. **Direct JSON-RPC over asyncio subprocess** — rejected `mcp.client.stdio.stdio_client` due to a cancel-scope RuntimeError in mcp SDK 1.30 + anyio 4.15.1 on CPython 3.13. The custom implementation is simpler (no anyio dependency for the client), handles initialize handshake + 3 list methods, and is easier to debug.
2. **In-memory storage for Plan 1.4 (superseded 2026-10-16)** — chose in-memory dict storage over SQLAlchemy for Plan 1.4 to keep the API testable without DB setup. DB integration is deferred to a refactor step (or Plan 1.5 if needed). Superseded: scans, targets, and findings now persist through `app/repositories/scans.py` (SQLAlchemy + Alembic); targets are keyed by full connection info, not name.
3. **Word-boundary param matching in MCP-004** — substring matching caused false positives (e.g. "target_url" matched "get"). Split on underscore and match whole words only.
4. **Async scan execution** — uses `asyncio.create_task` for background scan execution; the task opens its own DB session. FastAPI `BackgroundTasks` would work but only for sync tasks; `create_task` is simpler for the async scan flow.
