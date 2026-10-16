# Context

Background, project scope, and structural information extracted from all ingested documents.

---

## Project Identity

- **Name:** MCP Security Posture Scanner
- **Course:** AI Dev Tools Zoomcamp (DataTalksClub), 2026 cohort
- **Type:** Final project (draft requirements at time of writing)
- **One-line:** A security scanner that connects to an MCP server as a client, enumerates tools/resources/prompts, runs a deterministic rule set, and produces a scored findings report with diff/drift detection.
- **Rubric status:** Source rubric is explicitly marked draft for the 2026 cohort; re-verify against `DataTalksClub/ai-dev-tools-zoomcamp` before final submission.

---

## Problem Statement

Teams wire third-party MCP servers into AI agents with little security review. Known risk classes:
1. Prompt injection in tool descriptions/schemas
2. Overly broad input schemas (unconstrained shell/path/URL params)
3. Missing `readOnly`/`destructive` annotations
4. Read + network/write capability pairing (confused-deputy / exfiltration)
5. Unauthenticated transport
6. Tool descriptions that change after trust is established ("rug pull")

No lightweight, self-hostable tool exists for pre-connection posture assessment.

---

## Source Documents

| Source | Type | Precedence | Key Content |
|---|---|---|---|
| `mcp-scanner-project-brief.md` | PRD | 3rd | Single source of truth. Build plan, 10 rules, data model, API draft, rubric map, repository structure, non-goals, open items, decision model (Section 13) |
| `product-spec.md` | SPEC | 2nd | Product specification with rule table (MCP-001–010), data model, API contract summary, decision model description |
| `docs/decisions/2026-10-15-decision-model.md` | ADR | 1st | LOCKED decision to add hosted decision model. Typed input, policy floor, fallback, opt-in config, trade-offs |
| `docs/architecture.md` | DOC | 4th | System architecture: React frontend, FastAPI backend, SQLite/Postgres, MCP enumeration client, rule engine, diff/drift, trust boundaries, CI/CD, containerization |
| `docs/permissions.md` | DOC | 4th | Safety boundary: enumerate-only, no tool invocation, no LLM on target metadata, localhost default, consent for external, decision model air-gap |
| `AGENTS.md` | DOC | 4th | AI-assisted development workflow log. Ground rules, workflow pattern, session log (Phase 0 complete 2026-07-23) |
| `CLAUDE.md` | DOC | 4th | Agent instructions: constraints, layout, commands |

---

## Tech Stack

- **Frontend:** React + TypeScript (Vite), Vitest + React Testing Library
- **Backend:** FastAPI, SQLAlchemy + Alembic, official `mcp` Python SDK (client only)
- **Database:** SQLite (local) / Postgres (prod) via `DATABASE_URL`
- **Containerization:** Docker + Docker Compose
- **CI/CD:** GitHub Actions
- **Deployment:** Render, Fly.io, or Railway (single container or compose-based)
- **Security tooling:** CodeRabbit, Semgrep + custom rule, Syft + Grype (conditional on time budget)

---

## Build Phases Overview

| Phase | Description | Graded | Dependency | Status |
|---|---|---|---|---|
| 0 | Repo scaffold, product-spec, openapi.yaml, compose skeleton, docs | Indirect (enables graded work) | None | ✅ Complete (2026-07-23) |
| 1 | Core application: backend, frontend, tests, containerization | Categories 1, 3–11, 14 | None | ❌ Not started |
| 2 | Agent Extension Pack (conditional) | Category 12 (2 pts) | Phase 1 complete, Module 3 confirmed | ❌ Blocked |
| 3 | Security/Audit/DevOps Hardening | Category 13 (2 pts) | Phase 1 complete | ❌ Blocked |
| 4 | Deploy and Polish | Category 10 | Phase 1 + optional/graded phases | ❌ Blocked |
| 5 | Decision Model (operator-requested) | Not graded | Phase 1 complete; must not delay Phases 3–4 | ❌ Blocked |

---

## Open Items (from PRD Section 11)

1. **Deadline / time budget:** Unconfirmed. Determines whether Phase 3 Syft/Grype and diff-based drift detection fit, or get cut to future work.
2. **Module 3 completion:** Unconfirmed. Determines whether Phase 2 (Agent Extension Pack) is in scope.
3. **External scan target support:** Decide explicitly whether shipped product supports non-localhost targets with consent, or is restricted to fixture/self-hosted only. Default to restricted per Section 2.
4. **Decision model details:** Endpoint, request/response format, auth, and data retention of the hosted model not confirmed yet. Must confirm it is the operator's own model (not employer-owned, per clean-room constraint).

Do not proceed past Phase 1 without resolving items 1 and 2.

---

## Repository Layout

```
.
├── README.md
├── product-spec.md
├── AGENTS.md
├── openapi.yaml
├── docker-compose.yml
├── frontend/             # React + TypeScript (Vite)
│   ├── src/api/          # Centralized API client
│   ├── src/components/
│   ├── src/pages/
│   └── src/tests/
├── backend/              # FastAPI
│   ├── app/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── models/       # SQLAlchemy
│   │   ├── mcp_client/   # Enumerate-only MCP client
│   │   └── rules/        # Deterministic rule engine, one module per rule
│   ├── alembic/
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/  # Against stub MCP fixture servers
├── docs/
│   ├── architecture.md
│   ├── permissions.md
│   └── agent-extension-pack.md       # Phase 2 (conditional)
├── .github/workflows/
│   ├── ci.yml
│   ├── security-scan.yml
│   └── deploy.yml
├── security/             # Phase 3
│   ├── pr-audit/
│   ├── semgrep/
│   ├── sbom/             # Conditional on time budget
│   ├── grype/            # Conditional on time budget
│   └── ai-tool-data-policy.md
├── ops/                  # Phase 3
├── agent-capabilities/   # Phase 2 (conditional)
├── agent-hooks/          # Phase 2 (conditional)
├── mcp-server/           # Phase 2 (conditional)
└── custom-agent/         # Phase 2 (conditional)
```

---

## Non-Goals

1. Not a general-purpose vulnerability scanner — MCP posture only.
2. Not a live internet-scanning tool — local/fixture targets by default.
3. Not a reimplementation of employer-internal architecture or proprietary logic.
4. The core rule engine is not, and will not become, an LLM-judgment system on untrusted input. Permanent constraint.

---

## Agent-Assisted Development Practice

- `mcp-scanner-project-brief.md` is the single source of truth for all agents.
- Section 2 constraints are non-negotiable.
- Spec-first: `openapi.yaml` precedes backend code.
- No target-server data flows to an LLM in the application; AI assistance is development-time only.
- Phase 0 verified brief against live course rubric before scaffolding.
- Every agent-produced diff is reviewed by human operator before commit.
- Work accepted only when real commands pass: `uv run pytest`, `npm test`, `npx tsc --noEmit`, `docker compose up`.
