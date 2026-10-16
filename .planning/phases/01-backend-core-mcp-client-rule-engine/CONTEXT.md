# Phase 1: Backend Core + MCP Client + Rule Engine

## Status

Planned (5 plans, not started)

## Requirements mapped

FR-1, FR-2, FR-3, FR-4, FR-5, FR-7, MCP-001..MCP-010, NFR-1, NFR-2, NFR-3, NFR-4, NFR-5, R-01, R-02, R-03, R-06, R-07, R-14

## Plans

| # | Plan | Status | Tests |
|---|---|---|---|
| 1.1 | Project scaffold + DB | ○ Pending | Unit: models, config, health |
| 1.2 | MCP enumeration client | ○ Pending | Unit: parse/error; Integration: stub MCP server |
| 1.3 | Deterministic rule engine | ○ Pending | Unit: 10 rules; Integration: fixture snapshot |
| 1.4 | Scan/report/diff API + services | ○ Pending | Unit: consent, diff, scan lifecycle; Integration: full end-to-end |
| 1.5 | Docs, README, smoke test | ○ Pending | Smoke: standalone script, full test suite green |

## Test progression

Each plan runs its own tests plus all prior plans' tests — the suite expands monotonically.

```bash
# After plan 1.1:
uv run pytest tests/unit/ -v

# After plan 1.4 (all code complete):
uv run pytest tests/unit/ tests/integration/ -v

# After plan 1.5 (final smoke):
uv run pytest -v && uv run python scripts/smoke_test.py
```

## Dependencies between plans

```
1.1 (scaffold) → 1.2 (mcp client) → 1.3 (rules) → 1.4 (api) → 1.5 (docs)
```

## Decisions made during planning

- Test strategy: unit tests on every rule + service, integration tests on full flow against real fixture MCP server, smoke script for CI/manual validation
- Fixture MCP server is part of test infrastructure (not production), lives in `tests/fixtures/`
- Async background scan task via `asyncio.create_task` or FastAPI lifespan + background tasks
- SQLite in-memory for tests, SQLite file for local dev, Postgres for prod via DATABASE_URL
