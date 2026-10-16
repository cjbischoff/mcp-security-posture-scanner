FROM python:3.13-slim

RUN pip install --no-cache-dir uv==0.12.23

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY oncall/ ./oncall/

RUN addgroup --system --gid 1001 app && adduser --system --uid 1001 --ingroup app --home /home/app app \
    && mkdir -p /app/ops/incidents && chown app:app /app/ops/incidents
USER app

ENV INCIDENTS_DIR=/app/ops/incidents
EXPOSE 8080

# Run from the venv directly so nothing re-syncs dev dependencies at start.
CMD ["/app/.venv/bin/uvicorn", "oncall.app:app", "--host", "0.0.0.0", "--port", "8080"]
