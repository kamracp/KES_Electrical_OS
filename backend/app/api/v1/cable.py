"""
API endpoint for cable sizing and voltage drop calculations.
KESE-S2-M13
"""

from fastapi import APIRouter, HTTPException, status

from app.schemas.cable import (
    CableSizingRequest,
    CableSizingResponse,
)
from app.services.cable import (
    CableSizingService,
)

router = APIRouter(
    prefix="/electrical/cable",
    tags=["Electrical Cable Sizing"],
)

_service = CableSizingService()


@router.post(
    "/calculate",
    response_model=CableSizingResponse,
    status_code=status.HTTP_200_OK,
)
def calculate_cable_sizing(
    payload: CableSizingRequest,
) -> CableSizingResponse:
    """Calculate one validated cable sizing study."""

    try:
        result = _service.calculate_cable_sizing(payload)
        return CableSizingResponse.from_domain(result)

    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


__all__ = [
    "router",
]
