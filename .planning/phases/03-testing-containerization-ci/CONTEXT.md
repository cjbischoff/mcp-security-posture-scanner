# Phase 3: Testing + Containerization + CI

## Status

Planned (4 plans, not started)

## Requirements mapped

R-08, R-09, R-11, R-13 (partial)

## Plans

| # | Plan | Status | Critical tests |
|---|---|---|---|
| 3.1 | Backend Dockerfile | ○ Pending | docker compose build; container runs 86/86 tests |
| 3.2 | Frontend Dockerfile + nginx | ○ Pending | compose up full stack; /api/health proxies; HTML served |
| 3.3 | CI pipeline update | ○ Pending | CI yml valid; all jobs defined; deploy gates on CI |
| 3.4 | Semgrep custom rule + ops | ○ Pending | semgrep passes clean codebase; would match target-to-LLM patterns; /metrics responds |

## Test maintenance

After each plan:
```bash
cd backend && uv run pytest -v         # 86 backend tests — must pass
cd frontend && npx vitest run          # 26 frontend tests — must pass
cd frontend && npx tsc --noEmit        # TypeScript clean
cd backend && uv run python scripts/smoke_test.py  # smoke test
```

## Decisions

- Backend Dockerfile uses `uv sync` for fast installs; `--no-dev` excludes test deps from production image. Test runner entry point is separate (`docker compose run --rm backend uv run pytest`)
- Frontend multi-stage build: node:22-alpine for build, nginx:alpine for serve (minimal runtime)
- nginx proxies `/api/` to `http://backend:8000` (Docker Compose service name)
- Semgrep rule targets patterns that send `input_schema`, `description`, or snapshot data to any HTTP endpoint — the pattern is broad to prevent false negatives
- CI runs frontend and backend jobs in parallel; compose build check is a separate job that depends on both images being buildable
