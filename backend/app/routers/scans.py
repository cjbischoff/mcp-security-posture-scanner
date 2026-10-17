"""
Scan API router — endpoints for creating, listing, and inspecting scans.
"""
from fastapi import APIRouter, HTTPException
from typing import Literal

from pydantic import BaseModel

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


class ScanTargetCreate(BaseModel):
    """Target submitted with a scan; transport is limited to the openapi enum."""

    name: str
    transport: Literal["stdio", "http"] = "stdio"
    command: str | None = None
    args: list[str] = []
    url: str | None = None
    allow_external: bool = False


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
