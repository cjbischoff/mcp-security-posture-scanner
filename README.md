# MCP Security Posture Scanner

Final project for the [AI Dev Tools Zoomcamp](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp) (DataTalksClub, 2026 cohort).

**Status: Phase 0 (scaffold + specs). No application code yet.**

## Problem

Teams wire third-party MCP (Model Context Protocol) servers into AI agents
with little to no security review. Risk classes include prompt injection in
tool descriptions, overly broad input schemas, missing safety annotations,
confused-deputy capability pairings, unauthenticated transport, and
descriptions that change after a client has trusted them ("rug pull").

This project builds a lightweight, self-hostable scanner: point it at an MCP
server, it connects as a client, enumerates tools/resources/prompts, runs a
deterministic rule set, and produces a scored findings report — with diffing
between scans of the same server to catch description drift.

**Safety boundary:** the scanner only enumerates (`list_tools`,
`list_resources`, `list_prompts`). It never invokes a target server's tools.
The rule engine is deterministic — target metadata is never fed to an LLM.
See `docs/permissions.md`.

## Key documents

| File | Purpose |
|---|---|
| `mcp-scanner-project-brief.md` | Single source of truth: constraints, build order, rubric mapping |
| `product-spec.md` | Functional spec: rules, data model, flows |
| `openapi.yaml` | API contract (spec-first, written before backend) |
| `docs/architecture.md` | System architecture |
| `docs/permissions.md` | Enumerate-only safety boundary |
| `AGENTS.md` | AI-assisted development workflow log |
| `docs/decisions/` | Decision records (e.g. the Phase 5 decision model) |

## Repository structure

```
backend/            FastAPI + SQLAlchemy/Alembic
  app/rules/        deterministic check engine, one module per rule
  app/mcp_client/   enumeration-only MCP client
  tests/unit/       rule engine unit tests
  tests/integration/ full scans against stub fixture servers
  tests/fixtures/   known-vulnerable stub MCP servers (test targets only)
frontend/           React + TypeScript; single API client in src/api/
.github/workflows/  ci.yml (lint+tests), deploy.yml, security-scan.yml (Phase 3)
docs/               architecture, permissions, agent extension pack docs
security/           Phase 3 artifacts: CodeRabbit PR audits, Semgrep SARIF, SBOM, policy
ops/                Phase 3 artifacts: /health and /metrics sample output
agent-capabilities/ Phase 2 (conditional on Module 3)
agent-hooks/        Phase 2
mcp-server/         Phase 2: scanner exposed as MCP tools
custom-agent/       Phase 2
```

## Build plan (from the brief, in order)

- [x] **Phase 0 — Setup:** scaffold, `product-spec.md`, `openapi.yaml`, compose skeleton
- [ ] **Phase 1 — Core app:** MCP client, rule engine (capped at 10 rules), API per contract, frontend, unit + integration tests, `docker compose up` end to end
- [ ] **Phase 2 — Agent extension pack** *(blocked: confirm Module 3 completion first)*
- [ ] **Phase 3 — Security/audit/DevOps hardening:** CodeRabbit artifacts, Semgrep (+ custom `no-llm-on-untrusted-mcp-data` rule), Syft/Grype if time, `/health` `/metrics`, AI data policy
- [ ] **Phase 4 — Deploy + polish:** cloud deploy, deploy-on-merge workflow, final README/AGENTS.md
- [ ] **Phase 5 — Decision model** *(operator-requested, after Phase 1):* `GET /api/scans/{id}/verdict` returns allow/review/block + score. The operator's hosted model receives scanner-derived counts and rule IDs only, never target text. Deterministic policy fallback. See brief Section 13.

Do not start Phase 2/3 before Phase 1 tests pass and the open items below are
resolved.

## Open items (resolve before Phase 2/3)

1. **Deadline / time budget** — determines whether Syft/Grype and drift
   detection both fit v1.
2. **Module 3 completion** — gates the entire Agent Extension Pack (rubric
   category 12).
3. **External scan targets** — default is localhost/fixture only; expanding
   requires an explicit decision (consent flag + disclaimer already specified).
4. **Deployment target** — course expects a public cloud URL (Render/Fly/Railway);
   confirm an approved hosting target before Phase 4.
5. **Decision model** — confirm the hosted model's endpoint, request/response
   format, auth, and data retention before Phase 5.

## Running (Phase 1 onward)

```bash
docker compose up --build     # full stack: frontend :3000, backend :8000, Postgres
cd backend && uv sync && uv run pytest            # backend tests
cd frontend && npm install && npm test            # frontend tests
```

## Rubric coverage

See brief Section 9 for the full mapping table. Every deliverable in this
repo traces to a rubric line; anything else is out of scope.

## Future work (explicitly not v1)

- Rules beyond the capped set (rug-pull hash pinning, OAuth scope analysis)
- Scheduled re-scans and alerting
- Tool-inventory SBOM export
