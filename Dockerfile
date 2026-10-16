# Single deploy image: FastAPI serves the API and the built React app.
# Local development uses docker-compose.yml (separate frontend/backend/db).

FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
RUN pip install --no-cache-dir uv==0.12.23
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --no-dev --frozen
COPY backend/app/ ./app/
COPY backend/alembic/ ./alembic/
COPY backend/alembic.ini ./
# Bundled fixture servers: the only stdio targets allowed in public mode
COPY backend/tests/fixtures/ ./tests/fixtures/
COPY --from=web /web/dist ./static

RUN addgroup --system --gid 1001 app && adduser --system --uid 1001 --ingroup app --home /home/app app
USER app

ARG GIT_SHA=dev
ENV APP_VERSION=$GIT_SHA STATIC_DIR=/app/static PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
# Render sets PORT; default 8000 elsewhere
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
