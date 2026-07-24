# MCP Security Posture Scanner

Final project for AI Dev Tools Zoomcamp (DataTalksClub, 2026 cohort).
`mcp-scanner-project-brief.md` is the single source of truth — its Section 2
constraints are non-negotiable:

1. Rule engine is deterministic — never feed target-server descriptions/schemas
   to an LLM.
2. Default scan targets are localhost/fixture only; external needs logged
   consent flag.
3. Enumerate only — never invoke a target server's tools.
4. Clean-room: public sources only, no employer-internal logic.
5. Rule set capped at ~10-12 checks.

## Layout

- `backend/` — FastAPI + SQLAlchemy/Alembic; `app/rules/` one module per rule,
  `app/mcp_client/` enumeration client. Tests: `tests/unit/`,
  `tests/integration/` (fixture MCP servers in `tests/fixtures/`).
- `frontend/` — React + TypeScript (Vite); single API client in `src/api/`.
- `openapi.yaml` — contract, written before backend. Keep in sync.

## Commands

- Backend: `cd backend && uv sync && uv run pytest`
- Frontend: `cd frontend && npm install && npm test`
- Full stack: `docker compose up --build`
