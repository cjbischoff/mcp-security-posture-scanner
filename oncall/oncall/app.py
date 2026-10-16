"""HTTP entry point: Grafana posts alerts to ``POST /alert``.

Run: ``uvicorn oncall.app:app --host 0.0.0.0 --port 8080``.
"""

import logging
import threading

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from oncall.agent import respond
from oncall.tools import Config, parse_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("oncall")


def create_app(config: Config | None = None, client: httpx.Client | None = None) -> FastAPI:
    """Build the webhook app.

    Args:
        config: Settings; read from the environment when omitted.
        client: httpx client for outbound calls; a default one when omitted.

    Returns:
        FastAPI app with ``POST /alert`` and ``GET /health``.

    Example:
        >>> app = create_app(Config(admin_token="t"))
    """
    config = config or Config.from_env()
    # Constructs the client; no request body. The data boundary lives in tools.py.
    client = client or httpx.Client()  # nosemgrep: no-llm-on-untrusted-mcp-data
    app = FastAPI(title="MCP scanner on-call agent")
    # One incident at a time; Grafana re-sends while an alert keeps firing.
    busy = threading.Lock()

    def handle(payload: dict) -> None:
        if not busy.acquire(blocking=False):
            log.info("incident already in progress, skipping duplicate webhook")
            return
        try:
            respond(payload, config, client)
        except Exception:
            log.exception("responder failed")
        finally:
            busy.release()

    @app.get("/health")
    def health() -> dict:
        """Liveness probe."""
        return {"status": "ok"}

    @app.post("/alert", status_code=202)
    async def alert(request: Request, tasks: BackgroundTasks) -> JSONResponse:
        """Accept a Grafana webhook; respond in the background."""
        try:
            payload = await request.json()
            parsed = parse_alert(payload)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        log.info("alert received name=%s status=%s", parsed["alertname"], parsed["status"])
        tasks.add_task(handle, payload)
        return JSONResponse({"accepted": True, "alert": parsed["alertname"]}, status_code=202)

    return app


app = create_app()
