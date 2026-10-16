from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import Settings
from app.database import Base
from app import models  # noqa: register models
from app.routers import router as api_router
from app.observability import setup_observability
from app.metrics import setup_metrics, metrics_middleware


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — runs startup/shutdown logic."""
    # Create tables on startup for SQLite simplicity (Alembic for prod)
    from sqlalchemy import create_engine

    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    # Setup observability
    setup_observability(app, settings)
    setup_metrics(settings)
    yield


app = FastAPI(title="MCP Security Posture Scanner API", lifespan=lifespan)
app.middleware("http")(metrics_middleware)
app.include_router(api_router, prefix="/api")
