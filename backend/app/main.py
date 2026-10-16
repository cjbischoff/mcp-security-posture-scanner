"""FastAPI application entry point.

The schema is managed by Alembic (``alembic upgrade head`` runs before
uvicorn in the container), not created here.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
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


def mount_frontend(target: FastAPI, static_dir: str) -> None:
    """Serve the built React app from ``static_dir``.

    Real files are served directly. Any other non-API path returns
    index.html, so client-side routes work on reload. Register API routes
    before calling this.

    Args:
        target: The application to mount the frontend on.
        static_dir: Directory that holds index.html and the assets folder.
    """
    root = Path(static_dir).resolve()

    @target.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        """Return a static file, or index.html for client-side routes."""
        file = (root / path).resolve()
        if path and file.is_file() and file.is_relative_to(root):
            return FileResponse(file)
        return FileResponse(root / "index.html")


app = FastAPI(title="MCP Security Posture Scanner API", lifespan=lifespan)
app.middleware("http")(metrics_middleware)
app.include_router(api_router, prefix="/api")

# Deploy image only: one container serves API + frontend (see root Dockerfile)
if os.environ.get("STATIC_DIR"):
    mount_frontend(app, os.environ["STATIC_DIR"])
