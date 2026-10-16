test:
	cd backend && uv run pytest -q
	cd frontend && npm test

lint:
	cd backend && uv run ruff check .
	cd frontend && npm run build

.PHONY: test lint
