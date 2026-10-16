# MCP Security Posture Scanner

**Course:** AI Dev Tools Zoomcamp (DataTalksClub), 2026 cohort
**Type:** Final project
**Rubric source:** Draft for 2026 cohort; re-verify against `DataTalksClub/ai-dev-tools-zoomcamp` before final submission.

## Core Value

Teams wire third-party MCP servers into AI agents with little security review. Known risk classes include prompt injection in tool descriptions, overly broad input schemas, missing read-only/destructive annotations, read+network capability pairing (confused-deputy / exfiltration), unauthenticated transport, and tool descriptions that change after trust is established ("rug pull").

No lightweight, self-hostable tool exists for pre-connection posture assessment. The MCP Security Posture Scanner connects to an MCP server as a read-only client, enumerates tools/resources/prompts, runs a deterministic rule set against the metadata, and produces a scored findings report with diff/drift detection.

## Locked Decisions

| ID | Decision | Phase | Status |
|---|---|---|---|
| ADR-001 | Hosted "System 1" decision model for per-scan verdict (allow/review/block) | Phase 5 | LOCKED — operator-requested |

### ADR-001 Summary

- Input: typed only — counts per severity, triggered rule IDs (enum), transport type (enum), `allow_external` flag (bool). No free-text fields.
- Enforcement: typed input model, custom Semgrep rule (`no-llm-on-untrusted-mcp-data`), unit test asserting no target-derived string in serialized request.
- Policy floor: Critical finding → always `block`. Model can only make verdict stricter.
- Fallback: deterministic policy when model unconfigured/unavailable/unresponsive.
- Opt-in: `DECISION_MODEL_URL` and `DECISION_MODEL_API_KEY` env vars; unset = policy only.
- Data policy: scan metadata (counts, rule IDs) leaves the host; must be stated in `security/ai-tool-data-policy.md`.

## Permanent Constraints

1. **Deterministic rule engine** — Core rule engine never feeds target-server descriptions, schemas, or any untrusted data to an LLM. Permanent constraint, not a v1 limitation. (Source: PRD Section 2, item 1)
2. **Enumerate-only** — Scanner calls `list_tools`, `list_resources`, `list_prompts` only. Never invokes `call_tool`, reads resources, or executes prompts. (Source: PRD Section 2, item 3)
3. **Clean-room ruleset** — Derived from public sources only: OWASP MCP Top 10, published MCP security research, general appsec principles. No employer-internal architecture, logic, or threat models. (Source: PRD Section 2, item 4)
4. **Capped rule set** — v1 ships exactly 10 rules (MCP-001 through MCP-010). Additional rules go to future-work list. (Source: PRD Section 2, item 5)
5. **Spec-first development** — `openapi.yaml` written before backend code, used as shared contract by frontend and backend. (Source: PRD Sections 0, 5)
6. **Localhost/fixture default** — Default scan targets are localhost or self-hosted fixture servers only. External targets require explicit `allow_external` consent flag. (Source: PRD Section 2, item 2)

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | React + TypeScript (Vite), Vitest + React Testing Library | Centralized API client in `frontend/src/api/` |
| Backend | FastAPI, SQLAlchemy + Alembic, official `mcp` Python SDK (client only) | `/api` prefix on all endpoints per SPEC |
| Database | SQLite (local) / Postgres (prod) via `DATABASE_URL` | Alembic for migrations |
| Containerization | Docker + Docker Compose | Frontend, backend, Postgres |
| CI/CD | GitHub Actions | CI, security scan, deploy workflows |
| Deployment | Render, Fly.io, or Railway | Single container or compose-based |
| Security tooling | CodeRabbit, Semgrep + custom rule, Syft + Grype (conditional) | Phase 3 scope |

## Repository Layout

```
.
├── README.md                   # Problem, setup, run, test, deploy instructions
├── AGENTS.md                   # AI-assisted dev workflow documentation
├── openapi.yaml                # API contract (spec-first)
├── docker-compose.yml          # Full stack orchestration
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/            # FastAPI route handlers
│   │   ├── services/           # Business logic
│   │   ├── repositories/       # Data access layer
│   │   ├── models/             # SQLAlchemy models
│   │   ├── mcp_client/         # Enumerate-only MCP client
│   │   └── rules/              # Deterministic rule engine
│   ├── alembic/                # Database migrations
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/        # Against stub MCP fixture servers
│   └── requirements.txt / pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/                # Centralized API client
│   │   ├── components/
│   │   ├── pages/
│   │   └── tests/
│   └── package.json
├── docs/
│   ├── architecture.md         # System architecture documentation
│   ├── permissions.md          # Safety boundary documentation
│   └── agent-extension-pack.md # Phase 2 (conditional)
├── security/                   # Phase 3 audit artifacts
│   ├── pr-audit/
│   ├── semgrep/
│   ├── sbom/                   # Conditional on time budget
│   ├── grype/                  # Conditional on time budget
│   └── ai-tool-data-policy.md
├── ops/                        # Phase 3 ops artifacts
├── .github/workflows/
│   ├── ci.yml
│   ├── security-scan.yml
│   └── deploy.yml
├── agent-capabilities/         # Phase 2 (conditional on Module 3)
├── agent-hooks/                # Phase 2 (conditional on Module 3)
├── mcp-server/                 # Phase 2 (conditional on Module 3)
└── custom-agent/               # Phase 2 (conditional on Module 3)
```

## Non-Goals

1. Not a general-purpose vulnerability scanner — MCP posture only.
2. Not a live internet-scanning tool — local/fixture targets by default.
3. Not a reimplementation of employer-internal architecture or proprietary logic.
4. The core rule engine is not, and will not become, an LLM-judgment system on untrusted input. Permanent constraint.
