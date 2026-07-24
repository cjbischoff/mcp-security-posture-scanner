# Architecture

Planned system architecture (Phase 0 — updated as implementation lands).

## Components

- **Frontend** — React + TypeScript (Vite). All backend calls go through one
  centralized API client (`frontend/src/api/`). Pages: submit scan, scan
  list/status, findings report, scan diff.
- **Backend** — FastAPI. Layered: routers → services → repositories →
  SQLAlchemy models. Two special modules:
  - `app/mcp_client/` — connects to a scan target over stdio or streamable
    HTTP and **only enumerates** tools/resources/prompts.
  - `app/rules/` — deterministic rule engine, one module per rule (capped at
    10 for v1), run over the enumerated snapshot. No LLM involvement.
- **Database** — SQLite locally, Postgres in prod, selected via
  `DATABASE_URL`. Alembic migrations.
- **Containerization** — Docker Compose: `frontend` (nginx, proxies `/api`),
  `backend` (uvicorn :8000), `db` (Postgres 16).
- **CI/CD** — GitHub Actions: `ci.yml` lints and runs unit + integration
  tests on every push/PR; `deploy.yml` deploys on merge to main after CI
  passes; `security-scan.yml` (Phase 3) runs Semgrep incl. the custom
  `no-llm-on-untrusted-mcp-data` rule.

## Scan flow

```mermaid
sequenceDiagram
    participant U as User (browser)
    participant F as Frontend
    participant B as Backend API
    participant M as MCP Client (enumerate-only)
    participant T as Target MCP Server
    participant D as Database

    U->>F: submit target
    F->>B: POST /api/scans
    B->>D: create ScanTarget + Scan(pending)
    B-->>F: 201 (scan id)
    B->>M: background task
    M->>T: initialize, list_tools / list_resources / list_prompts
    Note over M,T: never call_tool — metadata only
    M-->>B: snapshot (tools, resources, prompts)
    B->>B: rule engine: MCP-001..009 over snapshot
    B->>D: store snapshot + findings, Scan(completed)
    F->>B: poll GET /api/scans/{id}
    F->>B: GET /api/scans/{id}/report
    B-->>F: findings by severity
```

## Diff / drift detection

`GET /api/scans/{id}/diff/{other_id}` compares two completed scans of the
same target: findings keyed by `(rule_id, subject)` produce added/removed/
unchanged sets; rule MCP-010 flags findings that changed severity or
disappeared **without** a corresponding description change in the stored
snapshots — the "rug pull" signal.

## Trust boundaries

```mermaid
flowchart LR
    subgraph trusted [Trusted]
        FE[Frontend] --> BE[Backend + rule engine] --> DB[(DB)]
    end
    subgraph untrusted [Untrusted input]
        TS[Target MCP server metadata]
    end
    BE -- "enumerate only,<br/>deterministic parsing" --> TS
    TS -. "never reaches an LLM" .-> BE
```

Target-server metadata is treated as hostile input: parsed by deterministic
rules, rendered inertly in the UI, never forwarded to any LLM API.
