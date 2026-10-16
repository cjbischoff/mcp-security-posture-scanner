FROM python:3.13-slim

# Install uv
RUN pip install --no-cache-dir uv==0.12.23

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY tests/ ./tests/
COPY scripts/ ./scripts/

# Create non-root user with home directory
RUN addgroup --system --gid 1001 app && adduser --system --uid 1001 --ingroup app --home /home/app app
USER app

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
