"""
Scan API router — endpoints for creating, listing, and inspecting scans.
"""
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.services.scan_service import (
    create_scan,
    get_scan,
    list_scans,
    get_report,
    diff_scans,
)
from app.services.consent import ConsentError

router = APIRouter()


# -- Pydantic request/response models --


# No NUL or other control characters: Postgres rejects NUL (was a 500)
NO_CONTROL = r"^[^\x00-\x1f\x7f]*$"


def _text(max_length: int, **kw) -> type[str]:
    """Build a string type with a length cap that rejects control characters.

    Args:
        max_length: Maximum number of characters.
        **kw: Extra ``StringConstraints`` options (for example ``min_length``).

    Returns:
        An ``Annotated[str, ...]`` type for a pydantic field.
    """
    return Annotated[str, StringConstraints(max_length=max_length, pattern=NO_CONTROL, **kw)]


class ScanTargetCreate(BaseModel):
    """Target submitted with a scan; limits match openapi.yaml ``ScanTargetCreate``."""

    name: _text(200, min_length=1, strip_whitespace=True)
    transport: Literal["stdio", "http"] = "stdio"
    command: _text(1000) | None = None
    args: Annotated[list[_text(1000)], Field(max_length=50)] = []
    url: _text(2048) | None = None
    allow_external: bool = False

    @model_validator(mode="after")
    def _transport_fields(self) -> "ScanTargetCreate":
        """Require ``url`` for http and ``command`` for stdio.

        Returns:
            The validated model.

        Raises:
            ValueError: If the field the transport needs is missing (422).
        """
        if self.transport == "http" and not self.url:
            raise ValueError("http transport requires url")
        if self.transport == "stdio" and not self.command:
            raise ValueError("stdio transport requires command")
        return self


class ScanCreate(BaseModel):
    target: ScanTargetCreate


# -- Endpoints --


@router.post("/scans", status_code=201)
async def post_scan(body: ScanCreate):
    """Submit a target and start a scan."""
    try:
        result = await create_scan(body.target.model_dump())
        return result
    except ConsentError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/scans")
async def get_all_scans():
    """List scans, newest first."""
    return list_scans()


@router.get("/scans/{scan_id}")
async def get_scan_by_id(scan_id: int):
    """Get scan status."""
    result = get_scan(scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return result


@router.get("/scans/{scan_id}/report")
async def get_scan_report(scan_id: int):
    """Findings report for a finished scan; 409 while pending/running."""
    result = get_report(scan_id)
    if result is None:
        scan = get_scan(scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Scan not found")
        raise HTTPException(status_code=409, detail="Scan not finished yet")
    return result


@router.get("/scans/{scan_id}/diff/{other_id}")
async def get_scan_diff(scan_id: int, other_id: int):
    """Diff findings between two scans of the same target."""
    result = diff_scans(scan_id, other_id)
    if result is None:
        scan1 = get_scan(scan_id)
        scan2 = get_scan(other_id)
        if scan1 is None or scan2 is None:
            raise HTTPException(status_code=404, detail="Scan not found")
        raise HTTPException(status_code=409, detail="Scans target different servers or are not finished")
    return result
