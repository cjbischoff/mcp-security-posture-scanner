"""Admin fault injection, used to trigger the ScanFailureRateHigh alert on demand.

Every route needs ``Authorization: Bearer $ADMIN_TOKEN``. If ``ADMIN_TOKEN``
is unset, the routes return 404, so a deploy without the variable exposes
nothing.
"""
import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException

from app.services.scan_service import FAULTS


def require_admin(authorization: str | None = Header(default=None)) -> None:
    """Check the bearer token against ``ADMIN_TOKEN``.

    Args:
        authorization: The ``Authorization`` request header.

    Raises:
        HTTPException: 404 if ADMIN_TOKEN is unset, 401 if the token is
            missing or wrong.
    """
    token = os.environ.get("ADMIN_TOKEN")
    if not token:
        raise HTTPException(status_code=404, detail="Not Found")
    given = (authorization or "").removeprefix("Bearer ")
    if not authorization or given == authorization or not hmac.compare_digest(given, token):
        raise HTTPException(status_code=401, detail="Invalid admin token")


router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


@router.get("/faults")
def get_faults() -> dict:
    """Show which faults are on.

    Returns:
        ``{"scan_failure": bool}``.
    """
    return dict(FAULTS)


@router.post("/faults/scan-failure")
def enable_scan_failure() -> dict:
    """Make every new scan fail fast with category ``fault_injected``.

    Returns:
        The fault flags after the change.
    """
    FAULTS["scan_failure"] = True
    return dict(FAULTS)


@router.delete("/faults/scan-failure")
def disable_scan_failure() -> dict:
    """Turn the scan failure fault off.

    Returns:
        The fault flags after the change.
    """
    FAULTS["scan_failure"] = False
    return dict(FAULTS)
