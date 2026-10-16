"""FastAPI application entry point.

The schema is managed by Alembic (``alembic upgrade head`` runs before
uvicorn in the container), not created here.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import Settings
from app import models  # noqa: F401 -- registers models on Base.metadata
from app.routers import router as api_router
from app.observability import setup_observability
from app.metrics import setup_metrics, metrics_middleware


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: set up observability and metrics.

    Args:
        app: The FastAPI application.

    Yields:
        Control to the running application.
    """
    setup_observability(app, settings)
    setup_metrics(settings)
    yield


app = FastAPI(title="MCP Security Posture Scanner API", lifespan=lifespan)
app.middleware("http")(metrics_middleware)
app.include_router(api_router, prefix="/api")
