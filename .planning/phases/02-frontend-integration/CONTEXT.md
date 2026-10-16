# Phase 2: Frontend + Integration

## Status

Planned (3 plans, not started)

## Requirements mapped

- R-04 (Frontend — functional, centralized API client, tests)
- Phase 2 Success Criteria 1-4 (submit scan, severity report, diff, consent toggle)

## Plans

| # | Plan | Status | Tests |
|---|---|---|---|
| 2.1 | Vite scaffold + API client | ○ Pending | Unit: API client (6), TypeScript compile |
| 2.2 | Scan form + list page | ○ Pending | RTL: NewScanPage (9), ScansPage (5), shared components |
| 2.3 | Report + diff pages + navigation | ○ Pending | RTL: ScanReportPage (8), ScanDiffPage (5), App navigation |

## Test maintenance

Backend tests must remain green throughout Phase 2:

```bash
cd frontend && npm test           # all frontend tests
cd backend && uv run pytest -v    # 86 backend tests
cd backend && uv run python scripts/smoke_test.py  # smoke test
```

Plan 2.3 is complete only when all three commands pass.

## Dependencies between plans

```
2.1 (scaffold + API client) → 2.2 (form + list) → 2.3 (report + diff + nav)
```

## Decisions

- MSW for HTTP interception in tests (no real backend needed during frontend tests)
- React Router v7 for declarative routing
- Vitest with jsdom environment (no browser needed for tests)
- API client is a single file with all endpoints, not one file per endpoint
- MSW handlers return fixture data matching stub MCP server output pattern
